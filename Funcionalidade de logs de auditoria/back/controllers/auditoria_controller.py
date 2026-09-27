import csv
import io
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, Response
from flask_login import login_required

from models import LogAuditoria
from decorators import perfil_requerido
from services.auditoria import registrar, Acoes

auditoria_bp = Blueprint("auditoria", __name__, url_prefix="/admin/auditoria")

POR_PAGINA = 25


def _consulta_filtrada():
    filtros = {
        "acao": request.args.get("acao", "").strip(),
        "usuario": request.args.get("usuario", "").strip(),
        "resultado": request.args.get("resultado", "").strip(),
        "data_inicio": request.args.get("data_inicio", "").strip(),
        "data_fim": request.args.get("data_fim", "").strip(),
    }

    consulta = LogAuditoria.query

    if filtros["acao"]:
        consulta = consulta.filter(LogAuditoria.acao == filtros["acao"])
    if filtros["usuario"]:
        consulta = consulta.filter(LogAuditoria.usuario_email.ilike(f"%{filtros['usuario']}%"))
    if filtros["resultado"] == "sucesso":
        consulta = consulta.filter(LogAuditoria.sucesso.is_(True))
    elif filtros["resultado"] == "falha":
        consulta = consulta.filter(LogAuditoria.sucesso.is_(False))

    try:
        if filtros["data_inicio"]:
            inicio = datetime.strptime(filtros["data_inicio"], "%Y-%m-%d")
            consulta = consulta.filter(LogAuditoria.criado_em >= inicio)
        if filtros["data_fim"]:
            fim = datetime.strptime(filtros["data_fim"], "%Y-%m-%d") + timedelta(days=1)
            consulta = consulta.filter(LogAuditoria.criado_em < fim)
    except ValueError:
        pass

    return consulta.order_by(LogAuditoria.criado_em.desc(), LogAuditoria.id.desc()), filtros


@auditoria_bp.route("/")
@login_required
@perfil_requerido("admin")
def listar():
    consulta, filtros = _consulta_filtrada()
    pagina = request.args.get("pagina", 1, type=int)
    paginacao = consulta.paginate(page=pagina, per_page=POR_PAGINA, error_out=False)

    if pagina == 1:
        filtros_usados = ", ".join(f"{k}={v}" for k, v in filtros.items() if v) or "sem filtros"
        registrar(Acoes.ACESSO_AUDITORIA, f"Consultou os logs de auditoria ({filtros_usados})")

    return render_template(
        "auditoria/listar.html",
        paginacao=paginacao,
        logs=paginacao.items,
        filtros=filtros,
        acoes=Acoes.todas(),
    )


@auditoria_bp.route("/exportar.csv")
@login_required
@perfil_requerido("admin")
def exportar_csv():
    consulta, filtros = _consulta_filtrada()
    logs = consulta.all()

    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow([
        "ID", "Data/hora", "Usuário (e-mail)", "Perfil", "Ação", "Resultado",
        "Descrição", "IP", "Método", "Rota", "Navegador",
    ])
    for log in logs:
        escritor.writerow([
            log.id,
            log.criado_em.strftime("%d/%m/%Y %H:%M:%S"),
            log.usuario_email or "anônimo",
            log.usuario_perfil or "",
            log.acao,
            "Sucesso" if log.sucesso else "Falha",
            log.descricao or "",
            log.ip or "",
            log.metodo or "",
            log.rota or "",
            log.user_agent or "",
        ])

    registrar(Acoes.EXPORTACAO_AUDITORIA, f"Exportou {len(logs)} registros de auditoria em CSV")

    nome_arquivo = f"auditoria_{datetime.now():%Y%m%d_%H%M}.csv"
    return Response(
        "﻿" + saida.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"},
    )
