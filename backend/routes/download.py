from flask import Blueprint, jsonify, send_from_directory, current_app
from werkzeug.utils import secure_filename
import os

download_bp = Blueprint('download', __name__)

@download_bp.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        safe_filename = secure_filename(filename)
        current_app.logger.info(f"Processing download request for {safe_filename}")
        response = send_from_directory(
            directory=current_app.config['DOWNLOAD_FOLDER'], 
            path=safe_filename, 
            as_attachment=True
        )
        current_app.logger.info(f"Sending file: {safe_filename}")
        return response
    except FileNotFoundError:
        current_app.logger.warning(f"File not found: {filename}")
        return jsonify({'error': '文件未找到'}), 404
    except Exception as e:
        current_app.logger.error(f"Error sending file {filename}: {e}")
        return jsonify({'error': '无法发送文件', 'details': str(e)}), 500
