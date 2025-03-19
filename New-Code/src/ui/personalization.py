from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QColorDialog, QFileDialog, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from utils.i18n import i18n
import os

class PersonalizationDialog(QDialog):
    def __init__(self, parent=None, accent_color=None, background_image=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.translate("personalization.title"))
        self.setMinimumWidth(400)
        
        # 保存当前设置
        self.accent_color = accent_color or "#7f744f"
        self.background_image = background_image or ""
        
        # 创建布局
        layout = QVBoxLayout()
        
        # 强调色设置
        color_group = QGroupBox(i18n.translate("personalization.accent_color"))
        color_layout = QHBoxLayout()
        self.color_label = QLabel(self.accent_color)
        self.color_label.setStyleSheet(f"background-color: {self.accent_color}; color: white; padding: 5px;")
        self.color_btn = QPushButton(i18n.translate("personalization.choose_color"))
        self.color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_label)
        color_layout.addWidget(self.color_btn)
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        
        # 背景图片设置
        bg_group = QGroupBox(i18n.translate("personalization.background"))
        bg_layout = QHBoxLayout()
        self.bg_label = QLabel(os.path.basename(self.background_image) if self.background_image else "")
        self.bg_btn = QPushButton(i18n.translate("personalization.choose_image"))
        self.bg_btn.clicked.connect(self.choose_background)
        bg_layout.addWidget(self.bg_label)
        bg_layout.addWidget(self.bg_btn)
        bg_group.setLayout(bg_layout)
        layout.addWidget(bg_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton(i18n.translate("dialog.ok"))
        self.cancel_btn = QPushButton(i18n.translate("dialog.cancel"))
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
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
            self.color_label.setText(self.accent_color)
            self.color_label.setStyleSheet(f"background-color: {self.accent_color}; color: white; padding: 5px;")
            
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