import QtQuick

Item {
    id: intro
    objectName: "startupIntro"
    signal finished()

    opacity: 1
    focus: true

    property bool closing: false
    property bool finishedEmitted: false

    function begin() {
        if (!closing && !finishedEmitted && !introSequence.running) introSequence.start()
    }

    function complete() {
        if (finishedEmitted) return
        finishedEmitted = true
        opacity = 0
        finished()
    }

    function finishImmediately() {
        if (finishedEmitted) return
        closing = true
        introSequence.stop()
        quickExit.stop()
        complete()
    }

    function dismiss() {
        if (closing) return
        closing = true
        introSequence.stop()
        quickExit.start()
    }

    Rectangle {
        anchors.fill: parent
        color: "#05070B"
    }

    Image {
        id: introImage
        anchors.fill: parent
        opacity: 0
        source: "../assets/baz-logo-intro.png"
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: true
        smooth: true

        onStatusChanged: {
            if (status === Image.Ready) intro.begin()
            else if (status === Image.Error) intro.finishImmediately()
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: intro.dismiss()
    }

    Keys.onPressed: function(event) {
        intro.dismiss()
        event.accepted = true
    }

    Component.onCompleted: {
        forceActiveFocus()
        if (introImage.status === Image.Ready) begin()
        else if (introImage.status === Image.Error) finishImmediately()
    }

    SequentialAnimation {
        id: introSequence
        NumberAnimation {
            target: introImage
            property: "opacity"
            from: 0
            to: 1
            duration: 280
            easing.type: Easing.OutCubic
        }
        PauseAnimation { duration: 1000 }
        NumberAnimation {
            target: intro
            property: "opacity"
            from: 1
            to: 0
            duration: 420
            easing.type: Easing.InCubic
        }
        ScriptAction { script: intro.complete() }
    }

    NumberAnimation {
        id: quickExit
        target: intro
        property: "opacity"
        from: intro.opacity
        to: 0
        duration: 160
        easing.type: Easing.OutCubic
        onFinished: intro.complete()
    }

    Timer {
        interval: 3000
        running: true
        repeat: false
        onTriggered: intro.finishImmediately()
    }
}
