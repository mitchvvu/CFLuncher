from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from qfluentwidgets import (
    CardWidget, StrongBodyLabel, BodyLabel, TextBrowser,
    setTheme, Theme
)

class AboutPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 主卡片
        main_card = CardWidget()
        main_layout = QVBoxLayout(main_card)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题
        title_label = StrongBodyLabel("ComfyUI 启动器")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 版本信息
        version_label = BodyLabel("版本 0.7.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_font = QFont()
        version_font.setPointSize(12)
        version_label.setFont(version_font)
        main_layout.addWidget(version_label)
        
        # 说明信息
        info_browser = TextBrowser()
        info_browser.setOpenExternalLinks(True)
        info_browser.setHtml("""
        <div style='text-align: center; font-family: "Segoe UI", sans-serif;'>
            <p style='font-size: 14px; margin: 20px 0;'>ComfyUI 启动器是一个简单的工具，用于在 Windows 平台上启动 ComfyUI，无需使用批处理文件。</p>
            <p style='font-size: 14px; font-weight: bold; margin: 15px 0;'>主要功能：</p>
            <ul style='text-align: left; font-size: 13px; margin: 10px 0; padding-left: 40px;'>
                <li style='margin: 8px 0;'>一键启动 ComfyUI</li>
                <li style='margin: 8px 0;'>配置代理设置</li>
                <li style='margin: 8px 0;'>启用局域网访问</li>
                <li style='margin: 8px 0;'>自定义节点管理</li>
                <li style='margin: 8px 0;'>依赖包管理</li>
                <li style='margin: 8px 0;'>其他高级启动参数支持</li>
            </ul>
            <p style='font-size: 12px; color: #666; margin-top: 30px;'>© 2025 ComfyUI 启动器</p>
        </div>
        """)
        info_browser.setMaximumHeight(300)
        main_layout.addWidget(info_browser)
        
        layout.addWidget(main_card)
        layout.addStretch()
        
        self.setLayout(layout)