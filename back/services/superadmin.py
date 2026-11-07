import logging
import os
from datetime import datetime

from models import db, Usuario

log = logging.getLogger(__name__)


def emails_superadmin(app) -> set[str]:
    return {conta["email"].lower() for conta in app.config.get("SUPERADMINS", [])}


def garantir_superadmins(app) -> None:
    for conta in app.config.get("SUPERADMINS", []):
        email = conta["email"].lower()
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario is None:
            senha = os.getenv(conta["variavel_senha"], "")
            if not senha:
                log.warning(
                    "Conta de administrador %s não criada: defina %s no .env",
                    email, conta["variavel_senha"],
                )
                continue
            usuario = Usuario(
                nome=conta["nome"],
                email=email,
                perfil="superadmin",
                ativo=True,
                aceite_termos=True,
                aceite_termos_em=datetime.now(),
            )
            usuario.set_senha(senha)
            db.session.add(usuario)
        else:
            usuario.perfil = "superadmin"
            usuario.ativo = True
    db.session.commit()
