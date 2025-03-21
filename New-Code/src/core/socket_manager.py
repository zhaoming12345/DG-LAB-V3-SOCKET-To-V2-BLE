import asyncio
import json
import websockets
import re
import logging
from config.settings import settings
from core.protocol import ProtocolConverter
from config.constants import BLE_CHAR_PWM_A34, BLE_CHAR_PWM_B34, BLE_CHAR_PWM_AB2

class SocketManager:
    def __init__(self, signals, ble_manager):
        self.signals = signals
        self.ble_manager = ble_manager
        self.ws = None
        self.running = False
        self.client_id = None  # 存储当前终端ID
        self.target_id = None  # 存储目标APP ID
        # 添加通道强度状态跟踪
        self.channel_intensity = {'A': 0, 'B': 0}  # A通道和B通道的当前强度
        
        # 从设置中加载最大强度值
        self.max_strength = {
            'A': settings.max_strength_a, 
            'B': settings.max_strength_b
        }
        
        # 记录初始化的最大强度值
        logging.info(f"SocketManager初始化，最大强度: A={self.max_strength['A']}, B={self.max_strength['B']}")
    
    async def connect(self, uri=None):
        """连接到WebSocket服务器
        
        Args:
            uri: 可选的WebSocket URI，如果不提供则使用settings中的配置
            
        Returns:
            bool: 连接是否成功
        """
        # 使用提供的URI或从设置中获取
        socket_uri = uri if uri else settings.socket_uri
        
        if not socket_uri:
            self.signals.log_message.emit("WebSocket地址未设置")
            return False
            
        try:
            self.signals.log_message.emit(f"正在连接到WebSocket服务器: {socket_uri}")
            self.ws = await websockets.connect(socket_uri)
            self.running = True
            asyncio.create_task(self._listen())
            self.signals.log_message.emit("WebSocket连接成功")
            self.signals.log_message.emit("服务器已连接")
            return True
        except Exception as e:
            self.signals.log_message.emit(f"WebSocket连接失败: {str(e)}")
            return False
            
    async def disconnect(self):
        """断开WebSocket连接"""
        self.running = False
        if self.ws:
            await self.ws.close()
            self.ws = None
            self.client_id = None
            self.target_id = None
            
    async def _listen(self):
        """监听WebSocket消息"""
        while self.running and self.ws:
            try:
                message = await self.ws.recv()
                await self._handle_message(message)
            except websockets.ConnectionClosed:
                self.signals.log_message.emit("WebSocket连接已关闭")
                break
            except Exception as e:
                self.signals.log_message.emit(f"WebSocket接收消息错误: {str(e)}")
                
    async def _handle_message(self, message):
        """处理接收到的WebSocket消息
        
        Args:
            message (str): 接收到的JSON消息
        """
        try:
            # 记录接收到的原始消息
            logging.debug(f"收到WebSocket消息原始数据: {message}")
            
            data = json.loads(message)
            
            # 处理不同类型的消息
            if 'type' in data:
                message_type = data['type']
                
                # 对于心跳消息，使用debug级别记录，避免日志过多
                if message_type == 'heartbeat':
                    logging.debug(f"收到心跳消息: {data}")
                else:
                    # 对于其他类型的消息，使用info级别记录
                    msg_info = f"收到WebSocket消息: 类型={message_type}"
                    logging.info(msg_info)
                    self.signals.log_message.emit(msg_info)
                    
                    # 记录更详细的消息内容（对于非心跳消息）
                    if message_type == 'msg' and 'message' in data:
                        msg_content = f"消息内容: {data['message']}"
                        logging.info(msg_content)
                        self.signals.log_message.emit(msg_content)
                
                    # 处理各种类型的消息
                    if message_type == 'hello':
                        await self._handle_hello_message(data)
                    elif message_type == 'command':
                        await self._handle_command_message(data)
                    elif message_type == 'break':
                        await self._handle_break_message(data)
                    elif message_type == 'bind':
                        await self._handle_bind_message(data)
                    elif message_type == 'heartbeat':
                        await self._handle_heartbeat_message(data)
                    elif message_type == 'msg':
                        await self._handle_msg_message(data)
                    else:
                        warning_msg = f"收到未知类型的消息: {message_type}"
                        self.signals.log_message.emit(warning_msg)
                        logging.warning(warning_msg)
            else:
                warning_msg = f"收到无类型的消息: {message}"
                self.signals.log_message.emit(warning_msg)
                logging.warning(warning_msg)
                
        except json.JSONDecodeError:
            error_msg = f"无法解析JSON消息: {message}"
            self.signals.log_message.emit(error_msg)
            logging.error(error_msg)
        except Exception as e:
            error_msg = f"处理消息时出错: {str(e)}"
            self.signals.log_message.emit(error_msg)
            logging.error(error_msg)

    async def _handle_strength_message(self, message):
        """处理强度控制消息
        
        格式1: strength-A通道强度+B通道强度+A强度上限+B强度上限
        例如: strength-50+30+100+100
        
        格式2: strength-通道+强度变化模式+数值
        例如: strength-1+1+5 (A通道强度增加5)
        
        Args:
            message (str): 强度控制消息
        """
        try:
            # 解析消息
            parts = message.replace('strength-', '').split('+')
            
            # 判断消息类型
            if len(parts) >= 3 and parts[0] in ['1', '2'] and parts[1] in ['0', '1', '2']:
                # 格式2: strength-通道+强度变化模式+数值
                channel_num = int(parts[0])
                mode = int(parts[1])
                value = int(parts[2])
                
                # 发送强度命令到蓝牙设备
                await self.ble_manager.send_strength_command(channel_num, mode, value)
                
            elif len(parts) >= 2:
                # 格式1: strength-A通道强度+B通道强度+A强度上限+B强度上限
                a_strength = int(parts[0])
                b_strength = int(parts[1])
                
                # 可选的最大强度值
                a_max = int(parts[2]) if len(parts) > 2 else self.max_strength['A']
                b_max = int(parts[3]) if len(parts) > 3 else self.max_strength['B']
                
                # 更新最大强度值
                if a_max != self.max_strength['A'] or b_max != self.max_strength['B']:
                    self.max_strength['A'] = a_max
                    self.max_strength['B'] = b_max
                    # 同步更新到设置
                    from config.settings import settings
                    settings.max_strength_a = a_max
                    settings.max_strength_b = b_max
                    settings.save()
                    logging.info(f"从服务器更新最大强度: A={a_max}, B={b_max}")
                    
                # 更新当前强度值
                self.channel_intensity['A'] = a_strength
                self.channel_intensity['B'] = b_strength
                
                # 发送到蓝牙设备
                logging.info(f"发送强度到蓝牙设备: A={a_strength}, B={b_strength}")
                
                # 编码并发送命令
                data = ProtocolConverter.encode_pwm_ab2(a_strength, b_strength)
                await self.ble_manager.send_command(BLE_CHAR_PWM_AB2, data)
                
                # 发送强度变更信号
                self.signals.strength_changed.emit()
            else:
                logging.warning(f"强度消息格式不正确: {message}")
                
        except Exception as e:
            self.signals.log_message.emit(f"处理强度消息失败: {str(e)}")
            logging.error(f"处理强度消息失败: {str(e)}")

    async def _handle_wave_message(self, message):
        """处理波形控制消息
        
        格式: wave-通道+波形ID
        例如: wave-A+1
        
        Args:
            message (str): 波形控制消息
        """
        try:
            # 解析消息
            parts = message.replace('wave-', '').split('+')
            if len(parts) >= 2:
                channel = parts[0].upper()  # 'A' 或 'B'
                wave_id = int(parts[1])
                
                logging.info(f"发送波形到蓝牙设备: 通道={channel}, 波形ID={wave_id}")
                
                # 根据通道选择特征值UUID
                char_uuid = BLE_CHAR_PWM_A34 if channel == 'A' else BLE_CHAR_PWM_B34
                
                # 将波形ID转换为x, y, z参数
                # 这里需要根据实际波形定义进行转换
                # 暂时使用默认值
                x, y = ProtocolConverter.v3_freq_to_v2(100)  # 默认频率100Hz
                z = ProtocolConverter.v3_intensity_to_v2_z(50)  # 默认强度50%
                
                # 编码波形数据
                data = ProtocolConverter.encode_pwm_channel(x, y, z)
                
                # 发送到蓝牙设备
                await self.ble_manager.send_command(char_uuid, data)
                
                # 发送波形数据更新信号
                self.signals.wave_data_updated.emit({'channel': channel, 'wave_id': wave_id})
                
        except Exception as e:
            self.signals.log_message.emit(f"处理波形消息失败: {str(e)}")
            logging.error(f"处理波形消息失败: {str(e)}")

    async def _handle_freq_message(self, message):
        """处理频率控制消息
        
        格式: freq-通道+频率值
        例如: freq-A+100
        
        Args:
            message (str): 频率控制消息
        """
        try:
            # 解析消息
            parts = message.replace('freq-', '').split('+')
            if len(parts) >= 2:
                channel = parts[0].upper()  # 'A' 或 'B'
                freq = int(parts[1])
                
                logging.info(f"发送频率到蓝牙设备: 通道={channel}, 频率={freq}Hz")
                
                # 根据通道选择特征值UUID
                char_uuid = BLE_CHAR_PWM_A34 if channel == 'A' else BLE_CHAR_PWM_B34
                
                # 将频率转换为x, y参数
                x, y = ProtocolConverter.v3_freq_to_v2(freq)
                
                # 获取当前强度对应的z参数
                current_strength = self.channel_intensity[channel]
                z = ProtocolConverter.v3_intensity_to_v2_z(current_strength)
                
                # 编码频率数据
                data = ProtocolConverter.encode_pwm_channel(x, y, z)
                
                # 发送到蓝牙设备
                await self.ble_manager.send_command(char_uuid, data)
                
        except Exception as e:
            self.signals.log_message.emit(f"处理频率消息失败: {str(e)}")
            logging.error(f"处理频率消息失败: {str(e)}")

    async def _handle_break_message(self, data):
        """处理break类型的消息，用于停止当前输出
        
        Args:
            data (dict): 消息数据
        """
        try:
            # 停止所有通道输出
            if self.ble_manager and self.ble_manager.is_connected:
                # 发送停止命令到A通道
                x, y = ProtocolConverter.v3_freq_to_v2(50)  # 使用默认频率
                z = 0  # 强度为0表示停止
                command_a = ProtocolConverter.create_v2_command(1, x, y, z)
                await self.ble_manager.send_command(BLE_CHAR_PWM_A34, command_a)
                
                # 发送停止命令到B通道
                command_b = ProtocolConverter.create_v2_command(2, x, y, z)
                await self.ble_manager.send_command(BLE_CHAR_PWM_B34, command_b)
                
                # 更新通道状态
                self.channel_intensity = {1: 0, 2: 0}
                
                # 发送状态更新信号
                self.signals.status_update.emit({'A': 0, 'B': 0})
                
                self.signals.log_message.emit("已停止所有通道输出")
        except Exception as e:
            self.signals.log_message.emit(f"处理break消息失败: {str(e)}")
    
    async def _handle_command_message(self, data):
        """处理command类型的消息
        
        Args:
            data (dict): 消息数据
        """
        try:
            if 'message' in data:
                message = data['message']
                self.signals.log_message.emit(f"收到命令消息: {message}")
                
                # 处理强度操作消息
                if message.startswith("strength-"):
                    await self._handle_strength_message(message)
                # 处理波形操作消息
                elif message.startswith("pulse-"):
                    await self._handle_pulse_message(message)
                # 处理清空波形队列消息
                elif message.startswith("clear-"):
                    await self._handle_clear_message(message)
                else:
                    self.signals.log_message.emit(f"未知数据消息: {message}")
            else:
                self.signals.log_message.emit("command消息中未包含message字段")
        except Exception as e:
            self.signals.log_message.emit(f"处理command消息失败: {str(e)}")
            
    async def _handle_strength_message(self, message):
        """处理强度控制消息"""
        # 记录收到的强度消息
        logging.info(f"处理强度消息: {message}")
        
        # 解析强度消息格式: strength-通道+强度变化模式+数值
        match = re.match(r"strength-(\d)\+(\d)\+(\d+)", message)
        if not match:
            self.signals.log_message.emit(f"无效的强度消息格式: {message}")
            logging.warning(f"无效的强度消息格式: {message}")
            return
            
        channel, mode, value = match.groups()
        channel = int(channel)
        mode = int(mode)
        value = int(value)
        
        # 检查参数有效性
        if channel not in [1, 2] or mode not in [0, 1, 2] or not (0 <= value <= 200):
            self.signals.log_message.emit(f"强度参数无效: 通道={channel}, 模式={mode}, 值={value}")
            logging.warning(f"强度参数无效: 通道={channel}, 模式={mode}, 值={value}")
            return
            
        # 获取通道字母标识
        channel_letter = 'A' if channel == 1 else 'B'
        
        # 计算实际强度值
        current_intensity = self.channel_intensity[channel_letter]
        if mode == 0:  # 减少强度
            new_intensity = max(0, current_intensity - value)
            operation = "减少"
        elif mode == 1:  # 增加强度
            new_intensity = min(self.max_strength[channel_letter], current_intensity + value)
            operation = "增加"
        else:  # mode == 2, 设置为指定值
            new_intensity = min(self.max_strength[channel_letter], max(0, value))
            operation = "设置"
        
        # 记录强度变化
        self.signals.log_message.emit(f"通道{channel_letter}强度{operation}: {current_intensity} -> {new_intensity}")
        logging.info(f"通道{channel_letter}强度{operation}: {current_intensity} -> {new_intensity}")
        
        # 更新本地强度状态
        self.channel_intensity[channel_letter] = new_intensity
        
        # 将更新后的强度值发送回服务器
        await self.send_strength_update()

    async def send_strength_update(self):
        """发送当前强度状态到服务器
        
        根据协议格式: strength-A通道强度+B通道强度+A强度上限+B强度上限
        """
        if not self.ws:
            logging.warning("无法发送强度更新：未连接到服务器")
            return False
            
        if not self.client_id:
            logging.warning("无法发送强度更新：未获取客户端ID")
            return False
        
        try:
            # 构建强度更新消息，按照协议格式
            strength_message = ProtocolConverter.format_strength_message(
                self.channel_intensity['A'],
                self.channel_intensity['B'],
                self.max_strength['A'],
                self.max_strength['B']
            )
            
            # 如果没有目标ID，则发送广播消息
            target_id = self.target_id if self.target_id else ""
            
            message = {
                "type": "msg",
                "clientId": self.client_id,
                "targetId": target_id,
                "message": strength_message
            }
            
            # 发送消息
            await self.ws.send(json.dumps(message))
            logging.info(f"已发送强度更新: {strength_message}")
            return True
        except Exception as e:
            self.signals.log_message.emit(f"发送强度更新失败: {str(e)}")
            logging.error(f"发送强度更新失败: {str(e)}")
            return False

    async def _handle_bind_message(self, data):
        """处理bind类型的消息，用于处理绑定请求
        
        Args:
            data (dict): 消息数据
        """
        try:
            # 处理服务器返回的ID
            if 'message' in data and data['message'] == 'targetId' and 'clientId' in data:
                self.client_id = data['clientId']
                self.signals.log_message.emit(f"收到服务器分配的ID: {self.client_id}")
                logging.info(f"收到服务器分配的ID: {self.client_id}")
                
                # 即使没有目标ID，也可以发送广播消息
                await self.send_strength_update()
                return
                
            # 处理绑定结果
            if 'message' in data and data['message'] == '200' and 'targetId' in data and 'clientId' in data:
                self.client_id = data['clientId']
                self.target_id = data['targetId']
                self.signals.log_message.emit(f"成功绑定: 客户端ID={self.client_id}, 目标ID={self.target_id}")
                logging.info(f"成功绑定: 客户端ID={self.client_id}, 目标ID={self.target_id}")
                
                # 绑定成功后发送当前强度状态
                await self.send_strength_update()
                return
                
            self.signals.log_message.emit(f"收到未处理的bind消息: {data}")
            logging.warning(f"收到未处理的bind消息: {data}")
            
        except Exception as e:
            self.signals.log_message.emit(f"处理bind消息失败: {str(e)}")
            logging.error(f"处理bind消息失败: {str(e)}")

    async def _handle_heartbeat_message(self, data):
        """处理heartbeat类型的消息，用于保持连接
        
        Args:
            data (dict): 消息数据
        """
        try:
            # 心跳消息通常不需要特殊处理，只需回复即可
            if self.ws:
                response = {"type": "heartbeat", "clientId": self.client_id}
                await self.ws.send(json.dumps(response))
                # 不记录日志以避免日志过多
        except Exception as e:
            self.signals.log_message.emit(f"处理heartbeat消息失败: {str(e)}")
    
    async def _handle_msg_message(self, data):
        """处理msg类型的消息，用于处理控制指令
        
        Args:
            data (dict): 消息数据
        """
        try:
            if 'message' not in data:
                return
            
            message = data['message']
            logging.info(f"处理控制消息: {message}")
            
            # 处理强度控制消息
            if message.startswith('strength-'):
                await self._handle_strength_message(message)
            # 处理波形控制消息
            elif message.startswith('wave-'):
                await self._handle_wave_message(message)
            # 处理频率控制消息
            elif message.startswith('freq-'):
                await self._handle_freq_message(message)
            # 处理清空波形队列命令
            elif message.startswith('clear-'):
                await self._handle_clear_message(message)
            # 处理波形数据消息
            elif message.startswith('pulse-'):
                await self._handle_pulse_message(message)
            # 处理其他类型的消息
            else:
                logging.warning(f"未知的控制消息类型: {message}")
                
        except Exception as e:
            self.signals.log_message.emit(f"处理控制消息失败: {str(e)}")
            logging.error(f"处理控制消息失败: {str(e)}")

    async def _handle_strength_message(self, message):
        """处理强度控制消息"""
        # 记录收到的强度消息
        logging.info(f"处理强度消息: {message}")
        
        # 解析强度消息格式: strength-通道+强度变化模式+数值
        match = re.match(r"strength-(\d)\+(\d)\+(\d+)", message)
        if not match:
            self.signals.log_message.emit(f"无效的强度消息格式: {message}")
            return
            
        channel, mode, value = match.groups()
        channel = int(channel)
        mode = int(mode)
        value = int(value)
        
        # 检查参数有效性
        if channel not in [1, 2] or mode not in [0, 1, 2] or not (0 <= value <= 200):
            self.signals.log_message.emit(f"强度参数无效: 通道={channel}, 模式={mode}, 值={value}")
            return
            
        # 获取通道字母标识
        channel_letter = 'A' if channel == 1 else 'B'
        
        # 计算实际强度值
        current_intensity = self.channel_intensity[channel_letter]
        if mode == 0:  # 减少强度
            new_intensity = max(0, current_intensity - value)
        elif mode == 1:  # 增加强度
            new_intensity = min(200, current_intensity + value)
        else:  # mode == 2, 设置为指定值
            new_intensity = min(200, max(0, value))
        
        # 更新本地强度状态
        self.channel_intensity[channel_letter] = new_intensity
        self.signals.log_message.emit(f"通道{channel_letter}强度更新为: {new_intensity}")
        
        # 转换为V2协议并发送到BLE设备
        if self.ble_manager and self.ble_manager.is_connected:
            # 将V3强度值转换为V2的z参数
            z_value = ProtocolConverter.v3_intensity_to_v2_z(new_intensity)
            
            # 根据通道选择特性UUID
            char_uuid = BLE_CHAR_PWM_A34 if channel == 1 else BLE_CHAR_PWM_B34
            
            # 创建V2命令 - 这里假设x和y值为固定值，实际应根据需求调整
            x, y = ProtocolConverter.v3_freq_to_v2(50)  # 默认频率50Hz
            command = ProtocolConverter.encode_pwm_channel(x, y, z_value)
            
            # 发送命令
            success = await self.ble_manager.send_command(char_uuid, command)
            if success:
                self.signals.log_message.emit(f"已发送强度命令到通道{channel_letter}")
            else:
                self.signals.log_message.emit(f"发送强度命令到通道{channel_letter}失败")
                
            # 更新UI状态
            channel_letter = 'A' if channel == 1 else 'B'
            self.signals.status_update.emit({channel_letter: new_intensity})
            
    async def _handle_pulse_message(self, message):
        """处理波形数据消息
        
        格式: pulse-通道:["波形数据","波形数据",...]
        例如: pulse-A:["0A0A0A0A64646464","0A0A0A0A64646464"]
        
        Args:
            message (str): 波形数据消息
        """
        try:
            # 检查基本格式
            if ':' not in message:
                logging.warning(f"波形数据消息格式不正确: {message}")
                return
                
            # 分离通道和数据部分
            parts = message[6:].split(':', 1)
            if len(parts) != 2:
                logging.warning(f"波形数据消息格式不正确: {message}")
                return
                
            channel = parts[0].upper()
            if channel not in ['A', 'B']:
                logging.warning(f"无效的通道: {channel}")
                return
                
            # 解析JSON数组
            import json
            try:
                wave_data_list = json.loads(parts[1])
            except json.JSONDecodeError:
                logging.warning(f"波形数据不是有效的JSON数组: {parts[1]}")
                return
                
            # 验证数组
            if not isinstance(wave_data_list, list) or len(wave_data_list) == 0:
                logging.warning("波形数据数组为空或格式不正确")
                return
                
            logging.info(f"处理{channel}通道波形数据，共{len(wave_data_list)}组")
            
            # 选择对应的特征值UUID
            char_uuid = BLE_CHAR_PWM_A34 if channel == 'A' else BLE_CHAR_PWM_B34
            
            # 处理每组波形数据
            for i, hex_data in enumerate(wave_data_list):
                if not isinstance(hex_data, str) or len(hex_data) != 16:
                    logging.warning(f"第{i+1}组波形数据格式不正确: {hex_data}")
                    continue
                    
                try:
                    # 解析V3波形数据
                    wave_params = self._parse_v3_wave_data(hex_data)
                    
                    # 发送到蓝牙设备
                    for param in wave_params:
                        # 每组参数发送一次
                        data = ProtocolConverter.encode_pwm_channel(
                            param['v2_x'], 
                            param['v2_y'], 
                            param['v2_z']
                        )
                        await self.ble_manager.send_command(char_uuid, data)
                        
                        # 短暂延迟，确保命令能被设备处理
                        await asyncio.sleep(0.05)
                    
                    logging.info(f"已发送第{i+1}组波形数据到{channel}通道")
                    
                except Exception as e:
                    logging.error(f"处理第{i+1}组波形数据失败: {str(e)}")
                    
            self.signals.log_message.emit(f"已发送波形数据到{channel}通道")
            
        except Exception as e:
            self.signals.log_message.emit(f"处理波形数据消息失败: {str(e)}")
            logging.error(f"处理波形数据消息失败: {str(e)}")
            
        def _parse_v3_wave_data(self, hex_data):
            """解析V3协议的波形数据
            
            Args:
                hex_data (str): 16字节的HEX字符串
                
            Returns:
                list: 包含解析后的波形参数的列表
            """
            try:
                # 将HEX字符串转换为字节
                data_bytes = bytes.fromhex(hex_data)
                
                # 确保数据长度正确
                if len(data_bytes) != 8:
                    raise ValueError("波形数据长度不正确，应为8字节")
                    
                # 解析数据
                # 根据V3协议文档，波形数据格式为:
                # 频率值1(1字节) + 强度值1(1字节) + 频率值2(1字节) + 强度值2(1字节) + ...
                result = []
                for i in range(0, 8, 2):
                    freq = data_bytes[i]
                    intensity = data_bytes[i+1]
                    
                    # 跳过强度为0的部分
                    if intensity == 0:
                        continue
                        
                    # 将V3协议的频率值转换为实际频率
                    real_freq = ProtocolConverter.v3_freq_to_real_freq(freq)
                    
                    # 将实际频率转换为V2协议的x和y参数
                    x, y = ProtocolConverter.v3_freq_to_v2(real_freq)
                    
                    # 将V3协议的强度值转换为V2协议的z参数
                    z = ProtocolConverter.v3_intensity_to_v2_z(intensity)
                    
                    result.append({
                        'v3_freq': freq,
                        'v3_intensity': intensity,
                        'v2_x': x,
                        'v2_y': y,
                        'v2_z': z,
                        'real_freq': real_freq
                    })
                    
                return result
            except Exception as e:
                raise ValueError(f"解析V3波形数据失败: {str(e)}")

    async def _handle_clear_message(self, message):
        """处理清空波形队列消息"""
        # 解析清空队列消息格式: clear-通道
        match = re.match(r"clear-(\d)", message)
        if not match:
            self.signals.log_message.emit(f"无效的清空队列消息格式: {message}")
            return
            
        channel = int(match.group(1))
        if channel not in [1, 2]:
            self.signals.log_message.emit(f"无效的通道值: {channel}")
            return
            
        self.signals.log_message.emit(f"清空通道{channel}的波形队列")
        
        # 在V2协议中可能没有直接的清空队列命令
        # 通过发送一个强度为0的命令来模拟清空效果
        if self.ble_manager and self.ble_manager.is_connected:
            char_uuid = BLE_CHAR_PWM_A34 if channel == 1 else BLE_CHAR_PWM_B34
            # 发送一个强度为0的命令
            command = ProtocolConverter.create_v2_command(channel, 1, 9, 0)
            await self.ble_manager.send_command(char_uuid, command)
            
            # 更新通道强度状态
            self.channel_intensity[channel] = 0
            # 更新UI状态
            channel_letter = 'A' if channel == 1 else 'B'
            self.signals.status_update.emit({channel_letter: 0})
            
            self.signals.log_message.emit(f"已发送清空命令到通道{channel}")
            
    async def send_bind_request(self, target_id):
        """发送绑定请求"""
        if not self.ws or not self.client_id:
            self.signals.log_message.emit("WebSocket未连接或未获取到终端ID")
            return False
            
        try:
            bind_data = {
                "type": "bind",
                "clientId": self.client_id,
                "targetId": target_id,
                "message": "DGLAB"
            }
            await self.ws.send(json.dumps(bind_data))
            self.signals.log_message.emit(f"已发送绑定请求到目标ID: {target_id}")
            return True
        except Exception as e:
            self.signals.log_message.emit(f"发送绑定请求失败: {str(e)}")

    async def _handle_clear_message(self, message):
        """处理清空波形队列命令
        
        格式: clear-通道
        例如: clear-1 (清空A通道)
        
        Args:
            message (str): 清空波形队列命令
        """
        try:
            # 解析消息
            channel_num = message.replace('clear-', '')
            
            if channel_num not in ['1', '2']:
                logging.warning(f"无效的通道号: {channel_num}")
                return
                
            channel = 'A' if channel_num == '1' else 'B'
            logging.info(f"清空{channel}通道波形队列")
            
            # 调用BLE管理器清空通道
            await self.ble_manager.clear_channel(channel)
            
        except Exception as e:
            self.signals.log_message.emit(f"处理清空波形队列命令失败: {str(e)}")
            logging.error(f"处理清空波形队列命令失败: {str(e)}")