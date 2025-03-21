from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from datetime import datetime
from utils.i18n import i18n
from .styles import get_style
import logging
from utils.logger import log_emitter  # 导入日志信号发射器
from config.settings import settings  # 添加这一行，导入settings

class LogWindow(QMainWindow):
    # 添加关闭信号
    window_closed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.translate("log.title"))
        self.setGeometry(100, 100, 800, 500)  # 使用旧版尺寸
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(15, 15, 15, 15)  # 使用旧版边距
        layout.setSpacing(10)  # 使用旧版间距
        
        # 添加标题标签
        title_label = QLabel(i18n.translate("log.title"))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 日志文本区域
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("font-family: 'Consolas', monospace; font-size: 9pt;")  # 使用等宽字体
        layout.addWidget(self.log_area)
        
        # 清除按钮
        clear_btn = QPushButton(i18n.translate("log.clear"))
        clear_btn.clicked.connect(self.clear_log)
        layout.addWidget(clear_btn)
        
        # 连接日志信号
        log_emitter.log_signal.connect(self.append_log)
        
        # 应用样式
        self.apply_theme()
        
    def append_log(self, message):
        """添加日志消息到日志区域"""
        try:
            # 添加时间戳（如果消息中没有）
            if not message.startswith('['):
                from datetime import datetime
                timestamp = datetime.now().strftime('[%H:%M:%S]')
                message = f"{timestamp} {message}"
                
            self.log_area.append(message)
            # 自动滚动到底部
            scrollbar = self.log_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            logging.error(f"添加日志到UI失败: {str(e)}")
        
    def clear_log(self):
        """清除日志区域"""
        self.log_area.clear()
        logging.info("日志窗口已清空")
        
    def closeEvent(self, event: QCloseEvent):
        """窗口关闭事件处理"""
        self.window_closed.emit()
        logging.info("日志窗口已关闭")
        event.accept()

    def apply_theme(self):
        """应用主题样式"""
        self.setStyleSheet(get_style(settings.accent_color, settings.background_image))