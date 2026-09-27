from datetime import datetime

from models import db


class LogAuditoria(db.Model):
    __tablename__ = "logs_auditoria"

    id = db.Column(db.Integer, primary_key=True)
    criado_em = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)

    usuario_id = db.Column(db.Integer, nullable=True, index=True)
    usuario_email = db.Column(db.String(150), nullable=True, index=True)
    usuario_perfil = db.Column(db.String(20), nullable=True)

    acao = db.Column(db.String(50), nullable=False, index=True)
    descricao = db.Column(db.String(500), nullable=True)
    sucesso = db.Column(db.Boolean, nullable=False, default=True)

    ip = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    metodo = db.Column(db.String(10), nullable=True)
    rota = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<LogAuditoria {self.acao} por {self.usuario_email} em {self.criado_em}>"
