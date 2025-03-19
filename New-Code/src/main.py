import sys
import asyncio
import logging  # 添加日志模块导入
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop
from ui.main_window import MainWindow
from utils.logger import setup_logging
from config.settings import load_config

def main():
    # Windows事件循环策略设置
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 设置日志 - 移除这个重复的配置，使用setup_logging()
    # logging.basicConfig(
    #     level=logging.INFO,
    #     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    #     handlers=[
    #         logging.StreamHandler()  # 添加控制台输出处理器
    #     ]
    # )
    
    # 初始化应用
    app = QApplication(sys.argv)
    
    # 设置日志
    setup_logging()
    
    # 加载配置
    load_config()
    
    # 创建事件循环
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 运行事件循环
    with loop:
        loop.run_forever()

if __name__ == '__main__':
    main()