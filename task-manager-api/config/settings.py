"""Configuração da aplicação (variáveis de ambiente) e constantes de domínio."""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

# Carrega só o .env do próprio projeto (load_dotenv() sem caminho subiria diretórios).
load_dotenv(Path(__file__).resolve().parent.parent / '.env')


def _env_int(name, default):
    return int(os.environ.get(name, default))


def _env_list(name, default=''):
    return [item.strip() for item in os.environ.get(name, default).split(',') if item.strip()]


class Settings:
    """Valores lidos do ambiente. Nenhum segredo literal: ausente = gerado em runtime ou desabilitado."""

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///tasks.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY_FROM_ENV = bool(os.environ.get('SECRET_KEY'))
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', '')
    TOKEN_MAX_AGE = _env_int('TOKEN_MAX_AGE', '28800')

    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'
    HOST = os.environ.get('HOST', '0.0.0.0')  # mesmo bind do legado; debug segue desligado
    PORT = _env_int('PORT', '5000')
    CORS_ORIGINS = _env_list('CORS_ORIGINS', '*')  # padrão do legado: todas as origens; restrinja por env
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

    SMTP_HOST = os.environ.get('SMTP_HOST', '')
    SMTP_PORT = _env_int('SMTP_PORT', '587')
    SMTP_USER = os.environ.get('SMTP_USER', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_SENDER = os.environ.get('SMTP_SENDER', '')


API_NAME = 'Task Manager API'
API_VERSION = '1.0'

# Tasks
STATUS_PENDING = 'pending'
STATUS_IN_PROGRESS = 'in_progress'
STATUS_DONE = 'done'
STATUS_CANCELLED = 'cancelled'
VALID_STATUSES = (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_DONE, STATUS_CANCELLED)
CLOSED_STATUSES = (STATUS_DONE, STATUS_CANCELLED)

PRIORITY_MIN = 1
PRIORITY_MAX = 5
DEFAULT_PRIORITY = 3
HIGH_PRIORITY_MAX = 2
PRIORITY_LABELS = {1: 'critical', 2: 'high', 3: 'medium', 4: 'low', 5: 'minimal'}

TITLE_MIN_LENGTH = 3
TITLE_MAX_LENGTH = 200
DATE_FORMAT = '%Y-%m-%d'
RECENT_ACTIVITY_DAYS = 7

# Usuários
ROLE_USER = 'user'
ROLE_ADMIN = 'admin'
ROLE_MANAGER = 'manager'
VALID_ROLES = (ROLE_USER, ROLE_ADMIN, ROLE_MANAGER)
DEFAULT_ROLE = ROLE_USER
PASSWORD_MIN_LENGTH = 4
EMAIL_PATTERN = r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$'

# Categorias
DEFAULT_CATEGORY_COLOR = '#000000'
COLOR_PATTERN = r'^#[0-9a-fA-F]{6}$'
