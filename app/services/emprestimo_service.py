"""Regras de negócio de empréstimo/devolução de exemplares.

Toda a validação de disponibilidade vive aqui, e não nas rotas, para que
qualquer forma de acesso (formulário web, script, chamada direta) passe
pela mesma checagem no back-end. As rotas nunca alteram `Exemplar.status`
diretamente - sempre chamam `registrar_emprestimo` / `registrar_devolucao`.
"""
from datetime import date, datetime

from app.extensions import db
from app.models import Emprestimo, Exemplar, StatusEmprestimo, StatusExemplar, Usuario


class EmprestimoError(Exception):
    """Erro genérico de regra de negócio de empréstimo."""


class ExemplarIndisponivelError(EmprestimoError):
    pass


class ExemplarNaoEncontradoError(EmprestimoError):
    pass


class UsuarioNaoEncontradoError(EmprestimoError):
    pass


class UsuarioComAtrasoError(EmprestimoError):
    pass


class EmprestimoNaoEncontradoError(EmprestimoError):
    pass


class EmprestimoJaDevolvidoError(EmprestimoError):
    pass


def usuario_possui_atraso(usuario_id):
    """True se o usuário tem algum empréstimo marcado como atrasado e ainda não devolvido."""
    return (
        Emprestimo.query.filter_by(usuario_id=usuario_id, status=StatusEmprestimo.ATRASADO)
        .filter(Emprestimo.data_devolucao.is_(None))
        .first()
        is not None
    )


def listar_emprestimos_atrasados():
    """Empréstimos atualmente atrasados (não devolvidos), usado para avisos no front-end."""
    return (
        Emprestimo.query.filter_by(status=StatusEmprestimo.ATRASADO)
        .filter(Emprestimo.data_devolucao.is_(None))
        .order_by(Emprestimo.data_prevista_devolucao)
        .all()
    )


def registrar_emprestimo(exemplar_id, usuario_id, dias_para_devolucao=None):
    """Cria um empréstimo somente se o exemplar estiver disponível E o usuário
    não tiver nenhuma devolução em atraso pendente.

    As duas regras são independentes uma da outra e ambas são checadas dentro
    da mesma transação: primeiro se confirma que o usuário não está bloqueado
    por atraso (uma regra sobre o tomador do empréstimo), depois se confirma
    e trava a disponibilidade do exemplar (uma regra sobre o item). Qualquer
    uma das duas falhando cancela a operação inteira - nenhuma alteração é
    persistida a menos que ambas passem.

    A leitura do exemplar usa SELECT ... FOR UPDATE (via with_for_update),
    e a checagem de status + criação do Emprestimo + atualização do
    Exemplar.status acontecem na mesma transação, confirmada com um único
    commit. Isso evita tanto a burla via requisição direta (a validação é
    sempre refeita aqui, no servidor) quanto a condição de corrida em que
    duas requisições simultâneas tentam emprestar o mesmo exemplar.
    """
    try:
        usuario = Usuario.query.get(usuario_id)
        if usuario is None:
            raise UsuarioNaoEncontradoError("Usuário não encontrado.")

        if usuario_possui_atraso(usuario.id):
            raise UsuarioComAtrasoError(
                "Você possui uma devolução em atraso. Regularize antes de "
                "realizar um novo empréstimo."
            )

        exemplar = (
            Exemplar.query.filter_by(id=exemplar_id).with_for_update().first()
        )
        if exemplar is None:
            raise ExemplarNaoEncontradoError("Exemplar não encontrado.")

        if exemplar.status != StatusExemplar.DISPONIVEL:
            raise ExemplarIndisponivelError("Este exemplar já está emprestado.")

        data_prevista = (
            Emprestimo.calcular_data_prevista(dias_para_devolucao)
            if dias_para_devolucao
            else Emprestimo.calcular_data_prevista()
        )

        emprestimo = Emprestimo(
            exemplar_id=exemplar.id,
            usuario_id=usuario.id,
            data_emprestimo=datetime.utcnow(),
            data_prevista_devolucao=data_prevista,
            data_devolucao=None,
            status=StatusEmprestimo.EM_DIA,
        )
        exemplar.status = StatusExemplar.EMPRESTADO

        db.session.add(emprestimo)
        db.session.commit()
        return emprestimo
    except EmprestimoError:
        db.session.rollback()
        raise
    except Exception:
        db.session.rollback()
        raise


def registrar_devolucao(emprestimo_id):
    """Marca o empréstimo como devolvido e libera o exemplar.

    Assim como no empréstimo, a atualização de `data_devolucao` e de
    `Exemplar.status` acontece na mesma transação/commit, garantindo que
    nunca fiquem inconsistentes entre si.
    """
    try:
        emprestimo = (
            Emprestimo.query.filter_by(id=emprestimo_id).with_for_update().first()
        )
        if emprestimo is None:
            raise EmprestimoNaoEncontradoError("Empréstimo não encontrado.")

        if emprestimo.data_devolucao is not None:
            raise EmprestimoJaDevolvidoError("Este empréstimo já foi devolvido.")

        exemplar = (
            Exemplar.query.filter_by(id=emprestimo.exemplar_id)
            .with_for_update()
            .first()
        )
        if exemplar is None:
            raise ExemplarNaoEncontradoError("Exemplar não encontrado.")

        emprestimo.data_devolucao = datetime.utcnow()
        exemplar.status = StatusExemplar.DISPONIVEL

        db.session.commit()
        return emprestimo
    except EmprestimoError:
        db.session.rollback()
        raise
    except Exception:
        db.session.rollback()
        raise


def marcar_emprestimos_atrasados():
    """Varre os empréstimos "em_dia" cuja devolução prevista já passou e ainda
    não foram devolvidos, e marca cada um como "atrasado".

    É a função chamada pelo job do APScheduler (ver `app/scheduler.py`), mas
    não depende dele: pode ser chamada manualmente (ex: em testes, ou por um
    comando de administração) para forçar a verificação imediatamente.
    Retorna a quantidade de empréstimos atualizados.
    """
    try:
        hoje = date.today()
        quantidade = (
            Emprestimo.query.filter(
                Emprestimo.status == StatusEmprestimo.EM_DIA,
                Emprestimo.data_devolucao.is_(None),
                Emprestimo.data_prevista_devolucao < hoje,
            ).update(
                {Emprestimo.status: StatusEmprestimo.ATRASADO},
                synchronize_session=False,
            )
        )
        db.session.commit()
        return quantidade
    except Exception:
        db.session.rollback()
        raise
