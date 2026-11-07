import secrets
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from models import db, CodigoRecuperacao

QUANTIDADE = 8
ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
METODO_HASH = "pbkdf2:sha256:60000"


def normalizar(codigo: str) -> str:
    return "".join(c for c in (codigo or "").upper() if c.isalnum())


def _novo_codigo() -> str:
    bruto = "".join(secrets.choice(ALFABETO) for _ in range(8))
    return f"{bruto[:4]}-{bruto[4:]}"


def gerar(usuario) -> list[str]:
    apagar(usuario)
    codigos = [_novo_codigo() for _ in range(QUANTIDADE)]
    for codigo in codigos:
        db.session.add(
            CodigoRecuperacao(
                usuario_id=usuario.id,
                codigo_hash=generate_password_hash(normalizar(codigo), method=METODO_HASH),
            )
        )
    db.session.commit()
    return codigos


def apagar(usuario) -> None:
    CodigoRecuperacao.query.filter_by(usuario_id=usuario.id).delete()
    db.session.commit()


def restantes(usuario) -> int:
    return CodigoRecuperacao.query.filter_by(usuario_id=usuario.id, usado_em=None).count()


def total(usuario) -> int:
    return CodigoRecuperacao.query.filter_by(usuario_id=usuario.id).count()


def usar(usuario, codigo_digitado: str) -> bool:
    codigo = normalizar(codigo_digitado)
    if len(codigo) != 8:
        return False
    for registro in CodigoRecuperacao.query.filter_by(usuario_id=usuario.id, usado_em=None).all():
        if check_password_hash(registro.codigo_hash, codigo):
            registro.usado_em = datetime.now()
            db.session.commit()
            return True
    return False
