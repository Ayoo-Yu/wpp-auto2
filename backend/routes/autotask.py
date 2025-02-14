from flask import Blueprint, request, jsonify
from models import AutoPredictionTask
from database_config import get_db
from datetime import datetime

autotask_bp = Blueprint('autotask', __name__)

@autotask_bp.route('/tasks', methods=['POST'])
def create_auto_task():
    data = request.json
    db = next(get_db())
    
    try:
        task = AutoPredictionTask(
            task_type=data['task_type'],
            schedule_time=data['schedule_time'],
            output_dir=data['output_dir'],
            is_active=True
        )
        db.add(task)
        db.commit()
        return jsonify({'task_id': task.id})
        
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@autotask_bp.route('/tasks/<int:task_id>', methods=['PUT'])
def update_auto_task(task_id):
    data = request.json
    db = next(get_db())
    
    task = db.query(AutoPredictionTask).get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
        
    try:
        if 'schedule_time' in data:
            task.schedule_time = data['schedule_time']
        if 'is_active' in data:
            task.is_active = data['is_active']
        if 'output_dir' in data:
            task.output_dir = data['output_dir']
            
        db.commit()
        return jsonify({'message': 'Task updated'})
        
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500 