import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    width: 1280
    height: 720
    color: "#0b1118"
    property var spectrumValues: []
    property int sequenceNumber: 0

    onSpectrumValuesChanged: spectrum.requestPaint()

    Rectangle {
        id: header
        anchors.left: parent.left
        anchors.right: parent.right
        height: 64
        color: "#101821"
        border.color: "#253646"

        RowLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 16
            Label { text: "EH OPERATÖR KONSOLU"; color: "#e7edf3"; font.bold: true; font.pixelSize: 16 }
            Rectangle { width: 1; height: 30; color: "#253646" }
            Label { text: "SİGMF KAYDI"; color: "#39bde8"; font.pixelSize: 12 }
            Label { text: "100,000 MHz · 8 MS/s"; color: "#8fa4b7"; font.pixelSize: 12 }
            Item { Layout.fillWidth: true }
            Label { text: "KAYIT OYNATMA"; color: "#10b981"; font.bold: true; font.pixelSize: 12 }
        }
    }

    Rectangle {
        id: navigation
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        width: 164
        color: "#101821"
        border.color: "#253646"

        Column {
            anchors.fill: parent
            anchors.topMargin: 16
            spacing: 4
            Repeater {
                model: ["Sinyal Tespiti", "Parametreler", "Dinleme", "Yön Bulma", "Konum", "Sistem"]
                delegate: Rectangle {
                    required property string modelData
                    required property int index
                    width: navigation.width
                    height: 42
                    color: index === 0 ? "#141f2a" : "transparent"
                    Rectangle { visible: index === 0; width: 3; height: parent.height; color: "#39bde8" }
                    Label {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: 16
                        text: modelData
                        color: index === 0 ? "#39bde8" : "#8fa4b7"
                        font.bold: index === 0
                        font.pixelSize: 12
                    }
                }
            }
        }
    }

    ColumnLayout {
        anchors.left: navigation.right
        anchors.right: inspector.left
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.margins: 14
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: ["Veri Kaynağı", "Ön İşleme", "FFT / Güç", "OS-CFAR", "Parametre"]
                delegate: Row {
                    required property string modelData
                    required property int index
                    spacing: 8
                    Rectangle {
                        width: 128
                        height: 34
                        radius: 4
                        color: index < 4 ? "#0e2a3a" : "#141f2a"
                        border.color: index < 4 ? "#39bde8" : "#253646"
                        Label { anchors.centerIn: parent; text: modelData; color: "#e7edf3"; font.pixelSize: 11 }
                    }
                    Label { visible: index < 4; anchors.verticalCenter: parent.verticalCenter; text: "›"; color: "#64748b" }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#090f15"
            border.color: "#253646"
            radius: 4

            Label {
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.topMargin: 12
                text: "Spektrum"
                color: "#e7edf3"
                font.pixelSize: 13
            }

            Canvas {
                id: spectrum
                anchors.fill: parent
                anchors.margins: 28
                anchors.topMargin: 48
                onPaint: {
                    const ctx = getContext("2d")
                    ctx.reset()
                    ctx.strokeStyle = "#1c2b3a"
                    ctx.lineWidth = 1
                    for (let line = 0; line <= 8; ++line) {
                        const y = line * height / 8
                        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke()
                    }
                    if (root.spectrumValues.length < 2)
                        return
                    ctx.strokeStyle = "#39bde8"
                    ctx.lineWidth = 1.5
                    ctx.beginPath()
                    for (let i = 0; i < root.spectrumValues.length; ++i) {
                        const x = i * width / (root.spectrumValues.length - 1)
                        const y = (1.0 - root.spectrumValues[i]) * height
                        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
                    }
                    ctx.stroke()
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Label { text: "Merkez: 100,000 MHz"; color: "#8fa4b7"; font.pixelSize: 11 }
            Label { text: "RBW: 1,953 kHz"; color: "#8fa4b7"; font.pixelSize: 11 }
            Item { Layout.fillWidth: true }
            Label { text: "Çerçeve " + root.sequenceNumber; color: "#8fa4b7"; font.pixelSize: 11 }
        }
    }

    Rectangle {
        id: inspector
        anchors.right: parent.right
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        width: 286
        color: "#141f2a"
        border.color: "#253646"

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12
            Label { text: "SEÇİLİ SİNYAL"; color: "#8fa4b7"; font.bold: true; font.pixelSize: 12 }
            Label { text: "100,500 MHz"; color: "#39bde8"; font.bold: true; font.pixelSize: 24 }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#253646" }
            Repeater {
                model: [
                    {"label": "Durum", "value": "Doğrulandı"},
                    {"label": "Bant Genişliği", "value": "—"},
                    {"label": "SNR", "value": "—"},
                    {"label": "Güç", "value": "−2,2 dBFS"},
                    {"label": "Kaynak", "value": "SigMF kaydı"}
                ]
                delegate: RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    Label { text: modelData.label; color: "#8fa4b7"; font.pixelSize: 11 }
                    Item { Layout.fillWidth: true }
                    Label { text: modelData.value; color: "#e7edf3"; font.bold: true; font.pixelSize: 11 }
                }
            }
            Item { Layout.fillHeight: true }
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "Kalibrasyon yapılmadı; güç değerleri dBFS ölçeğindedir."
                color: "#f59e0b"
                font.pixelSize: 11
            }
        }
    }
}
