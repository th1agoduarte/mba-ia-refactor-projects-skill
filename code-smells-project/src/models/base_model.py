"""Base dos models: recebe o provedor de conexão por injeção (nada de estado global)."""

from contextlib import contextmanager


class BaseModel:
    def __init__(self, db_provider):
        self._db_provider = db_provider

    @property
    def db(self):
        return self._db_provider()

    @contextmanager
    def transacao(self):
        """Commit no sucesso, rollback em qualquer exceção.

        Dentro dela use só métodos que não fazem commit próprio (documentados como "sem commit").
        """
        conn = self.db
        with conn:
            yield conn
