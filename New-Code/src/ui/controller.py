from qasync import asyncSlot
import logging
import asyncio
from utils.i18n import i18n

class Controller:
    """应用控制器，处理业务逻辑"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.ble_manager = main_window.ble_manager
        self.socket_manager = main_window.socket_manager
        self.signals = main_window.signals
        
        # 设置信号连接
        self.setup_connections()
        
    def setup_connections(self):
        """设置信号连接"""
        # 波形数据更新处理
        self.signals.wave_data_updated.connect(self.on_wave_data_updated)
        
        # 设备ID更新处理
        self.signals.device_id_updated.connect(self.on_device_id_updated)
        
        # 状态更新处理
        self.signals.status_update.connect(self.on_status_update)
        
        # 添加定时器，定期检查连接状态
        from PySide6.QtCore import QTimer
        self.connection_check_timer = QTimer()
        self.connection_check_timer.timeout.connect(self.check_connection_status)
        self.connection_check_timer.start(30000)  # 每30秒检查一次
    
    def on_wave_data_updated(self, data_dict):
        """处理波形数据更新
        
        Args:
            data_dict: 包含通道和数据的字典
        """
        # 记录日志
        channel = data_dict.get('channel')
        data = data_dict.get('data')
        if channel and data:
            logging.info(f"波形数据更新: 通道{channel}, 数据长度={len(data)}")  # 改为INFO级别，只输出数据长度
        
    def on_device_id_updated(self, device_id):
        """处理设备ID更新
        
        Args:
            device_id: 设备ID
        """
        logging.info(f"设备ID更新: {device_id}")
        
    def on_status_update(self, status_dict):
        """处理状态更新
        
        Args:
            status_dict: 状态信息字典
        """
        logging.info(f"状态更新: {status_dict}")  # 改为INFO级别
        
    @asyncSlot()
    async def disconnect_all(self):
        """断开所有连接"""
        # 断开蓝牙连接
        if self.ble_manager.is_connected:
            await self.ble_manager.disconnect()
            self.signals.log_message.emit(i18n.translate("status_updates.bluetooth_disconnected"))
            
        # 断开服务器连接
        if self.socket_manager.ws:
            await self.socket_manager.disconnect()
            self.signals.log_message.emit(i18n.translate("status_updates.server_disconnected"))
            
    def check_connection_status(self):
        """检查并输出连接状态"""
        self.signals.debug_connection_status(self.socket_manager)
        
        # 如果已连接但未绑定，尝试重新发送强度更新
        if (self.socket_manager.ws and self.socket_manager.client_id and 
            not self.socket_manager.target_id):
            logging.info("已连接服务器但未绑定目标，尝试发送广播消息")
            asyncio.create_task(self.socket_manager.send_strength_update())