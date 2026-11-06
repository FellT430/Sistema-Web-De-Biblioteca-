from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from models import db


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
    criado_em = db.Column(db.DateTime, default=datetime.now)
    ativo = db.Column(db.Boolean, default=True)

    # Registro de consentimento (LGPD): guarda se e quando o usuário aceitou
    # a Política de Privacidade e os Termos de Aceite no cadastro.
    aceite_termos = db.Column(db.Boolean, nullable=False, default=False)
    aceite_termos_em = db.Column(db.DateTime, nullable=True)

    # Autenticação de dois fatores (2FA) via TOTP (Google Authenticator,
    # Microsoft Authenticator, Authy etc.). O segredo é gerado pelo servidor,
    # mostrado ao usuário uma única vez via QR Code e fica guardado aqui.
    # `totp_ultimo_passo` guarda a "janela de 30s" do último código aceito,
    # impedindo que o mesmo código seja reutilizado (ataque de replay).
    dois_fatores_ativo = db.Column(db.Boolean, nullable=False, default=False)
    totp_secret = db.Column(db.String(64), nullable=True)
    totp_ultimo_passo = db.Column(db.BigInteger, nullable=True)

    def set_senha(self, senha_texto_puro: str) -> None:
        """Gera e armazena o hash da senha (nunca a senha em texto puro)."""
        self.senha_hash = generate_password_hash(senha_texto_puro)

    def checar_senha(self, senha_texto_puro: str) -> bool:
        return check_password_hash(self.senha_hash, senha_texto_puro)

    def __repr__(self):
        return f"<Usuario {self.email} ({self.perfil})>"
