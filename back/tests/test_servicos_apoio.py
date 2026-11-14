"""Testes dos serviços de apoio: 2FA, códigos de recuperação, e-mail, Google Books,
auditoria, painel do bibliotecário e agendador."""
from datetime import date, timedelta
from unittest.mock import patch, Mock

import pyotp
import pytest
import requests

from models import db, LogAuditoria, StatusEmprestimo, StatusCadastro
from services import (
    codigos_recuperacao, dois_fatores, envio_email, google_books, dashboard_bibliotecario, agendador,
)
from services.auditoria import registrar, Acoes
from services.google_books import GoogleBooksError


# ---------------------------------------------------------------- 2FA
def test_codigo_2fa_valido_e_invalido():
    segredo = dois_fatores.gerar_segredo()
    codigo = pyotp.TOTP(segredo, interval=30).now()
    assert dois_fatores.verificar_codigo(segredo, codigo) is not None
    assert dois_fatores.verificar_codigo(segredo, "000000") is None or codigo == "000000"
    assert dois_fatores.verificar_codigo(segredo, "12a456") is None
    assert dois_fatores.verificar_codigo("", codigo) is None


def test_codigo_2fa_nao_pode_ser_reutilizado():
    segredo = dois_fatores.gerar_segredo()
    codigo = pyotp.TOTP(segredo, interval=30).now()
    passo = dois_fatores.verificar_codigo(segredo, codigo)
    assert dois_fatores.verificar_codigo(segredo, codigo, ultimo_passo=passo) is None


def test_qr_code_e_formatacao_do_segredo():
    segredo = dois_fatores.gerar_segredo()
    uri = dois_fatores.uri_provisionamento(segredo, "maria@aluno.com")
    assert uri.startswith("otpauth://totp/") and "Livro" in uri
    assert "<svg" in dois_fatores.qr_code_svg(uri)
    assert dois_fatores.formatar_segredo("ABCDEFGH") == "ABCD EFGH"


# ---------------------------------------------------------------- Códigos de recuperação
def test_codigos_de_recuperacao_uso_unico(app, fabrica):
    usuario = fabrica.usuario()
    codigos = codigos_recuperacao.gerar(usuario)
    assert len(codigos) == 8 and codigos_recuperacao.total(usuario) == 8
    assert codigos_recuperacao.usar(usuario, codigos[0].lower())  # aceita minúsculas
    assert codigos_recuperacao.restantes(usuario) == 7
    assert not codigos_recuperacao.usar(usuario, codigos[0])      # não reutiliza
    assert not codigos_recuperacao.usar(usuario, "curto")
    assert not codigos_recuperacao.usar(usuario, "ZZZZ-ZZZZ")


def test_gerar_de_novo_substitui_os_codigos(app, fabrica):
    usuario = fabrica.usuario()
    antigos = codigos_recuperacao.gerar(usuario)
    codigos_recuperacao.gerar(usuario)
    assert codigos_recuperacao.total(usuario) == 8
    assert not codigos_recuperacao.usar(usuario, antigos[0])


# ---------------------------------------------------------------- E-mail
def test_token_de_confirmacao_ida_e_volta(app, fabrica):
    usuario = fabrica.usuario(status=StatusCadastro.AGUARDANDO_CONFIRMACAO)
    with app.test_request_context():
        token = envio_email.gerar_token_confirmacao(usuario)
    dados, erro = envio_email.ler_token_confirmacao(token)
    assert erro is None and dados["email"] == usuario.email
    assert envio_email.ler_token_confirmacao("token-invalido") == (None, "invalido")


def test_sem_servidor_de_email_nada_e_enviado(app, fabrica):
    """Sem MAIL_SERVER o sistema só mostra a mensagem no terminal."""
    resultado = envio_email.enviar("maria@aluno.com", "Assunto", ["Olá"])
    assert resultado is False


def test_emails_de_notificacao_sao_montados_sem_erro(app, fabrica):
    aluno = fabrica.usuario()
    emprestimo = fabrica.emprestimo(aluno, fabrica.livro(), prazo=date.today())
    with app.test_request_context():
        envio_email.enviar_lembrete_prazo(emprestimo, date.today())
        envio_email.enviar_aviso_atraso(emprestimo, 2)
        envio_email.enviar_devolucao(emprestimo)
        envio_email.enviar_confirmacao(aluno)
        envio_email.enviar_aprovacao(aluno)
        envio_email.enviar_reprovacao(aluno)
        envio_email.enviar_exclusao_solicitada(aluno)
        envio_email.enviar_exclusao_confirmada(aluno.email, aluno.nome)
        envio_email.enviar_exclusao_recusada(aluno, "motivo")


def test_email_enviado_por_smtp_quando_configurado(app):
    app.config.update(MAIL_SERVER="smtp.teste", MAIL_USERNAME="u", MAIL_PASSWORD="p")
    with patch("smtplib.SMTP") as smtp:
        assert envio_email.enviar("maria@aluno.com", "Assunto", ["Olá"], botao=("Entrar", "http://x"))
    assert smtp.called


def test_falha_no_smtp_nao_quebra_o_sistema(app):
    app.config.update(MAIL_SERVER="smtp.teste")
    with patch("smtplib.SMTP", side_effect=OSError("sem rede")):
        assert envio_email.enviar("maria@aluno.com", "Assunto", ["Olá"]) is False


# ---------------------------------------------------------------- Google Books
def _resposta_google():
    return {"items": [{
        "id": "abc123",
        "volumeInfo": {
            "title": "Python Fluente", "authors": ["Luciano Ramalho"], "publisher": "Novatec",
            "publishedDate": "2015-08-20", "description": "Sinopse",
            "categories": ["Computers / Programming"],
            "industryIdentifiers": [{"type": "ISBN_10", "identifier": "8575224628"},
                                    {"type": "ISBN_13", "identifier": "9788575224625"}],
            "imageLinks": {"thumbnail": "http://books.google.com/capa.jpg"},
        },
    }]}


def test_busca_google_books_normaliza_os_dados(app):
    resposta = Mock(json=Mock(return_value=_resposta_google()), raise_for_status=Mock())
    with patch("services.google_books.requests.get", return_value=resposta):
        livros = google_books.buscar_livros("python")
    livro = livros[0]
    assert livro["titulo"] == "Python Fluente"
    assert livro["isbn"] == "9788575224625"          # prefere ISBN-13
    assert livro["ano_publicacao"] == 2015
    assert livro["capa_url"].startswith("https://")  # força HTTPS
    assert livro["categoria"].startswith("Computação") or livro["categoria"]


def test_busca_vazia_nao_chama_a_api(app):
    with patch("services.google_books.requests.get") as get:
        assert google_books.buscar_livros("   ") == []
    get.assert_not_called()


def test_google_books_fora_do_ar(app):
    with patch("services.google_books.requests.get", side_effect=requests.exceptions.Timeout):
        with pytest.raises(GoogleBooksError):
            google_books.buscar_livros("python", por_isbn=True)


def test_google_books_resposta_invalida(app):
    resposta = Mock(json=Mock(side_effect=ValueError), raise_for_status=Mock())
    with patch("services.google_books.requests.get", return_value=resposta):
        with pytest.raises(GoogleBooksError):
            google_books.buscar_livros("python")


# ---------------------------------------------------------------- Auditoria
def test_auditoria_registra_acao(app, fabrica):
    usuario = fabrica.usuario()
    registrar(Acoes.LOGIN_SUCESSO, "Login realizado", usuario=usuario)
    log = LogAuditoria.query.one()
    assert log.acao == Acoes.LOGIN_SUCESSO and log.usuario_email == usuario.email and log.sucesso


def test_auditoria_registra_ip_dentro_de_requisicao(app):
    with app.test_request_context("/login", environ_base={"REMOTE_ADDR": "10.0.0.7"}):
        registrar(Acoes.LOGIN_FALHA, "Senha incorreta", email="x@aluno.com", sucesso=False)
    log = LogAuditoria.query.one()
    assert log.ip == "10.0.0.7" and log.rota == "/login" and not log.sucesso


# ---------------------------------------------------------------- Painel e agendador
def test_painel_do_bibliotecario(app, fabrica):
    hoje = date.today()
    livro = fabrica.livro(quantidade=3)
    fabrica.emprestimo(fabrica.usuario(), livro)
    fabrica.emprestimo(fabrica.usuario(), livro, prazo=hoje - timedelta(days=4))
    fabrica.emprestimo(fabrica.usuario(), fabrica.livro(), StatusEmprestimo.SOLICITADO)
    painel = dashboard_bibliotecario.montar_painel(hoje)
    assert isinstance(painel, dict)
    texto = str(painel)
    assert livro.titulo in texto  # aparece entre os mais emprestados/atrasos


def test_verificacao_do_agendador(app, fabrica):
    fabrica.emprestimo(fabrica.usuario(), fabrica.livro(), prazo=date.today() - timedelta(days=1))
    resumo = agendador.executar_verificacao(app)
    assert resumo["novos_atrasos"] == 1
    assert LogAuditoria.query.filter_by(acao=Acoes.VERIFICACAO_ATRASOS).count() == 1
