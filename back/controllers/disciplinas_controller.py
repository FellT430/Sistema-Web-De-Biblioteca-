"""Controller de Disciplinas (RF10) e das recomendações feitas pelo professor (RF11).

Fluxo do professor:
  1. "Minhas disciplinas"            -> listar()
  2. Cadastra uma disciplina          -> nova()
  3. Abre a disciplina e pesquisa
     livros do acervo                 -> detalhe()
  4. Relaciona livros à disciplina    -> adicionar_livro() / remover_livro()
  5. Recomenda livros aos alunos      -> recomendar() / remover_recomendacao()

A tela do aluno com as recomendações fica em recomendacoes_controller.py.
"""
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_

from models import db, Disciplina, Livro, Recomendacao
from forms import DisciplinaForm, RecomendacaoForm, AcaoForm
from decorators import perfil_requerido
from services.auditoria import registrar, Acoes

disciplinas_bp = Blueprint("disciplinas", __name__, url_prefix="/disciplinas")

LIMITE_RESULTADOS_BUSCA = 30


def _limpar(texto):
    """Tira espaços das pontas e transforma texto vazio em None."""
    return (texto or "").strip() or None


def _disciplina_do_professor(disciplina_id):
    """Busca a disciplina e garante que ela é do professor logado.

    RN32 / CA03: o professor só pode ver e alterar as disciplinas que ele
    cadastrou. Tentativa de mexer na disciplina de outro professor gera
    registro de ACESSO_NEGADO na auditoria e erro 403.
    """
    disciplina = db.get_or_404(Disciplina, disciplina_id)
    if disciplina.professor_id != current_user.id:
        registrar(
            Acoes.ACESSO_NEGADO,
            f"Tentou acessar a disciplina #{disciplina.id} '{disciplina.nome}', "
            f"que pertence a outro professor",
            sucesso=False,
        )
        abort(403)
    return disciplina


def _conferir_csrf():
    """Valida o token CSRF dos botões de ação (POST sem campos)."""
    if not AcaoForm().validate_on_submit():
        abort(400)


# ---------------------------------------------------------------------------
# Disciplinas (RF10)
# ---------------------------------------------------------------------------
@disciplinas_bp.route("/")
@login_required
@perfil_requerido("professor")
def listar():
    disciplinas = (
        Disciplina.query.filter_by(professor_id=current_user.id)
        .order_by(Disciplina.nome)
        .all()
    )
    return render_template("disciplinas/listar.html", disciplinas=disciplinas, form_acao=AcaoForm())


@disciplinas_bp.route("/nova", methods=["GET", "POST"])
@login_required
@perfil_requerido("professor")
def nova():
    form = DisciplinaForm()

    if form.validate_on_submit():
        disciplina = Disciplina(
            nome=form.nome.data.strip(),
            codigo=_limpar(form.codigo.data),
            descricao=_limpar(form.descricao.data),
            professor_id=current_user.id,
        )
        db.session.add(disciplina)
        db.session.commit()

        registrar(
            Acoes.DISCIPLINA_CRIADA,
            f"Disciplina #{disciplina.id} '{disciplina.nome}' cadastrada",
        )
        flash("Disciplina cadastrada! Agora relacione os livros do acervo a ela.", "success")
        return redirect(url_for("disciplinas.detalhe", disciplina_id=disciplina.id))

    return render_template("disciplinas/form.html", form=form, titulo_pagina="Nova disciplina")


@disciplinas_bp.route("/<int:disciplina_id>")
@login_required
@perfil_requerido("professor")
def detalhe(disciplina_id):
    """Mostra os livros da disciplina e a busca no acervo para adicionar novos."""
    disciplina = _disciplina_do_professor(disciplina_id)
    termo = request.args.get("q", "").strip()

    # Busca no acervo, sem os livros que já estão na disciplina (RN34)
    ids_ja_relacionados = [livro.id for livro in disciplina.livros]
    consulta = Livro.query
    if ids_ja_relacionados:
        consulta = consulta.filter(Livro.id.notin_(ids_ja_relacionados))
    if termo:
        padrao = f"%{termo}%"
        consulta = consulta.filter(
            or_(Livro.titulo.ilike(padrao), Livro.autor.ilike(padrao), Livro.isbn.ilike(padrao))
        )
    livros_acervo = consulta.order_by(Livro.titulo).limit(LIMITE_RESULTADOS_BUSCA).all()

    return render_template(
        "disciplinas/detalhe.html",
        disciplina=disciplina,
        livros_acervo=livros_acervo,
        termo=termo,
        limite=LIMITE_RESULTADOS_BUSCA,
        form_acao=AcaoForm(),
    )


@disciplinas_bp.route("/<int:disciplina_id>/editar", methods=["GET", "POST"])
@login_required
@perfil_requerido("professor")
def editar(disciplina_id):
    disciplina = _disciplina_do_professor(disciplina_id)
    form = DisciplinaForm(obj=disciplina)

    if form.validate_on_submit():
        nome_antigo = disciplina.nome
        disciplina.nome = form.nome.data.strip()
        disciplina.codigo = _limpar(form.codigo.data)
        disciplina.descricao = _limpar(form.descricao.data)
        db.session.commit()

        registrar(
            Acoes.DISCIPLINA_EDITADA,
            f"Disciplina #{disciplina.id} editada (nome: '{nome_antigo}' → '{disciplina.nome}')",
        )
        flash("Disciplina atualizada!", "success")
        return redirect(url_for("disciplinas.detalhe", disciplina_id=disciplina.id))

    return render_template(
        "disciplinas/form.html", form=form, titulo_pagina="Editar disciplina", disciplina=disciplina
    )


@disciplinas_bp.route("/<int:disciplina_id>/excluir", methods=["POST"])
@login_required
@perfil_requerido("professor")
def excluir(disciplina_id):
    _conferir_csrf()
    disciplina = _disciplina_do_professor(disciplina_id)
    descricao = (
        f"Disciplina #{disciplina.id} '{disciplina.nome}' excluída "
        f"({len(disciplina.livros)} livro(s) relacionado(s))"
    )
    # Os vínculos com livros e as recomendações são apagados junto (cascade);
    # os livros continuam no acervo.
    db.session.delete(disciplina)
    db.session.commit()

    registrar(Acoes.DISCIPLINA_EXCLUIDA, descricao)
    flash("Disciplina excluída. Os livros continuam no acervo.", "info")
    return redirect(url_for("disciplinas.listar"))


@disciplinas_bp.route("/<int:disciplina_id>/livros/<int:livro_id>/adicionar", methods=["POST"])
@login_required
@perfil_requerido("professor")
def adicionar_livro(disciplina_id, livro_id):
    _conferir_csrf()
    disciplina = _disciplina_do_professor(disciplina_id)
    livro = db.get_or_404(Livro, livro_id)  # RN33: só livros do acervo

    if not disciplina.adicionar_livro(livro):  # RN34 / CA02: sem duplicidade
        flash(f"\"{livro.titulo}\" já está nesta disciplina.", "warning")
    else:
        db.session.commit()
        registrar(
            Acoes.DISCIPLINA_LIVRO_ADICIONADO,
            f"Livro #{livro.id} '{livro.titulo}' relacionado à disciplina #{disciplina.id} '{disciplina.nome}'",
        )
        flash(f"\"{livro.titulo}\" adicionado à disciplina.", "success")

    return redirect(url_for("disciplinas.detalhe", disciplina_id=disciplina.id, q=request.args.get("q") or None))


@disciplinas_bp.route("/<int:disciplina_id>/livros/<int:livro_id>/remover", methods=["POST"])
@login_required
@perfil_requerido("professor")
def remover_livro(disciplina_id, livro_id):
    _conferir_csrf()
    disciplina = _disciplina_do_professor(disciplina_id)
    livro = db.get_or_404(Livro, livro_id)

    if disciplina.remover_livro(livro):
        db.session.commit()
        registrar(
            Acoes.DISCIPLINA_LIVRO_REMOVIDO,
            f"Livro #{livro.id} '{livro.titulo}' removido da disciplina #{disciplina.id} '{disciplina.nome}'",
        )
        flash(f"\"{livro.titulo}\" removido da disciplina.", "info")

    return redirect(url_for("disciplinas.detalhe", disciplina_id=disciplina.id))


# ---------------------------------------------------------------------------
# Recomendações feitas pelo professor (RF11)
# ---------------------------------------------------------------------------
@disciplinas_bp.route(
    "/<int:disciplina_id>/livros/<int:livro_id>/recomendar", methods=["GET", "POST"]
)
@login_required
@perfil_requerido("professor")
def recomendar(disciplina_id, livro_id):
    """Cria (ou edita) a recomendação de um livro da disciplina."""
    disciplina = _disciplina_do_professor(disciplina_id)
    livro = db.get_or_404(Livro, livro_id)

    # RN35: só dá para recomendar livro que está relacionado à disciplina
    if not disciplina.possui_livro(livro):
        flash("Relacione o livro à disciplina antes de recomendá-lo.", "warning")
        return redirect(url_for("disciplinas.detalhe", disciplina_id=disciplina.id))

    recomendacao = disciplina.recomendacao_do_livro(livro)
    form = RecomendacaoForm(obj=recomendacao if recomendacao and recomendacao.ativa else None)

    if form.validate_on_submit():
        if recomendacao is None:
            recomendacao = Recomendacao(
                professor_id=current_user.id, livro_id=livro.id, disciplina_id=disciplina.id
            )
            db.session.add(recomendacao)
            acao_texto = "recomendado"
        elif recomendacao.ativa:
            acao_texto = "teve a recomendação editada"
        else:
            acao_texto = "recomendado novamente"

        recomendacao.mensagem = _limpar(form.mensagem.data)
        recomendacao.ativa = True
        recomendacao.criado_em = datetime.now()  # data da recomendação (fluxo, passo 3)
        db.session.commit()

        registrar(
            Acoes.RECOMENDACAO_CRIADA,
            f"Livro #{livro.id} '{livro.titulo}' {acao_texto} na disciplina "
            f"#{disciplina.id} '{disciplina.nome}'",
        )
        flash(f"\"{livro.titulo}\" agora aparece nas recomendações dos alunos.", "success")
        return redirect(url_for("disciplinas.detalhe", disciplina_id=disciplina.id))

    return render_template(
        "disciplinas/recomendar.html",
        form=form,
        disciplina=disciplina,
        livro=livro,
        editando=bool(recomendacao and recomendacao.ativa),
    )


@disciplinas_bp.route(
    "/<int:disciplina_id>/livros/<int:livro_id>/remover-recomendacao", methods=["POST"]
)
@login_required
@perfil_requerido("professor")
def remover_recomendacao(disciplina_id, livro_id):
    """RN38: o professor pode remover a recomendação a qualquer momento."""
    _conferir_csrf()
    disciplina = _disciplina_do_professor(disciplina_id)
    livro = db.get_or_404(Livro, livro_id)
    recomendacao = disciplina.recomendacao_do_livro(livro)

    if recomendacao and recomendacao.ativa:
        recomendacao.ativa = False
        db.session.commit()
        registrar(
            Acoes.RECOMENDACAO_REMOVIDA,
            f"Recomendação do livro #{livro.id} '{livro.titulo}' removida da disciplina "
            f"#{disciplina.id} '{disciplina.nome}'",
        )
        flash(f"Recomendação de \"{livro.titulo}\" removida.", "info")

    return redirect(url_for("disciplinas.detalhe", disciplina_id=disciplina.id))
