"""Conexão SQLite por requisição (flask.g), schema e seed."""

import logging
import os
import sqlite3
from urllib.parse import quote

from flask import current_app, g
from werkzeug.security import generate_password_hash

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    descricao TEXT,
    preco REAL,
    estoque INTEGER,
    categoria TEXT,
    ativo INTEGER DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    email TEXT,
    senha TEXT,
    tipo TEXT DEFAULT 'cliente',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    status TEXT DEFAULT 'pendente',
    total REAL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS itens_pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER REFERENCES pedidos(id) ON DELETE CASCADE,
    produto_id INTEGER,
    quantidade INTEGER,
    preco_unitario REAL
);
"""

PRODUTOS_SEED = (
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
)

# Usuários de exemplo (ambiente de desenvolvimento). As senhas são gravadas com hash.
USUARIOS_SEED = (
    ("Admin", "admin@loja.com", "admin123", "admin"),
    ("João Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
)

HASH_PREFIXES = ("scrypt:", "pbkdf2:")


def connect(path, read_only=False):
    if read_only:
        conn = sqlite3.connect(f"file:{quote(os.path.abspath(path))}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """Conexão da requisição atual; aberta sob demanda e fechada no teardown."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_PATH"])
    return g.db


def get_read_only_db():
    if "db_ro" not in g:
        g.db_ro = connect(current_app.config["DATABASE_PATH"], read_only=True)
    return g.db_ro


def close_db(_exc=None):
    for key in ("db", "db_ro"):
        conn = g.pop(key, None)
        if conn is not None:
            conn.close()


def init_schema(conn):
    conn.executescript(SCHEMA)


def seed(conn):
    with conn:
        if conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
                PRODUTOS_SEED,
            )
            conn.executemany(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                [(nome, email, generate_password_hash(senha), tipo) for nome, email, senha, tipo in USUARIOS_SEED],
            )
        _migrar_senhas_texto_puro(conn)


def _migrar_senhas_texto_puro(conn):
    """Bancos criados pela versão antiga guardavam senha em texto puro: regrava com hash."""
    legados = [
        row for row in conn.execute("SELECT id, senha FROM usuarios").fetchall()
        if row["senha"] and not row["senha"].startswith(HASH_PREFIXES)
    ]
    for row in legados:
        conn.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (generate_password_hash(row["senha"]), row["id"]))
    if legados:
        log.warning("%d senha(s) em texto puro migrada(s) para hash", len(legados))


def init_app(app):
    app.teardown_appcontext(close_db)
    conn = connect(app.config["DATABASE_PATH"])
    try:
        init_schema(conn)
        seed(conn)
    finally:
        conn.close()
