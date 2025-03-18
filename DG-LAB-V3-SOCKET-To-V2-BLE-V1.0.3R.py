import sys
import asyncio
import json
import struct
import logging
import os
import glob
import re
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QGroupBox, QDialog, QListWidget, QFrame,
    QComboBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QIcon, QFont
from qasync import QEventLoop, asyncSlot
import websockets
from bleak import BleakClient, discover, BleakError
from collections import deque
from PySide6.QtGui import QIntValidator
import pyqtgraph as pg

# ------------ 事件循环策略（Windows必需）------------
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ------------ 控制台Debug日志设置 ------------
logging.basicConfig(level=logging.DEBUG)

# ------------ 全局配置 ------------
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dg_lab_config.json")
SOCKET_URI = ""
BLE_DEVICE_ADDRESS = ""
DEVICE_ID = ""
DEFAULT_MAX_STRENGTH = {'A': 100, 'B': 100}
DARK_MODE = False
LANG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "languages")
CURRENT_LANG = "zh_CN"
TRANSLATIONS = {}

# ------------ BLE 特征值 UUID ------------
BLE_CHAR_PWM_A34 = "0000ffe1-0000-1000-8000-00805f9b34fb"
BLE_CHAR_PWM_B34 = "0000ffe2-0000-1000-8000-00805f9b34fb"
BLE_CHAR_PWM_AB2 = "0000ffe3-0000-1000-8000-00805f9b34fb"
BLE_CHAR_BATTERY = "0000ffe4-0000-1000-8000-00805f9b34fb"

# ------------ 多语言支持函数 ------------
def load_available_languages():
    """加载所有可用的语言包文件"""
    logging.info("开始加载可用语言...")
    languages = {}
    
    # 检查语言目录是否存在
    if not os.path.exists(LANG_PATH):
        logging.error(f"语言目录不存在: {os.path.abspath(LANG_PATH)}")
        return languages
    
    # 获取语言文件列表
    lang_files = glob.glob(os.path.join(LANG_PATH, "*.json"))
    logging.info(f"找到语言文件列表: {lang_files}")
    
    if not lang_files:
        logging.error(f"在目录 {os.path.abspath(LANG_PATH)} 中没有找到任何json文件")
        return languages
    
    for lang_file in lang_files:
        lang_code = os.path.splitext(os.path.basename(lang_file))[0]
        logging.info(f"正在处理语言文件: {lang_file}")
        
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                try:
                    lang_data = json.load(f)
                    logging.info(f"成功解析语言文件: {lang_file}")
                    if "language_name" in lang_data:
                        lang_name = lang_data["language_name"]
                        logging.info(f"找到语言名称: {lang_name}")
                    else:
                        lang_name = lang_code
                        logging.warning(f"语言文件中没有language_name字段，使用文件名作为语言名称: {lang_code}")
                    languages[lang_code] = lang_name
                except json.JSONDecodeError as je:
                    logging.error(f"语言文件JSON解析失败 {lang_file}: {str(je)}")
                    continue
        except Exception as e:
            logging.error(f"读取语言文件失败 {lang_file}: {str(e)}")
            continue
    
    logging.info(f"最终加载的语言列表: {languages}")
    return languages

def load_language(lang_code):
    """加载指定的语言包"""
    global TRANSLATIONS
    logging.info(f"开始加载语言包: {lang_code}")
    
    try:
        lang_file = os.path.join(LANG_PATH, f"{lang_code}.json")
        abs_path = os.path.abspath(lang_file)
        logging.info(f"语言文件完整路径: {abs_path}")
        
        if not os.path.exists(lang_file):
            logging.error(f"语言文件不存在: {abs_path}")
            return False
            
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
                logging.info(f"成功读取语言文件，内容长度: {len(file_content)} 字节")
                try:
                    TRANSLATIONS = json.loads(file_content)
                    logging.info(f"成功解析语言文件，包含 {len(TRANSLATIONS)} 个翻译项")
                    return True
                except json.JSONDecodeError as je:
                    logging.error(f"语言文件JSON解析失败: {str(je)}")
                    return False
        except Exception as e:
            logging.error(f"读取语言文件失败: {str(e)}")
            return False
    except Exception as e:
        logging.error(f"加载语言包过程中发生错误: {str(e)}")
        return False

def translate(key, *args):
    """翻译指定的文本键值，支持格式化参数"""
    global TRANSLATIONS
    
    # 处理嵌套键，如 "status_updates.connection_failed"
    keys = key.split('.')
    value = TRANSLATIONS
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            # 键不存在，返回原始键
            return key
    
    # 如果不是字符串，返回原始键
    if not isinstance(value, str):
        return key
    
    # 格式化替换 {0}, {1} 等参数
    if args:
        try:
            return value.format(*args)
        except:
            return value
    
    return value

# ------------ 蓝牙服务配置 ------------
BLE_SERVICE_UUID = "955A180b-0FE2-F5AA-A094-84B8D4F3E8AD"
BLE_CHAR_DEVICE_ID = "955A1501-0FE2-F5AA-A094-84B8D4F3E8AD"  #设备ID特征
BLE_SERVICE_BATTERY = "0000180f-0000-1000-8000-00805f9b34fb"  # 电池服务

# ------------ 界面样式定义 ------------
LIGHT_STYLE = """
QMainWindow, QDialog {
    background-color: #f0f0f0;
}
QGroupBox {
    border: 1px solid #cccccc;
    border-radius: 5px;
    margin-top: 10px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px;
}
QPushButton {
    background-color: #007bff;
    color: white;
    border: none;
    padding: 5px 15px;
    border-radius: 3px;
}
QPushButton:hover {
    background-color: #0056b3;
}
QPushButton:disabled {
    background-color: #cccccc;
}
QLineEdit {
    padding: 5px;
    border: 1px solid #cccccc;
    border-radius: 3px;
}
QTextEdit {
    border: 1px solid #cccccc;
    border-radius: 3px;
}
"""

DARK_STYLE = """
QMainWindow, QDialog {
    background-color: #2b2b2b;
    color: #ffffff;
}
QGroupBox {
    border: 1px solid #555555;
    border-radius: 5px;
    margin-top: 10px;
    font-weight: bold;
    color: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px;
    color: #ffffff;
}
QPushButton {
    background-color: #0d47a1;
    color: white;
    border: none;
    padding: 5px 15px;
    border-radius: 3px;
}
QPushButton:hover {
    background-color: #1565c0;
}
QPushButton:disabled {
    background-color: #424242;
}
QLineEdit {
    padding: 5px;
    border: 1px solid #555555;
    border-radius: 3px;
    background-color: #424242;
    color: #ffffff;
}
QTextEdit {
    border: 1px solid #555555;
    border-radius: 3px;
    background-color: #424242;
    color: #ffffff;
}
QLabel {
    color: #ffffff;
}
QComboBox {
    background-color: #424242;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 5px;
}
QComboBox::drop-down {
    border: none;
}
QComboBox::down-arrow {
    image: url(down_arrow.png);
    width: 12px;
    height: 12px;
}
QComboBox QAbstractItemView {
    background-color: #424242;
    color: #ffffff;
    selection-background-color: #0d47a1;
}
"""

# ------------ 辅助函数 ------------
def is_valid_websocket_url(url):
    """验证WebSocket URL是否有效"""
    # 检查URL格式
    ws_pattern = r'^(ws|wss):\/\/[^\s\/$.?#].[^\s]*$'
    return bool(re.match(ws_pattern, url))

async def check_bluetooth_available():
    """检查蓝牙是否可用"""
    try:
        devices = await discover()
        return True
    except BleakError:
        return False
    except Exception:
        return False

class DeviceScanner(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translate("dialog.choose_device"))
        self.setGeometry(200, 200, 400, 400)
        self.setModal(True)  # 设置为模态对话框
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)  # 添加窗口标志
        
        # 创建布局
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 标题
        title_label = QLabel(translate("dialog.choose_device"))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 设备列表
        self.device_list = QListWidget()
        self.device_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #cccccc;
            }
            QListWidget::item:selected {
                background-color: #007bff;
                color: white;
            }
        """)
        layout.addWidget(self.device_list)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        self.refresh_btn = QPushButton(translate("dialog.refresh_devices"))
        self.refresh_btn.setMinimumWidth(120)
        self.cancel_btn = QPushButton(translate("dialog.cancel"))
        self.cancel_btn.setMinimumWidth(120)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        # 状态标签
        self.status_label = QLabel(translate("dialog.scanning"))  # 设置初始状态为正在扫描
        self.status_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # 连接信号
        self.refresh_btn.clicked.connect(self.on_refresh_clicked)
        self.cancel_btn.clicked.connect(self.reject)
        
        # 扫描任务
        self.scan_task = None
        
        # 应用主题
        self.apply_theme()
        
        # 初始禁用刷新按钮，等待第一次扫描完成
        self.refresh_btn.setEnabled(False)
        
    def apply_theme(self):
        """应用深色/浅色主题"""
        if DARK_MODE:
            self.setStyleSheet(DARK_STYLE + """
                QDialog {
                    background-color: #2b2b2b;
                }
                QListWidget {
                    background-color: #424242;
                    border: 1px solid #555555;
                    color: white;
                }
                QListWidget::item {
                    border-bottom: 1px solid #555555;
                }
                QListWidget::item:selected {
                    background-color: #0d47a1;
                }
                QLabel {
                    color: white;
                }
            """)
        else:
            self.setStyleSheet(LIGHT_STYLE + """
                QDialog {
                    background-color: white;
                }
                QListWidget {
                    background-color: white;
                }
            """)
            
    @asyncSlot()
    async def start_scan(self):
        """开始扫描设备"""
        try:
            if self.scan_task and not self.scan_task.done():
                return
                
            self.refresh_btn.setEnabled(False)
            self.status_label.setText(translate("dialog.scanning"))
            self.device_list.clear()
            
            # 检查蓝牙是否可用
            if not await check_bluetooth_available():
                self.status_label.setText(translate("dialog.bluetooth_not_available"))
                self.refresh_btn.setEnabled(True)
                return

            devices = await discover()
            self.device_list.clear()
            for d in devices:
                item_text = f"{d.name} | {d.address}" if d.name else f"{translate('device.unknown')} | {d.address}"
                self.device_list.addItem(item_text)
                
            if not devices:
                self.status_label.setText(translate("dialog.no_devices_found"))
            else:
                self.status_label.setText(translate("dialog.scan_complete"))
                
        except Exception as e:
            self.status_label.setText(translate("dialog.scan_failed", str(e)))
        finally:
            self.refresh_btn.setEnabled(True)

    @asyncSlot()
    async def on_refresh_clicked(self):
        """处理刷新按钮点击事件"""
        try:
            # 直接调用start_scan，不创建新的任务
            await self.start_scan()
        except Exception as e:
            self.status_label.setText(translate("dialog.scan_failed", str(e)))
            self.refresh_btn.setEnabled(True)

class DeviceSignals(QObject):
    status_update = Signal(str, str)
    log_message = Signal(str)
    device_selected = Signal(str)
    device_id_updated = Signal(str)
    connection_changed = Signal(bool)
    language_changed = Signal(str)
        
class LogWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translate("log.title"))
        self.setGeometry(100, 100, 600, 400)
        
        # 创建中心部件和布局
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        # 创建日志文本区域
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        
        # 清除日志按钮
        clear_btn = QPushButton(translate("log.clear"))
        clear_btn.clicked.connect(self.clear_logs)
        layout.addWidget(clear_btn)
        
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # 应用当前主题
        self.apply_theme()
        
    def apply_theme(self):
        style = DARK_STYLE if DARK_MODE else LIGHT_STYLE
        self.setStyleSheet(style)
        
    def closeEvent(self, event):
        # 通知父窗口日志窗口已关闭
        if isinstance(self.parent(), MainWindow):
            self.parent().on_log_window_closed()
        event.accept()
        
    def append_log(self, message):
        self.log_area.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        
    def clear_logs(self):
        self.log_area.clear()

    def toggle_log_window(self):
        if self.log_window is None:
            self.log_window = LogWindow(self)
        
        if self.log_window.isVisible():
            self.log_window.hide()
            self.log_window_btn.setText(translate("log.show"))
        else:
            self.log_window.show()
            self.log_window_btn.setText(translate("log.hide"))

    def on_log_window_closed(self):
        """当日志窗口被关闭时调用"""
        self.log_window_btn.setText(translate("log.show"))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.signals = DeviceSignals()
        self.ble_client = None
        self.ws_client = None  # WebSocket客户端
        self.wave_queues = {'A': deque(maxlen=100), 'B': deque(maxlen=100)}  # 限制队列长度为100个点
        self.current_strength = {'A': 0, 'B': 0}
        self.max_strength = DEFAULT_MAX_STRENGTH.copy()
        self.selected_device = ""
        self.log_window = None
        
        logging.info("开始初始化主窗口...")
        
        # 加载可用语言
        logging.info("开始加载可用语言列表...")
        self.available_languages = load_available_languages()
        logging.info(f"可用语言列表: {self.available_languages}")
        
        # 确保至少有一种语言可用
        if not self.available_languages:
            logging.warning("没有找到语言包文件，使用默认中文")
            self.available_languages = {"zh_CN": "简体中文"}
        
        # 加载配置
        logging.info("开始加载配置...")
        self.load_config()
        
        # 加载语言包
        global CURRENT_LANG
        logging.info(f"尝试加载默认语言: {CURRENT_LANG}")
        if not load_language(CURRENT_LANG):
            logging.warning(f"加载默认语言 {CURRENT_LANG} 失败，尝试加载备选语言")
            # 如果加载失败，尝试加载中文
            if "zh_CN" in self.available_languages and load_language("zh_CN"):
                logging.info("成功加载中文语言包")
                CURRENT_LANG = "zh_CN"
            # 如果中文也不可用，尝试加载任何可用的语言
            elif self.available_languages:
                first_lang = next(iter(self.available_languages.keys()))
                logging.info(f"尝试加载第一个可用语言: {first_lang}")
                if load_language(first_lang):
                    logging.info(f"成功加载语言: {first_lang}")
                    CURRENT_LANG = first_lang
                else:
                    logging.error("所有语言包加载都失败")
        
        logging.info("开始初始化UI...")
        self.init_ui()
        self.setup_connections()
        self.apply_theme()
        
        # 启动波形更新定时器
        self.update_timer = pg.QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_plot)
        self.update_timer.start(50)  # 每50ms更新一次
        
        logging.info("主窗口初始化完成")

    def load_config(self):
        global SOCKET_URI, DARK_MODE, CURRENT_LANG
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    # 先读取为字符串
                    config_str = f.read()
                    # 替换JavaScript布尔值为Python布尔值
                    config_str = config_str.replace('true', 'True').replace('false', 'False')
                    # 使用eval安全地解析配置
                    config = eval(config_str)
                    SOCKET_URI = config.get('socket_uri', "")
                    self.max_strength['A'] = config.get('max_strength_a', DEFAULT_MAX_STRENGTH['A'])
                    self.max_strength['B'] = config.get('max_strength_b', DEFAULT_MAX_STRENGTH['B'])
                    DARK_MODE = config.get('dark_mode', False)
                    CURRENT_LANG = config.get('language', "zh_CN")
        except Exception as e:
            logging.error(f"加载配置文件失败: {str(e)}")
            # 使用默认值
            SOCKET_URI = ""
            self.max_strength = DEFAULT_MAX_STRENGTH.copy()
            DARK_MODE = False
            CURRENT_LANG = "zh_CN"

    def save_config(self):
        global DARK_MODE, CURRENT_LANG
        config = {
            'socket_uri': SOCKET_URI,
            'max_strength_a': self.max_strength['A'],
            'max_strength_b': self.max_strength['B'],
            'dark_mode': DARK_MODE,
            'language': CURRENT_LANG
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                # 使用Python的repr来确保布尔值正确写入
                config_str = "{\n"
                config_str += f'    "socket_uri": "{config["socket_uri"]}",\n'
                config_str += f'    "max_strength_a": {config["max_strength_a"]},\n'
                config_str += f'    "max_strength_b": {config["max_strength_b"]},\n'
                config_str += f'    "dark_mode": {str(config["dark_mode"])},\n'
                config_str += f'    "language": "{config["language"]}"\n'
                config_str += "}"
                f.write(config_str)
            return True
        except Exception as e:
            logging.error(f"保存配置文件失败: {str(e)}")
            return False

    def apply_theme(self):
        global DARK_MODE
        style = DARK_STYLE if DARK_MODE else LIGHT_STYLE
        self.setStyleSheet(style)
        
        # 更新波形显示主题
        if hasattr(self, 'plot_widget_a') and hasattr(self, 'plot_widget_b'):
            for plot_widget in [self.plot_widget_a, self.plot_widget_b]:
                if DARK_MODE:
                    plot_widget.setBackground('#2b2b2b')
                    plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#ffffff'))
                    plot_widget.getAxis('left').setPen(pg.mkPen(color='#ffffff'))
                    plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color='#ffffff'))
                    plot_widget.getAxis('left').setTextPen(pg.mkPen(color='#ffffff'))
                else:
                    plot_widget.setBackground('w')
                    plot_widget.getAxis('bottom').setPen(pg.mkPen(color='k'))
                    plot_widget.getAxis('left').setPen(pg.mkPen(color='k'))
                    plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color='k'))
                    plot_widget.getAxis('left').setTextPen(pg.mkPen(color='k'))
        
        # 更新日志窗口主题
        if self.log_window:
            self.log_window.apply_theme()
            
        # 更新主题切换按钮文本
        if hasattr(self, 'theme_btn'):
            self.theme_btn.setText(translate("theme.toggle"))

    def toggle_theme(self):
        global DARK_MODE
        DARK_MODE = not DARK_MODE
        self.apply_theme()
        self.save_config()
        self.signals.log_message.emit(translate("status_updates.theme_changed", 
            translate("theme.dark" if DARK_MODE else "theme.light")))

    def change_language(self, lang_code):
        """切换界面语言"""
        logging.debug(f"开始切换语言到: {lang_code}")
        global CURRENT_LANG
        if load_language(lang_code):
            logging.debug("语言包加载成功")
            CURRENT_LANG = lang_code
            self.update_ui_texts()
            self.save_config()
            logging.debug("UI文本更新完成，配置已保存")
            self.signals.language_changed.emit(translate("language_name"))
        else:
            logging.error(f"切换语言失败: {lang_code}")

    def update_ui_texts(self):
        """更新所有UI元素的文本"""
        logging.debug("开始更新UI文本")
        try:
            # 更新窗口标题
            self.setWindowTitle(translate("app_title"))
            self.title_label.setText(translate("main_title"))
            
            # 更新主题按钮
            self.theme_btn.setText(translate("theme.toggle"))
            
            # 更新设备管理组
            self.device_group.setTitle(translate("device.management"))
            self.scan_btn.setText(translate("device.scan"))
            self.connect_btn.setText(translate("device.connect"))
            self.device_label.setText(translate("device.status", translate("device.unknown")))
            
            # 更新服务器配置组
            self.server_group.setTitle(translate("server.config"))
            self.server_address_label.setText(translate("server.address"))
            self.save_server_btn.setText(translate("server.save"))
            
            # 更新强度配置组
            self.config_group.setTitle(translate("strength.config"))
            self.channel_a_limit_label.setText(translate("strength.channel_a_limit"))
            self.channel_b_limit_label.setText(translate("strength.channel_b_limit"))
            self.save_btn.setText(translate("strength.save"))
            
            # 更新状态组
            self.status_group.setTitle(translate("status.realtime"))
            
            # 更新控制组
            self.control_group.setTitle(translate("control.manual"))
            self.test_a_btn.setText(translate("control.test_a"))
            self.test_b_btn.setText(translate("control.test_b"))
            self.clear_a_btn.setText(translate("control.clear_a"))
            self.clear_b_btn.setText(translate("control.clear_b"))
            
            # 更新日志组
            self.log_group.setTitle(translate("log.title"))
            
            logging.debug("UI文本更新完成")
        except Exception as e:
            logging.error(f"更新UI文本时发生错误: {str(e)}")

    def init_ui(self):
        self.setWindowTitle(translate("app_title"))
        self.setGeometry(100, 100, 800, 700)
        
        # 设置字体
        font = QFont("Microsoft YaHei", 9)
        self.setFont(font)
        
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 顶部标题和主题切换
        top_layout = QHBoxLayout()
        self.title_label = QLabel(translate("main_title"))
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.theme_btn = QPushButton(translate("theme.toggle"))
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.log_window_btn = QPushButton(translate("log.show"))
        self.log_window_btn.clicked.connect(self.toggle_log_window)
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()
        top_layout.addWidget(self.log_window_btn)
        top_layout.addWidget(self.theme_btn)
        main_layout.addLayout(top_layout)
        
        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # 语言选择
        self.lang_group = QGroupBox(translate("language.setting"))
        lang_layout = QHBoxLayout()
        self.lang_combo = QComboBox()
        
        # 填充语言下拉列表
        for lang_code, lang_name in self.available_languages.items():
            self.lang_combo.addItem(lang_name, lang_code)
            if lang_code == CURRENT_LANG:
                self.lang_combo.setCurrentText(lang_name)
        
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        lang_layout.addWidget(self.lang_combo)
        self.lang_group.setLayout(lang_layout)
        main_layout.addWidget(self.lang_group)
        
        # 设备管理组
        self.device_group = QGroupBox(translate("device.management"))
        device_layout = QHBoxLayout()
        self.scan_btn = QPushButton(translate("device.scan"))
        self.connect_btn = QPushButton(translate("device.connect"))
        self.connect_btn.setEnabled(False)
        self.device_label = QLabel(translate("device.status"))
        device_layout.addWidget(self.scan_btn)
        device_layout.addWidget(self.connect_btn)
        device_layout.addWidget(self.device_label)
        self.device_group.setLayout(device_layout)
        main_layout.addWidget(self.device_group)
        
        # 服务器配置组
        self.server_group = QGroupBox(translate("server.config"))
        server_layout = QHBoxLayout()
        self.server_address_label = QLabel(translate("server.address"))
        self.server_input = QLineEdit()
        self.server_input.setText(SOCKET_URI)
        self.save_server_btn = QPushButton(translate("server.save"))
        self.connect_server_btn = QPushButton("连接服务器")
        self.connect_server_btn.setEnabled(False)  # 初始禁用
        server_layout.addWidget(self.server_address_label)
        server_layout.addWidget(self.server_input)
        server_layout.addWidget(self.save_server_btn)
        server_layout.addWidget(self.connect_server_btn)
        self.server_group.setLayout(server_layout)
        main_layout.addWidget(self.server_group)
        
        # 配置区域
        self.config_group = QGroupBox(translate("strength.config"))
        config_layout = QHBoxLayout()
        self.channel_a_limit_label = QLabel(translate("strength.channel_a_limit"))
        self.channel_b_limit_label = QLabel(translate("strength.channel_b_limit"))
        self.a_max_input = QLineEdit(str(self.max_strength['A']))
        self.b_max_input = QLineEdit(str(self.max_strength['B']))
        
        # 设置输入验证
        validator = QIntValidator(0, 200)
        self.a_max_input.setValidator(validator)
        self.b_max_input.setValidator(validator)
        
        self.save_btn = QPushButton(translate("strength.save"))
        config_layout.addWidget(self.channel_a_limit_label)
        config_layout.addWidget(self.a_max_input)
        config_layout.addWidget(self.channel_b_limit_label)
        config_layout.addWidget(self.b_max_input)
        config_layout.addWidget(self.save_btn)
        self.config_group.setLayout(config_layout)
        main_layout.addWidget(self.config_group)
        
        # 状态显示
        self.status_group = QGroupBox(translate("status.realtime"))
        status_layout = QHBoxLayout()
        self.a_status = QLabel(translate("status.channel_a").format(0, self.max_strength['A']))
        self.b_status = QLabel(translate("status.channel_b").format(0, self.max_strength['B']))
        self.battery_label = QLabel(translate("status.battery").format("--"))
        self.rssi_label = QLabel(translate("status.signal_unknown"))
        status_layout.addWidget(self.a_status)
        status_layout.addWidget(self.b_status)
        status_layout.addWidget(self.battery_label)
        status_layout.addWidget(self.rssi_label)
        self.status_group.setLayout(status_layout)
        main_layout.addWidget(self.status_group)
        
        # 控制按钮
        self.control_group = QGroupBox(translate("control.manual"))
        control_layout = QHBoxLayout()
        self.test_a_btn = QPushButton(translate("control.test_a"))
        self.test_b_btn = QPushButton(translate("control.test_b"))
        self.clear_a_btn = QPushButton(translate("control.clear_a"))
        self.clear_b_btn = QPushButton(translate("control.clear_b"))
        control_layout.addWidget(self.test_a_btn)
        control_layout.addWidget(self.test_b_btn)
        control_layout.addWidget(self.clear_a_btn)
        control_layout.addWidget(self.clear_b_btn)
        self.control_group.setLayout(control_layout)
        main_layout.addWidget(self.control_group)
        
        # 波形显示区域
        wave_layout = QHBoxLayout()
        
        # A通道波形显示
        self.plot_widget_a = pg.PlotWidget()
        self.plot_widget_a.setBackground('w')
        self.plot_widget_a.setTitle("A通道实时波形")
        self.plot_widget_a.setLabel('left', '强度')
        self.plot_widget_a.setLabel('bottom', '时间')
        self.plot_widget_a.showGrid(x=True, y=True)
        self.plot_widget_a.setMouseEnabled(x=False, y=False)
        self.plot_widget_a.setMenuEnabled(False)
        view_box_a = self.plot_widget_a.getViewBox()
        view_box_a.setMouseMode(pg.ViewBox.RectMode)
        view_box_a.setMouseEnabled(x=False, y=False)
        view_box_a.enableAutoRange(enable=False)
        
        # B通道波形显示
        self.plot_widget_b = pg.PlotWidget()
        self.plot_widget_b.setBackground('w')
        self.plot_widget_b.setTitle("B通道实时波形")
        self.plot_widget_b.setLabel('left', '强度')
        self.plot_widget_b.setLabel('bottom', '时间')
        self.plot_widget_b.showGrid(x=True, y=True)
        self.plot_widget_b.setMouseEnabled(x=False, y=False)
        self.plot_widget_b.setMenuEnabled(False)
        view_box_b = self.plot_widget_b.getViewBox()
        view_box_b.setMouseMode(pg.ViewBox.RectMode)
        view_box_b.setMouseEnabled(x=False, y=False)
        view_box_b.enableAutoRange(enable=False)
        
        # 保存初始显示范围
        self.expected_y_range = (0, max(self.max_strength['A'], self.max_strength['B']))
        self.expected_x_range = (-100, 0)  # 显示最近100个数据点
        self.plot_widget_a.setYRange(*self.expected_y_range)
        self.plot_widget_a.setXRange(*self.expected_x_range)
        self.plot_widget_b.setYRange(*self.expected_y_range)
        self.plot_widget_b.setXRange(*self.expected_x_range)
        
        # 创建两条曲线
        self.curve_a = self.plot_widget_a.plot(pen=pg.mkPen(color='r', width=2), name='A通道')
        self.curve_b = self.plot_widget_b.plot(pen=pg.mkPen(color='b', width=2), name='B通道')
        
        # 添加到布局
        wave_layout.addWidget(self.plot_widget_a)
        wave_layout.addWidget(self.plot_widget_b)
        main_layout.addLayout(wave_layout, 1)  # 1表示拉伸因子
        
        # 创建范围监控定时器
        self.range_monitor = pg.QtCore.QTimer()
        self.range_monitor.timeout.connect(self.check_plot_range)
        self.range_monitor.start(50)  # 每50ms检查一次
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def check_plot_range(self):
        """检查并恢复波形显示范围"""
        # 检查A通道波形范围
        view_range_a = self.plot_widget_a.viewRange()
        current_y_range_a = view_range_a[1]
        current_x_range_a = view_range_a[0]
        
        # 检查B通道波形范围
        view_range_b = self.plot_widget_b.viewRange()
        current_y_range_b = view_range_b[1]
        current_x_range_b = view_range_b[0]
        
        # 如果当前范围与期望范围不同，立即恢复
        if current_y_range_a != self.expected_y_range:
            self.plot_widget_a.setYRange(*self.expected_y_range, padding=0)
        if current_x_range_a != self.expected_x_range:
            self.plot_widget_a.setXRange(*self.expected_x_range, padding=0)
            
        if current_y_range_b != self.expected_y_range:
            self.plot_widget_b.setYRange(*self.expected_y_range, padding=0)
        if current_x_range_b != self.expected_x_range:
            self.plot_widget_b.setXRange(*self.expected_x_range, padding=0)
            
        # 确保鼠标交互被禁用
        for plot_widget in [self.plot_widget_a, self.plot_widget_b]:
            plot_widget.setMouseEnabled(x=False, y=False)
            view_box = plot_widget.getViewBox()
            view_box.setMouseMode(pg.ViewBox.RectMode)
            view_box.setMouseEnabled(x=False, y=False)

    def update_plot(self):
        # 更新波形显示
        if self.wave_queues['A']:
            self.curve_a.setData(list(self.wave_queues['A']))
        if self.wave_queues['B']:
            self.curve_b.setData(list(self.wave_queues['B']))

    def toggle_log_window(self):
        if self.log_window is None:
            self.log_window = LogWindow(self)
        
        if self.log_window.isVisible():
            self.log_window.hide()
            self.log_window_btn.setText(translate("log.show"))
        else:
            self.log_window.show()
            self.log_window_btn.setText(translate("log.hide"))

    def on_log_window_closed(self):
        """当日志窗口被关闭时调用"""
        self.log_window_btn.setText(translate("log.show"))

    def log_output(self, message):
        if self.log_window:
            self.log_window.append_log(message)

    def setup_connections(self):
        self.scan_btn.clicked.connect(self.show_scanner)
        self.connect_btn.clicked.connect(self.on_connect_clicked)
        self.connect_server_btn.clicked.connect(self.on_connect_server_clicked)
        self.signals.device_selected.connect(self.update_device_address)
        self.signals.device_id_updated.connect(self.update_device_id)
        self.signals.connection_changed.connect(self.update_ui_state)
        self.signals.status_update.connect(self.update_status)
        self.signals.log_message.connect(self.log_output)
        self.save_btn.clicked.connect(self.update_max_strength)
        self.test_a_btn.clicked.connect(lambda: self.send_strength_command(1, 1, 10))
        self.test_b_btn.clicked.connect(lambda: self.send_strength_command(2, 1, 10))
        self.clear_a_btn.clicked.connect(lambda: self.clear_queue('A'))
        self.clear_b_btn.clicked.connect(lambda: self.clear_queue('B'))
        self.save_server_btn.clicked.connect(self.update_server_address)
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        
    @asyncSlot()
    async def show_scanner(self):
        try:
            # 检查蓝牙是否可用
            if not await check_bluetooth_available():
                QMessageBox.critical(self, 
                    translate("dialog.error"),
                    translate("dialog.bluetooth_not_available"),
                    QMessageBox.Ok)
                return
                
            scanner = DeviceScanner(self)
            scanner.setStyleSheet(self.styleSheet())  # 应用相同的主题
            scanner.device_list.itemDoubleClicked.connect(lambda: self.select_device(scanner))
            
            # 先显示窗口
            scanner.show()
            
            # 直接调用扫描方法，而不是创建新的任务
            await scanner.start_scan()
            
            # 等待窗口关闭
            scanner.exec()
            
        except Exception as e:
            logging.error(f"显示扫描窗口时发生错误: {str(e)}")
            QMessageBox.critical(self,
                translate("dialog.error"),
                translate("dialog.scan_window_error", str(e)),
                QMessageBox.Ok)

    def select_device(self, scanner):
        selected = scanner.device_list.currentItem().text()
        address = selected.split("|")[-1].strip()
        self.signals.device_selected.emit(address)
        scanner.close()
        
    def update_server_address(self):
        global SOCKET_URI
        new_uri = self.server_input.text().strip()
        
        # 验证URL格式
        if not is_valid_websocket_url(new_uri):
            QMessageBox.warning(self,
                translate("dialog.error"),
                translate("dialog.invalid_url"),
                QMessageBox.Ok)
            return
        
        SOCKET_URI = new_uri
        if self.save_config():
            self.signals.log_message.emit(translate("status_updates.server_updated", SOCKET_URI))
        else:
            self.signals.log_message.emit(translate("status_updates.server_update_failed", SOCKET_URI))
            QMessageBox.warning(self,
                translate("dialog.error"),
                translate("dialog.save_config_failed"),
                QMessageBox.Ok)
        
    def update_device_address(self, address):
        global BLE_DEVICE_ADDRESS
        BLE_DEVICE_ADDRESS = address
        self.selected_device = address
        self.device_label.setText(translate("device.status", address))
        self.connect_btn.setEnabled(True)
        self.signals.log_message.emit(translate("status_updates.device_selected", address))
        
    def update_device_id(self, device_id):
        global DEVICE_ID
        DEVICE_ID = device_id
        self.signals.log_message.emit(translate("status_updates.get_device_id_success", device_id))
        
    @asyncSlot()
    async def on_connect_clicked(self):
        if not self.selected_device:
            self.signals.log_message.emit(translate("status_updates.please_select_device"))
            return
            
        try:
            self.ble_client = BleakClient(BLE_DEVICE_ADDRESS)
            await self.ble_client.connect()
            self.signals.log_message.emit(translate("status_updates.bluetooth_connected"))
            await self.get_device_id()
            asyncio.create_task(self.process_wave_queues())
            asyncio.create_task(self.monitor_connection())
            self.signals.connection_changed.emit(True)
            self.connect_server_btn.setEnabled(True)  # 启用服务器连接按钮
        except Exception as e:
            self.signals.log_message.emit(translate("status_updates.connection_failed", str(e)))
            self.signals.connection_changed.emit(False)
            self.connect_server_btn.setEnabled(False)

    @asyncSlot()
    async def on_connect_server_clicked(self):
        if not self.ble_client or not self.ble_client.is_connected:
            self.signals.log_message.emit("请先确保蓝牙设备已连接")
            return
            
        if not SOCKET_URI:
            self.signals.log_message.emit(translate("status_updates.server_address_empty"))
            return
            
        try:
            asyncio.create_task(self.listen_websocket())
            self.connect_server_btn.setEnabled(False)
            self.signals.log_message.emit("正在连接服务器...")
        except Exception as e:
            self.signals.log_message.emit(f"连接服务器失败: {str(e)}")
            self.connect_server_btn.setEnabled(True)

    async def read_battery(self):
        try:
            value = await self.ble_client.read_gatt_char(BLE_CHAR_BATTERY)
            battery_level = int.from_bytes(value, byteorder='little')
            self.battery_label.setText(translate("status.battery", battery_level))
        except Exception as e:
            self.signals.log_message.emit(translate("status_updates.battery_read_failed", str(e)))
            
    async def monitor_connection(self):
        while self.ble_client and self.ble_client.is_connected:
            rssi = self.ble_client.rssi if hasattr(self.ble_client, 'rssi') else None
            if rssi:
                self.rssi_label.setText(translate("status.signal_strength", rssi))
            else:
                self.rssi_label.setText(translate("status.signal_unknown"))
            await asyncio.sleep(5)  # 每5秒更新一次
            await self.read_battery()

    async def get_device_id(self):
        try:
            value = await self.ble_client.read_gatt_char(BLE_CHAR_DEVICE_ID)
            device_id = value.hex().upper()
            global DEVICE_ID
            DEVICE_ID = device_id
            self.signals.device_id_updated.emit(device_id)
            self.signals.log_message.emit(translate("status_updates.get_device_id_success", device_id))
        except Exception as e:
            self.signals.log_message.emit(translate("status_updates.get_device_id_failed", str(e)))

    def update_ui_state(self, connected):
        self.connect_btn.setEnabled(not connected)
        self.scan_btn.setEnabled(not connected)
        self.connect_server_btn.setEnabled(connected)  # 只有在蓝牙连接成功时才启用
        status = translate("device.connected" if connected else "device.disconnected")
        self.device_label.setText(translate("device.status", status))
        # 更新实时状态
        self.update_status('A', self.current_strength['A'])
        self.update_status('B', self.current_strength['B'])
        if hasattr(self, 'battery_label'):
            self.battery_label.setText(translate("status.battery", "--"))
        if hasattr(self, 'rssi_label'):
            self.rssi_label.setText(translate("status.signal_unknown"))

    def update_status(self, channel, value):
        try:
            if channel == 'A':
                text = translate("status.channel_a", int(value), self.max_strength[channel])
                self.a_status.setText(text)
            else:
                text = translate("status.channel_b", int(value), self.max_strength[channel])
                self.b_status.setText(text)
        except ValueError:
            self.signals.log_message.emit(translate("status_updates.invalid_status_value"))

    def clear_queue(self, channel):
        self.wave_queues[channel].clear()
        self.signals.log_message.emit(translate("status_updates.queue_cleared", channel))
        
    async def send_ble_command(self, char_uuid, data):
        if self.ble_client and self.ble_client.is_connected:
            try:
                await self.ble_client.write_gatt_char(char_uuid, data)
                self.signals.log_message.emit(translate("status_updates.command_send_success", char_uuid[-4:]))
            except Exception as e:
                self.signals.log_message.emit(translate("status_updates.command_send_failed", str(e)))

    def v3_freq_to_v2(self, freq_input):
        if 10 <= freq_input <= 100:
            x = max(1, int(freq_input**0.5 * 0.8))
            y = 1000 // freq_input - x
        elif 101 <= freq_input <= 600:
            scaled = (freq_input - 100)/5 + 100
            x = int(scaled**0.5 * 1.2)
            y = max(1, (1000//freq_input)-x)
        elif 601 <= freq_input <= 1000:
            x = int((freq_input**0.5)*0.5)
            y = max(1, (1000//freq_input)-x)
        else: x,y = 1,9
        return max(1,min(31,x)), max(1,min(1023,y))

    def v3_intensity_to_v2_z(self, intensity):
        return min(31, int(20 + (15 * (intensity/100))))

    def encode_pwm_ab2(self, a, b):
        a_val = min(int(a*2047/200),2047)
        b_val = min(int(b*2047/200),2047)
        return bytes([(a_val>>3)&0xFF, ((a_val&0x07)<<5)|((b_val>>6)&0x1F), (b_val&0x3F)<<2])

    def encode_pwm_channel(self, x, y, z):
        return struct.pack('<I', (z&0x1F)<<19 | (y&0x3FF)<<5 | (x&0x1F))[:3]

    async def process_wave_queues(self):
        while True:
            for ch in ['A','B']:
                if len(self.wave_queues[ch]) >=4:
                    params = [self.wave_queues[ch].popleft() for _ in range(4)]
                    avg_x = sum(p[0] for p in params)//4
                    avg_y = sum(p[1] for p in params)//4
                    avg_z = sum(p[2] for p in params)//4
                    data = self.encode_pwm_channel(avg_x, avg_y, avg_z)
                    char = BLE_CHAR_PWM_A34 if ch == 'A' else BLE_CHAR_PWM_B34
                    await self.send_ble_command(char, data)
            await asyncio.sleep(0.025)

    async def send_websocket_message(self, message):
        """发送消息到WebSocket服务器"""
        try:
            if not self.ws_client:
                self.signals.log_message.emit("WebSocket未连接")
                return
            
            await self.ws_client.send(json.dumps(message))
            self.signals.log_message.emit("消息已发送到服务器")
        except Exception as e:
            self.signals.log_message.emit(f"发送消息到服务器失败: {str(e)}")
            self.ws_client = None  # 连接可能已断开，重置连接

    async def listen_websocket(self):
        try:
            if not SOCKET_URI:
                self.signals.log_message.emit(translate("status_updates.server_address_empty"))
                return
            
            async with websockets.connect(SOCKET_URI) as ws:
                self.ws_client = ws  # 保存WebSocket连接
                await ws.send(json.dumps({
                    "type": "bind",
                    "clientId": DEVICE_ID,
                    "targetId": "",
                    "message": "DGLAB"
                }))
                while True:
                    try:
                        message = await ws.recv()
                        self.signals.log_message.emit(translate("status_updates.received_command", message[:50]))
                        await self.handle_socket_message(message)
                    except websockets.ConnectionClosed:
                        self.signals.log_message.emit("WebSocket连接已关闭")
                        break
                    except Exception as e:
                        self.signals.log_message.emit(f"处理WebSocket消息时出错: {str(e)}")
                        break
        except Exception as e:
            self.signals.log_message.emit(translate("status_updates.network_error", str(e)))
        finally:
            self.ws_client = None  # 清除连接

    async def handle_socket_message(self, message):
        try:
            msg = json.loads(message)
            if msg["type"] != "msg": return
            
            cmd = msg["message"]
            if cmd.startswith("strength-"):
                parts = cmd[9:].split('+')
                await self.handle_strength_change(int(parts[0]), int(parts[1]), int(parts[2]))
            elif cmd.startswith("pulse-"):
                ch_part, wave_data = cmd[6:].split(':')
                channel = ch_part.upper()
                hex_waves = json.loads(wave_data)
                for hex_str in hex_waves[:100]:
                    freq = int(hex_str[:2],16)
                    intensity = int(hex_str[2:4],16)
                    x,y = self.v3_freq_to_v2(freq)
                    z = self.v3_intensity_to_v2_z(intensity)
                    self.wave_queues[channel].append((x,y,z))
                    # 更新波形显示
                    self.wave_queues[channel].append(intensity)
            elif cmd.startswith("clear-"):
                channel = 'A' if cmd[6:] == '1' else 'B'
                self.wave_queues[channel].clear()
                self.signals.log_message.emit(translate("status_updates.queue_cleared", channel))
                
        except Exception as e:
            self.signals.log_message.emit(translate("status_updates.message_process_error", str(e)))

    def update_max_strength(self):
        try:
            # 获取输入值
            a_value = int(self.a_max_input.text())
            b_value = int(self.b_max_input.text())
            
            # 验证范围
            if a_value < 0 or a_value > 200 or b_value < 0 or b_value > 200:
                QMessageBox.warning(self,
                    translate("dialog.error"),
                    translate("status_updates.strength_limit_range_error"),
                    QMessageBox.Ok)
                # 恢复原值
                self.a_max_input.setText(str(self.max_strength['A']))
                self.b_max_input.setText(str(self.max_strength['B']))
                return
            
            # 更新值
            self.max_strength['A'] = a_value
            self.max_strength['B'] = b_value
            
            # 更新波形显示的Y轴范围
            self.check_plot_range()
            
            if self.save_config():
                self.signals.log_message.emit(translate("status_updates.strength_limit_updated", 
                    self.max_strength['A'], self.max_strength['B']))
            else:
                self.signals.log_message.emit(translate("status_updates.strength_limit_update_failed", 
                    self.max_strength['A'], self.max_strength['B']))
                
            self.update_status('A', self.current_strength['A'])
            self.update_status('B', self.current_strength['B'])
        except ValueError:
            QMessageBox.warning(self,
                translate("dialog.error"),
                translate("status_updates.invalid_number"),
                QMessageBox.Ok)
            # 恢复原值
            self.a_max_input.setText(str(self.max_strength['A']))
            self.b_max_input.setText(str(self.max_strength['B']))

    def send_strength_command(self, channel, mode, value):
        asyncio.create_task(self.handle_strength_change(channel, mode, value))

    async def handle_strength_change(self, channel_num, mode, value):
        ch = 'A' if channel_num == 1 else 'B'
        try:
            current = self.current_strength[ch]
            if mode == 0: new = current - value
            elif mode == 1: new = current + value
            elif mode == 2: new = value
            else: return
            
            if new > self.max_strength[ch]:
                self.signals.log_message.emit(translate("status_updates.channel_over_limit", ch, self.max_strength[ch]))
                return
                
            new = max(0, min(new, self.max_strength[ch]))
            old_value = self.current_strength[ch]  # 保存旧值
            self.current_strength[ch] = new
            data = self.encode_pwm_ab2(self.current_strength['A'], self.current_strength['B'])
            await self.send_ble_command(BLE_CHAR_PWM_AB2, data)
            self.signals.status_update.emit(ch, str(new))
            
            # 更新波形显示
            self.wave_queues[ch].append(new)
            
            # 只有当值真正改变时才发送到服务器
            if new != old_value:
                message = {
                    "type": "msg",
                    "clientId": DEVICE_ID,
                    "targetId": "",
                    "message": f"strength-{channel_num}+2+{new}"  # 使用mode 2表示直接设置强度值
                }
                await self.send_websocket_message(message)
            
        except Exception as e:
            self.signals.log_message.emit(translate("status_updates.strength_adjust_failed", str(e)))

    def on_language_changed(self, index):
        """语言选择改变时的处理函数"""
        logging.debug(f"语言选择改变: index={index}")
        try:
            lang_code = self.lang_combo.itemData(index)
            logging.debug(f"选择的语言代码: {lang_code}")
            if lang_code:
                self.change_language(lang_code)
        except Exception as e:
            logging.error(f"处理语言改变事件时发生错误: {str(e)}")

if __name__ == "__main__":
    # 设置日志格式
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logging.info("程序启动")
    
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # 检查并创建语言包目录
    if not os.path.exists(LANG_PATH):
        try:
            os.makedirs(LANG_PATH)
            logging.info(f"成功创建语言包目录: {LANG_PATH}")
        except Exception as e:
            logging.error(f"创建语言包目录失败: {str(e)}")
    else:
        logging.info(f"语言包目录已存在: {LANG_PATH}")
    
    window = MainWindow()
    window.show()
    
    with loop:
        loop.run_forever()
