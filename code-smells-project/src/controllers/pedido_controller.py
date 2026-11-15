"""Casos de uso de pedidos: criação transacional com baixa de estoque e mudança de status."""

from src.config.settings import STATUS_PEDIDO_VALIDOS, STATUS_PENDENTE
from src.controllers.validators import exigir_objeto, is_int
from src.errors import ValidationError


def validar_itens(itens):
    if not itens or not isinstance(itens, list):
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    for item in itens:
        if not (isinstance(item, dict) and is_int(item.get("produto_id"))
                and is_int(item.get("quantidade")) and item["quantidade"] > 0):
            raise ValidationError("Item inválido: informe produto_id e quantidade (inteiro positivo)")
    return itens


class PedidoController:
    def __init__(self, pedido_model, produto_model, notifier):
        self.pedidos = pedido_model
        self.produtos = produto_model
        self.notifier = notifier

    def criar(self, dados):
        dados = exigir_objeto(dados)
        usuario_id = dados.get("usuario_id")
        if not usuario_id:
            raise ValidationError("Usuario ID é obrigatório")
        if not is_int(usuario_id):
            raise ValidationError("Usuario ID inválido")
        itens = validar_itens(dados.get("itens", []))

        with self.pedidos.transacao():
            produtos, total = self._conferir_itens(itens)
            pedido_id = self.pedidos.inserir(usuario_id, STATUS_PENDENTE, total)
            for item in itens:
                produto = produtos[item["produto_id"]]
                self.pedidos.inserir_item(pedido_id, item["produto_id"], item["quantidade"], produto["preco"])
                if not self.produtos.baixar_estoque(item["produto_id"], item["quantidade"]):
                    # estoque mudou entre a conferência e a baixa (concorrência): desfaz tudo
                    raise ValidationError("Estoque insuficiente para " + produto["nome"], com_sucesso=True)

        resultado = {"pedido_id": pedido_id, "total": total}
        self.notifier.pedido_criado(pedido_id, usuario_id)
        return resultado

    def _conferir_itens(self, itens):
        """Confere existência e estoque de todos os itens antes de escrever; calcula o total."""
        produtos, total = {}, 0
        for item in itens:
            produto = self.produtos.buscar_por_id(item["produto_id"])
            if produto is None:
                raise ValidationError(f"Produto {item['produto_id']} não encontrado", com_sucesso=True)
            if produto["estoque"] < item["quantidade"]:
                raise ValidationError("Estoque insuficiente para " + produto["nome"], com_sucesso=True)
            produtos[item["produto_id"]] = produto
            total = total + produto["preco"] * item["quantidade"]
        return produtos, total

    def listar(self, usuario_id=None):
        return self.pedidos.listar(usuario_id)

    def atualizar_status(self, pedido_id, dados):
        novo_status = dados.get("status", "") if isinstance(dados, dict) else ""
        if novo_status not in STATUS_PEDIDO_VALIDOS:
            raise ValidationError("Status inválido")
        self.pedidos.atualizar_status(pedido_id, novo_status)
        self.notifier.status_alterado(pedido_id, novo_status)
