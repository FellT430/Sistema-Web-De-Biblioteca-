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

    # Por padrão usa SQLite (zero configuração, ótimo para desenvolver/testar).
    # Para usar MySQL (como no projeto real), defina DATABASE_URL no .env, ex:
    # DATABASE_URL=mysql+pymysql://usuario:senha@localhost/livro_mais
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Perfis de usuário permitidos no sistema
    PERFIS_VALIDOS = ["admin", "professor", "aluno"]

    # Regra de negócio: o perfil do usuário é detectado automaticamente
    # pelo domínio do e-mail informado no cadastro, em vez de ser escolhido
    # manualmente. Ajuste os domínios abaixo conforme o padrão real da
    # instituição.
    DOMINIOS_PERFIL = {
        "aluno.com": "aluno",
        "professor.com": "professor",
        "bibliotecaadm.com": "admin",
    }
