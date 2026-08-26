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
    property var spectrumViewHistory: [{"start": 0, "end": 1}]
    property int spectrumViewHistoryIndex: 0
    property string spectrumHistorySource: ""
    property real spectrumCursorNormalized: -1
    property bool spectrumCursorVisible: false
    property real analysisDragStart: -1
    property real analysisDragEnd: -1
    property int selectedSystemBlock: 0
    property string systemLogFilter: "Tümü"
    property int spectrumTaskTab: 0
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
    property int uiSectionTextSize: width >= 1600 ? 11 : 10
    property int uiBodyTextSize: width >= 1600 ? 11 : 10
    property int uiMetaTextSize: width >= 1600 ? 10 : 9
    property int uiDenseMetaTextSize: width >= 1600 ? 10 : 8

    onWorkspaceChanged: {
        if (workspace === 0) {
            spectrumCanvas.requestPaint()
            waterfall.requestPaint()
        }
        Qt.callLater(function() {
            var target = workspaceNavigation.itemAt(root.workspace)
            if (target) target.forceActiveFocus(Qt.ShortcutFocusReason)
        })
    }

    function setSpectrumView(start, end) {
        var span = Math.max(0.02, Math.min(1.0, end - start))
        var boundedStart = Math.max(0.0, Math.min(1.0 - span, start))
        spectrumViewStart = boundedStart
        spectrumViewEnd = boundedStart + span
    }

    function commitSpectrumView() {
        var current = spectrumViewHistory[spectrumViewHistoryIndex]
        if (current && Math.abs(current.start - spectrumViewStart) < 0.000001
                && Math.abs(current.end - spectrumViewEnd) < 0.000001) return
        var history = spectrumViewHistory.slice(0, spectrumViewHistoryIndex + 1)
        history.push({"start": spectrumViewStart, "end": spectrumViewEnd})
        if (history.length > 24) history = history.slice(history.length - 24)
        spectrumViewHistory = history
        spectrumViewHistoryIndex = history.length - 1
    }

    function restoreSpectrumView(index) {
        if (index < 0 || index >= spectrumViewHistory.length) return
        spectrumViewHistoryIndex = index
        var target = spectrumViewHistory[index]
        setSpectrumView(target.start, target.end)
    }

    function spectrumViewBack() {
        restoreSpectrumView(spectrumViewHistoryIndex - 1)
    }

    function spectrumViewForward() {
        restoreSpectrumView(spectrumViewHistoryIndex + 1)
    }

    function zoomSpectrum(relativeCenter, factor) {
        var anchorRatio = Math.max(0.0, Math.min(1.0, relativeCenter))
        var oldSpan = spectrumViewEnd - spectrumViewStart
        var newSpan = Math.max(0.02, Math.min(1.0, oldSpan * factor))
        var anchor = spectrumViewStart + anchorRatio * oldSpan
        setSpectrumView(anchor - anchorRatio * newSpan, anchor + (1.0 - anchorRatio) * newSpan)
        commitSpectrumView()
    }

    function panSpectrum(delta) {
        setSpectrumView(spectrumViewStart + delta, spectrumViewEnd + delta)
        commitSpectrumView()
    }

    function resetSpectrumView() {
        setSpectrumView(0, 1)
        commitSpectrumView()
    }

    function clearSpectrumViewHistory() {
        setSpectrumView(0, 1)
        spectrumViewHistory = [{"start": 0, "end": 1}]
        spectrumViewHistoryIndex = 0
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

    function normalizedAtSpectrumX(x, width) {
        var plotLeft = 42
        var plotWidth = Math.max(1, width - plotLeft - 8)
        var ratio = Math.max(0, Math.min(1, (x - plotLeft) / plotWidth))
        return spectrumViewStart + ratio * (spectrumViewEnd - spectrumViewStart)
    }

    function stateColor(state) {
        if (state === "Hazır") return success
        if (state === "Çalışıyor") return accent
        if (state === "Hata") return danger
        if (state === "Bekliyor") return warning
        return textMuted
    }

    function systemLogMatches(item) {
        if (systemLogFilter === "Tümü") return true
        if (systemLogFilter === "Hata") return item.level === "HATA"
        if (systemLogFilter === "Kaynak") return item.component === "Kaynak" || item.component === "HackRF"
        return item.component !== "Kaynak" && item.component !== "HackRF" && item.level !== "HATA"
    }

    function systemLogMatchCount() {
        var count = 0
        for (var index = 0; index < operatorViewModel.eventLog.length; ++index) {
            if (systemLogMatches(operatorViewModel.eventLog[index])) ++count
        }
        return count
    }

    onSpectrumViewStartChanged: {
        spectrumCanvas.requestPaint()
        waterfall.requestPaint()
    }
    onSpectrumViewEndChanged: {
        spectrumCanvas.requestPaint()
        waterfall.requestPaint()
    }
    onSpectrumCursorNormalizedChanged: {
        spectrumCanvas.requestPaint()
        waterfall.requestPaint()
    }
    onSpectrumCursorVisibleChanged: {
        spectrumCanvas.requestPaint()
        waterfall.requestPaint()
    }
    onAnalysisDragStartChanged: spectrumCanvas.requestPaint()
    onAnalysisDragEndChanged: spectrumCanvas.requestPaint()

    Connections {
        target: operatorViewModel
        function onStateChanged() {
            if (root.spectrumHistorySource !== operatorViewModel.sourceName) {
                root.spectrumHistorySource = operatorViewModel.sourceName
                root.clearSpectrumViewHistory()
            }
        }
    }

    component Panel: Rectangle {
        color: root.surface
        border.color: root.border
        border.width: 1
        radius: 6
    }

    component SectionTitle: Label {
        color: root.textSecondary
        font.pixelSize: root.uiSectionTextSize
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
        Accessible.name: displayText
        Accessible.role: Accessible.ComboBox
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
        indicator: Canvas {
            x: control.width - width - 12
            anchors.verticalCenter: parent.verticalCenter
            width: 10
            height: 6
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                ctx.strokeStyle = root.textSecondary
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
        Accessible.name: "Durum: " + state
        Accessible.role: Accessible.StaticText
        implicitWidth: badgeText.implicitWidth + 18
        implicitHeight: 24
        radius: 12
        color: state === "Hazır" ? "#153B31" : state === "Çalışıyor" ? "#123B42" : state === "Hata" ? "#48252B" : state === "Bekliyor" ? "#3B321F" : "#25313A"
        border.color: state === "Hazır" ? root.success : state === "Çalışıyor" ? root.accent : state === "Hata" ? root.danger : state === "Bekliyor" ? root.warning : "#536570"
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
    Shortcut { sequence: "Space"; onActivated: if (root.workspace === 0 && operatorViewModel.sourceReady && !operatorViewModel.busy) operatorViewModel.playing ? operatorViewModel.pause() : operatorViewModel.startScan() }
    Shortcut { sequence: "Ctrl+1"; onActivated: root.workspace = 0 }
    Shortcut { sequence: "Ctrl+2"; onActivated: root.workspace = 1 }
    Shortcut { sequence: "Ctrl+3"; onActivated: root.workspace = 2 }
    Shortcut { sequence: "Ctrl+4"; onActivated: root.workspace = 3 }
    Shortcut { sequence: "Ctrl+B"; onActivated: if (root.workspace === 0) root.sourcePanelOpen = !root.sourcePanelOpen }
    Shortcut { sequence: "Alt+Left"; onActivated: if (root.workspace === 0) root.spectrumViewBack() }
    Shortcut { sequence: "Alt+Right"; onActivated: if (root.workspace === 0) root.spectrumViewForward() }
    Shortcut { sequence: "Ctrl+0"; onActivated: if (root.workspace === 0) root.resetSpectrumView() }
    Shortcut { sequence: "Escape"; onActivated: if (root.consoleOpen) root.consoleOpen = false }

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
                objectName: "eventConsoleButton"
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
                    id: workspaceNavigation
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
                        objectName: "workspaceNavigation" + index
                        Accessible.name: modelData.label
                        Accessible.description: "Çalışma alanı " + (index + 1) + ", Ctrl+" + (index + 1)
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
                        property real animatedWidth: root.sourcePanelOpen ? 230 : 0
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
                            anchors.margins: 14
                            spacing: 12
                            RowLayout {
                                Layout.fillWidth: true
                                SectionTitle { text: "VERİ KAYNAĞI"; Layout.fillWidth: true }
                                StateBadge { state: operatorViewModel.playing ? "Çalışıyor" : operatorViewModel.busy ? "Çalışıyor" : operatorViewModel.sourceState }
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
                                          ? (operatorViewModel.playing
                                             ? "Tarama çalışıyor. Tespitler canlı olarak güncelleniyor."
                                             : "Kaynak hazır. Spektrum taraması başlatılabilir.")
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
                                    Label { text: "TARAMA"; color: root.textMuted; font.pixelSize: 8; font.weight: Font.Bold }
                                    StateBadge { state: operatorViewModel.playing ? "Çalışıyor" : operatorViewModel.sourceReady ? "Hazır" : "Kullanılmıyor" }
                                    PrimaryButton {
                                        text: "Başlat"
                                        implicitWidth: 64
                                        implicitHeight: 28
                                        enabled: operatorViewModel.sourceReady && !operatorViewModel.playing && !operatorViewModel.busy
                                        Accessible.name: "Spektrum taramasını başlat"
                                        onClicked: operatorViewModel.startScan()
                                    }
                                    QuietButton {
                                        text: "Duraklat"
                                        implicitWidth: 70
                                        implicitHeight: 28
                                        enabled: operatorViewModel.playing
                                        Accessible.name: "Spektrum taramasını duraklat"
                                        onClicked: operatorViewModel.pause()
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 5
                                    Label { text: "FREKANS GÖRÜNÜMÜ"; color: root.textMuted; font.pixelSize: 8; font.weight: Font.Bold }
                                    QuietButton { text: "‹"; implicitWidth: 26; implicitHeight: 24; Accessible.name: "Önceki frekans görünümü"; enabled: root.spectrumViewHistoryIndex > 0; onClicked: root.spectrumViewBack() }
                                    QuietButton { text: "›"; implicitWidth: 26; implicitHeight: 24; Accessible.name: "Sonraki frekans görünümü"; enabled: root.spectrumViewHistoryIndex + 1 < root.spectrumViewHistory.length; onClicked: root.spectrumViewForward() }
                                    QuietButton { text: "−"; implicitWidth: 28; implicitHeight: 24; Accessible.name: "Frekans görünümünü uzaklaştır"; onClicked: root.zoomSpectrum(0.5, 1.4) }
                                    Label { text: (1 / (root.spectrumViewEnd - root.spectrumViewStart)).toFixed(1) + "×"; color: root.textSecondary; font.pixelSize: 9; font.family: "Consolas" }
                                    QuietButton { text: "+"; implicitWidth: 28; implicitHeight: 24; Accessible.name: "Frekans görünümünü yakınlaştır"; onClicked: root.zoomSpectrum(0.5, 0.7) }
                                    QuietButton { text: "1:1"; implicitWidth: 40; implicitHeight: 24; font.pixelSize: 9; Accessible.name: "Frekans görünümünü sıfırla"; enabled: root.spectrumViewStart > 0 || root.spectrumViewEnd < 1; onClicked: root.resetSpectrumView() }
                                    Item { Layout.fillWidth: true }
                                    Rectangle {
                                        implicitWidth: liveTrace.implicitWidth + 16
                                        implicitHeight: 22
                                        radius: 3
                                        color: root.accentSoft
                                        Label { id: liveTrace; anchors.centerIn: parent; text: "ANLIK · dBFS"; color: root.accent; font.pixelSize: 9; font.weight: Font.Bold }
                                    }
                                    Label { visible: root.width >= 1500; text: operatorViewModel.performanceText; color: root.textSecondary; font.pixelSize: 10 }
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
                                        function onSpectrumChanged() {
                                            if (root.workspace === 0) spectrumCanvas.requestPaint()
                                        }
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
                                        if (root.analysisDragStart >= 0 && root.analysisDragEnd >= 0) {
                                            var dragX1 = plotLeft + (Math.min(root.analysisDragStart, root.analysisDragEnd) - root.spectrumViewStart) * plotWidth / (root.spectrumViewEnd - root.spectrumViewStart)
                                            var dragX2 = plotLeft + (Math.max(root.analysisDragStart, root.analysisDragEnd) - root.spectrumViewStart) * plotWidth / (root.spectrumViewEnd - root.spectrumViewStart)
                                            ctx.fillStyle = "rgba(49,195,210,0.16)"
                                            ctx.fillRect(Math.max(plotLeft, dragX1), plotTop, Math.max(2, Math.min(plotRight, dragX2) - Math.max(plotLeft, dragX1)), plotHeight)
                                            ctx.strokeStyle = root.accent
                                            ctx.strokeRect(Math.max(plotLeft, dragX1), plotTop, Math.max(2, Math.min(plotRight, dragX2) - Math.max(plotLeft, dragX1)), plotHeight)
                                        }
                                        if (root.spectrumCursorVisible && root.spectrumCursorNormalized >= root.spectrumViewStart
                                                && root.spectrumCursorNormalized <= root.spectrumViewEnd) {
                                            var cursorX = plotLeft + (root.spectrumCursorNormalized - root.spectrumViewStart) * plotWidth / (root.spectrumViewEnd - root.spectrumViewStart)
                                            ctx.strokeStyle = "rgba(237,245,247,0.72)"
                                            ctx.lineWidth = 1
                                            ctx.beginPath(); ctx.moveTo(cursorX, plotTop); ctx.lineTo(cursorX, plotBottom); ctx.stroke()
                                            var cursorText = root.formatFrequency(root.frequencyAt(root.spectrumCursorNormalized))
                                            ctx.font = "10px Consolas"
                                            var cursorWidth = ctx.measureText(cursorText).width + 12
                                            var cursorLabelX = Math.max(plotLeft, Math.min(plotRight - cursorWidth, cursorX - cursorWidth / 2))
                                            ctx.fillStyle = "rgba(13,24,34,0.94)"
                                            ctx.fillRect(cursorLabelX, plotTop + 4, cursorWidth, 20)
                                            ctx.strokeStyle = root.borderStrong
                                            ctx.strokeRect(cursorLabelX, plotTop + 4, cursorWidth, 20)
                                            ctx.fillStyle = root.textPrimary
                                            ctx.textAlign = "center"; ctx.textBaseline = "middle"
                                            ctx.fillText(cursorText, cursorLabelX + cursorWidth / 2, plotTop + 14)
                                        }
                                    }
                                    MouseArea {
                                        id: spectrumInteraction
                                        anchors.fill: parent
                                        acceptedButtons: Qt.LeftButton
                                        hoverEnabled: true
                                        cursorShape: selectionMode ? Qt.CrossCursor : pressed ? Qt.ClosedHandCursor : Qt.CrossCursor
                                        property real pressX: 0
                                        property real pressStart: 0
                                        property real pressEnd: 1
                                        property bool selectionMode: false
                                        property real selectionAnchor: -1
                                        onEntered: root.spectrumCursorVisible = true
                                        onExited: {
                                            if (!pressed) root.spectrumCursorVisible = false
                                            spectrumCanvas.requestPaint(); waterfall.requestPaint()
                                        }
                                        onPressed: function(mouse) {
                                            pressX = mouse.x
                                            pressStart = root.spectrumViewStart
                                            pressEnd = root.spectrumViewEnd
                                            selectionMode = (mouse.modifiers & Qt.ShiftModifier) !== 0
                                            selectionAnchor = root.normalizedAtSpectrumX(mouse.x, width)
                                            root.spectrumCursorVisible = true
                                            root.spectrumCursorNormalized = selectionAnchor
                                            if (selectionMode) {
                                                root.analysisDragStart = selectionAnchor
                                                root.analysisDragEnd = selectionAnchor
                                            }
                                        }
                                        onPositionChanged: function(mouse) {
                                            root.spectrumCursorVisible = true
                                            root.spectrumCursorNormalized = root.normalizedAtSpectrumX(mouse.x, width)
                                            if (pressed) {
                                                if (selectionMode) {
                                                    root.analysisDragEnd = root.spectrumCursorNormalized
                                                } else {
                                                    var span = pressEnd - pressStart
                                                    var delta = -(mouse.x - pressX) * span / Math.max(1, width)
                                                    root.setSpectrumView(pressStart + delta, pressEnd + delta)
                                                }
                                            }
                                            spectrumCanvas.requestPaint(); waterfall.requestPaint()
                                        }
                                        onReleased: function(mouse) {
                                            if (selectionMode) {
                                                if (Math.abs(mouse.x - pressX) >= 4)
                                                    operatorViewModel.setAnalysisSpanDraftNormalized(root.analysisDragStart, root.analysisDragEnd)
                                                root.analysisDragStart = -1
                                                root.analysisDragEnd = -1
                                            } else if (Math.abs(mouse.x - pressX) >= 2) {
                                                root.commitSpectrumView()
                                            }
                                            selectionMode = false
                                            spectrumCanvas.requestPaint(); waterfall.requestPaint()
                                        }
                                        onCanceled: {
                                            root.analysisDragStart = -1
                                            root.analysisDragEnd = -1
                                            selectionMode = false
                                            spectrumCanvas.requestPaint(); waterfall.requestPaint()
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
                                Label {
                                    Layout.fillWidth: true
                                    text: "Kaydır: sürükle  ·  Analiz aralığı: Shift+sürükle  ·  Yakınlaştır: tekerlek  ·  Tam bant: çift tık"
                                    color: root.textMuted
                                    font.pixelSize: 9
                                    elide: Text.ElideRight
                                    horizontalAlignment: Text.AlignRight
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
                                    property var colorPalette: []
                                    function buildColorPalette() {
                                        var palette = []
                                        for (var index = 0; index < 64; index++) {
                                            var level = index / 63
                                            var red = level < 0.65 ? Math.round(7 + 48 * level) : Math.round(55 + 190 * (level - 0.65) / 0.35)
                                            var green = level < 0.45 ? Math.round(20 + 180 * level) : Math.round(101 + 118 * (level - 0.45) / 0.55)
                                            var blue = level < 0.70 ? Math.round(42 + 190 * level) : Math.round(175 - 115 * (level - 0.70) / 0.30)
                                            palette.push("rgb(" + red + "," + green + "," + blue + ")")
                                        }
                                        colorPalette = palette
                                    }
                                    Component.onCompleted: buildColorPalette()
                                    Connections {
                                        target: operatorViewModel
                                        function onSpectrumChanged() {
                                            var values = operatorViewModel.spectrumValues
                                            if (values && values.length) {
                                                waterfall.history.push(values.slice(0))
                                                if (waterfall.history.length > 48) waterfall.history.shift()
                                            } else waterfall.history = []
                                            if (root.workspace === 0) waterfall.requestPaint()
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
                                                ctx.fillStyle = colorPalette[Math.round(level * 63)]
                                                ctx.fillRect((col - firstIndex) * width / visibleCount, y, Math.ceil(step * width / visibleCount), rh)
                                            }
                                        }
                                        if (root.spectrumCursorVisible && root.spectrumCursorNormalized >= root.spectrumViewStart
                                                && root.spectrumCursorNormalized <= root.spectrumViewEnd) {
                                            var cursorX = (root.spectrumCursorNormalized - root.spectrumViewStart) * width / (root.spectrumViewEnd - root.spectrumViewStart)
                                            ctx.strokeStyle = "rgba(237,245,247,0.72)"
                                            ctx.lineWidth = 1
                                            ctx.beginPath(); ctx.moveTo(cursorX, 0); ctx.lineTo(cursorX, height); ctx.stroke()
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
                                        onEntered: root.spectrumCursorVisible = true
                                        onExited: {
                                            if (!pressed) root.spectrumCursorVisible = false
                                            spectrumCanvas.requestPaint(); waterfall.requestPaint()
                                        }
                                        onPressed: function(mouse) {
                                            pressX = mouse.x
                                            pressStart = root.spectrumViewStart
                                            pressEnd = root.spectrumViewEnd
                                            root.spectrumCursorVisible = true
                                            root.spectrumCursorNormalized = root.spectrumViewStart + Math.max(0, Math.min(1, mouse.x / Math.max(1, width))) * (root.spectrumViewEnd - root.spectrumViewStart)
                                        }
                                        onPositionChanged: function(mouse) {
                                            root.spectrumCursorVisible = true
                                            root.spectrumCursorNormalized = root.spectrumViewStart + Math.max(0, Math.min(1, mouse.x / Math.max(1, width))) * (root.spectrumViewEnd - root.spectrumViewStart)
                                            if (pressed) {
                                                var span = pressEnd - pressStart
                                                var delta = -(mouse.x - pressX) * span / Math.max(1, width)
                                                root.setSpectrumView(pressStart + delta, pressEnd + delta)
                                            }
                                            spectrumCanvas.requestPaint(); waterfall.requestPaint()
                                        }
                                        onReleased: function(mouse) { if (Math.abs(mouse.x - pressX) >= 2) root.commitSpectrumView() }
                                        onWheel: function(wheel) { root.zoomSpectrum(wheel.x / Math.max(1, width), wheel.angleDelta.y > 0 ? 0.75 : 1.333333) }
                                        onDoubleClicked: root.resetSpectrumView()
                                    }
                                }
                            }
                        }

                    }

                    Panel {
                        Layout.preferredWidth: 330
                        Layout.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10
                            RowLayout {
                                Layout.fillWidth: true
                                SectionTitle { text: "SİNYAL GÖREVİ"; Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: detectionCount.implicitWidth + 14
                                    implicitHeight: 22
                                    radius: 11
                                    color: root.accentSoft
                                    Label { id: detectionCount; anchors.centerIn: parent; text: operatorViewModel.detections.length; color: root.accent; font.pixelSize: 10; font.weight: Font.Bold }
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 68
                                radius: 4
                                color: operatorViewModel.selectedDetectionReady ? root.accentSoft : root.surfaceAlt
                                border.color: operatorViewModel.selectedDetectionReady ? "#28616B" : root.border
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Label {
                                            text: operatorViewModel.selectedDetectionTitle
                                            color: root.textPrimary
                                            font.pixelSize: 11
                                            font.weight: Font.DemiBold
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Label { text: operatorViewModel.selectedDetectionFrequencyText; color: operatorViewModel.selectedDetectionReady ? root.accent : root.textSecondary; font.pixelSize: 10; font.family: "Consolas"; Layout.fillWidth: true }
                                            Label { text: operatorViewModel.selectedDetectionStateText; color: operatorViewModel.selectedDetectionReady ? root.success : root.textMuted; font.pixelSize: 8; font.weight: Font.Bold }
                                        }
                                        Label { visible: operatorViewModel.selectedDetectionReady; text: "Tepe / gürültü oranı  " + operatorViewModel.selectedDetectionContrastText; color: root.textSecondary; font.pixelSize: 8 }
                                    }
                                    QuietButton {
                                        text: "Ölçüm ›"
                                        visible: root.spectrumTaskTab === 0
                                        implicitWidth: 68
                                        implicitHeight: 30
                                        enabled: operatorViewModel.selectedDetectionReady
                                        Accessible.name: "Seçili sinyalin ölçüm adımına geç"
                                        onClicked: root.spectrumTaskTab = 1
                                    }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                QuietButton {
                                    Layout.fillWidth: true
                                    text: "Tespitler"
                                    implicitHeight: 30
                                    checked: root.spectrumTaskTab === 0
                                    Accessible.name: "Tespit listesini göster"
                                    onClicked: root.spectrumTaskTab = 0
                                }
                                QuietButton {
                                    Layout.fillWidth: true
                                    text: "Ölçüm"
                                    implicitHeight: 30
                                    checked: root.spectrumTaskTab === 1
                                    Accessible.name: "Sinyal ölçümünü göster"
                                    onClicked: root.spectrumTaskTab = 1
                                }
                            }
                            ListView {
                                id: detectionList
                                objectName: "detectionList"
                                visible: root.spectrumTaskTab === 0
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                spacing: 3
                                model: operatorViewModel.detections
                                ScrollBar.vertical: ScrollBar {
                                    policy: ScrollBar.AlwaysOff
                                }
                                delegate: Button {
                                    required property var modelData
                                    width: ListView.view.width
                                    height: 52
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
                                            Label { text: "P/N " + modelData.snr; color: root.textSecondary; font.pixelSize: 8; Accessible.name: "Tepe gürültü oranı " + modelData.snr }
                                        }
                                    }
                                }
                                Rectangle {
                                    z: 3
                                    anchors.right: parent.right
                                    anchors.rightMargin: 1
                                    width: 3
                                    radius: 2
                                    visible: detectionList.contentHeight > detectionList.height
                                    height: Math.max(28, detectionList.height * detectionList.height / Math.max(detectionList.height, detectionList.contentHeight))
                                    y: Math.max(0, Math.min(detectionList.height - height,
                                                (detectionList.height - height) * detectionList.contentY
                                                / Math.max(1, detectionList.contentHeight - detectionList.height)))
                                    color: root.borderStrong
                                }
                            }
                            Label {
                                visible: root.spectrumTaskTab === 0 && operatorViewModel.detections.length === 0
                                text: operatorViewModel.sourceReady ? "Doğrulanmış aday bekleniyor." : "Önce gerçek bir kaynak hazırlayın."
                                color: root.textSecondary
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }
                            Rectangle { visible: root.spectrumTaskTab === 1; Layout.fillWidth: true; height: 1; color: root.border }
                            RowLayout {
                                visible: root.spectrumTaskTab === 1
                                Layout.fillWidth: true
                                SectionTitle { text: "SİNYAL ÖLÇÜMÜ"; Layout.fillWidth: true }
                                Label {
                                    text: operatorViewModel.parameterRows.length > 0 ? "SONUÇ HAZIR"
                                          : operatorViewModel.analysisSpanConfirmed ? "ARALIK ONAYLI"
                                          : operatorViewModel.selectedDetectionReady ? "ARALIK BEKLİYOR"
                                          : "TESPİT BEKLİYOR"
                                    color: operatorViewModel.parameterRows.length > 0 ? root.success : operatorViewModel.analysisSpanConfirmed ? root.accent : root.textMuted
                                    font.pixelSize: 8
                                    font.weight: Font.Bold
                                }
                            }
                            ScrollView {
                                id: measurementScroll
                                objectName: "measurementScroll"
                                visible: root.spectrumTaskTab === 1
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                                ColumnLayout {
                                    width: measurementScroll.availableWidth
                                    spacing: 9
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
                                    Label {
                                        Layout.fillWidth: true
                                        text: "Spektrum üzerinde Shift+sürükle ile aralık taslağı oluşturabilirsiniz."
                                        color: root.accent
                                        font.pixelSize: 9
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
                                    Repeater {
                                        model: operatorViewModel.parameterRows
                                        delegate: RowLayout {
                                            required property var modelData
                                            Layout.fillWidth: true
                                            implicitHeight: 26
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
                }
            }

            // DİNLEME
            Item {
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    Panel {
                        Layout.preferredWidth: 330
                        Layout.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 9
                            RowLayout {
                                Layout.fillWidth: true
                                SectionTitle { text: "KANAL HAZIRLAMA"; Layout.fillWidth: true }
                                StateBadge { state: operatorViewModel.busy ? "Çalışıyor" : operatorViewModel.listeningReady ? "Hazır" : operatorViewModel.selectedDetectionReady ? "Bekliyor" : "Kullanılmıyor" }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 76
                                radius: 4
                                color: operatorViewModel.selectedDetectionReady ? root.accentSoft : root.surfaceAlt
                                border.color: operatorViewModel.selectedDetectionReady ? "#28616B" : root.border
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 2
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: operatorViewModel.listeningDetectionTitle; color: root.textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold; Layout.fillWidth: true; elide: Text.ElideRight }
                                        Label { text: operatorViewModel.selectedDetectionStateText; color: operatorViewModel.selectedDetectionReady ? root.success : root.textMuted; font.pixelSize: 8; font.weight: Font.Bold }
                                    }
                                    Label { text: operatorViewModel.listeningDetectionFrequencyText; color: operatorViewModel.selectedDetectionReady ? root.accent : root.textSecondary; font.pixelSize: 10; font.family: "Consolas" }
                                    Label { text: "I/Q kayıt süresi  " + operatorViewModel.sourceDurationText; color: root.textMuted; font.pixelSize: 8 }
                                }
                            }
                            Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                            ScrollView {
                                id: listeningSettingsScroll
                                objectName: "listeningSettingsScroll"
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                ScrollBar.vertical.policy: ScrollBar.AsNeeded
                                ColumnLayout {
                                    width: listeningSettingsScroll.availableWidth
                                    spacing: 10
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
                                        implicitHeight: 26
                                        from: 0
                                        to: 1
                                        value: 0.8
                                        Accessible.name: "Dinleme ses seviyesi"
                                        background: Rectangle {
                                            x: listeningVolume.leftPadding
                                            y: listeningVolume.topPadding + listeningVolume.availableHeight / 2 - height / 2
                                            width: listeningVolume.availableWidth
                                            height: 4
                                            radius: 2
                                            color: "#172731"
                                            Rectangle {
                                                width: listeningVolume.visualPosition * parent.width
                                                height: parent.height
                                                radius: 2
                                                color: root.accent
                                            }
                                        }
                                        handle: Rectangle {
                                            x: listeningVolume.leftPadding + listeningVolume.visualPosition * (listeningVolume.availableWidth - width)
                                            y: listeningVolume.topPadding + listeningVolume.availableHeight / 2 - height / 2
                                            width: 14
                                            height: 14
                                            radius: 7
                                            color: listeningVolume.pressed ? "#D9FBFD" : root.textPrimary
                                            border.color: root.accent
                                            border.width: 2
                                        }
                                    }
                                }
                            }
                            PrimaryButton {
                                Layout.fillWidth: true
                                text: operatorViewModel.listeningReady ? "Kanal Sesini Yeniden Hazırla" : "Kanal Sesini Hazırla"
                                enabled: operatorViewModel.selectedDetectionReady && operatorViewModel.sourceReady && !operatorViewModel.busy
                                onClicked: operatorViewModel.requestListening(
                                    listeningMode.model[listeningMode.currentIndex].value,
                                    Number(listeningOffset.text),
                                    Number(listeningBandwidth.text),
                                    listeningVolume.value
                                )
                            }
                            Label {
                                Layout.fillWidth: true
                                text: "Kesintisiz sonuç için en az 5 saniyelik I/Q gerekir; kısa kayıt yalnız süreli önizleme üretir."
                                color: root.warning
                                font.pixelSize: 9
                                wrapMode: Text.Wrap
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 10
                        Panel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: root.height < 780 ? 250 : 310
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8
                                RowLayout {
                                    Layout.fillWidth: true
                                    SectionTitle { text: "DEMODÜLE SES DALGA BİÇİMİ"; Layout.fillWidth: true }
                                    Label { text: operatorViewModel.listeningPlaybackDurationText; color: root.textMuted; font.pixelSize: 9; font.family: "Consolas" }
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
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: "00:00.0"; color: root.textMuted; font.pixelSize: 8; font.family: "Consolas" }
                                    Item { Layout.fillWidth: true }
                                    Label { text: "GENLİK · NORMALİZE"; color: root.textMuted; font.pixelSize: 8; font.weight: Font.Bold }
                                    Item { Layout.fillWidth: true }
                                    Label { text: operatorViewModel.listeningPlaybackDurationText; color: root.textMuted; font.pixelSize: 8; font.family: "Consolas" }
                                }
                            }
                        }
                        Panel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8
                                RowLayout {
                                    Layout.fillWidth: true
                                    SectionTitle { text: "KANAL ÇIKIŞI"; Layout.fillWidth: true }
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
                                Rectangle {
                                    id: listeningTransport
                                    objectName: "listeningTransport"
                                    Layout.fillWidth: true
                                    implicitHeight: 76
                                    radius: 4
                                    color: "#071018"
                                    border.color: root.border
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        spacing: 6
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Label { text: operatorViewModel.listeningPlaybackState; color: operatorViewModel.listeningPlaybackState === "Oynatılıyor" ? root.success : root.textPrimary; font.pixelSize: 9; font.weight: Font.DemiBold; Layout.fillWidth: true }
                                            Label { text: operatorViewModel.listeningOutputState; color: operatorViewModel.listeningOutputState === "Ses çıkışı hazır" ? root.success : root.warning; font.pixelSize: 8 }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true
                                            implicitHeight: 6
                                            radius: 3
                                            color: "#172731"
                                            Accessible.name: "Oynatma konumu, salt okunur"
                                            Rectangle {
                                                width: parent.width * operatorViewModel.listeningPlaybackProgress
                                                height: parent.height
                                                radius: 3
                                                color: root.accent
                                                Behavior on width { NumberAnimation { duration: root.transitionDuration } }
                                            }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Label { text: operatorViewModel.listeningPlaybackPositionText; color: root.textSecondary; font.pixelSize: 8; font.family: "Consolas"; Layout.fillWidth: true }
                                            Label { text: operatorViewModel.listeningPlaybackDurationText; color: root.textSecondary; font.pixelSize: 8; font.family: "Consolas" }
                                        }
                                    }
                                }
                                Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                                ListView {
                                    id: listeningResultList
                                    objectName: "listeningResultList"
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
                                    QuietButton { text: "Oynat"; implicitWidth: 72; enabled: operatorViewModel.listeningAudioAvailable && !operatorViewModel.busy; onClicked: operatorViewModel.playListening() }
                                    QuietButton { text: "Duraklat"; implicitWidth: 82; enabled: operatorViewModel.listeningAudioAvailable && !operatorViewModel.busy; onClicked: operatorViewModel.pauseListening() }
                                    QuietButton { text: "Durdur"; implicitWidth: 72; enabled: operatorViewModel.listeningReady && !operatorViewModel.busy; onClicked: operatorViewModel.stopListening() }
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
                    anchors.margins: 14
                    spacing: 10

                    Panel {
                        Layout.preferredWidth: 330
                        Layout.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 9
                            RowLayout {
                                Layout.fillWidth: true
                                SectionTitle { text: "SAHA ÖLÇÜMÜ"; Layout.fillWidth: true }
                                StateBadge { state: operatorViewModel.directionReady ? "Hazır" : operatorViewModel.sourceReady ? "Bekliyor" : "Kullanılmıyor" }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 94
                                radius: 4
                                color: root.surfaceAlt
                                border.color: root.border
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 4
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: "KAYNAK BAĞLAMI"; color: root.textMuted; font.pixelSize: 8; font.weight: Font.Bold; Layout.fillWidth: true }
                                        Label { text: operatorViewModel.sourceReady ? "ETKİN KARE" : "KAYNAK YOK"; color: operatorViewModel.sourceReady ? root.success : root.warning; font.pixelSize: 8; font.weight: Font.Bold }
                                    }
                                    Label { text: operatorViewModel.sourceName; color: root.textPrimary; font.pixelSize: 10; font.weight: Font.DemiBold; elide: Text.ElideMiddle; Layout.fillWidth: true }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: operatorViewModel.centerFrequencyText; color: root.accent; font.pixelSize: 10; font.family: "Consolas"; Layout.fillWidth: true }
                                        Label { text: operatorViewModel.frameIndex + " / " + operatorViewModel.frameCount + " kare"; color: root.textSecondary; font.pixelSize: 9 }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: "Geniş bant kare gücü"; color: root.textSecondary; font.pixelSize: 9; Layout.fillWidth: true }
                                        Label { text: operatorViewModel.directionFramePowerText; color: root.textPrimary; font.pixelSize: 10; font.family: "Consolas"; font.weight: Font.DemiBold }
                                    }
                                }
                            }
                            ScrollView {
                                id: directionSettingsScroll
                                objectName: "directionSettingsScroll"
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                contentWidth: availableWidth
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                ColumnLayout {
                                    width: directionSettingsScroll.availableWidth
                                    spacing: 8
                                    Label { text: "Anten dönüş açısı (°)"; color: root.textSecondary; font.pixelSize: 10 }
                                    TextField {
                                        id: antennaAngle
                                        Layout.fillWidth: true
                                        text: "0"
                                        color: root.textPrimary
                                        validator: IntValidator { bottom: 0; top: 359 }
                                        inputMethodHints: Qt.ImhDigitsOnly
                                        Accessible.name: "Anten dönüş açısı, derece"
                                        background: Rectangle { color: "#09141C"; border.color: antennaAngle.activeFocus ? root.accent : root.border; radius: 4 }
                                    }
                                    Label { text: "Anten 0° yönünün referansı"; color: root.textSecondary; font.pixelSize: 10 }
                                    AppCombo {
                                        id: referenceMode
                                        Layout.fillWidth: true
                                        enabled: operatorViewModel.directionMeasurementCount === 0
                                        opacity: enabled ? 1.0 : 0.65
                                        model: [
                                            {text: "Gerçek kuzey (0°)", value: "north"},
                                            {text: "Elle girilen gerçek kerteriz", value: "manual"},
                                            {text: "Coğrafi referans yok", value: "none"}
                                        ]
                                        textRole: "text"
                                        Accessible.name: "Anten sıfır derece yön referansı"
                                    }
                                    Label { text: "Anten 0° gerçek kerterizi (°)"; color: root.textSecondary; font.pixelSize: 10; visible: referenceMode.currentIndex === 1 }
                                    TextField {
                                        id: referenceAngle
                                        Layout.fillWidth: true
                                        text: "0"
                                        color: root.textPrimary
                                        validator: IntValidator { bottom: 0; top: 359 }
                                        inputMethodHints: Qt.ImhDigitsOnly
                                        visible: referenceMode.currentIndex === 1
                                        enabled: operatorViewModel.directionMeasurementCount === 0
                                        opacity: enabled ? 1.0 : 0.65
                                        Accessible.name: "Anten sıfır derece gerçek kerterizi"
                                        background: Rectangle { color: "#09141C"; border.color: referenceAngle.activeFocus ? root.accent : root.border; radius: 4 }
                                    }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: "Ölçüm ilerlemesi"; color: root.textSecondary; font.pixelSize: 9; Layout.fillWidth: true }
                                        Label { text: operatorViewModel.directionRequirementText; color: root.textPrimary; font.pixelSize: 9; font.family: "Consolas" }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        implicitHeight: 6
                                        radius: 3
                                        color: "#172731"
                                        Rectangle { width: parent.width * operatorViewModel.directionProgress; height: parent.height; radius: 3; color: root.accent; Behavior on width { NumberAnimation { duration: root.transitionDuration } } }
                                    }
                                    Label { text: "İlk kayıt anten referansını bu ölçüm oturumu için sabitler."; color: root.textMuted; font.pixelSize: 9; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                }
                            }
                            PrimaryButton {
                                Layout.fillWidth: true
                                implicitHeight: 42
                                text: "Etkin Kare Gücünü Kaydet"
                                enabled: operatorViewModel.sourceReady && !operatorViewModel.busy && antennaAngle.acceptableInput && (referenceMode.currentIndex !== 1 || referenceAngle.acceptableInput)
                                Accessible.name: "Etkin kare gücünü anten açısıyla kaydet"
                                onClicked: operatorViewModel.addDirectionMeasurement(Number(antennaAngle.text), referenceMode.model[referenceMode.currentIndex].value, Number(referenceAngle.text))
                            }
                            QuietButton { Layout.fillWidth: true; text: "Ölçümleri Temizle"; enabled: operatorViewModel.directionPoints.length > 0; onClicked: operatorViewModel.clearDirectionMeasurements() }
                            Label { text: "Tek yönlü anten ve göreli dBFS kullanılır; faz uyumlu DoA, menzil veya hedef konumu üretilmez."; color: root.warning; font.pixelSize: 9; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 10
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: root.height < 760 ? 230 : 270
                            Layout.minimumHeight: root.height < 760 ? 230 : 270
                            Layout.maximumHeight: root.height < 760 ? 230 : 270
                            spacing: 10
                            Panel {
                                Layout.preferredWidth: root.height < 760 ? 250 : 290
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 4
                                    RowLayout {
                                        Layout.fillWidth: true
                                        SectionTitle { text: "RADYO KERTERİZİ"; Layout.fillWidth: true }
                                        Label { text: bearingCompass.geographicReference ? "GERÇEK" : "BAĞIL"; color: bearingCompass.indicatedBearing >= 0 ? root.success : root.textMuted; font.pixelSize: 8; font.weight: Font.Bold }
                                    }
                                    Canvas {
                                        id: bearingCompass
                                        objectName: "directionCompass"
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        property real indicatedBearing: -1
                                        property bool geographicReference: false
                                        Accessible.name: geographicReference ? "Gerçek kerteriz göstergesi" : "Bağıl geliş yönü göstergesi"
                                        onIndicatedBearingChanged: requestPaint()
                                        onGeographicReferenceChanged: requestPaint()
                                        Behavior on indicatedBearing {
                                            NumberAnimation { duration: root.transitionDuration + 130; easing.type: Easing.OutCubic }
                                        }
                                        Connections {
                                            target: operatorViewModel
                                            function onDirectionChanged() {
                                                var trueBearing = parseFloat(operatorViewModel.bearingText)
                                                var relativeBearing = parseFloat(operatorViewModel.relativeArrivalText)
                                                bearingCompass.geographicReference = !isNaN(trueBearing)
                                                bearingCompass.indicatedBearing = !isNaN(trueBearing) ? trueBearing : (!isNaN(relativeBearing) ? relativeBearing : -1)
                                                bearingCompass.requestPaint()
                                            }
                                        }
                                        onPaint: {
                                            var ctx = getContext("2d")
                                            ctx.reset(); ctx.clearRect(0, 0, width, height)
                                            var cx = width / 2; var cy = height / 2 + 3
                                            var radius = Math.min(width, height) * 0.36
                                            ctx.strokeStyle = root.borderStrong; ctx.lineWidth = 1.2
                                            ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2); ctx.stroke()
                                            ctx.font = "bold 9px Segoe UI"; ctx.fillStyle = root.textSecondary; ctx.textAlign = "center"; ctx.textBaseline = "middle"
                                            ctx.fillText(geographicReference ? "K" : "0°", cx, cy - radius - 11)
                                            ctx.fillText(geographicReference ? "D" : "90°", cx + radius + 13, cy)
                                            ctx.fillText(geographicReference ? "G" : "180°", cx, cy + radius + 11)
                                            ctx.fillText(geographicReference ? "B" : "270°", cx - radius - 13, cy)
                                            for (var tick = 0; tick < 24; tick++) {
                                                var angle = tick * Math.PI * 2 / 24 - Math.PI / 2
                                                var inner = radius - (tick % 6 === 0 ? 8 : 4)
                                                ctx.beginPath(); ctx.moveTo(cx + Math.cos(angle) * inner, cy + Math.sin(angle) * inner)
                                                ctx.lineTo(cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius); ctx.stroke()
                                            }
                                            var bearing = bearingCompass.indicatedBearing
                                            if (bearing >= 0) {
                                                var bearingRad = bearing * Math.PI / 180 - Math.PI / 2
                                                ctx.strokeStyle = geographicReference ? root.success : root.accent; ctx.lineWidth = 2.5
                                                ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(bearingRad) * (radius - 8), cy + Math.sin(bearingRad) * (radius - 8)); ctx.stroke()
                                                ctx.fillStyle = geographicReference ? root.success : root.accent; ctx.beginPath(); ctx.arc(cx, cy, 4, 0, Math.PI * 2); ctx.fill()
                                            } else {
                                                ctx.fillStyle = root.textMuted; ctx.font = "10px Segoe UI"
                                                ctx.fillText(operatorViewModel.directionMeasurementCount > 0 ? "Sonuç üretilemedi" : "Ölçüm bekleniyor", cx, cy)
                                            }
                                        }
                                    }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                spacing: 8
                                Panel {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 68
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 14
                                        anchors.rightMargin: 14
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 2
                                            Label { text: "ÖLÇÜM OTURUMU"; color: root.textSecondary; font.pixelSize: 9; font.weight: Font.DemiBold }
                                            Label { text: operatorViewModel.directionReferenceText; color: root.textPrimary; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                                        }
                                        Label { text: operatorViewModel.directionRequirementText; color: root.accent; font.pixelSize: 10; font.family: "Consolas"; font.weight: Font.DemiBold }
                                    }
                                }
                                Panel {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    RowLayout { anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 16
                                        ColumnLayout { Layout.fillWidth: true; spacing: 4
                                            Label { text: "BAĞIL GELİŞ YÖNÜ"; color: root.textSecondary; font.pixelSize: 10; font.weight: Font.DemiBold }
                                            Label { text: "Antenin 0° ekseninden saat yönünde"; color: root.textMuted; font.pixelSize: 9 }
                                        }
                                        Label { text: operatorViewModel.relativeArrivalText; color: root.accent; font.pixelSize: 28; font.family: "Consolas"; font.weight: Font.DemiBold }
                                    }
                                }
                                Panel {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    RowLayout { anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 16
                                        ColumnLayout { Layout.fillWidth: true; spacing: 4
                                            Label { text: "GERÇEK KERTERİZ"; color: root.textSecondary; font.pixelSize: 10; font.weight: Font.DemiBold }
                                            Label { text: "Gerçek kuzeyden saat yönünde"; color: root.textMuted; font.pixelSize: 9 }
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
                                    StateBadge { state: operatorViewModel.directionReady ? "Hazır" : operatorViewModel.directionMeasurementCount > 0 ? "Bekliyor" : "Kullanılmıyor" }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: operatorViewModel.directionStatusText; color: operatorViewModel.directionReady ? root.success : root.warning; font.pixelSize: 11; Layout.fillWidth: true }
                                    Label { text: operatorViewModel.directionRequirementText; color: root.textSecondary; font.pixelSize: 9; font.family: "Consolas" }
                                }
                                Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                                RowLayout {
                                    Layout.fillWidth: true
                                    visible: operatorViewModel.directionMeasurementCount > 0
                                    Label { text: "ANTEN AÇISI"; color: root.textSecondary; font.pixelSize: 9; Layout.preferredWidth: 86 }
                                    Label { text: "KARE GÜCÜ"; color: root.textSecondary; font.pixelSize: 9; Layout.preferredWidth: 100 }
                                    Label { text: "ANTEN AZİMUTU"; color: root.textSecondary; font.pixelSize: 9; Layout.preferredWidth: 105 }
                                    Label { text: "FREKANS"; color: root.textSecondary; font.pixelSize: 9; Layout.preferredWidth: 95 }
                                    Label { text: "KAYNAK"; color: root.textSecondary; font.pixelSize: 10; Layout.fillWidth: true }
                                }
                                ListView {
                                    id: directionMeasurementList
                                    objectName: "directionMeasurementList"
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
                                            Label { text: modelData.angle; color: root.textPrimary; font.pixelSize: 10; font.family: "Consolas"; Layout.preferredWidth: 78 }
                                            Label { text: modelData.power; color: root.textPrimary; font.pixelSize: 10; font.family: "Consolas"; Layout.preferredWidth: 92 }
                                            Label { text: modelData.bearing; color: root.textPrimary; font.pixelSize: 10; font.family: "Consolas"; Layout.preferredWidth: 97 }
                                            Label { text: modelData.frequency; color: root.textPrimary; font.pixelSize: 10; font.family: "Consolas"; Layout.preferredWidth: 87 }
                                            Label { text: modelData.source; color: root.textSecondary; font.pixelSize: 10; elide: Text.ElideMiddle; Layout.fillWidth: true }
                                        }
                                    }
                                    Label { anchors.centerIn: parent; visible: operatorViewModel.directionMeasurementCount === 0; text: "İlk saha ölçümü bekleniyor"; color: root.textMuted; font.pixelSize: 11 }
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
                    anchors.margins: 14
                    spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        SectionTitle { text: "SİSTEM / DURUM İZLEME"; Layout.fillWidth: true }
                        Label { text: "SALT OKUNUR SİSTEM DURUMU"; color: root.textMuted; font.pixelSize: root.uiMetaTextSize; font.weight: Font.Bold }
                        StateBadge { state: operatorViewModel.sourceReady ? "Hazır" : "Bekliyor" }
                    }
                    Panel {
                        id: systemMetricsPanel
                        Layout.fillWidth: true
                        Layout.preferredHeight: root.height < 780 ? 88 : 108
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 8
                            Repeater {
                                model: [
                                    {"label": "KAYNAK", "value": operatorViewModel.sourceState, "detail": operatorViewModel.sourceName},
                                    {"label": "İŞLENEN KARE", "value": operatorViewModel.frameIndex + " / " + operatorViewModel.frameCount, "detail": operatorViewModel.playing ? "Tarama çalışıyor" : "Tarama duraklatıldı"},
                                    {"label": "HOST İŞLEME", "value": operatorViewModel.performanceText, "detail": "GUI iş parçacığı dışında"},
                                    {"label": "PARAMETRE ÖLÇÜMÜ", "value": operatorViewModel.parameterCapabilityReady ? "Kullanılabilir" : "Kullanılamıyor", "detail": "Profil bütünlüğü doğrulandı"}
                                ]
                                delegate: Rectangle {
                                    required property var modelData
                                    required property int index
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    Layout.fillHeight: true
                                    radius: 4
                                    color: index === 0 && operatorViewModel.sourceReady ? "#0D211F" : root.surfaceAlt
                                    border.color: index === 0 && operatorViewModel.sourceReady ? "#265E50" : root.border
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        spacing: 2
                                        Label { text: modelData.label; color: root.textMuted; font.pixelSize: root.uiDenseMetaTextSize; font.weight: Font.Bold; font.letterSpacing: 0.8 }
                                        Label { text: modelData.value; color: index === 0 ? root.stateColor(operatorViewModel.sourceState) : root.textPrimary; font.pixelSize: root.height < 780 ? 10 : 12; font.family: index === 1 || index === 2 ? "Consolas" : "Segoe UI"; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                                        Label { visible: root.height >= 780; text: modelData.detail; color: root.textSecondary; font.pixelSize: root.uiDenseMetaTextSize; elide: Text.ElideMiddle; Layout.fillWidth: true }
                                    }
                                }
                            }
                        }
                    }
                    RowLayout {
                        id: systemWorkspace
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 10
                        Panel {
                            id: pipelinePanel
                            Layout.preferredWidth: root.width < 1400 ? 330 : 390
                            Layout.fillHeight: true
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 8
                                RowLayout {
                                    Layout.fillWidth: true
                                    SectionTitle { text: "İŞLEME ZİNCİRİ"; Layout.fillWidth: true }
                                    Label { text: operatorViewModel.pipelineBlocks.length + " aşama"; color: root.textMuted; font.pixelSize: root.uiMetaTextSize; font.family: "Consolas" }
                                }
                                Label { text: "Etkin yürütme katmanı ve doğrulanmış kaynak karşılıkları"; color: root.textSecondary; font.pixelSize: root.uiMetaTextSize; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                                ListView {
                                    id: pipelineList
                                    objectName: "pipelineList"
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    spacing: 4
                                    model: operatorViewModel.pipelineBlocks
                                    delegate: Rectangle {
                                        required property var modelData
                                        required property int index
                                        Accessible.name: modelData.name + ", " + modelData.runtime + ", " + modelData.state
                                        Accessible.role: Accessible.ListItem
                                        width: ListView.view.width
                                        height: root.height < 780 ? 48 : 64
                                        radius: 4
                                        color: root.selectedSystemBlock === index ? root.accentSoft : root.surfaceAlt
                                        border.color: root.selectedSystemBlock === index ? root.accent : root.border
                                        Rectangle { anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom; width: 2; visible: root.selectedSystemBlock === index; color: root.accent }
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 10
                                            anchors.rightMargin: 10
                                            spacing: 9
                                            Label { text: (index < 9 ? "0" : "") + (index + 1); color: root.textMuted; font.pixelSize: root.uiMetaTextSize; font.family: "Consolas" }
                                            Rectangle { width: 8; height: 8; radius: 4; color: root.stateColor(modelData.state) }
                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 1
                                                Label { text: modelData.name; color: root.textPrimary; font.pixelSize: root.uiBodyTextSize; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                                                Label { text: modelData.runtime + "  ·  " + modelData.state; color: root.textSecondary; font.pixelSize: root.uiDenseMetaTextSize; font.family: "Consolas" }
                                            }
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root.selectedSystemBlock = index
                                            onDoubleClicked: {
                                                root.selectedSystemBlock = index
                                                if (operatorViewModel.developerMode) operatorViewModel.openImplementationLocation(modelData.id, "host")
                                            }
                                        }
                                    }
                                }
                                Label { visible: operatorViewModel.developerMode; text: "Çift tıklama host kaynak konumunu açar."; color: root.accent; font.pixelSize: root.uiDenseMetaTextSize; Layout.fillWidth: true }
                            }
                        }
                        ColumnLayout {
                            id: systemDetailColumn
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 10
                            Panel {
                                id: componentInspector
                                property var block: operatorViewModel.pipelineBlocks.length > root.selectedSystemBlock ? operatorViewModel.pipelineBlocks[root.selectedSystemBlock] : ({})
                                Layout.fillWidth: true
                                Layout.preferredHeight: root.height < 780 ? 160 : 210
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        SectionTitle { text: "BİLEŞEN DENETÇİSİ"; Layout.fillWidth: true }
                                        Rectangle { width: 8; height: 8; radius: 4; color: root.stateColor(componentInspector.block.state || "") }
                                        Label { text: componentInspector.block.state || "—"; color: root.stateColor(componentInspector.block.state || ""); font.pixelSize: root.uiMetaTextSize; font.weight: Font.Bold }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 3
                                            Label { text: componentInspector.block.name || "Bileşen seçilmedi"; color: root.textPrimary; font.pixelSize: root.height < 780 ? 15 : 18; font.weight: Font.DemiBold }
                                            Label { text: componentInspector.block.description || ""; color: root.textSecondary; font.pixelSize: root.uiBodyTextSize; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                        }
                                        Rectangle {
                                            implicitWidth: runtimeText.implicitWidth + 20
                                            implicitHeight: 30
                                            radius: 4
                                            color: root.accentSoft
                                            border.color: "#28616B"
                                            Label { id: runtimeText; anchors.centerIn: parent; text: componentInspector.block.runtime || "—"; color: root.accent; font.pixelSize: root.uiBodyTextSize; font.family: "Consolas"; font.weight: Font.Bold }
                                        }
                                    }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                                    GridLayout {
                                        columns: 2
                                        Layout.fillWidth: true
                                        columnSpacing: 16
                                        rowSpacing: 4
                                        Label { text: "Uygulama"; color: root.textMuted; font.pixelSize: root.uiMetaTextSize }
                                        Label { text: componentInspector.block.implementation || "—"; color: root.textPrimary; font.pixelSize: root.uiMetaTextSize; Layout.fillWidth: true }
                                        Label { text: "Donanım sınırı"; color: root.textMuted; font.pixelSize: root.uiMetaTextSize }
                                        Label { text: componentInspector.block.rtlPath ? "Kaynak karşılığı mevcut; kart kabulü yok" : "Host üzerinde çalışıyor"; color: componentInspector.block.rtlPath ? root.warning : root.textSecondary; font.pixelSize: root.uiMetaTextSize; Layout.fillWidth: true }
                                    }
                                    RowLayout {
                                        visible: operatorViewModel.developerMode
                                        Layout.fillWidth: true
                                        Item { Layout.fillWidth: true }
                                        QuietButton { text: "Host Kaynağını Aç"; implicitHeight: 30; enabled: !!componentInspector.block.hostPath; onClicked: operatorViewModel.openImplementationLocation(componentInspector.block.id, "host") }
                                        QuietButton { text: "RTL / PS Kaynağını Aç"; implicitHeight: 30; enabled: !!componentInspector.block.rtlPath; onClicked: operatorViewModel.openImplementationLocation(componentInspector.block.id, "rtl") }
                                    }
                                }
                            }
                            Panel {
                                id: systemLogPanel
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 7
                                    RowLayout {
                                        Layout.fillWidth: true
                                        SectionTitle { text: "OPERASYON GÜNLÜĞÜ"; Layout.fillWidth: true }
                                        Repeater {
                                            model: ["Tümü", "Hata", "Kaynak", "Görev"]
                                            delegate: QuietButton {
                                                required property string modelData
                                                text: modelData
                                                implicitWidth: 58
                                                implicitHeight: 26
                                                font.pixelSize: 9
                                                checked: root.systemLogFilter === modelData
                                                onClicked: root.systemLogFilter = modelData
                                            }
                                        }
                                        Label { text: root.systemLogMatchCount() + " kayıt"; color: root.textMuted; font.pixelSize: root.uiMetaTextSize; font.family: "Consolas" }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        color: "#03070B"
                                        border.color: root.border
                                        radius: 4
                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: 8
                                            spacing: 0
                                            RowLayout {
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 24
                                                spacing: 10
                                                Label { text: "NO"; color: root.textMuted; font.pixelSize: root.uiDenseMetaTextSize; font.family: "Consolas"; Layout.preferredWidth: 34 }
                                                Label { text: "ZAMAN"; color: root.textMuted; font.pixelSize: root.uiDenseMetaTextSize; font.family: "Consolas"; Layout.preferredWidth: 62 }
                                                Label { text: "SEVİYE"; color: root.textMuted; font.pixelSize: root.uiDenseMetaTextSize; font.family: "Consolas"; Layout.preferredWidth: 52 }
                                                Label { text: "BİLEŞEN"; color: root.textMuted; font.pixelSize: root.uiDenseMetaTextSize; font.family: "Consolas"; Layout.preferredWidth: 86 }
                                                Label { text: "OLAY"; color: root.textMuted; font.pixelSize: root.uiDenseMetaTextSize; font.family: "Consolas"; Layout.fillWidth: true }
                                            }
                                            Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                                            ListView {
                                                id: systemLog
                                                objectName: "systemLog"
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                                clip: true
                                                model: operatorViewModel.eventLog
                                                delegate: Rectangle {
                                                    required property var modelData
                                                    required property int index
                                                    property bool matches: root.systemLogMatches(modelData)
                                                    width: ListView.view.width
                                                    height: matches ? 30 : 0
                                                    visible: matches
                                                    color: matches && index % 2 ? "#050A0F" : "transparent"
                                                    RowLayout {
                                                        anchors.fill: parent
                                                        spacing: 10
                                                        Label { text: modelData.sequence; color: root.textMuted; font.pixelSize: root.uiMetaTextSize; font.family: "Consolas"; Layout.preferredWidth: 34 }
                                                        Label { text: modelData.time; color: root.textMuted; font.pixelSize: root.uiMetaTextSize; font.family: "Consolas"; Layout.preferredWidth: 62 }
                                                        Label { text: modelData.level; color: modelData.level === "HATA" ? root.danger : modelData.level === "UYARI" ? root.warning : root.success; font.pixelSize: root.uiDenseMetaTextSize; font.family: "Consolas"; font.weight: Font.Bold; Layout.preferredWidth: 52 }
                                                        Label { text: modelData.component.toUpperCase(); color: root.accent; font.pixelSize: root.uiDenseMetaTextSize; font.family: "Consolas"; font.weight: Font.Bold; Layout.preferredWidth: 86; elide: Text.ElideRight }
                                                        Label { text: modelData.message; color: root.textPrimary; font.pixelSize: root.uiMetaTextSize; font.family: "Consolas"; Layout.fillWidth: true; elide: Text.ElideRight }
                                                    }
                                                }
                                            }
                                            RowLayout {
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 20
                                                Label { text: "●"; color: root.success; font.pixelSize: root.uiDenseMetaTextSize }
                                                Label { text: "Canlı olay akışı"; color: root.textMuted; font.pixelSize: root.uiDenseMetaTextSize; font.family: "Consolas"; Layout.fillWidth: true }
                                                Label { text: "Salt okunur · komut çalıştırmaz"; color: root.textMuted; font.pixelSize: root.uiDenseMetaTextSize; font.family: "Consolas" }
                                            }
                                        }
                                        Label {
                                            anchors.centerIn: parent
                                            visible: root.systemLogMatchCount() === 0
                                            text: "Bu filtreyle eşleşen olay yok"
                                            color: root.textSecondary
                                            font.pixelSize: root.uiBodyTextSize
                                        }
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
