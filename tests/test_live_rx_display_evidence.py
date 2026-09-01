"""Source-bound acceptance checks for the current physical RX display run."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

from app.operator_console.live_ed import LIVE_CAPTURE_QUEUE_CAPACITY
from scripts.measure_live_rx_display import SOURCES


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "results/evidence/phase08/live-rx-display-8msps-v2.json"
ARCHIVE = REPORT.with_suffix(".zip")


def test_current_physical_rx_display_evidence_preserves_the_open_usb_gate() -> None:
    raw_report = REPORT.read_bytes()
    report = json.loads(raw_report)
    with zipfile.ZipFile(ARCHIVE) as stored:
        library_entry = report["native_channelizer"]["archive_path"]
        assert set(stored.namelist()) == {*SOURCES, library_entry, "measurement.json"}
        # The archive is immutable physical evidence captured with Windows
        # newlines; the tracked JSON is normalized to the repository LF policy.
        assert stored.read("measurement.json").replace(b"\r\n", b"\n") == raw_report.replace(
            b"\r\n", b"\n"
        )
        assert hashlib.sha256(stored.read(library_entry)).hexdigest() == report["native_channelizer"]["sha256"]
        archived_sources = {}
        for name in SOURCES:
            archived = stored.read(name)
            assert hashlib.sha256(archived).hexdigest() == report["source_sha256"][name]
            archived_sources[name] = archived

    # Bu fiziksel koşu USB taşmasıyla kapıyı açık bırakan tarihsel bir ölçümdür.
    # Arşiv kendi kaynaklarına bağlı kalır; sonraki ürün değişiklikleri kanıtı
    # sessizce "güncel kabul" haline getirmemelidir.
    changed_since_capture = {
        name for name, archived in archived_sources.items()
        if archived != (ROOT / name).read_bytes()
    }
    assert changed_since_capture == {
        "app/operator_console/live_ed.py",
        "app/operator_console/quick_view_model.py",
        "app/operator_console/quick_application.py",
        "app/operator_console/qml/Main.qml",
        "app/operator_console/qml/RxSurveyView.qml",
        "app/operator_console/rx_survey.py",
        "app/operator_console/survey_controller.py",
        "platforms/acquisition/continuous.py",
    }

    diagnostics = report["diagnostics"]
    assert report["schema"] == "physical-rx-display-v2"
    assert report["status"] == "failed"
    assert report["transmit_enabled"] is False
    assert report["fpga_enabled"] is False
    assert report["checks"]["session_completed"] is False
    assert report["checks"]["zero_usb_overruns"] is False
    assert report["checks"]["native_cpp_channelizer_used"] is True
    assert report["checks"]["sources_unchanged_during_measurement"] is True
    assert diagnostics["completed_frames"] == report["configuration"]["frames"] == 29_297
    assert diagnostics["hackrf_statistics"]["overruns"] == 3
    assert diagnostics["hackrf_statistics"]["longest_overrun_bytes"] == 7_328
    assert diagnostics["channelizer_backend"] == "native-cpp"
    assert 0 < diagnostics["capture_queue_high_watermark"] <= LIVE_CAPTURE_QUEUE_CAPACITY
    assert report["fresh_updates_per_second"] >= 30
    assert report["render_interval_p95_ms"] <= 50
    assert report["host_receive_to_present_p95_ms"] <= 150
    # Fail-closed completion clears the graph instead of leaving stale RF data.
    assert report["display"]["bins"] == 0
    assert report["display"]["fpga_processing_sample_rate_hz"] == 2_000_000
