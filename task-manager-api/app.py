"""Composition root: cria a aplicação, injeta dependências e registra rotas e handlers de erro."""
import logging

from flask import Flask
from flask_cors import CORS

from config.settings import Settings
from controllers.category_controller import CategoryController
from controllers.report_controller import ReportController
from controllers.task_controller import TaskController
from controllers.user_controller import UserController
from database import db
from middlewares.error_handler import register_error_handlers
from routes.category_routes import create_category_blueprint
from routes.report_routes import create_report_blueprint
from routes.system_routes import create_system_blueprint
from routes.task_routes import create_task_blueprint
from routes.user_routes import create_user_blueprint
from services.notification_service import NotificationService
from services.token_service import TokenService

log = logging.getLogger(__name__)


def create_app(settings=Settings):
    logging.basicConfig(level=settings.LOG_LEVEL, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

    app = Flask(__name__)
    app.config.from_object(settings)
    if not settings.SECRET_KEY_FROM_ENV:
        log.warning('SECRET_KEY não definida; usando chave efêmera (tokens de login expiram ao reiniciar)')
    if settings.CORS_ORIGINS:
        CORS(app, origins=settings.CORS_ORIGINS)

    db.init_app(app)

    token_service = TokenService(app.config['SECRET_KEY'], settings.TOKEN_MAX_AGE)
    app.extensions['token_service'] = token_service
    notifier = NotificationService(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        user=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        sender=settings.SMTP_SENDER,
    )

    app.register_blueprint(create_system_blueprint())
    app.register_blueprint(create_task_blueprint(TaskController(notifier)))
    app.register_blueprint(create_user_blueprint(UserController(token_service)))
    app.register_blueprint(create_report_blueprint(ReportController()))
    app.register_blueprint(create_category_blueprint(CategoryController()))
    register_error_handlers(app)

    with app.app_context():
        db.create_all()
    return app


if __name__ == '__main__':
    create_app().run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)
