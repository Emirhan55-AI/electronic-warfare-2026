from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "phase08_endurance",
    ROOT / "scripts/verify_phase08_endurance.py",
)
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)
REPORT = ROOT / "results/evidence/phase08/live-rx-endurance-v2.json"


def test_archived_endurance_run_reproduces_the_summary() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report == VERIFY.summarize(REPORT.with_suffix(".zip"))
    assert report["frame_count"] == 439_453
    assert report["usb_overruns"] == 0
    assert report["sequence_errors"] == 0


def test_endurance_configuration_accepts_the_bounded_maximum() -> None:
    config = VERIFY.LiveEDConfiguration(
        output_center_frequency_hz=104_650_000,
        device_serial=VERIFY.SERIAL,
        frame_count=878_906,
        display_interval_frames=VERIFY.PROGRESS_INTERVAL_FRAMES,
    )
    assert config.frame_count == 878_906
    assert config.display_interval_frames == 4_096


def test_endurance_configuration_rejects_an_unbounded_run() -> None:
    with pytest.raises(Exception, match="kare sayısı"):
        VERIFY.LiveEDConfiguration(
            output_center_frequency_hz=104_650_000,
            device_serial=VERIFY.SERIAL,
            frame_count=878_907,
        )


def test_tampered_endurance_archive_is_rejected(tmp_path: Path) -> None:
    altered = tmp_path / "altered.zip"
    with zipfile.ZipFile(REPORT.with_suffix(".zip")) as source, zipfile.ZipFile(altered, "w") as target:
        run = json.loads(source.read("run.json"))
        run["result"]["transport_statistics"]["sequence_errors"] = 1
        target.writestr("run.json", json.dumps(run))
    with pytest.raises(ValueError, match="taşıma"):
        VERIFY.summarize(altered)
