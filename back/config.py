import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_recycle": 280, "pool_pre_ping": True}

    SECRET_KEY = os.getenv("SECRET_KEY", "troque-esta-chave-em-producao")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PERFIS_VALIDOS = ["superadmin", "admin", "professor", "aluno"]

    DOMINIOS_PERFIL = {
        "aluno.com": "aluno",
        "professor.com": "professor",
        "bibliotecaadm.com": "admin",
    }

    SUPERADMINS = [
        {"nome": "Bruno", "email": "bruno@livromais.com", "variavel_senha": "SUPERADMIN_BRUNO_SENHA"},
        {"nome": "Felipe", "email": "felipe@livromais.com", "variavel_senha": "SUPERADMIN_FELIPE_SENHA"},
    ]

    CONTATO_EMAIL = os.getenv("CONTATO_EMAIL", "contato@livromais.com")

    GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"
    GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "")

    PRAZO_DEVOLUCAO_DIAS = 7
    MAX_EMPRESTIMOS_POR_ALUNO = 3

    WTF_I18N_ENABLED = False
