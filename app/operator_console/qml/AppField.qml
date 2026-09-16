import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

TextField {
    id: control
    property string helpText: ""
    hoverEnabled: true
    Accessible.description: helpText
    ToolTip {
        visible: control.helpText.length > 0 && control.hovered
        delay: 500
        timeout: 12000
        width: 320
        text: control.helpText
        contentItem: Text { text: control.helpText; wrapMode: Text.WordWrap; color: "#EEEEEE"; font.pixelSize: 12 }
        background: Rectangle { color: "#303030"; border.color: "#737373"; radius: 4 }
    }
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
