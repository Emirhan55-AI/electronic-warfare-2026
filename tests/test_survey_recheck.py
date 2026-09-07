import json
import threading
from pathlib import Path
from types import SimpleNamespace

from app.operator_console.survey_recheck import recheck_signals


def test_recheck_separates_absence_from_capture_failure(tmp_path):
    items = [{"key": str(i), "frequency_hz": 950e6 + i * 1e6} for i in range(3)]
    def verify(item):
        if item["key"] == "0":
            return {"verification": {"frequency_hz": item["frequency_hz"]}}
        if item["key"] == "1":
            return None
        raise RuntimeError("capture failed")
    survey = SimpleNamespace(_cancel=threading.Event(), _verify_observation=verify)
    source = tmp_path / "source.jsonl"
    source.write_text("original evidence")
    updates = []
    destination = tmp_path / "recheck.jsonl"
    assert recheck_signals(survey, items, destination, source, updates.append) == "completed"
    assert [u["state"] for u in updates] == ["seen", "not_seen", "error"]
    saved = [json.loads(line) for line in destination.read_text().splitlines()]
    assert len(saved) == 5 and saved[0]["source_audit_sha256"]
    assert source.read_text() == "original evidence"


def test_cancel_during_verification_never_reports_signal_absence(tmp_path):
    event = threading.Event()
    def verify(item):
        event.set()
        return None
    survey = SimpleNamespace(_cancel=event, _verify_observation=verify)
    source = tmp_path / "source"
    source.write_text("evidence")
    updates = []
    state = recheck_signals(survey, [{"key": "a", "frequency_hz": 953e6}],
                            tmp_path / "result", source, updates.append)
    assert state == "cancelled" and updates == []


def test_existing_recheck_evidence_is_not_overwritten(tmp_path):
    import pytest
    destination = tmp_path / "result"
    destination.write_text("preserve")
    with pytest.raises(FileExistsError):
        recheck_signals(None, [], destination, tmp_path / "source", lambda x: None)
    assert destination.read_text() == "preserve"


def test_controller_finishes_only_after_automatic_recheck(tmp_path):
    import time
    from PySide6.QtGui import QGuiApplication
    from app.operator_console.survey_controller import SurveyController
    from app.operator_console.rx_survey import SurveyConfig, SurveyResult
    app = QGuiApplication.instance() or QGuiApplication([])
    pending = []
    pool = SimpleNamespace(start=pending.append)
    def factory(*args):
        event = threading.Event()
        return SimpleNamespace(_cancel=event, cancel=event.set,
            _verify_observation=lambda item: {"verification": {"frequency_hz": item["frequency_hz"]}})
    controller = SurveyController(factory=factory)
    source = tmp_path / "source.jsonl"
    source.write_text("source evidence")
    controller._audit = str(source)
    controller._serial = "0" * 32
    controller._recheck_pool = pool
    controller._config = SurveyConfig(952_600_000, 953_200_000)
    controller._started = time.monotonic()
    controller._current_observations = [{"key": "a", "frequency_hz": 953e6}]
    controller._rows = [{"eventId": "a", "frequencyHz": 953e6, "signalDetected": True}]
    completed = []
    controller.finished.connect(completed.append)
    controller._complete(SurveyResult("completed", 1, 1, 0, .5, str(source)))
    assert controller.running and controller.rechecking and completed == []
    controller._good = 500
    assert "kalan" not in controller.timeText
    pending[0].run()
    app.processEvents()
    assert completed == ["completed"] and not controller.running
    assert controller._rows[0]["recheckStatus"] == "Tekrar görüldü"
