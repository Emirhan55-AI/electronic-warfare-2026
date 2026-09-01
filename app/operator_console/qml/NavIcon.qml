import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Canvas {
    required property string kind
    property color strokeColor: BazTheme.textSecondary
    width: 22
    height: 22
    onStrokeColorChanged: requestPaint()
    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.strokeStyle = strokeColor
        ctx.fillStyle = strokeColor
        ctx.lineWidth = 1.7
        ctx.lineCap = "round"
        ctx.lineJoin = "round"
        if (kind === "spectrum") {
            ctx.beginPath()
            ctx.moveTo(1, 14); ctx.lineTo(5, 14); ctx.lineTo(8, 5)
            ctx.lineTo(11, 18); ctx.lineTo(14, 9); ctx.lineTo(17, 14); ctx.lineTo(21, 14)
            ctx.stroke()
        } else if (kind === "measurement") {
            ctx.beginPath(); ctx.moveTo(3, 18); ctx.lineTo(3, 12); ctx.lineTo(7, 12); ctx.lineTo(7, 18); ctx.stroke()
            ctx.beginPath(); ctx.moveTo(9, 18); ctx.lineTo(9, 7); ctx.lineTo(13, 7); ctx.lineTo(13, 18); ctx.stroke()
            ctx.beginPath(); ctx.moveTo(15, 18); ctx.lineTo(15, 3); ctx.lineTo(19, 3); ctx.lineTo(19, 18); ctx.stroke()
            ctx.beginPath(); ctx.moveTo(2, 19); ctx.lineTo(20, 19); ctx.stroke()
        } else if (kind === "listening") {
            ctx.beginPath(); ctx.arc(11, 12, 7, Math.PI, Math.PI * 2); ctx.stroke()
            ctx.beginPath(); ctx.moveTo(4, 12); ctx.lineTo(4, 18); ctx.lineTo(7, 18); ctx.lineTo(7, 13); ctx.stroke()
            ctx.beginPath(); ctx.moveTo(18, 12); ctx.lineTo(18, 18); ctx.lineTo(15, 18); ctx.lineTo(15, 13); ctx.stroke()
        } else if (kind === "direction") {
            ctx.beginPath(); ctx.arc(11, 11, 8, 0, Math.PI * 2); ctx.stroke()
            ctx.beginPath(); ctx.moveTo(11, 3); ctx.lineTo(14, 12); ctx.lineTo(11, 10); ctx.lineTo(8, 12); ctx.closePath(); ctx.fill()
        } else {
            ctx.strokeRect(3, 4, 16, 14)
            ctx.beginPath(); ctx.moveTo(6, 8); ctx.lineTo(16, 8); ctx.moveTo(6, 12); ctx.lineTo(13, 12); ctx.moveTo(6, 16); ctx.lineTo(10, 16); ctx.stroke()
        }
    }
}
