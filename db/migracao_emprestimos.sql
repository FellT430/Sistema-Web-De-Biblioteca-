-- Migração: empréstimos (RF13) e devoluções (RF14)
-- O app.py já cria esta tabela sozinho ao iniciar (db.create_all()).
-- Este script é só para quem preferir criar manualmente no MySQL Workbench,
-- ou para documentar a estrutura no TCC.

CREATE TABLE IF NOT EXISTS emprestimos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    aluno_id INT NOT NULL,
    livro_id INT NOT NULL,
    bibliotecario_id INT NULL,             -- quem confirmou a retirada
    bibliotecario_devolucao_id INT NULL,   -- quem registrou a devolução
    -- SOLICITADO | ATIVO | ATRASADO | DEVOLVIDO | CANCELADO
    status VARCHAR(20) NOT NULL DEFAULT 'SOLICITADO',
    data_solicitacao DATETIME NOT NULL,
    data_emprestimo DATETIME NULL,         -- confirmação da retirada
    data_prevista_devolucao DATE NULL,     -- RN43: retirada + 7 dias
    data_devolucao DATETIME NULL,          -- RN48: registrada automaticamente
    INDEX ix_emprestimos_aluno_id (aluno_id),
    INDEX ix_emprestimos_livro_id (livro_id),
    INDEX ix_emprestimos_status (status),
    CONSTRAINT fk_emprestimos_aluno FOREIGN KEY (aluno_id) REFERENCES usuarios (id) ON DELETE CASCADE,
    CONSTRAINT fk_emprestimos_livro FOREIGN KEY (livro_id) REFERENCES livros (id) ON DELETE CASCADE,
    CONSTRAINT fk_emprestimos_bibliotecario FOREIGN KEY (bibliotecario_id) REFERENCES usuarios (id),
    CONSTRAINT fk_emprestimos_bibliotecario_dev FOREIGN KEY (bibliotecario_devolucao_id) REFERENCES usuarios (id)
);
