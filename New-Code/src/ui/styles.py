import os  # 添加os模块导入

def get_style(accent_color, background_image=None):
    """获取应用样式表"""
    # 更新默认背景路径到src目录
    DEFAULT_BACKGROUND = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),  # 指向src目录
        'background.png'
    )
    if not background_image and os.path.exists(DEFAULT_BACKGROUND):
        background_image = DEFAULT_BACKGROUND
    
    # 基础颜色（从旧版迁移）
    base_bg = "#2b2b2b"
    text_color = "#ffffff"
    border_color = "#3f3f3f"
    hover_bg = "#3f3f3f"
    disabled_bg = "#404040"
    disabled_text = "#808080"
    
    # 背景图片样式（保持旧版处理方式）
    background_style = ""
    if background_image:
        bg_path = background_image.replace('\\', '/')
        background_style = f"""
            QMainWindow, QDialog {{
                background-image: url("{bg_path}");
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
        """
    
    return background_style + f"""
        /* 添加旧版字体设置 */
        QWidget {{
            font-family: "Microsoft YaHei";
            font-size: 10pt;
        }}
        
        /* 修复状态栏样式 */
        QStatusBar {{
            background: rgba(43, 43, 43, 180);
            color: {text_color};
        }}
        
        /* 添加旧版按钮悬停效果 */
        QPushButton:hover {{
            background-color: {hover_bg};
            border: 1px solid {accent_color};
        }}
        
        QMainWindow, QDialog {{
            background-color: {base_bg};
            color: {text_color};
        }}
        
        QGroupBox {{
            border: 1px solid rgba(63, 63, 63, 180);
            margin-top: 0.5em;
            padding-top: 0.5em;
            background-color: rgba(43, 43, 43, 120);
        }}
        
        QGroupBox::title {{
            color: {text_color};
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px;
        }}
        
        QPushButton {{
            background-color: {accent_color};
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 3px;
        }}
        
        QPushButton:hover {{
            background-color: {hover_bg};
        }}
        
        QLineEdit, QTextEdit, QComboBox {{
            background-color: rgba(43, 43, 43, 180);
            color: {text_color};
            border: 1px solid {border_color};
            padding: 3px;
            border-radius: 2px;
        }}
        
        QLabel {{
            color: {text_color};
            background-color: transparent;
        }}
        
        /* 新增旧版滚动条样式 */
        QScrollBar:vertical {{
            border: none;
            background-color: rgba(43, 43, 43, 120);
            width: 10px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background-color: rgba(63, 63, 63, 180);
            min-height: 20px;
            border-radius: 5px;
        }}
        
        /* 新增菜单栏样式 */
        QMenuBar {{
            background-color: rgba(43, 43, 43, 180);
            color: {text_color};
        }}
        QMenuBar::item:selected {{
            background-color: {hover_bg};
        }}
    """