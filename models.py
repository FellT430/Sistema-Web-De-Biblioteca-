from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Usuario(UserMixin, db.Model):
    """Representa qualquer usuário do sistema (admin, professor ou aluno).

    O campo `perfil` define o papel do usuário e é usado para controle
    de acesso (RBAC simples) nas rotas protegidas.
    """

    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(20), nullable=False)  # admin | professor | aluno
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)

    def set_senha(self, senha_texto_puro: str) -> None:
        """Gera e armazena o hash da senha (nunca a senha em texto puro)."""
        self.senha_hash = generate_password_hash(senha_texto_puro)

    def checar_senha(self, senha_texto_puro: str) -> bool:
        return check_password_hash(self.senha_hash, senha_texto_puro)

    def __repr__(self):
        return f"<Usuario {self.email} ({self.perfil})>"


class Livro(db.Model):
    """Cadastro simples de livros do acervo (sem integração com API externa).

    Campos mínimos para um CRUD funcional; dados como sinopse, capa e
    categorias podem ser adicionados depois, quando a integração com a
    Google Books API entrar no projeto.
    """

    __tablename__ = "livros"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(150), nullable=False)
    isbn = db.Column(db.String(20), nullable=True)
    editora = db.Column(db.String(120), nullable=True)
    ano_publicacao = db.Column(db.Integer, nullable=True)
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Livro {self.titulo}>"
