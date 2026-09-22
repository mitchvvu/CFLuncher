import QtQuick
import QtQuick.Dialogs
import PrismQML

Item {
    id: root
    property var backend
    readonly property var vramModes: ["gpu_only", "high", "normal", "low", "no", "cpu"]

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
    }

    FileDialog {
        id: pythonDialog
        title: "选择python.exe文件"
        fileMode: FileDialog.OpenFile
        currentFolder: backend.pythonFolderUrl
        nameFilters: ["可执行文件 (*.exe)", "所有文件 (*)"]
        onAccepted: backend.browsePythonFile(selectedFile.toString())
    }

    FolderDialog {
        id: outputDirDialog
        title: "选择输出目录"
        currentFolder: backend.outputFolderUrl
        onAccepted: backend.browseOutputDir(selectedFolder.toString())
    }

    FolderDialog {
        id: inputDirDialog
        title: "选择输入目录"
        currentFolder: backend.inputFolderUrl
        onAccepted: backend.browseInputDir(selectedFolder.toString())
    }

    PageHeader {
        id: header
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        currentText: "设置"
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

            // ==================== 代理设置 ====================
            Card {
                width: parent.width
                autoHeight: true

                Column {
                    width: parent.width
                    spacing: 12

                    Label {
                        type: Enums.label.type_body_strong
                        text: "代理设置"
                    }

                    SwitchRow {
                        text: "启用代理（仅对启动面板生效）"
                        checked: backend.proxyEnabled
                        onToggled: (checked) => {
                            backend.proxyEnabled = checked
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: 12
                        visible: backend.proxyEnabled

                        Row {
                            width: parent.width
                            spacing: 10

                            ParamLabel { text: "代理类型:" }

                            ComboBox {
                                id: proxyTypeCombo
                                width: 160
                                height: 32
                                model: ["系统代理", "Socks5代理"]
                                currentIndex: backend.proxyType === "socks5" ? 1 : 0
                                onActivated: backend.setProxyType(index === 0 ? "system" : "socks5")
                            }
                        }

                        Row {
                            width: parent.width
                            spacing: 10

                            ParamLabel { text: "代理网址:" }

                            LineEdit {
                                id: proxyHostEdit
                                width: parent.width - root.paramLabelWidth - 10
                                height: 32
                                text: backend.proxyHost
                                onTextEdited: backend.proxyHost = text
                            }
                        }

                        Row {
                            width: parent.width
                            spacing: 10

                            ParamLabel { text: "端口号:" }

                            LineEdit {
                                id: proxyPortEdit
                                width: 80
                                height: 32
                                text: backend.proxyPort
                                onTextEdited: backend.proxyPort = text
                                validator: IntValidator { bottom: 1; top: 65535 }
                            }
                        }
                    }
                }
            }

            // ==================== 局域网设置 ====================
            Card {
                width: parent.width
                autoHeight: true

                Column {
                    width: parent.width
                    spacing: 12

                    Label {
                        type: Enums.label.type_body_strong
                        text: "局域网设置"
                    }

                    SwitchRow {
                        text: "启用局域网访问"
                        checked: backend.lanAccess
                        onToggled: (checked) => {
                            backend.lanAccess = checked
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: 12
                        visible: backend.lanAccess

                        Row {
                            width: parent.width
                            spacing: 10

                            ParamLabel { text: "监听网址:" }

                            LineEdit {
                                id: listenEdit
                                width: parent.width - root.paramLabelWidth - 10
                                height: 32
                                text: backend.listenAddress
                                placeholderText: "例如: 0.0.0.0"
                                onTextEdited: backend.listenAddress = text
                            }
                        }
                    }

                    SwitchRow {
                        text: "启用自定义端口"
                        checked: backend.customPortEnabled
                        onToggled: (checked) => {
                            backend.customPortEnabled = checked
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: 12
                        visible: backend.customPortEnabled

                        Row {
                            width: parent.width
                            spacing: 10

                            ParamLabel { text: "端口号:" }

                            LineEdit {
                                id: listenPortEdit
                                width: 80
                                height: 32
                                text: backend.listenPort
                                placeholderText: "8188"
                                onTextEdited: backend.listenPort = text
                                validator: IntValidator { bottom: 1; top: 65535 }
                            }
                        }
                    }
                }
            }

            // ==================== Python 路径设置 ====================
            Card {
                width: parent.width
                autoHeight: true

                Column {
                    width: parent.width
                    spacing: 12

                    Label {
                        type: Enums.label.type_body_strong
                        text: "Python路径设置"
                    }

                    SwitchRow {
                        text: "使用自定义Python解释器路径"
                        checked: backend.customPathEnabled
                        onToggled: (checked) => {
                            backend.customPathEnabled = checked
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10
                        visible: backend.customPathEnabled

                        LineEdit {
                            id: pathEdit
                            width: parent.width - browseButton.width - openFolderButton.width - 20
                            height: 32
                            readOnly: true
                            text: backend.comfyuiPath
                            placeholderText: "请选择python.exe文件路径"
                        }

                        Button {
                            id: browseButton
                            height: 32
                            icon: "Folder"
                            text: "浏览..."
                            onClicked: pythonDialog.open()
                        }

                        Button {
                            id: openFolderButton
                            height: 32
                            icon: "Folder"
                            text: "打开所在文件夹"
                            enabled: backend.comfyuiPath !== ""
                            onClicked: backend.openPythonFolder()
                        }
                    }
                }
            }

            // ==================== 高级启动参数设置 ====================
            Card {
                width: parent.width
                autoHeight: true

                Column {
                    width: parent.width
                    spacing: 12

                    Label {
                        type: Enums.label.type_body_strong
                        text: "高级启动参数设置"
                    }

                    SwitchRow {
                        text: "启用自定义输出目录"
                        checked: backend.outputDirEnabled
                        onToggled: (checked) => {
                            backend.outputDirEnabled = checked
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10
                        visible: backend.outputDirEnabled

                        LineEdit {
                            id: outputDirEdit
                            width: parent.width - outputBrowseButton.width - 20
                            height: 32
                            readOnly: true
                            text: backend.outputDir
                            placeholderText: "请选择输出目录"
                        }

                        Button {
                            id: outputBrowseButton
                            height: 32
                            icon: "Folder"
                            text: "浏览..."
                            onClicked: outputDirDialog.open()
                        }
                    }

                    SwitchRow {
                        text: "启用自定义输入目录"
                        checked: backend.inputDirEnabled
                        onToggled: (checked) => {
                            backend.inputDirEnabled = checked
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10
                        visible: backend.inputDirEnabled

                        LineEdit {
                            id: inputDirEdit
                            width: parent.width - inputBrowseButton.width - 20
                            height: 32
                            readOnly: true
                            text: backend.inputDir
                            placeholderText: "请选择输入目录"
                        }

                        Button {
                            id: inputBrowseButton
                            height: 32
                            icon: "Folder"
                            text: "浏览..."
                            onClicked: inputDirDialog.open()
                        }
                    }

                    SwitchRow {
                        text: "启用显存模式设置"
                        checked: backend.vramEnabled
                        onToggled: (checked) => {
                            backend.vramEnabled = checked
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10
                        visible: backend.vramEnabled

                        ParamLabel { text: "显存模式:" }

                        ComboBox {
                            id: vramCombo
                            width: parent.width - root.paramLabelWidth - 10
                            height: 32
                            model: [
                                "仅GPU:  所有模型保持在GPU上 (--gpu-only)",
                                "高显存:  模型保持加载 (--highvram)",
                                "中显存:  正常显存使用 (--normalvram)",
                                "低显存:  分割UNet节省显存 (--lowvram)",
                                "极低显存:  当低显存仍显存不足时使用 (--novram)",
                                "仅CPU:  所有计算都在CPU上 (--cpu)"
                            ]
                            currentIndex: backend.vramModeIndex
                            onActivated: backend.vramMode = root.vramModes[index]
                        }
                    }

                    SwitchRow {
                        text: "启用预留显存"
                        checked: backend.reserveVramEnabled
                        onToggled: (checked) => {
                            backend.reserveVramEnabled = checked
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10
                        visible: backend.reserveVramEnabled

                        ParamLabel { text: "预留显存 (GB):" }

                        LineEdit {
                            id: reserveVramEdit
                            width: 80
                            height: 32
                            text: backend.reserveVram
                            onTextEdited: backend.reserveVram = text
                            validator: DoubleValidator { bottom: 0.0; top: 100.0; decimals: 2 }
                        }
                    }

                    SwitchRow {
                        text: "禁用元数据:  图片不保存工作流"
                        checked: backend.disableMetadata
                        onToggled: (checked) => {
                            backend.disableMetadata = checked
                        }
                    }
                }
            }

            // ==================== Manager 重启命令接管 ====================
            Card {
                width: parent.width
                autoHeight: true

                Column {
                    width: parent.width
                    spacing: 12

                    Label {
                        type: Enums.label.type_body_strong
                        text: "Manager重启命令接管"
                    }

                    SwitchRow {
                        text: "启用 (避免Manager重启失败导致端口占用)"
                        checked: backend.restartCommandEnabled
                        onToggled: (checked) => {
                            backend.restartCommandEnabled = checked
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10
                        visible: backend.restartCommandEnabled

                        ParamLabel { text: "重启命令关键词:" }

                        LineEdit {
                            id: restartKeywordEdit
                            width: parent.width - root.paramLabelWidth - 10
                            height: 32
                            text: backend.restartCommandKeyword
                            placeholderText: "输入用于识别重启命令的关键词"
                            onTextEdited: backend.restartCommandKeyword = text
                        }
                    }
                }
            }

            // ==================== 当前启动参数 ====================
            Card {
                width: parent.width
                autoHeight: true

                Column {
                    width: parent.width
                    spacing: 12

                    Label {
                        type: Enums.label.type_body_strong
                        text: "当前启动参数"
                    }

                    TextEdit {
                        width: parent.width
                        height: 80
                        readOnly: true
                        text: backend.commandPreview
                        wrapMode: TextEdit.Wrap
                    }
                }
            }

            // ==================== 保存按钮 ====================
            Button {
                width: parent.width
                height: 40
                style: Enums.button.style_primary
                text: backend.saveButtonText
                enabled: backend.saveEnabled
                onClicked: backend.saveSettings()
            }
        }
    }
}
