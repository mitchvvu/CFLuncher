import os

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot

# 显存模式：顺序与设置页下拉框一致
VRAM_MODES = ["gpu_only", "high", "normal", "low", "no", "cpu"]


def _str_prop(key, notify):
    return Property(
        str,
        lambda self: self._values.get(key, ""),
        lambda self, value: self._set(key, value),
        notify=notify,
    )


def _bool_prop(key, notify):
    return Property(
        bool,
        lambda self: self._values.get(key, False),
        lambda self, value: self._set(key, value),
        notify=notify,
    )


class SettingsBackend(QObject):
    """设置页后端：配置读写、路径浏览、启动参数预览。"""

    valueChanged = Signal()
    saveEnabledChanged = Signal()
    saveButtonTextChanged = Signal()
    commandPreviewChanged = Signal()

    notifySuccess = Signal(str, str)
    notifyError = Signal(str, str)

    proxyEnabled = _bool_prop("proxy_enabled", valueChanged)
    proxyType = _str_prop("proxy_type", valueChanged)
    proxyHost = _str_prop("proxy_host", valueChanged)
    proxyPort = _str_prop("proxy_port", valueChanged)

    lanAccess = _bool_prop("lan_access", valueChanged)
    listenAddress = _str_prop("listen_address", valueChanged)
    customPortEnabled = _bool_prop("custom_port_enabled", valueChanged)
    listenPort = _str_prop("listen_port", valueChanged)

    customPathEnabled = _bool_prop("custom_path_enabled", valueChanged)
    comfyuiPath = _str_prop("comfyui_path", valueChanged)

    outputDirEnabled = _bool_prop("output_dir_enabled", valueChanged)
    outputDir = _str_prop("output_dir", valueChanged)
    inputDirEnabled = _bool_prop("input_dir_enabled", valueChanged)
    inputDir = _str_prop("input_dir", valueChanged)

    vramEnabled = _bool_prop("vram_enabled", valueChanged)
    vramMode = _str_prop("vram_mode", valueChanged)
    reserveVramEnabled = _bool_prop("reserve_vram_enabled", valueChanged)
    reserveVram = _str_prop("reserve_vram", valueChanged)
    disableMetadata = _bool_prop("disable_metadata", valueChanged)

    restartCommandEnabled = _bool_prop("restart_command_enabled", valueChanged)
    restartCommandKeyword = _str_prop("restart_command_keyword", valueChanged)

    def __init__(self, data_model, startup_backend, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.startup_backend = startup_backend
        self._values = {}
        self._just_saved = False

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(3000)
        self._save_timer.timeout.connect(self._restore_save_state)

        self.startup_backend.isRunningChanged.connect(self._on_running_changed)
        self.startup_backend.commandPreviewChanged.connect(
            self.commandPreviewChanged.emit
        )

        self.loadSettings()

    # ==================== 只读属性 ====================
    def _get_command_preview(self):
        manager = self.startup_backend.process_manager
        return manager.get_command_string() if manager else ""

    commandPreview = Property(
        str, _get_command_preview, notify=commandPreviewChanged
    )

    def _is_running(self):
        manager = self.startup_backend.process_manager
        return manager.is_running() if manager else False

    def _get_save_enabled(self):
        return (not self._just_saved) and (not self._is_running())

    saveEnabled = Property(bool, _get_save_enabled, notify=saveEnabledChanged)

    def _get_save_button_text(self):
        if self._just_saved:
            return "设置已保存"
        if self._is_running():
            return "ComfyUI运行中，无法保存设置"
        return "保存设置"

    saveButtonText = Property(
        str, _get_save_button_text, notify=saveButtonTextChanged
    )

    def _get_vram_mode_index(self):
        mode = self._values.get("vram_mode", "normal")
        try:
            return VRAM_MODES.index(mode)
        except ValueError:
            return 2

    vramModeIndex = Property(int, _get_vram_mode_index, notify=valueChanged)

    def _get_python_folder_url(self):
        current = self._values.get("comfyui_path", "")
        if current and os.path.exists(current):
            folder = os.path.dirname(current)
        else:
            folder = os.path.expanduser("~")
        return QUrl.fromLocalFile(folder).toString()

    pythonFolderUrl = Property(str, _get_python_folder_url, notify=valueChanged)

    def _get_output_folder_url(self):
        return self._folder_url(self._values.get("output_dir", ""))

    outputFolderUrl = Property(str, _get_output_folder_url, notify=valueChanged)

    def _get_input_folder_url(self):
        return self._folder_url(self._values.get("input_dir", ""))

    inputFolderUrl = Property(str, _get_input_folder_url, notify=valueChanged)

    @staticmethod
    def _folder_url(path):
        if path and os.path.isdir(path):
            return QUrl.fromLocalFile(path).toString()
        return QUrl.fromLocalFile(os.path.expanduser("~")).toString()

    # ==================== 内部方法 ====================
    def _set(self, key, value):
        if self._values.get(key) == value:
            return
        self._values[key] = value
        self.valueChanged.emit()

    def _on_running_changed(self):
        self.saveEnabledChanged.emit()
        self.saveButtonTextChanged.emit()

    def _restore_save_state(self):
        self._just_saved = False
        self.saveEnabledChanged.emit()
        self.saveButtonTextChanged.emit()

    # ==================== 加载 / 保存 ====================
    @Slot()
    def loadSettings(self):
        dm = self.data_model
        self.data_model.set_value("proxy", "only_for_startup", True)
        self._values = {
            "proxy_enabled": dm.get_bool("proxy", "enabled"),
            "proxy_type": dm.get_value("proxy", "proxy_type", "system"),
            "proxy_host": dm.get_value("proxy", "http_proxy", "127.0.0.1"),
            "proxy_port": dm.get_value("proxy", "port", "7897"),
            "lan_access": dm.get_bool("network", "lan_access"),
            "listen_address": dm.get_value("network", "listen", "0.0.0.0"),
            "custom_port_enabled": dm.get_bool("network", "custom_port_enabled"),
            "listen_port": dm.get_value("network", "port", "8188"),
            "custom_path_enabled": dm.get_bool(
                "paths", "custom_comfyui_path_enabled"
            ),
            "comfyui_path": dm.get_value("paths", "comfyui_path", ""),
            "output_dir_enabled": dm.get_bool("advanced", "output_dir_enabled"),
            "output_dir": dm.get_value("advanced", "output_dir", ""),
            "input_dir_enabled": dm.get_bool("advanced", "input_dir_enabled"),
            "input_dir": dm.get_value("advanced", "input_dir", ""),
            "vram_enabled": dm.get_bool("advanced", "vram_enabled", False),
            "vram_mode": dm.get_value("advanced", "vram_mode", "normal"),
            "reserve_vram_enabled": dm.get_bool(
                "advanced", "reserve_vram_enabled"
            ),
            "reserve_vram": dm.get_value("advanced", "reserve_vram", "0.5"),
            "disable_metadata": dm.get_bool("advanced", "disable_metadata"),
            "restart_command_enabled": dm.get_bool(
                "advanced", "restart_command_intercept_enabled", True
            ),
            "restart_command_keyword": dm.get_value(
                "advanced", "restart_command_keyword", "Restarting..."
            ),
        }
        self.valueChanged.emit()
        self.saveEnabledChanged.emit()
        self.saveButtonTextChanged.emit()
        self.commandPreviewChanged.emit()

    @Slot()
    def saveSettings(self):
        dm = self.data_model
        v = self._values

        dm.set_value("proxy", "enabled", v.get("proxy_enabled", False))
        dm.set_value("proxy", "only_for_startup", True)
        dm.set_value("proxy", "proxy_type", v.get("proxy_type", "system"))
        dm.set_value("proxy", "http_proxy", v.get("proxy_host", ""))
        dm.set_value("proxy", "https_proxy", v.get("proxy_host", ""))
        dm.set_value("proxy", "port", v.get("proxy_port", ""))

        dm.set_value("network", "lan_access", v.get("lan_access", False))
        dm.set_value("network", "listen", v.get("listen_address", ""))
        dm.set_value("network", "port", v.get("listen_port", ""))
        dm.set_value(
            "network", "custom_port_enabled", v.get("custom_port_enabled", False)
        )

        dm.set_value(
            "paths",
            "custom_comfyui_path_enabled",
            v.get("custom_path_enabled", False),
        )
        dm.set_value("paths", "comfyui_path", v.get("comfyui_path", ""))

        dm.set_value(
            "advanced", "output_dir_enabled", v.get("output_dir_enabled", False)
        )
        dm.set_value("advanced", "output_dir", v.get("output_dir", ""))
        dm.set_value(
            "advanced", "input_dir_enabled", v.get("input_dir_enabled", False)
        )
        dm.set_value("advanced", "input_dir", v.get("input_dir", ""))

        dm.set_value("advanced", "vram_enabled", v.get("vram_enabled", False))
        dm.set_value("advanced", "vram_mode", v.get("vram_mode", "normal"))
        dm.set_value(
            "advanced",
            "reserve_vram_enabled",
            v.get("reserve_vram_enabled", False),
        )
        dm.set_value("advanced", "reserve_vram", v.get("reserve_vram", "0.5"))
        dm.set_value(
            "advanced", "disable_metadata", v.get("disable_metadata", False)
        )
        dm.set_value(
            "advanced",
            "restart_command_intercept_enabled",
            v.get("restart_command_enabled", True),
        )
        dm.set_value(
            "advanced",
            "restart_command_keyword",
            v.get("restart_command_keyword", "Restarting..."),
        )

        dm.save_config()

        # 通知启动页重建进程管理器，使新设置立即生效
        self.startup_backend.onSettingsChanged()

        self._just_saved = True
        self._save_timer.start()
        self.saveEnabledChanged.emit()
        self.saveButtonTextChanged.emit()
        self.commandPreviewChanged.emit()

    @Slot(str)
    def setProxyType(self, value):
        """代理类型下拉变更时立即持久化，并刷新预览与保存按钮状态。"""
        if self._values.get("proxy_type") == value:
            return
        self._values["proxy_type"] = value
        self.valueChanged.emit()

        self.data_model.set_value("proxy", "proxy_type", value)
        self.data_model.save_config()

        self.commandPreviewChanged.emit()
        self.saveEnabledChanged.emit()
        self.saveButtonTextChanged.emit()

    @Slot()
    def refreshCommandPreview(self):
        self.commandPreviewChanged.emit()

    # ==================== 浏览 / 打开路径 ====================
    @Slot(str)
    def browsePythonFile(self, file_url):
        path = QUrl(file_url).toLocalFile() if file_url else ""
        if not path:
            return
        if os.path.basename(path).lower() != "python.exe":
            self.notifyError.emit(
                "无效的文件", f"所选文件 '{path}' 不是python.exe文件。"
            )
            return
        self._set("comfyui_path", path)

    @Slot(str)
    def browseOutputDir(self, folder_url):
        path = QUrl(folder_url).toLocalFile() if folder_url else ""
        if path:
            self._set("output_dir", path)

    @Slot(str)
    def browseInputDir(self, folder_url):
        path = QUrl(folder_url).toLocalFile() if folder_url else ""
        if path:
            self._set("input_dir", path)

    @Slot()
    def openPythonFolder(self):
        path = self._values.get("comfyui_path", "")
        if path and os.path.exists(path):
            folder = os.path.dirname(path)
            try:
                os.startfile(folder)
            except OSError as e:
                self.notifyError.emit("打开失败", f"打开文件夹时出错: {str(e)}")
        else:
            self.notifyError.emit("错误", "文件路径不存在")
            self._set("comfyui_path", "")
