# Informações da LGPD

Recursos de adequação à LGPD (Lei nº 13.709/2018):

| Recurso | Arquivos |
|---|---|
| Política de Privacidade | `front/templates/politica_privacidade.html`, rota `politica_privacidade` em `back/controllers/auth_controller.py` |
| Termos de Aceite | `front/templates/termos_uso.html`, rota `termos_uso` |
| Consentimento obrigatório no cadastro | `aceite_termos` em `back/forms.py` (`CadastroForm`), `front/templates/cadastro.html`, rota `cadastro` |
| Registro de quando o consentimento foi dado | colunas `aceite_termos` e `aceite_termos_em` em `back/models/usuario.py` |
| Acesso do titular aos próprios dados | rota `meus_dados` e `front/templates/meus_dados.html` |
| Links em todas as páginas | rodapé de `front/templates/base.html` |
| Registro de consulta aos dados pessoais | ação `CONSULTA_DADOS_PESSOAIS` em `back/services/auditoria.py` |
| Proteção dos dados | senha com hash (`back/models/usuario.py`) e mensagem de login que não revela se o e-mail existe |

## Arquivos de apoio (necessários para rodar)

- `back/app.py`, `back/config.py`, `back/requirements.txt`, `back/.env`: inicialização e configuração
- `back/controllers/auth_controller.py`, `back/models/usuario.py`, `back/services/dois_fatores.py`, `back/forms.py`, `back/decorators.py`: login, 2FA e perfis (necessários porque a tela exige usuário logado)
- `back/services/auditoria.py`, `back/models/log_auditoria.py`: o sistema registra os eventos em log
- `front/templates/base.html`, `_campo.html`, `login.html`, `login_2fa.html`, `ativar_2fa.html`, `cadastro.html`, `dashboard.html`, `meus_dados.html`, `politica_privacidade.html`, `termos_uso.html`
- `front/static/css/style.css`, `front/static/img/logo.png`

## Como testar

1. Abra http://127.0.0.1:5000/politica-privacidade e http://127.0.0.1:5000/termos-uso (não precisa de login).
2. Tente se cadastrar sem marcar "Li e aceito…": o cadastro é recusado.
3. Cadastre-se marcando o aceite e faça login.
4. Clique em **Meus dados**: aparecem os dados guardados e a data e hora do aceite dos termos.

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
