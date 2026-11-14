import logging
import secrets
from datetime import datetime

from werkzeug.security import generate_password_hash

from models import (
    db, Usuario, Emprestimo, StatusEmprestimo, Reserva, StatusReserva, Notificacao, LogAuditoria,
    CodigoRecuperacao,
)
from services import envio_email
from services.auditoria import registrar, Acoes
from services.reservas import cancelar_reserva

_log = logging.getLogger("privacidade")

NOME_ANONIMIZADO = "Usuário removido"
DOMINIO_ANONIMIZADO = "anonimizado.invalid"
MSG_LIVROS_EM_MAOS = "Devolva os livros em seu poder antes de solicitar a exclusão dos dados."


class RegraPrivacidadeError(Exception):
    pass


def _motivo_bloqueio(usuario):
    if usuario.anonimizado:
        return "Os dados desta conta já foram anonimizados."
    if usuario.is_superadmin:
        return "Contas de Administrador não podem solicitar a exclusão dos dados."
    if Emprestimo.query.filter(
        Emprestimo.aluno_id == usuario.id,
        Emprestimo.status.in_(StatusEmprestimo.OCUPAM_EXEMPLAR),
    ).first():
        return MSG_LIVROS_EM_MAOS
    return None


def pendentes():
    return (
        Usuario.query.filter(Usuario.exclusao_solicitada_em.isnot(None), Usuario.anonimizado_em.is_(None))
        .order_by(Usuario.exclusao_solicitada_em).all()
    )


def solicitar_exclusao(usuario) -> None:
    motivo = _motivo_bloqueio(usuario)
    if motivo:
        raise RegraPrivacidadeError(motivo)
    if usuario.exclusao_pendente:
        raise RegraPrivacidadeError("Você já tem um pedido de exclusão aguardando análise.")

    usuario.exclusao_solicitada_em = datetime.now()
    db.session.commit()
    registrar(
        Acoes.EXCLUSAO_SOLICITADA,
        "Usuário solicitou a exclusão dos próprios dados (LGPD, art. 18, VI)",
        usuario=usuario,
    )
    _enviar_seguro(envio_email.enviar_exclusao_solicitada, usuario)


def recusar_exclusao(usuario, motivo, admin) -> None:
    if not usuario.exclusao_pendente:
        raise RegraPrivacidadeError("Este usuário não tem pedido de exclusão pendente.")
    motivo = (motivo or "").strip()
    if not motivo:
        raise RegraPrivacidadeError("Informe o motivo da recusa.")

    usuario.exclusao_solicitada_em = None
    db.session.commit()
    registrar(
        Acoes.EXCLUSAO_RECUSADA,
        f"Pedido de exclusão do usuário #{usuario.id} ({usuario.email}) recusado. Motivo: {motivo}",
        usuario=admin,
    )
    _enviar_seguro(envio_email.enviar_exclusao_recusada, usuario, motivo)


def confirmar_exclusao(usuario, admin) -> None:
    if not usuario.exclusao_pendente:
        raise RegraPrivacidadeError("Este usuário não tem pedido de exclusão pendente.")
    motivo = _motivo_bloqueio(usuario)
    if motivo:
        raise RegraPrivacidadeError(motivo)

    _enviar_seguro(envio_email.enviar_exclusao_confirmada, usuario.email, usuario.nome)
    anonimizar_usuario(usuario, admin)


def anonimizar_usuario(usuario, executor=None) -> None:
    email_original, nome_original, uid = usuario.email, usuario.nome, usuario.id
    email_anonimo = f"removido-{uid}-{secrets.token_hex(8)}@{DOMINIO_ANONIMIZADO}"

    for reserva in Reserva.query.filter_by(aluno_id=uid, status=StatusReserva.AGUARDANDO).all():
        cancelar_reserva(reserva, usuario)

    try:
        usuario.nome = NOME_ANONIMIZADO
        usuario.email = email_anonimo
        usuario.senha_hash = generate_password_hash(secrets.token_urlsafe(32))
        usuario.totp_secret = None
        usuario.totp_ultimo_passo = None
        usuario.dois_fatores_ativo = False
        usuario.ativo = False
        usuario.anonimizado_em = datetime.now()
        usuario.exclusao_solicitada_em = usuario.exclusao_solicitada_em or usuario.anonimizado_em

        CodigoRecuperacao.query.filter_by(usuario_id=uid).delete(synchronize_session=False)
        Notificacao.query.filter_by(usuario_id=uid).delete(synchronize_session=False)

        for log in LogAuditoria.query.filter(
            (LogAuditoria.usuario_id == uid)
            | (LogAuditoria.usuario_email == email_original)
            | (LogAuditoria.descricao.contains(email_original))
        ).all():
            if log.usuario_id == uid or log.usuario_email == email_original:
                log.usuario_email = email_anonimo
            if log.descricao and email_original in log.descricao:
                log.descricao = log.descricao.replace(email_original, email_anonimo)
            if log.descricao and nome_original in log.descricao and log.usuario_id == uid:
                log.descricao = log.descricao.replace(nome_original, NOME_ANONIMIZADO)

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    registrar(
        Acoes.USUARIO_ANONIMIZADO,
        f"Dados do usuário #{uid} anonimizados (LGPD, art. 18, VI)",
        usuario=executor,
    )


def _enviar_seguro(funcao, *args) -> bool:
    try:
        ok = funcao(*args)
    except Exception:
        _log.exception("Falha ao enviar e-mail de privacidade (%s)", getattr(funcao, "__name__", funcao))
        ok = False
    if not ok:
        registrar(Acoes.EMAIL_FALHA_ENVIO, "Falha ao enviar e-mail do fluxo de exclusão de dados", sucesso=False)
    return ok
