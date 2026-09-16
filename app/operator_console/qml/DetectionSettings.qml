import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog
    required property var theme
    property bool surveyMode: false
    objectName: surveyMode ? "surveyAdvancedSettings" : "receiverAdvancedSettings"
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(surveyMode ? 460 : 500, parent ? parent.width - 32 : 500)
    height: Math.min(surveyMode ? 230 : 330, parent ? parent.height - 32 : 330)
    modal: true
    title: surveyMode ? "Bant Taraması Ayarları" : "Ayarlar"
    header: Label {
        text: dialog.title
        font.pixelSize: 18
        font.bold: true
        color: "#EEEEEE"
        padding: 16
    }
    standardButtons: Dialog.NoButton
    footer: Item {
        implicitHeight: 52
        QuietButton {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.rightMargin: 12
            width: 120
            text: "Kapat"
            onClicked: dialog.close()
        }
    }
    palette.window: "#252525"
    palette.windowText: "#EEEEEE"
    palette.text: "#EEEEEE"
    palette.buttonText: "#EEEEEE"
    background: Rectangle { color: "#252525"; radius: 6; border.color: "#555555" }

    function sync() {
        var settings = operatorViewModel.detectionSettings
        exactNormalCoefficient = operatorViewModel.cardDetectionProfile.normal
        exactWeakCoefficient = operatorViewModel.cardDetectionProfile.weak
        normalCoefficient.text = formatCoefficient(exactNormalCoefficient)
        weakCoefficient.text = formatCoefficient(exactWeakCoefficient)
        normalCoefficientEdited = false
        weakCoefficientEdited = false
        frames.currentIndex = frames.model.indexOf(settings.survey_frames)
        guard.currentIndex = guard.model.indexOf(settings.survey_guard_frames)
        if (operatorViewModel.cardDetectionProfile.ready)
            fpgaFft.currentIndex = fpgaFft.model.indexOf(operatorViewModel.cardDetectionProfile.fftSize)
    }

    property string exactNormalCoefficient: ""
    property string exactWeakCoefficient: ""
    property bool normalCoefficientEdited: false
    property bool weakCoefficientEdited: false

    function formatCoefficient(value) {
        if (value === "")
            return ""
        return Number(value).toFixed(2).replace(".", ",")
    }

    function coefficientsValid() {
        var normal = Number(normalCoefficient.text.replace(",", "."))
        var weak = Number(weakCoefficient.text.replace(",", "."))
        return normalCoefficient.acceptableInput && weakCoefficient.acceptableInput
            && normal >= 1 && normal < 16 && weak >= 1 && weak < 4 && weak <= normal
    }

    function saveSurvey() {
        var settings = operatorViewModel.detectionSettings
        operatorViewModel.setDetectionSettings(
            settings.display_fft_size,
            settings.display_interval_frames,
            Number(frames.currentText),
            Number(guard.currentText))
        sync()
    }

    onOpened: sync()

    Connections {
        target: operatorViewModel
        function onDetectionProfileChanged() { dialog.sync() }
    }

    contentItem: ColumnLayout {
        spacing: 14

        GridLayout {
            visible: !dialog.surveyMode
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 14
            rowSpacing: 10

            Label {
                objectName: "detectionFftLabel"
                text: "FFT"
                color: dialog.theme.textSecondary
                font.pixelSize: 11
                Layout.preferredWidth: 105
                horizontalAlignment: Text.AlignRight
                verticalAlignment: Text.AlignVCenter
            }
            AppCombo {
                id: fpgaFft
                objectName: "detectionFpgaFFT"
                helpText: "4096 ile başlayın. 4096'dan 8192/16384'e geçerken yalnız Uygula yeterlidir. Daha küçük FFT'ye dönüşte uygulamayı değil kartı yeniden başlatmak gerekir."
                Layout.fillWidth: true
                model: [4096, 8192, 16384]
                enabled: !operatorViewModel.busy
                    && operatorViewModel.cardDetectionProfile.ready
                    && operatorViewModel.cardDetectionProfile.runtimeFftSupported
            }

            Label {
                objectName: "detectionNormalLabel"
                text: "Normal eşik"
                color: dialog.theme.textSecondary
                font.pixelSize: 11
                Layout.preferredWidth: 105
                horizontalAlignment: Text.AlignRight
                verticalAlignment: Text.AlignVCenter
            }
            AppField {
                id: normalCoefficient
                objectName: "detectionNormalCoefficient"
                helpText: "Varsayılan yaklaşık 8,58. Azaltmak daha çok aday ve yanlış alarm; artırmak daha az aday oluşturabilir."
                Layout.fillWidth: true
                horizontalAlignment: TextInput.AlignHCenter
                placeholderText: "1 ≤ değer < 16"
                enabled: !operatorViewModel.busy && operatorViewModel.cardDetectionProfile.ready
                validator: RegularExpressionValidator { regularExpression: /^\d{1,2}([.,]\d{1,10})?$/ }
                onTextEdited: dialog.normalCoefficientEdited = true
            }

            Label {
                objectName: "detectionWeakLabel"
                text: "Zayıf eşik"
                color: dialog.theme.textSecondary
                font.pixelSize: 11
                Layout.preferredWidth: 105
                horizontalAlignment: Text.AlignRight
                verticalAlignment: Text.AlignVCenter
            }
            AppField {
                id: weakCoefficient
                objectName: "detectionWeakCoefficient"
                helpText: "Varsayılan yaklaşık 3,98. Azaltmak zayıf adaylarla birlikte yanlış adayları da artırabilir. Normal eşikten büyük olamaz."
                Layout.fillWidth: true
                horizontalAlignment: TextInput.AlignHCenter
                placeholderText: "1 ≤ değer < 4"
                enabled: !operatorViewModel.busy && operatorViewModel.cardDetectionProfile.ready
                validator: RegularExpressionValidator { regularExpression: /^\d{1,2}([.,]\d{1,10})?$/ }
                onTextEdited: dialog.weakCoefficientEdited = true
            }
        }

        Label {
            visible: !dialog.surveyMode
                && operatorViewModel.cardDetectionProfile.message !== "Etkin tespit ayarları karttan henüz okunmadı."
            Layout.fillWidth: true
            text: operatorViewModel.cardDetectionProfile.message
            wrapMode: Text.WordWrap
            color: dialog.theme.textSecondary
            horizontalAlignment: Text.AlignHCenter
        }

        RowLayout {
            visible: !dialog.surveyMode
            Layout.fillWidth: true
            QuietButton {
                objectName: "readCardDetectionSettings"
                text: "Karttan Oku"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                enabled: !operatorViewModel.busy
                onClicked: operatorViewModel.refreshCardDetectionProfile()
            }
            QuietButton {
                objectName: "restoreCardDetectionSettings"
                text: "Varsayılana Dön"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                enabled: !operatorViewModel.busy && operatorViewModel.cardDetectionProfile.ready
                onClicked: operatorViewModel.restoreCardDetectionProfile()
            }
            PrimaryButton {
                objectName: "applyCfarSettings"
                text: "Uygula"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                enabled: !operatorViewModel.busy
                    && operatorViewModel.cardDetectionProfile.ready
                    && dialog.coefficientsValid()
                onClicked: operatorViewModel.applyCardDetectionProfileWithFFT(
                    Number(fpgaFft.currentText),
                    dialog.normalCoefficientEdited ? normalCoefficient.text : dialog.exactNormalCoefficient,
                    dialog.weakCoefficientEdited ? weakCoefficient.text : dialog.exactWeakCoefficient)
            }
        }

        GridLayout {
            visible: dialog.surveyMode
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 10
            enabled: !operatorViewModel.busy

            ColumnLayout {
                Layout.fillWidth: true
                Label {
                    objectName: "surveyFramesLabel"
                    text: "Gözlem (kare)"
                    color: dialog.theme.textSecondary
                    font.pixelSize: 11
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                }
                AppCombo {
                    id: frames
                    objectName: "detectionSurveyFrames"
                    helpText: "128 kare ile başlayın. 64 daha kısa, 256 daha uzun gözlem sağlar. Uzun gözlem kısa yayınları yakalama garantisi değildir."
                    Layout.fillWidth: true
                    model: [64, 128, 256]
                    onActivated: dialog.saveSurvey()
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Label {
                    objectName: "surveyGuardLabel"
                    text: "Yerleşme (kare)"
                    color: dialog.theme.textSecondary
                    font.pixelSize: 11
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                }
                AppCombo {
                    id: guard
                    objectName: "detectionSurveyGuard"
                    helpText: "Frekans değişiminin ardından ilk kareler tespit dışında tutulur. Varsayılan 8. Artırmak kullanılabilir gözlem süresini azaltır."
                    Layout.fillWidth: true
                    model: [8, 16, 32]
                    onActivated: dialog.saveSurvey()
                }
            }
        }

        QuietButton {
            visible: dialog.surveyMode
            objectName: "restoreSurveySettings"
            text: "Varsayılana Dön"
            Layout.fillWidth: true
            enabled: !operatorViewModel.busy
            onClicked: {
                var settings = operatorViewModel.detectionSettings
                operatorViewModel.setDetectionSettings(
                    settings.display_fft_size, settings.display_interval_frames, 128, 8)
                dialog.sync()
            }
        }

        Item { Layout.fillHeight: true }
    }
}
