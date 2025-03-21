import pyqtgraph as pg
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage
from config.settings import settings
import os

class RealTimeChart(QWidget):
    def __init__(self, parent=None, channel='A'):
        super().__init__(parent)
        self.channel = channel
        self.setup_ui()
        # 确保初始化后立即清除数据
        self.clear_data()
        
    def setup_ui(self):
        """设置UI组件"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建绘图窗口
        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)
        
        # 设置图表属性
        self.plot_widget.setLabel('left', '强度')
        self.plot_widget.setLabel('bottom', '时间' if self.channel == 'B' else '角度')
        self.plot_widget.showGrid(x=True, y=True)
        
        # 应用主题
        self.apply_theme()
        
        # 创建数据线
        pen = pg.mkPen(color='#00FF00', width=2)
        self.data_line = self.plot_widget.plot([], [], pen=pen)
        
        # 设置Y轴范围
        self.plot_widget.setYRange(0, 100)
        
        # 如果是A通道，设置X轴范围为0-100（角度）
        if self.channel == 'A':
            self.plot_widget.setXRange(0, 100)
        else:  # B通道
            self.plot_widget.setXRange(0, 100)  # 时间范围
            
        # 添加DG-LAB Logo作为背景
        self.add_background_logo()
    
    def add_background_logo(self):
        """添加DG-LAB Logo作为背景"""
        # 创建一个图像项
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets', 'dg_lab_logo.png')
        if os.path.exists(logo_path):
            logo_item = pg.ImageItem()
            logo_img = QImage(logo_path)
            logo_item.setImage(logo_img)
            # 设置图像位置和大小
            logo_item.setZValue(-100)  # 确保在数据线后面
            logo_item.setOpacity(0.2)  # 设置透明度
            # 添加到图表
            self.plot_widget.addItem(logo_item)
    
    def update_data(self, data):
        """更新图表数据
        
        Args:
            data: 新的数据点列表
        """
        if data and len(data) > 0:
            # 创建X轴数据
            x = np.linspace(0, 100, len(data))
            
            # 更新图表
            self.data_line.setData(x, data)
    
    def clear_data(self):
        """清除图表数据"""
        self.data_line.setData([], [])
    
    def apply_theme(self):
        """应用图表主题"""
        # 设置图表样式
        self.plot_widget.setBackground('#2D2D30')  # 深色背景
        
        # 设置坐标轴样式
        axis_pen = pg.mkPen(color='#888888', width=1)
        self.plot_widget.getAxis('left').setPen(axis_pen)
        self.plot_widget.getAxis('bottom').setPen(axis_pen)
        
        # 设置网格样式
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)