"""Autorização de endpoints administrativos via header X-Admin-Token (valor vem da config)."""

import hmac
from functools import wraps

from flask import current_app, request

from src.errors import ForbiddenError, UnauthorizedError

ADMIN_TOKEN_HEADER = "X-Admin-Token"


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        esperado = current_app.config.get("ADMIN_TOKEN")
        if not esperado:
            raise ForbiddenError("Endpoint administrativo desabilitado (defina ADMIN_TOKEN)")
        recebido = request.headers.get(ADMIN_TOKEN_HEADER, "")
        if not hmac.compare_digest(recebido.encode(), esperado.encode()):
            raise UnauthorizedError("Credencial de administrador inválida")
        return view(*args, **kwargs)

    return wrapper
