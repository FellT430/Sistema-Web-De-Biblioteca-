from functools import wraps

from flask import redirect, url_for, abort
from flask_login import current_user

def perfil_requerido(*perfis_permitidos):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.perfil not in perfis_permitidos:
                from services.auditoria import registrar, Acoes

                registrar(
                    Acoes.ACESSO_NEGADO,
                    f"Perfil '{current_user.perfil}' tentou acessar área restrita a: "
                    f"{', '.join(perfis_permitidos)}",
                    sucesso=False,
                )
                abort(403)
            return f(*args, **kwargs)

        return wrapper

    return decorator
