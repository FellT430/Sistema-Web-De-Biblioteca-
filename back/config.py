import os
from dotenv import load_dotenv

# override=False (padrão): variáveis já definidas no servidor têm prioridade
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def env(nome, padrao=None):
    """Lê variável de ambiente. Vazia conta como não definida."""
    valor = os.getenv(nome)
    return valor if valor else padrao


def env_obrigatoria(nome):
    """Lê variável obrigatória; para o sistema se não existir."""
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
    # ---------- Aplicação ----------
    DEBUG = env_bool("FLASK_DEBUG", False)
    SECRET_KEY = env_obrigatoria("SECRET_KEY")

    # ---------- Banco de dados ----------
    # Em desenvolvimento (DEBUG) aceita SQLite local; em produção é obrigatório
    if DEBUG:
        SQLALCHEMY_DATABASE_URI = env(
            "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"
        )
    else:
        SQLALCHEMY_DATABASE_URI = env_obrigatoria("DATABASE_URL")

    SQLALCHEMY_ENGINE_OPTIONS = {"pool_recycle": 280, "pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---------- Perfis e regras de negócio (fixas no código) ----------
    PERFIS_VALIDOS = ["superadmin", "admin", "professor", "aluno"]

    DOMINIOS_PERFIL = {
        "aluno.com": "aluno",
        "professor.com": "professor",
        "bibliotecaadm.com": "admin",
    }

    PRAZO_DEVOLUCAO_DIAS = 7
    MAX_EMPRESTIMOS_POR_ALUNO = 3

    # ---------- Super admins ----------
    # E-mails ficam no código; as senhas vêm do ambiente
    SUPERADMINS = [
        {"nome": "Bruno", "email": "bruno@livromais.com", "variavel_senha": "SUPERADMIN_BRUNO_SENHA"},
        {"nome": "Felipe", "email": "felipe@livromais.com", "variavel_senha": "SUPERADMIN_FELIPE_SENHA"},
    ]
    # Garante que nenhum super admin seja criado com senha vazia
    for _admin in SUPERADMINS:
        env_obrigatoria(_admin["variavel_senha"])

    # ---------- LGPD ----------
    CONTATO_EMAIL = env("CONTATO_EMAIL", "contato@livromais.com")

    # ---------- Google Books ----------
    GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"
    GOOGLE_BOOKS_API_KEY = env("GOOGLE_BOOKS_API_KEY", "")

    WTF_I18N_ENABLED = False
