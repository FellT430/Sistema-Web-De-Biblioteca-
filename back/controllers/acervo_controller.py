from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from sqlalchemy import or_

from models import db, Livro, Recomendacao
from decorators import perfil_requerido
from forms import AcaoForm
from services.emprestimos import motivo_para_nao_solicitar

acervo_bp = Blueprint("acervo", __name__, url_prefix="/acervo")

LIVROS_POR_PAGINA = 12


@acervo_bp.route("/")
@login_required
@perfil_requerido("aluno", "professor", "admin")
def listar():
    termo = request.args.get("q", "").strip()
    pagina = request.args.get("pagina", 1, type=int)

    consulta = Livro.query
    if termo:
        padrao = f"%{termo}%"
        consulta = consulta.filter(
            or_(
                Livro.titulo.ilike(padrao),
                Livro.autor.ilike(padrao),
                Livro.isbn.ilike(padrao),
                Livro.categoria.ilike(padrao),
            )
        )

    paginacao = consulta.order_by(Livro.titulo).paginate(
        page=pagina, per_page=LIVROS_POR_PAGINA, error_out=False
    )

    return render_template(
        "acervo/listar.html",
        livros=paginacao.items,
        paginacao=paginacao,
        termo=termo,
    )


@acervo_bp.route("/<int:livro_id>")
@login_required
@perfil_requerido("aluno", "professor", "admin")
def detalhe(livro_id):
    livro = db.get_or_404(Livro, livro_id)

    recomendacoes = (
        Recomendacao.query.filter_by(livro_id=livro.id, ativa=True)
        .order_by(Recomendacao.criado_em.desc())
        .all()
    )

    motivo_bloqueio = None
    if current_user.perfil == "aluno":
        motivo_bloqueio = motivo_para_nao_solicitar(current_user, livro)

    return render_template(
        "acervo/detalhe.html",
        livro=livro,
        recomendacoes=recomendacoes,
        voltar_q=request.args.get("q", ""),
        motivo_bloqueio=motivo_bloqueio,
        form_acao=AcaoForm(),
    )
