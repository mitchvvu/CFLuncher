import QtQuick
import QtQuick.Dialogs
import PrismQML

Item {
    id: root
    property var backend
    readonly property var vramModes: ["gpu_only", "high", "normal", "low", "no", "cpu"]

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

    ScrollArea {
        id: scroll
        anchors.fill: parent
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

                    CheckBox {
                        text: "启用代理（仅对启动面板生效）"
                        checked: backend.proxyEnabled
                        onToggled: backend.proxyEnabled = checked
                    }

                    Item {
                        width: parent.width
                        height: 32

                        Row {
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 10

                            ComboBox {
                                id: proxyTypeCombo
                                width: 160
                                height: 32
                                model: ["系统代理", "Socks5代理"]
                                currentIndex: backend.proxyType === "socks5" ? 1 : 0
                                onActivated: backend.setProxyType(index === 0 ? "system" : "socks5")
                            }

                            Label {
                                height: 32
                                verticalAlignment: Text.AlignVCenter
                                text: "代理网址:"
                            }

                            LineEdit {
                                id: proxyHostEdit
                                width: 350
                                height: 32
                                text: backend.proxyHost
                                onTextEdited: backend.proxyHost = text
                            }
                        }

                        Row {
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 10

                            Label {
                                height: 32
                                verticalAlignment: Text.AlignVCenter
                                text: "端口号:"
                            }

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

                    Item {
                        width: parent.width
                        height: 32

                        Row {
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 10

                            Item {
                                width: 160
                                height: 32
                                CheckBox {
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "启用局域网访问"
                                    checked: backend.lanAccess
                                    onToggled: backend.lanAccess = checked
                                }
                            }

                            Label {
                                height: 32
                                verticalAlignment: Text.AlignVCenter
                                text: "监听网址:"
                            }

                            LineEdit {
                                id: listenEdit
                                width: 350
                                height: 32
                                text: backend.listenAddress
                                placeholderText: "例如: 0.0.0.0"
                                onTextEdited: backend.listenAddress = text
                            }
                        }

                        Row {
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 10

                            Item {
                                width: 160
                                height: 32
                                CheckBox {
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "启用自定义端口"
                                    checked: backend.customPortEnabled
                                    onToggled: backend.customPortEnabled = checked
                                }
                            }

                            Label {
                                height: 32
                                verticalAlignment: Text.AlignVCenter
                                text: "端口号:"
                            }

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

                    CheckBox {
                        text: "使用自定义Python解释器路径"
                        checked: backend.customPathEnabled
                        onToggled: backend.customPathEnabled = checked
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        LineEdit {
                            id: pathEdit
                            width: parent.width - browseButton.width - openFolderButton.width - 20
                            height: 32
                            readOnly: true
                            enabled: backend.customPathEnabled
                            text: backend.comfyuiPath
                            placeholderText: "请选择python.exe文件路径"
                        }

                        Button {
                            id: browseButton
                            height: 32
                            icon: "Folder"
                            text: "浏览..."
                            enabled: backend.customPathEnabled
                            onClicked: pythonDialog.open()
                        }

                        Button {
                            id: openFolderButton
                            height: 32
                            icon: "Folder"
                            text: "打开所在文件夹"
                            enabled: backend.customPathEnabled && backend.comfyuiPath !== ""
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

                    Row {
                        width: parent.width
                        spacing: 10

                        Item {
                            width: 200
                            height: 32
                            CheckBox {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "启用自定义输出目录"
                                checked: backend.outputDirEnabled
                                onToggled: backend.outputDirEnabled = checked
                            }
                        }

                        LineEdit {
                            id: outputDirEdit
                            width: parent.width - outputBrowseButton.width - 20
                            height: 32
                            readOnly: true
                            enabled: backend.outputDirEnabled
                            text: backend.outputDir
                            placeholderText: "请选择输出目录"
                        }

                        Button {
                            id: outputBrowseButton
                            height: 32
                            icon: "Folder"
                            text: "浏览..."
                            enabled: backend.outputDirEnabled
                            onClicked: outputDirDialog.open()
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        Item {
                            width: 200
                            height: 32
                            CheckBox {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "启用自定义输入目录"
                                checked: backend.inputDirEnabled
                                onToggled: backend.inputDirEnabled = checked
                            }
                        }

                        LineEdit {
                            id: inputDirEdit
                            width: parent.width - inputBrowseButton.width - 20
                            height: 32
                            readOnly: true
                            enabled: backend.inputDirEnabled
                            text: backend.inputDir
                            placeholderText: "请选择输入目录"
                        }

                        Button {
                            id: inputBrowseButton
                            height: 32
                            icon: "Folder"
                            text: "浏览..."
                            enabled: backend.inputDirEnabled
                            onClicked: inputDirDialog.open()
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        Item {
                            width: 200
                            height: 32
                            CheckBox {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "启用显存模式设置"
                                checked: backend.vramEnabled
                                onToggled: backend.vramEnabled = checked
                            }
                        }

                        ComboBox {
                            id: vramCombo
                            width: parent.width - 200 - 10
                            height: 32
                            enabled: backend.vramEnabled
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

                    Row {
                        width: parent.width
                        spacing: 10

                        CheckBox {
                            id: reserveVramCheck
                            text: "预留显存 (GB):"
                            checked: backend.reserveVramEnabled
                            onToggled: backend.reserveVramEnabled = checked
                        }

                        LineEdit {
                            id: reserveVramEdit
                            width: 80
                            height: 32
                            enabled: backend.reserveVramEnabled
                            text: backend.reserveVram
                            onTextEdited: backend.reserveVram = text
                            validator: DoubleValidator { bottom: 0.0; top: 100.0; decimals: 2 }
                        }
                    }

                    CheckBox {
                        text: "禁用元数据:  图片不保存工作流"
                        checked: backend.disableMetadata
                        onToggled: backend.disableMetadata = checked
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

                    CheckBox {
                        text: "启用 (避免Manager重启失败导致端口占用)"
                        checked: backend.restartCommandEnabled
                        onToggled: backend.restartCommandEnabled = checked
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        Label {
                            height: 32
                            verticalAlignment: Text.AlignVCenter
                            text: "重启命令关键词:"
                        }

                        LineEdit {
                            id: restartKeywordEdit
                            width: parent.width - 130
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
