import logging
import os
from logging.handlers import TimedRotatingFileHandler

class SocketIOHandler(logging.Handler):
    """自定义日志处理器，通过SocketIO发送日志消息。"""
    def __init__(self, socketio):
        super().__init__()
        self.socketio = socketio

    def emit(self, record):
        log_entry = self.format(record)
        print(f"Emitting log: {log_entry}")  # 调试信息
        self.socketio.emit('log', {'message': log_entry})

def configure_logging(app, socketio):
    # 删除原有的RotatingFileHandler配置
    # 改用更安全的日志处理方式
    
    # 控制台日志
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # 文件日志（使用FileHandler替代RotatingFileHandler）
    file_handler = logging.FileHandler(
        'logs/app.log', 
        mode='a', 
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # 添加 SocketIO 处理器
    socketio_handler = SocketIOHandler(socketio)
    socketio_handler.setLevel(logging.INFO)
    
    # 格式化
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    socketio_handler.setFormatter(formatter)
    
    # 清空原有处理器
    app.logger.handlers.clear()
    
    # 添加新处理器
    app.logger.addHandler(console_handler)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(socketio_handler)
    app.logger.setLevel(logging.DEBUG)
    
    # 添加Socket.IO日志
    engineio_logger = logging.getLogger('engineio')
    engineio_logger.addHandler(console_handler)
    engineio_logger.addHandler(file_handler)
    engineio_logger.addHandler(socketio_handler)

    app.logger.info('Wind Forecast Backend Startup')
