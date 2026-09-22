import QtQuick
import QtQuick.Dialogs
import PrismQML

Item {
    id: root
    property var backend

    // 统一参数行的标签宽度，保证各参数左对齐
    readonly property int paramLabelWidth: 120

    // 参数行内的标签
    component ParamLabel: Label {
        width: root.paramLabelWidth
        height: 32
        verticalAlignment: Text.AlignVCenter
    }

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
        function onProgressStarted(title, content) {
            progressDialog.title = title
            progressDialog.content = content
            progressDialog.open()
        }
        function onProgressFinished() {
            progressDialog.close()
        }
        function onDepTextChanged() {
            if (depEdit.text !== backend.depText)
                depEdit.text = backend.depText
        }
    }

    // ==================== 文件选择 ====================
    FileDialog {
        id: depFileDialog
        title: backend.depTypeIndex === 2 ? "选择WHL文件" : "选择requirements.txt文件"
        fileMode: FileDialog.OpenFile
        nameFilters: backend.depTypeIndex === 2
                     ? ["WHL文件 (*.whl)", "所有文件 (*)"]
                     : ["文本文件 (*.txt)", "所有文件 (*)"]
        onAccepted: backend.setDepFile(selectedFile.toString())
    }

    FileDialog {
        id: exportDialog
        title: "导出依赖列表"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "txt"
        nameFilters: ["文本文件 (*.txt)"]
        onAccepted: backend.exportDependencies(selectedFile.toString())
    }

    // ==================== 执行进度对话框 ====================
    MessageBox {
        id: progressDialog
        title: "执行中"
        content: ""
        confirmText: "关闭"
        cancelText: "取消并终止"
        yesButtonVisible: false
        cancelButtonVisible: true
        onRejected: backend.cancelProgress()
    }

    // ==================== 页面顶部面包屑 ====================
    PageHeader {
        id: header
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        currentText: "依赖管理"
    }

    // ==================== 页面主体 ====================
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

            // ==================== 镜像设置 ====================
            Card {
                width: parent.width
                autoHeight: true

                Column {
                    width: parent.width
                    spacing: 12

                    Label {
                        type: Enums.label.type_body_strong
                        text: "镜像设置"
                    }

                    SwitchRow {
                        text: "启用代理"
                        checked: backend.proxyEnabled
                        onToggled: (checked) => {
                            backend.proxyEnabled = checked
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        ParamLabel { text: "镜像源:" }

                        ComboBox {
                            width: parent.width - root.paramLabelWidth
                                   - mirrorSaveButton.width - 20
                            height: 32
                            model: backend.mirrorNames
                            currentIndex: backend.mirrorIndex
                            onActivated: (index) => {
                                backend.mirrorIndex = index
                            }
                        }

                        Button {
                            id: mirrorSaveButton
                            height: 32
                            icon: "Save"
                            text: "保存设置"
                            onClicked: backend.saveMirrorSettings()
                        }
                    }
                }
            }

            // ==================== 安装依赖 ====================
            Card {
                width: parent.width
                autoHeight: true

                Column {
                    width: parent.width
                    spacing: 12

                    Label {
                        type: Enums.label.type_body_strong
                        text: "安装依赖"
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        ParamLabel { text: "操作类型:" }

                        ComboBox {
                            width: 160
                            height: 32
                            model: backend.depTypeNames
                            currentIndex: backend.depTypeIndex
                            onActivated: (index) => {
                                backend.depTypeIndex = index
                            }
                        }

                        Button {
                            id: depBrowseButton
                            height: 32
                            icon: "Folder"
                            text: "指定文件"
                            enabled: backend.depBrowseEnabled
                            onClicked: depFileDialog.open()
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        LineEdit {
                            id: depEdit
                            width: parent.width - depExecButton.width - 10
                            height: 32
                            text: backend.depText
                            placeholderText: backend.depPlaceholder
                            onTextEdited: backend.depText = text
                        }

                        Button {
                            id: depExecButton
                            height: 32
                            style: Enums.button.style_primary
                            text: "执行"
                            onClicked: backend.executeDepCommand()
                        }
                    }

                    Flow {
                        width: parent.width
                        spacing: 10

                        Button {
                            height: 32
                            text: "安装CF本体前端工作流文档依赖"
                            onClicked: backend.installComfyuiThreeDeps()
                        }

                        Button {
                            height: 32
                            icon: "Document"
                            text: "打开本体依赖"
                            onClicked: backend.openComfyuiRequirements()
                        }

                        Button {
                            height: 32
                            icon: "Document"
                            text: "导出依赖列表"
                            onClicked: exportDialog.open()
                        }
                    }
                }
            }
        }
    }
}
