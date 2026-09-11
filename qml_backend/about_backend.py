from PySide6.QtCore import QObject, Signal, Property

APP_VERSION = "0.7.0"
APP_TITLE = "ComfyUI 启动器"


class AboutBackend(QObject):
    """关于页后端，仅提供静态版本信息。"""

    appTitleChanged = Signal()
    appVersionChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._app_title = APP_TITLE
        self._app_version = APP_VERSION

    def _get_app_title(self):
        return self._app_title

    appTitle = Property(str, _get_app_title, notify=appTitleChanged)

    def _get_app_version(self):
        return self._app_version

    appVersion = Property(str, _get_app_version, notify=appVersionChanged)
