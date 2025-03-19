from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget
from PySide6.QtCore import Qt
from utils.i18n import i18n
import logging

class DeviceScanner(QDialog):
    def __init__(self, parent=None, ble_manager=None):
        super().__init__(parent)
        self.ble_manager = ble_manager
        self.scan_task = None
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        self.setWindowTitle(str(i18n.translate("dialog.choose_device")))
        self.setGeometry(200, 200, 400, 400)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # 设备列表
        self.device_list = QListWidget()
        layout.addWidget(self.device_list)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        self.refresh_btn = QPushButton(str(i18n.translate("dialog.refresh_devices")))
        self.cancel_btn = QPushButton(str(i18n.translate("dialog.cancel")))
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        # 状态标签
        self.status_label = QLabel(str(i18n.translate("dialog.scanning")))
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
    def setup_connections(self):
        self.refresh_btn.clicked.connect(self.start_scan)
        self.cancel_btn.clicked.connect(self.reject)
        self.device_list.itemDoubleClicked.connect(self.on_device_selected)
        
    async def start_scan(self):
        """开始扫描设备"""
        self.refresh_btn.setEnabled(False)
        self.device_list.clear()
        self.status_label.setText(str(i18n.translate("dialog.scanning")))
        
        if self.ble_manager is None:
            self.status_label.setText(str(i18n.translate("dialog.scan_failed")))
            logging.error("BLE管理器未初始化")
            self.refresh_btn.setEnabled(True)
            return
        
        try:
            # 确保ble_manager有scan_devices方法
            if not hasattr(self.ble_manager, 'scan_devices'):
                raise AttributeError("BLE管理器缺少scan_devices方法")
                
            devices = await self.ble_manager.scan_devices()
            for name, address in devices:
                self.device_list.addItem(f"{name} | {address}")
            
            if not devices:
                self.status_label.setText(str(i18n.translate("dialog.no_devices_found")))
            else:
                self.status_label.setText(str(i18n.translate("dialog.scan_complete")))
                
        except Exception as e:
            logging.error(f"扫描失败: {str(e)}")
            self.status_label.setText(str(i18n.translate("dialog.scan_failed")))
            
        finally:
            self.refresh_btn.setEnabled(True)
            
    def on_device_selected(self, item):
        """处理设备选择"""
        address = item.text().split("|")[-1].strip()
        
        # 安全地访问parent和signals
        parent = self.parent()
        if parent and hasattr(parent, 'signals') and parent.signals:
            parent.signals.device_selected.emit(address)
        else:
            logging.error("无法发送设备选择信号：父窗口或信号对象不存在")
            
        self.accept()