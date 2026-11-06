import secrets
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, abort, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

from models import db, Usuario, LogAuditoria, CadastroAutorizado
from forms import AcaoAdminForm, AutorizarCadastroForm
from decorators import perfil_requerido
from services.auditoria import registrar, Acoes
from services import codigos_recuperacao

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ACOES_DE_ALERTA = ["LOGIN_FALHA", "LOGIN_BLOQUEADO", "DOIS_FATORES_FALHA", "SENHA_REDEFINICAO_FALHA", "ACESSO_NEGADO"]
ALFABETO_SENHA = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"


def _conferir_csrf():
    if not AcaoAdminForm().validate_on_submit():
        abort(400)


def _alvo(usuario_id):
    usuario = db.get_or_404(Usuario, usuario_id)
    if usuario.id == current_user.id:
        flash("Você não pode executar esta ação na sua própria conta.", "warning")
        return None
    return usuario


def bibliotecarios_ativos() -> int:
    return Usuario.query.filter_by(perfil="admin", ativo=True).count()


@admin_bp.route("/")
@login_required
@perfil_requerido("superadmin")
def painel():
    agora = datetime.now()
    inicio_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    ultimas_24h = agora - timedelta(hours=24)

    por_perfil = dict(db.session.query(Usuario.perfil, func.count(Usuario.id)).group_by(Usuario.perfil).all())
    alertas = (
        db.session.query(LogAuditoria.acao, func.count(LogAuditoria.id))
        .filter(LogAuditoria.acao.in_(ACOES_DE_ALERTA), LogAuditoria.criado_em >= ultimas_24h)
        .group_by(LogAuditoria.acao)
        .all()
    )
    painel = {
        "data_atualizacao": agora,
        "total_usuarios": sum(por_perfil.values()),
        "por_perfil": [
            ("Alunos", por_perfil.get("aluno", 0)),
            ("Professores", por_perfil.get("professor", 0)),
            ("Bibliotecários", por_perfil.get("admin", 0)),
            ("Administradores", por_perfil.get("superadmin", 0)),
        ],
        "inativos": Usuario.query.filter_by(ativo=False).count(),
        "autorizacoes_pendentes": CadastroAutorizado.query.filter(CadastroAutorizado.usado_em.is_(None)).count(),
        "sem_2fa": Usuario.query.filter_by(dois_fatores_ativo=False).count(),
        "logins_hoje": LogAuditoria.query.filter(
            LogAuditoria.acao == "LOGIN_SUCESSO", LogAuditoria.criado_em >= inicio_dia
        ).count(),
        "alertas": dict(alertas),
        "total_alertas": sum(qtd for _, qtd in alertas),
        "bibliotecarios_ativos": bibliotecarios_ativos(),
        "ultimas_acoes": LogAuditoria.query.order_by(LogAuditoria.criado_em.desc()).limit(8).all(),
    }
    return render_template("admin/painel.html", painel=painel)


@admin_bp.route("/usuarios")
@login_required
@perfil_requerido("superadmin")
def usuarios():
    filtros = {
        "perfil": request.args.get("perfil", "").strip(),
        "situacao": request.args.get("situacao", "").strip(),
        "q": request.args.get("q", "").strip(),
    }
    consulta = Usuario.query
    if filtros["perfil"] in Usuario.NOMES_PERFIL:
        consulta = consulta.filter(Usuario.perfil == filtros["perfil"])
    if filtros["situacao"] == "ativos":
        consulta = consulta.filter(Usuario.ativo.is_(True))
    elif filtros["situacao"] == "inativos":
        consulta = consulta.filter(Usuario.ativo.is_(False))
    if filtros["q"]:
        termo = f"%{filtros['q']}%"
        consulta = consulta.filter((Usuario.nome.ilike(termo)) | (Usuario.email.ilike(termo)))

    lista = consulta.order_by(Usuario.criado_em.desc()).all()
    registrar(Acoes.ACESSO_AREA_ADMIN, f"Acessou a lista de usuários ({len(lista)} registros)")
    return render_template(
        "admin/usuarios.html",
        usuarios=lista,
        filtros=filtros,
        perfis=Usuario.NOMES_PERFIL,
        form_acao=AcaoAdminForm(),
        bibliotecarios_ativos=bibliotecarios_ativos(),
    )


@admin_bp.route("/autorizacoes", methods=["GET", "POST"])
@login_required
@perfil_requerido("superadmin")
def autorizacoes():
    form = AutorizarCadastroForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        perfil = current_app.config["DOMINIOS_PERFIL"][email.split("@")[-1]]
        if Usuario.query.filter_by(email=email).first():
            form.email.errors.append("Este e-mail já possui conta no sistema.")
        elif CadastroAutorizado.query.filter_by(email=email).first():
            form.email.errors.append("Este e-mail já está liberado para cadastro.")
        else:
            autorizacao = CadastroAutorizado(email=email, perfil=perfil, autorizado_por_id=current_user.id)
            db.session.add(autorizacao)
            db.session.commit()
            nome_perfil = Usuario.NOMES_PERFIL.get(perfil, perfil)
            registrar(Acoes.CADASTRO_AUTORIZADO, f"Cadastro liberado para {email} (perfil {nome_perfil})")
            flash(
                f"Cadastro liberado para {email} ({nome_perfil}). Agora a pessoa já pode "
                "acessar a tela de cadastro e criar a própria senha.",
                "success",
            )
            return redirect(url_for("admin.autorizacoes"))

    pendentes = (
        CadastroAutorizado.query.filter(CadastroAutorizado.usado_em.is_(None))
        .order_by(CadastroAutorizado.criado_em.desc()).all()
    )
    usadas = (
        CadastroAutorizado.query.filter(CadastroAutorizado.usado_em.isnot(None))
        .order_by(CadastroAutorizado.usado_em.desc()).limit(20).all()
    )
    return render_template(
        "admin/autorizacoes.html", form=form, pendentes=pendentes, usadas=usadas, form_acao=AcaoAdminForm(),
    )


@admin_bp.route("/autorizacoes/<int:autorizacao_id>/revogar", methods=["POST"])
@login_required
@perfil_requerido("superadmin")
def revogar_autorizacao(autorizacao_id):
    _conferir_csrf()
    autorizacao = db.get_or_404(CadastroAutorizado, autorizacao_id)
    if not autorizacao.pendente:
        flash("Este cadastro já foi concluído. Para bloquear o acesso, desative o usuário.", "warning")
        return redirect(url_for("admin.autorizacoes"))
    email = autorizacao.email
    db.session.delete(autorizacao)
    db.session.commit()
    registrar(Acoes.AUTORIZACAO_REVOGADA, f"Liberação de cadastro cancelada para {email}")
    flash(f"Liberação de cadastro de {email} cancelada.", "success")
    return redirect(url_for("admin.autorizacoes"))


@admin_bp.route("/usuarios/<int:usuario_id>/desativar", methods=["POST"])
@login_required
@perfil_requerido("superadmin")
def desativar(usuario_id):
    _conferir_csrf()
    usuario = _alvo(usuario_id)
    if usuario is None:
        return redirect(url_for("admin.usuarios"))
    if usuario.is_superadmin:
        flash("Contas de Administrador não podem ser desativadas.", "danger")
        return redirect(url_for("admin.usuarios"))
    if not usuario.ativo:
        flash(f"{usuario.nome} já está desativado(a).", "info")
        return redirect(url_for("admin.usuarios"))

    usuario.ativo = False
    db.session.commit()
    registrar(Acoes.USUARIO_DESATIVADO, f"Conta de {usuario.email} ({usuario.perfil_nome}) desativada")
    mensagem = f"{usuario.nome} foi desativado(a) e perdeu o acesso imediatamente."
    if usuario.perfil == "admin" and bibliotecarios_ativos() == 0:
        mensagem += " Atenção: a biblioteca está sem nenhum bibliotecário ativo."
    flash(mensagem, "success")
    return redirect(url_for("admin.usuarios"))


@admin_bp.route("/usuarios/<int:usuario_id>/reativar", methods=["POST"])
@login_required
@perfil_requerido("superadmin")
def reativar(usuario_id):
    _conferir_csrf()
    usuario = _alvo(usuario_id)
    if usuario is None:
        return redirect(url_for("admin.usuarios"))
    usuario.ativo = True
    db.session.commit()
    registrar(Acoes.USUARIO_REATIVADO, f"Conta de {usuario.email} ({usuario.perfil_nome}) reativada")
    flash(f"{usuario.nome} foi reativado(a).", "success")
    return redirect(url_for("admin.usuarios"))


@admin_bp.route("/usuarios/<int:usuario_id>/resetar-2fa", methods=["POST"])
@login_required
@perfil_requerido("superadmin")
def resetar_2fa(usuario_id):
    _conferir_csrf()
    usuario = _alvo(usuario_id)
    if usuario is None:
        return redirect(url_for("admin.usuarios"))
    usuario.dois_fatores_ativo = False
    usuario.totp_secret = None
    usuario.totp_ultimo_passo = None
    db.session.commit()
    codigos_recuperacao.apagar(usuario)
    registrar(Acoes.DOIS_FATORES_RESETADO, f"Administrador redefiniu a verificação em duas etapas de {usuario.email}")
    flash(
        f"Verificação em duas etapas de {usuario.nome} redefinida. No próximo login, "
        "será pedido para configurar o Google Authenticator novamente.",
        "success",
    )
    return redirect(url_for("admin.usuarios"))


@admin_bp.route("/usuarios/<int:usuario_id>/redefinir-senha", methods=["POST"])
@login_required
@perfil_requerido("superadmin")
def redefinir_senha(usuario_id):
    _conferir_csrf()
    usuario = _alvo(usuario_id)
    if usuario is None:
        return redirect(url_for("admin.usuarios"))
    temporaria = "".join(secrets.choice(ALFABETO_SENHA) for _ in range(10))
    usuario.set_senha(temporaria)
    db.session.commit()
    registrar(Acoes.SENHA_REDEFINIDA_ADMIN, f"Administrador gerou senha temporária para {usuario.email}")
    return render_template("admin/senha_temporaria.html", usuario=usuario, senha=temporaria)
