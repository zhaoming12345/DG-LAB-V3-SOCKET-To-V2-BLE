import os
import json
import logging
from config.settings import settings  # 导入设置模块

class I18n:
    def __init__(self):
        current_dir = os.path.dirname(__file__)
        self.lang_path = os.path.abspath(os.path.join(current_dir, '..', 'languages'))
        os.makedirs(self.lang_path, exist_ok=True)
        self.translations = {}
        self.current_lang = "en_US"  # 默认使用英文
        
        logging.info(f"Language path initialized at: {self.lang_path}")
        if not os.path.exists(self.lang_path):
            logging.error(f"Language directory not found: {self.lang_path}")
            return
        
        # 添加详细日志，输出settings对象的内容
        logging.info(f"Settings object: language={getattr(settings, 'language', 'not found')}")
        
        # 自动加载默认语言
        try:
            # 尝试从设置中加载语言
            if hasattr(settings, 'language') and settings.language:
                self.current_lang = settings.language
                logging.info(f"Loading language from settings: {self.current_lang}")
            # 记录当前语言设置
            logging.info(f"Current language set to: {self.current_lang}")
        except Exception as e:
            logging.error(f"Error loading language from settings: {str(e)}")
            
        # 确保语言文件存在并加载
        if not self.load_language(self.current_lang, save_to_config=False):  # 修改这里，不保存到配置文件
            # 如果加载失败，尝试加载英文
            if self.current_lang != "en_US":
                logging.info("Failed to load selected language, trying English")
                self.load_language("en_US", save_to_config=False)

    def load_languages(self):
        """加载所有可用的语言包"""
        languages = {}
        try:
            lang_files = os.listdir(self.lang_path)
            
            for file in lang_files:
                if file.endswith('.json'):
                    lang_code = os.path.splitext(file)[0]
                    try:
                        with open(os.path.join(self.lang_path, file), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if "language_name" in data:
                                languages[lang_code] = data["language_name"]
                                logging.info(f"Found language: {lang_code} - {data['language_name']}")
                    except Exception as e:
                        logging.error(f"Failed to load language file {file}: {str(e)}")
        except Exception as e:
            logging.error(f"Failed to list language directory: {str(e)}")
                    
        return languages

    def load_language(self, lang_code, save_to_config=True):
        """加载指定的语言包
        
        Args:
            lang_code: 语言代码
            save_to_config: 是否保存到配置文件，默认为True
        """
        if not lang_code:
            logging.error("Language code is empty")
            return False
            
        try:
            file_path = os.path.join(self.lang_path, f"{lang_code}.json")
            if not os.path.exists(file_path):
                logging.error(f"Language file does not exist: {file_path}")
                # 如果指定的语言文件不存在，尝试加载英文
                if lang_code != "en_US":
                    logging.info("Trying to load default English language")
                    return self.load_language("en_US")
                return False
                
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    new_translations = json.load(f)
                    # 验证语言文件格式
                    if not isinstance(new_translations, dict):
                        logging.error(f"Invalid language file format for {lang_code}")
                        return False
                        
                    self.translations = new_translations
                    self.current_lang = lang_code
                    
                    # 只有在需要时才更新设置并保存到配置文件
                    if save_to_config:
                        settings.language = lang_code
                        settings.save()
                        logging.info(f"Successfully loaded language: {lang_code} and saved to config")
                    else:
                        logging.info(f"Successfully loaded language: {lang_code} (not saved to config)")
                    return True
                except json.JSONDecodeError as e:
                    logging.error(f"Language file {lang_code} format error: {str(e)}")
                    return False
        except Exception as e:
            logging.error(f"Failed to load language pack: {str(e)}")
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
        if not key:
            return ""
            
        try:
            # 处理嵌套键，如 "group.connection"
            keys = key.split('.')
            value = self.translations
            
            for k in keys:
                if not isinstance(value, dict):
                    logging.debug(f"Translation path broken at '{k}' for key '{key}'")
                    return key
                value = value.get(k)
                if value is None:
                    logging.debug(f"Translation key not found: '{key}'")
                    return key
            
            # 确保value是字符串类型
            value = str(value)
                    
            if args or kwargs:
                try:
                    if args and isinstance(args[0], dict) and len(args) == 1:
                        # 处理字典参数 - 用于支持 {channel} 形式的占位符
                        return value.format(**args[0])
                    else:
                        # 处理位置参数和命名参数
                        return value.format(*args, **kwargs)
                except (KeyError, IndexError, ValueError) as e:
                    logging.error(f"Format error for key '{key}': {str(e)}")
                    return value
            return value
        except Exception as e:
            logging.debug(f"Translation failed for key '{key}': {str(e)}")
            return key

# 创建全局实例
i18n = I18n()
