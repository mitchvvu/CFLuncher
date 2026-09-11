import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QProcess
from PySide6.QtGui import QIcon, QFont

# 导入 Fluent Widgets
from qfluentwidgets import (FluentWindow, NavigationItemPosition, FluentIcon, 
                           setTheme, Theme)

# 导入自定义模块
from data_model import DataModel, NodesDataModel
from startup_panel import StartupPanel
from settings_panel import SettingsPanel
from nodes_panel import NodesPanel
from version_panel import VersionPanel
from about_panel import AboutPanel

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        
        # 确保配置文件正确移动到starter目录
        self.ensure_config_files()
        
        # 初始化数据模型
        self.data_model = DataModel()
        self.nodes_data_model = NodesDataModel()
        
        # 设置窗口属性
        self.setWindowTitle("ComfyUI 启动器")
        self.resize(1000, 960)
        self.setFixedSize(self.size())
        
        # 设置窗口图标，考虑打包后的路径
        def resource_path(relative_path):
            """获取资源的绝对路径，适用于开发环境和PyInstaller打包后的环境"""
            if getattr(sys, 'frozen', False):
                # 如果是打包后的可执行文件
                base_path = sys._MEIPASS
            else:
                # 如果是脚本运行
                base_path = os.path.abspath(os.path.dirname(__file__))
            return os.path.join(base_path, relative_path)
        
        # 使用resource_path函数获取图标路径
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"警告：无法找到图标文件：{icon_path}")
            # 尝试在其他可能的位置查找
            alt_paths = [
                "icon.ico",
                os.path.join(os.path.dirname(sys.executable), "icon.ico"),
                os.path.join(os.getcwd(), "icon.ico")
            ]
            for path in alt_paths:
                if os.path.exists(path):
                    self.setWindowIcon(QIcon(path))
                    print(f"找到图标文件：{path}")
                    break
        
        # 创建各个面板
        self.startup_panel = StartupPanel(self.data_model)
        self.startup_panel.setObjectName("startup_panel")
        
        self.version_panel = VersionPanel()
        self.version_panel.setObjectName("version_panel")
        
        self.nodes_panel = NodesPanel(self.data_model, self.nodes_data_model)
        self.nodes_panel.setObjectName("nodes_panel")
        
        self.settings_panel = SettingsPanel(self.data_model, self.startup_panel.process_manager)
        self.settings_panel.setObjectName("settings_panel")
        
        self.about_panel = AboutPanel()
        self.about_panel.setObjectName("about_panel")
        
        # 连接设置面板的settings_changed信号到启动面板的settings_updated方法
        self.settings_panel.settings_changed.connect(self.startup_panel.settings_updated)
        
        # 确保进程管理器的status_changed信号连接到设置面板的update_save_button_state方法
        # 在settings_panel的__init__方法中已经连接了这个信号，这里不需要重复连接
        # 只需要初始化保存按钮状态
        is_running = self.startup_panel.process_manager.is_running()
        print(f"主窗口初始化时ComfyUI运行状态: {is_running}")
        self.settings_panel.update_save_button_state(is_running)
        
        # 添加导航项目
        self.addSubInterface(self.startup_panel, FluentIcon.PLAY, "启动", NavigationItemPosition.TOP)
        self.addSubInterface(self.version_panel, FluentIcon.SYNC, "版本管理", NavigationItemPosition.TOP)
        self.addSubInterface(self.nodes_panel, FluentIcon.APPLICATION, "节点管理", NavigationItemPosition.TOP)
        self.addSubInterface(self.settings_panel, FluentIcon.SETTING, "设置", NavigationItemPosition.TOP)
        self.addSubInterface(self.about_panel, FluentIcon.INFO, "关于", NavigationItemPosition.BOTTOM)
        
        # 设置主题
        setTheme(Theme.AUTO)
    
    def changeEvent(self, event):
        """窗口状态变化事件，处理窗口最小化和恢复"""
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.WindowStateChange:
            # 窗口最小化时暂停加载操作
            is_minimized = self.windowState() & Qt.WindowMinimized
            if is_minimized:
                print("窗口最小化，暂停加载操作")
                # 通知版本面板处理窗口最小化
                if hasattr(self, 'version_panel'):
                    self.version_panel.handle_window_state_change(True)
                
                # 通知节点面板处理窗口最小化
                if hasattr(self, 'nodes_panel'):
                    self.nodes_panel.handle_window_state_change(True)
            
            # 窗口恢复时不自动恢复加载，让用户手动刷新以保持UI流畅
        
        super().changeEvent(event)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 确保ComfyUI进程被正确关闭
        if hasattr(self.startup_panel, 'process_manager'):
            # 停止ComfyUI进程
            # stop_comfyui方法内部已经设置了_intentional_kill标记
            self.startup_panel.process_manager.stop_comfyui()
            # 等待进程完全停止
            if self.startup_panel.process_manager.is_running():
                # 如果进程仍在运行，等待最多3秒
                if not self.startup_panel.process_manager.wait_for_finished(3000):
                    # 如果等待超时，强制结束进程
                    self.startup_panel.process_manager.force_kill()
                    # 强制终止后，确保_intentional_kill标记被设置，以便process_finished处理
                    self.startup_panel.process_manager._intentional_kill = True
                    # 再次等待进程完全停止，确保进程已经被终止
                    for _ in range(5):  # 尝试多次等待，确保进程完全终止
                        if self.startup_panel.process_manager.wait_for_finished(1000):
                            break  # 如果进程已终止，跳出循环
        
        # 注意：我们不再使用终止所有python.exe进程的方法
        # 因为这可能会影响系统中其他与ComfyUI无关的python.exe进程
        # 在process_manager.py的stop_comfyui和force_kill方法中
        # 已经通过进程ID精确终止了ComfyUI相关的进程及其子进程
        
        event.accept()
    
    def ensure_config_files(self):
        """确保配置文件正确移动到starter目录"""
        # 确保starter目录存在
        starter_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'starter')
        os.makedirs(starter_dir, exist_ok=True)
        
        # 检查launcher.ini是否存在，如果存在且starter/launcher.ini不存在，则复制
        launcher_ini = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'launcher.ini')
        starter_launcher_ini = os.path.join(starter_dir, 'launcher.ini')
        
        if os.path.exists(launcher_ini) and not os.path.exists(starter_launcher_ini):
            try:
                import shutil
                shutil.copy2(launcher_ini, starter_launcher_ini)
                print(f"已复制 {launcher_ini} 到 {starter_launcher_ini}")
            except Exception as e:
                print(f"复制配置文件失败: {str(e)}")
        
        # 注意：不再在这里创建nodes.ini文件
        # 让NodesDataModel自己处理默认配置，确保使用正确的default_settings


def main():
    # 确保当前工作目录是应用程序所在目录
    if getattr(sys, 'frozen', False):
        # 如果是打包后的可执行文件
        application_path = os.path.dirname(sys.executable)
    else:
        # 如果是脚本运行
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    os.chdir(application_path)
    
    # 启用高DPI支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    # 设置字体抗锯齿
    font = app.font()
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用程序事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()