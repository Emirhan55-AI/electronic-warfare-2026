pragma Singleton
import QtQuick

QtObject {
    readonly property color surface: "#0A131C"
    readonly property color surfaceAlt: "#0D1822"
    readonly property color raised: "#111F2A"
    readonly property color border: "#20313D"
    readonly property color textPrimary: "#EDF5F7"
    readonly property color textSecondary: "#8CA0AC"
    readonly property color textMuted: "#607480"
    readonly property color accent: "#31C3D2"
    readonly property color accentSoft: "#12343D"
    readonly property color success: "#59D39A"
    readonly property color warning: "#F0BC62"
    readonly property color danger: "#F07178"
    readonly property int transitionDuration: operatorViewModel.reducedMotion ? 0 : 170
    readonly property int uiSectionTextSize: 10
    readonly property int uiMetaTextSize: 9
}
