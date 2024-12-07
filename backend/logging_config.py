import logging
import os
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
import queue

class SocketIOHandler(logging.Handler):
    """自定义日志处理器，通过SocketIO发送日志消息。"""
    def __init__(self, socketio):
        super().__init__()
        self.socketio = socketio

    def emit(self, record):
        log_entry = self.format(record)
        self.socketio.emit('log', {'message': log_entry})

def configure_logging(app, socketio):
    # 创建日志队列
    log_queue = queue.Queue()

    # 创建logs目录，如果不存在的话
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # 文件日志处理器，使用RotatingFileHandler
    log_file_path = 'logs/app.log'
    file_handler = RotatingFileHandler(log_file_path, maxBytes=10240, backupCount=10)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # 创建QueueHandler，将日志放入队列
    queue_handler = QueueHandler(log_queue)

    # SocketIO日志处理器
    socketio_handler = SocketIOHandler(socketio)
    socketio_handler.setFormatter(formatter)
    socketio_handler.setLevel(logging.INFO)

    # 添加队列处理器和SocketIO处理器
    app.logger.addHandler(queue_handler)
    app.logger.addHandler(socketio_handler)

    # 使用QueueListener来监听日志队列并将日志写入文件
    listener = QueueListener(log_queue, file_handler)
    listener.start()

    # 设置日志级别
    app.logger.setLevel(logging.INFO)
    app.logger.info('Wind Forecast Backend Startup')
