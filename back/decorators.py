from functools import wraps

from flask import redirect, url_for, abort
from flask_login import current_user


def perfil_requerido(*perfis_permitidos):
    """Decorator simples de controle de acesso por perfil (RBAC).

    Uso: @perfil_requerido("admin") ou @perfil_requerido("admin", "professor")

    Tentativas de acesso sem permissão são registradas na auditoria
    (ação ACESSO_NEGADO) antes de retornar o erro 403.
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.perfil not in perfis_permitidos:
                # Import local para evitar import circular
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
