import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: panel
    objectName: "measurementScroll"
    required property var viewModel
    signal detectionRequested()
    signal listeningRequested()
    readonly property bool hasResult: viewModel.parameterRows.length > 0
    readonly property bool measuring: viewModel.parameterMeasurementActive
    property bool detailsOpen: false
    property bool editRange: false
    property string lowerInputText: ""
    property string upperInputText: ""
    readonly property bool rangeInputReady: lower.text.trim().length > 0 && upper.text.trim().length > 0
    readonly property var mainKeys: ["emission_center_frequency", "occupied_bandwidth", "channel_power_dbfs", "signal_domain"]
    readonly property var mainLabels: ["Emisyon merkez frekansı", "İşgal edilen bant genişliği (OBW %99)", "Kanal gücü (dBFS)", "Sinyal türü (PC, deneysel)"]
    readonly property var primaryRows: mainKeys.map(function(key, index) {
        var row = viewModel.parameterRows.find(function(item) { return item.key === key })
        return { label: mainLabels[index], value: row ? row.value : "—", state: row ? row.state : "pending", reason: row ? (row.reason || "") : "" }
    })
    readonly property var detailRows: viewModel.parameterRows.filter(function(row) {
        return mainKeys.indexOf(row.key) < 0 && row.key !== "signal_domain"
    })
    readonly property int validPrimaryCount: primaryRows.filter(function(row) {
        return row.state === "valid"
    }).length
    function stateText(state) {
        if (state === "valid") return "GEÇERLİ"
        if (state === "uncertain") return "BELİRSİZ"
        if (state === "insufficient_quality") return "KALİTE YETERSİZ"
        if (state === "not_observed") return "GÖZLENMEDİ"
        if (state === "not_applicable") return "UYGULANMAZ"
        return "BEKLİYOR"
    }
    function stateColor(state) {
        if (state === "valid") return BazTheme.success
        if (state === "pending" || state === "not_observed") return BazTheme.textMuted
        return BazTheme.warning
    }
    function syncRangeInputs() {
        lowerInputText = viewModel.analysisLowerMHzText
        upperInputText = viewModel.analysisUpperMHzText
    }
    onHasResultChanged: { detailsOpen = hasResult; editRange = false; syncRangeInputs() }
    Component.onCompleted: syncRangeInputs()
    Connections {
        target: panel.viewModel
        function onDetectionsChanged() {
            if (!panel.editRange) panel.syncRangeInputs()
        }
    }
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
            text: panel.measuring || panel.viewModel.errorMessage.length > 0 ? panel.viewModel.statusMessage
                  : panel.hasResult ? (panel.viewModel.sourceMode === "hackrf" ? "Kayıtlı sonuç · Alım durdu" : "Kayıtlı I/Q sonucu · Tarama duraklatıldı")
                  : panel.viewModel.measurementSelectionReady ? "Analiz aralığı sinyalin tamamını kapsamalıdır."
                  : panel.viewModel.selectedDetectionId >= 0 ? "Seçili sinyalin güncel, ardışık gözlemi bekleniyor."
                  : "Tespit ekranından doğrulanmış bir sinyal seçin."
            color: BazTheme.textSecondary
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }
        Rectangle {
            objectName: "automaticParameterCatalog"
            Layout.fillWidth: true
            implicitHeight: automaticCatalogContent.implicitHeight + 20
            radius: 6
            color: BazTheme.surfaceAlt
            border.color: BazTheme.border
            ColumnLayout {
                id: automaticCatalogContent
                anchors.fill: parent
                anchors.margins: 10
                spacing: 7
                Label {
                    text: "OTOMATİK PARAMETRE KATALOĞU"
                    color: BazTheme.textPrimary
                    font.pixelSize: 12
                    font.weight: Font.Bold
                }
                Label {
                    Layout.fillWidth: true
                    text: panel.viewModel.automaticParameterStatus
                    color: BazTheme.textSecondary
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                Label {
                    Layout.fillWidth: true
                    text: panel.viewModel.parameterCatalogSummary + " · dBm yalnız tam eşleşen, süresi geçmemiş kalibrasyonla gösterilir."
                    color: BazTheme.textMuted
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                RowLayout {
                    Layout.fillWidth: true
                    QuietButton {
                        objectName: "parameterCatalogRefresh"
                        text: "Yenile"
                        onClicked: panel.viewModel.refreshParameterCatalog()
                    }
                    QuietButton {
                        objectName: "parameterCatalogExport"
                        text: "CSV Dışa Aktar"
                        onClicked: panel.viewModel.exportParameterCatalog()
                    }
                    QuietButton {
                        objectName: "parameterCatalogOpenFolder"
                        text: "Klasörü Aç"
                        onClicked: panel.viewModel.openParameterCatalogFolder()
                    }
                    Item { Layout.fillWidth: true }
                }
                Repeater {
                    model: panel.viewModel.parameterHistory.slice(0, 32)
                    delegate: ColumnLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 2
                        Rectangle { Layout.fillWidth: true; height: 1; color: BazTheme.border }
                        RowLayout {
                            Layout.fillWidth: true
                            Label {
                                text: modelData.frequency
                                color: BazTheme.textPrimary
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                                Layout.fillWidth: true
                            }
                            Label {
                                text: modelData.dbfs
                                color: modelData.dbfs === "—" ? BazTheme.textMuted : BazTheme.success
                                font.pixelSize: 12
                                font.weight: Font.Bold
                            }
                            Label {
                                text: modelData.dbm
                                color: modelData.calibrationStatus === "calibrated" ? BazTheme.success : BazTheme.warning
                                font.pixelSize: 11
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: "Kenarlar " + modelData.lowerEdge + " – " + modelData.upperEdge
                                  + " · OBW " + modelData.bandwidth + " · SNR " + modelData.snr
                                  + " · " + modelData.receiver + " · " + modelData.status
                                  + (modelData.reason.length ? " · " + modelData.reason : "")
                            color: BazTheme.textSecondary
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
        ColumnLayout {
            visible: !panel.hasResult && !panel.measuring && panel.viewModel.measurementSelectionReady
            Layout.fillWidth: true
            spacing: 8
            Label {
                Layout.fillWidth: true
                text: panel.viewModel.analysisLowerMHzText.length > 0
                      ? "Analiz aralığı: " + panel.viewModel.analysisLowerMHzText + " – " + panel.viewModel.analysisUpperMHzText + " MHz"
                      : "Otomatik aralık oluşturulamadı. Alt ve üst frekansı elle girin."
                color: BazTheme.textPrimary
                font.pixelSize: 12
                wrapMode: Text.Wrap
            }
            Label {
                visible: panel.viewModel.analysisSpanLimited
                Layout.fillWidth: true
                text: "Aralık seçili sinyalin tamamını kapsamıyor. Ölçümden önce aralığı genişletin."
                color: BazTheme.warning
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
            QuietButton {
                objectName: "parameterEditRange"
                text: panel.editRange ? "Aralık Düzenlemeyi Kapat" : "Aralığı Düzenle"
                onClicked: {
                    if (!panel.editRange) panel.syncRangeInputs()
                    panel.editRange = !panel.editRange
                }
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
                        text: panel.lowerInputText
                        onTextEdited: panel.lowerInputText = text
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
                        text: panel.upperInputText
                        onTextEdited: panel.upperInputText = text
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
                visible: panel.editRange || (!panel.viewModel.analysisSpanConfirmed && panel.rangeInputReady)
                text: panel.viewModel.sourceMode === "hackrf"
                      ? "Aralığı Onayla ve Parametreleri Çıkar"
                      : "Analiz Aralığını Onayla"
                Layout.fillWidth: true
                enabled: panel.viewModel.parameterCapabilityReady && panel.rangeInputReady
                onClicked: {
                    panel.viewModel.confirmAnalysisSpan(Number(lower.text.trim().replace(",", ".")), Number(upper.text.trim().replace(",", ".")))
                    if (panel.viewModel.analysisSpanConfirmed) {
                        panel.editRange = false
                        panel.syncRangeInputs()
                        if (panel.viewModel.sourceMode === "hackrf")
                            panel.viewModel.requestMeasurement()
                    }
                }
            }
            Label {
                visible: panel.viewModel.statusMessage.length > 0
                Layout.fillWidth: true
                text: panel.viewModel.statusMessage
                color: BazTheme.textSecondary
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
            PrimaryButton {
                objectName: "parameterMeasure"
                visible: panel.viewModel.analysisSpanConfirmed && !panel.editRange
                text: panel.viewModel.liveSessionActive ? "Alımı Durdur ve Parametreleri Çıkar" : "Parametreleri Çıkar"
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
        Rectangle {
            objectName: "parameterValidationSummary"
            visible: panel.hasResult
            Layout.fillWidth: true
            implicitHeight: validationSummary.implicitHeight + 20
            radius: 4
            color: BazTheme.surfaceAlt
            border.color: panel.validPrimaryCount === panel.mainKeys.length ? BazTheme.success : BazTheme.warning
            ColumnLayout {
                id: validationSummary
                anchors.fill: parent
                anchors.margins: 10
                spacing: 3
                Label {
                    text: "DOĞRULAMA ÖZETİ · " + panel.validPrimaryCount + "/" + panel.mainKeys.length + " ANA ALAN GEÇERLİ"
                    color: panel.validPrimaryCount === panel.mainKeys.length ? BazTheme.success : BazTheme.warning
                    font.pixelSize: 11
                    font.weight: Font.Bold
                }
                Label {
                    Layout.fillWidth: true
                    text: "Alan geçerliliği kart/profil kalite kapılarını gösterir; fiziksel doğruluk kabulü değildir."
                    color: BazTheme.textSecondary
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }
        }
        Repeater {
            model: panel.primaryRows
            delegate: ColumnLayout {
                required property var modelData
                Layout.fillWidth: true
                spacing: 4
                Rectangle { Layout.fillWidth: true; height: 1; color: BazTheme.border }
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: modelData.label; color: BazTheme.textSecondary; font.pixelSize: 12; Layout.fillWidth: true }
                    Label {
                        text: panel.stateText(modelData.state)
                        color: panel.stateColor(modelData.state)
                        font.pixelSize: 9
                        font.weight: Font.Bold
                    }
                }
                Label {
                    text: modelData.value
                    Layout.fillWidth: true
                    color: modelData.state === "valid" ? BazTheme.textPrimary : BazTheme.textMuted
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    wrapMode: Text.Wrap
                }
                Label {
                    visible: modelData.state !== "valid" && modelData.reason.length > 0
                    text: modelData.reason
                    Layout.fillWidth: true
                    color: BazTheme.warning
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
            }
        }
        Label {
            Layout.fillWidth: true
            text: "OBW için analiz aralığı sinyalin tamamını kapsamalıdır. Analog/Sayısal sonucu PC'de otomatik hesaplanır; güven yetersizse Belirsiz gösterilir."
            color: BazTheme.textMuted
            font.pixelSize: 11
            wrapMode: Text.WordWrap
        }
        QuietButton {
            objectName: "parameterDetailsToggle"
            visible: panel.hasResult
            text: panel.detailsOpen ? "Teknik Doğrulamayı Gizle" : "Teknik Doğrulamayı Göster"
            onClicked: panel.detailsOpen = !panel.detailsOpen
        }
        ColumnLayout {
            objectName: "parameterDetails"
            visible: panel.hasResult && panel.detailsOpen
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: panel.detailRows
                delegate: ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 2
                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            text: modelData.label + ": " + modelData.value
                            Layout.fillWidth: true
                            color: BazTheme.textSecondary
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }
                        Label {
                            text: panel.stateText(modelData.state)
                            color: panel.stateColor(modelData.state)
                            font.pixelSize: 8
                            font.weight: Font.Bold
                        }
                    }
                    Label {
                        visible: modelData.reason.length > 0
                        text: modelData.reason
                        Layout.fillWidth: true
                        color: BazTheme.warning
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
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
            objectName: "parameterContinueListening"
            visible: panel.hasResult
            text: panel.viewModel.sourceMode === "hackrf" ? "Dinleme İçin Yeniden Al" : "Dinlemeye Geç"
            Layout.fillWidth: true
            enabled: !panel.viewModel.busy
            onClicked: if (panel.viewModel.continueToListening()) panel.listeningRequested()
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
