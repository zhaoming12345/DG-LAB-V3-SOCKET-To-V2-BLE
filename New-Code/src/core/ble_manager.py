import logging
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError
from bleak.backends.scanner import AdvertisementData
from bleak.backends.device import BLEDevice
from config.constants import (
    BLE_SERVICE_UUID, BLE_CHAR_DEVICE_ID, BLE_CHAR_BATTERY,
    BLE_CHAR_PWM_A34, BLE_CHAR_PWM_B34, BLE_CHAR_PWM_AB2
)

class BLEManager:
    def __init__(self, signals):
        self.connected = False
        self.selected_device = None
        self.client = None
        self.signals = signals  # 信号初始化
        self.device_address = None
        self.device_id = None
        self.is_connected = False  # 初始化连接状态属性
        self.has_bluetooth = False  # 添加蓝牙功能状态标志
        
    async def check_bluetooth_available(self):
        """检查系统是否支持蓝牙功能"""
        try:
            # 尝试扫描设备，如果成功则说明蓝牙功能可用
            devices = await BleakScanner.discover(timeout=1.0)  # 使用BleakScanner.discover
            self.has_bluetooth = True
            return True
        except Exception as e:
            self.has_bluetooth = False
            logging.error(f"蓝牙功能检查失败: {str(e)}")
            return False
            
    def is_bluetooth_available(self):
        """获取蓝牙功能状态"""
        return self.has_bluetooth
        
    async def connect(self, address):
        try:
            self.client = BleakClient(address)
            await self.client.connect()
            self.connected = True  # 更新连接状态
            self.is_connected = True  # 同步更新is_connected状态
            self.selected_device = address  # 设置选中设备
            self.device_address = address
            await self.get_device_id()
            self.signals.connection_changed.emit(True)
            return True
        except Exception as e:
            self.connected = False  # 更新连接状态
            self.is_connected = False  # 同步更新is_connected状态
            self.signals.log_message.emit(f"连接失败: {str(e)}")
            return False
            
    async def disconnect(self):
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            self.connected = False  # 更新连接状态
            self.is_connected = False  # 同步更新is_connected状态
            self.selected_device = None  # 清空选中设备
            self.signals.connection_changed.emit(False)
            
    async def get_device_id(self):
        """获取设备ID"""
        if not self.client:  # 添加对client为None的检查
            self.signals.log_message.emit("无法获取设备ID：未连接设备")
            return
            
        try:
            value = await self.client.read_gatt_char(BLE_CHAR_DEVICE_ID)
            self.device_id = value.hex().upper()
            self.signals.device_id_updated.emit(self.device_id)
        except Exception as e:
            self.signals.log_message.emit(f"获取设备ID失败: {str(e)}")
            
    async def send_command(self, char_uuid, data):
        """发送蓝牙命令"""
        if self.client and self.client.is_connected:
            try:
                await self.client.write_gatt_char(char_uuid, data)
                return True
            except Exception as e:
                self.signals.log_message.emit(f"发送命令失败: {str(e)}")
                return False
        return False  # 默认返回False

    async def scan_devices(self):
        """扫描蓝牙设备"""
        try:
            self.signals.log_message.emit("开始扫描蓝牙设备...")
            # 使用BleakScanner.discover而不是discover
            devices = await BleakScanner.discover()
            result = []
            
            for device in devices:
                # 获取设备名称，如果没有则使用地址
                name = device.name or "Unknown Device"
                # 获取设备地址
                address = device.address
                # 获取RSSI信号强度
                rssi = device.rssi
                
                # 构建设备信息字符串
                device_info = f"{name} | {address} | RSSI: {rssi}dB"
                result.append((name, address))
                
                # 发送日志消息
                self.signals.log_message.emit(f"发现设备: {device_info}")
            
            return result
            
        except Exception as e:
            self.signals.log_message.emit(f"扫描设备失败: {str(e)}")
            logging.error(f"扫描设备失败: {str(e)}")
            return []
