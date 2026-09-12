import configparser
import os
import re
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    Property,
    QThread,
    Qt,
    QTimer,
    QUrl,
    Signal,
    Slot,
)

import nodes_local_info
from qml_backend.node_version_backend import NodeVersionBackend

MIRROR_CONFIGS = [
    ("PIP官方源（国外）", ""),
    (
        "清华大学-更新及时",
        "-i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn",
    ),
    (
        "阿里云-稳定",
        "-i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com",
    ),
    (
        "中国科技大学-更新及时",
        "-i https://pypi.mirrors.ustc.edu.cn/simple/ --trusted-host pypi.mirrors.ustc.edu.cn",
    ),
    (
        "华为云-稳定",
        "-i https://repo.huaweicloud.com/repository/pypi/simple/ --trusted-host repo.huaweicloud.com",
    ),
    (
        "北京外国语大学-更新及时",
        "-i https://mirrors.cloud.tencent.com/pypi/simple/ --trusted-host mirrors.cloud.tencent.com",
    ),
]

DEP_TYPES = ["安装单个依赖", "卸载单个依赖", "WHL安装", "依赖文件安装"]


class NodeListModel(QAbstractListModel):
    """自定义节点列表模型。"""

    NameHtmlRole = Qt.UserRole + 1
    DisplayNameRole = Qt.UserRole + 2
    VersionRole = Qt.UserRole + 3
    DateRole = Qt.UserRole + 4
    IsEnabledRole = Qt.UserRole + 5
    HasRequirementsRole = Qt.UserRole + 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []

    def roleNames(self):
        return {
            self.NameHtmlRole: b"nameHtml",
            self.DisplayNameRole: b"displayName",
            self.VersionRole: b"version",
            self.DateRole: b"date",
            self.IsEnabledRole: b"isEnabled",
            self.HasRequirementsRole: b"hasRequirements",
        }

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return ""
        row = self._rows[index.row()]
        if role == self.NameHtmlRole:
            return row["nameHtml"]
        if role == self.DisplayNameRole:
            return row["displayName"]
        if role == self.VersionRole:
            return row["version"]
        if role == self.DateRole:
            return row["date"]
        if role == self.IsEnabledRole:
            return row["isEnabled"]
        if role == self.HasRequirementsRole:
            return row["hasRequirements"]
        return ""

    def set_rows(self, rows):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def row_at(self, index):
        if 0 <= index < len(self._rows):
            return self._rows[index]
        return None


class _VersionUpdateThread(QThread):
    """后台执行节点本地版本信息更新。"""

    done = Signal(bool, str)

    def run(self):
        try:
            nodes_local_info.update_nodes_version_info()
            self.done.emit(True, "")
        except Exception as e:
            self.done.emit(False, str(e))


class NodesBackend(QObject):
    """节点管理页后端：依赖管理、节点安装、节点列表管理。"""

    notifySuccess = Signal(str, str)
    notifyError = Signal(str, str)
    notifyInfo = Signal(str, str)
    confirmRequested = Signal(str, str)
    progressStarted = Signal(str, str)
    progressFinished = Signal()
    showNodeVersionDialog = Signal()
    toggleCancelled = Signal(int)

    proxyEnabledChanged = Signal()
    gitProxyEnabledChanged = Signal()
    mirrorIndexChanged = Signal()
    depTypeIndexChanged = Signal()
    depTextChanged = Signal()
    gitUrlChanged = Signal()
    searchTextChanged = Signal()
    busyChanged = Signal()
    listStatusChanged = Signal()
    activeNodeBackendChanged = Signal()

    def __init__(self, data_model, nodes_data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.nodes_data_model = nodes_data_model

        self.nodes_list_ini = os.path.join("starter", "nodes_list.ini")
        self.nodes_list_git_ini = os.path.join("starter", "nodes_list_git.ini")

        self._rows = []
        self._proxy_enabled = self.nodes_data_model.get_bool(
            "pip_mirror", "proxy_enabled"
        )
        self._git_proxy_enabled = self.nodes_data_model.get_bool("git", "proxy_enabled")
        self._mirror_index = self._read_mirror_index()
        self._dep_type_index = 0
        self._dep_text = ""
        self._git_url = ""
        self._search_text = ""
        self._search_count = ""
        self._search_matches = []
        self._current_match = -1
        self._busy = False
        self._list_status = "尚未加载节点列表"

        self._pending_confirm = None
        self._progress_process = None
        self._progress_timer = None
        self._progress_on_finish = None
        self._update_thread = None
        self._active_node_backend = None

        self.node_model = NodeListModel(self)

    # ==================== 基础路径 ====================
    def get_comfyui_path(self):
        dm = self.data_model
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if not dm.get_bool("paths", "custom_comfyui_path_enabled"):
            return os.path.join(app_dir, "ComfyUI")
        python_path = dm.get_value("paths", "comfyui_path")
        if python_path and os.path.exists(python_path):
            parent_dir = os.path.dirname(os.path.dirname(python_path))
            return os.path.join(parent_dir, "ComfyUI")
        return os.path.join(app_dir, "ComfyUI")

    def get_custom_nodes_path(self):
        return os.path.join(self.get_comfyui_path(), "custom_nodes")

    def get_python_exe_path(self):
        dm = self.data_model
        if not dm.get_bool("paths", "custom_comfyui_path_enabled"):
            return ".\\python_embeded\\python.exe"
        return dm.get_value("paths", "comfyui_path") or ".\\python_embeded\\python.exe"

    # ==================== 属性 ====================
    def _get_proxy_enabled(self):
        return self._proxy_enabled

    def _set_proxy_enabled(self, value):
        value = bool(value)
        if self._proxy_enabled == value:
            return
        self._proxy_enabled = value
        self.proxyEnabledChanged.emit()

    proxyEnabled = Property(
        bool, _get_proxy_enabled, _set_proxy_enabled, notify=proxyEnabledChanged
    )

    def _get_git_proxy_enabled(self):
        return self._git_proxy_enabled

    def _set_git_proxy_enabled(self, value):
        value = bool(value)
        if self._git_proxy_enabled == value:
            return
        self._git_proxy_enabled = value
        self.gitProxyEnabledChanged.emit()

    gitProxyEnabled = Property(
        bool,
        _get_git_proxy_enabled,
        _set_git_proxy_enabled,
        notify=gitProxyEnabledChanged,
    )

    def _get_mirror_index(self):
        return self._mirror_index

    def _set_mirror_index(self, value):
        value = int(value)
        if self._mirror_index == value:
            return
        self._mirror_index = value
        self.mirrorIndexChanged.emit()

    mirrorIndex = Property(
        int, _get_mirror_index, _set_mirror_index, notify=mirrorIndexChanged
    )

    def _get_mirror_names(self):
        return [name for name, _ in MIRROR_CONFIGS]

    mirrorNames = Property("QVariantList", _get_mirror_names, constant=True)

    def _get_dep_type_index(self):
        return self._dep_type_index

    def _set_dep_type_index(self, value):
        value = int(value)
        if self._dep_type_index == value:
            return
        self._dep_type_index = value
        self._dep_text = ""
        self.depTextChanged.emit()
        self.depTypeIndexChanged.emit()

    depTypeIndex = Property(
        int, _get_dep_type_index, _set_dep_type_index, notify=depTypeIndexChanged
    )

    def _get_dep_type_names(self):
        return list(DEP_TYPES)

    depTypeNames = Property("QVariantList", _get_dep_type_names, constant=True)

    def _get_dep_browse_enabled(self):
        return self._dep_type_index >= 2

    depBrowseEnabled = Property(
        bool, _get_dep_browse_enabled, notify=depTypeIndexChanged
    )

    def _get_dep_placeholder(self):
        if self._dep_type_index == 0 or self._dep_type_index == 1:
            return "输入依赖包名称"
        if self._dep_type_index == 2:
            return "WHL文件路径"
        return "requirements.txt文件路径"

    depPlaceholder = Property(str, _get_dep_placeholder, notify=depTypeIndexChanged)

    def _get_dep_text(self):
        return self._dep_text

    def _set_dep_text(self, value):
        if self._dep_text == value:
            return
        self._dep_text = value
        self.depTextChanged.emit()

    depText = Property(str, _get_dep_text, _set_dep_text, notify=depTextChanged)

    def _get_git_url(self):
        return self._git_url

    def _set_git_url(self, value):
        if self._git_url == value:
            return
        self._git_url = value
        self.gitUrlChanged.emit()

    gitUrl = Property(str, _get_git_url, _set_git_url, notify=gitUrlChanged)

    def _get_search_text(self):
        return self._search_text

    def _set_search_text(self, value):
        if self._search_text == value:
            return
        self._search_text = value
        self.searchTextChanged.emit()
        self._apply_search()

    searchText = Property(
        str, _get_search_text, _set_search_text, notify=searchTextChanged
    )

    def _get_search_count(self):
        return self._search_count

    searchCount = Property(str, lambda self: self._search_count, notify=searchTextChanged)

    def _get_busy(self):
        return self._busy

    busy = Property(bool, _get_busy, notify=busyChanged)

    def _get_list_status(self):
        return self._list_status

    listStatus = Property(str, _get_list_status, notify=listStatusChanged)

    def _get_node_model(self):
        return self.node_model

    nodeModel = Property(QObject, _get_node_model, constant=True)

    def _get_active_node_backend(self):
        return self._active_node_backend

    activeNodeBackend = Property(
        QObject, _get_active_node_backend, notify=activeNodeBackendChanged
    )

    # ==================== 内部工具 ====================
    def _set_busy(self, value):
        value = bool(value)
        if self._busy == value:
            return
        self._busy = value
        self.busyChanged.emit()

    def _set_list_status(self, text):
        if self._list_status != text:
            self._list_status = text
            self.listStatusChanged.emit()

    def _read_mirror_index(self):
        current_name = self.nodes_data_model.get_value(
            "pip_mirror", "mirror_name", "PIP官方源（国外）"
        )
        for i, (name, _) in enumerate(MIRROR_CONFIGS):
            if name == current_name:
                return i
        return 0

    def _mirror_params(self):
        return MIRROR_CONFIGS[self._mirror_index][1] if MIRROR_CONFIGS else ""

    def _proxy_env(self):
        env = os.environ.copy()
        if self._proxy_enabled:
            http_proxy = self.data_model.get_value("proxy", "http_proxy")
            proxy_port = self.data_model.get_value("proxy", "port")
            proxy_type = self.data_model.get_value("proxy", "proxy_type", "system")
            if isinstance(proxy_type, str) and proxy_type.strip().lower() == "socks5":
                proxy_url = f"socks5://{http_proxy}:{proxy_port}"
            else:
                proxy_url = f"http://{http_proxy}:{proxy_port}"
            env["http_proxy"] = proxy_url
            env["https_proxy"] = proxy_url
        return env

    def _git_proxy_env(self):
        env = os.environ.copy()
        if self._git_proxy_enabled:
            http_proxy = self.data_model.get_value("proxy", "http_proxy")
            proxy_port = self.data_model.get_value("proxy", "port")
            proxy_type = self.data_model.get_value("proxy", "proxy_type", "system")
            if isinstance(proxy_type, str) and proxy_type.strip().lower() == "socks5":
                proxy_url = f"socks5://{http_proxy}:{proxy_port}"
            else:
                proxy_url = f"http://{http_proxy}:{proxy_port}"
            env["http_proxy"] = proxy_url
            env["https_proxy"] = proxy_url
        else:
            env.pop("http_proxy", None)
            env.pop("https_proxy", None)
        return env

    # ==================== 依赖管理 ====================
    @Slot()
    def saveMirrorSettings(self):
        self.nodes_data_model.set_value(
            "pip_mirror", "proxy_enabled", self._proxy_enabled
        )
        self.nodes_data_model.set_value(
            "pip_mirror", "mirror_name", MIRROR_CONFIGS[self._mirror_index][0]
        )
        self.nodes_data_model.set_value(
            "pip_mirror", "mirror_source", MIRROR_CONFIGS[self._mirror_index][1]
        )
        self.nodes_data_model.save_config()
        self.notifySuccess.emit("保存成功", "依赖管理设置已保存")

    @Slot(str)
    def setDepFile(self, file_url):
        path = QUrl(file_url).toLocalFile() if file_url else ""
        if not path:
            return
        self._set_dep_text(f'"{path}"')

    @Slot(str)
    def exportDependencies(self, file_url):
        file_path = QUrl(file_url).toLocalFile() if file_url else ""
        if not file_path:
            return
        python_exe_path = self.get_python_exe_path()
        env = self._proxy_env()
        cmd = f'"{python_exe_path}" -m pip freeze > "{file_path}"'
        print(f"[调试-export_dependencies] 最终执行的导出命令: {cmd}")
        try:
            process = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
            )
            _stdout, stderr = process.communicate()
            if process.returncode == 0:
                self.notifySuccess.emit(
                    "导出成功", "依赖列表已成功导出到 requirements.txt"
                )
            else:
                error_msg = (
                    stderr.decode("utf-8", errors="ignore") if stderr else "未知错误"
                )
                self.notifyError.emit("导出失败", f"导出依赖列表时出错: {error_msg}")
        except Exception as e:
            self.notifyError.emit("导出失败", f"导出依赖列表时出错：{str(e)}")

    @Slot()
    def executeDepCommand(self):
        text_content = self._dep_text.strip()
        if not text_content:
            self.notifyError.emit("输入错误", "请输入依赖包名称或文件路径")
            return
        mirror_params = self._mirror_params()
        if self._dep_type_index == 0:
            self.installSinglePackage(text_content, mirror_params)
        elif self._dep_type_index == 1:
            self.uninstallSinglePackage(text_content)
        elif self._dep_type_index == 2:
            self.installWhlPackage(text_content)
        elif self._dep_type_index == 3:
            self.installRequirementsFile(text_content, mirror_params)

    def installSinglePackage(self, package_name, mirror_params):
        python_exe_path = self.get_python_exe_path()
        install_cmd = f'"{python_exe_path}" -m pip install "{package_name}"'
        if mirror_params:
            install_cmd += f" {mirror_params}"
        display_cmd = f"echo 执行命令: {install_cmd} & echo. & {install_cmd} & pause"
        self._run_console_command(
            "安装依赖",
            f"正在安装 {package_name}，请稍候...\n\n命令行窗口关闭后此对话框将自动关闭。",
            display_cmd,
            self._proxy_env(),
        )

    def uninstallSinglePackage(self, package_name):
        python_exe_path = self.get_python_exe_path()
        uninstall_cmd = f'"{python_exe_path}" -m pip uninstall "{package_name}" -y'
        display_cmd = f"echo 执行命令: {uninstall_cmd} & echo. & {uninstall_cmd} & pause"
        self._run_console_command(
            "卸载依赖",
            f"正在卸载 {package_name}，请稍候...\n\n命令行窗口关闭后此对话框将自动关闭。",
            display_cmd,
            self._proxy_env(),
        )

    def installWhlPackage(self, whl_path):
        python_exe_path = self.get_python_exe_path()
        if whl_path.startswith('"') and whl_path.endswith('"'):
            install_cmd = f'"{python_exe_path}" -m pip install {whl_path}'
        else:
            install_cmd = f'"{python_exe_path}" -m pip install "{whl_path}"'
        display_cmd = f"echo 执行命令: {install_cmd} & echo. & {install_cmd} & pause"
        self._run_console_command(
            "安装WHL",
            "正在安装 WHL 文件，请稍候...\n\n命令行窗口关闭后此对话框将自动关闭。",
            display_cmd,
            self._proxy_env(),
        )

    def installRequirementsFile(self, requirements_path, mirror_params, on_finish=None):
        python_exe_path = self.get_python_exe_path()
        if requirements_path.startswith('"') and requirements_path.endswith('"'):
            install_cmd = f'"{python_exe_path}" -m pip install -r {requirements_path}'
        else:
            install_cmd = f'"{python_exe_path}" -m pip install -r "{requirements_path}"'
        if mirror_params:
            install_cmd += f" {mirror_params}"
        display_cmd = f"echo 执行命令: {install_cmd} & echo. & {install_cmd} & pause"
        return self._run_console_command(
            "安装依赖文件",
            "正在安装依赖文件，请稍候...\n\n命令行窗口关闭后此对话框将自动关闭。",
            display_cmd,
            self._proxy_env(),
            on_finish=on_finish,
        )

    def _parse_package_from_requirements(self, package_name):
        req_path = os.path.join(self.get_comfyui_path(), "requirements.txt")
        if not os.path.exists(req_path):
            return None
        try:
            with open(req_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if package_name.lower() in line.lower():
                        return line
        except Exception as e:
            print(f"[错误-parse_package] 读取requirements.txt失败: {str(e)}")
        return None

    @Slot()
    def installComfyuiThreeDeps(self):
        dependencies = []
        for package in (
            "comfyui-frontend-package",
            "comfyui-workflow-templates",
            "comfyui-embedded-docs",
        ):
            dep = self._parse_package_from_requirements(package)
            if dep:
                dependencies.append(dep)
        if not dependencies:
            self.notifyError.emit("错误", "未在requirements.txt中找到任何ComfyUI相关依赖")
            return
        req_three_path = os.path.join(self.get_comfyui_path(), "req_three.txt")
        try:
            with open(req_three_path, "w", encoding="utf-8") as f:
                for dep in dependencies:
                    f.write(f"{dep}\n")
        except Exception as e:
            self.notifyError.emit("错误", f"创建临时依赖文件时出错：{str(e)}")
            return

        def cleanup():
            try:
                if os.path.exists(req_three_path):
                    os.remove(req_three_path)
            except Exception as e:
                print(f"删除临时文件失败: {str(e)}")

        started = self.installRequirementsFile(
            req_three_path, self._mirror_params(), on_finish=cleanup
        )
        if not started:
            cleanup()

    @Slot()
    def openComfyuiRequirements(self):
        req_path = os.path.join(self.get_comfyui_path(), "requirements.txt")
        if os.path.exists(req_path):
            self._open_path(req_path)
        else:
            self.notifyError.emit("错误", f"ComfyUI本体依赖文件不存在：{req_path}")

    def _open_path(self, path):
        try:
            os.startfile(path)
        except Exception as e:
            self.notifyError.emit("打开失败", f"无法打开：{str(e)}")

    # ==================== 控制台命令 ====================
    def _run_console_command(self, title, content, display_cmd, env, on_finish=None):
        try:
            process = subprocess.Popen(
                f'cmd.exe /c "{display_cmd}"',
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                env=env,
            )
        except Exception as e:
            self.notifyError.emit("错误", f"执行命令时出错：{str(e)}")
            return False

        self._progress_process = process
        self._progress_on_finish = on_finish
        self.progressStarted.emit(title, content)

        timer = QTimer(self)

        def check_process():
            if process.poll() is not None:
                timer.stop()
                self._progress_timer = None
                self._progress_process = None
                self.progressFinished.emit()
                callback = self._progress_on_finish
                self._progress_on_finish = None
                if callback:
                    callback()

        timer.timeout.connect(check_process)
        timer.start(500)
        self._progress_timer = timer
        return True

    @Slot()
    def cancelProgress(self):
        if self._progress_timer is not None:
            self._progress_timer.stop()
            self._progress_timer = None
        process = self._progress_process
        self._progress_process = None
        self._progress_on_finish = None
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except Exception:
                pass

    # ==================== 自定义节点安装 ====================
    @Slot()
    def executeGitClone(self):
        git_url = self._git_url.strip()
        if not git_url:
            self.notifyError.emit("错误", "请输入有效的git网址")
            return

        self.nodes_data_model.set_value("git", "proxy_enabled", self._git_proxy_enabled)
        self.nodes_data_model.save_config()

        custom_nodes_path = self.get_custom_nodes_path()
        cmd = f"git clone {git_url}"
        display_cmd = (
            f'echo 当前目录: {custom_nodes_path} & echo 执行命令: {cmd} & echo. & '
            f'cd /d "{custom_nodes_path}" & {cmd} & pause'
        )
        self._run_console_command(
            "自定义节点安装",
            "正在执行命令，请稍候...\n\n命令行窗口关闭后此对话框将自动关闭。",
            display_cmd,
            self._git_proxy_env(),
            on_finish=lambda: self.loadNodes(True),
        )

    # ==================== 节点列表 ====================
    def _load_nodes_from_folder(self):
        custom_nodes_path = self.get_custom_nodes_path()
        disabled_nodes_path = os.path.join(custom_nodes_path, ".disabled")

        enabled_nodes = []
        if os.path.exists(custom_nodes_path):
            try:
                for item in os.listdir(custom_nodes_path):
                    item_path = os.path.join(custom_nodes_path, item)
                    if (
                        os.path.isdir(item_path)
                        and item != "__pycache__"
                        and item != ".disabled"
                    ):
                        enabled_nodes.append(item)
            except Exception as e:
                self.notifyError.emit("加载失败", f"无法读取启用节点: {str(e)}")
                return [], []

        disabled_nodes = []
        if os.path.exists(disabled_nodes_path):
            try:
                for item in os.listdir(disabled_nodes_path):
                    item_path = os.path.join(disabled_nodes_path, item)
                    if os.path.isdir(item_path):
                        display_name = item.split("@")[0] if "@" in item else item
                        disabled_nodes.append((display_name, item))
            except Exception as e:
                self.notifyError.emit("加载失败", f"无法读取禁用节点: {str(e)}")
                return [], []

        self._save_nodes_to_ini(enabled_nodes, disabled_nodes)
        return enabled_nodes, disabled_nodes

    def _save_nodes_to_ini(self, enabled_nodes, disabled_nodes):
        config = configparser.ConfigParser()
        if os.path.exists(self.nodes_list_ini):
            config.read(self.nodes_list_ini, encoding="utf-8")

        update_info = dict(config.items("update_info")) if config.has_section(
            "update_info"
        ) else {}

        for section in ("enabled_nodes", "disabled_nodes", "update_info"):
            if config.has_section(section):
                config.remove_section(section)
            config.add_section(section)

        for i, node in enumerate(enabled_nodes):
            config.set("enabled_nodes", f"node_{i}", node)
            if f"{node}_version" not in update_info:
                config.set("update_info", f"{node}_version", "Unknown")
            if f"{node}_date" not in update_info:
                config.set("update_info", f"{node}_date", "Unknown")

        for i, (display_name, original_name) in enumerate(disabled_nodes):
            config.set("disabled_nodes", f"node_{i}_display", display_name)
            config.set("disabled_nodes", f"node_{i}_original", original_name)
            if f"{display_name}_version" not in update_info:
                config.set("update_info", f"{display_name}_version", "Unknown")
            if f"{display_name}_date" not in update_info:
                config.set("update_info", f"{display_name}_date", "Unknown")

        for key, value in update_info.items():
            config.set("update_info", key, value)

        with open(self.nodes_list_ini, "w", encoding="utf-8") as f:
            config.write(f)

    def _load_nodes_from_ini(self):
        if not os.path.exists(self.nodes_list_ini):
            enabled, disabled = self._load_nodes_from_folder()
            return enabled, disabled, {}

        config = configparser.ConfigParser()
        config.read(self.nodes_list_ini, encoding="utf-8")

        enabled_nodes = []
        if config.has_section("enabled_nodes"):
            for _, value in config.items("enabled_nodes"):
                enabled_nodes.append(value)

        disabled_nodes = []
        if config.has_section("disabled_nodes"):
            display_names = []
            original_names = []
            for key, value in config.items("disabled_nodes"):
                if key.endswith("_display"):
                    display_names.append((key, value))
                elif key.endswith("_original"):
                    original_names.append((key, value))
            for display_key, display_value in display_names:
                node_index = display_key.split("_")[1]
                original_key = f"node_{node_index}_original"
                for orig_key, orig_value in original_names:
                    if orig_key == original_key:
                        disabled_nodes.append((display_value, orig_value))
                        break

        git_info = {}
        if config.has_section("update_info"):
            git_info = dict(config.items("update_info"))

        return enabled_nodes, disabled_nodes, git_info

    def _load_update_flags(self):
        flags = {}
        if not os.path.exists(self.nodes_list_git_ini):
            return flags
        try:
            config = configparser.ConfigParser()
            config.read(self.nodes_list_git_ini, encoding="utf-8")
            if not config.has_section("git_info"):
                return flags
            for key in config.options("git_info"):
                if key.endswith("_has_update"):
                    node_name = key[: -len("_has_update")]
                    flags[node_name] = config.getboolean("git_info", key)
        except Exception as e:
            print(f"读取节点更新标记失败: {str(e)}")
        return flags

    def _build_name_html(self, name, has_update):
        base_color = "#feb201" if has_update else "#00a7b3"
        inner = name
        query = self._search_text.strip()
        if query:
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            inner = pattern.sub(
                lambda m: (
                    '<span style="background-color:#ffff00;color:#000000;">'
                    f"{m.group(0)}</span>"
                ),
                name,
            )
        return f'<span style="color:{base_color};font-weight:bold;">{inner}</span>'

    @Slot(bool)
    def loadNodes(self, force_reload_from_folder=False):
        custom_nodes_path = self.get_custom_nodes_path()
        if force_reload_from_folder:
            enabled_nodes, disabled_nodes = self._load_nodes_from_folder()
            update_flags = {}
        else:
            enabled_nodes, disabled_nodes, _git_info = self._load_nodes_from_ini()
            update_flags = self._load_update_flags()

        all_nodes = [(name, name, True) for name in enabled_nodes] + [
            (display_name, original_name, False)
            for display_name, original_name in disabled_nodes
        ]
        all_nodes.sort(key=lambda x: x[0].lower())

        rows = []
        for display_name, original_name, is_enabled in all_nodes:
            saved_state = self.nodes_data_model.get_value("nodes", display_name)
            if saved_state is not None:
                is_enabled = str(saved_state).lower() in ("true", "1", "yes", "on")

            if is_enabled:
                node_path = os.path.join(custom_nodes_path, original_name)
            else:
                node_path = os.path.join(
                    custom_nodes_path, ".disabled", original_name
                )

            version, date_time = nodes_local_info.get_node_git_version_and_date(
                node_path
            )
            has_update = bool(update_flags.get(display_name, False))

            rows.append(
                {
                    "displayName": display_name,
                    "originalName": original_name,
                    "isEnabled": is_enabled,
                    "nodePath": node_path,
                    "version": version,
                    "date": date_time,
                    "hasUpdate": has_update,
                    "hasRequirements": os.path.exists(
                        os.path.join(node_path, "requirements.txt")
                    ),
                    "nameHtml": self._build_name_html(display_name, has_update),
                }
            )

        self._rows = rows
        self._search_matches = []
        self._current_match = -1
        self._search_count = ""
        self.node_model.set_rows(rows)
        self.searchTextChanged.emit()
        self._set_list_status(
            "暂无自定义节点" if not rows else f"共 {len(rows)} 个自定义节点"
        )

    @Slot()
    def refreshNodeList(self):
        self._search_text = ""
        self.searchTextChanged.emit()
        self.loadNodes(True)

    @Slot()
    def fetchLocalVersions(self):
        if self._update_thread is not None and self._update_thread.isRunning():
            return
        self._set_busy(True)
        self.notifyInfo.emit("正在获取", "正在获取本地节点版本信息，请稍候...")

        def on_done(success, error):
            self._set_busy(False)
            if success:
                self.loadNodes(False)
                self.notifySuccess.emit("获取完成", "节点版本信息已更新")
            else:
                self.notifyError.emit("执行失败", f"获取版本信息时出错：{error}")

        self._update_thread = _VersionUpdateThread(self)
        self._update_thread.done.connect(on_done)
        self._update_thread.start()

    # ==================== 节点搜索 ====================
    @Slot()
    def clearSearch(self):
        if not self._search_text:
            return
        self._search_text = ""
        self.searchTextChanged.emit()
        self._apply_search()

    def _apply_search(self):
        query = self._search_text.strip().lower()
        self._search_matches = []
        if query:
            for i, row in enumerate(self._rows):
                if query in row["displayName"].lower():
                    self._search_matches.append(i)

        for row in self._rows:
            row["nameHtml"] = self._build_name_html(
                row["displayName"], row["hasUpdate"]
            )
        if self._rows:
            self.node_model.dataChanged.emit(
                self.node_model.index(0),
                self.node_model.index(len(self._rows) - 1),
                [NodeListModel.NameHtmlRole],
            )

        if self._search_matches:
            self._current_match = 0
            self._search_count = f"1/{len(self._search_matches)}"
        else:
            self._current_match = -1
            self._search_count = ""
        self.searchTextChanged.emit()
        return self._current_match

    @Slot(result=int)
    def nextMatch(self):
        return self._cycle_match(1)

    @Slot(result=int)
    def previousMatch(self):
        return self._cycle_match(-1)

    def _cycle_match(self, step):
        if not self._search_matches:
            return -1
        self._current_match = (self._current_match + step) % len(self._search_matches)
        self._search_count = f"{self._current_match + 1}/{len(self._search_matches)}"
        self.searchTextChanged.emit()
        return self._search_matches[self._current_match]

    @Slot(result=int)
    def currentMatchIndex(self):
        if not self._search_matches:
            return -1
        return self._search_matches[self._current_match]

    # ==================== 节点操作 ====================
    @Slot(int, bool)
    def toggleNode(self, index, enabled):
        row = self.node_model.row_at(index)
        if row is None:
            return
        if bool(row["isEnabled"]) == bool(enabled):
            return

        custom_nodes_path = self.get_custom_nodes_path()
        disabled_nodes_path = os.path.join(custom_nodes_path, ".disabled")

        if enabled:
            source_path = os.path.join(
                disabled_nodes_path, row["originalName"]
            )
            clean_name = (
                row["originalName"].split("@")[0]
                if "@" in row["originalName"]
                else row["originalName"]
            )
            target_path = os.path.join(custom_nodes_path, clean_name)
            conflict_message = f"文件夹 {clean_name} 已存在，是否覆盖？"
        else:
            source_path = os.path.join(custom_nodes_path, row["displayName"])
            target_path = os.path.join(disabled_nodes_path, row["displayName"])
            conflict_message = f"禁用文件夹中已存在 {row['displayName']}，是否覆盖？"

        def do_move():
            self._perform_toggle(index, enabled, source_path, target_path)

        if os.path.exists(target_path):
            self._pending_confirm = {"action": do_move, "index": index}
            self.confirmRequested.emit("确认覆盖", conflict_message)
            return

        do_move()

    @Slot()
    def confirmPending(self):
        pending = self._pending_confirm
        self._pending_confirm = None
        if pending is None:
            return
        pending["action"]()

    @Slot()
    def cancelPending(self):
        pending = self._pending_confirm
        self._pending_confirm = None
        if pending is not None:
            self.toggleCancelled.emit(pending["index"])

    def _perform_toggle(self, index, enabled, source_path, target_path):
        row = self.node_model.row_at(index)
        if row is None:
            return
        display_name = row["displayName"]
        custom_nodes_path = self.get_custom_nodes_path()
        disabled_nodes_path = os.path.join(custom_nodes_path, ".disabled")

        if not os.path.exists(disabled_nodes_path):
            os.makedirs(disabled_nodes_path, exist_ok=True)

        # 覆盖场景：先删除已存在的目标目录，避免移动进目标内部
        if os.path.exists(target_path):
            try:
                shutil.rmtree(target_path)
            except Exception as e:
                self.notifyError.emit("错误", f"无法删除现有文件夹：{str(e)}")
                self.toggleCancelled.emit(index)
                return

        try:
            shutil.move(source_path, target_path)
        except Exception as e:
            action = "启用" if enabled else "禁用"
            self.notifyError.emit("错误", f"无法{action}节点 {display_name}：{str(e)}")
            self.toggleCancelled.emit(index)
            return

        if enabled:
            clean_name = (
                row["originalName"].split("@")[0]
                if "@" in row["originalName"]
                else row["originalName"]
            )
            row["originalName"] = clean_name
            row["nodePath"] = target_path
            row["hasRequirements"] = os.path.exists(
                os.path.join(target_path, "requirements.txt")
            )
        else:
            row["originalName"] = display_name
            row["nodePath"] = target_path
            row["hasRequirements"] = os.path.exists(
                os.path.join(target_path, "requirements.txt")
            )

        row["isEnabled"] = enabled
        row["version"], row["date"] = nodes_local_info.get_node_git_version_and_date(
            row["nodePath"]
        )

        self.nodes_data_model.set_value("nodes", display_name, enabled)
        self.nodes_data_model.save_config()

        self._update_node_in_ini(display_name, enabled, row["originalName"])

        self.node_model.dataChanged.emit(
            self.node_model.index(index),
            self.node_model.index(index),
            [
                NodeListModel.IsEnabledRole,
                NodeListModel.VersionRole,
                NodeListModel.DateRole,
                NodeListModel.HasRequirementsRole,
            ],
        )

        self.notifySuccess.emit(
            "节点已启用" if enabled else "节点已禁用",
            f"节点 {display_name} 已成功{'启用' if enabled else '禁用'}",
        )

    def _update_node_in_ini(self, display_name, is_enabled, original_name=None):
        config = configparser.ConfigParser()
        if os.path.exists(self.nodes_list_ini):
            config.read(self.nodes_list_ini, encoding="utf-8")
        if not config.has_section("enabled_nodes"):
            config.add_section("enabled_nodes")
        if not config.has_section("disabled_nodes"):
            config.add_section("disabled_nodes")

        if is_enabled:
            for key in list(config["disabled_nodes"]):
                if (
                    key.endswith("_display")
                    and config["disabled_nodes"][key] == display_name
                ):
                    node_index = key.split("_")[1]
                    config.remove_option("disabled_nodes", key)
                    config.remove_option("disabled_nodes", f"node_{node_index}_original")

            max_index = -1
            for key in config["enabled_nodes"]:
                if key.startswith("node_"):
                    try:
                        max_index = max(max_index, int(key.split("_")[1]))
                    except ValueError:
                        pass
            config.set("enabled_nodes", f"node_{max_index + 1}", display_name)
        else:
            for key, value in list(config.items("enabled_nodes")):
                if value == display_name or (
                    original_name and value == original_name
                ):
                    config.remove_option("enabled_nodes", key)

            max_index = -1
            for key in config["disabled_nodes"]:
                if key.endswith("_display"):
                    try:
                        max_index = max(max_index, int(key.split("_")[1]))
                    except ValueError:
                        pass
            config.set("disabled_nodes", f"node_{max_index + 1}_display", display_name)
            config.set(
                "disabled_nodes",
                f"node_{max_index + 1}_original",
                original_name or display_name,
            )

        with open(self.nodes_list_ini, "w", encoding="utf-8") as f:
            config.write(f)

    @Slot(int)
    def installRequirementsForNode(self, index):
        row = self.node_model.row_at(index)
        if row is None:
            return
        req_path = os.path.join(row["nodePath"], "requirements.txt")
        if not os.path.exists(req_path):
            self.notifyError.emit("错误", f"未找到依赖文件：{req_path}")
            return
        self.installRequirementsFile(req_path, self._mirror_params())

    @Slot(int)
    def openFolderForNode(self, index):
        row = self.node_model.row_at(index)
        if row is None:
            return
        if os.path.exists(row["nodePath"]):
            self._open_path(row["nodePath"])
        else:
            self.notifyError.emit("错误", f"文件夹不存在：{row['nodePath']}")

    @Slot(int)
    def openReqFileForNode(self, index):
        row = self.node_model.row_at(index)
        if row is None:
            return
        req_path = os.path.join(row["nodePath"], "requirements.txt")
        if os.path.exists(req_path):
            self._open_path(req_path)
        else:
            self.notifyError.emit("错误", f"依赖文件不存在：{req_path}")

    # ==================== 单节点版本管理 ====================
    @Slot(int)
    def openNodeVersion(self, index):
        row = self.node_model.row_at(index)
        if row is None:
            return
        if not row["isEnabled"]:
            self.notifyError.emit("错误", "只能更新已启用的节点")
            return
        if not os.path.exists(os.path.join(row["nodePath"], ".git")):
            self.notifyError.emit(
                "错误", f"节点 {row['displayName']} 不是通过Git安装的，无法更新"
            )
            return

        self._active_node_backend = NodeVersionBackend(
            row["displayName"], row["nodePath"], self
        )
        self.activeNodeBackendChanged.emit()
        self.showNodeVersionDialog.emit()

    @Slot()
    def closeNodeVersion(self):
        if self._active_node_backend is None:
            return
        backend = self._active_node_backend
        self._active_node_backend = None
        self.activeNodeBackendChanged.emit()
        backend.deleteLater()
        self.loadNodes(False)
