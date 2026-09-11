from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.extensions import db
from app.models import Usuario

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


@usuarios_bp.route("/")
def listar():
    usuarios = Usuario.query.order_by(Usuario.nome).all()
    return render_template("usuarios/listar.html", usuarios=usuarios)


@usuarios_bp.route("/novo", methods=["GET", "POST"])
def novo():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        matricula = request.form.get("matricula", "").strip() or None

        if not nome or not email:
            flash("Nome e e-mail são obrigatórios.", "warning")
            return redirect(url_for("usuarios.novo"))

        if Usuario.query.filter_by(email=email).first():
            flash("Já existe um usuário com esse e-mail.", "danger")
            return redirect(url_for("usuarios.novo"))

        usuario = Usuario(nome=nome, email=email, matricula=matricula)
        db.session.add(usuario)
        db.session.commit()
        flash("Usuário cadastrado com sucesso!", "success")
        return redirect(url_for("usuarios.listar"))

    return render_template("usuarios/novo.html")
