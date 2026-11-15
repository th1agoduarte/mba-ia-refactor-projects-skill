"""Exceções de domínio e tratamento de erro centralizado (formato {"error": "..."})."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from database import db

log = logging.getLogger(__name__)


class AppError(Exception):
    status = 400

    def __init__(self, message, status=None):
        super().__init__(message)
        self.message = message
        if status is not None:
            self.status = status


class ValidationError(AppError):
    status = 400


class UnauthorizedError(AppError):
    status = 401


class ForbiddenError(AppError):
    status = 403


class NotFoundError(AppError):
    status = 404


class ConflictError(AppError):
    status = 409


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error):
        db.session.rollback()
        return jsonify({'error': error.message}), error.status

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        # 404 de rota inexistente, 405, 415 etc. mantêm o status e a resposta padrão do Flask.
        return error

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        db.session.rollback()
        log.exception('Erro não tratado')
        return jsonify({'error': 'Erro interno'}), 500
