"""KTR-4.1: conservative presentation grouping; raw RF evidence is unchanged."""

BIN_HZ = 2_000_000 / 4096


def signal_fields(item, window_index):
    verification = item.get("verification") or {}
    return {
        "signalDetected": bool(verification),
        "peakHz": float(item.get("peak_frequency_hz", item["frequency_hz"])),
        "verificationPeakHz": float(verification.get("peak_frequency_hz", item["frequency_hz"])),
        "bandwidthHz": float(item.get("bandwidth_hz", 0)),
        "windowIndex": window_index,
        "memberIds": [item["key"]],
        "rangeText": (
            f"{item['lower_frequency_hz'] / 1e6:.3f}–{item['upper_frequency_hz'] / 1e6:.3f} MHz"
            if float(item.get("bandwidth_hz", 0)) >= 50_000
            and "lower_frequency_hz" in item and "upper_frequency_hz" in item else ""
        ),
    }


def merge_signal_rows(newest, previous):
    """Merge only adjacent-window narrow lines agreeing in both tunings.

    Fixed anchors prevent transitive frequency drift. Broad emissions, energy
    regions, and separate lines in one window remain separate. No emitter
    identity or RF acceptance is inferred from grouping.
    """
    rows = [dict(row) for row in previous]
    for incoming in newest:
        match = None
        if incoming.get("signalDetected") and 0 < incoming.get("bandwidthHz", 0) < 50_000:
            match = next((row for row in rows
                if row.get("signalDetected")
                and row.get("evidenceKey") == incoming.get("evidenceKey")
                and 0 < row.get("bandwidthHz", 0) < 50_000
                and incoming["windowIndex"] - row["windowIndex"] == 1
                and abs(row["peakHz"] - incoming["peakHz"]) <= 2 * BIN_HZ
                and abs(row["verificationPeakHz"] - incoming["verificationPeakHz"]) <= 2 * BIN_HZ
            ), None)
        if match is None:
            rows.append(dict(incoming))
        else:
            match["memberIds"] = list(dict.fromkeys(match["memberIds"] + incoming["memberIds"]))
            match["latestWindow"] = True
            match["windowIndex"] = incoming["windowIndex"]
            match["qualityScore"] = max(match["qualityScore"], incoming["qualityScore"])
    return rows
