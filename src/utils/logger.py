import logging
from PySide6.QtCore import Signal, QObject
import os
from config.constants import LOG_DIR, LOG_FILE

# 创建一个QObject子类来发出日志信号
class LogSignalEmitter(QObject):
    log_signal = Signal(str)
    
    def __init__(self):
        super().__init__()
        
log_emitter = LogSignalEmitter()

class QtHandler(logging.Handler):
    """将日志消息发送到Qt信号的处理器"""
    def __init__(self):
        super().__init__()
        self.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S'))
        
    def emit(self, record):
        msg = self.format(record)
        log_emitter.log_signal.emit(msg)

def setup_logging():
    """设置日志配置"""
    # 移除所有现有的处理器
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 设置日志级别    
    root_logger.setLevel(logging.DEBUG)  # 确保根日志记录器级别为DEBUG
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # 控制台只显示INFO及以上级别
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 添加Qt信号处理器 - 确保UI中也能显示足够的日志
    qt_handler = QtHandler()
    qt_handler.setLevel(logging.INFO)  # 确保UI显示INFO及以上级别
    root_logger.addHandler(qt_handler)
    
    # 添加文件处理器 - 确保记录所有级别的日志
    try:
        # 使用constants.py中定义的常量
        os.makedirs(LOG_DIR, exist_ok=True)
        
        # 使用 'w' 模式打开文件，这会清空现有内容
        file_handler = logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # 确保文件记录所有DEBUG及以上级别
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        logging.info(f"日志文件已创建: {LOG_FILE}")
    except Exception as e:
        logging.error(f"创建日志文件失败: {str(e)}")
    
    # 防止日志传播到父记录器，避免重复日志
    root_logger.propagate = False
    
    logging.info("日志系统初始化完成")