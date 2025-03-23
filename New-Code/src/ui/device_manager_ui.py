from PySide6.QtCore import QTimer
from qasync import asyncSlot
import logging
from utils.i18n import i18n
from .device_scanner import DeviceScanner

class DeviceManagerUI:
    """设备管理UI逻辑"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.ble_manager = main_window.ble_manager
        self.signals = main_window.signals
        self.device_scanner = None
        self.setup_connections()
        
    def setup_connections(self):
        """设置信号连接"""
        # 设备扫描按钮
        self.main_window.scan_btn.clicked.connect(self.show_device_scanner)
        # 设备连接按钮
        self.main_window.connect_btn.clicked.connect(self.connect_device)
        # 设备选择信号
        self.signals.device_selected.connect(self.on_device_selected)
        # 连接状态变更信号
        self.signals.connection_changed.connect(self.on_connection_changed)
        
    @asyncSlot()
    async def initialize_bluetooth_check(self):
        """初始化蓝牙检查"""
        try:
            has_bluetooth = await self.ble_manager.check_bluetooth_available()
            if not has_bluetooth:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self.main_window,
                    i18n.translate("error.bluetooth_not_available"),
                    i18n.translate("error.bluetooth_not_available_message")
                )
                self.main_window.scan_btn.setEnabled(False)
                self.main_window.connect_btn.setEnabled(False)
        except Exception as e:
            logging.error(f"蓝牙检查失败: {str(e)}")
            
    def show_device_scanner(self):
        """显示设备扫描对话框"""
        if not self.device_scanner:
            self.device_scanner = DeviceScanner(self.main_window, self.ble_manager)
        self.device_scanner.show()
        # 添加日志记录
        self.signals.log_message.emit(i18n.translate("status_updates.scanning_devices"))
        
    def on_device_selected(self, device_address):
        """处理设备选择事件"""
        if device_address:
            device_name = self.ble_manager.selected_device_name or i18n.translate("device.unknown")
            self.main_window.device_label.setText(f"{device_name} ({device_address})")
            self.signals.log_message.emit(i18n.translate("status_updates.device_selected", device_name))
            
    @asyncSlot()
    async def connect_device(self):
        """连接到选定的设备"""
        if not self.ble_manager.selected_device:
            self.signals.log_message.emit(i18n.translate("status_updates.please_select_device"))
            logging.warning("尝试连接设备但未选择任何设备")
            return
            
        try:
            device_address = self.ble_manager.selected_device
            device_name = self.ble_manager.selected_device_name or "未知设备"
            
            self.signals.log_message.emit(f"正在连接设备: {device_name} ({device_address})")
            logging.info(f"正在连接设备: {device_name} ({device_address})")
            
            self.main_window.device_status.setText(i18n.translate("device.status", i18n.translate("device.connecting")))
            success = await self.ble_manager.connect(device_address)
            
            if success:
                self.main_window.device_status.setText(i18n.translate("device.status", i18n.translate("device.connected")))
                self.signals.log_message.emit(i18n.translate("status_updates.bluetooth_connected"))
                logging.info(f"设备连接成功: {device_name} ({device_address})")
                
                # 立即读取初始状态
                await self.update_battery()
                await self.update_signal_strength()
                
                # 启动定时器
                logging.info("启动电池和信号强度更新定时器")
                self.main_window.battery_update_timer.start()
                self.main_window.signal_update_timer.start()
                
            else:
                self.main_window.device_status.setText(i18n.translate("device.status", i18n.translate("device.disconnected")))
                logging.error(f"设备连接失败: {device_name} ({device_address})")
                
        except Exception as e:
            self.signals.log_message.emit(i18n.translate("status_updates.connection_failed", str(e)))
            self.main_window.device_status.setText(i18n.translate("device.status", i18n.translate("device.disconnected")))
            logging.error(f"设备连接异常: {str(e)}")
            
    @asyncSlot()
    async def update_battery(self):
        """更新电池电量"""
        try:
            if self.ble_manager.is_connected:
                battery_level = await self.ble_manager.read_battery()
                if battery_level is not None:
                    self.main_window.battery_status.setText(i18n.translate("status.battery", battery_level))
                    self.signals.battery_update.emit(battery_level)
                    # 确保保存到BLEManager属性
                    self.ble_manager.battery_level = battery_level
        except Exception as e:
            self.signals.log_message.emit(i18n.translate("status_updates.battery_read_failed", str(e)))
            
    @asyncSlot()
    async def update_signal_strength(self):
        """更新信号强度
        
        从设备读取当前信号强度并更新UI显示。
        信号强度范围通常在 -100 到 0 之间，单位为 dBm：
        - 大于 -50：信号极好
        - -50 到 -65：信号良好
        - -65 到 -75：信号一般
        - -75 到 -85：信号较弱
        - 小于 -85：信号很弱
        """
        if not self.ble_manager.is_connected:
            self.main_window.signal_status.setText(i18n.translate("status.signal_unknown"))
            return
            
        try:
            logging.debug(f"开始获取设备 {self.ble_manager.device_address} 的信号强度")
            signal_strength = await self.ble_manager.read_signal_strength()
            
            if signal_strength is None:
                # 如果无法获取信号强度，显示未知状态
                self.main_window.signal_status.setText(i18n.translate("status.signal_unknown"))
                return
                
            # 保存到BLEManager属性
            self.ble_manager.signal_strength = signal_strength
            logging.debug(f"成功获取信号强度: {signal_strength} dBm")
                
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
            
            # 更新UI显示
            self.main_window.signal_status.setText(f"{status_text} ({signal_strength} dBm)")
            self.signals.signal_update.emit(signal_strength)
            logging.debug(f"信号强度更新: {signal_strength} dBm, 状态: {status_text}")
            
        except Exception as e:
            # 发生错误时，显示未知状态
            self.main_window.signal_status.setText(i18n.translate("status.signal_unknown"))
            logging.error(f"读取信号强度失败: {str(e)}")
            # 只在真正的错误情况下发送错误消息
            self.signals.log_message.emit(i18n.translate("status_updates.signal_read_failed", str(e)))
            
    def on_connection_changed(self, connected):
        """处理连接状态变更"""
        if connected:
            self.main_window.device_status.setText(i18n.translate("device.status", i18n.translate("device.connected")))
            # 连接成功后立即更新一次状态
            QTimer.singleShot(0, self.update_battery)
            QTimer.singleShot(0, self.update_signal_strength)
            
            # 确保定时器在连接状态下运行
            if not self.main_window.battery_update_timer.isActive():
                logging.info("重新启动电池更新定时器")
                self.main_window.battery_update_timer.start()
            if not self.main_window.signal_update_timer.isActive():
                logging.info("重新启动信号强度更新定时器")
                self.main_window.signal_update_timer.start()
        else:
            self.main_window.device_status.setText(i18n.translate("device.status", i18n.translate("device.disconnected")))
            # 更新信号状态为未知
            self.main_window.signal_status.setText(i18n.translate("status.signal_unknown"))
            self.main_window.battery_status.setText(i18n.translate("status.battery", "--"))
            
            # 停止定时器
            if self.main_window.battery_update_timer.isActive():
                logging.info("停止电池更新定时器")
                self.main_window.battery_update_timer.stop()
            if self.main_window.signal_update_timer.isActive():
                logging.info("停止信号强度更新定时器")
                self.main_window.signal_update_timer.stop()