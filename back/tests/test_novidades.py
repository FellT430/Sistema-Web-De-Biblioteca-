from models import Disciplina, Recomendacao, Usuario, db


def criar_recomendacao(professor, disciplina, livro):
    recomendacao = Recomendacao(
        professor_id=professor.id,
        disciplina_id=disciplina.id,
        livro_id=livro.id,
        ativa=True,
    )
    db.session.add(recomendacao)
    db.session.commit()
    return recomendacao


def preparar_recomendacoes(fabrica):
    professor = fabrica.usuario("professor")
    aluno = fabrica.usuario("aluno")
    algoritmos = fabrica.disciplina(professor, nome="Algoritmos")
    algoritmos.codigo = "ALG1"
    banco = fabrica.disciplina(professor, nome="Banco de Dados")
    banco.codigo = "BD2"
    db.session.commit()
    livro_alg = fabrica.livro(titulo="Livro de Algoritmos")
    livro_bd = fabrica.livro(titulo="Livro de Banco")
    criar_recomendacao(professor, algoritmos, livro_alg)
    criar_recomendacao(professor, banco, livro_bd)
    return aluno


def test_recomendacoes_sem_busca_mostra_todas(client, fabrica):
    aluno = preparar_recomendacoes(fabrica)
    fabrica.logar(client, aluno)
    resposta = client.get("/recomendacoes/")
    assert resposta.status_code == 200
    assert b"Livro de Algoritmos" in resposta.data
    assert b"Livro de Banco" in resposta.data


def test_busca_por_nome_da_disciplina(client, fabrica):
    aluno = preparar_recomendacoes(fabrica)
    fabrica.logar(client, aluno)
    resposta = client.get("/recomendacoes/?q=banco")
    assert resposta.status_code == 200
    assert b"Livro de Banco" in resposta.data
    assert b"Livro de Algoritmos" not in resposta.data


def test_busca_por_codigo_da_disciplina(client, fabrica):
    aluno = preparar_recomendacoes(fabrica)
    fabrica.logar(client, aluno)
    resposta = client.get("/recomendacoes/?q=ALG1")
    assert b"Livro de Algoritmos" in resposta.data
    assert b"Livro de Banco" not in resposta.data


def test_busca_sem_resultado_mostra_aviso(client, fabrica):
    aluno = preparar_recomendacoes(fabrica)
    fabrica.logar(client, aluno)
    resposta = client.get("/recomendacoes/?q=quimica")
    assert resposta.status_code == 200
    assert "Nenhuma recomendação encontrada".encode() in resposta.data
    assert b"Livro de Algoritmos" not in resposta.data
    assert b"Livro de Banco" not in resposta.data


def test_busca_com_caractere_especial_nao_traz_tudo(client, fabrica):
    aluno = preparar_recomendacoes(fabrica)
    fabrica.logar(client, aluno)
    resposta = client.get("/recomendacoes/?q=%25")
    assert resposta.status_code == 200
    assert b"Livro de Algoritmos" not in resposta.data
    assert b"Livro de Banco" not in resposta.data


def test_busca_ignora_espacos_nas_pontas(client, fabrica):
    aluno = preparar_recomendacoes(fabrica)
    fabrica.logar(client, aluno)
    resposta = client.get("/recomendacoes/?q=%20%20Algoritmos%20%20")
    assert b"Livro de Algoritmos" in resposta.data
    assert b"Livro de Banco" not in resposta.data


def test_recomendacao_inativa_nao_aparece_na_busca(client, fabrica):
    aluno = preparar_recomendacoes(fabrica)
    recomendacao = Recomendacao.query.join(Disciplina).filter(Disciplina.nome == "Algoritmos").one()
    recomendacao.ativa = False
    db.session.commit()
    fabrica.logar(client, aluno)
    resposta = client.get("/recomendacoes/?q=Algoritmos")
    assert b"Livro de Algoritmos" not in resposta.data


def test_disciplina_sem_descricao_nao_e_criada(client, fabrica):
    professor = fabrica.usuario("professor")
    fabrica.logar(client, professor)
    resposta = client.post("/disciplinas/nova", data={"nome": "Redes", "codigo": "RD1"})
    assert resposta.status_code == 200
    assert "Informe a descrição da disciplina.".encode() in resposta.data
    assert Disciplina.query.filter_by(nome="Redes").count() == 0


def test_disciplina_com_descricao_e_criada(client, fabrica):
    professor = fabrica.usuario("professor")
    fabrica.logar(client, professor)
    client.post(
        "/disciplinas/nova",
        data={"nome": "Redes", "codigo": "RD1", "descricao": "Sistemas de Informação - 4º semestre"},
    )
    disciplina = Disciplina.query.filter_by(nome="Redes").one()
    assert disciplina.descricao == "Sistemas de Informação - 4º semestre"
    assert disciplina.professor_id == professor.id


def test_contas_de_administrador_criadas_com_novos_emails(app):
    emails = {usuario.email for usuario in Usuario.query.filter_by(perfil="superadmin").all()}
    assert emails == {"admin1@livromais.com", "admin2@livromais.com"}
