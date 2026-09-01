import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    required property var shell
    width: parent ? parent.width : 240
    spacing: 7
    QuietButton { Layout.fillWidth: true; text: "Bant Taraması ›"; enabled: !operatorViewModel.busy; onClicked: shell.rfSearchMode = true }
    QuietButton { Layout.fillWidth: true; text: operatorViewModel.hackrfReady ? "Alıcı bağlı" : "Alıcıyı Denetle"; enabled: !operatorViewModel.busy; onClicked: operatorViewModel.probeHackrf() }
    Label { text: "Merkez frekansı (Hz)"; color: shell.textSecondary; font.pixelSize: 10 }
    AppField { id: centerInput; objectName: "liveCenterInput"; Layout.fillWidth: true; text: String(operatorViewModel.liveReceiveSettings.center_hz); enabled: !operatorViewModel.busy; inputMethodHints: Qt.ImhDigitsOnly; Accessible.name: "İzleme merkez frekansı" }
    Connections {
        target: operatorViewModel
        function onLiveReceiveSettingsChanged() {
            centerInput.text = String(operatorViewModel.liveReceiveSettings.center_hz)
            lnaInput.currentIndex = lnaInput.model.indexOf(operatorViewModel.liveReceiveSettings.lna_db)
            vgaInput.currentIndex = vgaInput.model.indexOf(operatorViewModel.liveReceiveSettings.vga_db)
        }
    }
    Label { text: "Sabit frekansta canlı alım ve FPGA tespiti"; color: shell.textSecondary; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true }
    RowLayout {
        Layout.fillWidth: true
        ColumnLayout {
            Layout.fillWidth: true
            Label { text: "LNA (dB)"; color: shell.textSecondary; font.pixelSize: 10 }
            AppCombo { id: lnaInput; objectName: "liveLnaInput"; Layout.fillWidth: true; model: [0,8,16,24,32,40]; currentIndex: model.indexOf(operatorViewModel.liveReceiveSettings.lna_db); enabled: !operatorViewModel.busy }
        }
        ColumnLayout {
            Layout.fillWidth: true
            Label { text: "VGA (dB)"; color: shell.textSecondary; font.pixelSize: 10 }
            AppCombo { id: vgaInput; objectName: "liveVgaInput"; Layout.fillWidth: true; model: [0,8,16,24,32,40,48,56]; currentIndex: model.indexOf(operatorViewModel.liveReceiveSettings.vga_db); enabled: !operatorViewModel.busy }
        }
    }
    PrimaryButton {
        Layout.fillWidth: true
        text: "Taramayı Başlat"
        visible: !operatorViewModel.liveSessionActive
        enabled: operatorViewModel.hackrfReady && !operatorViewModel.busy
        onClicked: operatorViewModel.startLiveEDSession(Number(centerInput.text), Number(lnaInput.currentText), Number(vgaInput.currentText), shell.liveSessionFrameLimit)
    }
    QuietButton {
        Layout.fillWidth: true
        text: "Yalnız RX Önizleme"
        visible: false
        enabled: operatorViewModel.hackrfReady && !operatorViewModel.busy
        ToolTip.visible: hovered
        ToolTip.text: "Kart bağlantısı olmadan gerçek alımı gösterir; FPGA tespiti üretmez."
        onClicked: operatorViewModel.startRXPreview(Number(centerInput.text), Number(lnaInput.currentText), Number(vgaInput.currentText), shell.liveSessionFrameLimit)
    }
    QuietButton {
        Layout.fillWidth: true
        text: "Taramayı Durdur"
        visible: operatorViewModel.liveSessionActive
        enabled: operatorViewModel.liveSessionActive
        onClicked: operatorViewModel.stopLiveEDSession()
    }
}
