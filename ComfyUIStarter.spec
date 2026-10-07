# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置。

PyInstaller 的 PySide6 钩子默认会把整个 qml 目录、所有 Qt 插件和全部 Qt 翻译
文件都打包进来（其中 Qt6WebEngineCore.dll 单个就约 190MB），而本程序只用到
QtQuick / QtQuick.Controls / QtQuick.Dialogs / QtSvg / QtNetwork 等，
所以这里在官方默认行为的基础上做「瘦身」，显式剔除用不到的 Qt 模块、翻译文件
以及无关的第三方包（numpy / PIL / qrcode）。
"""
from PyInstaller.utils.hooks import collect_all

datas = [('qml', 'qml'), ('icon.ico', '.')]
binaries = []
hiddenimports = []
tmp_ret = collect_all('prismqml')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# ---------------------------------------------------------------------------
# 1) 不需要的 Python 模块
# ---------------------------------------------------------------------------
excludes = [
    # 本程序未使用的 Qt 模块
    'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineQuick', 'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebView', 'PySide6.QtWebChannel', 'PySide6.QtWebSockets',
    'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtGraphs',
    'PySide6.QtQuick3D', 'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput',
    'PySide6.Qt3DLogic', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras',
    'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'PySide6.QtSpatialAudio',
    'PySide6.QtVirtualKeyboard', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
    'PySide6.QtDesigner', 'PySide6.QtDesignerComponents', 'PySide6.QtUiTools',
    'PySide6.QtScxml', 'PySide6.QtStateMachine', 'PySide6.QtRemoteObjects',
    'PySide6.QtSensors', 'PySide6.QtSerialPort', 'PySide6.QtBluetooth', 'PySide6.QtNfc',
    'PySide6.QtLocation', 'PySide6.QtPositioning', 'PySide6.QtTest', 'PySide6.QtHelp',
    'PySide6.QtTextToSpeech', 'PySide6.QtNetworkAuth', 'PySide6.QtHttpServer',
    'PySide6.QtOpenGLWidgets',
    # 与程序无关的第三方包（仅 PrismQML 的二维码等可选功能才会用到）
    'numpy', 'PIL', 'qrcode',
]

# ---------------------------------------------------------------------------
# 2) 需要从打包结果里剔除的 Qt 动态库 / QML 模块目录 / 翻译文件
# ---------------------------------------------------------------------------
_QT_DLL_DENY = (
    'Qt6WebEngine', 'Qt6WebView', 'Qt6WebChannel', 'Qt6WebSockets',
    'Qt6Charts', 'Qt6DataVisualization', 'Qt6Graphs', 'Qt6Quick3D', 'Qt63D',
    'Qt6LabsWavefrontMesh', 'Qt6Multimedia', 'Qt6SpatialAudio', 'Qt6VirtualKeyboard',
    'Qt6Pdf', 'Qt6Designer', 'Qt6UiTools', 'Qt6Scxml', 'Qt6StateMachine',
    'Qt6RemoteObjects', 'Qt6Sensors', 'Qt6SerialPort', 'Qt6SerialBus',
    'Qt6Bluetooth', 'Qt6Nfc', 'Qt6Location', 'Qt6Positioning', 'Qt6Test', 'Qt6Help',
    'Qt6TextToSpeech', 'Qt6NetworkAuth', 'Qt6HttpServer', 'Qt6OpenGLWidgets',
)
_QML_DIR_DENY = {
    'Qt3D', 'QtCharts', 'QtDataVisualization', 'QtGraphs', 'QtQuick3D',
    'QtLocation', 'QtMultimedia', 'QtPositioning', 'QtRemoteObjects', 'QtScxml',
    'QtSensors', 'QtTest', 'QtTextToSpeech', 'QtWebChannel', 'QtWebEngine',
    'QtWebSockets', 'QtWebView',
}
# Qt 自带的界面翻译只需要保留这些语言，其余全部丢弃
_KEEP_TRANSLATIONS = ('_en.qm', '_zh_CN.qm', '_zh_TW.qm')


def _should_drop(dest):
    parts = dest.replace('/', '\\').split('\\')
    if parts[0] != 'PySide6':
        return False
    # 翻译文件：只保留英文 / 简繁中文
    if len(parts) >= 2 and parts[1] == 'translations':
        return not dest.endswith(_KEEP_TRANSLATIONS)
    # QML 模块目录
    if len(parts) >= 3 and parts[1] == 'qml':
        return parts[2] in _QML_DIR_DENY
    # PySide6 顶层动态库 / 可执行文件
    name = parts[1] if len(parts) == 2 else parts[-1]
    return name.startswith(_QT_DLL_DENY)


a = Analysis(
    ['main_qml.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

# 从分析结果里剔除上面标记的 Qt 二进制与数据文件
a.binaries = [b for b in a.binaries if not _should_drop(b[0])]
a.datas = [d for d in a.datas if not _should_drop(d[0])]

pyz = PYZ(a.pure)

# bootloader 启动图：双击后由 PyInstaller 引导器在解压/导入阶段立即显示，
# 覆盖 Python/Qt 尚未起来的那几秒；Qt 窗口就绪后由程序调用 pyi_splash.close() 关闭。
splash = Splash(
    'splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=True,
    max_img_size=(800, 600),
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    splash,
    splash.binaries,
    [],
    name='ComfyUIStarterV0.7.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
