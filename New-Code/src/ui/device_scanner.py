from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QLabel, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from utils.i18n import i18n
from utils.async_utils import asyncSlot
from .styles import get_style
import logging

class DeviceScanner(QDialog):
    def __init__(self, parent=None, ble_manager=None):
        super().__init__(parent)
        self.ble_manager = ble_manager
        self.scan_task = None
        self.selected_device = None
        self.init_ui()
        self.setup_connections()
        self.apply_theme()
        
    def init_ui(self):
        self.setWindowTitle(i18n.translate("dialog.choose_device"))
        self.setGeometry(200, 200, 500, 500)  # 使用旧版尺寸
        self.setModal(True)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)  # 使用旧版边距
        layout.setSpacing(15)  # 使用旧版间距
        
        # 标题标签
        title_label = QLabel(i18n.translate("dialog.choose_device"))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 设备列表
        self.device_list = QListWidget()
        self.device_list.setStyleSheet("""
            QListWidget {
                font-size: 12px;
                background-color: rgba(43, 43, 43, 180);
                border: 1px solid #3f3f3f;
                border-radius: 3px;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #3f3f3f;
                color: white;
            }
        """)
        layout.addWidget(self.device_list)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)  # 按钮间距
        self.refresh_btn = QPushButton(i18n.translate("dialog.refresh_devices"))
        self.cancel_btn = QPushButton(i18n.translate("dialog.cancel"))
        
        # 设置按钮大小与旧版一致
        self.refresh_btn.setFixedWidth(150)  # 调整为与旧版一致的大小
        self.cancel_btn.setFixedWidth(150)  # 调整为与旧版一致的大小
        
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # 状态标签
        self.status_label = QLabel(i18n.translate("dialog.scanning"))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #cccccc;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
    def setup_connections(self):
        self.refresh_btn.clicked.connect(self.start_scan)
        self.cancel_btn.clicked.connect(self.reject)
        self.device_list.itemDoubleClicked.connect(self.on_device_selected)
        
    def apply_theme(self):
        """应用主题样式"""
        # 获取父窗口的样式设置
        parent = self.parent()
        if parent and hasattr(parent, 'signals'):
            # 尝试从父窗口或settings获取颜色和背景图片
            accent_color = "#7f744f"  # 默认值
            background_image = ""
            
            if hasattr(parent, 'accent_color'):
                accent_color = parent.accent_color
                
            if hasattr(parent, 'background_image'):
                background_image = parent.background_image
                
            style_sheet = get_style(accent_color, background_image)
            self.setStyleSheet(style_sheet)
        
    @asyncSlot()
    async def start_scan(self):
        """开始扫描设备"""
        self.status_label.setText(i18n.translate("device.scanning"))
        self.device_list.clear()
        self.refresh_btn.setEnabled(False)
        
        try:
            # 检查蓝牙是否可用
            if not self.ble_manager.is_bluetooth_available():
                # 如果蓝牙不可用，先尝试再次检测
                if not await self.ble_manager.check_bluetooth_available():
                    self.status_label.setText(i18n.translate("error.bluetooth_not_available"))
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, 
                                       i18n.translate("error.bluetooth_not_available"),
                                       i18n.translate("error.bluetooth_not_available_message"))
                    self.refresh_btn.setEnabled(True)
                    return
                
            devices = await self.ble_manager.scan_devices()
            
            if devices:
                for name, address in devices:
                    item = QListWidgetItem(f"{name} ({address})")
                    item.setData(Qt.UserRole, address)  # 存储设备地址
                    self.device_list.addItem(item)
                self.status_label.setText(i18n.translate("device.scan_complete"))
            else:
                self.status_label.setText(i18n.translate("device.no_devices"))
                
        except Exception as e:
            self.status_label.setText(i18n.translate("device.scan_failed"))
            logging.error(f"扫描设备失败: {str(e)}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, 
                              i18n.translate("dialog.error"),
                              f"{i18n.translate('device.scan_failed')}: {str(e)}")
        
        self.refresh_btn.setEnabled(True)
            
    def on_device_selected(self, item):
        """处理设备选择"""
        address = item.data(Qt.UserRole)  # 获取存储的设备地址
        
        # 安全地访问parent和signals
        parent = self.parent()
        if parent and hasattr(parent, 'signals') and parent.signals:
            parent.signals.device_selected.emit(address)
        else:
            logging.error("无法发送设备选择信号：父窗口或信号对象不存在")
            
        self.accept()