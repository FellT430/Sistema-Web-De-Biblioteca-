import enum
from datetime import date, datetime, timedelta

from app.extensions import db

PRAZO_PADRAO_DIAS = 7


class StatusExemplar(enum.Enum):
    DISPONIVEL = "disponivel"
    EMPRESTADO = "emprestado"


class StatusEmprestimo(enum.Enum):
    EM_DIA = "em_dia"
    ATRASADO = "atrasado"


class Livro(db.Model):
    __tablename__ = "livros"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(150), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=True)
    ano_publicacao = db.Column(db.Integer, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    exemplares = db.relationship(
        "Exemplar", back_populates="livro", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Livro {self.titulo!r}>"


class Exemplar(db.Model):
    __tablename__ = "exemplares"

    id = db.Column(db.Integer, primary_key=True)
    livro_id = db.Column(db.Integer, db.ForeignKey("livros.id"), nullable=False)
    codigo_patrimonio = db.Column(db.String(30), unique=True, nullable=False)
    status = db.Column(
        db.Enum(
            StatusExemplar,
            name="status_exemplar",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=StatusExemplar.DISPONIVEL,
        server_default=StatusExemplar.DISPONIVEL.value,
    )
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    livro = db.relationship("Livro", back_populates="exemplares")
    emprestimos = db.relationship("Emprestimo", back_populates="exemplar")

    @property
    def disponivel(self):
        return self.status == StatusExemplar.DISPONIVEL

    def __repr__(self):
        return f"<Exemplar {self.codigo_patrimonio!r} ({self.status.value})>"


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    matricula = db.Column(db.String(30), unique=True, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    emprestimos = db.relationship("Emprestimo", back_populates="usuario")

    def __repr__(self):
        return f"<Usuario {self.nome!r}>"


class Emprestimo(db.Model):
    __tablename__ = "emprestimos"

    id = db.Column(db.Integer, primary_key=True)
    exemplar_id = db.Column(db.Integer, db.ForeignKey("exemplares.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    data_emprestimo = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_prevista_devolucao = db.Column(db.Date, nullable=False)
    data_devolucao = db.Column(db.DateTime, nullable=True)
    status = db.Column(
        db.Enum(
            StatusEmprestimo,
            name="status_emprestimo",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=StatusEmprestimo.EM_DIA,
        server_default=StatusEmprestimo.EM_DIA.value,
    )

    exemplar = db.relationship("Exemplar", back_populates="emprestimos")
    usuario = db.relationship("Usuario", back_populates="emprestimos")

    @property
    def esta_ativo(self):
        return self.data_devolucao is None

    @property
    def esta_atrasado(self):
        return self.status == StatusEmprestimo.ATRASADO

    @staticmethod
    def calcular_data_prevista(dias=PRAZO_PADRAO_DIAS):
        return date.today() + timedelta(days=dias)

    def __repr__(self):
        return f"<Emprestimo exemplar={self.exemplar_id} usuario={self.usuario_id}>"
