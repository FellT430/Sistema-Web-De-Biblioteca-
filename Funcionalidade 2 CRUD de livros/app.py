import os

from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required

from config import Config
from models import db, Usuario
from livros_routes import livros_bp


FRONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "front")
TEMPLATE_DIR = os.path.join(FRONT_DIR, "templates")
STATIC_DIR = os.path.join(FRONT_DIR, "static")

login_manager = LoginManager()
login_manager.login_view = "login_teste"
login_manager.login_message = "Faça login para acessar esta página."
login_manager.login_message_category = "warning"


def create_app():
    app = Flask(
        __name__,
        template_folder=TEMPLATE_DIR,
        static_folder=STATIC_DIR,
    )
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    app.register_blueprint(livros_bp)

    with app.app_context():
        db.create_all()

    return app


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


app = create_app()


# ---------------------------------------------------------------------
# Login simplificado, SÓ para permitir testar o CRUD de livros isolado.
# O login "de verdade" (com CadastroForm, CSRF, etc.) está na pasta
# "Funcionalidade Cadastro". Crie um usuário admin antes de testar
# (veja o README desta pasta).
# ---------------------------------------------------------------------
@app.route("/login-teste", methods=["GET", "POST"])
def login_teste():
    erro = None
    if request.method == "POST":
        usuario = Usuario.query.filter_by(email=request.form.get("email")).first()
        if usuario and usuario.checar_senha(request.form.get("senha", "")):
            login_user(usuario)
            return redirect(url_for("livros.listar"))
        erro = "E-mail ou senha inválidos."
    return render_template("login_teste.html", erro=erro)


@app.route("/logout-teste")
@login_required
def logout_teste():
    logout_user()
    return redirect(url_for("login_teste"))


if __name__ == "__main__":
    app.run(debug=True)
