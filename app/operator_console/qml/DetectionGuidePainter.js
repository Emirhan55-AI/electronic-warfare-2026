.pragma library

function paintDetectionGuides(root, operatorViewModel, ctx, left, top, plotWidth, plotHeight, includeCandidates) {
    paintDetectionGuidesInRange(root, operatorViewModel, ctx, left, top, plotWidth, plotHeight,
                                includeCandidates, true, root.spectrumViewStart, root.spectrumViewEnd)
}

function paintDetectionGuidesInRange(root, operatorViewModel, ctx, left, top, plotWidth, plotHeight,
                                     includeCandidates, includeSelected, viewStart, viewEnd) {
    var span = viewEnd - viewStart
    var markers = includeCandidates === false ? [] : operatorViewModel.detectionMarkers
    for (var i = 0; i < markers.length; i++) {
        var point = markers[i].peakNormalized
        if (point < viewStart || point > viewEnd) continue
        var bandStart = Math.max(viewStart, markers[i].startNormalized)
        var bandEnd = Math.min(viewEnd, markers[i].endNormalized)
        var bandX = left + (bandStart - viewStart) * plotWidth / span
        var bandWidth = Math.max(3, (bandEnd - bandStart) * plotWidth / span)
        var x = left + (point - viewStart) * plotWidth / span
        var stable = markers[i].verificationKey === "verified_two_lo"
        ctx.fillStyle = operatorViewModel.sourceMode === "hackrf" ? "rgba(226, 192, 141, 0.11)" : "rgba(46, 160, 67, 0.11)"
        ctx.fillRect(bandX, top, bandWidth, plotHeight)
        ctx.lineWidth = 1.5
        ctx.strokeStyle = stable ? root.success : root.warning
        ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, top + plotHeight); ctx.stroke()
        ctx.beginPath(); ctx.moveTo(x - 5, top); ctx.lineTo(x + 5, top); ctx.lineTo(x, top + 7); ctx.closePath(); ctx.fillStyle = stable ? root.success : root.warning; ctx.fill()
    }
    var selected = operatorViewModel.selectedRegionPeakNormalized
    if (includeSelected !== false && operatorViewModel.selectedDetectionCurrent
            && selected >= viewStart && selected <= viewEnd) {
        var selectedX = left + (selected - viewStart) * plotWidth / span
        ctx.strokeStyle = root.accent
        ctx.lineWidth = 1.5
        ctx.setLineDash([])
        ctx.beginPath(); ctx.moveTo(selectedX, top); ctx.lineTo(selectedX, top + plotHeight); ctx.stroke()
        ctx.setLineDash([])
    }
    ctx.lineWidth = 1
}

function paintDirectionTargetGuide(root, operatorViewModel, ctx, left, top, plotWidth, plotHeight,
                                   viewStart, viewEnd) {
    var point = operatorViewModel.directionTargetPeakNormalized
    if (point < viewStart || point > viewEnd) return
    var span = viewEnd - viewStart
    var bandStart = Math.max(viewStart, operatorViewModel.directionTargetStartNormalized)
    var bandEnd = Math.min(viewEnd, operatorViewModel.directionTargetEndNormalized)
    var bandX = left + (bandStart - viewStart) * plotWidth / span
    var bandWidth = Math.max(3, (bandEnd - bandStart) * plotWidth / span)
    var x = left + (point - viewStart) * plotWidth / span
    ctx.fillStyle = "rgba(226, 192, 141, 0.11)"
    if (bandEnd >= bandStart) ctx.fillRect(bandX, top, bandWidth, plotHeight)
    ctx.strokeStyle = root.warning; ctx.fillStyle = root.warning; ctx.lineWidth = 1.5
    ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, top + plotHeight); ctx.stroke()
    ctx.beginPath(); ctx.moveTo(x - 5, top); ctx.lineTo(x + 5, top); ctx.lineTo(x, top + 7); ctx.closePath(); ctx.fill()
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
