import QtQuick
import PrismQML

Item {
    id: root
    property var backend

    ScrollArea {
        anchors.fill: parent
        padding: 16

        Column {
            width: parent.width
            spacing: 16

            Card {
                width: parent.width
                Label { text: "PrismQML 冒烟测试" }
            }

            Button {
                text: "点我"
                onClicked: backend.ping()
            }

            Label {
                id: out
                text: backend ? backend.message : ""
            }
        }
    }
}
