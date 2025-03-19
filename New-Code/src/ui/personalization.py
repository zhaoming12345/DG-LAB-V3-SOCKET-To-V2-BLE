from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QColorDialog, QFileDialog, QGroupBox,
    QSlider, QSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from utils.i18n import i18n
import os
from .styles import get_style

class PersonalizationDialog(QDialog):
    def __init__(self, parent=None, accent_color=None, background_image=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.translate("personalization.title"))
        self.setMinimumWidth(500)  # 使用旧版宽度
        self.setMinimumHeight(400)  # 使用旧版高度
        
        # 保存当前设置
        self.accent_color = accent_color or "#7f744f"
        self.background_image = background_image or ""
        
        # 创建布局
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)  # 使用旧版边距
        layout.setSpacing(15)  # 使用旧版间距
        
        # 创建标题标签
        title_label = QLabel(i18n.translate("personalization.title"))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 强调色设置
        color_group = QGroupBox(i18n.translate("personalization.accent_color"))
        color_layout = QVBoxLayout()  # 改为垂直布局
        
        # 颜色预览和RGB值
        preview_layout = QHBoxLayout()
        self.color_label = QLabel()
        self.color_label.setFixedSize(100, 30)  # 与旧版保持一致的预览大小
        self.color_label.setStyleSheet(f"background-color: {self.accent_color}; border: 1px solid #999;")
        
        self.color_value_label = QLabel(self.accent_color)
        preview_layout.addWidget(self.color_label)
        preview_layout.addWidget(self.color_value_label)
        preview_layout.addStretch()
        color_layout.addLayout(preview_layout)
        
        # 选择颜色按钮
        button_layout = QHBoxLayout()
        self.color_btn = QPushButton(i18n.translate("personalization.choose_color"))
        self.color_btn.setFixedWidth(150)  # 使用旧版按钮宽度
        self.color_btn.clicked.connect(self.choose_color)
        button_layout.addStretch()
        button_layout.addWidget(self.color_btn)
        button_layout.addStretch()
        color_layout.addLayout(button_layout)
        
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        
        # 背景图片设置
        bg_group = QGroupBox(i18n.translate("personalization.background"))
        bg_layout = QVBoxLayout()  # 改为垂直布局
        
        # 当前背景路径显示
        bg_path_layout = QHBoxLayout()
        path_label = QLabel(i18n.translate("personalization.current_background"))
        self.bg_label = QLabel(os.path.basename(self.background_image) if self.background_image else i18n.translate("personalization.no_background"))
        bg_path_layout.addWidget(path_label)
        bg_path_layout.addWidget(self.bg_label)
        bg_layout.addLayout(bg_path_layout)
        
        # 选择背景按钮
        bg_button_layout = QHBoxLayout()
        self.bg_btn = QPushButton(i18n.translate("personalization.choose_image"))
        self.bg_btn.setFixedWidth(150)  # 使用旧版按钮宽度
        self.bg_btn.clicked.connect(self.choose_background)
        bg_button_layout.addStretch()
        bg_button_layout.addWidget(self.bg_btn)
        bg_button_layout.addStretch()
        bg_layout.addLayout(bg_button_layout)
        
        bg_group.setLayout(bg_layout)
        layout.addWidget(bg_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton(i18n.translate("dialog.ok"))
        self.cancel_btn = QPushButton(i18n.translate("dialog.cancel"))
        self.ok_btn.setFixedWidth(120)  # 使用旧版按钮宽度
        self.cancel_btn.setFixedWidth(120)  # 使用旧版按钮宽度
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        # 应用主题
        self.apply_theme()
        
    def choose_color(self):
        # 创建自定义颜色对话框
        color_dialog = QColorDialog(QColor(self.accent_color), self)
        # 设置对话框标题
        color_dialog.setWindowTitle(i18n.translate("dialog.choose_color"))
        # 禁用Alpha通道
        color_dialog.setOption(QColorDialog.ShowAlphaChannel, False)
        
        # 使用自定义对话框而非原生对话框
        color_dialog.setOption(QColorDialog.DontUseNativeDialog, True)
        
        # 获取对话框中的按钮并设置文本
        buttons = color_dialog.findChildren(QPushButton)
        for button in buttons:
            if button.text() == "OK" or button.text() == "&OK":
                button.setText(i18n.translate("dialog.ok"))
            elif button.text() == "Cancel" or button.text() == "&Cancel":
                button.setText(i18n.translate("dialog.cancel"))
        
        if color_dialog.exec():
            self.accent_color = color_dialog.selectedColor().name()
            self.color_label.setStyleSheet(f"background-color: {self.accent_color}; border: 1px solid #999;")
            self.color_value_label.setText(self.accent_color)
            
    def choose_background(self):
        # 创建自定义文件对话框
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle(i18n.translate("dialog.choose_image"))
        file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.bmp)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        
        # 使用自定义对话框而非原生对话框
        file_dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        
        # 设置按钮文本
        buttons = file_dialog.findChildren(QPushButton)
        for button in buttons:
            if button.text() == "Open" or button.text() == "&Open":
                button.setText(i18n.translate("dialog.ok"))
            elif button.text() == "Cancel" or button.text() == "&Cancel":
                button.setText(i18n.translate("dialog.cancel"))
        
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                self.background_image = file_path
                self.bg_label.setText(os.path.basename(file_path))
            
    def get_settings(self):
        return {
            'accent_color': self.accent_color,
            'background_image': self.background_image
        }
        
    def apply_theme(self):
        """应用主题样式"""
        # 获取父窗口的样式设置
        parent = self.parent()
        if parent:
            # 使用当前设置的颜色和背景
            style_sheet = get_style(self.accent_color, self.background_image)
            self.setStyleSheet(style_sheet)