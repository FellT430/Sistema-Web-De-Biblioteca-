from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from models import db


class StatusCadastro:
    AGUARDANDO_CONFIRMACAO = "AGUARDANDO_CONFIRMACAO"
    AGUARDANDO_APROVACAO = "AGUARDANDO_APROVACAO"
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"

    NOMES = {
        AGUARDANDO_CONFIRMACAO: "Aguardando confirmação do e-mail",
        AGUARDANDO_APROVACAO: "Aguardando aprovação",
        APROVADO: "Aprovado",
        RECUSADO: "Recusado",
    }


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

    status_cadastro = db.Column(
        db.String(30), nullable=False,
        default=StatusCadastro.APROVADO, server_default=StatusCadastro.APROVADO,
    )
    email_confirmado_em = db.Column(db.DateTime, nullable=True)
    aprovado_em = db.Column(db.DateTime, nullable=True)
    aprovado_por_id = db.Column(db.Integer, nullable=True)

    exclusao_solicitada_em = db.Column(db.DateTime, nullable=True)
    anonimizado_em = db.Column(db.DateTime, nullable=True)

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
    def aprovado(self) -> bool:
        return self.status_cadastro == StatusCadastro.APROVADO

    @property
    def status_cadastro_nome(self) -> str:
        return StatusCadastro.NOMES.get(self.status_cadastro, self.status_cadastro)

    @property
    def anonimizado(self) -> bool:
        return self.anonimizado_em is not None

    @property
    def exclusao_pendente(self) -> bool:
        return self.exclusao_solicitada_em is not None and self.anonimizado_em is None

    @property
    def is_superadmin(self) -> bool:
        return self.perfil == "superadmin"

    def set_senha(self, senha_texto_puro: str) -> None:
        self.senha_hash = generate_password_hash(senha_texto_puro)

    def checar_senha(self, senha_texto_puro: str) -> bool:
        return check_password_hash(self.senha_hash, senha_texto_puro)

    def __repr__(self):
        return f"<Usuario {self.email} ({self.perfil})>"
