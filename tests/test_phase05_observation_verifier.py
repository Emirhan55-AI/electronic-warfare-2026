"""KTR-4.3 temporal/frequency observation evidence contract."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_phase05_monitoring_observation",
    ROOT / "scripts" / "verify_phase05_monitoring_observation.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_monitoring_observation_evidence_is_current_and_passed() -> None:
    document = MODULE.build_evidence()
    assert document["status"] == "passed"
    assert document["hardware_status"] == "not_exercised"
    assert document["live_hackrf_status"] == "not_exercised"
    assert MODULE.check()
