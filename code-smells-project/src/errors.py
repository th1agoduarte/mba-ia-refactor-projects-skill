"""Exceções de domínio. O error handler central as converte em respostas HTTP."""


class AppError(Exception):
    status = 400

    def __init__(self, message, status=None, com_sucesso=False, body=None):
        super().__init__(message)
        self.message = message
        self.status = status or self.status
        self.com_sucesso = com_sucesso  # inclui "sucesso": false no corpo (formato original da rota)
        self.body = body  # corpo completo, quando a rota usa outro formato de erro


class ValidationError(AppError):
    status = 400


class NotFoundError(AppError):
    status = 404


class UnauthorizedError(AppError):
    status = 401


class ForbiddenError(AppError):
    status = 403


class ServiceUnavailableError(AppError):
    status = 500
