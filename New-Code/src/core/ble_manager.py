import logging
import struct
import asyncio  # 添加asyncio导入
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError
from bleak.backends.scanner import AdvertisementData
from bleak.backends.device import BLEDevice
from config.constants import (
    BLE_SERVICE_UUID, BLE_CHAR_DEVICE_ID, BLE_CHAR_BATTERY,
    BLE_CHAR_PWM_A34, BLE_CHAR_PWM_B34, BLE_CHAR_PWM_AB2,
    DEFAULT_MAX_STRENGTH
)
from core.protocol import ProtocolConverter

class BLEManager:
    def __init__(self, signals):
        """初始化BLE管理器
        
        Args:
            signals: 信号对象，用于跨线程通信
        """
        self.signals = signals
        self.device = None
        self.is_connected = False
        self.device_id = None
        self.current_strength = {'A': 0, 'B': 0}  # 当前强度
        
        # 从settings加载最大强度值
        from config.settings import settings
        self.max_strength = {
            'A': settings.max_strength_a,
            'B': settings.max_strength_b
        }
        
        logging.info(f"BLEManager初始化，最大强度: A={self.max_strength['A']}, B={self.max_strength['B']}")
    async def send_command(self, char_uuid, data):
        """发送蓝牙命令的核心方法
        Args:
            char_uuid: 蓝牙特征值UUID 
            data: 要发送的字节数据
        Returns:
            bool: 命令是否发送成功
        """
        # 使用Bleak的write_gatt_char方法进行低功耗蓝牙数据写入
        if not hasattr(self, 'client') or not self.client or not self.client.is_connected:
            self.signals.log_message.emit("发送蓝牙命令失败: 设备未连接")
            logging.warning("尝试发送蓝牙命令但设备未连接")
            return False
            
        try:
            # 增加更详细的日志，包括数据内容的十六进制表示
            hex_data = data.hex().upper()
            self.signals.log_message.emit(f"发送蓝牙命令: 特征值={char_uuid}, 数据={hex_data}")
            logging.info(f"发送蓝牙命令: 特征值={char_uuid}, 数据={hex_data}")
            
            await self.client.write_gatt_char(char_uuid, data)
            self.signals.log_message.emit(f"蓝牙命令发送成功: {char_uuid}")
            return True
        except Exception as e:
            self.signals.log_message.emit(f"发送蓝牙命令失败: {str(e)}")
            logging.error(f"发送蓝牙命令失败: 特征值={char_uuid}, 错误={str(e)}")
            return False

    async def connect(self, address):
        try:
            self.signals.log_message.emit(f"正在连接蓝牙设备: {address}")
            logging.info(f"正在连接蓝牙设备: {address}")
            
            self.client = BleakClient(address)
            await self.client.connect()
            self.connected = True  # 更新连接状态
            self.is_connected = True  # 同步更新is_connected状态
            self.selected_device = address  # 设置选中设备
            self.device_address = address
            
            self.signals.log_message.emit(f"蓝牙设备连接成功: {address}")
            logging.info(f"蓝牙设备连接成功: {address}")
            
            await self.get_device_id()
            self.signals.connection_changed.emit(True)
            return True
        except Exception as e:
            self.connected = False  # 更新连接状态
            self.is_connected = False  # 同步更新is_connected状态
            self.signals.log_message.emit(f"蓝牙设备连接失败: {str(e)}")
            logging.error(f"蓝牙设备连接失败: {address}, 错误={str(e)}")
            # 确保发送连接状态变更信号
            self.signals.connection_changed.emit(False)
            return False

    async def send_strength_command(self, channel_num, mode, value):
        """发送强度调整命令
        
        Args:
            channel_num: 通道号(1=A, 2=B)
            mode: 模式(0=减少, 1=增加, 2=设置)
            value: 强度值
        """
        ch = 'A' if channel_num == 1 else 'B'
        try:
            # 获取当前强度
            current = self.current_strength[ch]
            
            # 根据模式计算新强度
            if mode == 0:   # 减少强度
                new = max(0, current - value)
            elif mode == 1: # 增加强度
                new = min(self.max_strength[ch], current + value)
            elif mode == 2: # 设置为指定值
                new = min(self.max_strength[ch], max(0, value))
            else:
                return
                
            # 确保强度在有效范围内
            new = max(0, min(new, self.max_strength[ch]))
            
            # 保存旧值用于比较
            old_value = current
            
            # 更新当前强度
            self.current_strength[ch] = new
            self.signals.log_message.emit(f"通道{ch}强度更新为: {new}")
            
            # 编码并发送命令
            data = ProtocolConverter.encode_pwm_ab2(
                self.current_strength['A'], 
                self.current_strength['B']
            )
            await self.send_command(BLE_CHAR_PWM_AB2, data)
            
            # 更新UI状态
            self.signals.status_update.emit(ch, str(new))
            
            # 发送强度变更信号
            self.signals.strength_changed.emit()
            
        except Exception as e:
            self.signals.log_message.emit(f"调整强度失败: {str(e)}")
            logging.error(f"调整强度失败: {str(e)}")

    async def update_max_strength(self, channel, value):
        """更新通道最大强度
        
        Args:
            channel (str): 通道标识('A'或'B')
            value (int): 最大强度值(0-200)
        """
        if channel not in ['A', 'B'] or not (0 <= value <= 200):
            self.signals.log_message.emit(f"无效的最大强度参数: 通道={channel}, 值={value}")
            return
            
        # 更新最大强度
        self.max_strength[channel] = value
        self.signals.log_message.emit(f"通道{channel}最大强度更新为: {value}")
        
        # 如果当前强度超过新的最大强度，则调整当前强度
        if self.current_strength[channel] > value:
            self.current_strength[channel] = value
            self.signals.log_message.emit(f"通道{channel}当前强度已调整为最大值: {value}")
            
            # 更新UI状态
            self.signals.status_update.emit(channel, str(value))
            
            # 发送强度变更信号
            self.signals.strength_changed.emit()

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
            # 确保发送连接状态变更信号
            self.signals.connection_changed.emit(False)
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
        if not self.client or not self.client.is_connected:  # 更完善的检查
            self.signals.log_message.emit("无法获取设备ID：未连接设备")
            return
            
        try:
            value = await self.client.read_gatt_char(BLE_CHAR_DEVICE_ID)
            self.device_id = value.hex().upper()
            # 确保信号正确发送
            if hasattr(self.signals, 'device_id_updated'):
                self.signals.device_id_updated.emit(self.device_id)
                self.signals.log_message.emit(f"设备ID: {self.device_id}")
            else:
                self.signals.log_message.emit(f"设备ID: {self.device_id} (无法通过信号更新)")
        except Exception as e:
            self.signals.log_message.emit(f"获取设备ID失败: {str(e)}")
            
    async def read_battery(self):
        """读取电池电量"""
        try:
            value = await self.client.read_gatt_char(BLE_CHAR_BATTERY)
            battery_level = int.from_bytes(value, byteorder='little')
            return battery_level
        except Exception as e:
            self.signals.log_message.emit(f"读取电池电量失败: {str(e)}")
            return None

    async def read_signal_strength(self):
        """读取当前连接设备的信号强度"""
        try:
            if not self.client or not self.client.is_connected:
                return None
                
            # 在某些平台上，可以直接从客户端获取RSSI
            if hasattr(self.client, 'get_rssi'):
                rssi = await self.client.get_rssi()
                return rssi
                
            # 如果客户端没有直接提供RSSI方法，尝试通过扫描获取
            # 注意：这种方法效率较低，因为需要重新扫描
            scanner = BleakScanner()
            await scanner.start()
            await asyncio.sleep(1.0)  # 扫描1秒
            await scanner.stop()
            
            for device in scanner.discovered_devices:
                if device.address == self.device_address:
                    return device.rssi
                    
            return None
        except Exception as e:
            self.signals.log_message.emit(f"读取信号强度失败: {str(e)}")
            return None
            
    async def scan_devices(self):
        """扫描可用的蓝牙设备
        
        Returns:
            list: 设备列表，每个元素为(name, address)元组
        """
        try:
            # 记录开始扫描的日志
            self.signals.log_message.emit("开始扫描蓝牙设备...")
            logging.info("开始扫描蓝牙设备")
            
            devices = await BleakScanner.discover()
            result = []
            
            for device in devices:
                name = device.name or "未知设备"
                address = device.address
                result.append((name, address))
                logging.debug(f"发现设备: {name} ({address})")
                
            # 记录扫描结果的日志
            self.signals.log_message.emit(f"扫描完成，发现 {len(result)} 个设备")
            logging.info(f"蓝牙扫描完成，发现 {len(result)} 个设备")
            
            # 详细记录每个发现的设备
            if result:
                device_list = "\n".join([f"- {name} ({addr})" for name, addr in result])
                logging.debug(f"发现的设备列表:\n{device_list}")
                
            return result
        except Exception as e:
            self.signals.log_message.emit(f"扫描设备失败: {str(e)}")
            logging.error(f"扫描蓝牙设备失败: {str(e)}")
            return []

    async def set_channel_strength(self, channel, strength):
        """设置通道强度
        
        Args:
            channel (str): 通道标识('A'或'B')
            strength (int): 强度值(0-100)
            
        Returns:
            bool: 命令是否发送成功
        """
        try:
            if channel not in ['A', 'B']:
                self.signals.log_message.emit(f"无效的通道: {channel}")
                return False
                
            # 确保强度在有效范围内
            strength = max(0, min(self.max_strength[channel], strength))
            
            # 更新当前强度
            self.current_strength[channel] = strength
            
            # 编码并发送命令
            data = ProtocolConverter.encode_pwm_ab2(
                self.current_strength['A'], 
                self.current_strength['B']
            )
            success = await self.send_command(BLE_CHAR_PWM_AB2, data)
            
            if success:
                self.signals.log_message.emit(f"已设置{channel}通道强度为{strength}")
                # 更新UI状态
                self.signals.status_update.emit(channel, str(strength))
                # 发送强度变更信号
                self.signals.strength_changed.emit()
                
            return success
            
        except Exception as e:
            self.signals.log_message.emit(f"设置通道强度失败: {str(e)}")
            logging.error(f"设置通道强度失败: {str(e)}")
            return False
            
    async def get_current_strength(self, channel):
        """获取通道当前强度
        
        Args:
            channel (str): 通道标识('A'或'B')
            
        Returns:
            int: 当前强度值
        """
        if channel not in ['A', 'B']:
            self.signals.log_message.emit(f"无效的通道: {channel}")
            return 0
            
        return self.current_strength[channel]
        
    async def get_max_strength(self, channel):
        """获取通道最大强度
        
        Args:
            channel (str): 通道标识('A'或'B')
            
        Returns:
            int: 最大强度值
        """
        if channel not in ['A', 'B']:
            self.signals.log_message.emit(f"无效的通道: {channel}")
            return DEFAULT_MAX_STRENGTH
            
        return self.max_strength[channel]
        
    async def send_custom_wave(self, channel, freq_list, intensity_list):
        """发送自定义波形
        
        Args:
            channel (str): 通道标识('A'或'B')
            freq_list (list): 频率列表，每项为10-1000的整数
            intensity_list (list): 强度列表，每项为0-100的整数
            
        Returns:
            bool: 命令是否发送成功
        """
        try:
            if channel not in ['A', 'B']:
                self.signals.log_message.emit(f"无效的通道: {channel}")
                return False
                
            # 确保列表长度相同
            if len(freq_list) != len(intensity_list):
                self.signals.log_message.emit("频率列表和强度列表长度必须相同")
                return False
                
            # 根据通道选择特征值UUID
            char_uuid = BLE_CHAR_PWM_A34 if channel == 'A' else BLE_CHAR_PWM_B34
            
            # 处理每组波形参数
            for i in range(len(freq_list)):
                freq = freq_list[i]
                intensity = intensity_list[i]
                
                # 确保参数在有效范围内
                freq = max(10, min(1000, freq))
                intensity = max(0, min(self.max_strength[channel], intensity))
                
                # 跳过强度为0的部分
                if intensity == 0:
                    continue
                    
                # 将频率转换为V2协议的x和y参数
                x, y = ProtocolConverter.v3_freq_to_v2(freq)
                
                # 将强度转换为V2协议的z参数
                z = ProtocolConverter.v3_intensity_to_v2_z(intensity)
                
                # 编码并发送命令
                data = ProtocolConverter.encode_pwm_channel(x, y, z)
                success = await self.send_command(char_uuid, data)
                
                if not success:
                    self.signals.log_message.emit(f"发送波形参数失败: 频率={freq}, 强度={intensity}")
                    return False
                    
                # 短暂延迟，确保命令能被设备处理
                await asyncio.sleep(0.05)
                
            self.signals.log_message.emit(f"已发送自定义波形到{channel}通道")
            return True
            
        except Exception as e:
            self.signals.log_message.emit(f"发送自定义波形失败: {str(e)}")
            logging.error(f"发送自定义波形失败: {str(e)}")
            return False
            
    async def set_both_channels_strength(self, a_strength, b_strength):
        """同时设置两个通道的强度
        
        Args:
            a_strength (int): A通道强度值(0-100)
            b_strength (int): B通道强度值(0-100)
            
        Returns:
            bool: 命令是否发送成功
        """
        try:
            # 确保强度在有效范围内
            a_strength = max(0, min(self.max_strength['A'], a_strength))
            b_strength = max(0, min(self.max_strength['B'], b_strength))
            
            # 更新当前强度
            self.current_strength['A'] = a_strength
            self.current_strength['B'] = b_strength
            
            # 编码并发送命令
            data = ProtocolConverter.encode_pwm_ab2(a_strength, b_strength)
            success = await self.send_command(BLE_CHAR_PWM_AB2, data)
            
            if success:
                self.signals.log_message.emit(f"已设置A通道强度为{a_strength}，B通道强度为{b_strength}")
                # 更新UI状态
                self.signals.status_update.emit('A', str(a_strength))
                self.signals.status_update.emit('B', str(b_strength))
                # 发送强度变更信号
                self.signals.strength_changed.emit()
                
            return success
            
        except Exception as e:
            self.signals.log_message.emit(f"设置通道强度失败: {str(e)}")
            logging.error(f"设置通道强度失败: {str(e)}")
            return False
            
    async def reset_device(self):
        """重置设备状态
        
        将所有通道强度设置为0，清空波形队列
        
        Returns:
            bool: 命令是否发送成功
        """
        try:
            # 设置所有通道强度为0
            success1 = await self.set_both_channels_strength(0, 0)
            
            # 清空A通道波形队列
            success2 = await self.clear_channel('A')
            
            # 清空B通道波形队列
            success3 = await self.clear_channel('B')
            
            if success1 and success2 and success3:
                self.signals.log_message.emit("设备已重置")
                return True
            else:
                self.signals.log_message.emit("设备重置部分失败")
                return False
                
        except Exception as e:
            self.signals.log_message.emit(f"重置设备失败: {str(e)}")
            logging.error(f"重置设备失败: {str(e)}")
            return False
            
    async def get_device_info(self):
        """获取设备信息
        
        Returns:
            dict: 设备信息字典
        """
        try:
            # 获取设备ID
            if not self.device_id:
                await self.get_device_id()
                
            # 获取电池电量
            battery = await self.read_battery()
            
            # 获取信号强度
            rssi = await self.read_signal_strength()
            
            # 组装设备信息
            device_info = {
                'device_id': self.device_id,
                'battery': battery,
                'rssi': rssi,
                'connected': self.is_connected,
                'address': getattr(self, 'device_address', None),
                'current_strength': self.current_strength,
                'max_strength': self.max_strength
            }
            
            return device_info
            
        except Exception as e:
            self.signals.log_message.emit(f"获取设备信息失败: {str(e)}")
            logging.error(f"获取设备信息失败: {str(e)}")
            return {
                'device_id': self.device_id,
                'connected': self.is_connected,
                'error': str(e)
            }
