import logging

from config.settings import DEFAULT_PRIORITY, STATUS_DONE, STATUS_PENDING
from controllers.metrics import completion_rate
from controllers.validators import (
    normalize_tags,
    parse_date,
    parse_int,
    require_body,
    validate_priority,
    validate_status,
    validate_title,
)
from database import db, utcnow
from middlewares.error_handler import NotFoundError, ValidationError
from models.category import Category
from models.task import Task
from models.user import User

log = logging.getLogger(__name__)

CREATE_DATE_ERROR = 'Formato de data inválido. Use YYYY-MM-DD'
UPDATE_DATE_ERROR = 'Formato de data inválido'


class TaskController:
    def __init__(self, notifier):
        self.notifier = notifier

    def list_tasks(self):
        return [task.to_dict(include_overdue=True, include_relations=True) for task in Task.list_all(with_relations=True)]

    def get_task(self, task_id):
        return self._find_task(task_id).to_dict(include_overdue=True)

    def create_task(self, data):
        require_body(data)
        title = data.get('title')
        if not title:
            raise ValidationError('Título é obrigatório')
        validate_title(title)
        status = validate_status(data.get('status', STATUS_PENDING))
        priority = validate_priority(data.get('priority', DEFAULT_PRIORITY))
        user = self._find_user(data.get('user_id'))
        self._find_category(data.get('category_id'))
        due_date = parse_date(data['due_date'], CREATE_DATE_ERROR) if data.get('due_date') else None
        tags = normalize_tags(data['tags']) if data.get('tags') else None

        task = Task(
            title=title,
            description=data.get('description', ''),
            status=status,
            priority=priority,
            user_id=data.get('user_id'),
            category_id=data.get('category_id'),
            due_date=due_date,
            tags=tags,
        )
        db.session.add(task)
        db.session.commit()
        log.info('Task criada: %s', task.id)
        if user:
            self.notifier.notify_task_assigned(user, task)
        return task.to_dict()

    def update_task(self, task_id, data):
        task = self._find_task(task_id)
        require_body(data)

        changes = {}
        if 'title' in data:
            changes['title'] = validate_title(data['title'])
        if 'description' in data:
            changes['description'] = data['description']
        if 'status' in data:
            changes['status'] = validate_status(data['status'])
        if 'priority' in data:
            changes['priority'] = validate_priority(data['priority'])
        new_assignee = None
        if 'user_id' in data:
            new_assignee = self._find_user(data['user_id'])
            changes['user_id'] = data['user_id']
        if 'category_id' in data:
            self._find_category(data['category_id'])
            changes['category_id'] = data['category_id']
        if 'due_date' in data:
            changes['due_date'] = parse_date(data['due_date'], UPDATE_DATE_ERROR) if data['due_date'] else None
        if 'tags' in data:
            changes['tags'] = normalize_tags(data['tags'])

        assignee_changed = new_assignee is not None and new_assignee.id != task.user_id
        for field, value in changes.items():
            setattr(task, field, value)
        task.updated_at = utcnow()
        db.session.commit()
        log.info('Task atualizada: %s', task.id)
        if assignee_changed:
            self.notifier.notify_task_assigned(new_assignee, task)
        return task.to_dict()

    def delete_task(self, task_id):
        task = self._find_task(task_id)
        db.session.delete(task)
        db.session.commit()
        log.info('Task deletada: %s', task_id)
        return {'message': 'Task deletada com sucesso'}

    def search_tasks(self, text, status, priority, user_id):
        tasks = Task.search(
            text=text or None,
            status=status or None,
            priority=parse_int(priority, 'Prioridade inválida') if priority else None,
            user_id=parse_int(user_id, 'Usuário inválido') if user_id else None,
        )
        return [task.to_dict() for task in tasks]

    def stats(self):
        by_status = Task.count_by_status()
        total = Task.count()
        return {
            'total': total,
            **by_status,
            'overdue': Task.count_overdue(utcnow()),
            'completion_rate': completion_rate(by_status[STATUS_DONE], total),
        }

    @staticmethod
    def _find_task(task_id):
        task = Task.get(task_id)
        if not task:
            raise NotFoundError('Task não encontrada')
        return task

    @staticmethod
    def _find_user(user_id):
        if not user_id:
            return None
        user = User.get(user_id)
        if not user:
            raise NotFoundError('Usuário não encontrado')
        return user

    @staticmethod
    def _find_category(category_id):
        if not category_id:
            return None
        category = Category.get(category_id)
        if not category:
            raise NotFoundError('Categoria não encontrada')
        return category
