import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: panel
    objectName: "measurementScroll"
    required property var viewModel
    signal detectionRequested()
    readonly property bool hasResult: viewModel.parameterRows.length > 0
    readonly property bool measuring: viewModel.parameterMeasurementActive
    property bool detailsOpen: false
    property bool editRange: false
    readonly property var mainKeys: ["carrier_line_frequency", "occupied_bandwidth", "channel_power_dbfs", "signal_domain"]
    readonly property var mainLabels: ["Taşıyıcı frekansı", "Bant genişliği · OBW %99", "Güç seviyesi · kalibrasyonsuz", "Analog / Sayısal"]
    readonly property var primaryRows: mainKeys.map(function(key, index) {
        var row = viewModel.parameterRows.find(function(item) { return item.key === key })
        return { label: mainLabels[index], value: row ? row.value : "—", state: row ? row.state : "pending" }
    })
    readonly property var detailRows: viewModel.parameterRows.filter(function(row) { return mainKeys.indexOf(row.key) < 0 })
    onHasResultChanged: { detailsOpen = false; editRange = false }
    clip: true
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical: ScrollBar {
        x: panel.width - width
        y: 0
        width: 6
        height: panel.height
        orientation: Qt.Vertical
        policy: ScrollBar.AsNeeded
        contentItem: Rectangle {
            implicitWidth: 4
            radius: 2
            color: BazTheme.textMuted
            opacity: parent.active || parent.pressed ? 0.8 : 0.4
        }
        background: Item {}
    }

    ColumnLayout {
        width: panel.availableWidth
        spacing: 10
        Label {
            Layout.fillWidth: true
            text: panel.measuring ? "Alım durduruluyor ve seçili gözlem ölçülüyor…"
                  : panel.hasResult ? (panel.viewModel.sourceMode === "hackrf" ? "Kayıtlı sonuç · Alım durdu" : "Kayıtlı I/Q sonucu · Tarama duraklatıldı")
                  : panel.viewModel.measurementSelectionReady ? "Önerilen aralıkta yalnız seçtiğiniz sinyal bulunduğunu kontrol edin."
                  : panel.viewModel.selectedDetectionId >= 0 ? "Seçili sinyalin güncel, ardışık gözlemi bekleniyor."
                  : "Tespit ekranından doğrulanmış bir sinyal seçin."
            color: BazTheme.textSecondary
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }
        ColumnLayout {
            visible: !panel.hasResult && !panel.measuring && panel.viewModel.measurementSelectionReady
            Layout.fillWidth: true
            spacing: 8
            Label {
                Layout.fillWidth: true
                text: "Analiz aralığı: " + panel.viewModel.analysisLowerMHzText + " – " + panel.viewModel.analysisUpperMHzText + " MHz"
                color: BazTheme.textPrimary
                font.pixelSize: 12
                wrapMode: Text.Wrap
            }
            QuietButton {
                text: panel.editRange ? "Aralık Düzenlemeyi Kapat" : "Aralığı Düzenle"
                onClicked: panel.editRange = !panel.editRange
            }
            RowLayout {
                visible: panel.editRange
                Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true
                    Label { text: "Alt frekans (MHz)"; color: BazTheme.textSecondary; font.pixelSize: 11 }
                    TextField {
                        id: lower
                        objectName: "parameterLowerMHz"
                        Layout.fillWidth: true
                        text: panel.viewModel.analysisLowerMHzText
                        Accessible.name: "Analiz alt frekansı megahertz"
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Label { text: "Üst frekans (MHz)"; color: BazTheme.textSecondary; font.pixelSize: 11 }
                    TextField {
                        id: upper
                        objectName: "parameterUpperMHz"
                        Layout.fillWidth: true
                        text: panel.viewModel.analysisUpperMHzText
                        Accessible.name: "Analiz üst frekansı megahertz"
                    }
                }
            }
            Label {
                visible: panel.editRange
                text: "Spektrumda Shift+sürükle ile de aralık çizebilirsiniz."
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: BazTheme.textSecondary
                font.pixelSize: 11
            }
            PrimaryButton {
                objectName: "parameterConfirmRange"
                visible: !panel.viewModel.analysisSpanConfirmed || panel.editRange
                text: "Analiz Aralığını Onayla"
                Layout.fillWidth: true
                enabled: panel.viewModel.parameterCapabilityReady
                onClicked: {
                    panel.viewModel.confirmAnalysisSpan(Number(lower.text.trim().replace(",", ".")), Number(upper.text.trim().replace(",", ".")))
                    if (panel.viewModel.analysisSpanConfirmed) panel.editRange = false
                }
            }
            PrimaryButton {
                objectName: "parameterMeasure"
                visible: panel.viewModel.analysisSpanConfirmed && !panel.editRange
                text: panel.viewModel.liveSessionActive ? "Alımı Durdur ve Ölç" : "Seçili Kaydı Ölç"
                Layout.fillWidth: true
                enabled: panel.viewModel.measurementReady && (!panel.viewModel.busy || panel.viewModel.liveSessionActive)
                onClicked: panel.viewModel.requestMeasurement()
            }
        }
        QuietButton {
            objectName: "parameterCancel"
            visible: panel.measuring
            text: "Ölçümü İptal Et"
            Layout.fillWidth: true
            onClicked: panel.viewModel.cancelParameterMeasurement()
        }
        Repeater {
            model: panel.primaryRows
            delegate: ColumnLayout {
                required property var modelData
                Layout.fillWidth: true
                spacing: 4
                Rectangle { Layout.fillWidth: true; height: 1; color: BazTheme.border }
                Label { text: modelData.label; color: BazTheme.textSecondary; font.pixelSize: 12 }
                Label {
                    text: modelData.value
                    Layout.fillWidth: true
                    color: modelData.state === "valid" ? BazTheme.textPrimary : BazTheme.textMuted
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    wrapMode: Text.Wrap
                }
            }
        }
        Label {
            Layout.fillWidth: true
            text: "Güç dBFS referansındadır. Taşıyıcı çizgisi ve emisyon merkezi ayrı ölçümlerdir; yeterli kanıt yoksa karar belirsiz kalır."
            color: BazTheme.textMuted
            font.pixelSize: 11
            wrapMode: Text.WordWrap
        }
        QuietButton {
            objectName: "parameterDetailsToggle"
            visible: panel.hasResult
            text: panel.detailsOpen ? "Ölçüm Ayrıntılarını Gizle" : "Ölçüm Ayrıntıları"
            onClicked: panel.detailsOpen = !panel.detailsOpen
        }
        ColumnLayout {
            objectName: "parameterDetails"
            visible: panel.hasResult && panel.detailsOpen
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: panel.detailRows
                delegate: Label {
                    required property var modelData
                    text: modelData.label + ": " + modelData.value
                    Layout.fillWidth: true
                    color: BazTheme.textSecondary
                    font.pixelSize: 11
                    wrapMode: Text.Wrap
                }
            }
            Label {
                text: "Gözlem süresi: " + Number(panel.viewModel.measurementInfo.durationMs || 0).toFixed(3) + " ms · 4 kare\n"
                      + "Hesaplama bitişi (UTC): " + (panel.viewModel.measurementInfo.completedUtc || "Bilinmiyor")
                Layout.fillWidth: true
                color: BazTheme.textSecondary
                font.pixelSize: 11
                wrapMode: Text.Wrap
            }
            Label {
                text: "Ölçüm kaydı: " + panel.viewModel.measurementRecordPath
                Layout.fillWidth: true
                color: BazTheme.textMuted
                font.pixelSize: 10
                wrapMode: Text.WrapAnywhere
            }
        }
        PrimaryButton {
            objectName: "parameterReacquire"
            visible: !panel.measuring && !panel.viewModel.liveSessionActive && (panel.hasResult || (panel.viewModel.sourceMode === "hackrf" && panel.viewModel.selectedDetectionId >= 0))
            text: panel.viewModel.sourceMode === "hackrf" ? "Yeni Ölçüm İçin Alımı Başlat" : "Yeni Gözlem İçin Taramaya Dön"
            Layout.fillWidth: true
            enabled: !panel.viewModel.busy
            onClicked: if (panel.viewModel.restartParameterAcquisition()) panel.detectionRequested()
        }
    }
}
