"""Acesso a dados de produtos (SQL parametrizado)."""

from src.models.base_model import BaseModel

CAMPOS_PRODUTO = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")


def produto_to_dict(row):
    return {campo: row[campo] for campo in CAMPOS_PRODUTO}


class ProdutoModel(BaseModel):
    def listar(self):
        rows = self.db.execute("SELECT * FROM produtos ORDER BY id").fetchall()
        return [produto_to_dict(row) for row in rows]

    def buscar_por_id(self, produto_id):
        row = self.db.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
        return produto_to_dict(row) if row else None

    def buscar(self, termo=None, categoria=None, preco_min=None, preco_max=None):
        clausulas, params = [], []
        if termo:
            clausulas.append("(nome LIKE ? OR descricao LIKE ?)")
            params += [f"%{termo}%", f"%{termo}%"]
        if categoria:
            clausulas.append("categoria = ?")
            params.append(categoria)
        if preco_min is not None:
            clausulas.append("preco >= ?")
            params.append(preco_min)
        if preco_max is not None:
            clausulas.append("preco <= ?")
            params.append(preco_max)
        where = " WHERE " + " AND ".join(clausulas) if clausulas else ""
        rows = self.db.execute(f"SELECT * FROM produtos{where} ORDER BY id", params).fetchall()
        return [produto_to_dict(row) for row in rows]

    def criar(self, nome, descricao, preco, estoque, categoria):
        with self.transacao() as conn:
            cursor = conn.execute(
                "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
                (nome, descricao, preco, estoque, categoria),
            )
        return cursor.lastrowid

    def atualizar(self, produto_id, nome, descricao, preco, estoque, categoria):
        with self.transacao() as conn:
            conn.execute(
                "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
                (nome, descricao, preco, estoque, categoria, produto_id),
            )

    def deletar(self, produto_id):
        with self.transacao() as conn:
            conn.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))

    def baixar_estoque(self, produto_id, quantidade):
        """Sem commit (use dentro de transacao()). Retorna False se não houver estoque suficiente."""
        cursor = self.db.execute(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
            (quantidade, produto_id, quantidade),
        )
        return cursor.rowcount == 1
