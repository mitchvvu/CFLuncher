import QtQuick
import PrismQML
import QtQuick as QQ

Item {
    id: root
    property var backend

    readonly property color accentTeal: "#00a7b3"

    Connections {
        target: backend

        function onNotifySuccess(title, content) {
            NotificationManager.infoBar.success(root, title, content)
        }
        function onNotifyError(title, content) {
            NotificationManager.infoBar.error(root, title, content)
        }
        function onNotifyInfo(title, content) {
            NotificationManager.infoBar.info(root, title, content)
        }
        function onListReset() {
            versionList.currentIndex = -1
        }
        function onActiveTabChanged() {
            tabControl.currentIndex = backend.activeTab === "dev" ? 1 : 0
        }
    }

    Component.onCompleted: {
        if (backend)
            backend.loadInitialVersions()
    }

    MessageBox {
        id: switchDialog
        title: "确认切换版本"
        content: "确定要切换到以下版本吗？\n\n" + backend.selectedName
                 + "\n\n注意: 切换版本会丢失所有未提交的更改。"
        confirmText: "确定"
        cancelText: "取消"
        onAccepted: backend.switchVersion(backend.selectedIndex)
    }

    PageHeader {
        id: header
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        currentText: "版本管理"
    }

    ScrollArea {
        id: scroll
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        padding: 16

        Column {
            width: scroll.width - scroll.padding * 2
            spacing: 20

            // ==================== 版本管理设置 ====================
            Card {
                width: parent.width
                autoHeight: true

                Column {
                    width: parent.width
                    spacing: 12

                    Label {
                        type: Enums.label.type_body_strong
                        text: "ComfyUI 版本管理"
                    }

                    SwitchRow {
                        text: "启用代理"
                        checked: backend.proxyEnabled
                        function onToggled(checked) {
                            backend.proxyEnabled = checked
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        Label {
                            height: 32
                            verticalAlignment: Text.AlignVCenter
                            text: "源选择:"
                        }

                        ComboBox {
                            width: 260
                            height: 32
                            model: backend.sourceNames
                            currentIndex: backend.sourceIndex
                            function onActivated(index) {
                                backend.setSourceIndex(index)
                            }
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        Label {
                            height: 32
                            verticalAlignment: Text.AlignVCenter
                            text: "当前源:"
                        }

                        Label {
                            width: parent.width - refreshButton.width - 100
                            height: 32
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                            type: Enums.label.type_body_strong
                            customTextColor: root.accentTeal
                            text: backend.sourceUrl
                        }

                        Button {
                            id: refreshButton
                            height: 32
                            icon: "ArrowSync"
                            text: "刷新"
                            enabled: !backend.busy
                            onClicked: backend.refreshVersions()
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        Label {
                            height: 32
                            verticalAlignment: Text.AlignVCenter
                            text: "ComfyUI状态:"
                        }

                        Label {
                            height: 32
                            verticalAlignment: Text.AlignVCenter
                            type: Enums.label.type_body_strong
                            customTextColor: root.accentTeal
                            text: backend.statusText
                        }
                    }
                }
            }

            // ==================== 可用版本 ====================
            Card {
                width: parent.width
                autoHeight: true

                Column {
                    width: parent.width
                    spacing: 12

                    Label {
                        type: Enums.label.type_body_strong
                        text: "可用版本"
                    }

                    SegmentedControl {
                        id: tabControl
                        items: [
                            { key: "stable", text: "稳定版" },
                            { key: "dev", text: "开发版" }
                        ]
                        currentIndex: backend.activeTab === "dev" ? 1 : 0
                        function onItemClicked(index, byUser) {
                            backend.setTab(tabControl.items[index].key)
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 605
                        radius: 5
                        color: Enums.surfaceColor
                        border.color: Enums.borderColor
                        border.width: 1
                        clip: true

                        QQ.ListView {
                            id: versionList
                            anchors.fill: parent
                            anchors.margins: 2
                            clip: true
                            model: backend.versionModel
                            spacing: 1

                            delegate: Rectangle {
                                required property int index
                                required property string commitId
                                required property string date
                                required property string text
                                required property bool isCurrent

                                width: versionList.width
                                height: 55
                                color: index === versionList.currentIndex
                                       ? Qt.rgba(Enums.accentColor.r, Enums.accentColor.g, Enums.accentColor.b, 0.18)
                                       : (rowHover.hovered ? Enums.hoverColor : "transparent")

                                HoverHandler {
                                    id: rowHover
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        versionList.currentIndex = index
                                        backend.setSelectedIndex(index)
                                    }
                                }

                                Rectangle {
                                    width: 3
                                    height: parent.height - 12
                                    anchors.left: parent.left
                                    anchors.leftMargin: 4
                                    anchors.verticalCenter: parent.verticalCenter
                                    radius: 1.5
                                    visible: index === versionList.currentIndex
                                    color: Enums.accentColor
                                }

                                Row {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 14
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 0

                                    Label {
                                        width: 150
                                        height: 55
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                        type: Enums.label.type_body_strong
                                        customTextColor: root.accentTeal
                                        text: "Commit: " + commitId

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: backend.openCommitUrl(commitId)
                                        }
                                    }

                                    Label {
                                        width: 180
                                        height: 55
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                        type: Enums.label.type_caption
                                        text: date
                                    }

                                    Label {
                                        width: versionList.width - 150 - 180 - 90
                                        height: 55
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                        text: text
                                    }

                                    Label {
                                        height: 55
                                        verticalAlignment: Text.AlignVCenter
                                        type: Enums.label.type_body_strong
                                        customTextColor: Enums.accentColor
                                        visible: isCurrent
                                        text: "[当前]"
                                    }
                                }
                            }
                        }

                        Label {
                            anchors.centerIn: parent
                            visible: versionList.count === 0
                            type: Enums.label.type_caption
                            text: backend.busy ? "正在获取版本信息..." : "暂无版本信息，请点击刷新"
                        }
                    }

                    Button {
                        width: parent.width
                        height: 40
                        style: Enums.button.style_primary
                        text: backend.busy ? "处理中..." : "切换版本"
                        enabled: !backend.busy && backend.selectedIndex >= 0
                        onClicked: switchDialog.open()
                    }
                }
            }
        }
    }
}
