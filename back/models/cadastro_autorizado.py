from datetime import datetime

from models import db


class CadastroAutorizado(db.Model):

    __tablename__ = "cadastros_autorizados"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    perfil = db.Column(db.String(20), nullable=False)
    autorizado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    usado_em = db.Column(db.DateTime, nullable=True)

    autorizado_por = db.relationship("Usuario", foreign_keys=[autorizado_por_id])

    @property
    def pendente(self) -> bool:
        return self.usado_em is None
