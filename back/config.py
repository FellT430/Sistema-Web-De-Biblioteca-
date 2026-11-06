import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configurações centrais da aplicação.

    Todas as informações sensíveis vêm de variáveis de ambiente (.env),
    seguindo boa prática de nunca deixar credenciais hardcoded no código.
    """
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_recycle": 280, "pool_pre_ping": True}

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

    # Integração com a Google Books API, usada no cadastro de livros para
    # preencher automaticamente título, autor, editora, ano, sinopse e capa
    # a partir de uma busca por ISBN ou título (ver services/google_books.py).
    # A API pode ser usada sem chave (com limite de cota menor); definir
    # GOOGLE_BOOKS_API_KEY no .env aumenta o limite de requisições.
    GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"
    GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "")

    # Regras de empréstimo (RF13 / RF14)
    PRAZO_DEVOLUCAO_DIAS = 7          # RN43: prazo de devolução em dias corridos
    MAX_EMPRESTIMOS_POR_ALUNO = 3     # RN44: máximo de empréstimos simultâneos por aluno

    # Mensagens de validação dos formulários em português (traduções do próprio
    # WTForms, sem precisar do Flask-Babel). Ver FormularioBase em forms.py.
    WTF_I18N_ENABLED = False
