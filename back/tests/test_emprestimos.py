"""Testes das regras de empréstimo e devolução (services/emprestimos.py)."""
from datetime import date, timedelta

import pytest

from models import db, StatusEmprestimo
from services import emprestimos
from services.emprestimos import RegraEmprestimoError


def test_aluno_solicita_livro_disponivel(app, fabrica):
    aluno, livro = fabrica.usuario(), fabrica.livro(quantidade=2)
    emprestimo = emprestimos.solicitar(aluno, livro)
    assert emprestimo.status == StatusEmprestimo.SOLICITADO
    assert livro.exemplares_disponiveis() == 1


def test_aluno_com_atraso_nao_pode_solicitar(app, fabrica):
    aluno = fabrica.usuario()
    fabrica.emprestimo(aluno, fabrica.livro(), prazo=date.today() - timedelta(days=1))
    with pytest.raises(RegraEmprestimoError, match="atraso"):
        emprestimos.solicitar(aluno, fabrica.livro(quantidade=3))


def test_nao_pode_pedir_o_mesmo_livro_duas_vezes(app, fabrica):
    aluno, livro = fabrica.usuario(), fabrica.livro(quantidade=3)
    emprestimos.solicitar(aluno, livro)
    with pytest.raises(RegraEmprestimoError, match="já possui"):
        emprestimos.solicitar(aluno, livro)


def test_limite_de_emprestimos_simultaneos(app, fabrica):
    aluno = fabrica.usuario()
    limite = app.config["MAX_EMPRESTIMOS_POR_ALUNO"]
    for _ in range(limite):
        emprestimos.solicitar(aluno, fabrica.livro())
    assert emprestimos.quantidade_em_uso(aluno) == limite
    with pytest.raises(RegraEmprestimoError, match="limite"):
        emprestimos.solicitar(aluno, fabrica.livro())


def test_livro_sem_exemplares_nao_pode_ser_solicitado(app, fabrica):
    livro = fabrica.livro(quantidade=1)
    emprestimos.solicitar(fabrica.usuario(), livro)
    with pytest.raises(RegraEmprestimoError, match="Não há exemplares"):
        emprestimos.solicitar(fabrica.usuario(), livro)


def test_confirmar_retirada_define_prazo_de_7_dias(app, fabrica):
    aluno, livro, bib = fabrica.usuario(), fabrica.livro(), fabrica.usuario("admin")
    emprestimo = emprestimos.solicitar(aluno, livro)
    emprestimos.confirmar_retirada(emprestimo, bib)
    assert emprestimo.status == StatusEmprestimo.ATIVO
    assert emprestimo.data_prevista_devolucao == date.today() + timedelta(days=7)
    assert emprestimo.bibliotecario_id == bib.id


def test_confirmar_retirada_so_de_solicitacao(app, fabrica):
    emprestimo = fabrica.emprestimo(fabrica.usuario(), fabrica.livro())  
    with pytest.raises(RegraEmprestimoError):
        emprestimos.confirmar_retirada(emprestimo, fabrica.usuario("admin"))


def test_nao_confirma_retirada_de_aluno_com_atraso(app, fabrica):
    aluno = fabrica.usuario()
    pedido = emprestimos.solicitar(aluno, fabrica.livro())
    fabrica.emprestimo(aluno, fabrica.livro(), prazo=date.today() - timedelta(days=2))
    with pytest.raises(RegraEmprestimoError, match="atraso"):
        emprestimos.confirmar_retirada(pedido, fabrica.usuario("admin"))


def test_aluno_cancela_a_propria_solicitacao(app, fabrica):
    aluno, livro = fabrica.usuario(), fabrica.livro()
    pedido = emprestimos.solicitar(aluno, livro)
    emprestimos.cancelar_solicitacao(pedido, aluno)
    assert pedido.status == StatusEmprestimo.CANCELADO
    assert livro.exemplares_disponiveis() == 1


def test_aluno_nao_cancela_solicitacao_de_outro(app, fabrica):
    pedido = emprestimos.solicitar(fabrica.usuario(), fabrica.livro())
    with pytest.raises(PermissionError):
        emprestimos.cancelar_solicitacao(pedido, fabrica.usuario())


def test_nao_cancela_emprestimo_ja_retirado(app, fabrica):
    aluno = fabrica.usuario()
    emprestimo = fabrica.emprestimo(aluno, fabrica.livro())
    with pytest.raises(RegraEmprestimoError):
        emprestimos.cancelar_solicitacao(emprestimo, aluno)


def test_bibliotecario_recusa_solicitacao(app, fabrica):
    pedido = emprestimos.solicitar(fabrica.usuario(), fabrica.livro())
    emprestimos.recusar_solicitacao(pedido, fabrica.usuario("admin"))
    assert pedido.status == StatusEmprestimo.CANCELADO
    with pytest.raises(RegraEmprestimoError):
        emprestimos.recusar_solicitacao(pedido, fabrica.usuario("admin"))


def test_registrar_devolucao(app, fabrica):
    livro = fabrica.livro()
    emprestimo = fabrica.emprestimo(fabrica.usuario(), livro)
    emprestimos.registrar_devolucao(emprestimo, fabrica.usuario("admin"))
    assert emprestimo.status == StatusEmprestimo.DEVOLVIDO
    assert emprestimo.data_devolucao is not None
    assert livro.exemplares_disponiveis() == 1


def test_nao_registra_devolucao_de_solicitacao(app, fabrica):
    pedido = emprestimos.solicitar(fabrica.usuario(), fabrica.livro())
    with pytest.raises(RegraEmprestimoError):
        emprestimos.registrar_devolucao(pedido, fabrica.usuario("admin"))


def test_atualizar_atrasos_marca_somente_vencidos(app, fabrica):
    hoje = date.today()
    vencido = fabrica.emprestimo(fabrica.usuario(), fabrica.livro(), prazo=hoje - timedelta(days=1))
    no_dia = fabrica.emprestimo(fabrica.usuario(), fabrica.livro(), prazo=hoje)
    assert emprestimos.atualizar_atrasos(hoje) == 1
    db.session.refresh(vencido)
    db.session.refresh(no_dia)
    assert vencido.status == StatusEmprestimo.ATRASADO
    assert no_dia.status == StatusEmprestimo.ATIVO  
