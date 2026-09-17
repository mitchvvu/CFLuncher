import os
import sys
import time
import configparser
import webbrowser
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QLabel, QPushButton, QDialog
from PySide6.QtCore import Qt, Signal, QProcess, QSize, QTimer
from PySide6.QtGui import QFont, QIcon, QWheelEvent

from qfluentwidgets import (
    CardWidget, StrongBodyLabel, BodyLabel, TextBrowser, PushButton, PrimaryPushButton, InfoBar, InfoBarPosition,
    setTheme, Theme, FluentIcon, MessageBox, CheckBox, ComboBox, SegmentedWidget
)



import git
from data_model import DataModel


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

class VersionPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.data_model = DataModel()
        self.process = None
        self.repo = None
        self.versions = []
        self.versions_file = os.path.join('starter', 'git.ini')
        self.settings_file = os.path.join('starter', 'version.ini')
        # 添加定时器成员变量
        self.load_timer = QTimer(self)
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self.load_initial_versions)
        
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self.refresh_versions)
        
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_version_list)
        
        # 初始化刷新标志
        self.is_refreshing = False
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建版本设置卡片
        version_card = CardWidget()
        version_main_layout = QVBoxLayout()
        version_main_layout.addWidget(StrongBodyLabel("ComfyUI 版本管理"))
        
        # 顶部控制区域
        top_control_layout = QHBoxLayout()
        
        # 代理设置
        self.proxy_checkbox = CheckBox("启用代理")
        self.proxy_checkbox.setToolTip("启用代理后将使用设置面板中的代理配置")
        self.proxy_checkbox.stateChanged.connect(self.save_version_settings)
        top_control_layout.addWidget(self.proxy_checkbox)
        
        # 源选择
        top_control_layout.addWidget(BodyLabel("源选择:"))
        self.source_combo = ComboBox()
        # 源配置列表
        source_configs = [
            ("GitHub官方(国外)", "https://github.com/Comfy-Org/ComfyUI.git")
        ]
        
        # 添加项目并设置数据
        for name, url in source_configs:
            self.source_combo.addItem(name)
            index = self.source_combo.count() - 1
            self.source_combo.setItemData(index, url)
        
        # 设置当前选中的源
        current_source_url = self.data_model.get_value('version_manager', 'git_source_url', 'https://github.com/Comfy-Org/ComfyUI.git')
        for i in range(self.source_combo.count()):
            if self.source_combo.itemData(i) == current_source_url:
                self.source_combo.setCurrentIndex(i)
                break
        top_control_layout.addWidget(self.source_combo)
        
        # 刷新和执行按钮
        self.refresh_button = PushButton("刷新")
        self.refresh_button.setIcon(FluentIcon.SYNC)
        self.refresh_button.clicked.connect(self.refresh_versions_delayed)
        top_control_layout.addWidget(self.refresh_button)
        
        version_main_layout.addLayout(top_control_layout)
        
        # 源信息显示
        source_info_layout = QHBoxLayout()
        source_info_layout.addWidget(BodyLabel("当前源:"))
        self.source_label = BodyLabel("")
        source_info_layout.addWidget(self.source_label)
        source_info_layout.addStretch()
        version_main_layout.addLayout(source_info_layout)
        
        # ComfyUI状态
        status_layout = QHBoxLayout()
        status_layout.addWidget(BodyLabel("ComfyUI状态:"))
        self.status_label = BodyLabel("未检测")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        version_main_layout.addLayout(status_layout)
        
        # 版本选项卡和列表
        
        version_card.setLayout(version_main_layout)
        layout.addWidget(version_card)
        
        # 创建可用版本卡片
        version_list_card = CardWidget()
        version_list_layout = QVBoxLayout()
        version_list_layout.addWidget(StrongBodyLabel("可用版本"))
        
        # 创建选项卡
        self.version_tabs = SegmentedWidget()
        self.version_tabs.addItem("stable", "稳定版")
        self.version_tabs.addItem("dev", "开发版")
        self.version_tabs.setCurrentItem("stable")
        self.version_tabs.currentItemChanged.connect(self.on_tab_changed)
        version_list_layout.addWidget(self.version_tabs)
        
        # 版本列表 - 使用类似节点管理的表格样式
        self.version_list = SingleRowScrollListWidget()
        self.version_list.setMinimumHeight(605)
        
        # 添加虚拟化支持（如果版本数量很大）
        self.version_list.setUniformItemSizes(True)  # 统一项目大小以提高性能
        
        # 优化滚动性能
        self.version_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        
        # 设置列表样式为类似表格的布局
        self.version_list.setStyleSheet("""
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
        version_list_layout.addWidget(self.version_list)
        
        # 当前选中的选项卡
        self.current_tab = "stable"
        
        # 添加切换版本按钮，占据整行，使用PrimaryPushButton与启动面板保持一致
        self.execute_button = PrimaryPushButton("切换版本")
        self.execute_button.clicked.connect(self.switch_version)
        self.execute_button.setMinimumHeight(40)
        version_list_layout.addWidget(self.execute_button)
        
        # 版本列表卡片布局设置完成
        
        version_list_card.setLayout(version_list_layout)
        layout.addWidget(version_list_card)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # 初始化源显示
        self.update_source_display()
        
        # 连接信号
        self.source_combo.currentIndexChanged.connect(self.update_source_display)
        self.source_combo.currentIndexChanged.connect(self.save_source_settings)
        self.source_combo.currentIndexChanged.connect(self.save_version_settings)
        
        # 初始化时检查仓库状态并自动选择正确的选项卡
        if self.check_repo_status():
            try:
                current_commit = self.repo.head.commit.hexsha
                
                # 检查当前版本是分支还是标签
                is_branch = False
                for branch in self.repo.branches:
                    if branch.commit.hexsha == current_commit:
                        is_branch = True
                        break
                
                # 根据版本类型设置初始选项卡
                if is_branch:
                    self.current_tab = "dev"
                else:
                    self.current_tab = "stable"
                    
            except Exception as e:
                print(f"初始化选项卡失败: {str(e)}")
        
        # 无论仓库状态如何，都更新选项卡状态（在version_tabs创建之后）
        self.update_tab_button_states()
        
        # 加载版本管理面板设置
        self.load_version_settings()
    
    def showEvent(self, event):
        """面板显示事件"""
        super().showEvent(event)
        # 检查窗口状态，如果不是最小化状态，则加载版本列表
        if not self.window().isMinimized():
            self.load_versions_delayed()
    
    def hideEvent(self, event):
        """面板隐藏事件，取消所有正在进行的延时加载"""
        super().hideEvent(event)
        # 停止所有正在进行的定时器
        if self.load_timer.isActive():
            self.load_timer.stop()
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        if self.update_timer.isActive():
            self.update_timer.stop()
        # 如果有正在运行的git进程，停止它
        if self.process and self.process.state() == QProcess.Running:
            # 先断开所有信号连接，避免触发回调
            self.process.disconnect()
            self.process.kill()
            print("已停止正在运行的git进程")
            # 如果是在刷新版本列表时切换面板，显示一个小提示
            if hasattr(self, 'is_refreshing') and self.is_refreshing:
                # 使用QTimer延迟显示提示，确保在主窗口切换后显示
                QTimer.singleShot(300, lambda: InfoBar.info(
                    title="已取消",
                    content="版本列表刷新已取消",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=2000,
                    parent=self.window()
                ))
                self.is_refreshing = False
    
    def handle_window_state_change(self, minimized):
        """处理窗口状态变化"""
        if minimized:
            # 窗口最小化时暂停所有加载操作
            if self.load_timer.isActive():
                self.load_timer.stop()
            if self.refresh_timer.isActive():
                self.refresh_timer.stop()
            if self.update_timer.isActive():
                self.update_timer.stop()
            # 如果有正在运行的git进程，停止它
            if self.process and self.process.state() == QProcess.Running:
                # 先断开所有信号连接，避免触发回调
                self.process.disconnect()
                self.process.kill()
                print("窗口最小化，已停止正在运行的git进程")
                # 如果是在刷新版本列表时最小化窗口，重置刷新标志
                if hasattr(self, 'is_refreshing') and self.is_refreshing:
                    self.is_refreshing = False
    
    def load_versions_delayed(self):
        """延时加载版本列表"""
        # 停止所有可能正在运行的定时器
        if self.load_timer.isActive():
            self.load_timer.stop()
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        if self.update_timer.isActive():
            self.update_timer.stop()
        
        # 如果窗口处于最小化状态，不启动加载
        if self.window().isMinimized():
            print("窗口最小化状态，不加载版本列表")
            return
            
        # 设置刷新标志，用于在hideEvent中判断是否正在刷新
        self.is_refreshing = True
            
        # 清除现有版本列表
        self.version_list.clear()
        
        # 创建加载提示项，样式与节点面板一致
        loading_item = QListWidgetItem()
        loading_widget = QWidget()
        loading_layout = QHBoxLayout(loading_widget)
        loading_layout.setContentsMargins(10, 6, 10, 6)  # 与其他版本项保持一致的边距
        loading_layout.setSpacing(0)  # 减少内部间距
        loading_layout.setAlignment(Qt.AlignCenter)
        
        loading_label = BodyLabel("正在加载版本列表...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_layout.addWidget(loading_label)
        
        # 设置与其他版本项一致的高度
        size_hint = loading_widget.sizeHint()
        size_hint.setHeight(55)  # 与其他版本项保持一致的高度
        loading_item.setSizeHint(size_hint)
        self.version_list.addItem(loading_item)
        self.version_list.setItemWidget(loading_item, loading_widget)
        
        # 使用类成员定时器延迟加载版本列表，延迟0.35秒
        self.load_timer.start(350)
    
    def load_initial_versions(self):
        """加载初始版本列表"""
        # 尝试从文件加载版本信息
        if os.path.exists(self.versions_file):
            print("正在从文件加载版本信息...")
            self.load_versions_from_file()
        
        # 更新版本列表显示
        self.update_version_list()
        
        # 重置刷新标志
        self.is_refreshing = False
    
    def refresh_versions_delayed(self):
        """延时刷新版本列表"""
        # 停止所有可能正在运行的定时器
        if self.load_timer.isActive():
            self.load_timer.stop()
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        if self.update_timer.isActive():
            self.update_timer.stop()
        
        # 如果窗口处于最小化状态，不启动刷新
        if self.window().isMinimized():
            print("窗口最小化状态，不刷新版本列表")
            return
            
        # 设置刷新标志，用于在hideEvent中判断是否正在刷新
        self.is_refreshing = True
            
        # 清除现有版本列表
        self.version_list.clear()
        
        # 创建加载提示项，样式与节点面板一致
        loading_item = QListWidgetItem()
        loading_widget = QWidget()
        loading_layout = QHBoxLayout(loading_widget)
        loading_layout.setContentsMargins(10, 6, 10, 6)  # 与其他版本项保持一致的边距
        loading_layout.setSpacing(0)  # 减少内部间距
        loading_layout.setAlignment(Qt.AlignCenter)
        
        loading_label = BodyLabel("正在刷新版本列表...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_layout.addWidget(loading_label)
        
        # 设置与其他版本项一致的高度
        size_hint = loading_widget.sizeHint()
        size_hint.setHeight(55)  # 与其他版本项保持一致的高度
        loading_item.setSizeHint(size_hint)
        self.version_list.addItem(loading_item)
        self.version_list.setItemWidget(loading_item, loading_widget)
        
        # 使用类成员定时器延迟刷新版本列表，延迟35秒
        self.refresh_timer.start(350)
    
    def update_source_display(self):
        """更新源显示"""
        source_url = self.source_combo.currentData()
        if source_url is None:
            source_url = "https://github.com/Comfy-Org/ComfyUI.git"
        self.source_label.setText(source_url)

    def save_source_settings(self):
        """保存源设置"""
        current_source_url = self.source_combo.currentData()
        self.data_model.set_value('version_manager', 'git_source_url', current_source_url)
        InfoBar.success(
            title="设置已保存",
            content="版本管理源设置已保存",
            duration=3000,
            parent=self,
            position=InfoBarPosition.TOP_RIGHT
        )
    
    def load_version_settings(self):
        """从starter文件夹加载版本管理面板设置"""
        try:
            if os.path.exists(self.settings_file):
                config = configparser.ConfigParser()
                config.read(self.settings_file, encoding='utf-8')
                
                # 加载代理设置，默认关闭
                proxy_enabled = config.getboolean('settings', 'proxy_enabled', fallback=False)
                self.proxy_checkbox.setChecked(proxy_enabled)
                
                # 加载源选择设置，默认选择GitHub官方
                source_url = config.get('settings', 'source_url', fallback='https://github.com/Comfy-Org/ComfyUI.git')
                for i in range(self.source_combo.count()):
                    if self.source_combo.itemData(i) == source_url:
                        self.source_combo.setCurrentIndex(i)
                        break
                
                print("版本管理面板设置加载成功")
            else:
                # 如果文件不存在，设置默认值
                self.proxy_checkbox.setChecked(False)  # 默认关闭代理
                # 默认选择GitHub官方
                for i in range(self.source_combo.count()):
                    if self.source_combo.itemData(i) == 'https://github.com/Comfy-Org/ComfyUI.git':
                        self.source_combo.setCurrentIndex(i)
                        break
                print("使用默认版本管理面板设置")
        except Exception as e:
            print(f"加载版本管理面板设置失败: {str(e)}")
    
    def save_version_settings(self):
        """保存版本管理面板设置到starter文件夹"""
        try:
            # 确保starter文件夹存在
            os.makedirs('starter', exist_ok=True)
            
            config = configparser.ConfigParser()
            
            # 如果文件已存在，先读取现有内容
            if os.path.exists(self.settings_file):
                config.read(self.settings_file, encoding='utf-8')
            
            # 确保settings节存在
            if not config.has_section('settings'):
                config.add_section('settings')
            
            # 保存代理设置
            config.set('settings', 'proxy_enabled', str(self.proxy_checkbox.isChecked()))
            
            # 保存源选择设置
            current_source_url = self.source_combo.currentData()
            if current_source_url:
                config.set('settings', 'source_url', current_source_url)
            
            # 保存更新时间
            config.set('settings', 'last_updated', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            # 写入文件
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                config.write(f)
            
            print("版本管理面板设置已保存")
        except Exception as e:
            print(f"保存版本管理面板设置失败: {str(e)}")
    
    def get_comfyui_path(self):
        """获取ComfyUI路径
        
        从settings_panel获取ComfyUI路径，避免重复逻辑
        
        Returns:
            str: ComfyUI路径
        """
        # 获取主窗口中的settings_panel实例
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'settings_panel'):
            main_window = main_window.parent()
        
        if main_window and hasattr(main_window, 'settings_panel'):
            # 使用settings_panel中的方法获取ComfyUI路径
            return main_window.settings_panel.get_comfyui_path()
        else:
            # 如果无法获取settings_panel实例，使用默认路径
            # 获取当前程序所在目录，考虑打包后的环境
            if getattr(sys, 'frozen', False):
                # 如果是打包后的可执行文件，使用应用程序根目录
                base_path = os.path.dirname(sys.executable)
            else:
                # 如果是脚本运行，使用脚本所在目录
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            return os.path.join(base_path, 'ComfyUI')
    
    def check_repo_status(self):
        """检查仓库状态"""
        try:
            # 获取ComfyUI路径
            comfyui_path = self.get_comfyui_path()
            
            if not os.path.exists(comfyui_path):
                self.status_label.setText("未找到ComfyUI文件夹")
                print(f"错误: 路径不存在 - {comfyui_path}")
                return False
            
            # 检查是否为git仓库
            git_dir = os.path.join(comfyui_path, '.git')
            if not os.path.exists(git_dir):
                self.status_label.setText("不是Git仓库")
                print(f"错误: 不是Git仓库 (没有.git目录)")
                return False
                
            # 使用GitPython打开仓库
            self.repo = git.Repo(comfyui_path)
            
            # 检查是否处于分离头状态
            if self.repo.head.is_detached:
                self.status_label.setText("游离状态 (Detached HEAD)")
                print("仓库状态: 游离状态 (Detached HEAD)")
            else:
                # 获取当前分支名
                branch_name = self.repo.active_branch.name
                self.status_label.setText(f"分支: {branch_name}")
                print(f"仓库状态: 分支 {branch_name}")
            
            return True
        except git.exc.InvalidGitRepositoryError as e:
            self.status_label.setText("无效的Git仓库")
            print(f"错误: 无效的Git仓库 - {str(e)}")
            return False
        except git.exc.NoSuchPathError as e:
            self.status_label.setText("路径不存在")
            print(f"错误: Git路径不存在 - {str(e)}")
            return False
        except Exception as e:
            import traceback
            self.status_label.setText(f"检查失败: {str(e)}")
            print(f"检查仓库状态失败: {str(e)}")
            return False
    
    def refresh_versions(self):
        """刷新版本列表"""
        
        # 设置刷新标志，用于在hideEvent中判断是否正在刷新
        self.is_refreshing = True
        
        self.version_list.clear()
        self.versions = []
        
        # 检查仓库状态
        if not self.check_repo_status():
            print("无法获取版本信息: 仓库状态检查失败")
            
            # 尝试从文件加载版本信息
            if os.path.exists(self.versions_file):
                if self.load_versions_from_file():
                    print("成功从文件加载版本信息")
                    InfoBar.success(
                        title="加载成功",
                        content="已从本地文件加载版本信息",
                        duration=3000,
                        parent=self,
                        position=InfoBarPosition.TOP_RIGHT
                    )
                else:
                    print("从文件加载版本信息失败")
                    InfoBar.error(
                        title="加载失败",
                        content="无法从本地文件加载版本信息",
                        duration=3000,
                        parent=self,
                        position=InfoBarPosition.TOP_RIGHT
                    )
            return
            
        # 检查仓库状态并记录当前版本信息，但不自动切换选项卡
        try:
            current_commit = self.repo.head.commit.hexsha
            
            # 检查当前版本是分支还是标签
            is_branch = False
            for branch in self.repo.branches:
                if branch.commit.hexsha == current_commit:
                    is_branch = True
                    break
            
            # 仅记录当前版本类型，不自动切换选项卡
            version_type = "开发版(分支)" if is_branch else "稳定版(标签)"
        except Exception as e:
            print(f"检查当前版本类型失败: {str(e)}")
        
        try:
            # 获取远程仓库信息
            remote_url = self.source_combo.currentData()
            # 确保remote_url不为None
            if remote_url is None:
                # 如果为None，使用默认值
                remote_url = "https://github.com/Comfy-Org/ComfyUI.git"
                print(f"警告: 源URL为空，使用默认源")
            
            # 设置或更新远程仓库URL
            remote_name = "origin"
            try:
                # 检查远程仓库是否存在
                remote = self.repo.remote(remote_name)
                
                # 检查URL是否需要更新
                if remote.url != remote_url:
                    # 确保remote_url不为None
                    if remote_url is None:
                        remote_url = "https://github.com/Comfy-Org/ComfyUI.git"
                        print(f"警告: 更新远程仓库时URL为空，使用默认源")
                    
                    try:
                        self.repo.delete_remote(remote_name)
                        self.repo.create_remote(remote_name, remote_url)
                    except Exception as e:
                        print(f"更新远程仓库URL失败: {str(e)}")
                        raise
            except ValueError as e:
                # 如果远程仓库不存在，创建它
                try:
                    # 确保remote_url不为None
                    if remote_url is None:
                        remote_url = "https://github.com/Comfy-Org/ComfyUI.git"
                        print(f"警告: 创建远程仓库时URL为空，使用默认源")
                    
                    self.repo.create_remote(remote_name, remote_url)
                except Exception as e:
                    print(f"创建远程仓库失败: {str(e)}")
                    raise
            except Exception as e:
                print(f"处理远程仓库时出错: {str(e)}")
                raise
            
            # 设置代理环境变量
            env = {}
            if self.proxy_checkbox.isChecked():
                proxy_type = self.data_model.get_value('proxy', 'proxy_type', 'system')
                http_proxy = self.data_model.get_value('proxy', 'http_proxy')
                proxy_port = self.data_model.get_value('proxy', 'port')
                
                if proxy_type.lower() == 'socks5':
                    proxy_url = f"socks5://{http_proxy}:{proxy_port}"
                else:
                    proxy_url = f"http://{http_proxy}:{proxy_port}"
                
                env['http_proxy'] = proxy_url
                env['https_proxy'] = proxy_url
                print(f"使用代理: {proxy_url}")
            
            # 使用QProcess执行git fetch命令
            self.process = QProcess()
            self.process.setWorkingDirectory(self.get_comfyui_path())
            
            # 设置环境变量
            if env:
                process_env = QProcess.systemEnvironment()
                for key, value in env.items():
                    process_env.append(f"{key}={value}")
                self.process.setEnvironment(process_env)
            
            self.process.finished.connect(self.on_fetch_finished)
            self.process.errorOccurred.connect(self.on_process_error)
            
            # 显示正在获取信息的提示
            InfoBar.info(
                title="正在获取",
                content="正在获取远程版本信息，可以切换到其他面板继续操作",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            
            # 执行git fetch命令
            self.process.start("git", ["fetch", "--tags", remote_name])
            print("正在获取远程标签信息...")
        except Exception as e:
            print(f"刷新版本失败: {str(e)}")
            MessageBox("错误", f"刷新版本失败: {str(e)}", self).exec()
    
    def on_tab_changed(self, key):
        """选项卡切换事件"""
        print(f"选项卡切换到: {key}")
        self.on_tab_clicked(key)
    
    def on_tab_clicked(self, key):
        """选项卡点击事件处理"""
        tab = key
        
        if self.current_tab == tab:
            return
        
        self.current_tab = tab
        
        # 停止所有可能正在运行的定时器
        if self.load_timer.isActive():
            self.load_timer.stop()
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        if self.update_timer.isActive():
            self.update_timer.stop()
        
        # 如果窗口处于最小化状态，不启动加载
        if self.window().isMinimized():
            print("窗口最小化状态，不加载版本列表")
            return
            
        # 设置刷新标志，用于在hideEvent中判断是否正在刷新
        self.is_refreshing = True
            
        # 清空当前列表并显示加载提示
        self.version_list.clear()
        
        # 创建加载提示项，样式与节点面板一致
        loading_item = QListWidgetItem()
        loading_widget = QWidget()
        loading_layout = QHBoxLayout(loading_widget)
        loading_layout.setContentsMargins(10, 6, 10, 6)  # 与其他版本项保持一致的边距
        loading_layout.setSpacing(0)  # 减少内部间距
        loading_layout.setAlignment(Qt.AlignCenter)
        
        loading_label = BodyLabel("正在加载版本列表...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_layout.addWidget(loading_label)
        
        # 设置与其他版本项一致的高度
        size_hint = loading_widget.sizeHint()
        size_hint.setHeight(55)  # 与其他版本项保持一致的高度
        loading_item.setSizeHint(size_hint)
        self.version_list.addItem(loading_item)
        self.version_list.setItemWidget(loading_item, loading_widget)
        
        # 使用类成员定时器延迟更新版本列表，延迟0.35秒确保选项卡切换动画完全结束
        self.update_timer.start(350)
    
    def update_tab_button_states(self):
        """根据当前显示的版本类型更新选项卡状态"""
        self.version_tabs.setCurrentItem(self.current_tab)
    
    def update_version_list(self):
        """根据当前选项卡更新版本列表（优化版本）"""
        if not self.versions:
            # 重置刷新标志
            self.is_refreshing = False
            return
            
        self.version_list.clear()
        
        # 获取当前HEAD的commit id（只获取一次）
        current_commit_short = None
        try:
            if self.repo is not None:
                current_commit = self.repo.head.commit.hexsha
                current_commit_short = current_commit[:8]
        except Exception as e:
            print(f"获取当前HEAD提交ID失败: {str(e)}")
        
        # 根据当前选项卡筛选版本
        filtered_versions = []
        if self.current_tab == "stable":
            # 稳定版只显示标签版本
            filtered_versions = [v for v in self.versions if str(v.get("type", "")).lower() == "tag"]
        else:
            # 开发版显示master分支下的内容
            filtered_versions = [v for v in self.versions if 
                               str(v.get("type", "")).lower() == "branch" and 
                               (v.get("name") == "master" or 
                                "master" in str(v.get("ref", "")).lower() or 
                                v.get("branch") == "master" or 
                                v.get("name") == "--")]
        
        # 如果版本数量很多，使用分批加载
        if len(filtered_versions) > 50:
            self._load_versions_in_batches(filtered_versions, current_commit_short)
        else:
            self._load_versions_immediately(filtered_versions, current_commit_short)
        
        # 更新选项卡按钮状态以反映当前显示的内容
        self.update_tab_button_states()
        
        # 重置刷新状态标志
        self.is_refreshing = False
    
    def _load_versions_immediately(self, filtered_versions, current_commit_short):
        """立即加载版本列表（用于少量版本）"""
        # 暂时禁用重绘以提高性能
        self.version_list.setUpdatesEnabled(False)
        
        try:
            for i, version in enumerate(filtered_versions):
                self._create_version_item(version, current_commit_short)
        finally:
            # 重新启用重绘
            self.version_list.setUpdatesEnabled(True)
            self.version_list.repaint()
    
    def _load_versions_in_batches(self, filtered_versions, current_commit_short):
        """分批加载版本列表（用于大量版本）"""
        self.batch_size = 20  # 每批加载20个
        self.current_batch = 0
        self.filtered_versions = filtered_versions
        self.current_commit_short = current_commit_short
        
        # 创建批量加载定时器
        if not hasattr(self, 'batch_timer'):
            self.batch_timer = QTimer(self)
            self.batch_timer.setSingleShot(True)
            self.batch_timer.timeout.connect(self._load_next_batch)
        
        # 开始加载第一批
        self._load_next_batch()
    
    def _load_next_batch(self):
        """加载下一批版本"""
        if not hasattr(self, 'filtered_versions') or not self.filtered_versions:
            return
            
        start_idx = self.current_batch * self.batch_size
        end_idx = min(start_idx + self.batch_size, len(self.filtered_versions))
        
        if start_idx >= len(self.filtered_versions):
            return
        
        # 暂时禁用重绘以提高性能
        self.version_list.setUpdatesEnabled(False)
        
        try:
            # 加载当前批次的版本
            for i in range(start_idx, end_idx):
                version = self.filtered_versions[i]
                self._create_version_item(version, self.current_commit_short)
        finally:
            # 重新启用重绘
            self.version_list.setUpdatesEnabled(True)
            self.version_list.repaint()
        
        # 准备下一批
        self.current_batch += 1
        
        # 如果还有更多版本需要加载，继续
        if end_idx < len(self.filtered_versions):
            # 使用较短的延迟继续加载下一批
            self.batch_timer.start(50)  # 50ms延迟
    
    def _create_version_item(self, version, current_commit_short):
        """创建单个版本项（优化版本）"""
        try:
            item = QListWidgetItem()
            
            # 创建一个小部件来包含版本信息，以表格样式显示
            version_widget = QWidget()
            layout = QHBoxLayout(version_widget)
            layout.setContentsMargins(10, 6, 10, 6)
            layout.setSpacing(10)
            
            # 设置图标
            icon_label = QLabel()
            icon_label.setPixmap(FluentIcon.TAG.icon().pixmap(QSize(16, 16)))
            layout.addWidget(icon_label)
            
            # 根据选项卡类型创建不同的布局
            if self.current_tab == "dev":
                self._create_dev_version_layout(layout, version)
            else:
                self._create_stable_version_layout(layout, version)
            
            # 当前版本标记
            if current_commit_short and version['id'] == current_commit_short:
                current_label = BodyLabel("[当前]")
                current_label.setStyleSheet("color: #00a7b3; font-weight: bold;")
                layout.addWidget(current_label)
            
            # 添加弹性空间
            layout.addStretch()
            
            # 设置项目的大小提示
            size_hint = version_widget.sizeHint()
            size_hint.setHeight(55)
            item.setSizeHint(size_hint)
            
            # 存储版本数据
            item.setData(Qt.UserRole, version)
            
            # 添加到列表
            self.version_list.addItem(item)
            self.version_list.setItemWidget(item, version_widget)
            
        except Exception as e:
            print(f"创建版本项失败: {str(e)}")
    
    def _create_dev_version_layout(self, layout, version):
        """创建开发版版本布局"""
        # Commit ID标签
        commit_label = BodyLabel(f"Commit: {version['id']}")
        commit_label.setFixedWidth(150)
        commit_label.setStyleSheet("color: #00a7b3; font-weight: bold;")
        commit_label.setCursor(Qt.PointingHandCursor)
        
        # 简化点击事件处理
        commit_label.mousePressEvent = lambda event: self._open_commit_url(version['id'])
        layout.addWidget(commit_label)
        
        # 日期标签
        date_label = BodyLabel(version['date'])
        date_label.setFixedWidth(180)
        layout.addWidget(date_label)
        
        # 消息标签
        message_text = version.get('message', version.get('name', '--'))
        message_label = BodyLabel(message_text)
        message_label.setFixedWidth(300)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
    
    def _create_stable_version_layout(self, layout, version):
        """创建稳定版版本布局"""
        # Commit ID标签
        commit_label = BodyLabel(f"Commit: {version['id']}")
        commit_label.setFixedWidth(150)
        commit_label.setStyleSheet("color: #00a7b3; font-weight: bold;")
        commit_label.setCursor(Qt.PointingHandCursor)
        
        # 简化点击事件处理
        commit_label.mousePressEvent = lambda event: self._open_commit_url(version['id'])
        layout.addWidget(commit_label)
        
        # 日期标签
        date_label = BodyLabel(version['date'])
        date_label.setFixedWidth(180)
        layout.addWidget(date_label)
        
        # 版本名称标签
        name_text = version['name']
        if name_text == "--" and "message" in version:
            name_text = f"-- ({version['message']})"
        
        name_label = BodyLabel(name_text)
        name_label.setFixedWidth(250)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
    
    def _open_commit_url(self, commit_id):
        """打开commit URL（优化版本）"""
        try:
            if not self.repo:
                return
                
            remote_url = self.repo.remote().url
            
            # 处理可能的SSH URL格式
            if remote_url.startswith('git@'):
                remote_url = remote_url.replace(':', '/')
                remote_url = remote_url.replace('git@', 'https://')
            
            # 移除.git后缀
            if remote_url.endswith('.git'):
                remote_url = remote_url[:-4]
                
            # 构建commit URL
            commit_url = f"{remote_url}/commit/{commit_id}"
            webbrowser.open(commit_url)
        except Exception as e:
            print(f"打开commit URL失败: {str(e)}")
    
    def _force_refresh_commit_styles(self):
        """强制刷新所有commit标签的样式"""
        try:
            for i in range(self.version_list.count()):
                item = self.version_list.item(i)
                widget = self.version_list.itemWidget(item)
                if widget:
                    # 查找widget中的所有子控件
                    for child in widget.findChildren(BodyLabel):
                        # 如果是commit_label（文本以"Commit:"开头）
                        if child.text().startswith("Commit:"):
                            # 重新设置样式
                            child.setStyleSheet("color: #00a7b3; font-weight: bold;")
                            # 强制应用样式
                            child.style().unpolish(child)
                            child.style().polish(child)
                            child.update()
        except Exception as e:
            print(f"强制刷新commit样式失败: {str(e)}")
    
    def save_versions_to_file(self):
        """保存版本信息到文件"""
        try:
            if not self.versions:
                return False
                
            # 创建配置解析器
            config = configparser.ConfigParser()
            
            # 添加基本信息部分
            config.add_section('info')
            config.set('info', 'update_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            config.set('info', 'version_count', str(len(self.versions)))
            config.set('info', 'source_url', self.source_combo.currentData() or "")
            
            # 添加版本信息
            for i, version in enumerate(self.versions):
                section = f'version_{i}'
                config.add_section(section)
                
                # 保存版本的所有属性
                for key, value in version.items():
                    # 确保所有值都转换为字符串
                    config.set(section, key, str(value))
            
            # 保存到文件
            with open(self.versions_file, 'w', encoding='utf-8') as f:
                config.write(f)
                
            return True
        except Exception as e:
            print(f"保存版本信息失败: {str(e)}")
            return False
    
    def load_versions_from_file(self):
        """从文件加载版本信息"""
        try:
            if not os.path.exists(self.versions_file):
                return False
                
            # 创建配置解析器
            config = configparser.ConfigParser()
            config.read(self.versions_file, encoding='utf-8')
            
            # 检查基本信息
            if not config.has_section('info'):
                print("版本信息文件格式错误: 缺少info部分")
                return False
                
            # 获取版本数量
            try:
                version_count = config.getint('info', 'version_count')
                update_time = config.get('info', 'update_time')
                source_url = config.get('info', 'source_url', fallback="")
                
                # 如果源URL与当前不同，提示用户
                current_source_url = self.source_combo.currentData()
                if source_url and current_source_url and source_url != current_source_url:
                    print(f"警告: 保存的源URL({source_url})与当前源URL({current_source_url})不同")
            except Exception as e:
                print(f"读取版本信息基本数据失败: {str(e)}")
                return False
                
            # 加载所有版本信息
            versions = []
            for i in range(version_count):
                section = f'version_{i}'
                if not config.has_section(section):
                    print(f"警告: 缺少版本信息部分 {section}")
                    continue
                    
                # 创建版本信息字典
                version = {}
                for key, value in config.items(section):
                    # 确保类型字段的值是小写的，以便于比较
                    if key == 'type':
                        version[key] = value.lower()
                    else:
                        version[key] = value
                    
                versions.append(version)
                
            # 更新版本列表
            self.versions = versions
            
            # 更新UI显示
            self.update_version_list()
            
            # 强制刷新UI样式
            # 使用QTimer延迟刷新，确保样式正确应用
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._force_refresh_commit_styles)
            self.repaint()
            return True
        except Exception as e:
            print(f"加载版本信息失败: {str(e)}")
            return False
    

    
    def on_fetch_finished(self, exit_code, exit_status):
        """git fetch命令完成回调"""
        # 检查面板是否仍然可见，如果不可见则不更新UI
        if not self.isVisible():
            print("面板已隐藏，不更新版本列表")
            return
            
        if exit_code != 0:
            error_output = self.process.readAllStandardError().data().decode('utf-8', errors='ignore')
            print(f"获取远程信息失败: {error_output}")
            # 处理错误并返回
            InfoBar.error(
                title="获取失败",
                content="获取远程版本信息失败",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        try:
            # 获取当前HEAD的commit id
            try:
                current_commit = self.repo.head.commit.hexsha
            except Exception as e:
                print(f"获取当前HEAD提交ID失败: {str(e)}")
                current_commit = None
            
            # 获取所有标签和主分支
            versions = []
            
            # 添加所有分支
            try:
                # 获取远程分支
                remote = self.repo.remote("origin")
                
                # 列出所有远程引用
                for ref in remote.refs:
                    # 只处理分支引用，排除标签引用
                    if ref.name.startswith("origin/") and not ref.name.startswith("origin/tags/"):
                        branch_name = ref.name.replace("origin/", "")
                        commit = ref.commit
                        commit_id = commit.hexsha
                        commit_time = datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')
                        commit_message = commit.message.strip().split('\n')[0]  # 获取提交消息的第一行
                        versions.append({
                            "id": commit_id[:8],
                            "name": commit_message,  # 使用提交消息作为name
                            "date": commit_time,
                            "ref": ref.name,
                            "type": "branch",  # 确保类型是小写字符串
                            "message": commit_message,  # 保存提交消息
                            "branch": branch_name  # 保存分支名称
                        })
                
                # 获取最近的提交记录（没有标签的提交）
                # 获取master分支的提交
                try:
                    # 确保origin/master引用存在
                    if 'origin/master' in self.repo.refs:
                        commits = list(self.repo.iter_commits('origin/master', max_count=100))  # 增加获取最近100个提交
                    else:
                        # 查找所有包含master的引用
                        master_refs = [ref for ref in self.repo.refs if 'master' in ref.name.lower()]
                        if master_refs:
                            master_ref = master_refs[0]  # 使用第一个找到的master引用
                            commits = list(self.repo.iter_commits(master_ref.name, max_count=100))  # 增加获取最近100个提交
                        else:
                            print("错误: 找不到任何master相关引用")
                            commits = []
                except Exception as e:
                    print(f"获取master分支提交时出错: {str(e)}")
                    commits = []
                # 获取master分支信息
                try:
                    # 尝试获取master分支引用
                    master_ref = None
                    if 'origin/master' in self.repo.refs:
                        master_ref = self.repo.refs["origin/master"]
                    else:
                        # 查找所有包含master的引用
                        master_refs = [ref for ref in self.repo.refs if 'master' in ref.name.lower()]
                        if master_refs:
                            master_ref = master_refs[0]  # 使用第一个找到的master引用
                except Exception as e:
                    print(f"获取master分支信息失败: {str(e)}")
                
                # 过滤掉已经作为分支或标签添加的提交
                added_commit_ids = [v["id"] for v in versions]
                for commit in commits:
                    commit_id = commit.hexsha[:8]
                    # 如果这个提交ID已经添加过，跳过
                    if commit_id in added_commit_ids:
                        continue
                    
                    commit_time = datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')
                    commit_message = commit.message.strip().split('\n')[0]  # 获取提交消息的第一行
                    
                    # 确定引用名称
                    ref_name = "origin/master"  # 默认引用名
                    # 如果之前找到了master引用，使用它的名称
                    if 'master_ref' in locals() and master_ref:
                        ref_name = master_ref.name
                    
                    versions.append({
                        "id": commit_id,
                        "name": commit_message,  # 使用提交消息作为name
                        "date": commit_time,
                        "ref": ref_name,  # 使用实际的引用名称
                        "type": "branch".lower(),  # 将其归类为分支类型，以便在开发版选项卡中显示，确保类型是小写字符串
                        "message": commit_message,  # 保存提交消息
                        "branch": "master"  # 明确标记为master分支的提交
                    })
                    added_commit_ids.append(commit_id)  # 添加到已处理列表
            except Exception as e:
                print(f"获取分支和提交信息失败: {str(e)}")
            
            # 获取所有标签
            try:
                for tag in self.repo.tags:
                    if tag.name.startswith("v"):
                        try:
                            tag_name = tag.name
                            commit = tag.commit
                            commit_id = commit.hexsha
                            commit_time = datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')
                            
                            versions.append({
                                "id": commit_id[:8],
                                "name": tag_name,
                                "date": commit_time,
                                "ref": tag.name,
                                "type": "tag".lower()  # 确保类型是小写字符串
                            })
                        except Exception as e:
                            print(f"解析标签 {tag.name} 失败: {str(e)}")
            except Exception as e:
                print(f"获取标签列表失败: {str(e)}")
            
            # 按日期排序（最新的在前面）
            try:
                versions.sort(key=lambda x: x["date"], reverse=True)
                self.versions = versions
                
                # 保存版本信息到文件
                self.save_versions_to_file()
            except Exception as e:
                print(f"版本排序失败: {str(e)}")
            
            # 更新UI
            try:
                # 根据当前选项卡更新版本列表
                self.update_version_list()
            except Exception as e:
                print(f"更新UI显示失败: {str(e)}")
            
            # 版本获取完成
            # 重置刷新标志
            self.is_refreshing = False
        except Exception as e:
            print(f"解析版本信息失败: {str(e)}")
            # 重置刷新标志
            self.is_refreshing = False
        finally:
            # 处理异常
            pass
    
    def on_process_error(self, error):
        """进程错误处理"""
        print(f"进程错误: {error}")
        print(f"错误代码: {int(error)}")
        
        # 解释常见错误代码
        error_messages = {
            QProcess.FailedToStart: "进程启动失败 - 可能是git命令不存在或无法执行",
            QProcess.Crashed: "进程崩溃",
            QProcess.Timedout: "进程超时",
            QProcess.WriteError: "写入进程时出错",
            QProcess.ReadError: "从进程读取时出错",
            QProcess.UnknownError: "未知错误"
        }
        
        error_description = error_messages.get(error, "未知错误类型")
        print(f"错误说明: {error_description}")
        
        # 针对特定错误提供建议
        if error == QProcess.FailedToStart:
            print("请检查git是否已安装并添加到系统PATH环境变量中")
            print("您可以在命令行中运行'git --version'来验证git是否可用")
        
        
            # 处理进程错误
    
    def switch_version(self):
        """切换到选中的版本"""
        selected_items = self.version_list.selectedItems()
        if not selected_items:
            MessageBox("提示", "请先选择一个版本", self).exec()
            return
        
        selected_version = selected_items[0].data(Qt.UserRole)
        if selected_version is None:
            MessageBox("错误", "无法获取版本信息", self).exec()
            return
        
        # 确认对话框
        msg_box = MessageBox(
            "确认切换版本", 
            f"确定要切换到 {selected_version['name']} 版本吗？\n\n" +
            "注意: 切换版本会丢失所有未提交的更改。",
            self
        )
        if not msg_box.exec():
            return
        
        # 开始执行版本切换
        
        try:
            # 使用QProcess执行git命令
            self.process = QProcess()
            self.process.setWorkingDirectory(self.get_comfyui_path())
            
            # 设置代理环境变量
            if self.proxy_checkbox.isChecked():
                env = QProcess.systemEnvironment()
                proxy_type = self.data_model.get_value('proxy', 'proxy_type', 'system')
                http_proxy = self.data_model.get_value('proxy', 'http_proxy')
                proxy_port = self.data_model.get_value('proxy', 'port')
                
                if proxy_type.lower() == 'socks5':
                    proxy_url = f"socks5://{http_proxy}:{proxy_port}"
                else:
                    proxy_url = f"http://{http_proxy}:{proxy_port}"
                
                env.append(f"http_proxy={proxy_url}")
                env.append(f"https_proxy={proxy_url}")
                self.process.setEnvironment(env)
            
            self.process.finished.connect(self.on_checkout_finished)
            self.process.errorOccurred.connect(self.on_process_error)
            
            # 执行git checkout命令
            # 根据版本类型决定使用什么进行checkout
            if selected_version['type'] == 'branch':
                # 对于分支类型（开发版），直接使用commit ID
                commit_id = selected_version['id']
                self.process.start("git", ["checkout", commit_id])
            else:
                # 对于标签类型（稳定版），使用标签名
                ref_name = selected_version['ref']
                self.process.start("git", ["checkout", ref_name])
        except Exception as e:
            # 移除了关闭进度对话框的代码
            print(f"切换版本失败: {str(e)}")
            MessageBox("错误", f"切换版本失败: {str(e)}", self).exec()
    
    def on_checkout_finished(self, exit_code, exit_status):
        """git checkout命令完成回调"""
        if exit_code != 0:
            error_output = self.process.readAllStandardError().data().decode('utf-8', errors='ignore')
            print(f"切换版本失败: {error_output}")
            MessageBox("错误", f"切换版本失败: {error_output}", self).exec()
            return
        
        # 更新仓库状态显示
        self.check_repo_status()
        
        # 记录切换后的版本信息，但保持用户选择的选项卡
        try:
            current_commit = self.repo.head.commit.hexsha
            current_commit_short = current_commit[:8]
            
            # 手动更新版本列表以显示当前版本
            self.update_version_list()
        except Exception as e:
            print(f"更新版本信息失败: {str(e)}")
        
        # 显示成功消息
        InfoBar.success(
            title="成功",
            content="版本切换成功",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        