"""QML 页面后端（PrismQML 版）。

每个 QObject 子类对应一个 QML 页面的 backend，QML 根对象通过
`property var backend` 接收该对象并调用其 Slot / 绑定其 Property。
"""
