.pragma library

function activateWorkspace(root, item) {
    if (item.workspace === 0 && item.task === 0) {
        var optionsAlreadyVisible = root.workspace === 0
                                    && root.spectrumTaskTab === 0
                                    && !root.rfSearchMode
                                    && root.sourcePanelOpen
        root.workspace = 0
        root.spectrumTaskTab = 0
        root.rfSearchMode = false
        root.sourcePanelOpen = !optionsAlreadyVisible
        return
    }
    root.workspace = item.workspace
    if (item.task >= 0) root.spectrumTaskTab = item.task
}
