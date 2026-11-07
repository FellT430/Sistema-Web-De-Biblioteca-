import time
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, current_app, session, abort
from flask_login import login_user, logout_user, login_required, current_user

from models import db, Usuario, LogAuditoria, CadastroAutorizado
from forms import (
    LoginForm, CadastroForm, CodigoDoisFatoresForm, AcaoAdminForm, EsqueciSenhaForm,
    CodigoRecuperacaoForm, ConfirmarCodigosForm,
)
from decorators import perfil_requerido
from services.auditoria import registrar, Acoes
from services import dois_fatores, dashboard_bibliotecario, codigos_recuperacao
from services.notificacoes import verificar_e_notificar

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
                "(@aluno.com, @professor.com ou @bibliotecaadm.com).",
                "danger",
            )
            return render_template("cadastro.html", form=form)

        autorizacao = CadastroAutorizado.query.filter_by(email=email_normalizado, usado_em=None).first()
        if autorizacao is None:
            registrar(
                Acoes.CADASTRO_RECUSADO,
                "Tentativa de cadastro com e-mail não autorizado pelo Administrador",
                email=email_normalizado,
                sucesso=False,
            )
            flash(
                "Este e-mail ainda não foi liberado para cadastro. "
                "Procure a administração da biblioteca.",
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
        autorizacao.usado_em = datetime.now()
        db.session.commit()

        registrar(
            Acoes.CADASTRO_USUARIO,
            f"Novo usuário cadastrado com perfil {novo_usuario.perfil_nome} (cadastro autorizado; aceite de termos registrado)",
            usuario=novo_usuario,
        )

        flash(
            f"Cadastro realizado com sucesso como {novo_usuario.perfil_nome.lower()}! Faça login para continuar.",
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
    if primeira_configuracao and not pendente.get("novo_segredo"):
        pendente["novo_segredo"] = dois_fatores.gerar_segredo()
        session[SESSAO_2FA_PENDENTE] = pendente

    segredo = pendente["novo_segredo"] if primeira_configuracao else usuario.totp_secret
    form = CodigoDoisFatoresForm()

    precisa_aceite = primeira_configuracao and not usuario.aceite_termos
    if form.validate_on_submit() and precisa_aceite and not form.aceite_termos.data:
        form.aceite_termos.errors = ["Você precisa aceitar a Política de Privacidade e os Termos de Aceite."]
    elif form.validate_on_submit():
        ultimo_passo = None if primeira_configuracao else usuario.totp_ultimo_passo
        passo = dois_fatores.verificar_codigo(segredo, form.codigo.data, ultimo_passo)

        if passo is not None:
            session.pop(SESSAO_2FA_PENDENTE, None)
            if primeira_configuracao:
                usuario.totp_secret = segredo
                usuario.dois_fatores_ativo = True
                if precisa_aceite:
                    usuario.aceite_termos = True
                    usuario.aceite_termos_em = datetime.now()
            usuario.totp_ultimo_passo = passo
            db.session.commit()

            login_user(usuario)
            if primeira_configuracao:
                registrar(Acoes.DOIS_FATORES_ATIVADO, "Google Authenticator configurado no primeiro acesso", usuario=usuario)
            registrar(Acoes.LOGIN_SUCESSO, "Login realizado com sucesso (senha + 2FA)", usuario=usuario)
            if primeira_configuracao:
                return _mostrar_codigos_novos(usuario, voltar_para="auth.dashboard")
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

        flash("Código inválido. Confira o código no app e o horário do celular e tente novamente.", "danger")

    if primeira_configuracao:
        uri = dois_fatores.uri_provisionamento(segredo, usuario.email)
        return render_template(
            "ativar_2fa.html",
            form=form,
            qr_svg=dois_fatores.qr_code_svg(uri),
            segredo_formatado=dois_fatores.formatar_segredo(segredo),
            precisa_aceite=precisa_aceite,
        )
    return render_template("login_2fa.html", form=form)


SESSAO_CODIGOS_NOVOS = "codigos_recuperacao_novos"


def _mostrar_codigos_novos(usuario, voltar_para):
    codigos = codigos_recuperacao.gerar(usuario)
    session[SESSAO_CODIGOS_NOVOS] = {"codigos": codigos, "voltar_para": voltar_para}
    registrar(Acoes.CODIGOS_RECUPERACAO_GERADOS, f"{len(codigos)} códigos de recuperação gerados", usuario=usuario)
    return redirect(url_for("auth.codigos_recuperacao_novos"))


@auth_bp.route("/codigos-recuperacao", methods=["GET", "POST"])
@login_required
def codigos_recuperacao_novos():
    dados = session.get(SESSAO_CODIGOS_NOVOS)
    if not dados:
        return redirect(url_for("auth.meus_dados"))

    form = ConfirmarCodigosForm()
    if form.validate_on_submit():
        session.pop(SESSAO_CODIGOS_NOVOS, None)
        flash("Tudo pronto! Guarde bem seus códigos de recuperação.", "success")
        return redirect(url_for(dados["voltar_para"]))

    return render_template("codigos_recuperacao.html", codigos=dados["codigos"], form=form)


@auth_bp.route("/meus-dados/codigos-recuperacao/gerar", methods=["POST"])
@login_required
def gerar_codigos_recuperacao():
    if not AcaoAdminForm().validate_on_submit():
        abort(400)
    if not current_user.dois_fatores_ativo:
        flash("Configure o Google Authenticator antes de gerar códigos de recuperação.", "warning")
        return redirect(url_for("auth.meus_dados"))
    return _mostrar_codigos_novos(current_user, voltar_para="auth.meus_dados")


@auth_bp.route("/login/recuperacao", methods=["GET", "POST"])
def login_recuperacao():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    pendente = session.get(SESSAO_2FA_PENDENTE)
    if not pendente:
        return redirect(url_for("auth.login"))

    usuario = db.session.get(Usuario, pendente["usuario_id"])
    expirado = int(time.time()) - pendente["inicio"] > TEMPO_MAX_2FA_SEGUNDOS
    if usuario is None or not usuario.ativo or expirado or not usuario.dois_fatores_ativo:
        session.pop(SESSAO_2FA_PENDENTE, None)
        flash("Sua verificação expirou. Faça login novamente.", "warning")
        return redirect(url_for("auth.login"))

    form = CodigoRecuperacaoForm()
    if form.validate_on_submit():
        if codigos_recuperacao.usar(usuario, form.codigo.data):
            session.pop(SESSAO_2FA_PENDENTE, None)
            login_user(usuario)
            sobram = codigos_recuperacao.restantes(usuario)
            registrar(
                Acoes.CODIGO_RECUPERACAO_USADO,
                f"Login com código de recuperação (restam {sobram})",
                usuario=usuario,
            )
            registrar(Acoes.LOGIN_SUCESSO, "Login realizado com sucesso (senha + código de recuperação)", usuario=usuario)
            flash(
                f"Você entrou com um código de recuperação. Restam {sobram} código(s). "
                "Se perdeu o celular, peça ao administrador para redefinir a verificação em duas etapas "
                "e gere novos códigos em Meus dados.",
                "warning",
            )
            return redirect(url_for("auth.dashboard"))

        pendente["tentativas"] += 1
        session[SESSAO_2FA_PENDENTE] = pendente
        registrar(
            Acoes.DOIS_FATORES_FALHA,
            f"Código de recuperação inválido (tentativa {pendente['tentativas']}/{MAX_TENTATIVAS_2FA})",
            usuario=usuario,
            sucesso=False,
        )
        if pendente["tentativas"] >= MAX_TENTATIVAS_2FA:
            session.pop(SESSAO_2FA_PENDENTE, None)
            flash("Muitas tentativas inválidas. Faça login novamente.", "danger")
            return redirect(url_for("auth.login"))
        flash("Código de recuperação inválido ou já utilizado.", "danger")

    return render_template("login_recuperacao.html", form=form)


MAX_FALHAS_REDEFINICAO = 5
JANELA_FALHAS_MINUTOS = 15


def _falhas_recentes_redefinicao(email: str) -> int:
    limite = datetime.now() - timedelta(minutes=JANELA_FALHAS_MINUTOS)
    return LogAuditoria.query.filter(
        LogAuditoria.acao == Acoes.SENHA_REDEFINICAO_FALHA,
        LogAuditoria.usuario_email == email,
        LogAuditoria.criado_em >= limite,
    ).count()


@auth_bp.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    form = EsqueciSenhaForm()

    if form.validate_on_submit():
        email = form.email.data.lower().strip()

        if _falhas_recentes_redefinicao(email) >= MAX_FALHAS_REDEFINICAO:
            flash(
                f"Muitas tentativas inválidas. Aguarde {JANELA_FALHAS_MINUTOS} minutos e tente novamente.",
                "danger",
            )
            return render_template("esqueci_senha.html", form=form)

        usuario = Usuario.query.filter_by(email=email).first()
        passo = None
        if usuario and usuario.ativo and usuario.dois_fatores_ativo:
            passo = dois_fatores.verificar_codigo(
                usuario.totp_secret, form.codigo.data, usuario.totp_ultimo_passo
            )

        if passo is None:
            if usuario is None:
                motivo = "e-mail não cadastrado"
            elif not usuario.dois_fatores_ativo:
                motivo = "usuário ainda não configurou o Google Authenticator"
            elif not usuario.ativo:
                motivo = "conta desativada"
            else:
                motivo = "código do Google Authenticator inválido"
            registrar(
                Acoes.SENHA_REDEFINICAO_FALHA,
                f"Tentativa de redefinir senha recusada: {motivo}",
                usuario=usuario,
                email=email,
                sucesso=False,
            )
            flash(
                "Não foi possível redefinir a senha: confira o e-mail e o código do app. "
                "Se você perdeu o celular ou nunca configurou o app, procure a administração do sistema.",
                "danger",
            )
            return render_template("esqueci_senha.html", form=form)

        usuario.set_senha(form.nova_senha.data)
        usuario.totp_ultimo_passo = passo
        db.session.commit()
        session.pop(SESSAO_2FA_PENDENTE, None)

        registrar(Acoes.SENHA_REDEFINIDA, "Senha redefinida pelo Google Authenticator", usuario=usuario)
        flash("Senha redefinida! Entre com a nova senha.", "success")
        return redirect(url_for("auth.login"))

    return render_template("esqueci_senha.html", form=form)


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
    if current_user.perfil == "superadmin":
        return redirect(url_for("admin.painel"))
    verificar_e_notificar()
    if current_user.perfil == "admin":
        return render_template(
            "dashboard_bibliotecario.html",
            usuario=current_user,
            painel=dashboard_bibliotecario.montar_painel(),
        )
    return render_template("dashboard.html", usuario=current_user)


@auth_bp.route("/meus-dados")
@login_required
def meus_dados():
    registrar(Acoes.CONSULTA_DADOS_PESSOAIS, "Usuário consultou os próprios dados pessoais (LGPD)")
    return render_template(
        "meus_dados.html",
        usuario=current_user,
        codigos_restantes=codigos_recuperacao.restantes(current_user),
        codigos_total=codigos_recuperacao.total(current_user),
        form_acao=AcaoAdminForm(),
    )


@auth_bp.route("/politica-privacidade")
def politica_privacidade():
    return render_template("politica_privacidade.html", contato_email=current_app.config["CONTATO_EMAIL"])


@auth_bp.route("/termos-uso")
def termos_uso():
    return render_template("termos_uso.html")
