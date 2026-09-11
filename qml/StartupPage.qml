import QtQuick
import QtQuick.Dialogs
import PrismQML

Item {
    id: root
    property var backend

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
    }

    MessageBox {
        id: forceStopDialog
        title: "警告"
        content: "强行停止会终止系统中所有Python.exe进程，慎用！！！"
        confirmText: "确定"
        cancelText: "取消"
        onAccepted: backend.forceStopAllPython()
    }

    FileDialog {
        id: saveLogDialog
        title: "保存日志文件"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "txt"
        nameFilters: ["文本文件 (*.txt)", "所有文件 (*)"]
        acceptLabel: "保存"
        onAccepted: backend.saveLogToFile(selectedFile.toString())
    }

    Column {
        id: pageColumn
        anchors.fill: parent
        anchors.margins: 10
        spacing: 20

        // ==================== ComfyUI 控制 ====================
        Card {
            width: parent.width
            autoHeight: true

            Column {
                width: parent.width
                spacing: 16

                Label {
                    type: Enums.label.type_body_strong
                    text: "ComfyUI 控制"
                }

                Row {
                    id: controlRow
                    width: parent.width
                    spacing: 10

                    Button {
                        id: startButton
                        width: Math.round(controlRow.width * 0.55)
                        height: 50
                        style: Enums.button.style_primary
                        icon: "Power"
                        text: backend.isRunning ? "正在运行..." : "启动 ComfyUI"
                        enabled: backend.startEnabled && !backend.isRunning
                        onClicked: backend.toggleComfyUI()
                    }

                    Button {
                        width: Math.round((controlRow.width - startButton.width - 30) / 3)
                        height: 50
                        text: "重启"
                        enabled: backend.isRunning
                        onClicked: backend.restartComfyUI()
                    }

                    Button {
                        width: Math.round((controlRow.width - startButton.width - 30) / 3)
                        height: 50
                        text: "停止"
                        enabled: backend.isRunning
                        onClicked: backend.stopComfyUI()
                    }

                    Button {
                        width: Math.round((controlRow.width - startButton.width - 30) / 3)
                        height: 50
                        text: "强行停止"
                        onClicked: forceStopDialog.open()
                    }
                }

                Label {
                    width: parent.width
                    visible: !backend.startEnabled
                    type: Enums.label.type_caption
                    customTextColor: "#BB0000"
                    text: backend.pythonMissingMessage
                    wrapMode: Text.WordWrap
                }
            }
        }

        // ==================== 文件夹快捷访问 ====================
        Card {
            width: parent.width
            autoHeight: true

            Column {
                width: parent.width
                spacing: 16

                Label {
                    type: Enums.label.type_body_strong
                    text: "文件夹快捷访问"
                }

                Grid {
                    width: parent.width
                    columns: 3
                    spacing: 10

                    Button {
                        width: Math.round((parent.width - 20) / 3)
                        icon: "Folder"
                        text: "根目录"
                        onClicked: backend.openRootFolder()
                    }
                    Button {
                        width: Math.round((parent.width - 20) / 3)
                        icon: "Folder"
                        text: "节点目录"
                        onClicked: backend.openCustomNodesFolder()
                    }
                    Button {
                        width: Math.round((parent.width - 20) / 3)
                        icon: "Folder"
                        text: "模型目录"
                        onClicked: backend.openModelsFolder()
                    }
                    Button {
                        width: Math.round((parent.width - 20) / 3)
                        icon: "Folder"
                        text: "用户工作流"
                        onClicked: backend.openWorkflowsFolder()
                    }
                    Button {
                        width: Math.round((parent.width - 20) / 3)
                        icon: "Folder"
                        text: "输入文件夹"
                        onClicked: backend.openInputFolder()
                    }
                    Button {
                        width: Math.round((parent.width - 20) / 3)
                        icon: "Folder"
                        text: "输出文件夹"
                        onClicked: backend.openOutputFolder()
                    }
                }
            }
        }

        // ==================== 运行日志 ====================
        Card {
            width: parent.width
            autoHeight: true

            Column {
                width: parent.width
                spacing: 12

                Label {
                    type: Enums.label.type_body_strong
                    text: "运行日志"
                }

                Rectangle {
                    width: parent.width
                    height: 320
                    radius: 5
                    color: Enums.surfaceColor
                    border.color: Enums.borderColor
                    border.width: 1
                    clip: true

                    ListView {
                        id: logView
                        anchors.fill: parent
                        anchors.margins: 6
                        clip: true
                        model: backend.logModel
                        onCountChanged: positionViewAtEnd()

                        delegate: Text {
                            width: logView.width
                            text: model.richText
                            textFormat: Text.RichText
                            wrapMode: Text.NoWrap
                            font.family: Enums.fontFamily
                            font.pixelSize: 12
                            color: Enums.textColor.primary
                        }
                    }

                    Connections {
                        target: backend.logModel
                        function onDataChanged() { logView.positionViewAtEnd() }
                    }

                    Label {
                        anchors.centerIn: parent
                        visible: logView.count <= 1
                        type: Enums.label.type_caption
                        text: "等待启动..."
                    }
                }

                Row {
                    width: parent.width
                    spacing: 10

                    Button {
                        text: "清空日志"
                        onClicked: backend.clearLog()
                    }
                    Button {
                        text: "复制日志"
                        onClicked: backend.copyLog()
                    }
                    Button {
                        text: "保存到文件"
                        onClicked: saveLogDialog.open()
                    }
                }
            }
        }
    }
}
