# Funcionalidade: Cadastro / Login (Livro +)

Este pacote contém **apenas** a funcionalidade de cadastro, login e controle
de acesso por perfil do sistema Livro +. Roda de forma independente.

## O que está aqui

- `back/app.py` — application factory, registra só o blueprint de autenticação (`auth_bp`)
- `back/routes.py` — rotas `/cadastro`, `/login`, `/logout`, `/dashboard`, `/admin`
- `back/models.py` — modelo `Usuario` (perfis: admin, professor, aluno)
- `back/forms.py` — `LoginForm` e `CadastroForm`
- `back/decorators.py` — RBAC (`perfil_requerido`)
- `back/config.py` — configurações (lidas do `.env`)
- `front/templates/` — `login.html`, `cadastro.html`, `dashboard.html`, `base.html`
- `front/static/css/style.css`

## Regra de negócio

O perfil do usuário é detectado **automaticamente pelo domínio do e-mail**
no cadastro:

- `@aluno.com` → aluno
- `@professor.com` → professor
- `@bibliotecaadm.com` → admin

## Como rodar

```bash
cd back
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Acesse **http://127.0.0.1:5000**.

## Observação

`style.css`, `base.html`, `config.py` e o script de banco são compartilhados
com a pasta "Funcionalidade Crud de Livros" — por isso aparecem duplicados
nos dois pacotes, para que cada um rode de forma independente.
