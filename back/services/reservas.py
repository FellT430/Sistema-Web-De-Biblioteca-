import logging
from datetime import date, datetime, timedelta
from functools import partial

from flask import current_app

from models import db, Emprestimo, StatusEmprestimo, Reserva, StatusReserva, TipoNotificacao
from services import envio_email
from services.auditoria import registrar, Acoes
from services.emprestimos import RegraEmprestimoError, aluno_tem_atraso, quantidade_em_uso
from services.notificacoes import _notificar, _enviar_emails

_log = logging.getLogger("reservas")

AUTOR_SISTEMA = "agendador@sistema"


class RegraReservaError(RegraEmprestimoError):
    pass


def _descricao(reserva) -> str:
    return (
        f"Reserva #{reserva.id}: livro #{reserva.livro_id} '{reserva.livro.titulo}' "
        f"para {reserva.aluno.nome} ({reserva.aluno.email})"
    )


def _auditar(acao, descricao, usuario=None) -> None:
    registrar(acao, descricao, usuario=usuario, email=AUTOR_SISTEMA)


def reservas_ativas(aluno) -> int:
    return Reserva.query.filter_by(aluno_id=aluno.id, status=StatusReserva.AGUARDANDO).count()


def motivo_para_nao_reservar(aluno, livro):
    if livro.exemplares_disponiveis() > 0:
        return "Este livro tem exemplares disponíveis. Faça a solicitação de empréstimo em vez de reservar."

    if aluno_tem_atraso(aluno):
        return "Você possui empréstimo em atraso. Devolva o livro atrasado para poder reservar."

    if Reserva.query.filter_by(
        aluno_id=aluno.id, livro_id=livro.id, status=StatusReserva.AGUARDANDO
    ).first():
        return "Você já tem uma reserva ativa deste livro."

    if Emprestimo.query.filter(
        Emprestimo.aluno_id == aluno.id,
        Emprestimo.livro_id == livro.id,
        Emprestimo.status.in_(StatusEmprestimo.OCUPAM_EXEMPLAR),
    ).first():
        return "Você já possui uma solicitação ou empréstimo em andamento deste livro."

    limite = current_app.config["MAX_RESERVAS_POR_ALUNO"]
    if reservas_ativas(aluno) >= limite:
        return f"Você atingiu o limite de {limite} reservas ativas."

    return None


def criar_reserva(aluno, livro) -> Reserva:
    motivo = motivo_para_nao_reservar(aluno, livro)
    if motivo:
        raise RegraReservaError(motivo)

    reserva = Reserva(aluno_id=aluno.id, livro_id=livro.id, status=StatusReserva.AGUARDANDO)
    db.session.add(reserva)
    db.session.commit()
    _auditar(Acoes.RESERVA_CRIADA, f"{_descricao(reserva)} criada (entrou na fila)", usuario=aluno)
    return reserva


def cancelar_reserva(reserva, aluno) -> None:
    if reserva.aluno_id != aluno.id:
        raise PermissionError("A reserva não pertence a este aluno.")
    if reserva.status != StatusReserva.AGUARDANDO:
        raise RegraReservaError("Só é possível cancelar reservas que ainda estão aguardando na fila.")

    reserva.status = StatusReserva.CANCELADA
    db.session.commit()
    _auditar(Acoes.RESERVA_CANCELADA, f"{_descricao(reserva)} cancelada pelo aluno", usuario=aluno)


def _motivo_aluno_nao_pode_retirar(aluno):
    if not aluno.ativo:
        return "conta desativada"
    if aluno_tem_atraso(aluno):
        return "possui empréstimo em atraso"
    if quantidade_em_uso(aluno) >= current_app.config["MAX_EMPRESTIMOS_POR_ALUNO"]:
        return "atingiu o limite de empréstimos simultâneos"
    return None


def atender_proxima_reserva(livro) -> dict:
    resultado = {"atendidas": 0, "emails_enviados": 0}
    try:
        prazo = current_app.config["PRAZO_RETIRADA_RESERVA_DIAS"]

        while livro.exemplares_disponiveis() > 0:
            reserva = (
                Reserva.query.filter_by(livro_id=livro.id, status=StatusReserva.AGUARDANDO)
                .order_by(Reserva.criada_em, Reserva.id)
                .first()
            )
            if reserva is None:
                break

            motivo = _motivo_aluno_nao_pode_retirar(reserva.aluno)
            if motivo:
                reserva.status = StatusReserva.CANCELADA
                db.session.commit()
                _auditar(
                    Acoes.RESERVA_CANCELADA,
                    f"{_descricao(reserva)} cancelada pelo sistema: aluno {motivo}",
                )
                continue

            agora = datetime.now()
            limite = agora.date() + timedelta(days=prazo)
            emprestimo = Emprestimo(
                aluno_id=reserva.aluno_id, livro_id=livro.id, status=StatusEmprestimo.SOLICITADO
            )
            db.session.add(emprestimo)
            db.session.flush()

            reserva.status = StatusReserva.ATENDIDA
            reserva.atendida_em = agora
            reserva.emprestimo_id = emprestimo.id

            nova = _notificar(
                emprestimo,
                TipoNotificacao.RESERVA_DISPONIVEL,
                f"Reserva atendida: \"{livro.titulo}\" está disponível. "
                f"Retire na biblioteca até {limite.strftime('%d/%m/%Y')}.",
                agora.date(),
            )
            db.session.commit()

            resultado["atendidas"] += 1
            _auditar(
                Acoes.RESERVA_ATENDIDA,
                f"{_descricao(reserva)} atendida; empréstimo #{emprestimo.id} aguardando retirada "
                f"até {limite.strftime('%d/%m/%Y')}",
            )
            if nova:
                resultado["emails_enviados"] += _enviar_emails(
                    [partial(envio_email.enviar_reserva_disponivel, reserva, limite)]
                )
    except Exception:
        db.session.rollback()
        _log.exception("Falha ao atender a fila de reservas do livro #%s", getattr(livro, "id", "?"))
    return resultado


def expirar_reservas(hoje=None) -> dict:
    hoje = hoje or date.today()
    prazo = current_app.config["PRAZO_RETIRADA_RESERVA_DIAS"]
    resultado = {"expiradas": 0, "atendidas": 0, "emails_enviados": 0}

    aguardando_retirada = (
        Reserva.query.join(Emprestimo, Reserva.emprestimo_id == Emprestimo.id)
        .filter(
            Reserva.status == StatusReserva.ATENDIDA,
            Emprestimo.status == StatusEmprestimo.SOLICITADO,
        )
        .all()
    )

    for reserva in aguardando_retirada:
        if reserva.atendida_em is None or reserva.atendida_em.date() + timedelta(days=prazo) >= hoje:
            continue

        try:
            emprestimo, livro = reserva.emprestimo, reserva.livro
            emprestimo.status = StatusEmprestimo.CANCELADO
            reserva.status = StatusReserva.EXPIRADA
            nova = _notificar(
                emprestimo,
                TipoNotificacao.RESERVA_EXPIRADA,
                f"Sua reserva de \"{livro.titulo}\" expirou: o livro não foi retirado no prazo "
                "e passou para o próximo da fila.",
                hoje,
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
            _log.exception("Falha ao expirar a reserva #%s", reserva.id)
            continue

        resultado["expiradas"] += 1
        _auditar(
            Acoes.RESERVA_EXPIRADA,
            f"{_descricao(reserva)} expirada: livro não retirado em {prazo} dia(s); "
            f"solicitação #{reserva.emprestimo_id} cancelada",
        )
        if nova:
            resultado["emails_enviados"] += _enviar_emails(
                [partial(envio_email.enviar_reserva_expirada, reserva)]
            )

        proxima = atender_proxima_reserva(reserva.livro)
        resultado["atendidas"] += proxima["atendidas"]
        resultado["emails_enviados"] += proxima["emails_enviados"]

    return resultado
