import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt, QObject, Slot, Signal, Property
from prismqml import App, AsyncQmlPage, setTheme, Theme

App.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)


class Backend(QObject):
    messageChanged = Signal()

    def __init__(self):
        super().__init__()
        self._message = "就绪"

    def _get_message(self):
        return self._message

    message = Property(str, _get_message, notify=messageChanged)

    @Slot()
    def ping(self):
        print("PING FROM QML")
        self._message = "已点击"
        self.messageChanged.emit()


app = App(
    sys.argv,
    window_width=520,
    window_height=420,
    persist_appearance=False,
    auto_update_slot_redirect=False,
)
setTheme(Theme.AUTO)

window = app.create_window()
window.setSplashEnabled(False)
window.setWindowTitle("Smoke")

qml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml", "Smoke.qml")
page = AsyncQmlPage(qml_path, backend=Backend())
window.addPage(page, "Play", "启动")
window.show()

sys.exit(app.exec())
