import QtQuick
import PrismQML

// 页面顶部面包屑：显示当前功能位置，例如「ComfyUI 启动器 > 节点管理」
Item {
    id: root

    property string parentText: "启动器"
    property string currentText: ""

    // 字号为正文的两倍，字重保持 regular
    readonly property int headerFontSize: Enums.typography.body * 2

    implicitHeight: 64

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        spacing: 10

        Label {
            height: 40
            verticalAlignment: Text.AlignVCenter
            type: Enums.label.type_body
            font.pixelSize: root.headerFontSize
            customTextColor: Enums.secondaryForeground
            text: root.parentText
        }

        Label {
            height: 40
            verticalAlignment: Text.AlignVCenter
            type: Enums.label.type_body
            font.pixelSize: root.headerFontSize
            customTextColor: Enums.tertiaryForeground
            text: ">"
        }

        Label {
            height: 40
            verticalAlignment: Text.AlignVCenter
            type: Enums.label.type_body
            font.pixelSize: root.headerFontSize
            customTextColor: Enums.foregroundColor
            text: root.currentText
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: Enums.dividerColor
    }
}
