"""Autorização de operações administrativas.

Aceita `Authorization: Bearer <credencial>`, onde a credencial é:
- o ADMIN_TOKEN da config (comparação em tempo constante), ou
- o token devolvido por POST /login de um usuário ativo com papel admin.
"""
import hmac
from functools import wraps

from flask import current_app, request

from middlewares.error_handler import ForbiddenError, UnauthorizedError
from models.user import User


def _bearer_token():
    scheme, _, token = request.headers.get('Authorization', '').partition(' ')
    return token.strip() if scheme.lower() == 'bearer' else ''


def authorize_admin():
    token = _bearer_token()
    if not token:
        raise UnauthorizedError('Credencial de administrador ausente')

    admin_token = current_app.config.get('ADMIN_TOKEN')
    if admin_token and hmac.compare_digest(token.encode(), admin_token.encode()):
        return

    user_id = current_app.extensions['token_service'].verify(token)
    user = User.get(user_id) if user_id is not None else None
    if user is None or not user.active:
        raise UnauthorizedError('Credencial inválida ou expirada')
    if not user.is_admin():
        raise ForbiddenError('Acesso restrito a administradores')


def authorize_self_or_admin(user_id):
    """Alterar um usuário exige o token do próprio usuário (POST /login) ou credencial de administrador."""
    token = _bearer_token()
    if not token:
        raise UnauthorizedError('Credencial ausente')

    admin_token = current_app.config.get('ADMIN_TOKEN')
    if admin_token and hmac.compare_digest(token.encode(), admin_token.encode()):
        return

    caller_id = current_app.extensions['token_service'].verify(token)
    caller = User.get(caller_id) if caller_id is not None else None
    if caller is None or not caller.active:
        raise UnauthorizedError('Credencial inválida ou expirada')
    if caller.id != user_id and not caller.is_admin():
        raise ForbiddenError('Só o próprio usuário ou um administrador pode alterar este usuário')


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        authorize_admin()
        return view(*args, **kwargs)

    return wrapper
