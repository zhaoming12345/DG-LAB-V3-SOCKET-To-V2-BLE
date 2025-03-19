from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTextEdit, QPushButton
from datetime import datetime
from utils.i18n import i18n

class LogWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.translate("log.title"))
        self.setGeometry(100, 100, 600, 400)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        
        # 日志文本区域
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        
        # 清除按钮
        self.clear_btn = QPushButton(i18n.translate("log.clear"))
        self.clear_btn.clicked.connect(self.clear_logs)
        layout.addWidget(self.clear_btn)
        
    def append_log(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_area.append(f"[{timestamp}] {message}")
        
    def clear_logs(self):
        """清除所有日志"""
        self.log_area.clear()