from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required

from models import db, Livro
from forms import LivroForm
from decorators import perfil_requerido

livros_bp = Blueprint("livros", __name__, url_prefix="/livros")


@livros_bp.route("/")
@login_required
@perfil_requerido("admin")
def listar():
    livros = Livro.query.order_by(Livro.titulo).all()
    return render_template("livros/listar.html", livros=livros)


@livros_bp.route("/novo", methods=["GET", "POST"])
@login_required
@perfil_requerido("admin")
def novo():
    form = LivroForm()

    if form.validate_on_submit():
        livro = Livro(
            titulo=form.titulo.data.strip(),
            autor=form.autor.data.strip(),
            isbn=(form.isbn.data or "").strip() or None,
            editora=(form.editora.data or "").strip() or None,
            ano_publicacao=form.ano_publicacao.data,
            quantidade=form.quantidade.data,
        )
        db.session.add(livro)
        db.session.commit()

        flash("Livro cadastrado com sucesso!", "success")
        return redirect(url_for("livros.listar"))

    return render_template("livros/form.html", form=form, titulo_pagina="Novo livro")


@livros_bp.route("/<int:livro_id>/editar", methods=["GET", "POST"])
@login_required
@perfil_requerido("admin")
def editar(livro_id):
    livro = Livro.query.get_or_404(livro_id)
    form = LivroForm(obj=livro)

    if form.validate_on_submit():
        livro.titulo = form.titulo.data.strip()
        livro.autor = form.autor.data.strip()
        livro.isbn = (form.isbn.data or "").strip() or None
        livro.editora = (form.editora.data or "").strip() or None
        livro.ano_publicacao = form.ano_publicacao.data
        livro.quantidade = form.quantidade.data

        db.session.commit()

        flash("Livro atualizado com sucesso!", "success")
        return redirect(url_for("livros.listar"))

    return render_template("livros/form.html", form=form, titulo_pagina="Editar livro", livro=livro)


@livros_bp.route("/<int:livro_id>/excluir", methods=["POST"])
@login_required
@perfil_requerido("admin")
def excluir(livro_id):
    livro = Livro.query.get_or_404(livro_id)
    db.session.delete(livro)
    db.session.commit()

    flash("Livro excluído com sucesso!", "info")
    return redirect(url_for("livros.listar"))
