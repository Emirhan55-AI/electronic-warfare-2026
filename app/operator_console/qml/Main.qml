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
    color: "#071018"

    property int workspace: 0
    property color appBackground: "#071018"
    property color surface: "#0D1822"
    property color raised: "#12222E"
    property color border: "#263B49"
    property color textPrimary: "#E8F1F5"
    property color textSecondary: "#93A8B5"
    property color accent: "#32B8C6"
    property color success: "#53C58C"
    property color warning: "#E6B85C"
    property color danger: "#EF6B73"
    property int transitionDuration: operatorViewModel.reducedMotion ? 0 : 150

    component Panel: Rectangle {
        color: root.surface
        border.color: root.border
        border.width: 1
        radius: 8
    }

    component SectionTitle: Label {
        color: root.textSecondary
        font.pixelSize: 11
        font.weight: Font.DemiBold
        font.letterSpacing: 1.2
    }

    component PrimaryButton: Button {
        id: control
        implicitHeight: 38
        font.pixelSize: 13
        font.weight: Font.DemiBold
        Accessible.name: text
        background: Rectangle {
            radius: 5
            color: control.enabled ? (control.down ? "#218F9B" : root.accent) : "#263640"
            border.color: control.activeFocus ? "#C9F7FA" : "transparent"
            border.width: 2
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
        implicitHeight: 36
        font.pixelSize: 13
        Accessible.name: text
        background: Rectangle {
            radius: 5
            color: control.checked ? "#173A45" : control.down ? "#1C3441" : "#12242F"
            border.color: control.activeFocus ? root.accent : root.border
            border.width: control.activeFocus ? 2 : 1
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
        Text {
            id: badgeText
            anchors.centerIn: parent
            text: parent.state
            color: parent.border.color
            font.pixelSize: 11
            font.weight: Font.DemiBold
        }
    }

    FileDialog {
        id: sigmfDialog
        title: "SigMF metadata kaydını seç"
        nameFilters: ["SigMF metadata (*.sigmf-meta)"]
        fileMode: FileDialog.OpenFile
        onAccepted: operatorViewModel.openSigmf(selectedFile.toString())
    }

    Shortcut { sequence: "Ctrl+O"; onActivated: if (operatorViewModel.sourceMode === "sigmf") sigmfDialog.open() }
    Shortcut { sequence: "Space"; onActivated: operatorViewModel.playing ? operatorViewModel.pause() : operatorViewModel.startScan() }
    Shortcut { sequence: "Ctrl+1"; onActivated: root.workspace = 0 }
    Shortcut { sequence: "Ctrl+2"; onActivated: root.workspace = 1 }
    Shortcut { sequence: "Ctrl+3"; onActivated: root.workspace = 2 }

    header: Rectangle {
        height: 72
        color: "#09151E"
        border.color: root.border
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 22
            anchors.rightMargin: 22
            spacing: 22

            ColumnLayout {
                Layout.preferredWidth: 330
                spacing: 2
                Label { text: "ELEKTRONİK HARP"; color: root.accent; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 2 }
                Label { text: "Operatör Konsolu"; color: root.textPrimary; font.pixelSize: 20; font.weight: Font.DemiBold }
            }

            Rectangle { Layout.fillHeight: true; width: 1; color: root.border; Layout.topMargin: 16; Layout.bottomMargin: 16 }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                Label { text: operatorViewModel.sourceName; color: root.textPrimary; font.pixelSize: 13; elide: Text.ElideMiddle; Layout.fillWidth: true }
                Label { text: operatorViewModel.statusMessage; color: operatorViewModel.errorMessage ? root.danger : root.textSecondary; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
            }

            ColumnLayout {
                spacing: 2
                Label { text: "MERKEZ"; color: root.textSecondary; font.pixelSize: 10 }
                Label { text: operatorViewModel.centerFrequencyText; color: root.textPrimary; font.pixelSize: 14; font.family: "Consolas" }
            }
            ColumnLayout {
                spacing: 2
                Label { text: "ÖRNEKLEME"; color: root.textSecondary; font.pixelSize: 10 }
                Label { text: operatorViewModel.sampleRateText; color: root.textPrimary; font.pixelSize: 14; font.family: "Consolas" }
            }
            StateBadge { state: operatorViewModel.busy ? "Çalışıyor" : operatorViewModel.sourceState }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 92
            Layout.fillHeight: true
            color: "#09151E"
            border.color: root.border
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.topMargin: 18
                anchors.bottomMargin: 18
                spacing: 8

                Repeater {
                    model: [
                        {"label": "Operasyon", "key": "O"},
                        {"label": "Yön Bulma", "key": "Y"},
                        {"label": "Sistem", "key": "S"}
                    ]
                    delegate: Button {
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true
                        Layout.preferredHeight: 64
                        flat: true
                        Accessible.name: modelData.label
                        onClicked: root.workspace = index
                        background: Rectangle {
                            color: root.workspace === index ? "#13313B" : "transparent"
                            border.color: root.workspace === index ? root.accent : "transparent"
                            border.width: root.workspace === index ? 1 : 0
                            radius: 5
                        }
                        contentItem: Column {
                            spacing: 4
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.key; color: root.workspace === index ? root.accent : root.textSecondary; font.pixelSize: 18; font.weight: Font.Bold }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.label; color: root.workspace === index ? root.textPrimary : root.textSecondary; font.pixelSize: 10 }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
                Button {
                    Layout.alignment: Qt.AlignHCenter
                    flat: true
                    text: operatorViewModel.reducedMotion ? "Hareket\nkapalı" : "Hareket\naçık"
                    Accessible.name: "Hareketi azalt"
                    onClicked: operatorViewModel.setReducedMotion(!operatorViewModel.reducedMotion)
                    contentItem: Text { text: parent.text; color: root.textSecondary; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 10 }
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
                    anchors.margins: 14
                    spacing: 12

                    Panel {
                        Layout.preferredWidth: 274
                        Layout.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12
                            SectionTitle { text: "VERİ KAYNAĞI" }

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
                            SectionTitle { text: "KAYNAK SÖZLEŞMESİ" }
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
                                implicitHeight: profileText.implicitHeight + 20
                                radius: 5
                                color: "#0A141C"
                                border.color: root.border
                                Label {
                                    id: profileText
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    text: operatorViewModel.profileSummary
                                    wrapMode: Text.Wrap
                                    color: root.textSecondary
                                    font.pixelSize: 10
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
                                    SectionTitle { text: "SPEKTRUM · ANLIK dBFS"; Layout.fillWidth: true }
                                    Label { text: operatorViewModel.performanceText; color: root.textSecondary; font.pixelSize: 10 }
                                }
                                Canvas {
                                    id: spectrumCanvas
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    Accessible.name: "Anlık güç spektrumu"
                                    onWidthChanged: operatorViewModel.setSpectrumViewportWidth(width)
                                    Connections { target: operatorViewModel; function onSpectrumChanged() { spectrumCanvas.requestPaint() } }
                                    onPaint: {
                                        var ctx = getContext("2d")
                                        ctx.reset()
                                        ctx.fillStyle = "#08121A"
                                        ctx.fillRect(0, 0, width, height)
                                        ctx.strokeStyle = "#19303D"
                                        ctx.lineWidth = 1
                                        for (var gx = 0; gx <= 8; gx++) {
                                            var x = gx * width / 8
                                            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke()
                                        }
                                        for (var gy = 0; gy <= 5; gy++) {
                                            var y = gy * height / 5
                                            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke()
                                        }
                                        var values = operatorViewModel.spectrumValues
                                        if (!values || values.length < 2) return
                                        var low = operatorViewModel.spectrumMinDb
                                        var high = operatorViewModel.spectrumMaxDb
                                        ctx.strokeStyle = root.accent
                                        ctx.lineWidth = 1.5
                                        ctx.beginPath()
                                        for (var i = 0; i < values.length; i++) {
                                            var px = i * width / (values.length - 1)
                                            var py = height - Math.max(0, Math.min(1, (values[i] - low) / (high - low))) * height
                                            if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py)
                                        }
                                        ctx.stroke()
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: "− Fs/2"; color: root.textSecondary; font.pixelSize: 10 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: operatorViewModel.centerFrequencyText; color: root.textPrimary; font.pixelSize: 10 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: "+ Fs/2"; color: root.textSecondary; font.pixelSize: 10 }
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
                                SectionTitle { text: "SPEKTROGRAM · SON 48 KARE" }
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
                                        ctx.reset(); ctx.fillStyle = "#08121A"; ctx.fillRect(0, 0, width, height)
                                        var low = operatorViewModel.spectrumMinDb
                                        var high = operatorViewModel.spectrumMaxDb
                                        for (var row = 0; row < history.length; row++) {
                                            var vals = history[row]
                                            var y = height - (history.length - row) * height / 48
                                            var rh = Math.ceil(height / 48)
                                            for (var col = 0; col < vals.length; col += 3) {
                                                var level = Math.max(0, Math.min(1, (vals[col] - low) / (high - low)))
                                                var red = Math.round(20 + 35 * level)
                                                var green = Math.round(45 + 150 * level)
                                                var blue = Math.round(60 + 160 * level)
                                                ctx.fillStyle = "rgb(" + red + "," + green + "," + blue + ")"
                                                ctx.fillRect(col * width / vals.length, y, Math.ceil(3 * width / vals.length), rh)
                                            }
                                        }
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
                        Layout.preferredWidth: 300
                        Layout.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10
                            RowLayout {
                                Layout.fillWidth: true
                                SectionTitle { text: "TESPİTLER"; Layout.fillWidth: true }
                                Label { text: operatorViewModel.detections.length; color: root.accent; font.pixelSize: 12; font.weight: Font.Bold }
                            }
                            ListView {
                                id: detectionList
                                Layout.fillWidth: true
                                Layout.preferredHeight: Math.min(270, contentHeight)
                                clip: true
                                spacing: 6
                                model: operatorViewModel.detections
                                delegate: Button {
                                    required property var modelData
                                    width: ListView.view.width
                                    height: 62
                                    Accessible.name: modelData.title + ", " + modelData.state
                                    onClicked: operatorViewModel.selectDetection(modelData.eventId)
                                    background: Rectangle {
                                        radius: 5
                                        color: operatorViewModel.selectedDetectionId === modelData.eventId ? "#163540" : "#0A151D"
                                        border.color: operatorViewModel.selectedDetectionId === modelData.eventId ? root.accent : root.border
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
                            SectionTitle { text: "PARAMETRE ÖLÇÜMÜ" }
                            Label {
                                Layout.fillWidth: true
                                text: operatorViewModel.parameterCapabilityReady
                                      ? "F5 · Dört ardışık kare · Operatör onaylı analiz aralığı"
                                      : "Doğrulanmış F5 ürün profili kullanılamıyor."
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
                                    Label { text: "Alt sınır (MHz)"; color: root.textSecondary; font.pixelSize: 9 }
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
                                    Label { text: "Üst sınır (MHz)"; color: root.textSecondary; font.pixelSize: 9 }
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
                                    height: 24
                                    Label { text: modelData.label; color: root.textSecondary; font.pixelSize: 10; Layout.fillWidth: true }
                                    Label { text: modelData.value; color: root.textPrimary; font.pixelSize: 10; font.family: "Consolas" }
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
                            Panel {
                                Layout.fillWidth: true; Layout.preferredHeight: 120
                                Column { anchors.centerIn: parent; spacing: 7
                                    Label { anchors.horizontalCenter: parent.horizontalCenter; text: "BAĞIL GELİŞ AÇISI"; color: root.textSecondary; font.pixelSize: 11 }
                                    Label { anchors.horizontalCenter: parent.horizontalCenter; text: operatorViewModel.relativeArrivalText; color: root.accent; font.pixelSize: 30; font.weight: Font.DemiBold }
                                }
                            }
                            Panel {
                                Layout.fillWidth: true; Layout.preferredHeight: 120
                                Column { anchors.centerIn: parent; spacing: 7
                                    Label { anchors.horizontalCenter: parent.horizontalCenter; text: "GERÇEK KUZEYE GÖRE KERTERİZ"; color: root.textSecondary; font.pixelSize: 11 }
                                    Label { anchors.horizontalCenter: parent.horizontalCenter; text: operatorViewModel.bearingText; color: root.success; font.pixelSize: 30; font.weight: Font.DemiBold }
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
                        Layout.preferredHeight: 176
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 12
                            RowLayout {
                                Layout.fillWidth: true
                                SectionTitle { text: "İŞLEME AKIŞI · SALT OKUNUR"; Layout.fillWidth: true }
                                Label { text: operatorViewModel.profileSummary; color: root.textSecondary; font.pixelSize: 10 }
                            }
                            GridLayout {
                                Layout.fillWidth: true
                                columns: 5
                                columnSpacing: 8
                                Repeater {
                                    model: operatorViewModel.pipelineBlocks
                                    delegate: Panel {
                                        required property var modelData
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 0
                                        Layout.preferredHeight: 82
                                        Column {
                                            anchors.centerIn: parent
                                            width: parent.width - 12
                                            spacing: 7
                                            Label { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.name; color: root.textPrimary; font.pixelSize: 10; font.weight: Font.DemiBold; elide: Text.ElideRight; width: parent.width; horizontalAlignment: Text.AlignHCenter }
                                            StateBadge { anchors.horizontalCenter: parent.horizontalCenter; state: modelData.state }
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
                                SectionTitle { text: "OLAY GÜNLÜĞÜ"; Layout.fillWidth: true }
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
                                    width: ListView.view.width; height: 42; color: index % 2 ? "#0A151D" : "transparent"
                                    RowLayout { anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8; spacing: 16
                                        Label { text: modelData.time; color: root.textSecondary; font.pixelSize: 11; font.family: "Consolas"; Layout.preferredWidth: 72 }
                                        Label { text: modelData.component; color: modelData.component === "Hata" ? root.danger : root.accent; font.pixelSize: 11; font.weight: Font.DemiBold; Layout.preferredWidth: 110 }
                                        Label { text: modelData.message; color: root.textPrimary; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight }
                                    }
                                }
                            }
                        }
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
