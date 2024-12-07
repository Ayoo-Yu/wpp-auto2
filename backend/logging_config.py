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
        self.socketio.emit('log', {'message': log_entry})

def configure_logging(app, socketio):
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # 使用基于时间的日志轮换
    file_handler = TimedRotatingFileHandler(
        'logs/app.log', 
        when='midnight',  # 每天午夜进行轮换
        interval=1,       # 间隔1天
        backupCount=10    # 保留最近10个日志文件
    )
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # 自定义 SocketIO 日志处理器
    socketio_handler = SocketIOHandler(socketio)
    socketio_handler.setFormatter(formatter)
    socketio_handler.setLevel(logging.INFO)

    # 将文件和 SocketIO 日志处理器添加到应用的日志系统中
    app.logger.addHandler(file_handler)
    app.logger.addHandler(socketio_handler)

    # 设置日志记录级别为 INFO
    app.logger.setLevel(logging.INFO)
    app.logger.info('Wind Forecast Backend Startup')
