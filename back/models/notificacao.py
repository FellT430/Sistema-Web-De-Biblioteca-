from datetime import date, datetime

from models import db


class TipoNotificacao:
    """Tipos de notificação (enum TipoNotificacao do diagrama de classes)."""

    PRAZO_PROXIMO = "PRAZO_PROXIMO"              # devolução vence hoje ou amanhã (RF15, CA02)
    ATRASO = "ATRASO"                            # empréstimo passou do prazo (RF15, CA01)
    DEVOLUCAO_REGISTRADA = "DEVOLUCAO_REGISTRADA"  # bibliotecário registrou a devolução


class Notificacao(db.Model):
    """Aviso exibido ao aluno dentro do sistema (sininho na barra superior).

    `data_referencia` é o dia a que o aviso se refere; junto com o empréstimo
    e o tipo, impede notificações duplicadas no mesmo dia (RN50).
    """

    __tablename__ = "notificacoes"
    __table_args__ = (
        db.UniqueConstraint(
            "emprestimo_id", "tipo", "data_referencia", name="uq_notificacao_emprestimo_tipo_dia"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    emprestimo_id = db.Column(
        db.Integer, db.ForeignKey("emprestimos.id", ondelete="CASCADE"), nullable=True, index=True
    )
    tipo = db.Column(db.String(30), nullable=False)
    mensagem = db.Column(db.String(255), nullable=False)
    data_referencia = db.Column(db.Date, nullable=False, default=date.today)
    criada_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    lida = db.Column(db.Boolean, nullable=False, default=False)

    usuario = db.relationship("Usuario")
    emprestimo = db.relationship(
        "Emprestimo", backref=db.backref("notificacoes", cascade="all, delete-orphan", lazy=True)
    )

    def marcar_como_lida(self) -> None:
        self.lida = True

    def __repr__(self):
        return f"<Notificacao {self.tipo} usuario={self.usuario_id}>"
