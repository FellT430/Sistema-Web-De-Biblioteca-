"""Testes da fila de reservas (services/reservas.py)."""
from datetime import date, datetime, timedelta

import pytest

from models import db, StatusEmprestimo, StatusReserva, Notificacao, TipoNotificacao
from services import emprestimos, reservas
from services.reservas import RegraReservaError


def _livro_esgotado(fabrica):
    """Livro com 1 exemplar já emprestado para outro aluno."""
    livro = fabrica.livro(quantidade=1)
    portador = fabrica.usuario()
    emprestimo = fabrica.emprestimo(portador, livro)
    db.session.refresh(livro)
    return livro, emprestimo


def test_reserva_so_quando_nao_ha_exemplar(app, fabrica):
    livro = fabrica.livro(quantidade=2)
    with pytest.raises(RegraReservaError, match="exemplares disponíveis"):
        reservas.criar_reserva(fabrica.usuario(), livro)


def test_aluno_entra_na_fila(app, fabrica):
    livro, _ = _livro_esgotado(fabrica)
    reserva = reservas.criar_reserva(fabrica.usuario(), livro)
    assert reserva.status == StatusReserva.AGUARDANDO
    assert reserva.posicao_na_fila() == 1
    assert livro.reservas_na_fila() == 1


def test_aluno_com_atraso_nao_reserva(app, fabrica):
    livro, _ = _livro_esgotado(fabrica)
    aluno = fabrica.usuario()
    fabrica.emprestimo(aluno, fabrica.livro(), prazo=date.today() - timedelta(days=1))
    with pytest.raises(RegraReservaError, match="atraso"):
        reservas.criar_reserva(aluno, livro)


def test_nao_reserva_duas_vezes_o_mesmo_livro(app, fabrica):
    livro, _ = _livro_esgotado(fabrica)
    aluno = fabrica.usuario()
    reservas.criar_reserva(aluno, livro)
    with pytest.raises(RegraReservaError, match="já tem uma reserva"):
        reservas.criar_reserva(aluno, livro)


def test_quem_esta_com_o_livro_nao_reserva_ele(app, fabrica):
    livro, emprestimo = _livro_esgotado(fabrica)
    with pytest.raises(RegraReservaError, match="já possui"):
        reservas.criar_reserva(emprestimo.aluno, livro)


def test_limite_de_reservas_ativas(app, fabrica):
    aluno = fabrica.usuario()
    for _ in range(app.config["MAX_RESERVAS_POR_ALUNO"]):
        reservas.criar_reserva(aluno, _livro_esgotado(fabrica)[0])
    with pytest.raises(RegraReservaError, match="limite"):
        reservas.criar_reserva(aluno, _livro_esgotado(fabrica)[0])


def test_aluno_cancela_reserva(app, fabrica):
    livro, _ = _livro_esgotado(fabrica)
    aluno = fabrica.usuario()
    reserva = reservas.criar_reserva(aluno, livro)
    reservas.cancelar_reserva(reserva, aluno)
    assert reserva.status == StatusReserva.CANCELADA
    with pytest.raises(RegraReservaError):
        reservas.cancelar_reserva(reserva, aluno)


def test_nao_cancela_reserva_de_outro_aluno(app, fabrica):
    livro, _ = _livro_esgotado(fabrica)
    reserva = reservas.criar_reserva(fabrica.usuario(), livro)
    with pytest.raises(PermissionError):
        reservas.cancelar_reserva(reserva, fabrica.usuario())


def test_devolucao_atende_o_primeiro_da_fila(app, fabrica):
    livro, emprestimo = _livro_esgotado(fabrica)
    primeiro, segundo = fabrica.usuario(), fabrica.usuario()
    r1 = reservas.criar_reserva(primeiro, livro)
    r2 = reservas.criar_reserva(segundo, livro)

    emprestimos.registrar_devolucao(emprestimo, fabrica.usuario("admin"))

    db.session.refresh(r1)
    db.session.refresh(r2)
    assert r1.status == StatusReserva.ATENDIDA
    assert r1.emprestimo.status == StatusEmprestimo.SOLICITADO
    assert r1.emprestimo.aluno_id == primeiro.id
    assert r2.status == StatusReserva.AGUARDANDO and r2.posicao_na_fila() == 1
    aviso = Notificacao.query.filter_by(usuario_id=primeiro.id).first()
    assert aviso.tipo == TipoNotificacao.RESERVA_DISPONIVEL


def test_fila_pula_aluno_com_atraso(app, fabrica):
    livro, emprestimo = _livro_esgotado(fabrica)
    atrasado, proximo = fabrica.usuario(), fabrica.usuario()
    r1 = reservas.criar_reserva(atrasado, livro)
    r2 = reservas.criar_reserva(proximo, livro)
    # depois de reservar, o primeiro da fila fica com outro livro atrasado
    fabrica.emprestimo(atrasado, fabrica.livro(), prazo=date.today() - timedelta(days=1))

    emprestimos.registrar_devolucao(emprestimo, fabrica.usuario("admin"))

    db.session.refresh(r1)
    db.session.refresh(r2)
    assert r1.status == StatusReserva.CANCELADA
    assert r2.status == StatusReserva.ATENDIDA


def test_reserva_nao_retirada_expira_e_passa_para_o_proximo(app, fabrica):
    livro, emprestimo = _livro_esgotado(fabrica)
    primeiro, segundo = fabrica.usuario(), fabrica.usuario()
    r1 = reservas.criar_reserva(primeiro, livro)
    r2 = reservas.criar_reserva(segundo, livro)
    emprestimos.registrar_devolucao(emprestimo, fabrica.usuario("admin"))
    db.session.refresh(r1)

    prazo = app.config["PRAZO_RETIRADA_RESERVA_DIAS"]
    resultado = reservas.expirar_reservas(hoje=date.today() + timedelta(days=prazo + 1))

    db.session.refresh(r1)
    db.session.refresh(r2)
    assert resultado["expiradas"] == 1 and resultado["atendidas"] == 1
    assert r1.status == StatusReserva.EXPIRADA
    assert r1.emprestimo.status == StatusEmprestimo.CANCELADO
    assert r2.status == StatusReserva.ATENDIDA


def test_reserva_dentro_do_prazo_nao_expira(app, fabrica):
    livro, emprestimo = _livro_esgotado(fabrica)
    r1 = reservas.criar_reserva(fabrica.usuario(), livro)
    emprestimos.registrar_devolucao(emprestimo, fabrica.usuario("admin"))
    resultado = reservas.expirar_reservas(hoje=date.today() + timedelta(days=1))
    db.session.refresh(r1)
    assert resultado["expiradas"] == 0
    assert r1.status == StatusReserva.ATENDIDA


def test_cancelar_solicitacao_tambem_libera_para_a_fila(app, fabrica):
    livro = fabrica.livro(quantidade=1)
    portador = fabrica.usuario()
    pedido = emprestimos.solicitar(portador, livro)
    reserva = reservas.criar_reserva(fabrica.usuario(), livro)
    emprestimos.cancelar_solicitacao(pedido, portador)
    db.session.refresh(reserva)
    assert reserva.status == StatusReserva.ATENDIDA
