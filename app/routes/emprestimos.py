from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.models import Emprestimo, Exemplar, StatusExemplar, Usuario
from app.services.emprestimo_service import (
    EmprestimoJaDevolvidoError,
    EmprestimoNaoEncontradoError,
    ExemplarIndisponivelError,
    ExemplarNaoEncontradoError,
    UsuarioComAtrasoError,
    UsuarioNaoEncontradoError,
    listar_emprestimos_atrasados,
    registrar_devolucao,
    registrar_emprestimo,
)

emprestimos_bp = Blueprint("emprestimos", __name__, url_prefix="/emprestimos")


@emprestimos_bp.route("/")
def listar():
    emprestimos_ativos = (
        Emprestimo.query.filter(Emprestimo.data_devolucao.is_(None))
        .order_by(Emprestimo.data_emprestimo.desc())
        .all()
    )
    emprestimos_finalizados = (
        Emprestimo.query.filter(Emprestimo.data_devolucao.isnot(None))
        .order_by(Emprestimo.data_devolucao.desc())
        .limit(20)
        .all()
    )
    return render_template(
        "emprestimos/listar.html",
        emprestimos_ativos=emprestimos_ativos,
        emprestimos_finalizados=emprestimos_finalizados,
    )


@emprestimos_bp.route("/novo", methods=["GET", "POST"])
def novo():
    if request.method == "POST":
        # Nunca confiamos no que o front-end mostrou como "disponível":
        # registrar_emprestimo() sempre reconfere o status no banco.
        exemplar_id = request.form.get("exemplar_id", type=int)
        usuario_id = request.form.get("usuario_id", type=int)

        if not exemplar_id or not usuario_id:
            flash("Selecione um exemplar e um usuário.", "warning")
            return redirect(url_for("emprestimos.novo"))

        try:
            registrar_emprestimo(exemplar_id, usuario_id)
        except (
            ExemplarIndisponivelError,
            ExemplarNaoEncontradoError,
            UsuarioNaoEncontradoError,
            UsuarioComAtrasoError,
        ) as erro:
            flash(str(erro), "danger")
            return redirect(url_for("emprestimos.novo", exemplar_id=exemplar_id))

        flash("Empréstimo registrado com sucesso!", "success")
        return redirect(url_for("emprestimos.listar"))

    exemplar_id_preselecionado = request.args.get("exemplar_id", type=int)
    exemplares_disponiveis = (
        Exemplar.query.filter_by(status=StatusExemplar.DISPONIVEL)
        .join(Exemplar.livro)
        .order_by(Exemplar.codigo_patrimonio)
        .all()
    )
    usuarios = Usuario.query.order_by(Usuario.nome).all()
    emprestimos_atrasados = listar_emprestimos_atrasados()
    usuarios_bloqueados_ids = {e.usuario_id for e in emprestimos_atrasados}

    return render_template(
        "emprestimos/novo.html",
        exemplares=exemplares_disponiveis,
        usuarios=usuarios,
        exemplar_id_preselecionado=exemplar_id_preselecionado,
        emprestimos_atrasados=emprestimos_atrasados,
        usuarios_bloqueados_ids=usuarios_bloqueados_ids,
    )


@emprestimos_bp.route("/<int:emprestimo_id>/devolver", methods=["POST"])
def devolver(emprestimo_id):
    try:
        registrar_devolucao(emprestimo_id)
    except EmprestimoJaDevolvidoError as erro:
        flash(str(erro), "warning")
    except EmprestimoNaoEncontradoError as erro:
        flash(str(erro), "danger")
    else:
        flash("Devolução registrada com sucesso!", "success")
    return redirect(url_for("emprestimos.listar"))
