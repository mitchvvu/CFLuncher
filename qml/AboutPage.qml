import QtQuick
import PrismQML

Item {
    id: root
    property var backend

    ScrollArea {
        id: scroll
        anchors.fill: parent
        padding: 16

        Column {
            width: scroll.width - scroll.padding * 2
            spacing: 16

            Card {
                width: parent.width
                autoHeight: true

                Column {
                    width: parent.width
                    spacing: 12

                    Label {
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        type: Enums.label.type_title
                        text: backend ? backend.appTitle : "ComfyUI 启动器"
                    }

                    Label {
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        type: Enums.label.type_subtitle
                        text: backend ? ("版本 " + backend.appVersion) : ""
                    }

                    Separator {
                        width: parent.width
                    }

                    Label {
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        text: "ComfyUI 启动器是一个简单的工具，用于在 Windows 平台上启动 ComfyUI，无需使用批处理文件。"
                    }

                    Label {
                        type: Enums.label.type_body_strong
                        text: "主要功能："
                    }

                    Label { text: "• 一键启动 ComfyUI" }
                    Label { text: "• 配置代理设置" }
                    Label { text: "• 启用局域网访问" }
                    Label { text: "• 自定义节点管理" }
                    Label { text: "• 依赖包管理" }
                    Label { text: "• 其他高级启动参数支持" }

                    Label {
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        type: Enums.label.type_caption
                        text: "© 2025 ComfyUI 启动器"
                    }
                }
            }
        }
    }
}
