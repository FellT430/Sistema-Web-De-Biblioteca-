CREATE TABLE IF NOT EXISTS reservas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    aluno_id INT NOT NULL,
    livro_id INT NOT NULL,
    emprestimo_id INT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'AGUARDANDO',
    criada_em DATETIME NOT NULL,
    atendida_em DATETIME NULL,
    INDEX ix_reservas_aluno_id (aluno_id),
    INDEX ix_reservas_livro_id (livro_id),
    INDEX ix_reservas_emprestimo_id (emprestimo_id),
    INDEX ix_reservas_status (status),
    CONSTRAINT fk_reservas_aluno FOREIGN KEY (aluno_id) REFERENCES usuarios (id) ON DELETE CASCADE,
    CONSTRAINT fk_reservas_livro FOREIGN KEY (livro_id) REFERENCES livros (id) ON DELETE CASCADE,
    CONSTRAINT fk_reservas_emprestimo FOREIGN KEY (emprestimo_id) REFERENCES emprestimos (id) ON DELETE SET NULL
);
