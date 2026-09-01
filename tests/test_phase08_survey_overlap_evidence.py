import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "results/evidence/phase08/survey-overlap-v1.json"


def test_survey_overlap_evidence_is_current_and_bounded():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["schema"] == "phase08-survey-overlap-v1"
    assert report["status"] == "pass"
    assert report["transmit_enabled"] is False
    assert report["scope"] == "host_only_geometry_and_matching_not_rf_or_fpga_acceptance"
    assert report["profile"] == {
        "responsibility_width_hz": 600_000,
        "detector_window_hz": 2_000_000,
        "channelizer_passband_half_hz": 800_000,
        "maximum_full_support_hz": 1_000_000,
    }
    assert report["geometry"]["integer_center_offsets_checked"] == 600_001
    assert report["geometry"]["full_support_inside_passband"] is True
    assert report["geometry"]["two_detector_flank_regions_fit_in_frame"] is True
    assert report["independent_retune_matching"] == {
        "broad_support_matches_after_900khz_peak_move": True,
        "unrelated_broad_support_rejected": True,
        "narrow_100khz_peak_move_rejected": True,
    }
    assert any("2 MHz" in item for item in report["limits"])
    for name, digest in report["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
