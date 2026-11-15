"""Relatório de vendas: agrega os dados do model e aplica a política de desconto."""

from src.config.settings import FAIXAS_DESCONTO, STATUS_APROVADO, STATUS_CANCELADO, STATUS_PENDENTE


def desconto_para(faturamento):
    return next((faturamento * taxa for limite, taxa in FAIXAS_DESCONTO if faturamento > limite), 0)


class RelatorioController:
    def __init__(self, pedido_model):
        self.pedidos = pedido_model

    def vendas(self):
        stats = self.pedidos.estatisticas()
        total_pedidos, faturamento = stats["total_pedidos"], stats["faturamento"]
        por_status = stats["por_status"]
        desconto = desconto_para(faturamento)
        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, 2),
            "desconto_aplicavel": round(desconto, 2),
            "faturamento_liquido": round(faturamento - desconto, 2),
            "pedidos_pendentes": por_status.get(STATUS_PENDENTE, 0),
            "pedidos_aprovados": por_status.get(STATUS_APROVADO, 0),
            "pedidos_cancelados": por_status.get(STATUS_CANCELADO, 0),
            "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
        }
