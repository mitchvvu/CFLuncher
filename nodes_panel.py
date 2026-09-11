from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QApplication, QListWidget, QListWidgetItem, QLabel, QDialog
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QWheelEvent, QPainter, QPaintEvent
import sys
import os
import configparser
import nodes_local_info  # 导入节点本地信息模块

class SingleRowScrollListWidget(QListWidget):
    """自定义QListWidget，每次滚动只移动一行"""
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def wheelEvent(self, event: QWheelEvent):
        """重写滚轮事件，每次滚动只移动一行"""
        # 获取滚动方向
        delta = event.angleDelta().y()
        
        # 根据滚动方向移动一行
        if delta > 0:  # 向上滚动
            self.setCurrentRow(max(0, self.currentRow() - 1))
        else:  # 向下滚动
            self.setCurrentRow(min(self.count() - 1, self.currentRow() + 1))
        
        # 阻止事件继续传播
        event.accept()

from qfluentwidgets import (CheckBox, LineEdit, BodyLabel, PrimaryPushButton, 
                           PushButton, CardWidget, StrongBodyLabel, ComboBox, 
                           MessageBox, InfoBar, InfoBarPosition, FluentIcon,
                           ScrollArea)


class SearchLineEdit(LineEdit):
    """带有搜索结果计数显示的搜索框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.count_text = ""
        self.setTextMargins(0, 0, 60, 0)  # 为计数文本预留更多右侧空间
    
    def setCountText(self, text):
        """设置计数文本"""
        self.count_text = text
        self.update()  # 触发重绘
    
    def paintEvent(self, event: QPaintEvent):
        """重写绘制事件，在右侧显示计数文本"""
        super().paintEvent(event)
        
        if self.count_text:
            painter = QPainter(self)
            painter.setPen(Qt.gray)
            # 在右侧绘制计数文本
            rect = self.rect()
            painter.drawText(
                rect.right() - 80,  # 右侧留出更多距离
                0,
                70,  # 增加文本宽度
                rect.height(),
                Qt.AlignRight | Qt.AlignVCenter,
                self.count_text
            )
import os
import shutil
import subprocess
import threading
from pathlib import Path
import re

class NodesPanel(QWidget):
    def __init__(self, data_model, nodes_data_model):
        super().__init__()
        self.data_model = data_model  # 用于代理设置等通用配置
        self.nodes_data_model = nodes_data_model  # 用于节点面板特定设置
        
        # 添加定时器成员变量
        self.load_timer = QTimer(self)
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self.load_nodes)
        
        # 添加标志，用于标记是否是第一次显示面板
        self.first_show = True
        
        self.init_ui()
        # 初始化时不再自动加载节点列表，只在第一次显示面板时加载
    
    def showEvent(self, event):
        """重写showEvent方法，在面板显示时不再自动刷新节点列表"""
        # 调用父类的showEvent方法
        super().showEvent(event)
        # 检查窗口状态，如果不是最小化状态，且是第一次显示面板，则加载节点列表
        if not self.window().isMinimized() and self.first_show:
            print("[调试-showEvent] 节点管理面板首次显示，从文件夹加载节点列表")
            self.first_show = False
            self.load_nodes_delayed(force_reload_from_folder=True)
            # 非首次显示时不再自动刷新节点列表，只有点击"获取当前版本"按钮时才会更新
    
    def hideEvent(self, event):
        """面板隐藏事件，取消所有正在进行的延时加载"""
        super().hideEvent(event)
        # 停止所有正在进行的定时器
        if self.load_timer.isActive():
            self.load_timer.stop()
            
        # 如果更新线程正在运行，等待其完成
        if hasattr(self, 'update_thread') and self.update_thread.isRunning():
            print("[调试-hideEvent] 等待更新线程完成...")
            self.update_thread.wait()
    
    def handle_window_state_change(self, minimized):
        """处理窗口状态变化"""
        if minimized:
            # 窗口最小化时暂停所有加载操作
            if self.load_timer.isActive():
                self.load_timer.stop()
                
            # 如果更新线程正在运行，等待其完成
            if hasattr(self, 'update_thread') and self.update_thread.isRunning():
                print("[调试-handle_window_state_change] 等待更新线程完成...")
                self.update_thread.wait()
                print("窗口最小化，已停止节点列表加载定时器")
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建依赖管理卡片
        dep_card = CardWidget()
        dep_main_layout = QVBoxLayout()
        dep_main_layout.addWidget(StrongBodyLabel("依赖管理"))
        
        # 第一行：代理和镜像源设置
        mirror_layout = QHBoxLayout()
        
        # 添加代理复选框
        self.proxy_checkbox = CheckBox("启用代理")
        self.proxy_checkbox.setChecked(self.nodes_data_model.get_bool('pip_mirror', 'proxy_enabled'))
        self.proxy_checkbox.setFixedWidth(160)
        mirror_layout.addWidget(self.proxy_checkbox)
        
        # 添加镜像源下拉选单
        self.mirror_combobox = ComboBox()
        
        # 镜像源配置列表
        mirror_configs = [
            ("PIP官方源（国外）", ""),  # 官方源不需要额外参数
            ("清华大学-更新及时", "-i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn"),
            ("阿里云-稳定", "-i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com"),
            ("中国科技大学-更新及时", "-i https://pypi.mirrors.ustc.edu.cn/simple/ --trusted-host pypi.mirrors.ustc.edu.cn"),
            ("华为云-稳定", "-i https://repo.huaweicloud.com/repository/pypi/simple/ --trusted-host repo.huaweicloud.com"),
            ("北京外国语大学-更新及时", "-i https://mirrors.cloud.tencent.com/pypi/simple/ --trusted-host mirrors.cloud.tencent.com")
        ]
        
        # 添加项目并设置数据
        for name, params in mirror_configs:
            self.mirror_combobox.addItem(name)
            index = self.mirror_combobox.count() - 1
            self.mirror_combobox.setItemData(index, params)
        
        # 设置当前选中的镜像源
        current_mirror_name = self.nodes_data_model.get_value('pip_mirror', 'mirror_name', '清华大学-更新及时')
        
        for i in range(self.mirror_combobox.count()):
            item_text = self.mirror_combobox.itemText(i)
            if item_text == current_mirror_name:
                self.mirror_combobox.setCurrentIndex(i)
                break
        
        self.mirror_combobox_width = 160
        self.mirror_combobox.setMinimumWidth(self.mirror_combobox_width)
        mirror_layout.addWidget(self.mirror_combobox)
        
        # 保存代理和镜像源设置按钮
        save_mirror_button = PushButton("保存设置")
        save_mirror_button.setIcon(FluentIcon.SAVE)
        save_mirror_button.clicked.connect(self.save_mirror_settings)
        self.button_width_1 = 160
        save_mirror_button.setFixedWidth(self.button_width_1)
        mirror_layout.addWidget(save_mirror_button)
        
        # 导出依赖列表按钮
        export_deps_button = PushButton("导出依赖列表")
        export_deps_button.setIcon(FluentIcon.LINK)
        export_deps_button.clicked.connect(self.export_dependencies)
        self.button_width_2 = 160
        export_deps_button.setFixedWidth(self.button_width_2)
        mirror_layout.addWidget(export_deps_button)
        
        dep_main_layout.addLayout(mirror_layout)
        
        # 第二行：依赖操作
        dep_layout = QHBoxLayout()
        
        # 添加操作类型下拉选单
        self.dep_type_combobox = ComboBox()
        self.dep_type_combobox.addItem("安装单个依赖")
        self.dep_type_combobox.addItem("卸载单个依赖")
        self.dep_type_combobox.addItem("WHL安装")
        self.dep_type_combobox.addItem("依赖文件安装")
        self.dep_type_combobox.currentIndexChanged.connect(self.update_dep_ui_state)
        checkbox_width = 160
        self.dep_type_combobox.setFixedWidth(checkbox_width)
        dep_layout.addWidget(self.dep_type_combobox)
        
        # 添加文本框
        self.dep_text_edit = LineEdit()
        self.dep_text_edit.setPlaceholderText("输入依赖名称或路径")
        self.dep_text_edit.setMinimumWidth(self.mirror_combobox_width)
        dep_layout.addWidget(self.dep_text_edit, 1)
        
        # 添加浏览按钮
        self.dep_browse_button = PushButton("指定文件路径")
        self.dep_browse_button.setIcon(FluentIcon.FOLDER)
        self.dep_browse_button.clicked.connect(self.browse_dep_file)
        self.dep_browse_button.setFixedWidth(self.button_width_1)
        dep_layout.addWidget(self.dep_browse_button)
        
        # 添加执行按钮
        self.dep_execute_button = PrimaryPushButton("执行")
        self.dep_execute_button.clicked.connect(self.execute_dep_command)
        self.dep_execute_button.setFixedWidth(self.button_width_2)
        dep_layout.addWidget(self.dep_execute_button)
        
        dep_main_layout.addLayout(dep_layout)
        
        # ComfyUI依赖管理 - 所有按钮在一行
        comfyui_all_deps_layout = QHBoxLayout()
        

        
        # 安装前端、工作流、文档依赖按钮（合并）
        self.install_all_comfyui_deps_button = PushButton("安装CF本体前端、工作流、文档依赖")
        self.install_all_comfyui_deps_button.setIcon(FluentIcon.DOWNLOAD)
        self.install_all_comfyui_deps_button.clicked.connect(self.install_three_comfyui_dependencies)
        self.install_all_comfyui_deps_button.setFixedWidth(581)
        comfyui_all_deps_layout.addWidget(self.install_all_comfyui_deps_button)

        # 打开本体依赖按钮
        self.open_comfyui_deps_button = PushButton("打开本体依赖")
        self.open_comfyui_deps_button.setIcon(FluentIcon.DOCUMENT)
        self.open_comfyui_deps_button.clicked.connect(self.open_comfyui_requirements)
        self.open_comfyui_deps_button.setFixedWidth(325)  # 宽度变为原来的2倍
        comfyui_all_deps_layout.addWidget(self.open_comfyui_deps_button)
        
        # 添加弹性空间
        # comfyui_all_deps_layout.addStretch()
        
        dep_main_layout.addLayout(comfyui_all_deps_layout)
        dep_card.setLayout(dep_main_layout)
        layout.addWidget(dep_card)
        
        # 初始化UI状态
        self.update_dep_ui_state()
        
        # 创建自定义节点安装卡片
        node_install_card = CardWidget()
        node_install_layout = QVBoxLayout()
        node_install_layout.addWidget(StrongBodyLabel("自定义节点安装"))
        
        # 创建Git安装布局
        git_install_layout = QHBoxLayout()
        
        # 添加代理复选框
        self.git_proxy_checkbox = CheckBox("启用代理")
        self.git_proxy_checkbox.setChecked(self.nodes_data_model.get_bool('git', 'proxy_enabled'))
        self.git_proxy_checkbox.setFixedWidth(240)
        git_install_layout.addWidget(self.git_proxy_checkbox)
        
        # 不再需要Git源下拉选单，只使用GitHub官方源
        
        # 添加Git URL输入框
        self.git_clone_url = LineEdit()
        self.git_clone_url.setPlaceholderText("输入git网址")
        # 移除 setFixedWidth，使其长度可变
        git_install_layout.addWidget(self.git_clone_url, 1)
        
        # 添加执行按钮
        self.git_execute_button = PrimaryPushButton("执行")
        self.git_execute_button.clicked.connect(self.execute_git_clone)
        self.git_execute_button.setFixedWidth(160)
        git_install_layout.addWidget(self.git_execute_button)
        
        node_install_layout.addLayout(git_install_layout)
        node_install_card.setLayout(node_install_layout)
        layout.addWidget(node_install_card)
        
        # 创建节点列表卡片
        nodes_card = CardWidget()
        nodes_layout = QVBoxLayout()
        nodes_layout.setAlignment(Qt.AlignTop)  # 设置布局向上对齐
        nodes_layout.addWidget(StrongBodyLabel("自定义节点管理"))
        

        
        # 创建节点列表 - 使用与版本管理相同的列表控件
        self.nodes_list = SingleRowScrollListWidget()
        self.nodes_list.setFixedHeight(550)  # 设置固定高度
        # 设置列表样式为类似表格的布局
        self.nodes_list.setStyleSheet("""
            QListWidget {
                background-color: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding-top: 0px;  /* 确保顶部没有额外的内边距 */
            }
            QListWidget::item {
                padding: 5px 5px;  /* 增加上下内边距 */
                border-bottom: 1px solid #e0e0e0;
                margin-top: 0px;  /* 确保项目之间没有额外的间距 */
                margin-bottom: 0px;
            }
            QListWidget::item:selected {
                background-color: #f0f8f8;
                color: #000000;
                border-left: 3px solid #00a7b3;  /* 添加左侧边框突出显示选中项 */
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        
        # 为了兼容性，保留一个空的nodes_layout属性
        self.nodes_layout = QVBoxLayout()
        
        # 创建搜索和按钮区域 - 所有控件在同一行
        search_and_buttons_layout = QHBoxLayout()
        
        # 添加搜索文本框
        self.search_edit = SearchLineEdit()
        self.search_edit.setPlaceholderText("搜索自定义节点名称...")
        self.search_edit.textChanged.connect(self.on_search_text_changed)
        search_and_buttons_layout.addWidget(self.search_edit, 1)  # 占用剩余空间
        
        # 添加上一个"<"按钮
        self.prev_button = PushButton("<")
        self.prev_button.clicked.connect(self.go_to_previous_match)
        self.prev_button.setEnabled(False)
        self.prev_button.setFixedWidth(35)
        search_and_buttons_layout.addWidget(self.prev_button)
        
        # 添加下一个">"按钮
        self.next_button = PushButton(">")
        self.next_button.clicked.connect(self.go_to_next_match)
        self.next_button.setEnabled(False)
        self.next_button.setFixedWidth(35)
        search_and_buttons_layout.addWidget(self.next_button)
        
        # 添加获取当前版本按钮
        get_version_button = PushButton("获取本地版本")

        get_version_button.clicked.connect(self.update_nodes_version_info)
        get_version_button.setFixedWidth(160)  # 设置宽度
        search_and_buttons_layout.addWidget(get_version_button)
        
        # 添加刷新列表按钮（宽度减半）
        refresh_button = PushButton("刷新列表")
        refresh_button.setIcon(FluentIcon.SYNC)
        refresh_button.clicked.connect(lambda: self.load_nodes(force_reload_from_folder=True))
        refresh_button.setFixedWidth(160)  # 设置宽度
        search_and_buttons_layout.addWidget(refresh_button)
        
        # 初始化搜索相关变量
        self.search_matches = []  # 存储搜索匹配的项目索引
        self.current_match_index = -1  # 当前匹配项的索引
        
        nodes_layout.addLayout(search_and_buttons_layout)
        nodes_layout.addWidget(self.nodes_list)
        nodes_card.setLayout(nodes_layout)
        layout.addWidget(nodes_card)
        
        self.setLayout(layout)
    
    def get_custom_nodes_path(self):
        """获取custom_nodes文件夹路径"""
        # 获取主窗口中的settings_panel实例
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'settings_panel'):
            main_window = main_window.parent()
        
        if main_window and hasattr(main_window, 'settings_panel'):
            # 使用settings_panel中的方法获取ComfyUI路径
            comfyui_path = main_window.settings_panel.get_comfyui_path()
            custom_nodes_path = os.path.join(comfyui_path, "custom_nodes")
            # print(f"[调试-get_custom_nodes_path] 从settings_panel获取路径: {custom_nodes_path}")
            return custom_nodes_path
        else:
            # 如果无法获取settings_panel实例，使用默认路径
            # 处理PyInstaller打包后的路径问题
            if getattr(sys, 'frozen', False):
                # 如果是打包后的可执行文件，使用应用程序所在目录
                base_path = os.path.dirname(sys.executable)
            else:
                # 如果是脚本运行，使用当前工作目录
                base_path = os.getcwd()
                
            custom_nodes_path = os.path.join(base_path, "ComfyUI", "custom_nodes")
            print(f"[调试-get_custom_nodes_path] 使用默认路径: {custom_nodes_path}")
            return custom_nodes_path
    
    def load_nodes_delayed(self, force_reload_from_folder=False):
        """延时加载节点列表"""
        # 停止可能正在运行的定时器
        if self.load_timer.isActive():
            self.load_timer.stop()
        
        # 如果窗口处于最小化状态，不启动加载
        if self.window().isMinimized():
            print("窗口最小化状态，不加载节点列表")
            return
            
        # 清除现有节点列表并显示加载提示
        self.nodes_list.clear()
        
        # 创建加载提示项
        loading_item = QListWidgetItem()
        loading_widget = QWidget()
        loading_layout = QHBoxLayout(loading_widget)
        loading_layout.setContentsMargins(10, 6, 10, 6)  # 与其他节点项保持一致的边距
        loading_layout.setSpacing(0)  # 减少内部间距
        loading_layout.setAlignment(Qt.AlignCenter)
        
        loading_label = BodyLabel("正在加载节点列表...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_layout.addWidget(loading_label)
        
        # 设置与其他节点项一致的高度
        size_hint = loading_widget.sizeHint()
        size_hint.setHeight(55)  # 与其他节点项保持一致的高度
        loading_item.setSizeHint(size_hint)
        self.nodes_list.addItem(loading_item)
        self.nodes_list.setItemWidget(loading_item, loading_widget)
        
        # 使用类成员定时器延迟加载节点列表，延迟0.35秒
        # 将force_reload_from_folder参数传递给load_nodes方法
        self.load_timer.timeout.disconnect()
        self.load_timer.timeout.connect(lambda: self.load_nodes(force_reload_from_folder))
        self.load_timer.start(350)
    
    def load_nodes_from_folder(self):
        """从文件夹读取节点列表"""
        # 获取custom_nodes文件夹路径
        custom_nodes_path = self.get_custom_nodes_path()
        print(f"[调试-load_nodes_from_folder] 从文件夹加载节点列表，路径: {custom_nodes_path}")
        
        disabled_nodes_path = os.path.join(custom_nodes_path, ".disabled")
        
        # 获取启用的节点列表
        enabled_nodes = []
        if os.path.exists(custom_nodes_path):
            try:
                for item in os.listdir(custom_nodes_path):
                    item_path = os.path.join(custom_nodes_path, item)
                    if os.path.isdir(item_path) and item != "__pycache__" and item != ".disabled":
                        enabled_nodes.append(item)
                print(f"[调试-load_nodes_from_folder] 找到启用节点: {len(enabled_nodes)}个")
            except Exception as e:
                print(f"[错误-load_nodes_from_folder] 读取启用节点失败: {str(e)}")
                # 使用InfoBar显示错误信息
                InfoBar.error(
                    title="加载失败",
                    content=f"无法读取启用节点: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=5000,
                    parent=self
                )
                return [], []
        
        # 获取禁用的节点列表
        disabled_nodes = []
        if os.path.exists(disabled_nodes_path):
            try:
                for item in os.listdir(disabled_nodes_path):
                    item_path = os.path.join(disabled_nodes_path, item)
                    if os.path.isdir(item_path):
                        # 提取@前面的部分作为显示名称
                        display_name = item.split('@')[0] if '@' in item else item
                        disabled_nodes.append((display_name, item))
                print(f"[调试-load_nodes_from_folder] 找到禁用节点: {len(disabled_nodes)}个")
            except Exception as e:
                print(f"[错误-load_nodes_from_folder] 读取禁用节点失败: {str(e)}")
                # 使用InfoBar显示错误信息
                InfoBar.error(
                    title="加载失败",
                    content=f"无法读取禁用节点: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=5000,
                    parent=self
                )
                return [], []
        
        # 保存到ini文件
        self.save_nodes_to_ini(enabled_nodes, disabled_nodes)
        
        return enabled_nodes, disabled_nodes
    
    def update_node_in_ini(self, display_name, is_enabled, original_name=None):
        """更新ini文件中的节点列表
        
        Args:
            display_name: 节点显示名称
            is_enabled: 是否启用
            original_name: 原始节点名称，用于禁用节点时从启用列表中移除
        """
        nodes_list_ini = os.path.join('starter', 'nodes_list.ini')
        config = configparser.ConfigParser()
        
        # 读取现有配置（如果存在）
        if os.path.exists(nodes_list_ini):
            config.read(nodes_list_ini, encoding='utf-8')
        
        # 确保节点列表部分存在
        if not config.has_section('enabled_nodes'):
            config.add_section('enabled_nodes')
        if not config.has_section('disabled_nodes'):
            config.add_section('disabled_nodes')
        
        # 根据节点状态更新配置
        if is_enabled:
            # 从禁用列表中移除
            for key in list(config['disabled_nodes']):
                if key.endswith('_display') and config['disabled_nodes'][key] == display_name:
                    node_index = key.split('_')[1]
                    config.remove_option('disabled_nodes', key)
                    config.remove_option('disabled_nodes', f'node_{node_index}_original')
            
            # 添加到启用列表
            # 查找最大的节点索引
            max_index = -1
            for key in config['enabled_nodes']:
                if key.startswith('node_'):
                    try:
                        index = int(key.split('_')[1])
                        max_index = max(max_index, index)
                    except ValueError:
                        pass
            
            # 添加新节点
            config.set('enabled_nodes', f'node_{max_index + 1}', display_name)
        else:
            # 从启用列表中移除
            for key, value in list(config.items('enabled_nodes')):
                if value == display_name or (original_name and value == original_name):
                    config.remove_option('enabled_nodes', key)
            
            # 添加到禁用列表
            # 查找最大的节点索引
            max_index = -1
            for key in config['disabled_nodes']:
                if key.endswith('_display'):
                    try:
                        index = int(key.split('_')[1])
                        max_index = max(max_index, index)
                    except ValueError:
                        pass
            
            # 添加新节点
            config.set('disabled_nodes', f'node_{max_index + 1}_display', display_name)
            config.set('disabled_nodes', f'node_{max_index + 1}_original', original_name or display_name)
        
        # 保存到文件
        with open(nodes_list_ini, 'w', encoding='utf-8') as f:
            config.write(f)
        
        print(f"[调试-update_node_in_ini] 已更新节点 {display_name} 的状态为 {'启用' if is_enabled else '禁用'}")
    
    def save_nodes_to_ini(self, enabled_nodes, disabled_nodes):
        """保存节点列表到ini文件"""
        config = configparser.ConfigParser()
        nodes_list_ini = os.path.join('starter', 'nodes_list.ini')
        
        # 读取现有配置（如果存在）
        if os.path.exists(nodes_list_ini):
            config.read(nodes_list_ini, encoding='utf-8')
        
        # 确保节点列表部分存在
        if not config.has_section('enabled_nodes'):
            config.add_section('enabled_nodes')
        if not config.has_section('disabled_nodes'):
            config.add_section('disabled_nodes')
        if not config.has_section('update_info'):
            config.add_section('update_info')
        
        # 清除现有配置
        config.remove_section('enabled_nodes')
        config.add_section('enabled_nodes')
        config.remove_section('disabled_nodes')
        config.add_section('disabled_nodes')
        
        # 保留update_info部分，如果存在的话
        if config.has_section('update_info'):
            update_info = dict(config.items('update_info'))
            config.remove_section('update_info')
            config.add_section('update_info')
            for key, value in update_info.items():
                config.set('update_info', key, value)
        else:
            config.add_section('update_info')
        
        # 获取custom_nodes文件夹路径
        custom_nodes_path = self.get_custom_nodes_path()
        
        # 添加启用的节点
        for i, node in enumerate(enabled_nodes):
            config.set('enabled_nodes', f'node_{i}', node)
            
            # 不再自动获取Git信息，只保留已有的信息
            # 如果update_info中没有该节点的信息，则使用默认值
            if f'{node}_version' not in update_info:
                config.set('update_info', f'{node}_version', 'Unknown')
            if f'{node}_date' not in update_info:
                config.set('update_info', f'{node}_date', 'Unknown')
        
        # 添加禁用的节点
        for i, node_tuple in enumerate(disabled_nodes):
            display_name, original_name = node_tuple
            config.set('disabled_nodes', f'node_{i}_display', display_name)
            config.set('disabled_nodes', f'node_{i}_original', original_name)
            
            # 不再自动获取Git信息，只保留已有的信息
            # 如果update_info中没有该节点的信息，则使用默认值
            if f'{display_name}_version' not in update_info:
                config.set('update_info', f'{display_name}_version', 'Unknown')
            if f'{display_name}_date' not in update_info:
                config.set('update_info', f'{display_name}_date', 'Unknown')
        
        # 保存到文件
        with open(nodes_list_ini, 'w', encoding='utf-8') as f:
            config.write(f)
        
        print(f"[调试-save_nodes_to_ini] 已保存节点列表到 {nodes_list_ini}")
    
    def load_nodes_from_ini(self):
        """从ini文件加载节点列表"""
        nodes_list_ini = os.path.join('starter', 'nodes_list.ini')
        
        if not os.path.exists(nodes_list_ini):
            print(f"[调试-load_nodes_from_ini] 节点列表文件不存在，将从文件夹加载")
            return self.load_nodes_from_folder()
        
        config = configparser.ConfigParser()
        config.read(nodes_list_ini, encoding='utf-8')
        
        enabled_nodes = []
        disabled_nodes = []
        git_info = {}
        
        # 读取启用的节点
        if config.has_section('enabled_nodes'):
            for key, value in config.items('enabled_nodes'):
                enabled_nodes.append(value)
        
        # 读取禁用的节点
        if config.has_section('disabled_nodes'):
            # 获取所有禁用节点的显示名称
            display_names = []
            original_names = []
            
            for key, value in config.items('disabled_nodes'):
                if key.endswith('_display'):
                    display_names.append((key, value))
                elif key.endswith('_original'):
                    original_names.append((key, value))
            
            # 将显示名称和原始名称配对
            for display_key, display_value in display_names:
                node_index = display_key.split('_')[1]
                original_key = f'node_{node_index}_original'
                
                # 查找对应的原始名称
                original_value = None
                for orig_key, orig_value in original_names:
                    if orig_key == original_key:
                        original_value = orig_value
                        break
                
                if original_value:
                    disabled_nodes.append((display_value, original_value))
        
        # 读取Git信息
        if config.has_section('update_info'):
            for key, value in config.items('update_info'):
                git_info[key] = value
        
        print(f"[调试-load_nodes_from_ini] 从ini文件加载节点列表，启用节点: {len(enabled_nodes)}个，禁用节点: {len(disabled_nodes)}个")
        return enabled_nodes, disabled_nodes, git_info
    
    def load_nodes(self, force_reload_from_folder=False):
        """加载节点列表"""
        # 清除现有节点列表
        self.nodes_list.clear()
        
        # 清除搜索状态
        self.search_matches.clear()
        self.current_match_index = -1
        self.search_edit.clear()
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)
        
        # 获取节点列表
        if force_reload_from_folder:
            # 强制从文件夹重新加载
            enabled_nodes, disabled_nodes = self.load_nodes_from_folder()
            git_info = {}
        else:
            # 从ini文件加载，如果ini文件不存在则从文件夹加载
            enabled_nodes, disabled_nodes, git_info = self.load_nodes_from_ini()
        
        # 合并并按音序排序
        all_nodes = [(name, name, True) for name in enabled_nodes] + \
                    [(display_name, original_name, False) for display_name, original_name in disabled_nodes]
        all_nodes.sort(key=lambda x: x[0].lower())
        
        # 保存Git信息供add_node_to_ui使用
        self.git_info = git_info
        
        # 添加节点到UI，并考虑nodes_data_model中保存的状态
        for display_name, original_name, is_enabled in all_nodes:
            # 检查nodes_data_model中是否有保存的状态
            saved_state = self.nodes_data_model.get_value('nodes', display_name)
            if saved_state is not None:
                # 如果有保存的状态，使用保存的状态，确保转换为布尔值
                if isinstance(saved_state, str):
                    is_enabled = saved_state.lower() in ('true', '1', 'yes', 'on')
                else:
                    is_enabled = bool(saved_state)
            self.add_node_to_ui(display_name, original_name, is_enabled)
        
        # 不再自动应用更新信息，只在点击"获取当前版本"按钮时才更新
    
    def add_node_to_ui(self, display_name, original_name, is_enabled):
        """添加节点到UI"""
        # 创建列表项
        item = QListWidgetItem()
        item.setData(Qt.UserRole, {"display_name": display_name, "original_name": original_name, "is_enabled": is_enabled})
        
        # 创建节点项容器控件
        node_widget = QWidget()
        node_layout = QHBoxLayout(node_widget)
        node_layout.setContentsMargins(10, 6, 10, 6)  # 增加内边距，与版本管理面板一致
        node_layout.setSpacing(6)  # 减小控件之间的间距
        node_layout.setAlignment(Qt.AlignVCenter)  # 设置布局垂直居中
        
        # 获取节点路径
        custom_nodes_path = self.get_custom_nodes_path()
        if is_enabled:
            node_path = os.path.join(custom_nodes_path, original_name)
        else:
            node_path = os.path.join(custom_nodes_path, ".disabled", original_name)
        
        # 添加tag图标（与版本面板保持一致）
        icon_label = QLabel()
        icon_label.setPixmap(FluentIcon.TAG.icon().pixmap(QSize(16, 16)))
        node_layout.addWidget(icon_label)
        
        # 节点名称标签
        name_label = BodyLabel(display_name)
        name_label.setFixedWidth(290)  # 调整固定宽度，为版本时间戳标签留出空间
        name_label.setAlignment(Qt.AlignVCenter)  # 垂直居中
        name_label.setStyleSheet("color: #00a7b3; font-weight: bold;")  # 设置与版本面板commit相同的样式
        # 保存原始文本用于搜索功能
        name_label.setProperty("original_text", display_name)
        # 强制应用样式
        name_label.style().unpolish(name_label)
        name_label.style().polish(name_label)
        name_label.update()  # 强制更新显示
        node_layout.addWidget(name_label)
        
        # 获取Git信息
        version, date_time = nodes_local_info.get_node_git_version_and_date(node_path)
        
        # 创建版本时间戳的容器
        version_date_widget = QWidget()
        version_date_layout = QVBoxLayout(version_date_widget)
        version_date_layout.setContentsMargins(0, 0, 0, 0)
        version_date_layout.setSpacing(0)
        
        # 添加版本标签（小字体）
        version_label = QLabel(f"版本ID: {version}")
        version_label.setStyleSheet("font-size: 12px; color: #666666;")
        version_date_layout.addWidget(version_label)
        
        # 添加时间戳标签（小字体）
        date_label = QLabel(f"时间戳: {date_time}")
        date_label.setStyleSheet("font-size: 12px; color: #666666;")
        version_date_layout.addWidget(date_label)
        
        # 设置容器宽度
        version_date_widget.setFixedWidth(180)
        node_layout.addWidget(version_date_widget)
        
        # 添加弹性空间
        node_layout.addStretch(1)
        
        # 存储按钮引用的列表
        buttons = []
        
        # 检查是否有requirements.txt文件
        req_path = os.path.join(node_path, "requirements.txt")
        
        # 添加启用/禁用开关（先创建复选框，以便按钮可以引用它）
        toggle_checkbox = CheckBox("启用")
        toggle_checkbox.setChecked(is_enabled)
        # 设置属性以便后续识别
        toggle_checkbox.setProperty("display_name", display_name)
        toggle_checkbox.setProperty("original_name", original_name)
        toggle_checkbox.setProperty("node_path", node_path)
        toggle_checkbox.setProperty("is_enabled", is_enabled)
        toggle_checkbox.setFixedWidth(70)
        toggle_checkbox.setFixedHeight(32)  # 设置固定高度以便垂直居中
        
        if os.path.exists(req_path):
            # 添加安装依赖按钮
            req_button = PushButton("安装依赖")
            # 移除图标
            # req_button.setIcon(FluentIcon.DOWNLOAD)
            req_button.setToolTip("左键点击安装，右键点击打开依赖文件")
            # 使用lambda函数动态获取当前正确的路径，传递复选框对象
            req_button.clicked.connect(lambda: self.install_requirements_for_node(toggle_checkbox))
            req_button.setContextMenuPolicy(Qt.CustomContextMenu)
            req_button.customContextMenuRequested.connect(lambda: self.open_req_file_for_node(display_name))
            req_button.setEnabled(is_enabled)  # 只有启用状态才能使用
            req_button.setFixedWidth(83)  # 减小宽度
            req_button.setFixedHeight(32)  # 设置固定高度以便垂直居中
            node_layout.addWidget(req_button)
            buttons.append(req_button)
        
        # 添加更新按钮
        update_button = PushButton("更新")
        # 移除图标
        # update_button.setIcon(FluentIcon.UPDATE)
        # 添加更新功能
        update_button.clicked.connect(lambda: self.update_single_node(toggle_checkbox))
        update_button.setEnabled(is_enabled)
        update_button.setFixedWidth(70)  # 减小宽度
        update_button.setFixedHeight(32)  # 设置固定高度以便垂直居中
        node_layout.addWidget(update_button)
        buttons.append(update_button)
        
        # 添加打开文件夹按钮
        folder_button = PushButton("打开")
        # 移除图标
        # folder_button.setIcon(FluentIcon.FOLDER)
        # 使用lambda函数动态获取当前正确的路径，传递复选框对象
        folder_button.clicked.connect(lambda: self.open_folder_for_node(toggle_checkbox))
        folder_button.setEnabled(is_enabled)
        folder_button.setFixedWidth(70)  # 减小宽度
        folder_button.setFixedHeight(32)  # 设置固定高度以便垂直居中
        node_layout.addWidget(folder_button)
        buttons.append(folder_button)
        
        # 缓存按钮引用以提高性能
        toggle_checkbox.setProperty("buttons", buttons)
        # 连接事件处理
        toggle_checkbox.stateChanged.connect(lambda state, cb=toggle_checkbox: self.toggle_node(cb, state))
        node_layout.addWidget(toggle_checkbox)
        
        # 设置列表项的大小提示 - 与版本管理面板保持一致
        size_hint = node_widget.sizeHint()
        size_hint.setHeight(55)  # 与版本管理面板保持一致的高度
        item.setSizeHint(size_hint)
        
        # 将控件添加到列表项
        self.nodes_list.addItem(item)
        self.nodes_list.setItemWidget(item, node_widget)
    
    def save_mirror_settings(self):
        """保存代理和镜像源设置"""
        # 保存代理启用状态
        self.nodes_data_model.set_value('pip_mirror', 'proxy_enabled', self.proxy_checkbox.isChecked())
        
        # 保存选择的镜像源名称（中文显示名称）
        mirror_name = self.mirror_combobox.currentText()
        self.nodes_data_model.set_value('pip_mirror', 'mirror_name', mirror_name)
        
        # 同时保存镜像源参数（用于实际使用）
        mirror_source = self.mirror_combobox.currentData()
        self.nodes_data_model.set_value('pip_mirror', 'mirror_source', mirror_source)
        
        # 保存到文件
        self.nodes_data_model.save_config()
        
        MessageBox("保存成功", "依赖管理设置已保存", self).exec()
    
    def update_dep_ui_state(self):
        """根据依赖操作类型更新UI状态"""
        current_index = self.dep_type_combobox.currentIndex()
        
        # 对于前两个选项（安装单个依赖、卸载单个依赖），浏览按钮不可用
        if current_index < 2:  # 0或1
            self.dep_browse_button.setEnabled(False)
            self.dep_text_edit.clear()
            self.dep_text_edit.setPlaceholderText("输入依赖包名称")
        else:
            self.dep_browse_button.setEnabled(True)
            self.dep_text_edit.clear()
            
            # 根据选项设置浏览按钮文本和文本框提示
            if current_index == 2:  # WHL安装
                self.dep_browse_button.setText("指定文件路径")
                self.dep_text_edit.setPlaceholderText("WHL文件路径")
            elif current_index == 3:  # 依赖文件安装
                self.dep_browse_button.setText("指定文件路径")
                self.dep_text_edit.setPlaceholderText("requirements.txt文件路径")

    
    def install_requirements(self, req_path):
        """安装requirements.txt中的依赖"""
        # 获取镜像源参数
        mirror_params = self._get_mirror_params()
        
        # 使用新的install_requirements_file方法
        self.install_requirements_file(req_path, mirror_params)
    
    def export_dependencies(self):
        """导出依赖列表到requirements.txt"""
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存依赖列表", "requirements.txt", "文本文件 (*.txt)"
        )
        
        if not file_path:
            return  # 用户取消了选择
        
        # 获取Python解释器路径 - 使用settings_panel中的方法
        # 获取主窗口中的settings_panel实例
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'settings_panel'):
            main_window = main_window.parent()
        
        if main_window and hasattr(main_window, 'settings_panel'):
            # 使用settings_panel中的方法获取Python解释器路径
            python_exe_path = main_window.settings_panel.get_python_exe_path()
        else:
            # 如果无法获取settings_panel实例，使用默认路径
            python_exe_path = ".\python_embeded\python.exe"
        
        # 不再转换路径分隔符
        # replaced_path = file_path.replace('\\', '/')
        formatted_path = f'"{file_path}"'
        
        # 构建命令
        cmd = f'"{python_exe_path}" -m pip freeze > {formatted_path}'
        
        # 设置环境变量
        env = os.environ.copy()
        
        # 使用依赖管理下的启动代理按钮状态，独立于设置面板的启动代理选项
        use_proxy = self.proxy_checkbox.isChecked()
        
        # 如果需要使用代理，设置代理环境变量
        if use_proxy:
            http_proxy = self.data_model.get_value('proxy', 'http_proxy')
            proxy_port = self.data_model.get_value('proxy', 'port')
            proxy_type = self.data_model.get_value('proxy', 'proxy_type', 'system')
            
            # 确保代理类型是字符串并且进行严格比较
            if isinstance(proxy_type, str) and proxy_type.strip().lower() == 'socks5':
                proxy_url = f"socks5://{http_proxy}:{proxy_port}"
                print(f"[调试-export_dependencies] 代理已启用: Socks5代理 {proxy_url}")
            else:  # 系统代理
                proxy_url = f"http://{http_proxy}:{proxy_port}"
                print(f"[调试-export_dependencies] 代理已启用: 系统代理 {proxy_url}")
            
            env['http_proxy'] = proxy_url
            env['https_proxy'] = proxy_url
        else:
            print(f"[调试-export_dependencies] 代理未启用 (依赖管理面板代理选项未勾选)")
        
        # 输出最终的导出命令调试信息
        print(f"[调试-export_dependencies] 最终执行的导出命令: {cmd}")
        
        try:
            # 在后台运行命令，不显示cmd窗口
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            
            # 等待进程完成
            stdout, stderr = process.communicate()
            
            # 检查命令执行结果
            if process.returncode == 0:
                # 使用 InfoBar 显示成功消息
                InfoBar.success(
                    title="导出成功",
                    content="依赖列表已成功导出到 requirements.txt",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
            else:
                # 使用 InfoBar 显示错误消息
                error_msg = stderr.decode('utf-8', errors='ignore') if stderr else "未知错误"
                InfoBar.error(
                    title="导出失败",
                    content=f"导出依赖列表时出错: {error_msg}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=5000,
                    parent=self
                )
            
        except Exception as e:
            # 使用 InfoBar 显示错误消息
            InfoBar.error(
                title="导出失败",
                content=f"导出依赖列表时出错：{str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
    
    def open_req_file(self, req_path):
        """使用系统默认文本编辑器打开requirements.txt文件"""
        try:
            os.startfile(req_path)
        except Exception as e:
            MessageBox("打开失败", f"无法打开依赖文件：{str(e)}", self).exec()
    
    def open_folder(self, folder_path):
        """打开文件夹"""
        try:
            os.startfile(folder_path)
        except Exception as e:
            MessageBox("打开失败", f"无法打开文件夹：{str(e)}", self).exec()
    
    def browse_dep_file(self):
        """浏览并选择依赖文件"""
        current_index = self.dep_type_combobox.currentIndex()
        
        if current_index == 2:  # WHL安装
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择WHL文件", "", "WHL文件 (*.whl)"
            )
        elif current_index == 3:  # 依赖文件安装
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择依赖文件", "", "文本文件 (*.txt)"
            )
        else:
            return
        
        if file_path:
            # 不再转换路径分隔符
            # 使用常规字符串处理方式避免f-string中的反斜杠问题
            # replaced_path = file_path.replace('\\', '/')
            formatted_path = f'"{file_path}"'
            self.dep_text_edit.setText(formatted_path)
    
    def execute_dep_command(self):
        """执行依赖管理命令"""
        # 获取当前选择的操作类型
        current_index = self.dep_type_combobox.currentIndex()
        
        # 获取文本框内容
        text_content = self.dep_text_edit.text().strip()
        if not text_content:
            MessageBox("输入错误", "请输入依赖包名称或文件路径", self).exec()
            return
        
        # 获取镜像源参数
        mirror_params = self.mirror_combobox.currentData()
        if not mirror_params:
            mirror_params = self.nodes_data_model.get_value('pip_mirror', 'mirror_source')
        
        # 根据操作类型调用对应的重构方法
        if current_index == 0:  # 安装单个依赖
            self.install_single_package(text_content, mirror_params)
        elif current_index == 1:  # 卸载单个依赖
            self.uninstall_single_package(text_content, mirror_params)
        elif current_index == 2:  # WHL安装
            self.install_whl_package(text_content, mirror_params)
        elif current_index == 3:  # 依赖文件安装
            self.install_requirements_file(text_content, mirror_params)
    

    def execute_git_clone(self):
        """执行git clone命令安装自定义节点"""
        # 获取git clone URL
        git_url = self.git_clone_url.text().strip()
        if not git_url:
            MessageBox("错误", "请输入有效的git网址", self).exec()
            return
        
        # 只使用GitHub官方源
        print(f"[调试-execute_git_clone] 原始URL: {git_url}")
        
        # 构建git clone命令
        cmd = f'git clone {git_url}'
        print(f"[调试-execute_git_clone] 使用GitHub官方: {git_url}")
        
        # 设置环境变量和代理
        env = os.environ.copy()
        
        # 判断是否使用代理
        # 如果勾选了Git代理复选框，则使用设置面板中的代理设置
        use_proxy = self.git_proxy_checkbox.isChecked()
        
        if use_proxy:
            # 从数据模型中获取代理设置
            http_proxy = self.data_model.get_value('proxy', 'http_proxy')
            proxy_port = self.data_model.get_value('proxy', 'port')
            proxy_type = self.data_model.get_value('proxy', 'proxy_type', 'system')
            
            # 保存Git代理设置到nodes_data_model
            self.nodes_data_model.set_value('git', 'proxy_enabled', True)
            
            # 确保代理类型是字符串并且进行严格比较
            if isinstance(proxy_type, str) and proxy_type.strip().lower() == 'socks5':
                proxy_url = f"socks5://{http_proxy}:{proxy_port}"
                print(f"[调试-execute_git_clone] 代理已启用: Socks5代理 {proxy_url}")
            else:  # 系统代理
                proxy_url = f"http://{http_proxy}:{proxy_port}"
                print(f"[调试-execute_git_clone] 代理已启用: 系统代理 {proxy_url}")
            
            env['http_proxy'] = proxy_url
            env['https_proxy'] = proxy_url
        else:
            # 保存Git代理设置到nodes_data_model
            self.nodes_data_model.set_value('git', 'proxy_enabled', False)
            
            # 确保环境变量中没有代理设置
            if 'http_proxy' in env:
                del env['http_proxy']
            if 'https_proxy' in env:
                del env['https_proxy']
            print(f"[调试-execute_git_clone] 代理未启用")
        
        # 获取custom_nodes目录路径
        custom_nodes_path = self.get_custom_nodes_path()
        
        try:
            # 创建信息对话框
            info_dialog = MessageBox("自定义节点安装", f"正在执行命令，请稍候...\n\n命令行窗口关闭后此对话框将自动关闭。", self)
            
            # 启动cmd窗口运行命令，不做隐藏
            # 在命令前添加echo来显示要执行的命令和当前目录
            display_cmd = f'echo 当前目录: {custom_nodes_path} & echo 执行命令: {cmd} & echo. & cd /d "{custom_nodes_path}" & {cmd} & pause'
            process = subprocess.Popen(f'cmd.exe /c "{display_cmd}"', 
                                    creationflags=subprocess.CREATE_NEW_CONSOLE, env=env)
            
            # 创建一个定时器来检查进程状态
            timer = QTimer(self)
            
            # 定义检查进程的函数
            def check_process():
                if process.poll() is not None:  # 如果进程已结束
                    timer.stop()
                    info_dialog.accept()  # 自动关闭对话框
                    # 刷新节点列表
                    self.load_nodes()
            
            # 设置定时器每500毫秒检查一次进程状态
            timer.timeout.connect(check_process)
            timer.start(500)
            
            # 显示对话框（这会阻塞直到对话框关闭）
            info_dialog.exec()
            
            # 停止定时器
            timer.stop()
            
            # 当对话框关闭时，检查进程是否仍在运行
            if process.poll() is None:  # 如果进程仍在运行
                # 尝试终止进程
                try:
                    process.terminate()
                except Exception:
                    pass  # 忽略终止失败的错误
            
        except Exception as e:
            MessageBox("执行失败", f"启动命令进程时出错：{str(e)}", self).exec()
    
    def toggle_node(self, checkbox, state):
        """处理单个节点的启用/禁用"""
        display_name = checkbox.property("display_name")
        original_name = checkbox.property("original_name")
        is_enabled = checkbox.property("is_enabled")
        is_checked = checkbox.isChecked()
        
        # 如果状态没有变化，直接返回
        if is_checked == is_enabled:
            return
        
        # 暂时禁用复选框，防止重复点击
        checkbox.setEnabled(False)
        
        # 获取custom_nodes文件夹路径
        custom_nodes_path = self.get_custom_nodes_path()
        disabled_nodes_path = os.path.join(custom_nodes_path, ".disabled")
        
        # 确保.disabled文件夹存在
        if not os.path.exists(disabled_nodes_path):
            os.makedirs(disabled_nodes_path, exist_ok=True)
        
        try:
            if is_checked:  # 启用节点
                # 从.disabled移动到custom_nodes
                source_path = os.path.join(disabled_nodes_path, original_name)
                # 移除@及其后面的部分（此处为兼容其他插件的功能）
                clean_name = original_name.split('@')[0] if '@' in original_name else original_name
                target_path = os.path.join(custom_nodes_path, clean_name)
                
                # 如果目标路径已存在，询问是否覆盖
                if os.path.exists(target_path):
                    reply = MessageBox("确认覆盖", 
                                      f"文件夹 {clean_name} 已存在，是否覆盖？", self)
                    if reply.exec() != MessageBox.Yes:
                        # 用户取消，恢复复选框状态
                        checkbox.setChecked(False)
                        checkbox.setEnabled(True)
                        return
                    # 删除现有文件夹
                    try:
                        shutil.rmtree(target_path)
                    except Exception as e:
                        MessageBox("错误", f"无法删除现有文件夹：{str(e)}", self).exec()
                        checkbox.setChecked(False)
                        checkbox.setEnabled(True)
                        return
                
                # 移动文件夹
                shutil.move(source_path, target_path)
                
                # 批量更新属性和状态
                checkbox.setProperty("is_enabled", True)
                checkbox.setProperty("original_name", clean_name)
                checkbox.setProperty("node_path", target_path)
                checkbox.setChecked(True)
                
                # 更新同一行中的按钮状态
                self.update_node_buttons_state(checkbox, True)
                
                # 保存节点状态到nodes_data_model
                self.nodes_data_model.set_value('nodes', display_name, True)
                self.nodes_data_model.save_config()
                
                # 更新ini文件中的节点列表
                self.update_node_in_ini(display_name, True)
                
                # 显示成功提示
                InfoBar.success(
                    title="节点已启用",
                    content=f"节点 {display_name} 已成功启用",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=1500,  # 减少显示时间
                    parent=self
                )
                
            else:  # 禁用节点
                # 从custom_nodes移动到.disabled
                source_path = os.path.join(custom_nodes_path, display_name)
                # 直接使用原名称，不添加时间戳（为了兼容其他插件）
                target_path = os.path.join(disabled_nodes_path, display_name)
                
                # 如果目标路径已存在，询问是否覆盖
                if os.path.exists(target_path):
                    reply = MessageBox("确认覆盖", 
                                      f"禁用文件夹中已存在 {display_name}，是否覆盖？", self)
                    if reply.exec() != MessageBox.Yes:
                        # 用户取消，恢复复选框状态
                        checkbox.setChecked(True)
                        checkbox.setEnabled(True)
                        return
                    # 删除现有文件夹
                    try:
                        shutil.rmtree(target_path)
                    except Exception as e:
                        MessageBox("错误", f"无法删除现有文件夹：{str(e)}", self).exec()
                        checkbox.setChecked(True)
                        checkbox.setEnabled(True)
                        return
                
                # 移动文件夹
                shutil.move(source_path, target_path)
                
                # 批量更新属性和状态
                checkbox.setProperty("is_enabled", False)
                checkbox.setProperty("original_name", display_name)
                checkbox.setProperty("node_path", target_path)
                checkbox.setChecked(False)
                
                # 更新同一行中的按钮状态
                self.update_node_buttons_state(checkbox, False)
                
                # 保存节点状态到nodes_data_model
                self.nodes_data_model.set_value('nodes', display_name, False)
                self.nodes_data_model.save_config()
                
                # 更新ini文件中的节点列表
                self.update_node_in_ini(display_name, False, original_name=display_name)
                
                # 显示成功提示
                InfoBar.success(
                    title="节点已禁用",
                    content=f"节点 {display_name} 已成功禁用",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=1500,  # 减少显示时间
                    parent=self
                )
            
        except Exception as e:
            # 发生错误时恢复复选框状态
            checkbox.setChecked(is_enabled)
            MessageBox("错误", f"无法{'启用' if is_checked else '禁用'}节点 {display_name}：{str(e)}", self).exec()
        finally:
            # 重新启用复选框
            checkbox.setEnabled(True)
    
    def update_node_buttons_state(self, checkbox, enabled):
        """更新节点按钮的启用状态"""
        # 直接从复选框的缓存属性中获取按钮引用
        buttons = checkbox.property("buttons")
        if buttons:
            for button in buttons:
                button.setEnabled(enabled)
    
    def install_requirements_for_node(self, checkbox):
        """为指定节点安装依赖，动态获取正确路径"""
        # 获取节点的当前状态和名称
        is_enabled = checkbox.property("is_enabled")
        original_name = checkbox.property("original_name")
        display_name = checkbox.property("display_name")
        
        print(f"[调试-install_requirements_for_node] 开始为节点安装依赖: {display_name} (原名: {original_name}, 启用状态: {is_enabled})")
        
        # 动态计算正确的路径
        custom_nodes_path = self.get_custom_nodes_path()
        if is_enabled:
            # 如果节点已启用，路径在custom_nodes下
            node_path = os.path.join(custom_nodes_path, original_name)
        
        # 构建requirements.txt文件的完整路径
        req_path = os.path.join(node_path, "requirements.txt")
        
        print(f"[调试-install_requirements_for_node] 节点路径: {node_path}")
        print(f"[调试-install_requirements_for_node] requirements.txt路径: {req_path}")
        
        # 检查requirements.txt文件是否存在
        if os.path.exists(req_path):
            print(f"[调试-install_requirements_for_node] requirements.txt文件存在，开始安装依赖")
            # 获取镜像源参数
            mirror_params = self._get_mirror_params()
            # 使用新的install_requirements_file方法
            self.install_requirements_file(req_path, mirror_params)
        else:
            print(f"[调试-install_requirements_for_node] requirements.txt文件不存在: {req_path}")
            MessageBox("错误", f"未找到依赖文件：{req_path}", self).exec()
    
    def open_folder_for_node(self, checkbox):
        """为指定节点打开文件夹，动态获取正确路径"""
        # 获取节点的当前状态和名称
        is_enabled = checkbox.property("is_enabled")
        original_name = checkbox.property("original_name")
        
        # 动态计算正确的路径
        custom_nodes_path = self.get_custom_nodes_path()
        if is_enabled:
            # 如果节点已启用，路径在custom_nodes下
            node_path = os.path.join(custom_nodes_path, original_name)
        
        # 检查路径是否存在
        if os.path.exists(node_path):
            # 使用系统默认程序打开文件夹
            os.startfile(node_path)
        else:
            MessageBox("错误", f"文件夹不存在：{node_path}", self).exec()
    
    def open_req_file_for_node(self, node_name):
        """为指定节点打开requirements.txt文件，动态获取正确路径"""
        # 动态计算正确的路径
        custom_nodes_path = self.get_custom_nodes_path()
        
        # 尝试在启用的节点中查找
        node_path = os.path.join(custom_nodes_path, node_name)
        req_path = os.path.join(node_path, "requirements.txt")
        
        # 检查requirements.txt文件是否存在
        if os.path.exists(req_path):
            # 使用系统默认程序打开文件
            self.open_req_file(req_path)
        else:
            MessageBox("错误", f"依赖文件不存在：{req_path}", self).exec()
    
    def install_comfyui_requirements(self):
        """安装ComfyUI本体依赖"""
        # 显示确认弹窗
        msg_box = MessageBox("确认安装", "直接安装本体依赖可能会产生不可恢复的冲突，是否继续？", self)
        msg_box.yesButton.setText("确定")
        msg_box.cancelButton.setText("取消")
        
        # 如果用户点击取消，则不执行安装
        if msg_box.exec() != MessageBox.Accepted:
            print("[调试-install_comfyui_requirements] 用户取消了安装操作")
            return
        
        # 获取ComfyUI路径
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'settings_panel'):
            main_window = main_window.parent()
        
        if main_window and hasattr(main_window, 'settings_panel'):
            # 使用settings_panel中的方法获取ComfyUI路径
            comfyui_path = main_window.settings_panel.get_comfyui_path()
        else:
            # 如果无法获取settings_panel实例，使用默认路径
            if getattr(sys, 'frozen', False):
                # 如果是打包后的可执行文件，使用应用程序所在目录
                base_path = os.path.dirname(sys.executable)
            else:
                # 如果是脚本运行，使用当前工作目录
                base_path = os.getcwd()
            comfyui_path = os.path.join(base_path, "ComfyUI")
        
        # 构建requirements.txt文件的完整路径
        req_path = os.path.join(comfyui_path, "requirements.txt")
        
        print(f"[调试-install_comfyui_requirements] ComfyUI路径: {comfyui_path}")
        print(f"[调试-install_comfyui_requirements] requirements.txt路径: {req_path}")
        
        # 检查requirements.txt文件是否存在
        if os.path.exists(req_path):
            print(f"[调试-install_comfyui_requirements] ComfyUI requirements.txt文件存在，开始安装依赖")
            # 获取镜像源参数
            mirror_params = self._get_mirror_params()
            # 使用新的install_requirements_file方法
            self.install_requirements_file(req_path, mirror_params)
        else:
            print(f"[调试-install_comfyui_requirements] ComfyUI requirements.txt文件不存在: {req_path}")
            MessageBox("错误", f"未找到ComfyUI本体依赖文件：{req_path}", self).exec()
    
    def open_comfyui_requirements(self):
        """打开ComfyUI本体依赖文件"""
        # 获取ComfyUI路径
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'settings_panel'):
            main_window = main_window.parent()
        
        if main_window and hasattr(main_window, 'settings_panel'):
            # 使用settings_panel中的方法获取ComfyUI路径
            comfyui_path = main_window.settings_panel.get_comfyui_path()
        else:
            # 如果无法获取settings_panel实例，使用默认路径
            if getattr(sys, 'frozen', False):
                # 如果是打包后的可执行文件，使用应用程序所在目录
                base_path = os.path.dirname(sys.executable)
            else:
                # 如果是脚本运行，使用当前工作目录
                base_path = os.getcwd()
            comfyui_path = os.path.join(base_path, "ComfyUI")
        
        # 构建requirements.txt文件的完整路径
        req_path = os.path.join(comfyui_path, "requirements.txt")
        
        print(f"[调试-open_comfyui_requirements] ComfyUI路径: {comfyui_path}")
        print(f"[调试-open_comfyui_requirements] requirements.txt路径: {req_path}")
        
        # 检查requirements.txt文件是否存在
        if os.path.exists(req_path):
            # 使用系统默认程序打开文件
            self.open_req_file(req_path)
        else:
            MessageBox("错误", f"ComfyUI本体依赖文件不存在：{req_path}", self).exec()
    
    def get_comfyui_path(self):
        """获取ComfyUI路径的通用方法"""
        # 获取ComfyUI路径
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'settings_panel'):
            main_window = main_window.parent()
        
        if main_window and hasattr(main_window, 'settings_panel'):
            # 使用settings_panel中的方法获取ComfyUI路径
            return main_window.settings_panel.get_comfyui_path()
        else:
            # 如果无法获取settings_panel实例，使用默认路径
            if getattr(sys, 'frozen', False):
                # 如果是打包后的可执行文件，使用应用程序所在目录
                base_path = os.path.dirname(sys.executable)
            else:
                # 如果是脚本运行，使用当前工作目录
                base_path = os.getcwd()
            return os.path.join(base_path, "ComfyUI")
    
    def parse_package_from_requirements(self, package_name):
        """从requirements.txt文件中解析指定包的完整依赖信息"""
        comfyui_path = self.get_comfyui_path()
        req_path = os.path.join(comfyui_path, "requirements.txt")
        
        if not os.path.exists(req_path):
            print(f"[调试-parse_package_from_requirements] requirements.txt文件不存在: {req_path}")
            return None
        
        try:
            with open(req_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                # 跳过空行和注释行
                if not line or line.startswith('#'):
                    continue
                
                # 检查是否包含目标包名
                if package_name.lower() in line.lower():
                    print(f"[调试-parse_package_from_requirements] 找到匹配行: {line}")
                    return line
            
            print(f"[调试-parse_package_from_requirements] 未找到包 {package_name}")
            return None
            
        except Exception as e:
            print(f"[错误-parse_package_from_requirements] 读取requirements.txt失败: {str(e)}")
            return None
    
    def install_single_dependency(self, dependency_spec):
        """安装单个依赖"""
        if not dependency_spec:
            return
        
        # 获取镜像源参数
        mirror_params = self._get_mirror_params()
        
        # 使用新的install_single_package方法
        self.install_single_package(dependency_spec, mirror_params)
    
    def install_frontend_dependencies(self):
        """安装前端依赖"""
        dependency = self.parse_package_from_requirements("comfyui-frontend-package")
        if dependency:
            self.install_single_dependency(dependency)
        else:
            MessageBox("错误", "未在requirements.txt中找到comfyui-frontend-package依赖", self).exec()
    
    def install_workflow_dependencies(self):
        """安装工作流依赖"""
        dependency = self.parse_package_from_requirements("comfyui-workflow-templates")
        if dependency:
            self.install_single_dependency(dependency)
        else:
            MessageBox("错误", "未在requirements.txt中找到comfyui-workflow-templates依赖", self).exec()
    
    def install_docs_dependencies(self):
        """安装文档依赖"""
        dependency = self.parse_package_from_requirements("comfyui-embedded-docs")
        if dependency:
            self.install_single_dependency(dependency)
        else:
            MessageBox("错误", "未在requirements.txt中找到comfyui-embedded-docs依赖", self).exec()
    
    def install_three_comfyui_dependencies(self):
        """安装ComfyUI本体前端、工作流、文档依赖（创建临时文件方式）"""
        # 获取所有需要安装的依赖
        dependencies = []
        
        # 解析前端依赖
        frontend_dep = self.parse_package_from_requirements("comfyui-frontend-package")
        if frontend_dep:
            dependencies.append(frontend_dep)
        
        # 解析工作流依赖
        workflow_dep = self.parse_package_from_requirements("comfyui-workflow-templates")
        if workflow_dep:
            dependencies.append(workflow_dep)
        
        # 解析文档依赖
        docs_dep = self.parse_package_from_requirements("comfyui-embedded-docs")
        if docs_dep:
            dependencies.append(docs_dep)
        
        if not dependencies:
            MessageBox("错误", "未在requirements.txt中找到任何ComfyUI相关依赖", self).exec()
            return
        
        # 获取ComfyUI路径
        comfyui_path = self.get_comfyui_path()
        req_three_path = os.path.join(comfyui_path, "req_three.txt")
        
        try:
            # 创建临时的req_three.txt文件
            with open(req_three_path, 'w', encoding='utf-8') as f:
                for dep in dependencies:
                    f.write(f"{dep}\n")
            
            print(f"[调试-install_three_comfyui_dependencies] 已创建临时文件: {req_three_path}")
            print(f"[调试-install_three_comfyui_dependencies] 文件内容: {dependencies}")
            
            # 获取镜像源参数
            mirror_params = self._get_mirror_params()
            
            # 使用install_requirements_file方法安装
            self.install_requirements_file(req_three_path, mirror_params)
            
        except Exception as e:
            MessageBox("错误", f"创建临时依赖文件时出错：{str(e)}", self).exec()
            return
        finally:
            # 安装完成后删除临时文件
            try:
                if os.path.exists(req_three_path):
                    os.remove(req_three_path)
                    print(f"[调试-install_three_comfyui_dependencies] 已删除临时文件: {req_three_path}")
            except Exception as e:
                print(f"[调试-install_three_comfyui_dependencies] 删除临时文件失败: {str(e)}")
    
    # ==================== 重构的依赖安装方法 ====================
    
    def _get_python_exe_path(self):
        """获取Python解释器路径的内部方法"""
        # 获取主窗口中的settings_panel实例
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'settings_panel'):
            main_window = main_window.parent()
        
        if main_window and hasattr(main_window, 'settings_panel'):
            # 使用settings_panel中的方法获取Python解释器路径
            return main_window.settings_panel.get_python_exe_path()
        else:
            # 如果无法获取settings_panel实例，使用默认路径
            return ".\\python_embeded\\python.exe"
    
    def get_python_interpreter_path(self):
        """获取Python解释器路径（供外部调用）"""
        return self._get_python_exe_path()
    
    def _get_mirror_params(self):
        """获取镜像源参数的内部方法"""
        mirror_params = self.mirror_combobox.currentData()
        if not mirror_params:
            mirror_params = self.nodes_data_model.get_value('pip_mirror', 'mirror_source')
        return mirror_params if mirror_params else ""
    
    def _setup_proxy_env(self):
        """设置代理环境变量的内部方法"""
        env = os.environ.copy()
        use_proxy = self.proxy_checkbox.isChecked()
        
        if use_proxy:
            http_proxy = self.data_model.get_value('proxy', 'http_proxy')
            proxy_port = self.data_model.get_value('proxy', 'port')
            proxy_type = self.data_model.get_value('proxy', 'proxy_type', 'system')
            
            if isinstance(proxy_type, str) and proxy_type.strip().lower() == 'socks5':
                proxy_url = f"socks5://{http_proxy}:{proxy_port}"
            else:
                proxy_url = f"http://{http_proxy}:{proxy_port}"
            
            env['http_proxy'] = proxy_url
            env['https_proxy'] = proxy_url
        
        return env
    
    def install_single_package(self, package_name, mirror_params):
        """安装单个依赖包
        
        Args:
            package_name (str): 包名或包规格
            mirror_params (str): 国内源参数
        """
        if not package_name:
            return
        
        python_exe_path = self._get_python_exe_path()
        
        # 构建安装命令
        install_cmd = f'"{python_exe_path}" -m pip install "{package_name}"'
        
        # 添加镜像源参数
        if mirror_params:
            install_cmd += f' {mirror_params}'
        
        # 设置环境变量
        env = self._setup_proxy_env()
        
        print(f"[调试-install_single_package] 最终执行的安装命令: {install_cmd}")
        
        try:
            # 创建信息对话框
            info_dialog = MessageBox("安装依赖", f"正在安装 {package_name}，请稍候...\n\n命令行窗口关闭后此对话框将自动关闭。", self)
            
            # 启动cmd窗口运行安装命令
            display_cmd = f'echo 执行命令: {install_cmd} & echo. & {install_cmd} & pause'
            process = subprocess.Popen(f'cmd.exe /c "{display_cmd}"', 
                                    creationflags=subprocess.CREATE_NEW_CONSOLE, env=env)
            
            # 创建一个定时器来检查进程状态
            timer = QTimer(self)
            
            def check_process():
                if process.poll() is not None:
                    timer.stop()
                    info_dialog.accept()
            
            timer.timeout.connect(check_process)
            timer.start(500)
            
            info_dialog.exec()
            timer.stop()
            
            if process.poll() is None:
                try:
                    process.terminate()
                except Exception:
                    pass
            
        except Exception as e:
            MessageBox("错误", f"执行命令时出错：{str(e)}", self).exec()
    
    def on_search_text_changed(self, text):
        """搜索文本变化时的处理"""
        self.search_matches.clear()
        self.current_match_index = -1
        
        if not text.strip():
            # 如果搜索文本为空，清除所有高亮并禁用导航按钮
            self.clear_all_highlights()
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.search_edit.setCountText("")  # 清除计数文本
            return
        
        # 搜索匹配的项目
        search_text = text.lower()
        for i in range(self.nodes_list.count()):
            item = self.nodes_list.item(i)
            if item:
                data = item.data(Qt.UserRole)
                if data and isinstance(data, dict):
                    display_name = data.get("display_name", "")
                    if search_text in display_name.lower():
                        self.search_matches.append(i)
        
        # 更新高亮显示
        self.update_search_highlights(search_text)
        
        # 更新导航按钮状态
        has_matches = len(self.search_matches) > 0
        self.prev_button.setEnabled(has_matches)
        self.next_button.setEnabled(has_matches)
        
        # 更新搜索结果计数
        if has_matches:
            self.current_match_index = 0
            self.update_search_count_label()
            self.nodes_list.setCurrentRow(self.search_matches[0])
            self.nodes_list.scrollToItem(self.nodes_list.item(self.search_matches[0]))
        else:
            self.search_edit.setCountText("")  # 清除计数文本
    
    def update_search_highlights(self, search_text):
        """更新搜索高亮显示"""
        for i in range(self.nodes_list.count()):
            item = self.nodes_list.item(i)
            if item:
                widget = self.nodes_list.itemWidget(item)
                if widget:
                    # 查找名称标签
                    name_label = None
                    for child in widget.findChildren(BodyLabel):
                        if hasattr(child, 'property') and child.property("original_text"):
                            name_label = child
                            break
                    
                    if name_label:
                        original_text = name_label.property("original_text")
                        if search_text and search_text in original_text.lower():
                            # 高亮匹配的文本
                            highlighted_text = self.highlight_text(original_text, search_text)
                            name_label.setText(highlighted_text)
                        else:
                            # 恢复原始文本
                            name_label.setText(original_text)
                        name_label.setStyleSheet("color: #00a7b3; font-weight: bold;")
    
    def highlight_text(self, text, search_text):
        """为文本添加高亮标记"""
        if not search_text:
            return text
        
        # 使用HTML标记来高亮文本
        import re
        pattern = re.compile(re.escape(search_text), re.IGNORECASE)
        highlighted = pattern.sub(f'<span style="background-color: yellow; color: black;">{search_text}</span>', text)
        return highlighted
    
    def clear_all_highlights(self):
        """清除所有高亮显示"""
        for i in range(self.nodes_list.count()):
            item = self.nodes_list.item(i)
            if item:
                widget = self.nodes_list.itemWidget(item)
                if widget:
                    # 查找名称标签
                    name_label = None
                    for child in widget.findChildren(BodyLabel):
                        if hasattr(child, 'property') and child.property("original_text"):
                            name_label = child
                            break
                    
                    if name_label:
                        # 恢复原始文本
                        original_text = name_label.property("original_text")
                        name_label.setText(original_text)
                        name_label.setStyleSheet("color: #00a7b3; font-weight: bold;")
    
    def update_search_count_label(self):
        """更新搜索结果计数标签"""
        if self.search_matches and self.current_match_index >= 0:
            total = len(self.search_matches)
            current = self.current_match_index + 1  # 显示为1-based索引
            self.search_edit.setCountText(f"{current}/{total}")
        else:
            self.search_edit.setCountText("")
            
    # check_nodes_updates函数已删除，保留git_nodes_update_info.py文件以备后续功能更新
    
    def update_nodes_version_info(self):
        """获取当前节点版本信息并更新到ini文件"""
        try:
            # 创建信息对话框
            from PySide6.QtWidgets import QVBoxLayout, QLabel
            from qfluentwidgets import MessageBox
            
            # 创建简化的对话框，不再显示进度信息
            msg_box = MessageBox("正在获取版本信息", "正在获取本自定义节点版本信息，完成之后本窗口会自动关闭。请稍后...", self)
            msg_box.setWindowFlag(Qt.WindowCloseButtonHint, False)  # 禁用关闭按钮
            msg_box.show()
            
            def process_complete():
                msg_box.accept()
                
                # 从INI文件加载版本信息并应用到UI
                import nodes_local_info
                version_info = nodes_local_info.load_version_info_from_ini()
                nodes_local_info.apply_version_info_to_ui(self.nodes_list, version_info)
                
                # 刷新节点列表
                self.load_nodes(force_reload_from_folder=False)
            
            # 在QThread中执行更新操作
            from PySide6.QtCore import QThread, Signal
            
            class UpdateThread(QThread):
                complete_signal = Signal()
                error_signal = Signal(str)
                
                def run(self):
                    try:
                        import nodes_local_info
                        
                        # 直接执行更新
                        nodes_local_info.update_nodes_version_info()
                        
                        self.complete_signal.emit()
                    except Exception as e:
                        print(f"[错误-update_nodes_version_info] 更新节点版本信息失败: {str(e)}")
                        self.error_signal.emit(str(e))
            
            # 创建线程并连接信号
            self.update_thread = UpdateThread()
            self.update_thread.complete_signal.connect(process_complete)
            self.update_thread.error_signal.connect(lambda error_msg: MessageBox("执行失败", f"获取版本信息时出错：{error_msg}", self).exec())
            self.update_thread.start()
            
        except Exception as e:
            MessageBox("执行失败", f"获取版本信息时出错：{str(e)}", self).exec()
    
    # 节点版本信息相关方法已移动到 nodes_local_info.py 中
    
    def apply_update_info(self):
        """应用更新信息到节点列表"""
        try:
            # 导入节点本地信息模块
            import nodes_local_info
            
            # 从INI文件加载版本信息
            version_info = nodes_local_info.load_version_info_from_ini()
            
            # 应用版本信息到UI
            nodes_local_info.apply_version_info_to_ui(self.nodes_list, version_info)
                
        except Exception as e:
            print(f"[错误-apply_update_info] 应用更新信息时出错: {str(e)}")
            MessageBox("错误", f"应用更新信息时出错：{str(e)}", self).exec()
    
    def update_single_node(self, checkbox):
        """更新单个节点"""
        try:
            # 获取节点信息
            display_name = checkbox.property("display_name")
            original_name = checkbox.property("original_name")
            node_path = checkbox.property("node_path")
            is_enabled = checkbox.property("is_enabled")
            
            if not is_enabled:
                MessageBox("错误", "只能更新已启用的节点", self).exec()
                return
            
            # 首先尝试从nodes_list_git.ini获取Git信息
            git_info = self.get_node_git_info(display_name)
            
            # 如果没有获取到Git信息，检查是否是git仓库
            if not git_info and not os.path.exists(os.path.join(node_path, '.git')):
                MessageBox("错误", f"节点 {display_name} 不是通过Git安装的，无法更新", self).exec()
                return
            
            # 导入节点更新对话框
            from nodes_update_single import NodeUpdateDialog
            
            # 获取代理设置
            proxy_enabled = self.proxy_checkbox.isChecked()
            proxy_url = self.proxy_edit.text() if proxy_enabled else ""
            
            # 获取镜像源设置
            mirror_index = self.mirror_combobox.currentIndex()
            
            # 创建并显示节点更新对话框
            update_dialog = NodeUpdateDialog(
                node_name=display_name,
                node_path=node_path,
                proxy_enabled=proxy_enabled,
                proxy_url=proxy_url,
                mirror_index=mirror_index,
                parent=self,
                git_info=git_info  # 传递Git信息
            )
            
            # 显示对话框
            result = update_dialog.exec()
            
            # 如果对话框成功关闭（用户完成了操作），刷新节点列表
            if result == QDialog.Accepted:
                # 刷新节点列表，不再自动应用更新信息
                self.load_nodes(force_reload_from_folder=False)
            
        except Exception as e:
            print(f"[错误-update_single_node] 更新节点时出错: {str(e)}")
            MessageBox("执行失败", f"更新节点时出错：{str(e)}", self).exec()
    
    # 节点Git版本信息相关方法已移动到 nodes_local_info.py 中
    
    def get_node_git_info(self, node_name):
        """从nodes_list_git.ini文件获取节点的Git信息
        
        Args:
            node_name: 节点名称
            
        Returns:
            dict: 节点的Git信息，如果没有找到则返回None
        """
        try:
            # 读取nodes_list_git.ini文件
            nodes_list_git_ini = os.path.join('starter', 'nodes_list_git.ini')
            if not os.path.exists(nodes_list_git_ini):
                print(f"[警告-get_node_git_info] 节点Git信息文件不存在: {nodes_list_git_ini}")
                return None
            
            config = configparser.ConfigParser()
            config.read(nodes_list_git_ini, encoding='utf-8')
            
            # 检查是否有git_info部分
            if not config.has_section('git_info'):
                print(f"[警告-get_node_git_info] 节点Git信息文件中没有git_info部分")
                return None
            
            # 检查节点是否在git_info部分中
            has_update_key = f'{node_name}_has_update'
            if not config.has_option('git_info', has_update_key):
                print(f"[警告-get_node_git_info] 节点 {node_name} 的Git信息不存在")
                return None
            
            # 获取节点的Git信息
            git_info = {}
            
            # 基本信息
            git_info['has_update'] = config.getboolean('git_info', has_update_key)
            git_info['current_version'] = config.get('git_info', f'{node_name}_current_version')
            git_info['latest_version'] = config.get('git_info', f'{node_name}_latest_version')
            git_info['update_msg'] = config.get('git_info', f'{node_name}_update_msg')
            
            # 可选信息
            if config.has_option('git_info', f'{node_name}_current_commit'):
                git_info['current_commit'] = config.get('git_info', f'{node_name}_current_commit')
            
            if config.has_option('git_info', f'{node_name}_branch'):
                git_info['branch'] = config.get('git_info', f'{node_name}_branch')
            
            if config.has_option('git_info', f'{node_name}_remote_url'):
                git_info['remote_url'] = config.get('git_info', f'{node_name}_remote_url')
            
            return git_info
            
        except Exception as e:
            print(f"[错误-get_node_git_info] 获取节点 {node_name} 的Git信息时出错: {str(e)}")
            return None
    
    def go_to_previous_match(self):
        """跳转到上一个匹配项"""
        if not self.search_matches:
            return
        
        self.current_match_index = (self.current_match_index - 1) % len(self.search_matches)
        row = self.search_matches[self.current_match_index]
        self.nodes_list.setCurrentRow(row)
        self.nodes_list.scrollToItem(self.nodes_list.item(row))
        self.update_search_count_label()  # 更新计数标签
    
    def go_to_next_match(self):
        """跳转到下一个匹配项"""
        if not self.search_matches:
            return
        
        self.current_match_index = (self.current_match_index + 1) % len(self.search_matches)
        row = self.search_matches[self.current_match_index]
        self.nodes_list.setCurrentRow(row)
        self.nodes_list.scrollToItem(self.nodes_list.item(row))
        self.update_search_count_label()  # 更新计数标签
    
    def uninstall_single_package(self, package_name, mirror_params):
        """卸载单个依赖包
        
        Args:
            package_name (str): 包名
            mirror_params (str): 国内源参数（卸载时不使用）
        """
        if not package_name:
            return
        
        python_exe_path = self._get_python_exe_path()
        
        # 构建卸载命令
        uninstall_cmd = f'"{python_exe_path}" -m pip uninstall "{package_name}" -y'
        
        # 设置环境变量
        env = self._setup_proxy_env()
        
        print(f"[调试-uninstall_single_package] 最终执行的卸载命令: {uninstall_cmd}")
        
        try:
            # 创建信息对话框
            info_dialog = MessageBox("卸载依赖", f"正在卸载 {package_name}，请稍候...\n\n命令行窗口关闭后此对话框将自动关闭。", self)
            
            # 启动cmd窗口运行卸载命令
            display_cmd = f'echo 执行命令: {uninstall_cmd} & echo. & {uninstall_cmd} & pause'
            process = subprocess.Popen(f'cmd.exe /c "{display_cmd}"', 
                                    creationflags=subprocess.CREATE_NEW_CONSOLE, env=env)
            
            # 创建一个定时器来检查进程状态
            timer = QTimer(self)
            
            def check_process():
                if process.poll() is not None:
                    timer.stop()
                    info_dialog.accept()
            
            timer.timeout.connect(check_process)
            timer.start(500)
            
            info_dialog.exec()
            timer.stop()
            
            if process.poll() is None:
                try:
                    process.terminate()
                except Exception:
                    pass
            
        except Exception as e:
            MessageBox("错误", f"执行命令时出错：{str(e)}", self).exec()
    
    def install_whl_package(self, whl_path, mirror_params):
        """安装WHL依赖包
        
        Args:
            whl_path (str): WHL文件路径
            mirror_params (str): 国内源参数（WHL安装时不使用）
        """
        if not whl_path:
            return
        
        python_exe_path = self._get_python_exe_path()
        
        # 构建安装命令
        if whl_path.startswith('"') and whl_path.endswith('"'):
            install_cmd = f'"{python_exe_path}" -m pip install {whl_path}'
        else:
            install_cmd = f'"{python_exe_path}" -m pip install "{whl_path}"'
        
        # 设置环境变量
        env = self._setup_proxy_env()
        
        print(f"[调试-install_whl_package] 最终执行的安装命令: {install_cmd}")
        
        try:
            # 创建信息对话框
            info_dialog = MessageBox("安装WHL", f"正在安装 WHL 文件，请稍候...\n\n命令行窗口关闭后此对话框将自动关闭。", self)
            
            # 启动cmd窗口运行安装命令
            display_cmd = f'echo 执行命令: {install_cmd} & echo. & {install_cmd} & pause'
            process = subprocess.Popen(f'cmd.exe /c "{display_cmd}"', 
                                    creationflags=subprocess.CREATE_NEW_CONSOLE, env=env)
            
            # 创建一个定时器来检查进程状态
            timer = QTimer(self)
            
            def check_process():
                if process.poll() is not None:
                    timer.stop()
                    info_dialog.accept()
            
            timer.timeout.connect(check_process)
            timer.start(500)
            
            info_dialog.exec()
            timer.stop()
            
            if process.poll() is None:
                try:
                    process.terminate()
                except Exception:
                    pass
            
        except Exception as e:
            MessageBox("错误", f"执行命令时出错：{str(e)}", self).exec()
    
    def install_requirements_file(self, requirements_path, mirror_params):
        """安装依赖文件
        
        Args:
            requirements_path (str): requirements.txt文件路径
            mirror_params (str): 国内源参数
        """
        if not requirements_path:
            return
        
        python_exe_path = self._get_python_exe_path()
        
        # 构建安装命令
        if requirements_path.startswith('"') and requirements_path.endswith('"'):
            install_cmd = f'"{python_exe_path}" -m pip install -r {requirements_path}'
        else:
            install_cmd = f'"{python_exe_path}" -m pip install -r "{requirements_path}"'
        
        # 添加镜像源参数
        if mirror_params:
            install_cmd += f' {mirror_params}'
        
        # 设置环境变量
        env = self._setup_proxy_env()
        
        print(f"[调试-install_requirements_file] 最终执行的安装命令: {install_cmd}")
        
        try:
            # 创建信息对话框
            info_dialog = MessageBox("安装依赖文件", f"正在安装依赖文件，请稍候...\n\n命令行窗口关闭后此对话框将自动关闭。", self)
            
            # 启动cmd窗口运行安装命令
            display_cmd = f'echo 执行命令: {install_cmd} & echo. & {install_cmd} & pause'
            process = subprocess.Popen(f'cmd.exe /c "{display_cmd}"', 
                                    creationflags=subprocess.CREATE_NEW_CONSOLE, env=env)
            
            # 创建一个定时器来检查进程状态
            timer = QTimer(self)
            
            def check_process():
                if process.poll() is not None:
                    timer.stop()
                    info_dialog.accept()
            
            timer.timeout.connect(check_process)
            timer.start(500)
            
            info_dialog.exec()
            timer.stop()
            
            if process.poll() is None:
                try:
                    process.terminate()
                except Exception:
                    pass
            
        except Exception as e:
            MessageBox("错误", f"执行命令时出错：{str(e)}", self).exec()
    
