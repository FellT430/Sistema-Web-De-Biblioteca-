from flask import Flask, redirect, url_for

from app.config import Config
from app.extensions import db, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    from app import models  # noqa: F401  registra os models antes das migrations

    from app.routes.emprestimos import emprestimos_bp
    from app.routes.exemplares import exemplares_bp
    from app.routes.livros import livros_bp
    from app.routes.usuarios import usuarios_bp

    app.register_blueprint(livros_bp)
    app.register_blueprint(exemplares_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(emprestimos_bp)

    @app.route("/")
    def index():
        return redirect(url_for("emprestimos.listar"))

    from app.scheduler import init_scheduler

    init_scheduler(app)

    return app
