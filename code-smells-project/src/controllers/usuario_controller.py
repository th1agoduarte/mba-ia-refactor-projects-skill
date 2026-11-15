"""Casos de uso de usuários e autenticação."""

import logging

from src.controllers.validators import exigir_objeto, texto
from src.errors import NotFoundError, UnauthorizedError, ValidationError

log = logging.getLogger(__name__)


class UsuarioController:
    def __init__(self, usuario_model):
        self.usuarios = usuario_model

    def listar(self):
        return self.usuarios.listar()

    def buscar(self, usuario_id):
        usuario = self.usuarios.buscar_por_id(usuario_id)
        if not usuario:
            raise NotFoundError("Usuário não encontrado")
        return usuario

    def criar(self, dados):
        dados = exigir_objeto(dados)
        nome, email, senha = texto(dados, "nome"), texto(dados, "email"), texto(dados, "senha")
        if not (nome and email and senha):
            raise ValidationError("Nome, email e senha são obrigatórios")
        usuario_id = self.usuarios.criar(nome, email, senha)
        log.info("Usuário %s criado", usuario_id)
        return {"id": usuario_id}

    def login(self, dados):
        dados = dados if isinstance(dados, dict) else {}
        email, senha = texto(dados, "email"), texto(dados, "senha")
        if not (email and senha):
            raise ValidationError("Email e senha são obrigatórios")
        usuario = self.usuarios.autenticar(email, senha)
        if not usuario:
            log.info("Falha de login")
            raise UnauthorizedError("Email ou senha inválidos", com_sucesso=True)
        log.info("Login do usuário %s", usuario["id"])
        return usuario
