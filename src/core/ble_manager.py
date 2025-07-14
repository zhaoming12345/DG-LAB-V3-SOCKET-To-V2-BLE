import logging
import asyncio
import pydglab

class BLEManager:
    def __init__(self, signals):
        """初始化BLE管理器
        
        Args:
            signals (DeviceSignals): 信号对象，用于UI通信
        """
        self.signals = signals
        self.driver = None  # DGLAB驱动实例
        self.is_connected = False  # 是否已连接属性
        self.device_address = None  # 设备蓝牙MAC地址属性

    async def send_command(self, channel, strength_value):
        """发送命令到BLE设备
        
        Args:
            channel (int): 通道号(1=A, 2=B)
            strength_type (int): 强度类型(1=频率, 2=强度)
            strength_value (int): 强度值(0-100)
            
        Returns:
            bool: 命令是否发送成功
        """
        if not self.is_connected or not self.driver:
            self.signals.log_message.emit("设备未连接")
            logging.error("发送命令失败: 设备未连接")
            return False
            
        try:
            # 使用DGLAB驱动发送命令
            if channel == 1:  # A通道
                await self.driver.set_strength_sync(strength_value, 0)
            else:  # B通道
                await self.driver.set_strength_sync(0, strength_value)
                
            self.signals.log_message.emit(f"命令发送成功 (通道: {channel})")
            return True
        except Exception as e:
            self.signals.log_message.emit(f"命令发送失败: {str(e)}")
            logging.error(f"命令发送失败: {str(e)}")
            return False

    async def connect(self, address):
        """连接到指定地址的蓝牙设备
        
        Args:
            address (str): 设备MAC地址
            
        Returns:
            bool: 连接是否成功
        """
        try:
            self.signals.log_message.emit(f"正在连接蓝牙设备: {address}")
            logging.info(f"正在连接蓝牙设备: {address}")
            
            # 使用DGLAB驱动连接
            self.driver = dglab_v3(address)
            await self.driver.create()
            self.is_connected = True
            self.device_address = address
            
            self.signals.log_message.emit(f"蓝牙设备连接成功: {address}")
            logging.info(f"蓝牙设备连接成功: {address}")
            self.signals.connection_changed.emit(True)
            return True
        except Exception as e:
            self.is_connected = False
            self.driver = None
            self.device_address = None
            self.signals.log_message.emit(f"蓝牙设备连接失败: {str(e)}")
            logging.error(f"蓝牙设备连接失败: {address}, 错误={str(e)}")
            self.signals.connection_changed.emit(False)
            return False
            
    async def disconnect(self):
        """断开蓝牙设备连接"""
        if self.driver and self.is_connected:
            try:
                await self.driver.close()
            except Exception as e:
                logging.error(f"断开设备连接时发生错误: {str(e)}")
            finally:
                self.is_connected = False
                self.driver = None
                self.device_address = None
                self.signals.connection_changed.emit(False)

    async def send_strength_command(self, channel, strength_type, strength_value):
        """发送强度命令到设备
        
        Args:
            channel (int): 通道号(1=A, 2=B)
            strength_type (int): 强度类型(1=频率, 2=强度)
            strength_value (int): 强度值(0-100)
            
        Returns:
            bool: 命令是否发送成功
        """
        try:
            # 确保强度值在有效范围内
            strength_value = max(0, min(100, strength_value))
            
            # 使用PWM_AB2特征值发送强度命令
            if channel == 1:  # A通道
                self.current_strength['A'] = strength_value
                data = ProtocolConverter.encode_pwm_ab2(strength_value, self.current_strength['B'])
            else:  # B通道
                self.current_strength['B'] = strength_value
                data = ProtocolConverter.encode_pwm_ab2(self.current_strength['A'], strength_value)
                
            # 发送命令
            return await self.send_command(BLE_CHAR_PWM_AB2, data)
        except Exception as e:
            self.signals.log_message.emit(f"发送强度命令失败: {str(e)}")
            logging.error(f"发送强度命令失败: {str(e)}")
            return False

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
            self.signals.status_update.emit({channel: str(value)})
            
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
        
    async def get_device_id(self):
        """获取设备ID"""
        if not self.client or not self.client.is_connected:  # 更完善的检查
            self.signals.log_message.emit("无法获取设备ID：未连接设备")
            return
            
        try:
            # 确保client不为None后再调用read_gatt_char方法
            value = None  # 初始化value变量
            if self.client is not None:
                value = await self.client.read_gatt_char(BLE_CHAR_DEVICE_ID)
                self.device_id = value.hex().upper()
            else:
                self.signals.log_message.emit("无法获取设备ID：客户端未初始化")
                return
            # 确保信号正确发送
            if hasattr(self.signals, 'device_id_updated'):
                self.signals.device_id_updated.emit(self.device_id)
                self.signals.log_message.emit(f"设备ID: {self.device_id}")
            else:
                self.signals.log_message.emit(f"设备ID: {self.device_id} (无法通过信号更新)")
        except Exception as e:
            self.signals.log_message.emit(f"获取设备ID失败: {str(e)}")
            
    async def read_battery(self):
        """读取电池电量
        
        Returns:
            int: 电池电量百分比，如果读取失败则返回None
        """
        if not self.is_connected or not self.client:
            return None
            
        try:
            # 尝试读取电池电量特征值
            battery_data = await self.client.read_gatt_char(BLE_CHAR_BATTERY)
            if battery_data:
                battery_level = int(battery_data[0])
                self.battery_level = battery_level  # 保存电池电量
                return battery_level
            return None
        except Exception as e:
            logging.error(f"读取电池电量失败: {str(e)}")
            return None
    
    async def read_signal_strength(self):
        """读取信号强度
        
        Returns:
            int: 信号强度(dBm)，如果读取失败则返回None
        """
        if not self.is_connected or not self.client:
            return None
            
        try:
            # 尝试获取信号强度
            rssi = None
            # BleakClient没有直接的rssi属性，所以我们直接使用扫描方式获取
            
            if rssi is not None:
                self.signal_strength = rssi
                logging.debug(f"获取到设备 {self.device_address} 的信号强度: {rssi} dBm")
                return rssi
            
            # 如果client没有rssi属性，尝试使用BleakScanner获取
            scanner = BleakScanner()
            await scanner.start()
            await asyncio.sleep(1.0)  # 减少扫描时间以提高响应速度
            
            # 停止扫描并获取结果
            devices = await scanner.get_discovered_devices()
            await scanner.stop()
            
            # 查找匹配的设备
            for device in devices:
                if self.device_address and device.address and device.address.upper() == self.device_address.upper():
                    self.signal_strength = device.rssi
                    logging.debug(f"通过扫描获取到设备 {self.device_address} 的信号强度: {device.rssi} dBm")
                    return device.rssi
            
            # 如果没有找到设备
            logging.warning(f"无法获取设备 {self.device_address} 的信号强度")
            return None
        except Exception as e:
            logging.error(f"读取信号强度失败: {str(e)}")
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
                self.signals.status_update.emit({channel: str(strength)})
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
                self.signals.status_update.emit({'A': str(a_strength), 'B': str(b_strength)})
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

    async def set_strength(self, channel, strength):
        """设置通道强度
        
        Args:
            channel (str): 通道标识('A'或'B')
            strength (int): 强度值(0-100)
            
        Returns:
            bool: 操作是否成功
        """
        if not self.is_connected:
            logging.warning("尝试设置强度但设备未连接")
            return False
            
        try:
            # 验证强度范围
            max_strength = self.max_strength[channel]
            if strength < 0 or strength > max_strength:
                logging.warning(f"强度值超出范围: {strength}, 最大值: {max_strength}")
                return False
                
            # 更新当前强度属性
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
                self.signals.status_update.emit({channel: str(strength)})
                # 发送强度变更信号
                self.signals.strength_changed.emit()
                
            return success
            
        except Exception as e:
            self.signals.log_message.emit(f"设置通道强度失败: {str(e)}")
            logging.error(f"设置通道强度失败: {str(e)}")
            return False
            
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
        if not self.is_connected:
            self.signals.log_message.emit("设备未连接")
            return
            
        try:
            # 获取当前强度和限制
            current = self.current_strength[channel]
            max_strength = self.max_strength[channel]
            new_strength = current + delta
            
            # 验证并设置新强度
            if 0 <= new_strength <= max_strength:
                # 发送强度调整命令
                await self.set_strength(channel, new_strength)
                # 发送状态更新消息
                self.signals.log_message.emit(f"通道{channel}强度已调整：{current} -> {new_strength}")
                logging.info(f"通道{channel}强度已调整：{current} -> {new_strength}")
        except Exception as e:
            # 错误处理
            error_msg = str(e)
            self.signals.log_message.emit(f"调整通道{channel}强度失败: {error_msg}")
            logging.error(f"调整通道{channel}强度失败: {error_msg}")

    async def clear_channel(self, channel):
        """清空指定通道的波形队列
        
        Args:
            channel (str): 通道标识('A'或'B')
            
        Returns:
            bool: 操作是否成功
        """
        if not self.is_connected or not self.client:
            self.signals.log_message.emit("设备未连接，无法清空波形队列")
            return False
            
        try:
            # 根据通道选择特征值UUID
            char_uuid = BLE_CHAR_PWM_A34 if channel == 'A' else BLE_CHAR_PWM_B34
            
            # 发送空波形数据来清空队列
            # 使用x=1, y=1, z=0的参数，表示停止输出
            data = ProtocolConverter.encode_pwm_channel(1, 1, 0)
            await self.send_command(char_uuid, data)
            
            self.signals.log_message.emit(f"通道{channel}波形队列已清空")
            return True
        except Exception as e:
            self.signals.log_message.emit(f"清空通道{channel}波形队列失败: {str(e)}")
            logging.error(f"清空通道{channel}波形队列失败: {str(e)}")
            return False
