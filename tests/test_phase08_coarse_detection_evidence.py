import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/coarse-rx-detection-v1.json"


def test_coarse_rx_detection_evidence_is_source_bound_and_bounded() -> None:
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["scope"] == "host_only_8msps_coarse_proposal"
    assert report["transmit_enabled"] is False
    assert report["fpga_confirmation"] is False
    summaries = {item["family"]: item for item in report["summaries"]}
    for width in (100_000, 500_000, 1_000_000, 2_000_000, 4_000_000):
        row = summaries[f"signal_{width}"]
        assert row["recovered_at_least_80_percent"] == row["frames"] == 32
    assert summaries["signal_6000000"]["status"] == "characterized_not_guaranteed"
    assert 0 < summaries["signal_6000000"]["recovered_at_least_80_percent"] < 32
    for family in ("noise_flat", "noise_slope_12db", "noise_step_12db"):
        assert summaries[family]["frames_with_false_candidate"] == 0
    assert summaries["signal_8000000"]["status"] == "known_limit_passed"
    assert summaries["signal_8000000"]["frames_with_candidate"] == 0
    for name, expected in report["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
