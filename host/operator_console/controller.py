"""Single-worker controller for recorded-frame navigation and DSP."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from PySide6.QtCore import QElapsedTimer, QObject, QSignalBlocker, QRunnable, QThreadPool, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import QFileDialog
import numpy as np

from host.acquisition.contracts import (
    AcquisitionError,
    CaptureResult,
    DeviceStatus,
    EDRXDeviceConfig,
    HackRFBackend,
    RXConfig,
    ToolInventory,
    load_ed_rx_config,
)
from host.acquisition.hackrf import RealHackRFBackend
from host.acquisition.source import BoundedCI8FrameSource
from reference.detection import DetectionEvent, DetectionFrameResult, DetectionRegion
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
from reference.p0.models import CandidateRegion, P0ParameterResult
from reference.p0.parameters import ParameterExtractor as P0ParameterExtractor
from reference.p0.search import P0SearchEngine, ReplaySearchBackend, TuningWindow
from reference.spectrum import (
    ExponentialPowerAverager,
    SigMFFrameSource,
    SpectrumResult,
)
from reference.sigmf import HACKRF_REPLAY_DESCRIPTION

from .audio_playback import AudioPlayback
from .main_window import MainWindow
from .ui_text import ERROR_TEXT, TEXT


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class P0MeasurementIntent:
    generation: int
    configuration_generation: int
    event: DetectionEvent
    frame_index: int
    neighboring_regions: tuple[DetectionRegion, ...]
    recorded_hackrf_replay: bool = False

    @property
    def generation_key(self) -> tuple[int, int, int, int]:
        return (
            self.generation,
            self.configuration_generation,
            int(self.event.event_id),
            self.frame_index,
        )


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
    """Read and demodulate twenty continuous seconds outside the UI thread."""

    def __init__(self, intent: ListeningIntent, source: object, *, allow_short_fixture: bool = False) -> None:
        super().__init__()
        self.intent = intent
        self.source = source
        self.allow_short_fixture = allow_short_fixture
        self.signals = ListeningTaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            sample_rate = float(self.source.sample_rate_hz)
            start_sample = self.intent.start_frame * int(self.source.frame_length)
            sample_count = int(20.0 * sample_rate)
            available_samples = int(self.source.frame_count) * int(self.source.frame_length) - start_sample
            if available_samples < sample_count:
                if not self.allow_short_fixture or available_samples < 4 * int(self.source.frame_length):
                    raise ValueError("insufficient_iq")
                frames = tuple(self.source.read_frame(self.intent.start_frame + offset) for offset in range(4))
                config = AnalogMonitorConfig(
                    self.intent.mode,
                    sample_rate,
                    self.intent.center_offset_hz,
                    self.intent.channel_bandwidth_hz,
                )
                result = AnalogMonitor().process(frames, config, volume=self.intent.volume)
                self.signals.completed.emit(self.intent.generation_key, result)
                return
            # Bounded one-second reads retain DSP state in process_continuous.
            block_size = int(sample_rate)
            blocks = tuple(
                self.source.read_samples(start_sample + offset, min(block_size, sample_count - offset))
                for offset in range(0, sample_count, block_size)
            )
            config = AnalogMonitorConfig(
                self.intent.mode,
                float(self.source.sample_rate_hz),
                self.intent.center_offset_hz,
                self.intent.channel_bandwidth_hz,
            )
            result = AnalogMonitor().process_continuous(blocks, config, volume=self.intent.volume)
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
                    else DeviceStatus("NOT_EXERCISED", reason_code="tools_unavailable")
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


class P0MeasurementTask(QRunnable):
    """Measure one selected, identity-bound replay event outside the UI thread."""

    def __init__(self, intent: P0MeasurementIntent, source: object, processor: object) -> None:
        super().__init__()
        self.intent = intent
        self.source = source
        self.processor = processor
        self.signals = MeasurementTaskSignals()

    @staticmethod
    def _candidate(region: DetectionRegion, scale: float) -> CandidateRegion:
        return CandidateRegion(
            int(region.start_bin),
            int(region.end_bin),
            int(region.peak_bin),
            float(region.peak_power) * scale,
            float(region.local_noise_power) * scale,
            float(region.threshold_power) * scale,
        )

    @Slot()
    def run(self) -> None:
        try:
            samples = self.source.read_frame(self.intent.frame_index)
            spectrum = self.processor.process(
                samples,
                sample_rate_hz=self.source.sample_rate_hz,
                center_frequency_hz=self.source.center_frequency_hz,
            )
            shifted_power = np.fft.fftshift(spectrum.fft_power_unshifted)
            scale = float((spectrum.frame_length * spectrum.window_coherent_gain) ** 2)
            candidate = self._candidate(self.intent.event.region, scale)
            neighbors = tuple(self._candidate(region, scale) for region in self.intent.neighboring_regions)
            result = P0ParameterExtractor().extract(
                frame_id=self.intent.frame_index,
                iq=samples,
                shifted_power=shifted_power,
                sample_rate_hz=spectrum.sample_rate_hz,
                center_frequency_hz=spectrum.center_frequency_hz,
                candidate=candidate,
                confirmed=True,
                provenance="REPLAY",
                backend=(
                    "HACKRF KAYDI / REPLAY → PHASE-03 aday + P0 parametre referansı"
                    if self.intent.recorded_hackrf_replay
                    else "REPLAY → PHASE-03 aday + P0 parametre referansı"
                ),
                neighboring_candidates=neighbors,
            )
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
        ed_rx_config: EDRXDeviceConfig | None = None,
        test_backend_factory: Callable[[], HackRFBackend] | None = None,
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
        # Render timer: independent of playback speed, drives UI updates at target FPS.
        # latest-frame-wins: _task_completed stores result in _pending_render;
        # _render_tick flushes the pending result to the UI on each tick.
        self._render_timer = QTimer(self)
        self._render_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._render_timer.timeout.connect(self._render_tick)
        self._render_fps: int = 30
        self._pending_render: object | None = None  # (line_display, result) tuple
        self._render_elapsed = QElapsedTimer()
        self._last_render_ms: float = 0.0
        self._rendered_frame_count: int = 0
        self._fps_elapsed = QElapsedTimer()
        self._fps_elapsed.start()
        self._fps_window_count: int = 0
        self._actual_fps: float = 0.0
        self.source: object | None = None
        self.source_factory = source_factory
        self.acquisition_backend = acquisition_backend or RealHackRFBackend()
        self.ed_rx_config = ed_rx_config or load_ed_rx_config()
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
        self._pending_measurement: MeasurementIntent | P0MeasurementIntent | None = None
        self._pending_acquisition: tuple[int, Literal["probe", "capture", "test_capture"], HackRFBackend, RXConfig] | None = None
        self._pending_listening: ListeningIntent | None = None
        self._listening_intent: ListeningIntent | None = None
        self._listening_result: AnalogMonitorResult | None = None
        self._listening_revision = 0
        self._source_is_fixture = False
        self._recorded_hackrf_replay = False
        self._measurement_intent: MeasurementIntent | P0MeasurementIntent | None = None
        self._selected_event_id: int | None = None
        self._automatic_measurement_event_id: int | None = None
        self._automatic_scan_remaining = 0
        self._span: AnalysisSpan | None = None
        self._span_revision = 0
        self._configuration_generation = 0
        self._event_observation_history: dict[int, list[bool]] = {}
        self._closing = False
        self._closing_event = threading.Event()
        self._hackrf_device_ready = False
        self._active_acquisition_backend: HackRFBackend | None = None
        self.playing = False
        self.window.set_hackrf_configuration(self.ed_rx_config.serial)

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
        window.df_power_measure_requested.connect(self.measure_df_power)
        window.demod_combo.currentIndexChanged.connect(self._listening_config_changed)
        window.listen_offset_spin.valueChanged.connect(self._listening_config_changed)
        window.listen_bandwidth_spin.valueChanged.connect(self._listening_config_changed)
        window.listen_volume_slider.valueChanged.connect(self._listening_config_changed)
        window.listening_spectrum.carrier_selected.connect(self._listening_carrier_selected)
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
        self._recorded_hackrf_replay = False
        self.window.set_replay_source_badge("SİGMF KAYDI / REPLAY")
        self.window.show_empty()
        self.window.set_acquisition_mode(mode)

    @Slot()
    def probe_hackrf(self) -> bool:
        if self._closing or self.window.source_kind != "hackrf":
            return False
        self._hackrf_device_ready = False
        self.window.set_hackrf_state("searching")
        config = RXConfig(**self.window.hackrf_settings, device_serial=self.ed_rx_config.serial)
        return self._queue_acquisition("probe", self.acquisition_backend, config)

    @Slot()
    def start_hackrf_capture(self) -> bool:
        if self._closing or self.window.source_kind != "hackrf" or not self._hackrf_device_ready:
            return False
        try:
            config = RXConfig(**self.window.hackrf_settings, device_serial=self.ed_rx_config.serial)
        except AcquisitionError as exc:
            self.window.show_error(ERROR_TEXT.get(exc.code, TEXT["source_error"]))
            return False
        self.window.set_hackrf_state("capture_starting")
        return self._queue_acquisition("capture", self.acquisition_backend, config)

    @Slot()
    def open_deterministic_source(self) -> bool:
        if self._closing or self.window.source_kind != "deterministic_test" or self.test_backend_factory is None:
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
        LOGGER.info("SigMF kaynağı açma isteği: %s", metadata_path)
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
        self._automatic_measurement_event_id = None
        self.clear_analysis()
        self.clear_listening()
        self.averager.reset()
        self.runtime_pipeline.detection.reset()
        self._recorded_hackrf_replay = (
            getattr(source, "source_description", None) == HACKRF_REPLAY_DESCRIPTION
        )
        self.window.set_replay_source_badge(
            "HACKRF KAYDI / REPLAY" if self._recorded_hackrf_replay else "SİGMF KAYDI / REPLAY"
        )
        self.window.set_source(label, source.report)  # type: ignore[attr-defined]
        frame_count = int(source.frame_count)  # type: ignore[attr-defined]
        self._automatic_scan_remaining = 0
        search_frame_count = min(frame_count, 8)
        if search_frame_count >= 2:
            search_frames = tuple(source.read_frame(index) for index in range(search_frame_count))  # type: ignore[attr-defined]
            search_window = TuningWindow(
                window_id=f"sigmf:{Path(label).name}:0-{search_frame_count - 1}",
                center_frequency_hz=float(source.center_frequency_hz),  # type: ignore[attr-defined]
                sample_rate_hz=float(source.sample_rate_hz),  # type: ignore[attr-defined]
                frames=search_frames,
                provenance="REPLAY",
            )
            self.window.set_p0_search_engine(P0SearchEngine(ReplaySearchBackend((search_window,))))
            LOGGER.info("Replay hakem arama backend'i bağlandı: %s bounded kare.", search_frame_count)
        else:
            self.window.set_p0_search_engine(None)
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
            if not inventory.receive_available or device.state == "TOOLCHAIN_UNAVAILABLE":
                self.window.set_hackrf_state("tools_missing")
            elif device.state == "NO_DEVICE":
                self.window.set_hackrf_state("device_missing")
            elif device.state in {"ONE_DEVICE", "MULTIPLE_DEVICES"}:
                serial = self.ed_rx_config.serial
                if serial is None:
                    self.window.set_hackrf_state("serial_unassigned")
                elif any(identity.serial.casefold() == serial.casefold() for identity in device.devices):
                    self._hackrf_device_ready = True
                    self.window.set_hackrf_state("device_ready")
                else:
                    self.window.set_hackrf_state("configured_device_missing")
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
                self.window.set_hackrf_runtime(
                    center_frequency_hz=result.config.center_frequency_hz,
                    sample_rate_hz=result.config.sample_rate_hz,
                )
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
            LOGGER.warning("Replay baslatılamadı: kaynak yok.")
            return
        LOGGER.info("Replay oynatma baslatildı: frame=%s, hiz=%s fps.", self.current_index, self.window.speed_spin.value())
        self.playing = True
        if self._selected_event_id is None:
            self._automatic_scan_remaining = int(self.source.frame_count)
        self.window.set_state("playing")
        self._speed_changed(self.window.speed_spin.value())
        self.playback_timer.start()
        self._render_timer.start(max(1, round(1000 / self._render_fps)))
        self._fps_elapsed.restart()
        self._fps_window_count = 0
        if self.last_result is None:
            self.request_current_frame()

    @Slot()
    def pause(self) -> None:
        self.playing = False
        self._automatic_scan_remaining = 0
        self.playback_timer.stop()
        self._render_timer.stop()
        if self.source is not None:
            self.window.set_state("paused")

    @Slot()
    def stop(self) -> None:
        if self.source is None:
            return
        self.playing = False
        self._automatic_scan_remaining = 0
        self.playback_timer.stop()
        self._render_timer.stop()
        self._pending_render = None
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

    @Slot()
    def measure_df_power(self) -> None:
        """Persist one bounded power average from the actually active IQ source."""
        if self.source is None or self.last_result is None:
            self.window.set_df_power_measurement_unavailable(
                "GÜÇ ÖLÇ için seçili IQ kaynağından işlenmiş bir kare yok; kayıt oluşturulmadı."
            )
            return
        linear_power = np.asarray(self.last_result.display.bin_power_fs2, dtype=np.float64)
        finite_power = linear_power[np.isfinite(linear_power) & (linear_power > 0.0)]
        if finite_power.size == 0:
            self.window.set_df_power_measurement_unavailable(
                "GÜÇ ÖLÇ için geçerli bounded güç verisi yok; kayıt oluşturulmadı."
            )
            return
        relative_power_db = float(10.0 * np.log10(np.mean(finite_power)))
        selected_kind = str(self.window.source_type_combo.currentData())
        source = {
            "sigmf": "REPLAY",
            "deterministic_test": "HOST/SYNTHETIC",
            "hackrf": "LIVE RX",
        }.get(selected_kind, "BİLİNMEYEN IQ KAYNAĞI")
        if selected_kind == "sigmf" and self._recorded_hackrf_replay:
            source = "HACKRF KAYDI / GERÇEK AÇI-GÜÇ ÖLÇÜMÜ"
        self.window.save_selected_iq_power(
            relative_power_db=relative_power_db,
            frequency_hz=float(self.last_result.center_frequency_hz),
            source=source,
        )

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
            # Store latest result for render tick; if render timer fires between
            # two completed tasks it will display the most recent frame (latest-frame-wins).
            self._pending_render = (line_display, result)
            # Non-visual backend state is always updated immediately.
            self.window.set_detection_result(
                self.last_detection,
                selected_event_id=self._selected_event_id,
            )
            self._select_and_measure_first_ready_event()
            self.window.set_parameter_result(self.last_parameters)
            if self._selected_event_id is not None:
                self._refresh_selected_event()
            assert self.source is not None
            self.window.set_frame_position(index, self.source.frame_count)
            self.frame_rendered.emit(index, elapsed_seconds)
            # If not playing (paused/single-frame), flush immediately.
            if not self.playing:
                self._flush_render()
        pending = self._refresh_pending
        self._refresh_pending = False
        self.task_counters_changed.emit()
        if self._dispatch_pending_intent():
            return
        if (
            self._automatic_scan_remaining > 0
            and self._selected_event_id is None
            and self.source is not None
            and not self._closing
        ):
            self._automatic_scan_remaining -= 1
            if self._automatic_scan_remaining > 0:
                self.current_index = (self.current_index + 1) % self.source.frame_count
                self.request_current_frame()
                return
        elif self._selected_event_id is not None:
            self._automatic_scan_remaining = 0
        if pending and not self._closing:
            self.request_current_frame()

    def _flush_render(self) -> None:
        """Push the pending render result to the UI. Called by render timer or immediately when paused."""
        if self._pending_render is None:
            return
        line_display, result = self._pending_render  # type: ignore[misc]
        self._pending_render = None
        self.window.spectrum_view.update_spectrum(
            line_display,
            result.spectrum.display,
            append_waterfall=True,
            detection_result=self.last_detection,
            spectrum_result=result.spectrum,
            parameter_result=self.last_parameters,
        )
        # Track actual FPS.
        self._rendered_frame_count += 1
        self._fps_window_count += 1
        elapsed_fps = self._fps_elapsed.elapsed()
        if elapsed_fps >= 1000:
            self._actual_fps = self._fps_window_count * 1000.0 / elapsed_fps
            self._fps_window_count = 0
            self._fps_elapsed.restart()
            if hasattr(self.window, "status_fps_label"):
                self.window.status_fps_label.setText(f"{self._actual_fps:.0f} fps")

    @Slot()
    def _render_tick(self) -> None:
        """Called by render_timer; flushes latest available frame to the display."""
        self._flush_render()

    def _select_and_measure_first_ready_event(self) -> None:
        """Run the existing selection/measurement path once a usable event is available."""
        if self.last_detection is None:
            return
        if self._selected_event_id is None:
            ready = sorted(
                (
                    event for event in self.last_detection.active_events
                    if event.state == "confirmed" and event.observed_this_frame
                ),
                key=lambda event: (-event.region.peak_to_noise_db, event.event_id),
            )
            if not ready:
                return
            event_id = int(ready[0].event_id)
            for row in range(self.window.detection_list.count()):
                item = self.window.detection_list.item(row)
                if int(item.data(Qt.ItemDataRole.UserRole)) == event_id:
                    self.window.detection_list.setCurrentRow(row)
                    break
        if self._selected_event_id is None or self._automatic_measurement_event_id == self._selected_event_id:
            return
        if self.e1_capability is not None:
            observations = tuple(self._event_observation_history.get(self._selected_event_id, ()))
            if self.current_index < 3 or len(observations) != 4 or not all(observations):
                return
        if self.request_measurement():
            self._automatic_measurement_event_id = self._selected_event_id

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
        interval = max(1, round(1000 / frames_per_second))
        self.playback_timer.setInterval(interval)
        # Keep render FPS >= playback FPS (cap at 60 for stability)
        self._render_fps = min(60, max(frames_per_second, 30))
        self._render_timer.setInterval(max(1, round(1000 / self._render_fps)))

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
            LOGGER.info("Tespit seçimi temizlendi; etkin seçim yok.")
            self.clear_analysis()
            self.clear_listening()
            return
        event_id = int(items[0].data(Qt.ItemDataRole.UserRole))
        event = next((item for item in self.last_detection.active_events if item.event_id == event_id), None)
        if event is None or event.state != "confirmed" or not event.observed_this_frame:
            LOGGER.warning("Tespit seçimi reddedildi: olay etkin/doğrulanmış değil (id=%s).", event_id)
            self.clear_analysis()
            self.clear_listening()
            return
        self._selected_event_id = event_id
        LOGGER.info("Doğrulanmış replay olayı seçildi: id=%s, frame=%s.", event_id, self.current_index)
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
        self.window.measure_button.setEnabled(True)
        self._render_selected_event_spectrum(event, span)
        if span is None:
            self._span = None
            self.window.span_value.setText(TEXT["manual_span_available"])
            return
        self._span = span
        self.window.set_analysis_span(span.lower_shifted_bin, span.upper_shifted_bin, span.provenance)

    def _render_selected_event_spectrum(self, event: DetectionEvent, span: AnalysisSpan | None) -> None:
        """Bind the selected event to its current real replay spectrum, never a substitute curve."""
        if self.last_result is None:
            return
        spectrum = self.window.analysis_spectrum
        spectrum.set_spectrum(self.last_result.display)
        spectrum.set_event_markers(
            lower_hz=float(event.region.start_frequency_hz),
            carrier_hz=float(event.region.peak_frequency_hz),
            upper_hz=float(event.region.end_frequency_hz),
        )
        if span is not None:
            spectrum.set_span(span.lower_shifted_bin, span.upper_shifted_bin)

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
        self._render_selected_event_spectrum(event, self._span)
        self.window.measure_button.setEnabled(True)

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
        if self.source is None or self._selected_event_id is None:
            LOGGER.warning("Parametre ölçümü başlatılamadı: doğrulanmış olay seçilmedi.")
            self.window.show_measurement_rejected(TEXT["measurement_no_selection"])
            return False
        if self.e1_capability is None:
            event = next(
                (item for item in (self.last_detection.active_events if self.last_detection else ()) if item.event_id == self._selected_event_id),
                None,
            )
            if event is None or event.state != "confirmed" or not event.observed_this_frame:
                LOGGER.warning("Parametre ölçümü başlatılamadı: seçili olay artık etkin değil.")
                self.window.show_measurement_rejected(TEXT["measurement_event_unavailable"])
                return False
            intent = P0MeasurementIntent(
                self.generation,
                self._configuration_generation,
                event,
                self.current_index,
                tuple(item.region for item in self.last_detection.active_events if item.observed_this_frame),
                self._recorded_hackrf_replay,
            )
            self._measurement_intent = intent
            self.window.set_measurement_busy()
            LOGGER.info("P0 replay parametre ölçümü başlatıldı: olay=%s, frame=%s.", event.event_id, self.current_index)
            if self._active_tasks:
                self._pending_measurement = intent
                self._refresh_pending = False
                self.max_pending_intents = max(self.max_pending_intents, 1)
                return True
            self._start_measurement(intent)
            return True
        if self._span is None:
            self.window.show_measurement_rejected(TEXT["measurement_no_selection"])
            return False
        observations = tuple(self._event_observation_history.get(self._selected_event_id, ()))
        if self.current_index < 3 or len(observations) != 4 or not all(observations):
            self.window.show_measurement_rejected(TEXT["measurement_failed"] + ": " + TEXT["insufficient_quality"])
            return False
        event = next((item for item in (self.last_detection.active_events if self.last_detection else ()) if item.event_id == self._selected_event_id), None)
        if event is None or event.state != "confirmed" or not event.observed_this_frame:
            self.window.show_measurement_rejected(TEXT["measurement_event_unavailable"])
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

    def _start_measurement(self, intent: MeasurementIntent | P0MeasurementIntent) -> None:
        assert self.source is not None
        task = (
            P0MeasurementTask(intent, self.source, self.runtime_pipeline.processor)
            if isinstance(intent, P0MeasurementIntent)
            else MeasurementTask(intent, self.source, self.runtime_pipeline.processor)
        )
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
            if isinstance(result, P0ParameterResult):
                self.window.set_p0_parameter_result(result)
                self.window.analysis_spectrum.set_event_markers(
                    lower_hz=result.lower_frequency_hz,
                    carrier_hz=result.carrier_frequency_hz,
                    upper_hz=result.upper_frequency_hz,
                )
                self.window.set_measurement_complete()
                LOGGER.info("P0 replay parametre ölçümü tamamlandı: olay=%s.", result.candidate.peak_bin)
            else:
                fields = self.e1_capability.validated_fields if self.e1_capability is not None else ()
                self.window.set_operator_measurement(result, fields)
        self.task_counters_changed.emit()
        self._dispatch_pending_intent()

    @Slot(object, str)
    def _measurement_failed(self, generation_key: object, code: str) -> None:
        self._active_tasks = 0
        self.failed_task_count += 1
        if self._measurement_intent is not None and generation_key == self._measurement_intent.generation_key and not self._closing:
            self.window.measurement_state.setText(TEXT["measurement_failed"] + f": {code}")
            self.window.parameter_state.setText("Sonuç güncellenemedi")
            self.window.measure_button.setText(TEXT["start_measurement"])
            self.window.measure_button.setEnabled(self._selected_event_id is not None)
            self.window.show_error(TEXT["measurement_failed"] + f": {code}")
            LOGGER.error("Parametre ölçümü başarısız: %s", code)
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

    @Slot(float)
    def _listening_carrier_selected(self, carrier_frequency_hz: float) -> None:
        if self.source is None:
            return
        blocker = QSignalBlocker(self.window.listen_offset_spin)
        self.window.listen_offset_spin.setValue(
            (carrier_frequency_hz - float(self.source.center_frequency_hz)) / 1000.0
        )
        del blocker
        self._listening_config_changed()

    @Slot()
    def request_listening(self) -> bool:
        if self.source is None or self._selected_event_id is None or self.last_detection is None:
            LOGGER.warning("Dinleme hazırlanamadı: doğrulanmış olay seçilmedi.")
            return False
        event = next(
            (item for item in self.last_detection.active_events if item.event_id == self._selected_event_id),
            None,
        )
        if event is None or event.state != "confirmed" or not event.observed_this_frame:
            self.window.listening_state.setText(TEXT["listening_failed"])
            return False
        required_samples = int(20.0 * float(self.source.sample_rate_hz))
        start_sample = self.current_index * int(self.source.frame_length)
        if (
            not self._source_is_fixture
            and start_sample + required_samples > int(self.source.frame_count) * int(self.source.frame_length)
        ):
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
        LOGGER.info("Dinleme hazırlanıyor: olay=%s, mod=%s, frame=%s.", event.event_id, config.mode, self.current_index)
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
        task = ListeningTask(intent, self.source, allow_short_fixture=self._source_is_fixture)
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
            assert self.source is not None and self._listening_intent is not None
            self.window.set_listening_result(
                result,
                audio_available=self.audio_playback.available,
                source_sample_rate_hz=float(self.source.sample_rate_hz),
                carrier_frequency_hz=(
                    float(self.source.center_frequency_hz) + self._listening_intent.center_offset_hz
                ),
                channel_bandwidth_hz=self._listening_intent.channel_bandwidth_hz,
                backend=(
                    "HACKRF KAYDI / ANALOG REPLAY"
                    if self._recorded_hackrf_replay
                    else "REPLAY / HOST · NumPy PHASE-05"
                ),
            )
            LOGGER.info(
                "Dinleme hazır: mod=%s, süre=%.3f s, ton=%.1f Hz.",
                result.mode,
                result.audio.size / result.sample_rate_hz,
                result.dominant_tone_hz,
            )
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
