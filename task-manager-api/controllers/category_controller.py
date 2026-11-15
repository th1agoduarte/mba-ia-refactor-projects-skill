import logging

from config.settings import DEFAULT_CATEGORY_COLOR
from controllers.validators import require_body, require_text, validate_color
from database import db
from middlewares.error_handler import NotFoundError, ValidationError
from models.category import Category

log = logging.getLogger(__name__)


class CategoryController:
    def list_categories(self):
        return [
            {**category.to_dict(), 'task_count': task_count}
            for category, task_count in Category.list_with_task_count()
        ]

    def create_category(self, data):
        require_body(data)
        name = data.get('name')
        if not name:
            raise ValidationError('Nome é obrigatório')
        require_text(name, 'Nome é obrigatório')
        category = Category(
            name=name,
            description=data.get('description', ''),
            color=validate_color(data.get('color', DEFAULT_CATEGORY_COLOR)),
        )
        db.session.add(category)
        db.session.commit()
        log.info('Categoria criada: %s', category.id)
        return category.to_dict()

    def update_category(self, category_id, data):
        category = self._find_category(category_id)
        require_body(data)
        if 'name' in data:
            require_text(data['name'], 'Nome é obrigatório')
        if 'color' in data:
            validate_color(data['color'])
        for field in ('name', 'description', 'color'):
            if field in data:
                setattr(category, field, data[field])
        db.session.commit()
        return category.to_dict()

    def delete_category(self, category_id):
        category = self._find_category(category_id)
        db.session.delete(category)  # tasks da categoria ficam com category_id = NULL
        db.session.commit()
        log.info('Categoria deletada: %s', category_id)
        return {'message': 'Categoria deletada'}

    @staticmethod
    def _find_category(category_id):
        category = Category.get(category_id)
        if not category:
            raise NotFoundError('Categoria não encontrada')
        return category
