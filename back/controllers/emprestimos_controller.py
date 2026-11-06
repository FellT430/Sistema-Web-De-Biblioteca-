from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_

from models import db, Emprestimo, StatusEmprestimo, Livro, Usuario
from forms import AcaoForm
from decorators import perfil_requerido
from services import emprestimos as servico
from services.emprestimos import RegraEmprestimoError
from services.auditoria import registrar, Acoes
from services.notificacoes import notificar_devolucao, verificar_e_notificar

emprestimos_bp = Blueprint("emprestimos", __name__, url_prefix="/emprestimos")


def _conferir_csrf():
    if not AcaoForm().validate_on_submit():
        abort(400)


def _descricao(emprestimo):
    return (
        f"Empréstimo #{emprestimo.id}: livro #{emprestimo.livro.id} '{emprestimo.livro.titulo}' "
        f"para {emprestimo.aluno.nome} ({emprestimo.aluno.email})"
    )


@emprestimos_bp.route("/solicitar/<int:livro_id>", methods=["POST"])
@login_required
@perfil_requerido("aluno")
def solicitar(livro_id):
    _conferir_csrf()
    livro = db.get_or_404(Livro, livro_id)

    try:
        emprestimo = servico.solicitar(current_user, livro)
    except RegraEmprestimoError as erro:
        registrar(
            Acoes.EMPRESTIMO_RECUSADO_REGRA,
            f"Solicitação do livro #{livro.id} '{livro.titulo}' recusada: {erro}",
            sucesso=False,
        )
        flash(str(erro), "danger")
        return redirect(url_for("acervo.detalhe", livro_id=livro.id))

    registrar(Acoes.EMPRESTIMO_SOLICITADO, f"{_descricao(emprestimo)} solicitado")
    flash(
        f"Solicitação de \"{livro.titulo}\" enviada! Retire o livro na biblioteca; "
        "o prazo de devolução começa a contar na retirada.",
        "success",
    )
    return redirect(url_for("emprestimos.meus"))


@emprestimos_bp.route("/meus")
@login_required
@perfil_requerido("aluno")
def meus():
    verificar_e_notificar()
    emprestimos = (
        Emprestimo.query.filter_by(aluno_id=current_user.id)
        .order_by(Emprestimo.data_solicitacao.desc())
        .all()
    )
    em_aberto = [e for e in emprestimos if e.status not in StatusEmprestimo.FINAIS]
    historico = [e for e in emprestimos if e.status in StatusEmprestimo.FINAIS]

    return render_template(
        "emprestimos/meus.html",
        em_aberto=em_aberto,
        historico=historico,
        Status=StatusEmprestimo,
        form_acao=AcaoForm(),
    )


@emprestimos_bp.route("/<int:emprestimo_id>/cancelar", methods=["POST"])
@login_required
@perfil_requerido("aluno")
def cancelar(emprestimo_id):
    _conferir_csrf()
    emprestimo = db.get_or_404(Emprestimo, emprestimo_id)

    if emprestimo.aluno_id != current_user.id:
        registrar(
            Acoes.ACESSO_NEGADO,
            f"Tentou cancelar o empréstimo #{emprestimo.id}, que pertence a outro aluno",
            sucesso=False,
        )
        abort(403)

    try:
        servico.cancelar_solicitacao(emprestimo, current_user)
    except RegraEmprestimoError as erro:
        flash(str(erro), "warning")
        return redirect(url_for("emprestimos.meus"))

    registrar(Acoes.EMPRESTIMO_CANCELADO, f"{_descricao(emprestimo)} cancelado pelo aluno")
    flash("Solicitação cancelada.", "info")
    return redirect(url_for("emprestimos.meus"))


FILTROS = {
    "pendentes": ("Aguardando retirada", [StatusEmprestimo.SOLICITADO]),
    "andamento": ("Com o aluno", [StatusEmprestimo.ATIVO, StatusEmprestimo.ATRASADO]),
    "atrasados": ("Atrasados", [StatusEmprestimo.ATRASADO]),
    "historico": ("Histórico", [StatusEmprestimo.DEVOLVIDO, StatusEmprestimo.CANCELADO]),
}


@emprestimos_bp.route("/")
@login_required
@perfil_requerido("admin")
def gerenciar():
    verificar_e_notificar()

    filtro = request.args.get("filtro", "pendentes")
    if filtro not in FILTROS:
        filtro = "pendentes"
    termo = request.args.get("q", "").strip()

    contagens = {
        chave: Emprestimo.query.filter(Emprestimo.status.in_(status)).count()
        for chave, (_, status) in FILTROS.items()
    }

    consulta = (
        Emprestimo.query.join(Usuario, Emprestimo.aluno_id == Usuario.id)
        .join(Livro, Emprestimo.livro_id == Livro.id)
        .filter(Emprestimo.status.in_(FILTROS[filtro][1]))
    )
    if termo:
        padrao = f"%{termo}%"
        consulta = consulta.filter(
            or_(
                Usuario.nome.ilike(padrao),
                Usuario.email.ilike(padrao),
                Livro.titulo.ilike(padrao),
                Livro.isbn.ilike(padrao),
            )
        )

    if filtro == "historico":
        consulta = consulta.order_by(Emprestimo.data_solicitacao.desc())
    elif filtro == "pendentes":
        consulta = consulta.order_by(Emprestimo.data_solicitacao)
    else:
        consulta = consulta.order_by(Emprestimo.data_prevista_devolucao)

    return render_template(
        "emprestimos/gerenciar.html",
        emprestimos=consulta.all(),
        filtro=filtro,
        filtros=FILTROS,
        contagens=contagens,
        termo=termo,
        Status=StatusEmprestimo,
        form_acao=AcaoForm(),
    )


def _acao_bibliotecario(emprestimo_id, funcao, acao_auditoria, texto_auditoria, mensagem, depois=None):
    _conferir_csrf()
    emprestimo = db.get_or_404(Emprestimo, emprestimo_id)
    voltar = url_for(
        "emprestimos.gerenciar",
        filtro=request.args.get("filtro") or None,
        q=request.args.get("q") or None,
    )

    try:
        funcao(emprestimo, current_user)
    except RegraEmprestimoError as erro:
        registrar(acao_auditoria, f"{_descricao(emprestimo)}: operação recusada ({erro})", sucesso=False)
        flash(str(erro), "danger")
        return redirect(voltar)

    registrar(acao_auditoria, f"{_descricao(emprestimo)} {texto_auditoria(emprestimo)}")
    if depois:
        depois(emprestimo)
    flash(mensagem(emprestimo), "success")
    return redirect(voltar)


@emprestimos_bp.route("/<int:emprestimo_id>/confirmar", methods=["POST"])
@login_required
@perfil_requerido("admin")
def confirmar(emprestimo_id):
    return _acao_bibliotecario(
        emprestimo_id,
        servico.confirmar_retirada,
        Acoes.EMPRESTIMO_CONFIRMADO,
        lambda e: f"retirado; devolução prevista para {e.data_prevista_devolucao.strftime('%d/%m/%Y')}",
        lambda e: (
            f"Retirada confirmada. {e.aluno.nome} deve devolver "
            f"\"{e.livro.titulo}\" até {e.data_prevista_devolucao.strftime('%d/%m/%Y')}."
        ),
    )


@emprestimos_bp.route("/<int:emprestimo_id>/recusar", methods=["POST"])
@login_required
@perfil_requerido("admin")
def recusar(emprestimo_id):
    return _acao_bibliotecario(
        emprestimo_id,
        servico.recusar_solicitacao,
        Acoes.EMPRESTIMO_RECUSADO,
        lambda e: "recusado pelo bibliotecário",
        lambda e: "Solicitação recusada. O exemplar voltou a ficar disponível.",
    )


@emprestimos_bp.route("/<int:emprestimo_id>/devolver", methods=["POST"])
@login_required
@perfil_requerido("admin")
def devolver(emprestimo_id):
    return _acao_bibliotecario(
        emprestimo_id,
        servico.registrar_devolucao,
        Acoes.DEVOLUCAO_REGISTRADA,
        lambda e: "devolvido" + (f" com {e.dias_atraso()} dia(s) de atraso" if e.devolvido_com_atraso else " no prazo"),
        lambda e: (
            f"Devolução de \"{e.livro.titulo}\" registrada"
            + (f" com {e.dias_atraso()} dia(s) de atraso." if e.devolvido_com_atraso else " dentro do prazo.")
        ),
        depois=notificar_devolucao,
    )
