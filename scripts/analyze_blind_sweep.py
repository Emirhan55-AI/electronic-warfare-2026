"""Compare paired HackRF sweep CSV files without using transmitter frequency truth."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np


def _load(path: Path, lower_hz: int, upper_hz: int) -> dict[int, list[float]]:
    bins: dict[int, list[float]] = defaultdict(list)
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.reader(stream):
            if len(row) < 7:
                continue
            row_lower = float(row[2])
            bin_width = float(row[4])
            for index, value in enumerate(row[6:]):
                frequency = int(round(row_lower + index * bin_width))
                if lower_hz <= frequency <= upper_hz:
                    bins[frequency].append(float(value))
    return dict(bins)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _cluster(rows: list[dict], maximum_gap_hz: float) -> list[dict]:
    groups: list[list[dict]] = []
    for row in rows:
        if not groups or row["frequency_hz"] - groups[-1][-1]["frequency_hz"] > maximum_gap_hz:
            groups.append([row])
        else:
            groups[-1].append(row)
    output = []
    for group in groups:
        peak = max(group, key=lambda item: (item["median_delta_db"], item["frequency_hz"]))
        output.append({
            "lower_hz": group[0]["frequency_hz"],
            "upper_hz": group[-1]["frequency_hz"],
            "peak_frequency_hz": peak["frequency_hz"],
            "peak_median_delta_db": peak["median_delta_db"],
            "peak_off_median_db": peak["off_median_db"],
            "peak_on_median_db": peak["on_median_db"],
            "positive_repeats": peak["positive_repeats"],
            "paired_repeats": peak["paired_repeats"],
            "bin_count": len(group),
        })
    return sorted(output, key=lambda item: item["peak_median_delta_db"], reverse=True)


def analyze(off_path: Path, on_path: Path, lower_hz: int, upper_hz: int) -> dict:
    off = _load(off_path, lower_hz, upper_hz)
    on = _load(on_path, lower_hz, upper_hz)
    rows = []
    for frequency in sorted(set(off) & set(on)):
        paired = min(len(off[frequency]), len(on[frequency]))
        if paired == 0:
            continue
        off_values = np.asarray(off[frequency][:paired], dtype=np.float64)
        on_values = np.asarray(on[frequency][:paired], dtype=np.float64)
        deltas = on_values - off_values
        rows.append({
            "frequency_hz": frequency,
            "off_median_db": round(float(np.median(off_values)), 4),
            "on_median_db": round(float(np.median(on_values)), 4),
            "median_delta_db": round(float(np.median(deltas)), 4),
            "positive_repeats": int(np.count_nonzero(deltas >= 6.0)),
            "paired_repeats": paired,
        })
    qualified = [
        row for row in rows
        if row["median_delta_db"] >= 6.0
        and row["positive_repeats"] >= max(2, int(np.ceil(0.75 * row["paired_repeats"])))
    ]
    widths = np.diff([row["frequency_hz"] for row in rows])
    nominal_width = float(np.median(widths[widths > 0])) if np.any(widths > 0) else 100_000.0
    return {
        "schema": "baz.blind-sweep-comparison.v1",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "scope_hz": [lower_hz, upper_hz],
        "decision_rule": "median TX-on minus TX-off >= 6 dB and >=75% paired repeats >= 6 dB",
        "bin_count": len(rows),
        "nominal_bin_spacing_hz": nominal_width,
        "candidate_clusters": _cluster(qualified, 2.1 * nominal_width),
        "top_deltas": sorted(rows, key=lambda item: item["median_delta_db"], reverse=True)[:20],
        "inputs": {
            "tx_off": {"path": str(off_path), "sha256": _sha256(off_path)},
            "tx_on": {"path": str(on_path), "sha256": _sha256(on_path)},
        },
        "limitations": [
            "TX durumu operatör beyanıdır.",
            "Sonuç kalibrasyonsuz göreli dB karşılaştırmasıdır; verici kimliği veya Pd/Pfa kabulü değildir.",
            "Hızlı süpürme aday frekansı üretir; sabit bant iki-LO doğrulaması ayrıca gerekir.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--off", type=Path, required=True)
    parser.add_argument("--on", type=Path, required=True)
    parser.add_argument("--lower-hz", type=int, required=True)
    parser.add_argument("--upper-hz", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.off, args.on, args.lower_hz, args.upper_hz)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
