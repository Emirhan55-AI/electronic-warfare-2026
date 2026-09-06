"""KTR-4.1 / KTR-4.1-OPS-B0 gerçek GUI+RX ham arşivini salt okunur denetler.

Arşiv bütünlüğü ile ölçüm başarısı ayrıdır. Güncel kaynak veya RF kabulü üretmez.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

import numpy as np


def summarize(run):
    """Kayıtlı passed/checks alanlarına güvenmeden ham ölçümden sonucu çıkarır."""
    sessions = run.get("sessions", [])
    observation = sessions[0] if len(sessions) == 1 else {}
    result = observation.get("result", {})
    rx = observation.get("rx") or {}
    transport = observation.get("transport") or {}
    frames = run.get("configuration", {}).get("frame_count", 0)
    presented = run.get("presented", [])
    health = run.get("health", [])
    elapsed = health[-1][0] if health else 0
    valid_samples = bool(presented) and all(
        len(row) == 3 and all(np.isfinite(x) for x in row) and row[2] >= 0
        for row in presented)
    ordered_samples = valid_samples and all(
        a[0] < b[0] and a[1] < b[1] for a, b in zip(presented, presented[1:]))
    intervals = np.diff([r[1] for r in presented]) * 1000 if valid_samples else []
    p95_interval = float(np.percentile(intervals, 95)) if len(intervals) else None
    p95_age = float(np.percentile([r[2] for r in presented], 95)) if valid_samples else None
    rate = len(presented) / elapsed if elapsed > 0 else 0
    gaps = ([presented[0][1]] + list(np.diff([r[1] for r in presented])) +
            [elapsed-presented[-1][1]]) if ordered_samples else []
    final_stats = re.search(r"Transfer statistics:.*?(\d+) overruns, longest (\d+) bytes",
                            rx.get("stderr_text", ""), re.S)
    checks = {
        "single_successful_real_fpga_session": len(sessions) == 1 and result.get("fpga_enabled") is True
            and run.get("fpga_response_observed") is True and not observation.get("error"),
        "complete_frame_and_byte_counts": frames > 0
            and result.get("completed_frames") == rx.get("frames_received")
            == transport.get("frames_sent") == transport.get("frames_received") == frames
            and rx.get("bytes_received") == frames * 32768,
        "zero_usb_overruns_in_raw_final_statistics": final_stats is not None
            and tuple(map(int, final_stats.groups())) == (0, 0)
            and rx.get("overruns") == rx.get("longest_overrun_bytes") == rx.get("process_returncode") == 0,
        "zero_transport_errors": all(transport.get(k) == 0 for k in ("crc_errors", "sequence_errors", "queue_drops"))
            and transport.get("last_error") is None,
        "no_iq_clipping": result.get("input_saturated_components") == result.get("output_saturated_components") == 0,
        "complete_visible_measurement": bool(health) and all(r[3] and r[4] for r in health)
            and elapsed >= frames * 4096 / 2e6 * .95,
        "ordered_real_presentations": bool(ordered_samples) and result.get("preview_frames", 0) > 0,
        "full_session_display_rate_at_least_30hz": rate >= 30,
        "no_presentation_gap_over_one_second": bool(gaps) and min(gaps) >= 0 and max(gaps) <= 1,
        "presentation_interval_p95_at_most_50ms": p95_interval is not None and p95_interval <= 50,
        "rx_age_p95_at_most_150ms": p95_age is not None and p95_age <= 150,
        "no_timeout_or_ui_error": not run.get("timed_out") and not run.get("ui_error")
            and not run.get("measurement_error"),
        "source_stability_observed": run.get("checks", {}).get("source_and_native_unchanged") is True,
    }
    checks = {name: bool(value) for name, value in checks.items()}
    return {"measurement_passed": all(checks.values()), "checks": checks,
            "completed_frames": result.get("completed_frames", observation.get("diagnostics", {}).get("completed_frames")),
            "usb_overruns": rx.get("overruns"), "full_session_display_hz": rate,
            "presentation_interval_p95_ms": p95_interval, "rx_age_p95_ms": p95_age,
            "maximum_presentation_gap_seconds": max(gaps) if gaps else None,
            "fpga_image_identity_verified": bool(run.get("board", {}).get("running_bitstream_sha256")),
            "ST06_complete": False, "rf_accuracy_acceptance": False}


def verify(path):
    with zipfile.ZipFile(path) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("Arşivde yinelenen dosya adı var.")
        if archive.testzip() is not None:
            raise ValueError("Arşiv CRC bütünlüğü başarısız.")
        run = json.loads(archive.read("measurement.json"))
        if run.get("schema") != "live-gui-fpga-observation-v1":
            raise ValueError("Beklenmeyen ölçüm şeması.")
        for name, digest in run["source_sha256"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError("Arşiv kaynak özeti uyuşmuyor: " + name)
        native = [n for n in archive.namelist() if n.startswith("native/")]
        if len(native) != 1 or hashlib.sha256(archive.read(native[0])).hexdigest() != run["native_sha256"]:
            raise ValueError("Yerel kanal seçici özeti uyuşmuyor.")
        if json.loads(archive.read("board.json")) != run["board"]:
            raise ValueError("Kart kaydı uyuşmuyor.")
    return {"archive_integrity": "passed", "scope": "archived_observation_not_current_source_acceptance",
            **summarize(run)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    result = verify(args.archive)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # Geçerli bir başarısız ölçüm arşivi başarıya çevrilmez.
    return 0 if result["measurement_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
