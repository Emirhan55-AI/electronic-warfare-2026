import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    property string state: "Kullanılmıyor"
    Accessible.name: "Durum: " + state
    Accessible.role: Accessible.StaticText
    implicitWidth: badgeText.implicitWidth + 18
    implicitHeight: 24
    radius: 12
    color: "#1F1F1F"
    border.color: state === "Hazır" ? BazTheme.success : state === "Çalışıyor" ? BazTheme.accent : state === "Hata" ? BazTheme.danger : state === "Bekliyor" ? BazTheme.warning : "#6E7681"
    Behavior on color { ColorAnimation { duration: BazTheme.transitionDuration } }
    Behavior on border.color { ColorAnimation { duration: BazTheme.transitionDuration } }
    Text {
        id: badgeText
        anchors.centerIn: parent
        text: parent.state
        color: parent.border.color
        font.pixelSize: 11
        font.weight: Font.DemiBold
    }
}
