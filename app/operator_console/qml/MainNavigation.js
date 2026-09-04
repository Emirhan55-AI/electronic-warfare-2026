.pragma library

function activateWorkspace(root, item) {
    if (item.workspace === 0 && item.task === 0) {
        var optionsAlreadyVisible = root.operatingDomain === "ED"
                                    && root.workspace === 0
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

function etBadgeState(operatorViewModel) {
    if (operatorViewModel.etStatus === "ÇALIŞIYOR") return "Çalışıyor"
    if (operatorViewModel.etStatus === "HATA") return "Hata"
    return "Hazır"
}

function etTaskName(operatorViewModel) {
    if (operatorViewModel.etTask === "continuous") return "Sürekli Karıştırma"
    if (operatorViewModel.etTask === "interleaved") return "Arabakışlı Karıştırma"
    if (operatorViewModel.etTask === "analog") return "Analog Telsiz Aldatma"
    return "GPS L1 Senaryosu"
}
