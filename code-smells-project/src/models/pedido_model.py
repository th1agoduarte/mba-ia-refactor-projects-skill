"""Acesso a dados de pedidos e itens de pedido."""

from collections import defaultdict

from src.models.base_model import BaseModel

PRODUTO_DESCONHECIDO = "Desconhecido"


class PedidoModel(BaseModel):
    def inserir(self, usuario_id, status, total):
        """Sem commit (use dentro de transacao())."""
        cursor = self.db.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, status, total),
        )
        return cursor.lastrowid

    def inserir_item(self, pedido_id, produto_id, quantidade, preco_unitario):
        """Sem commit (use dentro de transacao())."""
        self.db.execute(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
            (pedido_id, produto_id, quantidade, preco_unitario),
        )

    def listar(self, usuario_id=None):
        """Pedidos com itens em 2 consultas (sem N+1). Filtra por usuário quando informado."""
        filtro, params = ("WHERE usuario_id = ?", (usuario_id,)) if usuario_id is not None else ("", ())
        pedidos = self.db.execute(f"SELECT * FROM pedidos {filtro} ORDER BY id", params).fetchall()
        if not pedidos:
            return []

        itens = self.db.execute(
            "SELECT i.pedido_id, i.produto_id, i.quantidade, i.preco_unitario, p.nome AS produto_nome "
            "FROM itens_pedido i LEFT JOIN produtos p ON p.id = i.produto_id "
            f"WHERE i.pedido_id IN (SELECT id FROM pedidos {filtro}) ORDER BY i.id",
            params,
        ).fetchall()
        itens_por_pedido = defaultdict(list)
        for item in itens:
            itens_por_pedido[item["pedido_id"]].append({
                "produto_id": item["produto_id"],
                "produto_nome": item["produto_nome"] if item["produto_nome"] is not None else PRODUTO_DESCONHECIDO,
                "quantidade": item["quantidade"],
                "preco_unitario": item["preco_unitario"],
            })

        return [
            {
                "id": pedido["id"],
                "usuario_id": pedido["usuario_id"],
                "status": pedido["status"],
                "total": pedido["total"],
                "criado_em": pedido["criado_em"],
                "itens": itens_por_pedido[pedido["id"]],
            }
            for pedido in pedidos
        ]

    def atualizar_status(self, pedido_id, status):
        with self.transacao() as conn:
            conn.execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))

    def estatisticas(self):
        """Totais e contagem por status em 2 consultas (GROUP BY)."""
        total_pedidos, faturamento = self.db.execute(
            "SELECT COUNT(*), COALESCE(SUM(total), 0) FROM pedidos"
        ).fetchone()
        por_status = dict(self.db.execute("SELECT status, COUNT(*) FROM pedidos GROUP BY status").fetchall())
        return {"total_pedidos": total_pedidos, "faturamento": faturamento, "por_status": por_status}
