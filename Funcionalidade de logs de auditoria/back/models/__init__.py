from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
from models.usuario import Usuario
from models.log_auditoria import LogAuditoria

__all__ = ["db", "Usuario", "LogAuditoria"]
