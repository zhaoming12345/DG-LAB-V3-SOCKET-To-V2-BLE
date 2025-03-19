from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QColor
import pyqtgraph as pg
from utils.i18n import i18n

class RealTimeChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_chart()
        self.apply_theme()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)  # 使用旧版边距
        layout.setSpacing(15)  # 使用旧版间距
        
        # 标题标签
        title_label = QLabel(i18n.translate("chart.real_time_waveform"))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 图表区域
        self.chart_widget = pg.PlotWidget()
        self.chart_widget.setBackground('transparent')
        self.chart_widget.setFixedHeight(300)  # 使用旧版高度
        layout.addWidget(self.chart_widget)
        
        self.setLayout(layout)
        
    def setup_chart(self):
        # 设置图表样式
        self.chart_widget.setBackground('transparent')
        self.chart_widget.showGrid(x=True, y=True)
        self.chart_widget.setLabel('left', i18n.translate("chart.amplitude"))
        self.chart_widget.setLabel('bottom', i18n.translate("chart.time"))
        
        # 设置坐标轴样式
        self.chart_widget.getAxis('left').setPen(pg.mkPen(color='#cccccc'))
        self.chart_widget.getAxis('bottom').setPen(pg.mkPen(color='#cccccc'))
        self.chart_widget.getAxis('left').setTextPen(pg.mkPen(color='#cccccc'))
        self.chart_widget.getAxis('bottom').setTextPen(pg.mkPen(color='#cccccc'))
        
        # 创建曲线
        self.curve = self.chart_widget.plot(pen=pg.mkPen(color='#00ff00', width=2))
        
    def apply_theme(self):
        # 应用主题样式
        if hasattr(self.parent(), 'settings'):
            settings = self.parent().settings
            accent_color = settings.get('accent_color', '#00ff00')
            
            # 更新曲线颜色
            self.curve.setPen(pg.mkPen(color=accent_color, width=2))
            
            # 更新坐标轴颜色
            self.chart_widget.getAxis('left').setPen(pg.mkPen(color=accent_color))
            self.chart_widget.getAxis('bottom').setPen(pg.mkPen(color=accent_color))
            self.chart_widget.getAxis('left').setTextPen(pg.mkPen(color=accent_color))
            self.chart_widget.getAxis('bottom').setTextPen(pg.mkPen(color=accent_color))
            
            # 更新网格颜色
            self.chart_widget.setBackground('transparent')
            self.chart_widget.showGrid(x=True, y=True, alpha=0.3)
            
    def update_data(self, data):
        self.curve.setData(data) 