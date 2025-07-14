import os  # 导入os模块，用于处理文件路径和检查文件是否存在

def get_style(accent_color, background_image=None):
    """
    获取应用样式表
    
    参数:
        accent_color: 强调色，用于按钮等UI元素
        background_image: 可选，背景图片路径。如果未提供，将使用默认背景
    
    返回:
        str: 包含完整Qt样式表的字符串
    """
    # 设置默认背景图片路径，指向src目录下的background.png
    DEFAULT_BACKGROUND = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),  # 获取当前文件所在目录(ui)的父目录(src)
        'background.png'
    )
    # 如果未提供背景图片且默认背景图片存在，则使用默认背景
    if not background_image and os.path.exists(DEFAULT_BACKGROUND):
        background_image = DEFAULT_BACKGROUND
    
    # 定义应用中使用的基础颜色（从旧版应用迁移过来的颜色方案）
    base_bg = "#2b2b2b"        # 基础背景色（深灰色）
    text_color = "#ffffff"      # 文本颜色（白色）
    border_color = "#3f3f3f"    # 边框颜色（中灰色）
    hover_bg = "#3f3f3f"        # 悬停背景色（中灰色）
    disabled_bg = "#404040"     # 禁用状态背景色（灰色）
    disabled_text = "#808080"   # 禁用状态文本颜色（浅灰色）
    
    # 处理背景图片样式
    background_style = ""
    if background_image:
        # 将Windows路径分隔符(\)转换为URL兼容的正斜杠(/)
        bg_path = background_image.replace('\\', '/')
        # 创建背景图片CSS样式
        background_style = f"""
            QMainWindow, QDialog {{
                background-image: url("{bg_path}");  /* 设置背景图片 */
                background-position: center;         /* 背景图片居中 */
                background-repeat: no-repeat;        /* 背景图片不重复 */
                background-attachment: fixed;        /* 背景图片固定，不随滚动条滚动 */
            }}
        """
    
    # 返回完整的样式表，包括背景样式和其他UI元素样式
    return background_style + f"""
        /* 全局字体设置 */
        QWidget {{
            font-family: "Microsoft YaHei";  /* 使用微软雅黑字体 */
            font-size: 10pt;                 /* 设置字体大小为10点 */
        }}
        
        /* 状态栏样式 */
        QStatusBar {{
            background: rgba(43, 43, 43, 180);  /* 半透明深灰色背景 */
            color: {text_color};                /* 使用定义的文本颜色 */
        }}
        
        /* 按钮悬停效果 */
        QPushButton:hover {{
            background-color: {hover_bg};      /* 悬停时的背景色 */
            border: 1px solid {accent_color};  /* 悬停时添加强调色边框 */
        }}
        
        /* 波形图控件样式 - 确保完全透明以便正确显示背景 */
        PyQtGraph {{
            background-color: transparent;  /* PyQtGraph控件透明背景 */
        }}
        QGraphicsView {{
            background-color: transparent;  /* 图形视图透明背景 */
        }}
        
        /* 主窗口和对话框基础样式 */
        QMainWindow, QDialog {{
            background-color: {base_bg};  /* 设置基础背景色 */
            color: {text_color};          /* 设置文本颜色 */
        }}
        
        /* 分组框样式 */
        QGroupBox {{
            border: 1px solid rgba(63, 63, 63, 180);  /* 半透明边框 */
            margin-top: 0.5em;                        /* 顶部外边距 */
            padding-top: 0.5em;                       /* 顶部内边距 */
            background-color: rgba(43, 43, 43, 120);  /* 轻度透明背景 */
        }}
        
        /* 分组框标题样式 */
        QGroupBox::title {{
            color: {text_color};        /* 标题文本颜色 */
            subcontrol-origin: margin;  /* 控制标题位置从margin开始 */
            left: 10px;                 /* 左侧位置 */
            padding: 0 3px;             /* 水平内边距 */
        }}
        
        /* 按钮基础样式 */
        QPushButton {{
            background-color: {accent_color};  /* 使用强调色作为按钮背景 */
            color: white;                      /* 按钮文本为白色 */
            border: none;                      /* 无边框 */
            padding: 5px 10px;                 /* 内边距 */
            border-radius: 3px;                /* 圆角边框 */
        }}
        
        /* 按钮悬停样式 */
        QPushButton:hover {{
            background-color: {hover_bg};  /* 悬停时背景色变化 */
        }}
        
        /* 按钮禁用状态样式 */
        QPushButton:disabled {{
            background-color: {disabled_bg};   /* 禁用时的背景色 */
            color: {disabled_text};            /* 禁用时的文本颜色 */
        }}
        
        /* 文本输入框、文本编辑区和下拉框样式 */
        QLineEdit, QTextEdit, QComboBox {{
            background-color: rgba(43, 43, 43, 180);  /* 半透明背景 */
            color: {text_color};                      /* 文本颜色 */
            border: 1px solid {border_color};         /* 边框 */
            padding: 3px;                             /* 内边距 */
            border-radius: 2px;                       /* 圆角边框 */
        }}
        
        /* 标签样式 */
        QLabel {{
            color: {text_color};           /* 标签文本颜色 */
            background-color: transparent;  /* 透明背景 */
        }}
        
        /* 垂直滚动条样式 */
        QScrollBar:vertical {{
            border: none;                           /* 无边框 */
            background-color: rgba(43, 43, 43, 120);  /* 轻度透明背景 */
            width: 10px;                            /* 宽度 */
            margin: 0px;                            /* 无外边距 */
        }}
        /* 垂直滚动条滑块样式 */
        QScrollBar::handle:vertical {{
            background-color: rgba(63, 63, 63, 180);  /* 半透明滑块 */
            min-height: 20px;                        /* 最小高度 */
            border-radius: 5px;                      /* 圆角 */
        }}
        
        /* 菜单栏样式 */
        QMenuBar {{
            background-color: rgba(43, 43, 43, 180);  /* 半透明背景 */
            color: {text_color};                      /* 文本颜色 */
        }}
        /* 菜单栏选中项样式 */
        QMenuBar::item:selected {{
            background-color: {hover_bg};  /* 选中时的背景色 */
        }}
    """