"""
协议转换器实现
"""

import logging

class ProtocolConverter:
    """协议转换工具类
    
    用于在V2和V3协议之间进行转换
    """
    
    @staticmethod
    def encode_pwm_ab2(a_strength, b_strength):
        """编码PWM_AB2命令
        
        将A和B通道的强度编码为V2协议的字节数据
        
        Args:
            a_strength (int): A通道强度(0-100)
            b_strength (int): B通道强度(0-100)
            
        Returns:
            bytes: 编码后的数据
        """
        # 确保强度值在有效范围内
        a_strength = max(0, min(100, a_strength))
        b_strength = max(0, min(100, b_strength))
        
        # 根据郊狼官方V2蓝牙协议支持文档，PWM_AB2的格式是:
        # 23-22bit(保留) 21-11bit(A通道实际强度) 10-0bit(B通道实际强度)
        # 在APP中每增加一点强度是增加7(脉冲主机中设置的实际强度值为APP中显示值的7倍)
        
        # 将APP显示的强度值转换为实际强度值
        a_actual = a_strength * 7
        b_actual = b_strength * 7
        
        # 确保实际强度值不超过2047
        a_actual = min(2047, a_actual)
        b_actual = min(2047, b_actual)
        
        # 编码为3字节数据
        # 第一个字节: B通道的低8位
        byte1 = b_actual & 0xFF
        
        # 第二个字节: B通道的高3位 + A通道的低5位
        byte2 = ((b_actual >> 8) & 0x07) | ((a_actual & 0x1F) << 3)
        
        # 第三个字节: A通道的高6位
        byte3 = (a_actual >> 5) & 0x3F
        
        return bytes([byte1, byte2, byte3])
        
    @staticmethod
    def v3_freq_to_v2(freq):
        """将V3协议的频率值转换为V2协议的x和y参数
        
        Args:
            freq (int): V3协议的频率值(10-240)
            
        Returns:
            tuple: (x, y)参数
        """
        # 根据V3协议文档中的频率转换公式计算实际频率(Hz)
        if freq <= 100:
            actual_freq = freq  # 10-100 -> 10-100Hz
        elif freq <= 200:
            actual_freq = (freq - 100) * 5 + 100  # 101-200 -> 105-600Hz
        else:
            actual_freq = (freq - 200) * 10 + 600  # 201-240 -> 610-1000Hz
        
        # 计算波形周期(ms)
        period_ms = 1000.0 / actual_freq
        
        # 根据V2协议文档中的公式计算x和y
        # X = ((Frequency / 1000)^ 0.5) * 15
        # Y = Frequency - X
        # 其中Frequency = X + Y = period_ms
        
        # 计算x值
        x = int(((actual_freq / 1000.0) ** 0.5) * 15)
        x = max(1, min(31, x))  # 确保x在1-31范围内
        
        # 计算y值
        y = int(1000.0 / actual_freq - x)
        y = max(1, min(1023, y))  # 确保y在1-1023范围内
        
        return (x, y)
    
    @staticmethod
    def v3_intensity_to_v2_z(intensity):
        """将V3协议的强度值(0-100)转换为V2协议的z参数(0-31)
        
        Args:
            intensity (int): V3协议的强度值(0-100)
            
        Returns:
            int: V2协议的z参数(0-31)
        """
        # 确保强度值在有效范围内
        intensity = max(0, min(100, intensity))
        
        # 线性映射到0-31范围
        return int(intensity * 31 / 100)
    
    @staticmethod
    def encode_pwm_channel(x, y, z):
        """编码单个PWM通道的数据
        
        将x、y、z参数编码为V2协议的字节数据
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
        # 第一个字节: x的5位 + y的低3位
        byte1 = (x & 0x1F) | ((y & 0x07) << 5)
        
        # 第二个字节: y的高7位
        byte2 = (y >> 3) & 0xFF
        
        # 第三个字节: z的5位
        byte3 = z & 0x1F
        
        # 确保所有字节都在0-255范围内
        byte1 = max(0, min(255, byte1))
        byte2 = max(0, min(255, byte2))
        byte3 = max(0, min(255, byte3))
        
        return bytes([byte1, byte2, byte3])
    
    @staticmethod
    def decode_hex_wave_data(hex_string):
        """解码十六进制波形数据字符串为字节数组
        
        Args:
            hex_string (str): 十六进制字符串
            
        Returns:
            bytes: 解码后的字节数组
        """
        try:
            # 移除可能存在的0x前缀
            if hex_string.startswith('0x'):
                hex_string = hex_string[2:]
                
            # 确保字符串长度是偶数
            if len(hex_string) % 2 != 0:
                hex_string = '0' + hex_string
                
            # 将十六进制字符串转换为字节数组
            byte_array = []
            for i in range(0, len(hex_string), 2):
                byte_value = int(hex_string[i:i+2], 16)
                byte_array.append(byte_value)
                
            return bytes(byte_array)
        except ValueError as e:
            raise ValueError(f"无效的十六进制数据: {hex_string}, 错误: {str(e)}")
    
    @staticmethod
    def parse_strength_message(message):
        """解析强度消息
        
        解析格式为"strength-A+B+MAX"的强度消息
        
        Args:
            message (str): 强度消息字符串
            
        Returns:
            dict: 解析后的强度数据
        """
        result = {}
        try:
            # 移除前缀
            if message.startswith('strength-'):
                data = message[9:]
            else:
                data = message
                
            # 按+分割
            parts = data.split('+')
            if len(parts) >= 2:
                result['A'] = int(parts[0])
                result['B'] = int(parts[1])
                
                # 如果有最大强度信息
                if len(parts) >= 3:
                    result['A_max'] = int(parts[2])
                    result['B_max'] = int(parts[2])
                    
            return result
        except Exception as e:
            logging.error(f"解析强度消息失败: {str(e)}")
            return {'A': 0, 'B': 0}
    
    @staticmethod
    def format_strength_message(a_strength, b_strength, a_max=100, b_max=100):
        """格式化强度消息
        
        将强度数据格式化为"strength-A+B+MAX"的消息字符串
        
        Args:
            a_strength (int): A通道强度
            b_strength (int): B通道强度
            a_max (int): A通道最大强度
            b_max (int): B通道最大强度
            
        Returns:
            str: 格式化后的强度消息
        """
        # 使用A通道的最大强度作为整体最大强度
        return f"strength-{a_strength}+{b_strength}+{a_max}"