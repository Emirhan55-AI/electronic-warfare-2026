import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: chart
    required property string title
    required property var values
    color: "#1F1F1F"
    border.color: BazTheme.border
    radius: 4
    Accessible.name: title
    onValuesChanged: plot.requestPaint()
    Label {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 10
        text: chart.title
        color: BazTheme.textSecondary
        font.pixelSize: BazTheme.uiMetaTextSize + 1
        font.weight: Font.DemiBold
    }
    Canvas {
        id: plot
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        anchors.topMargin: 30
        anchors.bottomMargin: 8
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.strokeStyle = BazTheme.border
            ctx.lineWidth = 1
            for (var grid = 1; grid < 4; ++grid) {
                var gy = grid * height / 4
                ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(width, gy); ctx.stroke()
            }
            if (!chart.values || chart.values.length < 2) {
                ctx.fillStyle = BazTheme.textMuted
                ctx.font = "11px 'Segoe UI'"
                ctx.textAlign = "center"
                ctx.fillText("Sonuç bekleniyor", width / 2, height / 2)
                return
            }
            var minimum = Number.POSITIVE_INFINITY
            var maximum = Number.NEGATIVE_INFINITY
            for (var index = 0; index < chart.values.length; ++index) {
                if (chart.values[index] === null || chart.values[index] === undefined) continue
                var value = Number(chart.values[index])
                if (!isFinite(value)) continue
                minimum = Math.min(minimum, value)
                maximum = Math.max(maximum, value)
            }
            if (!isFinite(minimum) || !isFinite(maximum)) return
            var span = Math.max(0.0000001, maximum - minimum)
            ctx.strokeStyle = BazTheme.accent
            ctx.lineWidth = 1.5
            ctx.beginPath()
            var drawing = false
            for (var point = 0; point < chart.values.length; ++point) {
                if (chart.values[point] === null || chart.values[point] === undefined || !isFinite(Number(chart.values[point]))) {
                    drawing = false
                    continue
                }
                var x = point * width / Math.max(1, chart.values.length - 1)
                var y = height - (Number(chart.values[point]) - minimum) / span * height
                if (!drawing) { ctx.moveTo(x, y); drawing = true } else ctx.lineTo(x, y)
            }
            ctx.stroke()
        }
    }
}
