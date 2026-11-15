from sqlalchemy.orm import joinedload

from config.settings import CLOSED_STATUSES, DEFAULT_PRIORITY, STATUS_DONE, STATUS_PENDING, VALID_STATUSES
from database import db, utcnow


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=STATUS_PENDING)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', back_populates='tasks')
    category = db.relationship('Category', back_populates='tasks')

    # ---- regras da entidade ----

    def is_overdue(self, now=None):
        reference = now or utcnow()
        return bool(self.due_date and self.due_date < reference and self.status not in CLOSED_STATUSES)

    # ---- serialização (view) ----

    def to_dict(self, include_overdue=False, include_relations=False):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'tags': self.tags.split(',') if self.tags else [],
        }
        if include_overdue:
            data['overdue'] = self.is_overdue()
        if include_relations:
            data['user_name'] = self.user.name if self.user else None
            data['category_name'] = self.category.name if self.category else None
        return data

    def to_summary_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'created_at': str(self.created_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'overdue': self.is_overdue(),
        }

    # ---- acesso a dados ----

    @classmethod
    def get(cls, task_id):
        return db.session.get(cls, task_id)

    @classmethod
    def list_all(cls, with_relations=False):
        stmt = db.select(cls).order_by(cls.id)
        if with_relations:
            stmt = stmt.options(joinedload(cls.user), joinedload(cls.category))
        return db.session.execute(stmt).scalars().all()

    @classmethod
    def list_by_user(cls, user_id):
        stmt = db.select(cls).filter_by(user_id=user_id).order_by(cls.id)
        return db.session.execute(stmt).scalars().all()

    @classmethod
    def search(cls, text=None, status=None, priority=None, user_id=None):
        stmt = db.select(cls)
        if text:
            pattern = f'%{text}%'
            stmt = stmt.where(db.or_(cls.title.like(pattern), cls.description.like(pattern)))
        if status:
            stmt = stmt.where(cls.status == status)
        if priority is not None:
            stmt = stmt.where(cls.priority == priority)
        if user_id is not None:
            stmt = stmt.where(cls.user_id == user_id)
        return db.session.execute(stmt.order_by(cls.id)).scalars().all()

    @classmethod
    def count(cls):
        return db.session.scalar(db.select(db.func.count(cls.id)))

    @classmethod
    def count_by_status(cls, user_id=None):
        stmt = db.select(cls.status, db.func.count(cls.id)).group_by(cls.status)
        if user_id is not None:
            stmt = stmt.where(cls.user_id == user_id)
        counts = dict(db.session.execute(stmt).all())
        return {status: counts.get(status, 0) for status in VALID_STATUSES}

    @classmethod
    def count_by_priority(cls):
        return dict(db.session.execute(db.select(cls.priority, db.func.count(cls.id)).group_by(cls.priority)).all())

    @classmethod
    def _overdue_filter(cls, now):
        return (cls.due_date.is_not(None), cls.due_date < now, cls.status.not_in(CLOSED_STATUSES))

    @classmethod
    def list_overdue(cls, now):
        stmt = db.select(cls).where(*cls._overdue_filter(now)).order_by(cls.id)
        return db.session.execute(stmt).scalars().all()

    @classmethod
    def count_overdue(cls, now, user_id=None):
        stmt = db.select(db.func.count(cls.id)).where(*cls._overdue_filter(now))
        if user_id is not None:
            stmt = stmt.where(cls.user_id == user_id)
        return db.session.scalar(stmt)

    @classmethod
    def count_high_priority(cls, user_id, max_priority):
        stmt = db.select(db.func.count(cls.id)).where(cls.user_id == user_id, cls.priority <= max_priority)
        return db.session.scalar(stmt)

    @classmethod
    def count_created_since(cls, since):
        return db.session.scalar(db.select(db.func.count(cls.id)).where(cls.created_at >= since))

    @classmethod
    def count_done_since(cls, since):
        stmt = db.select(db.func.count(cls.id)).where(cls.status == STATUS_DONE, cls.updated_at >= since)
        return db.session.scalar(stmt)

    @classmethod
    def totals_by_user(cls):
        """{user_id: (total, concluídas)} numa única consulta agregada."""
        done = db.func.sum(db.case((cls.status == STATUS_DONE, 1), else_=0))
        stmt = db.select(cls.user_id, db.func.count(cls.id), done).group_by(cls.user_id)
        return {user_id: (total, completed or 0) for user_id, total, completed in db.session.execute(stmt).all()}
