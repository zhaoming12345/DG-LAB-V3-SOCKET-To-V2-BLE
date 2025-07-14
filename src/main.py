# 程序版本：Insidre-Previe-20250325-rc0
import sys
import os
import json
import logging
import asyncio
import qasync
from PySide6.QtWidgets import QApplication

# 导入settings实例
from config.settings import settings

from ui.main_window import MainWindow
# 导入setup_logging
from utils.logger import setup_logging
# 导入ProtocolConverter和常量
from core.protocol.converter import ProtocolConverter
from core.protocol.constants import BLE_CHAR_PWM_A34, BLE_CHAR_PWM_B34, BLE_CHAR_PWM_AB2

def main():
    """应用程序主入口"""
    # 设置日志 - 使用logger模块中的配置
    setup_logging()  # 调用setup_logging函数而不是使用logging.basicConfig
    
    # 记录应用程序启动信息
    logging.info("=" * 50)
    logging.info("DG-LAB Controller Application Starting")
    logging.info(f"Python Version: {sys.version}")
    logging.info(f"Operating System: {os.name} - {sys.platform}")
    
    # 确保配置文件存在并加载
    config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dg_lab_config.json')
    logging.info(f"Config file path: {config_file}")
    
    # 加载配置文件
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_content = json.load(f)
                logging.info(f"Config content: {config_content}")
                
                # 确保settings已经加载了配置文件
                settings.load()  # 强制重新加载配置
                
                # 确认最大强度值已正确加载
                logging.info(f"Loaded config, max strength: A={settings.max_strength_a}, B={settings.max_strength_b}")
                
                # 验证配置文件中的值与加载的值是否一致
                if 'max_strength_a' in config_content and settings.max_strength_a != config_content['max_strength_a']:
                    logging.warning(f"Max strength A mismatch: config={config_content['max_strength_a']}, settings={settings.max_strength_a}")
                    
                if 'max_strength_b' in config_content and settings.max_strength_b != config_content['max_strength_b']:
                    logging.warning(f"Max strength B mismatch: config={config_content['max_strength_b']}, settings={settings.max_strength_b}")
                    
                # 验证语言设置
                if 'language' in config_content:
                    logging.info(f"Language setting in config: {config_content['language']}")
        except Exception as e:
            logging.error(f"Failed to read config file: {str(e)}")
    else:
        logging.warning(f"Config file not found: {config_file}")
        
    # 记录协议转换器测试
    try:
        test_freq = 100
        x, y = ProtocolConverter.v3_freq_to_v2(test_freq)
        test_intensity = 50
        z = ProtocolConverter.v3_intensity_to_v2_z(test_intensity)
        logging.info(f"Protocol conversion test: Frequency {test_freq}Hz -> x={x}, y={y}, Intensity {test_intensity}% -> z={z}")
    except Exception as e:
        logging.error(f"Protocol conversion test failed: {str(e)}")

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
