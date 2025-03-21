from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, QTimer
from qasync import asyncSlot
import logging
import sys
import os

from utils.signals import DeviceSignals
from utils.i18n import i18n
from core.ble_manager import BLEManager
from core.socket_manager import SocketManager
from core.protocol import ProtocolConverter
from config.settings import settings

from .components import (
    create_language_group, create_device_group, 
    create_server_group, create_strength_group, create_wave_group
)
from .device_manager_ui import DeviceManagerUI
from .server_manager_ui import ServerManagerUI
from .strength_manager_ui import StrengthManagerUI
from .wave_manager_ui import WaveManagerUI
from .log_window import LogWindow
from .personalization import PersonalizationDialog
from .styles import get_style

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 添加项目根目录到PATH

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_attributes()
        self.init_ui()
        self.setup_managers()  # 先初始化管理器
        self.setup_connections()  # 然后设置连接
        self.apply_theme()
        
        # 不在初始化中直接调用异步方法
        # 使用QTimer在初始化完成后调用
        QTimer.singleShot(0, self.device_manager.initialize_bluetooth_check)
        
    def init_attributes(self):
        """初始化属性"""
        # 创建信号对象
        self.signals = DeviceSignals()
        
        # 创建管理器实例
        self.ble_manager = BLEManager(self.signals)
        
        # 确保BLE管理器使用正确的最大强度值
        self.ble_manager.max_strength = {
            'A': settings.max_strength_a,
            'B': settings.max_strength_b
        }
        logging.info(f"BLEManager初始化，最大强度: A={self.ble_manager.max_strength['A']}, B={self.ble_manager.max_strength['B']}")
        
        self.socket_manager = SocketManager(self.signals, self.ble_manager)
        
        # 创建日志窗口
        self.log_window = None
        
        # 从设置中获取主题相关属性
        self.accent_color = settings.accent_color
        self.background_image = settings.background_image
        
        # 设置窗口标题和大小
        self.setWindowTitle(i18n.translate("app_title"))
        self.setMinimumSize(800, 600)
        
        # 应用样式
        self.apply_theme()

        self.battery_update_timer = QTimer()  # 添加电池更新定时器
        self.signal_update_timer = QTimer()   # 添加信号强度更新定时器
        self.accent_color = settings.accent_color
        self.background_image = settings.background_image
        self.old_title = i18n.translate("main_title")  # 保存当前标题文本
    
    def setup_managers(self):
        """初始化管理器"""
        # 不要重新创建BLEManager和SocketManager实例，使用init_attributes中已创建的实例
        # self.ble_manager = BLEManager(self.signals)
        # self.socket_manager = SocketManager(self.signals, self.ble_manager)
        
        # 初始化UI管理器
        self.device_manager = DeviceManagerUI(self)
        self.server_manager = ServerManagerUI(self)
        self.strength_manager = StrengthManagerUI(self)
        self.wave_manager = WaveManagerUI(self)
        
        # 记录日志，确认使用的最大强度值
        logging.info(f"UI管理器初始化完成，BLEManager最大强度: A={self.ble_manager.max_strength['A']}, B={self.ble_manager.max_strength['B']}")
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(i18n.translate("main_title"))
        self.setGeometry(100, 100, 1440, 600)  # 主窗口默认尺寸
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建顶部标题栏
        self.title_layout = QHBoxLayout()
        title_label = QLabel(i18n.translate("main_title"))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 15px;")  # 使用旧版字体样式
        self.title_layout.addWidget(title_label)
        self.title_layout.addStretch()
        
        # 顶部工具栏按钮
        self.log_btn = QPushButton(i18n.translate("log.show"))
        self.theme_btn = QPushButton(i18n.translate("personalization.button"))
        self.log_btn.setFixedWidth(150)
        self.theme_btn.setFixedWidth(150)
        self.title_layout.addWidget(self.log_btn)
        self.title_layout.addWidget(self.theme_btn)
        
        main_layout.addLayout(self.title_layout)
        
        # 创建语言设置组件
        self.lang_group, self.lang_combo = create_language_group()
        
        # 创建设备管理组件
        self.device_group, self.device_label, self.scan_btn, self.connect_btn, self.device_status = create_device_group()
        
        # 创建服务器配置组件
        self.server_group, self.server_input, self.server_save_btn, self.server_connect_btn = create_server_group()
        
        # 创建强度配置组件
        self.strength_group, self.a_limit_input, self.b_limit_input, self.save_strength_btn = create_strength_group()
        
        # 创建波形显示组件
        self.wave_group, self.a_status, self.b_status, self.battery_status, self.signal_status, self.plot_widget_a, self.plot_widget_b = create_wave_group()
        
        # 创建手动控制组件
        self.control_group = QGroupBox(i18n.translate("control.manual"))
        control_layout = QHBoxLayout()
        
        # 测试按钮
        self.test_a_btn = QPushButton(i18n.translate("control.test_a"))
        self.test_b_btn = QPushButton(i18n.translate("control.test_b"))
        self.clear_a_btn = QPushButton(i18n.translate("control.clear_a"))
        self.clear_b_btn = QPushButton(i18n.translate("control.clear_b"))
        
        control_layout.addWidget(self.test_a_btn)
        control_layout.addWidget(self.test_b_btn)
        control_layout.addWidget(self.clear_a_btn)
        control_layout.addWidget(self.clear_b_btn)
        
        self.control_group.setLayout(control_layout)
        
        # 添加所有组件到主布局
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.lang_group)
        left_layout.addWidget(self.device_group)
        left_layout.addWidget(self.server_group)
        left_layout.addWidget(self.strength_group)
        left_layout.addStretch()
        
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.wave_group)
        right_layout.addWidget(self.control_group)
        right_layout.addStretch()
        
        # 创建水平布局，左右分栏
        content_layout = QHBoxLayout()
        content_layout.addLayout(left_layout, 1)  # 左侧占比1
        content_layout.addLayout(right_layout, 2)  # 右侧占比2
        
        main_layout.addLayout(content_layout)
        
    def setup_connections(self):
        """设置信号连接"""
        # 日志按钮
        self.log_btn.clicked.connect(self.toggle_log_window)
        # 主题按钮
        self.theme_btn.clicked.connect(self.show_personalization)
        
        # 语言选择
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        
        # 手动控制按钮
        self.test_a_btn.clicked.connect(self.test_channel_a)
        self.test_b_btn.clicked.connect(self.test_channel_b)
        self.clear_a_btn.clicked.connect(lambda: self.clear_channel('A'))
        self.clear_b_btn.clicked.connect(lambda: self.clear_channel('B'))
        
        # 电池和信号强度更新定时器
        self.battery_update_timer.timeout.connect(self.device_manager.update_battery)
        self.signal_update_timer.timeout.connect(self.device_manager.update_signal_strength)
        
        # 加载可用语言
        self.load_languages()
        
        # 加载服务器地址
        self.server_input.setText(settings.socket_uri)
        
    def load_languages(self):
        """加载可用语言"""
        self.lang_combo.clear()
        languages = i18n.load_languages()
        
        current_index = 0  # 默认选择第一项
        
        for idx, (code, name) in enumerate(languages.items()):
            self.lang_combo.addItem(name, code)
            
            # 设置当前语言
            if code == i18n.current_lang:  # 使用i18n中的current_lang
                current_index = idx
                logging.info(f"Found current language in combo: {code} at index {idx}")
        
        # 设置当前选中的语言，但不触发change_language事件
        if self.lang_combo.count() > 0:
            self.lang_combo.setCurrentIndex(current_index)
            logging.info(f"Set language combo to index {current_index} for language {i18n.current_lang}")
    
    def change_language(self, index):
        """切换语言"""
        if index < 0:
            return
            
        lang_code = self.lang_combo.itemData(index)
        logging.info(f"Language selection changed to: {lang_code}")
        
        if lang_code and lang_code != i18n.current_lang:
            # 加载新语言
            if i18n.load_language(lang_code):
                # 更新UI文本
                self.update_ui_texts()
                
                # 通知用户语言已更改
                self.signals.log_message.emit(i18n.translate("status_updates.language_changed"))
                logging.info(f"UI已更新为语言: {lang_code}")
            
            # 删除以下重复代码
            # settings.current_lang = lang_code
            # settings.save()
            # logging.info(f"Language settings saved: {lang_code}")
            # 
            # # 更新UI文本
            # self.update_ui_texts()
            # 
            # # 通知用户语言已更改
            # self.signals.log_message.emit(i18n.translate("status_updates.language_changed"))
    
    def update_ui_texts(self):
        """更新UI上的所有文本"""
        # 更新窗口标题
        self.setWindowTitle(i18n.translate("main_title"))
        
        # 更新顶部标题
        for i in range(self.title_layout.count()):
            widget = self.title_layout.itemAt(i).widget()
            if isinstance(widget, QLabel) and widget.text() == self.old_title:
                widget.setText(i18n.translate("main_title"))
                self.old_title = i18n.translate("main_title")
                break
        
        # 更新按钮文本
        self.log_btn.setText(i18n.translate("log.show") if not self.log_window or not self.log_window.isVisible() else i18n.translate("log.hide"))
        self.theme_btn.setText(i18n.translate("personalization.button"))
        
        # 更新组件标题和内容
        self.lang_group.setTitle(i18n.translate("language.setting"))
        self.device_group.setTitle(i18n.translate("device.management"))
        self.device_status.setText(i18n.translate("device.status", 
            i18n.translate("device.connected") if self.ble_manager.is_connected else i18n.translate("device.disconnected")))
        self.scan_btn.setText(i18n.translate("device.scan"))
        self.connect_btn.setText(i18n.translate("device.connect"))
        
        # 更新设备标签
        if hasattr(self, 'device_label'):
            self.device_label.setText(i18n.translate("label.no_device"))
        
        # 更新服务器组件
        self.server_group.setTitle(i18n.translate("server.config"))
        # 查找服务器地址标签并更新
        for i in range(self.server_group.layout().count()):
            item = self.server_group.layout().itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QLabel):
                if "服务器地址" in item.widget().text() or "Server Address" in item.widget().text():
                    item.widget().setText(i18n.translate("server.address"))
                    break
        
        self.server_save_btn.setText(i18n.translate("server.save"))
        self.server_connect_btn.setText(i18n.translate("server.connect"))
        
        # 更新强度组件
        self.strength_group.setTitle(i18n.translate("strength.config"))
        # 查找强度标签并更新
        for i in range(self.strength_group.layout().count()):
            item = self.strength_group.layout().itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QLabel):
                if "A通道" in item.widget().text() or "Channel A" in item.widget().text():
                    item.widget().setText(i18n.translate("strength.channel_a_limit"))
                elif "B通道" in item.widget().text() or "Channel B" in item.widget().text():
                    item.widget().setText(i18n.translate("strength.channel_b_limit"))
        
        self.save_strength_btn.setText(i18n.translate("strength.save"))
        
        # 更新波形组件
        self.wave_group.setTitle(i18n.translate("status.realtime"))
        self.a_status.setText(i18n.translate("status.channel_a", "0", "0"))
        self.b_status.setText(i18n.translate("status.channel_b", "0", "0"))
        self.battery_status.setText(i18n.translate("status.battery", "--"))
        self.signal_status.setText(i18n.translate("status.signal_unknown"))
        
        # 更新控制组件
        self.control_group.setTitle(i18n.translate("control.manual"))
        self.test_a_btn.setText(i18n.translate("control.test_a"))
        self.test_b_btn.setText(i18n.translate("control.test_b"))
        self.clear_a_btn.setText(i18n.translate("control.clear_a"))
        self.clear_b_btn.setText(i18n.translate("control.clear_b"))
        
        # 更新波形图标题和标签
        self.plot_widget_a.setTitle(i18n.translate("status.wave_title_a"))
        self.plot_widget_a.setLabel('left', i18n.translate("status.wave_y_label"))
        self.plot_widget_a.setLabel('bottom', i18n.translate("status.wave_x_label"))
        
        self.plot_widget_b.setTitle(i18n.translate("status.wave_title_b"))
        self.plot_widget_b.setLabel('left', i18n.translate("status.wave_y_label"))
        self.plot_widget_b.setLabel('bottom', i18n.translate("status.wave_x_label"))
    
    def toggle_log_window(self):
        """切换日志窗口显示状态"""
        if not self.log_window:
            self.log_window = LogWindow(self)
            self.log_window.window_closed.connect(self.on_log_window_closed)
            self.log_window.apply_theme()
            
        if self.log_window.isVisible():
            self.log_window.hide()
            self.log_btn.setText(i18n.translate("log.show"))
        else:
            self.log_window.show()
            self.log_btn.setText(i18n.translate("log.hide"))
            
    def on_log_window_closed(self):
        """日志窗口关闭事件处理"""
        self.log_btn.setText(i18n.translate("log.show"))
        
    def show_personalization(self):
        """显示个性化设置对话框"""
        dialog = PersonalizationDialog(self, self.accent_color, self.background_image)
        if dialog.exec():
            # 获取新的设置
            self.accent_color = dialog.accent_color
            self.background_image = dialog.background_image
            
            # 更新设置
            settings.accent_color = self.accent_color
            settings.background_image = self.background_image
            settings.save()
            
            # 应用新主题
            self.apply_theme()
            
            # 如果日志窗口存在，也应用新主题
            if self.log_window:
                self.log_window.apply_theme(self.accent_color, self.background_image)
                
    def apply_theme(self):
        """应用主题样式"""
        style_sheet = get_style(self.accent_color, self.background_image)
        self.setStyleSheet(style_sheet)
        
    @asyncSlot()
    async def test_channel_a(self):
        """测试A通道"""
        if not self.ble_manager.is_connected:
            self.signals.log_message.emit(i18n.translate("status_updates.no_device_connected"))
            return
            
        try:
            # 发送测试波形到A通道
            await self.ble_manager.send_test_wave('A')
            self.signals.log_message.emit(i18n.translate("status_updates.test_wave_sent", 'A'))
        except Exception as e:
            self.signals.log_message.emit(i18n.translate("status_updates.test_wave_failed", 'A', str(e)))
            
    @asyncSlot()
    async def test_channel_b(self):
        """测试B通道"""
        if not self.ble_manager.is_connected:
            self.signals.log_message.emit(i18n.translate("status_updates.no_device_connected"))
            return
            
        try:
            # 发送测试波形到B通道
            await self.ble_manager.send_test_wave('B')
            self.signals.log_message.emit(i18n.translate("status_updates.test_wave_sent", 'B'))
        except Exception as e:
            self.signals.log_message.emit(i18n.translate("status_updates.test_wave_failed", 'B', str(e)))
            
    def clear_channel(self, channel):
        """清除通道数据"""
        if channel not in ['A', 'B']:
            return
            
        # 清除波形数据
        self.wave_manager.clear_channel_data(channel)
        
        # 如果设备已连接，发送清除命令
        if self.ble_manager.is_connected:
            asyncio.create_task(self.ble_manager.clear_channel(channel))