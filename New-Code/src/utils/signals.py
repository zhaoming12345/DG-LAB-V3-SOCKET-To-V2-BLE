from PySide6.QtCore import QObject, Signal
import logging

class DeviceSignals(QObject):
    """设备信号类，用于跨线程通信"""
    
    # 连接状态变更信号
    connection_changed = Signal(bool)
    
    # 日志消息信号
    log_message = Signal(str)
    
    # 设备ID更新信号
    device_id_updated = Signal(str)
    
    # 状态更新信号
    status_update = Signal(dict)
    
    # 波形数据更新信号
    wave_data_updated = Signal(dict)
    
    # 强度变更信号
    strength_changed = Signal()
    
    # 设备选择信号
    device_selected = Signal(str)
    
    # 电池更新信号
    battery_update = Signal(int)
    
    # 信号强度更新
    signal_update = Signal(int)
    
    # 在DeviceSignals类中添加一个方法来发送日志
    def emit_log(self, message, level="INFO"):
        """发送日志消息
        
        Args:
            message: 日志消息
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        """
        # 记录到Python日志系统
        if level == "DEBUG":
            logging.debug(message)
        elif level == "INFO":
            logging.info(message)
        elif level == "WARNING":
            logging.warning(message)
        elif level == "ERROR":
            logging.error(message)
        else:
            logging.info(message)
            
        # 发送到UI
        self.log_message.emit(message)
    
    def debug_connection_status(self, socket_manager):
        """输出连接状态信息，用于调试"""
        if socket_manager:
            status = {
                "websocket": "已连接" if socket_manager.ws else "未连接",
                "client_id": socket_manager.client_id or "未分配",
                "target_id": socket_manager.target_id or "未绑定",
                "running": "运行中" if socket_manager.running else "已停止"
            }
            
            status_msg = f"连接状态: WebSocket={status['websocket']}, ClientID={status['client_id']}, TargetID={status['target_id']}, 运行状态={status['running']}"
            logging.info(status_msg)
            self.log_message.emit(status_msg)