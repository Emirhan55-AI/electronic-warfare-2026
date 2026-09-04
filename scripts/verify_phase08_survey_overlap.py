"""Produce source-bound host evidence for the overlapping RX survey geometry."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.operator_console.rx_survey import (
    SURVEY_CHANNELIZER_PASSBAND_HALF_HZ,
    SURVEY_MAX_FULL_SUPPORT_HZ,
    SURVEY_RESPONSIBILITY_WIDTH_HZ,
    _verification_matches,
)


SOURCES = (
    "app/operator_console/rx_survey.py",
    "scripts/verify_phase08_survey_overlap.py",
)


def verify() -> dict:
    half_support_hz = SURVEY_MAX_FULL_SUPPORT_HZ / 2
    half_responsibility_hz = SURVEY_RESPONSIBILITY_WIDTH_HZ // 2
    offsets = range(-half_responsibility_hz, half_responsibility_hz + 1)
    checked = 0
    minimum_frame_edge_margin_bins = float("inf")
    for offset_hz in offsets:
        if abs(offset_hz) + half_support_hz > SURVEY_CHANNELIZER_PASSBAND_HALF_HZ:
            raise AssertionError("1 MHz destek kanal seçici geçiş bandından taşıyor.")
        first_bin = 2048 + (offset_hz - half_support_hz) * 4096 / 2_000_000
        final_bin = 2048 + (offset_hz + half_support_hz) * 4096 / 2_000_000
        if first_bin < 256 or final_bin >= 3840:
            raise AssertionError("İki dış detector bölgesi için çerçeve payı kalmıyor.")
        minimum_frame_edge_margin_bins = min(
            minimum_frame_edge_margin_bins,
            first_bin,
            4096 - final_bin,
        )
        checked += 1

    observation = {
        "frequency_hz": 100_000_000.0,
        "peak_frequency_hz": 99_550_000.0,
        "lower_frequency_hz": 99_500_000.0,
        "upper_frequency_hz": 100_500_000.0,
    }
    broad_peak_moved_match = _verification_matches(
        observation,
        99_500_000.0,
        100_500_000.0,
        100_000_000.0,
        100_450_000.0,
    )
    broad_unrelated_rejected = not _verification_matches(
        observation,
        101_000_000.0,
        102_000_000.0,
        101_500_000.0,
        101_950_000.0,
    )
    narrow_moved_rejected = not _verification_matches(
        {
            "frequency_hz": 100_000_000.0,
            "peak_frequency_hz": 100_000_000.0,
            "lower_frequency_hz": 99_997_500.0,
            "upper_frequency_hz": 100_002_500.0,
        },
        100_097_500.0,
        100_102_500.0,
        100_100_000.0,
        100_100_000.0,
    )
    if not (broad_peak_moved_match and broad_unrelated_rejected and narrow_moved_rejected):
        raise AssertionError("Bağımsız ayar eşleştirme kapısı geçmedi.")

    return {
        "schema": "phase08-survey-overlap-v1",
        "status": "pass",
        "scope": "host_only_geometry_and_matching_not_rf_or_fpga_acceptance",
        "transmit_enabled": False,
        "profile": {
            "responsibility_width_hz": SURVEY_RESPONSIBILITY_WIDTH_HZ,
            "detector_window_hz": 2_000_000,
            "channelizer_passband_half_hz": SURVEY_CHANNELIZER_PASSBAND_HALF_HZ,
            "maximum_full_support_hz": SURVEY_MAX_FULL_SUPPORT_HZ,
        },
        "geometry": {
            "integer_center_offsets_checked": checked,
            "maximum_absolute_center_offset_hz": half_responsibility_hz,
            "minimum_frame_edge_margin_bins": minimum_frame_edge_margin_bins,
            "full_support_inside_passband": True,
            "two_detector_flank_regions_fit_in_frame": True,
        },
        "independent_retune_matching": {
            "broad_support_matches_after_900khz_peak_move": broad_peak_moved_match,
            "unrelated_broad_support_rejected": broad_unrelated_rejected,
            "narrow_100khz_peak_move_rejected": narrow_moved_rejected,
        },
        "limits": [
            "Bu rapor sentetik geometri ve host eşleştirme kanıtıdır.",
            "Kanal seçici dalga şekli, RF algılama olasılığı ve yanlış alarm ölçülmemiştir.",
            "Bütün 2 MHz pencereyi dolduran yayın bu yöntemle çözülmüş sayılmaz.",
            "Güncel SystemVerilog bitstream ve fiziksel ZedBoard kabulü bu raporun dışındadır.",
        ],
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in SOURCES
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Örtüşen RX tarama geometrisini doğrula")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"status": report["status"], **report["geometry"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
