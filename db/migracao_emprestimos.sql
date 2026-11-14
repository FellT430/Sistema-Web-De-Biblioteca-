CREATE TABLE IF NOT EXISTS emprestimos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    aluno_id INT NOT NULL,
    livro_id INT NOT NULL,
    bibliotecario_id INT NULL,
    bibliotecario_devolucao_id INT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'SOLICITADO',
    data_solicitacao DATETIME NOT NULL,
    data_emprestimo DATETIME NULL,
    data_prevista_devolucao DATE NULL,
    data_devolucao DATETIME NULL,
    INDEX ix_emprestimos_aluno_id (aluno_id),
    INDEX ix_emprestimos_livro_id (livro_id),
    INDEX ix_emprestimos_status (status),
    CONSTRAINT fk_emprestimos_aluno FOREIGN KEY (aluno_id) REFERENCES usuarios (id) ON DELETE CASCADE,
    CONSTRAINT fk_emprestimos_livro FOREIGN KEY (livro_id) REFERENCES livros (id) ON DELETE CASCADE,
    CONSTRAINT fk_emprestimos_bibliotecario FOREIGN KEY (bibliotecario_id) REFERENCES usuarios (id),
    CONSTRAINT fk_emprestimos_bibliotecario_dev FOREIGN KEY (bibliotecario_devolucao_id) REFERENCES usuarios (id)
);
