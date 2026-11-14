from datetime import datetime

from models import db


class StatusReserva:

    AGUARDANDO = "AGUARDANDO"
    ATENDIDA = "ATENDIDA"
    CANCELADA = "CANCELADA"
    EXPIRADA = "EXPIRADA"


class Reserva(db.Model):

    __tablename__ = "reservas"

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    livro_id = db.Column(
        db.Integer, db.ForeignKey("livros.id", ondelete="CASCADE"), nullable=False, index=True
    )
    emprestimo_id = db.Column(
        db.Integer, db.ForeignKey("emprestimos.id", ondelete="SET NULL"), nullable=True, index=True
    )

    status = db.Column(db.String(20), nullable=False, default=StatusReserva.AGUARDANDO, index=True)
    criada_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    atendida_em = db.Column(db.DateTime, nullable=True)

    aluno = db.relationship("Usuario", foreign_keys=[aluno_id])
    emprestimo = db.relationship("Emprestimo", foreign_keys=[emprestimo_id])
    livro = db.relationship(
        "Livro", backref=db.backref("reservas", cascade="all, delete-orphan", lazy=True)
    )

    def posicao_na_fila(self):
        if self.status != StatusReserva.AGUARDANDO:
            return None
        antes_ou_eu = db.or_(
            Reserva.criada_em < self.criada_em,
            db.and_(Reserva.criada_em == self.criada_em, Reserva.id <= self.id),
        )
        return Reserva.query.filter(
            Reserva.livro_id == self.livro_id,
            Reserva.status == StatusReserva.AGUARDANDO,
            antes_ou_eu,
        ).count()

    def __repr__(self):
        return f"<Reserva #{self.id} livro={self.livro_id} aluno={self.aluno_id} {self.status}>"
