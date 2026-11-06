from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from models import db


class Usuario(UserMixin, db.Model):

    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(20), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.now)
    ativo = db.Column(db.Boolean, default=True)

    aceite_termos = db.Column(db.Boolean, nullable=False, default=False)
    aceite_termos_em = db.Column(db.DateTime, nullable=True)

    dois_fatores_ativo = db.Column(db.Boolean, nullable=False, default=False)
    totp_secret = db.Column(db.String(64), nullable=True)
    totp_ultimo_passo = db.Column(db.BigInteger, nullable=True)

    NOMES_PERFIL = {
        "superadmin": "Admin",
        "admin": "Bibliotecário",
        "professor": "Professor",
        "aluno": "Aluno",
    }

    @property
    def perfil_nome(self) -> str:
        return self.NOMES_PERFIL.get(self.perfil, self.perfil)

    @property
    def is_superadmin(self) -> bool:
        return self.perfil == "superadmin"

    def set_senha(self, senha_texto_puro: str) -> None:
        self.senha_hash = generate_password_hash(senha_texto_puro)

    def checar_senha(self, senha_texto_puro: str) -> bool:
        return check_password_hash(self.senha_hash, senha_texto_puro)

    def __repr__(self):
        return f"<Usuario {self.email} ({self.perfil})>"
