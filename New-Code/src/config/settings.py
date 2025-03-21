import os
import json
import logging
from config.constants import (
    DEFAULT_SOCKET_URI, DEFAULT_LANGUAGE, DEFAULT_ACCENT_COLOR,
    DEFAULT_BACKGROUND_IMAGE, DEFAULT_MAX_STRENGTH, CONFIG_FILE
)

class Settings:
    def __init__(self):
        # 使用constants.py中定义的常量
        self.config_file = CONFIG_FILE
        self.socket_uri = DEFAULT_SOCKET_URI
        self.language = DEFAULT_LANGUAGE
        self.accent_color = DEFAULT_ACCENT_COLOR
        self.background_image = DEFAULT_BACKGROUND_IMAGE
        self.max_strength_a = DEFAULT_MAX_STRENGTH['A']
        self.max_strength_b = DEFAULT_MAX_STRENGTH['B']
        self.load()
        
    def load(self):
        """从配置文件加载设置"""
        try:
            if os.path.exists(self.config_file):
                logging.info(f"正在加载配置文件: {self.config_file}")
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.socket_uri = config.get('socket_uri', "")
                    
                    # 只使用 language 字段
                    self.language = config.get('language', "en_US")
                        
                    self.accent_color = config.get('accent_color', "#7f744f")
                    self.background_image = config.get('background_image', "")
                    self.max_strength_a = config.get('max_strength_a', 50)
                    self.max_strength_b = config.get('max_strength_b', 50)
                    logging.info(f"配置已加载: {self.config_file}")
                    logging.info(f"当前语言设置: {self.language}")
            else:
                logging.warning(f"配置文件不存在: {self.config_file}，将使用默认设置")
        except Exception as e:
            logging.error(f"加载配置失败: {str(e)}")
            
    def save(self):
        """保存设置到配置文件"""
        try:
            # 确保最大强度值是整数
            self.max_strength_a = int(self.max_strength_a)
            self.max_strength_b = int(self.max_strength_b)
            
            config = {
                'socket_uri': self.socket_uri,
                'language': self.language,      # 只使用 language 字段
                'accent_color': self.accent_color,
                'background_image': self.background_image,
                'max_strength_a': self.max_strength_a,
                'max_strength_b': self.max_strength_b
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
                
            logging.info(f"配置已保存: {self.config_file}")
            logging.info(f"保存的语言设置: {self.language}")
            logging.info(f"保存的服务器地址: {self.socket_uri}")
            logging.info(f"保存的最大强度: A={self.max_strength_a}, B={self.max_strength_b}")
            return True
        except Exception as e:
            logging.error(f"保存配置失败: {str(e)}")
            return False

# 创建全局实例
settings = Settings()