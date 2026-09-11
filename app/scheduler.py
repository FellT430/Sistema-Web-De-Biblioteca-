"""Job em segundo plano que marca empréstimos atrasados automaticamente.

O scheduler roda dentro do próprio processo Flask (BackgroundScheduler,
que usa uma thread separada), então não depende de nenhum usuário acessar
o sistema para a checagem acontecer.
"""
import atexit
import logging
import os
import sys
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

INTERVALO_HORAS = 1
JOB_ID = "marcar_emprestimos_atrasados"

scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")


def _esta_servindo_a_aplicacao():
    """True quando a app foi criada para de fato atender requisições
    (`python run.py` ou `flask run`), False para comandos de gerenciamento
    (`flask db migrate/upgrade`, `flask shell`, etc.).

    Sem essa checagem, comandos como `flask db upgrade` também instanciam
    a app (via create_app() no topo de run.py) e o job chegaria a rodar
    antes mesmo de uma migration terminar - por exemplo, tentando ler uma
    coluna que a própria migration em andamento ainda vai criar.
    """
    if len(sys.argv) <= 1:
        # `python run.py`: sem subcomando de CLI.
        return True
    return sys.argv[1] == "run"


def _executar_job(app):
    """Roda dentro do app context (fora de qualquer request) e nunca deixa
    uma exceção pontual (ex: banco fora do ar) derrubar o scheduler."""
    with app.app_context():
        try:
            from app.services.emprestimo_service import marcar_emprestimos_atrasados

            quantidade = marcar_emprestimos_atrasados()
            if quantidade:
                logger.info(
                    "Job de atraso: %s empréstimo(s) marcado(s) como atrasado.",
                    quantidade,
                )
        except Exception:
            logger.exception(
                "Erro ao executar o job de marcação de empréstimos atrasados."
            )


def init_scheduler(app):
    """Registra e inicia o job. Chamado uma vez a partir de create_app()."""
    if not app.config.get("SCHEDULER_ENABLED", True):
        return

    if not _esta_servindo_a_aplicacao():
        return

    if scheduler.running:
        return

    # Em modo debug, o reloader do Werkzeug sobe dois processos: o pai
    # (que só supervisiona) e o filho, marcado com WERKZEUG_RUN_MAIN=true
    # (que de fato serve a aplicação). Sem essa checagem o job rodaria
    # duplicado - uma vez por processo.
    is_reloader_child = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    if app.debug and not is_reloader_child:
        return

    scheduler.add_job(
        func=_executar_job,
        trigger="interval",
        hours=INTERVALO_HORAS,
        args=[app],
        id=JOB_ID,
        replace_existing=True,
        next_run_time=datetime.now(),
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

    def _encerrar_scheduler():
        if scheduler.running:
            scheduler.shutdown(wait=False)

    atexit.register(_encerrar_scheduler)
