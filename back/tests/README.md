# Testes automatizados do LIVRO+

Os testes usam **pytest** e rodam com um banco SQLite em memória, criado do zero a cada teste.
Nenhum e-mail real é enviado, o agendador não é iniciado e a Google Books API é simulada.
O `.env` e o banco de vocês **não são alterados**.

## Instalar (uma vez)

Dentro da pasta `back`, com o venv ativado:

    pip install -r requirements-dev.txt

## Rodar os testes

    pytest

## Rodar com o relatório de cobertura

    pytest --cov=. --cov-report=term-missing --cov-report=html

O resumo aparece no terminal (linha TOTAL). O relatório detalhado fica em `htmlcov/index.html`.

## O que é testado

| Arquivo | O que cobre |
|---|---|
| test_models.py | Regras das classes: senha em hash, exemplares disponíveis, atraso, posição na fila |
| test_emprestimos.py | Solicitar, confirmar retirada, recusar, cancelar, devolver, limite e bloqueio por atraso |
| test_reservas.py | Fila de reserva, atendimento automático, pular aluno atrasado e expiração em 2 dias |
| test_notificacoes_privacidade.py | Avisos de atraso e lembretes sem repetição; exclusão de dados por anonimização (LGPD) |
| test_servicos_apoio.py | 2FA, códigos de recuperação, e-mail, Google Books (simulada), auditoria, painel e agendador |
| test_rotas.py | Integração front-end + back-end + banco: cadastro, login, permissões por perfil e fluxos completos |
