import os

from flask import Flask, render_template
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
from controllers.admin_controller import admin_bp
from services.agendador import iniciar_agendador
from services.superadmin import garantir_superadmins

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
    app.register_blueprint(admin_bp)

    @app.template_filter("nome_perfil")
    def nome_perfil(perfil):
        return Usuario.NOMES_PERFIL.get(perfil, perfil or "")

    @app.context_processor
    def contador_notificacoes():
        from flask_login import current_user
        from services.notificacoes import nao_lidas

        if current_user.is_authenticated and current_user.perfil == "aluno":
            return {"notificacoes_nao_lidas": nao_lidas(current_user)}
        return {"notificacoes_nao_lidas": 0}

    @app.errorhandler(403)
    def acesso_negado(_erro):
        return render_template("erro.html", codigo=403, titulo="Acesso negado",
                               mensagem="Você não tem permissão para acessar esta página."), 403

    @app.errorhandler(404)
    def nao_encontrada(_erro):
        return render_template("erro.html", codigo=404, titulo="Página não encontrada",
                               mensagem="O endereço acessado não existe ou foi removido."), 404

    @app.errorhandler(400)
    def requisicao_invalida(_erro):
        return render_template("erro.html", codigo=400, titulo="Requisição inválida",
                               mensagem="A página expirou ou o formulário é inválido. Volte e tente novamente."), 400

    @app.errorhandler(500)
    def erro_interno(_erro):
        db.session.rollback()
        return render_template("erro.html", codigo=500, titulo="Erro interno",
                               mensagem="Ocorreu um erro inesperado. Tente novamente em instantes."), 500

    with app.app_context():
        db.create_all()
        _adicionar_colunas_2fa()
        garantir_superadmins(app)

    iniciar_agendador(app)

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
    usuario = db.session.get(Usuario, int(user_id))
    if usuario is None or not usuario.ativo:
        return None
    return usuario


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
