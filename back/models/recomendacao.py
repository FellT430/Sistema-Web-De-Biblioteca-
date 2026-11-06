from datetime import datetime

from models import db


class Recomendacao(db.Model):

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
    livro = db.relationship(
        "Livro", backref=db.backref("recomendacoes", cascade="all, delete-orphan", lazy=True)
    )

    def __repr__(self):
        return f"<Recomendacao livro={self.livro_id} disciplina={self.disciplina_id}>"
