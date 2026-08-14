"""Single-worker controller for recorded-frame navigation and DSP."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable, Literal

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from host.acquisition import (
    AcquisitionError,
    BoundedCI8FrameSource,
    CaptureResult,
    DeterministicMockBackend,
    DeviceStatus,
    HackRFBackend,
    RXConfig,
    RealHackRFBackend,
    ToolInventory,
)
from reference.detection import DetectionFrameResult
from reference.parameters import (
    AnalysisSpan,
    MeasurementCandidate,
    MeasurementContext,
    MeasurementIntent,
    OperatorMeasurementProcessor,
    ParameterFrameResult,
    suggest_analysis_span,
)
from reference.monitoring import (
    AnalogMonitor,
    AnalogMonitorConfig,
    AnalogMonitorResult,
    ListeningIntent,
    write_wav,
)
from reference.pipeline import (
    ProcessingProfile,
    RuntimeFrameResult,
    RuntimePipeline,
    VerifiedProfileBinding,
    resolve_default_operation_profile,
)
from reference.pipeline.profile import load_phase04e1_capability
from reference.spectrum import (
    ExponentialPowerAverager,
    SigMFFrameSource,
    SpectrumResult,
)

from .audio_playback import AudioPlayback
from .main_window import MainWindow
from .ui_text import ERROR_TEXT, TEXT


class FrameTaskSignals(QObject):
    completed = Signal(int, int, object, float)
    failed = Signal(int, int, str, str)


class SourceOpenTaskSignals(QObject):
    completed = Signal(int, object, str)
    failed = Signal(int, str, str)


class MeasurementTaskSignals(QObject):
    completed = Signal(object, object)
    failed = Signal(object, str)


class AcquisitionTaskSignals(QObject):
    completed = Signal(int, str, object)
    failed = Signal(int, str, str)


class ListeningTaskSignals(QObject):
    completed = Signal(object, object)
    failed = Signal(object, str)


class WavExportTaskSignals(QObject):
    completed = Signal(object)
    failed = Signal(object, str)


class ListeningTask(QRunnable):
    """Read and demodulate exactly four frames outside the UI thread."""

    def __init__(self, intent: ListeningIntent, source: object) -> None:
        super().__init__()
        self.intent = intent
        self.source = source
        self.signals = ListeningTaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            frames = tuple(self.source.read_frame(self.intent.start_frame + offset) for offset in range(4))
            config = AnalogMonitorConfig(
                self.intent.mode,
                float(self.source.sample_rate_hz),
                self.intent.center_offset_hz,
                self.intent.channel_bandwidth_hz,
            )
            result = AnalogMonitor().process(frames, config, volume=self.intent.volume)
        except Exception as exc:
            self.signals.failed.emit(self.intent.generation_key, str(getattr(exc, "code", "insufficient_audio")))
            return
        self.signals.completed.emit(self.intent.generation_key, result)


class WavExportTask(QRunnable):
    """Write one already-bounded PCM payload outside the UI thread."""

    def __init__(self, generation_key: object, destination: Path, pcm16: bytes) -> None:
        super().__init__()
        self.generation_key = generation_key
        self.destination = destination
        self.pcm16 = pcm16
        self.signals = WavExportTaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            write_wav(self.destination, self.pcm16)
        except Exception as exc:
            self.signals.failed.emit(self.generation_key, str(getattr(exc, "code", "wav_write_failed")))
            return
        self.signals.completed.emit(self.generation_key)


class AcquisitionTask(QRunnable):
    """Run HackRF discovery or one bounded capture outside the UI thread."""

    def __init__(
        self,
        generation: int,
        operation: Literal["probe", "capture", "test_capture"],
        backend: HackRFBackend,
        config: RXConfig,
        closing_event: threading.Event,
    ) -> None:
        super().__init__()
        self.generation = generation
        self.operation = operation
        self.backend = backend
        self.config = config
        self.closing_event = closing_event
        self.signals = AcquisitionTaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            if self.operation == "probe":
                inventory = self.backend.discover_tools(inspect_help=True)
                device = (
                    self.backend.discover_device(self.closing_event)
                    if inventory.receive_available
                    else DeviceStatus("not_exercised", reason_code="tools_unavailable")
                )
                result: object = (inventory, device)
            else:
                result = self.backend.capture(self.config, self.closing_event)
        except Exception as exc:
            self.signals.failed.emit(self.generation, self.operation, str(getattr(exc, "code", "device_probe_failed")))
            return
        if self.closing_event.is_set():
            return
        self.signals.completed.emit(self.generation, self.operation, result)


class MeasurementTask(QRunnable):
    """Bounded four-frame E1 read and measurement outside the UI thread."""

    def __init__(self, intent: MeasurementIntent, source: object, processor: object) -> None:
        super().__init__()
        self.intent = intent
        self.source = source
        self.processor = processor
        self.signals = MeasurementTaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            samples = tuple(self.source.read_frame(self.intent.start_frame + offset) for offset in range(4))
            spectra = tuple(
                self.processor.process(
                    frame,
                    sample_rate_hz=self.source.sample_rate_hz,
                    center_frequency_hz=self.source.center_frequency_hz,
                )
                for frame in samples
            )
            result = OperatorMeasurementProcessor().measure(self.intent, samples, spectra)
        except Exception as exc:
            self.signals.failed.emit(self.intent.generation_key, str(getattr(exc, "code", "measurement_failed")))
            return
        self.signals.completed.emit(self.intent.generation_key, result)


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
        source: object,
        runtime_pipeline: RuntimePipeline,
    ) -> None:
        super().__init__()
        self.generation = generation
        self.index = index
        self.source = source
        self.runtime_pipeline = runtime_pipeline
        self.signals = FrameTaskSignals()

    @Slot()
    def run(self) -> None:
        started = time.perf_counter()
        try:
            frame = self.source.read_frame(self.index)
            result = self.runtime_pipeline.process(
                frame,
                sample_rate_hz=self.source.sample_rate_hz,
                center_frequency_hz=self.source.center_frequency_hz,
                frame_index=self.index,
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
        acquisition_backend: HackRFBackend | None = None,
        test_backend_factory: Callable[[], HackRFBackend] = DeterministicMockBackend,
        profile: ProcessingProfile | None = None,
        verified_binding: VerifiedProfileBinding | None = None,
        audio_playback: AudioPlayback | None = None,
    ) -> None:
        super().__init__(window)
        self.window = window
        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(1)
        self.playback_timer = QTimer(self)
        self.playback_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.playback_timer.timeout.connect(self._advance_playback)
        self.source: object | None = None
        self.source_factory = source_factory
        self.acquisition_backend = acquisition_backend or RealHackRFBackend()
        self.test_backend_factory = test_backend_factory
        if profile is None:
            resolved = resolve_default_operation_profile()
            self.profile = resolved.profile
            self.verified_binding = resolved.binding
            self.profile_fallback_code = resolved.fallback_code
        else:
            self.profile = profile
            self.verified_binding = verified_binding
            self.profile_fallback_code = None
        self.runtime_pipeline = RuntimePipeline(self.profile, verified_binding=self.verified_binding)
        self.e1_capability = load_phase04e1_capability()
        self.audio_playback = audio_playback or AudioPlayback(self)
        self.processor = self.runtime_pipeline.processor
        self.averager = ExponentialPowerAverager(alpha=0.2)
        self.current_index = 0
        self.generation = 0
        self.last_result: SpectrumResult | None = None
        self.last_detection: DetectionFrameResult | None = None
        self.last_parameters: ParameterFrameResult | None = None
        self._active_tasks = 0
        self._refresh_pending = False
        self._pending_open: tuple[int, Path, Path | None, Literal["standard", "explicit"]] | None = None
        self._pending_measurement: MeasurementIntent | None = None
        self._pending_acquisition: tuple[int, Literal["probe", "capture", "test_capture"], HackRFBackend, RXConfig] | None = None
        self._pending_listening: ListeningIntent | None = None
        self._listening_intent: ListeningIntent | None = None
        self._listening_result: AnalogMonitorResult | None = None
        self._listening_revision = 0
        self._source_is_fixture = False
        self._measurement_intent: MeasurementIntent | None = None
        self._selected_event_id: int | None = None
        self._span: AnalysisSpan | None = None
        self._span_revision = 0
        self._configuration_generation = 0
        self._event_observation_history: dict[int, list[bool]] = {}
        self._closing = False
        self._closing_event = threading.Event()
        self._hackrf_device_ready = False
        self._active_acquisition_backend: HackRFBackend | None = None
        self.playing = False

        self.requested_task_count = 0
        self.completed_task_count = 0
        self.failed_task_count = 0
        self.stale_results_rejected = 0
        self.coalesced_request_count = 0
        self.max_concurrent_tasks = 0
        self.max_pending_intents = 0

        window.open_button.clicked.connect(self.activate_selected_source)
        window.source_type_combo.currentIndexChanged.connect(self._source_type_changed)
        window.hackrf_refresh_button.clicked.connect(self.probe_hackrf)
        window.hackrf_start_button.clicked.connect(self.start_hackrf_capture)
        window.hackrf_stop_button.clicked.connect(self.stop_hackrf_capture)
        window.start_button.clicked.connect(self.start)
        window.pause_button.clicked.connect(self.pause)
        window.stop_button.clicked.connect(self.stop)
        window.frame_spin.valueChanged.connect(self._frame_changed)
        window.speed_spin.valueChanged.connect(self._speed_changed)
        window.axis_combo.currentIndexChanged.connect(self._axis_changed)
        window.metric_combo.currentIndexChanged.connect(self._metric_changed)
        window.dc_checkbox.toggled.connect(self._dsp_config_changed)
        window.average_checkbox.toggled.connect(self._average_changed)
        window.detection_layer_checkbox.toggled.connect(self._detection_layer_changed)
        window.pfa_combo.currentIndexChanged.connect(self._detector_config_changed)
        window.center_checkbox.toggled.connect(self._detector_config_changed)
        window.detection_list.itemSelectionChanged.connect(self._analysis_event_selected)
        window.analysis_spectrum.span_changed.connect(self._analysis_span_changed)
        window.measure_button.clicked.connect(self.request_measurement)
        window.clear_measurement_button.clicked.connect(self.clear_analysis)
        window.prepare_listening_button.clicked.connect(self.request_listening)
        window.play_audio_button.clicked.connect(self.play_listening)
        window.pause_audio_button.clicked.connect(self.pause_listening)
        window.stop_audio_button.clicked.connect(self.stop_listening)
        window.export_wav_button.clicked.connect(self.export_listening_wav)
        window.demod_combo.currentIndexChanged.connect(self._listening_config_changed)
        window.listen_offset_spin.valueChanged.connect(self._listening_config_changed)
        window.listen_bandwidth_spin.valueChanged.connect(self._listening_config_changed)
        window.listen_volume_slider.valueChanged.connect(self._listening_config_changed)
        window.set_audio_availability(self.audio_playback.available)
        self._show_profile_summary()
        if self.profile_fallback_code is not None:
            self.window.show_warning(TEXT["phase04_fallback"])

    @property
    def active_task_count(self) -> int:
        return self._active_tasks

    @property
    def pending_intent_count(self) -> int:
        return 1 if self._refresh_pending or self._pending_open is not None or self._pending_measurement is not None or self._pending_acquisition is not None or self._pending_listening is not None else 0

    @Slot()
    def activate_selected_source(self) -> None:
        if self.window.source_kind == "deterministic_test":
            self.open_deterministic_source()
        elif self.window.source_kind == "sigmf":
            self.choose_source()

    @Slot(int)
    def _source_type_changed(self, _: int) -> None:
        mode = self.window.source_kind
        self.pause()
        self.acquisition_backend.cancel()
        if self._active_acquisition_backend is not None:
            self._active_acquisition_backend.cancel()
        self._pending_acquisition = None
        self._pending_listening = None
        self._hackrf_device_ready = False
        if self.source is not None:
            self.source.close()  # type: ignore[attr-defined]
            self.source = None
        self._invalidate_processing(clear_history=True)
        self.window.show_empty()
        self.window.set_acquisition_mode(mode)

    @Slot()
    def probe_hackrf(self) -> bool:
        if self._closing or self.window.source_kind != "hackrf":
            return False
        self._hackrf_device_ready = False
        self.window.set_hackrf_state("searching")
        config = RXConfig(**self.window.hackrf_settings)
        return self._queue_acquisition("probe", self.acquisition_backend, config)

    @Slot()
    def start_hackrf_capture(self) -> bool:
        if self._closing or self.window.source_kind != "hackrf" or not self._hackrf_device_ready:
            return False
        try:
            config = RXConfig(**self.window.hackrf_settings)
        except AcquisitionError as exc:
            self.window.show_error(ERROR_TEXT.get(exc.code, TEXT["source_error"]))
            return False
        self.window.set_hackrf_state("capture_starting")
        return self._queue_acquisition("capture", self.acquisition_backend, config)

    @Slot()
    def open_deterministic_source(self) -> bool:
        if self._closing or self.window.source_kind != "deterministic_test":
            return False
        config = RXConfig()
        self.window.show_opening()
        return self._queue_acquisition("test_capture", self.test_backend_factory(), config)

    @Slot()
    def stop_hackrf_capture(self) -> None:
        self.acquisition_backend.cancel()
        self._pending_acquisition = None
        self.pause()
        self._invalidate_processing(clear_history=True)
        self.window.set_hackrf_state("stopped")

    def _queue_acquisition(
        self,
        operation: Literal["probe", "capture", "test_capture"],
        backend: HackRFBackend,
        config: RXConfig,
    ) -> bool:
        self._invalidate_processing(clear_history=True)
        request = (self.generation, operation, backend, config)
        if self._active_tasks:
            self._pending_acquisition = request
            self._pending_open = None
            self._pending_measurement = None
            self._pending_listening = None
            self._refresh_pending = False
            self.coalesced_request_count += 1
            self.max_pending_intents = max(self.max_pending_intents, 1)
            return True
        self._start_acquisition(request)
        return True

    def _start_acquisition(
        self,
        request: tuple[int, Literal["probe", "capture", "test_capture"], HackRFBackend, RXConfig],
    ) -> None:
        generation, operation, backend, config = request
        task = AcquisitionTask(generation, operation, backend, config, self._closing_event)
        task.signals.completed.connect(self._acquisition_completed)
        task.signals.failed.connect(self._acquisition_failed)
        self._active_tasks = 1
        self._active_acquisition_backend = backend
        self.requested_task_count += 1
        self.max_concurrent_tasks = max(self.max_concurrent_tasks, self._active_tasks)
        self.thread_pool.start(task)
        self.task_counters_changed.emit()

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

        self._install_source(source, filename)
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

    def _install_source(self, source: object, label: str) -> None:
        previous_source = self.source
        self.source = source
        if previous_source is not None and previous_source is not source:
            previous_source.close()  # type: ignore[attr-defined]
        self.current_index = 0
        self.last_result = None
        self.last_detection = None
        self.last_parameters = None
        self.clear_analysis()
        self.clear_listening()
        self.averager.reset()
        self.runtime_pipeline.detection.reset()
        self.window.set_source(label, source.report)  # type: ignore[attr-defined]
        metadata_path = getattr(source, "metadata_path", None)
        self._source_is_fixture = metadata_path is not None and "phase05" in Path(metadata_path).parts
        self.window.set_fixture_source(self._source_is_fixture)
        self.window.finish_opening(source_available=True)

    @Slot(int, str, object)
    def _acquisition_completed(self, generation: int, operation: str, result: object) -> None:
        self._active_tasks = 0
        self._active_acquisition_backend = None
        self.completed_task_count += 1
        if self._closing or generation != self.generation:
            self.stale_results_rejected += 1
            self._dispatch_pending_intent()
            return
        if operation == "probe":
            inventory, device = result  # type: ignore[misc]
            assert isinstance(inventory, ToolInventory) and isinstance(device, DeviceStatus)
            if not inventory.receive_available:
                self.window.set_hackrf_state("tools_missing")
            elif device.state == "ready":
                self._hackrf_device_ready = True
                self.window.set_hackrf_state("device_ready")
            elif device.state == "not_found":
                self.window.set_hackrf_state("device_missing")
            else:
                self.window.set_hackrf_state("cli_error")
        else:
            assert isinstance(result, CaptureResult)
            source = BoundedCI8FrameSource(result)
            label = "Deterministik ci8 test kaynağı" if result.backend_kind == "deterministic_test" else "HackRF-1 bounded RX"
            self._install_source(source, label)
            if result.backend_kind == "deterministic_test":
                self.window.set_hackrf_state("test_source")
                self.window.show_warning(TEXT["deterministic_source_active"])
            else:
                self.window.set_hackrf_state("live")
            self.request_current_frame()
        self.task_counters_changed.emit()
        self._dispatch_pending_intent()

    @Slot(int, str, str)
    def _acquisition_failed(self, generation: int, operation: str, code: str) -> None:
        self._active_tasks = 0
        self._active_acquisition_backend = None
        self.failed_task_count += 1
        if not self._closing and generation == self.generation:
            if code == "operation_timeout":
                self.window.set_hackrf_state("timeout")
            elif operation == "probe" and code == "tools_unavailable":
                self.window.set_hackrf_state("tools_missing")
            else:
                self.window.set_hackrf_state("cli_error")
            self.window.show_error(ERROR_TEXT.get(code, TEXT["hackrf_cli_error"]))
            self.window.finish_opening(source_available=self.source is not None)
        self.task_counters_changed.emit()
        self._dispatch_pending_intent()

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
        task = FrameTask(self.generation, self.current_index, self.source, self.runtime_pipeline)
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
        result: RuntimeFrameResult,
        elapsed_seconds: float,
    ) -> None:
        self._active_tasks = 0
        self.completed_task_count += 1
        if generation != self.generation or index != self.current_index:
            self.stale_results_rejected += 1
        else:
            self.last_result = result.spectrum
            self.last_detection = result.detection  # type: ignore[assignment]
            active_ids = {int(item.event_id) for item in self.last_detection.active_events}
            for event_id in set(self._event_observation_history) | active_ids:
                event = next((item for item in self.last_detection.active_events if int(item.event_id) == event_id), None)
                self._event_observation_history.setdefault(event_id, []).append(bool(event is not None and event.observed_this_frame))
                self._event_observation_history[event_id] = self._event_observation_history[event_id][-4:]
            self.last_parameters = result.parameters
            averaged_power = (
                self.averager.update(result.spectrum.fft_power_unshifted)
                if self.window.average_checkbox.isChecked()
                else result.spectrum.fft_power_unshifted
            )
            line_display = self.processor.display_from_power(result.spectrum, averaged_power)
            self.window.spectrum_view.update_spectrum(
                line_display,
                result.spectrum.display,
                append_waterfall=True,
                detection_result=self.last_detection,
                spectrum_result=result.spectrum,
                parameter_result=self.last_parameters,
            )
            self.window.set_detection_result(self.last_detection)
            self.window.set_parameter_result(self.last_parameters)
            if self._selected_event_id is not None:
                self._refresh_selected_event()
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
        if self._pending_acquisition is not None:
            request = self._pending_acquisition
            self._pending_acquisition = None
            self._refresh_pending = False
            self._start_acquisition(request)
            return True
        if self._pending_measurement is not None:
            intent = self._pending_measurement
            self._pending_measurement = None
            self._start_measurement(intent)
            return True
        if self._pending_listening is not None:
            intent = self._pending_listening
            self._pending_listening = None
            self._start_listening(intent)
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
        del enabled
        self._pipeline_config_changed()

    @Slot()
    def _detector_config_changed(self, *_: object) -> None:
        self._pipeline_config_changed()

    def _pipeline_config_changed(self) -> None:
        try:
            pipeline = RuntimePipeline(
                self.profile,
                verified_binding=self.verified_binding,
                pfa=self.window.pfa,
                evaluate_center=self.window.center_checkbox.isChecked(),
                remove_dc=self.window.dc_checkbox.isChecked(),
            )
        except Exception as exc:
            code = str(getattr(exc, "code", "parameter_outside_validated_envelope"))
            self.window.show_error(ERROR_TEXT.get(code, TEXT["parameter_error"]))
            return
        self.runtime_pipeline = pipeline
        self.processor = pipeline.processor
        self.averager.reset()
        self.last_result = None
        self.last_detection = None
        self._event_observation_history.clear()
        self.last_parameters = None
        self._configuration_generation += 1
        self.clear_analysis()
        self._show_profile_summary()
        self._invalidate_processing(clear_history=True)
        self.request_current_frame()

    @Slot(bool)
    def _detection_layer_changed(self, visible: bool) -> None:
        self.window.spectrum_view.set_detection_visible(visible)
        self._render_last_without_history()

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
            detection_result=self.last_detection,
            spectrum_result=self.last_result,
            parameter_result=self.last_parameters,
        )

    def _invalidate_processing(self, *, clear_history: bool) -> None:
        self.generation += 1
        self._refresh_pending = False
        # Replace, rather than mutate, the generation-bound pipeline. A stale
        # worker may still own the previous instance until its result is rejected.
        self.runtime_pipeline = RuntimePipeline(
            self.profile,
            verified_binding=self.verified_binding,
            pfa=self.runtime_pipeline.pfa,
            evaluate_center=self.runtime_pipeline.evaluate_center,
            remove_dc=self.runtime_pipeline.remove_dc,
        )
        self.processor = self.runtime_pipeline.processor
        self.last_detection = None
        self._event_observation_history.clear()
        self.window.clear_detections()
        self.last_parameters = None
        self.window.clear_parameters()
        self.window.spectrum_view.clear_detection_overlay()
        self.clear_analysis()
        self.clear_listening()
        if clear_history:
            self.window.spectrum_view.clear_history()

    def set_profile(
        self,
        profile: ProcessingProfile,
        *,
        verified_binding: VerifiedProfileBinding | None = None,
    ) -> None:
        """Replace the operation profile and reset all generation-bound state."""
        pipeline = RuntimePipeline(profile, verified_binding=verified_binding)
        self.pause()
        self.profile = profile
        self.verified_binding = verified_binding
        self.profile_fallback_code = None
        self.runtime_pipeline = pipeline
        self.processor = pipeline.processor
        self.averager.reset()
        self.last_result = None
        self._show_profile_summary()
        self._invalidate_processing(clear_history=True)
        self.request_current_frame()

    def _show_profile_summary(self) -> None:
        center = "merkez dâhil" if self.runtime_pipeline.evaluate_center else "merkez dışarıda"
        method = {
            "regional": "Bölgesel",
            "ca_cfar": "CA-CFAR",
            "os_cfar": "OS-CFAR",
            "os_regional_cap": "OS + bölgesel sınır",
        }[self.runtime_pipeline.detector_method]
        summary = f"Varsayılan v{self.profile.profile_version} · {method}\nPfa/CUT {self.runtime_pipeline.pfa:g} · {center}"
        if self.profile.parameter_block is not None:
            block = self.profile.parameter_block
            assert block is not None
            summary += (
                "\nParametre: "
                + str(block.parameters["bandwidth_method"]).removeprefix("band.")
                + " · "
                + str(block.parameters["signal_domain_method"]).removeprefix("domain.")
            )
        self.window.set_profile_summary(summary, validated=True)

    @Slot()
    def _analysis_event_selected(self) -> None:
        items = self.window.detection_list.selectedItems()
        if not items or self.last_detection is None or self.last_result is None:
            self.clear_analysis()
            self.clear_listening()
            return
        event_id = int(items[0].data(Qt.ItemDataRole.UserRole))
        event = next((item for item in self.last_detection.active_events if item.event_id == event_id), None)
        if event is None or event.state != "confirmed" or not event.observed_this_frame:
            self.clear_analysis()
            self.clear_listening()
            return
        self._selected_event_id = event_id
        self._span_revision += 1
        if self.e1_capability is not None and self.e1_capability.automatic_span_validated:
            span = suggest_analysis_span(event, self.last_detection.active_events, revision=self._span_revision)
        else:
            lower = max(20, int(event.region.start_bin))
            upper = min(4075, int(event.region.end_bin))
            if upper - lower + 1 < 8:
                upper = min(4075, lower + 7)
                lower = max(20, upper - 7)
            span = AnalysisSpan(lower, upper, "operator_adjusted", self._span_revision)
        self.window.set_analysis_event(event)
        self.window.set_listening_event(
            event,
            offset_hz=float(event.region.peak_frequency_hz - self.last_result.center_frequency_hz),
        )
        self.window.listening_spectrum.set_spectrum(self.last_result.display)
        self.window.measure_button.setEnabled(self.e1_capability is not None)
        self.window.analysis_spectrum.set_spectrum(self.last_result.display)
        if span is None:
            self._span = None
            self.window.span_value.setText(TEXT["manual_span_available"])
            return
        self._span = span
        self.window.analysis_spectrum.set_span(span.lower_shifted_bin, span.upper_shifted_bin)
        self.window.set_analysis_span(span.lower_shifted_bin, span.upper_shifted_bin, span.provenance)

    def _refresh_selected_event(self) -> None:
        if self.last_detection is None:
            self.clear_analysis()
            self.clear_listening()
            return
        event = next((item for item in self.last_detection.active_events if item.event_id == self._selected_event_id), None)
        if event is None or event.state != "confirmed" or not event.observed_this_frame:
            self.clear_analysis()
            self.clear_listening()
            return
        self.window.set_analysis_event(event)
        if self.last_result is not None:
            self.window.set_listening_event(event)
            self.window.listening_spectrum.set_spectrum(self.last_result.display)
        self.window.measure_button.setEnabled(self.e1_capability is not None)

    @Slot(int, int)
    def _analysis_span_changed(self, lower: int, upper: int) -> None:
        if self._selected_event_id is None:
            return
        self._span_revision += 1
        self._span = AnalysisSpan(lower, upper, "operator_adjusted", self._span_revision)
        self._measurement_intent = None
        self.window.set_analysis_span(lower, upper, self._span.provenance)

    @Slot()
    def request_measurement(self) -> bool:
        if self.e1_capability is None or self.source is None or self._selected_event_id is None or self._span is None:
            return False
        observations = tuple(self._event_observation_history.get(self._selected_event_id, ()))
        if self.current_index < 3 or len(observations) != 4 or not all(observations):
            self.window.measurement_state.setText(TEXT["measurement_failed"] + ": " + TEXT["insufficient_quality"])
            return False
        event = next((item for item in (self.last_detection.active_events if self.last_detection else ()) if item.event_id == self._selected_event_id), None)
        if event is None or event.state != "confirmed" or not event.observed_this_frame:
            return False
        candidates = tuple(
            MeasurementCandidate(
                int(item.event_id), int(item.seen_count), int(item.region.start_bin), int(item.region.end_bin),
                item.state == "confirmed",
            )
            for item in (self.last_detection.active_events if self.last_detection else ())
        )
        context = MeasurementContext(
            self.generation,
            self.generation,
            self._configuration_generation,
            int(event.event_id),
            int(event.seen_count),
            observations,  # type: ignore[arg-type]
            candidates,
        )
        intent = MeasurementIntent(
            self.generation,
            self.generation,
            self._configuration_generation,
            event.event_id,
            event.seen_count,
            self.current_index - 3,
            self._span,
            context,
        )
        self._measurement_intent = intent
        self.window.set_measurement_busy()
        if self._active_tasks:
            self._pending_measurement = intent
            self._refresh_pending = False
            self.max_pending_intents = max(self.max_pending_intents, 1)
            return True
        self._start_measurement(intent)
        return True

    def _start_measurement(self, intent: MeasurementIntent) -> None:
        assert self.source is not None
        task = MeasurementTask(intent, self.source, self.runtime_pipeline.processor)
        task.signals.completed.connect(self._measurement_completed)
        task.signals.failed.connect(self._measurement_failed)
        self._active_tasks = 1
        self.requested_task_count += 1
        self.max_concurrent_tasks = max(self.max_concurrent_tasks, self._active_tasks)
        self.thread_pool.start(task)
        self.task_counters_changed.emit()

    @Slot(object, object)
    def _measurement_completed(self, generation_key: object, result: object) -> None:
        self._active_tasks = 0
        self.completed_task_count += 1
        if self._measurement_intent is None or generation_key != self._measurement_intent.generation_key or self._closing:
            self.stale_results_rejected += 1
        else:
            fields = self.e1_capability.validated_fields if self.e1_capability is not None else ()
            self.window.set_operator_measurement(result, fields)
        self.task_counters_changed.emit()
        self._dispatch_pending_intent()

    @Slot(object, str)
    def _measurement_failed(self, generation_key: object, _: str) -> None:
        self._active_tasks = 0
        self.failed_task_count += 1
        if self._measurement_intent is not None and generation_key == self._measurement_intent.generation_key and not self._closing:
            self.window.measurement_state.setText(TEXT["measurement_failed"])
        self.task_counters_changed.emit()
        self._dispatch_pending_intent()

    @Slot()
    def _listening_config_changed(self, *_: object) -> None:
        self._listening_revision += 1
        self._listening_result = None
        self.audio_playback.stop()
        self.window.listening_state.setText(TEXT["listening_not_prepared"])
        self.window.play_audio_button.setEnabled(False)
        self.window.pause_audio_button.setEnabled(False)
        self.window.stop_audio_button.setEnabled(False)
        self.window.export_wav_button.setEnabled(False)
        if self._selected_event_id is not None:
            self.window.prepare_listening_button.setEnabled(True)

    @Slot()
    def request_listening(self) -> bool:
        if self.source is None or self._selected_event_id is None or self.last_detection is None:
            return False
        event = next(
            (item for item in self.last_detection.active_events if item.event_id == self._selected_event_id),
            None,
        )
        if event is None or event.state != "confirmed" or not event.observed_this_frame:
            self.window.listening_state.setText(TEXT["listening_failed"])
            return False
        if self.current_index + 4 > int(self.source.frame_count):
            self.window.listening_state.setText(ERROR_TEXT["insufficient_iq"])
            return False
        try:
            mode = str(self.window.demod_combo.currentData())
            config = AnalogMonitorConfig(
                mode,  # type: ignore[arg-type]
                float(self.source.sample_rate_hz),
                self.window.listen_offset_spin.value() * 1000.0,
                self.window.listen_bandwidth_spin.value() * 1000.0,
            )
        except Exception as exc:
            code = str(getattr(exc, "code", "invalid_channel_bandwidth"))
            self.window.listening_state.setText(ERROR_TEXT.get(code, TEXT["listening_failed"]))
            return False
        intent = ListeningIntent(
            self.generation,
            self.generation,
            self._configuration_generation,
            int(event.event_id),
            int(event.seen_count) + self._listening_revision,
            self.current_index,
            config.mode,
            config.center_offset_hz,
            config.channel_bandwidth_hz,
            self.window.listen_volume_slider.value() / 100.0,
        )
        self._listening_intent = intent
        self.window.set_listening_busy()
        if self._active_tasks:
            self._pending_open = None
            self._pending_acquisition = None
            self._pending_measurement = None
            self._pending_listening = intent
            self._refresh_pending = False
            self.coalesced_request_count += 1
            self.max_pending_intents = max(self.max_pending_intents, 1)
            self.task_counters_changed.emit()
            return True
        self._start_listening(intent)
        return True

    def _start_listening(self, intent: ListeningIntent) -> None:
        assert self.source is not None
        task = ListeningTask(intent, self.source)
        task.signals.completed.connect(self._listening_completed)
        task.signals.failed.connect(self._listening_failed)
        self._active_tasks = 1
        self.requested_task_count += 1
        self.max_concurrent_tasks = max(self.max_concurrent_tasks, self._active_tasks)
        self.thread_pool.start(task)
        self.task_counters_changed.emit()

    @Slot(object, object)
    def _listening_completed(self, generation_key: object, result: object) -> None:
        self._active_tasks = 0
        self.completed_task_count += 1
        if (
            self._listening_intent is None
            or generation_key != self._listening_intent.generation_key
            or self._closing
        ):
            self.stale_results_rejected += 1
        elif isinstance(result, AnalogMonitorResult):
            self._listening_result = result
            self.audio_playback.load(result.pcm16)
            self.window.set_listening_result(result, audio_available=self.audio_playback.available)
        self.task_counters_changed.emit()
        self._dispatch_pending_intent()

    @Slot(object, str)
    def _listening_failed(self, generation_key: object, code: str) -> None:
        self._active_tasks = 0
        self.failed_task_count += 1
        if self._listening_intent is not None and generation_key == self._listening_intent.generation_key:
            self.window.listening_state.setText(ERROR_TEXT.get(code, TEXT["listening_failed"]))
            self.window.prepare_listening_button.setEnabled(self._selected_event_id is not None)
        self.task_counters_changed.emit()
        self._dispatch_pending_intent()

    @Slot()
    def play_listening(self) -> None:
        if not self.audio_playback.play():
            self.window.set_audio_availability(False)

    @Slot()
    def pause_listening(self) -> None:
        self.audio_playback.pause()

    @Slot()
    def stop_listening(self) -> None:
        self.audio_playback.stop()

    @Slot()
    def export_listening_wav(self) -> bool:
        if self._listening_result is None or self._listening_intent is None or self._active_tasks:
            return False
        filename, _ = QFileDialog.getSaveFileName(
            self.window,
            TEXT["export_wav"],
            "dinleme.wav",
            TEXT["wav_filter"],
        )
        if not filename:
            return False
        task = WavExportTask(
            self._listening_intent.generation_key,
            Path(filename),
            self._listening_result.pcm16,
        )
        task.signals.completed.connect(self._wav_export_completed)
        task.signals.failed.connect(self._wav_export_failed)
        self._active_tasks = 1
        self.requested_task_count += 1
        self.max_concurrent_tasks = max(self.max_concurrent_tasks, self._active_tasks)
        self.thread_pool.start(task)
        self.task_counters_changed.emit()
        return True

    @Slot(object)
    def _wav_export_completed(self, generation_key: object) -> None:
        self._active_tasks = 0
        if self._listening_intent is None or generation_key != self._listening_intent.generation_key:
            self.stale_results_rejected += 1
        else:
            self.window.show_warning(TEXT["wav_saved"])
        self.task_counters_changed.emit()
        self._dispatch_pending_intent()

    @Slot(object, str)
    def _wav_export_failed(self, generation_key: object, code: str) -> None:
        self._active_tasks = 0
        if self._listening_intent is not None and generation_key == self._listening_intent.generation_key:
            self.window.show_error(ERROR_TEXT.get(code, ERROR_TEXT["wav_write_failed"]))
        self.task_counters_changed.emit()
        self._dispatch_pending_intent()

    @Slot()
    def clear_listening(self) -> None:
        self._pending_listening = None
        self._listening_intent = None
        self._listening_result = None
        self.audio_playback.stop()
        self.window.clear_listening()

    @Slot()
    def clear_analysis(self) -> None:
        self._selected_event_id = None
        self._span = None
        self._measurement_intent = None
        self._pending_measurement = None
        self._pending_listening = None
        self.window.clear_analysis()

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
        self._pending_acquisition = None
        self._pending_measurement = None
        self._pending_listening = None
        self._measurement_intent = None
        self._refresh_pending = False
        self.playback_timer.stop()
        self.acquisition_backend.close()
        self.audio_playback.close()
        if self._active_acquisition_backend is not None:
            self._active_acquisition_backend.close()
        self.thread_pool.waitForDone()
        self._active_tasks = 0
        if self.source is not None:
            self.source.close()  # type: ignore[attr-defined]
            self.source = None
