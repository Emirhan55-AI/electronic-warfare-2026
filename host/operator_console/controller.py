"""Single-worker controller for recorded-frame navigation and DSP."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable, Literal

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from reference.spectrum import (
    ExponentialPowerAverager,
    SigMFFrameSource,
    SpectrumConfig,
    SpectrumProcessor,
    SpectrumResult,
)

from .main_window import MainWindow
from .ui_text import ERROR_TEXT, TEXT


class FrameTaskSignals(QObject):
    completed = Signal(int, int, object, float)
    failed = Signal(int, int, str, str)


class SourceOpenTaskSignals(QObject):
    completed = Signal(int, object, str)
    failed = Signal(int, str, str)


class SourceOpenTask(QRunnable):
    """Inspect and resolve one SigMF source entirely outside the UI thread."""

    def __init__(
        self,
        generation: int,
        metadata_path: Path,
        data_path: Path | None,
        mode: Literal["standard", "explicit"],
        source_factory: Callable[..., SigMFFrameSource],
        closing_event: threading.Event,
    ) -> None:
        super().__init__()
        self.generation = generation
        self.metadata_path = metadata_path
        self.data_path = data_path
        self.mode = mode
        self.source_factory = source_factory
        self.closing_event = closing_event
        self.signals = SourceOpenTaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            source = self.source_factory(
                self.metadata_path,
                self.data_path,
                mode=self.mode,
                frame_length=4096,
            )
        except Exception as exc:  # Worker boundary exposes only typed failure data.
            code = getattr(exc, "code", "source_open_failed")
            self.signals.failed.emit(self.generation, str(code), str(exc))
            return
        if self.closing_event.is_set():
            source.close()
            return
        self.signals.completed.emit(self.generation, source, self.metadata_path.name)


class FrameTask(QRunnable):
    def __init__(
        self,
        generation: int,
        index: int,
        source: SigMFFrameSource,
        processor: SpectrumProcessor,
    ) -> None:
        super().__init__()
        self.generation = generation
        self.index = index
        self.source = source
        self.processor = processor
        self.signals = FrameTaskSignals()

    @Slot()
    def run(self) -> None:
        started = time.perf_counter()
        try:
            frame = self.source.read_frame(self.index)
            result = self.processor.process(
                frame,
                sample_rate_hz=self.source.sample_rate_hz,
                center_frequency_hz=self.source.center_frequency_hz,
            )
        except Exception as exc:  # Worker boundary reports typed details to the controller.
            code = getattr(exc, "code", "processing_failed")
            self.signals.failed.emit(self.generation, self.index, str(code), type(exc).__name__)
            return
        self.signals.completed.emit(
            self.generation,
            self.index,
            result,
            time.perf_counter() - started,
        )


class OperatorController(QObject):
    """Coordinate one bounded source, one worker, and the visible UI."""

    frame_rendered = Signal(int, float)
    task_counters_changed = Signal()

    def __init__(
        self,
        window: MainWindow,
        *,
        source_factory: Callable[..., SigMFFrameSource] = SigMFFrameSource,
    ) -> None:
        super().__init__(window)
        self.window = window
        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(1)
        self.playback_timer = QTimer(self)
        self.playback_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.playback_timer.timeout.connect(self._advance_playback)
        self.source: SigMFFrameSource | None = None
        self.source_factory = source_factory
        self.processor = SpectrumProcessor()
        self.averager = ExponentialPowerAverager(alpha=0.2)
        self.current_index = 0
        self.generation = 0
        self.last_result: SpectrumResult | None = None
        self._active_tasks = 0
        self._refresh_pending = False
        self._pending_open: tuple[int, Path, Path | None, Literal["standard", "explicit"]] | None = None
        self._closing = False
        self._closing_event = threading.Event()
        self.playing = False

        self.requested_task_count = 0
        self.completed_task_count = 0
        self.failed_task_count = 0
        self.stale_results_rejected = 0
        self.coalesced_request_count = 0
        self.max_concurrent_tasks = 0
        self.max_pending_intents = 0

        window.open_button.clicked.connect(self.choose_source)
        window.start_button.clicked.connect(self.start)
        window.pause_button.clicked.connect(self.pause)
        window.stop_button.clicked.connect(self.stop)
        window.frame_spin.valueChanged.connect(self._frame_changed)
        window.speed_spin.valueChanged.connect(self._speed_changed)
        window.axis_combo.currentIndexChanged.connect(self._axis_changed)
        window.metric_combo.currentIndexChanged.connect(self._metric_changed)
        window.dc_checkbox.toggled.connect(self._dsp_config_changed)
        window.average_checkbox.toggled.connect(self._average_changed)

    @property
    def active_task_count(self) -> int:
        return self._active_tasks

    @property
    def pending_intent_count(self) -> int:
        return 1 if self._refresh_pending or self._pending_open is not None else 0

    @Slot()
    def choose_source(self) -> None:
        metadata_name, _ = QFileDialog.getOpenFileName(
            self.window,
            TEXT["select_metadata"],
            "",
            TEXT["file_filter"],
        )
        if not metadata_name:
            return
        metadata_path = Path(metadata_name)
        data_path: Path | None = None
        mode = "standard" if metadata_path.name.endswith(".sigmf-meta") else "explicit"
        if mode == "explicit":
            data_name, _ = QFileDialog.getOpenFileName(
                self.window,
                TEXT["select_data"],
                str(metadata_path.parent),
                TEXT["data_filter"],
            )
            if not data_name:
                return
            data_path = Path(data_name)
        self.open_source(metadata_path, data_path=data_path, mode=mode)

    def open_source(
        self,
        metadata_path: Path,
        *,
        data_path: Path | None = None,
        mode: str = "standard",
    ) -> bool:
        if self._closing:
            return False
        if mode not in {"standard", "explicit"}:
            self.window.show_error(TEXT["source_error"])
            return False
        self.pause()
        self._invalidate_processing(clear_history=True)
        generation = self.generation
        request = (
            generation,
            Path(metadata_path),
            Path(data_path) if data_path is not None else None,
            mode,  # type: ignore[arg-type]
        )
        self.window.show_opening()
        if self._active_tasks:
            self._pending_open = request
            self._refresh_pending = False
            self.coalesced_request_count += 1
            self.max_pending_intents = max(self.max_pending_intents, 1)
            self.task_counters_changed.emit()
            return True
        self._start_source_open(request)
        return True

    def _start_source_open(
        self,
        request: tuple[int, Path, Path | None, Literal["standard", "explicit"]],
    ) -> None:
        generation, metadata_path, data_path, mode = request
        task = SourceOpenTask(
            generation,
            metadata_path,
            data_path,
            mode,
            self.source_factory,
            self._closing_event,
        )
        task.signals.completed.connect(self._source_open_completed)
        task.signals.failed.connect(self._source_open_failed)
        self._active_tasks = 1
        self.requested_task_count += 1
        self.max_concurrent_tasks = max(self.max_concurrent_tasks, self._active_tasks)
        self.thread_pool.start(task)
        self.task_counters_changed.emit()

    @Slot(int, object, str)
    def _source_open_completed(
        self,
        generation: int,
        source: SigMFFrameSource,
        filename: str,
    ) -> None:
        self._active_tasks = 0
        self.completed_task_count += 1
        if self._closing or generation != self.generation:
            source.close()
            self.stale_results_rejected += 1
            self._dispatch_pending_intent()
            return

        previous_source = self.source
        self.source = source
        if previous_source is not None and previous_source is not source:
            previous_source.close()
        self.current_index = 0
        self.last_result = None
        self.averager.reset()
        self.window.set_source(filename, source.report)
        warning_messages = [self._warning_text(issue.code) for issue in source.report.warnings]
        warning_messages = [message for message in warning_messages if message]
        if warning_messages:
            self.window.show_warning(" ".join(warning_messages))
        else:
            self.window.hide_notification()
        self.window.finish_opening(source_available=True)
        self.task_counters_changed.emit()
        if not self._dispatch_pending_intent():
            self.request_current_frame()

    @Slot(int, str, str)
    def _source_open_failed(self, generation: int, code: str, detail: str) -> None:
        self._active_tasks = 0
        self.failed_task_count += 1
        if not self._closing and generation == self.generation:
            message = ERROR_TEXT.get(code)
            if message is None:
                message = next(
                    (translated for issue_code, translated in ERROR_TEXT.items() if issue_code in detail),
                    TEXT["source_error"],
                )
            self.window.show_error(message)
            self.window.finish_opening(source_available=self.source is not None)
        self.task_counters_changed.emit()
        self._dispatch_pending_intent()

    @Slot()
    def start(self) -> None:
        if self.source is None:
            return
        self.playing = True
        self.window.set_state("playing")
        self._speed_changed(self.window.speed_spin.value())
        self.playback_timer.start()
        if self.last_result is None:
            self.request_current_frame()

    @Slot()
    def pause(self) -> None:
        self.playing = False
        self.playback_timer.stop()
        if self.source is not None:
            self.window.set_state("paused")

    @Slot()
    def stop(self) -> None:
        if self.source is None:
            return
        self.playing = False
        self.playback_timer.stop()
        self.current_index = 0
        self.averager.reset()
        self._invalidate_processing(clear_history=True)
        self.window.set_state("stopped")
        self.window.set_frame_position(0, self.source.frame_count)
        self.request_current_frame()

    def request_current_frame(self) -> bool:
        if self.source is None or self.source.frame_count == 0:
            return False
        if self._active_tasks:
            self._refresh_pending = True
            self.coalesced_request_count += 1
            self.max_pending_intents = max(self.max_pending_intents, 1)
            self.task_counters_changed.emit()
            return False
        task = FrameTask(self.generation, self.current_index, self.source, self.processor)
        task.signals.completed.connect(self._task_completed)
        task.signals.failed.connect(self._task_failed)
        self._active_tasks = 1
        self.requested_task_count += 1
        self.max_concurrent_tasks = max(self.max_concurrent_tasks, self._active_tasks)
        self.thread_pool.start(task)
        self.task_counters_changed.emit()
        return True

    @Slot(int, int, object, float)
    def _task_completed(
        self,
        generation: int,
        index: int,
        result: SpectrumResult,
        elapsed_seconds: float,
    ) -> None:
        self._active_tasks = 0
        self.completed_task_count += 1
        if generation != self.generation or index != self.current_index:
            self.stale_results_rejected += 1
        else:
            self.last_result = result
            averaged_power = (
                self.averager.update(result.fft_power_unshifted)
                if self.window.average_checkbox.isChecked()
                else result.fft_power_unshifted
            )
            line_display = self.processor.display_from_power(result, averaged_power)
            self.window.spectrum_view.update_spectrum(
                line_display,
                result.display,
                append_waterfall=True,
            )
            assert self.source is not None
            self.window.set_frame_position(index, self.source.frame_count)
            self.frame_rendered.emit(index, elapsed_seconds)
        pending = self._refresh_pending
        self._refresh_pending = False
        self.task_counters_changed.emit()
        if self._dispatch_pending_intent():
            return
        if pending and not self._closing:
            self.request_current_frame()

    @Slot(int, int, str, str)
    def _task_failed(self, generation: int, index: int, code: str, _: str) -> None:
        self._active_tasks = 0
        self.failed_task_count += 1
        if generation == self.generation and index == self.current_index:
            self.window.show_error(ERROR_TEXT.get(code, TEXT["processing_error"]))
        pending = self._refresh_pending
        self._refresh_pending = False
        self.task_counters_changed.emit()
        if self._dispatch_pending_intent():
            return
        if pending and not self._closing:
            self.request_current_frame()

    def _dispatch_pending_intent(self) -> bool:
        if self._active_tasks or self._closing:
            return False
        if self._pending_open is not None:
            request = self._pending_open
            self._pending_open = None
            self._refresh_pending = False
            self._start_source_open(request)
            return True
        return False

    @Slot()
    def _advance_playback(self) -> None:
        if not self.playing or self.source is None or self._active_tasks:
            return
        self.current_index = (self.current_index + 1) % self.source.frame_count
        self.request_current_frame()

    @Slot(int)
    def _frame_changed(self, user_index: int) -> None:
        if self.source is None:
            return
        requested = user_index - 1
        if requested == self.current_index:
            return
        self.pause()
        self.current_index = requested
        self.averager.reset()
        self._invalidate_processing(clear_history=True)
        self.request_current_frame()

    @Slot(int)
    def _speed_changed(self, frames_per_second: int) -> None:
        self.playback_timer.setInterval(max(1, round(1000 / frames_per_second)))

    @Slot(int)
    def _axis_changed(self, _: int) -> None:
        self.window.spectrum_view.set_axis_mode(self.window.axis_mode)
        self._render_last_without_history()

    @Slot(int)
    def _metric_changed(self, _: int) -> None:
        self.window.spectrum_view.set_metric(self.window.metric)
        self.window.spectrum_view.clear_history()
        self._render_last_without_history()

    @Slot(bool)
    def _dsp_config_changed(self, enabled: bool) -> None:
        self.processor = SpectrumProcessor(SpectrumConfig(remove_dc=enabled))
        self.averager.reset()
        self.last_result = None
        self._invalidate_processing(clear_history=True)
        self.request_current_frame()

    @Slot(bool)
    def _average_changed(self, _: bool) -> None:
        self.averager.reset()
        self.window.spectrum_view.clear_history()
        self._render_last_without_history()

    def _render_last_without_history(self) -> None:
        if self.last_result is None:
            return
        self.window.spectrum_view.update_spectrum(
            self.last_result.display,
            self.last_result.display,
            append_waterfall=False,
        )

    def _invalidate_processing(self, *, clear_history: bool) -> None:
        self.generation += 1
        self._refresh_pending = False
        if clear_history:
            self.window.spectrum_view.clear_history()

    @staticmethod
    def _warning_text(code: str) -> str:
        return {
            "channel_count_defaulted": TEXT["warning_default_channel"],
            "nonstandard_metadata_extension": TEXT["warning_nonstandard_name"],
            "incomplete_frame_dropped": TEXT["warning_partial_frame"],
        }.get(code, "")

    def close(self) -> None:
        self._closing = True
        self._closing_event.set()
        self.generation += 1
        self._pending_open = None
        self._refresh_pending = False
        self.playback_timer.stop()
        self.thread_pool.waitForDone()
        self._active_tasks = 0
        if self.source is not None:
            self.source.close()
            self.source = None
