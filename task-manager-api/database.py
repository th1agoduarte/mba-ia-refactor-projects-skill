from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow():
    """UTC atual como datetime naive, compatível com as colunas DateTime já gravadas no SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
