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
            SectionTitle { text: "TEKLİ GÖREV" }
            Rectangle { Layout.fillWidth: true; height: 1; color: shell.border }
            Label {
                text: operatorViewModel.etStatus
                color: operatorViewModel.etTransmitting ? shell.warning : shell.textSecondary
                font.pixelSize: shell.uiMetaTextSize
                font.family: "Consolas"
                font.weight: Font.Bold
            }
        }

        Panel {
            Layout.fillWidth: true
            Layout.fillHeight: true

            RowLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 22

                ColumnLayout {
                    Layout.preferredWidth: Math.min(430, etWorkspace.width * 0.38)
                    Layout.maximumWidth: 460
                    Layout.fillHeight: true
                    spacing: 12

                    Label {
                        text: "Tek hedef frekans bandı"
                        color: shell.textPrimary
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                    }
                    Label {
                        text: "Seçilen aralıkta bant sınırlı gürültü üretilir. Görev en geç 30 saniyede kendiliğinden sona erer."
                        color: shell.textSecondary
                        font.pixelSize: shell.uiBodyTextSize
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }

                    GridLayout {
                        columns: 2
                        columnSpacing: 10
                        rowSpacing: 8
                        Layout.fillWidth: true

                        Label { text: "Alt frekans"; color: shell.textSecondary }
                        AppField {
                            id: lowerFrequency
                            objectName: "etSingleLowerMHz"
                            text: "853.500"
                            placeholderText: "MHz"
                            enabled: !operatorViewModel.etTransmitting
                            validator: DoubleValidator { bottom: 1; top: 6000; decimals: 6; locale: "C" }
                            Accessible.name: "Tekli görev alt frekansı megahertz"
                            Layout.fillWidth: true
                        }

                        Label { text: "Üst frekans"; color: shell.textSecondary }
                        AppField {
                            id: upperFrequency
                            objectName: "etSingleUpperMHz"
                            text: "854.500"
                            placeholderText: "MHz"
                            enabled: !operatorViewModel.etTransmitting
                            validator: DoubleValidator { bottom: 1; top: 6000; decimals: 6; locale: "C" }
                            Accessible.name: "Tekli görev üst frekansı megahertz"
                            Layout.fillWidth: true
                        }

                        Label { text: "Görev süresi"; color: shell.textSecondary }
                        AppField {
                            id: missionDuration
                            objectName: "etSingleDurationSeconds"
                            text: "1.0"
                            placeholderText: "saniye"
                            enabled: !operatorViewModel.etTransmitting
                            validator: DoubleValidator { bottom: 0.1; top: 30; decimals: 3; locale: "C" }
                            Accessible.name: "Tekli görev süresi saniye"
                            Layout.fillWidth: true
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: gateText.implicitHeight + 20
                        radius: 4
                        color: shell.surfaceAlt
                        border.color: operatorViewModel.etCanTransmit ? shell.success : shell.border
                        Label {
                            id: gateText
                            objectName: "etTxGateState"
                            anchors.fill: parent
                            anchors.margins: 10
                            text: operatorViewModel.etTxGateState
                            color: operatorViewModel.etCanTransmit ? shell.success : shell.textMuted
                            font.pixelSize: shell.uiMetaTextSize
                            wrapMode: Text.Wrap
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        QuietButton {
                            objectName: "etSinglePreview"
                            text: "İletimsiz Doğrula"
                            enabled: !operatorViewModel.busy && !operatorViewModel.etTransmitting
                            Layout.fillWidth: true
                            onClicked: operatorViewModel.previewETSingle(
                                lowerFrequency.text, upperFrequency.text, missionDuration.text
                            )
                        }
                        QuietButton {
                            objectName: "etSingleStart"
                            text: "Gönderimi Başlat"
                            enabled: operatorViewModel.etCanTransmit && !operatorViewModel.busy && !operatorViewModel.etTransmitting
                            Layout.fillWidth: true
                            onClicked: operatorViewModel.startETSingle(
                                lowerFrequency.text, upperFrequency.text, missionDuration.text
                            )
                        }
                    }
                    QuietButton {
                        objectName: "etSingleStop"
                        text: "Gönderimi Durdur"
                        enabled: operatorViewModel.etTransmitting
                        Layout.fillWidth: true
                        onClicked: operatorViewModel.stopETSingle()
                    }
                    QuietButton {
                        objectName: "etSingleEmergencyStop"
                        text: "ACİL DURDUR"
                        enabled: operatorViewModel.etTransmitting
                        Layout.fillWidth: true
                        onClicked: operatorViewModel.emergencyStopETSingle()
                    }
                    Item { Layout.fillHeight: true }
                }

                Rectangle { Layout.fillHeight: true; width: 1; color: shell.border }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 12

                    Label {
                        objectName: "etResultTitle"
                        text: operatorViewModel.etResultTitle
                        color: shell.textPrimary
                        font.pixelSize: 22
                        font.weight: Font.DemiBold
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                    Label {
                        objectName: "etResultDetail"
                        text: operatorViewModel.etResultDetail
                        color: shell.textSecondary
                        font.pixelSize: shell.uiBodyTextSize
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: shell.border }
                    Repeater {
                        model: operatorViewModel.etMetricRows
                        delegate: RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            Label {
                                text: modelData.label
                                color: shell.textMuted
                                font.pixelSize: shell.uiMetaTextSize
                                Layout.fillWidth: true
                            }
                            Label {
                                text: modelData.value
                                color: shell.textPrimary
                                font.pixelSize: shell.uiBodyTextSize
                                font.family: "Consolas"
                            }
                        }
                    }
                    Item { Layout.fillHeight: true }
                    Label {
                        text: "RF gönderimi yalnız seri kimliği, izinli bant, süreli fiziksel kapı ve doğrulanmış zayıflatma birlikte geçerse açılır."
                        color: shell.textMuted
                        font.pixelSize: shell.uiMetaTextSize
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }
}
