"""Casos de uso de produtos."""

import logging

from src.config.settings import CATEGORIA_PADRAO, CATEGORIAS_VALIDAS, NOME_PRODUTO_MAX, NOME_PRODUTO_MIN
from src.controllers.validators import exigir_objeto, is_int, is_number, numero_opcional, texto
from src.errors import NotFoundError, ValidationError

log = logging.getLogger(__name__)


def validar_produto(dados):
    """Valida o corpo de criação/atualização e devolve os campos normalizados."""
    dados = exigir_objeto(dados)
    for campo, mensagem in (("nome", "Nome é obrigatório"), ("preco", "Preço é obrigatório"),
                            ("estoque", "Estoque é obrigatório")):
        if campo not in dados:
            raise ValidationError(mensagem)

    nome, preco, estoque = dados["nome"], dados["preco"], dados["estoque"]
    categoria = dados.get("categoria", CATEGORIA_PADRAO)

    if not is_number(preco):
        raise ValidationError("Preço inválido")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if not is_int(estoque):
        raise ValidationError("Estoque inválido")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if not isinstance(nome, str):
        raise ValidationError("Nome inválido")
    if len(nome) < NOME_PRODUTO_MIN:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_PRODUTO_MAX:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(list(CATEGORIAS_VALIDAS)))

    return {"nome": nome, "descricao": texto(dados, "descricao"), "preco": preco,
            "estoque": estoque, "categoria": categoria}


class ProdutoController:
    def __init__(self, produto_model):
        self.produtos = produto_model

    def listar(self):
        produtos = self.produtos.listar()
        log.debug("Listando %d produtos", len(produtos))
        return produtos

    def buscar(self, produto_id):
        produto = self.produtos.buscar_por_id(produto_id)
        if not produto:
            raise NotFoundError("Produto não encontrado", com_sucesso=True)
        return produto

    def pesquisar(self, termo, categoria, preco_min, preco_max):
        return self.produtos.buscar(
            termo=termo,
            categoria=categoria,
            preco_min=numero_opcional(preco_min, "preco_min"),
            preco_max=numero_opcional(preco_max, "preco_max"),
        )

    def criar(self, dados):
        produto = validar_produto(dados)
        produto_id = self.produtos.criar(**produto)
        log.info("Produto criado com ID %s", produto_id)
        return {"id": produto_id}

    def atualizar(self, produto_id, dados):
        self._garantir_existe(produto_id)
        self.produtos.atualizar(produto_id, **validar_produto(dados))

    def deletar(self, produto_id):
        self._garantir_existe(produto_id)
        self.produtos.deletar(produto_id)
        log.info("Produto %s deletado", produto_id)

    def _garantir_existe(self, produto_id):
        if not self.produtos.buscar_por_id(produto_id):
            raise NotFoundError("Produto não encontrado")
