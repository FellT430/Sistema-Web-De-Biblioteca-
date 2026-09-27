# Funcionalidade de login

Login com **autenticação** (e-mail, senha e Google Authenticator), **autorização** (perfis admin,
professor e aluno) e **criptografia** (senhas com hash e códigos TOTP).

## Onde está cada parte

| Parte | Arquivos |
|---|---|
| Autenticação (senha) | `back/controllers/auth_controller.py` (rotas `login`, `logout`, `cadastro`), `back/forms.py`, `front/templates/login.html`, `front/templates/cadastro.html` |
| Autenticação em duas etapas (2FA) | `back/services/dois_fatores.py`, rota `login_2fa` em `auth_controller.py`, `front/templates/login_2fa.html`, `front/templates/ativar_2fa.html` |
| Autorização por perfil | `back/decorators.py` (`perfil_requerido`), `back/config.py` (`DOMINIOS_PERFIL`), rotas `/admin` e `resetar_2fa` |
| Criptografia | `back/models/usuario.py` (`set_senha` e `checar_senha` com hash do Werkzeug), segredo TOTP em `dois_fatores.py` |
| Sessão do usuário | `back/app.py` (Flask-Login) |
| Banco | `back/models/usuario.py`, `db/migracao_2fa.sql` |

Arquivos de apoio: `back/services/auditoria.py` e `back/models/log_auditoria.py` (o login registra os
acessos), `front/templates/base.html`, `dashboard.html`, `meus_dados.html`, `politica_privacidade.html`
e `termos_uso.html` (páginas abertas depois do login e links do cadastro).

## Como testar

1. Cadastre um usuário com e-mail `@aluno.com`, `@professor.com` ou `@bibliotecaadm.com`. O perfil é definido pelo domínio.
2. Faça login. Depois da senha, escaneie o QR Code com o Google Authenticator e digite o código.
3. Saia e entre de novo: agora só o código é pedido.
4. Com um aluno, tente abrir http://127.0.0.1:5000/admin: o acesso é negado (erro 403).
5. Com um admin, abra **Usuários** e use **Resetar** para exigir um novo QR Code de um usuário.

## Como rodar

No PowerShell, dentro desta pasta:

```
cd back
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Acesse http://127.0.0.1:5000. O banco SQLite (`back/app.db`) é criado automaticamente.

O arquivo `back/.env` tem apenas valores de exemplo. Para usar MySQL ou outra chave secreta, copie os
valores do `back/.env.example` e preencha com os dados reais.
