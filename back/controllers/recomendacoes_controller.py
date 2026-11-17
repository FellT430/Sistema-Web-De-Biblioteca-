from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import or_

from models import Disciplina, Recomendacao, Usuario
from decorators import perfil_requerido

recomendacoes_bp = Blueprint("recomendacoes", __name__, url_prefix="/recomendacoes")


@recomendacoes_bp.route("/")
@login_required
@perfil_requerido("aluno", "professor", "admin")
def listar():
    busca = request.args.get("q", "").strip()

    consulta = (
        Recomendacao.query.filter_by(ativa=True)
        .join(Disciplina, Recomendacao.disciplina_id == Disciplina.id)
        .join(Usuario, Disciplina.professor_id == Usuario.id)
    )
    if busca:
        termo = "%" + busca.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        consulta = consulta.filter(
            or_(
                Disciplina.nome.ilike(termo, escape="\\"),
                Disciplina.codigo.ilike(termo, escape="\\"),
            )
        )
    recomendacoes = consulta.order_by(
        Disciplina.nome, Recomendacao.criado_em.desc()
    ).all()

    por_disciplina = {}
    for recomendacao in recomendacoes:
        por_disciplina.setdefault(recomendacao.disciplina, []).append(recomendacao)

    return render_template(
        "recomendacoes/listar.html", por_disciplina=por_disciplina, busca=busca
    )
