import logging

def setup_logging():
    """设置日志配置"""
    # 移除所有现有的处理器
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 设置日志级别    
    root_logger.setLevel(logging.DEBUG)
    
    # 添加单个控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                datefmt='%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)