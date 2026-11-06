from datetime import datetime

from models import db


class LogAuditoria(db.Model):
    """Registro de auditoria: quem fez o quê, quando e de onde.

    Cada linha representa um evento relevante do sistema (login, logout,
    cadastro, acesso negado, alterações no acervo etc.).

    Decisões de projeto:
    - `usuario_id` NÃO é chave estrangeira de propósito: o histórico de
      auditoria precisa continuar existindo mesmo que o usuário seja
      excluído, e uma FK impediria a exclusão (erro 1451 no MySQL).
    - `usuario_email` guarda uma "foto" do e-mail no momento do evento,
      para identificar o autor mesmo depois de exclusões ou alterações.
    - Os registros são apenas inseridos pelo sistema; não há rota para
      editar ou apagar logs (integridade da trilha de auditoria).
    """

    __tablename__ = "logs_auditoria"

    id = db.Column(db.Integer, primary_key=True)
    criado_em = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)

    usuario_id = db.Column(db.Integer, nullable=True, index=True)
    usuario_email = db.Column(db.String(150), nullable=True, index=True)
    usuario_perfil = db.Column(db.String(20), nullable=True)

    acao = db.Column(db.String(50), nullable=False, index=True)
    descricao = db.Column(db.String(500), nullable=True)
    sucesso = db.Column(db.Boolean, nullable=False, default=True)

    # Contexto da requisição
    ip = db.Column(db.String(45), nullable=True)  # 45 caracteres cabem um IPv6
    user_agent = db.Column(db.String(255), nullable=True)
    metodo = db.Column(db.String(10), nullable=True)
    rota = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<LogAuditoria {self.acao} por {self.usuario_email} em {self.criado_em}>"
