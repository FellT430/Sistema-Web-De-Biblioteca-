# Funcionalidade: CRUD de Livros (Livro +)

Este pacote contém a funcionalidade de cadastro/edição/exclusão de livros
do sistema Livro +.

## O que está aqui

- `back/app.py` — application factory, registra o blueprint `livros_bp`
- `back/livros_routes.py` — rotas `/livros`, `/livros/novo`, `/livros/<id>/editar`, `/livros/<id>/excluir`
- `back/models.py` — modelo `Livro` (a funcionalidade própria deste pacote) +
  modelo `Usuario` (incluído só como **dependência**, pois o CRUD exige login)
- `back/forms.py` — `LivroForm`
- `back/decorators.py` — RBAC (`perfil_requerido`), adaptado para este pacote isolado
- `front/templates/livros/` — `listar.html`, `form.html`
- `front/static/css/style.css`

##  Dependência importante

O CRUD de livros é **restrito ao perfil `admin`** — por isso, mesmo isolado,
este pacote precisa de login funcionando. No projeto completo, esse login é
feito pelo pacote **"Funcionalidade Cadastro"**.

Para permitir testar este pacote sozinho, incluí um **login simplificado de
teste** (`/login-teste`, em `app.py` e `front/templates/login_teste.html`) —
ele não tem o formulário validado nem CSRF do cadastro real, serve só para
autenticar e acessar `/livros`.

## Como rodar e testar isoladamente

```bash
cd back
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Como este banco começa vazio, crie um usuário admin manualmente antes de
testar (com o servidor rodando, em outro terminal):

```bash
cd back
source venv/bin/activate
python -c "
from app import app
from models import db, Usuario
with app.app_context():
    u = Usuario(nome='Admin Teste', email='admin@bibliotecaadm.com', perfil='admin')
    u.set_senha('123456')
    db.session.add(u)
    db.session.commit()
    print('Usuário criado.')
"
```

Depois acesse **http://127.0.0.1:5000/login-teste**, entre com
`admin@bibliotecaadm.com` / `123456`, e você será redirecionado para
`/livros`.

## Observação

`base.html`, `style.css`, `config.py` e `decorators.py` são compartilhados
com a pasta "Funcionalidade Cadastro" — aparecem duplicados (com o ajuste
de rota já mencionado) para que cada pacote rode de forma independente.
