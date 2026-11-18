from datetime import date, timedelta

from models import (
    db, Usuario, StatusCadastro, Livro, Emprestimo, StatusEmprestimo, Reserva, StatusReserva,
    Disciplina, LogAuditoria,
)
from services import privacidade



def test_paginas_publicas_abrem(client):
    for rota in ("/login", "/cadastro", "/politica-privacidade", "/termos-uso", "/esqueci-senha"):
        assert client.get(rota).status_code == 200, rota


def test_rota_protegida_sem_login_redireciona(client):
    resposta = client.get("/emprestimos/")
    assert resposta.status_code == 302 and "/login" in resposta.headers["Location"]


def test_aluno_nao_acessa_area_do_bibliotecario(client, fabrica):
    fabrica.logar(client, fabrica.usuario("aluno"))
    assert client.get("/livros/").status_code == 403
    assert client.get("/admin/").status_code == 403
    assert LogAuditoria.query.filter_by(acao="ACESSO_NEGADO").count() >= 1


def test_pagina_inexistente(client):
    assert client.get("/nao-existe").status_code == 404



def test_cadastro_com_dominio_de_aluno(client):
    resposta = client.post("/cadastro", data={
        "nome": "Maria Silva", "email": "maria@aluno.com", "senha": "Senha@123",
        "confirmar_senha": "Senha@123", "aceite_termos": "y",
    })
    assert resposta.status_code in (200, 302)
    usuario = Usuario.query.filter_by(email="maria@aluno.com").one()
    assert usuario.perfil == "aluno"
    assert usuario.status_cadastro == StatusCadastro.AGUARDANDO_CONFIRMACAO
    assert usuario.checar_senha("Senha@123")


def test_cadastro_com_dominio_invalido_e_recusado(client):
    client.post("/cadastro", data={
        "nome": "Fulano", "email": "fulano@gmail.com", "senha": "Senha@123",
        "confirmar_senha": "Senha@123", "aceite_termos": "y",
    })
    assert Usuario.query.filter_by(email="fulano@gmail.com").first() is None


def test_cadastro_sem_aceite_dos_termos_e_recusado(client):
    client.post("/cadastro", data={
        "nome": "Fulano", "email": "fulano@aluno.com", "senha": "Senha@123",
        "confirmar_senha": "Senha@123",
    })
    assert Usuario.query.filter_by(email="fulano@aluno.com").first() is None


def test_link_de_confirmacao_libera_para_aprovacao(app, client, fabrica):
    from services.envio_email import gerar_token_confirmacao
    usuario = fabrica.usuario(status=StatusCadastro.AGUARDANDO_CONFIRMACAO)
    token = gerar_token_confirmacao(usuario)
    client.get(f"/confirmar-email/{token}")
    db.session.refresh(usuario)
    assert usuario.status_cadastro == StatusCadastro.AGUARDANDO_APROVACAO


def test_login_com_senha_errada(client, fabrica):
    usuario = fabrica.usuario()
    resposta = client.post("/login", data={"email": usuario.email, "senha": "errada"})
    assert b"inv" in resposta.data
    assert LogAuditoria.query.filter_by(sucesso=False).count() >= 1


def test_login_correto_pede_a_verificacao_em_duas_etapas(client, fabrica):
    usuario = fabrica.usuario()
    resposta = client.post("/login", data={"email": usuario.email, "senha": "Senha@123"})
    assert resposta.status_code == 302 and "verificacao" in resposta.headers["Location"]
    assert client.get("/login/verificacao").status_code == 200


def test_cadastro_nao_aprovado_nao_entra(client, fabrica):
    usuario = fabrica.usuario(status=StatusCadastro.AGUARDANDO_APROVACAO)
    resposta = client.post("/login", data={"email": usuario.email, "senha": "Senha@123"})
    assert "verificacao" not in resposta.headers.get("Location", "")


def test_paginas_do_usuario_logado(client, fabrica):
    fabrica.logar(client, fabrica.usuario())
    for rota in ("/dashboard", "/meus-dados", "/acervo/", "/recomendacoes/", "/emprestimos/meus",
                 "/notificacoes/"):
        resposta = client.get(rota, follow_redirects=True)
        assert resposta.status_code == 200, rota



def test_fluxo_completo_de_emprestimo(client, fabrica):
    aluno, bib = fabrica.usuario("aluno"), fabrica.usuario("admin")
    livro = fabrica.livro(quantidade=1)

    fabrica.logar(client, aluno)
    assert client.get(f"/acervo/{livro.id}").status_code == 200
    client.post(f"/emprestimos/solicitar/{livro.id}")
    emprestimo = Emprestimo.query.filter_by(aluno_id=aluno.id).one()
    assert emprestimo.status == StatusEmprestimo.SOLICITADO

    fabrica.logar(client, bib)
    assert client.get("/emprestimos/?filtro=pendentes").status_code == 200
    client.post(f"/emprestimos/{emprestimo.id}/confirmar")
    db.session.refresh(emprestimo)
    assert emprestimo.status == StatusEmprestimo.ATIVO

    client.post(f"/emprestimos/{emprestimo.id}/devolver")
    db.session.refresh(emprestimo)
    assert emprestimo.status == StatusEmprestimo.DEVOLVIDO


def test_reserva_pelo_navegador(client, fabrica):
    livro = fabrica.livro(quantidade=1)
    fabrica.emprestimo(fabrica.usuario(), livro)
    aluno = fabrica.usuario()
    fabrica.logar(client, aluno)
    client.post(f"/emprestimos/reservar/{livro.id}")
    reserva = Reserva.query.filter_by(aluno_id=aluno.id).one()
    assert reserva.status == StatusReserva.AGUARDANDO
    assert client.get(f"/acervo/{livro.id}").status_code == 200
    client.post(f"/emprestimos/reservas/{reserva.id}/cancelar")
    db.session.refresh(reserva)
    assert reserva.status == StatusReserva.CANCELADA


def test_bibliotecario_recusa_e_aluno_cancela(client, fabrica):
    aluno, bib = fabrica.usuario(), fabrica.usuario("admin")
    e1 = fabrica.emprestimo(aluno, fabrica.livro(), StatusEmprestimo.SOLICITADO)
    e2 = fabrica.emprestimo(aluno, fabrica.livro(), StatusEmprestimo.SOLICITADO)
    fabrica.logar(client, aluno)
    client.post(f"/emprestimos/{e1.id}/cancelar")
    fabrica.logar(client, bib)
    client.post(f"/emprestimos/{e2.id}/recusar")
    db.session.refresh(e1)
    db.session.refresh(e2)
    assert e1.status == e2.status == StatusEmprestimo.CANCELADO


def test_telas_do_bibliotecario(client, fabrica):
    bib = fabrica.usuario("admin")
    fabrica.emprestimo(fabrica.usuario(), fabrica.livro(), prazo=date.today() - timedelta(days=2))
    fabrica.logar(client, bib)
    for rota in ("/dashboard", "/livros/", "/livros/novo", "/emprestimos/",
                 "/emprestimos/?filtro=atrasados", "/emprestimos/?filtro=andamento",
                 "/emprestimos/?filtro=historico"):
        assert client.get(rota, follow_redirects=True).status_code == 200, rota
    client.post("/notificacoes/verificar-agora", follow_redirects=True)



def test_bibliotecario_cadastra_edita_e_exclui_livro(client, fabrica):
    fabrica.logar(client, fabrica.usuario("admin"))
    client.post("/livros/novo", data={"titulo": "Código Limpo", "autor": "Robert C. Martin",
                                      "quantidade": "2", "ano_publicacao": "2009"})
    livro = Livro.query.filter_by(titulo="Código Limpo").one()
    assert livro.quantidade == 2

    assert client.get(f"/livros/{livro.id}/editar").status_code == 200
    client.post(f"/livros/{livro.id}/editar", data={"titulo": "Código Limpo", "autor": "Robert C. Martin",
                                                     "quantidade": "5"})
    db.session.refresh(livro)
    assert livro.quantidade == 5

    client.post(f"/livros/{livro.id}/excluir")
    assert db.session.get(Livro, livro.id) is None


def test_quantidade_invalida_nao_grava_livro(client, fabrica):
    fabrica.logar(client, fabrica.usuario("admin"))
    client.post("/livros/novo", data={"titulo": "Sem Exemplar", "autor": "X", "quantidade": "0"})
    assert Livro.query.filter_by(titulo="Sem Exemplar").first() is None


def test_busca_google_books_sem_termo(client, fabrica):
    fabrica.logar(client, fabrica.usuario("admin"))
    resposta = client.get("/livros/buscar-google-books?q=")
    assert resposta.status_code == 400 and "erro" in resposta.get_json()



def test_professor_cria_disciplina_e_recomenda_livro(client, fabrica):
    professor = fabrica.usuario("professor")
    livro = fabrica.livro()
    fabrica.logar(client, professor)
    assert client.get("/disciplinas/nova").status_code == 200
    client.post("/disciplinas/nova", data={"nome": "Estrutura de Dados", "codigo": "ED1", "descricao": "Sistemas de Informação - 3º semestre"})
    disciplina = Disciplina.query.filter_by(nome="Estrutura de Dados").one()

    assert client.get(f"/disciplinas/{disciplina.id}").status_code == 200
    client.post(f"/disciplinas/{disciplina.id}/livros/{livro.id}/adicionar")
    db.session.refresh(disciplina)
    assert disciplina.possui_livro(livro)

    client.post(f"/disciplinas/{disciplina.id}/editar", data={"nome": "Estrutura de Dados II", "descricao": "Sistemas de Informação - 3º semestre"})
    db.session.refresh(disciplina)
    assert disciplina.nome == "Estrutura de Dados II"

    client.post(f"/disciplinas/{disciplina.id}/livros/{livro.id}/remover")
    db.session.refresh(disciplina)
    assert not disciplina.possui_livro(livro)



def test_admin_aprova_cadastro_somente_com_email_confirmado(client, fabrica):
    from datetime import datetime
    sem_confirmar = fabrica.usuario("aluno", status=StatusCadastro.AGUARDANDO_APROVACAO)
    confirmado = fabrica.usuario("aluno", status=StatusCadastro.AGUARDANDO_APROVACAO)
    confirmado.email_confirmado_em = datetime.now()
    db.session.commit()
    fabrica.logar(client, fabrica.usuario("superadmin"))
    for rota in ("/admin/", "/admin/usuarios", "/admin/solicitacoes", "/admin/auditoria/"):
        assert client.get(rota).status_code == 200, rota

    client.post(f"/admin/solicitacoes/{sem_confirmar.id}/aprovar")
    client.post(f"/admin/solicitacoes/{confirmado.id}/aprovar")
    db.session.refresh(sem_confirmar)
    db.session.refresh(confirmado)
    assert sem_confirmar.status_cadastro == StatusCadastro.AGUARDANDO_APROVACAO
    assert confirmado.status_cadastro == StatusCadastro.APROVADO


def test_admin_desativa_reativa_e_reseta_2fa(client, fabrica):
    usuario = fabrica.usuario(dois_fatores=True)
    fabrica.logar(client, fabrica.usuario("superadmin"))
    client.post(f"/admin/usuarios/{usuario.id}/desativar")
    db.session.refresh(usuario)
    assert not usuario.ativo
    client.post(f"/admin/usuarios/{usuario.id}/reativar")
    client.post(f"/admin/usuarios/{usuario.id}/resetar-2fa")
    db.session.refresh(usuario)
    assert usuario.ativo and not usuario.dois_fatores_ativo


def test_admin_exporta_auditoria_em_csv(client, fabrica):
    fabrica.logar(client, fabrica.usuario("superadmin"))
    resposta = client.get("/admin/auditoria/exportar.csv")
    assert resposta.status_code == 200 and "csv" in resposta.content_type


def test_exclusao_de_dados_pelo_navegador(client, fabrica):
    aluno = fabrica.usuario()
    fabrica.logar(client, aluno)
    client.post("/meus-dados/solicitar-exclusao", data={"senha": "Senha@123"})
    db.session.refresh(aluno)
    assert aluno.exclusao_pendente

    fabrica.logar(client, fabrica.usuario("superadmin"))
    client.post(f"/admin/exclusoes/{aluno.id}/confirmar")
    db.session.refresh(aluno)
    assert aluno.nome == privacidade.NOME_ANONIMIZADO
