from datetime import datetime

from models import db


class Recomendacao(db.Model):
    """Recomendação de um livro feita por um professor em uma disciplina (RF11).

    - RN35: só livros relacionados à disciplina podem ser recomendados nela
      (validado no controller antes de criar).
    - RN36: o comentário (mensagem) é opcional e tem no máximo 500 caracteres.
    - RN38: o professor pode remover a recomendação a qualquer momento. Em vez
      de apagar a linha, marcamos `ativa = False`; assim o histórico fica
      guardado e, se ele recomendar de novo, a mesma linha é reativada.

    A restrição única abaixo garante uma recomendação por livro em cada
    disciplina.
    """

    __tablename__ = "recomendacoes"
    __table_args__ = (
        db.UniqueConstraint("disciplina_id", "livro_id", name="uq_recomendacao_disciplina_livro"),
    )

    id = db.Column(db.Integer, primary_key=True)
    professor_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    livro_id = db.Column(
        db.Integer, db.ForeignKey("livros.id", ondelete="CASCADE"), nullable=False, index=True
    )
    disciplina_id = db.Column(
        db.Integer, db.ForeignKey("disciplinas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mensagem = db.Column(db.String(500), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.now)
    ativa = db.Column(db.Boolean, nullable=False, default=True)

    professor = db.relationship("Usuario")
    # Ao excluir um livro do acervo, as recomendações dele são excluídas junto.
    livro = db.relationship(
        "Livro", backref=db.backref("recomendacoes", cascade="all, delete-orphan", lazy=True)
    )

    def __repr__(self):
        return f"<Recomendacao livro={self.livro_id} disciplina={self.disciplina_id}>"
