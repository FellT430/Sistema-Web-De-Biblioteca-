from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.extensions import db
from app.models import Livro

livros_bp = Blueprint("livros", __name__, url_prefix="/livros")


@livros_bp.route("/")
def listar():
    livros = Livro.query.order_by(Livro.titulo).all()
    return render_template("livros/listar.html", livros=livros)


@livros_bp.route("/novo", methods=["GET", "POST"])
def novo():
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        autor = request.form.get("autor", "").strip()
        isbn = request.form.get("isbn", "").strip() or None
        ano_publicacao = request.form.get("ano_publicacao", type=int)

        if not titulo or not autor:
            flash("Título e autor são obrigatórios.", "warning")
            return redirect(url_for("livros.novo"))

        livro = Livro(
            titulo=titulo, autor=autor, isbn=isbn, ano_publicacao=ano_publicacao
        )
        db.session.add(livro)
        db.session.commit()
        flash("Livro cadastrado com sucesso!", "success")
        return redirect(url_for("livros.listar"))

    return render_template("livros/novo.html")
