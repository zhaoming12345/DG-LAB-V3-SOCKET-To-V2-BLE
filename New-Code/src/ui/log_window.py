from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from datetime import datetime
from utils.i18n import i18n
from .styles import get_style
import logging

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
        self.clear_btn = QPushButton(i18n.translate("log.clear"))
        self.clear_btn.setFixedWidth(150)  # 使用旧版按钮宽度
        self.clear_btn.clicked.connect(self.clear_logs)
        layout.addWidget(self.clear_btn, 0, Qt.AlignCenter)  # 居中对齐
        
        # 添加日志处理器
        self.log_handler = QTextEditHandler(self.log_area)
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                                      datefmt='%H:%M:%S'))
        logging.getLogger().addHandler(self.log_handler)
        
    def append_log(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_area.append(f"[{timestamp}] {message}")
        # 自动滚动到底部
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())
        
    def clear_logs(self):
        """清除所有日志"""
        self.log_area.clear()
        logging.info(i18n.translate("status_updates.logs_cleared"))
        
    def apply_theme(self, accent_color, background_image):
        """应用主题样式"""
        style_sheet = get_style(accent_color, background_image)
        self.setStyleSheet(style_sheet)
        
    def closeEvent(self, event: QCloseEvent):
        """窗口关闭事件处理"""
        # 移除日志处理器
        logging.getLogger().removeHandler(self.log_handler)
        self.window_closed.emit()
        event.accept()

class QTextEditHandler(logging.Handler):
    """自定义日志处理器，将日志输出到QTextEdit"""
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        
    def emit(self, record):
        msg = self.format(record)
        self.text_edit.append(msg)
        # 自动滚动到底部
        self.text_edit.verticalScrollBar().setValue(self.text_edit.verticalScrollBar().maximum())