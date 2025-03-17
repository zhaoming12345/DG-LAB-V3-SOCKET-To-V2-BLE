import sys
import asyncio
import json
import struct
import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QGroupBox, QDialog, QListWidget
)
from PySide6.QtCore import Qt, Signal, QObject
from qasync import QEventLoop, asyncSlot
import websockets
from bleak import BleakClient, discover
from collections import deque

# ------------ 事件循环策略（Windows必需）------------
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ------------ 控制台Debug日志设置 ------------
logging.basicConfig(level=logging.DEBUG)

# ------------ 全局配置 ------------
SOCKET_URI = ""
BLE_DEVICE_ADDRESS = ""
DEVICE_ID = ""
DEFAULT_MAX_STRENGTH = {'A': 100, 'B': 100}

# ------------ 蓝牙服务配置 ------------
BLE_SERVICE_UUID = "955A180b-0FE2-F5AA-A094-84B8D4F3E8AD"
BLE_CHAR_PWM_AB2 = "955A1504-0FE2-F5AA-A094-84B8D4F3E8AD"
BLE_CHAR_PWM_A34 = "955A1505-0FE2-F5AA-A094-84B8D4F3E8AD"
BLE_CHAR_PWM_B34 = "955A1506-0FE2-F5AA-A094-84B8D4F3E8AD"
BLE_CHAR_DEVICE_ID = "955A1501-0FE2-F5AA-A094-84B8D4F3E8AD"

class DeviceScanner(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择蓝牙设备")
        self.setGeometry(200, 200, 400, 300)
        layout = QVBoxLayout()
        self.device_list = QListWidget()
        self.refresh_btn = QPushButton("刷新设备列表")
        layout.addWidget(self.device_list)
        layout.addWidget(self.refresh_btn)
        self.setLayout(layout)
        self.refresh_btn.clicked.connect(self.scan_devices)
        
    @asyncSlot()
    async def scan_devices(self):
        self.device_list.clear()
        devices = await discover()
        for d in devices:
            item_text = f"{d.name} | {d.address}" if d.name else f"Unknown Device | {d.address}"
            self.device_list.addItem(item_text)
        
class DeviceSignals(QObject):
    status_update = Signal(str, str)
    log_message = Signal(str)
    device_selected = Signal(str)
    device_id_updated = Signal(str)
    connection_changed = Signal(bool)
        
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.signals = DeviceSignals()
        self.ble_client = None
        self.wave_queues = {'A': deque(), 'B': deque()}
        self.current_strength = {'A': 0, 'B': 0}
        self.max_strength = DEFAULT_MAX_STRENGTH.copy()
        self.selected_device = ""
        
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        self.setWindowTitle("DG-LAB 控制器")
        self.setGeometry(100, 100, 800, 600)
        
        main_widget = QWidget()
        layout = QVBoxLayout()
        
        # 设备管理组
        device_group = QGroupBox("设备管理")
        device_layout = QHBoxLayout()
        self.scan_btn = QPushButton("扫描设备")
        self.connect_btn = QPushButton("连接设备")
        self.connect_btn.setEnabled(False)
        self.device_label = QLabel("当前设备: 未选择")
        device_layout.addWidget(self.scan_btn)
        device_layout.addWidget(self.connect_btn)
        device_layout.addWidget(self.device_label)
        device_group.setLayout(device_layout)
        
        # 配置区域
        config_group = QGroupBox("强度上限配置")
        # 服务器配置组
        server_group = QGroupBox("服务器配置")
        server_layout = QHBoxLayout()
        self.server_input = QLineEdit()
        self.save_server_btn = QPushButton("保存服务器地址")
        server_layout.addWidget(QLabel("服务器地址:"))
        server_layout.addWidget(self.server_input)
        server_layout.addWidget(self.save_server_btn)
        server_group.setLayout(server_layout)
        config_layout = QHBoxLayout()
        self.a_max_input = QLineEdit(str(self.max_strength['A']))
        self.b_max_input = QLineEdit(str(self.max_strength['B']))
        self.save_btn = QPushButton("保存配置")
        config_layout.addWidget(QLabel("A通道上限:"))
        config_layout.addWidget(self.a_max_input)
        config_layout.addWidget(QLabel("B通道上限:"))
        config_layout.addWidget(self.b_max_input)
        config_layout.addWidget(self.save_btn)
        config_group.setLayout(config_layout)
        
        # 状态显示
        status_group = QGroupBox("实时状态")
        status_layout = QHBoxLayout()
        self.a_status = QLabel(f"A通道强度: 0/{self.max_strength['A']}")
        self.b_status = QLabel(f"B通道强度: 0/{self.max_strength['B']}")
        status_layout.addWidget(self.a_status)
        status_layout.addWidget(self.b_status)
        status_group.setLayout(status_layout)
        
        # 控制按钮
        control_group = QGroupBox("手动控制")
        control_layout = QHBoxLayout()
        self.test_a_btn = QPushButton("测试A通道+10")
        self.test_b_btn = QPushButton("测试B通道+10")
        self.clear_a_btn = QPushButton("清空A队列")
        self.clear_b_btn = QPushButton("清空B队列")
        control_layout.addWidget(self.test_a_btn)
        control_layout.addWidget(self.test_b_btn)
        control_layout.addWidget(self.clear_a_btn)
        control_layout.addWidget(self.clear_b_btn)
        control_group.setLayout(control_layout)
        
        # 日志区域
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        
        # 布局组装
        layout.addWidget(device_group)
        layout.addWidget(config_group)
        layout.addWidget(server_group)
        layout.addWidget(status_group)
        layout.addWidget(control_group)
        layout.addWidget(self.log_area)
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)
        
    def setup_connections(self):
        self.scan_btn.clicked.connect(self.show_scanner)
        self.connect_btn.clicked.connect(self.on_connect_clicked)
        self.signals.device_selected.connect(self.update_device_address)
        self.signals.device_id_updated.connect(self.update_device_id)
        self.signals.connection_changed.connect(self.update_ui_state)
        self.signals.status_update.connect(self.update_status)
        self.signals.log_message.connect(self.log_output)
        self.save_btn.clicked.connect(self.update_max_strength)
        self.test_a_btn.clicked.connect(lambda: self.send_strength_command(1, 1, 10))
        self.test_b_btn.clicked.connect(lambda: self.send_strength_command(2, 1, 10))
        self.clear_a_btn.clicked.connect(lambda: self.clear_queue('A'))
        self.clear_b_btn.clicked.connect(lambda: self.clear_queue('B'))
        self.save_server_btn.clicked.connect(self.update_server_address)
        
    def show_scanner(self):
        scanner = DeviceScanner(self)
        scanner.device_list.itemDoubleClicked.connect(lambda: self.select_device(scanner))
        scanner.exec()
        
    def select_device(self, scanner):
        selected = scanner.device_list.currentItem().text()
        address = selected.split("|")[-1].strip()
        self.signals.device_selected.emit(address)
        scanner.close()
        
    def update_server_address(self):
        global SOCKET_URI
        SOCKET_URI = self.server_input.text()
        self.signals.log_message.emit(f"✅ 服务器地址已更新: {SOCKET_URI}")
        
    def update_device_address(self, address):
        global BLE_DEVICE_ADDRESS
        BLE_DEVICE_ADDRESS = address
        self.selected_device = address
        self.device_label.setText(f"已选设备: {address}")
        self.connect_btn.setEnabled(True)
        self.signals.log_message.emit(f"✅ 已选择设备: {address}")
        
    def update_device_id(self, device_id):
        global DEVICE_ID
        DEVICE_ID = device_id
        self.signals.log_message.emit(f"设备ID已更新: {device_id}")
        
    @asyncSlot()
    async def on_connect_clicked(self):
        if not self.selected_device:
            self.signals.log_message.emit("❌ 请先选择设备")
            return
            
        try:
            self.ble_client = BleakClient(BLE_DEVICE_ADDRESS)
            await self.ble_client.connect()
            self.signals.log_message.emit("🔵 蓝牙连接成功")
            await self.get_device_id()
            asyncio.create_task(self.process_wave_queues())
            asyncio.create_task(self.listen_websocket())
            self.signals.connection_changed.emit(True)
        except Exception as e:
            self.signals.log_message.emit(f"🔴 连接失败: {str(e)}")
            self.signals.connection_changed.emit(False)

    async def get_device_id(self):
        try:
            value = await self.ble_client.read_gatt_char(BLE_CHAR_DEVICE_ID)
            device_id = value.hex().upper()
            global DEVICE_ID
            DEVICE_ID = device_id
            self.signals.device_id_updated.emit(device_id)
            self.signals.log_message.emit(f"✅ 获取设备ID成功: {device_id}")
        except Exception as e:
            self.signals.log_message.emit(f"❌ 获取设备ID失败: {str(e)}")

    def update_ui_state(self, connected):
        self.connect_btn.setEnabled(not connected)
        self.scan_btn.setEnabled(not connected)
        self.device_label.setText(f"状态: {'已连接' if connected else '未连接'}")

    def update_status(self, channel, value):
        try:
            text = f"{channel}通道强度: {int(value)}/{self.max_strength[channel]}"
            if channel == 'A':
                self.a_status.setText(text)
            else:
                self.b_status.setText(text)
        except ValueError:
            self.signals.log_message.emit("❌ 状态更新值无效")

    def clear_queue(self, channel):
        self.wave_queues[channel].clear()
        self.signals.log_message.emit(f"♻️ 已清空{channel}通道队列")
        
    def log_output(self, message):
        self.log_area.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    async def send_ble_command(self, char_uuid, data):
        if self.ble_client and self.ble_client.is_connected:
            try:
                await self.ble_client.write_gatt_char(char_uuid, data)
                self.signals.log_message.emit(f"指令发送成功: {char_uuid[-4:]}")
            except Exception as e:
                self.signals.log_message.emit(f"发送失败: {str(e)}")

    def v3_freq_to_v2(self, freq_input):
        if 10 <= freq_input <= 100:
            x = max(1, int(freq_input**0.5 * 0.8))
            y = 1000 // freq_input - x
        elif 101 <= freq_input <= 600:
            scaled = (freq_input - 100)/5 + 100
            x = int(scaled**0.5 * 1.2)
            y = max(1, (1000//freq_input)-x)
        elif 601 <= freq_input <= 1000:
            x = int((freq_input**0.5)*0.5)
            y = max(1, (1000//freq_input)-x)
        else: x,y = 1,9
        return max(1,min(31,x)), max(1,min(1023,y))

    def v3_intensity_to_v2_z(self, intensity):
        return min(31, int(20 + (15 * (intensity/100))))

    def encode_pwm_ab2(self, a, b):
        a_val = min(int(a*2047/200),2047)
        b_val = min(int(b*2047/200),2047)
        return bytes([(a_val>>3)&0xFF, ((a_val&0x07)<<5)|((b_val>>6)&0x1F), (b_val&0x3F)<<2])

    def encode_pwm_channel(self, x, y, z):
        return struct.pack('<I', (z&0x1F)<<19 | (y&0x3FF)<<5 | (x&0x1F))[:3]

    async def process_wave_queues(self):
        while True:
            for ch in ['A','B']:
                if len(self.wave_queues[ch]) >=4:
                    params = [self.wave_queues[ch].popleft() for _ in range(4)]
                    avg_x = sum(p[0] for p in params)//4
                    avg_y = sum(p[1] for p in params)//4
                    avg_z = sum(p[2] for p in params)//4
                    data = self.encode_pwm_channel(avg_x, avg_y, avg_z)
                    char = BLE_CHAR_PWM_A34 if ch == 'A' else BLE_CHAR_PWM_B34
                    await self.send_ble_command(char, data)
            await asyncio.sleep(0.025)

    async def handle_strength_change(self, channel_num, mode, value):
        ch = 'A' if channel_num == 1 else 'B'
        try:
            current = self.current_strength[ch]
            if mode == 0: new = current - value
            elif mode == 1: new = current + value
            elif mode == 2: new = value
            else: return
            
            if new > self.max_strength[ch]:
                self.signals.log_message.emit(f"⚠️ {ch}通道超过上限{self.max_strength[ch]}")
                return
                
            new = max(0, min(new, self.max_strength[ch]))
            self.current_strength[ch] = new
            data = self.encode_pwm_ab2(self.current_strength['A'], self.current_strength['B'])
            await self.send_ble_command(BLE_CHAR_PWM_AB2, data)
            self.signals.status_update.emit(ch, str(new))
            
        except Exception as e:
            self.signals.log_message.emit(f"❌ 强度调节失败: {str(e)}")

    async def handle_socket_message(self, message):
        try:
            msg = json.loads(message)
            if msg["type"] != "msg": return
            
            cmd = msg["message"]
            if cmd.startswith("strength-"):
                parts = cmd[9:].split('+')
                await self.handle_strength_change(int(parts[0]), int(parts[1]), int(parts[2]))
            elif cmd.startswith("pulse-"):
                ch_part, wave_data = cmd[6:].split(':')
                channel = ch_part.upper()
                hex_waves = json.loads(wave_data)
                for hex_str in hex_waves[:100]:
                    freq = int(hex_str[:2],16)
                    intensity = int(hex_str[2:4],16)
                    x,y = self.v3_freq_to_v2(freq)
                    z = self.v3_intensity_to_v2_z(intensity)
                    self.wave_queues[channel].append((x,y,z))
            elif cmd.startswith("clear-"):
                channel = 'A' if cmd[6:] == '1' else 'B'
                self.wave_queues[channel].clear()
                self.signals.log_message.emit(f"♻️ 已清空{channel}通道队列")
                
        except Exception as e:
            self.signals.log_message.emit(f"❌ 消息处理错误: {str(e)}")

    def update_max_strength(self):
        try:
            self.max_strength['A'] = min(200, int(self.a_max_input.text()))
            self.max_strength['B'] = min(200, int(self.b_max_input.text()))
            self.signals.log_message.emit(f"✅ 强度上限更新: A={self.max_strength['A']} B={self.max_strength['B']}")
            self.update_status('A', self.current_strength['A'])
            self.update_status('B', self.current_strength['B'])
        except ValueError:
            self.signals.log_message.emit("❌ 请输入有效数字")

    async def listen_websocket(self):
        try:
            if not SOCKET_URI:
                self.signals.log_message.emit("❌ 请先设置服务器地址")
                return
            
            async with websockets.connect(SOCKET_URI) as ws:
                await ws.send(json.dumps({
                    "type": "bind",
                    "clientId": DEVICE_ID,
                    "targetId": "",
                    "message": "DGLAB"
                }))
                while True:
                    message = await ws.recv()
                    self.signals.log_message.emit(f"📥 收到指令: {message[:50]}...")
                    await self.handle_socket_message(message)
        except Exception as e:
            self.signals.log_message.emit(f"🔴 网络错误: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = MainWindow()
    window.show()
    
    with loop:
        loop.run_forever()
