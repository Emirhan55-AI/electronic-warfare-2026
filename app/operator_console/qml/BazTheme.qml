pragma Singleton
import QtQuick

QtObject {
    readonly property color surface: "#1F1F1F"
    readonly property color surfaceAlt: "#202020"
    readonly property color raised: "#2B2B2B"
    readonly property color border: "#2B2B2B"
    readonly property color textPrimary: "#CCCCCC"
    readonly property color textSecondary: "#9D9D9D"
    readonly property color textMuted: "#868686"
    readonly property color accent: "#0078D4"
    readonly property color accentSoft: "#2B2B2B"
    readonly property color success: "#2EA043"
    readonly property color warning: "#E2C08D"
    readonly property color danger: "#F85149"
    readonly property int transitionDuration: operatorViewModel.reducedMotion ? 0 : 170
    readonly property int uiSectionTextSize: 10
    readonly property int uiMetaTextSize: 9
}
