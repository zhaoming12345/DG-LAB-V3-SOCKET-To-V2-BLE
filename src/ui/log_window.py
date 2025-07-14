from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QCloseEvent
from datetime import datetime
from utils.i18n import i18n
from .styles import get_style
import logging
from utils.logger import log_emitter  # 导入日志信号发射器
from config.settings import settings  # 导入settings

class LogWindow(QMainWindow):
    # 添加关闭信号
    window_closed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.translate("log.title"))
        self.setGeometry(100, 100, 800, 500)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 添加标题标签
        title_label = QLabel(i18n.translate("log.title"))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 日志文本区域
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("font-family: 'Consolas', monospace; font-size: 9pt;")
        layout.addWidget(self.log_area)
        
        # 清除按钮
        clear_btn = QPushButton(i18n.translate("log.clear"))
        clear_btn.clicked.connect(self.clear_log)
        layout.addWidget(clear_btn)
        
        # 初始化日志缓冲区和更新定时器
        self.log_buffer = []
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.flush_log_buffer)
        self.update_timer.setInterval(100)  # 每100ms更新一次
        self.update_timer.start()
        
        # 连接日志信号
        log_emitter.log_signal.connect(self.buffer_log)
        
        # 应用样式
        self.apply_theme()
        
    def buffer_log(self, message):
        """将日志消息添加到缓冲区"""
        try:
            # 添加时间戳（如果消息中没有）
            if not message.startswith('['):
                timestamp = datetime.now().strftime('[%H:%M:%S]')
                message = f"{timestamp} {message}"
            
            self.log_buffer.append(message)
            
        except Exception as e:
            logging.error(f"添加日志到缓冲区失败: {str(e)}")
            
    def flush_log_buffer(self):
        """将缓冲区中的日志消息批量更新到UI"""
        if not self.log_buffer:
            return
            
        try:
            # 获取当前滚动条位置
            scrollbar = self.log_area.verticalScrollBar()
            was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
            
            # 批量添加日志
            self.log_area.append('\n'.join(self.log_buffer))
            
            # 只有在之前滚动条在底部时才自动滚动
            if was_at_bottom:
                scrollbar.setValue(scrollbar.maximum())
                
            # 清空缓冲区
            self.log_buffer.clear()
            
        except Exception as e:
            logging.error(f"刷新日志缓冲区失败: {str(e)}")
        
    def clear_log(self):
        """清除日志区域"""
        self.log_area.clear()
        self.log_buffer.clear()
        logging.info("日志窗口已清空")
        
    def closeEvent(self, event: QCloseEvent):
        """窗口关闭事件处理"""
        self.update_timer.stop()  # 停止更新定时器
        self.window_closed.emit()
        logging.info("日志窗口已关闭")
        event.accept()

    def apply_theme(self):
        """应用主题样式"""
        self.setStyleSheet(get_style(settings.accent_color, settings.background_image))