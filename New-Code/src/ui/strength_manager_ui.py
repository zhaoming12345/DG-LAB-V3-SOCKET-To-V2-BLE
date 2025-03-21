from PySide6.QtWidgets import QMessageBox
from qasync import asyncSlot
import asyncio  # 导入asyncio
import logging
from utils.i18n import i18n
from config.settings import settings

class StrengthManagerUI:
    """强度管理UI逻辑"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.ble_manager = main_window.ble_manager
        self.signals = main_window.signals
        self.setup_connections()
        self.load_strength_settings()
        
    def setup_connections(self):
        """设置信号连接"""
        # 保存强度设置按钮 - 使用asyncSlot
        # 修改这里，使用正确的方式连接异步槽函数
        self.main_window.save_strength_btn.clicked.connect(self.on_save_strength_clicked)
        # 强度变更信号
        self.signals.strength_changed.connect(self.update_strength_display)
        
    # 添加这个方法作为中间处理函数
    def on_save_strength_clicked(self):
        """保存按钮点击处理函数"""
        asyncio.create_task(self.save_strength_settings())
        # 添加日志，确认按钮点击被处理
        logging.info("保存强度设置按钮被点击")
        self.signals.log_message.emit("正在保存强度设置...")
        
    def load_strength_settings(self):
        """加载强度设置"""
        # 从设置加载最大强度
        a_max = self.ble_manager.max_strength['A']
        b_max = self.ble_manager.max_strength['B']
        
        # 记录日志，确认加载的值
        logging.info(f"加载强度设置到UI: A={a_max}, B={b_max}")
        
        # 设置输入框的值
        self.main_window.a_limit_input.setText(str(a_max))
        self.main_window.b_limit_input.setText(str(b_max))
        
        # 更新显示
        self.update_strength_display()
        
    async def save_strength_settings(self):
        """保存强度设置"""
        try:
            # 获取输入值
            a_max = int(self.main_window.a_limit_input.text())
            b_max = int(self.main_window.b_limit_input.text())
            
            # 验证范围
            if not (0 <= a_max <= 200) or not (0 <= b_max <= 200):
                QMessageBox.warning(
                    self.main_window,
                    i18n.translate("dialog.error"),
                    i18n.translate("error.strength_range")
                )
                self.signals.log_message.emit(i18n.translate("error.strength_range"))
                return
                
            # 记录旧值，用于日志
            old_a = self.ble_manager.max_strength['A']
            old_b = self.ble_manager.max_strength['B']
                
            # 更新BLE管理器中的最大强度
            self.ble_manager.max_strength['A'] = a_max
            self.ble_manager.max_strength['B'] = b_max
            
            # 同步更新Socket管理器中的最大强度
            self.main_window.socket_manager.max_strength['A'] = a_max
            self.main_window.socket_manager.max_strength['B'] = b_max
            
            # 保存到设置
            settings.max_strength_a = a_max
            settings.max_strength_b = b_max
            settings.save()
            
            self.signals.log_message.emit(i18n.translate("status_updates.strength_settings_updated", 
                                                        f"A: {old_a}->{a_max}, B: {old_b}->{b_max}"))
                
            # 更新显示
            self.update_strength_display()
            
            # 向服务器发送更新后的强度设置
            if self.main_window.socket_manager.ws:
                result = await self.main_window.socket_manager.send_strength_update()
                if result:
                    self.signals.log_message.emit("已向服务器发送更新后的强度设置")
                    logging.info("已向服务器发送更新后的强度设置")
                else:
                    self.signals.log_message.emit("向服务器发送强度设置失败")
                    logging.warning("向服务器发送强度设置失败")
                
        except ValueError:
            QMessageBox.warning(
                self.main_window,
                i18n.translate("dialog.error"),
                i18n.translate("error.invalid_number")
            )
            self.signals.log_message.emit(i18n.translate("error.invalid_number"))
            
    def update_strength_display(self):
        """更新强度显示"""
        # 更新A通道状态
        self.main_window.a_status.setText(i18n.translate(
            "status.channel_a", 
            self.ble_manager.current_strength['A'],
            self.ble_manager.max_strength['A']
        ))
        
        # 更新B通道状态
        self.main_window.b_status.setText(i18n.translate(
            "status.channel_b", 
            self.ble_manager.current_strength['B'],
            self.ble_manager.max_strength['B']
        ))