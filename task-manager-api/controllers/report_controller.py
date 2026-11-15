from datetime import timedelta

from config.settings import HIGH_PRIORITY_MAX, PRIORITY_LABELS, RECENT_ACTIVITY_DAYS, STATUS_DONE
from controllers.metrics import completion_rate
from database import utcnow
from middlewares.error_handler import NotFoundError
from models.category import Category
from models.task import Task
from models.user import User


class ReportController:
    def summary(self):
        now = utcnow()
        since = now - timedelta(days=RECENT_ACTIVITY_DAYS)
        by_priority = Task.count_by_priority()
        overdue_tasks = Task.list_overdue(now)
        totals_by_user = Task.totals_by_user()

        return {
            'generated_at': str(now),
            'overview': {
                'total_tasks': Task.count(),
                'total_users': User.count(),
                'total_categories': Category.count(),
            },
            'tasks_by_status': Task.count_by_status(),
            'tasks_by_priority': {label: by_priority.get(level, 0) for level, label in PRIORITY_LABELS.items()},
            'overdue': {
                'count': len(overdue_tasks),
                'tasks': [
                    {
                        'id': task.id,
                        'title': task.title,
                        'due_date': str(task.due_date),
                        'days_overdue': (now - task.due_date).days,
                    }
                    for task in overdue_tasks
                ],
            },
            # Os nomes das chaves fazem parte do contrato público e não acompanham a constante.
            'recent_activity': {
                'tasks_created_last_7_days': Task.count_created_since(since),
                'tasks_completed_last_7_days': Task.count_done_since(since),
            },
            'user_productivity': [self._productivity(user, totals_by_user) for user in User.list_all()],
        }

    def user_report(self, user_id):
        user = User.get(user_id)
        if not user:
            raise NotFoundError('Usuário não encontrado')

        by_status = Task.count_by_status(user_id=user_id)
        total = sum(by_status.values())
        return {
            'user': {'id': user.id, 'name': user.name, 'email': user.email},
            'statistics': {
                'total_tasks': total,
                **by_status,
                'overdue': Task.count_overdue(utcnow(), user_id=user_id),
                'high_priority': Task.count_high_priority(user_id, HIGH_PRIORITY_MAX),
                'completion_rate': completion_rate(by_status[STATUS_DONE], total),
            },
        }

    @staticmethod
    def _productivity(user, totals_by_user):
        total, completed = totals_by_user.get(user.id, (0, 0))
        return {
            'user_id': user.id,
            'user_name': user.name,
            'total_tasks': total,
            'completed_tasks': completed,
            'completion_rate': completion_rate(completed, total),
        }
