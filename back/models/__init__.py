from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.usuario import Usuario
from models.livro import Livro
from models.log_auditoria import LogAuditoria
from models.disciplina import Disciplina, disciplina_livros
from models.recomendacao import Recomendacao
from models.emprestimo import Emprestimo, StatusEmprestimo
from models.notificacao import Notificacao, TipoNotificacao
from models.codigo_recuperacao import CodigoRecuperacao
from models.cadastro_autorizado import CadastroAutorizado

__all__ = ["db", "Usuario", "Livro", "LogAuditoria", "Disciplina", "disciplina_livros", "Recomendacao", "Emprestimo", "StatusEmprestimo", "Notificacao", "TipoNotificacao", "CodigoRecuperacao", "CadastroAutorizado"]
