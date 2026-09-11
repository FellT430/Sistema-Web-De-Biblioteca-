from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.extensions import db
from app.models import Exemplar, Livro, StatusExemplar

exemplares_bp = Blueprint("exemplares", __name__, url_prefix="/exemplares")


@exemplares_bp.route("/")
def listar():
    exemplares = (
        Exemplar.query.join(Exemplar.livro)
        .order_by(Livro.titulo, Exemplar.codigo_patrimonio)
        .all()
    )
    return render_template(
        "exemplares/listar.html", exemplares=exemplares, StatusExemplar=StatusExemplar
    )


@exemplares_bp.route("/novo", methods=["GET", "POST"])
def novo():
    if request.method == "POST":
        livro_id = request.form.get("livro_id", type=int)
        codigo_patrimonio = request.form.get("codigo_patrimonio", "").strip()

        if not livro_id or not codigo_patrimonio:
            flash("Selecione o livro e informe o código de patrimônio.", "warning")
            return redirect(url_for("exemplares.novo"))

        if Exemplar.query.filter_by(codigo_patrimonio=codigo_patrimonio).first():
            flash("Já existe um exemplar com esse código de patrimônio.", "danger")
            return redirect(url_for("exemplares.novo"))

        exemplar = Exemplar(
            livro_id=livro_id,
            codigo_patrimonio=codigo_patrimonio,
            status=StatusExemplar.DISPONIVEL,
        )
        db.session.add(exemplar)
        db.session.commit()
        flash("Exemplar cadastrado com sucesso!", "success")
        return redirect(url_for("exemplares.listar"))

    livros = Livro.query.order_by(Livro.titulo).all()
    if not livros:
        flash("Cadastre um livro antes de cadastrar um exemplar.", "warning")
        return redirect(url_for("livros.novo"))

    return render_template("exemplares/novo.html", livros=livros)
