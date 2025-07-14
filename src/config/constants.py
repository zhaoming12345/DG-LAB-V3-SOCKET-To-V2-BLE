import os
# 使用基础UUID: 955Axxxx-0FE2-F5AA-A094-84B8D4F3E8AD (将xxxx替换为服务的UUID)
BLE_SERVICE_UUID = "955A180B-0FE2-F5AA-A094-84B8D4F3E8AD"  # 0x180B 蓝牙服务UUID
BLE_CHAR_DEVICE_ID = "955A1501-0FE2-F5AA-A094-84B8D4F3E8AD"  # 0x1501 设备ID
BLE_SERVICE_BATTERY = "955A180A-0FE2-F5AA-A094-84B8D4F3E8AD"  # 0x180A 电池服务

# BLE特征值UUID
BLE_CHAR_PWM_AB2 = "955A1504-0FE2-F5AA-A094-84B8D4F3E8AD"  # 0x1504 AB两通道强度
BLE_CHAR_PWM_A34 = "955A1505-0FE2-F5AA-A094-84B8D4F3E8AD"  # 0x1505 A通道波形数据
BLE_CHAR_PWM_B34 = "955A1506-0FE2-F5AA-A094-84B8D4F3E8AD"  # 0x1506 B通道波形数据
BLE_CHAR_BATTERY = "955A1500-0FE2-F5AA-A094-84B8D4F3E8AD"  # 0x1500 电池电量

# 默认配置
DEFAULT_BACKGROUND_IMAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'background.png')  # 默认背景图片路径
DEFAULT_MAX_STRENGTH = {'A': 100, 'B': 100}  # 默认最大强度，与官方APP一致
DEFAULT_ACCENT_COLOR = "#7f744f"  # 默认界面强调色
DEFAULT_SOCKET_URI = "ws://127.0.0.1:9999/1234-123456789-12345-12345-01"  # 默认SOCKET服务器地址为本地回环地址，默认端口与《我的世界》的DG-LAB模组的默认端口一致
DEFAULT_LANGUAGE = "zh_CN"  # 默认中文语言

# 日志文件路径
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')  # 日志文件夹路径为.\logs
LOG_FILE = os.path.join(LOG_DIR, 'DG-LAB-V3-SOCKET-To-V2-BLE.log')  # 日志文件名称为“DG-LAB-V3-SOCKET-To-V2-BLE.log”

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')  # 配置文件名称为“confng.json”
