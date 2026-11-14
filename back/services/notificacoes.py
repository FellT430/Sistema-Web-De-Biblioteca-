import logging
from datetime import date, timedelta
from functools import partial

from models import db, Emprestimo, StatusEmprestimo, Notificacao, TipoNotificacao
from services.emprestimos import atualizar_atrasos
from services import envio_email

_log = logging.getLogger("notificacoes")


def _ja_notificado(emprestimo, tipo, dia) -> bool:
    return (
        Notificacao.query.filter_by(emprestimo_id=emprestimo.id, tipo=tipo, data_referencia=dia).first()
        is not None
    )


def _notificar(emprestimo, tipo, mensagem, dia) -> bool:
    if _ja_notificado(emprestimo, tipo, dia):
        return False
    db.session.add(
        Notificacao(
            usuario_id=emprestimo.aluno_id,
            emprestimo_id=emprestimo.id,
            tipo=tipo,
            mensagem=mensagem[:255],
            data_referencia=dia,
        )
    )
    return True


def _enviar_emails(pendentes) -> int:
    enviados = 0
    for envio in pendentes:
        try:
            if envio():
                enviados += 1
        except Exception:
            _log.exception("Falha ao enviar e-mail de notificação de empréstimo")
    return enviados


def verificar_e_notificar(hoje=None) -> dict:
    hoje = hoje or date.today()
    novos_atrasos = atualizar_atrasos(hoje)
    lembretes = avisos_atraso = 0
    pendentes = []

    vencendo = Emprestimo.query.filter(
        Emprestimo.status == StatusEmprestimo.ATIVO,
        Emprestimo.data_prevista_devolucao.in_([hoje, hoje + timedelta(days=1)]),
    ).all()
    for emprestimo in vencendo:
        quando = "hoje" if emprestimo.data_prevista_devolucao == hoje else "amanhã"
        mensagem = (
            f"Lembrete: devolva \"{emprestimo.livro.titulo}\" até {quando} "
            f"({emprestimo.data_prevista_devolucao.strftime('%d/%m/%Y')})."
        )
        if _notificar(emprestimo, TipoNotificacao.PRAZO_PROXIMO, mensagem, hoje):
            lembretes += 1
            pendentes.append(partial(envio_email.enviar_lembrete_prazo, emprestimo, hoje))

    atrasados = Emprestimo.query.filter(Emprestimo.status == StatusEmprestimo.ATRASADO).all()
    for emprestimo in atrasados:
        dias = emprestimo.dias_atraso(hoje)
        mensagem = (
            f"Atraso: \"{emprestimo.livro.titulo}\" está {dias} dia(s) atrasado. "
            "Devolva o livro para poder fazer novos empréstimos."
        )
        if _notificar(emprestimo, TipoNotificacao.ATRASO, mensagem, hoje):
            avisos_atraso += 1
            pendentes.append(partial(envio_email.enviar_aviso_atraso, emprestimo, dias))

    db.session.commit()
    emails_enviados = _enviar_emails(pendentes)
    return {
        "novos_atrasos": novos_atrasos,
        "lembretes": lembretes,
        "avisos_atraso": avisos_atraso,
        "emails_enviados": emails_enviados,
    }


def notificar_devolucao(emprestimo) -> None:
    hoje = date.today()
    mensagem = f"Devolução de \"{emprestimo.livro.titulo}\" registrada. Obrigado!"
    if emprestimo.devolvido_com_atraso:
        mensagem = (
            f"Devolução de \"{emprestimo.livro.titulo}\" registrada com "
            f"{emprestimo.dias_atraso()} dia(s) de atraso."
        )
    if _notificar(emprestimo, TipoNotificacao.DEVOLUCAO_REGISTRADA, mensagem, hoje):
        db.session.commit()
        _enviar_emails([partial(envio_email.enviar_devolucao, emprestimo)])


def nao_lidas(usuario) -> int:
    return Notificacao.query.filter_by(usuario_id=usuario.id, lida=False).count()
