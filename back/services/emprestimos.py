from datetime import date, datetime, timedelta

from flask import current_app

from models import db, Emprestimo, StatusEmprestimo


class RegraEmprestimoError(Exception):
    pass


def atualizar_atrasos(hoje=None) -> int:
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
    atualizar_atrasos()
    return (
        Emprestimo.query.filter_by(aluno_id=aluno.id, status=StatusEmprestimo.ATRASADO).first()
        is not None
    )


def quantidade_em_uso(aluno) -> int:
    return Emprestimo.query.filter(
        Emprestimo.aluno_id == aluno.id,
        Emprestimo.status.in_(StatusEmprestimo.OCUPAM_EXEMPLAR),
    ).count()


def motivo_para_nao_solicitar(aluno, livro):
    if aluno_tem_atraso(aluno):
        return "Você possui empréstimo em atraso. Devolva o livro atrasado para poder pegar outro."

    ja_pediu = Emprestimo.query.filter(
        Emprestimo.aluno_id == aluno.id,
        Emprestimo.livro_id == livro.id,
        Emprestimo.status.in_(StatusEmprestimo.OCUPAM_EXEMPLAR),
    ).first()
    if ja_pediu:
        return "Você já possui uma solicitação ou empréstimo em andamento deste livro."

    limite = current_app.config["MAX_EMPRESTIMOS_POR_ALUNO"]
    if quantidade_em_uso(aluno) >= limite:
        return f"Você atingiu o limite de {limite} empréstimos simultâneos."

    if livro.exemplares_disponiveis() <= 0:
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
    if emprestimo.aluno_id != aluno.id:
        raise PermissionError("A solicitação não pertence a este aluno.")
    if emprestimo.status != StatusEmprestimo.SOLICITADO:
        raise RegraEmprestimoError("Só é possível cancelar solicitações que ainda não foram retiradas.")
    emprestimo.status = StatusEmprestimo.CANCELADO
    db.session.commit()


def confirmar_retirada(emprestimo, bibliotecario) -> None:
    if emprestimo.status != StatusEmprestimo.SOLICITADO:
        raise RegraEmprestimoError("Esta solicitação não está mais aguardando retirada.")

    if aluno_tem_atraso(emprestimo.aluno):
        raise RegraEmprestimoError(
            "O aluno possui empréstimo em atraso e não pode retirar outro livro até devolvê-lo."
        )

    agora = datetime.now()
    prazo = current_app.config["PRAZO_DEVOLUCAO_DIAS"]
    emprestimo.status = StatusEmprestimo.ATIVO
    emprestimo.data_emprestimo = agora
    emprestimo.data_prevista_devolucao = agora.date() + timedelta(days=prazo)
    emprestimo.bibliotecario_id = bibliotecario.id
    db.session.commit()


def recusar_solicitacao(emprestimo, bibliotecario) -> None:
    if emprestimo.status != StatusEmprestimo.SOLICITADO:
        raise RegraEmprestimoError("Esta solicitação não está mais aguardando retirada.")
    emprestimo.status = StatusEmprestimo.CANCELADO
    emprestimo.bibliotecario_id = bibliotecario.id
    db.session.commit()


def registrar_devolucao(emprestimo, bibliotecario) -> None:
    if emprestimo.status not in StatusEmprestimo.EM_ANDAMENTO:
        raise RegraEmprestimoError("Só é possível registrar a devolução de empréstimos ativos ou atrasados.")

    emprestimo.status = StatusEmprestimo.DEVOLVIDO
    emprestimo.data_devolucao = datetime.now()
    emprestimo.bibliotecario_devolucao_id = bibliotecario.id
    db.session.commit()
