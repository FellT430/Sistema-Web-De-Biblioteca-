import secrets
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, abort, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

from models import db, Usuario, LogAuditoria, StatusCadastro
from forms import AcaoAdminForm, RecusarExclusaoForm
from decorators import perfil_requerido
from services.auditoria import registrar, Acoes
from services import codigos_recuperacao, envio_email, privacidade

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ACOES_DE_ALERTA = ["LOGIN_FALHA", "LOGIN_BLOQUEADO", "DOIS_FATORES_FALHA", "SENHA_REDEFINICAO_FALHA", "ACESSO_NEGADO"]
ALFABETO_SENHA = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"


def _conferir_csrf():
    if not AcaoAdminForm().validate_on_submit():
        abort(400)


def _alvo(usuario_id):
    usuario = db.get_or_404(Usuario, usuario_id)
    if usuario.anonimizado:
        flash("Esta conta foi anonimizada (LGPD) e não pode mais ser alterada.", "warning")
        return None
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
        "data_hoje": agora.strftime("%Y-%m-%d"),
        "data_ontem": (agora - timedelta(days=1)).strftime("%Y-%m-%d"),
        "total_usuarios": sum(por_perfil.values()),
        "por_perfil": [
            ("Alunos", por_perfil.get("aluno", 0)),
            ("Professores", por_perfil.get("professor", 0)),
            ("Bibliotecários", por_perfil.get("admin", 0)),
            ("Administradores", por_perfil.get("superadmin", 0)),
        ],
        "inativos": Usuario.query.filter_by(ativo=False).count(),
        "solicitacoes_pendentes": Usuario.query.filter_by(
            status_cadastro=StatusCadastro.AGUARDANDO_APROVACAO).count(),
        "sem_2fa": Usuario.query.filter_by(
            dois_fatores_ativo=False, status_cadastro=StatusCadastro.APROVADO).count(),
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
    elif filtros["situacao"] == "pendentes":
        consulta = consulta.filter(Usuario.status_cadastro != StatusCadastro.APROVADO)
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


@admin_bp.route("/solicitacoes")
@login_required
@perfil_requerido("superadmin")
def solicitacoes():
    aguardando_aprovacao = (
        Usuario.query.filter_by(status_cadastro=StatusCadastro.AGUARDANDO_APROVACAO)
        .order_by(Usuario.email_confirmado_em).all()
    )
    aguardando_confirmacao = (
        Usuario.query.filter_by(status_cadastro=StatusCadastro.AGUARDANDO_CONFIRMACAO)
        .order_by(Usuario.criado_em.desc()).all()
    )
    recusados = (
        Usuario.query.filter_by(status_cadastro=StatusCadastro.RECUSADO)
        .order_by(Usuario.criado_em.desc()).limit(20).all()
    )
    exclusoes = privacidade.pendentes()
    return render_template(
        "admin/solicitacoes.html",
        aguardando_aprovacao=aguardando_aprovacao,
        aguardando_confirmacao=aguardando_confirmacao,
        recusados=recusados,
        exclusoes=exclusoes,
        bloqueios_exclusao={u.id: privacidade._motivo_bloqueio(u) for u in exclusoes},
        form_acao=AcaoAdminForm(),
        form_recusa=RecusarExclusaoForm(),
    )


@admin_bp.route("/exclusoes/<int:usuario_id>/confirmar", methods=["POST"])
@login_required
@perfil_requerido("superadmin")
def confirmar_exclusao(usuario_id):
    _conferir_csrf()
    usuario = db.get_or_404(Usuario, usuario_id)
    try:
        privacidade.confirmar_exclusao(usuario, current_user)
    except privacidade.RegraPrivacidadeError as erro:
        flash(str(erro), "warning")
    else:
        flash("Dados anonimizados. O usuário foi avisado por e-mail antes da exclusão.", "success")
    return redirect(url_for("admin.solicitacoes"))


@admin_bp.route("/exclusoes/<int:usuario_id>/recusar", methods=["POST"])
@login_required
@perfil_requerido("superadmin")
def recusar_exclusao(usuario_id):
    form = RecusarExclusaoForm()
    if not form.validate_on_submit():
        flash("Informe o motivo da recusa (até 300 caracteres).", "danger")
        return redirect(url_for("admin.solicitacoes"))
    usuario = db.get_or_404(Usuario, usuario_id)
    try:
        privacidade.recusar_exclusao(usuario, form.motivo.data, current_user)
    except privacidade.RegraPrivacidadeError as erro:
        flash(str(erro), "warning")
    else:
        flash("Pedido de exclusão recusado. O usuário foi avisado por e-mail.", "info")
    return redirect(url_for("admin.solicitacoes"))


@admin_bp.route("/solicitacoes/<int:usuario_id>/aprovar", methods=["POST"])
@login_required
@perfil_requerido("superadmin")
def aprovar_cadastro(usuario_id):
    _conferir_csrf()
    usuario = db.get_or_404(Usuario, usuario_id)

    if usuario.status_cadastro not in (StatusCadastro.AGUARDANDO_APROVACAO, StatusCadastro.RECUSADO):
        flash(f"{usuario.nome} não está aguardando aprovação ({usuario.status_cadastro_nome}).", "warning")
        return redirect(url_for("admin.solicitacoes"))
    if usuario.email_confirmado_em is None:
        flash(f"{usuario.nome} ainda não confirmou o e-mail e não pode ser aprovado.", "warning")
        return redirect(url_for("admin.solicitacoes"))

    usuario.status_cadastro = StatusCadastro.APROVADO
    usuario.aprovado_em = datetime.now()
    usuario.aprovado_por_id = current_user.id
    db.session.commit()
    registrar(Acoes.CADASTRO_APROVADO, f"Cadastro de {usuario.email} ({usuario.perfil_nome}) aprovado")

    if envio_email.enviar_aprovacao(usuario):
        flash(f"Cadastro de {usuario.nome} aprovado. Enviamos um e-mail avisando que já pode entrar.", "success")
    else:
        registrar(Acoes.EMAIL_FALHA_ENVIO, f"Falha ao enviar o aviso de aprovação para {usuario.email}", sucesso=False)
        flash(f"Cadastro de {usuario.nome} aprovado, mas o e-mail de aviso não pôde ser enviado.", "warning")
    return redirect(url_for("admin.solicitacoes"))


@admin_bp.route("/solicitacoes/<int:usuario_id>/recusar", methods=["POST"])
@login_required
@perfil_requerido("superadmin")
def recusar_cadastro(usuario_id):
    _conferir_csrf()
    usuario = db.get_or_404(Usuario, usuario_id)

    if usuario.status_cadastro not in (StatusCadastro.AGUARDANDO_APROVACAO, StatusCadastro.AGUARDANDO_CONFIRMACAO):
        flash(f"{usuario.nome} não está com o cadastro pendente ({usuario.status_cadastro_nome}).", "warning")
        return redirect(url_for("admin.solicitacoes"))

    email_confirmado = usuario.status_cadastro == StatusCadastro.AGUARDANDO_APROVACAO
    usuario.status_cadastro = StatusCadastro.RECUSADO
    db.session.commit()
    registrar(Acoes.CADASTRO_REPROVADO, f"Cadastro de {usuario.email} ({usuario.perfil_nome}) recusado")

    if email_confirmado:
        envio_email.enviar_reprovacao(usuario)
    flash(f"Cadastro de {usuario.nome} recusado.", "info")
    return redirect(url_for("admin.solicitacoes"))


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
