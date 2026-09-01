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
    color: state === "Hazır" ? "#153B31" : state === "Çalışıyor" ? "#123B42" : state === "Hata" ? "#48252B" : state === "Bekliyor" ? "#3B321F" : "#25313A"
    border.color: state === "Hazır" ? BazTheme.success : state === "Çalışıyor" ? BazTheme.accent : state === "Hata" ? BazTheme.danger : state === "Bekliyor" ? BazTheme.warning : "#536570"
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
