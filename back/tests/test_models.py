"""Testes das classes de domínio (models)."""
from datetime import date, datetime, timedelta

from models import (
    db, StatusCadastro, StatusEmprestimo, Reserva, StatusReserva, Notificacao, TipoNotificacao,
    CodigoRecuperacao,
)


# ---------------------------------------------------------------- Usuario
def test_senha_e_guardada_em_hash_e_conferida(app, fabrica):
    usuario = fabrica.usuario(senha="MinhaSenha1")
    assert usuario.senha_hash != "MinhaSenha1"
    assert usuario.checar_senha("MinhaSenha1")
    assert not usuario.checar_senha("senha-errada")


def test_propriedades_do_usuario(app, fabrica):
    aluno = fabrica.usuario("aluno")
    admin = fabrica.usuario("superadmin")
    pendente = fabrica.usuario("professor", status=StatusCadastro.AGUARDANDO_APROVACAO)

    assert aluno.aprovado and aluno.perfil_nome == "Aluno"
    assert admin.is_superadmin and not aluno.is_superadmin
    assert not pendente.aprovado
    assert pendente.status_cadastro_nome
    assert not aluno.anonimizado and not aluno.exclusao_pendente

    aluno.exclusao_solicitada_em = datetime.now()
    assert aluno.exclusao_pendente
    aluno.anonimizado_em = datetime.now()
    assert aluno.anonimizado and not aluno.exclusao_pendente


# ---------------------------------------------------------------- Livro
def test_exemplares_disponiveis_desconta_emprestimos_em_andamento(app, fabrica):
    livro = fabrica.livro(quantidade=3)
    a1, a2, a3 = fabrica.usuario(), fabrica.usuario(), fabrica.usuario()
    fabrica.emprestimo(a1, livro, StatusEmprestimo.SOLICITADO)
    fabrica.emprestimo(a2, livro, StatusEmprestimo.ATIVO)
    fabrica.emprestimo(a3, livro, StatusEmprestimo.DEVOLVIDO)  # devolvido não ocupa
    db.session.refresh(livro)
    assert livro.exemplares_disponiveis() == 1


def test_exemplares_disponiveis_nunca_fica_negativo(app, fabrica):
    livro = fabrica.livro(quantidade=1)
    fabrica.emprestimo(fabrica.usuario(), livro, StatusEmprestimo.ATIVO)
    fabrica.emprestimo(fabrica.usuario(), livro, StatusEmprestimo.ATRASADO)
    db.session.refresh(livro)
    assert livro.exemplares_disponiveis() == 0


def test_reservas_na_fila_conta_so_aguardando(app, fabrica):
    livro = fabrica.livro()
    db.session.add_all([
        Reserva(aluno_id=fabrica.usuario().id, livro_id=livro.id, status=StatusReserva.AGUARDANDO),
        Reserva(aluno_id=fabrica.usuario().id, livro_id=livro.id, status=StatusReserva.CANCELADA),
    ])
    db.session.commit()
    assert livro.reservas_na_fila() == 1


# ---------------------------------------------------------------- Emprestimo
def test_emprestimo_atrasado_e_dias_de_atraso(app, fabrica):
    livro, aluno = fabrica.livro(), fabrica.usuario()
    hoje = date.today()
    emprestimo = fabrica.emprestimo(aluno, livro, prazo=hoje - timedelta(days=3))
    assert emprestimo.esta_atrasado(hoje)
    assert emprestimo.dias_atraso(hoje) == 3


def test_emprestimo_no_dia_do_vencimento_nao_esta_atrasado(app, fabrica):
    hoje = date.today()
    emprestimo = fabrica.emprestimo(fabrica.usuario(), fabrica.livro(), prazo=hoje)
    assert not emprestimo.esta_atrasado(hoje)
    assert emprestimo.dias_atraso(hoje) == 0


def test_devolvido_com_atraso_usa_a_data_da_devolucao(app, fabrica):
    prazo = date.today() - timedelta(days=5)
    devolvido = datetime.combine(prazo + timedelta(days=2), datetime.min.time())
    emprestimo = fabrica.emprestimo(fabrica.usuario(), fabrica.livro(), StatusEmprestimo.DEVOLVIDO,
                                    prazo=prazo, devolvido_em=devolvido)
    assert emprestimo.dias_atraso() == 2
    assert emprestimo.devolvido_com_atraso


def test_solicitado_sem_prazo_nao_tem_atraso(app, fabrica):
    emprestimo = fabrica.emprestimo(fabrica.usuario(), fabrica.livro(), StatusEmprestimo.SOLICITADO)
    assert emprestimo.dias_atraso() == 0
    assert not emprestimo.esta_atrasado()


# ---------------------------------------------------------------- Reserva
def test_posicao_na_fila_segue_ordem_de_chegada(app, fabrica):
    livro = fabrica.livro()
    agora = datetime.now()
    primeira = Reserva(aluno_id=fabrica.usuario().id, livro_id=livro.id, criada_em=agora - timedelta(minutes=5))
    segunda = Reserva(aluno_id=fabrica.usuario().id, livro_id=livro.id, criada_em=agora)
    db.session.add_all([primeira, segunda])
    db.session.commit()
    assert primeira.posicao_na_fila() == 1
    assert segunda.posicao_na_fila() == 2

    primeira.status = StatusReserva.CANCELADA
    db.session.commit()
    assert primeira.posicao_na_fila() is None
    assert segunda.posicao_na_fila() == 1


# ---------------------------------------------------------------- Notificacao e CodigoRecuperacao
def test_marcar_notificacao_como_lida(app, fabrica):
    aluno = fabrica.usuario()
    notificacao = Notificacao(usuario_id=aluno.id, tipo=TipoNotificacao.ATRASO, mensagem="x")
    db.session.add(notificacao)
    db.session.commit()
    assert not notificacao.lida
    notificacao.marcar_como_lida()
    assert notificacao.lida


def test_codigo_de_recuperacao_disponivel_ate_ser_usado(app, fabrica):
    codigo = CodigoRecuperacao(usuario_id=fabrica.usuario().id, codigo_hash="hash")
    assert codigo.disponivel
    codigo.usado_em = datetime.now()
    assert not codigo.disponivel
