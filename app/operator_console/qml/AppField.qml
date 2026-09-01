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
    selectedTextColor: "#041014"
    font.pixelSize: 11
    background: Rectangle {
        radius: 4
        color: "#09141C"
        border.color: control.activeFocus ? BazTheme.accent : BazTheme.border
        border.width: control.activeFocus ? 2 : 1
    }
}
