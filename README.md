# Livro + — Login e Cadastro de Usuários

Estrutura do projeto:

```
projeto_login/
├── back/                  # Back-end (Flask)
│   ├── app.py              # Cria a aplicação (application factory)
│   ├── config.py           # Configurações (lidas do .env)
│   ├── models.py           # Modelo Usuario (SQLAlchemy)
│   ├── forms.py            # Formulários com validação e CSRF
│   ├── routes.py           # Rotas: login, cadastro, logout, dashboard
│   ├── requirements.txt
│   └── .env.example
└── front/                  # Front-end (templates e assets)
    ├── templates/
    │   ├── base.html
    │   ├── login.html
    │   ├── cadastro.html
    │   └── dashboard.html
    └── static/
        └── css/style.css
```

## Como rodar

```bash
cd back
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Acesse http://127.0.0.1:5000 — o banco SQLite (`app.db`) é criado automaticamente
na primeira execução.

## Como funciona

- **Cadastro** (`/cadastro`): cria um usuário escolhendo o perfil (admin, professor
  ou aluno). A senha nunca é salva em texto puro — usamos hash com
  `werkzeug.security`.
- **Login** (`/login`): autentica por e-mail/senha e cria a sessão com
  `Flask-Login`.
- **Dashboard** (`/dashboard`): conteúdo muda conforme o perfil do usuário logado.
- **Controle de acesso por perfil**: o decorator `perfil_requerido("admin")` em
  `routes.py` protege rotas exclusivas (veja a rota `/admin`, que lista todos
  os usuários cadastrados).
- **CSRF**: todos os formulários usam `Flask-WTF`, que já inclui proteção
  contra CSRF automaticamente.

## Verificação em duas etapas (Google Authenticator) — obrigatória

Todo login tem duas etapas: primeiro e-mail e senha, depois o código de 6
dígitos do Google Authenticator (rota `/login/verificacao`). O usuário só é
logado depois de passar pelas duas.

- **Primeiro acesso:** logo após a senha, o sistema gera um segredo e mostra um
  QR Code (padrão TOTP, RFC 6238). O usuário escaneia com o Google Authenticator
  (ou Microsoft Authenticator, Authy…) e digita o código para confirmar. O segredo
  só é salvo depois desse código válido.
- **Próximos acessos:** após a senha, basta digitar o código atual do app.

Regras de segurança implementadas:

- Entre a senha e o código, só fica um id "pendente" na sessão, válido por 10 minutos.
- No máximo 5 códigos errados; depois disso é preciso digitar a senha de novo.
- Um código já usado não é aceito de novo (proteção contra replay).
- Tolerância de ±30 s para pequenas diferenças de relógio. **O relógio do servidor precisa estar correto.**
- Configuração do app e códigos errados ficam registrados na auditoria.
- **Perdeu o celular?** Na área do admin (Usuários), o botão **Resetar** na coluna
  "Verificação em 2 etapas" apaga o app configurado daquele usuário. No próximo login
  ele verá o QR Code de novo. O reset também fica registrado na auditoria.

Arquivos envolvidos: `back/services/dois_fatores.py`, rotas `login` e `login_2fa` em
`back/controllers/auth_controller.py`, templates `login_2fa.html` e `ativar_2fa.html`.
Bancos já existentes recebem as colunas novas automaticamente ao iniciar o `app.py`
(ou rode `db/migracao_2fa.sql`).

## Para usar MySQL (como no projeto final)

No `.env`, descomente e ajuste:

```
DATABASE_URL=mysql+pymysql://usuario:senha@localhost/livro_mais
```

E no `requirements.txt`, descomente `PyMySQL`.

## Próximos passos sugeridos

- Adicionar recuperação de senha
- Adicionar 2FA (pyotp), como planejado no projeto
- Criar seed de um usuário admin inicial via comando CLI do Flask
