"""
Camada Model (MVC).

`db` é a instância única do SQLAlchemy, compartilhada por todos os models
para evitar import circular entre app.py, controllers e os próprios models.

As classes de model ficam em arquivos separados (usuario.py, livro.py,
disciplina.py, recomendacao.py etc.),
mas são reexportadas aqui para que o resto do projeto possa importar
apenas de `models`, ex:  from models import Usuario, Livro
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.usuario import Usuario  # noqa: E402
from models.livro import Livro      # noqa: E402
from models.log_auditoria import LogAuditoria  # noqa: E402
from models.disciplina import Disciplina, disciplina_livros  # noqa: E402
from models.recomendacao import Recomendacao  # noqa: E402
from models.emprestimo import Emprestimo, StatusEmprestimo  # noqa: E402
from models.notificacao import Notificacao, TipoNotificacao  # noqa: E402

__all__ = ["db", "Usuario", "Livro", "LogAuditoria", "Disciplina", "disciplina_livros", "Recomendacao", "Emprestimo", "StatusEmprestimo", "Notificacao", "TipoNotificacao"]
