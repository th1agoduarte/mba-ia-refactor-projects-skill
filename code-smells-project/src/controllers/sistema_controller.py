"""Índice da API, health check e operações administrativas."""

import logging
import sqlite3

from src.errors import ServiceUnavailableError, ValidationError

log = logging.getLogger(__name__)

ENDPOINTS = {
    "produtos": "/produtos",
    "usuarios": "/usuarios",
    "pedidos": "/pedidos",
    "login": "/login",
    "relatorios": "/relatorios/vendas",
    "health": "/health",
}


class SistemaController:
    def __init__(self, sistema_model, versao, ambiente):
        self.sistema = sistema_model
        self.versao = versao
        self.ambiente = ambiente

    def indice(self):
        return {"mensagem": "Bem-vindo à API da Loja", "versao": self.versao, "endpoints": ENDPOINTS}

    def health(self):
        try:
            counts = self.sistema.contagens()
        except sqlite3.Error:
            log.exception("Health check: banco indisponível")
            raise ServiceUnavailableError(
                "Banco de dados indisponível",
                body={"status": "erro", "detalhes": "Banco de dados indisponível"},
            ) from None
        return {"status": "ok", "database": "connected", "counts": counts,
                "versao": self.versao, "ambiente": self.ambiente}

    def resetar_banco(self):
        self.sistema.resetar()
        log.warning("Banco de dados resetado por administrador")

    def executar_consulta(self, dados):
        sql = dados.get("sql", "") if isinstance(dados, dict) else ""
        if not sql or not isinstance(sql, str):
            raise ValidationError("Query não informada")
        if not sql.strip().upper().startswith("SELECT"):
            raise ValidationError("Somente consultas SELECT são permitidas")
        try:
            return self.sistema.consultar_somente_leitura(sql)
        except sqlite3.Error as exc:
            raise ValidationError(f"Query inválida: {exc}") from None
