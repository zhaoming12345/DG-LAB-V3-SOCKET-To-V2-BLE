class ProtocolConverter:
    @staticmethod
    def v3_freq_to_v2(freq_input):
        """V3协议频率值转V2协议参数
        根据文档公式: X = ((Frequency / 1000)^ 0.5) * 15, Y = Frequency - X
        
        Args:
            freq_input (int): V3协议频率值(10-1000Hz)
        Returns:
            tuple: (x, y) V2协议参数对
        """
        # 输入值钳位处理，确保在有效范围内
        # 增强输入类型检查
        if not isinstance(freq_input, (int, float)):
            raise ValueError("频率值必须是数字类型")
        
        freq_input = max(10, min(1000, freq_input))
        
        # 按照官方文档公式计算
        x = int(((freq_input / 1000) ** 0.5) * 15)
        y = freq_input - x
        
        # 输出参数范围验证
        return (
            max(1, min(31, x)),    # x参数范围限制1-31（5位二进制）
            max(1, min(1023, y))   # y参数范围限制1-1023（10位二进制）
        )
        
    @staticmethod
    def v3_intensity_to_v2_z(intensity):
        """将V3协议的强度值转换为V2协议的z参数
        
        Z的范围是【0-31】，实际的脉冲宽度为Z*5us
        当Z>20时脉冲更容易引起刺痛
        
        Args:
            intensity (int): V3协议的强度值(0-100)
            
        Returns:
            int: V2协议的z参数值(0-31)
        """
        # 将0-100的强度值映射到0-31的Z值范围
        return min(31, max(0, int(intensity * 31 / 100)))
        
    @staticmethod
    def encode_pwm_ab2(a, b):
        """编码PWM AB2通道的数据
        
        将A、B通道的强度值编码为V2协议的字节数据。
        PWM_AB2: 23-22bit(保留) 21-11bit(A通道实际强度) 10-0bit(B通道实际强度)
        
        Args:
            a (int): A通道强度值(0-200)
            b (int): B通道强度值(0-200)
            
        Returns:
            bytes: 编码后的3字节数据
        """
        # 将0-200的APP显示值转换为0-2047的实际强度值（文档中提到APP中每增加一点强度是增加7）
        a_val = min(int(a * 7), 2047)
        b_val = min(int(b * 7), 2047)
        
        # 按照位域结构打包数据
        # 低字节在前，高字节在后
        byte1 = (b_val & 0xFF)  # B通道低8位
        byte2 = ((b_val >> 8) & 0x07) | ((a_val & 0x1F) << 3)  # B通道高3位 + A通道低5位
        byte3 = (a_val >> 5) & 0xFF  # A通道高8位
        
        return bytes([byte1, byte2, byte3])
    
    @staticmethod
    def encode_pwm_channel(x, y, z):
        """编码单个PWM通道的数据
        
        将x、y、z参数编码为V2协议的字节数据。
        PWM_A34/B34: 23-20bit(保留) 19-15bit(z) 14-5bit(y) 4-0bit(x)
        
        Args:
            x (int): 频率参数x(1-31)
            y (int): 频率参数y(1-1023)
            z (int): 强度参数z(0-31)
            
        Returns:
            bytes: 编码后的3字节数据
        """
        # 确保参数在有效范围内
        x = max(1, min(31, x))
        y = max(1, min(1023, y))
        z = max(0, min(31, z))
        
        # 按照位域结构打包数据
        # 低字节在前，高字节在后
        byte1 = (x & 0x1F) | ((y & 0x1F) << 5)  # x的5位 + y的低5位
        byte2 = ((y >> 5) & 0x1F) | ((z & 0x1F) << 5)  # y的高5位 + z的5位
        byte3 = 0  # 保留位，全为0
        
        return bytes([byte1, byte2, byte3])

    @staticmethod
    def create_v2_command(channel, x, y, z):
        """创建V2协议命令"""
        return bytes([x, y & 0xFF, y >> 8, z])
        
    @staticmethod
    def format_strength_message(a_strength, b_strength, a_max, b_max):
        """格式化强度数据消息
        
        根据SOCKETV3控制协议，格式化当前强度和最大强度数据
        格式: strength-A通道强度+B通道强度+A强度上限+B强度上限
        
        Args:
            a_strength (int): A通道当前强度
            b_strength (int): B通道当前强度
            a_max (int): A通道最大强度
            b_max (int): B通道最大强度
            
        Returns:
            str: 格式化的强度消息
        """
        return f"strength-{a_strength}+{b_strength}+{a_max}+{b_max}"
    
    @staticmethod
    def parse_strength_message(message):
        """解析强度数据消息
        
        根据SOCKETV3控制协议，解析强度消息
        格式: strength-A通道强度+B通道强度+A强度上限+B强度上限
        
        Args:
            message (str): 强度消息字符串
            
        Returns:
            dict: 包含解析后的强度数据的字典
        """
        try:
            # 移除前缀并按+分割
            parts = message.replace('strength-', '').split('+')
            
            # 确保至少有两个部分（A和B通道强度）
            if len(parts) < 2:
                raise ValueError("强度消息格式不正确")
                
            result = {
                'A': int(parts[0]),
                'B': int(parts[1])
            }
            
            # 如果有A通道最大强度
            if len(parts) > 2:
                result['A_max'] = int(parts[2])
                
            # 如果有B通道最大强度
            if len(parts) > 3:
                result['B_max'] = int(parts[3])
                
            return result
        except Exception as e:
            raise ValueError(f"解析强度消息失败: {str(e)}")
            
    @staticmethod
    def parse_strength_command(message):
        """解析强度操作命令
        
        根据SOCKETV3控制协议，解析强度操作命令
        格式: strength-通道+强度变化模式+数值
        
        Args:
            message (str): 强度操作命令字符串
            
        Returns:
            dict: 包含解析后的操作数据的字典
        """
        try:
            # 移除前缀并按+分割
            parts = message.replace('strength-', '').split('+')
            
            # 确保有三个部分
            if len(parts) != 3:
                raise ValueError("强度操作命令格式不正确")
                
            channel = int(parts[0])
            mode = int(parts[1])
            value = int(parts[2])
            
            # 验证参数
            if channel not in [1, 2]:
                raise ValueError("通道值必须是1(A通道)或2(B通道)")
                
            if mode not in [0, 1, 2]:
                raise ValueError("强度变化模式必须是0(减少)、1(增加)或2(指定)")
                
            if not (0 <= value <= 200):
                raise ValueError("强度值必须在0-200范围内")
                
            return {
                'channel': 'A' if channel == 1 else 'B',
                'mode': mode,
                'value': value
            }
        except Exception as e:
            raise ValueError(f"解析强度操作命令失败: {str(e)}")
            
    @staticmethod
    def parse_wave_message(message):
        """解析波形操作命令
        
        根据SOCKETV3控制协议，解析波形操作命令
        格式: pulse-通道:["波形数据","波形数据",...]
        
        Args:
            message (str): 波形操作命令字符串
            
        Returns:
            dict: 包含解析后的波形数据的字典
        """
        try:
            # 检查基本格式
            if not message.startswith('pulse-'):
                raise ValueError("波形操作命令格式不正确")
                
            # 分离通道和数据部分
            parts = message[6:].split(':', 1)
            if len(parts) != 2:
                raise ValueError("波形操作命令格式不正确")
                
            channel = parts[0].upper()
            if channel not in ['A', 'B']:
                raise ValueError("通道值必须是A或B")
                
            # 解析JSON数组
            import json
            try:
                wave_data = json.loads(parts[1])
            except json.JSONDecodeError:
                raise ValueError("波形数据不是有效的JSON数组")
                
            # 验证数组长度
            if len(wave_data) > 100:
                raise ValueError("波形数据数组长度超过100")
                
            # 验证每个波形数据
            for i, data in enumerate(wave_data):
                if not isinstance(data, str) or len(data) != 16:
                    raise ValueError(f"第{i+1}个波形数据不是16字节的HEX字符串")
                    
                # 尝试将HEX字符串转换为字节
                try:
                    bytes.fromhex(data)
                except ValueError:
                    raise ValueError(f"第{i+1}个波形数据不是有效的HEX字符串")
                    
            return {
                'channel': channel,
                'wave_data': wave_data
            }
        except Exception as e:
            raise ValueError(f"解析波形操作命令失败: {str(e)}")
            
    @staticmethod
    def parse_clear_command(message):
        """解析清空波形队列命令
        
        根据SOCKETV3控制协议，解析清空波形队列命令
        格式: clear-通道
        
        Args:
            message (str): 清空波形队列命令字符串
            
        Returns:
            str: 通道标识('A'或'B')
        """
        try:
            # 检查基本格式
            if not message.startswith('clear-'):
                raise ValueError("清空波形队列命令格式不正确")
                
            channel = message[6:]
            if channel not in ['1', '2']:
                raise ValueError("通道值必须是1(A通道)或2(B通道)")
                
            return 'A' if channel == '1' else 'B'
        except Exception as e:
            raise ValueError(f"解析清空波形队列命令失败: {str(e)}")
            
    @staticmethod
    def v3_wave_to_v2(freq, intensity):
        """将V3协议的波形数据转换为V2协议的参数
        
        根据文档，V3波形频率转V2: V3波形频率 = V2 (X + Y)
        V3波形强度转V2: V3波形强度 = V2 (Z * 5)
        
        Args:
            freq (int): V3协议的波形频率(10-240)
            intensity (int): V3协议的波形强度(0-100)
            
        Returns:
            tuple: (x, y, z) V2协议参数三元组
        """
        # 将V3的波形频率(10-240)转换为实际频率(10-1000)
        real_freq = ProtocolConverter.v3_freq_to_real_freq(freq)
        
        # 将实际频率转换为V2的x和y参数
        x, y = ProtocolConverter.v3_freq_to_v2(real_freq)
        
        # 将V3的波形强度(0-100)转换为V2的z参数(0-31)
        z = ProtocolConverter.v3_intensity_to_v2_z(intensity)
        
        return (x, y, z)
        
    @staticmethod
    def v3_freq_to_real_freq(v3_freq):
        """将V3协议的波形频率值转换为实际频率值
        
        根据文档中的转换算法:
        输入值范围(10-240)
        实际频率 = when(输入值){
            in 10..100 -> 输入值
            in 101..200 -> (输入值 - 100) * 5 + 100
            in 201..240 -> (输入值 - 200) * 10 + 600
        }
        
        Args:
            v3_freq (int): V3协议的波形频率值(10-240)
            
        Returns:
            int: 实际频率值(10-1000)
        """
        # 确保输入在有效范围内
        v3_freq = max(10, min(240, v3_freq))
        
        # 根据文档算法转换
        if 10 <= v3_freq <= 100:
            return v3_freq
        elif 101 <= v3_freq <= 200:
            return (v3_freq - 100) * 5 + 100
        elif 201 <= v3_freq <= 240:
            return (v3_freq - 200) * 10 + 600
        else:
            return 10  # 默认最小值
            
    @staticmethod
    def real_freq_to_v3_freq(real_freq):
        """将实际频率值转换为V3协议的波形频率值
        
        根据文档中的转换算法的逆运算:
        实际频率 -> V3波形频率值
        
        Args:
            real_freq (int): 实际频率值(10-1000)
            
        Returns:
            int: V3协议的波形频率值(10-240)
        """
        # 确保输入在有效范围内
        real_freq = max(10, min(1000, real_freq))
        
        # 根据文档算法的逆运算
        if 10 <= real_freq <= 100:
            return real_freq
        elif 101 <= real_freq <= 600:
            return int((real_freq - 100) / 5) + 100
        elif 601 <= real_freq <= 1000:
            return int((real_freq - 600) / 10) + 200
        else:
            return 10  # 默认最小值
            
    @staticmethod
    def parse_v3_wave_data(hex_data):
        """解析V3协议的波形数据
        
        根据V3协议文档，解析16字节的HEX字符串波形数据
        
        Args:
            hex_data (str): 16字节的HEX字符串
            
        Returns:
            dict: 包含解析后的波形数据的字典
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
                
                # 将V3协议的频率和强度值转换为V2协议的参数
                x, y, z = ProtocolConverter.v3_wave_to_v2(freq, intensity)
                
                result.append({
                    'v3_freq': freq,
                    'v3_intensity': intensity,
                    'v2_x': x,
                    'v2_y': y,
                    'v2_z': z,
                    'real_freq': ProtocolConverter.v3_freq_to_real_freq(freq)
                })
                
            return result
        except Exception as e:
            raise ValueError(f"解析V3波形数据失败: {str(e)}")
            
    @staticmethod
    def format_wave_message(channel, wave_data_list):
        """格式化波形数据消息
        
        根据SOCKETV3控制协议，格式化波形数据
        格式: pulse-通道:["波形数据","波形数据",...]
        
        Args:
            channel (str): 通道标识('A'或'B')
            wave_data_list (list): 波形数据列表，每项为16字节的HEX字符串
            
        Returns:
            str: 格式化的波形消息
        """
        import json
        
        # 验证通道
        if channel not in ['A', 'B']:
            raise ValueError("通道值必须是A或B")
            
        # 验证波形数据列表
        if not isinstance(wave_data_list, list):
            raise ValueError("波形数据必须是列表")
            
        # 验证每个波形数据
        for i, data in enumerate(wave_data_list):
            if not isinstance(data, str) or len(data) != 16:
                raise ValueError(f"第{i+1}个波形数据不是16字节的HEX字符串")
                
            # 尝试将HEX字符串转换为字节
            try:
                bytes.fromhex(data)
            except ValueError:
                raise ValueError(f"第{i+1}个波形数据不是有效的HEX字符串")
                
        # 格式化消息
        return f"pulse-{channel}:{json.dumps(wave_data_list)}"
        
    @staticmethod
    def format_clear_command(channel):
        """格式化清空波形队列命令
        
        根据SOCKETV3控制协议，格式化清空波形队列命令
        格式: clear-通道
        
        Args:
            channel (str): 通道标识('A'或'B')
            
        Returns:
            str: 格式化的清空命令
        """
        # 验证通道
        if channel not in ['A', 'B']:
            raise ValueError("通道值必须是A或B")
            
        # 转换通道标识为数字
        channel_num = '1' if channel == 'A' else '2'
            
        # 格式化命令
        return f"clear-{channel_num}"
        
    @staticmethod
    def format_freq_message(channel, freq):
        """格式化频率控制消息
        
        根据SOCKETV3控制协议，格式化频率控制消息
        格式: freq-通道+频率值
        
        Args:
            channel (str): 通道标识('A'或'B')
            freq (int): 频率值(10-1000)
            
        Returns:
            str: 格式化的频率控制消息
        """
        # 验证通道
        if channel not in ['A', 'B']:
            raise ValueError("通道值必须是A或B")
            
        # 验证频率值
        if not isinstance(freq, (int, float)):
            raise ValueError("频率值必须是数字类型")
            
        freq = max(10, min(1000, int(freq)))
            
        # 格式化消息
        return f"freq-{channel}+{freq}"
        
    @staticmethod
    def format_wave_command(channel, wave_id):
        """格式化波形控制消息
        
        根据SOCKETV3控制协议，格式化波形控制消息
        格式: wave-通道+波形ID
        
        Args:
            channel (str): 通道标识('A'或'B')
            wave_id (int): 波形ID
            
        Returns:
            str: 格式化的波形控制消息
        """
        # 验证通道
        if channel not in ['A', 'B']:
            raise ValueError("通道值必须是A或B")
            
        # 验证波形ID
        if not isinstance(wave_id, int):
            raise ValueError("波形ID必须是整数")
            
        wave_id = max(0, min(100, wave_id))
            
        # 格式化消息
        return f"wave-{channel}+{wave_id}"
        
    @staticmethod
    def create_v3_wave_data(freq_list, intensity_list):
        """创建V3协议的波形数据
        
        根据V3协议文档，创建16字节的HEX字符串波形数据
        
        Args:
            freq_list (list): 频率值列表，每项为10-240的整数
            intensity_list (list): 强度值列表，每项为0-100的整数
            
        Returns:
            str: 16字节的HEX字符串"""