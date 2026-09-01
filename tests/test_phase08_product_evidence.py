from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("phase08_product_evidence", ROOT / "scripts/verify_phase08_product.py")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)
REPORT = ROOT / "results/evidence/phase08/product-live-acceptance.json"


def test_archived_physical_runs_reproduce_the_summary() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report == VERIFY.summarize(REPORT.with_suffix(".zip"))
    assert report["cohort_completed_frames"] == 20480
    assert report["phase08_complete"] is False
    assert report["runs"][0]["error_code"] == "iq_saturation"
    for current, archived in (("live-completed.png", "02-live-completed.png"), ("clipped-rejected.png", "01-clipped-rejected.png")):
        assert hashlib.sha256((REPORT.parent / current).read_bytes()).hexdigest() == report["screenshot_sha256"][archived]


@pytest.mark.parametrize("fault", ["usb", "crc", "dma", "snapshot", "remove_negative"])
def test_altered_physical_evidence_is_rejected(tmp_path: Path, fault: str) -> None:
    altered = tmp_path / "altered.zip"
    with zipfile.ZipFile(REPORT.with_suffix(".zip")) as original, zipfile.ZipFile(altered, "w") as output:
        for name in original.namelist():
            raw = original.read(name)
            if name == "run-01.json" and fault == "remove_negative":
                continue
            if name == "run-02.json":
                run = json.loads(raw)
                if fault == "usb":
                    run["result"]["hackrf_statistics"]["overruns"] = 1
                elif fault == "crc":
                    run["result"]["transport_statistics"]["crc_errors"] = 1
                elif fault == "dma":
                    run["snapshots"][0]["response"]["dma_status_flags"] = 0
                elif fault == "snapshot":
                    run["snapshots"].pop()
                raw = json.dumps(run).encode("utf-8")
            output.writestr(name, raw)
    with pytest.raises(ValueError):
        VERIFY.summarize(altered)
