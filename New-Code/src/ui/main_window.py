from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QGroupBox,
    QMessageBox, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator  # 添加QIntValidator导入
import pyqtgraph as pg
from collections import deque
from qasync import asyncSlot
import logging  # 添加日志模块导入

from utils.signals import DeviceSignals
from utils.i18n import i18n
from core.ble_manager import BLEManager
from core.socket_manager import SocketManager
from core.protocol import ProtocolConverter
from config.settings import settings
from .device_scanner import DeviceScanner
from .log_window import LogWindow
from .personalization import PersonalizationDialog
from .styles import get_style
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 添加项目根目录到PATH

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_attributes()
        self.init_ui()
        self.setup_connections()
        self.setup_managers()
        self.apply_theme()
        
    def init_attributes(self):
        """初始化属性"""
        self.signals = DeviceSignals()
        self.wave_queues = {'A': deque(maxlen=100), 'B': deque(maxlen=100)}
        self.current_strength = {'A': 0, 'B': 0}
        self.max_strength = settings.max_strength
        self.log_window = None
        
    def setup_managers(self):
        """初始化管理器"""
        self.ble_manager = BLEManager(self.signals)
        self.socket_manager = SocketManager(self.signals, self.ble_manager)
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(i18n.translate("main_title"))
        self.setGeometry(100, 100, 1024, 768)  # 旧版默认尺寸
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 添加标题标签 - 修正位置为左上角
        title_layout = QHBoxLayout()
        title_label = QLabel(i18n.translate("main_title"))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()  # 添加弹性空间，使标题靠左
        
        # 顶部工具栏布局 - 放在同一行
        self.log_btn = QPushButton(i18n.translate("log.show"))
        self.theme_btn = QPushButton(i18n.translate("personalization.button"))
        # 设置按钮固定宽度，使其大小一致
        self.log_btn.setFixedWidth(120)
        self.theme_btn.setFixedWidth(120)
        title_layout.addWidget(self.log_btn)
        title_layout.addWidget(self.theme_btn)
        
        main_layout.addLayout(title_layout)
        
        # 语言设置
        self.lang_group = QGroupBox(str(i18n.translate("language.setting")))
        lang_layout = QVBoxLayout()
        self.lang_combo = QComboBox()
        self.update_language_list()
        lang_layout.addWidget(self.lang_combo)
        self.lang_group.setLayout(lang_layout)
        main_layout.addWidget(self.lang_group)
        
        # 设备管理 (修正布局顺序)
        self.device_group = QGroupBox(str(i18n.translate("device.management")))
        device_layout = QVBoxLayout()
        
        # 添加设备标签 (旧版关键元素)
        self.device_label = QLabel(str(i18n.translate("label.no_device")))
        device_layout.addWidget(self.device_label)
        
        device_buttons = QHBoxLayout()
        self.scan_btn = QPushButton(str(i18n.translate("device.scan")))
        self.connect_btn = QPushButton(str(i18n.translate("device.connect")))
        device_buttons.addWidget(self.scan_btn)
        device_buttons.addWidget(self.connect_btn)
        device_layout.addLayout(device_buttons)
        
        # 设备状态标签 (保持旧版样式)
        self.device_status = QLabel(str(i18n.translate("device.status", str(i18n.translate("device.disconnected")))))
        device_layout.addWidget(self.device_status)
        
        self.device_group.setLayout(device_layout)
        main_layout.addWidget(self.device_group)
        
        # 服务器配置
        self.server_group = QGroupBox(i18n.translate("server.config"))
        server_layout = QVBoxLayout()
        server_input_layout = QHBoxLayout()
        self.address_label = QLabel(i18n.translate("server.address"))
        server_input_layout.addWidget(self.address_label)
        self.server_input = QLineEdit(settings.socket_uri)
        server_input_layout.addWidget(self.server_input)
        server_buttons = QHBoxLayout()
        self.server_save_btn = QPushButton(i18n.translate("server.save"))
        self.server_connect_btn = QPushButton(i18n.translate("server.connect"))
        server_buttons.addWidget(self.server_save_btn)
        server_buttons.addWidget(self.server_connect_btn)
        server_layout.addLayout(server_input_layout)
        server_layout.addLayout(server_buttons)
        self.server_group.setLayout(server_layout)
        main_layout.addWidget(self.server_group)
        
        # 添加强度配置组（与旧版一致）
        self.strength_group = QGroupBox(i18n.translate("strength.config"))
        strength_layout = QVBoxLayout()
        
        # 通道A强度限制
        a_limit_layout = QHBoxLayout()
        a_limit_layout.addWidget(QLabel(i18n.translate("strength.channel_a_limit")))
        self.a_limit_input = QLineEdit(str(self.max_strength['A']))
        self.a_limit_input.setValidator(QIntValidator(0, 200))
        a_limit_layout.addWidget(self.a_limit_input)
        strength_layout.addLayout(a_limit_layout)
        
        # 通道B强度限制
        b_limit_layout = QHBoxLayout()
        b_limit_layout.addWidget(QLabel(i18n.translate("strength.channel_b_limit")))
        self.b_limit_input = QLineEdit(str(self.max_strength['B']))
        self.b_limit_input.setValidator(QIntValidator(0, 200))
        b_limit_layout.addWidget(self.b_limit_input)
        strength_layout.addLayout(b_limit_layout)
        
        # 保存强度设置按钮
        self.save_strength_btn = QPushButton(i18n.translate("strength.save"))
        strength_layout.addWidget(self.save_strength_btn)
        
        self.strength_group.setLayout(strength_layout)
        main_layout.addWidget(self.strength_group)
        
        # 实时状态
        self.wave_group = QGroupBox(i18n.translate("status.realtime"))
        wave_layout = QVBoxLayout()
        
        # 状态标签
        status_layout = QHBoxLayout()
        self.a_status = QLabel(i18n.translate("status.channel_a", 0, self.max_strength['A']))
        self.b_status = QLabel(i18n.translate("status.channel_b", 0, self.max_strength['B']))
        # 修改初始化时的电池显示，避免显示0%
        self.battery_status = QLabel(i18n.translate("status.signal_unknown").replace("信号强度", "电池"))
        self.signal_status = QLabel(i18n.translate("status.signal_unknown"))
        status_layout.addWidget(self.a_status)
        status_layout.addWidget(self.b_status)
        status_layout.addWidget(self.battery_status)
        status_layout.addWidget(self.signal_status)
        wave_layout.addLayout(status_layout)
        
        # 创建双波形水平布局
        plots_layout = QHBoxLayout()
        
        # 通道A波形
        self.plot_widget_a = pg.PlotWidget(title=i18n.translate("status.wave_title_a"))
        self.plot_widget_a.setBackground('transparent')  # 修改为transparent
        self.plot_widget_a.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget_a.setLabel('left', i18n.translate("status.wave_y_label"))
        self.plot_widget_a.setLabel('bottom', i18n.translate("status.wave_x_label"))
        # 设置Y轴范围为0到当前最大强度
        self.plot_widget_a.setYRange(0, self.max_strength['A'])
        # 禁用鼠标交互功能，使波形图表变为只读模式
        self.plot_widget_a.setMouseEnabled(x=False, y=False)
        self.plot_widget_a.setMenuEnabled(False)
        self.plot_widget_a.getViewBox().setMouseMode(pg.ViewBox.PanMode)
        self.plot_widget_a.getViewBox().setMouseEnabled(x=False, y=False)
        self.curve_a = self.plot_widget_a.plot(pen=pg.mkPen(color='g', width=2))
        
        # 通道B波形
        self.plot_widget_b = pg.PlotWidget(title=i18n.translate("status.wave_title_b"))
        self.plot_widget_b.setBackground('transparent')  # 修改为transparent
        self.plot_widget_b.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget_b.setLabel('left', i18n.translate("status.wave_y_label"))
        self.plot_widget_b.setLabel('bottom', i18n.translate("status.wave_x_label"))
        # 设置Y轴范围为0到当前最大强度
        self.plot_widget_b.setYRange(0, self.max_strength['B'])
        # 禁用鼠标交互功能，使波形图表变为只读模式
        self.plot_widget_b.setMouseEnabled(x=False, y=False)
        self.plot_widget_b.setMenuEnabled(False)
        self.plot_widget_b.getViewBox().setMouseMode(pg.ViewBox.PanMode)
        self.plot_widget_b.getViewBox().setMouseEnabled(x=False, y=False)
        self.curve_b = self.plot_widget_b.plot(pen=pg.mkPen(color='r', width=2))
        
        plots_layout.addWidget(self.plot_widget_a)
        plots_layout.addWidget(self.plot_widget_b)
        
        # 将波形布局添加到组布局
        wave_layout.addLayout(plots_layout)
        
        # 手动控制
        control_layout = QHBoxLayout()
        self.test_a_btn = QPushButton(i18n.translate("control.test_a"))
        self.test_b_btn = QPushButton(i18n.translate("control.test_b"))
        self.clear_a_btn = QPushButton(i18n.translate("control.clear_a"))
        self.clear_b_btn = QPushButton(i18n.translate("control.clear_b"))
        control_layout.addWidget(self.test_a_btn)
        control_layout.addWidget(self.test_b_btn)
        control_layout.addWidget(self.clear_a_btn)
        control_layout.addWidget(self.clear_b_btn)
        wave_layout.addLayout(control_layout)
        
        self.wave_group.setLayout(wave_layout)
        main_layout.addWidget(self.wave_group)
    
        # 删除重复的波形图表代码
    
        # 设置波形更新定时器
        self.update_timer = pg.QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_plot)
        self.update_timer.start(50)

    # 将这些方法移到类级别
    def update_language_list(self):
        """更新语言选择列表"""
        self.lang_combo.clear()
        languages = i18n.load_languages()
        for code, name in languages.items():
            self.lang_combo.addItem(name, code)
        
        # 设置当前语言
        current_index = self.lang_combo.findData(settings.current_lang)
        if current_index >= 0:
            self.lang_combo.setCurrentIndex(current_index)
            
    def on_language_changed(self, text):
        """处理语言切换"""
        index = self.lang_combo.currentIndex()
        lang_code = self.lang_combo.itemData(index)
        if lang_code != settings.current_lang:
            if i18n.load_language(lang_code):
                settings.current_lang = lang_code
                settings.save()
                self.update_ui_texts()
                
    def update_ui_texts(self):
        """更新UI文本"""
        # 更新窗口标题
        self.setWindowTitle(str(i18n.translate("main_title")))
        
        # 更新分组标题
        self.lang_group.setTitle(str(i18n.translate("language.setting")))
        self.device_group.setTitle(str(i18n.translate("device.management")))
        self.server_group.setTitle(str(i18n.translate("server.config")))
        self.strength_group.setTitle(str(i18n.translate("strength.config")))
        self.wave_group.setTitle(str(i18n.translate("status.realtime")))
        
        # 更新按钮文本
        self.scan_btn.setText(str(i18n.translate("device.scan")))
        self.connect_btn.setText(str(i18n.translate("device.connect")))
        self.server_save_btn.setText(str(i18n.translate("server.save")))
        self.server_connect_btn.setText(str(i18n.translate("server.connect")))
        self.save_strength_btn.setText(str(i18n.translate("strength.save")))
        self.address_label.setText(str(i18n.translate("server.address")))
        self.test_a_btn.setText(str(i18n.translate("control.test_a")))
        self.test_b_btn.setText(str(i18n.translate("control.test_b")))
        self.clear_a_btn.setText(str(i18n.translate("control.clear_a")))
        self.clear_b_btn.setText(str(i18n.translate("control.clear_b")))
        
        # 更新日志和主题按钮
        self.log_btn.setText(str(i18n.translate("log.show") if not self.log_window or not self.log_window.isVisible() 
                     else i18n.translate("log.hide")))
        self.theme_btn.setText(str(i18n.translate("personalization.button")))
        
        # 更新设备标签
        self.device_label.setText(str(i18n.translate("label.no_device")))
        
        # 更新状态标签 - 使用更安全的检查方式
        connected = False
        if hasattr(self, 'ble_manager'):
            if hasattr(self.ble_manager, 'is_connected'):
                connected = self.ble_manager.is_connected
            elif hasattr(self.ble_manager, 'device') and self.ble_manager.device:
                connected = True  # 如果设备对象存在，假定已连接
        
        self.device_status.setText(str(i18n.translate("device.status", 
                              str(i18n.translate("device.connected" if connected else "device.disconnected")))))
        
        # 更新通道状态
        self.a_status.setText(str(i18n.translate("status.channel_a", self.current_strength['A'], self.max_strength['A'])))
        self.b_status.setText(str(i18n.translate("status.channel_b", self.current_strength['B'], self.max_strength['B'])))
        
        # 更新波形图标题和标签
        self.plot_widget_a.setTitle(str(i18n.translate("status.wave_title_a")))
        self.plot_widget_a.setLabel('left', str(i18n.translate("status.wave_y_label")))
        self.plot_widget_a.setLabel('bottom', str(i18n.translate("status.wave_x_label")))
        
        self.plot_widget_b.setTitle(str(i18n.translate("status.wave_title_b")))
        self.plot_widget_b.setLabel('left', str(i18n.translate("status.wave_y_label")))
        self.plot_widget_b.setLabel('bottom', str(i18n.translate("status.wave_x_label")))
        
    def log_output(self, message):
        """输出日志消息"""
        # 同时输出到终端和日志窗口
        logging.info(message)
        if self.log_window:
            self.log_window.append_log(message)
            
    def on_connection_changed(self, connected):
        status_text = i18n.translate("device.connected" if connected else "device.disconnected")
        self.device_status.setText(i18n.translate("device.status", status_text))
        self.device_label.setText(i18n.translate("label.no_device"))
        if connected:
            self.scan_btn.setEnabled(False)
            self.signals.log_message.emit(i18n.translate("status.connected"))
        else:
            self.scan_btn.setEnabled(True)
            self.signals.log_message.emit(i18n.translate("status.disconnected"))
            # 重置电池和信号显示
            self.battery_status.setText(i18n.translate("status.signal_unknown").replace("信号强度", "电池"))
            self.signal_status.setText(i18n.translate("status.signal_unknown"))
        
    def setup_connections(self):
        """设置信号连接"""
        # 按钮点击事件
        self.server_save_btn.clicked.connect(self.update_server_address)
        self.server_connect_btn.clicked.connect(self.connect_server)
        self.scan_btn.clicked.connect(self.show_device_scanner)
        self.connect_btn.clicked.connect(self.connect_device)
        self.log_btn.clicked.connect(self.toggle_log_window)
        self.theme_btn.clicked.connect(self.show_personalization)
        self.save_strength_btn.clicked.connect(self.update_strength_limits)
        
        # 语言切换
        self.lang_combo.currentTextChanged.connect(self.on_language_changed)
        
        # 信号处理
        self.signals.log_message.connect(self.log_output)
        self.signals.device_selected.connect(self.on_device_selected)
        self.signals.status_update.connect(self.update_status)
        self.signals.connection_changed.connect(self.on_connection_changed)
        self.signals.battery_update.connect(self.update_battery)
        self.signals.signal_update.connect(self.update_signal_strength)
    
        # 手动控制按钮连接
        self.test_a_btn.clicked.connect(lambda: self.test_channel('A'))
        self.test_b_btn.clicked.connect(lambda: self.test_channel('B'))
        self.clear_a_btn.clicked.connect(lambda: self.clear_channel('A'))
        self.clear_b_btn.clicked.connect(lambda: self.clear_channel('B'))
        
    @asyncSlot()
    async def show_device_scanner(self):
        """显示设备扫描对话框"""
        scanner = DeviceScanner(self, self.ble_manager)
        await scanner.start_scan()
        scanner.exec()
        
    @asyncSlot()
    async def on_device_selected(self, address):
        """处理设备选择"""
        if await self.ble_manager.connect(address):
            self.device_label.setText(f"Device: {address}")
            self.signals.log_message.emit(i18n.translate("status.device_connected"))
        
    def update_server_address(self):
        """更新服务器地址"""
        new_uri = self.server_input.text().strip()
        settings.socket_uri = new_uri
        settings.save()
        self.signals.log_message.emit(i18n.translate("status.server_updated"))
        
    def toggle_log_window(self):
        """切换日志窗口显示状态"""
        if not self.log_window:
            self.log_window = LogWindow(self)
        
        if self.log_window.isVisible():
            self.log_window.hide()
            self.log_btn.setText(i18n.translate("button.show_log"))
        else:
            self.log_window.show()
            self.log_btn.setText(i18n.translate("button.hide_log"))
            
    def show_personalization(self):
        """显示个性化设置对话框"""
        dialog = PersonalizationDialog(
            self,
            settings.accent_color,
            settings.background_image
        )
        if dialog.exec():
            settings_data = dialog.get_settings()
            settings.accent_color = settings_data['accent_color']
            settings.background_image = settings_data['background_image']
            settings.save()
            self.apply_theme()
            
    def apply_theme(self):
        """应用主题"""
        style = get_style(settings.accent_color, settings.background_image)
        self.setStyleSheet(style)
        
        # 更新波形图样式
        if hasattr(self, 'plot_widget_a') and hasattr(self, 'plot_widget_b'):
            # 设置波形图背景为透明
            self.plot_widget_a.setBackground('transparent')  # 修改为transparent
            self.plot_widget_b.setBackground('transparent')  # 修改为transparent
            
            # 设置网格线颜色
            self.plot_widget_a.getAxis('left').setPen(pg.mkPen(color='#888888'))
            self.plot_widget_a.getAxis('bottom').setPen(pg.mkPen(color='#888888'))
            self.plot_widget_b.getAxis('left').setPen(pg.mkPen(color='#888888'))
            self.plot_widget_b.getAxis('bottom').setPen(pg.mkPen(color='#888888'))
            
            # 设置标签颜色
            self.plot_widget_a.getAxis('left').setTextPen(pg.mkPen(color='#cccccc'))
            self.plot_widget_a.getAxis('bottom').setTextPen(pg.mkPen(color='#cccccc'))
            self.plot_widget_b.getAxis('left').setTextPen(pg.mkPen(color='#cccccc'))
            self.plot_widget_b.getAxis('bottom').setTextPen(pg.mkPen(color='#cccccc'))
            
            # 设置标题颜色
            self.plot_widget_a.setTitle(i18n.translate("status.wave_title_a"), color='#cccccc')
            self.plot_widget_b.setTitle(i18n.translate("status.wave_title_b"), color='#cccccc')

    def update_plot(self):
        """更新波形图"""
        if self.wave_queues['A']:
            self.curve_a.setData(list(self.wave_queues['A']))
        if self.wave_queues['B']:
            self.curve_b.setData(list(self.wave_queues['B']))
    
    def update_status(self, channel, value):
        """更新通道状态
        
        Args:
            channel (str): 通道名称 ('A' 或 'B')
            value (int): 当前强度值
        """
        if channel not in ['A', 'B']:
            return
            
        # 更新当前强度值
        self.current_strength[channel] = value
        
        # 更新状态标签
        if channel == 'A':
            self.a_status.setText(i18n.translate("status.channel_a", value, self.max_strength['A']))
        else:
            self.b_status.setText(i18n.translate("status.channel_b", value, self.max_strength['B']))
            
        # 更新波形数据
        self.wave_queues[channel].append(value)

    async def connect_server(self):
        """连接服务器"""
        await self.socket_manager.connect(self.server_input.text().strip())
        
    async def connect_device(self):
        """连接设备"""
        if self.ble_manager.selected_device:
            await self.ble_manager.connect(self.ble_manager.selected_device)
    
    def test_channel(self, channel):
        """测试指定通道
        
        Args:
            channel (str): 通道名称 ('A' 或 'B')
        """
        # 检查设备是否已连接
        if not self.ble_manager or not self.ble_manager.is_connected:
            QMessageBox.warning(self, i18n.translate("dialog.error"), 
                           i18n.translate("status_updates.please_select_device"))
            return
            
        if channel not in ['A', 'B']:
            return
            
        # 模拟通道测试，生成一个从0到最大强度的波形
        max_val = self.max_strength[channel]
        
        # 清空当前队列
        self.wave_queues[channel].clear()
        
        # 生成测试波形数据
        for i in range(0, max_val + 1, 5):
            self.current_strength[channel] = i
            self.wave_queues[channel].append(i)
            
            # 更新状态标签
            if channel == 'A':
                self.a_status.setText(str(i18n.translate("status.channel_a", i, max_val)))
            else:
                self.b_status.setText(str(i18n.translate("status.channel_b", i, max_val)))
        
        # 记录日志 - 修复参数不匹配问题
        self.signals.log_message.emit(str(i18n.translate("status_updates.channel_tested", {"channel": channel})))

    def clear_channel(self, channel):
        """清空指定通道"""
        # 检查设备是否已连接
        if not self.ble_manager or not self.ble_manager.is_connected:
            QMessageBox.warning(self, i18n.translate("dialog.error"), 
                           i18n.translate("status_updates.please_select_device"))
            return
            
        if channel in self.wave_queues:
            self.wave_queues[channel].clear()
            self.current_strength[channel] = 0
            self.signals.log_message.emit(str(i18n.translate("status_updates.queue_cleared", {"channel": channel})))

    def update_battery(self, percentage):
        """更新电池状态
        
        Args:
            percentage (int): 电池百分比
        """
        # 只有在设备连接时才显示电池百分比
        if self.ble_manager and self.ble_manager.is_connected:
            self.battery_status.setText(i18n.translate("status.battery", percentage))
            self.signals.log_message.emit(i18n.translate("status_updates.battery", percentage))
        else:
            self.battery_status.setText(i18n.translate("status.signal_unknown").replace("信号强度", "电池"))
        
    def update_signal_strength(self, rssi):
        """更新信号强度
        
        Args:
            rssi (int): 信号强度(dBm)
        """
        # 只有在设备连接时才显示信号强度
        if self.ble_manager and self.ble_manager.is_connected:
            self.signal_status.setText(i18n.translate("status.signal_strength", rssi))
            self.signals.log_message.emit(i18n.translate("status_updates.signal", rssi))
        else:
            self.signal_status.setText(i18n.translate("status.signal_unknown"))
        # 删除这行多余的日志输出，避免在未连接时也显示信号强度
        # self.signals.log_message.emit(i18n.translate("status_updates.signal", rssi))
        
    def update_strength_limits(self):
        """更新强度限制设置"""
        try:
            new_a_limit = int(self.a_limit_input.text())
            new_b_limit = int(self.b_limit_input.text())
            
            # 验证输入范围
            if 0 <= new_a_limit <= 200 and 0 <= new_b_limit <= 200:
                self.max_strength['A'] = new_a_limit
                self.max_strength['B'] = new_b_limit
                
                # 更新设置
                settings.max_strength = self.max_strength
                settings.save()
                
                # 更新UI
                self.a_status.setText(i18n.translate("status.channel_a", 
                                self.current_strength['A'], self.max_strength['A']))
                self.b_status.setText(i18n.translate("status.channel_b", 
                                self.current_strength['B'], self.max_strength['B']))
                
                # 更新波形图Y轴范围
                self.plot_widget_a.setYRange(0, self.max_strength['A'])
                self.plot_widget_b.setYRange(0, self.max_strength['B'])
                
                self.signals.log_message.emit(i18n.translate("status_updates.strength_limits_updated"))
            else:
                QMessageBox.warning(self, i18n.translate("dialog.error"), 
                               i18n.translate("error.invalid_strength_range"))
        except ValueError:
            QMessageBox.warning(self, i18n.translate("dialog.error"), 
                           i18n.translate("error.invalid_strength_value"))