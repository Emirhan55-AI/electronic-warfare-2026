"""KTR-4.2 tanısı özgün ölçümü korur ve değiştirilmiş kanıtı reddeder."""
import hashlib
import json

import pytest

from algorithms.parameters import AnalysisSpan, MeasurementCandidate, MeasurementContext, MeasurementIntent
from algorithms.spectrum import SpectrumConfig
from app.operator_console.measurement_record import measure_and_record, utc_now
from scripts.diagnose_parameter_bench import diagnose, run
from scripts.validate_parameter_bench import signal


def test_diagnostic_matches_product_and_preserves_record(tmp_path):
    frames, _ = signal("CW", 73002, 12)
    candidate = MeasurementCandidate(1, 1, 2207, 2209)
    context = MeasurementContext(1, 1, 1, 1, 1, (True,) * 4, (candidate,))
    intent = MeasurementIntent(1, 1, 1, 1, 1, 0, AnalysisSpan(1978, 2438, "operator_adjusted", 1), context)
    saved = measure_and_record(intent, frames, sample_rate_hz=2_000_000,
        center_frequency_hz=700_000_000, spectrum_config=SpectrumConfig(),
        source={"kind": "synthetic_diagnostic"}, requested_utc=utc_now(), directory=tmp_path)
    before = saved.path.read_bytes()
    diagnostic = diagnose(saved.path)
    assert saved.path.read_bytes() == before
    assert diagnostic["record_sha256"] == hashlib.sha256(before).hexdigest()
    assert diagnostic["domain"]["value"] == saved.result.signal_domain.value
    assert diagnostic["domain"]["state"] == saved.result.signal_domain.state
    assert diagnostic["carrier_state"] == "not_observed"
    assert not all(diagnostic["carrier_gates"].values())


def test_report_digest_mismatch_does_not_publish_diagnostic(tmp_path):
    (tmp_path / "sample.zip").write_bytes(b"altered")
    (tmp_path / "report.json").write_text(json.dumps({"measurements": [
        {"record": "sample.zip", "sha256": "0" * 64, "family": "CW"}]}), encoding="utf-8")
    output = tmp_path / "diagnostics.json"
    with pytest.raises(ValueError, match="özetle eşleşmiyor"):
        run(tmp_path, output)
    assert not output.exists()
