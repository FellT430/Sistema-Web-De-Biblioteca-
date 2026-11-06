"""Dados do painel do bibliotecário (perfil admin).

Todas as consultas ficam aqui, na camada de serviços, e o controller só
repassa o resultado para o template. Os agrupamentos por mês são feitos em
Python para funcionar igual no SQLite e no MySQL.
"""
from datetime import date

from sqlalchemy import func

from models import db, Emprestimo, StatusEmprestimo, Livro
from services.emprestimos import atualizar_atrasos

TOP_LIVROS = 5
MESES_GRAFICO = 6
MAX_ATRASOS_NA_TABELA = 10

NOMES_MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _contar_por_status(status) -> int:
    return Emprestimo.query.filter(Emprestimo.status == status).count()


def _livros_mais_emprestados(limite=TOP_LIVROS):
    """Livros com mais empréstimos efetivados (solicitações canceladas não contam)."""
    linhas = (
        db.session.query(Livro.titulo, func.count(Emprestimo.id).label("total"))
        .join(Emprestimo, Emprestimo.livro_id == Livro.id)
        .filter(Emprestimo.status != StatusEmprestimo.CANCELADO)
        .group_by(Livro.id, Livro.titulo)
        .order_by(func.count(Emprestimo.id).desc(), Livro.titulo)
        .limit(limite)
        .all()
    )
    return [{"rotulo": titulo, "valor": total} for titulo, total in linhas]


def _ultimos_meses(quantidade, hoje):
    """Lista de (ano, mes) dos últimos `quantidade` meses, do mais antigo ao atual."""
    meses = []
    ano, mes = hoje.year, hoje.month
    for _ in range(quantidade):
        meses.append((ano, mes))
        mes -= 1
        if mes == 0:
            ano, mes = ano - 1, 12
    return list(reversed(meses))


def _emprestimos_por_mes(hoje, quantidade=MESES_GRAFICO):
    meses = _ultimos_meses(quantidade, hoje)
    inicio = date(meses[0][0], meses[0][1], 1)

    datas = (
        db.session.query(Emprestimo.data_emprestimo)
        .filter(Emprestimo.data_emprestimo.isnot(None), Emprestimo.data_emprestimo >= inicio)
        .all()
    )
    contagem = {mes: 0 for mes in meses}
    for (data,) in datas:
        chave = (data.year, data.month)
        if chave in contagem:
            contagem[chave] += 1

    return [{"rotulo": NOMES_MESES[mes - 1], "valor": contagem[(ano, mes)]} for ano, mes in meses]


def _atrasos(hoje, limite=MAX_ATRASOS_NA_TABELA):
    emprestimos = (
        Emprestimo.query.filter(Emprestimo.status == StatusEmprestimo.ATRASADO)
        .order_by(Emprestimo.data_prevista_devolucao)
        .limit(limite)
        .all()
    )
    return [
        {
            "aluno": e.aluno.nome,
            "livro": e.livro.titulo,
            "prazo": e.data_prevista_devolucao,
            "dias_atraso": e.dias_atraso(hoje),
        }
        for e in emprestimos
    ]


def _com_proporcao(itens):
    """Acrescenta a cada item a largura (0 a 100) da barra, relativa ao maior valor."""
    maior = max((item["valor"] for item in itens), default=0)
    for item in itens:
        item["percentual"] = round(item["valor"] * 100 / maior) if maior else 0
    return itens


def montar_painel(hoje=None) -> dict:
    hoje = hoje or date.today()
    atualizar_atrasos(hoje)  # garante que ATIVO vencido apareça como ATRASADO

    total_exemplares = db.session.query(func.coalesce(func.sum(Livro.quantidade), 0)).scalar()

    return {
        "data_atualizacao": hoje,
        "total_titulos": Livro.query.count(),
        "total_exemplares": int(total_exemplares),
        "em_andamento": _contar_por_status(StatusEmprestimo.ATIVO),
        "atrasados": _contar_por_status(StatusEmprestimo.ATRASADO),
        "aguardando_retirada": _contar_por_status(StatusEmprestimo.SOLICITADO),
        "mais_emprestados": _com_proporcao(_livros_mais_emprestados()),
        "por_mes": _com_proporcao(_emprestimos_por_mes(hoje)),
        "atrasos": _atrasos(hoje),
    }
