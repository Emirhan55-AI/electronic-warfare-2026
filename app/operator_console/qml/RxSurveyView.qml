import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Teknofest.Display 1.0

Item {
    id: view
    required property var theme
    readonly property var survey: operatorViewModel.survey
    signal fixedBandRequested()

    component Caption: Label {
        color: view.theme.textSecondary
        font.pixelSize: 11
    }
    component Action: Button {
        id: action
        implicitHeight: 36
        padding: 10
        contentItem: Text {
            text: action.text
            color: action.enabled ? view.theme.textPrimary : view.theme.textMuted
            font.pixelSize: 11
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 4
            color: action.hovered ? view.theme.accentSoft : view.theme.surfaceAlt
            border.color: action.activeFocus ? view.theme.accent : view.theme.border
        }
    }
    component Card: Rectangle {
        color: view.theme.surface
        border.color: view.theme.border
        radius: 6
    }
    component FrequencyField: TextField {
        id: field
        color: view.theme.textPrimary
        font.family: "Consolas"
        font.pixelSize: 13
        implicitHeight: 34
        padding: 8
        background: Rectangle { radius: 4; color: "#071019"; border.color: field.activeFocus ? view.theme.accent : view.theme.border }
    }
    component GainChoice: ComboBox {
        id: gain
        implicitHeight: 34
        contentItem: Text { text: gain.displayText; color: gain.enabled ? view.theme.textPrimary : view.theme.textMuted; leftPadding: 8; verticalAlignment: Text.AlignVCenter; font.pixelSize: 12 }
        indicator: Text { text: "⌄"; color: view.theme.textSecondary; x: gain.width - width - 8; y: 7 }
        background: Rectangle { radius: 4; color: "#071019"; border.color: gain.activeFocus ? view.theme.accent : view.theme.border }
        delegate: ItemDelegate {
            required property var modelData
            width: gain.width
            text: String(modelData)
            contentItem: Text { text: parent.text; color: view.theme.textPrimary; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter }
            background: Rectangle { color: parent.hovered ? view.theme.accentSoft : view.theme.surfaceAlt }
        }
        popup.background: Rectangle { color: view.theme.surfaceAlt; border.color: view.theme.border; radius: 4 }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10
        Card {
            Layout.fillWidth: true
            implicitHeight: controls.implicitHeight + 28
            ColumnLayout {
                id: controls
                anchors.fill: parent
                anchors.margins: 14
                spacing: 12
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "BANT TARAMASI"; color: view.theme.textPrimary; font.pixelSize: 14; font.weight: Font.DemiBold }
                    Caption { text: "Canlı alım ve FPGA tespiti · " + survey.runConditionText; Layout.fillWidth: true }
                    Caption { text: survey.state; color: survey.running ? view.theme.accent : view.theme.textSecondary }
                    Action { text: "Sabit Frekans ›"; enabled: !operatorViewModel.busy; onClicked: view.fixedBandRequested() }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    ColumnLayout {
                        spacing: 3
                        Caption { text: "Alt sınır · MHz" }
                        FrequencyField { id: lower; objectName: "surveyLowerMHz"; Layout.preferredWidth: 90; text: "1"; enabled: !operatorViewModel.busy; validator: DoubleValidator { bottom: 1; top: 6000; locale: "C" } Accessible.name: "Tarama alt sınırı megahertz" }
                    }
                    ColumnLayout {
                        spacing: 3
                        Caption { text: "Üst sınır · MHz" }
                        FrequencyField { id: upper; objectName: "surveyUpperMHz"; Layout.preferredWidth: 90; text: "6000"; enabled: !operatorViewModel.busy; validator: DoubleValidator { bottom: 1; top: 6000; locale: "C" } Accessible.name: "Tarama üst sınırı megahertz" }
                    }
                    ColumnLayout {
                        spacing: 3
                        Caption { text: "AZAMİ LNA · dB" }
                        GainChoice { id: lna; Layout.preferredWidth: 75; model: [0,8,16,24,32,40]; currentIndex: 4; enabled: !operatorViewModel.busy; Accessible.name: "Tarama azami LNA kazancı" }
                    }
                    ColumnLayout {
                        spacing: 3
                        Caption { text: "AZAMİ VGA · dB" }
                        GainChoice { id: vga; Layout.preferredWidth: 75; model: [0,8,16,24,32,40,48,56]; currentIndex: 4; enabled: !operatorViewModel.busy; Accessible.name: "Tarama azami VGA kazancı" }
                    }
                    Item { Layout.fillWidth: true }
                    Action { text: operatorViewModel.hackrfReady ? "Alıcı bağlı" : "Alıcıyı Denetle"; enabled: !operatorViewModel.busy; onClicked: operatorViewModel.probeHackrf() }
                    Action {
                        objectName: "surveyStart"
                        text: "Taramayı Başlat"
                        enabled: operatorViewModel.hackrfReady && !operatorViewModel.busy && lower.acceptableInput && upper.acceptableInput && Number(lower.text) < Number(upper.text)
                        onClicked: operatorViewModel.startFrequencySurvey(Number(lower.text), Number(upper.text), Number(lna.currentText), Number(vga.currentText))
                    }
                    Action { objectName: "surveyStop"; text: "Taramayı Durdur"; enabled: survey.running && survey.state !== "Durduruluyor"; onClicked: survey.cancel() }
                }
                RowLayout {
                    visible: false
                    Layout.fillWidth: true
                    spacing: 8
                    Caption { text: "Kontrollü verici kanıtı"; font.weight: Font.Bold }
                    Action {
                        objectName: "surveyReferenceStart"
                        text: "1 · TX’İ KAPAT → REFERANS"
                        enabled: operatorViewModel.hackrfReady && !operatorViewModel.busy && lower.acceptableInput && upper.acceptableInput && Number(lower.text) < Number(upper.text)
                        onClicked: operatorViewModel.startReferenceSurvey(Number(lower.text), Number(upper.text), Number(lna.currentText), Number(vga.currentText))
                        ToolTip.visible: hovered
                        ToolTip.text: "Harici test vericisini gerçekten kapatın. Ortam ve alıcı çizgileri aynı ayarlarla kaydedilir."
                    }
                    Action {
                        objectName: "surveyComparisonStart"
                        text: "2 · TX’İ AÇ → KARŞILAŞTIR"
                        enabled: operatorViewModel.hackrfReady && !operatorViewModel.busy && survey.referenceReady && lower.acceptableInput && upper.acceptableInput && Number(lower.text) < Number(upper.text)
                        onClicked: operatorViewModel.startComparisonSurvey(Number(lower.text), Number(upper.text), Number(lna.currentText), Number(vga.currentText))
                        ToolTip.visible: hovered
                        ToolTip.text: "Harici test vericisini açın. Aynı frekans, gerçek kazanç ve süreyle referansa göre değişen adaylar ayrılır. Bu laboratuvar karşılaştırması yayıncı kimliğini veya saha başarısını kanıtlamaz."
                    }
                    Action { text: "Referansı Sil"; visible: survey.referenceReady; enabled: !operatorViewModel.busy; onClicked: survey.clearReference() }
                    Caption { text: survey.referenceText; Layout.fillWidth: true; wrapMode: Text.Wrap; color: survey.referenceReady ? view.theme.accent : view.theme.textSecondary }
                }
                Caption { visible: !!operatorViewModel.errorMessage; text: operatorViewModel.errorMessage; color: view.theme.danger; Layout.fillWidth: true; wrapMode: Text.Wrap }
                RowLayout {
                    visible: false
                    Layout.fillWidth: true
                    Caption { text: "Arama aralığı" }
                    Action { text: "1,3 GHz çevresi"; enabled: !operatorViewModel.busy; onClicked: { lower.text = "1280"; upper.text = "1330" } }
                    Action { text: "2,4 GHz çevresi"; enabled: !operatorViewModel.busy; onClicked: { lower.text = "2400"; upper.text = "2500" } }
                    Action { text: "5,8 GHz çevresi"; enabled: !operatorViewModel.busy; onClicked: { lower.text = "5725"; upper.text = "5875" } }
                    Action { text: "Tüm aralık"; enabled: !operatorViewModel.busy; onClicked: { lower.text = "1"; upper.text = "6000" } }
                    Caption { text: "600 kHz adımlı örtüşen 2 MHz ayarlar; kısa yayınlar yine kaçabilir."; Layout.fillWidth: true; wrapMode: Text.Wrap; font.pixelSize: 10 }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10
                Card {
                    Layout.fillWidth: true
                    implicitHeight: 150
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            Caption { text: "TARAMA KAPSAMI"; font.weight: Font.Bold; Layout.fillWidth: true }
                            Caption { text: survey.timeText; font.family: "Consolas" }
                        }
                        Label { text: survey.currentRange; color: view.theme.textPrimary; font.pixelSize: 20; font.family: "Consolas" }
                        Canvas {
                            id: coverageCanvas
                            objectName: "surveyCoverage"
                            Layout.fillWidth: true
                            Layout.preferredHeight: 20
                            Accessible.role: Accessible.ProgressBar
                            Accessible.name: survey.coverageText
                            Connections { target: view.survey; function onChanged() { coverageCanvas.requestPaint() } }
                            onPaint: {
                                var ctx = getContext("2d"), states = survey.coverage
                                ctx.reset(); ctx.fillStyle = view.theme.surfaceAlt; ctx.fillRect(0,0,width,height)
                                // Group by screen column: an error or unvisited window must not disappear under a completed neighbour.
                                for (var x = 0; x < Math.ceil(width); x++) {
                                    var a = Math.floor(x * states.length / width)
                                    var b = Math.min(states.length, Math.max(a + 1, Math.ceil((x + 1) * states.length / width)))
                                    var pending = false, failed = false
                                    for (var i = a; i < b; i++) { pending = pending || states[i] === 0; failed = failed || states[i] === 2 }
                                    ctx.fillStyle = failed ? view.theme.warning : pending ? view.theme.surfaceAlt : view.theme.accent
                                    ctx.fillRect(x,0,1,height)
                                }
                                if (survey.running && survey.currentIndex >= 0) {
                                    ctx.fillStyle = view.theme.textPrimary
                                    ctx.fillRect(survey.currentIndex * width / Math.max(1,states.length),0,2,height)
                                }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Caption { text: survey.coverageText; Layout.fillWidth: true }
                            Caption { text: "Gri: bekliyor · Mavi: tarandı · Sarı: hata"; font.pixelSize: 9 }
                        }
                        Caption { text: survey.detail; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                    }
                }
                Card {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            Caption { text: "SON DOĞRULANAN PENCERE"; font.weight: Font.Bold; Layout.fillWidth: true }
                            Caption { text: operatorViewModel.centerFrequencyText; font.family: "Consolas" }
                        }
                        Canvas {
                            id: spectrum
                            objectName: "surveySpectrum"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 90
                            SpectrumTrace { anchors.fill: parent; z: -1; source: operatorViewModel.spectralDisplay }
                            Accessible.role: Accessible.Graphic
                            Accessible.name: "Son tarama penceresinin kalibrasyonsuz dBFS spektrumu"
                            Connections { target: operatorViewModel; function onSpectrumChanged() { spectrum.requestPaint() } }
                            onPaint: {
                                var ctx = getContext("2d")
                                ctx.reset(); ctx.clearRect(0,0,width,height)
                                var left = 42, w = Math.max(1,width-left-8), h = Math.max(1,height-20)
                                ctx.font = "9px Consolas"; ctx.textAlign = "right"
                                for (var i = 0; i <= 4; i++) {
                                    var y = 8+i*(h-16)/4
                                    ctx.strokeStyle = view.theme.border; ctx.beginPath(); ctx.moveTo(left,y); ctx.lineTo(width,y); ctx.stroke()
                                    ctx.fillStyle = view.theme.textSecondary
                                    ctx.fillText((operatorViewModel.spectrumMaxDb-i*(operatorViewModel.spectrumMaxDb-operatorViewModel.spectrumMinDb)/4).toFixed(0),left-6,y+3)
                                }
                            }
                            Label { anchors.centerIn: parent; visible: operatorViewModel.spectrumPointCount < 2; text: "Kart yanıtı bekleniyor"; color: view.theme.textMuted }
                        }
                        WaterfallImage {
                            objectName: "surveyWaterfall"
                            visibleRows: 8
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.max(60, Math.min(120, view.height * 0.14))
                            source: operatorViewModel.spectralDisplay
                            Accessible.name: "Son tamamlanan tarama penceresinin spektrogramı; frekans değişince geçmiş temizlenir"
                        }
                        Caption { text: operatorViewModel.spectralDisplay.historyText + " · Her pencere ayrı frekans geçmişidir"; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
                        RowLayout {
                            Layout.fillWidth: true
                            Caption { text: operatorViewModel.sourceReady ? ((operatorViewModel.centerFrequencyHz-1e6)/1e6).toFixed(3)+" MHz" : "—" }
                            Caption { text: "dBFS · 2 MHz pencere"; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
                            Caption { text: operatorViewModel.sourceReady ? ((operatorViewModel.centerFrequencyHz+1e6)/1e6).toFixed(3)+" MHz" : "—" }
                        }
                    }
                }
            }
            Card {
                Layout.preferredWidth: 320
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8
                    Label { text: "BULUNAN RF ADAYLARI"; color: view.theme.textPrimary; font.pixelSize: 12; font.weight: Font.DemiBold }
                    Caption { text: survey.currentObservationText; color: view.theme.accent; Layout.fillWidth: true; wrapMode: Text.Wrap }
                    RowLayout {
                        Layout.fillWidth: true
                        Caption { text: survey.observationText; Layout.fillWidth: true; wrapMode: Text.Wrap }
                        Caption { text: "ÖNE ÇIKANLAR ÜSTTE"; color: view.theme.textSecondary; font.pixelSize: 9; font.weight: Font.Bold }
                    }
                    ListView {
                        id: observationList
                        objectName: "surveyObservations"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 4
                        model: survey.observationModel
                        reuseItems: true
                        onCountChanged: if (count > 0) positionViewAtBeginning()
                        ScrollBar.vertical: ScrollBar {}
                        delegate: Button {
                            required property var modelData
                            width: observationList.width
                            height: 92
                            Accessible.name: modelData.frequency + ", " + modelData.detail
                            ToolTip.visible: hovered
                            ToolTip.text: modelData.detail + "\n" + modelData.evidenceDetail
                            onClicked: survey.selectObservation(modelData.eventId)
                            background: Rectangle {
                                radius: 4
                                color: survey.selectedKey === modelData.eventId || modelData.latestWindow ? view.theme.accentSoft : view.theme.surfaceAlt
                                border.color: survey.selectedKey === modelData.eventId || modelData.latestWindow ? view.theme.accent : view.theme.border
                            }
                            contentItem: Column {
                                spacing: 3
                                Row {
                                    width: parent.width
                                    spacing: 8
                                    Label { text: modelData.frequency; color: view.theme.textPrimary; font.family: "Consolas"; font.pixelSize: 14 }
                                    Caption { visible: modelData.latestWindow; text: "YENİ"; color: view.theme.accent; font.pixelSize: 9; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                                }
                                Caption { text: modelData.evidence; color: modelData.evidenceKey === "ab_candidate" || modelData.evidenceKey === "uncertain" || modelData.evidenceKey === "energy_candidate" ? view.theme.warning : modelData.evidenceKey === "reference" ? view.theme.textMuted : view.theme.accent; font.pixelSize: 10; font.weight: Font.Bold }
                                Caption { text: modelData.detail; color: view.theme.textSecondary; font.pixelSize: 10; width: parent.width; elide: Text.ElideRight }
                                Caption { text: modelData.window + " · " + modelData.evidenceDetail; color: view.theme.textMuted; font.pixelSize: 9; elide: Text.ElideRight; width: parent.width }
                            }
                        }
                        Caption { anchors.centerIn: parent; visible: observationList.count === 0; text: "Henüz RF adayı bulunmadı"; width: parent.width - 24; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
                    }
                    Caption { text: survey.selectedFrequency > 0 ? (survey.selectedFrequency/1e6).toFixed(6)+" MHz seçildi" : "Sürekli izleme için bir frekans seçin"; Layout.fillWidth: true; wrapMode: Text.Wrap }
                    Action {
                        objectName: "surveyMonitor"
                        Layout.fillWidth: true
                        text: survey.running ? "Önce taramayı durdurun" : "Sabit Frekansta Tara"
                        enabled: !operatorViewModel.busy && survey.selectedFrequency > 0
                        onClicked: if (operatorViewModel.monitorSurveyObservation()) view.fixedBandRequested()
                    }
                }
            }
        }
        Caption {
            HoverHandler { id: footerHover }
            text: "Sonuçlar RF adaylarını gösterir. Seçtiğiniz adayı sabit frekansta yeniden tarayabilirsiniz."
            Layout.fillWidth: true
            font.pixelSize: 10
            elide: Text.ElideRight
            ToolTip.visible: footerHover.hovered
            ToolTip.text: survey.auditPath ? "Alım kaydı: " + survey.auditPath : "Her tarama ayrı alım kaydına yazılır."
        }
    }
}
