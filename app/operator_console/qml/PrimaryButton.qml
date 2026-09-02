import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Button {
    id: control
    implicitHeight: 40
    font.pixelSize: 13
    font.weight: Font.DemiBold
    Accessible.name: text
    scale: control.down ? 0.985 : 1.0
    Behavior on scale { NumberAnimation { duration: BazTheme.transitionDuration; easing.type: Easing.OutCubic } }
    background: Rectangle {
        radius: 4
        color: control.enabled ? (control.down ? "#026EC1" : BazTheme.accent) : "#313131"
        border.color: control.activeFocus ? "#6CADDF" : "transparent"
        border.width: 2
        Behavior on color { ColorAnimation { duration: BazTheme.transitionDuration } }
    }
    contentItem: Text {
        text: control.text
        color: control.enabled ? "#FFFFFF" : "#868686"
        font: control.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
