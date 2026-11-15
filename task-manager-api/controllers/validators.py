"""Validações de entrada reutilizadas por create e update. Levantam ValidationError (400)."""
import re
from datetime import datetime

from config.settings import (
    COLOR_PATTERN,
    DATE_FORMAT,
    EMAIL_PATTERN,
    PASSWORD_MIN_LENGTH,
    PRIORITY_MAX,
    PRIORITY_MIN,
    TITLE_MAX_LENGTH,
    TITLE_MIN_LENGTH,
    VALID_ROLES,
    VALID_STATUSES,
)
from middlewares.error_handler import ValidationError


def require_body(data):
    if not data or not isinstance(data, dict):
        raise ValidationError('Dados inválidos')
    return data


def require_text(value, message):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(message)
    return value


def validate_title(title):
    if not isinstance(title, str):
        raise ValidationError('Título inválido')
    if len(title) < TITLE_MIN_LENGTH:
        raise ValidationError('Título muito curto')
    if len(title) > TITLE_MAX_LENGTH:
        raise ValidationError('Título muito longo')
    return title


def validate_status(status):
    if status not in VALID_STATUSES:
        raise ValidationError('Status inválido')
    return status


def validate_priority(priority):
    is_integer = isinstance(priority, int) and not isinstance(priority, bool)
    if not is_integer or not PRIORITY_MIN <= priority <= PRIORITY_MAX:
        raise ValidationError(f'Prioridade deve ser entre {PRIORITY_MIN} e {PRIORITY_MAX}')
    return priority


def parse_date(value, message):
    if not isinstance(value, str):
        raise ValidationError(message)
    try:
        return datetime.strptime(value, DATE_FORMAT)
    except ValueError:
        raise ValidationError(message) from None


def normalize_tags(tags):
    if tags is None or isinstance(tags, str):
        return tags
    if isinstance(tags, list):
        return ','.join(str(tag) for tag in tags)
    raise ValidationError('Tags inválidas')


def parse_int(value, message):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(message) from None


def validate_email(email):
    if not isinstance(email, str) or not re.match(EMAIL_PATTERN, email):
        raise ValidationError('Email inválido')
    return email


def validate_password(password, message):
    if not isinstance(password, str) or len(password) < PASSWORD_MIN_LENGTH:
        raise ValidationError(message)
    return password


def validate_role(role):
    if role not in VALID_ROLES:
        raise ValidationError('Role inválido')
    return role


def validate_active(active):
    if not isinstance(active, bool):
        raise ValidationError('Campo active deve ser booleano')
    return active


def validate_color(color):
    if not isinstance(color, str) or not re.match(COLOR_PATTERN, color):
        raise ValidationError('Cor inválida')
    return color
