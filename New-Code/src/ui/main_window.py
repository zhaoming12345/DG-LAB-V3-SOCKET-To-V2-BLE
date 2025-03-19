from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QGroupBox,
    QMessageBox, QComboBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIntValidator
import pyqtgraph as pg
from collections import deque
from qasync import asyncSlot
import logging  # 日志模块导入
import re  # 添加正则表达式模块用于URL验证

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
        # 初始化测试数据以确保波形图显示正常
        self.init_test_data()
        # 不在初始化中直接调用异步方法
        # 改为使用QTimer在初始化完成后调用
        QTimer.singleShot(0, self.initialize_bluetooth_check)
        
    def init_attributes(self):
        """初始化属性"""
        self.signals = DeviceSignals()
        # 修改波形队列为存储二维坐标点的队列，每个点是(x,y)格式
        self.wave_data = {'A': [], 'B': []}
        self.wave_indices = {'A': [], 'B': []}
        self.wave_queues = {'A': deque(maxlen=100), 'B': deque(maxlen=100)}
        self.current_strength = {'A': 0, 'B': 0}
        self.max_strength = settings.max_strength
        self.log_window = None
        self.data_points = 0
        
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
        main_layout.setSpacing(10)  # 使用旧版的间距
        main_layout.setContentsMargins(10, 10, 10, 10)  # 使用旧版的边距
        
        # 创建顶部标题栏 - 与旧版一致
        title_layout = QHBoxLayout()
        title_label = QLabel(i18n.translate("main_title"))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 15px;")  # 使用旧版字体样式
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # 顶部工具栏按钮 - 与旧版按钮大小和位置一致
        self.log_btn = QPushButton(i18n.translate("log.show"))
        self.theme_btn = QPushButton(i18n.translate("personalization.button"))
        self.log_btn.setFixedWidth(150)  # 调整为与旧版一致的大小
        self.theme_btn.setFixedWidth(150)  # 调整为与旧版一致的大小
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
        
        # 设备管理
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
        # 修改初始化时的电池显示，避免显示0%，并使用专门的翻译键
        self.battery_status = QLabel(i18n.translate("status.battery", "--"))
        self.signal_status = QLabel(i18n.translate("status.signal_unknown"))
        status_layout.addWidget(self.a_status)
        status_layout.addWidget(self.b_status)
        status_layout.addWidget(self.battery_status)
        status_layout.addWidget(self.signal_status)
        wave_layout.addLayout(status_layout)
        
        # 创建双波形水平布局
        plots_layout = QHBoxLayout()
        
        # 通道A波形
        self.plot_widget_a = pg.PlotWidget()
        self.plot_widget_a.setBackground('transparent')  # 使用'transparent'替代None
        self.plot_widget_a.setTitle(i18n.translate("status.wave_title_a"))
        self.plot_widget_a.setLabel('left', i18n.translate("status.wave_y_label"))
        self.plot_widget_a.setLabel('bottom', i18n.translate("status.wave_x_label"))
        self.plot_widget_a.showGrid(x=True, y=True, alpha=0.3)  # 设置网格透明度
        self.plot_widget_a.setMouseEnabled(x=False, y=False)
        self.plot_widget_a.setMenuEnabled(False)
        view_box_a = self.plot_widget_a.getViewBox()
        view_box_a.setMouseMode(pg.ViewBox.RectMode)
        view_box_a.setMouseEnabled(x=False, y=False)
        view_box_a.enableAutoRange(enable=False)
        view_box_a.setBackgroundColor(None)  # 设置ViewBox背景为透明
        
        # 设置轴线颜色和透明度
        axis_pen = pg.mkPen(color='#ffffff', width=1)
        axis_text_pen = pg.mkPen(color='#ffffff')
        self.plot_widget_a.getAxis('bottom').setPen(axis_pen)
        self.plot_widget_a.getAxis('left').setPen(axis_pen)
        self.plot_widget_a.getAxis('bottom').setTextPen(axis_text_pen)
        self.plot_widget_a.getAxis('left').setTextPen(axis_text_pen)
        
        # 通道B波形
        self.plot_widget_b = pg.PlotWidget()
        self.plot_widget_b.setBackground('transparent')  # 使用'transparent'替代None
        self.plot_widget_b.setTitle(i18n.translate("status.wave_title_b"))
        self.plot_widget_b.setLabel('left', i18n.translate("status.wave_y_label"))
        self.plot_widget_b.setLabel('bottom', i18n.translate("status.wave_x_label"))
        self.plot_widget_b.showGrid(x=True, y=True, alpha=0.3)  # 设置网格透明度
        self.plot_widget_b.setMouseEnabled(x=False, y=False)
        self.plot_widget_b.setMenuEnabled(False)
        view_box_b = self.plot_widget_b.getViewBox()
        view_box_b.setMouseMode(pg.ViewBox.RectMode)
        view_box_b.setMouseEnabled(x=False, y=False)
        view_box_b.enableAutoRange(enable=False)
        view_box_b.setBackgroundColor(None)  # 设置ViewBox背景为透明
        
        # 设置轴线颜色和透明度
        self.plot_widget_b.getAxis('bottom').setPen(axis_pen)
        self.plot_widget_b.getAxis('left').setPen(axis_pen)
        self.plot_widget_b.getAxis('bottom').setTextPen(axis_text_pen)
        self.plot_widget_b.getAxis('left').setTextPen(axis_text_pen)
        
        # 保存初始显示范围
        self.expected_y_range_a = (0, self.max_strength['A'])
        self.expected_y_range_b = (0, self.max_strength['B'])
        self.expected_x_range = (-100, 0)  # 显示最近100个数据点
        self.plot_widget_a.setYRange(*self.expected_y_range_a)
        self.plot_widget_a.setXRange(*self.expected_x_range)
        self.plot_widget_b.setYRange(*self.expected_y_range_b)
        self.plot_widget_b.setXRange(*self.expected_x_range)
        
        # 创建两条曲线
        self.curve_a = self.plot_widget_a.plot(pen=pg.mkPen(color=(0, 255, 0, 200), width=2), name='A通道')  # 绿色，半透明
        self.curve_b = self.plot_widget_b.plot(pen=pg.mkPen(color=(255, 0, 0, 200), width=2), name='B通道')  # 红色，半透明
        
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
    
        # 设置波形更新定时器
        self.update_timer = pg.QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_plot)
        self.update_timer.start(50)

        # 创建范围监控定时器
        self.range_monitor = pg.QtCore.QTimer()
        self.range_monitor.timeout.connect(self.check_plot_range)
        self.range_monitor.start(50)  # 每50ms检查一次

        # 初始化时禁用连接服务器按钮和手动控制按钮
        self.server_connect_btn.setEnabled(False)
        self.test_a_btn.setEnabled(False)
        self.test_b_btn.setEnabled(False)
        self.clear_a_btn.setEnabled(False)
        self.clear_b_btn.setEnabled(False)

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
        
        # 根据连接状态启用/禁用按钮
        self.scan_btn.setEnabled(not connected)
        self.connect_btn.setEnabled(not connected)
        self.server_connect_btn.setEnabled(connected)  # 只有连接了蓝牙设备才能连接服务器
        
        # 控制手动控制按钮的状态
        self.test_a_btn.setEnabled(connected)
        self.test_b_btn.setEnabled(connected)
        self.clear_a_btn.setEnabled(connected)
        self.clear_b_btn.setEnabled(connected)
        
        if connected:
            self.signals.log_message.emit(i18n.translate("status.connected"))
        else:
            self.signals.log_message.emit(i18n.translate("status.disconnected"))
            # 重置电池和信号显示 - 使用正确的翻译键
            self.battery_status.setText(i18n.translate("status.battery", "--"))
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
        
        # 验证URL格式
        if not is_valid_websocket_url(new_uri):
            QMessageBox.warning(self,
                i18n.translate("dialog.error"),
                i18n.translate("dialog.invalid_url"),
                QMessageBox.Ok)
            return
        
        settings.socket_uri = new_uri
        settings.save()
        self.signals.log_message.emit(i18n.translate("status_updates.server_updated", new_uri))
        
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
        """应用主题样式"""
        # 获取当前设置
        accent_color = settings.accent_color
        background_image = settings.background_image
        
        # 应用样式表
        style_sheet = get_style(accent_color, background_image)
        self.setStyleSheet(style_sheet)
        
        # 更新波形图样式
        axis_pen = pg.mkPen(color='#ffffff', width=1)
        axis_text_pen = pg.mkPen(color='#ffffff')
        
        for plot_widget in [self.plot_widget_a, self.plot_widget_b]:
            # 设置背景为透明
            plot_widget.setBackground('transparent')
            # 设置轴线颜色和透明度
            plot_widget.getAxis('bottom').setPen(axis_pen)
            plot_widget.getAxis('left').setPen(axis_pen)
            plot_widget.getAxis('bottom').setTextPen(axis_text_pen)
            plot_widget.getAxis('left').setTextPen(axis_text_pen)
            # 设置网格线
            plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # 设置A通道的波形颜色为绿色，与旧版一致
        self.curve_a.setPen(pg.mkPen(color=(0, 255, 0, 200), width=2))
        # 设置B通道的波形颜色为红色，与旧版一致
        self.curve_b.setPen(pg.mkPen(color=(255, 0, 0, 200), width=2))
        
        # 如果日志窗口存在，也应用样式
        if self.log_window:
            self.log_window.setStyleSheet(style_sheet)
        
    def update_plot(self):
        """更新波形图"""
        # 只有当队列中有数据时才更新曲线
        for channel in ['A', 'B']:
            if len(self.wave_queues[channel]) > 0:
                # 创建x轴数据(索引列表)
                x_data = list(range(-len(self.wave_queues[channel]), 0))
                # 使用队列中的数据作为y轴数据
                y_data = list(self.wave_queues[channel])
                # 更新相应的曲线
                if channel == 'A':
                    self.curve_a.setData(x_data, y_data)
                else:
                    self.curve_b.setData(x_data, y_data)

    def update_status(self, channel, value):
        """更新通道状态
        
        Args:
            channel (str): 通道名称 ('A' 或 'B')
            value (int): 当前强度值
        """
        if channel not in ['A', 'B']:
            return
            
        # 更新当前强度值
        try:
            value = int(value)
            self.current_strength[channel] = value
            
            # 更新状态标签
            if channel == 'A':
                self.a_status.setText(i18n.translate("status.channel_a", value, self.max_strength['A']))
            else:
                self.b_status.setText(i18n.translate("status.channel_b", value, self.max_strength['B']))
                
            # 更新波形数据 - 只保存Y值，X值在绘图时生成
            self.wave_queues[channel].append(value)
            
            # 记录数据点数量
            self.data_points += 1
            
            # 每增加一个数据点就检查一次范围
            if self.data_points % 5 == 0:  # 每5个点检查一次以减少CPU负担
                self.check_plot_range()
                
        except (ValueError, TypeError) as e:
            logging.error(f"更新状态时出错: {str(e)}")

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
            return  # 如果未连接设备，直接返回，按钮状态已经由on_connection_changed控制
            
        if channel not in ['A', 'B']:
            return
            
        # 模拟通道测试，生成一个从0到最大强度的波形
        max_val = self.max_strength[channel]
        
        # 清空当前队列
        self.wave_queues[channel].clear()
        
        # 生成测试波形数据 - 使用正弦波形更好地测试显示效果
        import math
        steps = 50  # 测试使用50个点
        for i in range(steps):
            # 生成0到最大值之间的正弦波形
            value = int(max_val * 0.5 * (1 + math.sin(i * 2 * math.pi / steps)))
            self.current_strength[channel] = value
            self.wave_queues[channel].append(value)
            
            # 更新状态标签
            if channel == 'A':
                self.a_status.setText(str(i18n.translate("status.channel_a", value, max_val)))
            else:
                self.b_status.setText(str(i18n.translate("status.channel_b", value, max_val)))
        
        # 记录日志
        self.signals.log_message.emit(str(i18n.translate("status_updates.channel_tested", {"channel": channel})))

    def clear_channel(self, channel):
        """清空指定通道"""
        # 检查设备是否已连接
        if not self.ble_manager or not self.ble_manager.is_connected:
            return  # 如果未连接设备，直接返回，按钮状态已经由on_connection_changed控制
            
        if channel in self.wave_queues:
            self.wave_queues[channel].clear()
            self.current_strength[channel] = 0
            
            # 更新状态标签
            if channel == 'A':
                self.a_status.setText(str(i18n.translate("status.channel_a", 0, self.max_strength['A'])))
            else:
                self.b_status.setText(str(i18n.translate("status.channel_b", 0, self.max_strength['B'])))
                
            # 重置波形图
            if channel == 'A':
                self.curve_a.setData([], [])
            else:
                self.curve_b.setData([], [])
                
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
                
                # 更新波形图Y轴范围 - 每个通道使用各自的最大值
                self.expected_y_range_a = (0, self.max_strength['A'])
                self.expected_y_range_b = (0, self.max_strength['B'])
                self.plot_widget_a.setYRange(0, self.max_strength['A'])
                self.plot_widget_b.setYRange(0, self.max_strength['B'])
                
                self.signals.log_message.emit(i18n.translate("status_updates.strength_limits_updated"))
            else:
                QMessageBox.warning(self, i18n.translate("dialog.error"), 
                               i18n.translate("error.invalid_strength_range"))
        except ValueError:
            QMessageBox.warning(self, i18n.translate("dialog.error"), 
                           i18n.translate("error.invalid_strength_value"))

    @asyncSlot()
    async def initialize_bluetooth_check(self):
        """初始化完成后检查蓝牙功能"""
        await self.check_bluetooth_available()

    async def check_bluetooth_available(self):
        """检查蓝牙功能是否可用"""
        if not await self.ble_manager.check_bluetooth_available():
            from PySide6.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle(i18n.translate("error.bluetooth_not_available"))
            msg.setText(i18n.translate("error.bluetooth_not_available_message"))
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            # 禁用相关按钮
            self.connect_btn.setEnabled(False)
            self.scan_btn.setEnabled(False)

    def check_plot_range(self):
        """检查并维护波形图的显示范围
        
        确保波形图的显示范围保持在预期的范围内，包括：
        1. Y轴范围：从0到各自通道的最大强度值
        2. X轴范围：显示最近100个数据点
        """
        try:
            # 更新Y轴范围 - 分别使用各自通道的最大值
            if self.expected_y_range_a[1] != self.max_strength['A']:
                self.expected_y_range_a = (0, self.max_strength['A'])
                self.plot_widget_a.setYRange(0, self.max_strength['A'])
                
            if self.expected_y_range_b[1] != self.max_strength['B']:
                self.expected_y_range_b = (0, self.max_strength['B'])
                self.plot_widget_b.setYRange(0, self.max_strength['B'])
            
            # 检查并重置当前范围 - 防止用户意外修改显示范围
            # A通道波形图范围检查
            y_range = self.plot_widget_a.getViewBox().viewRange()[1]
            if abs(y_range[0] - self.expected_y_range_a[0]) > 5 or abs(y_range[1] - self.expected_y_range_a[1]) > 5:
                self.plot_widget_a.setYRange(*self.expected_y_range_a)
                
            x_range = self.plot_widget_a.getViewBox().viewRange()[0]
            if abs(x_range[0] - self.expected_x_range[0]) > 5 or abs(x_range[1] - self.expected_x_range[1]) > 5:
                self.plot_widget_a.setXRange(*self.expected_x_range)
                
            # B通道波形图范围检查
            y_range = self.plot_widget_b.getViewBox().viewRange()[1]
            if abs(y_range[0] - self.expected_y_range_b[0]) > 5 or abs(y_range[1] - self.expected_y_range_b[1]) > 5:
                self.plot_widget_b.setYRange(*self.expected_y_range_b)
                
            x_range = self.plot_widget_b.getViewBox().viewRange()[0]
            if abs(x_range[0] - self.expected_x_range[0]) > 5 or abs(x_range[1] - self.expected_x_range[1]) > 5:
                self.plot_widget_b.setXRange(*self.expected_x_range)
                    
        except Exception as e:
            logging.error(f"检查波形范围时发生错误: {str(e)}")

    def init_test_data(self):
        """初始化波形图显示，不添加测试数据"""
        # 将波形队列清空
        for channel in ['A', 'B']:
            self.wave_queues[channel].clear()
        
        # 设置波形曲线为空数据
        self.curve_a.setData([], [])
        self.curve_b.setData([], [])
        
        # 确保Y轴和X轴范围设置正确
        self.plot_widget_a.setYRange(0, self.max_strength['A'])
        self.plot_widget_a.setXRange(*self.expected_x_range)
        self.plot_widget_b.setYRange(0, self.max_strength['B'])
        self.plot_widget_b.setXRange(*self.expected_x_range)

def is_valid_websocket_url(url):
    """验证WebSocket URL是否有效
    
    使用正则表达式检查URL格式是否符合WebSocket协议要求。
    
    Args:
        url (str): 要验证的WebSocket URL
        
    Returns:
        bool: URL格式是否有效
    """
    # 检查URL格式
    ws_pattern = r'^(ws|wss):\/\/[^\s\/$.?#].[^\s]*$'
    return bool(re.match(ws_pattern, url))
