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
        
        # 设置输入框的值 - 修正组件名称
        self.main_window.a_limit_input.setText(str(a_max))
        self.main_window.b_limit_input.setText(str(b_max))
        
        # 更新显示
        self.update_strength_display()
        
    @asyncSlot()
    async def save_strength_settings(self):
        """保存强度设置"""
        try:
            # 获取当前设置的值
            a_max = int(self.main_window.a_limit_input.text())
            b_max = int(self.main_window.b_limit_input.text())
            
            # 验证输入值
            if a_max < 0 or a_max > 200 or b_max < 0 or b_max > 200:
                self.signals.log_message.emit("强度值必须在0-200范围内")
                return False
            
            # 更新BLE管理器的最大强度设置
            self.main_window.ble_manager.max_strength['A'] = a_max
            self.main_window.ble_manager.max_strength['B'] = b_max
            
            # 更新Socket管理器的最大强度设置
            self.main_window.socket_manager.max_strength['A'] = a_max
            self.main_window.socket_manager.max_strength['B'] = b_max
            
            # 更新设置对象
            settings.max_strength_a = a_max
            settings.max_strength_b = b_max
            
            # 保存设置到文件
            settings.save()
            
            # 记录日志
            self.main_window.signals.log_message.emit(f"最大强度设置已保存: A={a_max}, B={b_max}")
            logging.info(f"保存的最大强度: A={a_max}, B={b_max}")
            
            # 如果Socket已连接，发送更新到服务器
            if self.main_window.socket_manager.is_connected:
                try:
                    # 发送强度更新
                    await self.main_window.socket_manager.send_strength_update()
                    self.main_window.signals.log_message.emit("已发送强度更新到服务器")
                except Exception as e:
                    self.main_window.signals.log_message.emit(f"发送强度更新到服务器失败: {str(e)}")
                    logging.error(f"发送强度更新到服务器失败: {str(e)}")
            
            return True
        except ValueError:
            self.main_window.signals.log_message.emit("请输入有效的数字")
            logging.error("保存强度设置失败: 输入的不是有效数字")
            return False
        except Exception as e:
            self.main_window.signals.log_message.emit(f"保存强度设置失败: {str(e)}")
            logging.error(f"保存强度设置失败: {str(e)}")
            return False
    
    def update_strength_display(self):
        """更新强度显示"""
        try:
            # 更新当前强度显示
            a_strength = self.ble_manager.current_strength['A']
            b_strength = self.ble_manager.current_strength['B']
            
            # 更新最大强度显示
            a_max = self.ble_manager.max_strength['A']
            b_max = self.ble_manager.max_strength['B']
            
            # 更新UI显示
            self.main_window.a_strength_label.setText(f"A: {a_strength}/{a_max}")
            self.main_window.b_strength_label.setText(f"B: {b_strength}/{b_max}")
            
            # 记录日志
            logging.debug(f"更新强度显示: A={a_strength}/{a_max}, B={b_strength}/{b_max}")
        except Exception as e:
            logging.error(f"更新强度显示失败: {str(e)}")