import os, time
os.environ["TZ"] = "America/Sao_Paulo"
time.tzset()
from datetime import datetime

os.environ["DESATIVAR_AGENDADOR"] = "1"

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from apscheduler.schedulers.blocking import BlockingScheduler

from app import app
from services.agendador import executar_verificacao, INTERVALO_HORAS

agendador = BlockingScheduler()
agendador.add_job(
    executar_verificacao,
    trigger="interval",
    hours=INTERVALO_HORAS,
    args=[app],
    id="verificar_atrasos",
    next_run_time=datetime.now(),
)

print(f"Agendador iniciado: verificação a cada {INTERVALO_HORAS} hora(s).", flush=True)
agendador.start()
