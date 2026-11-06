from flask import Blueprint, render_template
from flask_login import login_required

from models import Disciplina, Recomendacao, Usuario
from decorators import perfil_requerido

recomendacoes_bp = Blueprint("recomendacoes", __name__, url_prefix="/recomendacoes")


@recomendacoes_bp.route("/")
@login_required
@perfil_requerido("aluno", "professor", "admin")
def listar():
    recomendacoes = (
        Recomendacao.query.filter_by(ativa=True)
        .join(Disciplina, Recomendacao.disciplina_id == Disciplina.id)
        .join(Usuario, Disciplina.professor_id == Usuario.id)
        .order_by(Disciplina.nome, Recomendacao.criado_em.desc())
        .all()
    )

    por_disciplina = {}
    for recomendacao in recomendacoes:
        por_disciplina.setdefault(recomendacao.disciplina, []).append(recomendacao)

    return render_template("recomendacoes/listar.html", por_disciplina=por_disciplina)
