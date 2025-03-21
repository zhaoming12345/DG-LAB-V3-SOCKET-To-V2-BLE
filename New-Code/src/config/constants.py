import os
# 蓝牙服务UUID
# 基础UUID: 955Axxxx-0FE2-F5AA-A094-84B8D4F3E8AD (将xxxx替换为服务的UUID)
BLE_SERVICE_UUID = "955A180B-0FE2-F5AA-A094-84B8D4F3E8AD"  # 0x180B
BLE_CHAR_DEVICE_ID = "955A1501-0FE2-F5AA-A094-84B8D4F3E8AD"  # 设备ID特征
BLE_SERVICE_BATTERY = "955A180A-0FE2-F5AA-A094-84B8D4F3E8AD"  # 0x180A

# BLE特征值UUID
BLE_CHAR_PWM_AB2 = "955A1504-0FE2-F5AA-A094-84B8D4F3E8AD"  # 0x1504 AB两通道强度
BLE_CHAR_PWM_A34 = "955A1505-0FE2-F5AA-A094-84B8D4F3E8AD"  # 0x1505 A通道波形数据
BLE_CHAR_PWM_B34 = "955A1506-0FE2-F5AA-A094-84B8D4F3E8AD"  # 0x1506 B通道波形数据
BLE_CHAR_BATTERY = "955A1500-0FE2-F5AA-A094-84B8D4F3E8AD"  # 0x1500 电池电量

# 默认配置
DEFAULT_BACKGROUND_IMAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'background.png')
DEFAULT_MAX_STRENGTH = {'A': 100, 'B': 100}
DEFAULT_ACCENT_COLOR = "#7f744f"
DEFAULT_SOCKET_URI = "ws://192.168.31.115:8080/ws"
DEFAULT_LANGUAGE = "en_US"

# 日志文件路径
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'dg_lab.log')

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'dg_lab_config.json')