from datetime import date, datetime

from models import db


class StatusEmprestimo:

    SOLICITADO = "SOLICITADO"
    ATIVO = "ATIVO"
    ATRASADO = "ATRASADO"
    DEVOLVIDO = "DEVOLVIDO"
    CANCELADO = "CANCELADO"

    OCUPAM_EXEMPLAR = (SOLICITADO, ATIVO, ATRASADO)
    EM_ANDAMENTO = (ATIVO, ATRASADO)
    FINAIS = (DEVOLVIDO, CANCELADO)


class Emprestimo(db.Model):

    __tablename__ = "emprestimos"

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    livro_id = db.Column(
        db.Integer, db.ForeignKey("livros.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bibliotecario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    bibliotecario_devolucao_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    status = db.Column(db.String(20), nullable=False, default=StatusEmprestimo.SOLICITADO, index=True)
    data_solicitacao = db.Column(db.DateTime, nullable=False, default=datetime.now)
    data_emprestimo = db.Column(db.DateTime, nullable=True)
    data_prevista_devolucao = db.Column(db.Date, nullable=True)
    data_devolucao = db.Column(db.DateTime, nullable=True)

    aluno = db.relationship("Usuario", foreign_keys=[aluno_id])
    bibliotecario = db.relationship("Usuario", foreign_keys=[bibliotecario_id])
    bibliotecario_devolucao = db.relationship("Usuario", foreign_keys=[bibliotecario_devolucao_id])
    livro = db.relationship(
        "Livro", backref=db.backref("emprestimos", cascade="all, delete-orphan", lazy=True)
    )

    def esta_atrasado(self, hoje=None) -> bool:
        hoje = hoje or date.today()
        return (
            self.status in StatusEmprestimo.EM_ANDAMENTO
            and self.data_prevista_devolucao is not None
            and hoje > self.data_prevista_devolucao
        )

    def dias_atraso(self, hoje=None) -> int:
        if self.data_prevista_devolucao is None:
            return 0
        if self.status == StatusEmprestimo.DEVOLVIDO and self.data_devolucao:
            referencia = self.data_devolucao.date()
        else:
            referencia = hoje or date.today()
        return max((referencia - self.data_prevista_devolucao).days, 0)

    @property
    def devolvido_com_atraso(self) -> bool:
        return self.status == StatusEmprestimo.DEVOLVIDO and self.dias_atraso() > 0

    def __repr__(self):
        return f"<Emprestimo #{self.id} livro={self.livro_id} aluno={self.aluno_id} {self.status}>"
