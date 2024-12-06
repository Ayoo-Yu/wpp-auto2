import logging
import os
from logging.handlers import RotatingFileHandler

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
    
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    socketio_handler = SocketIOHandler(socketio)
    socketio_handler.setFormatter(formatter)
    socketio_handler.setLevel(logging.INFO)

    app.logger.addHandler(file_handler)
    app.logger.addHandler(socketio_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Wind Forecast Backend Startup')
