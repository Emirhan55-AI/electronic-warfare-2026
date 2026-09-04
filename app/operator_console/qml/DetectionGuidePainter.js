.pragma library

function paintDetectionGuides(root, operatorViewModel, ctx, left, top, plotWidth, plotHeight, includeCandidates) {
    var span = root.spectrumViewEnd - root.spectrumViewStart
    var markers = includeCandidates === false ? [] : operatorViewModel.detectionMarkers
    for (var i = 0; i < markers.length; i++) {
        var point = markers[i].peakNormalized
        if (point < root.spectrumViewStart || point > root.spectrumViewEnd) continue
        var bandStart = Math.max(root.spectrumViewStart, markers[i].startNormalized)
        var bandEnd = Math.min(root.spectrumViewEnd, markers[i].endNormalized)
        var bandX = left + (bandStart - root.spectrumViewStart) * plotWidth / span
        var bandWidth = Math.max(3, (bandEnd - bandStart) * plotWidth / span)
        var x = left + (point - root.spectrumViewStart) * plotWidth / span
        var stable = markers[i].verificationKey === "verified_two_lo"
        ctx.fillStyle = operatorViewModel.sourceMode === "hackrf" ? "rgba(226, 192, 141, 0.11)" : "rgba(46, 160, 67, 0.11)"
        ctx.fillRect(bandX, top, bandWidth, plotHeight)
        ctx.lineWidth = 1.5
        ctx.strokeStyle = stable ? root.success : root.warning
        ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, top + plotHeight); ctx.stroke()
        ctx.beginPath(); ctx.moveTo(x - 5, top); ctx.lineTo(x + 5, top); ctx.lineTo(x, top + 7); ctx.closePath(); ctx.fillStyle = stable ? root.success : root.warning; ctx.fill()
    }
    var selected = operatorViewModel.selectedRegionPeakNormalized
    if (operatorViewModel.selectedDetectionCurrent
            && selected >= root.spectrumViewStart && selected <= root.spectrumViewEnd) {
        var selectedX = left + (selected - root.spectrumViewStart) * plotWidth / span
        ctx.strokeStyle = root.accent
        ctx.lineWidth = 1.5
        ctx.setLineDash([])
        ctx.beginPath(); ctx.moveTo(selectedX, top); ctx.lineTo(selectedX, top + plotHeight); ctx.stroke()
        ctx.setLineDash([])
    }
    ctx.lineWidth = 1
}

function paintCoarseDetectionGuides(root, operatorViewModel, ctx, left, top, plotWidth, plotHeight) {
    var span = root.spectrumViewEnd - root.spectrumViewStart
    var markers = operatorViewModel.coarseDetectionMarkers
    for (var i = 0; i < markers.length; i++) {
        var bandStart = Math.max(root.spectrumViewStart, markers[i].startNormalized)
        var bandEnd = Math.min(root.spectrumViewEnd, markers[i].endNormalized)
        if (bandEnd < bandStart) continue
        var bandX = left + (bandStart - root.spectrumViewStart) * plotWidth / span
        var bandWidth = Math.max(3, (bandEnd - bandStart) * plotWidth / span)
        var peakX = left + (markers[i].peakNormalized - root.spectrumViewStart) * plotWidth / span
        ctx.fillStyle = "rgba(226, 192, 141, 0.08)"
        ctx.fillRect(bandX, top, bandWidth, plotHeight)
        ctx.strokeStyle = "rgba(226, 192, 141, 0.72)"
        ctx.lineWidth = 1
        ctx.setLineDash([3, 3])
        ctx.strokeRect(bandX, top, bandWidth, plotHeight)
        ctx.setLineDash([])
        if (markers[i].peakNormalized >= root.spectrumViewStart && markers[i].peakNormalized <= root.spectrumViewEnd) {
            ctx.beginPath(); ctx.moveTo(peakX, top); ctx.lineTo(peakX, top + 6); ctx.stroke()
        }
    }
}
