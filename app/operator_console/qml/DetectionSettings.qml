import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog
    required property var theme
    property bool surveyMode: false
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(540, parent ? parent.width - 32 : 540)
    height: Math.min(surveyMode ? 280 : 620, parent ? parent.height - 32 : 620)
    modal: true
    title: surveyMode ? "Bant taraması ayarları" : "Sinyal tespiti ayarları"
    header: Label { text: dialog.title; font.pixelSize: 18; font.bold: true; color: "#EEEEEE"; padding: 16 }
    standardButtons: Dialog.NoButton
    footer: Item {
        implicitHeight: 52
        QuietButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.rightMargin: 12; width: 120; text: "Kapat"; onClicked: dialog.close() }
    }
    palette.window: "#252525"
    palette.windowText: "#EEEEEE"
    palette.text: "#EEEEEE"
    palette.buttonText: "#EEEEEE"
    background: Rectangle { color: "#252525"; radius: 6; border.color: "#555555" }

    function sync() {
        var settings = operatorViewModel.detectionSettings
        fft.currentIndex = fft.model.indexOf(settings.display_fft_size)
        interval.currentIndex = interval.model.indexOf(settings.display_interval_frames)
        frames.currentIndex = frames.model.indexOf(settings.survey_frames)
        guard.currentIndex = guard.model.indexOf(settings.survey_guard_frames)
        if (operatorViewModel.cardDetectionProfile.ready)
            fpgaFft.currentIndex = fpgaFft.model.indexOf(operatorViewModel.cardDetectionProfile.fftSize)
    }
    function save() {
        operatorViewModel.setDetectionSettings(Number(fft.currentText), Number(interval.currentText), Number(frames.currentText), Number(guard.currentText))
        sync()
    }
    onOpened: sync()
    Connections {
        target: operatorViewModel
        function onDetectionProfileChanged() {
            normalCoefficient.text = operatorViewModel.cardDetectionProfile.normal
            weakCoefficient.text = operatorViewModel.cardDetectionProfile.weak
            fpgaFft.currentIndex = fpgaFft.model.indexOf(operatorViewModel.cardDetectionProfile.fftSize)
        }
    }
    contentItem: ScrollView {
      id: settingsScroll
      clip: true
      contentWidth: availableWidth
      ColumnLayout {
        width: settingsScroll.availableWidth
        spacing: 12
        ColumnLayout {
            visible: !dialog.surveyMode
            Layout.fillWidth: true
            Label { text: "Sinyal tespiti (FPGA)"; color: dialog.theme.textPrimary; font.bold: true }
            Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; visible: operatorViewModel.cardDetectionProfile.message !== "Etkin tespit ayarları karttan henüz okunmadı."; text: operatorViewModel.cardDetectionProfile.message; color: dialog.theme.textSecondary }
            RowLayout {
                enabled: !operatorViewModel.busy && operatorViewModel.cardDetectionProfile.ready
                         && operatorViewModel.cardDetectionProfile.runtimeFftSupported
                Label { text: "FFT boyutu"; color: dialog.theme.textPrimary }
                AppCombo { id: fpgaFft; objectName: "detectionFpgaFFT"; Layout.fillWidth: true; model: [4096,8192,16384] }
            }
            GridLayout {
                columns: 2
                Layout.fillWidth: true
                enabled: !operatorViewModel.busy && operatorViewModel.cardDetectionProfile.ready
                Label { text: "Normal eşik katsayısı"; color: dialog.theme.textPrimary }
                AppField { id: normalCoefficient; objectName: "detectionNormalCoefficient"; Layout.fillWidth: true; placeholderText: "Katsayı" }
                Label { text: "Zayıf eşik katsayısı"; color: dialog.theme.textPrimary }
                AppField { id: weakCoefficient; objectName: "detectionWeakCoefficient"; Layout.fillWidth: true; placeholderText: "Katsayı" }
            }
            RowLayout {
                enabled: !operatorViewModel.busy
                QuietButton { text: "Karttan oku"; onClicked: operatorViewModel.refreshCardDetectionProfile() }
                QuietButton { text: "Uygula"; enabled: operatorViewModel.cardDetectionProfile.ready; onClicked: operatorViewModel.applyCardDetectionProfileWithFFT(Number(fpgaFft.currentText), normalCoefficient.text, weakCoefficient.text) }
                QuietButton { text: "Varsayılan profil"; enabled: operatorViewModel.cardDetectionProfile.ready; onClicked: operatorViewModel.restoreCardDetectionProfile() }
            }
        }
        Rectangle { visible: !dialog.surveyMode; Layout.fillWidth: true; height: 1; color: "#555555" }
        Label { visible: !dialog.surveyMode; text: "Spektrum ve spektrogram"; color: dialog.theme.textPrimary; font.bold: true }
        GridLayout {
            columns: 2
            Layout.fillWidth: true
            enabled: !operatorViewModel.busy
            Label { visible: !dialog.surveyMode; text: "Spektrum FFT boyutu"; color: dialog.theme.textPrimary }
            AppCombo { id: fft; objectName: "detectionDisplayFFT"; visible: !dialog.surveyMode; Layout.fillWidth: true; model: [4096,8192,16384]; onActivated: dialog.save() }
            Label { visible: !dialog.surveyMode; text: "Yenileme aralığı (kare)"; color: dialog.theme.textPrimary }
            AppCombo { id: interval; objectName: "detectionDisplayInterval"; visible: !dialog.surveyMode; Layout.fillWidth: true; model: [8,15,32,64]; onActivated: dialog.save() }
            Label { visible: dialog.surveyMode; text: "Gözlem uzunluğu (kare)"; color: dialog.theme.textPrimary }
            AppCombo { id: frames; objectName: "detectionSurveyFrames"; visible: dialog.surveyMode; Layout.fillWidth: true; model: [64,128,256,512]; onActivated: dialog.save() }
            Label { visible: dialog.surveyMode; text: "Yerleşme süresi (kare)"; color: dialog.theme.textPrimary }
            AppCombo { id: guard; objectName: "detectionSurveyGuard"; visible: dialog.surveyMode; Layout.fillWidth: true; model: [8,16,32]; onActivated: dialog.save() }
        }
        ColumnLayout {
            visible: !dialog.surveyMode
            Layout.fillWidth: true
            RowLayout {
                Label { text: "Alt seviye (dBFS)"; color: dialog.theme.textSecondary }
                AppField { Layout.preferredWidth: 65; text: String(Math.round(operatorViewModel.spectralDisplay.floorDb)); horizontalAlignment: TextInput.AlignHCenter; validator: IntValidator { bottom: -200; top: 0 } onEditingFinished: if (acceptableInput) operatorViewModel.spectralDisplay.setLevels(Number(text), operatorViewModel.spectralDisplay.spanDb) }
                Label { text: "Seviye aralığı (dB)"; color: dialog.theme.textSecondary }
                AppField { Layout.preferredWidth: 65; text: String(Math.round(operatorViewModel.spectralDisplay.spanDb)); horizontalAlignment: TextInput.AlignHCenter; validator: IntValidator { bottom: 20; top: 120 } onEditingFinished: if (acceptableInput) operatorViewModel.spectralDisplay.setLevels(operatorViewModel.spectralDisplay.floorDb, Number(text)) }
            }
            RowLayout {
                CheckBox {
                    id: peakHold
                    text: "Tepeyi tut"; checked: operatorViewModel.spectralDisplay.peakHold
                    onToggled: operatorViewModel.spectralDisplay.setPeakHold(checked)
                    implicitHeight: 32
                    indicator: Rectangle {
                        x: 0; y: (parent.height - height) / 2; width: 16; height: 16; radius: 3
                        color: peakHold.checked ? "#0078D4" : "#313131"; border.color: "#868686"
                        Rectangle { anchors.centerIn: parent; width: 8; height: 8; color: "white"; visible: peakHold.checked }
                    }
                    contentItem: Text { text: peakHold.text; leftPadding: 23; color: dialog.theme.textPrimary; verticalAlignment: Text.AlignVCenter }
                }
                QuietButton { text: "Otomatik ölçek"; onClicked: operatorViewModel.spectralDisplay.fitLevels() }
            }
        }
        QuietButton {
            text: dialog.surveyMode ? "Tarama varsayılanları" : "Görünüm varsayılanları"
            enabled: !operatorViewModel.busy
            onClicked: { operatorViewModel.setDetectionSettings(16384, 15, 128, 8); dialog.sync() }
        }
      }
    }
}
