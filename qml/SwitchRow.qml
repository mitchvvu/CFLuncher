import QtQuick
import PrismQML

// 通用开关行：左侧文字、右侧开关，独占一行
Item {
    id: root

    property string text: ""
    property alias checked: toggleControl.checked
    signal toggled(bool checked)

    width: parent.width
    height: 32

    Label {
        id: switchRowLabel
        anchors.left: parent.left
        anchors.right: toggleControl.left
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        elide: Text.ElideRight
        text: root.text
    }

    ToggleSwitch {
        id: toggleControl
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        text: ""
        function onToggled(checked) {
            root.toggled(checked)
        }
    }
}
