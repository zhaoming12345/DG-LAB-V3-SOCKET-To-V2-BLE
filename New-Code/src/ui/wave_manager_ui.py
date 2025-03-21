from PySide6.QtCore import QTimer
from collections import deque
import pyqtgraph as pg
import numpy as np
from utils.i18n import i18n

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
        self.curve_a = self.main_window.plot_widget_a.plot(pen=pg.mkPen(color='#00ff00', width=2))
        self.curve_b = self.main_window.plot_widget_b.plot(pen=pg.mkPen(color='#00ff00', width=2))
        
        # 设置波形图范围
        self.main_window.plot_widget_a.setYRange(0, 100)
        self.main_window.plot_widget_a.setXRange(0, 100)
        self.main_window.plot_widget_b.setYRange(0, 100)
        self.main_window.plot_widget_b.setXRange(0, 100)
        
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
        
    def update_wave_data(self, data_dict):
        """更新波形数据
        
        Args:
            data_dict: 包含通道和数据的字典
        """
        channel = data_dict.get('channel')
        data = data_dict.get('data')
        
        if not channel or not data or channel not in ['A', 'B']:
            return
            
        # 添加数据点
        self.data_points += 1
        self.wave_queues[channel].append((self.data_points, data))
        
        # 更新波形数据
        self.wave_indices[channel] = [p[0] for p in self.wave_queues[channel]]
        self.wave_data[channel] = [p[1] for p in self.wave_queues[channel]]
        
        # 更新曲线
        if channel == 'A':
            self.curve_a.setData(self.wave_indices[channel], self.wave_data[channel])
        else:
            self.curve_b.setData(self.wave_indices[channel], self.wave_data[channel])
            
        # 自动调整X轴范围
        if self.wave_indices[channel]:
            min_x = min(self.wave_indices[channel])
            max_x = max(self.wave_indices[channel])
            if channel == 'A':
                self.main_window.plot_widget_a.setXRange(min_x, max_x)
            else:
                self.main_window.plot_widget_b.setXRange(min_x, max_x)
    
    # 删除init_test_data方法，不再生成测试数据
            
    def clear_channel_data(self, channel):
        """清除通道数据
        
        Args:
            channel: 通道标识('A'或'B')
        """
        if channel not in ['A', 'B']:
            return
            
        # 清空队列
        self.wave_queues[channel].clear()
        self.wave_indices[channel] = []
        self.wave_data[channel] = []
        
        # 更新曲线
        if channel == 'A':
            self.curve_a.setData([], [])
        else:
            self.curve_b.setData([], [])
            
        self.signals.log_message.emit(i18n.translate("status_updates.queue_cleared", channel))