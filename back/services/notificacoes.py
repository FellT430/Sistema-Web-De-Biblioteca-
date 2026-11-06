"""Verificação automática de atrasos e notificações aos alunos (RF15).

`verificar_e_notificar()` é a tarefa que o agendador (services/agendador.py)
executa sozinho, sem intervenção manual (RN49). Ela:

  1. marca como ATRASADO todo empréstimo ATIVO que passou do prazo (RN46/RN51);
  2. avisa o aluno quando a devolução vence hoje ou amanhã (CA02);
  3. avisa o aluno de cada empréstimo atrasado, uma vez por dia (CA01, RN50).

Empréstimos devolvidos ou cancelados nunca geram aviso (CA03).
"""
from datetime import date, timedelta

from models import db, Emprestimo, StatusEmprestimo, Notificacao, TipoNotificacao
from services.emprestimos import atualizar_atrasos


def _ja_notificado(emprestimo, tipo, dia) -> bool:
    """RN50: o mesmo empréstimo não recebe o mesmo aviso duas vezes no mesmo dia."""
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


def verificar_e_notificar(hoje=None) -> dict:
    """Executa a verificação e devolve um resumo do que foi feito."""
    hoje = hoje or date.today()
    novos_atrasos = atualizar_atrasos(hoje)
    lembretes = avisos_atraso = 0

    # Lembrete: vence hoje ou amanhã (só empréstimos ATIVOS, com o livro com o aluno)
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

    # Atraso: um aviso por empréstimo atrasado por dia
    atrasados = Emprestimo.query.filter(Emprestimo.status == StatusEmprestimo.ATRASADO).all()
    for emprestimo in atrasados:
        dias = emprestimo.dias_atraso(hoje)
        mensagem = (
            f"Atraso: \"{emprestimo.livro.titulo}\" está {dias} dia(s) atrasado. "
            "Devolva o livro para poder fazer novos empréstimos."
        )
        if _notificar(emprestimo, TipoNotificacao.ATRASO, mensagem, hoje):
            avisos_atraso += 1

    db.session.commit()
    return {"novos_atrasos": novos_atrasos, "lembretes": lembretes, "avisos_atraso": avisos_atraso}


def notificar_devolucao(emprestimo) -> None:
    """Avisa o aluno que a devolução foi registrada (tipo DEVOLUCAO_REGISTRADA)."""
    hoje = date.today()
    mensagem = f"Devolução de \"{emprestimo.livro.titulo}\" registrada. Obrigado!"
    if emprestimo.devolvido_com_atraso:
        mensagem = (
            f"Devolução de \"{emprestimo.livro.titulo}\" registrada com "
            f"{emprestimo.dias_atraso()} dia(s) de atraso."
        )
    if _notificar(emprestimo, TipoNotificacao.DEVOLUCAO_REGISTRADA, mensagem, hoje):
        db.session.commit()


def nao_lidas(usuario) -> int:
    return Notificacao.query.filter_by(usuario_id=usuario.id, lida=False).count()
