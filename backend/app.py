import os
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from config import Config
from logging_config import configure_logging

app = Flask(__name__)
app.config.from_object(Config)

CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# 配置日志
configure_logging(app, socketio)

# 注册蓝图
from routes.upload import upload_bp
from routes.predict import predict_bp
from routes.download import download_bp

app.register_blueprint(upload_bp, url_prefix='/')
app.register_blueprint(predict_bp, url_prefix='/')
app.register_blueprint(download_bp, url_prefix='/')

@app.errorhandler(413)
def request_entity_too_large(error):
    app.logger.warning("文件太大，超过限制")
    return {'error': '文件太大，最大允许200MB'}, 413

# SocketIO 事件
@socketio.on('connect')
def handle_connect():
    app.logger.info("Client connected")
    socketio.emit('response', {'message': '连接成功！'})

@socketio.on('disconnect')
def handle_disconnect():
    app.logger.info("Client disconnected")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
