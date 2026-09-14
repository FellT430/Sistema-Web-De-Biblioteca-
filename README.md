# LIVRO + - SISTEMA WEB BIBLIOTECA (PROJETO PFC)

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


# CONTAS COM EXEMPLOS

Perfil	Domínio de e-mail	O que pode fazer hoje
Aluno	@aluno.com	Login e acesso ao dashboard
Professor	@professor.com	Login e acesso ao dashboard
Admin/Bibliotecário	@bibliotecaadm.com	Login, dashboard, gestão de usuários e CRUD de livros


O aluno e o professor ainda não têm telas próprias além do dashboard — as funcionalidades específicas de cada perfil (relacionar livros a disciplinas, recomendações, empréstimos) fazem parte das próximas etapas.

# Como funciona o cadastro e login

Regra de negócio central: o usuário não escolhe seu perfil no formulário de cadastro. O perfil é detectado automaticamente pelo domínio do e-mail informado (função detectar_perfil_pelo_email, em routes.py):

nome@aluno.com → perfil aluno
nome@professor.com → perfil professor
nome@bibliotecaadm.com → perfil admin

Fluxo de cadastro (/cadastro):

Usuário preenche nome, e-mail e senha (com confirmação).
O sistema verifica se o e-mail já existe.
O domínio do e-mail é comparado à lista de domínios válidos (Config.DOMINIOS_PERFIL). Se não for reconhecido, o cadastro é recusado.
A senha é transformada em hash (werkzeug.security) — nunca é salva em texto puro.
Usuário é criado no banco e redirecionado para o login.

Fluxo de login (/login):

Usuário informa e-mail e senha.
O sistema busca o usuário pelo e-mail, confere a senha (hash) e se a conta está ativa.
Se tudo estiver correto, a sessão é criada com Flask-Login e o usuário vai para o /dashboard.

Outras rotas relacionadas:

/logout — encerra a sessão.
/dashboard — conteúdo do usuário logado.
/admin — lista todos os usuários cadastrados (só para o perfil admin).
