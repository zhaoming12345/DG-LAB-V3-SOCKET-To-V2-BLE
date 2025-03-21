from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QLineEdit
)
import pyqtgraph as pg
from utils.i18n import i18n

def create_language_group():
    """创建语言设置组件"""
    group = QGroupBox(i18n.translate("language.setting"))
    layout = QHBoxLayout()
    
    # 语言选择下拉框
    combo = QComboBox()
    combo.setFixedWidth(200)  # 设置固定宽度，避免过小
    
    # 初始时阻止信号发射，避免在初始化时触发语言切换
    combo.blockSignals(True)
    
    layout.addWidget(combo)
    group.setLayout(layout)
    
    return group, combo

def create_device_group():
    """创建设备管理组件"""
    group = QGroupBox(i18n.translate("device.management"))
    layout = QVBoxLayout()
    
    # 设备标签
    device_label = QLabel(i18n.translate("label.no_device"))
    
    # 按钮布局
    btn_layout = QHBoxLayout()
    scan_btn = QPushButton(i18n.translate("device.scan"))
    connect_btn = QPushButton(i18n.translate("device.connect"))
    
    btn_layout.addWidget(scan_btn)
    btn_layout.addWidget(connect_btn)
    
    # 状态标签
    status_label = QLabel(i18n.translate("device.status", i18n.translate("device.disconnected")))
    
    layout.addWidget(device_label)
    layout.addLayout(btn_layout)
    layout.addWidget(status_label)
    
    group.setLayout(layout)
    
    return group, device_label, scan_btn, connect_btn, status_label

def create_server_group():
    """创建服务器配置组件"""
    group = QGroupBox(i18n.translate("server.config"))
    layout = QVBoxLayout()
    
    # 服务器地址输入
    addr_layout = QHBoxLayout()
    addr_label = QLabel(i18n.translate("server.address"))  # 确保使用正确的翻译键
    addr_input = QLineEdit()
    
    addr_layout.addWidget(addr_label)
    addr_layout.addWidget(addr_input)
    
    # 按钮布局
    btn_layout = QHBoxLayout()
    save_btn = QPushButton(i18n.translate("server.save"))
    connect_btn = QPushButton(i18n.translate("server.connect"))
    
    btn_layout.addWidget(save_btn)
    btn_layout.addWidget(connect_btn)
    
    layout.addLayout(addr_layout)
    layout.addLayout(btn_layout)
    
    group.setLayout(layout)
    
    return group, addr_input, save_btn, connect_btn

def create_strength_group():
    """创建强度配置组件"""
    group = QGroupBox(i18n.translate("strength.config"))
    layout = QVBoxLayout()
    
    # A通道强度限制
    a_layout = QHBoxLayout()
    a_label = QLabel(i18n.translate("strength.channel_a_limit"))  # 确保使用正确的翻译键
    a_input = QLineEdit()
    a_input.setFixedWidth(100)
    
    a_layout.addWidget(a_label)
    a_layout.addWidget(a_input)
    a_layout.addStretch()
    
    # B通道强度限制
    b_layout = QHBoxLayout()
    b_label = QLabel(i18n.translate("strength.channel_b_limit"))  # 确保使用正确的翻译键
    b_input = QLineEdit()
    b_input.setFixedWidth(100)
    
    b_layout.addWidget(b_label)
    b_layout.addWidget(b_input)
    b_layout.addStretch()
    
    # 保存按钮
    save_btn = QPushButton(i18n.translate("strength.save"))
    
    layout.addLayout(a_layout)
    layout.addLayout(b_layout)
    layout.addWidget(save_btn)
    
    group.setLayout(layout)
    
    return group, a_input, b_input, save_btn

def create_wave_group():
    """创建波形显示组件"""
    group = QGroupBox(i18n.translate("status.realtime"))
    layout = QVBoxLayout()
    
    # 状态标签
    status_layout = QHBoxLayout()
    
    a_status = QLabel(i18n.translate("status.channel_a", "0", "0"))
    b_status = QLabel(i18n.translate("status.channel_b", "0", "0"))
    battery_status = QLabel(i18n.translate("status.battery", "--"))
    signal_status = QLabel(i18n.translate("status.signal_unknown"))
    
    status_layout.addWidget(a_status)
    status_layout.addWidget(b_status)
    status_layout.addWidget(battery_status)
    status_layout.addWidget(signal_status)
    
    # 波形图
    plot_layout = QHBoxLayout()
    
    # A通道波形图
    plot_a = pg.PlotWidget()
    plot_a.setTitle(i18n.translate("status.wave_title_a"))
    plot_a.setLabel('left', i18n.translate("status.wave_y_label"))
    plot_a.setLabel('bottom', i18n.translate("status.wave_x_label"))
    plot_a.showGrid(x=True, y=True)
    
    # B通道波形图
    plot_b = pg.PlotWidget()
    plot_b.setTitle(i18n.translate("status.wave_title_b"))
    plot_b.setLabel('left', i18n.translate("status.wave_y_label"))
    plot_b.setLabel('bottom', i18n.translate("status.wave_x_label"))
    plot_b.showGrid(x=True, y=True)
    
    plot_layout.addWidget(plot_a)
    plot_layout.addWidget(plot_b)
    
    layout.addLayout(status_layout)
    layout.addLayout(plot_layout)
    
    group.setLayout(layout)
    
    return group, a_status, b_status, battery_status, signal_status, plot_a, plot_b