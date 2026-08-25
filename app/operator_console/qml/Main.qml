import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

ApplicationWindow {
    id: root
    width: 1440
    height: 900
    minimumWidth: 1180
    minimumHeight: 680
    visible: true
    title: "Elektronik Harp Operatör Konsolu"
    color: "#050B11"

    property int workspace: 0
    property bool consoleOpen: false
    property bool sourcePanelOpen: true
    property real spectrumViewStart: 0
    property real spectrumViewEnd: 1
    property color appBackground: "#050B11"
    property color surface: "#0A131C"
    property color surfaceAlt: "#0D1822"
    property color raised: "#111F2A"
    property color border: "#20313D"
    property color borderStrong: "#304858"
    property color textPrimary: "#EDF5F7"
    property color textSecondary: "#8CA0AC"
    property color textMuted: "#607480"
    property color accent: "#31C3D2"
    property color accentSoft: "#12343D"
    property color success: "#59D39A"
    property color warning: "#F0BC62"
    property color danger: "#F07178"
    property int transitionDuration: operatorViewModel.reducedMotion ? 0 : 170

    function setSpectrumView(start, end) {
        var span = Math.max(0.02, Math.min(1.0, end - start))
        var boundedStart = Math.max(0.0, Math.min(1.0 - span, start))
        spectrumViewStart = boundedStart
        spectrumViewEnd = boundedStart + span
    }

    function zoomSpectrum(relativeCenter, factor) {
        var anchorRatio = Math.max(0.0, Math.min(1.0, relativeCenter))
        var oldSpan = spectrumViewEnd - spectrumViewStart
        var newSpan = Math.max(0.02, Math.min(1.0, oldSpan * factor))
        var anchor = spectrumViewStart + anchorRatio * oldSpan
        setSpectrumView(anchor - anchorRatio * newSpan, anchor + (1.0 - anchorRatio) * newSpan)
    }

    function panSpectrum(delta) {
        setSpectrumView(spectrumViewStart + delta, spectrumViewEnd + delta)
    }

    function resetSpectrumView() {
        spectrumViewStart = 0
        spectrumViewEnd = 1
    }

    function formatFrequency(hz) {
        if (!operatorViewModel.sourceReady) return "—"
        if (Math.abs(hz) >= 1000000000) return (hz / 1000000000).toFixed(6).replace(/0+$/, "").replace(/\.$/, "") + " GHz"
        if (Math.abs(hz) >= 1000000) return (hz / 1000000).toFixed(6).replace(/0+$/, "").replace(/\.$/, "") + " MHz"
        if (Math.abs(hz) >= 1000) return (hz / 1000).toFixed(3).replace(/0+$/, "").replace(/\.$/, "") + " kHz"
        return hz.toFixed(0) + " Hz"
    }

    function frequencyAt(normalized) {
        return operatorViewModel.centerFrequencyHz + (normalized - 0.5) * operatorViewModel.sampleRateHz
    }

    onSpectrumViewStartChanged: {
        spectrumCanvas.requestPaint()
        waterfall.requestPaint()
    }
    onSpectrumViewEndChanged: {
        spectrumCanvas.requestPaint()
        waterfall.requestPaint()
    }

    component Panel: Rectangle {
        color: root.surface
        border.color: root.border
        border.width: 1
        radius: 6
    }

    component SectionTitle: Label {
        color: root.textSecondary
        font.pixelSize: 10
        font.weight: Font.Bold
        font.letterSpacing: 1.35
    }

    component PrimaryButton: Button {
        id: control
        implicitHeight: 40
        font.pixelSize: 13
        font.weight: Font.DemiBold
        Accessible.name: text
        background: Rectangle {
            radius: 4
            color: control.enabled ? (control.down ? "#1B929E" : root.accent) : "#22313A"
            border.color: control.activeFocus ? "#C9F7FA" : "transparent"
            border.width: 2
            Behavior on color { ColorAnimation { duration: root.transitionDuration } }
        }
        contentItem: Text {
            text: control.text
            color: control.enabled ? "#041014" : "#788A94"
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    component QuietButton: Button {
        id: control
        implicitHeight: 38
        font.pixelSize: 13
        Accessible.name: text
        background: Rectangle {
            radius: 4
            color: control.checked ? root.accentSoft : control.down ? "#172A35" : root.surfaceAlt
            border.color: control.activeFocus || control.checked ? root.accent : root.border
            border.width: control.activeFocus ? 2 : 1
            Behavior on color { ColorAnimation { duration: root.transitionDuration } }
            Behavior on border.color { ColorAnimation { duration: root.transitionDuration } }
        }
        contentItem: Text {
            text: control.text
            color: control.enabled ? root.textPrimary : "#60727C"
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    component AppCombo: ComboBox {
        id: control
        implicitHeight: 36
        leftPadding: 10
        rightPadding: 28
        background: Rectangle {
            radius: 4
            color: "#09141C"
            border.color: control.activeFocus ? root.accent : root.border
        }
        contentItem: Text {
            text: control.displayText
            color: root.textPrimary
            font.pixelSize: 12
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        indicator: Text {
            x: control.width - width - 10
            anchors.verticalCenter: parent.verticalCenter
            text: "⌄"
            color: root.textSecondary
            font.pixelSize: 14
        }
        popup: Popup {
            y: control.height + 2
            width: control.width
            implicitHeight: contentItem.implicitHeight + 8
            padding: 4
            background: Rectangle { color: root.raised; border.color: root.border; radius: 4 }
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: control.popup.visible ? control.delegateModel : null
                currentIndex: control.highlightedIndex
            }
        }
    }

    component StateBadge: Rectangle {
        property string state: "Kullanılmıyor"
        implicitWidth: badgeText.implicitWidth + 18
        implicitHeight: 24
        radius: 12
        color: state === "Hazır" ? "#153B31" : state === "Çalışıyor" ? "#123B42" : state === "Hata" ? "#48252B" : "#25313A"
        border.color: state === "Hazır" ? root.success : state === "Çalışıyor" ? root.accent : state === "Hata" ? root.danger : "#536570"
        Behavior on color { ColorAnimation { duration: root.transitionDuration } }
        Behavior on border.color { ColorAnimation { duration: root.transitionDuration } }
        Text {
            id: badgeText
            anchors.centerIn: parent
            text: parent.state
            color: parent.border.color
            font.pixelSize: 11
            font.weight: Font.DemiBold
        }
    }

    component NavIcon: Canvas {
        required property string kind
        property color strokeColor: root.textSecondary
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

    FileDialog {
        id: sigmfDialog
        title: "SigMF metadata kaydını seç"
        nameFilters: ["SigMF metadata (*.sigmf-meta)"]
        fileMode: FileDialog.OpenFile
        onAccepted: operatorViewModel.openSigmf(selectedFile.toString())
    }

    FileDialog {
        id: wavDialog
        title: "Dinleme sesini kaydet"
        nameFilters: ["WAV ses dosyası (*.wav)"]
        fileMode: FileDialog.SaveFile
        defaultSuffix: "wav"
        onAccepted: operatorViewModel.exportListeningWav(selectedFile.toString())
    }

    Shortcut { sequence: "Ctrl+O"; onActivated: if (operatorViewModel.sourceMode === "sigmf") sigmfDialog.open() }
    Shortcut { sequence: "Space"; onActivated: operatorViewModel.playing ? operatorViewModel.pause() : operatorViewModel.startScan() }
    Shortcut { sequence: "Ctrl+1"; onActivated: root.workspace = 0 }
    Shortcut { sequence: "Ctrl+2"; onActivated: root.workspace = 1 }
    Shortcut { sequence: "Ctrl+3"; onActivated: root.workspace = 2 }
    Shortcut { sequence: "Ctrl+4"; onActivated: root.workspace = 3 }
    Shortcut { sequence: "Ctrl+B"; onActivated: root.sourcePanelOpen = !root.sourcePanelOpen }

    header: Rectangle {
        height: 76
        color: "#071018"
        border.color: root.border
        border.width: 1

        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 3
            color: root.accent
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            spacing: 18

            ColumnLayout {
                Layout.preferredWidth: 246
                spacing: 1
                Label { text: "ELEKTRONİK HARP"; color: root.accent; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 2.2 }
                Label { text: "Operatör Konsolu"; color: root.textPrimary; font.pixelSize: 19; font.weight: Font.DemiBold }
            }

            Rectangle {
                Layout.preferredWidth: 42
                Layout.preferredHeight: 26
                radius: 4
                color: root.accentSoft
                border.color: "#29606A"
                Label { anchors.centerIn: parent; text: "ED"; color: root.accent; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1 }
            }

            Rectangle { Layout.fillHeight: true; width: 1; color: root.border; Layout.topMargin: 17; Layout.bottomMargin: 17 }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                Label { text: operatorViewModel.sourceName; color: root.textPrimary; font.pixelSize: 12; font.weight: Font.DemiBold; elide: Text.ElideMiddle; Layout.fillWidth: true }
                Label { text: operatorViewModel.statusMessage; color: operatorViewModel.errorMessage ? root.danger : root.textSecondary; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
            }

            ColumnLayout {
                spacing: 2
                Label { text: "MERKEZ FREKANSI"; color: root.textMuted; font.pixelSize: 9; font.weight: Font.DemiBold }
                Label { text: operatorViewModel.centerFrequencyText; color: root.textPrimary; font.pixelSize: 13; font.family: "Consolas" }
            }
            ColumnLayout {
                spacing: 2
                Label { text: "ÖRNEKLEME HIZI"; color: root.textMuted; font.pixelSize: 9; font.weight: Font.DemiBold }
                Label { text: operatorViewModel.sampleRateText; color: root.textPrimary; font.pixelSize: 13; font.family: "Consolas" }
            }
            StateBadge { state: operatorViewModel.busy ? "Çalışıyor" : operatorViewModel.sourceState }
        }
    }

    footer: Rectangle {
        height: 28
        color: "#071018"
        border.color: root.border
        border.width: 1
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 12
            Rectangle { width: 7; height: 7; radius: 4; color: operatorViewModel.errorMessage ? root.danger : operatorViewModel.sourceReady ? root.success : root.textMuted }
            Label { text: operatorViewModel.sourceReady ? "Kaynak bağlı" : "Kaynak bekleniyor"; color: root.textSecondary; font.pixelSize: 9 }
            Rectangle { width: 1; Layout.fillHeight: true; Layout.topMargin: 7; Layout.bottomMargin: 7; color: root.border }
            Label { text: operatorViewModel.performanceText; color: root.textMuted; font.pixelSize: 9; font.family: "Consolas"; Layout.fillWidth: true }
            Button {
                flat: true
                implicitHeight: 24
                text: root.consoleOpen ? "Olay Konsolunu Kapat" : "Olay Konsolu"
                Accessible.name: text
                onClicked: root.consoleOpen = !root.consoleOpen
                contentItem: Text { text: parent.text; color: root.consoleOpen ? root.accent : root.textSecondary; font.pixelSize: 9; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { color: root.consoleOpen ? root.accentSoft : "transparent"; radius: 3 }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 76
            Layout.fillHeight: true
            color: "#071018"
            border.color: root.border
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.topMargin: 14
                anchors.bottomMargin: 12
                anchors.leftMargin: 7
                anchors.rightMargin: 7
                spacing: 6

                Repeater {
                    model: [
                        {"label": "Spektrum", "icon": "spectrum"},
                        {"label": "Dinleme", "icon": "listening"},
                        {"label": "Yön Bulma", "icon": "direction"},
                        {"label": "Sistem", "icon": "system"}
                    ]
                    delegate: Button {
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true
                        Layout.preferredHeight: 58
                        flat: true
                        Accessible.name: modelData.label
                        onClicked: root.workspace = index
                        background: Rectangle {
                            color: root.workspace === index ? root.accentSoft : "transparent"
                            radius: 4
                            Behavior on color { ColorAnimation { duration: root.transitionDuration } }
                            Rectangle {
                                visible: root.workspace === index
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                width: 2
                                height: 26
                                radius: 1
                                color: root.accent
                            }
                        }
                        contentItem: Column {
                            spacing: 5
                            NavIcon { anchors.horizontalCenter: parent.horizontalCenter; kind: modelData.icon; strokeColor: root.workspace === index ? root.accent : root.textSecondary }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.label; color: root.workspace === index ? root.textPrimary : root.textSecondary; font.pixelSize: 9 }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
                Button {
                    Layout.alignment: Qt.AlignHCenter
                    flat: true
                    Layout.fillWidth: true
                    Layout.preferredHeight: 42
                    text: operatorViewModel.reducedMotion ? "Hareket\nazaltıldı" : "Hareket"
                    Accessible.name: "Hareketi azalt"
                    onClicked: operatorViewModel.setReducedMotion(!operatorViewModel.reducedMotion)
                    contentItem: Text { text: parent.text; color: operatorViewModel.reducedMotion ? root.warning : root.textMuted; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.pixelSize: 8; wrapMode: Text.Wrap }
                    background: Rectangle { color: "transparent"; border.color: operatorViewModel.reducedMotion ? "#67532F" : "transparent"; radius: 4 }
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.workspace

            // OPERASYON
            Item {
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10

                    Panel {
                        id: sourcePanel
                        property real animatedWidth: root.sourcePanelOpen ? 244 : 0
                        Layout.preferredWidth: animatedWidth
                        Layout.minimumWidth: animatedWidth
                        Layout.maximumWidth: animatedWidth
                        Layout.fillHeight: true
                        visible: animatedWidth > 0.5
                        opacity: root.sourcePanelOpen ? 1 : 0
                        clip: true
                        Behavior on animatedWidth { NumberAnimation { duration: root.transitionDuration + 60; easing.type: Easing.OutCubic } }
                        Behavior on opacity { NumberAnimation { duration: root.transitionDuration } }
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12
                            RowLayout {
                                Layout.fillWidth: true
                                SectionTitle { text: "VERİ KAYNAĞI"; Layout.fillWidth: true }
                                StateBadge { state: operatorViewModel.busy ? "Çalışıyor" : operatorViewModel.sourceState }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                QuietButton {
                                    Layout.fillWidth: true
                                    text: "SigMF Kaydı"
                                    enabled: !operatorViewModel.busy
                                    checked: operatorViewModel.sourceMode === "sigmf"
                                    onClicked: operatorViewModel.setSourceMode("sigmf")
                                }
                                QuietButton {
                                    Layout.fillWidth: true
                                    text: "HackRF Canlı RX"
                                    enabled: !operatorViewModel.busy
                                    checked: operatorViewModel.sourceMode === "hackrf"
                                    onClicked: operatorViewModel.setSourceMode("hackrf")
                                }
                            }

                            Loader {
                                Layout.fillWidth: true
                                sourceComponent: operatorViewModel.sourceMode === "sigmf" ? sigmfControls : hackrfControls
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                            SectionTitle { text: "KAYNAK BİLGİLERİ" }
                            GridLayout {
                                columns: 2
                                Layout.fillWidth: true
                                columnSpacing: 10
                                rowSpacing: 7
                                Label { text: "Merkez"; color: root.textSecondary; font.pixelSize: 11 }
                                Label { text: operatorViewModel.centerFrequencyText; color: root.textPrimary; font.pixelSize: 11; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                                Label { text: "Örnekleme"; color: root.textSecondary; font.pixelSize: 11 }
                                Label { text: operatorViewModel.sampleRateText; color: root.textPrimary; font.pixelSize: 11; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                                Label { text: "Güç ölçeği"; color: root.textSecondary; font.pixelSize: 11 }
                                Label { text: operatorViewModel.calibrationText; color: root.warning; font.pixelSize: 11; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                                Label { text: "Kare"; color: root.textSecondary; font.pixelSize: 11 }
                                Label { text: operatorViewModel.frameIndex + " / " + operatorViewModel.frameCount; color: root.textPrimary; font.pixelSize: 11; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                            }

                            Item { Layout.fillHeight: true }
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: taskState.implicitHeight + 28
                                radius: 4
                                color: root.surfaceAlt
                                border.color: root.border
                                Label {
                                    id: taskState
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    text: operatorViewModel.sourceReady
                                          ? "Kaynak hazır. Spektrum izlemeyi başlatabilirsiniz."
                                          : "Bir SigMF kaydı açın veya bağlı HackRF alıcısını denetleyin."
                                    wrapMode: Text.Wrap
                                    color: operatorViewModel.sourceReady ? root.success : root.textSecondary
                                    font.pixelSize: 11
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 12

                        Panel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8
                                RowLayout {
                                    Layout.fillWidth: true
                                    Button {
                                        flat: true
                                        implicitWidth: 28
                                        implicitHeight: 24
                                        text: root.sourcePanelOpen ? "‹" : "›"
                                        Accessible.name: root.sourcePanelOpen ? "Kaynak panelini gizle" : "Kaynak panelini göster"
                                        onClicked: root.sourcePanelOpen = !root.sourcePanelOpen
                                        contentItem: Text { text: parent.text; color: root.textSecondary; font.pixelSize: 18; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                        background: Rectangle { color: parent.hovered ? root.surfaceAlt : "transparent"; border.color: parent.activeFocus ? root.accent : "transparent"; radius: 3 }
                                    }
                                    SectionTitle { text: "SPEKTRUM"; Layout.fillWidth: true }
                                    QuietButton { text: "−"; implicitWidth: 28; implicitHeight: 24; Accessible.name: "Frekans görünümünü uzaklaştır"; onClicked: root.zoomSpectrum(0.5, 1.4) }
                                    Label { text: (1 / (root.spectrumViewEnd - root.spectrumViewStart)).toFixed(1) + "×"; color: root.textSecondary; font.pixelSize: 9; font.family: "Consolas" }
                                    QuietButton { text: "+"; implicitWidth: 28; implicitHeight: 24; Accessible.name: "Frekans görünümünü yakınlaştır"; onClicked: root.zoomSpectrum(0.5, 0.7) }
                                    QuietButton { text: "1:1"; implicitWidth: 40; implicitHeight: 24; font.pixelSize: 9; Accessible.name: "Frekans görünümünü sıfırla"; enabled: root.spectrumViewStart > 0 || root.spectrumViewEnd < 1; onClicked: root.resetSpectrumView() }
                                    Rectangle {
                                        implicitWidth: liveTrace.implicitWidth + 16
                                        implicitHeight: 22
                                        radius: 3
                                        color: root.accentSoft
                                        Label { id: liveTrace; anchors.centerIn: parent; text: "ANLIK · dBFS"; color: root.accent; font.pixelSize: 9; font.weight: Font.Bold }
                                    }
                                    Label { text: operatorViewModel.performanceText; color: root.textSecondary; font.pixelSize: 10 }
                                }
                                Canvas {
                                    id: spectrumCanvas
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    property real selectionOpacity: 1
                                    property int lastSelectionId: -1
                                    Accessible.name: "Anlık güç spektrumu"
                                    onWidthChanged: operatorViewModel.setSpectrumViewportWidth(width)
                                    onSelectionOpacityChanged: requestPaint()
                                    NumberAnimation {
                                        id: selectionFade
                                        target: spectrumCanvas
                                        property: "selectionOpacity"
                                        from: 0
                                        to: 1
                                        duration: root.transitionDuration + 90
                                        easing.type: Easing.OutCubic
                                    }
                                    Connections {
                                        target: operatorViewModel
                                        function onSpectrumChanged() { spectrumCanvas.requestPaint() }
                                        function onDetectionsChanged() {
                                            var selectedId = operatorViewModel.selectedDetectionId
                                            if (selectedId !== spectrumCanvas.lastSelectionId) {
                                                spectrumCanvas.lastSelectionId = selectedId
                                                spectrumCanvas.selectionOpacity = selectedId >= 0 ? 0 : 1
                                                selectionFade.restart()
                                            }
                                            spectrumCanvas.requestPaint()
                                        }
                                    }
                                    onPaint: {
                                        var ctx = getContext("2d")
                                        ctx.reset()
                                        ctx.fillStyle = "#040A0F"
                                        ctx.fillRect(0, 0, width, height)
                                        var plotLeft = 42
                                        var plotRight = width - 8
                                        var plotTop = 8
                                        var plotBottom = height - 18
                                        var plotWidth = plotRight - plotLeft
                                        var plotHeight = plotBottom - plotTop
                                        ctx.strokeStyle = "#152630"
                                        ctx.lineWidth = 1
                                        for (var gx = 0; gx <= 8; gx++) {
                                            var x = plotLeft + gx * plotWidth / 8
                                            ctx.beginPath(); ctx.moveTo(x, plotTop); ctx.lineTo(x, plotBottom); ctx.stroke()
                                        }
                                        for (var gy = 0; gy <= 5; gy++) {
                                            var y = plotTop + gy * plotHeight / 5
                                            ctx.beginPath(); ctx.moveTo(plotLeft, y); ctx.lineTo(plotRight, y); ctx.stroke()
                                        }
                                        var selectionStart = operatorViewModel.selectedRegionStartNormalized
                                        var selectionEnd = operatorViewModel.selectedRegionEndNormalized
                                        var selectionPeak = operatorViewModel.selectedRegionPeakNormalized
                                        if (selectionStart >= 0 && selectionEnd >= selectionStart) {
                                            var visibleSelectionStart = Math.max(root.spectrumViewStart, selectionStart)
                                            var visibleSelectionEnd = Math.min(root.spectrumViewEnd, selectionEnd)
                                            var coarseX1 = plotLeft + (visibleSelectionStart - root.spectrumViewStart) * plotWidth / (root.spectrumViewEnd - root.spectrumViewStart)
                                            var coarseX2 = plotLeft + (visibleSelectionEnd - root.spectrumViewStart) * plotWidth / (root.spectrumViewEnd - root.spectrumViewStart)
                                            if (coarseX2 - coarseX1 < 3) {
                                                var coarseCenter = plotLeft + (selectionPeak - root.spectrumViewStart) * plotWidth / (root.spectrumViewEnd - root.spectrumViewStart)
                                                coarseX1 = coarseCenter - 1.5; coarseX2 = coarseCenter + 1.5
                                            }
                                            if (visibleSelectionEnd >= visibleSelectionStart && coarseX2 >= plotLeft && coarseX1 <= plotRight) {
                                                coarseX1 = Math.max(plotLeft, coarseX1); coarseX2 = Math.min(plotRight, coarseX2)
                                                ctx.globalAlpha = spectrumCanvas.selectionOpacity
                                                ctx.fillStyle = "rgba(240,188,98,0.10)"
                                                ctx.fillRect(coarseX1, plotTop, coarseX2 - coarseX1, plotHeight)
                                                ctx.strokeStyle = "rgba(240,188,98,0.82)"
                                                ctx.setLineDash([4, 3]); ctx.strokeRect(coarseX1, plotTop, coarseX2 - coarseX1, plotHeight); ctx.setLineDash([])
                                                ctx.globalAlpha = 1
                                            }
                                        }
                                        var analysisStart = operatorViewModel.analysisSpanStartNormalized
                                        var analysisEnd = operatorViewModel.analysisSpanEndNormalized
                                        if (analysisStart >= 0 && analysisEnd >= analysisStart) {
                                            var analysisX1 = plotLeft + (analysisStart - root.spectrumViewStart) * plotWidth / (root.spectrumViewEnd - root.spectrumViewStart)
                                            var analysisX2 = plotLeft + (analysisEnd - root.spectrumViewStart) * plotWidth / (root.spectrumViewEnd - root.spectrumViewStart)
                                            if (analysisX2 >= plotLeft && analysisX1 <= plotRight) {
                                                analysisX1 = Math.max(plotLeft, analysisX1); analysisX2 = Math.min(plotRight, analysisX2)
                                                ctx.globalAlpha = spectrumCanvas.selectionOpacity
                                                ctx.fillStyle = operatorViewModel.analysisSpanConfirmed ? "rgba(49,195,210,0.13)" : "rgba(49,195,210,0.07)"
                                                ctx.fillRect(analysisX1, plotTop, Math.max(2, analysisX2 - analysisX1), plotHeight)
                                                ctx.strokeStyle = operatorViewModel.analysisSpanConfirmed ? "rgba(49,195,210,0.95)" : "rgba(49,195,210,0.55)"
                                                ctx.strokeRect(analysisX1, plotTop, Math.max(2, analysisX2 - analysisX1), plotHeight)
                                                ctx.globalAlpha = 1
                                            }
                                        }
                                        var values = operatorViewModel.spectrumValues
                                        if (!values || values.length < 2) return
                                        var firstIndex = Math.max(0, Math.floor(root.spectrumViewStart * (values.length - 1)))
                                        var lastIndex = Math.min(values.length - 1, Math.ceil(root.spectrumViewEnd * (values.length - 1)))
                                        var visibleDenominator = Math.max(1, lastIndex - firstIndex)
                                        var low = operatorViewModel.spectrumMinDb
                                        var high = operatorViewModel.spectrumMaxDb
                                        ctx.fillStyle = "#647987"
                                        ctx.font = "9px Consolas"
                                        ctx.textAlign = "right"
                                        ctx.textBaseline = "middle"
                                        for (var labelIndex = 0; labelIndex <= 5; labelIndex++) {
                                            var labelY = plotTop + labelIndex * plotHeight / 5
                                            var labelValue = high - labelIndex * (high - low) / 5
                                            ctx.fillText(labelValue.toFixed(0), plotLeft - 6, labelY)
                                        }
                                        var fill = ctx.createLinearGradient(0, plotTop, 0, plotBottom)
                                        fill.addColorStop(0, "rgba(49,195,210,0.22)")
                                        fill.addColorStop(1, "rgba(49,195,210,0.00)")
                                        ctx.beginPath()
                                        for (var fillIndex = firstIndex; fillIndex <= lastIndex; fillIndex++) {
                                            var fillX = plotLeft + (fillIndex - firstIndex) * plotWidth / visibleDenominator
                                            var fillY = plotBottom - Math.max(0, Math.min(1, (values[fillIndex] - low) / (high - low))) * plotHeight
                                            if (fillIndex === firstIndex) ctx.moveTo(fillX, fillY); else ctx.lineTo(fillX, fillY)
                                        }
                                        ctx.lineTo(plotRight, plotBottom); ctx.lineTo(plotLeft, plotBottom); ctx.closePath()
                                        ctx.fillStyle = fill; ctx.fill()
                                        ctx.strokeStyle = root.accent
                                        ctx.lineWidth = 1.6
                                        ctx.beginPath()
                                        for (var i = firstIndex; i <= lastIndex; i++) {
                                            var px = plotLeft + (i - firstIndex) * plotWidth / visibleDenominator
                                            var py = plotBottom - Math.max(0, Math.min(1, (values[i] - low) / (high - low))) * plotHeight
                                            if (i === firstIndex) ctx.moveTo(px, py); else ctx.lineTo(px, py)
                                        }
                                        ctx.stroke()
                                        ctx.strokeStyle = "rgba(237,245,247,0.32)"
                                        ctx.setLineDash([3, 4])
                                        if (root.spectrumViewStart <= 0.5 && root.spectrumViewEnd >= 0.5) {
                                            var centerX = plotLeft + (0.5 - root.spectrumViewStart) * plotWidth / (root.spectrumViewEnd - root.spectrumViewStart)
                                            ctx.beginPath(); ctx.moveTo(centerX, plotTop); ctx.lineTo(centerX, plotBottom); ctx.stroke()
                                        }
                                        ctx.setLineDash([])
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        acceptedButtons: Qt.LeftButton
                                        hoverEnabled: true
                                        cursorShape: pressed ? Qt.ClosedHandCursor : Qt.CrossCursor
                                        property real pressX: 0
                                        property real pressStart: 0
                                        property real pressEnd: 1
                                        onPressed: function(mouse) { pressX = mouse.x; pressStart = root.spectrumViewStart; pressEnd = root.spectrumViewEnd }
                                        onPositionChanged: function(mouse) {
                                            if (!pressed) return
                                            var span = pressEnd - pressStart
                                            var delta = -(mouse.x - pressX) * span / Math.max(1, width)
                                            root.setSpectrumView(pressStart + delta, pressEnd + delta)
                                        }
                                        onWheel: function(wheel) { root.zoomSpectrum(wheel.x / Math.max(1, width), wheel.angleDelta.y > 0 ? 0.75 : 1.333333) }
                                        onDoubleClicked: root.resetSpectrumView()
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: root.formatFrequency(root.frequencyAt(root.spectrumViewStart)); color: root.textSecondary; font.pixelSize: 10 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: root.formatFrequency(root.frequencyAt((root.spectrumViewStart + root.spectrumViewEnd) / 2)); color: root.textPrimary; font.pixelSize: 10 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: root.formatFrequency(root.frequencyAt(root.spectrumViewEnd)); color: root.textSecondary; font.pixelSize: 10 }
                                }
                            }
                        }

                        Panel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 168
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8
                                RowLayout {
                                    Layout.fillWidth: true
                                    SectionTitle { text: "SPEKTROGRAM"; Layout.fillWidth: true }
                                    Label { text: root.spectrumViewStart > 0 || root.spectrumViewEnd < 1 ? "SPEKTRUMLA BAĞLI" : "TAM BANT"; color: root.accent; font.pixelSize: 9; font.weight: Font.Bold }
                                    Label { text: "SON 48 KARE"; color: root.textMuted; font.pixelSize: 9; font.family: "Consolas" }
                                }
                                Canvas {
                                    id: waterfall
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    property var history: []
                                    Connections {
                                        target: operatorViewModel
                                        function onSpectrumChanged() {
                                            var values = operatorViewModel.spectrumValues
                                            if (values && values.length) {
                                                waterfall.history = waterfall.history.concat([values.slice(0)])
                                                if (waterfall.history.length > 48) waterfall.history = waterfall.history.slice(-48)
                                            } else waterfall.history = []
                                            waterfall.requestPaint()
                                        }
                                    }
                                    onPaint: {
                                        var ctx = getContext("2d")
                                        ctx.reset(); ctx.fillStyle = "#040A0F"; ctx.fillRect(0, 0, width, height)
                                        var low = operatorViewModel.spectrumMinDb
                                        var high = operatorViewModel.spectrumMaxDb
                                        for (var row = 0; row < history.length; row++) {
                                            var vals = history[row]
                                            var firstIndex = Math.max(0, Math.floor(root.spectrumViewStart * (vals.length - 1)))
                                            var lastIndex = Math.min(vals.length - 1, Math.ceil(root.spectrumViewEnd * (vals.length - 1)))
                                            var visibleCount = Math.max(1, lastIndex - firstIndex + 1)
                                            var step = Math.max(1, Math.floor(visibleCount / Math.max(1, width / 3)))
                                            var y = height - (history.length - row) * height / 48
                                            var rh = Math.ceil(height / 48)
                                            for (var col = firstIndex; col <= lastIndex; col += step) {
                                                var level = Math.max(0, Math.min(1, (vals[col] - low) / (high - low)))
                                                var red = level < 0.65 ? Math.round(7 + 48 * level) : Math.round(55 + 190 * (level - 0.65) / 0.35)
                                                var green = level < 0.45 ? Math.round(20 + 180 * level) : Math.round(101 + 118 * (level - 0.45) / 0.55)
                                                var blue = level < 0.70 ? Math.round(42 + 190 * level) : Math.round(175 - 115 * (level - 0.70) / 0.30)
                                                ctx.fillStyle = "rgb(" + red + "," + green + "," + blue + ")"
                                                ctx.fillRect((col - firstIndex) * width / visibleCount, y, Math.ceil(step * width / visibleCount), rh)
                                            }
                                        }
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        acceptedButtons: Qt.LeftButton
                                        hoverEnabled: true
                                        cursorShape: pressed ? Qt.ClosedHandCursor : Qt.CrossCursor
                                        property real pressX: 0
                                        property real pressStart: 0
                                        property real pressEnd: 1
                                        onPressed: function(mouse) { pressX = mouse.x; pressStart = root.spectrumViewStart; pressEnd = root.spectrumViewEnd }
                                        onPositionChanged: function(mouse) {
                                            if (!pressed) return
                                            var span = pressEnd - pressStart
                                            var delta = -(mouse.x - pressX) * span / Math.max(1, width)
                                            root.setSpectrumView(pressStart + delta, pressEnd + delta)
                                        }
                                        onWheel: function(wheel) { root.zoomSpectrum(wheel.x / Math.max(1, width), wheel.angleDelta.y > 0 ? 0.75 : 1.333333) }
                                        onDoubleClicked: root.resetSpectrumView()
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            PrimaryButton { text: "Taramayı Başlat"; enabled: operatorViewModel.sourceReady && !operatorViewModel.playing && !operatorViewModel.busy; onClicked: operatorViewModel.startScan() }
                            QuietButton { text: "Duraklat"; enabled: operatorViewModel.playing; onClicked: operatorViewModel.pause() }
                            Label { Layout.fillWidth: true; text: "Boşluk: başlat/duraklat"; color: root.textSecondary; font.pixelSize: 10; horizontalAlignment: Text.AlignRight }
                        }
                    }

                    Panel {
                        Layout.preferredWidth: 326
                        Layout.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10
                            RowLayout {
                                Layout.fillWidth: true
                                SectionTitle { text: "TESPİTLER"; Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: detectionCount.implicitWidth + 14
                                    implicitHeight: 22
                                    radius: 11
                                    color: root.accentSoft
                                    Label { id: detectionCount; anchors.centerIn: parent; text: operatorViewModel.detections.length; color: root.accent; font.pixelSize: 10; font.weight: Font.Bold }
                                }
                            }
                            ListView {
                                id: detectionList
                                Layout.fillWidth: true
                                Layout.preferredHeight: root.height < 780 ? 190 : 250
                                clip: true
                                spacing: 3
                                model: operatorViewModel.detections
                                delegate: Button {
                                    required property var modelData
                                    width: ListView.view.width
                                    height: 56
                                    Accessible.name: modelData.title + ", " + modelData.state
                                    onPressed: operatorViewModel.selectDetection(modelData.eventId)
                                    background: Rectangle {
                                        radius: 4
                                        color: operatorViewModel.selectedDetectionId === modelData.eventId ? root.accentSoft : root.surfaceAlt
                                        border.color: operatorViewModel.selectedDetectionId === modelData.eventId ? root.accent : root.border
                                        Behavior on color { ColorAnimation { duration: root.transitionDuration } }
                                        Behavior on border.color { ColorAnimation { duration: root.transitionDuration } }
                                        Rectangle {
                                            visible: operatorViewModel.selectedDetectionId === modelData.eventId
                                            anchors.left: parent.left
                                            anchors.top: parent.top
                                            anchors.bottom: parent.bottom
                                            width: 2
                                            color: root.accent
                                        }
                                    }
                                    contentItem: ColumnLayout {
                                        spacing: 3
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Label { text: modelData.title; color: root.textPrimary; font.pixelSize: 12; font.weight: Font.DemiBold; Layout.fillWidth: true }
                                            Label { text: modelData.state; color: modelData.stateKey === "confirmed" ? root.success : root.warning; font.pixelSize: 10 }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Label { text: modelData.frequency; color: root.textSecondary; font.pixelSize: 10; Layout.fillWidth: true }
                                            Label { text: "Δ " + modelData.snr; color: root.textSecondary; font.pixelSize: 10 }
                                        }
                                    }
                                }
                            }
                            Label {
                                visible: operatorViewModel.detections.length === 0
                                text: operatorViewModel.sourceReady ? "Doğrulanmış aday bekleniyor." : "Önce gerçek bir kaynak hazırlayın."
                                color: root.textSecondary
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }
                            Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                            RowLayout {
                                Layout.fillWidth: true
                                SectionTitle { text: "SİNYAL ÖLÇÜMÜ"; Layout.fillWidth: true }
                                Label {
                                    text: operatorViewModel.parameterRows.length > 0 ? "SONUÇ HAZIR" : operatorViewModel.analysisSpanConfirmed ? "ARALIK ONAYLI" : "SEÇİM BEKLİYOR"
                                    color: operatorViewModel.parameterRows.length > 0 ? root.success : operatorViewModel.analysisSpanConfirmed ? root.accent : root.textMuted
                                    font.pixelSize: 8
                                    font.weight: Font.Bold
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 5
                                Repeater {
                                    model: ["1  Tespit", "2  Aralık", "3  Ölçüm"]
                                    delegate: Rectangle {
                                        required property string modelData
                                        required property int index
                                        Layout.fillWidth: true
                                        implicitHeight: 24
                                        radius: 3
                                        color: (index === 0 && operatorViewModel.selectedDetectionReady)
                                               || (index === 1 && operatorViewModel.analysisSpanConfirmed)
                                               || (index === 2 && operatorViewModel.parameterRows.length > 0) ? root.accentSoft : "#091219"
                                        border.color: (index === 0 && operatorViewModel.selectedDetectionReady)
                                                      || (index === 1 && operatorViewModel.analysisSpanConfirmed)
                                                      || (index === 2 && operatorViewModel.parameterRows.length > 0) ? "#28616B" : root.border
                                        Label { anchors.centerIn: parent; text: modelData; color: parent.border.color === root.border ? root.textMuted : root.accent; font.pixelSize: 8; font.weight: Font.DemiBold }
                                    }
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                text: operatorViewModel.parameterCapabilityReady
                                      ? "Dört ardışık gözlem ve operatör onaylı analiz aralığı kullanılır."
                                      : "Doğrulanmış parametre ölçüm profili kullanılamıyor."
                                color: operatorViewModel.parameterCapabilityReady ? root.textSecondary : root.warning
                                font.pixelSize: 10
                                wrapMode: Text.Wrap
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Label { text: "Analiz alt frekansı (MHz)"; color: root.textSecondary; font.pixelSize: 9 }
                                    TextField {
                                        id: analysisLowerMHz
                                        Layout.fillWidth: true
                                        text: operatorViewModel.analysisLowerMHzText
                                        color: root.textPrimary
                                        validator: DoubleValidator { decimals: 6; notation: DoubleValidator.StandardNotation }
                                        Accessible.name: "Analiz alt frekansı megahertz"
                                        background: Rectangle { color: "#09141C"; border.color: analysisLowerMHz.activeFocus ? root.accent : root.border; radius: 4 }
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Label { text: "Analiz üst frekansı (MHz)"; color: root.textSecondary; font.pixelSize: 9 }
                                    TextField {
                                        id: analysisUpperMHz
                                        Layout.fillWidth: true
                                        text: operatorViewModel.analysisUpperMHzText
                                        color: root.textPrimary
                                        validator: DoubleValidator { decimals: 6; notation: DoubleValidator.StandardNotation }
                                        Accessible.name: "Analiz üst frekansı megahertz"
                                        background: Rectangle { color: "#09141C"; border.color: analysisUpperMHz.activeFocus ? root.accent : root.border; radius: 4 }
                                    }
                                }
                            }
                            QuietButton {
                                Layout.fillWidth: true
                                text: operatorViewModel.analysisSpanConfirmed ? "Analiz Aralığı Onaylandı" : "Analiz Aralığını Onayla"
                                enabled: operatorViewModel.selectedDetectionReady && operatorViewModel.parameterCapabilityReady && !operatorViewModel.busy
                                onClicked: operatorViewModel.confirmAnalysisSpan(Number(analysisLowerMHz.text), Number(analysisUpperMHz.text))
                            }
                            PrimaryButton {
                                Layout.fillWidth: true
                                text: "Ölçümü Başlat"
                                enabled: operatorViewModel.measurementReady && !operatorViewModel.busy
                                onClicked: operatorViewModel.requestMeasurement()
                            }
                            ListView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                spacing: 2
                                model: operatorViewModel.parameterRows
                                delegate: RowLayout {
                                    required property var modelData
                                    width: ListView.view.width
                                    height: 26
                                    Label { text: modelData.label; color: root.textSecondary; font.pixelSize: 10; Layout.fillWidth: true }
                                    Label { text: modelData.value; color: root.textPrimary; font.pixelSize: 10; font.family: "Consolas"; font.weight: Font.DemiBold }
                                }
                            }
                            Label {
                                visible: operatorViewModel.parameterRows.length === 0
                                text: operatorViewModel.selectedDetectionReady
                                      ? (operatorViewModel.analysisSpanConfirmed
                                         ? "Dört ardışık gözlem ve ölçüm komutu bekleniyor."
                                         : "Önerilen analiz aralığını doğrulayıp onaylayın.")
                                      : "Doğrulanmış bir tespit seçin."
                                color: root.textSecondary
                                font.pixelSize: 10
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }
                            Label {
                                visible: root.height >= 780
                                text: "Sayılar kalibrasyonsuz göreli ölçümlerdir; kalite kapısı geçmeyen alanlarda sonuç gösterilmez."
                                color: root.textSecondary
                                font.pixelSize: 10
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }

            // DİNLEME
            Item {
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 14

                    Panel {
                        Layout.preferredWidth: 350
                        Layout.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 11
                            SectionTitle { text: "ANALOG KANAL SEÇİMİ" }
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 70
                                radius: 4
                                color: root.surfaceAlt
                                border.color: operatorViewModel.selectedDetectionReady ? root.accent : root.border
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 11
                                    spacing: 3
                                    Label { text: operatorViewModel.listeningDetectionTitle; color: root.textPrimary; font.pixelSize: 12; font.weight: Font.DemiBold }
                                    Label { text: operatorViewModel.listeningDetectionFrequencyText; color: root.accent; font.pixelSize: 11; font.family: "Consolas" }
                                    Label { text: "Kaynak süresi: " + operatorViewModel.sourceDurationText; color: root.textMuted; font.pixelSize: 9 }
                                }
                            }
                            Label { text: "Demodülasyon"; color: root.textSecondary; font.pixelSize: 10 }
                            AppCombo {
                                id: listeningMode
                                Layout.fillWidth: true
                                model: [{text: "Genlik Modülasyonu (AM)", value: "am"}, {text: "Dar Bant FM (NFM)", value: "nfm"}]
                                textRole: "text"
                                Accessible.name: "Dinleme modu"
                            }
                            Label { text: "Merkez frekans ofseti (kHz)"; color: root.textSecondary; font.pixelSize: 10 }
                            RowLayout {
                                Layout.fillWidth: true
                                TextField {
                                    id: listeningOffset
                                    Layout.fillWidth: true
                                    text: operatorViewModel.selectedDetectionOffsetKHz.toFixed(3)
                                    color: root.textPrimary
                                    validator: DoubleValidator { decimals: 3; notation: DoubleValidator.StandardNotation }
                                    Accessible.name: "Dinleme merkez frekans ofseti kilohertz"
                                    background: Rectangle { color: "#09141C"; border.color: listeningOffset.activeFocus ? root.accent : root.border; radius: 4 }
                                }
                                QuietButton {
                                    text: "Tespiti Kullan"
                                    implicitHeight: 36
                                    font.pixelSize: 10
                                    enabled: operatorViewModel.selectedDetectionReady
                                    onClicked: listeningOffset.text = operatorViewModel.selectedDetectionOffsetKHz.toFixed(3)
                                }
                            }
                            Label { text: "Kanal bant genişliği (kHz)"; color: root.textSecondary; font.pixelSize: 10 }
                            TextField {
                                id: listeningBandwidth
                                Layout.fillWidth: true
                                text: "16"
                                color: root.textPrimary
                                validator: DoubleValidator { bottom: 2; top: 200; decimals: 1; notation: DoubleValidator.StandardNotation }
                                Accessible.name: "Dinleme kanal bant genişliği kilohertz"
                                background: Rectangle { color: "#09141C"; border.color: listeningBandwidth.activeFocus ? root.accent : root.border; radius: 4 }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: "Ses seviyesi"; color: root.textSecondary; font.pixelSize: 10; Layout.fillWidth: true }
                                Label { text: Math.round(listeningVolume.value * 100) + "%"; color: root.textPrimary; font.pixelSize: 10; font.family: "Consolas" }
                            }
                            Slider {
                                id: listeningVolume
                                Layout.fillWidth: true
                                from: 0
                                to: 1
                                value: 0.8
                                Accessible.name: "Dinleme ses seviyesi"
                            }
                            PrimaryButton {
                                Layout.fillWidth: true
                                text: "Kanal Sesini Hazırla"
                                enabled: operatorViewModel.selectedDetectionReady && operatorViewModel.sourceReady && !operatorViewModel.busy
                                onClicked: operatorViewModel.requestListening(
                                    listeningMode.model[listeningMode.currentIndex].value,
                                    Number(listeningOffset.text),
                                    Number(listeningBandwidth.text),
                                    listeningVolume.value
                                )
                            }
                            Item { Layout.fillHeight: true }
                            Label {
                                Layout.fillWidth: true
                                text: "Kesintisiz dinleme için kaynakta en az 5 saniyelik I/Q gerekir. Daha kısa kayıt yalnız açıkça etiketli kısa önizleme üretir."
                                color: root.warning
                                font.pixelSize: 10
                                wrapMode: Text.Wrap
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 14
                        Panel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 280
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 10
                                RowLayout {
                                    Layout.fillWidth: true
                                    SectionTitle { text: "SES DALGA BİÇİMİ"; Layout.fillWidth: true }
                                    StateBadge { state: operatorViewModel.listeningReady ? "Hazır" : operatorViewModel.busy ? "Çalışıyor" : "Kullanılmıyor" }
                                }
                                Canvas {
                                    id: listeningWaveformCanvas
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    Accessible.name: "Demodüle edilmiş ses dalga biçimi"
                                    Connections { target: operatorViewModel; function onListeningChanged() { listeningWaveformCanvas.requestPaint() } }
                                    onPaint: {
                                        var ctx = getContext("2d")
                                        ctx.reset(); ctx.fillStyle = "#040A0F"; ctx.fillRect(0, 0, width, height)
                                        ctx.strokeStyle = "#152630"; ctx.lineWidth = 1
                                        for (var gx = 0; gx <= 8; gx++) { var x = gx * width / 8; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke() }
                                        for (var gy = 0; gy <= 4; gy++) { var y = gy * height / 4; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke() }
                                        var values = operatorViewModel.listeningWaveform
                                        if (!values || values.length < 2) {
                                            ctx.fillStyle = root.textMuted; ctx.font = "11px Segoe UI"; ctx.textAlign = "center"; ctx.textBaseline = "middle"
                                            ctx.fillText("Hazırlanmış kanal sesi yok", width / 2, height / 2)
                                            return
                                        }
                                        ctx.strokeStyle = root.accent; ctx.lineWidth = 1.4; ctx.beginPath()
                                        for (var index = 0; index < values.length; index++) {
                                            var px = index * width / (values.length - 1)
                                            var py = height / 2 - values[index] * height * 0.42
                                            if (index === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py)
                                        }
                                        ctx.stroke()
                                    }
                                }
                            }
                        }
                        Panel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 10
                                RowLayout {
                                    Layout.fillWidth: true
                                    SectionTitle { text: "DİNLEME SONUCU"; Layout.fillWidth: true }
                                    Label {
                                        text: operatorViewModel.listeningShortPreview ? "KISA ÖNİZLEME" : operatorViewModel.listeningReady ? "KESİNTİSİZ" : "BEKLENİYOR"
                                        color: operatorViewModel.listeningShortPreview ? root.warning : operatorViewModel.listeningReady ? root.success : root.textMuted
                                        font.pixelSize: 9
                                        font.weight: Font.Bold
                                    }
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: operatorViewModel.listeningState
                                    color: operatorViewModel.listeningShortPreview ? root.warning : operatorViewModel.listeningReady ? root.success : root.textSecondary
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }
                                Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                                ListView {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    model: operatorViewModel.listeningRows
                                    delegate: RowLayout {
                                        required property var modelData
                                        width: ListView.view.width
                                        height: 30
                                        Label { text: modelData.label; color: root.textSecondary; font.pixelSize: 10; Layout.fillWidth: true }
                                        Label { text: modelData.value; color: root.textPrimary; font.pixelSize: 10; font.family: "Consolas"; font.weight: Font.DemiBold }
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    QuietButton { text: "Oynat"; enabled: operatorViewModel.listeningAudioAvailable && !operatorViewModel.busy; onClicked: operatorViewModel.playListening() }
                                    QuietButton { text: "Duraklat"; enabled: operatorViewModel.listeningAudioAvailable && !operatorViewModel.busy; onClicked: operatorViewModel.pauseListening() }
                                    QuietButton { text: "Durdur"; enabled: operatorViewModel.listeningReady && !operatorViewModel.busy; onClicked: operatorViewModel.stopListening() }
                                    Item { Layout.fillWidth: true }
                                    PrimaryButton { text: "WAV Dışa Aktar"; enabled: operatorViewModel.listeningReady && !operatorViewModel.busy; onClicked: wavDialog.open() }
                                }
                            }
                        }
                    }
                }
            }

            // YÖN BULMA
            Item {
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 14

                    Panel {
                        Layout.preferredWidth: 340
                        Layout.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 12
                            SectionTitle { text: "ANTEN AÇISI–GÜÇ ÖLÇÜMÜ" }
                            Label { text: "Her kayıt, etkin I/Q karesinin gerçek dBFS gücünü anten açısıyla bağlar."; color: root.textSecondary; font.pixelSize: 11; wrapMode: Text.Wrap; Layout.fillWidth: true }

                            Label { text: "Anten dönüş açısı"; color: root.textSecondary; font.pixelSize: 11 }
                            TextField {
                                id: antennaAngle
                                Layout.fillWidth: true
                                text: "0"
                                color: root.textPrimary
                                validator: IntValidator { bottom: 0; top: 359 }
                                inputMethodHints: Qt.ImhDigitsOnly
                                Accessible.name: "Anten dönüş açısı"
                                background: Rectangle { color: "#09141C"; border.color: antennaAngle.activeFocus ? root.accent : root.border; radius: 4 }
                            }
                            Label { text: "0° referansı"; color: root.textSecondary; font.pixelSize: 11 }
                            AppCombo {
                                id: referenceMode
                                Layout.fillWidth: true
                                model: [
                                    {text: "Gerçek kuzey / 0°", value: "north"},
                                    {text: "Anten Referans Yönü", value: "manual"},
                                    {text: "Referans yok", value: "none"}
                                ]
                                textRole: "text"
                                Accessible.name: "Anten sıfır derece referansı"
                            }
                            Label { text: "Anten Referans Yönü"; color: root.textSecondary; font.pixelSize: 11; visible: referenceMode.currentIndex === 1 }
                            TextField {
                                id: referenceAngle
                                Layout.fillWidth: true
                                text: "0"
                                color: root.textPrimary
                                validator: IntValidator { bottom: 0; top: 359 }
                                inputMethodHints: Qt.ImhDigitsOnly
                                visible: referenceMode.currentIndex === 1
                                Accessible.name: "Anten Referans Yönü"
                                background: Rectangle { color: "#09141C"; border.color: referenceAngle.activeFocus ? root.accent : root.border; radius: 4 }
                            }
                            PrimaryButton {
                                Layout.fillWidth: true
                                text: "Güç Ölçümünü Kaydet"
                                enabled: operatorViewModel.sourceReady && !operatorViewModel.busy
                                onClicked: operatorViewModel.addDirectionMeasurement(Number(antennaAngle.text), referenceMode.model[referenceMode.currentIndex].value, Number(referenceAngle.text))
                            }
                            QuietButton { Layout.fillWidth: true; text: "Ölçümleri Temizle"; enabled: operatorViewModel.directionPoints.length > 0; onClicked: operatorViewModel.clearDirectionMeasurements() }
                            Item { Layout.fillHeight: true }
                            Label { text: "Faz uyumlu çok kanallı DoA veya menzil sonucu üretilmez."; color: root.warning; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 14
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 190
                            Layout.minimumHeight: 190
                            Layout.maximumHeight: 190
                            Panel {
                                Layout.preferredWidth: 230
                                Layout.fillHeight: true
                                Canvas {
                                    id: bearingCompass
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    property real indicatedBearing: -1
                                    Accessible.name: "Kerteriz göstergesi"
                                    onIndicatedBearingChanged: requestPaint()
                                    Behavior on indicatedBearing {
                                        NumberAnimation { duration: root.transitionDuration + 130; easing.type: Easing.OutCubic }
                                    }
                                    Connections {
                                        target: operatorViewModel
                                        function onDirectionChanged() {
                                            var targetBearing = parseFloat(operatorViewModel.bearingText)
                                            bearingCompass.indicatedBearing = isNaN(targetBearing) ? -1 : targetBearing
                                            bearingCompass.requestPaint()
                                        }
                                    }
                                    onPaint: {
                                        var ctx = getContext("2d")
                                        ctx.reset(); ctx.clearRect(0, 0, width, height)
                                        var cx = width / 2; var cy = height / 2 + 4
                                        var radius = Math.min(width, height) * 0.37
                                        ctx.strokeStyle = root.borderStrong; ctx.lineWidth = 1.2
                                        ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2); ctx.stroke()
                                        ctx.font = "bold 9px Segoe UI"; ctx.fillStyle = root.textSecondary; ctx.textAlign = "center"; ctx.textBaseline = "middle"
                                        ctx.fillText("K", cx, cy - radius - 11); ctx.fillText("D", cx + radius + 11, cy)
                                        ctx.fillText("G", cx, cy + radius + 11); ctx.fillText("B", cx - radius - 11, cy)
                                        for (var tick = 0; tick < 24; tick++) {
                                            var angle = tick * Math.PI * 2 / 24 - Math.PI / 2
                                            var inner = radius - (tick % 6 === 0 ? 8 : 4)
                                            ctx.beginPath(); ctx.moveTo(cx + Math.cos(angle) * inner, cy + Math.sin(angle) * inner)
                                            ctx.lineTo(cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius); ctx.stroke()
                                        }
                                        var bearing = bearingCompass.indicatedBearing
                                        if (bearing >= 0) {
                                            var bearingRad = bearing * Math.PI / 180 - Math.PI / 2
                                            ctx.strokeStyle = root.success; ctx.lineWidth = 2.5
                                            ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(bearingRad) * (radius - 8), cy + Math.sin(bearingRad) * (radius - 8)); ctx.stroke()
                                            ctx.fillStyle = root.success; ctx.beginPath(); ctx.arc(cx, cy, 4, 0, Math.PI * 2); ctx.fill()
                                        } else {
                                            ctx.fillStyle = root.textMuted; ctx.font = "10px Segoe UI"; ctx.fillText("Ölçüm bekleniyor", cx, cy)
                                        }
                                    }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                spacing: 10
                                Panel {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    RowLayout { anchors.fill: parent; anchors.leftMargin: 20; anchors.rightMargin: 20
                                        ColumnLayout { Layout.fillWidth: true; spacing: 4
                                            Label { text: "BAĞIL GELİŞ AÇISI"; color: root.textSecondary; font.pixelSize: 10; font.weight: Font.DemiBold }
                                            Label { text: "Antenin tanımlı 0° eksenine göre"; color: root.textMuted; font.pixelSize: 9 }
                                        }
                                        Label { text: operatorViewModel.relativeArrivalText; color: root.accent; font.pixelSize: 28; font.family: "Consolas"; font.weight: Font.DemiBold }
                                    }
                                }
                                Panel {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    RowLayout { anchors.fill: parent; anchors.leftMargin: 20; anchors.rightMargin: 20
                                        ColumnLayout { Layout.fillWidth: true; spacing: 4
                                            Label { text: "GERÇEK KUZEYE GÖRE KERTERİZ"; color: root.textSecondary; font.pixelSize: 10; font.weight: Font.DemiBold }
                                            Label { text: "Geçerli anten referansı gerektirir"; color: root.textMuted; font.pixelSize: 9 }
                                        }
                                        Label { text: operatorViewModel.bearingText; color: root.success; font.pixelSize: 28; font.family: "Consolas"; font.weight: Font.DemiBold }
                                    }
                                }
                            }
                        }
                        Panel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 10
                                RowLayout {
                                    Layout.fillWidth: true
                                    SectionTitle { text: "ÖLÇÜM GEÇMİŞİ"; Layout.fillWidth: true }
                                    StateBadge { state: operatorViewModel.directionStatus === "LOB HAZIR" ? "Hazır" : "Kullanılmıyor" }
                                }
                                Label { text: operatorViewModel.directionStatus; color: operatorViewModel.directionStatus === "LOB HAZIR" ? root.success : root.warning; font.pixelSize: 12 }
                                Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: "ANTEN AÇISI"; color: root.textSecondary; font.pixelSize: 10; Layout.preferredWidth: 110 }
                                    Label { text: "GÜÇ"; color: root.textSecondary; font.pixelSize: 10; Layout.preferredWidth: 120 }
                                    Label { text: "KERTERİZ"; color: root.textSecondary; font.pixelSize: 10; Layout.preferredWidth: 100 }
                                    Label { text: "KAYNAK"; color: root.textSecondary; font.pixelSize: 10; Layout.fillWidth: true }
                                }
                                ListView {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    model: operatorViewModel.directionPoints
                                    spacing: 2
                                    delegate: Rectangle {
                                        required property var modelData
                                        required property int index
                                        width: ListView.view.width; height: 38; color: index % 2 ? "#0A151D" : "transparent"
                                        RowLayout { anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8
                                            Label { text: modelData.angle; color: root.textPrimary; font.pixelSize: 11; Layout.preferredWidth: 102 }
                                            Label { text: modelData.power; color: root.textPrimary; font.pixelSize: 11; Layout.preferredWidth: 112 }
                                            Label { text: modelData.bearing; color: root.textPrimary; font.pixelSize: 11; Layout.preferredWidth: 92 }
                                            Label { text: modelData.source; color: root.textSecondary; font.pixelSize: 11; Layout.fillWidth: true }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // SİSTEM
            Item {
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 14
                    Panel {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 150
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 12
                            RowLayout {
                                Layout.fillWidth: true
                                SectionTitle { text: "SİSTEM DURUMU"; Layout.fillWidth: true }
                                Label { text: operatorViewModel.sourceReady ? "Operasyonel bileşenler izleniyor" : "Kaynak bağlantısı bekleniyor"; color: operatorViewModel.sourceReady ? root.success : root.textSecondary; font.pixelSize: 10 }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                Repeater {
                                    model: operatorViewModel.pipelineBlocks
                                    delegate: Rectangle {
                                        required property var modelData
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 0
                                        Layout.preferredHeight: 58
                                        radius: 4
                                        color: root.surfaceAlt
                                        border.color: root.border
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 11
                                            anchors.rightMargin: 11
                                            spacing: 8
                                            Rectangle { width: 7; height: 7; radius: 4; color: modelData.state === "Hazır" ? root.success : modelData.state === "Çalışıyor" ? root.accent : modelData.state === "Hata" ? root.danger : root.textMuted }
                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 2
                                                Label { text: modelData.name; color: root.textPrimary; font.pixelSize: 9; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                                                Label { text: modelData.state; color: root.textMuted; font.pixelSize: 8 }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    Panel {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 10
                            RowLayout {
                                Layout.fillWidth: true
                                SectionTitle { text: "SON OLAYLAR"; Layout.fillWidth: true }
                                Label { text: operatorViewModel.performanceText; color: root.textSecondary; font.pixelSize: 10 }
                            }
                            Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                            ListView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                model: operatorViewModel.eventLog
                                spacing: 2
                                delegate: Rectangle {
                                    required property var modelData
                                    required property int index
                                    width: ListView.view.width; height: 36; color: index % 2 ? "#070E14" : "transparent"
                                    RowLayout { anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8; spacing: 16
                                        Label { text: modelData.time; color: root.textMuted; font.pixelSize: 10; font.family: "Consolas"; Layout.preferredWidth: 72 }
                                        Label { text: modelData.component.toUpperCase(); color: modelData.component === "Hata" ? root.danger : root.accent; font.pixelSize: 9; font.family: "Consolas"; font.weight: Font.Bold; Layout.preferredWidth: 110 }
                                        Label { text: modelData.message; color: root.textPrimary; font.pixelSize: 10; font.family: "Consolas"; Layout.fillWidth: true; elide: Text.ElideRight }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        id: eventConsole
        z: 50
        x: 76
        y: root.contentItem.height - height
        width: root.contentItem.width - x
        height: root.consoleOpen ? Math.min(238, root.contentItem.height * 0.36) : 0
        visible: height > 0
        clip: true
        color: "#03070B"
        border.color: root.borderStrong
        border.width: 1
        Behavior on height { NumberAnimation { duration: root.transitionDuration + 40; easing.type: Easing.OutCubic } }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 8
            RowLayout {
                Layout.fillWidth: true
                SectionTitle { text: "OLAY KONSOLU"; Layout.fillWidth: true }
                Label { text: operatorViewModel.eventLog.length + " kayıt"; color: root.textMuted; font.pixelSize: 9; font.family: "Consolas" }
                QuietButton { text: "Kapat"; implicitHeight: 28; onClicked: root.consoleOpen = false }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: operatorViewModel.eventLog
                spacing: 0
                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    width: ListView.view.width
                    height: 27
                    color: index % 2 ? "#050A0F" : "transparent"
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 6
                        anchors.rightMargin: 6
                        spacing: 12
                        Label { text: modelData.time; color: root.textMuted; font.pixelSize: 10; font.family: "Consolas"; Layout.preferredWidth: 68 }
                        Label { text: modelData.component.toUpperCase(); color: modelData.component === "Hata" ? root.danger : root.accent; font.pixelSize: 9; font.family: "Consolas"; font.weight: Font.Bold; Layout.preferredWidth: 100 }
                        Label { text: modelData.message; color: root.textPrimary; font.pixelSize: 10; font.family: "Consolas"; Layout.fillWidth: true; elide: Text.ElideRight }
                    }
                }
            }
        }
    }

    Component {
        id: sigmfControls
        ColumnLayout {
            width: parent ? parent.width : 240
            spacing: 8
            PrimaryButton { Layout.fillWidth: true; text: "Kaydı Aç"; enabled: !operatorViewModel.busy; onClicked: sigmfDialog.open() }
            Label { text: "Standart SigMF metadata ve eş adlı veri dosyası gerekir."; color: root.textSecondary; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true }
        }
    }

    Component {
        id: hackrfControls
        ColumnLayout {
            width: parent ? parent.width : 240
            spacing: 7
            QuietButton { Layout.fillWidth: true; text: "Cihazı Denetle"; enabled: !operatorViewModel.busy; onClicked: operatorViewModel.probeHackrf() }
            Label { text: "Merkez frekansı (Hz)"; color: root.textSecondary; font.pixelSize: 10 }
            TextField { id: centerInput; Layout.fillWidth: true; text: "100000000"; inputMethodHints: Qt.ImhDigitsOnly; Accessible.name: "HackRF merkez frekansı" }
            Label { text: "Örnekleme hızı"; color: root.textSecondary; font.pixelSize: 10 }
            AppCombo { id: rateInput; Layout.fillWidth: true; model: [8000000, 10000000, 20000000]; Accessible.name: "HackRF örnekleme hızı" }
            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true
                    Label { text: "LNA (dB)"; color: root.textSecondary; font.pixelSize: 10 }
                    AppCombo { id: lnaInput; Layout.fillWidth: true; model: [0,8,16,24,32,40]; currentIndex: 2 }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Label { text: "VGA (dB)"; color: root.textSecondary; font.pixelSize: 10 }
                    AppCombo { id: vgaInput; Layout.fillWidth: true; model: [0,8,16,24,32,40,48,56]; currentIndex: 2 }
                }
            }
            PrimaryButton {
                Layout.fillWidth: true
                text: "RX Alımını Başlat"
                enabled: operatorViewModel.sourceState === "Hazır" && !operatorViewModel.sourceReady && !operatorViewModel.busy
                onClicked: operatorViewModel.startHackrfCapture(Number(centerInput.text), Number(rateInput.currentText), Number(lnaInput.currentText), Number(vgaInput.currentText), 16384)
            }
        }
    }

    onClosing: function(close) { operatorViewModel.shutdown() }
}
