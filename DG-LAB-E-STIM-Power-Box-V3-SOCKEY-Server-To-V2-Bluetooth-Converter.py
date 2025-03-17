# 这是一个转换程序，它会接收3.0socket指令并转换成2.0蓝牙指令，然后转发到设备，实现让3.0socket服务器向下兼容2.0设备的功能
import asyncio
import sys
import logging
import json
import struct
import websockets
from bleak import BleakClient
from collections import deque

# ------------ 配置项 ------------
SOCKET_URI = "ws://192.168.1.50:30/1234-123456789-12345-12345-01"  # 可以使用QR码识别软件获取
DEVICE_ID = "wj3548jjyaLTxavQPQVeGA=="  # 可以从https://github.com/DG-LAB-OPENSOURCE/DG-LAB-OPENSOURCE/blob/main/coyote/web/README.md获取
BLE_DEVICE_ADDRESS = "DF:F0:63:40:D5:A9"  # 可以通过Scan-Bluetooth-devices.py获取
MAX_STRENGTH = {
    'A': 50,  # A通道最大强度
    'B': 50   # B通道最大强度
}

# ------------ 蓝牙操作函数 ------------
async def send_ble_command(char_uuid, data):
    """向蓝牙设备发送指令"""
    if ble_client and ble_client.is_connected:
        try:
            await ble_client.write_gatt_char(char_uuid, data)
            logging.debug(f"成功发送数据到 {char_uuid}: {data.hex()}")
        except Exception as e:
            logging.error(f"蓝牙发送失败: {str(e)}")
    else:
        logging.warning("蓝牙未连接，忽略发送请求")

# ------------ 事件循环策略（Windows必需）------------
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ------------ 日志设置 ------------
logging.basicConfig(level=logging.DEBUG)

# ------------ 蓝牙服务配置(V2蓝牙特性) ------------
BLE_SERVICE_UUID = "955A180b-0FE2-F5AA-A094-84B8D4F3E8AD"
BLE_CHAR_PWM_AB2 = "955A1504-0FE2-F5AA-A094-84B8D4F3E8AD"
BLE_CHAR_PWM_A34 = "955A1505-0FE2-F5AA-A094-84B8D4F3E8AD"
BLE_CHAR_PWM_B34 = "955A1506-0FE2-F5AA-A094-84B8D4F3E8AD"

# ------------ 全局状态 ------------
ble_client = None
wave_queues = {"A": deque(), "B": deque()}
current_strength = {'A': 0, 'B': 0}
pending_strength_changes = {'A': 0, 'B': 0}

# ------------ V3波形转换核心逻辑 ------------
def v3_freq_to_v2(freq_input):
    """将V3频率输入(10-1000)转换为V2的X,Y值"""
    if 10 <= freq_input <= 100:
        x = max(1, int(freq_input ** 0.5 * 0.8))
        y = 1000 // freq_input - x
    elif 101 <= freq_input <= 600:
        scaled = (freq_input - 100) / 5 + 100
        x = int(scaled ** 0.5 * 1.2)
        y = max(1, (1000 // freq_input) - x)
    elif 601 <= freq_input <= 1000:
        x = int((freq_input ** 0.5) * 0.5)
        y = max(1, (1000 // freq_input) - x)
    else:
        x, y = 1, 9  # 默认100Hz
    
    x = max(1, min(31, x))
    y = max(1, min(1023, y))
    return x, y

def v3_intensity_to_v2_z(intensity):
    """将V3强度(0-100)转换为V2的Z值"""
    base_width = 20  # 基准宽度对应20
    dynamic_range = intensity / 100.0
    return min(31, int(base_width + (15 * dynamic_range)))

# ------------ 蓝牙数据编码 ------------
def encode_pwm_ab2(a_strength, b_strength):
    a = min(int(a_strength * 2047 / 200), 2047)
    b = min(int(b_strength * 2047 / 200), 2047)
    return bytes([
        (a >> 3) & 0xFF,
        ((a & 0x07) << 5) | ((b >> 6) & 0x1F),
        (b & 0x3F) << 2
    ])

def encode_pwm_channel(x, y, z):
    """编码单个通道波形数据"""
    return struct.pack('<I', 
        (z & 0x1F) << 19 |
        (y & 0x3FF) << 5 |
        (x & 0x1F)
    )[:3]

# ------------ 波形队列处理 ------------
async def process_wave_queues():
    global ble_client
    while True:
        for channel in ['A', 'B']:
            if len(wave_queues[channel]) >= 4:
                # 取4个25ms段合并为100ms数据
                params = [wave_queues[channel].popleft() for _ in range(4)]
                
                # 计算平均参数（可根据需求改为其他逻辑）
                avg_x = sum(p[0] for p in params) // 4
                avg_y = sum(p[1] for p in params) // 4
                avg_z = sum(p[2] for p in params) // 4
                
                # 编码并发送
                data = encode_pwm_channel(avg_x, avg_y, avg_z)
                char = BLE_CHAR_PWM_A34 if channel == 'A' else BLE_CHAR_PWM_B34
                await send_ble_command(char, data)
        
        await asyncio.sleep(0.025)  # 25ms周期
async def handle_socket_message(message):
    global wave_queues  # 声明使用全局变量
    
    try:
        msg = json.loads(message)
        if msg["type"] != "msg":
            return

        cmd = msg["message"]
        
        # 处理清空指令
        if cmd.startswith("clear-"):
            channel = "B" if cmd.split("-")[1] == "2" else "A"
            wave_queues[channel].clear()
            print(f"已清空通道 {channel} 的波形队列")
            
    except Exception as e:
        print(f"消息处理错误: {str(e)}")

# ------------ 强度变化处理 ------------
async def handle_strength_change(channel, mode, value):
    global current_strength, pending_strength_changes
    
    # 获取当前通道类型（'A'或'B'）
    ch = 'A' if channel == 1 else 'B'
    max_strength = MAX_STRENGTH[ch]
    
    try:
        if mode == 0:  # 减少
            new_value = current_strength[ch] - value
        elif mode == 1:  # 增加
            new_value = current_strength[ch] + value
            # 上限检查
            if new_value > max_strength:
                logging.warning(f"通道{ch}强度已达上限 {max_strength}，忽略增加请求")
                return
        elif mode == 2:  # 设为指定值
            new_value = value
            if new_value > max_strength:
                logging.warning(f"通道{ch}指定强度 {new_value} 超过上限 {max_strength}")
                return

        # 应用范围限制
        new_value = max(0, min(new_value, max_strength))
        
        # 更新强度值
        current_strength[ch] = new_value
        
        # 发送蓝牙指令
        data = encode_pwm_ab2(current_strength['A'], current_strength['B'])
        await send_ble_command(BLE_CHAR_PWM_AB2, data)
        logging.info(f"通道{ch}强度已更新为：{new_value}")

    except Exception as e:
        logging.error(f"强度处理失败：{str(e)}")

# ------------ WebSocket消息处理 ------------
async def handle_socket_message(message):
    try:
        msg = json.loads(message)
        if msg["type"] != "msg":
            return

        cmd = msg["message"]
        
        # 处理强度变化
        if cmd.startswith("strength-"):
            parts = cmd[9:].split('+')
            channel = int(parts[0])
            mode = int(parts[1])
            value = int(parts[2])
            await handle_strength_change('A' if channel==1 else 'B', mode, value)
        
        # 处理波形数据
        elif cmd.startswith("pulse-"):
            channel_part, wave_data = cmd[6:].split(':')
            channel = channel_part.upper()
            hex_waves = json.loads(wave_data)
            
            for hex_str in hex_waves[:100]:  # 限制最多100条
                # 解析V3波形数据（根据实际协议可能需要调整）
                freq = int(hex_str[:2], 16)
                intensity = int(hex_str[2:4], 16)
                x, y = v3_freq_to_v2(freq)
                z = v3_intensity_to_v2_z(intensity)
                wave_queues[channel].append((x, y, z))
        
        # 处理清空队列
        elif cmd.startswith("clear-"):
            channel = 'A' if cmd[6:] == '1' else 'B'
            wave_queues[channel].clear()

    except Exception as e:
        print(f"消息处理错误: {str(e)}")

# ------------ 主程序 ------------
async def main():
    global ble_client
    
    try:
        # 连接蓝牙
        logging.info(f"尝试连接设备: {BLE_DEVICE_ADDRESS}")
        ble_client = BleakClient(BLE_DEVICE_ADDRESS)
        await ble_client.connect(timeout=15.0)
        logging.info("蓝牙连接成功！")

        # 启动波形处理任务
        asyncio.create_task(process_wave_queues())

        # 连接WebSocket服务器
        async with websockets.connect(SOCKET_URI) as ws:
            await ws.send(json.dumps({
                "type": "bind",
                "clientId": DEVICE_ID,
                "targetId": "",
                "message": "DGLAB"
            }))
            
            while True:
                message = await ws.recv()
                await handle_socket_message(message)
                
    except Exception as e:
        logging.error(f"发生致命错误: {str(e)}")
    finally:
        if ble_client and ble_client.is_connected:
            await ble_client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())