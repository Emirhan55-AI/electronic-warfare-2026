import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ComboBox {
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
    readonly property int popupMaximumHeight: 280
    implicitHeight: 36
    leftPadding: 10
    rightPadding: 28
    Accessible.name: displayText
    Accessible.role: Accessible.ComboBox
    background: Rectangle {
        radius: 4
        color: "#313131"
        border.color: control.activeFocus ? BazTheme.accent : BazTheme.border
    }
    contentItem: Text {
        text: control.displayText
        color: BazTheme.textPrimary
        font.family: "Consolas"
        font.pixelSize: 13
        horizontalAlignment: Text.AlignHCenter
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
        id: comboPopup
        objectName: control.objectName + "Popup"
        y: control.height + 2
        width: control.width
        height: Math.min(popupList.contentHeight + 8, control.popupMaximumHeight)
        padding: 4
        onOpened: Qt.callLater(function() {
            popupList.positionViewAtIndex(control.currentIndex, ListView.Center)
        })
        background: Rectangle { color: BazTheme.raised; border.color: BazTheme.border; radius: 4 }
        contentItem: ListView {
            id: popupList
            objectName: control.objectName + "PopupList"
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            boundsBehavior: Flickable.StopAtBounds
            ScrollIndicator.vertical: ScrollIndicator { }
        }
    }
}
