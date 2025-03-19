class ProtocolConverter:
    @staticmethod
    def v3_freq_to_v2(freq_input):
        """将V3协议的频率值转换为V2协议的参数"""
        # 确保频率在有效范围内
        freq_input = max(10, min(1000, freq_input))
        
        # 使用V2文档建议的公式
        x = int(((freq_input / 1000) ** 0.5) * 15)
        y = 1000 // freq_input - x
        
        # 确保x和y在有效范围内
        x = max(1, min(31, x))
        y = max(1, min(1023, y))
        
        return x, y
        
    @staticmethod
    def v3_intensity_to_v2_z(intensity):
        """将V3协议的强度值转换为V2协议的z参数"""
        return min(31, int(20 + (15 * (intensity/100))))
        
    @staticmethod
    def create_v2_command(channel, x, y, z):
        """创建V2协议命令"""
        return bytes([x, y & 0xFF, y >> 8, z])