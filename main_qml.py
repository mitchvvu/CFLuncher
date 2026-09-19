import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _application_dir():
    """返回应用程序所在目录，兼容 PyInstaller 打包后的环境。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return BASE_DIR


os.chdir(_application_dir())
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from prismqml import App, AsyncQmlPage, Window, WindowType, Theme, setTheme

from data_model import DataModel, NodesDataModel
from qml_backend.about_backend import AboutBackend
from qml_backend.nodes_backend import NodesBackend
from qml_backend.settings_backend import SettingsBackend
from qml_backend.startup_backend import StartupBackend
from qml_backend.version_backend import VersionBackend

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
MIN_WINDOW_WIDTH = 600
MIN_WINDOW_HEIGHT = 600
QML_DIR = os.path.join(BASE_DIR, "qml")


def _resource_path(relative_path):
    """获取资源绝对路径，兼容开发环境与 PyInstaller 打包后的环境。"""
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = BASE_DIR
    return os.path.join(base_path, relative_path)


def ensure_config_files():
    """确保配置文件正确移动到 starter 目录。"""
    starter_dir = os.path.join(_application_dir(), "starter")
    os.makedirs(starter_dir, exist_ok=True)

    launcher_ini = os.path.join(_application_dir(), "launcher.ini")
    starter_launcher_ini = os.path.join(starter_dir, "launcher.ini")

    if os.path.exists(launcher_ini) and not os.path.exists(starter_launcher_ini):
        try:
            import shutil

            shutil.copy2(launcher_ini, starter_launcher_ini)
            print(f"已复制 {launcher_ini} 到 {starter_launcher_ini}")
        except Exception as e:
            print(f"复制配置文件失败: {str(e)}")


def _qml(name):
    return os.path.join(QML_DIR, name)


class MainWindow(Window):
    """主窗口，负责导航与各页面 backend 的生命周期。"""

    def __init__(self, data_model, nodes_data_model):
        super().__init__(window_type=WindowType.BAR)
        self.data_model = data_model
        self.nodes_data_model = nodes_data_model

        self.setWindowTitle("ComfyUI 启动器")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # 过渡动画：首次切页不再用圆形遮罩缩放，改为与已加载页一致的「下滑入+淡入」，
        # 页面未加载完成期间只显示居中的等待动画；关闭窗口也不再播放圆形收缩动画。
        # 0 对应 PrismQML 的 Enums.lazyAnimation.none。
        self._set_window_property("lazyAnimationType", 0)
        self._set_window_property("closeAnimationType", 0)

        icon_path = _resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(icon_path)
        else:
            print(f"警告：无法找到图标文件：{icon_path}")

        # 各页面 backend（随窗口存活）
        self.startup_backend = StartupBackend(data_model, self)
        self.about_backend = AboutBackend(self)
        self.settings_backend = SettingsBackend(
            data_model, self.startup_backend, self
        )
        self.version_backend = VersionBackend(data_model, self)
        self.nodes_backend = NodesBackend(data_model, nodes_data_model, self)

        self.startup_page = AsyncQmlPage(
            _qml("StartupPage.qml"), backend=self.startup_backend
        )
        self.version_page = AsyncQmlPage(
            _qml("VersionPage.qml"), backend=self.version_backend
        )
        self.nodes_page = AsyncQmlPage(
            _qml("NodesPage.qml"), backend=self.nodes_backend
        )
        self.dependency_page = AsyncQmlPage(
            _qml("DependencyPage.qml"), backend=self.nodes_backend
        )
        self.settings_page = AsyncQmlPage(
            _qml("SettingsPage.qml"), backend=self.settings_backend
        )
        self.about_page = AsyncQmlPage(_qml("AboutPage.qml"), backend=self.about_backend)

        self.addPage(self.startup_page, "Play", "启动", position="top")
        self.addPage(self.version_page, "ArrowSync", "版本管理", position="top")
        self.addPage(self.dependency_page, "Box", "依赖管理", position="top")
        self.addPage(self.nodes_page, "Tag", "节点管理", position="top")
        self.addPage(self.settings_page, "Settings", "设置", position="top")
        self.addPage(self.about_page, "Info", "关于", position="bottom")

    @property
    def process_manager(self):
        return self.startup_backend.process_manager

    def closeEvent(self, event):
        """窗口关闭事件，确保 ComfyUI 进程被正确关闭。"""
        if self.process_manager is not None:
            self.process_manager.stop_comfyui()
            if self.process_manager.is_running():
                if not self.process_manager.wait_for_finished(3000):
                    self.process_manager.force_kill()
                    self.process_manager._intentional_kill = True
                    for _ in range(5):
                        if self.process_manager.wait_for_finished(1000):
                            break
        event.accept()


def main():
    App.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    ensure_config_files()

    icon_path = _resource_path("icon.ico")
    app = App(
        sys.argv,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        application_icon=icon_path if os.path.exists(icon_path) else None,
        persist_appearance=False,
        auto_update_slot_redirect=False,
    )
    setTheme(Theme.AUTO)

    font = app.font()
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    data_model = DataModel()
    nodes_data_model = NodesDataModel()

    window = MainWindow(data_model, nodes_data_model)
    window.setSplashEnabled(False)
    window.show()
    # 仅保留一个最小尺寸，宽高均可自由拉伸（不再锁定为固定大小）。
    window.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
