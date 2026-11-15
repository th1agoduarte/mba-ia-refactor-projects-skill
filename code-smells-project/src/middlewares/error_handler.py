"""Tratamento de erro centralizado: exceções de domínio → JSON; o resto → 500 genérico com log."""

import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from src.errors import AppError

log = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error):
        if error.body is not None:
            return jsonify(error.body), error.status
        body = {"erro": error.message}
        if error.com_sucesso:
            body["sucesso"] = False
        return jsonify(body), error.status

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        return error  # 404/405 etc. do Flask seguem com o status e o corpo padrão

    @app.errorhandler(Exception)
    def handle_unexpected(_error):
        log.exception("Erro não tratado")
        return jsonify({"erro": "Erro interno do servidor"}), 500
