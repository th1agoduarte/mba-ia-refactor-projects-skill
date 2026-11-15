"""Configuração da aplicação (lida do ambiente) e constantes de domínio.

Nenhum segredo literal: valores ausentes viram defaults seguros. Veja `.env.example`.
"""

import logging
import os
import secrets

log = logging.getLogger(__name__)


def _env_bool(name, default=False):
    return os.environ.get(name, "1" if default else "0").strip().lower() in ("1", "true", "yes", "on")


def _env_list(name):
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


class Settings:
    """Valores de runtime. Lidos uma vez, na importação; testes podem passar outra classe ao create_app."""

    SECRET_KEY = os.environ.get("SECRET_KEY") or None  # resolvido em resolve_secret_key()
    DEBUG = _env_bool("FLASK_DEBUG")
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")  # vazio = endpoints /admin desabilitados (403)
    CORS_ORIGINS = _env_list("CORS_ORIGINS")  # vazio = CORS desligado (só mesma origem)
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
    APP_ENV = os.environ.get("APP_ENV", "producao")
    APP_VERSION = "1.0.0"


def resolve_secret_key(settings):
    """Devolve a SECRET_KEY do ambiente ou uma chave efêmera (com aviso)."""
    if settings.SECRET_KEY:
        return settings.SECRET_KEY
    log.warning("SECRET_KEY não definida; usando chave efêmera (sessões não sobrevivem a reinícios)")
    return secrets.token_hex(32)


# --- Constantes de domínio -------------------------------------------------

CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
CATEGORIA_PADRAO = "geral"
NOME_PRODUTO_MIN = 2
NOME_PRODUTO_MAX = 200

TIPO_USUARIO_PADRAO = "cliente"

STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_ENVIADO = "enviado"
STATUS_ENTREGUE = "entregue"
STATUS_CANCELADO = "cancelado"
STATUS_PEDIDO_VALIDOS = (STATUS_PENDENTE, STATUS_APROVADO, STATUS_ENVIADO, STATUS_ENTREGUE, STATUS_CANCELADO)

# (faturamento acima de, taxa de desconto), da maior faixa para a menor
FAIXAS_DESCONTO = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))
