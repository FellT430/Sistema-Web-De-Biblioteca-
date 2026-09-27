
ALTER TABLE usuarios ADD COLUMN dois_fatores_ativo BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE usuarios ADD COLUMN totp_secret VARCHAR(64) NULL;
ALTER TABLE usuarios ADD COLUMN totp_ultimo_passo BIGINT NULL;
