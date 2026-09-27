import time
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, current_app, session, abort, request
from flask_login import login_user, logout_user, login_required, current_user

from models import db, Usuario
from forms import LoginForm, CadastroForm, CodigoDoisFatoresForm, AcaoAdminForm
from decorators import perfil_requerido
from services.auditoria import registrar, Acoes
from services import dois_fatores

auth_bp = Blueprint("auth", __name__)


def detectar_perfil_pelo_email(email: str):
    dominio = email.split("@")[-1].lower().strip()
    return current_app.config["DOMINIOS_PERFIL"].get(dominio)


SESSAO_2FA_PENDENTE = "2fa_pendente"
TEMPO_MAX_2FA_SEGUNDOS = 10 * 60
MAX_TENTATIVAS_2FA = 5


@auth_bp.route("/", methods=["GET"])
def index():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    form = CadastroForm()

    if form.validate_on_submit():
        email_normalizado = form.email.data.lower().strip()

        email_existente = Usuario.query.filter_by(email=email_normalizado).first()
        if email_existente:
            registrar(
                Acoes.CADASTRO_RECUSADO,
                "Tentativa de cadastro com e-mail já existente",
                email=email_normalizado,
                sucesso=False,
            )
            flash("Este e-mail já está cadastrado.", "danger")
            return render_template("cadastro.html", form=form)

        perfil_detectado = detectar_perfil_pelo_email(email_normalizado)
        if perfil_detectado is None:
            registrar(
                Acoes.CADASTRO_RECUSADO,
                "Tentativa de cadastro com domínio de e-mail não reconhecido",
                email=email_normalizado,
                sucesso=False,
            )
            flash(
                "E-mail não reconhecido. Use um e-mail institucional válido "
                "(ex.: @aluno.com, @professor.com ou @bibliotecaadm.com).",
                "danger",
            )
            return render_template("cadastro.html", form=form)

        novo_usuario = Usuario(
            nome=form.nome.data.strip(),
            email=email_normalizado,
            perfil=perfil_detectado,
            aceite_termos=bool(form.aceite_termos.data),
            aceite_termos_em=datetime.now(),
        )
        novo_usuario.set_senha(form.senha.data)

        db.session.add(novo_usuario)
        db.session.commit()

        registrar(
            Acoes.CADASTRO_USUARIO,
            f"Novo usuário cadastrado com perfil '{perfil_detectado}' (aceite de termos registrado)",
            usuario=novo_usuario,
        )

        flash(
            f"Cadastro realizado com sucesso como {perfil_detectado}! Faça login para continuar.",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template("cadastro.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    form = LoginForm()

    if form.validate_on_submit():
        email_informado = form.email.data.lower().strip()
        usuario = Usuario.query.filter_by(email=email_informado).first()

        if usuario and usuario.checar_senha(form.senha.data):
            if usuario.ativo:
                session.pop(SESSAO_2FA_PENDENTE, None)
                session[SESSAO_2FA_PENDENTE] = {
                    "usuario_id": usuario.id,
                    "inicio": int(time.time()),
                    "tentativas": 0,
                }
                return redirect(url_for("auth.login_2fa"))

            registrar(
                Acoes.LOGIN_BLOQUEADO,
                "Senha correta, mas a conta está desativada",
                usuario=usuario,
                sucesso=False,
            )
        else:
            motivo = "senha incorreta" if usuario else "e-mail não cadastrado"
            registrar(
                Acoes.LOGIN_FALHA,
                f"Falha de login: {motivo}",
                usuario=usuario,
                email=email_informado,
                sucesso=False,
            )

        flash("E-mail ou senha inválidos.", "danger")

    return render_template("login.html", form=form)


@auth_bp.route("/login/verificacao", methods=["GET", "POST"])
def login_2fa():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    pendente = session.get(SESSAO_2FA_PENDENTE)
    if not pendente:
        return redirect(url_for("auth.login"))

    usuario = db.session.get(Usuario, pendente["usuario_id"])
    expirado = int(time.time()) - pendente["inicio"] > TEMPO_MAX_2FA_SEGUNDOS
    if usuario is None or not usuario.ativo or expirado:
        session.pop(SESSAO_2FA_PENDENTE, None)
        flash("Sua verificação expirou. Faça login novamente.", "warning")
        return redirect(url_for("auth.login"))

    primeira_configuracao = not usuario.dois_fatores_ativo
    if primeira_configuracao and not usuario.totp_secret:
        usuario.totp_secret = dois_fatores.gerar_segredo()
        usuario.totp_ultimo_passo = None
        db.session.commit()

    segredo = usuario.totp_secret
    form = CodigoDoisFatoresForm()

    if form.validate_on_submit():
        ultimo_passo = None if primeira_configuracao else usuario.totp_ultimo_passo
        passo = dois_fatores.verificar_codigo(segredo, form.codigo.data, ultimo_passo)

        if passo is not None:
            session.pop(SESSAO_2FA_PENDENTE, None)
            if primeira_configuracao:
                usuario.dois_fatores_ativo = True
            usuario.totp_ultimo_passo = passo
            db.session.commit()

            login_user(usuario)
            if primeira_configuracao:
                registrar(Acoes.DOIS_FATORES_ATIVADO, "Google Authenticator configurado no primeiro acesso", usuario=usuario)
            registrar(Acoes.LOGIN_SUCESSO, "Login realizado com sucesso (senha + 2FA)", usuario=usuario)
            flash(f"Bem-vindo(a), {usuario.nome}!", "success")
            return redirect(url_for("auth.dashboard"))

        pendente["tentativas"] += 1
        session[SESSAO_2FA_PENDENTE] = pendente
        registrar(
            Acoes.DOIS_FATORES_FALHA,
            f"Código 2FA inválido no login (tentativa {pendente['tentativas']}/{MAX_TENTATIVAS_2FA})",
            usuario=usuario,
            sucesso=False,
        )
        if pendente["tentativas"] >= MAX_TENTATIVAS_2FA:
            session.pop(SESSAO_2FA_PENDENTE, None)
            flash("Muitas tentativas inválidas. Faça login novamente.", "danger")
            return redirect(url_for("auth.login"))

        dica = dois_fatores.diagnosticar_codigo(segredo, form.codigo.data, usuario.totp_ultimo_passo)
        if dica:
            flash(dica, "warning")
        else:
            flash(
                "Código inválido. Confira se está usando a conta \"Livro +\" com o seu e-mail no app"
                + (" e se escaneou o QR Code desta tela" if primeira_configuracao else "")
                + ". Se houver mais de uma conta \"Livro +\" no app, apague as antigas.",
                "danger",
            )

    elif request.method == "POST" and "csrf_token" in form.errors:
        flash("A página expirou. Digite o código novamente.", "warning")

    if primeira_configuracao:
        uri = dois_fatores.uri_provisionamento(segredo, usuario.email)
        return render_template(
            "ativar_2fa.html",
            form=form,
            qr_svg=dois_fatores.qr_code_svg(uri),
            segredo_formatado=dois_fatores.formatar_segredo(segredo),
        )
    return render_template("login_2fa.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    registrar(Acoes.LOGOUT, "Logout realizado")
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", usuario=current_user)


@auth_bp.route("/meus-dados")
@login_required
def meus_dados():
    registrar(Acoes.CONSULTA_DADOS_PESSOAIS, "Usuário consultou os próprios dados pessoais (LGPD)")
    return render_template("meus_dados.html", usuario=current_user)


@auth_bp.route("/politica-privacidade")
def politica_privacidade():
    return render_template("politica_privacidade.html")


@auth_bp.route("/termos-uso")
def termos_uso():
    return render_template("termos_uso.html")


@auth_bp.route("/admin")
@perfil_requerido("admin")
def area_admin():
    usuarios = Usuario.query.order_by(Usuario.criado_em.desc()).all()
    registrar(Acoes.ACESSO_AREA_ADMIN, f"Acessou a lista de usuários ({len(usuarios)} registros)")
    return render_template(
        "dashboard.html", usuario=current_user, usuarios=usuarios, form_acao=AcaoAdminForm()
    )


@auth_bp.route("/admin/usuarios/<int:usuario_id>/resetar-2fa", methods=["POST"])
@perfil_requerido("admin")
def resetar_2fa(usuario_id):
    form = AcaoAdminForm()
    if not form.validate_on_submit():
        abort(400)

    usuario = db.get_or_404(Usuario, usuario_id)
    usuario.dois_fatores_ativo = False
    usuario.totp_secret = None
    usuario.totp_ultimo_passo = None
    db.session.commit()

    registrar(
        Acoes.DOIS_FATORES_RESETADO,
        f"Admin resetou a verificação em duas etapas de {usuario.email}",
    )
    flash(
        f"Verificação em duas etapas de {usuario.nome} foi resetada. "
        "No próximo login, será pedido para configurar o Google Authenticator novamente.",
        "success",
    )
    return redirect(url_for("auth.area_admin"))

