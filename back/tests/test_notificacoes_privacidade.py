"""Testes das notificações automáticas e da exclusão de dados por anonimização (LGPD)."""
from datetime import date, datetime, timedelta

import pytest

from models import (
    db, Usuario, StatusEmprestimo, Notificacao, TipoNotificacao, Reserva, StatusReserva,
    LogAuditoria, CodigoRecuperacao,
)
from services import notificacoes, privacidade, codigos_recuperacao
from services.auditoria import registrar
from services.privacidade import RegraPrivacidadeError


def test_verificacao_gera_atraso_e_lembretes(app, fabrica):
    hoje = date.today()
    atrasado = fabrica.emprestimo(fabrica.usuario(), fabrica.livro(), prazo=hoje - timedelta(days=2))
    fabrica.emprestimo(fabrica.usuario(), fabrica.livro(), prazo=hoje)                      
    fabrica.emprestimo(fabrica.usuario(), fabrica.livro(), prazo=hoje + timedelta(days=1))  
    fabrica.emprestimo(fabrica.usuario(), fabrica.livro(), prazo=hoje + timedelta(days=5))  

    resumo = notificacoes.verificar_e_notificar(hoje)

    assert resumo["novos_atrasos"] == 1
    assert resumo["avisos_atraso"] == 1
    assert resumo["lembretes"] == 2
    db.session.refresh(atrasado)
    assert atrasado.status == StatusEmprestimo.ATRASADO


def test_mesmo_aviso_nao_se_repete_no_mesmo_dia(app, fabrica):
    hoje = date.today()
    fabrica.emprestimo(fabrica.usuario(), fabrica.livro(), prazo=hoje - timedelta(days=1))
    notificacoes.verificar_e_notificar(hoje)
    segunda = notificacoes.verificar_e_notificar(hoje)  
    assert segunda["avisos_atraso"] == 0
    assert Notificacao.query.filter_by(tipo=TipoNotificacao.ATRASO).count() == 1


def test_notificacao_de_devolucao_e_contador_de_nao_lidas(app, fabrica):
    aluno = fabrica.usuario()
    prazo = date.today() - timedelta(days=3)
    emprestimo = fabrica.emprestimo(aluno, fabrica.livro(), StatusEmprestimo.DEVOLVIDO,
                                    prazo=prazo, devolvido_em=datetime.now())
    notificacoes.notificar_devolucao(emprestimo)
    aviso = Notificacao.query.filter_by(usuario_id=aluno.id).one()
    assert aviso.tipo == TipoNotificacao.DEVOLUCAO_REGISTRADA
    assert "atraso" in aviso.mensagem
    assert notificacoes.nao_lidas(aluno) == 1


def test_falha_no_email_nao_interrompe_o_envio(app):
    def quebra():
        raise RuntimeError("servidor fora do ar")
    assert notificacoes._enviar_emails([quebra, lambda: True]) == 1


def test_aluno_solicita_exclusao(app, fabrica):
    aluno = fabrica.usuario()
    privacidade.solicitar_exclusao(aluno)
    assert aluno.exclusao_pendente
    assert aluno in privacidade.pendentes()
    with pytest.raises(RegraPrivacidadeError, match="já tem um pedido"):
        privacidade.solicitar_exclusao(aluno)


def test_aluno_com_livro_em_maos_nao_pode_pedir_exclusao(app, fabrica):
    aluno = fabrica.usuario()
    fabrica.emprestimo(aluno, fabrica.livro())
    with pytest.raises(RegraPrivacidadeError, match="Devolva os livros"):
        privacidade.solicitar_exclusao(aluno)


def test_administrador_nao_pode_pedir_exclusao(app, fabrica):
    with pytest.raises(RegraPrivacidadeError, match="Administrador"):
        privacidade.solicitar_exclusao(fabrica.usuario("superadmin"))


def test_admin_recusa_exclusao_com_motivo(app, fabrica):
    aluno, admin = fabrica.usuario(), fabrica.usuario("superadmin")
    privacidade.solicitar_exclusao(aluno)
    with pytest.raises(RegraPrivacidadeError, match="motivo"):
        privacidade.recusar_exclusao(aluno, "  ", admin)
    privacidade.recusar_exclusao(aluno, "Pendência na biblioteca", admin)
    assert not aluno.exclusao_pendente


def test_confirmar_exclusao_anonimiza_e_mantem_historico(app, fabrica):
    aluno = fabrica.usuario(nome="Maria Silva", email="maria@aluno.com")
    admin = fabrica.usuario("superadmin")
    devolvido = fabrica.emprestimo(aluno, fabrica.livro(), StatusEmprestimo.DEVOLVIDO,
                                   devolvido_em=datetime.now())
    codigos_recuperacao.gerar(aluno)
    registrar("LOGIN_SUCESSO", "Login de maria@aluno.com", usuario=aluno)
    privacidade.solicitar_exclusao(aluno)

    privacidade.confirmar_exclusao(aluno, admin)

    db.session.refresh(aluno)
    assert aluno.nome == privacidade.NOME_ANONIMIZADO
    assert aluno.email.endswith("@" + privacidade.DOMINIO_ANONIMIZADO)
    assert not aluno.ativo and aluno.anonimizado
    assert not aluno.checar_senha("Senha@123")
    assert CodigoRecuperacao.query.filter_by(usuario_id=aluno.id).count() == 0
    assert Notificacao.query.filter_by(usuario_id=aluno.id).count() == 0
 
    assert db.session.get(type(devolvido), devolvido.id).aluno_id == aluno.id
    
    assert LogAuditoria.query.filter(LogAuditoria.usuario_email == "maria@aluno.com").count() == 0
    assert LogAuditoria.query.filter(LogAuditoria.descricao.contains("maria@aluno.com")).count() == 0
    assert Usuario.query.filter_by(email="maria@aluno.com").first() is None


def test_anonimizar_cancela_reservas_na_fila(app, fabrica):
    livro = fabrica.livro(quantidade=1)
    fabrica.emprestimo(fabrica.usuario(), livro)
    aluno = fabrica.usuario()
    reserva = Reserva(aluno_id=aluno.id, livro_id=livro.id, status=StatusReserva.AGUARDANDO)
    db.session.add(reserva)
    db.session.commit()
    privacidade.anonimizar_usuario(aluno, fabrica.usuario("superadmin"))
    db.session.refresh(reserva)
    assert reserva.status == StatusReserva.CANCELADA


def test_conta_anonimizada_nao_pede_exclusao_de_novo(app, fabrica):
    aluno = fabrica.usuario()
    privacidade.anonimizar_usuario(aluno)
    with pytest.raises(RegraPrivacidadeError, match="já foram anonimizados"):
        privacidade.solicitar_exclusao(aluno)


def test_confirmar_sem_pedido_pendente_falha(app, fabrica):
    with pytest.raises(RegraPrivacidadeError):
        privacidade.confirmar_exclusao(fabrica.usuario(), fabrica.usuario("superadmin"))
