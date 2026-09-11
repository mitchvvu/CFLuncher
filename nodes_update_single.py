import os
import sys
import time
import configparser
import git
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, 
                             QLabel, QPushButton, QDialog, QApplication, QProgressBar)
from PySide6.QtCore import Qt, Signal, QProcess, QSize, QTimer
from PySide6.QtGui import QFont, QIcon, QWheelEvent

from qfluentwidgets import (
    CardWidget, StrongBodyLabel, BodyLabel, TextBrowser, PushButton, PrimaryPushButton, InfoBar, InfoBarPosition,
    setTheme, Theme, FluentIcon, MessageBox, CheckBox, ComboBox, SegmentedWidget
)

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

class NodeUpdateDialog(QDialog):
    """节点更新对话框"""
    def __init__(self, node_name, node_path, proxy_enabled=False, proxy_url="", mirror_index=0, parent=None, git_info=None):
        super().__init__(parent)
        self.node_name = node_name
        self.node_path = node_path
        self.proxy_enabled = proxy_enabled
        self.proxy_url = proxy_url
        self.mirror_index = mirror_index
        self.process = None
        self.repo = None
        self.versions = []
        self.git_info = git_info  # 保存Git信息
        self.settings_file = os.path.join('starter', 'nodes.ini')
        
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
        
        # 自动刷新版本列表
        self.refresh_versions_delayed()
    
    def init_ui(self):
        self.setWindowTitle(f"节点版本管理 - {self.node_name}")
        self.resize(600, 700)  # 设置对话框大小
        self.setFixedSize(self.size()) # 固定对话框大小
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建节点信息卡片
        info_card = CardWidget()
        info_layout = QVBoxLayout()
        info_layout.addWidget(StrongBodyLabel(f"节点: {self.node_name}"))
        
        # 顶部控制区域
        top_control_layout = QHBoxLayout()
        
        # 代理设置
        self.proxy_checkbox = CheckBox("启用代理")
        self.proxy_checkbox.setToolTip("启用代理后将使用设置面板中的代理配置")
        top_control_layout.addWidget(self.proxy_checkbox)
        
        # 添加一个占位符，使布局更平衡
        top_control_layout.addStretch()
        
        # 刷新按钮
        self.refresh_button = PushButton("刷新")
        self.refresh_button.setIcon(FluentIcon.SYNC)
        self.refresh_button.clicked.connect(self.refresh_versions_delayed)
        top_control_layout.addWidget(self.refresh_button)
        
        info_layout.addLayout(top_control_layout)
        
        # 仓库信息显示
        repo_info_layout = QHBoxLayout()
        repo_info_layout.addWidget(BodyLabel("仓库路径:"))
        self.repo_path_label = BodyLabel(self.node_path)
        repo_info_layout.addWidget(self.repo_path_label)
        repo_info_layout.addStretch()
        info_layout.addLayout(repo_info_layout)
        
        # 仓库状态
        status_layout = QHBoxLayout()
        status_layout.addWidget(BodyLabel("仓库状态:"))
        self.status_label = BodyLabel("未检测")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        info_layout.addLayout(status_layout)
        
        info_card.setLayout(info_layout)
        layout.addWidget(info_card)
        
        # 创建版本列表卡片
        version_list_card = CardWidget()
        version_list_layout = QVBoxLayout()
        
        # 版本列表标题
        version_title_layout = QHBoxLayout()
        version_title_layout.addWidget(StrongBodyLabel("所有版本"))
        
        # 添加只看主分支复选框
        self.main_branch_only_checkbox = CheckBox("只看主分支")
        self.main_branch_only_checkbox.setChecked(True)  # 默认勾选
        self.main_branch_only_checkbox.clicked.connect(self.update_version_list)  # 点击时更新版本列表
        version_title_layout.addStretch()
        version_title_layout.addWidget(self.main_branch_only_checkbox)
        
        version_list_layout.addLayout(version_title_layout)
        
        # 版本列表
        self.version_list = SingleRowScrollListWidget()
        self.version_list.setMinimumHeight(400)
        
        # 添加虚拟化支持
        self.version_list.setUniformItemSizes(True)
        
        # 优化滚动性能
        self.version_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        
        # 设置列表样式
        self.version_list.setStyleSheet("""
            QListWidget {
                background-color: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding-top: 0px;
            }
            QListWidget::item {
                padding: 5px 5px;
                border-bottom: 1px solid #e0e0e0;
                margin-top: 0px;
                margin-bottom: 0px;
            }
            QListWidget::item:selected {
                background-color: #f0f8f8;
                color: #000000;
                border-left: 3px solid #00a7b3;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        version_list_layout.addWidget(self.version_list)
        
        # 不再需要选项卡
        
        # 添加切换版本按钮
        self.execute_button = PrimaryPushButton("切换版本")
        self.execute_button.clicked.connect(self.switch_version)
        self.execute_button.setMinimumHeight(40)
        version_list_layout.addWidget(self.execute_button)
        
        version_list_card.setLayout(version_list_layout)
        layout.addWidget(version_list_card)
        
        self.setLayout(layout)
        
        # 加载节点设置
        self.load_node_settings()
    
    def load_node_settings(self):
        """加载节点设置"""
        try:
            # 从nodes.ini文件中读取代理设置
            config = configparser.ConfigParser()
            if os.path.exists(self.settings_file):
                config.read(self.settings_file, encoding='utf-8')
                
                # 读取git部分的代理设置
                if config.has_section('git'):
                    self.proxy_enabled = config.getboolean('git', 'proxy_enabled', fallback=False)
                
            # 设置代理复选框状态
            self.proxy_checkbox.setChecked(self.proxy_enabled)
            
            # 连接代理复选框状态变化信号
            self.proxy_checkbox.clicked.connect(self.save_proxy_settings)
            
            print("节点设置加载成功")
        except Exception as e:
            print(f"加载节点设置失败: {str(e)}")
    
    def check_repo_status(self):
        """检查仓库状态"""
        try:
            if not os.path.exists(self.node_path):
                self.status_label.setText("节点路径不存在")
                print(f"错误: 路径不存在 - {self.node_path}")
                return False
            
            # 检查是否为git仓库
            git_dir = os.path.join(self.node_path, '.git')
            if not os.path.exists(git_dir):
                self.status_label.setText("不是Git仓库")
                print(f"错误: 不是Git仓库 (没有.git目录)")
                return False
                
            # 使用GitPython打开仓库
            self.repo = git.Repo(self.node_path)
            
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
            self.status_label.setText(f"检查失败: {str(e)}")
            print(f"检查仓库状态失败: {str(e)}")
            return False
    
    def load_versions_delayed(self):
        """延时加载版本列表"""
        # 停止所有可能正在运行的定时器
        if self.load_timer.isActive():
            self.load_timer.stop()
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        if self.update_timer.isActive():
            self.update_timer.stop()
        
        # 设置刷新标志
        self.is_refreshing = True
            
        # 清除现有版本列表
        self.version_list.clear()
        
        # 创建加载提示项
        loading_item = QListWidgetItem()
        loading_widget = QWidget()
        loading_layout = QHBoxLayout(loading_widget)
        loading_layout.setContentsMargins(10, 6, 10, 6)
        loading_layout.setSpacing(0)
        loading_layout.setAlignment(Qt.AlignCenter)
        
        loading_label = BodyLabel("正在加载版本列表...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_layout.addWidget(loading_label)
        
        # 设置高度
        size_hint = loading_widget.sizeHint()
        size_hint.setHeight(55)
        loading_item.setSizeHint(size_hint)
        self.version_list.addItem(loading_item)
        self.version_list.setItemWidget(loading_item, loading_widget)
        
        # 使用定时器延迟加载版本列表
        self.load_timer.start(350)
    
    def load_initial_versions(self):
        """加载初始版本列表"""
        # 更新版本列表显示
        self.update_version_list()
        
        # 重置刷新标志
        self.is_refreshing = False
    
    def refresh_versions_delayed(self):
        """延时刷新版本列表"""
        # 保存当前代理设置
        self.save_proxy_settings()
        
        # 停止所有可能正在运行的定时器
        if self.load_timer.isActive():
            self.load_timer.stop()
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        if self.update_timer.isActive():
            self.update_timer.stop()
        
        # 设置刷新标志
        self.is_refreshing = True
            
        # 清除现有版本列表
        self.version_list.clear()
        
        # 创建加载提示项
        loading_item = QListWidgetItem()
        loading_widget = QWidget()
        loading_layout = QHBoxLayout(loading_widget)
        loading_layout.setContentsMargins(10, 6, 10, 6)
        loading_layout.setSpacing(0)
        loading_layout.setAlignment(Qt.AlignCenter)
        
        loading_label = BodyLabel("正在刷新版本列表...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_layout.addWidget(loading_label)
        
        # 设置高度
        size_hint = loading_widget.sizeHint()
        size_hint.setHeight(55)
        loading_item.setSizeHint(size_hint)
        self.version_list.addItem(loading_item)
        self.version_list.setItemWidget(loading_item, loading_widget)
        
        # 使用定时器延迟刷新版本列表
        self.refresh_timer.start(350)
    
    # 移除选项卡切换相关方法
    
    # 移除选项卡相关方法
    
    def refresh_versions(self):
        """刷新版本列表"""
        # 保存当前代理设置
        self.save_proxy_settings()
        
        # 设置刷新标志
        self.is_refreshing = True
        
        self.version_list.clear()
        self.versions = []
        
        # 如果有git_info信息，可以先显示一些基本信息
        if self.git_info:
            try:
                # 更新UI显示一些基本信息
                if 'branch' in self.git_info:
                    branch_name = self.git_info['branch']
                    InfoBar.info(
                        title="当前分支",
                        content=f"当前分支: {branch_name}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                
                # 显示是否有更新
                if 'has_update' in self.git_info and self.git_info['has_update']:
                    InfoBar.warning(
                        title="有更新",
                        content=f"当前版本: {self.git_info.get('current_version', '未知')}，最新版本: {self.git_info.get('latest_version', '未知')}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=5000,
                        parent=self
                    )
            except Exception as e:
                print(f"显示Git信息失败: {str(e)}")
        
        # 检查仓库状态
        if not self.check_repo_status():
            print("无法获取版本信息: 仓库状态检查失败")
            return
        
        try:
            # 记录当前版本信息
            current_commit = self.repo.head.commit.hexsha
            
            # 检查当前版本是分支还是标签
            is_branch = False
            for branch in self.repo.branches:
                if branch.commit.hexsha == current_commit:
                    is_branch = True
                    break
            
            # 仅记录当前版本类型
            version_type = "开发版(分支)" if is_branch else "稳定版(标签)"
        except Exception as e:
            print(f"检查当前版本类型失败: {str(e)}")
        
        try:
            # 设置代理环境变量
            env = {}
            if self.proxy_checkbox.isChecked():
                # 获取系统代理设置
                http_proxy = os.environ.get('http_proxy', '')
                https_proxy = os.environ.get('https_proxy', '')
                
                if http_proxy:
                    env['http_proxy'] = http_proxy
                if https_proxy:
                    env['https_proxy'] = https_proxy
                print(f"刷新版本使用系统代理: http_proxy={http_proxy}, https_proxy={https_proxy}")
            
            # 移除镜像源相关代码
            
            # 使用QProcess执行git fetch命令
            self.process = QProcess()
            self.process.setWorkingDirectory(self.node_path)
            
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
                content="正在获取远程版本信息",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            
            # 执行git fetch命令
            self.process.start("git", ["fetch", "--tags", "origin"])
            print("正在获取远程标签信息...")
        except Exception as e:
            print(f"刷新版本失败: {str(e)}")
            MessageBox("错误", f"刷新版本失败: {str(e)}", self).exec()
    
    def on_fetch_finished(self, exit_code, exit_status):
        """git fetch命令完成回调"""
        if exit_code != 0:
            error_output = self.process.readAllStandardError().data().decode('utf-8', errors='ignore')
            print(f"获取远程信息失败: {error_output}")
            MessageBox("错误", f"获取远程信息失败: {error_output}", self).exec()
            return
        
        print("获取远程信息成功，正在解析版本列表...")
        
        try:
            # 获取所有标签和分支
            self.versions = []
            
            # 获取当前HEAD的commit id
            current_commit = self.repo.head.commit.hexsha
            
            # 添加标签版本
            for tag in self.repo.tags:
                tag_date = time.strftime("%Y-%m-%d", time.gmtime(tag.commit.committed_date))
                tag_time = time.strftime("%H:%M:%S", time.gmtime(tag.commit.committed_date))
                is_current = tag.commit.hexsha == current_commit
                
                self.versions.append({
                    "type": "tag",
                    "name": tag.name,
                    "date": tag_date,
                    "time": tag_time,
                    "commit": tag.commit.hexsha,
                    "commit_short": tag.commit.hexsha[:8],
                    "is_current": is_current,
                    "message": tag.commit.message.strip()
                })
            
            # 添加分支版本
            for branch in self.repo.branches:
                branch_date = time.strftime("%Y-%m-%d", time.gmtime(branch.commit.committed_date))
                branch_time = time.strftime("%H:%M:%S", time.gmtime(branch.commit.committed_date))
                is_current = branch.commit.hexsha == current_commit
                
                self.versions.append({
                    "type": "branch",
                    "name": branch.name,
                    "date": branch_date,
                    "time": branch_time,
                    "commit": branch.commit.hexsha,
                    "commit_short": branch.commit.hexsha[:8],
                    "is_current": is_current,
                    "message": branch.commit.message.strip()
                })
            
            # 添加远程分支版本
            for ref in self.repo.remotes.origin.refs:
                # 跳过HEAD引用
                if ref.name == 'origin/HEAD':
                    continue
                    
                # 解析分支名
                branch_name = ref.name.replace('origin/', '')
                
                # 跳过已经添加的本地分支
                if branch_name in [b.name for b in self.repo.branches]:
                    continue
                    
                branch_date = time.strftime("%Y-%m-%d", time.gmtime(ref.commit.committed_date))
                branch_time = time.strftime("%H:%M:%S", time.gmtime(ref.commit.committed_date))
                is_current = ref.commit.hexsha == current_commit
                
                self.versions.append({
                    "type": "branch",
                    "name": branch_name,
                    "date": branch_date,
                    "time": branch_time,
                    "commit": ref.commit.hexsha,
                    "commit_short": ref.commit.hexsha[:8],
                    "is_current": is_current,
                    "message": ref.commit.message.strip(),
                    "ref": ref.name
                })
            
            # 按时间戳排序版本列表
            self.versions.sort(key=lambda x: (x["date"], x["time"]), reverse=True)
            
            # 更新版本列表显示
            self.update_version_list()
            
            # 显示成功提示
            InfoBar.success(
                title="获取成功",
                content=f"已获取 {len(self.versions)} 个版本信息",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except Exception as e:
            print(f"解析版本列表失败: {str(e)}")
            MessageBox("错误", f"解析版本列表失败: {str(e)}", self).exec()
        
        # 重置刷新标志
        self.is_refreshing = False
    
    def on_process_error(self, error):
        """进程错误回调"""
        print(f"进程错误: {error}")
        MessageBox("错误", f"执行Git命令时出错: {error}", self).exec()
        
        # 重置刷新标志
        self.is_refreshing = False
    
    def update_version_list(self):
        """更新版本列表，根据设置显示所有版本或只显示主分支版本"""
        if not self.versions:
            # 重置刷新标志
            self.is_refreshing = False
            return
            
        self.version_list.clear()
        
        # 获取当前HEAD的commit id
        current_commit_short = None
        try:
            if self.repo is not None:
                current_commit = self.repo.head.commit.hexsha
                current_commit_short = current_commit[:8]
        except Exception as e:
            print(f"获取当前HEAD提交ID失败: {str(e)}")
        
        # 根据复选框状态决定是否只显示主分支版本
        main_branch_only = self.main_branch_only_checkbox.isChecked()
        main_branches = ["main", "master"]
        
        # 筛选版本
        filtered_versions = []
        for version in self.versions:
            # 如果只看主分支且版本不是主分支，则跳过
            if main_branch_only and version["type"] == "branch" and version["name"] not in main_branches:
                continue
            filtered_versions.append(version)
        
        # 添加版本项
        for version in filtered_versions:
            item = QListWidgetItem()
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(10, 0, 10, 0)
            
            # 版本名称和时间戳
            version_info = QVBoxLayout()
            
            # 版本名称
            name_label = BodyLabel(version["name"])
            font = name_label.font()
            font.setBold(True)
            name_label.setFont(font)
            
            # 如果是当前版本，添加标记
            if version.get("is_current", False) or version.get("commit_short") == current_commit_short:
                name_label.setText(f"{version['name']} (当前版本)")
                name_label.setStyleSheet("color: #00a7b3;")
            
            version_info.addWidget(name_label)
            
            # 提交信息
            message = version.get("message", "").split('\n')[0]  # 只取第一行
            if len(message) > 50:
                message = message[:50] + "..."
            message_label = BodyLabel(message)
            message_label.setStyleSheet("color: #666666; font-size: 12px;")
            version_info.addWidget(message_label)
            
            layout.addLayout(version_info, 4)  # 分配更多空间给版本信息
            
            # 提交ID和时间戳
            commit_info = QVBoxLayout()
            
            # 版本ID
            commit_label = BodyLabel(f"版本ID: {version['commit_short']}")
            commit_label.setStyleSheet("color: #666666; font-size: 12px;")
            commit_info.addWidget(commit_label)
            
            # 日期和时间
            date_label = BodyLabel(f"时间戳: {version['date']} {version['time']}")
            date_label.setStyleSheet("color: #666666; font-size: 12px;")
            commit_info.addWidget(date_label)
            
            layout.addLayout(commit_info, 2)  # 分配较少空间给提交信息
            
            # 设置项目数据
            item.setData(Qt.UserRole, version)
            
            # 设置项目大小
            size_hint = widget.sizeHint()
            size_hint.setHeight(55)  # 固定高度
            item.setSizeHint(size_hint)
            
            self.version_list.addItem(item)
            self.version_list.setItemWidget(item, widget)
        
        # 如果没有版本，显示提示
        if not self.versions:
            item = QListWidgetItem()
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(10, 6, 10, 6)
            layout.setAlignment(Qt.AlignCenter)
            
            message = "没有找到任何版本"
                
            label = BodyLabel(message)
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
            
            size_hint = widget.sizeHint()
            size_hint.setHeight(55)
            item.setSizeHint(size_hint)
            
            self.version_list.addItem(item)
            self.version_list.setItemWidget(item, widget)
        

        # 重置刷新状态标志
        self.is_refreshing = False
    
    def switch_version(self):
        """切换版本"""
        # 获取选中的版本
        current_item = self.version_list.currentItem()
        if not current_item:
            MessageBox("提示", "请先选择一个版本", self).exec()
            return
        
        version_data = current_item.data(Qt.UserRole)
        if not version_data:
            MessageBox("错误", "无法获取版本信息", self).exec()
            return
        
        # 检查是否是当前版本
        if version_data.get("is_current", False):
            MessageBox("提示", "已经是当前版本，无需切换", self).exec()
            return
        
        # 确认切换
        confirm = MessageBox(
            "确认切换",
            f"确定要切换到 {version_data['name']} (版本ID: {version_data['commit_short']}) 吗？\n\n" +
            "切换版本可能会导致不兼容问题，请确保已备份重要数据。",
            self
        )
        if confirm.exec() != QDialog.Accepted:
            return
        
        try:
            # 保存当前代理设置
            self.save_proxy_settings()
            
            # 创建进度对话框
            progress_dialog = MessageBox(
                "正在切换版本",
                f"正在切换到 {version_data['name']} (版本ID: {version_data['commit_short']})，请稍候...",
                self
            )
            progress_dialog.setWindowFlag(Qt.WindowCloseButtonHint, False)  # 禁用关闭按钮
            
            # 添加进度显示标签
            content_layout = QVBoxLayout()
            progress_label = QLabel("正在切换版本...")
            progress_label.setAlignment(Qt.AlignCenter)
            progress_label.setStyleSheet("font-size: 14px; font-weight: bold;")
            content_layout.addWidget(progress_label)
            progress_dialog.contentLabel.setLayout(content_layout)
            
            # 设置代理环境变量
            env = {}
            if self.proxy_checkbox.isChecked():
                # 获取系统代理设置
                http_proxy = os.environ.get('http_proxy', '')
                https_proxy = os.environ.get('https_proxy', '')
                
                if http_proxy:
                    env['http_proxy'] = http_proxy
                if https_proxy:
                    env['https_proxy'] = https_proxy
                print(f"切换版本使用系统代理: http_proxy={http_proxy}, https_proxy={https_proxy}")
            
            # 使用QProcess执行git命令
            self.process = QProcess()
            self.process.setWorkingDirectory(self.node_path)
            
            # 设置环境变量
            if env:
                process_env = QProcess.systemEnvironment()
                for key, value in env.items():
                    process_env.append(f"{key}={value}")
                self.process.setEnvironment(process_env)
            
            # 连接信号
            self.process.finished.connect(lambda code, status: self.on_switch_finished(code, status, progress_dialog))
            self.process.errorOccurred.connect(lambda error: self.on_switch_error(error, progress_dialog))
            
            # 执行git命令
            if version_data.get("type") == "tag":
                # 切换到标签
                self.process.start("git", ["checkout", "tags/" + version_data["name"]])
            elif "ref" in version_data:
                # 切换到远程分支
                self.process.start("git", ["checkout", "-b", version_data["name"], version_data["ref"]])
            else:
                # 切换到本地分支
                self.process.start("git", ["checkout", version_data["name"]])
            
            # 显示进度对话框
            progress_dialog.exec()
        except Exception as e:
            print(f"切换版本失败: {str(e)}")
            MessageBox("错误", f"切换版本失败: {str(e)}", self).exec()
    
    def on_switch_finished(self, exit_code, exit_status, progress_dialog):
        """切换版本完成回调"""
        # 关闭进度对话框
        progress_dialog.accept()
        
        if exit_code != 0:
            error_output = self.process.readAllStandardError().data().decode('utf-8', errors='ignore')
            print(f"切换版本失败: {error_output}")
            MessageBox("错误", f"切换版本失败: {error_output}", self).exec()
            return
        
        print("切换版本成功")
        
        # 刷新版本列表
        self.refresh_versions()
        
        # 显示成功提示
        InfoBar.success(
            title="切换成功",
            content="节点版本切换成功",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        
        # 更新节点列表中的更新信息
        self.update_nodes_list_ini()
        
        # 接受对话框（关闭）
        self.accept()
    
    def on_switch_error(self, error, progress_dialog):
        """切换版本错误回调"""
        # 关闭进度对话框
        progress_dialog.accept()
        
        print(f"切换版本错误: {error}")
        MessageBox("错误", f"切换版本时出错: {error}", self).exec()
    
    def save_proxy_settings(self):
        """保存代理设置到nodes.ini文件"""
        try:
            # 获取当前代理复选框状态
            proxy_enabled = self.proxy_checkbox.isChecked()
            
            # 读取现有配置
            config = configparser.ConfigParser()
            if os.path.exists(self.settings_file):
                config.read(self.settings_file, encoding='utf-8')
            
            # 确保git部分存在
            if not config.has_section('git'):
                config.add_section('git')
            
            # 更新代理设置
            config.set('git', 'proxy_enabled', str(proxy_enabled))
            
            # 写入文件
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                config.write(f)
            
            # 更新实例变量
            self.proxy_enabled = proxy_enabled
            
            print(f"已保存代理设置: proxy_enabled={proxy_enabled}")
        except Exception as e:
            print(f"保存代理设置失败: {str(e)}")
    
    def update_nodes_list_ini(self):
        """更新nodes_list.ini文件中的更新信息"""
        try:
            nodes_list_ini = os.path.join('starter', 'nodes_list.ini')
            
            if not os.path.exists(nodes_list_ini):
                print(f"节点列表文件不存在: {nodes_list_ini}")
                return
            
            config = configparser.ConfigParser()
            config.read(nodes_list_ini, encoding='utf-8')
            
            # 确保更新信息部分存在
            if not config.has_section('update_info'):
                config.add_section('update_info')
            
            # 更新当前节点的更新信息
            config.set('update_info', f"{self.node_name}_has_update", "False")
            
            # 写入文件
            with open(nodes_list_ini, 'w', encoding='utf-8') as f:
                config.write(f)
            
            print(f"已更新节点 {self.node_name} 的更新信息")
        except Exception as e:
            print(f"更新节点列表文件失败: {str(e)}")

# 主函数，用于测试
def main():
    app = QApplication(sys.argv)
    dialog = NodeUpdateDialog("test_node", "D:/test_path")
    dialog.exec()

if __name__ == "__main__":
    main()