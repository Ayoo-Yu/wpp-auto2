# backend/app.py

# 1. 立即导入 eventlet 并打补丁
import eventlet
eventlet.monkey_patch()

# 2. 导入其他模块
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import pandas as pd
import hashlib
import datetime
from werkzeug.utils import secure_filename
import uuid
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import shutil
from scripts.prediction_timestamp import post_process_predictions
from scripts.evaluator_model import evaluate_model
from scripts.train_run import train_run

# 3. 继续您的应用逻辑
# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)

# 初始化 SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# 配置上传和下载文件夹
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'forecasts')

# 创建文件夹（如果不存在）
for folder in [UPLOAD_FOLDER, DOWNLOAD_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 配置日志记录
if not os.path.exists('logs'):
    os.makedirs('logs')

class SocketIOHandler(logging.Handler):
    """自定义日志处理器，通过 SocketIO 发送日志消息到前端。"""

    def __init__(self, socketio_instance):
        super().__init__()
        self.socketio = socketio_instance

    def emit(self, record):
        log_entry = self.format(record)
        # 将日志消息发送到前端的 'log' 事件
        self.socketio.emit('log', {'message': log_entry})

file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# 添加 SocketIO 日志处理器
socketio_handler = SocketIOHandler(socketio)
socketio_handler.setFormatter(formatter)
socketio_handler.setLevel(logging.INFO)

app.logger.addHandler(file_handler)
app.logger.addHandler(socketio_handler)

app.logger.setLevel(logging.INFO)
app.logger.info('Wind Forecast Backend Startup')

@app.errorhandler(413)
def request_entity_too_large(error):
    app.logger.warning("文件太大，超过200MB限制")
    return jsonify({'error': '文件太大，最大允许200MB'}), 413

@app.route('/upload', methods=['POST'])
def upload_file():
    app.logger.info("Received /upload request")
    
    # 打印所有表单数据和文件
    app.logger.info(f"request.form: {request.form}")
    app.logger.info(f"request.files: {request.files}")

    if 'file' not in request.files:
        app.logger.warning("No 'file' part in request.files")
        return jsonify({'error': '没有文件部分'}), 400

    file = request.files['file']
    app.logger.info(f"Received file: {file.filename}")

    if file.filename == '':
        app.logger.warning("No selected file")
        return jsonify({'error': '没有选择文件'}), 400

    if file and allowed_file(file.filename):
        # 生成唯一的 file_id
        file_id = str(uuid.uuid4())
        app.logger.info(f"Generated file_id: {file_id}")

        # 分离文件名和扩展名
        filename_wo_ext, ext = os.path.splitext(secure_filename(file.filename))
        
        # 生成新的上传文件名，包含 file_id
        new_upload_filename = f"{filename_wo_ext}_{file_id}{ext}"
        
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], new_upload_filename)
        try:
            file.save(upload_path)
            app.logger.info(f"Saved uploaded file to {upload_path}")
        except Exception as e:
            app.logger.error(f"无法保存上传文件: {e}")
            return jsonify({'error': '无法保存上传文件', 'details': str(e)}), 500

        return jsonify({'file_id': file_id}), 200

    else:
        app.logger.warning("Invalid file type")
        return jsonify({'error': '无效的文件类型'}), 400

@app.route('/predict', methods=['POST'])
def predict():
    app.logger.info("Received /predict request")
    data = request.get_json()
    if not data or 'file_id' not in data or 'model' not in data:
        app.logger.warning("Missing 'file_id' or 'model' in request data")
        return jsonify({'error': "缺少 'file_id' 或 'model' 参数"}), 400

    file_id = data['file_id']
    model = data['model']
    app.logger.info(f"Received file_id: {file_id}, model: {model}")

    # 在 UPLOAD_FOLDER 中查找包含 file_id 的文件
    matched_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if file_id in f]
    if not matched_files:
        app.logger.warning(f"No file found for file_id: {file_id}")
        return jsonify({'error': '无效的 file_id'}), 400

    filename = matched_files[0]
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(upload_path):
        app.logger.warning(f"File not found on server: {upload_path}")
        return jsonify({'error': '文件未找到'}), 404

    # 执行预测
    try:
        app.logger.info("Starting prediction...")
        forecast_file_path_temp = train_run(DATA_FILE_PATH=upload_path, MODEL=model)
        forecast_file_path = post_process_predictions(upload_path, forecast_file_path_temp)
        app.logger.info(f"train_run returned: {forecast_file_path}")
        app.logger.info("Executed prediction successfully")
    except Exception as e:
        app.logger.error(f"预测过程中出错: {e}")
        return jsonify({'error': '预测过程中出错', 'details': str(e)}), 500

    # 确保 train_run 返回的是文件路径
    if not isinstance(forecast_file_path, str) or not os.path.isfile(forecast_file_path):
        app.logger.error("train_run did not return a valid file path")
        return jsonify({'error': '预测文件生成失败'}), 500

    # 生成预测结果文件名并保存到 DOWNLOAD_FOLDER
    forecast_timestamp_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename_wo_ext, ext = os.path.splitext(filename)
    output_filename = f"forecast_{filename_wo_ext}_{forecast_timestamp_str}.csv"
    output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], output_filename)

    try:
        shutil.copy(forecast_file_path, output_path)
        app.logger.info(f"Copied forecast result to {output_path}")
    except Exception as e:
        app.logger.error(f"无法保存预测结果文件: {e}")
        return jsonify({'error': '无法保存预测结果文件', 'details': str(e)}), 500

    # 执行模型评估
    try:
        app.logger.info("Starting model evaluation...")
        # 定义评估结果的保存目录，建议与预测结果同目录下的子目录
        evaluation_output_dir = os.path.join(app.config['DOWNLOAD_FOLDER'], f"evaluation_{filename_wo_ext}_{forecast_timestamp_str}")
        evaluation_result = evaluate_model(
            data_path=output_path,
            save_plots=True,
            save_csv=True,
            save_report=True,
            custom_save_dir=evaluation_output_dir
        )
        app.logger.info(f"Model evaluation completed. Results saved in {evaluation_output_dir}")
    except Exception as e:
        app.logger.error(f"模型评估过程中出错: {e}")
        return jsonify({'error': '模型评估过程中出错', 'details': str(e)}), 500

    # 生成评估报告的下载链接
    report_filename = 'model_evaluation_report.txt'
    report_path = os.path.join(evaluation_output_dir, report_filename)
    if os.path.exists(report_path):
        # 复制报告到 DOWNLOAD_FOLDER 以便下载
        report_output_filename = f"report_{filename_wo_ext}_{forecast_timestamp_str}.txt"
        report_output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], report_output_filename)
        try:
            shutil.copy(report_path, report_output_path)
            app.logger.info(f"Copied evaluation report to {report_output_path}")
        except Exception as e:
            app.logger.error(f"无法保存评估报告文件: {e}")
            return jsonify({'error': '无法保存评估报告文件', 'details': str(e)}), 500
        # 生成下载链接
        report_download_url = f"/download/{secure_filename(report_output_filename)}"
    else:
        app.logger.warning("评估报告文件未找到")
        report_download_url = None

    # 生成下载链接（指向 /download/<filename>）
    download_url = f"/download/{secure_filename(output_filename)}"
    app.logger.info(f"Generated forecast download URL: {download_url}")
    if report_download_url:
        app.logger.info(f"Generated report download URL: {report_download_url}")

    return jsonify({
        'download_url': download_url,
        'report_download_url': report_download_url
    }), 200

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        safe_filename = secure_filename(filename)
        app.logger.info(f"Processing download request for {safe_filename}")
        response = send_from_directory(directory=app.config['DOWNLOAD_FOLDER'], path=safe_filename, as_attachment=True)
        app.logger.info(f"Sending file: {safe_filename}")
        return response
    except FileNotFoundError:
        app.logger.warning(f"File not found: {filename}")
        return jsonify({'error': '文件未找到'}), 404
    except Exception as e:
        app.logger.error(f"Error sending file {filename}: {e}")
        return jsonify({'error': '无法发送文件', 'details': str(e)}), 500

# SocketIO 事件处理（可选，当前只需确保前端能连接）
@socketio.on('connect')
def handle_connect():
    app.logger.info("Client connected")
    emit('response', {'message': '连接成功！'})

@socketio.on('disconnect')
def handle_disconnect():
    app.logger.info("Client disconnected")

if __name__ == '__main__':
    # 使用 SocketIO 运行应用
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
