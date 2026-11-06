import os

from flask import Flask
from flask_login import LoginManager
from sqlalchemy import inspect, text

from config import Config
from models import db, Usuario
from controllers.auth_controller import auth_bp
from controllers.livros_controller import livros_bp
from controllers.auditoria_controller import auditoria_bp
from controllers.disciplinas_controller import disciplinas_bp
from controllers.recomendacoes_controller import recomendacoes_bp
from controllers.acervo_controller import acervo_bp
from controllers.emprestimos_controller import emprestimos_bp
from controllers.notificacoes_controller import notificacoes_bp
from services.agendador import iniciar_agendador

# Caminhos para as pastas de front-end (templates e static ficam separados do back-end)
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
    app.register_blueprint(livros_bp)
    app.register_blueprint(auditoria_bp)
    app.register_blueprint(disciplinas_bp)
    app.register_blueprint(recomendacoes_bp)
    app.register_blueprint(acervo_bp)
    app.register_blueprint(emprestimos_bp)
    app.register_blueprint(notificacoes_bp)

    @app.context_processor
    def contador_notificacoes():
        """Deixa o número de notificações não lidas disponível em todos os templates (sininho)."""
        from flask_login import current_user
        from services.notificacoes import nao_lidas

        if current_user.is_authenticated and current_user.perfil == "aluno":
            return {"notificacoes_nao_lidas": nao_lidas(current_user)}
        return {"notificacoes_nao_lidas": 0}

    with app.app_context():
        db.create_all()
        _adicionar_colunas_2fa()

    # RF15: verificação automática de atrasos e notificações (APScheduler)
    iniciar_agendador(app)

    return app


def _adicionar_colunas_2fa():
    """Adiciona as colunas do 2FA em bancos criados antes dessa funcionalidade.

    `db.create_all()` só cria tabelas novas; ele não altera tabelas que já
    existem. Sem isso, um banco antigo daria erro "Unknown column". O mesmo
    SQL está em db/migracao_2fa.sql para quem preferir rodar manualmente.
    """
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
    return db.session.get(Usuario, int(user_id))


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
