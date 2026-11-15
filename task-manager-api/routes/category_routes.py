from flask import Blueprint, jsonify, request


def create_category_blueprint(controller):
    bp = Blueprint('categories', __name__)

    @bp.get('/categories')
    def list_categories():
        return jsonify(controller.list_categories()), 200

    @bp.post('/categories')
    def create_category():
        return jsonify(controller.create_category(request.get_json())), 201

    @bp.put('/categories/<int:category_id>')
    def update_category(category_id):
        return jsonify(controller.update_category(category_id, request.get_json())), 200

    @bp.delete('/categories/<int:category_id>')
    def delete_category(category_id):
        return jsonify(controller.delete_category(category_id)), 200

    return bp
