import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from PySide6.QtCore import Signal, QTimer
from PySide6.QtGui import QIntValidator, QDoubleValidator
from qfluentwidgets import (
    CheckBox, LineEdit, BodyLabel, PrimaryPushButton, 
    PushButton, CardWidget, StrongBodyLabel, SpinBox, 
    ComboBox, TextEdit, MessageBox, InfoBar, InfoBarPosition,
    FluentIcon
)
from data_model import DataModel
from process_manager import ComfyUIProcessManager

class SettingsPanel(QWidget):
    # 定义信号
    settings_changed = Signal()
    
    def __init__(self, data_model, process_manager):
        super().__init__()
        self.data_model = data_model
        self.process_manager = process_manager
        # 连接进程状态变化信号
        self.process_manager.status_changed.connect(self.update_save_button_state)
        print("已连接process_manager.status_changed信号到update_save_button_state方法")
        self.init_ui()
        self.load_settings()
        # 初始化保存按钮状态
        is_running = self.process_manager.is_running()
        print(f"初始化时ComfyUI运行状态: {is_running}")
        self.update_save_button_state(is_running)
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 代理设置卡片
        proxy_card = CardWidget()
        proxy_layout = QVBoxLayout()
        proxy_layout.addWidget(StrongBodyLabel("代理设置"))
        
        # 启用代理复选框（合并了两个功能）
        self.proxy_checkbox = CheckBox("启用代理（仅对启动面板生效）")
        proxy_layout.addWidget(self.proxy_checkbox)
        
        # HTTP代理、HTTPS代理和代理端口放在一行
        proxy_row_layout = QHBoxLayout()
        
        # 代理类型下拉选单
        proxy_type_layout = QHBoxLayout()
        # proxy_type_label = BodyLabel("代理类型:")
        # proxy_type_label.setFixedWidth(200)
        # proxy_type_layout.addWidget(proxy_type_label)
        self.proxy_type_combobox = ComboBox()
        self.proxy_type_combobox.addItem("系统代理", "system")
        self.proxy_type_combobox.addItem("Socks5代理", "socks5")
        self.proxy_type_combobox.currentIndexChanged.connect(self.update_proxy_display)
        self.proxy_type_combobox.setFixedWidth(160)  # 设置下拉框固定宽度
        proxy_type_layout.addWidget(self.proxy_type_combobox)
        proxy_row_layout.addLayout(proxy_type_layout)
        
        # 代理网址
        proxy_url_layout = QHBoxLayout()
        proxy_url_layout.addWidget(BodyLabel("代理网址:"))
        self.http_proxy_edit = LineEdit()
        self.http_proxy_edit.setFixedWidth(350)  # 设置输入框固定宽度
        proxy_url_layout.addWidget(self.http_proxy_edit)
        proxy_row_layout.addLayout(proxy_url_layout)
        
        # 添加弹性空间
        proxy_row_layout.addStretch(1)
        
        # 代理端口
        port_layout = QHBoxLayout()
        port_layout.addWidget(BodyLabel("端口号:"))
        self.proxy_port_edit = LineEdit()
        self.proxy_port_edit.setValidator(QIntValidator(1, 65535))
        self.proxy_port_edit.setFixedWidth(80)  # 设置端口输入框固定宽度
        port_layout.addWidget(self.proxy_port_edit)
        proxy_row_layout.addLayout(port_layout)
        
        proxy_layout.addLayout(proxy_row_layout)
        proxy_card.setLayout(proxy_layout)
        layout.addWidget(proxy_card)
        
        # 网络设置卡片
        network_card = CardWidget()
        network_layout = QVBoxLayout()
        network_layout.addWidget(StrongBodyLabel("局域网设置"))
        
        # 将所有网络设置控件放在一行
        network_row_layout = QHBoxLayout()
        
        # 启用局域网访问复选框
        lan_container = QWidget()
        lan_container.setFixedWidth(160)
        lan_layout = QHBoxLayout(lan_container)
        lan_layout.setContentsMargins(0, 0, 0, 0)
        self.lan_checkbox = CheckBox("启用局域网访问")
        lan_layout.addWidget(self.lan_checkbox)
        lan_layout.addStretch()
        network_row_layout.addWidget(lan_container)
        
        # 监听地址
        network_row_layout.addWidget(BodyLabel("监听网址:"))
        self.listen_edit = LineEdit()
        self.listen_edit.setText("0.0.0.0")  # 设置默认值
        self.listen_edit.setPlaceholderText("例如: 0.0.0.0")
        self.listen_edit.setFixedWidth(350)  # 限制宽度
        network_row_layout.addWidget(self.listen_edit)
        
        # 添加弹性空间
        network_row_layout.addStretch(1)
        
        # 启用自定义端口复选框
        port_container = QWidget()
        port_container.setFixedWidth(160)
        port_layout_inner = QHBoxLayout(port_container)
        port_layout_inner.setContentsMargins(0, 0, 0, 0)
        self.custom_port_checkbox = CheckBox("启用自定义端口")
        port_layout_inner.addWidget(self.custom_port_checkbox)
        port_layout_inner.addStretch()
        network_row_layout.addWidget(port_container)
        
        # 端口号
        port_number_layout = QHBoxLayout()
        port_number_layout.addWidget(BodyLabel("端口号:"))
        self.port_spinbox = LineEdit()
        self.port_spinbox.setValidator(QIntValidator(1, 65535))
        self.port_spinbox.setText("8188") # 设置默认值
        self.port_spinbox.setFixedWidth(80)  # 设置端口输入框固定宽度
        self.port_spinbox.setPlaceholderText("8188")
        port_number_layout.addWidget(self.port_spinbox)
        network_row_layout.addLayout(port_number_layout)
        
        network_layout.addLayout(network_row_layout)
        network_card.setLayout(network_layout)
        layout.addWidget(network_card)
        
        # Python路径设置卡片
        path_card = CardWidget()
        path_layout = QVBoxLayout()
        path_layout.addWidget(StrongBodyLabel("Python路径设置"))
        
        # 启用自定义路径复选框
        self.custom_path_checkbox = CheckBox("使用自定义Python解释器路径")
        self.custom_path_checkbox.toggled.connect(self.toggle_custom_path)
        path_layout.addWidget(self.custom_path_checkbox)
        
        # 路径选择区域
        path_select_layout = QHBoxLayout()
        self.path_edit = LineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("请选择python.exe文件路径")
        path_select_layout.addWidget(self.path_edit, 1)  # 1表示伸展因子
        
        self.browse_button = PushButton("浏览...")
        self.browse_button.setIcon(FluentIcon.FOLDER)
        self.browse_button.clicked.connect(self.browse_file)
        path_select_layout.addWidget(self.browse_button)
        
        self.open_folder_button = PushButton("打开所在文件夹")
        self.open_folder_button.setIcon(FluentIcon.FOLDER)
        self.open_folder_button.clicked.connect(self.open_folder)
        path_select_layout.addWidget(self.open_folder_button)
        
        path_layout.addLayout(path_select_layout)
        path_card.setLayout(path_layout)
        layout.addWidget(path_card)
        
        # 高级启动参数设置卡片
        advanced_card = CardWidget()
        advanced_layout = QVBoxLayout()
        advanced_layout.addWidget(StrongBodyLabel("高级启动参数设置"))
        
        # 输出目录设置 - 将复选框和文件夹选择框放在一行
        output_dir_layout = QHBoxLayout()
        self.output_dir_checkbox = CheckBox("启用自定义输出目录")
        self.output_dir_checkbox.toggled.connect(self.toggle_output_dir)
        output_dir_layout.addWidget(self.output_dir_checkbox)
        
        self.output_dir_edit = LineEdit()
        self.output_dir_edit.setReadOnly(True)
        self.output_dir_edit.setPlaceholderText("请选择输出目录")
        output_dir_layout.addWidget(self.output_dir_edit, 1)  # 1表示伸展因子
        
        self.output_dir_browse_button = PushButton("浏览...")
        self.output_dir_browse_button.setIcon(FluentIcon.FOLDER)
        self.output_dir_browse_button.clicked.connect(self.browse_output_dir)
        output_dir_layout.addWidget(self.output_dir_browse_button)
        
        advanced_layout.addLayout(output_dir_layout)
        
        # 输入目录设置 - 将复选框和文件夹选择框放在一行
        input_dir_layout = QHBoxLayout()
        self.input_dir_checkbox = CheckBox("启用自定义输入目录")
        self.input_dir_checkbox.toggled.connect(self.toggle_input_dir)
        input_dir_layout.addWidget(self.input_dir_checkbox)
        
        self.input_dir_edit = LineEdit()
        self.input_dir_edit.setReadOnly(True)
        self.input_dir_edit.setPlaceholderText("请选择输入目录")
        input_dir_layout.addWidget(self.input_dir_edit, 1)  # 1表示伸展因子
        
        self.input_dir_browse_button = PushButton("浏览...")
        self.input_dir_browse_button.setIcon(FluentIcon.FOLDER)
        self.input_dir_browse_button.clicked.connect(self.browse_input_dir)
        input_dir_layout.addWidget(self.input_dir_browse_button)
        
        advanced_layout.addLayout(input_dir_layout)
        
        # 显存模式设置
        vram_layout = QHBoxLayout()
        
        # 添加显存模式启用复选框
        self.vram_enabled_checkbox = CheckBox("启用显存模式设置")
        self.vram_enabled_checkbox.toggled.connect(self.toggle_vram_mode)
        vram_layout.addWidget(self.vram_enabled_checkbox)
        
        # 创建下拉选项栏
        self.vram_combobox = ComboBox()
        # 添加显存模式选项
        self.vram_combobox.addItem("仅GPU:  所有模型保持在GPU上 (--gpu-only)", "gpu_only")
        self.vram_combobox.addItem("高显存:  模型保持加载 (--highvram)", "high")
        self.vram_combobox.addItem("中显存:  正常显存使用 (--normalvram)", "normal")
        self.vram_combobox.addItem("低显存:  分割UNet节省显存 (--lowvram)", "low")
        self.vram_combobox.addItem("极低显存:  当低显存仍显存不足时使用 (--novram)", "no")
        self.vram_combobox.addItem("仅CPU:  所有计算都在CPU上 (--cpu)", "cpu")
        
        # 设置默认选项为正常显存模式
        self.vram_combobox.setCurrentIndex(2)  # 正常显存模式的索引
        
        vram_layout.addWidget(self.vram_combobox, 1)  # 1表示伸展因子

        # 预留显存设置
        self.reserve_vram_checkbox = CheckBox("预留显存 (GB):")
        self.reserve_vram_checkbox.setChecked(False) # 默认不选中
        self.reserve_vram_edit = LineEdit() # 创建LineEdit对象
        self.reserve_vram_edit.setText("0.5") # 设置默认值0.5G
        self.reserve_vram_edit.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.reserve_vram_edit.setMaximumWidth(80)
        self.reserve_vram_edit.setEnabled(False) # 默认禁用

        self.reserve_vram_checkbox.stateChanged.connect(self.reserve_vram_edit.setEnabled)

        vram_layout.addWidget(self.reserve_vram_checkbox)
        vram_layout.addWidget(self.reserve_vram_edit)
        advanced_layout.addLayout(vram_layout)
        
        # 禁用元数据选项
        self.disable_metadata_checkbox = CheckBox("禁用元数据:  图片不保存工作流")
        advanced_layout.addWidget(self.disable_metadata_checkbox)
        
        advanced_card.setLayout(advanced_layout)
        layout.addWidget(advanced_card)
        
        # 重启命令接管设置卡片
        restart_card = CardWidget()
        restart_layout = QVBoxLayout()
        restart_layout.addWidget(StrongBodyLabel("Manager重启命令接管"))
        
        # 启用重启命令接管复选框
        self.restart_command_checkbox = CheckBox("启用 (避免Manager重启失败导致端口占用)")
        restart_layout.addWidget(self.restart_command_checkbox)
        
        # 重启命令关键词设置
        restart_keyword_layout = QHBoxLayout()
        restart_keyword_layout.addWidget(BodyLabel("重启命令关键词:"))
        self.restart_keyword_edit = LineEdit()
        self.restart_keyword_edit.setPlaceholderText("输入用于识别重启命令的关键词")
        restart_keyword_layout.addWidget(self.restart_keyword_edit)
        restart_layout.addLayout(restart_keyword_layout)
        
        restart_card.setLayout(restart_layout)
        layout.addWidget(restart_card)
        
        # 当前启动参数卡片
        command_card = CardWidget()
        command_layout = QVBoxLayout()
        command_layout.addWidget(StrongBodyLabel("当前启动参数"))
        
        self.command_text = TextEdit()
        self.command_text.setReadOnly(True)
        self.command_text.setMaximumHeight(80)
        command_layout.addWidget(self.command_text)
        
        command_card.setLayout(command_layout)
        layout.addWidget(command_card)
        
        # 保存按钮
        self.save_button = PrimaryPushButton("保存设置")
        self.save_button.clicked.connect(self.save_settings)
        layout.addWidget(self.save_button)
        
        # 添加弹性空间
        layout.addStretch(1)
        
        self.setLayout(layout)
    
    def update_command_display(self):
        """更新启动参数显示"""
        command_str = self.process_manager.get_command_string()
        self.command_text.setPlainText(command_str)
    
    def update_proxy_display(self):
        """根据选择的代理类型更新UI显示"""
        # 保存当前值
        current_proxy_type = self.proxy_type_combobox.currentData()
        # 确保代理类型不为None
        if current_proxy_type is None:
            # 获取当前选中的索引
            current_index = self.proxy_type_combobox.currentIndex()
            # 根据索引设置代理类型
            current_proxy_type = 'system' if current_index == 0 else 'socks5'
        
        self.data_model.set_value('proxy', 'proxy_type', current_proxy_type)
        print(f"更新代理类型显示: {current_proxy_type}")
        
        # 立即保存到配置文件
        self.data_model.save_config()
        
        # 更新启动参数显示
        self.update_command_display()
        
        # 更新保存按钮状态
        is_running = self.process_manager.is_running()
        print(f"加载设置后ComfyUI运行状态: {is_running}")
        self.update_save_button_state(is_running)
    
    def load_settings(self):
        """从配置文件加载设置"""
        # 加载代理和局域网设置
        self.proxy_checkbox.setChecked(self.data_model.get_bool('proxy', 'enabled'))
        # 设置代理只对启动面板生效（固定值）
        self.data_model.set_value('proxy', 'only_for_startup', True)
        self.lan_checkbox.setChecked(self.data_model.get_bool('network', 'lan_access'))
        
        # 加载代理类型设置
        proxy_type = self.data_model.get_value('proxy', 'proxy_type', 'system')
        proxy_type_index = 0 if proxy_type == 'system' else 1
        self.proxy_type_combobox.setCurrentIndex(proxy_type_index)
        
        # 加载代理设置
        self.http_proxy_edit.setText(self.data_model.get_value('proxy', 'http_proxy', '127.0.0.1'))
        self.proxy_port_edit.setText(self.data_model.get_value('proxy', 'port', '7897'))
        
        # 加载网络设置
        self.listen_edit.setText(self.data_model.get_value('network', 'listen', '0.0.0.0'))
        self.port_spinbox.setText(self.data_model.get_value('network', 'port', '8188'))
        self.custom_port_checkbox.setChecked(self.data_model.get_bool('network', 'custom_port_enabled'))
            
        # 加载路径设置
        self.custom_path_checkbox.setChecked(self.data_model.get_bool('paths', 'custom_comfyui_path_enabled'))
        self.path_edit.setText(self.data_model.get_value('paths', 'comfyui_path', ''))
        self.toggle_custom_path(self.custom_path_checkbox.isChecked())
        
        # 加载高级启动参数设置
        # 输出目录
        self.output_dir_checkbox.setChecked(self.data_model.get_bool('advanced', 'output_dir_enabled'))
        output_dir = self.data_model.get_value('advanced', 'output_dir', '')
        # 不再转换路径分隔符
        # output_dir = output_dir.replace('\\', '/')
        self.output_dir_edit.setText(output_dir)
        self.toggle_output_dir(self.output_dir_checkbox.isChecked())
        
        # 输入目录
        self.input_dir_checkbox.setChecked(self.data_model.get_bool('advanced', 'input_dir_enabled'))
        input_dir = self.data_model.get_value('advanced', 'input_dir', '')
        # 不再转换路径分隔符
        # input_dir = input_dir.replace('\\', '/')
        self.input_dir_edit.setText(input_dir)
        self.toggle_input_dir(self.input_dir_checkbox.isChecked())
        
        # 显存模式启用状态
        self.vram_enabled_checkbox.setChecked(self.data_model.get_bool('advanced', 'vram_enabled', False))

        # 预留显存
        reserve_vram_enabled = self.data_model.get_bool('advanced', 'reserve_vram_enabled')
        self.reserve_vram_checkbox.setChecked(reserve_vram_enabled);
        self.reserve_vram_edit.setText(self.data_model.get_value('advanced', 'reserve_vram', '0.5'));
        self.reserve_vram_edit.setEnabled(reserve_vram_enabled);
        
        # 显存模式
        vram_mode = self.data_model.get_value('advanced', 'vram_mode', 'normal')
        # 设置下拉选项栏的当前选项
        mode_index_map = {
            'gpu_only': 0,
            'high': 1,
            'normal': 2,
            'low': 3,
            'no': 4,
            'cpu': 5
        }
        self.vram_combobox.setCurrentIndex(mode_index_map.get(vram_mode, 2))  # 默认为正常模式（索引2）
            
        # 设置显存模式控件状态
        self.toggle_vram_mode(self.vram_enabled_checkbox.isChecked())
        
        # 禁用元数据
        self.disable_metadata_checkbox.setChecked(self.data_model.get_bool('advanced', 'disable_metadata'))
        
        # 加载重启命令接管设置
        self.restart_command_checkbox.setChecked(self.data_model.get_bool('advanced', 'restart_command_intercept_enabled', True))
        self.restart_keyword_edit.setText(self.data_model.get_value('advanced', 'restart_command_keyword', 'Restarting...'))
        
        # 更新启动参数显示
        self.update_command_display()
    
    def save_settings(self):
        """保存设置到配置文件"""
        # 临时禁用保存按钮并显示正在保存状态
        self.save_button.setEnabled(False)
        self.save_button.setText("正在保存...")
        print("开始保存设置，临时禁用保存按钮")
        
        # 保存代理和局域网设置
        self.data_model.set_value('proxy', 'enabled', self.proxy_checkbox.isChecked())
        # 设置代理只对启动面板生效（固定值）
        self.data_model.set_value('proxy', 'only_for_startup', True)
        self.data_model.set_value('network', 'lan_access', self.lan_checkbox.isChecked())
        
        # 保存代理设置
        self.data_model.set_value('proxy', 'http_proxy', self.http_proxy_edit.text())
        self.data_model.set_value('proxy', 'https_proxy', self.http_proxy_edit.text())  # 使用相同的值
        self.data_model.set_value('proxy', 'port', self.proxy_port_edit.text())
        # 保存代理类型
        proxy_type = self.proxy_type_combobox.currentData()
        # 确保代理类型不为None
        if proxy_type is None:
            # 获取当前选中的索引
            current_index = self.proxy_type_combobox.currentIndex()
            # 根据索引设置代理类型
            proxy_type = 'system' if current_index == 0 else 'socks5'
        self.data_model.set_value('proxy', 'proxy_type', proxy_type)
        print(f"保存代理类型: {proxy_type}")
        
        # 保存网络设置
        self.data_model.set_value('network', 'listen', self.listen_edit.text())
        self.data_model.set_value('network', 'port', self.port_spinbox.text())
        self.data_model.set_value('network', 'custom_port_enabled', self.custom_port_checkbox.isChecked())
        
        # 保存路径设置
        self.data_model.set_value('paths', 'custom_comfyui_path_enabled', self.custom_path_checkbox.isChecked())
        self.data_model.set_value('paths', 'comfyui_path', self.path_edit.text())
        
        # 保存高级启动参数设置
        # 输出目录
        self.data_model.set_value('advanced', 'output_dir_enabled', self.output_dir_checkbox.isChecked())
        output_dir = self.output_dir_edit.text()
        # 不再转换路径分隔符
        # output_dir = output_dir.replace('\\', '/')
        self.data_model.set_value('advanced', 'output_dir', output_dir)
        
        # 输入目录
        self.data_model.set_value('advanced', 'input_dir_enabled', self.input_dir_checkbox.isChecked())
        input_dir = self.input_dir_edit.text()
        # 不再转换路径分隔符
        # input_dir = input_dir.replace('\\', '/')
        self.data_model.set_value('advanced', 'input_dir', input_dir)
        
        # 显存模式启用状态
        self.data_model.set_value('advanced', 'vram_enabled', self.vram_enabled_checkbox.isChecked())

        # 预留显存
        self.data_model.set_value('advanced', 'reserve_vram_enabled', self.reserve_vram_checkbox.isChecked())
        self.data_model.set_value('advanced', 'reserve_vram', self.reserve_vram_edit.text())
        
        # 显存模式
        # 获取下拉选项栏的当前数据
        vram_mode = self.vram_combobox.currentData()
        self.data_model.set_value('advanced', 'vram_mode', vram_mode)
        
        # 禁用元数据
        self.data_model.set_value('advanced', 'disable_metadata', self.disable_metadata_checkbox.isChecked())
        
        # 保存重启命令接管设置
        self.data_model.set_value('advanced', 'restart_command_intercept_enabled', self.restart_command_checkbox.isChecked())
        self.data_model.set_value('advanced', 'restart_command_keyword', self.restart_keyword_edit.text())
        
        # 保存到文件
        self.data_model.save_config()
        
        # 更新启动参数显示
        self.update_command_display()
        
        # 发射设置已更改信号
        self.settings_changed.emit()
        
        # 显示保存成功状态
        self.save_button.setText("设置已保存")
        
        # 3秒后恢复按钮状态
        QTimer.singleShot(3000, self.restore_save_button_state)
        
        # 显示保存成功消息
    
    def restore_save_button_state(self):
        """恢复保存按钮状态"""
        print("恢复保存按钮状态")
        
        # 检查ComfyUI运行状态
        if self.process_manager and self.process_manager.is_running():
            # 如果ComfyUI正在运行，保持禁用状态
            self.save_button.setEnabled(False)
            self.save_button.setText("ComfyUI运行中，无法保存设置")
        else:
            # 如果ComfyUI未运行，恢复为可用状态
            self.save_button.setEnabled(True)
            self.save_button.setText("保存设置")
        
        print(f"保存按钮状态已恢复，当前状态: {self.save_button.isEnabled()}")

    
    def toggle_custom_path(self, enabled):
        """切换自定义路径控件状态"""
        self.path_edit.setEnabled(enabled)
        self.browse_button.setEnabled(enabled)
        self.open_folder_button.setEnabled(enabled and bool(self.path_edit.text()))
        
    def toggle_output_dir(self, enabled):
        """启用/禁用输出目录"""
        self.output_dir_edit.setEnabled(enabled)
        self.output_dir_browse_button.setEnabled(enabled)
        
    def toggle_input_dir(self, enabled):
        """启用/禁用输入目录"""
        self.input_dir_edit.setEnabled(enabled)
        self.input_dir_browse_button.setEnabled(enabled)
        
    def toggle_vram_mode(self, enabled):
        """启用/禁用显存模式选项"""
        # 启用或禁用显存模式下拉选项栏
        self.vram_combobox.setEnabled(enabled)
        
    def browse_output_dir(self):
        """浏览选择输出目录"""
        folder = QFileDialog.getExistingDirectory(self, "选择输出目录", self.output_dir_edit.text())
        if folder:
            # 不再转换路径分隔符
            # folder = folder.replace('\\', '/')
            self.output_dir_edit.setText(folder)
            
    def browse_input_dir(self):
        """浏览选择输入目录"""
        folder = QFileDialog.getExistingDirectory(self, "选择输入目录", self.input_dir_edit.text())
        if folder:
            # 不再转换路径分隔符
            # folder = folder.replace('\\', '/')
            self.input_dir_edit.setText(folder)
    
    def browse_file(self):
        """浏览选择python.exe文件"""
        current_path = self.path_edit.text()
        start_dir = os.path.dirname(current_path) if current_path and os.path.exists(current_path) else os.path.expanduser("~")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择python.exe文件",
            start_dir,
            "可执行文件 (*.exe);;所有文件 (*)"
        )
        
        if file_path:
            # 检查是否是python.exe文件
            if os.path.basename(file_path).lower() == "python.exe":
                self.path_edit.setText(file_path)
                self.open_folder_button.setEnabled(True)
            else:
                MessageBox(
                    "无效的文件",
                    f"所选文件 '{file_path}' 不是python.exe文件。",
                    self
                ).exec()
    
    def open_folder(self):
        """打开python.exe所在文件夹"""
        file_path = self.path_edit.text()
        if file_path and os.path.exists(file_path):
            # 获取文件所在的文件夹路径
            folder_path = os.path.dirname(file_path)
            # 使用系统默认方式打开文件夹
            os.startfile(folder_path)
        else:
            MessageBox("错误", "文件路径不存在", self).exec()
            self.path_edit.setText("")
            self.open_folder_button.setEnabled(False)
    
    def update_save_button_state(self, is_running):
        """根据ComfyUI进程运行状态更新保存按钮状态"""
        print(f"设置面板接收到状态变化信号: {is_running}，当前按钮状态: {self.save_button.isEnabled()}")
        
        # 根据ComfyUI运行状态更新保存按钮
        if is_running:
            # 如果ComfyUI正在运行，禁用保存按钮
            self.save_button.setEnabled(False)
            self.save_button.setText("ComfyUI运行中，无法保存设置")
        else:
            # 如果ComfyUI未运行，启用保存按钮
            self.save_button.setEnabled(True)
            self.save_button.setText("保存设置")
        
        # 强制更新按钮状态
        self.save_button.repaint()
        
        print(f"保存按钮状态已更新，当前状态: {self.save_button.isEnabled()}")
    
    def get_python_exe_path(self):
        """获取Python解释器路径
        
        根据是否选中自定义Python解释器路径复选框返回不同的路径：
        - 如果未选中，返回默认的 .\python_embeded\python.exe 路径
        - 如果选中，返回用户选择的python.exe路径
        
        Returns:
            str: Python解释器路径
        """
        if not self.custom_path_checkbox.isChecked():
            # 未选中自定义路径，返回默认路径
            return ".\\python_embeded\\python.exe"
        else:
            # 选中自定义路径，返回用户选择的路径
            return self.path_edit.text()
    
    def get_comfyui_path(self):
        """获取ComfyUI路径
        
        根据是否选中自定义Python解释器路径复选框返回不同的路径：
        - 如果未选中，返回默认的 .\ComfyUI\ 路径
        - 如果选中，返回基于Python解释器路径的上级目录下的ComfyUI文件夹
        
        Returns:
            str: ComfyUI路径
        """
        if not self.custom_path_checkbox.isChecked():
            # 未选中自定义路径，返回默认路径
            return ".\\ComfyUI\\"
        else:
            # 选中自定义路径，基于Python解释器路径计算ComfyUI路径
            python_path = self.get_python_exe_path()
            if python_path and os.path.exists(python_path):
                # 获取Python解释器所在目录的上级目录
                parent_dir = os.path.dirname(os.path.dirname(python_path))
                # 返回上级目录下的ComfyUI文件夹路径
                return os.path.join(parent_dir, "ComfyUI")
            else:
                # 如果路径不存在，返回默认路径
                return ".\\ComfyUI\\"