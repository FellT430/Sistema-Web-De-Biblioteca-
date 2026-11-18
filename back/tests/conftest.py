import logging
import os
import sys
from datetime import date, datetime, timedelta

import pytest

BACK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACK_DIR not in sys.path:
    sys.path.insert(0, BACK_DIR)


os.environ.update({
    "FLASK_DEBUG": "1",
    "SECRET_KEY": "chave-somente-para-testes",
    "DATABASE_URL": "sqlite://",            
    "SUPERADMIN1_SENHA": "SenhaDeTeste@123",
    "SUPERADMIN2_SENHA": "SenhaDeTeste@123",
    "MAIL_SERVER": "",                     
    "GOOGLE_BOOKS_API_KEY": "",
    "DESATIVAR_AGENDADOR": "1",           
})


logging.getLogger("auditoria").addHandler(logging.NullHandler())

from app import create_app
from models import (
    db, Usuario, StatusCadastro, Livro, Emprestimo, StatusEmprestimo, Disciplina,
)


@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    contexto = app.app_context()
    contexto.push()
    yield app
    db.session.remove()
    db.drop_all()
    contexto.pop()


@pytest.fixture
def client(app):
    return app.test_client()



_contador = {"n": 0}


def _proximo():
    _contador["n"] += 1
    return _contador["n"]


def criar_usuario(perfil="aluno", nome=None, email=None, senha="Senha@123", ativo=True,
                  status=StatusCadastro.APROVADO, dois_fatores=False):
    n = _proximo()
    dominio = {"aluno": "aluno.com", "professor": "professor.com", "admin": "bibliotecaadm.com",
               "superadmin": "livromais.com"}[perfil]
    usuario = Usuario(
        nome=nome or f"Usuário {n}",
        email=email or f"usuario{n}@{dominio}",
        perfil=perfil,
        ativo=ativo,
        aceite_termos=True,
        aceite_termos_em=datetime.now(),
        status_cadastro=status,
        dois_fatores_ativo=dois_fatores,
    )
    usuario.set_senha(senha)
    db.session.add(usuario)
    db.session.commit()
    return usuario


def criar_livro(titulo=None, quantidade=1):
    livro = Livro(titulo=titulo or f"Livro {_proximo()}", autor="Autor de Teste", quantidade=quantidade)
    db.session.add(livro)
    db.session.commit()
    return livro


def criar_emprestimo(aluno, livro, status=StatusEmprestimo.ATIVO, prazo=None, devolvido_em=None):
    emprestimo = Emprestimo(aluno_id=aluno.id, livro_id=livro.id, status=status)
    if status != StatusEmprestimo.SOLICITADO:
        emprestimo.data_emprestimo = datetime.now() - timedelta(days=7)
        emprestimo.data_prevista_devolucao = prazo or (date.today() + timedelta(days=7))
    emprestimo.data_devolucao = devolvido_em
    db.session.add(emprestimo)
    db.session.commit()
    return emprestimo


def criar_disciplina(professor, nome="Algoritmos"):
    disciplina = Disciplina(nome=nome, professor_id=professor.id)
    db.session.add(disciplina)
    db.session.commit()
    return disciplina


def logar(client, usuario):
    from flask import g
    g.pop("_login_user", None)  
    with client.session_transaction() as sessao:
        sessao["_user_id"] = str(usuario.id)
        sessao["_fresh"] = True


@pytest.fixture
def fabrica():
    class Fabrica:
        usuario = staticmethod(criar_usuario)
        livro = staticmethod(criar_livro)
        emprestimo = staticmethod(criar_emprestimo)
        disciplina = staticmethod(criar_disciplina)
        logar = staticmethod(logar)
    return Fabrica
