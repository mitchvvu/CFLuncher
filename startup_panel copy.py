from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QGridLayout
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QTextCursor

# 导入 Fluent Widgets
from qfluentwidgets import (PrimaryPushButton, PushButton, TextEdit, 
                           CardWidget, StrongBodyLabel, BodyLabel,
                           MessageBox, InfoBar, InfoBarPosition, FluentIcon)

import os
import subprocess
import sys
from pathlib import Path
from process_manager import ComfyUIProcessManager

# 导入设置面板，用于获取Python解释器和ComfyUI路径
from settings_panel import SettingsPanel

class StartupPanel(QWidget):
    def __init__(self, data_model):
        super().__init__()
        self.data_model = data_model
        # 创建进程管理器
        self.process_manager = ComfyUIProcessManager(data_model)
        # 连接进程管理器信号
        self.process_manager.log_signal.connect(self.update_log)
        self.process_manager.status_changed.connect(self.update_ui_status)
        self.process_manager.error_occurred.connect(self.show_error_message)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 按钮区域卡片
        buttons_card = CardWidget()
        buttons_layout = QVBoxLayout(buttons_card)
        buttons_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = StrongBodyLabel("ComfyUI 控制")
        buttons_layout.addWidget(title_label)
        
        # 按钮区域布局
        buttons_row_layout = QHBoxLayout()
        
        # 启动按钮
        self.start_button = PrimaryPushButton("启动 ComfyUI")
        self.start_button.setIcon(FluentIcon.POWER_BUTTON)
        self.start_button.setMinimumHeight(50)
        self.start_button.clicked.connect(self.toggle_comfyui)
        buttons_row_layout.addWidget(self.start_button, 2)
        
        # 右侧按钮容器
        right_buttons_layout = QHBoxLayout()
        
        # 重启按钮
        self.restart_button = PushButton("重启")
        self.restart_button.setMinimumHeight(50)
        self.restart_button.clicked.connect(self.restart_comfyui)
        self.restart_button.setEnabled(False)  # 初始状态禁用
        right_buttons_layout.addWidget(self.restart_button)
        
        # 停止按钮
        self.stop_button = PushButton("停止")
        self.stop_button.setMinimumHeight(50)
        self.stop_button.clicked.connect(self.stop_comfyui)
        self.stop_button.setEnabled(False)  # 初始状态禁用
        right_buttons_layout.addWidget(self.stop_button)
        
        # 强行停止按钮
        self.force_stop_button = PushButton("强行停止")
        self.force_stop_button.setMinimumHeight(50)
        self.force_stop_button.clicked.connect(self.force_stop_all_python)
        right_buttons_layout.addWidget(self.force_stop_button)
        
        buttons_row_layout.addLayout(right_buttons_layout, 1)
        buttons_layout.addLayout(buttons_row_layout)
        
        layout.addWidget(buttons_card)
        
        # 文件夹快捷按钮区域卡片
        folders_card = CardWidget()
        folders_layout = QVBoxLayout(folders_card)
        folders_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        folders_title = StrongBodyLabel("文件夹快捷访问")
        folders_layout.addWidget(folders_title)
        
        # 使用网格布局放置六个按钮
        folders_grid = QGridLayout()
        folders_grid.setSpacing(10)
        
        # 创建六个按钮
        self.root_folder_button = PushButton("根目录")
        self.root_folder_button.setIcon(FluentIcon.FOLDER)
        self.root_folder_button.clicked.connect(self.open_root_folder)
        
        self.custom_nodes_button = PushButton("节点目录")
        self.custom_nodes_button.setIcon(FluentIcon.FOLDER)
        self.custom_nodes_button.clicked.connect(self.open_custom_nodes_folder)
        
        self.models_button = PushButton("模型目录")
        self.models_button.setIcon(FluentIcon.FOLDER)
        self.models_button.clicked.connect(self.open_models_folder)
        
        self.workflows_button = PushButton("用户工作流")
        self.workflows_button.setIcon(FluentIcon.FOLDER)
        self.workflows_button.clicked.connect(self.open_workflows_folder)
        
        self.input_folder_button = PushButton("输入文件夹")
        self.input_folder_button.setIcon(FluentIcon.FOLDER)
        self.input_folder_button.clicked.connect(self.open_input_folder)
        
        self.output_folder_button = PushButton("输出文件夹")
        self.output_folder_button.setIcon(FluentIcon.FOLDER)
        self.output_folder_button.clicked.connect(self.open_output_folder)
        
        # 将按钮添加到网格布局中
        folders_grid.addWidget(self.root_folder_button, 0, 0)
        folders_grid.addWidget(self.custom_nodes_button, 0, 1)
        folders_grid.addWidget(self.models_button, 0, 2)
        folders_grid.addWidget(self.workflows_button, 1, 0)
        folders_grid.addWidget(self.input_folder_button, 1, 1)
        folders_grid.addWidget(self.output_folder_button, 1, 2)
        
        folders_layout.addLayout(folders_grid)
        layout.addWidget(folders_card)
        
        # 日志输出区域卡片
        log_card = CardWidget()
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(20, 20, 20, 20)
        
        # 日志标题
        log_title = StrongBodyLabel("运行日志")
        log_layout.addWidget(log_title)
        
        # 使用 Fluent TextEdit 替代 QTextEdit
        self.log_text = TextEdit()
        self.log_text.setReadOnly(True)  # 只读模式
        self.log_text.setPlaceholderText("等待启动...")
        self.log_text.setMinimumHeight(300)  # 设置最小高度
        
        # 设置字体以支持特殊字符
        font = self.log_text.font()
        font.setFamily("Microsoft YaHei")
        self.log_text.setFont(font)

        # 添加日志控件
        log_layout.addWidget(self.log_text)
        
        # 添加按钮布局
        log_buttons_layout = QHBoxLayout()
        
        # 添加清空日志按钮
        clear_button = PushButton("清空日志")
        clear_button.clicked.connect(self.clear_log)
        log_buttons_layout.addWidget(clear_button)
        
        # 添加复制按钮
        copy_button = PushButton("复制日志")
        copy_button.clicked.connect(self.copy_log)
        log_buttons_layout.addWidget(copy_button)
        
        # 添加保存按钮
        save_button = PushButton("保存到文件")
        save_button.clicked.connect(self.save_log_to_file)
        log_buttons_layout.addWidget(save_button)
        
        log_buttons_layout.addStretch()  # 添加弹性空间
        
        log_layout.addLayout(log_buttons_layout)
        
        layout.addWidget(log_card)
        
        self.setLayout(layout)
        
        # 检查python_embeded是否存在
        self.check_python_embedded()
    
    def check_python_embedded(self):
        """检查Python解释器是否存在"""
        # 获取主窗口中的settings_panel实例
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'settings_panel'):
            main_window = main_window.parent()
        
        if main_window and hasattr(main_window, 'settings_panel'):
            # 使用settings_panel中的方法获取Python解释器路径
            python_path = main_window.settings_panel.get_python_exe_path()
            if not os.path.exists(python_path):
                self.start_button.setEnabled(False)
                self.log_text.setPlainText(f"Python解释器路径不存在: {python_path}")
        else:
            # 如果无法获取settings_panel实例，使用旧方法
            if not self.data_model.check_python_embedded():
                self.start_button.setEnabled(False)
                self.log_text.setPlainText("请先初始化实例，确保Python解释器存在")
    
    # 已移除 load_settings 和 save_settings 方法，因为它们的功能已移动到设置面板
        
    def settings_updated(self):
        """当设置面板中的设置被更新时调用"""
        # 更新进程管理器的数据模型
        self.process_manager = ComfyUIProcessManager(self.data_model)
        # 重新连接信号
        self.process_manager.log_signal.connect(self.update_log)
        self.process_manager.status_changed.connect(self.update_ui_status)
        self.process_manager.error_occurred.connect(self.show_error_message)
    
    def toggle_comfyui(self):
        """启动或停止ComfyUI"""
        if not self.process_manager.is_running():
            self.start_comfyui()
        else:
            self.stop_comfyui()
    
    def start_comfyui(self):
        """启动ComfyUI"""
        if self.process_manager.start_comfyui():
            self.start_button.setText("正在运行...")
            self.start_button.setEnabled(False)
            self.restart_button.setEnabled(True)
            self.stop_button.setEnabled(True)
    
    def stop_comfyui(self):
        """停止ComfyUI"""
        if self.process_manager.stop_comfyui():
            self.update_ui_status(False)
    
    def restart_comfyui(self):
        """重启ComfyUI"""
        self.process_manager.restart_comfyui()
    
    def update_ui_status(self, is_running):
        """更新UI状态"""
        print(f"启动面板接收到状态变化信号: {is_running}")
        if is_running:
            self.start_button.setText("正在运行...")
            self.start_button.setEnabled(False)
            self.restart_button.setEnabled(True)
            self.stop_button.setEnabled(True)
        else:
            self.start_button.setText("启动 ComfyUI")
            self.start_button.setEnabled(True)
            self.restart_button.setEnabled(False)
            self.stop_button.setEnabled(False)
        # 确保process_manager的状态与UI状态一致
        if self.process_manager.is_running() != is_running:
            print(f"警告：process_manager状态({self.process_manager.is_running()})与UI状态({is_running})不一致")
    
    def show_error_message(self, error_msg):
        """记录错误信息到日志（不再显示弹窗）"""
        # 只记录到日志，不显示弹窗
        self.update_log(f"\n错误: {error_msg}\n")
    
    def update_log(self, text):
        """更新日志显示，支持颜色"""
        # 将光标移动到末尾
        self.log_text.moveCursor(QTextCursor.End)
        
        # 解析ANSI颜色代码并应用HTML格式
        text = self._process_ansi_colors(text)
        
        # 插入HTML格式的文本
        self.log_text.insertHtml(text)
        
        # 滚动到底部
        self.log_text.ensureCursorVisible()
    
    def _process_ansi_colors(self, text):
        """处理ANSI颜色代码，转换为HTML格式"""
        import re
        
        # ANSI颜色代码映射到HTML颜色
        color_map = {
            '30': '#111111',  # black
            '31': '#BB0000',  # red
            '32': '#009900',  # green
            '33': '#FEB200',  # yellow
            '34': '#0909ff',  # blue
            '35': '#d020d0',  # magenta
            '36': '#00afaf',  # cyan
            '37': '#EEEEEE',  # white
            '90': '#808080',  # gray
            '91': '#FF6060',  # lightred
            '92': '#47d547',  # lightgreen
            '93': '#FEB201',  # lightyellow
            '94': '#6060FF',  # lightblue
            '95': '#e476e4',  # lightmagenta
            '96': '#83d0d0',  # lightcyan
            '97': '#EEEEEE'   # white
        }
        
        # 替换ANSI颜色代码为HTML标签
        # 匹配格式：\033[颜色代码m文本\033[0m
        pattern = r'\033\[(\d+)m([^\033]*)\033\[0m'
        
        def replace_color(match):
            color_code = match.group(1)
            content = match.group(2)
            # 将黑色文本也显示为白色EEEEEE
            html_color = color_map.get(color_code, '#EEEEEE')
            # 添加font-weight:bold使彩色文本显示为加粗效果
            return f'<span style="color:{html_color}; font-weight:bold;">{content}</span>'
        
        # 替换所有颜色代码
        colored_text = re.sub(pattern, replace_color, text)
        
        # 处理没有结束代码的情况
        pattern_no_end = r'\033\[(\d+)m([^\033]*)$'
        colored_text = re.sub(pattern_no_end, replace_color, colored_text)
        
        # 将换行符转换为HTML换行
        colored_text = colored_text.replace('\n', '<br>')
        
        # 如果没有任何颜色代码，将文本设置为白色EEEEEE
        if colored_text == text:
            text_with_br = text.replace('\n', '<br>')
            return f'<span style="color:#EEEEEE;">{text_with_br}</span>'
        
        return colored_text
    
    def copy_log(self):
        """复制日志内容到剪贴板"""
        self.log_text.selectAll()
        self.log_text.copy()
        # 取消选择
        cursor = self.log_text.textCursor()
        cursor.clearSelection()
        self.log_text.setTextCursor(cursor)
        
        # 使用 Fluent InfoBar 显示成功消息
        InfoBar.success(
            title="复制成功",
            content="日志内容已复制到剪贴板",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def clear_log(self):
        """清空日志内容"""
        self.log_text.clear()
        
        # 使用 Fluent InfoBar 显示成功消息
        InfoBar.success(
            title="清空成功",
            content="日志内容已清空",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def save_log_to_file(self):
        """保存日志内容到文本文件"""
        # 获取当前日期时间作为默认文件名
        from datetime import datetime
        default_filename = f"ComfyUI_Log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # 打开文件保存对话框
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存日志文件",
            default_filename,
            "文本文件 (*.txt);;所有文件 (*)"
        )
        
        # 如果用户选择了文件路径
        if file_path:
            try:
                # 获取日志内容
                log_content = self.log_text.toPlainText()
                
                # 写入文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                
                # 使用 Fluent InfoBar 显示成功消息
                InfoBar.success(
                    title="保存成功",
                    content=f"日志已保存到: {file_path}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
            except Exception as e:
                # 使用 Fluent InfoBar 显示错误消息
                InfoBar.error(
                    title="保存失败",
                    content=f"保存日志时出错: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
    
    def force_stop_all_python(self):
        """强行停止所有Python进程"""
        # 创建确认对话框
        message_box = MessageBox(
            '警告',
            '强行停止会终止系统中所有Python.exe进程，慎用！！！',
            self
        )
        # 设置对话框按钮
        message_box.yesButton.setText('确定')
        message_box.cancelButton.setText('取消')
        
        # 显示对话框并获取结果
        if message_box.exec():
            # 用户点击了确定按钮
            try:
                import subprocess
                self.update_log("正在查找并终止所有Python.exe进程...\n")
                # 使用taskkill命令终止所有python.exe进程
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", "python.exe"], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    text=True
                )
                
                # 输出结果
                if result.returncode == 0:
                    self.update_log("已成功终止所有Python.exe进程\n")
                    # 更新UI状态
                    self.update_ui_status(False)
                else:
                    self.update_log(f"终止进程时出现错误: {result.stderr}\n")
            except Exception as e:
                self.update_log(f"执行命令时出错: {str(e)}\n")
        else:
            # 用户点击了取消按钮，不执行任何操作
            pass
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        self.process_manager.stop_comfyui()
        event.accept()
    
    def get_comfyui_root_folder(self):
        """获取ComfyUI根目录路径"""
        # 获取主窗口中的settings_panel实例
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'settings_panel'):
            main_window = main_window.parent()
        
        if main_window and hasattr(main_window, 'settings_panel'):
            # 使用settings_panel中的方法获取ComfyUI路径
            return main_window.settings_panel.get_comfyui_path()
        else:
            # 如果无法获取settings_panel实例，使用旧方法
            # 如果设置了自定义Python解释器路径
            if self.data_model.get_bool('paths', 'custom_comfyui_path_enabled'):
                python_path = self.data_model.get_value('paths', 'comfyui_path')
                if python_path:
                    # 获取python.exe所在目录的上级目录下的ComfyUI文件夹
                    python_dir = os.path.dirname(python_path)
                    parent_dir = os.path.dirname(python_dir)
                    return os.path.join(parent_dir, 'ComfyUI')
            # 默认使用当前目录下的ComfyUI文件夹
            return os.path.join(os.getcwd(), "ComfyUI")
    
    def open_folder(self, folder_path):
        """打开指定文件夹"""
        try:
            # 确保路径格式正确
            folder_path = os.path.normpath(folder_path)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path, exist_ok=True)
                self.update_log(f"创建文件夹: {folder_path}\n")
            
            # 根据操作系统打开文件夹
            if sys.platform == 'win32':
                os.startfile(folder_path)
            elif sys.platform == 'darwin':  # macOS
                subprocess.run(['open', folder_path])
            else:  # Linux
                subprocess.run(['xdg-open', folder_path])
            
            self.update_log(f"打开文件夹: {folder_path}\n")
        except Exception as e:
            self.update_log(f"打开文件夹失败: {str(e)}\n")
    
    def open_root_folder(self):
        """打开ComfyUI根目录"""
        root_folder = self.get_comfyui_root_folder()
        self.open_folder(root_folder)
    
    def open_custom_nodes_folder(self):
        """打开自定义节点文件夹"""
        root_folder = self.get_comfyui_root_folder()
        custom_nodes_folder = os.path.join(root_folder, "custom_nodes")
        self.open_folder(custom_nodes_folder)
    
    def open_models_folder(self):
        """打开模型文件夹"""
        root_folder = self.get_comfyui_root_folder()
        models_folder = os.path.join(root_folder, "models")
        self.open_folder(models_folder)
    
    def open_workflows_folder(self):
        """打开用户工作流文件夹"""
        root_folder = self.get_comfyui_root_folder()
        workflows_folder = os.path.join(root_folder, "user", "default", "workflows")
        self.open_folder(workflows_folder)
    
    def open_input_folder(self):
        """打开输入文件夹"""
        # 获取主窗口中的settings_panel实例
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'settings_panel'):
            main_window = main_window.parent()
        
        # 检查是否启用了自定义输入文件夹
        if self.data_model.get_bool('advanced', 'input_dir_enabled'):
            input_folder = self.data_model.get_value('advanced', 'input_dir')
            if input_folder:
                self.open_folder(input_folder)
                return
        
        # 使用默认输入文件夹
        root_folder = self.get_comfyui_root_folder()
        input_folder = os.path.join(root_folder, "input")
        self.open_folder(input_folder)
    
    def open_output_folder(self):
        """打开输出文件夹"""
        # 获取主窗口中的settings_panel实例
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'settings_panel'):
            main_window = main_window.parent()
        
        # 检查是否启用了自定义输出文件夹
        if self.data_model.get_bool('advanced', 'output_dir_enabled'):
            output_folder = self.data_model.get_value('advanced', 'output_dir')
            if output_folder:
                self.open_folder(output_folder)
                return
        
        # 使用默认输出文件夹
        root_folder = self.get_comfyui_root_folder()
        output_folder = os.path.join(root_folder, "output")
        self.open_folder(output_folder)