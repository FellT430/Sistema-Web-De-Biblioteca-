LIVRO + - SISTEMA WEB BIBLIOTECA (PROJETO PFC)

A Livro+ é um sistema web de biblioteca educacional que conecta professores, alunos e biblioteca, permitindo relacionar livros às disciplinas, consultar a disponibilidade dos exemplares e facilitar o acesso dos alunos a materiais recomendados pelos docentes, além de auxiliar no gerenciamento dos empréstimos e devoluções.

# TECNOLOGIAS E ESTRUTURAS DO SISTEMA
FRONT-END: Uso de HTML e CSS para estilização, desenvolvimento e design das páginas. JavaScript e Bootstrap serão utilizados para desenvolver e estruturar a interface do sistema.

BACK-END: Python e Flask serão utilizados no desenvolvimento do back-end, realizando a conexão com o banco de dados MySQL (via SQLAlchemy) e com a Google Books API, utilizada para buscar as informações dos livros.

BANCO DE DADOS: MySQL, administrado com o MySQL Workbench, e SQLAlchemy como ORM — para armazenar usuários, livros, exemplares e empréstimos, e facilitar a comunicação entre o Python e o banco. A integração externa será feita pela Google Books API para buscar automaticamente as informações dos livros (título, autor, ISBN, capa, descrição), sem precisar cadastrar tudo manualmente. A classificação obtida pela API também será utilizada pelo sistema para verificar se o livro está de acordo com as áreas definidas no projeto. A segurança e a automação de tarefas serão realizadas utilizando bibliotecas, seguindo as diretrizes da LGPD no tratamento de dados pessoais, como:

bcrypt / Werkzeug — para gerar e verificar o hash das senhas dos usuários.
python-dotenv — para gerenciar e carregar variáveis de ambiente, permitindo manter configurações e informações sensíveis, como chaves de API, fora do código-fonte.
pyotp — para autenticação de dois fatores (2FA), compatível com o Google Authenticator.
APScheduler — para automatizar tarefas, como verificar empréstimos atrasados e disparar notificações.
deep-translator — para traduzir informações vindas da API quando necessário.
