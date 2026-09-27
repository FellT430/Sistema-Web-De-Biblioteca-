import logging
import os
from logging.handlers import RotatingFileHandler

from flask import has_request_context, request
from flask_login import current_user

from models import db
from models.log_auditoria import LogAuditoria

class Acoes:
    LOGIN_SUCESSO = "LOGIN_SUCESSO"
    LOGIN_FALHA = "LOGIN_FALHA"
    LOGIN_BLOQUEADO = "LOGIN_BLOQUEADO"
    LOGOUT = "LOGOUT"
    ACESSO_NEGADO = "ACESSO_NEGADO"
    ACESSO_AREA_ADMIN = "ACESSO_AREA_ADMIN"
    ACESSO_AUDITORIA = "ACESSO_AUDITORIA"
    EXPORTACAO_AUDITORIA = "EXPORTACAO_AUDITORIA"
    CONSULTA_DADOS_PESSOAIS = "CONSULTA_DADOS_PESSOAIS"

    DOIS_FATORES_ATIVADO = "DOIS_FATORES_ATIVADO"
    DOIS_FATORES_FALHA = "DOIS_FATORES_FALHA"
    DOIS_FATORES_RESETADO = "DOIS_FATORES_RESETADO"

    CADASTRO_USUARIO = "CADASTRO_USUARIO"
    CADASTRO_RECUSADO = "CADASTRO_RECUSADO"

    LIVRO_CRIADO = "LIVRO_CRIADO"
    LIVRO_EDITADO = "LIVRO_EDITADO"
    LIVRO_EXCLUIDO = "LIVRO_EXCLUIDO"
    BUSCA_GOOGLE_BOOKS = "BUSCA_GOOGLE_BOOKS"

    @classmethod
    def todas(cls):
        return sorted(
            valor for nome, valor in vars(cls).items()
            if nome.isupper() and isinstance(valor, str)
        )


_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
_arquivo_logger = logging.getLogger("auditoria")


def _configurar_log_arquivo():
    if _arquivo_logger.handlers:
        return
    os.makedirs(_LOG_DIR, exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join(_LOG_DIR, "auditoria.log"),
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", "%d/%m/%Y %H:%M:%S"))
    _arquivo_logger.addHandler(handler)
    _arquivo_logger.setLevel(logging.INFO)
    _arquivo_logger.propagate = False


_configurar_log_arquivo()


def _ip_do_cliente():
    encaminhado = request.headers.get("X-Forwarded-For", "")
    if encaminhado:
        return encaminhado.split(",")[0].strip()[:45]
    return (request.remote_addr or "")[:45]


def registrar(acao, descricao="", usuario=None, email=None, sucesso=True):
    if usuario is None and has_request_context() and current_user.is_authenticated:
        usuario = current_user

    log = LogAuditoria(
        acao=acao,
        descricao=(descricao or "")[:500],
        sucesso=sucesso,
        usuario_id=getattr(usuario, "id", None),
        usuario_email=getattr(usuario, "email", None) or email,
        usuario_perfil=getattr(usuario, "perfil", None),
    )

    if has_request_context():
        log.ip = _ip_do_cliente()
        log.user_agent = (request.headers.get("User-Agent") or "")[:255]
        log.metodo = request.method
        log.rota = request.path[:255]

    _arquivo_logger.info(
        "%s | %s | usuario=%s | ip=%s | %s %s | %s",
        acao,
        "OK" if sucesso else "FALHA",
        log.usuario_email or "anônimo",
        log.ip or "-",
        log.metodo or "-",
        log.rota or "-",
        log.descricao,
    )

    try:
        db.session.add(log)
        db.session.commit()
    except Exception as erro:
        db.session.rollback()
        _arquivo_logger.error("ERRO ao gravar auditoria no banco: %s", erro)
