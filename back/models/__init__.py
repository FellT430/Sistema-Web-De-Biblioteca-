from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.usuario import Usuario, StatusCadastro
from models.livro import Livro
from models.log_auditoria import LogAuditoria
from models.disciplina import Disciplina, disciplina_livros
from models.recomendacao import Recomendacao
from models.emprestimo import Emprestimo, StatusEmprestimo
from models.notificacao import Notificacao, TipoNotificacao
from models.reserva import Reserva, StatusReserva
from models.codigo_recuperacao import CodigoRecuperacao

__all__ = ["db", "Usuario", "StatusCadastro", "Livro", "LogAuditoria", "Disciplina", "disciplina_livros", "Recomendacao", "Emprestimo", "StatusEmprestimo", "Notificacao", "TipoNotificacao", "Reserva", "StatusReserva", "CodigoRecuperacao"]
