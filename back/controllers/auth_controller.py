import time
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, current_app, session, abort
from flask_login import login_user, logout_user, login_required, current_user

from models import db, Usuario, LogAuditoria
from forms import LoginForm, CadastroForm, CodigoDoisFatoresForm, AcaoAdminForm, EsqueciSenhaForm
from decorators import perfil_requerido
from services.auditoria import registrar, Acoes
from services import dois_fatores, dashboard_bibliotecario
from services.notificacoes import verificar_e_notificar

auth_bp = Blueprint("auth", __name__)


def detectar_perfil_pelo_email(email: str):
    """Detecta o perfil do usuário a partir do domínio do e-mail.

    Regra de negócio do projeto: o perfil não é escolhido manualmente no
    cadastro, e sim inferido pelo domínio (ex.: @aluno.com -> aluno).
    Os domínios aceitos ficam centralizados em Config.DOMINIOS_PERFIL.

    Retorna o perfil (str) ou None se o domínio não for reconhecido.
    """
    dominio = email.split("@")[-1].lower().strip()
    return current_app.config["DOMINIOS_PERFIL"].get(dominio)


# ---------------------------------------------------------------------------
# Autenticação de dois fatores (2FA) — ver services/dois_fatores.py
# ---------------------------------------------------------------------------
SESSAO_2FA_PENDENTE = "2fa_pendente"          # login aguardando o código
TEMPO_MAX_2FA_SEGUNDOS = 10 * 60              # prazo para concluir a 2ª etapa após a senha
MAX_TENTATIVAS_2FA = 5                        # tentativas antes de exigir a senha de novo


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
                # Senha correta é só a 1ª etapa. O 2FA é obrigatório para
                # todos: o usuário ainda NÃO é logado aqui. Guardamos apenas
                # um id "pendente" na sessão e seguimos para a 2ª etapa
                # (código do Google Authenticator).
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
            # A mensagem para o usuário é genérica (não revela se o e-mail
            # existe), mas a auditoria guarda o motivo real.
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
    """Segunda etapa do login (obrigatória para todos os usuários).

    - Se o usuário ainda não configurou o app: mostra o QR Code para
      escanear no Google Authenticator e pede o primeiro código.
    - Se já configurou: pede apenas o código de 6 dígitos do app.

    Só depois de um código válido o usuário é realmente logado.
    """
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

    # Primeiro acesso: o segredo fica só na sessão até o usuário provar que
    # escaneou o QR Code (digitando um código válido). Só então é salvo.
    primeira_configuracao = not usuario.dois_fatores_ativo
    if primeira_configuracao and not pendente.get("novo_segredo"):
        pendente["novo_segredo"] = dois_fatores.gerar_segredo()
        session[SESSAO_2FA_PENDENTE] = pendente

    segredo = pendente["novo_segredo"] if primeira_configuracao else usuario.totp_secret
    form = CodigoDoisFatoresForm()

    if form.validate_on_submit():
        ultimo_passo = None if primeira_configuracao else usuario.totp_ultimo_passo
        passo = dois_fatores.verificar_codigo(segredo, form.codigo.data, ultimo_passo)

        if passo is not None:
            session.pop(SESSAO_2FA_PENDENTE, None)
            if primeira_configuracao:
                usuario.totp_secret = segredo
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

        flash("Código inválido. Confira o código no app e o horário do celular e tente novamente.", "danger")

    if primeira_configuracao:
        uri = dois_fatores.uri_provisionamento(segredo, usuario.email)
        return render_template(
            "ativar_2fa.html",
            form=form,
            qr_svg=dois_fatores.qr_code_svg(uri),
            segredo_formatado=dois_fatores.formatar_segredo(segredo),
        )
    return render_template("login_2fa.html", form=form)


# ---------------------------------------------------------------------------
# Esqueci minha senha (redefinição pelo Google Authenticator)
# ---------------------------------------------------------------------------
MAX_FALHAS_REDEFINICAO = 5          # tentativas erradas por e-mail...
JANELA_FALHAS_MINUTOS = 15          # ...dentro desta janela de tempo


def _falhas_recentes_redefinicao(email: str) -> int:
    """Conta as tentativas erradas recentes para o e-mail, direto na auditoria.

    O limite fica no servidor (e não na sessão), então abrir outra aba ou
    limpar os cookies não zera a contagem.
    """
    limite = datetime.now() - timedelta(minutes=JANELA_FALHAS_MINUTOS)
    return LogAuditoria.query.filter(
        LogAuditoria.acao == Acoes.SENHA_REDEFINICAO_FALHA,
        LogAuditoria.usuario_email == email,
        LogAuditoria.criado_em >= limite,
    ).count()


@auth_bp.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    """O usuário prova que é o dono da conta com o código do Google Authenticator
    e define uma nova senha. Não precisa de servidor de e-mail.

    Quem nunca configurou o app ou perdeu o celular procura o bibliotecário.
    """
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
            # Mensagem genérica: não revela se o e-mail existe nem qual campo errou.
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
                "Se você perdeu o celular ou nunca configurou o app, procure a biblioteca.",
                "danger",
            )
            return render_template("esqueci_senha.html", form=form)

        usuario.set_senha(form.nova_senha.data)
        usuario.totp_ultimo_passo = passo  # o mesmo código não pode ser usado de novo
        db.session.commit()
        session.pop(SESSAO_2FA_PENDENTE, None)

        registrar(Acoes.SENHA_REDEFINIDA, "Senha redefinida pelo Google Authenticator", usuario=usuario)
        flash("Senha redefinida! Entre com a nova senha.", "success")
        return redirect(url_for("auth.login"))

    return render_template("esqueci_senha.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    # Registra antes do logout_user(), enquanto ainda sabemos quem é o usuário
    registrar(Acoes.LOGOUT, "Logout realizado")
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    # RF15: além do agendador (de hora em hora), a verificação roda ao abrir o
    # painel, então um atraso visto na tela já chega como aviso ao aluno.
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
    """Apaga o Google Authenticator de um usuário (ex.: perdeu o celular).

    No próximo login, depois da senha, ele verá o QR Code de novo para
    configurar o app em um novo aparelho.
    """
    form = AcaoAdminForm()
    if not form.validate_on_submit():  # confere o token CSRF
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
