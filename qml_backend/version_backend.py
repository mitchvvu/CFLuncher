import configparser
import os
import sys
import webbrowser
from datetime import datetime

import git
from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    Property,
    QProcess,
    Qt,
    Signal,
    Slot,
)

DEFAULT_SOURCE_URL = "https://github.com/Comfy-Org/ComfyUI.git"

SOURCE_CONFIGS = [
    ("GitHub官方(国外)", "https://github.com/Comfy-Org/ComfyUI.git"),
]


class VersionListModel(QAbstractListModel):
    """可用版本列表模型。"""

    CommitRole = Qt.UserRole + 1
    DateRole = Qt.UserRole + 2
    TextRole = Qt.UserRole + 3
    IsCurrentRole = Qt.UserRole + 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []

    def roleNames(self):
        return {
            self.CommitRole: b"commitId",
            self.DateRole: b"date",
            self.TextRole: b"text",
            self.IsCurrentRole: b"isCurrent",
        }

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return ""
        row = self._rows[index.row()]
        if role == self.CommitRole:
            return row["commitId"]
        if role == self.DateRole:
            return row["date"]
        if role == self.TextRole:
            return row["text"]
        if role == self.IsCurrentRole:
            return row["isCurrent"]
        return ""

    def set_rows(self, rows):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()


class VersionBackend(QObject):
    """版本管理页后端：版本列表加载、刷新、切换。"""

    notifySuccess = Signal(str, str)
    notifyError = Signal(str, str)
    notifyInfo = Signal(str, str)

    proxyEnabledChanged = Signal()
    activeTabChanged = Signal()
    statusChanged = Signal()
    sourceChanged = Signal()
    busyChanged = Signal()
    selectedChanged = Signal()
    listReset = Signal()

    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.versions_file = os.path.join("starter", "git.ini")
        self.settings_file = os.path.join("starter", "version.ini")

        self.repo = None
        self.process = None
        self.versions = []
        self._filtered = []

        self._proxy_enabled = False
        self._source_url = DEFAULT_SOURCE_URL
        self._active_tab = "stable"
        self._status_text = "未检测"
        self._busy = False
        self._selected_index = -1

        self.version_model = VersionListModel(self)

        self.loadSettings()
        self.checkRepoStatus()
        self._detect_initial_tab()

    # ==================== 属性 ====================
    def _get_proxy_enabled(self):
        return self._proxy_enabled

    def _set_proxy_enabled(self, value):
        value = bool(value)
        if self._proxy_enabled == value:
            return
        self._proxy_enabled = value
        self.saveSettings()
        self.proxyEnabledChanged.emit()

    proxyEnabled = Property(
        bool, _get_proxy_enabled, _set_proxy_enabled, notify=proxyEnabledChanged
    )

    def _get_source_url(self):
        return self._source_url

    def _set_source_url(self, value):
        if not value or self._source_url == value:
            return
        self._source_url = value
        self.data_model.set_value("version_manager", "git_source_url", value)
        self.saveSettings()
        self.sourceChanged.emit()
        self.notifySuccess.emit("设置已保存", "版本管理源设置已保存")

    sourceUrl = Property(
        str, _get_source_url, _set_source_url, notify=sourceChanged
    )

    def _get_source_names(self):
        return [name for name, _url in SOURCE_CONFIGS]

    sourceNames = Property("QVariantList", _get_source_names, constant=True)

    def _get_source_index(self):
        for i, (_name, url) in enumerate(SOURCE_CONFIGS):
            if url == self._source_url:
                return i
        return 0

    sourceIndex = Property(int, _get_source_index, notify=sourceChanged)

    @Slot(int)
    def setSourceIndex(self, index):
        if 0 <= index < len(SOURCE_CONFIGS):
            self._set_source_url(SOURCE_CONFIGS[index][1])

    def _get_active_tab(self):
        return self._active_tab

    activeTab = Property(str, _get_active_tab, notify=activeTabChanged)

    def _get_status_text(self):
        return self._status_text

    statusText = Property(str, _get_status_text, notify=statusChanged)

    def _get_busy(self):
        return self._busy

    busy = Property(bool, _get_busy, notify=busyChanged)

    def _get_selected_index(self):
        return self._selected_index

    selectedIndex = Property(int, _get_selected_index, notify=selectedChanged)

    def _get_selected_name(self):
        if 0 <= self._selected_index < len(self._filtered):
            return self._filtered[self._selected_index].get("name", "")
        return ""

    selectedName = Property(str, _get_selected_name, notify=selectedChanged)

    def _get_version_model(self):
        return self.version_model

    versionModel = Property(QObject, _get_version_model, constant=True)

    # ==================== 设置读写 ====================
    @Slot()
    def loadSettings(self):
        try:
            if os.path.exists(self.settings_file):
                config = configparser.ConfigParser()
                config.read(self.settings_file, encoding="utf-8")
                self._proxy_enabled = config.getboolean(
                    "settings", "proxy_enabled", fallback=False
                )
                self._source_url = config.get(
                    "settings", "source_url", fallback=DEFAULT_SOURCE_URL
                )
                return
        except Exception as e:
            print(f"加载版本管理设置失败: {str(e)}")
        self._proxy_enabled = False
        self._source_url = self.data_model.get_value(
            "version_manager", "git_source_url", DEFAULT_SOURCE_URL
        )

    @Slot()
    def saveSettings(self):
        try:
            os.makedirs("starter", exist_ok=True)
            config = configparser.ConfigParser()
            if os.path.exists(self.settings_file):
                config.read(self.settings_file, encoding="utf-8")
            if not config.has_section("settings"):
                config.add_section("settings")
            config.set("settings", "proxy_enabled", str(self._proxy_enabled))
            config.set("settings", "source_url", self._source_url)
            config.set(
                "settings", "last_updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            with open(self.settings_file, "w", encoding="utf-8") as f:
                config.write(f)
        except Exception as e:
            print(f"保存版本管理设置失败: {str(e)}")

    # ==================== 路径与仓库状态 ====================
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

    def _set_status(self, text):
        if self._status_text != text:
            self._status_text = text
            self.statusChanged.emit()

    @Slot(result=bool)
    def checkRepoStatus(self):
        comfyui_path = self.get_comfyui_path()
        if not os.path.exists(comfyui_path):
            self._set_status("未找到ComfyUI文件夹")
            return False
        if not os.path.exists(os.path.join(comfyui_path, ".git")):
            self._set_status("不是Git仓库")
            return False
        try:
            self.repo = git.Repo(comfyui_path)
            if self.repo.head.is_detached:
                self._set_status("游离状态 (Detached HEAD)")
            else:
                self._set_status(f"分支: {self.repo.active_branch.name}")
            return True
        except git.exc.InvalidGitRepositoryError:
            self._set_status("无效的Git仓库")
        except git.exc.NoSuchPathError:
            self._set_status("路径不存在")
        except Exception as e:
            self._set_status(f"检查失败: {str(e)}")
        return False

    def _detect_initial_tab(self):
        if not self.repo:
            return
        try:
            current_commit = self.repo.head.commit.hexsha
            is_branch = any(
                branch.commit.hexsha == current_commit for branch in self.repo.branches
            )
            self._active_tab = "dev" if is_branch else "stable"
        except Exception as e:
            print(f"初始化选项卡失败: {str(e)}")

    # ==================== 加载 / 刷新 ====================
    @Slot()
    def loadInitialVersions(self):
        if os.path.exists(self.versions_file):
            self.loadVersionsFromFile()
        self.updateVersionList()

    @Slot()
    def refreshVersions(self):
        self._set_busy(True)
        if not self.checkRepoStatus():
            if os.path.exists(self.versions_file) and self.loadVersionsFromFile():
                self.notifySuccess.emit("加载成功", "已从本地文件加载版本信息")
            else:
                self.notifyError.emit("加载失败", "无法从本地文件加载版本信息")
            self._set_busy(False)
            return

        try:
            remote_url = self._source_url or DEFAULT_SOURCE_URL
            try:
                remote = self.repo.remote("origin")
                if remote.url != remote_url:
                    self.repo.delete_remote("origin")
                    self.repo.create_remote("origin", remote_url)
            except ValueError:
                self.repo.create_remote("origin", remote_url)

            self.notifyInfo.emit(
                "正在获取", "正在获取远程版本信息，可以切换到其他面板继续操作"
            )
            self._start_process(
                ["fetch", "--tags", "origin"], self._on_fetch_finished
            )
        except Exception as e:
            self._set_busy(False)
            self.notifyError.emit("错误", f"刷新版本失败: {str(e)}")

    def _start_process(self, args, callback):
        process = QProcess(self)
        process.setWorkingDirectory(self.get_comfyui_path())
        if self._proxy_enabled:
            env = QProcess.systemEnvironment()
            proxy_type = self.data_model.get_value("proxy", "proxy_type", "system")
            http_proxy = self.data_model.get_value("proxy", "http_proxy")
            proxy_port = self.data_model.get_value("proxy", "port")
            if str(proxy_type).lower() == "socks5":
                proxy_url = f"socks5://{http_proxy}:{proxy_port}"
            else:
                proxy_url = f"http://{http_proxy}:{proxy_port}"
            env.append(f"http_proxy={proxy_url}")
            env.append(f"https_proxy={proxy_url}")
            process.setEnvironment(env)

        self.process = process
        process.finished.connect(callback)
        process.errorOccurred.connect(self._on_process_error)
        process.start("git", args)

    def _on_process_error(self, error):
        self._set_busy(False)
        names = {
            QProcess.FailedToStart: "进程启动失败 - 可能是git命令不存在或无法执行",
            QProcess.Crashed: "进程崩溃",
            QProcess.Timedout: "进程超时",
            QProcess.WriteError: "写入进程时出错",
            QProcess.ReadError: "从进程读取时出错",
            QProcess.UnknownError: "未知错误",
        }
        print(f"进程错误: {names.get(error, '未知错误类型')}")

    def _on_fetch_finished(self, exit_code, exit_status):
        if exit_code != 0:
            error_output = ""
            if self.process:
                error_output = (
                    self.process.readAllStandardError().data().decode("utf-8", "ignore")
                )
            print(f"获取远程信息失败: {error_output}")
            self._set_busy(False)
            self.notifyError.emit("获取失败", "获取远程版本信息失败")
            return

        try:
            self.versions = self._collect_versions()
            self.versions.sort(key=lambda x: x["date"], reverse=True)
            self.saveVersionsToFile()
            self.updateVersionList()
        except Exception as e:
            print(f"解析版本信息失败: {str(e)}")
        finally:
            self._set_busy(False)

    def _collect_versions(self):
        versions = []
        current_commit = None
        try:
            current_commit = self.repo.head.commit.hexsha
        except Exception as e:
            print(f"获取当前HEAD提交ID失败: {str(e)}")

        # 远程分支
        try:
            remote = self.repo.remote("origin")
            for ref in remote.refs:
                if ref.name.startswith("origin/") and not ref.name.startswith(
                    "origin/tags/"
                ):
                    branch_name = ref.name.replace("origin/", "")
                    commit = ref.commit
                    message = commit.message.strip().split("\n")[0]
                    versions.append(
                        {
                            "id": commit.hexsha[:8],
                            "name": message,
                            "date": datetime.fromtimestamp(
                                commit.committed_date
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "ref": ref.name,
                            "type": "branch",
                            "message": message,
                            "branch": branch_name,
                        }
                    )
        except Exception as e:
            print(f"获取分支信息失败: {str(e)}")

        # master 分支最近提交
        try:
            if "origin/master" in self.repo.refs:
                commits = list(self.repo.iter_commits("origin/master", max_count=100))
            else:
                master_refs = [
                    ref for ref in self.repo.refs if "master" in ref.name.lower()
                ]
                commits = (
                    list(self.repo.iter_commits(master_refs[0].name, max_count=100))
                    if master_refs
                    else []
                )
            added_ids = [v["id"] for v in versions]
            for commit in commits:
                commit_id = commit.hexsha[:8]
                if commit_id in added_ids:
                    continue
                message = commit.message.strip().split("\n")[0]
                versions.append(
                    {
                        "id": commit_id,
                        "name": message,
                        "date": datetime.fromtimestamp(commit.committed_date).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "ref": "origin/master",
                        "type": "branch",
                        "message": message,
                        "branch": "master",
                    }
                )
                added_ids.append(commit_id)
        except Exception as e:
            print(f"获取master分支提交失败: {str(e)}")

        # 标签
        try:
            for tag in self.repo.tags:
                if not tag.name.startswith("v"):
                    continue
                try:
                    commit = tag.commit
                    versions.append(
                        {
                            "id": commit.hexsha[:8],
                            "name": tag.name,
                            "date": datetime.fromtimestamp(commit.committed_date).strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                            "ref": tag.name,
                            "type": "tag",
                        }
                    )
                except Exception as e:
                    print(f"解析标签 {tag.name} 失败: {str(e)}")
        except Exception as e:
            print(f"获取标签列表失败: {str(e)}")

        return versions

    @Slot()
    def updateVersionList(self):
        current_commit_short = None
        if self.repo is not None:
            try:
                current_commit_short = self.repo.head.commit.hexsha[:8]
            except Exception as e:
                print(f"获取当前HEAD提交ID失败: {str(e)}")

        if self._active_tab == "stable":
            filtered = [v for v in self.versions if v.get("type", "").lower() == "tag"]
        else:
            filtered = [
                v
                for v in self.versions
                if v.get("type", "").lower() == "branch"
                and (
                    v.get("name") == "master"
                    or "master" in str(v.get("ref", "")).lower()
                    or v.get("branch") == "master"
                    or v.get("name") == "--"
                )
            ]

        self._filtered = filtered
        rows = []
        for version in filtered:
            if self._active_tab == "dev":
                text = version.get("message", version.get("name", "--"))
            else:
                text = version.get("name", "--")
                if text == "--" and "message" in version:
                    text = f"-- ({version['message']})"
            rows.append(
                {
                    "commitId": version.get("id", ""),
                    "date": version.get("date", ""),
                    "text": text,
                    "isCurrent": bool(
                        current_commit_short
                        and version.get("id") == current_commit_short
                    ),
                }
            )

        self.version_model.set_rows(rows)
        self._selected_index = -1
        self.selectedChanged.emit()
        self.listReset.emit()

    @Slot(str)
    def setTab(self, key):
        if key not in ("stable", "dev") or self._active_tab == key:
            return
        self._active_tab = key
        self.activeTabChanged.emit()
        self.updateVersionList()

    @Slot(int)
    def setSelectedIndex(self, index):
        if self._selected_index == index:
            return
        self._selected_index = index
        self.selectedChanged.emit()

    @Slot(int)
    def switchVersion(self, index):
        if not (0 <= index < len(self._filtered)):
            self.notifyError.emit("错误", "请先选择一个版本")
            return
        version = self._filtered[index]
        self._set_busy(True)
        try:
            if version.get("type") == "branch":
                args = ["checkout", version["id"]]
            else:
                args = ["checkout", version["ref"]]
            self._start_process(args, self._on_checkout_finished)
        except Exception as e:
            self._set_busy(False)
            self.notifyError.emit("错误", f"切换版本失败: {str(e)}")

    def _on_checkout_finished(self, exit_code, exit_status):
        self._set_busy(False)
        if exit_code != 0:
            error_output = ""
            if self.process:
                error_output = (
                    self.process.readAllStandardError().data().decode("utf-8", "ignore")
                )
            self.notifyError.emit("错误", f"切换版本失败: {error_output}")
            return
        self.checkRepoStatus()
        self.updateVersionList()
        self.notifySuccess.emit("成功", "版本切换成功")

    @Slot(str)
    def openCommitUrl(self, commit_id):
        try:
            if not self.repo:
                return
            remote_url = self.repo.remote().url
            if remote_url.startswith("git@"):
                remote_url = remote_url.replace(":", "/").replace("git@", "https://")
            if remote_url.endswith(".git"):
                remote_url = remote_url[:-4]
            webbrowser.open(f"{remote_url}/commit/{commit_id}")
        except Exception as e:
            print(f"打开commit URL失败: {str(e)}")

    # ==================== 文件缓存 ====================
    def saveVersionsToFile(self):
        try:
            if not self.versions:
                return False
            config = configparser.ConfigParser()
            config.add_section("info")
            config.set("info", "update_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            config.set("info", "version_count", str(len(self.versions)))
            config.set("info", "source_url", self._source_url or "")
            for i, version in enumerate(self.versions):
                section = f"version_{i}"
                config.add_section(section)
                for key, value in version.items():
                    config.set(section, key, str(value))
            with open(self.versions_file, "w", encoding="utf-8") as f:
                config.write(f)
            return True
        except Exception as e:
            print(f"保存版本信息失败: {str(e)}")
            return False

    def loadVersionsFromFile(self):
        try:
            if not os.path.exists(self.versions_file):
                return False
            config = configparser.ConfigParser()
            config.read(self.versions_file, encoding="utf-8")
            if not config.has_section("info"):
                return False
            version_count = config.getint("info", "version_count")
            versions = []
            for i in range(version_count):
                section = f"version_{i}"
                if not config.has_section(section):
                    continue
                version = {}
                for key, value in config.items(section):
                    version[key] = value.lower() if key == "type" else value
                versions.append(version)
            self.versions = versions
            return True
        except Exception as e:
            print(f"加载版本信息失败: {str(e)}")
            return False

    # ==================== 内部方法 ====================
    def _set_busy(self, value):
        value = bool(value)
        if self._busy == value:
            return
        self._busy = value
        self.busyChanged.emit()
