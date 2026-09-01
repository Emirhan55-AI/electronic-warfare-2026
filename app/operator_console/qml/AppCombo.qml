import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ComboBox {
    id: control
    implicitHeight: 36
    leftPadding: 10
    rightPadding: 28
    Accessible.name: displayText
    Accessible.role: Accessible.ComboBox
    background: Rectangle {
        radius: 4
        color: "#09141C"
        border.color: control.activeFocus ? BazTheme.accent : BazTheme.border
    }
    contentItem: Text {
        text: control.displayText
        color: BazTheme.textPrimary
        font.pixelSize: 12
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    indicator: Canvas {
        x: control.width - width - 12
        anchors.verticalCenter: parent.verticalCenter
        width: 10
        height: 6
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.strokeStyle = BazTheme.textSecondary
            ctx.lineWidth = 1.5
            ctx.lineCap = "round"
            ctx.beginPath()
            ctx.moveTo(1, 1)
            ctx.lineTo(width / 2, height - 1)
            ctx.lineTo(width - 1, 1)
            ctx.stroke()
        }
    }
    popup: Popup {
        y: control.height + 2
        width: control.width
        implicitHeight: contentItem.implicitHeight + 8
        padding: 4
        background: Rectangle { color: BazTheme.raised; border.color: BazTheme.border; radius: 4 }
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
        }
    }
}
