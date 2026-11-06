from datetime import datetime

from models import db


class Livro(db.Model):
    """Cadastro de livros do acervo.

    Os campos abaixo podem ser preenchidos manualmente ou automaticamente
    a partir de uma busca na Google Books API (ver services/google_books.py),
    que o bibliotecário confirma antes de salvar.
    """

    __tablename__ = "livros"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(150), nullable=False)
    isbn = db.Column(db.String(20), nullable=True)
    editora = db.Column(db.String(120), nullable=True)
    ano_publicacao = db.Column(db.Integer, nullable=True)
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    sinopse = db.Column(db.Text, nullable=True)
    categoria = db.Column(db.String(150), nullable=True)
    capa_url = db.Column(db.String(500), nullable=True)
    google_books_id = db.Column(db.String(50), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.now)

    def exemplares_disponiveis(self) -> int:
        """Quantidade de exemplares disponíveis para empréstimo (RN39).

        RN39: disponível = total de exemplares - empréstimos ativos ou atrasados.
        Também são descontadas as solicitações ainda não retiradas (status
        SOLICITADO), para que dois alunos não peçam o último exemplar ao
        mesmo tempo. Todas as telas que mostram disponibilidade usam este método.
        """
        from models.emprestimo import StatusEmprestimo  # import local evita import circular

        ocupados = sum(
            1 for emprestimo in self.emprestimos
            if emprestimo.status in StatusEmprestimo.OCUPAM_EXEMPLAR
        )
        return max(self.quantidade - ocupados, 0)

    def __repr__(self):
        return f"<Livro {self.titulo}>"
