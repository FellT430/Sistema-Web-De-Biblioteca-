-- Migração: disciplinas (RF10) e recomendações (RF11)
-- O app.py já cria essas tabelas sozinho ao iniciar (db.create_all() cria
-- tabelas novas). Este script é só para quem preferir criar manualmente no
-- MySQL Workbench, ou para documentar a estrutura no TCC.

CREATE TABLE IF NOT EXISTS disciplinas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(120) NOT NULL,
    codigo VARCHAR(20) NULL,
    descricao TEXT NULL,
    professor_id INT NOT NULL,
    criado_em DATETIME NULL,
    INDEX ix_disciplinas_professor_id (professor_id),
    CONSTRAINT fk_disciplinas_professor
        FOREIGN KEY (professor_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

-- Ligação muitos-para-muitos entre disciplinas e livros (RN31).
-- A chave primária composta impede o mesmo livro duas vezes na disciplina (RN34).
CREATE TABLE IF NOT EXISTS disciplina_livros (
    disciplina_id INT NOT NULL,
    livro_id INT NOT NULL,
    adicionado_em DATETIME NULL,
    PRIMARY KEY (disciplina_id, livro_id),
    CONSTRAINT fk_disciplina_livros_disciplina
        FOREIGN KEY (disciplina_id) REFERENCES disciplinas (id) ON DELETE CASCADE,
    CONSTRAINT fk_disciplina_livros_livro
        FOREIGN KEY (livro_id) REFERENCES livros (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recomendacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    professor_id INT NOT NULL,
    livro_id INT NOT NULL,
    disciplina_id INT NOT NULL,
    mensagem VARCHAR(500) NULL,
    criado_em DATETIME NULL,
    ativa BOOLEAN NOT NULL DEFAULT 1,
    CONSTRAINT uq_recomendacao_disciplina_livro UNIQUE (disciplina_id, livro_id),
    INDEX ix_recomendacoes_professor_id (professor_id),
    INDEX ix_recomendacoes_livro_id (livro_id),
    INDEX ix_recomendacoes_disciplina_id (disciplina_id),
    CONSTRAINT fk_recomendacoes_professor
        FOREIGN KEY (professor_id) REFERENCES usuarios (id) ON DELETE CASCADE,
    CONSTRAINT fk_recomendacoes_livro
        FOREIGN KEY (livro_id) REFERENCES livros (id) ON DELETE CASCADE,
    CONSTRAINT fk_recomendacoes_disciplina
        FOREIGN KEY (disciplina_id) REFERENCES disciplinas (id) ON DELETE CASCADE
);
