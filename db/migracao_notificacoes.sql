CREATE TABLE IF NOT EXISTS notificacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    emprestimo_id INT NULL,
    tipo VARCHAR(30) NOT NULL,
    mensagem VARCHAR(255) NOT NULL,
    data_referencia DATE NOT NULL,
    criada_em DATETIME NOT NULL,
    lida BOOLEAN NOT NULL DEFAULT 0,
    CONSTRAINT uq_notificacao_emprestimo_tipo_dia UNIQUE (emprestimo_id, tipo, data_referencia),
    INDEX ix_notificacoes_usuario_id (usuario_id),
    INDEX ix_notificacoes_emprestimo_id (emprestimo_id),
    CONSTRAINT fk_notificacoes_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE,
    CONSTRAINT fk_notificacoes_emprestimo FOREIGN KEY (emprestimo_id) REFERENCES emprestimos (id) ON DELETE CASCADE
);
