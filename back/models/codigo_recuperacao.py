from datetime import datetime

from models import db


class CodigoRecuperacao(db.Model):

    __tablename__ = "codigos_recuperacao"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    codigo_hash = db.Column(db.String(255), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    usado_em = db.Column(db.DateTime, nullable=True)

    @property
    def disponivel(self) -> bool:
        return self.usado_em is None
