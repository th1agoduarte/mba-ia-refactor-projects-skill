from itsdangerous import BadSignature, URLSafeTimedSerializer


class TokenService:
    """Tokens de sessão assinados com a SECRET_KEY (substituem o antigo 'fake-jwt-token-<id>')."""

    def __init__(self, secret_key, max_age):
        self._serializer = URLSafeTimedSerializer(secret_key, salt='auth-token')
        self._max_age = max_age

    def issue(self, user_id):
        return self._serializer.dumps({'user_id': user_id})

    def verify(self, token):
        """Devolve o user_id do token, ou None se a assinatura for inválida ou o token tiver expirado."""
        try:
            payload = self._serializer.loads(token, max_age=self._max_age)
        except BadSignature:
            return None
        return payload.get('user_id') if isinstance(payload, dict) else None
