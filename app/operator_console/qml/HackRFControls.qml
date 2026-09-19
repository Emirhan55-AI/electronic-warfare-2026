import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    required property var shell
    width: parent ? parent.width : 240
    spacing: 7
    DetectionSettings { id: detectionSettings; theme: shell }
    QuietButton { objectName: "bandSurveyButton"; Layout.fillWidth: true; text: "Bant Taraması ›"; enabled: !operatorViewModel.busy; onClicked: shell.rfSearchMode = true }
    QuietButton { objectName: "systemCheckButton"; visible: !operatorViewModel.hackrfReady; Layout.fillWidth: true; text: "Sistemi Denetle"; enabled: !operatorViewModel.busy; onClicked: operatorViewModel.probeHackrf() }
    Label { text: "Merkez frekansı (MHz)"; color: shell.textSecondary; font.pixelSize: 11; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
    AppField {
        font.pixelSize: 13
        font.family: "Consolas"
        horizontalAlignment: TextInput.AlignHCenter
        verticalAlignment: TextInput.AlignVCenter
        id: centerInput
        objectName: "liveCenterInput"
        Layout.fillWidth: true
        text: String(operatorViewModel.liveReceiveSettings.center_hz / 1000000)
        readonly property real frequencyHz: Math.round(Number(text.trim().replace(",", ".")) * 1000000)
        readonly property bool frequencyValid: /^[0-9]+([.,][0-9]{1,6})?$/.test(text.trim()) && frequencyHz >= 1000000 && frequencyHz <= 6000000000
        readonly property bool numericCentered: horizontalAlignment === TextInput.AlignHCenter
        enabled: !operatorViewModel.busy
        inputMethodHints: Qt.ImhFormattedNumbersOnly
        placeholderText: "Örn. 933 veya 104,65"
        Accessible.name: "İzleme merkez frekansı, MHz"
    }
    Label { visible: !centerInput.frequencyValid; text: "1–6000 MHz arasında bir değer girin."; color: shell.textSecondary; font.pixelSize: 11; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
    Connections {
        target: operatorViewModel
        function onLiveReceiveSettingsChanged() {
            centerInput.text = String(operatorViewModel.liveReceiveSettings.center_hz / 1000000)
            lnaInput.currentIndex = lnaInput.model.indexOf(operatorViewModel.liveReceiveSettings.lna_db)
            vgaInput.currentIndex = vgaInput.model.indexOf(operatorViewModel.liveReceiveSettings.vga_db)
        }
    }
    RowLayout {
        Layout.fillWidth: true
        ColumnLayout {
            Layout.fillWidth: true
            Label { text: "LNA (dB)"; color: shell.textSecondary; font.pixelSize: 11; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
            AppCombo { id: lnaInput; objectName: "liveLnaInput"; helpText: "16 dB başlangıç olabilir. 8 dB adımlarla deneyin; kırpılma veya yeni sahte tepeler oluşursa azaltın. Harici LNA varsa daha düşük kazanç gerekebilir."; Layout.fillWidth: true; model: [0,8,16,24,32,40]; currentIndex: model.indexOf(operatorViewModel.liveReceiveSettings.lna_db); enabled: !operatorViewModel.busy }
        }
        ColumnLayout {
            Layout.fillWidth: true
            Label { text: "VGA (dB)"; color: shell.textSecondary; font.pixelSize: 11; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
            AppCombo { id: vgaInput; objectName: "liveVgaInput"; helpText: "16 dB başlangıç olabilir. 2 dB adımlarla ince ayar yapın. En yüksek değer en iyi alım demek değildir."; Layout.fillWidth: true; model: [0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,54,56,58,60,62]; currentIndex: model.indexOf(operatorViewModel.liveReceiveSettings.vga_db); enabled: !operatorViewModel.busy }
        }
    }
    ColumnLayout {
        Layout.fillWidth: true
        Label { objectName: "liveAmplifierLabel"; text: "AMP"; color: shell.textSecondary; font.pixelSize: 11; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
        QuietButton {
            id: amplifierInput
            objectName: "liveAmplifierInput"
            helpText: "Kapalı başlayın. Çok zayıf sinyalde Açık ile karşılaştırın; kırpılma veya bozulma artarsa kapatın."
            Layout.fillWidth: true
            leftPadding: 28
            rightPadding: 28
            text: operatorViewModel.receiverRFAmplifier ? "Açık" : "Kapalı"
            checked: operatorViewModel.receiverRFAmplifier
            enabled: !operatorViewModel.busy
            Accessible.role: Accessible.CheckBox
            Accessible.checked: operatorViewModel.receiverRFAmplifier
            Accessible.name: "RF yükselteci " + (operatorViewModel.receiverRFAmplifier ? "açık" : "kapalı")
            onClicked: operatorViewModel.toggleReceiverRFAmplifier()
        }
    }
    Item {
        id: liveSessionActionSlot
        objectName: "liveSessionActionSlot"
        Layout.fillWidth: true
        Layout.preferredHeight: 40
        PrimaryButton {
            objectName: "liveStartButton"
            anchors.fill: parent
            text: "Taramayı Başlat"
            visible: !operatorViewModel.liveSessionActive
            enabled: operatorViewModel.hackrfReady && !operatorViewModel.busy && centerInput.frequencyValid
            onClicked: {
                shell.clearSpectrumViewHistory()
                operatorViewModel.startLiveEDSession(centerInput.frequencyHz, Number(lnaInput.currentText), Number(vgaInput.currentText), shell.liveSessionFrameLimit)
            }
        }
        QuietButton {
            objectName: "liveStopButton"
            anchors.fill: parent
            text: "Taramayı Durdur"
            visible: operatorViewModel.liveSessionActive
            enabled: operatorViewModel.liveSessionActive
            onClicked: operatorViewModel.stopLiveEDSession()
        }
    }
    QuietButton { objectName: "liveDetectionSettingsButton"; Layout.fillWidth: true; text: "Ayarlar"; onClicked: detectionSettings.open() }
    QuietButton {
        Layout.fillWidth: true
        text: "Yalnız RX Önizleme"
        visible: false
        enabled: operatorViewModel.hackrfReady && !operatorViewModel.busy && centerInput.frequencyValid
        ToolTip.visible: hovered
        ToolTip.text: "Kart bağlantısı olmadan gerçek alımı gösterir; FPGA tespiti üretmez."
        onClicked: operatorViewModel.startRXPreview(centerInput.frequencyHz, Number(lnaInput.currentText), Number(vgaInput.currentText), shell.liveSessionFrameLimit)
    }
}
