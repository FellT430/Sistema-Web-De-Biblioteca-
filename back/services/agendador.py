import logging
import os
from datetime import datetime

from services.auditoria import registrar, Acoes

INTERVALO_HORAS = 1

_log = logging.getLogger("agendador")
_agendador = None


def executar_verificacao(app) -> dict:
    from services.notificacoes import verificar_e_notificar

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
    global _agendador

    if os.getenv("DESATIVAR_AGENDADOR") == "1":
      return

    if app.config.get("TESTING") or _agendador is not None:
        return
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
        next_run_time=datetime.now(),
        replace_existing=True,
    )
    _agendador.start()
    _log.info("Agendador iniciado: verificação de atrasos a cada %s hora(s).", INTERVALO_HORAS)
