import sys
import os
import json  # 添加json模块导入
import logging
import asyncio
import qasync
from PySide6.QtWidgets import QApplication

# 导入settings实例
from config.settings import settings

from ui.main_window import MainWindow
# 修改这一行，导入setup_logging函数
from utils.logger import setup_logging

def main():
    """应用程序主入口"""
    # 设置日志 - 使用logger模块中的配置
    setup_logging()  # 调用setup_logging函数而不是使用logging.basicConfig
    
    # 记录应用程序启动信息
    logging.info("=" * 50)
    logging.info("DG-LAB Controller 应用程序启动")
    logging.info(f"Python版本: {sys.version}")
    logging.info(f"操作系统: {os.name} - {sys.platform}")
    
    # 记录配置文件路径和内容
    config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dg_lab_config.json')
    logging.info(f"配置文件路径: {config_file}")
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_content = json.load(f)
                logging.info(f"配置文件内容: {config_content}")
                
                # 确保settings已经加载了配置文件
                settings.load()  # 强制重新加载配置
                
                # 确认最大强度值已正确加载
                logging.info(f"已加载配置，最大强度: A={settings.max_strength_a}, B={settings.max_strength_b}")
                
                # 验证配置文件中的值与加载的值是否一致
                if 'max_strength_a' in config_content and settings.max_strength_a != config_content['max_strength_a']:
                    logging.warning(f"配置文件中的A通道最大强度({config_content['max_strength_a']})与settings中的值({settings.max_strength_a})不一致")
                    
                if 'max_strength_b' in config_content and settings.max_strength_b != config_content['max_strength_b']:
                    logging.warning(f"配置文件中的B通道最大强度({config_content['max_strength_b']})与settings中的值({settings.max_strength_b})不一致")
        except Exception as e:
            logging.error(f"读取配置文件失败: {str(e)}")
    else:
        logging.warning(f"配置文件不存在: {config_file}")
        
    # 记录协议转换器测试
    try:
        test_freq = 100
        x, y = ProtocolConverter.v3_freq_to_v2(test_freq)
        test_intensity = 50
        z = ProtocolConverter.v3_intensity_to_v2_z(test_intensity)
        logging.info(f"协议转换测试: 频率{test_freq}Hz -> x={x}, y={y}, 强度{test_intensity}% -> z={z}")
    except Exception as e:
        logging.error(f"协议转换测试失败: {str(e)}")

    # 创建Qt应用
    app = QApplication(sys.argv)
    app.setApplicationName("DG-LAB Controller")
    
    # 创建事件循环
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用
    with loop:
        sys.exit(loop.run_forever())

if __name__ == "__main__":
    main()