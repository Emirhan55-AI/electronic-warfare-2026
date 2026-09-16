"""KTR-4.1: conservative presentation grouping; raw RF evidence is unchanged."""

import math

BIN_HZ = 2_000_000 / 4096


def _signal_difference_db(item):
    """Return the measured signal-to-noise difference when it is available.

    The receive survey does not have a calibrated absolute power value for
    every candidate.  The FPGA event and the integrated RX path both provide
    a comparable peak-to-noise value, so the UI uses that value only to set
    review order and labels it accordingly.
    """
    event = item.get("event") or {}
    if isinstance(event, dict):
        try:
            peak = float(event.get("peak_power", 0.0))
            noise = float(event.get("noise_power", 0.0))
        except (TypeError, ValueError):
            peak = noise = 0.0
        if peak > 0.0 and noise > 0.0:
            value = 10.0 * math.log10(peak / noise)
            if math.isfinite(value):
                return value
    try:
        value = float(item.get("peak_to_noise_db", float("nan")))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _format_signal_difference(value):
    if value is None or not math.isfinite(value):
        return ""
    return f"Sinyal farkı: {value:.1f} dB".replace(".", ",")


def _format_detection_range(item):
    """Format every measured candidate span at a useful, honest precision."""
    try:
        lower = float(item["lower_frequency_hz"])
        upper = float(item["upper_frequency_hz"])
    except (KeyError, TypeError, ValueError):
        return ""
    width = upper - lower
    if not all(math.isfinite(value) for value in (lower, upper, width)) or width <= 0:
        return ""
    # Three decimals match the frequency labels. Only sub-kHz spans need one
    # extra digit so their two edges do not collapse to one MHz value.
    decimals = 3 if width >= 1_000 else 4
    lower_text = f"{lower / 1e6:.{decimals}f}".replace(".", ",")
    upper_text = f"{upper / 1e6:.{decimals}f}".replace(".", ",")
    return f"{lower_text}–{upper_text} MHz"


def signal_fields(item, window_index, possible_frames=120):
    verification = item.get("verification") or {}
    width = float(item.get("bandwidth_hz", 0))
    verified_width = float(verification.get("bandwidth_hz", 0))
    count = int(item.get("observed_frames", 0))
    compatible = bool(verification) and count <= possible_frames
    if width >= 125_488.28125:
        overlap = max(0, min(item.get("upper_frequency_hz", 0), verification.get("upper_frequency_hz", 0))
                      - max(item.get("lower_frequency_hz", 0), verification.get("lower_frequency_hz", 0)))
        compatible = compatible and overlap >= .25 * max(width, verified_width)
    signal_difference_db = _signal_difference_db(item)
    return {
        "signalDetected": compatible,
        "reviewReason": ("Ölçüm sayısı tutarsız; bu kayda güvenmeyin." if count > possible_frames else
                         "İkinci ölçüm aynı aralığı göstermedi; yeniden ölçün." if verification and not compatible else
                         "Henüz ikinci ölçüm yapılmadı; yeniden ölçün." if not verification else ""),
        "continuity": min(1., count / max(1, possible_frames), float(verification.get("observed_frames", 0)) / 40),
        "peakHz": float(item.get("peak_frequency_hz", item["frequency_hz"])),
        "verificationPeakHz": float(verification.get("peak_frequency_hz", item["frequency_hz"])),
        "bandwidthHz": float(item.get("bandwidth_hz", 0)),
        "windowIndex": window_index,
        "memberIds": [item["key"]],
        "rangeText": _format_detection_range(item),
        "signalDifferenceDb": signal_difference_db,
        "signalDifferenceText": _format_signal_difference(signal_difference_db),
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
            if incoming.get("signalDifferenceDb") is not None:
                match["signalDifferenceDb"] = incoming["signalDifferenceDb"]
                match["signalDifferenceText"] = incoming.get("signalDifferenceText", "")
    return rows


GROUPS = (("verified", "Tekrar doğrulanan adaylar"),
          ("candidate", "Tekrar ölçülmesi gerekenler"),
          ("suspect", "Alıcı etkisi olabilecekler"))

GROUP_DESCRIPTIONS = {
    "verified": "İki ayrı alımda görüldü; önce bunları inceleyin. Aynı grupta sinyal farkı yüksek olanlar üstte.",
    "candidate": "Tek ölçümde bulundu; yayın olduğu henüz belli değil. Sinyal farkı yüksek olanlar üstte; zayıf kayıtlar da listede kalır.",
    "suspect": "Alıcı kaynaklı olabilir; yayın olarak kabul etmeyin.",
}


def grouped_signal_rows(rows, expanded, *, preserve_order=False):
    """Presentation-only suspicion; retain every record and its original key.

    Three distinct narrow lines near 40 MHz harmonics nominate a family, not
    confirmed interference. A real emission at a family frequency stays available.
    """
    def harmonic(row):
        frequency = float(row.get("frequencyHz", 0))
        return (0 < row.get("bandwidthHz", 0) < 50_000 and frequency >= 40e6
                and abs(frequency - round(frequency / 40e6) * 40e6) <= 10_000)
    family = {round(row["frequencyHz"] / 40e6) for row in rows if harmonic(row)}
    groups = {key: [] for key, _ in GROUPS}
    for row in rows:
        # A family can only be judged after the scan has settled. Moving an
        # already visible row between groups during a live scan makes the card
        # appear to vanish, even though the underlying observation still exists.
        suspect = not preserve_order and len(family) >= 3 and harmonic(row)
        stale = row.get("recheckState") in {"not_seen", "error"}
        key = "suspect" if suspect else "verified" if row.get("signalDetected") and not stale else "candidate"
        reason = ("Düzenli aralıklı izler; alıcı kaynaklı olabilir. Yayın olarak kabul etmeyin."
                  if suspect else row.get("recheckStatus", "") if stale else row.get("reviewReason", ""))
        if stale:
            status_text = ("Son kontrolde tekrar görülmedi; yeniden ölçün."
                           if row.get("recheckState") == "not_seen"
                           else "Kontrol tamamlanamadı; yeniden ölçün.")
        elif key == "verified":
            status_text = "Aynı frekans tekrar görüldü; önce bunu inceleyin."
        elif key == "suspect":
            status_text = "Alıcı kaynaklı olabilir; yayın olarak kabul etmeyin."
        else:
            status_text = "Tekrar ölçülmeli; henüz kesin değil."
        groups[key].append({**row, "isHeader": False, "groupKey": key,
                            "reviewReason": reason, "statusText": status_text})
    result = []
    for key, title in GROUPS:
        def sort_key(row):
            try:
                signal_difference = float(row.get("signalDifferenceDb"))
            except (TypeError, ValueError):
                signal_difference = float("nan")
            has_signal_difference = math.isfinite(signal_difference)
            try:
                continuity = float(row.get("continuity", 0))
            except (TypeError, ValueError):
                continuity = 0.0
            try:
                quality_score = float(row.get("qualityScore", 0))
            except (TypeError, ValueError):
                quality_score = 0.0
            return (
                not has_signal_difference,
                -signal_difference if has_signal_difference else 0.0,
                -continuity,
                -quality_score,
                float(row["frequencyHz"]),
            )

        members = sorted(
            groups[key],
            key=(
                (lambda row: (int(row.get("displayOrder", 1 << 30)), float(row["frequencyHz"])))
                if preserve_order
                else sort_key
            ),
        )
        result.append({"eventId": "group:" + key, "isHeader": True, "groupKey": key,
                       "groupTitle": title, "groupDescription": GROUP_DESCRIPTIONS[key],
                       "groupCount": len(members), "expanded": key in expanded})
        if key in expanded:
            result.extend(members)
    return result
