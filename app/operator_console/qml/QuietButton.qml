import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Button {
    id: control
    implicitHeight: 38
    font.pixelSize: 13
    Accessible.name: text
    scale: control.down ? 0.985 : 1.0
    Behavior on scale { NumberAnimation { duration: BazTheme.transitionDuration; easing.type: Easing.OutCubic } }
    background: Rectangle {
        radius: 4
        color: control.checked ? BazTheme.accentSoft : control.down ? "#172A35" : BazTheme.surfaceAlt
        border.color: control.activeFocus || control.checked ? BazTheme.accent : BazTheme.border
        border.width: control.activeFocus ? 2 : 1
        Behavior on color { ColorAnimation { duration: BazTheme.transitionDuration } }
        Behavior on border.color { ColorAnimation { duration: BazTheme.transitionDuration } }
    }
    contentItem: Text {
        text: control.text
        color: control.enabled ? BazTheme.textPrimary : "#60727C"
        font: control.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
