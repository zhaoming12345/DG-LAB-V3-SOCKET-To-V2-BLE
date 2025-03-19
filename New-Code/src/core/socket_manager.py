import asyncio
import json
import websockets
import re
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
        self.channel_intensity = {1: 0, 2: 0}  # A通道和B通道的当前强度
        
    async def connect(self):
        """连接到WebSocket服务器"""
        if not settings.socket_uri:
            self.signals.log_message.emit("WebSocket地址未设置")
            return False
            
        try:
            self.ws = await websockets.connect(settings.socket_uri)
            self.running = True
            asyncio.create_task(self._listen())
            self.signals.log_message.emit("WebSocket连接成功")
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
        """处理接收到的消息"""
        try:
            data = json.loads(message)
            
            # 检查消息格式是否符合要求
            if not all(key in data for key in ["type", "clientId", "message"]):
                self.signals.log_message.emit("消息格式不完整")
                return
                
            msg_type = data.get("type")
            client_id = data.get("clientId")
            target_id = data.get("targetId", "")
            msg_content = data.get("message", "")
            
            # 处理不同类型的消息
            if msg_type == "bind":
                await self._handle_bind_message(client_id, target_id, msg_content)
            elif msg_type == "msg":
                await self._handle_data_message(client_id, target_id, msg_content)
            elif msg_type == "heartbeat":
                # 心跳包处理，可以简单记录或回复
                pass
            elif msg_type == "break":
                self.signals.log_message.emit("收到断开连接请求")
                await self.disconnect()
            elif msg_type == "error":
                self.signals.log_message.emit(f"服务器错误: {msg_content}")
            else:
                self.signals.log_message.emit(f"未知消息类型: {msg_type}")
                
        except json.JSONDecodeError:
            self.signals.log_message.emit("无效的JSON消息")
        except Exception as e:
            self.signals.log_message.emit(f"处理消息失败: {str(e)}")
            
    async def _handle_bind_message(self, client_id, target_id, message):
        """处理绑定消息"""
        if message == "targetId":
            # 服务器返回的ID，保存为自己的ID
            self.client_id = client_id
            self.signals.log_message.emit(f"获取到终端ID: {client_id}")
        elif message == "200":
            # 绑定成功
            self.target_id = target_id
            self.signals.log_message.emit("绑定成功")
            self.signals.connection_status_changed.emit(True)
        else:
            # 其他绑定相关消息，可能是错误码
            self.signals.log_message.emit(f"绑定消息: {message}")
            
    async def _handle_data_message(self, client_id, target_id, message):
        """处理数据消息"""
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
            
    async def _handle_strength_message(self, message):
        """处理强度相关消息"""
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
            
        # 计算实际强度值
        current_intensity = self.channel_intensity[channel]
        if mode == 0:  # 减少强度
            new_intensity = max(0, current_intensity - value)
        elif mode == 1:  # 增加强度
            new_intensity = min(200, current_intensity + value)
        else:  # mode == 2, 设置为指定值
            new_intensity = min(200, max(0, value))
        
        # 更新本地强度状态
        self.channel_intensity[channel] = new_intensity
        self.signals.log_message.emit(f"通道{channel}强度更新为: {new_intensity}")
        
        # 转换为V2协议并发送到BLE设备
        if self.ble_manager and self.ble_manager.is_connected:
            # 将V3强度值转换为V2的z参数
            z_value = ProtocolConverter.v3_intensity_to_v2_z(new_intensity)
            
            # 根据通道选择特性UUID
            char_uuid = BLE_CHAR_PWM_A34 if channel == 1 else BLE_CHAR_PWM_B34
            
            # 创建V2命令 - 这里假设x和y值为固定值，实际应根据需求调整
            x, y = 1, 9  # 默认值，可以根据需要调整
            command = ProtocolConverter.create_v2_command(channel, x, y, z_value)
            
            # 发送命令
            success = await self.ble_manager.send_command(char_uuid, command)
            if success:
                self.signals.log_message.emit(f"已发送强度命令到通道{channel}")
            else:
                self.signals.log_message.emit(f"发送强度命令到通道{channel}失败")
            
    async def _handle_pulse_message(self, message):
        """处理波形相关消息"""
        # 解析波形消息格式: pulse-通道:[波形数据数组]
        match = re.match(r"pulse-([AB]):(\[.*\])", message)
        if not match:
            self.signals.log_message.emit(f"无效的波形消息格式: {message}")
            return
            
        channel_letter, data_str = match.groups()
        # 将通道字母转换为数字
        channel = 1 if channel_letter == 'A' else 2
        
        try:
            # 解析波形数据数组
            wave_data = json.loads(data_str)
            if not isinstance(wave_data, list) or len(wave_data) > 100:
                self.signals.log_message.emit(f"波形数据无效或超出长度限制: {len(wave_data) if isinstance(wave_data, list) else type(wave_data)}")
                return
                
            self.signals.log_message.emit(f"处理波形消息: 通道={channel_letter}, 数据长度={len(wave_data)}")
            
            # 转换为V2协议并发送到BLE设备
            if self.ble_manager and self.ble_manager.is_connected:
                # 选择正确的特性UUID
                char_uuid = BLE_CHAR_PWM_A34 if channel == 1 else BLE_CHAR_PWM_B34
                
                # 对每个波形数据进行处理
                for wave_item in wave_data:
                    try:
                        # 解析V3波形数据
                        # 假设wave_item是16进制字符串，需要转换为字节
                        v3_data = bytes.fromhex(wave_item)
                        
                        # 从V3数据中提取频率和强度
                        # 这里需要根据V3协议文档进行正确解析
                        # 假设前4字节是A通道数据，后4字节是B通道数据
                        if channel == 1:  # A通道
                            freq_data = v3_data[0:4]  # 前4字节为频率数据
                            intensity_data = v3_data[4:8]  # 后4字节为强度数据
                        else:  # B通道
                            freq_data = v3_data[8:12]  # 前4字节为频率数据
                            intensity_data = v3_data[12:16]  # 后4字节为强度数据
                        
                        # 提取频率和强度值
                        # 这里的解析逻辑需要根据实际V3协议调整
                        freq = int.from_bytes(freq_data, byteorder='little')
                        intensity = int.from_bytes(intensity_data, byteorder='little')
                        
                        # 转换为V2协议参数
                        x, y = ProtocolConverter.v3_freq_to_v2(freq)
                        z = ProtocolConverter.v3_intensity_to_v2_z(intensity)
                        
                        # 创建并发送V2命令
                        command = ProtocolConverter.create_v2_command(channel, x, y, z)
                        await self.ble_manager.send_command(char_uuid, command)
                        
                    except Exception as e:
                        self.signals.log_message.emit(f"处理波形数据项失败: {str(e)}")
                        continue
                    
        except json.JSONDecodeError:
            self.signals.log_message.emit(f"波形数据解析失败: {data_str}")
        except Exception as e:
            self.signals.log_message.emit(f"处理波形数据失败: {str(e)}")
            
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
        # 可以通过发送一个强度为0的命令来模拟清空效果
        if self.ble_manager and self.ble_manager.is_connected:
            char_uuid = BLE_CHAR_PWM_A34 if channel == 1 else BLE_CHAR_PWM_B34
            # 发送一个强度为0的命令
            command = ProtocolConverter.create_v2_command(channel, 1, 9, 0)
            await self.ble_manager.send_command(char_uuid, command)
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