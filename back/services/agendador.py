"""Agendador de tarefas automáticas (APScheduler) — RF15 / RN49.

Roda a verificação de atrasos e notificações em segundo plano, junto com o
Flask, sem ninguém precisar abrir uma tela:
  - uma vez logo que o sistema inicia;
  - e depois a cada INTERVALO_HORAS horas.

Rodar várias vezes no mesmo dia não duplica avisos, porque a verificação
respeita a RN50 (um aviso por empréstimo, por tipo, por dia).
"""
import logging
import os
from datetime import datetime

from services.auditoria import registrar, Acoes

INTERVALO_HORAS = 1

_log = logging.getLogger("agendador")
_agendador = None


def executar_verificacao(app) -> dict:
    """Executa a verificação dentro do contexto da aplicação e registra na auditoria."""
    from services.notificacoes import verificar_e_notificar  # import local evita import circular

    with app.app_context():
        resumo = verificar_e_notificar()
        registrar(
            Acoes.VERIFICACAO_ATRASOS,
            "Verificação automática: "
            f"{resumo['novos_atrasos']} empréstimo(s) marcado(s) como atrasado, "
            f"{resumo['lembretes']} lembrete(s) e {resumo['avisos_atraso']} aviso(s) de atraso enviados",
            email="agendador@sistema",
        )
        return resumo


def iniciar_agendador(app) -> None:
    """Liga o APScheduler. Chamado uma vez em create_app()."""
    global _agendador

    if os.getenv("DESATIVAR_AGENDADOR") == "1":
      return
  
    if app.config.get("TESTING") or _agendador is not None:
        return
    # Com debug=True o Flask roda o app duas vezes (o "reloader"); só o processo
    # filho (WERKZEUG_RUN_MAIN=true) liga o agendador, senão a tarefa rodaria em dobro.
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        _log.warning("APScheduler não instalado: rode 'pip install -r requirements.txt'.")
        return

    _agendador = BackgroundScheduler(daemon=True)
    _agendador.add_job(
        executar_verificacao,
        trigger="interval",
        hours=INTERVALO_HORAS,
        args=[app],
        id="verificar_atrasos",
        next_run_time=datetime.now(),  # roda já na inicialização
        replace_existing=True,
    )
    _agendador.start()
    _log.info("Agendador iniciado: verificação de atrasos a cada %s hora(s).", INTERVALO_HORAS)
