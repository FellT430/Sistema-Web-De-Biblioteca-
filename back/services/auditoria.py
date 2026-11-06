"""Serviço de auditoria.

Centraliza o registro de eventos de auditoria em dois lugares:

1. Tabela `logs_auditoria` no banco (consultável pela tela /admin/auditoria).
2. Arquivo `back/logs/auditoria.log` (cópia em texto, útil se o banco
   estiver fora do ar ou para análise externa).

Uso nos controllers:

    from services.auditoria import registrar, Acoes
    registrar(Acoes.LOGIN_SUCESSO, "Login realizado", usuario=usuario)

Uma falha ao gravar o log NUNCA derruba a ação do usuário: o erro é
registrado no arquivo e a requisição segue normalmente.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

from flask import has_request_context, request
from flask_login import current_user

from models import db
from models.log_auditoria import LogAuditoria


class Acoes:
    """Catálogo de ações auditadas (evita erros de digitação nos controllers)."""

    # Acessos
    LOGIN_SUCESSO = "LOGIN_SUCESSO"
    LOGIN_FALHA = "LOGIN_FALHA"
    LOGIN_BLOQUEADO = "LOGIN_BLOQUEADO"
    LOGOUT = "LOGOUT"
    ACESSO_NEGADO = "ACESSO_NEGADO"
    ACESSO_AREA_ADMIN = "ACESSO_AREA_ADMIN"
    ACESSO_AUDITORIA = "ACESSO_AUDITORIA"
    EXPORTACAO_AUDITORIA = "EXPORTACAO_AUDITORIA"
    CONSULTA_DADOS_PESSOAIS = "CONSULTA_DADOS_PESSOAIS"

    # Autenticação de dois fatores (2FA)
    DOIS_FATORES_ATIVADO = "DOIS_FATORES_ATIVADO"
    DOIS_FATORES_FALHA = "DOIS_FATORES_FALHA"
    DOIS_FATORES_RESETADO = "DOIS_FATORES_RESETADO"

    # Usuários
    CADASTRO_USUARIO = "CADASTRO_USUARIO"
    CADASTRO_RECUSADO = "CADASTRO_RECUSADO"
    SENHA_REDEFINIDA = "SENHA_REDEFINIDA"
    SENHA_REDEFINICAO_FALHA = "SENHA_REDEFINICAO_FALHA"

    # Acervo
    LIVRO_CRIADO = "LIVRO_CRIADO"
    LIVRO_EDITADO = "LIVRO_EDITADO"
    LIVRO_EXCLUIDO = "LIVRO_EXCLUIDO"
    BUSCA_GOOGLE_BOOKS = "BUSCA_GOOGLE_BOOKS"

    # Disciplinas (RF10)
    DISCIPLINA_CRIADA = "DISCIPLINA_CRIADA"
    DISCIPLINA_EDITADA = "DISCIPLINA_EDITADA"
    DISCIPLINA_EXCLUIDA = "DISCIPLINA_EXCLUIDA"
    DISCIPLINA_LIVRO_ADICIONADO = "DISCIPLINA_LIVRO_ADICIONADO"
    DISCIPLINA_LIVRO_REMOVIDO = "DISCIPLINA_LIVRO_REMOVIDO"

    # Recomendações (RF11)
    RECOMENDACAO_CRIADA = "RECOMENDACAO_CRIADA"
    RECOMENDACAO_REMOVIDA = "RECOMENDACAO_REMOVIDA"

    # Empréstimos e devoluções (RF13 / RF14)
    EMPRESTIMO_SOLICITADO = "EMPRESTIMO_SOLICITADO"
    EMPRESTIMO_RECUSADO_REGRA = "EMPRESTIMO_RECUSADO_REGRA"
    EMPRESTIMO_CANCELADO = "EMPRESTIMO_CANCELADO"
    EMPRESTIMO_CONFIRMADO = "EMPRESTIMO_CONFIRMADO"
    EMPRESTIMO_RECUSADO = "EMPRESTIMO_RECUSADO"
    DEVOLUCAO_REGISTRADA = "DEVOLUCAO_REGISTRADA"

    # Verificação automática de atrasos (RF15)
    VERIFICACAO_ATRASOS = "VERIFICACAO_ATRASOS"

    @classmethod
    def todas(cls):
        return sorted(
            valor for nome, valor in vars(cls).items()
            if nome.isupper() and isinstance(valor, str)
        )


# ---------------------------------------------------------------------------
# Log em arquivo
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
_arquivo_logger = logging.getLogger("auditoria")


def _configurar_log_arquivo():
    if _arquivo_logger.handlers:
        return
    os.makedirs(_LOG_DIR, exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join(_LOG_DIR, "auditoria.log"),
        maxBytes=1_000_000,  # ~1 MB por arquivo
        backupCount=5,       # guarda os 5 arquivos anteriores
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", "%d/%m/%Y %H:%M:%S"))
    _arquivo_logger.addHandler(handler)
    _arquivo_logger.setLevel(logging.INFO)
    _arquivo_logger.propagate = False


_configurar_log_arquivo()


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------
def _ip_do_cliente():
    # Se o sistema estiver atrás de um proxy (ex.: Nginx), o IP real vem aqui
    encaminhado = request.headers.get("X-Forwarded-For", "")
    if encaminhado:
        return encaminhado.split(",")[0].strip()[:45]
    return (request.remote_addr or "")[:45]


def registrar(acao, descricao="", usuario=None, email=None, sucesso=True):
    """Grava um evento de auditoria.

    - `usuario`: objeto Usuario autor da ação. Se omitido, usa o usuário
      logado (se houver).
    - `email`: usado quando não há usuário identificado (ex.: tentativa de
      login com e-mail inexistente).
    - `sucesso`: False para tentativas que falharam ou foram bloqueadas.
    """
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
    except Exception as erro:  # noqa: BLE001 — auditoria nunca pode derrubar a requisição
        db.session.rollback()
        _arquivo_logger.error("ERRO ao gravar auditoria no banco: %s", erro)
