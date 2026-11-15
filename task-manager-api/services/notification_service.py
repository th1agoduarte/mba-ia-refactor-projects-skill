import logging
import smtplib
from email.message import EmailMessage

log = logging.getLogger(__name__)


class NotificationService:
    """Notificações por e-mail. Sem SMTP_HOST configurado, só registra no log (modo desabilitado)."""

    def __init__(self, host, port, user, password, sender):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._sender = sender or user

    @property
    def enabled(self):
        return bool(self._host)

    def notify_task_assigned(self, user, task):
        subject = f'Nova task atribuída: {task.title}'
        body = (
            f'Olá {user.name},\n\nA task \'{task.title}\' foi atribuída a você.\n\n'
            f'Prioridade: {task.priority}\nStatus: {task.status}'
        )
        return self._send(user.email, subject, body, task_id=task.id)

    def _send(self, recipient, subject, body, task_id):
        if not self.enabled:
            log.info('Notificação não enviada (SMTP desabilitado): task %s', task_id)
            return False

        message = EmailMessage()
        message['Subject'] = subject
        message['From'] = self._sender
        message['To'] = recipient
        message.set_content(body)
        try:
            with smtplib.SMTP(self._host, self._port, timeout=10) as server:
                server.starttls()
                if self._user:
                    server.login(self._user, self._password)
                server.send_message(message)
        except (smtplib.SMTPException, OSError):
            log.exception('Falha ao enviar notificação da task %s', task_id)
            return False
        log.info('Notificação enviada: task %s', task_id)
        return True
