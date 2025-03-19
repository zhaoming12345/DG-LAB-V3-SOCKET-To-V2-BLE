import os
import json
import logging
from pathlib import Path

class Settings:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.base_path = Path(__file__).parent.parent.parent
        self.config_file = self.base_path / "dg_lab_config.json"
        self.lang_path = self.base_path / "languages"
        
        # 默认配置
        self.socket_uri = ""
        self.current_lang = "zh_CN"
        self.accent_color = "#7f744f"
        self.background_image = str(self.base_path / "background.png")
        self.max_strength = {'A': 100, 'B': 100}
        
        # 加载配置
        self.load()
    
    def load(self):
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.socket_uri = config.get('socket_uri', self.socket_uri)
                    self.current_lang = config.get('language', self.current_lang)
                    self.accent_color = config.get('accent_color', self.accent_color)
                    self.background_image = config.get('background_image', self.background_image)
                    self.max_strength['A'] = config.get('max_strength_a', self.max_strength['A'])
                    self.max_strength['B'] = config.get('max_strength_b', self.max_strength['B'])
        except Exception as e:
            logging.error(f"加载配置文件失败: {str(e)}")
    
    def save(self):
        """保存配置到文件"""
        try:
            config = {
                'socket_uri': self.socket_uri,
                'language': self.current_lang,
                'accent_color': self.accent_color,
                'background_image': self.background_image,
                'max_strength_a': self.max_strength['A'],
                'max_strength_b': self.max_strength['B']
            }
            
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"保存配置文件失败: {str(e)}")
            return False

# 全局设置实例
settings = Settings()

def load_config():
    """加载配置的便捷函数"""
    settings.load()