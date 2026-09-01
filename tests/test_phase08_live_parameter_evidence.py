from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "phase08_live_parameter",
    ROOT / "scripts/verify_phase08_live_parameter.py",
)
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)
REPORT = ROOT / "results/evidence/phase08/live-parameter-functional.json"


def test_archived_live_parameter_run_reproduces_the_summary() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report == VERIFY.summarize(REPORT.with_suffix(".zip"))
    assert report["status"] == "functional_binding_passed"
    assert report["accuracy_proven"] is False
    assert len(report["measurement_sequence_numbers"]) == 4
    assert report["parameter_field_count"] == 9


def test_tampered_measurement_window_is_rejected(tmp_path: Path) -> None:
    altered = tmp_path / "altered.zip"
    with zipfile.ZipFile(REPORT.with_suffix(".zip")) as source, zipfile.ZipFile(altered, "w") as target:
        target.writestr("run.json", source.read("run.json"))
        ui = json.loads(source.read("ui-state.json"))
        ui["measurement_window"][2]["sequence_number"] += 5
        target.writestr("ui-state.json", json.dumps(ui))
    with pytest.raises(ValueError, match="sıra numaraları"):
        VERIFY.summarize(altered)
