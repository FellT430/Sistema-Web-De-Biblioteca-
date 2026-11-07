from flask import Blueprint, render_template, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user

from models import db, Notificacao
from forms import AcaoForm
from decorators import perfil_requerido
from services.agendador import executar_verificacao
from services.notificacoes import verificar_e_notificar

notificacoes_bp = Blueprint("notificacoes", __name__, url_prefix="/notificacoes")


def _conferir_csrf():
    if not AcaoForm().validate_on_submit():
        abort(400)


@notificacoes_bp.route("/")
@login_required
@perfil_requerido("aluno")
def listar():
    verificar_e_notificar()
    notificacoes = (
        Notificacao.query.filter_by(usuario_id=current_user.id)
        .order_by(Notificacao.lida, Notificacao.criada_em.desc())
        .limit(100)
        .all()
    )
    return render_template("notificacoes/listar.html", notificacoes=notificacoes, form_acao=AcaoForm())


@notificacoes_bp.route("/<int:notificacao_id>/lida", methods=["POST"])
@login_required
@perfil_requerido("aluno")
def marcar_lida(notificacao_id):
    _conferir_csrf()
    notificacao = db.get_or_404(Notificacao, notificacao_id)
    if notificacao.usuario_id != current_user.id:
        abort(403)
    notificacao.marcar_como_lida()
    db.session.commit()
    return redirect(url_for("notificacoes.listar"))


@notificacoes_bp.route("/marcar-todas", methods=["POST"])
@login_required
@perfil_requerido("aluno")
def marcar_todas():
    _conferir_csrf()
    Notificacao.query.filter_by(usuario_id=current_user.id, lida=False).update({"lida": True})
    db.session.commit()
    flash("Todas as notificações foram marcadas como lidas.", "info")
    return redirect(url_for("notificacoes.listar"))


@notificacoes_bp.route("/verificar-agora", methods=["POST"])
@login_required
@perfil_requerido("admin")
def verificar_agora():
    _conferir_csrf()
    resumo = executar_verificacao(current_app._get_current_object())
    flash(
        "Verificação executada: "
        f"{resumo['novos_atrasos']} empréstimo(s) marcado(s) como atrasado, "
        f"{resumo['lembretes']} lembrete(s) e {resumo['avisos_atraso']} aviso(s) de atraso enviados aos alunos.",
        "success",
    )
    return redirect(url_for("emprestimos.gerenciar", filtro="andamento"))
