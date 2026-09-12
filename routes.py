from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user

from models import db, Usuario
from forms import LoginForm, CadastroForm
from decorators import perfil_requerido

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
            flash("Este e-mail já está cadastrado.", "danger")
            return render_template("cadastro.html", form=form)

        perfil_detectado = detectar_perfil_pelo_email(email_normalizado)
        if perfil_detectado is None:
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
        )
        novo_usuario.set_senha(form.senha.data)

        db.session.add(novo_usuario)
        db.session.commit()

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
        usuario = Usuario.query.filter_by(email=form.email.data.lower().strip()).first()

        if usuario and usuario.ativo and usuario.checar_senha(form.senha.data):
            login_user(usuario)
            flash(f"Bem-vindo(a), {usuario.nome}!", "success")
            return redirect(url_for("auth.dashboard"))

        flash("E-mail ou senha inválidos.", "danger")

    return render_template("login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", usuario=current_user)


@auth_bp.route("/admin")
@perfil_requerido("admin")
def area_admin():
    usuarios = Usuario.query.order_by(Usuario.criado_em.desc()).all()
    return render_template("dashboard.html", usuario=current_user, usuarios=usuarios)
