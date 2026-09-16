import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import Teknofest.Display 1.0
import "DetectionGuidePainter.js" as DetectionGuidePainter
import "MainNavigation.js" as MainNavigation

ApplicationWindow {
    id: root
    width: 1440
    height: 900
    minimumWidth: 1180
    minimumHeight: 680
    visible: true
    title: "BÂZ"
    color: "#181818"

    property int workspace: 0
    property bool startupIntroVisible: startupIntroRequested
    property bool navigationOpen: false
    property bool sourcePanelOpen: false
    property bool rfSearchMode: false
    property real spectrumViewStart: 0
    property real spectrumViewEnd: 1
    property var spectrumViewHistory: [{"start": 0, "end": 1}]
    property int spectrumViewHistoryIndex: 0
    property string spectrumHistorySource: ""
    property real spectrumCursorNormalized: -1
    property bool spectrumCursorVisible: false
    property real analysisDragStart: -1
    property real analysisDragEnd: -1
    property int spectrumTaskTab: 0
    property color appBackground: "#181818"
    property color surface: "#1F1F1F"
    property color surfaceAlt: "#202020"
    property color raised: "#2B2B2B"
    property color border: "#2B2B2B"
    property color borderStrong: "#3C3C3C"
    property color textPrimary: "#CCCCCC"
    property color textSecondary: "#9D9D9D"
    property color textMuted: "#868686"
    property color accent: "#0078D4"
    property color accentSoft: "#2B2B2B"
    property color success: "#2EA043"
    property color warning: "#E2C08D"
    property color danger: "#F85149"
    property int transitionDuration: operatorViewModel.reducedMotion ? 0 : 170
    property int uiSectionTextSize: width >= 1600 ? 11 : 10
    property int uiBodyTextSize: width >= 1600 ? 11 : 10
    property int uiMetaTextSize: width >= 1600 ? 10 : 9
    property int uiDenseMetaTextSize: width >= 1600 ? 10 : 8
    readonly property int liveSessionFrameLimit: 878906

    onWorkspaceChanged: {
        if (workspace === 0) {
            spectrumCanvas.requestPaint()
            waterfall.requestPaint()
        }
        Qt.callLater(function() {
            var navigationIndex = root.workspace === 0 ? root.spectrumTaskTab : root.workspace + 1
            var target = workspaceNavigation.itemAt(navigationIndex)
            if (target) target.forceActiveFocus(Qt.ShortcutFocusReason)
        })
    }

    onSpectrumTaskTabChanged: {
        if (workspace !== 0) return
        spectrumCanvas.requestPaint()
        waterfall.requestPaint()
        Qt.callLater(function() {
            var target = workspaceNavigation.itemAt(root.spectrumTaskTab)
            if (target) target.forceActiveFocus(Qt.ShortcutFocusReason)
        })
    }

    function setSpectrumView(start, end) {
        var span = Math.max(0.02, Math.min(1.0, end - start))
        var boundedStart = Math.max(0.0, Math.min(1.0 - span, start))
        spectrumViewStart = boundedStart
        spectrumViewEnd = boundedStart + span
    }

    function paintDetectionGuides(ctx, left, top, plotWidth, plotHeight, includeCandidates) {
        DetectionGuidePainter.paintDetectionGuides(root, operatorViewModel, ctx, left, top, plotWidth, plotHeight, includeCandidates)
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
        return operatorViewModel.spectrumCenterFrequencyHz + (normalized - 0.5) * operatorViewModel.spectrumSampleRateHz
    }

    function normalizedAtSpectrumX(x, width) {
        var plotLeft = 0
        var plotWidth = Math.max(1, width - 1)
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

    function receiverBadgeState() {
        if (operatorViewModel.busy || operatorViewModel.liveSessionActive) return "Çalışıyor"
        if (operatorViewModel.sourceState === "Hata") return "Hata"
        if (operatorViewModel.hackrfReady) return "Hazır"
        return "Bekliyor"
    }

    function activateWorkspaceNavigation(item) {
        MainNavigation.activateWorkspace(root, item)
    }

    function togglePrimaryNavigation() {
        navigationOpen = !navigationOpen
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

    function paintCoarseDetectionGuides(ctx, left, top, plotWidth, plotHeight) {
        DetectionGuidePainter.paintCoarseDetectionGuides(root, operatorViewModel, ctx, left, top, plotWidth, plotHeight)
    }

    FileDialog {
        id: wavDialog
        title: "WAV çıktısını kaydet"
        nameFilters: ["WAV ses dosyası (*.wav)"]
        fileMode: FileDialog.SaveFile
        defaultSuffix: "wav"
        onAccepted: operatorViewModel.exportListeningWav(selectedFile.toString())
    }

    Shortcut { sequence: "Space"; onActivated: if (root.workspace === 0 && root.spectrumTaskTab === 0 && operatorViewModel.sourceReady && !operatorViewModel.busy) operatorViewModel.playing ? operatorViewModel.pause() : operatorViewModel.startScan() }
    Shortcut { sequence: "Ctrl+1"; onActivated: { root.workspace = 0; root.spectrumTaskTab = 0 } }
    Shortcut { sequence: "Ctrl+2"; onActivated: { root.workspace = 0; root.spectrumTaskTab = 1 } }
    Shortcut { sequence: "Ctrl+3"; onActivated: root.workspace = 1 }
    Shortcut { sequence: "Ctrl+4"; onActivated: root.workspace = 2 }

    header: Rectangle {
        height: 76
        color: "#181818"
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

            RowLayout {
                Layout.preferredWidth: 246
                spacing: 8

                Button {
                    id: primaryMenuButton
                    objectName: "primaryMenuButton"
                    Layout.preferredWidth: 106
                    Layout.preferredHeight: 62
                    flat: true
                    Accessible.name: "Ana görev menüsü"
                    Accessible.description: navigationOpen ? "Görev menüsü açık; kapat" : "Görev menüsünü aç"
                    ToolTip.visible: hovered
                    ToolTip.delay: 450
                    ToolTip.text: navigationOpen ? "Görev menüsünü kapat" : "Görev menüsünü aç"
                    onClicked: root.togglePrimaryNavigation()
                    background: Rectangle {
                        radius: 4
                        color: primaryMenuButton.hovered || primaryMenuButton.activeFocus || root.navigationOpen
                               ? root.accentSoft : "transparent"
                        border.color: primaryMenuButton.activeFocus || root.navigationOpen ? root.accent : "transparent"
                        Behavior on color { ColorAnimation { duration: root.transitionDuration } }
                    }
                    contentItem: Item {
                        Image {
                            anchors.fill: parent
                            source: "../assets/baz-logo-glow.png"
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            mipmap: true
                            asynchronous: true
                            opacity: 0.95
                        }
                        Image {
                            objectName: "brandLogo"
                            anchors.fill: parent
                            anchors.margins: 3
                            source: "../assets/baz-logo-metal-red.png"
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            mipmap: true
                            asynchronous: true
                        }
                    }
                }

                Label {
                    text: "BÂZ"
                    color: root.accent
                    font.pixelSize: 25
                    font.weight: Font.Bold
                    font.letterSpacing: 2.8
                    verticalAlignment: Text.AlignVCenter
                    Layout.fillWidth: true
                }
            }

            Item { Layout.fillWidth: true }

            ColumnLayout {
                visible: operatorViewModel.sourceReady || operatorViewModel.liveSessionActive
                spacing: 2
                Label { text: "MERKEZ FREKANSI"; color: root.textMuted; font.pixelSize: 9; font.weight: Font.DemiBold }
                Label { text: operatorViewModel.centerFrequencyText; color: root.textPrimary; font.pixelSize: 13; font.family: "Consolas" }
            }
            ColumnLayout {
                visible: operatorViewModel.sourceReady || operatorViewModel.liveSessionActive
                spacing: 2
                Label { text: operatorViewModel.sampleRateTitle; color: root.textMuted; font.pixelSize: 9; font.weight: Font.DemiBold }
                Label { text: operatorViewModel.sampleRateText; color: root.textPrimary; font.pixelSize: 13; font.family: "Consolas" }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            id: primaryNavigation
            objectName: "primaryNavigation"
            property real animatedWidth: root.navigationOpen ? 76 : 0
            Layout.preferredWidth: animatedWidth
            Layout.minimumWidth: animatedWidth
            Layout.maximumWidth: animatedWidth
            Layout.fillHeight: true
            visible: animatedWidth > 0.5
            opacity: root.navigationOpen ? 1 : 0
            clip: true
            color: "#181818"
            border.color: root.border
            border.width: 1
            Behavior on opacity { NumberAnimation { duration: root.transitionDuration } }

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
                        {"label": "Tespit", "title": "Sinyal Tespiti", "icon": "spectrum", "workspace": 0, "task": 0, "shortcut": 1},
                        {"label": "Parametre", "title": "Parametre Çıkarımı", "icon": "measurement", "workspace": 0, "task": 1, "shortcut": 2},
                        {"label": "Dinleme", "title": "Sinyal Dinleme", "icon": "listening", "workspace": 1, "task": -1, "shortcut": 3},
                        {"label": "Yön Bulma", "title": "Yön Bulma", "icon": "direction", "workspace": 2, "task": -1, "shortcut": 4}
                    ]
                    delegate: Button {
                        id: navControl
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true
                        Layout.preferredHeight: 58
                        flat: true
                        objectName: "workspaceNavigation" + index
                        Accessible.name: modelData.title
                        property bool selected: root.workspace === modelData.workspace
                                                && (modelData.task < 0 || root.spectrumTaskTab === modelData.task)
                        Accessible.description: modelData.title + " çalışma alanı, Ctrl+" + modelData.shortcut
                                                + (modelData.task === 0 ? "; tekrar seçildiğinde alıcı seçeneklerini açar veya kapatır" : "")
                        ToolTip.visible: hovered
                        ToolTip.delay: 500
                        ToolTip.text: modelData.title + " · Ctrl+" + modelData.shortcut
                        onClicked: root.activateWorkspaceNavigation(modelData)
                        background: Rectangle {
                            color: navControl.selected ? root.accentSoft : "transparent"
                            radius: 4
                            Behavior on color { ColorAnimation { duration: root.transitionDuration } }
                            Rectangle {
                                visible: navControl.selected
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
                            NavIcon { anchors.horizontalCenter: parent.horizontalCenter; kind: modelData.icon; strokeColor: navControl.selected ? root.accent : root.textSecondary }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.label; color: navControl.selected ? root.textPrimary : root.textSecondary; font.pixelSize: 9 }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.workspace

            // OPERASYON
            Item {
                RxSurveyView {
                    objectName: "frequencySurveyView"
                    anchors.fill: parent
                    theme: root
                    visible: operatorViewModel.sourceMode === "hackrf" && root.rfSearchMode && root.spectrumTaskTab === 0
                    onFixedBandRequested: root.rfSearchMode = false
                    onSurveyRequested: root.rfSearchMode = true
                    onParameterRequested: {
                        root.rfSearchMode = false
                        root.spectrumTaskTab = 1
                    }
                }
                RowLayout {
                    visible: operatorViewModel.sourceMode !== "hackrf" || !root.rfSearchMode || root.spectrumTaskTab !== 0
                    anchors.fill: parent
                    spacing: 0

                    Panel {
                        id: sourcePanel
                        objectName: "sourcePanel"
                        property real animatedWidth: root.sourcePanelOpen && root.spectrumTaskTab === 0 ? 220 : 0
                        Layout.preferredWidth: animatedWidth
                        Layout.minimumWidth: animatedWidth
                        Layout.maximumWidth: animatedWidth
                        Layout.fillHeight: true
                        visible: animatedWidth > 0.5
                        opacity: root.sourcePanelOpen && root.spectrumTaskTab === 0 ? 1 : 0
                        clip: true
                        color: "transparent"
                        border.width: 0
                        radius: 0
                        Behavior on animatedWidth { NumberAnimation { duration: root.transitionDuration + 60; easing.type: Easing.OutCubic } }
                        Behavior on opacity { NumberAnimation { duration: root.transitionDuration } }
                        Rectangle {
                            objectName: "sourcePanelDivider"
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: 1
                            color: root.border
                        }
                        ColumnLayout {
                            objectName: "sourcePanelContent"
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 12
                            RowLayout {
                                Layout.fillWidth: true
                                SectionTitle { text: "ALICI AYARLARI"; Layout.fillWidth: true }
                                StateBadge {
                                    objectName: "receiverSettingsBadge"
                                    state: root.receiverBadgeState()
                                }
                            }

                            Loader {
                                Layout.fillWidth: true
                                sourceComponent: hackrfControls
                            }

                            Rectangle {
                                objectName: "receiverError"
                                visible: !!operatorViewModel.errorMessage
                                Layout.fillWidth: true
                                implicitHeight: receiverErrorContent.implicitHeight + 18
                                radius: 4
                                color: "#1F1F1F"
                                border.color: root.danger
                                ColumnLayout {
                                    id: receiverErrorContent
                                    anchors.fill: parent
                                    anchors.margins: 9
                                    Label { objectName: "receiverErrorText"; text: operatorViewModel.errorMessage; color: root.danger; font.pixelSize: 10; font.weight: Font.DemiBold; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                }
                            }

                            Item { Layout.fillHeight: true }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 0

                        Panel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: "transparent"
                            border.width: 0
                            radius: 0
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 0
                                anchors.rightMargin: 0
                                anchors.topMargin: 6
                                anchors.bottomMargin: 0
                                spacing: 6
                                SectionTitle {
                                    objectName: "spectrumSectionTitle"
                                    text: "SPEKTRUM"
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignHCenter
                                    font.pixelSize: root.uiSectionTextSize + 2
                                }
                                Canvas {
                                    id: spectrumCanvas
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    SpectrumTrace {
                                        anchors.fill: parent
                                        z: -1
                                        source: operatorViewModel.spectralDisplay
                                        viewStart: root.spectrumViewStart
                                        viewEnd: root.spectrumViewEnd
                                    }
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
                                        function onDetectionsChanged() {
                                            var selectedId = operatorViewModel.selectedDetectionId
                                            if (selectedId !== spectrumCanvas.lastSelectionId) {
                                                spectrumCanvas.lastSelectionId = selectedId
                                                spectrumCanvas.selectionOpacity = selectedId >= 0 ? 0 : 1
                                                selectionFade.restart()
                                            }
                                            if (root.workspace === 0) spectrumCanvas.requestPaint()
                                        }
                                    }
                                    Label {
                                        id: emptySpectrumMessage
                                        objectName: "emptySpectrumMessage"
                                        anchors.centerIn: parent
                                        visible: operatorViewModel.spectrumPointCount < 2
                                        text: "Taramayı başlatınca spektrum burada görünür"
                                        color: root.textMuted
                                        font.pixelSize: 11
                                        Accessible.role: Accessible.StaticText
                                    }
                                    onPaint: {
                                        var ctx = getContext("2d")
                                        ctx.reset()
                                        ctx.clearRect(0, 0, width, height)
                                        var plotLeft = 0
                                        var plotRight = width - 1
                                        var plotTop = 0
                                        var plotBottom = height - 1
                                        var plotWidth = plotRight - plotLeft
                                        var plotHeight = plotBottom - plotTop
                                        var gridRows = 6
                                        var gridColumns = Math.max(1, Math.round(plotWidth * gridRows / plotHeight))
                                        ctx.strokeStyle = "#2B2B2B"
                                        ctx.lineWidth = 1
                                        for (var gx = 0; gx <= gridColumns; gx++) {
                                            var x = plotLeft + gx * plotWidth / gridColumns
                                            ctx.beginPath(); ctx.moveTo(x, plotTop); ctx.lineTo(x, plotBottom); ctx.stroke()
                                        }
                                         for (var gy = 0; gy <= gridRows; gy++) {
                                             var y = plotTop + gy * plotHeight / gridRows
                                             ctx.beginPath(); ctx.moveTo(plotLeft, y); ctx.lineTo(plotRight, y); ctx.stroke()
                                         }
                                         if (operatorViewModel.spectrumPointCount < 2) return
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
                                                ctx.fillStyle = operatorViewModel.selectedDetectionCurrent ? "rgba(226,192,141,0.10)" : "rgba(157,157,157,0.06)"
                                                ctx.fillRect(coarseX1, plotTop, coarseX2 - coarseX1, plotHeight)
                                                ctx.strokeStyle = operatorViewModel.selectedDetectionCurrent ? "rgba(226,192,141,0.82)" : "rgba(157,157,157,0.55)"
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
                                                ctx.fillStyle = operatorViewModel.analysisSpanConfirmed ? "rgba(0,120,212,0.13)" : "rgba(0,120,212,0.07)"
                                                ctx.fillRect(analysisX1, plotTop, Math.max(2, analysisX2 - analysisX1), plotHeight)
                                                ctx.strokeStyle = operatorViewModel.analysisSpanConfirmed ? "rgba(0,120,212,0.95)" : "rgba(0,120,212,0.55)"
                                                ctx.strokeRect(analysisX1, plotTop, Math.max(2, analysisX2 - analysisX1), plotHeight)
                                                ctx.globalAlpha = 1
                                            }
                                        }
                                        if (operatorViewModel.sourceMode === "hackrf" && operatorViewModel.liveDetectionEnabled) {
                                            var fpgaStart = operatorViewModel.liveDetectionStartNormalized
                                            var fpgaEnd = operatorViewModel.liveDetectionEndNormalized
                                            var fpgaX1 = plotLeft + (fpgaStart - root.spectrumViewStart) * plotWidth / (root.spectrumViewEnd - root.spectrumViewStart)
                                            var fpgaX2 = plotLeft + (fpgaEnd - root.spectrumViewStart) * plotWidth / (root.spectrumViewEnd - root.spectrumViewStart)
                                            if (fpgaX2 >= plotLeft && fpgaX1 <= plotRight) {
                                                fpgaX1 = Math.max(plotLeft, fpgaX1); fpgaX2 = Math.min(plotRight, fpgaX2)
                                                ctx.fillStyle = "rgba(0,120,212,0.05)"
                                                ctx.fillRect(fpgaX1, plotTop, fpgaX2 - fpgaX1, plotHeight)
                                                ctx.strokeStyle = "rgba(0,120,212,0.45)"
                                                ctx.setLineDash([4, 4]); ctx.strokeRect(fpgaX1, plotTop, fpgaX2 - fpgaX1, plotHeight); ctx.setLineDash([])
                                                ctx.fillStyle = "rgba(0,120,212,0.82)"
                                                ctx.font = "8px 'Segoe UI'"
                                                ctx.textAlign = "center"
                                                if (fpgaX2 - fpgaX1 < plotWidth * 0.98)
                                                    ctx.fillText("TARANAN ARALIK", (fpgaX1 + fpgaX2) / 2, plotTop + 10)
                                            }
                                        }
                                         var low = operatorViewModel.spectrumMinDb
                                        var high = operatorViewModel.spectrumMaxDb
                                        ctx.fillStyle = "#868686"
                                        ctx.font = "9px Consolas"
                                        ctx.textAlign = "left"
                                        ctx.textBaseline = "middle"
                                        for (var labelIndex = 0; labelIndex <= gridRows; labelIndex++) {
                                            var labelY = Math.max(6, Math.min(plotBottom - 6,
                                                                             plotTop + labelIndex * plotHeight / gridRows))
                                            var labelValue = high - labelIndex * (high - low) / gridRows
                                            ctx.fillText(labelValue.toFixed(0), plotLeft + 5, labelY)
                                        }
                                        ctx.strokeStyle = "rgba(204,204,204,0.32)"
                                        ctx.setLineDash([3, 4])
                                        if (root.spectrumViewStart <= 0.5 && root.spectrumViewEnd >= 0.5) {
                                            var centerX = plotLeft + (0.5 - root.spectrumViewStart) * plotWidth / (root.spectrumViewEnd - root.spectrumViewStart)
                                            ctx.beginPath(); ctx.moveTo(centerX, plotTop); ctx.lineTo(centerX, plotBottom); ctx.stroke()
                                        }
                                        ctx.setLineDash([])
                                        root.paintDetectionGuides(ctx, plotLeft, plotTop, plotWidth, plotHeight)
                                        root.paintCoarseDetectionGuides(ctx, plotLeft, plotTop, plotWidth, plotHeight)
                                        if (root.analysisDragStart >= 0 && root.analysisDragEnd >= 0) {
                                            var dragX1 = plotLeft + (Math.min(root.analysisDragStart, root.analysisDragEnd) - root.spectrumViewStart) * plotWidth / (root.spectrumViewEnd - root.spectrumViewStart)
                                            var dragX2 = plotLeft + (Math.max(root.analysisDragStart, root.analysisDragEnd) - root.spectrumViewStart) * plotWidth / (root.spectrumViewEnd - root.spectrumViewStart)
                                            ctx.fillStyle = "rgba(0,120,212,0.16)"
                                            ctx.fillRect(Math.max(plotLeft, dragX1), plotTop, Math.max(2, Math.min(plotRight, dragX2) - Math.max(plotLeft, dragX1)), plotHeight)
                                            ctx.strokeStyle = root.accent
                                            ctx.strokeRect(Math.max(plotLeft, dragX1), plotTop, Math.max(2, Math.min(plotRight, dragX2) - Math.max(plotLeft, dragX1)), plotHeight)
                                        }
                                        if (root.spectrumCursorVisible && root.spectrumCursorNormalized >= root.spectrumViewStart
                                                && root.spectrumCursorNormalized <= root.spectrumViewEnd) {
                                            var cursorX = plotLeft + (root.spectrumCursorNormalized - root.spectrumViewStart) * plotWidth / (root.spectrumViewEnd - root.spectrumViewStart)
                                            ctx.strokeStyle = "rgba(204,204,204,0.72)"
                                            ctx.lineWidth = 1
                                            ctx.beginPath(); ctx.moveTo(cursorX, plotTop); ctx.lineTo(cursorX, plotBottom); ctx.stroke()
                                            var cursorText = root.formatFrequency(root.frequencyAt(root.spectrumCursorNormalized))
                                            ctx.font = "10px Consolas"
                                            var cursorWidth = ctx.measureText(cursorText).width + 12
                                            var cursorLabelX = Math.max(plotLeft, Math.min(plotRight - cursorWidth, cursorX - cursorWidth / 2))
                                            ctx.fillStyle = "rgba(32,32,32,0.94)"
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
                                    visible: operatorViewModel.spectrumPointCount >= 2
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
                            objectName: "waterfallPanel"
                            visible: root.spectrumTaskTab === 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.max(210, Math.min(310, root.height * 0.32))
                            color: "transparent"
                            border.width: 0
                            radius: 0
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 0
                                anchors.rightMargin: 0
                                anchors.topMargin: 6
                                anchors.bottomMargin: 0
                                spacing: 6
                                SectionTitle {
                                    objectName: "spectrogramSectionTitle"
                                    text: "SPEKTROGRAM"
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignHCenter
                                    font.pixelSize: root.uiSectionTextSize + 2
                                }
                                Canvas {
                                    id: waterfall
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    property real plotLeft: 0
                                    property real plotWidth: Math.max(1, width - 1)
                                    WaterfallImage {
                                        anchors.fill: parent
                                        z: -1
                                        source: operatorViewModel.spectralDisplay
                                        viewStart: root.spectrumViewStart
                                        viewEnd: root.spectrumViewEnd
                                    }
                                     Connections {
                                        target: operatorViewModel
                                        function onDetectionsChanged() { if (root.workspace === 0) waterfall.requestPaint() }
                                     }
                                     Label {
                                         anchors.centerIn: parent
                                         visible: operatorViewModel.spectrumPointCount < 2
                                         text: "Taramayı başlatınca spektrogram burada görünür"
                                         color: root.textMuted
                                         font.pixelSize: 11
                                     }
                                     onPaint: {
                                         var ctx = getContext("2d")
                                         ctx.reset(); ctx.clearRect(0, 0, width, height)
                                         if (operatorViewModel.spectrumPointCount < 2) return
                                         root.paintDetectionGuides(ctx, plotLeft, 0, plotWidth, height, false)
                                        if (root.spectrumCursorVisible && root.spectrumCursorNormalized >= root.spectrumViewStart
                                                && root.spectrumCursorNormalized <= root.spectrumViewEnd) {
                                            var cursorX = plotLeft + (root.spectrumCursorNormalized - root.spectrumViewStart) * plotWidth / (root.spectrumViewEnd - root.spectrumViewStart)
                                            ctx.strokeStyle = "rgba(204,204,204,0.72)"
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
                                            root.spectrumCursorNormalized = root.spectrumViewStart + Math.max(0, Math.min(1, (mouse.x - waterfall.plotLeft) / waterfall.plotWidth)) * (root.spectrumViewEnd - root.spectrumViewStart)
                                        }
                                        onPositionChanged: function(mouse) {
                                            root.spectrumCursorVisible = true
                                            root.spectrumCursorNormalized = root.spectrumViewStart + Math.max(0, Math.min(1, (mouse.x - waterfall.plotLeft) / waterfall.plotWidth)) * (root.spectrumViewEnd - root.spectrumViewStart)
                                            if (pressed) {
                                                var span = pressEnd - pressStart
                                                var delta = -(mouse.x - pressX) * span / waterfall.plotWidth
                                                root.setSpectrumView(pressStart + delta, pressEnd + delta)
                                            }
                                            spectrumCanvas.requestPaint(); waterfall.requestPaint()
                                        }
                                        onReleased: function(mouse) { if (Math.abs(mouse.x - pressX) >= 2) root.commitSpectrumView() }
                                        onWheel: function(wheel) { root.zoomSpectrum(Math.max(0, Math.min(1, (wheel.x - waterfall.plotLeft) / waterfall.plotWidth)), wheel.angleDelta.y > 0 ? 0.75 : 1.333333) }
                                        onDoubleClicked: root.resetSpectrumView()
                                    }
                                }
                            }
                        }

                    }

                    Panel {
                        objectName: "signalTaskPanel"
                        Layout.preferredWidth: root.spectrumTaskTab === 0 ? 290 : Math.min(500, root.width * 0.42)
                        Layout.fillHeight: true
                        color: "transparent"
                        border.width: 0
                        radius: 0
                        Rectangle {
                            objectName: "signalPanelDivider"
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: 1
                            color: root.border
                        }
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            anchors.topMargin: 6
                            anchors.bottomMargin: 14
                            spacing: 10
                            Item {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 22
                                SectionTitle {
                                    objectName: "signalDetectionSectionTitle"
                                    anchors.centerIn: parent
                                    text: root.spectrumTaskTab === 0 ? "SİNYAL TESPİTİ" : "PARAMETRE ÇIKARIMI"
                                    horizontalAlignment: Text.AlignHCenter
                                    font.pixelSize: root.uiSectionTextSize + 2
                                }
                                Rectangle {
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: root.spectrumTaskTab === 0 && operatorViewModel.stableDetectionCount > 0
                                    width: detectionCount.implicitWidth + 14
                                    height: 22
                                    radius: 11
                                    color: root.accentSoft
                                    Label { id: detectionCount; anchors.centerIn: parent; text: operatorViewModel.stableDetectionCount; color: root.accent; font.pixelSize: 10; font.weight: Font.Bold }
                                }
                            }
                            Rectangle {
                                id: signalSummaryCard
                                objectName: "signalSummaryCard"
                                visible: root.spectrumTaskTab !== 0
                                Layout.fillWidth: true
                                implicitHeight: 64
                                radius: 3
                                color: root.surfaceAlt
                                border.color: root.border
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Label {
                                            text: operatorViewModel.sourceReady ? operatorViewModel.selectedDetectionTitle : "Tespit için kaynak seçin"
                                            color: root.textPrimary
                                            font.pixelSize: 12
                                            font.weight: Font.DemiBold
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Label {
                                                text: operatorViewModel.sourceReady ? operatorViewModel.selectedDetectionFrequencyText : ""
                                                color: root.textPrimary
                                                font.pixelSize: 12
                                                font.family: "Consolas"
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }
                                    QuietButton {
                                        visible: root.spectrumTaskTab === 1 && operatorViewModel.sourceMode === "hackrf" && operatorViewModel.selectedDetectionId >= 0
                                        text: "×"
                                        implicitWidth: 28
                                        Accessible.name: "Tespit seçimini temizle"
                                        onClicked: operatorViewModel.clearDetectionSelection()
                                    }
                                    QuietButton {
                                        objectName: "measurementOpenButton"
                                        text: "Ölçüm ›"
                                        visible: false
                                        implicitWidth: 68
                                        implicitHeight: 30
                                        enabled: operatorViewModel.measurementSelectionReady
                                        Accessible.name: "Seçili sinyalin ölçüm adımına geç"
                                        onClicked: root.spectrumTaskTab = 1
                                    }
                                    QuietButton {
                                        objectName: "measurementChooseDetection"
                                        text: operatorViewModel.selectedDetectionId >= 0 ? "Tespiti Değiştir" : "Tespit Seç"
                                        visible: root.spectrumTaskTab === 1
                                        implicitHeight: 30
                                        Accessible.name: "Sinyal tespiti ekranına dön"
                                        onClicked: root.spectrumTaskTab = 0
                                    }
                                }
                            }
                            Label {
                                objectName: "activeDetectionVerification"
                                visible: root.spectrumTaskTab === 0 && operatorViewModel.fixedVerificationActive
                                text: "Ek doğrulama sürüyor"
                                color: root.warning
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                            }
                            ListView {
                                id: detectionList
                                objectName: "detectionList"
                                visible: root.spectrumTaskTab === 0
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                spacing: 0
                                model: operatorViewModel.detectionModel
                                Label {
                                    id: emptyDetectionMessage
                                    objectName: "emptyDetectionMessage"
                                    anchors.centerIn: parent
                                    width: Math.max(1, parent.width - 24)
                                    horizontalAlignment: Text.AlignHCenter
                                    wrapMode: Text.WordWrap
                                    visible: operatorViewModel.detections.length === 0
                                             && operatorViewModel.hackrfReady
                                    text: !operatorViewModel.liveSessionActive ? "Taramayı başlatın"
                                          : "Sinyal aranıyor"
                                    color: root.textMuted
                                    font.pixelSize: 11
                                }
                                ScrollBar.vertical: ScrollBar {
                                    policy: ScrollBar.AlwaysOff
                                }
                                header: Label {
                                    visible: false
                                    width: detectionList.width
                                    height: visible ? 30 : 0
                                    text: "Sinyal durumu"
                                    color: root.textMuted
                                    font.pixelSize: 9
                                    font.weight: Font.DemiBold
                                    verticalAlignment: Text.AlignVCenter
                                }
                                delegate: AbstractButton {
                                    id: detectionDelegate
                                    hoverEnabled: true
                                    leftPadding: 10
                                    rightPadding: 12
                                    topPadding: 6
                                    bottomPadding: 6
                                    required property var modelData
                                    width: ListView.view.width
                                    height: 62
                                    enabled: modelData.observed
                                    Accessible.name: modelData.frequency + ", " + modelData.state + ", " + modelData.title
                                    ToolTip.visible: hovered && !!modelData.verificationLabel
                                    ToolTip.text: modelData.verificationLabel || ""
                                    onPressed: operatorViewModel.selectDetection(modelData.eventId)
                                    background: Rectangle {
                                        radius: 0
                                        color: operatorViewModel.selectedDetectionId === modelData.eventId ? root.accentSoft : detectionDelegate.hovered ? root.raised : "transparent"
                                        border.width: 0
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
                                        Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 1; color: root.border }
                                    }
                                    contentItem: ColumnLayout {
                                        spacing: 3
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Label { text: operatorViewModel.sourceMode === "hackrf" ? modelData.frequency : modelData.title; color: root.textPrimary; font.pixelSize: 12; font.weight: Font.DemiBold; Layout.fillWidth: true }
                                            Label {
                                                text: !modelData.observed ? "Artık alınmıyor"
                                                      : operatorViewModel.sourceMode !== "hackrf" ? (modelData.stateKey === "confirmed" ? "Tespit edildi" : "Aday")
                                                      : modelData.verificationKey === "verified_two_lo" ? "Doğrulandı"
                                                      : modelData.verificationKey === "rx_supported" ? "Tespit edildi" : "Aday"
                                                color: !modelData.observed ? root.textMuted
                                                     : modelData.verificationKey === "verified_two_lo" ? root.success
                                                     : modelData.verificationKey === "rx_supported" ? root.accent : root.warning
                                                font.pixelSize: 10
                                                font.weight: Font.DemiBold
                                            }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Label {
                                                visible: operatorViewModel.sourceMode !== "hackrf" || (modelData.observed && modelData.verificationKey !== "rx_supported")
                                                text: operatorViewModel.sourceMode !== "hackrf" ? modelData.frequency
                                                      : modelData.verificationKey === "pending" ? "Kontrol ediliyor; biraz bekleyin."
                                                      : modelData.verificationKey === "verified_two_lo" ? "Aynı frekans tekrar görüldü; önce bunu inceleyin."
                                                      : modelData.verificationLabel || "Doğrulama bekliyor"
                                                wrapMode: Text.WordWrap
                                                color: root.textMuted
                                                font.pixelSize: 10
                                                Layout.fillWidth: true
                                            }
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
                            Rectangle { visible: root.spectrumTaskTab === 1; Layout.fillWidth: true; height: 1; color: root.border }
                            RowLayout {
                                visible: root.spectrumTaskTab === 1
                                Layout.fillWidth: true
                                SectionTitle { text: "ÖLÇÜM DURUMU"; Layout.fillWidth: true }
                                Label {
                                    readonly property int validMeasurements: operatorViewModel.parameterRows.filter(function(row) {
                                        return ["emission_center_frequency", "occupied_bandwidth", "channel_power_dbfs", "signal_domain"].indexOf(row.key) >= 0 && row.state === "valid"
                                    }).length
                                    text: operatorViewModel.errorMessage.length > 0 ? "HATA"
                                          : operatorViewModel.parameterMeasurementActive ? "ÖLÇÜLÜYOR"
                                          : operatorViewModel.parameterRows.length > 0 ? (validMeasurements === 4 ? "SONUÇ HAZIR" : validMeasurements > 0 ? "KISMİ SONUÇ" : "ÖLÇÜM DOĞRULANAMADI")
                                          : operatorViewModel.sourceMode === "hackrf" && !operatorViewModel.liveSessionActive && operatorViewModel.selectedDetectionId >= 0 ? "ALIM DURDU"
                                          : operatorViewModel.analysisSpanConfirmed ? "ARALIK ONAYLI"
                                          : operatorViewModel.measurementSelectionReady ? "ARALIK BEKLİYOR"
                                          : "TESPİT BEKLİYOR"
                                    color: operatorViewModel.errorMessage.length > 0 ? root.danger
                                          : operatorViewModel.parameterRows.length > 0 ? (validMeasurements === 4 ? root.success : root.warning)
                                          : operatorViewModel.analysisSpanConfirmed ? root.accent : root.textMuted
                                    font.pixelSize: 8
                                    font.weight: Font.Bold
                                }
                            }
                            ParameterMeasurementPanel {
                                visible: root.spectrumTaskTab === 1
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                viewModel: operatorViewModel
                                onDetectionRequested: root.spectrumTaskTab = 0
                                onListeningRequested: root.workspace = 1
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
                                SectionTitle { text: "KANAL AYARI"; Layout.fillWidth: true }
                                StateBadge { state: operatorViewModel.busy ? "Çalışıyor" : operatorViewModel.listeningReady ? "Hazır" : operatorViewModel.listeningSelectionReady ? "Hazır" : operatorViewModel.selectedDetectionReady ? "Bekliyor" : "Kullanılmıyor" }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 78
                                radius: 4
                                color: operatorViewModel.selectedDetectionReady ? root.accentSoft : root.surfaceAlt
                                border.color: operatorViewModel.selectedDetectionReady ? "#0078D4" : root.border
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
                                    Label {
                                        text: operatorViewModel.sourceMode === "hackrf"
                                              ? operatorViewModel.liveListeningBufferText
                                              : "I/Q kayıt süresi  " + operatorViewModel.sourceDurationText
                                        color: operatorViewModel.listeningSelectionReady ? root.success : root.textMuted
                                        font.pixelSize: 8
                                    }
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
                                    Label { text: "Yayın türü"; color: root.textSecondary; font.pixelSize: 10 }
                                    AppCombo {
                                        id: listeningMode
                                        objectName: "listeningMode"; helpText: "Yayının türüne göre AM veya dar bant FM seçin. Geniş bant FM radyo yayını (WFM) bu seçenek değildir."
                                        Layout.fillWidth: true
                                        model: [{text: "Genlik Modülasyonu (AM)", value: "am"}, {text: "Dar Bant FM (NFM)", value: "nfm"}]
                                        textRole: "text"
                                        Accessible.name: "Dinleme modu"
                                        onActivated: listeningBandwidth.applySuggestion()
                                    }
                                    Label { text: "Frekans düzeltmesi (kHz)"; color: root.textSecondary; font.pixelSize: 10 }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        TextField {
                                            id: listeningOffset
                                            objectName: "listeningOffset"
                                            Layout.fillWidth: true
                                            property string suggestionBasis: operatorViewModel.listeningParameterBasisText
                                            property bool operatorEdited: false
                                            text: ""
                                            color: root.textPrimary
                                            validator: DoubleValidator { decimals: 3; notation: DoubleValidator.StandardNotation }
                                            Accessible.name: "Dinleme merkez frekans ofseti kilohertz"
                                            background: Rectangle { color: "#313131"; border.color: listeningOffset.activeFocus ? root.accent : root.border; radius: 4 }
                                            function applySuggestion(operatorChoice) {
                                                text = operatorViewModel.listeningSuggestedOffsetKHz.toFixed(3)
                                                operatorEdited = operatorChoice
                                            }
                                            Component.onCompleted: applySuggestion(false)
                                            onSuggestionBasisChanged: applySuggestion(false)
                                            onTextEdited: operatorEdited = true
                                            function nudge(delta) {
                                                var value = Number(text.replace(",", "."))
                                                if (!isFinite(value) || text.length === 0) return
                                                text = (value + delta).toFixed(3)
                                                operatorEdited = true
                                            }
                                        }
                                        QuietButton {
                                            text: "Tespit Frekansını Kullan"
                                            implicitHeight: 36
                                            font.pixelSize: 10
                                            enabled: operatorViewModel.selectedDetectionReady
                                            onClicked: listeningOffset.applySuggestion(true)
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        QuietButton { text: "−0,1 kHz"; objectName: "listeningTuneDown"; Layout.fillWidth: true; onClicked: listeningOffset.nudge(-0.1) }
                                        QuietButton { text: "+0,1 kHz"; objectName: "listeningTuneUp"; Layout.fillWidth: true; onClicked: listeningOffset.nudge(0.1) }
                                    }
                                    AppCombo {
                                        id: listeningBandwidthPreset
                                        objectName: "listeningBandwidthPreset"; helpText: "Önce tespit önerisini deneyin. Sinyali kesmeyecek kadar geniş tutun; gereksiz genişlik komşu sinyalleri ve gürültüyü içeri alabilir."
                                        Layout.fillWidth: true
                                        textRole: "text"
                                        model: listeningMode.currentIndex === 0
                                            ? [{text: "Tespit önerisi", value: 0}, {text: "6 kHz", value: 6}, {text: "9 kHz", value: 9}, {text: "12 kHz", value: 12}, {text: "Özel", value: -1}]
                                            : [{text: "Tespit önerisi", value: 0}, {text: "8 kHz", value: 8}, {text: "12,5 kHz", value: 12.5}, {text: "16 kHz", value: 16}, {text: "25 kHz", value: 25}, {text: "Özel", value: -1}]
                                        onActivated: {
                                            var value = model[currentIndex].value
                                            if (value === 0) listeningBandwidth.applySuggestion()
                                            else if (value > 0) {
                                                listeningBandwidth.text = value.toFixed(1)
                                                listeningBandwidth.operatorEdited = true
                                            }
                                        }
                                    }
                                    Label { text: "Alım bant genişliği (kHz)"; color: root.textSecondary; font.pixelSize: 10 }
                                    TextField {
                                        id: listeningBandwidth
                                        objectName: "listeningBandwidth"
                                        Layout.fillWidth: true
                                        property string suggestionBasis: operatorViewModel.listeningParameterBasisText
                                        property bool operatorEdited: false
                                        text: ""
                                        color: root.textPrimary
                                        validator: DoubleValidator { bottom: 2; top: 25; decimals: 1; notation: DoubleValidator.StandardNotation }
                                        Accessible.name: "Dinleme kanal bant genişliği kilohertz"
                                        background: Rectangle { color: "#313131"; border.color: listeningBandwidth.activeFocus ? root.accent : root.border; radius: 4 }
                                        function applySuggestion() {
                                            var suggested = Math.max(2, Math.min(25, operatorViewModel.listeningSuggestedBandwidthKHz))
                                            text = suggested.toFixed(1)
                                            operatorEdited = false
                                            listeningBandwidthPreset.currentIndex = 0
                                        }
                                        Component.onCompleted: applySuggestion()
                                        onSuggestionBasisChanged: applySuggestion()
                                        onTextEdited: { operatorEdited = true; listeningBandwidthPreset.currentIndex = listeningBandwidthPreset.count - 1 }
                                    }
                                    Label {
                                        visible: listeningMode.currentIndex === 1
                                        text: "Ses profili"
                                        color: root.textSecondary
                                        font.pixelSize: 10
                                    }
                                    AppCombo {
                                        id: listeningDeemphasis
                                        objectName: "listeningDeemphasis"
                                        visible: listeningMode.currentIndex === 1
                                        helpText: "Önce Net ses profilini kullanın. Yalnız eşleşen bir telsiz profili gerekiyorsa 750 µs düzeltmeyi seçin."
                                        Layout.fillWidth: true
                                        textRole: "text"
                                        model: [
                                            {text: "Net ses", value: 0},
                                            {text: "Telsiz düzeltmesi · 750 µs", value: 750}
                                        ]
                                        currentIndex: operatorViewModel.listeningDeemphasisUs === 0 ? 0 : 1
                                        enabled: !operatorViewModel.busy
                                        onActivated: {
                                            if (!operatorViewModel.setReceiverAndAudioSettings(
                                                    operatorViewModel.receiverRFAmplifier,
                                                    model[currentIndex].value))
                                                currentIndex = operatorViewModel.listeningDeemphasisUs === 0 ? 0 : 1
                                        }
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
                                            color: "#2B2B2B"
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
                                            color: listeningVolume.pressed ? "#FFFFFF" : root.textPrimary
                                            border.color: root.accent
                                            border.width: 2
                                        }
                                    }
                                }
                            }
                            PrimaryButton {
                                Layout.fillWidth: true
                                text: operatorViewModel.listeningReady ? "Kanalı Yeniden Hazırla" : "Kanalı Hazırla"
                                enabled: operatorViewModel.listeningSelectionReady && (!operatorViewModel.busy || operatorViewModel.liveSessionActive)
                                onClicked: operatorViewModel.requestListening(
                                    listeningMode.model[listeningMode.currentIndex].value,
                                    Number(listeningOffset.text),
                                    Number(listeningBandwidth.text),
                                    listeningVolume.value
                                )
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
                                    SectionTitle { text: "SES DALGA BİÇİMİ"; Layout.fillWidth: true }
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
                                        ctx.reset(); ctx.fillStyle = "#1F1F1F"; ctx.fillRect(0, 0, width, height)
                                        ctx.strokeStyle = "#2B2B2B"; ctx.lineWidth = 1
                                        for (var gx = 0; gx <= 8; gx++) { var x = gx * width / 8; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke() }
                                        for (var gy = 0; gy <= 4; gy++) { var y = gy * height / 4; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke() }
                                        var values = operatorViewModel.listeningWaveform
                                        if (!values || values.length < 2) {
                                            ctx.fillStyle = root.textMuted; ctx.font = "11px 'Segoe UI'"; ctx.textAlign = "center"; ctx.textBaseline = "middle"
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
                                    SectionTitle { text: "SİNYAL KARARLILIĞI"; Layout.fillWidth: true }
                                    Label { text: "SEVİYE"; color: root.accent; font.pixelSize: 8; font.weight: Font.Bold }
                                    Label { text: "FREKANS"; color: root.warning; font.pixelSize: 8; font.weight: Font.Bold }
                                }
                                Canvas {
                                    id: listeningObservationCanvas
                                    objectName: "listeningObservationCanvas"
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 72
                                    Accessible.name: "Kanal gücü ve merkez frekans değişimi"
                                    Connections { target: operatorViewModel; function onListeningChanged() { listeningObservationCanvas.requestPaint() } }
                                    onPaint: {
                                        var ctx = getContext("2d")
                                        ctx.reset(); ctx.fillStyle = "#1F1F1F"; ctx.fillRect(0, 0, width, height)
                                        var points = operatorViewModel.listeningObservationPoints
                                        if (!points || points.length < 2) {
                                            ctx.fillStyle = root.textMuted; ctx.font = "10px 'Segoe UI'"; ctx.textAlign = "center"; ctx.textBaseline = "middle"
                                            ctx.fillText("Beş saniyelik kanal gözlemi yok", width / 2, height / 2)
                                            return
                                        }
                                        function drawSeries(key, color) {
                                            var low = points[0][key]
                                            var high = low
                                            for (var scan = 1; scan < points.length; scan++) {
                                                low = Math.min(low, points[scan][key]); high = Math.max(high, points[scan][key])
                                            }
                                            var span = Math.max(1e-12, high - low)
                                            ctx.strokeStyle = color; ctx.lineWidth = 1.4; ctx.beginPath()
                                            for (var index = 0; index < points.length; index++) {
                                                var px = index * width / (points.length - 1)
                                                var py = height - 5 - (points[index][key] - low) * (height - 10) / span
                                                if (index === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py)
                                            }
                                            ctx.stroke()
                                        }
                                        drawSeries("power", root.accent)
                                        drawSeries("frequency", root.warning)
                                    }
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
                                    SectionTitle { text: "SES ÇIKIŞI"; Layout.fillWidth: true }
                                    Label {
                                        text: operatorViewModel.listeningShortPreview ? "KISA ÖNİZLEME" : operatorViewModel.listeningReady ? "HAZIR" : "BEKLENİYOR"
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
                                    color: "#1F1F1F"
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
                                            color: "#2B2B2B"
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
                                GridLayout {
                                    id: listeningResultList
                                    objectName: "listeningResultList"
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    columns: root.width < 1100 ? 1 : 2
                                    columnSpacing: 18
                                    rowSpacing: 4
                                    Repeater {
                                        model: operatorViewModel.listeningRows
                                        delegate: RowLayout {
                                            required property var modelData
                                            Layout.fillWidth: true
                                            Layout.minimumWidth: 0
                                            implicitHeight: 26
                                            Label { text: modelData.label; color: root.textSecondary; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                            Label { text: modelData.value; color: root.textPrimary; font.pixelSize: 10; font.family: "Consolas"; font.weight: Font.DemiBold }
                                        }
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
                                StateBadge { state: operatorViewModel.directionCapturePending ? "Çalışıyor" : operatorViewModel.directionReady ? "Hazır" : operatorViewModel.sourceReady ? "Bekliyor" : "Kullanılmıyor" }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 66
                                radius: 4
                                color: root.surfaceAlt
                                border.color: root.border
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 3
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: "ÖLÇÜM GİRDİSİ"; color: root.textMuted; font.pixelSize: 8; font.weight: Font.Bold; Layout.fillWidth: true }
                                        Label { text: operatorViewModel.directionCapturePending ? "ÖLÇÜLÜYOR" : operatorViewModel.directionMeasurementReady ? "KANAL SEÇİLİ" : "ÖLÇÜM KAPALI"; color: operatorViewModel.directionMeasurementReady ? root.success : root.warning; font.pixelSize: 8; font.weight: Font.Bold }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: "Seçili kanal gücü"; color: root.textSecondary; font.pixelSize: 9; Layout.fillWidth: true }
                                        Label { text: operatorViewModel.directionFramePowerText; color: root.textPrimary; font.pixelSize: 10; font.family: "Consolas"; font.weight: Font.DemiBold }
                                        Rectangle { width: 1; height: 12; color: root.border }
                                        Label { text: operatorViewModel.liveSessionActive ? "Canlı alım" : "Alım durdu"; color: root.textSecondary; font.pixelSize: 9 }
                                    }
                                    Label { text: operatorViewModel.directionTargetText; color: root.textMuted; font.pixelSize: 8; elide: Text.ElideMiddle; Layout.fillWidth: true }
                                }
                            }
                            Rectangle {
                                objectName: "directionClockwiseGuide"
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                radius: 4
                                color: root.surfaceAlt
                                border.color: root.border
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 9
                                    Label { objectName: "directionCaptureReason"; text: operatorViewModel.directionCaptureText; color: root.warning; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                    Label { text: "SAAT YÖNÜNDE OTOMATİK ADIM"; color: root.textMuted; font.pixelSize: 8; font.weight: Font.Bold }
                                    Label {
                                        objectName: "directionNextAngle"
                                        text: operatorViewModel.directionNextAngleText
                                        color: operatorViewModel.directionNextAngleDeg >= 0 ? root.accent : root.success
                                        font.pixelSize: 30
                                        font.family: "Consolas"
                                        font.weight: Font.DemiBold
                                    }
                                    Label {
                                        objectName: "directionStepInstruction"
                                        text: operatorViewModel.directionStepInstructionText
                                        color: root.textPrimary
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                        Layout.fillWidth: true
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
                                        color: "#2B2B2B"
                                        Rectangle { width: parent.width * operatorViewModel.directionProgress; height: parent.height; radius: 3; color: root.accent; Behavior on width { NumberAnimation { duration: root.transitionDuration } } }
                                    }
                                    Label { text: "Her başarılı ölçümden sonra hedef açı otomatik 15° ilerler. Açı, 0° başlangıcına göre bağıl olarak kaydedilir."; color: root.textMuted; font.pixelSize: 9; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                    Item { Layout.fillHeight: true }
                                }
                            }
                            PrimaryButton {
                                Layout.fillWidth: true
                                implicitHeight: 42
                                objectName: "directionStartMeasurement"
                                text: operatorViewModel.directionCapturePending ? "Ölçüm alınıyor…"
                                      : operatorViewModel.directionNextAngleDeg < 0 ? "360° Tur Tamamlandı"
                                      : operatorViewModel.directionNextAngleText + " Ölçümünü Al"
                                enabled: operatorViewModel.directionNextAngleDeg >= 0 && operatorViewModel.directionMeasurementReady && (!operatorViewModel.busy || operatorViewModel.liveSessionActive)
                                Accessible.name: "Saat yönündeki sıradaki bağıl anten açısının kanal gücünü ölç"
                                onClicked: operatorViewModel.addNextClockwiseDirectionMeasurement()
                            }
                            QuietButton { Layout.fillWidth: true; text: "Ölçümü İptal Et"; visible: operatorViewModel.directionCaptureCancellable; onClicked: operatorViewModel.cancelDirectionMeasurement() }
                            QuietButton { Layout.fillWidth: true; text: "Ölçümleri Temizle"; enabled: (operatorViewModel.directionChannelLocked || operatorViewModel.directionPoints.length > 0) && !operatorViewModel.directionCapturePending && (!operatorViewModel.busy || operatorViewModel.liveSessionActive); onClicked: operatorViewModel.clearDirectionMeasurements() }
                            Label { text: "Anteni her ölçüm arasında saat yönünde 15° çevirerek 360° turu tamamlayın."; color: root.warning; font.pixelSize: 9; wrapMode: Text.Wrap; Layout.fillWidth: true }
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
                                        SectionTitle { text: "BAĞIL YÖN GÖSTERGESİ"; Layout.fillWidth: true }
                                        Label { text: "SAAT YÖNÜNDE"; color: bearingCompass.indicatedBearing >= 0 ? root.accent : root.textMuted; font.pixelSize: 8; font.weight: Font.Bold }
                                    }
                                    Canvas {
                                        id: bearingCompass
                                        objectName: "directionCompass"
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        property real indicatedBearing: -1
                                        Accessible.name: "Saat yönündeki bağıl geliş yönü göstergesi"
                                        onIndicatedBearingChanged: requestPaint()
                                        Behavior on indicatedBearing {
                                            NumberAnimation { duration: root.transitionDuration + 130; easing.type: Easing.OutCubic }
                                        }
                                        Connections {
                                            target: operatorViewModel
                                            function onDirectionChanged() {
                                                var relativeBearing = parseFloat(operatorViewModel.relativeArrivalText)
                                                bearingCompass.indicatedBearing = !isNaN(relativeBearing) ? relativeBearing : -1
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
                                            ctx.font = "bold 9px 'Segoe UI'"; ctx.fillStyle = root.textSecondary; ctx.textAlign = "center"; ctx.textBaseline = "middle"
                                            ctx.fillText("0°", cx, cy - radius - 11)
                                            ctx.fillText("90°", cx + radius + 13, cy)
                                            ctx.fillText("180°", cx, cy + radius + 11)
                                            ctx.fillText("270°", cx - radius - 13, cy)
                                            for (var tick = 0; tick < 24; tick++) {
                                                var angle = tick * Math.PI * 2 / 24 - Math.PI / 2
                                                var inner = radius - (tick % 6 === 0 ? 8 : 4)
                                                ctx.beginPath(); ctx.moveTo(cx + Math.cos(angle) * inner, cy + Math.sin(angle) * inner)
                                                ctx.lineTo(cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius); ctx.stroke()
                                            }
                                            var bearing = bearingCompass.indicatedBearing
                                            if (bearing >= 0) {
                                                var bearingRad = bearing * Math.PI / 180 - Math.PI / 2
                                                ctx.strokeStyle = root.accent; ctx.lineWidth = 2.5
                                                ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(bearingRad) * (radius - 8), cy + Math.sin(bearingRad) * (radius - 8)); ctx.stroke()
                                                ctx.fillStyle = root.accent; ctx.beginPath(); ctx.arc(cx, cy, 4, 0, Math.PI * 2); ctx.fill()
                                            } else {
                                                ctx.fillStyle = root.textMuted; ctx.font = "10px 'Segoe UI'"
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
                                            Label { text: "SAAT YÖNÜNDE TARAMA"; color: root.textSecondary; font.pixelSize: 9; font.weight: Font.DemiBold }
                                            Label { text: "0° başlangıcından 15° adımlarla"; color: root.textPrimary; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                                        }
                                        Label { text: operatorViewModel.directionRequirementText; color: root.accent; font.pixelSize: 10; font.family: "Consolas"; font.weight: Font.DemiBold }
                                    }
                                }
                                Panel {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    RowLayout { anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 16
                                        ColumnLayout { Layout.fillWidth: true; spacing: 4
                                            Label { text: "BAĞIL TEPE YÖNÜ"; color: root.textSecondary; font.pixelSize: 10; font.weight: Font.DemiBold }
                                            Label { text: "Antenin 0° ekseninden saat yönünde"; color: root.textMuted; font.pixelSize: 9 }
                                        }
                                        Label { text: operatorViewModel.relativeArrivalText; color: root.accent; font.pixelSize: 28; font.family: "Consolas"; font.weight: Font.DemiBold }
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
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: operatorViewModel.directionStatusText; color: operatorViewModel.directionReady ? root.success : root.warning; font.pixelSize: 11; Layout.fillWidth: true }
                                }
                                Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                                RowLayout {
                                    Layout.fillWidth: true
                                    visible: operatorViewModel.directionMeasurementCount > 0
                                    Label { text: "BAĞIL AÇI"; color: root.textSecondary; font.pixelSize: 9; Layout.preferredWidth: 86 }
                                    Label { text: "KANAL GÜCÜ"; color: root.textSecondary; font.pixelSize: 9; Layout.preferredWidth: 100 }
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
                                        width: ListView.view.width; height: 38; color: index % 2 ? "#202020" : "transparent"
                                        RowLayout { anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8
                                            Label { text: modelData.angle; color: root.textPrimary; font.pixelSize: 10; font.family: "Consolas"; Layout.preferredWidth: 78 }
                                            Label { text: modelData.power; color: root.textPrimary; font.pixelSize: 10; font.family: "Consolas"; Layout.preferredWidth: 92 }
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


       }
    }

    Component {
        id: hackrfControls
        HackRFControls { shell: root }
    }

    Window {
        id: startupIntroWindow
        objectName: "startupIntroWindow"
        transientParent: root
        screen: root.screen
        modality: Qt.ApplicationModal
        flags: Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        visibility: root.startupIntroVisible ? Window.FullScreen : Window.Hidden
        color: "#05070B"

        Loader {
            id: startupIntroLoader
            objectName: "startupIntroLoader"
            anchors.fill: parent
            active: root.startupIntroVisible
            sourceComponent: StartupIntro {
                onFinished: {
                    root.startupIntroVisible = false
                    var applicationRoot = root
                    var navigation = workspaceNavigation
                    Qt.callLater(function() {
                        applicationRoot.requestActivate()
                        var navigationIndex = applicationRoot.workspace === 0 ? applicationRoot.spectrumTaskTab : applicationRoot.workspace + 1
                        var target = navigation.itemAt(navigationIndex)
                        if (target) target.forceActiveFocus(Qt.ShortcutFocusReason)
                    })
                }
            }
        }
    }

    onClosing: function(close) { operatorViewModel.shutdown() }
}
