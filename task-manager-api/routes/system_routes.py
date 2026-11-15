from datetime import datetime

from flask import Blueprint

from config.settings import API_NAME, API_VERSION


def create_system_blueprint():
    bp = Blueprint('system', __name__)

    @bp.get('/health')
    def health():
        return {'status': 'ok', 'timestamp': str(datetime.now())}

    @bp.get('/')
    def index():
        return {'message': API_NAME, 'version': API_VERSION}

    return bp
