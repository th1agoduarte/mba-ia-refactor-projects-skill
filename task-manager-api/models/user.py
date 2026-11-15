import hashlib
import hmac
import re

from werkzeug.security import check_password_hash, generate_password_hash

from config.settings import DEFAULT_ROLE, ROLE_ADMIN
from database import db, utcnow
from models.task import Task


# Formato do hash gravado pela versão legada (hashlib.md5(...).hexdigest()).
_LEGACY_MD5 = re.compile(r'[0-9a-f]{32}')


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=DEFAULT_ROLE)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    password_upgraded = False  # atributo de instância, não é coluna

    # Remover o usuário remove as tasks dele na mesma transação.
    tasks = db.relationship('Task', back_populates='user', cascade='save-update, merge, delete')

    def to_dict(self):
        """Serialização pública: nunca inclui a senha nem o hash."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': str(self.created_at),
        }

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        """Confere a senha. Hash MD5 legado (32 hex, sem salt) é aceito uma vez e regravado
        com o hash forte; quem chama deve fazer commit se `password_upgraded` ficar True."""
        if _LEGACY_MD5.fullmatch(self.password or ''):
            legacy = hashlib.md5(raw_password.encode()).hexdigest()
            if not hmac.compare_digest(legacy, self.password):
                return False
            self.set_password(raw_password)
            self.password_upgraded = True
            return True
        return check_password_hash(self.password, raw_password)

    def is_admin(self):
        return self.role == ROLE_ADMIN

    @classmethod
    def get(cls, user_id):
        return db.session.get(cls, user_id)

    @classmethod
    def find_by_email(cls, email):
        return db.session.execute(db.select(cls).filter_by(email=email)).scalar_one_or_none()

    @classmethod
    def count(cls):
        return db.session.scalar(db.select(db.func.count(cls.id)))

    @classmethod
    def list_all(cls):
        return db.session.execute(db.select(cls).order_by(cls.id)).scalars().all()

    @classmethod
    def list_with_task_count(cls):
        stmt = (
            db.select(cls, db.func.count(Task.id))
            .outerjoin(Task, Task.user_id == cls.id)
            .group_by(cls.id)
            .order_by(cls.id)
        )
        return db.session.execute(stmt).all()
