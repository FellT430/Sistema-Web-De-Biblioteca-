import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Configurações centrais da aplicação.

    Todas as informações sensíveis vêm de variáveis de ambiente (.env),
    seguindo boa prática de nunca deixar credenciais hardcoded no código.
    """

    SECRET_KEY = os.getenv("SECRET_KEY", "troque-esta-chave-em-producao")


    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


    PERFIS_VALIDOS = ["admin", "professor", "aluno"]

   
    DOMINIOS_PERFIL = {
        "aluno.com": "aluno",
        "professor.com": "professor",
        "bibliotecaadm.com": "admin",
    }
