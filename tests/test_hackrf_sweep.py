import threading

import pytest

from app.operator_console.rx_survey import RXSurvey, SurveyConfig
from platforms.acquisition.contracts import AcquisitionError
from platforms.acquisition.process import ProcessResult
from platforms.acquisition.sweep import HackRFSweepScreen, SWEEP_OPTIONS, parse_sweep_csv


def csv_data(*, missing=False, bad_power=False, transient=False):
    rows = []
    for turn in range(2):
        for lower in (101_000_000, 100_000_000):
            if missing and turn == 1 and lower == 100_000_000:
                continue
            power = ["-80"] * 40
            if lower == 100_000_000 and not (transient and turn == 1):
                power[20] = "nan" if bad_power else "-30"
            rows.append(f"2026-09-14, 10:00:0{turn}.000000, {lower}, {lower + 1_000_000}, 25000.00, 800, " + ", ".join(power))
    return ("\n".join(rows) + "\n").encode()


def test_interleaved_csv_requires_repeatability_and_uses_power_count():
    assert parse_sweep_csv(csv_data(), 100_000_000, 102_000_000) == (100_512_500,)
    assert parse_sweep_csv(csv_data(transient=True), 100_000_000, 102_000_000) == ()


@pytest.mark.parametrize("payload", [csv_data(missing=True), csv_data(bad_power=True),
                                    csv_data() + csv_data(), b"broken", b"\xff"])
def test_incomplete_or_corrupt_data_never_proves_coverage(payload):
    with pytest.raises(AcquisitionError):
        parse_sweep_csv(payload, 100_000_000, 102_000_000)


class Runner:
    def __init__(self, *, truncated=False):
        self.calls = []
        self.truncated = truncated

    def run(self, argv, **kwargs):
        self.calls.append(argv)
        if "-h" in argv:
            return ProcessResult(0, " ".join(SWEEP_OPTIONS | {"-P"}).encode(), b"", False, False)
        return ProcessResult(0, csv_data(), b"", self.truncated, False)

    def close(self):
        pass


def test_screen_is_serial_bound_finite_and_explicitly_disables_antenna_power():
    runner = Runner()
    screen = HackRFSweepScreen("hackrf_transfer", runner=runner)
    screen.executable = "hackrf_sweep"
    rows = []
    selected, evidence = screen.run(SurveyConfig(100_000_000, 102_000_000), "0" * 32, threading.Event(),
                                     lambda end, row: rows.append(row))
    assert selected == (0, 1)
    argv = runner.calls[-1]
    assert argv[argv.index("-d") + 1] == "0" * 32
    assert argv[argv.index("-N") + 1] == "2"
    assert argv[argv.index("-p") + 1] == "0"
    assert "-n" in argv and "estimate" in argv
    assert rows[0]["csv"] and evidence[0]["stdout_sha256"]
    assert "csv" not in evidence[0]


def test_truncated_output_rejected_and_pre_cancel_never_starts_process():
    runner = Runner(truncated=True)
    screen = HackRFSweepScreen("hackrf_transfer", runner=runner)
    screen.executable = "hackrf_sweep"
    with pytest.raises(AcquisitionError, match="eksik"):
        screen.run(SurveyConfig(100_000_000, 102_000_000), "0" * 32, threading.Event())
    token = threading.Event()
    token.set()
    runner.calls.clear()
    with pytest.raises(AcquisitionError):
        screen.run(SurveyConfig(), "0" * 32, token)
    assert runner.calls == []


class Screen:
    def __init__(self, executable):
        pass

    def run(self, config, serial, token, callback):
        return (), []

    def cancel(self):
        pass


def test_no_coarse_candidates_never_runs_card_or_claims_full_card_coverage(tmp_path):
    def forbidden(*args):
        raise AssertionError("No card windows selected")
    updates = []
    result = RXSurvey("hackrf_transfer", "0" * 32,
                      SurveyConfig(100_000_000, 102_000_000, mode="fast"), tmp_path / "scan.jsonl",
                      session_factory=forbidden, screen_factory=Screen).run(updates.append)
    assert result.state == "completed" and result.completed_windows == 0
    assert all(not row.observations for row in updates)
    assert updates[-1].state == "coarse_complete"


def test_fast_mode_cannot_be_used_for_reference_comparison():
    with pytest.raises(ValueError):
        SurveyConfig(mode="fast", operator_condition="tx_off_reference")


def test_cancellation_after_screening_never_starts_card(tmp_path):
    class Cancelled(Screen):
        def run(self, config, serial, token, callback):
            token.set()
            return (0,), []
    def forbidden(*args):
        raise AssertionError("Cancellation must retain receiver ownership boundary")
    result = RXSurvey("hackrf_transfer", "0" * 32,
                      SurveyConfig(100_000_000, 102_000_000, mode="fast"), tmp_path / "scan.jsonl",
                      session_factory=forbidden, screen_factory=Cancelled).run()
    assert result.state == "cancelled"
    assert result.completed_windows == 0


def test_fast_screen_selection_runs_only_selected_card_windows(tmp_path):
    from test_rx_survey import _Session
    class Selected(Screen):
        def run(self, config, serial, token, callback):
            return (1,), []
    updates = []
    result = RXSurvey("hackrf_transfer", "0" * 32,
                      SurveyConfig(100_000_000, 102_000_000, mode="fast"), tmp_path / "scan.jsonl",
                      session_factory=_Session, screen_factory=Selected).run(updates.append)
    completed = [row for row in updates if row.state == "complete"]
    assert result.completed_windows == 1
    assert completed[0].window.index == 1
    assert completed[0].observations[0]["verification"]
    assert completed[0].timing["primary_seconds"] >= 0
