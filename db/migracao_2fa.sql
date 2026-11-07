-- Migração: autenticação de dois fatores (Google Authenticator)
-- Adiciona à tabela `usuarios` as colunas usadas pelo 2FA.
-- Compatível com MySQL e SQLite. Rode uma única vez em bancos já existentes.
-- (O app.py também faz isso automaticamente ao iniciar, se as colunas faltarem.)

ALTER TABLE usuarios ADD COLUMN dois_fatores_ativo BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE usuarios ADD COLUMN totp_secret VARCHAR(64) NULL;
ALTER TABLE usuarios ADD COLUMN totp_ultimo_passo BIGINT NULL;
