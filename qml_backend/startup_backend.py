import html
import os
import re
import subprocess
import sys
from datetime import datetime

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    Property,
    Qt,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QGuiApplication

from process_manager import ComfyUIProcessManager

# ANSI 颜色代码 → HTML 颜色（与旧版启动面板保持一致）
ANSI_COLOR_MAP = {
    "30": "#111111",  # black
    "31": "#BB0000",  # red
    "32": "#009900",  # green
    "33": "#FEB200",  # yellow
    "34": "#1919e8",  # blue
    "35": "#d020d0",  # magenta
    "36": "#00afaf",  # cyan
    "37": "#EEEEEE",  # white
    "90": "#808080",  # gray
    "91": "#FF6060",  # lightred
    "92": "#47d547",  # lightgreen
    "93": "#FEB201",  # lightyellow
    "94": "#6060FF",  # lightblue
    "95": "#e476e4",  # lightmagenta
    "96": "#83d0d0",  # lightcyan
    "97": "#EEEEEE",  # white
}

_ANSI_RE = re.compile(r"\x1b\[(\d+)m")


def _wrap_html(text, color):
    escaped = html.escape(text)
    if color:
        return f'<span style="color:{color}; font-weight:bold;">{escaped}</span>'
    return escaped


def _ansi_line_to_html(raw_line):
    """把单行文本中的 ANSI 颜色代码转换为 HTML。"""
    if "\x1b" not in raw_line:
        return html.escape(raw_line)

    parts = []
    pos = 0
    color = None
    for match in _ANSI_RE.finditer(raw_line):
        chunk = raw_line[pos:match.start()]
        if chunk:
            parts.append(_wrap_html(chunk, color))
        code = match.group(1)
        if code == "1":
            # 粗体标记，保持当前颜色
            pass
        elif code == "0" or code not in ANSI_COLOR_MAP:
            color = None
        else:
            color = ANSI_COLOR_MAP[code]
        pos = match.end()

    tail = raw_line[pos:]
    if tail:
        parts.append(_wrap_html(tail, color))
    return "".join(parts)


def _strip_ansi(raw_line):
    return _ANSI_RE.sub("", raw_line)


class LogModel(QAbstractListModel):
    """运行日志模型，每行保存原始文本与 HTML（带颜色）两套内容。"""

    RichTextRole = Qt.UserRole + 1
    PlainTextRole = Qt.UserRole + 2

    MAX_LINES = 10000
    TRIM_LINES = 1000

    def __init__(self, parent=None):
        super().__init__(parent)
        # 每行结构：[原始文本(含ANSI), HTML文本]
        self._rows = [["", ""]]

    def roleNames(self):
        return {
            self.RichTextRole: b"richText",
            self.PlainTextRole: b"plainText",
        }

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return ""
        raw, rich = self._rows[index.row()]
        if role == self.RichTextRole:
            return rich
        if role == self.PlainTextRole:
            return _strip_ansi(raw)
        return ""

    # ==================== 写入接口 ====================
    def feed(self, text):
        """追加一段文本（可能跨多行）。"""
        if not self._rows:
            self._rows.append(["", ""])
        for idx, part in enumerate(text.split("\n")):
            if idx > 0:
                self._append_empty_row()
            if part:
                self._append_to_last(part)

    def drop_last_row_if_not_empty(self):
        """模拟 \\r：清空最后一行（仅在非空时），保留该行占位。"""
        if not self._rows:
            self._rows.append(["", ""])
            return
        row = len(self._rows) - 1
        if self._rows[row][0] == "":
            return
        self._rows[row] = ["", ""]
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [self.RichTextRole, self.PlainTextRole])

    def clear_all(self):
        self.beginResetModel()
        self._rows = [["", ""]]
        self.endResetModel()

    def full_text(self):
        return "\n".join(_strip_ansi(raw) for raw, _ in self._rows)

    # ==================== 内部方法 ====================
    def _append_empty_row(self):
        row = len(self._rows)
        self.beginInsertRows(QModelIndex(), row, row)
        self._rows.append(["", ""])
        self.endInsertRows()
        self._trim()

    def _append_to_last(self, part):
        row = len(self._rows) - 1
        raw = self._rows[row][0] + part
        self._rows[row] = [raw, _ansi_line_to_html(raw)]
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [self.RichTextRole, self.PlainTextRole])

    def _trim(self):
        if len(self._rows) >= self.MAX_LINES:
            self.beginRemoveRows(QModelIndex(), 0, self.TRIM_LINES - 1)
            del self._rows[: self.TRIM_LINES]
            self.endRemoveRows()


class StartupBackend(QObject):
    """启动页后端：进程控制、日志、文件夹快捷访问。"""

    isRunningChanged = Signal()
    commandPreviewChanged = Signal()
    startEnabledChanged = Signal()
    pythonMissingChanged = Signal()

    notifySuccess = Signal(str, str)  # title, content
    notifyError = Signal(str, str)
    notifyInfo = Signal(str, str)

    def __init__(self, data_model, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.log_model = LogModel(self)

        self._python_missing_message = ""
        self.process_manager = self._create_process_manager()
        self._refresh_python_state()
        if self._python_missing_message:
            self.log_model.feed(self._python_missing_message + "\n")

    # ==================== 属性 ====================
    def _get_is_running(self):
        return self.process_manager.is_running() if self.process_manager else False

    isRunning = Property(bool, _get_is_running, notify=isRunningChanged)

    def _get_command_preview(self):
        return self.process_manager.get_command_string() if self.process_manager else ""

    commandPreview = Property(
        str, _get_command_preview, notify=commandPreviewChanged
    )

    def _get_start_enabled(self):
        return self._python_missing_message == ""

    startEnabled = Property(bool, _get_start_enabled, notify=startEnabledChanged)

    def _get_python_missing_message(self):
        return self._python_missing_message

    pythonMissingMessage = Property(
        str, _get_python_missing_message, notify=pythonMissingChanged
    )

    def _get_log_model(self):
        return self.log_model

    logModel = Property(QObject, _get_log_model, constant=True)

    # ==================== 进程控制 ====================
    @Slot()
    def toggleComfyUI(self):
        if self.process_manager.is_running():
            self.stopComfyUI()
        else:
            self.startComfyUI()

    @Slot()
    def startComfyUI(self):
        if not self._get_start_enabled():
            self.notifyError.emit("无法启动", self._python_missing_message)
            return
        self.process_manager.start_comfyui()
        self.isRunningChanged.emit()

    @Slot()
    def stopComfyUI(self):
        self.process_manager.stop_comfyui()
        self.isRunningChanged.emit()

    @Slot()
    def restartComfyUI(self):
        self.process_manager.restart_comfyui()
        self.isRunningChanged.emit()

    @Slot()
    def forceStopAllPython(self):
        """强行终止系统中所有 python.exe 进程。"""
        self.log_model.feed("正在查找并终止所有Python.exe进程...\n")
        try:
            result = subprocess.run(
                ["taskkill", "/F", "/IM", "python.exe"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True,
            )
            if result.returncode == 0:
                self.log_model.feed("已成功终止所有Python.exe进程\n")
                # 复位界面状态：结束启动器持有的 cmd.exe 进程，使 isRunning 回到 False
                try:
                    if self.process_manager.is_running():
                        self.process_manager.force_kill()
                        self.process_manager.wait_for_finished(3000)
                except Exception as e:
                    print(f"复位进程状态失败: {str(e)}")
                self.isRunningChanged.emit()
            else:
                self.log_model.feed(f"终止进程时出现错误: {result.stderr}\n")
        except Exception as e:
            self.log_model.feed(f"执行命令时出错: {str(e)}\n")

    @Slot()
    def refreshCommandPreview(self):
        self.commandPreviewChanged.emit()

    @Slot()
    def onSettingsChanged(self):
        """设置保存后重建进程管理器并重新连接信号。"""
        self.process_manager = self._create_process_manager()
        self._refresh_python_state()
        self.commandPreviewChanged.emit()
        self.isRunningChanged.emit()

    # ==================== 日志 ====================
    @Slot()
    def clearLog(self):
        self.log_model.clear_all()
        self.notifySuccess.emit("清空成功", "日志内容已清空")

    @Slot()
    def copyLog(self):
        QGuiApplication.clipboard().setText(self.log_model.full_text())
        self.notifySuccess.emit("复制成功", "日志内容已复制到剪贴板")

    @Slot(str)
    def saveLogToFile(self, file_url):
        path = QUrl(file_url).toLocalFile() if file_url else ""
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log_model.full_text())
            self.notifySuccess.emit("保存成功", f"日志已保存到: {path}")
        except Exception as e:
            self.notifyError.emit("保存失败", f"保存日志时出错: {str(e)}")

    @Slot(result=str)
    def defaultLogFileName(self):
        return f"ComfyUI_Log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    # ==================== 文件夹快捷访问 ====================
    @Slot()
    def openRootFolder(self):
        self._open_folder(self.get_comfyui_root_folder())

    @Slot()
    def openCustomNodesFolder(self):
        self._open_folder(os.path.join(self.get_comfyui_root_folder(), "custom_nodes"))

    @Slot()
    def openModelsFolder(self):
        self._open_folder(os.path.join(self.get_comfyui_root_folder(), "models"))

    @Slot()
    def openWorkflowsFolder(self):
        self._open_folder(
            os.path.join(self.get_comfyui_root_folder(), "user", "default", "workflows")
        )

    @Slot()
    def openInputFolder(self):
        if self.data_model.get_bool("advanced", "input_dir_enabled"):
            custom = self.data_model.get_value("advanced", "input_dir")
            if custom:
                self._open_folder(custom)
                return
        self._open_folder(os.path.join(self.get_comfyui_root_folder(), "input"))

    @Slot()
    def openOutputFolder(self):
        if self.data_model.get_bool("advanced", "output_dir_enabled"):
            custom = self.data_model.get_value("advanced", "output_dir")
            if custom:
                self._open_folder(custom)
                return
        self._open_folder(os.path.join(self.get_comfyui_root_folder(), "output"))

    def get_comfyui_root_folder(self):
        path = self.process_manager.get_comfyui_path() or os.path.join("ComfyUI")
        return os.path.abspath(path)

    def _open_folder(self, folder_path):
        try:
            folder_path = os.path.normpath(folder_path)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path, exist_ok=True)
                self.log_model.feed(f"创建文件夹: {folder_path}\n")

            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder_path])
            else:
                subprocess.run(["xdg-open", folder_path])

            self.log_model.feed(f"打开文件夹: {folder_path}\n")
        except Exception as e:
            self.log_model.feed(f"打开文件夹失败: {str(e)}\n")

    # ==================== 内部方法 ====================
    def _create_process_manager(self):
        manager = ComfyUIProcessManager(self.data_model)
        manager.log_signal.connect(self._on_log)
        manager.status_changed.connect(self._on_status_changed)
        manager.error_occurred.connect(self._on_error)
        return manager

    def _on_log(self, text):
        if "\r" in text:
            self.log_model.drop_last_row_if_not_empty()
            text = text.replace("\r", "")
        self.log_model.feed(text)

    def _on_status_changed(self, is_running):
        print(f"启动面板接收到状态变化信号: {is_running}")
        self.isRunningChanged.emit()

    def _on_error(self, error_msg):
        self.log_model.feed(f"\n错误: {error_msg}\n")

    def _refresh_python_state(self):
        python_path = self.process_manager.get_python_exe_path()
        if not python_path or not os.path.exists(python_path):
            self._python_missing_message = f"Python解释器路径不存在: {python_path}"
        else:
            self._python_missing_message = ""
        self.pythonMissingChanged.emit()
        self.startEnabledChanged.emit()
