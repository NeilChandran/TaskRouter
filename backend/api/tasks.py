from flask import Blueprint, request, jsonify
from backend.models.task import Task

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/', methods=['GET'])
def list_tasks():
    return jsonify([task.to_dict() for task in Task.get_all()])

@tasks_bp.route('/', methods=['POST'])
def create_task():
    data = request.json
    task = Task.create(data)
    return jsonify(task.to_dict()), 201

@tasks_bp.route('/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = Task.get(task_id)
    return jsonify(task.to_dict() if task else {}), 200
