from PySide6.QtCore import QTimer
from collections import deque
import pyqtgraph as pg
import numpy as np
from utils.i18n import i18n
import logging

class WaveManagerUI:
    """波形图管理UI逻辑"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.signals = main_window.signals
        
        # 初始化波形数据
        self.wave_data = {'A': [], 'B': []}
        self.wave_indices = {'A': [], 'B': []}
        self.wave_queues = {'A': deque(maxlen=100), 'B': deque(maxlen=100)}
        self.data_points = 0
        
        # 创建波形曲线
        self.curve_a = self.main_window.plot_widget_a.plot(pen=pg.mkPen(color=self.main_window.accent_color, width=2))
        self.curve_b = self.main_window.plot_widget_b.plot(pen=pg.mkPen(color=self.main_window.accent_color, width=2))
        
        # 设置波形图范围
        self.update_plot_ranges()
        
        # 设置波形图背景为透明
        self.main_window.plot_widget_a.setBackground(None)
        self.main_window.plot_widget_b.setBackground(None)
        
        # 设置信号连接
        self.setup_connections()
        
        # 初始化时清空两个通道的数据
        self.clear_channel_data('A')
        self.clear_channel_data('B')
        
    def setup_connections(self):
        """设置信号连接"""
        # 波形数据更新信号
        self.signals.wave_data_updated.connect(self.update_wave_data)
        # 强度设置更新信号
        self.signals.strength_changed.connect(self.update_plot_ranges)
        
    def update_plot_ranges(self):
        """更新波形图的显示范围"""
        # 从BLE管理器获取最大强度设置
        max_strength_a = self.main_window.ble_manager.max_strength['A']
        max_strength_b = self.main_window.ble_manager.max_strength['B']
        
        # 设置Y轴范围
        self.main_window.plot_widget_a.setYRange(0, max_strength_a)
        self.main_window.plot_widget_b.setYRange(0, max_strength_b)
        # X轴范围保持不变
        self.main_window.plot_widget_a.setXRange(0, 100)
        self.main_window.plot_widget_b.setXRange(0, 100)

    def update_wave_data(self, data_dict):
        """更新波形数据
        
        Args:
            data_dict: 包含通道和数据的字典，格式为：
                {
                    'channel': 'A' 或 'B',
                    'data': 强度值(整数)
                }
        """
        try:
            channel = data_dict.get('channel')
            data = data_dict.get('data')
            
            # 验证通道
            if not channel or channel not in ['A', 'B']:
                logging.warning(f"无效的通道: {channel}")
                return
                
            # 验证数据
            if data is None:
                logging.warning("数据为空")
                return
                
            # 确保数据是数值类型
            try:
                strength = float(data)
                # 限制强度不小于0，但上限跟随最大强度设置
                max_strength = self.main_window.ble_manager.max_strength[channel]
                strength = max(0, min(max_strength, strength))
            except (ValueError, TypeError):
                logging.error(f"无效的强度值: {data}")
                return
                
            # 添加数据点
            self.data_points += 1
            self.wave_queues[channel].append((self.data_points, strength))
            
            # 更新波形数据
            self.wave_indices[channel] = [p[0] for p in self.wave_queues[channel]]
            self.wave_data[channel] = [p[1] for p in self.wave_queues[channel]]
            
            # 更新曲线
            if channel == 'A':
                self.curve_a.setData(self.wave_indices[channel], self.wave_data[channel])
            else:
                self.curve_b.setData(self.wave_indices[channel], self.wave_data[channel])
                
            # 自动调整X轴范围，保持最近的100个点可见
            if self.wave_indices[channel]:
                max_x = max(self.wave_indices[channel])
                min_x = max_x - 100 if max_x > 100 else 0
                if channel == 'A':
                    self.main_window.plot_widget_a.setXRange(min_x, max_x)
                else:
                    self.main_window.plot_widget_b.setXRange(min_x, max_x)
                    
        except Exception as e:
            logging.error(f"更新波形数据失败: {str(e)}")
            self.signals.log_message.emit(f"更新波形数据失败: {str(e)}")
            
    # 删除init_test_data方法，不再生成测试数据
            
    def clear_channel_data(self, channel):
        """清除通道数据
        
        Args:
            channel: 通道标识('A'或'B')
        """
        try:
            if channel not in ['A', 'B']:
                logging.warning(f"无效的通道: {channel}")
                return
                
            # 清空队列
            self.wave_queues[channel].clear()
            self.wave_indices[channel] = []
            self.wave_data[channel] = []
            
            # 更新曲线
            if channel == 'A':
                self.curve_a.setData([], [])
                # 重置X轴范围
                self.main_window.plot_widget_a.setXRange(0, 100)
            else:
                self.curve_b.setData([], [])
                # 重置X轴范围
                self.main_window.plot_widget_b.setXRange(0, 100)
                
            self.signals.log_message.emit(i18n.translate("status_updates.queue_cleared", channel))
            
        except Exception as e:
            logging.error(f"清除通道{channel}数据失败: {str(e)}")
            self.signals.log_message.emit(f"清除通道{channel}数据失败: {str(e)}")

    def apply_theme(self):
        """应用主题样式，更新波形曲线颜色"""
        # 更新曲线颜色
        self.curve_a.setPen(pg.mkPen(color=self.main_window.accent_color, width=2))
        self.curve_b.setPen(pg.mkPen(color=self.main_window.accent_color, width=2))