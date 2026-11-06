"""Regras de negócio dos empréstimos e devoluções (RF13 / RF14).

Os controllers só chamam estas funções; todas as regras (RN41 a RN48) ficam
concentradas aqui, na camada de serviços, para não ficarem espalhadas.

Ciclo de vida de um empréstimo:

    SOLICITADO --(bibliotecário confirma retirada)--> ATIVO --(passa do prazo)--> ATRASADO
        |                                                |                              |
        +--(aluno cancela / bibliotecário recusa)        +-------(devolução)-----------+
                      v                                                  v
                  CANCELADO                                          DEVOLVIDO
"""
from datetime import date, datetime, timedelta

from flask import current_app

from models import db, Emprestimo, StatusEmprestimo


class RegraEmprestimoError(Exception):
    """Operação recusada por uma regra de negócio. A mensagem vai para o usuário."""


# ---------------------------------------------------------------------------
# Atrasos (RN46: ATIVO -> ATRASADO)
# ---------------------------------------------------------------------------
def atualizar_atrasos(hoje=None) -> int:
    """Marca como ATRASADO todo empréstimo ATIVO cujo prazo já passou.

    É chamada antes de cada consulta e verificação de empréstimos, então o
    status está sempre correto. No RF15, o agendador (APScheduler) vai chamar
    esta mesma função periodicamente para gerar as notificações.
    Retorna quantos empréstimos mudaram para ATRASADO.
    """
    hoje = hoje or date.today()
    vencidos = Emprestimo.query.filter(
        Emprestimo.status == StatusEmprestimo.ATIVO,
        Emprestimo.data_prevista_devolucao < hoje,
    ).all()
    for emprestimo in vencidos:
        emprestimo.status = StatusEmprestimo.ATRASADO
    if vencidos:
        db.session.commit()
    return len(vencidos)


def aluno_tem_atraso(aluno) -> bool:
    """RN41: o aluno tem algum empréstimo em atraso?"""
    atualizar_atrasos()
    return (
        Emprestimo.query.filter_by(aluno_id=aluno.id, status=StatusEmprestimo.ATRASADO).first()
        is not None
    )


def quantidade_em_uso(aluno) -> int:
    """Empréstimos do aluno que ocupam exemplar (solicitados, ativos ou atrasados)."""
    return Emprestimo.query.filter(
        Emprestimo.aluno_id == aluno.id,
        Emprestimo.status.in_(StatusEmprestimo.OCUPAM_EXEMPLAR),
    ).count()


# ---------------------------------------------------------------------------
# Solicitação pelo aluno (RF13, passos 1 e 2)
# ---------------------------------------------------------------------------
def motivo_para_nao_solicitar(aluno, livro):
    """Retorna o motivo pelo qual o aluno NÃO pode pedir o livro, ou None se pode.

    Usada na tela (para mostrar o aviso no lugar do botão) e na hora de
    solicitar (para recusar), garantindo que as duas sigam a mesma regra.
    """
    if aluno_tem_atraso(aluno):  # RN41 / CA02
        return "Você possui empréstimo em atraso. Devolva o livro atrasado para poder pegar outro."

    ja_pediu = Emprestimo.query.filter(
        Emprestimo.aluno_id == aluno.id,
        Emprestimo.livro_id == livro.id,
        Emprestimo.status.in_(StatusEmprestimo.OCUPAM_EXEMPLAR),
    ).first()
    if ja_pediu:
        return "Você já possui uma solicitação ou empréstimo em andamento deste livro."

    limite = current_app.config["MAX_EMPRESTIMOS_POR_ALUNO"]
    if quantidade_em_uso(aluno) >= limite:  # RN44
        return f"Você atingiu o limite de {limite} empréstimos simultâneos."

    if livro.exemplares_disponiveis() <= 0:  # RN42 / CA03
        return "Não há exemplares disponíveis deste livro no momento."

    return None


def solicitar(aluno, livro) -> Emprestimo:
    motivo = motivo_para_nao_solicitar(aluno, livro)
    if motivo:
        raise RegraEmprestimoError(motivo)

    emprestimo = Emprestimo(aluno_id=aluno.id, livro_id=livro.id, status=StatusEmprestimo.SOLICITADO)
    db.session.add(emprestimo)
    db.session.commit()
    return emprestimo


def cancelar_solicitacao(emprestimo, aluno) -> None:
    """O aluno desiste de uma solicitação que ainda não foi retirada."""
    if emprestimo.aluno_id != aluno.id:
        raise PermissionError("A solicitação não pertence a este aluno.")
    if emprestimo.status != StatusEmprestimo.SOLICITADO:
        raise RegraEmprestimoError("Só é possível cancelar solicitações que ainda não foram retiradas.")
    emprestimo.status = StatusEmprestimo.CANCELADO
    db.session.commit()


# ---------------------------------------------------------------------------
# Confirmação da retirada pelo bibliotecário (RF13, passos 3 a 5)
# ---------------------------------------------------------------------------
def confirmar_retirada(emprestimo, bibliotecario) -> None:
    if emprestimo.status != StatusEmprestimo.SOLICITADO:
        raise RegraEmprestimoError("Esta solicitação não está mais aguardando retirada.")

    # A situação do aluno pode ter mudado desde a solicitação (RN41)
    if aluno_tem_atraso(emprestimo.aluno):
        raise RegraEmprestimoError(
            "O aluno possui empréstimo em atraso e não pode retirar outro livro até devolvê-lo."
        )

    agora = datetime.now()
    prazo = current_app.config["PRAZO_DEVOLUCAO_DIAS"]
    emprestimo.status = StatusEmprestimo.ATIVO  # RN45
    emprestimo.data_emprestimo = agora
    emprestimo.data_prevista_devolucao = agora.date() + timedelta(days=prazo)  # RN43
    emprestimo.bibliotecario_id = bibliotecario.id
    db.session.commit()


def recusar_solicitacao(emprestimo, bibliotecario) -> None:
    """O bibliotecário recusa a solicitação (ex.: o aluno não foi retirar)."""
    if emprestimo.status != StatusEmprestimo.SOLICITADO:
        raise RegraEmprestimoError("Esta solicitação não está mais aguardando retirada.")
    emprestimo.status = StatusEmprestimo.CANCELADO
    emprestimo.bibliotecario_id = bibliotecario.id
    db.session.commit()


# ---------------------------------------------------------------------------
# Devolução (RF14)
# ---------------------------------------------------------------------------
def registrar_devolucao(emprestimo, bibliotecario) -> None:
    # RN46 / RN47 / CA03: só ATIVO ou ATRASADO podem virar DEVOLVIDO
    if emprestimo.status not in StatusEmprestimo.EM_ANDAMENTO:
        raise RegraEmprestimoError("Só é possível registrar a devolução de empréstimos ativos ou atrasados.")

    emprestimo.status = StatusEmprestimo.DEVOLVIDO
    emprestimo.data_devolucao = datetime.now()  # RN48: data registrada automaticamente
    emprestimo.bibliotecario_devolucao_id = bibliotecario.id
    db.session.commit()
