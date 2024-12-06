from flask import Blueprint, request, jsonify, current_app
from services.file_service import allowed_file, save_uploaded_file
import uuid

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    current_app.logger.info("Received /upload request")
    if 'file' not in request.files:
        current_app.logger.warning("No 'file' part in request.files")
        return jsonify({'error': '没有文件部分'}), 400

    file = request.files['file']
    current_app.logger.info(f"Received file: {file.filename}")

    if file.filename == '':
        current_app.logger.warning("No selected file")
        return jsonify({'error': '没有选择文件'}), 400

    if file and allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
        file_id = str(uuid.uuid4())
        current_app.logger.info(f"Generated file_id: {file_id}")
        try:
            save_uploaded_file(file, file_id, current_app.config['UPLOAD_FOLDER'])
        except Exception as e:
            current_app.logger.error(f"无法保存上传文件: {e}")
            return jsonify({'error': '无法保存上传文件', 'details': str(e)}), 500
        return jsonify({'file_id': file_id}), 200
    else:
        current_app.logger.warning("Invalid file type")
        return jsonify({'error': '无效的文件类型'}), 400
