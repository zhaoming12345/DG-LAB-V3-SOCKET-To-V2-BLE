"""
协议转换模块 - 兼容性导入

此文件保留用于向后兼容，新代码应直接导入protocol包
"""

# 修正导入路径
from .protocol.converter import ProtocolConverter
from .protocol.constants import BLE_CHAR_PWM_A34, BLE_CHAR_PWM_B34, BLE_CHAR_PWM_AB2, BLE_CHAR_BATTERY

# 保留原有的类和常量，以保持向后兼容
__all__ = ['ProtocolConverter', 'BLE_CHAR_PWM_A34', 'BLE_CHAR_PWM_B34', 'BLE_CHAR_PWM_AB2', 'BLE_CHAR_BATTERY']