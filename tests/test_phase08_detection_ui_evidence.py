from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("phase08_detection_ui", ROOT / "scripts/verify_phase08_detection_ui.py")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)
REPORT = ROOT / "results/evidence/phase08/detection-ui-decoupling.json"


def test_detection_ui_observation_reproduces() -> None:
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    assert payload == VERIFY.summarize(REPORT.with_suffix(".zip"))
    assert payload["status"] == "capture_decoupling_observed"
    assert payload["baseline"]["display_50_usb_overrun_failures"] == 1
    assert payload["decoupled_capture"]["completed_frames"] >= 32_768
    assert payload["decoupled_capture"]["usb_overrun_failures"] == 0
    assert payload["decoupled_capture"]["cancelled_runs"] == 1
    assert payload["phase08_complete"] is False


def test_usb_failure_cannot_be_hidden(tmp_path: Path) -> None:
    altered = tmp_path / "altered.zip"
    with zipfile.ZipFile(REPORT.with_suffix(".zip")) as source, zipfile.ZipFile(altered, "w") as target:
        for name in source.namelist():
            raw = source.read(name)
            if name == "baseline/run-01.json":
                run = json.loads(raw)
                run["status"] = "passed"
                raw = json.dumps(run).encode()
            target.writestr(name, raw)
    with pytest.raises(ValueError):
        VERIFY.summarize(altered)
