"""Composition root: cria a app, carrega a config, instancia dependências e registra rotas e handlers."""

import logging

from flask import Flask

from src import database
from src.config.settings import Settings, resolve_secret_key
from src.controllers.pedido_controller import PedidoController
from src.controllers.produto_controller import ProdutoController
from src.controllers.relatorio_controller import RelatorioController
from src.controllers.sistema_controller import SistemaController
from src.controllers.usuario_controller import UsuarioController
from src.middlewares.error_handler import register_error_handlers
from src.models.pedido_model import PedidoModel
from src.models.produto_model import ProdutoModel
from src.models.sistema_model import SistemaModel
from src.models.usuario_model import UsuarioModel
from src.services.notification_service import LogNotificationService
from src.views.pedido_routes import create_pedido_blueprint
from src.views.produto_routes import create_produto_blueprint
from src.views.relatorio_routes import create_relatorio_blueprint
from src.views.sistema_routes import create_sistema_blueprint
from src.views.usuario_routes import create_usuario_blueprint


def configure_logging(level):
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(settings=Settings, notifier=None):
    configure_logging(settings.LOG_LEVEL)

    app = Flask(__name__)
    app.config.from_object(settings)
    app.config["SECRET_KEY"] = resolve_secret_key(settings)

    if settings.CORS_ORIGINS:
        from flask_cors import CORS
        CORS(app, origins=settings.CORS_ORIGINS)

    database.init_app(app)

    produto_model = ProdutoModel(database.get_db)
    usuario_model = UsuarioModel(database.get_db)
    pedido_model = PedidoModel(database.get_db)
    sistema_model = SistemaModel(database.get_db, database.get_read_only_db)

    app.register_blueprint(create_sistema_blueprint(
        SistemaController(sistema_model, versao=settings.APP_VERSION, ambiente=settings.APP_ENV)))
    app.register_blueprint(create_produto_blueprint(ProdutoController(produto_model)))
    app.register_blueprint(create_usuario_blueprint(UsuarioController(usuario_model)))
    app.register_blueprint(create_pedido_blueprint(
        PedidoController(pedido_model, produto_model, notifier or LogNotificationService())))
    app.register_blueprint(create_relatorio_blueprint(RelatorioController(pedido_model)))

    register_error_handlers(app)
    return app
