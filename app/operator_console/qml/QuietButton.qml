import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Button {
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
    property int textAlignment: Text.AlignHCenter
    implicitHeight: 38
    font.pixelSize: 13
    Accessible.name: text
    scale: control.down ? 0.985 : 1.0
    Behavior on scale { NumberAnimation { duration: BazTheme.transitionDuration; easing.type: Easing.OutCubic } }
    background: Rectangle {
        radius: 4
        color: control.checked ? BazTheme.accentSoft : control.down ? "#2B2B2B" : BazTheme.surfaceAlt
        border.color: control.activeFocus || control.checked ? BazTheme.accent : BazTheme.border
        border.width: control.activeFocus ? 2 : 1
        Behavior on color { ColorAnimation { duration: BazTheme.transitionDuration } }
        Behavior on border.color { ColorAnimation { duration: BazTheme.transitionDuration } }
    }
    contentItem: Text {
        text: control.text
        color: control.enabled ? BazTheme.textPrimary : "#868686"
        font: control.font
        horizontalAlignment: control.textAlignment
        verticalAlignment: Text.AlignVCenter
    }
}
