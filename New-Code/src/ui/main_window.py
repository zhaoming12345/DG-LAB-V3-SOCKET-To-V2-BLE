from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, QTimer
from qasync import asyncSlot
import logging
import sys
import os
import asyncio
import json

from utils.signals import DeviceSignals
from utils.i18n import i18n
from core.ble_manager import BLEManager
from core.socket_manager import SocketManager
# 修正导入路径
from core.protocol import ProtocolConverter, BLE_CHAR_PWM_A34, BLE_CHAR_PWM_B34, BLE_CHAR_PWM_AB2
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
    """主窗口类
    
    负责创建和管理应用程序的主界面，包括：
    - 设备连接和管理
    - 服务器连接和配置
    - 强度控制和波形显示
    - 语言切换
    - 主题设置
    """
    
    def __init__(self):
        """初始化主窗口
        
        执行顺序：
        1. 初始化基本属性（init_attributes）
        2. 创建UI组件（init_ui）
        3. 设置管理器（setup_managers）
        4. 建立信号连接（setup_connections）
        5. 应用主题（apply_theme）
        """
        super().__init__()
        logging.info("开始初始化主窗口...")
        self.init_attributes()
        logging.info("基本属性初始化完成")
        self.init_ui()
        logging.info("UI组件初始化完成")
        self.setup_managers()
        logging.info("管理器设置完成")
        self.setup_connections()
        logging.info("信号连接设置完成")
        self.apply_theme()
        logging.info("主题应用完成")
        logging.info("主窗口初始化完成")
        
        QTimer.singleShot(0, self.device_manager.initialize_bluetooth_check)
        logging.info("已设置蓝牙检查延迟执行")
        
    def init_attributes(self):
        """初始化窗口属性和管理器
        
        包括：
        - 信号对象（用于跨组件通信）
        - BLE管理器（处理蓝牙通信）
        - Socket管理器（处理服务器通信）
        - 主题相关属性
        - 定时器（用于更新电池和信号强度）
        """
        # 创建信号对象用于组件间通信
        self.signals = DeviceSignals()
        
        # 创建蓝牙管理器并设置最大强度
        self.ble_manager = BLEManager(self.signals)
        self.ble_manager.max_strength = {
            'A': settings.max_strength_a,
            'B': settings.max_strength_b
        }
        logging.info(f"BLE管理器初始化完成，最大强度配置：A={self.ble_manager.max_strength['A']}, B={self.ble_manager.max_strength['B']}")
        
        # 创建Socket管理器
        # 确保事件循环已启动
        if not asyncio.get_event_loop().is_running():
            asyncio.set_event_loop(asyncio.new_event_loop())
        self.socket_manager = SocketManager(self.signals, self.ble_manager)
        
        # 日志窗口初始为None，首次显示时才创建
        self.log_window = None
        
        # 从配置加载主题设置
        self.accent_color = settings.accent_color
        self.background_image = settings.background_image
        
        # 设置窗口基本属性
        self.setWindowTitle(i18n.translate("app_title"))
        self.setMinimumSize(750, 965)  # 窗口最小大小
        
        # 应用主题样式
        self.apply_theme()

        # 创建定时器用于定期更新状态
        self.battery_update_timer = QTimer()  # 电池电量更新定时器
        self.signal_update_timer = QTimer()   # 信号强度更新定时器
        
        # 保存当前标题文本，用于语言切换时更新
        self.old_title = i18n.translate("main_title")
        
    def init_ui(self):
        """初始化用户界面
        
        创建和布局所有UI组件，包括：
        - 顶部标题栏
        - 左侧控制面板（语言、设备、服务器、强度设置）
        - 右侧显示面板（波形图、控制按钮）
        """
        # 设置窗口基本属性
        self.setWindowTitle(i18n.translate("main_title"))
        self.setGeometry(100, 100, 1250, 965)  # 窗口默认大小
        
        # 中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)  # 增加布局间距
        main_layout.setContentsMargins(15, 15, 15, 15)  # 增加边距
        
        # 顶部标题栏
        self.title_layout = QHBoxLayout()
        title_label = QLabel(i18n.translate("main_title"))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 15px;")
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
        
        # 创建各功能组件
        self.lang_group, self.lang_combo = create_language_group()
        self.device_group, self.device_label, self.scan_btn, self.connect_btn, self.device_status = create_device_group()
        self.server_group, self.server_input, self.server_save_btn, self.server_connect_btn = create_server_group()
        self.strength_group, self.a_limit_input, self.b_limit_input, self.save_strength_btn = create_strength_group()
        self.wave_group, self.a_status, self.b_status, self.battery_status, self.signal_status, self.plot_widget_a, self.plot_widget_b = create_wave_group()
        
        # 强度显示标签
        self.a_strength_label = QLabel('0%')
        self.b_strength_label = QLabel('0%')
        wave_layout.addWidget(QLabel(i18n.translate("status.strength_a")))
        wave_layout.addWidget(self.a_strength_label)
        wave_layout.addWidget(QLabel(i18n.translate("status.strength_b")))
        wave_layout.addWidget(self.b_strength_label)
        
        # 创建手动控制组件
        self.control_group = QGroupBox(i18n.translate("control.manual"))
        control_layout = QHBoxLayout()
        
        # A通道控制按钮组
        a_control_layout = QHBoxLayout()
        self.a_plus_btn = QPushButton("+")    # A通道增加按钮
        self.a_minus_btn = QPushButton("-")   # A通道减少按钮
        self.clear_a_btn = QPushButton(i18n.translate("control.clear_a"))  # A通道清除按钮
        a_control_layout.addWidget(self.a_plus_btn)
        a_control_layout.addWidget(self.a_minus_btn)
        a_control_layout.addWidget(self.clear_a_btn)
        
        # B通道控制按钮组
        b_control_layout = QHBoxLayout()
        self.b_plus_btn = QPushButton("+")    # B通道增加按钮
        self.b_minus_btn = QPushButton("-")   # B通道减少按钮
        self.clear_b_btn = QPushButton(i18n.translate("control.clear_b"))  # B通道清除按钮
        b_control_layout.addWidget(self.b_plus_btn)
        b_control_layout.addWidget(self.b_minus_btn)
        b_control_layout.addWidget(self.clear_b_btn)
        
        # 统一设置所有控制按钮的样式
        control_buttons = [
            self.a_plus_btn, self.a_minus_btn, self.clear_a_btn,
            self.b_plus_btn, self.b_minus_btn, self.clear_b_btn
        ]
        
        # 设置按钮的统一样式
        for btn in control_buttons:
            if btn in [self.a_plus_btn, self.a_minus_btn, self.b_plus_btn, self.b_minus_btn]:
                # 加减按钮使用正方形样式
                btn.setFixedSize(27, 27)
                btn.setStyleSheet("""
                    QPushButton {
                        font-size: 10px;
                        font-weight: bold;
                        padding: 5px 10px;
                        min-width: 50px;
                    }
                """)
            else:
                # 清除按钮使用相同高度，但宽度更大
                btn.setFixedSize(120, 27)  # 设置清除按钮的尺寸
                btn.setStyleSheet("""
                    QPushButton {
                        font-size: 14px;
                        font-weight: bold;
                        padding: 5px;
                        min-width: 120px;
                    }
                """)
        
        # 设置布局间距
        a_control_layout.setSpacing(10)  # 设置按钮之间的间距
        b_control_layout.setSpacing(10)  # 设置按钮之间的间距
        
        # 组装控制布局
        control_layout.addLayout(a_control_layout)
        control_layout.addSpacing(30)  # 通道间距
        control_layout.addLayout(b_control_layout)
        self.control_group.setLayout(control_layout)
        
        # 创建左右分栏布局
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.lang_group)      # 语言设置
        left_layout.addWidget(self.device_group)    # 设备管理
        left_layout.addWidget(self.server_group)    # 服务器配置
        left_layout.addWidget(self.strength_group)  # 强度设置
        left_layout.addWidget(self.control_group)   # 将控制组添加到左侧布局
        left_layout.addStretch()  # 添加弹性空间
        
        # 创建上部布局（左侧设置）
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)  # 增加左右布局之间的间距
        top_layout.addLayout(left_layout, 1)   # 左侧占比1
        
        # 创建波形图布局
        wave_layout = QVBoxLayout()
        wave_layout.addWidget(self.wave_group)  # 波形显示
        
        # 将布局添加到主布局
        main_layout.addLayout(top_layout, 1)  # 上部布局占1份
        main_layout.addLayout(wave_layout, 2)  # 波形图布局占2份
        
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
    
    def setup_connections(self):
        """设置信号连接"""
        logging.info("开始设置信号连接...")
        
        # 日志按钮
        self.log_btn.clicked.connect(self.toggle_log_window)
        logging.debug("日志按钮信号已连接")
        
        # 主题按钮
        self.theme_btn.clicked.connect(self.show_personalization)
        logging.debug("主题按钮信号已连接")
        
        # 语言选择
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        logging.debug("语言选择信号已连接")
        
        # 手动控制按钮
        self.a_plus_btn.clicked.connect(lambda: asyncio.create_task(self.adjust_strength('A', 1)))
        self.a_minus_btn.clicked.connect(lambda: asyncio.create_task(self.adjust_strength('A', -1)))
        self.b_plus_btn.clicked.connect(lambda: asyncio.create_task(self.adjust_strength('B', 1)))
        self.b_minus_btn.clicked.connect(lambda: asyncio.create_task(self.adjust_strength('B', -1)))
        self.clear_a_btn.clicked.connect(lambda: asyncio.create_task(self.clear_channel('A')))
        self.clear_b_btn.clicked.connect(lambda: asyncio.create_task(self.clear_channel('B')))
        logging.debug("控制按钮信号已连接")
        
        # 电池和信号强度更新定时器
        self.battery_update_timer.timeout.connect(self.device_manager.update_battery)
        self.signal_update_timer.timeout.connect(self.device_manager.update_signal_strength)
        
        # 设置并启动定时器
        self.battery_update_timer.setInterval(60000)  # 一分钟更新一次电池状态
        self.signal_update_timer.setInterval(5000)   # 5秒更新一次信号强度
        
        # 启动定时器
        self.battery_update_timer.start()
        self.signal_update_timer.start()
        logging.debug("定时器已设置并启动 - 电池更新间隔: 60秒, 信号强度更新间隔: 5秒")
        
        # 加载可用语言
        self.load_languages()
        logging.debug("语言已加载")
        
        # 加载服务器地址
        self.server_input.setText(settings.socket_uri)
        logging.debug(f"已加载服务器地址: {settings.socket_uri}")
        
        logging.info("所有信号连接设置完成")
    
    def load_languages(self):
        """加载可用语言"""
        # 阻止信号触发
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()
        languages = i18n.load_languages()
        
        current_index = 0  # 默认选择第一项
        
        for idx, (code, name) in enumerate(languages.items()):
            self.lang_combo.addItem(name, code)
            logging.info(f"Adding language: {code} - {name}")
            
            # 设置当前语言
            if code == i18n.current_lang:
                current_index = idx
                logging.info(f"Found current language in combo: {code} at index {idx}")
        
        # 设置当前选中的语言
        if self.lang_combo.count() > 0:
            self.lang_combo.setCurrentIndex(current_index)
            logging.info(f"Set language combo to index {current_index} for language {i18n.current_lang}")
        
        # 恢复信号连接
        self.lang_combo.blockSignals(False)
    
    def change_language(self, index):
        """切换语言"""
        if index < 0:
            return
            
        lang_code = self.lang_combo.itemData(index)
        logging.info(f"Language selection changed to: {lang_code}")
        
        if not lang_code:
            logging.error("No language code found for index: {index}")
            return
            
        if lang_code == i18n.current_lang:
            logging.info("Selected language is already current")
            return
            
        # 加载新语言
        if i18n.load_language(lang_code, save_to_config=True):
            logging.info(f"Successfully loaded language: {lang_code}")
            
            # 更新UI文本
            self.update_ui_texts()
            
            # 通知用户语言已更改
            self.signals.log_message.emit(i18n.translate("status_updates.language_changed"))
            logging.info(f"UI language updated to: {lang_code}")
        else:
            # 如果加载失败，显示错误消息
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                i18n.translate("dialog.error"),
                i18n.translate("error.language_load_failed")
            )
            logging.error(f"Failed to load language: {lang_code}")
            
            # 重置下拉框选择
            for i in range(self.lang_combo.count()):
                if self.lang_combo.itemData(i) == i18n.current_lang:
                    self.lang_combo.setCurrentIndex(i)
                    break
                    
    def update_ui_texts(self):
        """更新UI上的所有文本"""
        logging.info("开始更新UI文本...")
        try:
            # 更新窗口标题
            new_title = i18n.translate("main_title")
            old_title = self.windowTitle()
            self.setWindowTitle(new_title)
            logging.debug(f"窗口标题更新: {old_title} -> {new_title}")
            
            # 更新顶部标题
            for i in range(self.title_layout.count()):
                widget = self.title_layout.itemAt(i).widget()
                if isinstance(widget, QLabel) and widget.text() == self.old_title:
                    widget.setText(new_title)
                    self.old_title = new_title
                    logging.debug(f"顶部标题更新为: {new_title}")
                    break
            
            # 更新按钮文本
            self.log_btn.setText(i18n.translate("log.show"))
            self.theme_btn.setText(i18n.translate("personalization.button"))
            
            # 更新分组框标题
            self.lang_group.setTitle(i18n.translate("language.setting"))
            self.device_group.setTitle(i18n.translate("device.management"))
            self.server_group.setTitle(i18n.translate("server.config"))
            self.strength_group.setTitle(i18n.translate("strength.config"))
            self.control_group.setTitle(i18n.translate("control.manual"))
            self.wave_group.setTitle(i18n.translate("status.realtime"))
            
            # 更新设备管理组件
            self.device_label.setText(i18n.translate("label.no_device") if not self.ble_manager.selected_device else 
                                f"{self.ble_manager.selected_device_name or i18n.translate('device.unknown')} ({self.ble_manager.selected_device})")
            self.scan_btn.setText(i18n.translate("device.scan"))
            self.connect_btn.setText(i18n.translate("device.connect"))
            
            # 更新设备状态文本
            status_text = i18n.translate("device.connected") if self.ble_manager.is_connected else i18n.translate("device.disconnected")
            self.device_status.setText(i18n.translate("device.status", status_text))
            
            # 更新服务器配置组件
            self.server_save_btn.setText(i18n.translate("server.save"))
            self.server_connect_btn.setText(i18n.translate("server.connect"))
            
            # 更新强度配置组件标签
            for i in range(self.strength_group.layout().count()):
                item = self.strength_group.layout().itemAt(i)
                if isinstance(item, QHBoxLayout):
                    for j in range(item.count()):
                        widget = item.itemAt(j).widget()
                        if isinstance(widget, QLabel):
                            if "A" in widget.text():
                                widget.setText(i18n.translate("strength.channel_a_limit"))
                            elif "B" in widget.text():
                                widget.setText(i18n.translate("strength.channel_b_limit"))
            
            # 更新强度保存按钮
            self.save_strength_btn.setText(i18n.translate("strength.save"))
            
            # 更新手动控制按钮
            self.clear_a_btn.setText(i18n.translate("control.clear_a"))
            self.clear_b_btn.setText(i18n.translate("control.clear_b"))
            
            # 更新实时状态显示
            self.strength_manager.update_strength_display()
            
            # 更新电池和信号状态
            if hasattr(self, 'battery_status') and self.battery_status:
                battery_level = self.ble_manager.battery_level if hasattr(self.ble_manager, 'battery_level') else None
                if battery_level is not None:
                    self.battery_status.setText(i18n.translate("status.battery", battery_level))
                
            if hasattr(self, 'signal_status') and self.signal_status:
                signal_strength = self.ble_manager.signal_strength if hasattr(self.ble_manager, 'signal_strength') else None
                if signal_strength is not None:
                    # 根据信号强度设置不同的状态文本
                    if signal_strength > -50:
                        status_text = i18n.translate("status.signal_excellent")
                    elif signal_strength > -65:
                        status_text = i18n.translate("status.signal_good")
                    elif signal_strength > -75:
                        status_text = i18n.translate("status.signal_fair")
                    elif signal_strength > -85:
                        status_text = i18n.translate("status.signal_weak")
                    else:
                        status_text = i18n.translate("status.signal_very_weak")
                    
                    self.signal_status.setText(f"{status_text} ({signal_strength} dBm)")
                else:
                    self.signal_status.setText(i18n.translate("status.signal_unknown"))
            logging.info("UI文本更新完成")
        except Exception as e:
            logging.error(f"更新UI文本时出错: {str(e)}")
            self.signals.log_message.emit(f"更新UI文本失败: {str(e)}")
    
    def toggle_log_window(self):
        """切换日志窗口显示状态"""
        try:
            if not self.log_window:
                logging.debug("创建新的日志窗口")
                self.log_window = LogWindow(self)
                self.log_window.window_closed.connect(self.on_log_window_closed)
                # 设置窗口位置为主窗口右侧
                main_pos = self.pos()
                main_size = self.size()
                self.log_window.move(main_pos.x() + main_size.width() + 20, main_pos.y())
                self.log_window.apply_theme()
                logging.debug("日志窗口初始化完成")
            
            if self.log_window.isVisible():
                logging.debug("隐藏日志窗口")
                self.log_window.hide()
                self.log_btn.setText(i18n.translate("log.show"))
            else:
                logging.debug("显示日志窗口")
                # 如果窗口已最小化，恢复它
                if self.log_window.isMinimized():
                    self.log_window.showNormal()
                else:
                    self.log_window.show()
                self.log_btn.setText(i18n.translate("log.hide"))
                
        except Exception as e:
            logging.error(f"切换日志窗口时发生错误: {str(e)}")
            
    def on_log_window_closed(self):
        """日志窗口关闭事件处理"""
        logging.debug("日志窗口已关闭")
        self.log_btn.setText(i18n.translate("log.show"))
        # 不销毁窗口实例，只是隐藏它
        if self.log_window:
            self.log_window.hide()
        
    def show_personalization(self):
        """显示个性化设置对话框"""
        logging.info("打开个性化设置对话框")
        dialog = PersonalizationDialog(self, self.accent_color, self.background_image)
        
        if dialog.exec():
            logging.info("用户确认了个性化设置更改")
            # 获取新的设置
            old_accent = self.accent_color
            old_bg = self.background_image
            self.accent_color = dialog.accent_color
            self.background_image = dialog.background_image
            
            logging.debug(f"主题色变更: {old_accent} -> {self.accent_color}")
            logging.debug(f"背景图变更: {old_bg} -> {self.background_image}")
            
            # 更新设置
            settings.accent_color = self.accent_color
            settings.background_image = self.background_image
            settings.save()
            logging.info("个性化设置已保存到配置文件")
            
            # 应用新主题
            self.apply_theme()
            logging.debug("新主题已应用到主窗口")
            
            # 如果日志窗口存在，也应用新主题
            if self.log_window:
                self.log_window.apply_theme(self.accent_color, self.background_image)
                logging.debug("新主题已应用到日志窗口")
        else:
            logging.info("用户取消了个性化设置更改")
    
    def apply_theme(self):
        """应用主题样式"""
        logging.info(f"开始应用主题 - 主题色: {self.accent_color}, 背景图: {self.background_image}")
        try:
            style_sheet = get_style(self.accent_color, self.background_image)
            self.setStyleSheet(style_sheet)
            # 更新波形图颜色
            if hasattr(self, 'wave_manager'):
                self.wave_manager.apply_theme()
            logging.info("主题样式应用成功")
        except Exception as e:
            logging.error(f"应用主题样式失败: {str(e)}")
    
    @asyncSlot()
    async def adjust_strength(self, channel, delta):
        """调整通道强度的异步方法
        
        Args:
            channel (str): 通道标识('A'或'B')
            delta (int): 强度变化值(+1或-1)
            
        流程：
        1. 检查设备连接状态
        2. 获取当前强度和最大强度限制
        3. 计算新强度值并验证范围
        4. 发送强度调整命令
        5. 更新UI显示
        """
        # 检查设备连接状态
        if not self.ble_manager.is_connected:
            self.signals.log_message.emit(i18n.translate("status_updates.no_device_connected"))
            return
            
        try:
            # 获取当前强度和限制
            current = self.ble_manager.current_strength[channel]
            max_strength = self.ble_manager.max_strength[channel]
            
            # 如果当前强度为0且要减小强度，直接返回
            if current == 0 and delta < 0:
                self.signals.log_message.emit(i18n.translate("status_updates.strength_min_reached", channel))
                logging.info(f"通道{channel}强度已经是最小值(0)")
                return
                
            # 如果当前强度为最大值且要增加强度，直接返回
            if current == max_strength and delta > 0:
                self.signals.log_message.emit(i18n.translate("status_updates.strength_max_reached", channel))
                logging.info(f"通道{channel}强度已经是最大值({max_strength})")
                return
                
            # 计算新强度值
            new_strength = current + delta
            
            # 验证并设置新强度
            if 0 <= new_strength <= max_strength:
                # 发送强度调整命令
                await self.ble_manager.set_strength(channel, new_strength)
                # 发送状态更新消息
                self.signals.log_message.emit(i18n.translate("status_updates.strength_adjusted", 
                    channel, new_strength))
                logging.info(f"通道{channel}强度已调整：{current} -> {new_strength}")
            else:
                # 如果新强度超出范围，发送提示消息
                if new_strength < 0:
                    self.signals.log_message.emit(i18n.translate("status_updates.strength_min_reached", channel))
                    logging.info(f"通道{channel}强度已达到最小值")
                elif new_strength > max_strength:
                    self.signals.log_message.emit(i18n.translate("status_updates.strength_max_reached", channel))
                    logging.info(f"通道{channel}强度已达到最大值")
                    
        except Exception as e:
            # 错误处理
            error_msg = str(e)
            self.signals.log_message.emit(i18n.translate("status_updates.strength_adjust_failed", error_msg))
            logging.error(f"调整通道{channel}强度失败: {error_msg}")
            
    async def clear_channel(self, channel):
        """清除指定通道的数据
        
        Args:
            channel (str): 通道标识('A'或'B')
            
        执行操作：
        1. 清除波形显示数据
        2. 如果设备已连接，发送清除命令
        3. 更新UI显示
        """
        if channel not in ['A', 'B']:
            logging.warning(f"无效的通道标识: {channel}")
            return
            
        try:
            # 清除波形显示
            self.wave_manager.clear_channel_data(channel)
            logging.info(f"已清除通道{channel}的波形数据")
            
            # 如果设备已连接，发送清除命令
            if self.ble_manager.is_connected:
                # 将强度设置为0
                await self.ble_manager.set_strength(channel, 0)
                self.signals.log_message.emit(i18n.translate("status_updates.channel_cleared", channel))
                logging.info(f"已发送清除通道{channel}的命令")
                
                # 如果连接了服务器，同步更新服务器状态
                if self.socket_manager.ws:
                    channel_num = 1 if channel == 'A' else 2
                    message = {
                        "type": "msg",
                        "clientId": self.socket_manager.client_id,
                        "targetId": self.socket_manager.target_id or "",
                        "message": f"clear-{channel_num}"
                    }
                    await self.socket_manager.ws.send(json.dumps(message))
                    logging.info(f"已向服务器发送通道{channel}的清除命令")
                    
        except Exception as e:
            error_msg = str(e)
            self.signals.log_message.emit(i18n.translate("status_updates.clear_channel_failed", channel, error_msg))
            logging.error(f"清除通道{channel}失败: {error_msg}")
    
    def closeEvent(self, event):
        """窗口关闭事件处理"""
        logging.info("应用程序开始关闭...")
        try:
            # 保存当前设置
            settings.save()
            logging.info("设置已保存")
            
            # 断开设备连接
            if self.ble_manager.is_connected:
                asyncio.create_task(self.ble_manager.disconnect())
                logging.info("已发送设备断开连接命令")
            
            # 断开服务器连接
            if self.socket_manager.is_connected:
                self.socket_manager.disconnect()
                logging.info("已断开服务器连接")
            
            # 关闭日志窗口
            if self.log_window:
                self.log_window.close()
                logging.info("日志窗口已关闭")
                
            logging.info("应用程序正常关闭")
        except Exception as e:
            logging.error(f"应用程序关闭时发生错误: {str(e)}")
        finally:
            event.accept()