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
        function onConfirmRequested(title, content) {
            confirmDialog.title = title
            confirmDialog.content = content
            confirmDialog.open()
        }
        function onProgressStarted(title, content) {
            progressDialog.title = title
            progressDialog.content = content
            progressDialog.open()
        }
        function onProgressFinished() {
            progressDialog.close()
        }
        function onShowNodeVersionDialog() {
            nodeVersionDialog.open()
            if (backend.activeNodeBackend) {
                backend.activeNodeBackend.loadInitialVersions()
                backend.activeNodeBackend.refreshVersions()
            }
        }
        function onSearchTextChanged() {
            if (searchEdit.text !== backend.searchText)
                searchEdit.text = backend.searchText
        }
    }

    Component.onCompleted: {
        if (backend)
            backend.loadNodes(true)
    }

    // ==================== 通用对话框 ====================
    MessageBox {
        id: confirmDialog
        title: "确认覆盖"
        content: ""
        confirmText: "确定"
        cancelText: "取消"
        onAccepted: backend.confirmPending()
        onRejected: backend.cancelPending()
    }

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

    MessageBox {
        id: nvSwitchDialog
        title: "确认切换版本"
        content: ""
        confirmText: "确定"
        cancelText: "取消"
        onAccepted: {
            if (nodeVersionDialog.nodeBackend)
                nodeVersionDialog.nodeBackend.switchVersion(
                    nodeVersionDialog.nodeBackend.selectedIndex)
        }
    }

    // ==================== 单节点版本管理对话框 ====================
    DialogBoxCore {
        id: nodeVersionDialog
        contentWidth: 560

        readonly property var nodeBackend: backend ? backend.activeNodeBackend : null

        Connections {
            target: nodeVersionDialog.nodeBackend

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
                nvList.currentIndex = -1
            }
            function onRequestClose() {
                nodeVersionDialog.close()
                backend.closeNodeVersion()
            }
        }

        Column {
            width: 560
            spacing: 12

            Label {
                width: parent.width
                type: Enums.label.type_subtitle
                elide: Text.ElideRight
                text: "节点版本管理 - "
                      + (nodeVersionDialog.nodeBackend
                         ? nodeVersionDialog.nodeBackend.nodeName : "")
            }

            Row {
                width: parent.width
                spacing: 8

                Label {
                    height: 32
                    verticalAlignment: Text.AlignVCenter
                    text: "仓库状态:"
                }

                Label {
                    height: 32
                    verticalAlignment: Text.AlignVCenter
                    type: Enums.label.type_body_strong
                    customTextColor: root.accentTeal
                    elide: Text.ElideRight
                    text: nodeVersionDialog.nodeBackend
                          ? nodeVersionDialog.nodeBackend.statusText : ""
                }
            }

            SwitchRow {
                text: "只看主分支"
                checked: nodeVersionDialog.nodeBackend
                         ? nodeVersionDialog.nodeBackend.mainBranchOnly : false
                onToggled: (checked) => {
                    if (nodeVersionDialog.nodeBackend)
                        nodeVersionDialog.nodeBackend.mainBranchOnly = checked
                }
            }

            SwitchRow {
                text: "启用代理"
                checked: nodeVersionDialog.nodeBackend
                         ? nodeVersionDialog.nodeBackend.proxyEnabled : false
                onToggled: (checked) => {
                    if (nodeVersionDialog.nodeBackend)
                        nodeVersionDialog.nodeBackend.proxyEnabled = checked
                }
            }

            Rectangle {
                width: parent.width
                height: 360
                radius: 5
                color: Enums.surfaceColor
                border.color: Enums.borderColor
                border.width: 1
                clip: true

                QQ.ListView {
                    id: nvList
                    anchors.fill: parent
                    anchors.margins: 2
                    clip: true
                    spacing: 1
                    model: nodeVersionDialog.nodeBackend
                           ? nodeVersionDialog.nodeBackend.versionModel : null

                    delegate: Rectangle {
                        required property int index
                        required property string name
                        required property string message
                        required property string commitShort
                        required property string dateTime
                        required property bool isCurrent

                        width: nvList.width
                        height: 48
                        color: index === nvList.currentIndex
                               ? Qt.rgba(Enums.accentColor.r, Enums.accentColor.g,
                                         Enums.accentColor.b, 0.18)
                               : (nvRowHover.hovered ? Enums.hoverColor : "transparent")

                        HoverHandler {
                            id: nvRowHover
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                nvList.currentIndex = index
                                nodeVersionDialog.nodeBackend.setSelectedIndex(index)
                            }
                        }

                        Row {
                            anchors.left: parent.left
                            anchors.leftMargin: 12
                            anchors.right: parent.right
                            anchors.rightMargin: 12
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 10

                            Label {
                                width: 130
                                height: 48
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                                type: Enums.label.type_body_strong
                                customTextColor: root.accentTeal
                                text: name
                            }

                            Label {
                                width: 70
                                height: 48
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                                type: Enums.label.type_caption
                                text: commitShort
                            }

                            Label {
                                width: 140
                                height: 48
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                                type: Enums.label.type_caption
                                text: dateTime
                            }

                            Label {
                                width: parent.width - 130 - 70 - 140 - 60
                                height: 48
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                                text: message
                            }

                            Label {
                                height: 48
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
                    visible: nvList.count === 0
                    type: Enums.label.type_caption
                    text: (nodeVersionDialog.nodeBackend
                           && nodeVersionDialog.nodeBackend.busy)
                          ? "正在获取版本信息..." : "暂无版本信息，请点击刷新"
                }
            }
        }

        footer: Component {
            Row {
                spacing: 12

                Button {
                    width: 140
                    height: 32
                    icon: "ArrowSync"
                    text: "刷新版本"
                    enabled: nodeVersionDialog.nodeBackend !== null
                             && !nodeVersionDialog.nodeBackend.busy
                    onClicked: nodeVersionDialog.nodeBackend.refreshVersions()
                }

                Button {
                    width: 140
                    height: 32
                    style: Enums.button.style_primary
                    text: "切换版本"
                    enabled: nodeVersionDialog.nodeBackend !== null
                             && !nodeVersionDialog.nodeBackend.busy
                             && nodeVersionDialog.nodeBackend.selectedIndex >= 0
                    onClicked: {
                        nvSwitchDialog.title = "确认切换版本"
                        nvSwitchDialog.content = "确定要切换到以下版本吗？\n\n"
                                + nodeVersionDialog.nodeBackend.selectedName
                        nvSwitchDialog.open()
                    }
                }

                Button {
                    width: 100
                    height: 32
                    text: "关闭"
                    onClicked: {
                        nodeVersionDialog.close()
                        backend.closeNodeVersion()
                    }
                }
            }
        }
    }

    // ==================== 页面顶部面包屑 ====================
    PageHeader {
        id: header
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        currentText: "节点管理"
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
            id: contentColumn
            width: scroll.width - scroll.padding * 2
            height: scroll.height - scroll.padding * 2
            spacing: 20

            // ==================== 自定义节点安装 ====================
            Card {
                id: installCard
                width: parent.width
                autoHeight: true

                Column {
                    width: parent.width
                    spacing: 12

                    Label {
                        type: Enums.label.type_body_strong
                        text: "自定义节点安装"
                    }

                    SwitchRow {
                        text: "启用代理"
                        checked: backend.gitProxyEnabled
                        onToggled: (checked) => {
                            backend.gitProxyEnabled = checked
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        LineEdit {
                            id: gitUrlEdit
                            width: parent.width - gitCloneButton.width - 10
                            height: 32
                            text: backend.gitUrl
                            placeholderText: "输入Git仓库地址，例如: https://github.com/xxx/yyy"
                            onTextEdited: backend.gitUrl = text
                        }

                        Button {
                            id: gitCloneButton
                            height: 32
                            icon: "ArrowSync"
                            text: "执行"
                            onClicked: backend.executeGitClone()
                        }
                    }
                }
            }

            // ==================== 自定义节点管理 ====================
            Card {
                id: nodeListCard
                width: parent.width
                // 高度 = 撑满剩余空间（视口高 - 上方安装卡 - 间距）
                preferredHeight: Math.max(320,
                                          contentColumn.height - installCard.height
                                          - contentColumn.spacing)

                Column {
                    id: nodeListColumn
                    width: parent.width
                    height: parent.height
                    spacing: 12

                    Label {
                        id: nodeListTitle
                        type: Enums.label.type_body_strong
                        text: "自定义节点管理"
                    }

                    Row {
                        id: searchRow
                        width: parent.width
                        spacing: 10

                        LineEdit {
                            id: searchEdit
                            width: parent.width - countLabel.width
                                   - prevMatchButton.width - nextMatchButton.width - 30
                            height: 32
                            text: backend.searchText
                            placeholderText: "搜索节点名称"
                            onTextEdited: backend.searchText = text
                        }

                        Label {
                            id: countLabel
                            width: 50
                            height: 32
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            type: Enums.label.type_caption
                            text: backend.searchCount
                        }

                        Button {
                            id: prevMatchButton
                            width: 40
                            height: 32
                            text: "<"
                            onClicked: {
                                var i = backend.previousMatch()
                                if (i >= 0)
                                    nodeList.scrollToIndex(i)
                            }
                        }

                        Button {
                            id: nextMatchButton
                            width: 40
                            height: 32
                            text: ">"
                            onClicked: {
                                var i = backend.nextMatch()
                                if (i >= 0)
                                    nodeList.scrollToIndex(i)
                            }
                        }
                    }

                    Row {
                        id: actionsRow
                        width: parent.width
                        spacing: 10

                        Button {
                            height: 32
                            icon: "ArrowSync"
                            text: "获取本地版本"
                            enabled: !backend.busy
                            onClicked: backend.fetchLocalVersions()
                        }

                        Button {
                            height: 32
                            icon: "ArrowSync"
                            text: "刷新列表"
                            enabled: !backend.busy
                            onClicked: backend.refreshNodeList()
                        }

                        Label {
                            height: 32
                            verticalAlignment: Text.AlignVCenter
                            type: Enums.label.type_caption
                            text: backend.listStatus
                        }
                    }

                    Rectangle {
                        width: parent.width
                        // 撑满“自定义节点管理”卡片剩余高度
                        height: Math.max(160,
                                         nodeListColumn.height - nodeListTitle.height
                                         - searchRow.height - actionsRow.height
                                         - nodeListColumn.spacing * 3)
                        radius: 5
                        color: Enums.surfaceColor
                        border.color: Enums.borderColor
                        border.width: 1
                        clip: true

                        QQ.ListView {
                            id: nodeList
                            anchors.fill: parent
                            anchors.margins: 2
                            clip: true
                            spacing: 1
                            model: backend.nodeModel

                            delegate: Rectangle {
                                required property int index
                                required property string nameHtml
                                required property string version
                                required property string date
                                required property bool isEnabled
                                required property bool hasRequirements

                                width: nodeList.width
                                height: 55
                                color: nodeRowHover.hovered ? Enums.hoverColor : "transparent"

                                HoverHandler {
                                    id: nodeRowHover
                                }

                                Connections {
                                    target: backend
                                    function onToggleCancelled(cancelIndex) {
                                        if (cancelIndex === index)
                                            enableCheck.checked = isEnabled
                                    }
                                }

                                Row {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 12
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 10

                                    Label {
                                        width: 200
                                        height: 55
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                        textFormat: Text.RichText
                                        text: nameHtml
                                    }

                                    Label {
                                        width: 110
                                        height: 55
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                        type: Enums.label.type_caption
                                        text: version
                                    }

                                    Label {
                                        width: 160
                                        height: 55
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                        type: Enums.label.type_caption
                                        text: date
                                    }
                                }

                                Row {
                                    anchors.right: parent.right
                                    anchors.rightMargin: 12
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 8

                                    Label {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: isEnabled ? "已启用" : "已禁用"
                                    }

                                    ToggleSwitch {
                                        id: enableCheck
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: ""
                                        checked: isEnabled
                                        onToggled: (checked) => {
                                            backend.toggleNode(index, checked)
                                        }
                                    }

                                    Button {
                                        id: installReqButton
                                        height: 30
                                        icon: "Document"
                                        text: "安装依赖"
                                        visible: hasRequirements
                                        enabled: isEnabled
                                        onClicked: backend.installRequirementsForNode(index)

                                        MouseArea {
                                            anchors.fill: parent
                                            acceptedButtons: Qt.RightButton
                                            onClicked: backend.openReqFileForNode(index)
                                        }
                                    }

                                    Button {
                                        height: 30
                                        icon: "ArrowSync"
                                        text: "更新"
                                        enabled: isEnabled
                                        onClicked: backend.openNodeVersion(index)
                                    }

                                    Button {
                                        height: 30
                                        icon: "Folder"
                                        text: "打开"
                                        enabled: isEnabled
                                        onClicked: backend.openFolderForNode(index)
                                    }
                                }
                            }
                        }

                        Label {
                            anchors.centerIn: parent
                            visible: nodeList.count === 0
                            type: Enums.label.type_caption
                            text: backend.listStatus
                        }
                    }
                }
            }
        }
    }
}
