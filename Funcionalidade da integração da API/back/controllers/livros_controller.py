from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required

from models import db, Livro
from forms import LivroForm
from decorators import perfil_requerido
from services.google_books import buscar_livros, GoogleBooksError
from services.auditoria import registrar, Acoes

livros_bp = Blueprint("livros", __name__, url_prefix="/livros")

CAMPOS_AUDITADOS = {
    "titulo": "título",
    "autor": "autor",
    "isbn": "ISBN",
    "editora": "editora",
    "ano_publicacao": "ano",
    "quantidade": "quantidade",
    "sinopse": "sinopse",
    "categoria": "categoria",
    "capa_url": "capa",
}


def _resumo(valor, limite=40):
    texto = "vazio" if valor in (None, "") else str(valor)
    return texto if len(texto) <= limite else texto[:limite] + "…"


@livros_bp.route("/")
@login_required
@perfil_requerido("admin")
def listar():
    livros = Livro.query.order_by(Livro.titulo).all()
    return render_template("livros/listar.html", livros=livros)


@livros_bp.route("/buscar-google-books")
@login_required
@perfil_requerido("admin")
def buscar_google_books():
    termo = request.args.get("q", "").strip()
    por_isbn = request.args.get("por_isbn") == "1"

    if not termo:
        return jsonify({"erro": "Informe um ISBN ou um título para buscar."}), 400

    try:
        resultados = buscar_livros(termo, por_isbn=por_isbn)
    except GoogleBooksError as erro:
        registrar(
            Acoes.BUSCA_GOOGLE_BOOKS,
            f"Busca por {'ISBN' if por_isbn else 'título'} '{termo}' falhou: {erro}",
            sucesso=False,
        )
        return jsonify({"erro": str(erro)}), 502

    registrar(
        Acoes.BUSCA_GOOGLE_BOOKS,
        f"Busca por {'ISBN' if por_isbn else 'título'} '{termo}' ({len(resultados)} resultados)",
    )

    return jsonify({"resultados": resultados})


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
            sinopse=(form.sinopse.data or "").strip() or None,
            categoria=(form.categoria.data or "").strip() or None,
            capa_url=(form.capa_url.data or "").strip() or None,
            google_books_id=(form.google_books_id.data or "").strip() or None,
        )
        db.session.add(livro)
        db.session.commit()

        registrar(
            Acoes.LIVRO_CRIADO,
            f"Livro #{livro.id} '{livro.titulo}' de {livro.autor} cadastrado "
            f"({livro.quantidade} exemplar(es))",
        )

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
        valores_antigos = {campo: getattr(livro, campo) for campo in CAMPOS_AUDITADOS}

        livro.titulo = form.titulo.data.strip()
        livro.autor = form.autor.data.strip()
        livro.isbn = (form.isbn.data or "").strip() or None
        livro.editora = (form.editora.data or "").strip() or None
        livro.ano_publicacao = form.ano_publicacao.data
        livro.quantidade = form.quantidade.data
        livro.sinopse = (form.sinopse.data or "").strip() or None
        livro.categoria = (form.categoria.data or "").strip() or None
        livro.capa_url = (form.capa_url.data or "").strip() or None
        livro.google_books_id = (form.google_books_id.data or "").strip() or None

        db.session.commit()

        alteracoes = [
            f"{rotulo}: {_resumo(valores_antigos[campo])} → {_resumo(getattr(livro, campo))}"
            for campo, rotulo in CAMPOS_AUDITADOS.items()
            if valores_antigos[campo] != getattr(livro, campo)
        ]
        registrar(
            Acoes.LIVRO_EDITADO,
            f"Livro #{livro.id} '{livro.titulo}' editado. "
            + ("; ".join(alteracoes) if alteracoes else "Nenhum campo alterado."),
        )

        flash("Livro atualizado com sucesso!", "success")
        return redirect(url_for("livros.listar"))

    return render_template("livros/form.html", form=form, titulo_pagina="Editar livro", livro=livro)


@livros_bp.route("/<int:livro_id>/excluir", methods=["POST"])
@login_required
@perfil_requerido("admin")
def excluir(livro_id):
    livro = Livro.query.get_or_404(livro_id)
    descricao = (
        f"Livro #{livro.id} '{livro.titulo}' de {livro.autor} excluído "
        f"(ISBN: {livro.isbn or '-'}, {livro.quantidade} exemplar(es))"
    )
    db.session.delete(livro)
    db.session.commit()

    registrar(Acoes.LIVRO_EXCLUIDO, descricao)

    flash("Livro excluído com sucesso!", "info")
    return redirect(url_for("livros.listar"))
