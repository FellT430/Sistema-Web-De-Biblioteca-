from datetime import date, datetime

from models import db


class StatusEmprestimo:
    """Situações possíveis de um empréstimo.

    - SOLICITADO: o aluno pediu o livro e aguarda o bibliotecário confirmar a
      retirada no balcão (RF13, passos 1 a 3). Já ocupa um exemplar, para que
      dois alunos não peçam o último exemplar ao mesmo tempo.
    - ATIVO: retirada confirmada; o empréstimo começa aqui (RN45).
    - ATRASADO: passou da data prevista sem devolução (RN46).
    - DEVOLVIDO: devolução registrada; status final (RN47).
    - CANCELADO: solicitação cancelada pelo aluno ou recusada pelo
      bibliotecário antes da retirada; também é final.
    """

    SOLICITADO = "SOLICITADO"
    ATIVO = "ATIVO"
    ATRASADO = "ATRASADO"
    DEVOLVIDO = "DEVOLVIDO"
    CANCELADO = "CANCELADO"

    # Situações que ocupam um exemplar do livro (descontadas da disponibilidade)
    OCUPAM_EXEMPLAR = (SOLICITADO, ATIVO, ATRASADO)
    # Situações em que o livro está com o aluno (permitem registrar devolução)
    EM_ANDAMENTO = (ATIVO, ATRASADO)
    # Situações finais: não mudam mais
    FINAIS = (DEVOLVIDO, CANCELADO)


class Emprestimo(db.Model):
    """Empréstimo de um exemplar de livro para um aluno (RF13 / RF14)."""

    __tablename__ = "emprestimos"

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    livro_id = db.Column(
        db.Integer, db.ForeignKey("livros.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Bibliotecário que confirmou a retirada e o que registrou a devolução
    bibliotecario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    bibliotecario_devolucao_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    status = db.Column(db.String(20), nullable=False, default=StatusEmprestimo.SOLICITADO, index=True)
    data_solicitacao = db.Column(db.DateTime, nullable=False, default=datetime.now)
    data_emprestimo = db.Column(db.DateTime, nullable=True)          # confirmação da retirada
    data_prevista_devolucao = db.Column(db.Date, nullable=True)      # RN43
    data_devolucao = db.Column(db.DateTime, nullable=True)           # RN48

    aluno = db.relationship("Usuario", foreign_keys=[aluno_id])
    bibliotecario = db.relationship("Usuario", foreign_keys=[bibliotecario_id])
    bibliotecario_devolucao = db.relationship("Usuario", foreign_keys=[bibliotecario_devolucao_id])
    livro = db.relationship(
        "Livro", backref=db.backref("emprestimos", cascade="all, delete-orphan", lazy=True)
    )

    # ------------------------------------------------------------------
    # Métodos do diagrama de classes
    # ------------------------------------------------------------------
    def esta_atrasado(self, hoje=None) -> bool:
        """Livro ainda com o aluno e data prevista já passou."""
        hoje = hoje or date.today()
        return (
            self.status in StatusEmprestimo.EM_ANDAMENTO
            and self.data_prevista_devolucao is not None
            and hoje > self.data_prevista_devolucao
        )

    def dias_atraso(self, hoje=None) -> int:
        """Dias de atraso: até hoje (se ainda está com o aluno) ou até a devolução."""
        if self.data_prevista_devolucao is None:
            return 0
        if self.status == StatusEmprestimo.DEVOLVIDO and self.data_devolucao:
            referencia = self.data_devolucao.date()
        else:
            referencia = hoje or date.today()
        return max((referencia - self.data_prevista_devolucao).days, 0)

    @property
    def devolvido_com_atraso(self) -> bool:
        """RN48: devoluções após o prazo ficam identificadas."""
        return self.status == StatusEmprestimo.DEVOLVIDO and self.dias_atraso() > 0

    def __repr__(self):
        return f"<Emprestimo #{self.id} livro={self.livro_id} aluno={self.aluno_id} {self.status}>"
