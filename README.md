# LIVRO+ — Sistema Web de Biblioteca Educacional

Sistema web que conecta **professores, alunos e biblioteca**: professores relacionam livros às suas disciplinas e os recomendam aos alunos, que consultam a disponibilidade, solicitam empréstimos e entram na fila de reserva quando não há exemplares. A biblioteca controla empréstimos, devoluções e atrasos, com notificações automáticas no sistema e por e-mail.

Projeto Final de Curso (PFC) — Bacharelado em Sistemas de Informação — Universidade de Mogi das Cruzes (UMC), 2026.
Autores: Bruno Dante Nogueira Alves e Felipe Lima Torres.

---

## Sumário

1. [Funcionalidades](#funcionalidades)
2. [Tecnologias](#tecnologias)
3. [Estrutura do projeto](#estrutura-do-projeto)
4. [Como executar](#como-executar)
5. [Primeiro acesso](#primeiro-acesso)
6. [Testes automatizados](#testes-automatizados)
7. [Publicação (PythonAnywhere)](#publicação-pythonanywhere)
8. [Segurança e LGPD](#segurança-e-lgpd)

---

## Funcionalidades

O perfil do usuário é definido automaticamente pelo domínio do e-mail informado no cadastro:

| Perfil | Domínio do e-mail | Principais funções |
|---|---|---|
| Aluno | `@aluno.com` | Consultar o acervo e as recomendações, solicitar empréstimos, reservar livros sem exemplares, acompanhar prazos e notificações |
| Professor | `@professor.com` | Cadastrar disciplinas, relacionar livros a elas e recomendá-los aos alunos |
| Bibliotecário | `@bibliotecaadm.com` | Cadastrar livros (com dados da Google Books API), confirmar retiradas, registrar devoluções e acompanhar o painel de indicadores |
| Administrador do sistema | contas fixas (`config.py`) | Aprovar cadastros, gerenciar contas, redefinir 2FA e senha, confirmar exclusões de dados e consultar a auditoria |

Recursos do sistema:

- **Cadastro pelo próprio usuário**, com confirmação do e-mail (link válido por 48 h) e aprovação do administrador.
- **Login com verificação em duas etapas** (Google Authenticator) e 8 códigos de recuperação de uso único.
- **Acervo integrado à Google Books API**: busca por título ou ISBN e preenchimento automático dos dados do livro.
- **Disciplinas e recomendações** dos professores, visíveis para os alunos.
- **Empréstimos**: solicitação pelo aluno, retirada confirmada no balcão, prazo de 7 dias, limite de 3 empréstimos simultâneos e bloqueio de novos empréstimos para quem está em atraso.
- **Reserva de livros** com fila de espera: quando um exemplar é liberado, o primeiro da fila é atendido automaticamente e tem 2 dias para retirar o livro.
- **Notificações no sistema e por e-mail**: lembrete de prazo, aviso de atraso, devolução registrada e reserva disponível ou expirada.
- **Verificação automática** de atrasos e de reservas não retiradas a cada hora (APScheduler).
- **Painel de indicadores** do bibliotecário, com acesso direto às listas correspondentes.
- **Logs de auditoria** das ações relevantes, com exportação em CSV.
- **Exclusão de dados pessoais por anonimização** (LGPD), solicitada pelo usuário e confirmada pelo administrador.

---

## Tecnologias

| Camada | Tecnologias |
|---|---|
| Front-end | HTML, CSS, JavaScript, Bootstrap e templates Jinja2 |
| Back-end | Python e Flask (padrão MVC com camada de serviços) |
| Banco de dados | MySQL (SQLite opcional para testes locais), SQLAlchemy como ORM |
| Integração externa | Google Books API e envio de e-mails por SMTP (Mailtrap nos testes) |
| Segurança | Werkzeug (hash de senhas), Flask-Login, Flask-WTF (CSRF), pyotp e qrcode (2FA), itsdangerous (links assinados), python-dotenv |
| Tarefas automáticas | APScheduler |
| Testes | pytest e pytest-cov |
| Ferramentas | Visual Studio Code, Git e GitHub, GitHub Projects (Kanban), MySQL Workbench, Postman |

---

## Estrutura do projeto

```
Sistema-Web-De-Biblioteca-/
├── .vscode/                  # Configuração do VS Code (executar com F5 e aba de testes)
├── back/                     # Back-end (Flask)
│   ├── app.py                # Cria a aplicação, registra as rotas e inicia o agendador
│   ├── config.py             # Configurações lidas das variáveis de ambiente
│   ├── forms.py              # Formulários com validação e proteção CSRF
│   ├── decorators.py         # Controle de acesso por perfil
│   ├── controllers/          # Rotas (auth, acervo, livros, empréstimos, disciplinas, admin...)
│   ├── models/               # Classes do domínio / tabelas (SQLAlchemy)
│   ├── services/             # Regras de negócio (empréstimos, reservas, notificações, LGPD...)
│   ├── tests/                # Testes automatizados (pytest)
│   ├── rodar_agendador.py    # Agendador em processo separado (produção)
│   ├── requirements.txt      # Dependências do sistema
│   ├── requirements-dev.txt  # Dependências dos testes
│   └── .env.example          # Modelo das variáveis de ambiente
├── front/
│   ├── templates/            # Páginas (Jinja2)
│   └── static/               # CSS, JavaScript e imagens
└── db/                       # Scripts SQL de migração (referência para bancos já existentes)
```

---

## Como executar

### Pré-requisitos

- Python 3.11 ou superior
- MySQL 8 (ou nenhum banco, usando o SQLite para um teste rápido)
- Git
- Aplicativo Google Authenticator (ou outro compatível com TOTP) no celular

### 1. Baixar o projeto

```bash
git clone https://github.com/FellT430/Sistema-Web-De-Biblioteca-.git
cd Sistema-Web-De-Biblioteca-
git checkout entrega1411
cd back
```

### 2. Criar o ambiente virtual e instalar as dependências

Windows (PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Linux / macOS:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Criar o banco de dados (MySQL)

No MySQL Workbench ou no terminal do MySQL:

```sql
CREATE DATABASE livro_mais CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Não é preciso criar tabelas: o sistema cria todas elas, e as colunas novas, automaticamente ao iniciar.

### 4. Configurar as variáveis de ambiente

Copie o modelo e preencha os valores:

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

Substitua cada `${...}` por um valor real. Exemplo para uso local (valores fictícios):

```
SECRET_KEY=troque-por-uma-chave-longa-e-aleatoria
FLASK_DEBUG=True
DATABASE_URL=mysql+pymysql://root:SUA_SENHA@localhost:3306/livro_mais
SUPERADMIN_BRUNO_SENHA=defina-uma-senha-forte
SUPERADMIN_FELIPE_SENHA=defina-uma-senha-forte
MAIL_SERVER=sandbox.smtp.mailtrap.io
MAIL_PORT=2525
MAIL_USERNAME=usuario-do-mailtrap
MAIL_PASSWORD=senha-do-mailtrap
APP_URL=http://127.0.0.1:5000
```

| Variável | Obrigatória | Descrição |
|---|---|---|
| `SECRET_KEY` | Sim | Chave usada para assinar sessões e links |
| `DATABASE_URL` | Sim (com `FLASK_DEBUG=False`) | Conexão com o MySQL |
| `SUPERADMIN_BRUNO_SENHA`, `SUPERADMIN_FELIPE_SENHA` | Sim | Senhas das contas de administrador do sistema |
| `FLASK_DEBUG` | Não | `True` em desenvolvimento |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD` | Não | Servidor de e-mail (SMTP). Sem `MAIL_SERVER`, os e-mails são exibidos no terminal |
| `GOOGLE_BOOKS_API_KEY` | Não | Sem chave, a API funciona com um limite menor de requisições |
| `CONTATO_EMAIL` | Não | E-mail de contato exibido na Política de Privacidade |
| `APP_URL` | Não | Endereço do site usado nos links dos e-mails automáticos |

> **Teste rápido sem MySQL:** com `FLASK_DEBUG=True` e sem a linha `DATABASE_URL`, o sistema usa um banco SQLite local (`back/app.db`), criado automaticamente.

O arquivo `.env` contém senhas e **não deve ser enviado ao GitHub** (já está no `.gitignore`).

### 5. Iniciar o sistema

```bash
python app.py
```

Acesse **http://127.0.0.1:5000**.

No VS Code também é possível iniciar com **F5** (configuração “LIVRO+ (Flask)” em `.vscode/launch.json`).

---

## Primeiro acesso

1. Entre com uma conta de administrador do sistema: `bruno@livromais.com` ou `felipe@livromais.com`, com a senha definida no `.env`. As contas são criadas automaticamente quando o sistema inicia.
2. No primeiro login, escaneie o QR Code com o Google Authenticator e guarde os códigos de recuperação exibidos.
3. Para criar outros usuários, acesse **Cadastre-se** com um e-mail de domínio válido (`@aluno.com`, `@professor.com` ou `@bibliotecaadm.com`), confirme o e-mail pelo link recebido (na caixa do Mailtrap ou no terminal) e aprove o cadastro em **Painel do administrador → Solicitações de cadastro**.

Os e-mails dos usuários de teste são fictícios; com o Mailtrap, nenhuma mensagem chega a destinatários reais.

---

## Testes automatizados

O projeto possui **94 testes automatizados** (pytest), com **81% de cobertura** do código do sistema. Eles cobrem as regras de empréstimo, reserva, notificações, LGPD, 2FA, integração com a Google Books (simulada), auditoria e os fluxos completos pelas rotas (front-end, back-end e banco integrados).

Os testes usam um banco SQLite em memória, não enviam e-mails e não alteram o banco nem o `.env` do projeto.

Dentro da pasta `back`, com o ambiente virtual ativado:

```bash
pip install -r requirements-dev.txt
pytest
```

Com o relatório de cobertura:

```bash
pytest --cov=. --cov-report=term-missing --cov-report=html
```

O resultado da última execução está em `back/relatorio_testes.txt`. Os testes também podem ser executados pela aba **Testes** do VS Code. A descrição de cada arquivo de teste está em `back/tests/README.md`.

---

## Publicação (PythonAnywhere)

- Aplicação Flask e banco MySQL hospedados no PythonAnywhere, com acesso via HTTPS.
- As variáveis de ambiente são definidas no `.env` do servidor, com `FLASK_DEBUG=False`.
- O agendador roda em um processo separado como **Always-on task**:
  ```bash
  python /caminho/do/projeto/back/rodar_agendador.py
  ```
  Nesse caso, defina `DESATIVAR_AGENDADOR=1` no `.env` do servidor, para que a aplicação web não inicie um segundo agendador.

---

## Segurança e LGPD

- Senhas armazenadas apenas em hash; verificação em duas etapas obrigatória.
- Proteção contra CSRF em todos os formulários e controle de acesso por perfil.
- Credenciais e chaves somente em variáveis de ambiente, fora do código-fonte.
- Aceite da Política de Privacidade e dos Termos de Uso registrado com data e hora.
- O usuário consulta seus dados em **Meus dados** e pode solicitar a exclusão deles; após a confirmação do administrador, a conta é anonimizada, preservando o histórico de empréstimos sem identificar a pessoa.
- Ações relevantes registradas em log de auditoria, consultado apenas pelo administrador do sistema.
