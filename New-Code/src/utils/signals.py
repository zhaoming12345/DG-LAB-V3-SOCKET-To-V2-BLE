from PySide6.QtCore import QObject, Signal

class DeviceSignals(QObject):
    """设备信号类，用于在不同组件间传递信号"""
    
    # 日志消息信号
    log_message = Signal(str)
    
    # 设备选择信号
    device_selected = Signal(str)
    
    # 连接状态变化信号
    connection_changed = Signal(bool)
    
    # 通道状态更新信号 (通道, 强度值)
    status_update = Signal(str, int)
    
    # 电池状态更新信号
    battery_update = Signal(int)
    
    # 信号强度更新信号
    signal_update = Signal(int)