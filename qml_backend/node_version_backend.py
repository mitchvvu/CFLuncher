import configparser
import os
import time

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


class NodeVersionListModel(QAbstractListModel):
    """节点版本列表模型。"""

    NameRole = Qt.UserRole + 1
    MessageRole = Qt.UserRole + 2
    CommitRole = Qt.UserRole + 3
    DateTimeRole = Qt.UserRole + 4
    IsCurrentRole = Qt.UserRole + 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []

    def roleNames(self):
        return {
            self.NameRole: b"name",
            self.MessageRole: b"message",
            self.CommitRole: b"commitShort",
            self.DateTimeRole: b"dateTime",
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
        if role == self.NameRole:
            return row["name"]
        if role == self.MessageRole:
            return row["message"]
        if role == self.CommitRole:
            return row["commitShort"]
        if role == self.DateTimeRole:
            return row["dateTime"]
        if role == self.IsCurrentRole:
            return row["isCurrent"]
        return ""

    def set_rows(self, rows):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()


class NodeVersionBackend(QObject):
    """单个自定义节点的版本管理后端。"""

    notifySuccess = Signal(str, str)
    notifyError = Signal(str, str)
    notifyInfo = Signal(str, str)

    nodeNameChanged = Signal()
    repoPathChanged = Signal()
    proxyEnabledChanged = Signal()
    mainBranchOnlyChanged = Signal()
    statusChanged = Signal()
    busyChanged = Signal()
    selectedChanged = Signal()
    listReset = Signal()
    requestClose = Signal()

    def __init__(self, node_name, node_path, parent=None):
        super().__init__(parent)
        self.node_name = node_name
        self._node_path = node_path
        self.settings_file = os.path.join("starter", "nodes.ini")

        self.repo = None
        self.process = None
        self.versions = []
        self._filtered = []

        self._proxy_enabled = False
        self._main_branch_only = True
        self._status_text = "未检测"
        self._busy = False
        self._selected_index = -1

        self.version_model = NodeVersionListModel(self)

        self.loadSettings()
        self.checkRepoStatus()

    # ==================== 属性 ====================
    def _get_node_name(self):
        return self.node_name

    nodeName = Property(str, _get_node_name, notify=nodeNameChanged)

    def _get_repo_path(self):
        return self._node_path

    repoPath = Property(str, _get_repo_path, notify=repoPathChanged)

    def _get_proxy_enabled(self):
        return self._proxy_enabled

    def _set_proxy_enabled(self, value):
        value = bool(value)
        if self._proxy_enabled == value:
            return
        self._proxy_enabled = value
        self.saveProxySettings()
        self.proxyEnabledChanged.emit()

    proxyEnabled = Property(
        bool, _get_proxy_enabled, _set_proxy_enabled, notify=proxyEnabledChanged
    )

    def _get_main_branch_only(self):
        return self._main_branch_only

    def _set_main_branch_only(self, value):
        value = bool(value)
        if self._main_branch_only == value:
            return
        self._main_branch_only = value
        self.mainBranchOnlyChanged.emit()
        self.updateVersionList()

    mainBranchOnly = Property(
        bool,
        _get_main_branch_only,
        _set_main_branch_only,
        notify=mainBranchOnlyChanged,
    )

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

    # ==================== 设置 ====================
    @Slot()
    def loadSettings(self):
        try:
            if os.path.exists(self.settings_file):
                config = configparser.ConfigParser()
                config.read(self.settings_file, encoding="utf-8")
                if config.has_section("git"):
                    self._proxy_enabled = config.getboolean(
                        "git", "proxy_enabled", fallback=False
                    )
        except Exception as e:
            print(f"加载节点代理设置失败: {str(e)}")

    @Slot()
    def saveProxySettings(self):
        try:
            os.makedirs("starter", exist_ok=True)
            config = configparser.ConfigParser()
            if os.path.exists(self.settings_file):
                config.read(self.settings_file, encoding="utf-8")
            if not config.has_section("git"):
                config.add_section("git")
            config.set("git", "proxy_enabled", str(self._proxy_enabled))
            with open(self.settings_file, "w", encoding="utf-8") as f:
                config.write(f)
        except Exception as e:
            print(f"保存节点代理设置失败: {str(e)}")

    # ==================== 仓库状态 ====================
    def _set_status(self, text):
        if self._status_text != text:
            self._status_text = text
            self.statusChanged.emit()

    @Slot(result=bool)
    def checkRepoStatus(self):
        if not os.path.exists(self._node_path):
            self._set_status("节点路径不存在")
            return False
        if not os.path.exists(os.path.join(self._node_path, ".git")):
            self._set_status("不是Git仓库")
            return False
        try:
            self.repo = git.Repo(self._node_path)
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

    # ==================== 版本加载 / 刷新 ====================
    @Slot()
    def loadInitialVersions(self):
        self.updateVersionList()

    @Slot()
    def refreshVersions(self):
        self._set_busy(True)
        if not self.checkRepoStatus():
            self._set_busy(False)
            self.notifyError.emit("错误", "无法获取版本信息: 仓库状态检查失败")
            return

        try:
            self.notifyInfo.emit("正在获取", "正在获取远程版本信息")
            self._start_process(["fetch", "--tags", "origin"], self._on_fetch_finished)
        except Exception as e:
            self._set_busy(False)
            self.notifyError.emit("错误", f"刷新版本失败: {str(e)}")

    def _proxy_env(self):
        if not self._proxy_enabled:
            return None
        http_proxy = os.environ.get("http_proxy", "")
        https_proxy = os.environ.get("https_proxy", "")
        if not http_proxy and not https_proxy:
            return None
        env = QProcess.systemEnvironment()
        if http_proxy:
            env.append(f"http_proxy={http_proxy}")
        if https_proxy:
            env.append(f"https_proxy={https_proxy}")
        return env

    def _start_process(self, args, callback):
        process = QProcess(self)
        process.setWorkingDirectory(self._node_path)
        env = self._proxy_env()
        if env is not None:
            process.setEnvironment(env)
        self.process = process
        process.finished.connect(callback)
        process.errorOccurred.connect(self._on_process_error)
        process.start("git", args)

    def _on_process_error(self, error):
        self._set_busy(False)
        print(f"节点进程错误: {error}")

    def _on_fetch_finished(self, exit_code, exit_status):
        if exit_code != 0:
            error_output = ""
            if self.process:
                error_output = (
                    self.process.readAllStandardError().data().decode("utf-8", "ignore")
                )
            self._set_busy(False)
            self.notifyError.emit("错误", f"获取远程信息失败: {error_output}")
            return

        try:
            self.versions = self._collect_versions()
            self.versions.sort(
                key=lambda x: (x["date"], x["time"]), reverse=True
            )
            self.updateVersionList()
            self.notifySuccess.emit("获取成功", f"已获取 {len(self.versions)} 个版本信息")
        except Exception as e:
            print(f"解析版本列表失败: {str(e)}")
            self.notifyError.emit("错误", f"解析版本列表失败: {str(e)}")
        finally:
            self._set_busy(False)

    def _collect_versions(self):
        versions = []
        current_commit = None
        try:
            current_commit = self.repo.head.commit.hexsha
        except Exception as e:
            print(f"获取当前HEAD提交ID失败: {str(e)}")

        for tag in self.repo.tags:
            try:
                commit = tag.commit
                versions.append(
                    {
                        "type": "tag",
                        "name": tag.name,
                        "date": time.strftime(
                            "%Y-%m-%d", time.gmtime(commit.committed_date)
                        ),
                        "time": time.strftime(
                            "%H:%M:%S", time.gmtime(commit.committed_date)
                        ),
                        "commit": commit.hexsha,
                        "commit_short": commit.hexsha[:8],
                        "is_current": commit.hexsha == current_commit,
                        "message": commit.message.strip(),
                    }
                )
            except Exception as e:
                print(f"解析标签 {tag.name} 失败: {str(e)}")

        local_branch_names = []
        for branch in self.repo.branches:
            try:
                commit = branch.commit
                local_branch_names.append(branch.name)
                versions.append(
                    {
                        "type": "branch",
                        "name": branch.name,
                        "date": time.strftime(
                            "%Y-%m-%d", time.gmtime(commit.committed_date)
                        ),
                        "time": time.strftime(
                            "%H:%M:%S", time.gmtime(commit.committed_date)
                        ),
                        "commit": commit.hexsha,
                        "commit_short": commit.hexsha[:8],
                        "is_current": commit.hexsha == current_commit,
                        "message": commit.message.strip(),
                    }
                )
            except Exception as e:
                print(f"解析分支 {branch.name} 失败: {str(e)}")

        try:
            for ref in self.repo.remotes.origin.refs:
                if ref.name == "origin/HEAD":
                    continue
                branch_name = ref.name.replace("origin/", "")
                if branch_name in local_branch_names:
                    continue
                commit = ref.commit
                versions.append(
                    {
                        "type": "branch",
                        "name": branch_name,
                        "date": time.strftime(
                            "%Y-%m-%d", time.gmtime(commit.committed_date)
                        ),
                        "time": time.strftime(
                            "%H:%M:%S", time.gmtime(commit.committed_date)
                        ),
                        "commit": commit.hexsha,
                        "commit_short": commit.hexsha[:8],
                        "is_current": commit.hexsha == current_commit,
                        "message": commit.message.strip(),
                        "ref": ref.name,
                    }
                )
        except Exception as e:
            print(f"获取远程分支失败: {str(e)}")

        return versions

    @Slot()
    def updateVersionList(self):
        current_commit_short = None
        if self.repo is not None:
            try:
                current_commit_short = self.repo.head.commit.hexsha[:8]
            except Exception as e:
                print(f"获取当前HEAD提交ID失败: {str(e)}")

        main_branches = ["main", "master"]
        filtered = []
        for version in self.versions:
            if (
                self._main_branch_only
                and version["type"] == "branch"
                and version["name"] not in main_branches
            ):
                continue
            filtered.append(version)

        self._filtered = filtered
        rows = []
        for version in filtered:
            message = version.get("message", "").split("\n")[0]
            rows.append(
                {
                    "name": version.get("name", ""),
                    "message": message,
                    "commitShort": version.get("commit_short", ""),
                    "dateTime": f"{version.get('date', '')} {version.get('time', '')}",
                    "isCurrent": bool(
                        version.get("is_current", False)
                        or version.get("commit_short") == current_commit_short
                    ),
                }
            )

        self.version_model.set_rows(rows)
        self._selected_index = -1
        self.selectedChanged.emit()
        self.listReset.emit()

    @Slot(int)
    def setSelectedIndex(self, index):
        if self._selected_index == index:
            return
        self._selected_index = index
        self.selectedChanged.emit()

    @Slot(int)
    def switchVersion(self, index):
        if not (0 <= index < len(self._filtered)):
            self.notifyError.emit("提示", "请先选择一个版本")
            return
        version = self._filtered[index]
        if version.get("is_current", False):
            self.notifyError.emit("提示", "已经是当前版本，无需切换")
            return

        self._set_busy(True)
        self.saveProxySettings()
        try:
            if version.get("type") == "tag":
                args = ["checkout", "tags/" + version["name"]]
            elif "ref" in version:
                args = ["checkout", "-b", version["name"], version["ref"]]
            else:
                args = ["checkout", version["name"]]
            self._start_process(args, self._on_switch_finished)
        except Exception as e:
            self._set_busy(False)
            self.notifyError.emit("错误", f"切换版本失败: {str(e)}")

    def _on_switch_finished(self, exit_code, exit_status):
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
        self.updateNodesListIni()
        self.notifySuccess.emit("切换成功", "节点版本切换成功")
        self.requestClose.emit()

    def updateNodesListIni(self):
        """把当前节点的更新标记重置为 False。"""
        try:
            nodes_list_ini = os.path.join("starter", "nodes_list.ini")
            if not os.path.exists(nodes_list_ini):
                return
            config = configparser.ConfigParser()
            config.read(nodes_list_ini, encoding="utf-8")
            if not config.has_section("update_info"):
                config.add_section("update_info")
            config.set("update_info", f"{self.node_name}_has_update", "False")
            with open(nodes_list_ini, "w", encoding="utf-8") as f:
                config.write(f)
        except Exception as e:
            print(f"更新节点列表文件失败: {str(e)}")

    def _set_busy(self, value):
        value = bool(value)
        if self._busy == value:
            return
        self._busy = value
        self.busyChanged.emit()
