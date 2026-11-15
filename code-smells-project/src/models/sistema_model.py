"""Operações de sistema: contagens do health check, reset e consulta somente leitura."""

from src.models.base_model import BaseModel

TABELAS_RESET = ("itens_pedido", "pedidos", "produtos", "usuarios")  # filhas antes das pais


class SistemaModel(BaseModel):
    def __init__(self, db_provider, read_only_db_provider):
        super().__init__(db_provider)
        self._read_only_db_provider = read_only_db_provider

    def contagens(self):
        row = self.db.execute(
            "SELECT (SELECT COUNT(*) FROM produtos) AS produtos, "
            "(SELECT COUNT(*) FROM usuarios) AS usuarios, "
            "(SELECT COUNT(*) FROM pedidos) AS pedidos"
        ).fetchone()
        return dict(row)

    def resetar(self):
        with self.transacao() as conn:
            for tabela in TABELAS_RESET:
                conn.execute(f"DELETE FROM {tabela}")  # nomes vêm da constante acima, não da entrada

    def consultar_somente_leitura(self, sql):
        """Executa uma única instrução numa conexão aberta em modo read-only."""
        rows = self._read_only_db_provider().execute(sql).fetchall()
        return [dict(row) for row in rows]
