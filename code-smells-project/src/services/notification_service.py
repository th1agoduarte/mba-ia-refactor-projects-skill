"""Notificações (e-mail, SMS, push) atrás de uma interface única.

A implementação atual só registra no log, como o sistema original fazia com print.
Para integrar um provedor real, crie outra classe com os mesmos métodos e injete-a em create_app().
O controller só notifica depois do commit, então uma falha de envio nunca desfaz o pedido gravado.
"""

import logging

from src.config.settings import STATUS_APROVADO, STATUS_CANCELADO

log = logging.getLogger(__name__)

MENSAGENS_STATUS = {
    STATUS_APROVADO: "Pedido %s foi aprovado! Preparar envio.",
    STATUS_CANCELADO: "Pedido %s cancelado. Devolver estoque.",
}


class LogNotificationService:
    CANAIS_PEDIDO_CRIADO = ("email", "sms", "push")

    def pedido_criado(self, pedido_id, usuario_id):
        for canal in self.CANAIS_PEDIDO_CRIADO:
            self._enviar(canal, "Pedido %s criado para usuário %s", pedido_id, usuario_id)

    def status_alterado(self, pedido_id, status):
        mensagem = MENSAGENS_STATUS.get(status)
        if mensagem:
            self._enviar("interno", mensagem, pedido_id)

    def _enviar(self, canal, mensagem, *args):
        log.info("Notificação [%s]: " + mensagem, canal, *args)
