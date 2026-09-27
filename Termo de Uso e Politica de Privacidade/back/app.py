import os

from flask import Flask
from flask_login import LoginManager
from sqlalchemy import inspect, text

from config import Config
from models import db, Usuario
from controllers.auth_controller import auth_bp

FRONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "front")
TEMPLATE_DIR = os.path.join(FRONT_DIR, "templates")
STATIC_DIR = os.path.join(FRONT_DIR, "static")

login_manager = LoginManager()
login_manager.login_view = "auth.login"
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
    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()
        _adicionar_colunas_2fa()

    return app


def _adicionar_colunas_2fa():
    colunas_existentes = {c["name"] for c in inspect(db.engine).get_columns("usuarios")}
    novas_colunas = {
        "dois_fatores_ativo": "BOOLEAN NOT NULL DEFAULT 0",
        "totp_secret": "VARCHAR(64) NULL",
        "totp_ultimo_passo": "BIGINT NULL",
    }
    with db.engine.begin() as conexao:
        for nome, tipo in novas_colunas.items():
            if nome not in colunas_existentes:
                conexao.execute(text(f"ALTER TABLE usuarios ADD COLUMN {nome} {tipo}"))


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


app = create_app()



if __name__ == "__main__":
    app.run(debug=True)
