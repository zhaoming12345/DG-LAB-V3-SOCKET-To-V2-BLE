from qasync import asyncSlot
import logging
from utils.i18n import i18n
from config.settings import settings

class ServerManagerUI:
    """服务器管理UI逻辑"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.socket_manager = main_window.socket_manager
        self.signals = main_window.signals
        self.setup_connections()
        
    def setup_connections(self):
        """设置信号连接"""
        # 保存服务器地址按钮
        self.main_window.server_save_btn.clicked.connect(self.save_server_address)
        # 连接服务器按钮
        self.main_window.server_connect_btn.clicked.connect(self.connect_server)
        
    def save_server_address(self):
        """保存服务器地址"""
        address = self.main_window.server_input.text().strip()
        
        if not address:
            self.signals.log_message.emit(i18n.translate("status_updates.server_address_empty"))
            return
            
        # 验证WebSocket URL格式
        # 要求以ws://或wss://开头
        if not address.startswith(('ws://', 'wss://')):
            address = 'ws://' + address
            logging.info(f"添加ws://前缀: {address}")
            self.main_window.server_input.setText(address)
        
        # 保存到设置
        settings.socket_uri = address
        settings.save()
        
        self.signals.log_message.emit(i18n.translate("status_updates.server_address_saved"))
        logging.info(f"服务器地址已保存: {address}")
        
    @asyncSlot()
    async def connect_server(self):
        """连接到服务器"""
        address = self.main_window.server_input.text().strip()
        
        if not address:
            self.signals.log_message.emit(i18n.translate("status_updates.server_address_empty"))
            logging.warning("尝试连接服务器但地址为空")
            return
            
        # 验证WebSocket URL格式
        if not address.startswith(('ws://', 'wss://')):
            address = 'ws://' + address
            logging.info(f"添加ws://前缀: {address}")
            self.main_window.server_input.setText(address)
        
        # 尝试连接
        self.signals.log_message.emit(i18n.translate("status_updates.connecting_to_server", address))
        logging.info(f"正在连接服务器: {address}")
        
        # 连接到服务器
        success = await self.socket_manager.connect(address)
        
        if success:
            self.signals.log_message.emit(i18n.translate("status_updates.server_connected"))
            logging.info(f"服务器连接成功: {address}")
            # 保存成功的地址
            settings.socket_uri = address
            settings.save()
        else:
            self.signals.log_message.emit(i18n.translate("status_updates.server_connection_failed"))
            logging.error(f"服务器连接失败: {address}")