from datetime import datetime

from models import db

class Livro(db.Model):
    __tablename__ = "livros"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(150), nullable=False)
    isbn = db.Column(db.String(20), nullable=True)
    editora = db.Column(db.String(120), nullable=True)
    ano_publicacao = db.Column(db.Integer, nullable=True)
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    sinopse = db.Column(db.Text, nullable=True)
    categoria = db.Column(db.String(150), nullable=True)
    capa_url = db.Column(db.String(500), nullable=True)
    google_books_id = db.Column(db.String(50), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Livro {self.titulo}>"
