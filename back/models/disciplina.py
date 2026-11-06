from datetime import datetime

from models import db


# Tabela de ligação entre disciplinas e livros (relacionamento muitos-para-muitos).
# RN31: um livro pode estar em várias disciplinas e uma disciplina pode ter
# vários livros. A chave primária composta (disciplina_id + livro_id) garante
# a RN34: o mesmo livro não entra duas vezes na mesma disciplina.
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
    """Disciplina cadastrada por um professor (RF10).

    Cada disciplina pertence a um único professor (RN32: só ele pode alterá-la)
    e reúne os livros do acervo que servem de bibliografia para ela.
    """

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

    # Livros relacionados (bibliografia). O backref cria Livro.disciplinas.
    livros = db.relationship(
        "Livro",
        secondary=disciplina_livros,
        order_by="Livro.titulo",
        backref=db.backref("disciplinas", lazy=True),
        lazy=True,
    )

    # Ao excluir a disciplina, as recomendações dela são excluídas junto.
    recomendacoes = db.relationship(
        "Recomendacao",
        backref="disciplina",
        cascade="all, delete-orphan",
        lazy=True,
    )

    # ------------------------------------------------------------------
    # Métodos do diagrama de classes
    # ------------------------------------------------------------------
    def possui_livro(self, livro) -> bool:
        return livro in self.livros

    def adicionar_livro(self, livro) -> bool:
        """Relaciona o livro à disciplina. Retorna False se já estava (RN34)."""
        if self.possui_livro(livro):
            return False
        self.livros.append(livro)
        return True

    def remover_livro(self, livro) -> bool:
        """Remove o livro da disciplina e a recomendação dele, se houver (RN35)."""
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
        """Recomendação (ativa ou não) deste livro nesta disciplina, se existir."""
        for recomendacao in self.recomendacoes:
            if recomendacao.livro_id == livro.id:
                return recomendacao
        return None

    def __repr__(self):
        return f"<Disciplina {self.nome}>"
