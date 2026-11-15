import logging

from config.settings import DEFAULT_ROLE
from controllers.validators import (
    require_body,
    require_text,
    validate_active,
    validate_email,
    validate_password,
    validate_role,
)
from database import db
from middlewares.error_handler import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError, ValidationError
from models.task import Task
from models.user import User

log = logging.getLogger(__name__)

PASSWORD_TOO_SHORT_ON_CREATE = 'Senha deve ter no mínimo 4 caracteres'
PASSWORD_TOO_SHORT_ON_UPDATE = 'Senha muito curta'


class UserController:
    """Casos de uso de usuário. `authorize_admin` é injetado pela rota e levanta 401/403 sem credencial."""

    def __init__(self, token_service):
        self.token_service = token_service

    def list_users(self):
        return [{**user.to_dict(), 'task_count': task_count} for user, task_count in User.list_with_task_count()]

    def get_user(self, user_id):
        user = self._find_user(user_id)
        data = user.to_dict()
        data['tasks'] = [task.to_dict() for task in Task.list_by_user(user_id)]
        return data

    def create_user(self, data, authorize_admin):
        require_body(data)
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', DEFAULT_ROLE)
        if not name:
            raise ValidationError('Nome é obrigatório')
        if not email:
            raise ValidationError('Email é obrigatório')
        if not password:
            raise ValidationError('Senha é obrigatória')
        require_text(name, 'Nome é obrigatório')
        validate_email(email)
        validate_password(password, PASSWORD_TOO_SHORT_ON_CREATE)
        if User.find_by_email(email):
            raise ConflictError('Email já cadastrado')
        validate_role(role)
        if role != DEFAULT_ROLE:
            authorize_admin()

        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        log.info('Usuário criado: %s', user.id)
        return user.to_dict()

    def update_user(self, user_id, data, authorize_admin):
        user = self._find_user(user_id)
        require_body(data)

        if 'name' in data:
            require_text(data['name'], 'Nome é obrigatório')
        if 'email' in data:
            validate_email(data['email'])
            existing = User.find_by_email(data['email'])
            if existing and existing.id != user_id:
                raise ConflictError('Email já cadastrado')
        if 'password' in data:
            validate_password(data['password'], PASSWORD_TOO_SHORT_ON_UPDATE)
        if 'role' in data:
            validate_role(data['role'])
            if data['role'] != user.role:
                authorize_admin()
        if 'active' in data:
            validate_active(data['active'])

        for field in ('name', 'email', 'role', 'active'):
            if field in data:
                setattr(user, field, data[field])
        if 'password' in data:
            user.set_password(data['password'])
        db.session.commit()
        log.info('Usuário atualizado: %s', user.id)
        return user.to_dict()

    def delete_user(self, user_id):
        user = self._find_user(user_id)
        db.session.delete(user)  # cascade remove as tasks do usuário na mesma transação
        db.session.commit()
        log.info('Usuário deletado: %s', user_id)
        return {'message': 'Usuário deletado com sucesso'}

    def list_user_tasks(self, user_id):
        self._find_user(user_id)
        return [task.to_summary_dict() for task in Task.list_by_user(user_id)]

    def login(self, data):
        require_body(data)
        email = data.get('email')
        password = data.get('password')
        if not email or not password:
            raise ValidationError('Email e senha são obrigatórios')

        user = User.find_by_email(email) if isinstance(email, str) else None
        if not user or not isinstance(password, str) or not user.check_password(password):
            raise UnauthorizedError('Credenciais inválidas')
        if not user.active:
            raise ForbiddenError('Usuário inativo')
        if user.password_upgraded:  # hash MD5 legado migrado no login
            db.session.commit()
            log.info('Hash de senha legado migrado para o usuário %s', user.id)

        return {
            'message': 'Login realizado com sucesso',
            'user': user.to_dict(),
            'token': self.token_service.issue(user.id),
        }

    @staticmethod
    def _find_user(user_id):
        user = User.get(user_id)
        if not user:
            raise NotFoundError('Usuário não encontrado')
        return user
