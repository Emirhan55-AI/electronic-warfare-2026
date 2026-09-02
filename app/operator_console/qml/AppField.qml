import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

TextField {
    id: control
    implicitHeight: 36
    leftPadding: 10
    rightPadding: 10
    color: BazTheme.textPrimary
    placeholderTextColor: BazTheme.textMuted
    selectionColor: BazTheme.accent
    selectedTextColor: "#FFFFFF"
    font.pixelSize: 11
    background: Rectangle {
        radius: 4
        color: "#313131"
        border.color: control.activeFocus ? BazTheme.accent : BazTheme.border
        border.width: control.activeFocus ? 2 : 1
    }
}
