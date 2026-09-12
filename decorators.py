from functools import wraps

from flask import redirect, url_for, abort
from flask_login import current_user


def perfil_requerido(*perfis_permitidos):
    """Decorator simples de controle de acesso por perfil (RBAC).

    Uso: @perfil_requerido("admin") ou @perfil_requerido("admin", "professor")
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.perfil not in perfis_permitidos:
                abort(403)
            return f(*args, **kwargs)

        return wrapper

    return decorator
