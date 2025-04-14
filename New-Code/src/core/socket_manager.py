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
        self.is_connected = False  # 添加连接状态标志
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
            self.is_connected = True  # 设置连接状态
            asyncio.create_task(self._listen())
            self.signals.log_message.emit("WebSocket连接成功")
            self.signals.log_message.emit("服务器已连接")
            
            # 连接成功后等待一小段时间，确保ID绑定完成
            await asyncio.sleep(1)
            
            # 连接成功后自动发送当前最大强度设置
            if self.client_id:
                try:
                    await self.send_strength_update()
                    logging.info("连接后自动发送强度设置到服务器")
                except Exception as e:
                    logging.error(f"连接后自动发送强度设置失败: {str(e)}")
            
            return True
        except Exception as e:
            self.signals.log_message.emit(f"WebSocket连接失败: {str(e)}")
            self.is_connected = False  # 连接失败时设置状态
            return False
            
    async def disconnect(self):
        """断开WebSocket连接"""
        self.running = False
        self.is_connected = False  # 断开连接时设置状态
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
                    logging.debug("收到心跳消息")
                    # 回复心跳消息
                    if self.ws and self.client_id:
                        response = {
                            'type': 'heartbeat',
                            'clientId': self.client_id,
                            'targetId': self.target_id if self.target_id else '',
                            'message': 'pong'
                        }
                        await self.ws.send(json.dumps(response))
                        logging.info("已发送targetId响应")
                elif message_type == 'bind':
                    # 处理绑定消息
                    await self._handle_bind_message(data)
                elif message_type == 'msg':
                    # 处理控制消息
                    await self._handle_msg_message(data)
                elif message_type == 'break':
                    # 处理断开连接消息
                    self.signals.log_message.emit("收到断开连接消息")
                    logging.info("收到断开连接消息")
                elif message_type == 'error':
                    # 处理错误消息
                    error_msg = data.get('message', '未知错误')
                    self.signals.log_message.emit(f"收到错误消息: {error_msg}")
                    logging.error(f"收到错误消息: {error_msg}")
                else:
                    # 未知消息类型
                    self.signals.log_message.emit(f"收到未知类型消息: {message_type}")
                    logging.warning(f"收到未知类型消息: {message_type}")
            else:
                # 消息格式错误
                self.signals.log_message.emit("收到格式错误的消息: 缺少type字段")
                logging.warning("收到格式错误的消息: 缺少type字段")
        except json.JSONDecodeError:
            # JSON解析错误
            self.signals.log_message.emit("收到无效的JSON消息")
            logging.error(f"收到无效的JSON消息: {message}")
        except Exception as e:
            # 其他错误
            self.signals.log_message.emit(f"处理WebSocket消息时发生错误: {str(e)}")
            logging.error(f"处理WebSocket消息时发生错误: {str(e)}")
    
    async def _handle_bind_message(self, data):
        """处理绑定消息
        
        Args:
            data (dict): 消息数据
        """
        try:
            if 'clientId' in data:
                self.client_id = data['clientId']
                logging.info(f"已绑定客户端ID: {self.client_id}")
                
            if 'targetId' in data and data['targetId']:
                self.target_id = data['targetId']
                logging.info(f"已绑定目标ID: {self.target_id}")
                
            if 'message' in data:
                bind_message = data['message']
                
                if bind_message == 'targetId':
                    # 需要回复targetId消息
                    if self.ws and self.client_id:
                        response = {
                            'type': 'bind',
                            'clientId': self.client_id,
                            'targetId': '',
                            'message': 'targetId'
                        }
                        await self.ws.send(json.dumps(response))
                        logging.info("已发送targetId响应")
                elif bind_message == '200':
                    # 绑定成功
                    self.signals.log_message.emit("设备绑定成功")
                    logging.info("设备绑定成功")
                    
                    # 绑定成功后发送当前强度设置
                    try:
                        await self.send_strength_update()
                        logging.info("绑定成功后自动发送强度设置到服务器")
                    except Exception as e:
                        logging.error(f"绑定成功后自动发送强度设置失败: {str(e)}")
        except Exception as e:
            logging.error(f"处理绑定消息失败: {str(e)}")
    
    async def _handle_msg_message(self, data):
        """处理控制消息
        
        Args:
            data (dict): 消息数据
        """
        if 'message' in data:
            message = data['message']
            logging.info(f"处理控制消息: {message}")
            
            # 处理不同类型的控制消息
            if message.startswith('strength-'):
                # 处理强度控制消息
                try:
                    # 解析强度消息格式: strength-A+B+MAX
                    # 例如: strength-1+2+60 表示A=1, B=2, MAX=60
                    parts = message[9:].split('+')
                    if len(parts) >= 2:
                        a_strength = int(parts[0])
                        b_strength = int(parts[1])
                        
                        # 如果有最大强度信息，也更新
                        if len(parts) >= 3:
                            a_max = int(parts[2])
                            if a_max != self.max_strength['A']:
                                logging.info(f"更新A通道最大强度: {a_max}")
                                self.max_strength['A'] = a_max
                                
                        # 更新通道强度
                        self.channel_intensity['A'] = a_strength
                        self.channel_intensity['B'] = b_strength
                        
                        logging.info(f"收到强度控制: A={a_strength}, B={b_strength}")
                        
                        # 检查强度是否超出范围
                        if self.channel_intensity['A'] > self.max_strength['A']:
                            logging.warning(f"A通道强度值超出范围: {self.channel_intensity['A']}, 最大值: {self.max_strength['A']}")
                            self.channel_intensity['A'] = self.max_strength['A']
                            
                        if self.channel_intensity['B'] > self.max_strength['B']:
                            logging.warning(f"B通道强度值超出范围: {self.channel_intensity['B']}, 最大值: {self.max_strength['B']}")
                            self.channel_intensity['B'] = self.max_strength['B']
                        
                        # 发送强度命令到设备
                        if self.ble_manager and self.ble_manager.is_connected:
                            # 编码PWM_AB2命令
                            pwm_data = ProtocolConverter.encode_pwm_ab2(
                                self.channel_intensity['A'], 
                                self.channel_intensity['B']
                            )
                            # 发送到设备
                            success = await self.ble_manager.send_command(BLE_CHAR_PWM_AB2, pwm_data)
                            if success:
                                logging.info(f"已发送强度命令到设备: A={self.channel_intensity['A']}, B={self.channel_intensity['B']}")
                            else:
                                logging.error("发送强度命令到设备失败")
                except Exception as e:
                    logging.error(f"处理强度控制消息失败: {str(e)}")
            
            # 处理波形数据
            elif message.startswith('pulse-A:') or message.startswith('pulse-B:'):
                channel = 'A' if message.startswith('pulse-A:') else 'B'
                try:
                    # 提取波形数据JSON字符串
                    json_str = message[8:]  # 移除"pulse-A:"或"pulse-B:"前缀
                    wave_data_list = json.loads(json_str)
                    logging.info(f"处理{channel}通道波形数据，共{len(wave_data_list)}组")
                    
                    # 处理每组波形数据
                    for i, wave_data in enumerate(wave_data_list):
                        try:
                            # 解析V3波形数据
                            freq1 = int(wave_data[0:2], 16)  # 波形频率1
                            balance1 = int(wave_data[2:4], 16)  # 频率平衡1
                            intensity = int(wave_data[8:10], 16)  # 第一个强度值
                            
                            # 将V3频率转换为V2的x和y参数
                            x, y = ProtocolConverter.v3_freq_to_v2(freq1)
                            
                            # 将V3强度转换为V2的z参数
                            z = ProtocolConverter.v3_intensity_to_v2_z(intensity)
                            
                            # 编码为V2协议数据
                            pwm_data = ProtocolConverter.encode_pwm_channel(x, y, z)
                            
                            # 发送到对应通道
                            char_uuid = BLE_CHAR_PWM_A34 if channel == 'A' else BLE_CHAR_PWM_B34
                            if self.ble_manager and self.ble_manager.is_connected:
                                success = await self.ble_manager.send_command(char_uuid, pwm_data)
                                if success:
                                    logging.info(f"已发送{channel}通道第{i+1}组波形数据: x={x}, y={y}, z={z}")
                                else:
                                    logging.error(f"发送{channel}通道第{i+1}组波形数据失败")
                        except Exception as e:
                            logging.error(f"处理第{i+1}组波形数据失败: {str(e)}")
                except json.JSONDecodeError:
                    logging.error(f"波形数据JSON解析失败: {message[8:]}")
                except Exception as e:
                    logging.error(f"处理{channel}通道波形数据失败: {str(e)}")
            
            # 处理清空命令
            elif message.startswith('clear-'):
                channel_num = message[6:]
                if channel_num == '1':
                    logging.info("清空A通道波形队列")
                    # 这里可以添加清空A通道波形队列的代码
                elif channel_num == '2':
                    logging.info("清空B通道波形队列")
                    # 这里可以添加清空B通道波形队列的代码
            
            # 其他类型的消息
            else:
                logging.info(f"收到未处理的控制消息: {message}")
    
    async def send_strength_update(self):
        """发送当前强度状态到服务器
        
        格式: strength-A通道强度+B通道强度+A强度上限+B强度上限
        """
        if not self.is_connected or not self.ws:
            logging.warning("无法发送强度更新：WebSocket未连接")
            return False
            
        try:
            # 获取当前强度和最大强度
            a_strength = self.channel_intensity['A']
            b_strength = self.channel_intensity['B']
            a_max = self.max_strength['A']
            b_max = self.max_strength['B']
            
            # 按照协议格式构建消息: strength-A通道强度+B通道强度+A强度上限+B强度上限
            strength_message = f"strength-{a_strength}+{b_strength}+{a_max}+{b_max}"
            
            # 构建完整的JSON消息
            message = {
                'type': 'msg',
                'clientId': self.client_id,
                'targetId': self.target_id if self.target_id else '',
                'message': strength_message
            }
            
            # 发送消息
            await self.ws.send(json.dumps(message))
            logging.info(f"已发送强度更新: {strength_message}")
            return True
        except Exception as e:
            logging.error(f"发送强度更新失败: {str(e)}")
            return False