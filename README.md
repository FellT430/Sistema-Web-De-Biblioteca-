# Livro+ — Sistema Web de Biblioteca (Projeto PFC)

A Livro+ é um sistema web de biblioteca educacional que conecta professores, alunos e biblioteca, permitindo relacionar livros às disciplinas, consultar a disponibilidade dos exemplares e facilitar o acesso dos alunos a materiais recomendados pelos docentes, além de auxiliar no gerenciamento dos empréstimos e devoluções.

## Estrutura do repositório

| Pasta | Conteúdo |
|---|---|
| `Funcionalidade de login` | Cadastro, login com 2FA (Google Authenticator), perfis de acesso e hash de senhas |
| `Funcionalidade de logs de auditoria` | Registro de eventos do sistema, tela de consulta com filtros e exportação em CSV |
| `Informações da LGPD` | Política de Privacidade, Termos de Aceite, consentimento no cadastro e página "Meus dados" |
| `Funcionalidade da integração da API` | Cadastro de livros com busca automática na Google Books API |
| `Documentação sobre API` | Documentação da integração com a Google Books API |

Cada pasta de funcionalidade roda de forma independente.

## Tecnologias

**Front-end:** HTML, CSS, JavaScript e Bootstrap, com templates Jinja2.

**Back-end:** Python com Flask, conectado ao banco de dados via SQLAlchemy e à Google Books API, usada para buscar as informações dos livros.

**Banco de dados:** MySQL (administrado com o MySQL Workbench) e SQLAlchemy como ORM. Sem configuração, o sistema usa SQLite, o que facilita os testes.

**Integração externa:** Google Books API, para buscar automaticamente título, autor, ISBN, editora, capa e sinopse dos livros, sem precisar cadastrar tudo manualmente.

**Segurança e LGPD:**
- **Werkzeug**: hash das senhas (nunca são salvas em texto puro).
- **pyotp + qrcode**: autenticação de dois fatores, compatível com o Google Authenticator.
- **Flask-Login**: controle de sessão.
- **Flask-WTF**: validação de formulários e proteção contra CSRF.
- **python-dotenv**: chaves e configurações sensíveis ficam no `.env`, fora do código-fonte.

**Planejado para as próximas etapas:**
- **APScheduler**: verificar empréstimos atrasados e disparar notificações.
- **deep-translator**: traduzir informações vindas da API quando necessário.
- Usar a classificação obtida pela API para verificar se o livro está de acordo com as áreas definidas no projeto.

## Perfis de acesso

| Perfil | Domínio de e-mail | O que pode fazer hoje |
|---|---|---|
| Aluno | `@aluno.com` | Login, dashboard e "Meus dados" |
| Professor | `@professor.com` | Login, dashboard e "Meus dados" |
| Admin/Bibliotecário | `@bibliotecaadm.com` | Tudo acima, mais gestão de usuários (incluindo reset do 2FA), CRUD de livros com busca na Google Books e logs de auditoria |

O aluno e o professor ainda não têm telas próprias além do dashboard. As funcionalidades específicas de cada perfil (relacionar livros a disciplinas, recomendações, empréstimos) fazem parte das próximas etapas.

## Cadastro e login

**Regra de negócio central:** o usuário não escolhe seu perfil no cadastro. O perfil é detectado automaticamente pelo domínio do e-mail (função `detectar_perfil_pelo_email`, em `controllers/auth_controller.py`):

- `nome@aluno.com` → aluno
- `nome@professor.com` → professor
- `nome@bibliotecaadm.com` → admin

### Cadastro (`/cadastro`)

1. O usuário preenche nome, e-mail e senha (com confirmação).
2. O usuário precisa aceitar a Política de Privacidade e os Termos de Aceite (LGPD). A data e a hora do aceite são registradas.
3. O sistema verifica se o e-mail já existe.
4. O domínio do e-mail é comparado aos domínios válidos (`Config.DOMINIOS_PERFIL`). Se não for reconhecido, o cadastro é recusado.
5. A senha é transformada em hash e o usuário é redirecionado para o login.

### Login (`/login`)

1. O usuário informa e-mail e senha.
2. O sistema confere a senha (hash) e se a conta está ativa.
3. **Verificação em duas etapas (`/login/verificacao`):**
   - no primeiro acesso, é exibido um QR Code para configurar o Google Authenticator;
   - nos acessos seguintes, o usuário digita o código de 6 dígitos do app.
4. Só depois do código válido a sessão é criada e o usuário vai para o `/dashboard`.

Após 5 códigos inválidos, é preciso digitar a senha novamente. Todos os acessos ficam registrados nos logs de auditoria.

### Outras rotas

- `/logout`: encerra a sessão.
- `/dashboard`: página inicial do usuário logado.
- `/meus-dados`: dados pessoais guardados pelo sistema (LGPD).
- `/politica-privacidade` e `/termos-uso`: documentos da LGPD.
- `/admin`: lista de usuários (somente admin).
- `/livros`: acervo e cadastro de livros (somente admin).
- `/admin/auditoria`: logs de auditoria (somente admin).

## Como rodar

Dentro da pasta da funcionalidade desejada:

```
cd back
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Acesse http://127.0.0.1:5000. Para usar MySQL ou a chave da Google Books API, preencha o arquivo `back/.env` com base no `back/.env.example`.
