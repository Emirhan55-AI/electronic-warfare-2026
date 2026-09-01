import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    required property var shell
    id: etWorkspace
    objectName: "etWorkspace"
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 24
            SectionTitle { text: "GÖREV SEÇİMİ" }
            Rectangle { Layout.fillWidth: true; height: 1; color: shell.border }
        }

        RowLayout {
            id: etTaskRow
            property real cardHeight: shell.height < 780 ? 66 : 72
            Layout.fillWidth: true
            Layout.preferredHeight: cardHeight
            Layout.minimumHeight: cardHeight
            Layout.maximumHeight: cardHeight
            spacing: 8
            Repeater {
                model: operatorViewModel.etTaskCards
                delegate: Button {
                    id: etTaskCard
                    required property var modelData
                    Layout.preferredWidth: Math.max(180, (shell.width - 124) / 4)
                    Layout.minimumWidth: Layout.preferredWidth
                    Layout.maximumWidth: Layout.preferredWidth
                    Layout.fillHeight: true
                    property bool selected: operatorViewModel.etTask === modelData.id
                    Accessible.name: modelData.name + ", " + modelData.maturity
                    onClicked: operatorViewModel.selectETTask(modelData.id)
                    scale: down ? 0.99 : 1.0
                    Behavior on scale { NumberAnimation { duration: shell.transitionDuration; easing.type: Easing.OutCubic } }
                    background: Rectangle {
                        radius: 5
                        color: etTaskCard.selected ? shell.accentSoft : shell.surfaceAlt
                        border.color: etTaskCard.selected ? shell.accent : shell.border
                        Behavior on color { ColorAnimation { duration: shell.transitionDuration } }
                        Rectangle {
                            anchors.left: parent.left; anchors.bottom: parent.bottom
                            height: 3; radius: 2; color: shell.accent
                            width: etTaskCard.selected ? parent.width : 0
                            Behavior on width { NumberAnimation { duration: shell.transitionDuration + 40; easing.type: Easing.OutCubic } }
                        }
                    }
                    contentItem: ColumnLayout {
                        spacing: 3
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: modelData.name; color: etTaskCard.selected ? shell.textPrimary : shell.textSecondary; font.pixelSize: shell.uiBodyTextSize + 1; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                            Text { visible: shell.width >= 1400; text: modelData.maturity; color: etTaskCard.selected ? shell.accent : shell.textMuted; font.pixelSize: 8; font.family: "Consolas"; font.weight: Font.Bold }
                        }
                        Text { text: modelData.detail; color: shell.textMuted; font.pixelSize: shell.uiMetaTextSize; elide: Text.ElideRight; Layout.fillWidth: true }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            Panel {
                id: etResultPanel
                Layout.fillWidth: true
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Label { text: operatorViewModel.etResultTitle; color: shell.textPrimary; font.pixelSize: shell.height < 780 ? 15 : 18; font.weight: Font.DemiBold; Layout.fillWidth: true; elide: Text.ElideRight }
                            Label { text: operatorViewModel.etResultDetail; color: operatorViewModel.etStatus === "HATA" ? shell.danger : shell.textSecondary; font.pixelSize: shell.uiMetaTextSize + 1; Layout.fillWidth: true; wrapMode: Text.Wrap }
                        }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: shell.border }
                    RowLayout {
                        visible: operatorViewModel.etTask !== "gnss"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 8
                        EtChart { Layout.fillWidth: true; Layout.fillHeight: true; title: operatorViewModel.etPrimaryTitle; values: operatorViewModel.etPrimaryValues }
                        EtChart { Layout.fillWidth: true; Layout.fillHeight: true; title: operatorViewModel.etSecondaryTitle; values: operatorViewModel.etSecondaryValues }
                    }
                    Panel {
                        visible: operatorViewModel.etTask === "gnss"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#071018"
                        ColumnLayout {
                            anchors.centerIn: parent
                            width: Math.min(parent.width - 40, 520)
                            spacing: 10
                            Label { text: "GPS L1 C/A"; color: shell.textPrimary; font.pixelSize: 24; font.weight: Font.DemiBold; Layout.alignment: Qt.AlignHCenter }
                            Label { text: "Bu görev yalnız konum, kesin UTC ve PRN metadata sözleşmesini doğrular."; color: shell.textSecondary; font.pixelSize: shell.uiBodyTextSize; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
                            Rectangle { Layout.fillWidth: true; height: 1; color: shell.border }
                            Label { text: "EFEMERİS YOK  ·  NAV MESAJI YOK  ·  I/Q DALGA ŞEKLİ YOK"; color: shell.warning; font.pixelSize: shell.uiMetaTextSize; font.family: "Consolas"; font.weight: Font.Bold; Layout.alignment: Qt.AlignHCenter }
                        }
                    }
                    RowLayout {
                        visible: operatorViewModel.etTask === "interleaved" && operatorViewModel.etTimeline.length > 0
                        Layout.fillWidth: true
                        Layout.preferredHeight: 58
                        Layout.minimumHeight: 58
                        Layout.maximumHeight: 58
                        spacing: 4
                        Repeater {
                            model: operatorViewModel.etTimeline
                            delegate: Rectangle {
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                radius: 3
                                color: modelData.state === "GÖREV" ? "#153B31" : modelData.state === "GECİKME" ? "#3B321F" : modelData.state === "KORUMA" ? "#35252A" : "#0D1822"
                                border.color: modelData.state === "GÖREV" ? shell.success : modelData.state === "GECİKME" ? shell.warning : modelData.state === "KORUMA" ? shell.danger : shell.border
                                ColumnLayout {
                                    anchors.centerIn: parent
                                    spacing: 1
                                    Label { text: modelData.index; color: shell.textMuted; font.pixelSize: 8; font.family: "Consolas"; Layout.alignment: Qt.AlignHCenter }
                                    Label { text: modelData.state; color: shell.textPrimary; font.pixelSize: shell.uiDenseMetaTextSize; font.weight: Font.Bold; Layout.alignment: Qt.AlignHCenter }
                                }
                            }
                        }
                    }
                }
                Rectangle {
                    id: etResultFlash
                    z: 5
                    anchors.fill: parent
                    radius: parent.radius
                    color: "transparent"
                    border.color: shell.accent
                    border.width: 1
                    opacity: 0
                }
            }

            Panel {
                Layout.preferredWidth: shell.width < 1400 ? 286 : 326
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 9
                    RowLayout {
                        Layout.fillWidth: true
                        SectionTitle { text: "GÖREV AYARLARI"; Layout.fillWidth: true }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: shell.border }
                    StackLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: operatorViewModel.etTask === "gnss" ? 150 : 108
                        Layout.minimumHeight: Layout.preferredHeight
                        Layout.maximumHeight: Layout.preferredHeight
                        currentIndex: operatorViewModel.etTask === "continuous" ? 0 : operatorViewModel.etTask === "interleaved" ? 1 : operatorViewModel.etTask === "analog" ? 2 : 3
                        Item {
                            ColumnLayout { anchors.fill: parent; spacing: 7
                                Label { text: "Dalga biçimi ailesi"; color: shell.textSecondary; font.pixelSize: shell.uiMetaTextSize }
                                AppCombo { id: etContinuousOption; objectName: "etContinuousOption"; Layout.fillWidth: true; model: ["Tekli", "Çoklu", "Baraj", "Doğrusal Süpürme"] }
                                PrimaryButton { objectName: "etContinuousRun"; Layout.fillWidth: true; text: "Görevi Çalıştır"; onClicked: operatorViewModel.runETTask("continuous", ["single", "multiple", "barrage", "sweep"][etContinuousOption.currentIndex]) }
                            }
                        }
                        Item {
                            ColumnLayout { anchors.fill: parent; spacing: 7
                                Label { text: "Deterministik analiz girdisi"; color: shell.textSecondary; font.pixelSize: shell.uiMetaTextSize }
                                AppCombo { id: etInterleavedOption; objectName: "etInterleavedOption"; Layout.fillWidth: true; model: ["Hedef Yok", "Sürekli Hedef", "Kesintili Hedef", "Eşik Kenarı"] }
                                PrimaryButton { objectName: "etInterleavedRun"; Layout.fillWidth: true; text: "Zamanlamayı Çalıştır"; onClicked: operatorViewModel.runETTask("interleaved", ["absent", "present", "intermittent", "edge"][etInterleavedOption.currentIndex]) }
                            }
                        }
                        Item {
                            ColumnLayout { anchors.fill: parent; spacing: 7
                                Label { text: "Yerel döngü modu"; color: shell.textSecondary; font.pixelSize: shell.uiMetaTextSize }
                                AppCombo { id: etAnalogOption; objectName: "etAnalogOption"; Layout.fillWidth: true; model: ["NFM", "FM", "AM"] }
                                PrimaryButton { objectName: "etAnalogRun"; Layout.fillWidth: true; text: "Yerel Döngüyü Çalıştır"; onClicked: operatorViewModel.runETTask("analog", etAnalogOption.currentText) }
                            }
                        }
                        Item {
                            ColumnLayout { anchors.fill: parent; spacing: 5
                                RowLayout { Layout.fillWidth: true
                                    AppField { id: etLatitude; Layout.fillWidth: true; Layout.preferredHeight: 30; text: "39.93340"; placeholderText: "Enlem"; Accessible.name: "Sanal enlem" }
                                    AppField { id: etLongitude; Layout.fillWidth: true; Layout.preferredHeight: 30; text: "32.85970"; placeholderText: "Boylam"; Accessible.name: "Sanal boylam" }
                                }
                                AppField { id: etUtc; Layout.fillWidth: true; Layout.preferredHeight: 30; text: "2026-08-16T12:00:00Z"; placeholderText: "UTC zaman"; Accessible.name: "Senaryo UTC zamanı" }
                                AppField { id: etPrns; Layout.fillWidth: true; Layout.preferredHeight: 30; text: "3, 8, 63"; placeholderText: "PRN kodları"; Accessible.name: "GPS L1 C/A PRN kodları" }
                                PrimaryButton { objectName: "etGnssValidate"; Layout.fillWidth: true; Layout.preferredHeight: 36; text: "Senaryoyu Denetle"; onClicked: operatorViewModel.validateETGNSS(Number(etLatitude.text), Number(etLongitude.text), etUtc.text, etPrns.text) }
                            }
                        }
                    }
                    SectionTitle { text: "ÖLÇÜMLER"; visible: operatorViewModel.etMetricRows.length > 0 }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 2
                        model: operatorViewModel.etMetricRows
                        delegate: Rectangle {
                            required property var modelData
                            width: ListView.view.width
                            height: 26
                            color: "#071018"
                            radius: 3
                            RowLayout { anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8
                                Label { text: modelData.label; color: shell.textSecondary; font.pixelSize: shell.uiMetaTextSize + 1; Layout.fillWidth: true }
                                Label { text: modelData.value; color: modelData.value === "FAIL" ? shell.danger : shell.textPrimary; font.pixelSize: shell.uiMetaTextSize + 1; font.family: "Consolas"; font.weight: Font.DemiBold }
                            }
                        }
                    }
                }
            }
        }
    }
}
