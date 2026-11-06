from datetime import datetime

from models import db


disciplina_livros = db.Table(
    "disciplina_livros",
    db.Column(
        "disciplina_id",
        db.Integer,
        db.ForeignKey("disciplinas.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "livro_id",
        db.Integer,
        db.ForeignKey("livros.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column("adicionado_em", db.DateTime, default=datetime.now),
)


class Disciplina(db.Model):

    __tablename__ = "disciplinas"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    codigo = db.Column(db.String(20), nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    professor_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    criado_em = db.Column(db.DateTime, default=datetime.now)

    professor = db.relationship("Usuario", backref=db.backref("disciplinas", lazy=True))

    livros = db.relationship(
        "Livro",
        secondary=disciplina_livros,
        order_by="Livro.titulo",
        backref=db.backref("disciplinas", lazy=True),
        lazy=True,
    )

    recomendacoes = db.relationship(
        "Recomendacao",
        backref="disciplina",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def possui_livro(self, livro) -> bool:
        return livro in self.livros

    def adicionar_livro(self, livro) -> bool:
        if self.possui_livro(livro):
            return False
        self.livros.append(livro)
        return True

    def remover_livro(self, livro) -> bool:
        if not self.possui_livro(livro):
            return False
        self.livros.remove(livro)
        for recomendacao in list(self.recomendacoes):
            if recomendacao.livro_id == livro.id:
                self.recomendacoes.remove(recomendacao)
        return True

    def listar_livros(self):
        return list(self.livros)

    def recomendacao_do_livro(self, livro):
        for recomendacao in self.recomendacoes:
            if recomendacao.livro_id == livro.id:
                return recomendacao
        return None

    def __repr__(self):
        return f"<Disciplina {self.nome}>"
