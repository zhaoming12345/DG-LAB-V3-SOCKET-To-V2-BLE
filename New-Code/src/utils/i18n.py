import os
import json
import logging

class I18n:
    def __init__(self):
        current_dir = os.path.dirname(__file__)
        self.lang_path = os.path.abspath(os.path.join(current_dir, '..', 'languages'))
        os.makedirs(self.lang_path, exist_ok=True)
        self.translations = {}
        self.current_lang = "zh_CN"  # 默认使用中文
        
        logging.info(f"Language path initialized at: {self.lang_path}")
        if not os.path.exists(self.lang_path):
            logging.error(f"Language directory not found: {self.lang_path}")
        
        # 自动加载默认语言
        self.load_language(self.current_lang)

    def load_languages(self):
        """加载所有可用的语言包"""
        languages = {}
        lang_files = os.listdir(self.lang_path)
        
        for file in lang_files:
            if file.endswith('.json'):
                lang_code = os.path.splitext(file)[0]
                try:
                    with open(os.path.join(self.lang_path, file), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if "language_name" in data:
                            languages[lang_code] = data["language_name"]
                except Exception as e:
                    logging.error(f"加载语言文件失败 {file}: {str(e)}")
                    
        return languages
        
    def load_language(self, lang_code):
        """加载指定的语言包"""
        try:
            file_path = os.path.join(self.lang_path, f"{lang_code}.json")
            with open(file_path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
                self.current_lang = lang_code
                logging.info(f"成功加载语言: {lang_code}")
                return True
        except Exception as e:
            logging.error(f"加载语言包失败: {str(e)}")
            return False
            
    def translate(self, key: str, *args, **kwargs) -> str:
        """翻译指定的文本键值
        
        Args:
            key: 翻译键值，如 "device.status"
            *args: 位置格式化参数
            **kwargs: 命名格式化参数，用于支持命名占位符
            
        Returns:
            翻译后的文本，如果找不到对应的键值则返回原键值
        """
        try:
            # 处理嵌套键，如 "group.connection"
            keys = key.split('.')
            value = self.translations
            
            for k in keys:
                value = value[k]
            
            # 确保value是字符串类型
            value = str(value)
                    
            if args or kwargs:
                if args and isinstance(args[0], dict) and len(args) == 1:
                    # 处理字典参数 - 用于支持 {channel} 形式的占位符
                    return value.format(**args[0])
                else:
                    # 处理位置参数和命名参数
                    return value.format(*args, **kwargs)
            return value
        except Exception as e:
            logging.debug(f"翻译键值失败 '{key}': {str(e)}")
            return key

# 创建全局实例
i18n = I18n()
