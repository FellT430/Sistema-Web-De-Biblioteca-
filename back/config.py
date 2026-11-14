import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def env(nome, padrao=None):
    valor = os.getenv(nome)
    return valor if valor else padrao


def env_obrigatoria(nome):
    valor = os.getenv(nome)
    if not valor:
        raise RuntimeError(f"Variável de ambiente obrigatória não definida: {nome}")
    return valor


def env_bool(nome, padrao=False):
    valor = os.getenv(nome)
    if not valor:
        return padrao
    return valor.strip().lower() in ("1", "true", "sim", "yes")


class Config:
    DEBUG = env_bool("FLASK_DEBUG", False)
    SECRET_KEY = env_obrigatoria("SECRET_KEY")

    if DEBUG:
        SQLALCHEMY_DATABASE_URI = env(
            "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"
        )
    else:
        SQLALCHEMY_DATABASE_URI = env_obrigatoria("DATABASE_URL")

    SQLALCHEMY_ENGINE_OPTIONS = {"pool_recycle": 280, "pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PERFIS_VALIDOS = ["superadmin", "admin", "professor", "aluno"]

    DOMINIOS_PERFIL = {
        "aluno.com": "aluno",
        "professor.com": "professor",
        "bibliotecaadm.com": "admin",
    }

    PRAZO_DEVOLUCAO_DIAS = 7
    MAX_EMPRESTIMOS_POR_ALUNO = 3

    MAX_RESERVAS_POR_ALUNO = 3
    PRAZO_RETIRADA_RESERVA_DIAS = 2

    SUPERADMINS = [
        {"nome": "Bruno", "email": "bruno@livromais.com", "variavel_senha": "SUPERADMIN_BRUNO_SENHA"},
        {"nome": "Felipe", "email": "felipe@livromais.com", "variavel_senha": "SUPERADMIN_FELIPE_SENHA"},
    ]
    for _admin in SUPERADMINS:
        env_obrigatoria(_admin["variavel_senha"])

    CONTATO_EMAIL = env("CONTATO_EMAIL", "contato@livromais.com")

    GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"
    GOOGLE_BOOKS_API_KEY = env("GOOGLE_BOOKS_API_KEY", "")

    MAIL_SERVER = env("MAIL_SERVER")
    MAIL_PORT = int(env("MAIL_PORT", "2525"))
    MAIL_USE_TLS = env_bool("MAIL_USE_TLS", True)
    MAIL_USERNAME = env("MAIL_USERNAME")
    MAIL_PASSWORD = env("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = env("MAIL_DEFAULT_SENDER", "nao-responda@livromais.com")

    APP_URL = env("APP_URL", "http://127.0.0.1:5000")

    HORAS_VALIDADE_CONFIRMACAO = 48

    WTF_I18N_ENABLED = False
