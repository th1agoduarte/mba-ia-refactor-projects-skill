"""Acesso a dados de usuários. Senha só é gravada como hash e nunca é serializada."""

from werkzeug.security import check_password_hash, generate_password_hash

from src.config.settings import TIPO_USUARIO_PADRAO
from src.models.base_model import BaseModel

CAMPOS_PUBLICOS = ("id", "nome", "email", "tipo", "criado_em")
CAMPOS_LOGIN = ("id", "nome", "email", "tipo")


def usuario_to_dict(row, campos=CAMPOS_PUBLICOS):
    return {campo: row[campo] for campo in campos}


def _senha_confere(senha_hash, senha):
    try:
        return bool(senha_hash) and check_password_hash(senha_hash, senha)
    except ValueError:  # valor gravado não é um hash reconhecido
        return False


class UsuarioModel(BaseModel):
    def listar(self):
        rows = self.db.execute("SELECT * FROM usuarios ORDER BY id").fetchall()
        return [usuario_to_dict(row) for row in rows]

    def buscar_por_id(self, usuario_id):
        row = self.db.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        return usuario_to_dict(row) if row else None

    def criar(self, nome, email, senha, tipo=TIPO_USUARIO_PADRAO):
        with self.transacao() as conn:
            cursor = conn.execute(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                (nome, email, generate_password_hash(senha), tipo),
            )
        return cursor.lastrowid

    def autenticar(self, email, senha):
        """Dados públicos do usuário se e-mail e senha conferem; senão None."""
        rows = self.db.execute("SELECT * FROM usuarios WHERE email = ? ORDER BY id", (email,)).fetchall()
        for row in rows:
            if _senha_confere(row["senha"], senha):
                return usuario_to_dict(row, CAMPOS_LOGIN)
        return None
