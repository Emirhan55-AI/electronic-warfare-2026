"""Normalized replay and HackRF-host RX sources for the P0 PC boundary."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Literal, Protocol

import numpy as np
import numpy.typing as npt

from .contracts import HackRFBackend, RXConfig
from .source import BoundedCI8FrameSource


@dataclass(frozen=True)
class NormalizedIQFrame:
    sequence_number: int
    sample_rate_hz: int
    center_frequency_hz: int
    samples: npt.NDArray[np.complex128]
    source: str


@dataclass(frozen=True)
class RXSourceStatistics:
    state: Literal["STOPPED", "RUNNING", "DISCONNECTED", "ERROR"]
    frames_produced: int
    frames_read: int
    dropped_frames: int
    capture_errors: int
    queue_depth: int
    last_error_code: str | None


class RxSource(Protocol):
    def read(self) -> NormalizedIQFrame | None: ...
    def stop(self) -> None: ...


class ReplayRxSource:
    def __init__(self, source: object) -> None:
        self._source = source
        self._index = 0
        self._stopped = False

    def read(self) -> NormalizedIQFrame | None:
        if self._stopped or self._index >= int(getattr(self._source, "frame_count")):
            return None
        samples = np.asarray(getattr(self._source, "read_frame")(self._index), dtype=np.complex128)
        samples.setflags(write=False)
        frame = NormalizedIQFrame(
            self._index,
            int(round(float(getattr(self._source, "sample_rate_hz")))),
            int(round(float(getattr(self._source, "center_frequency_hz")))),
            samples,
            "REPLAY",
        )
        self._index += 1
        return frame

    def stop(self) -> None:
        self._stopped = True


class HackRFHostRxSource:
    """Bounded receive-only producer with one worker and explicit backpressure."""

    def __init__(self, backend: HackRFBackend, config: RXConfig, *, queue_capacity: int = 8) -> None:
        if isinstance(queue_capacity, bool) or not isinstance(queue_capacity, int) or not 1 <= queue_capacity <= 64:
            raise ValueError("HackRF RX queue capacity must be in [1, 64]")
        self._backend = backend
        self._config = config
        self._queue: queue.Queue[NormalizedIQFrame] = queue.Queue(maxsize=queue_capacity)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._state: Literal["STOPPED", "RUNNING", "DISCONNECTED", "ERROR"] = "STOPPED"
        self._sequence = 0
        self._frames_produced = 0
        self._frames_read = 0
        self._dropped_frames = 0
        self._capture_errors = 0
        self._last_error_code: str | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._state = "RUNNING"
            self._last_error_code = None
            self._thread = threading.Thread(target=self._produce, name="HackRF-ED-RX", daemon=True)
            self._thread.start()

    def _produce(self) -> None:
        while not self._stop_event.is_set():
            try:
                capture = self._backend.capture(self._config, self._stop_event)
                source = BoundedCI8FrameSource(capture)
                for index in range(source.frame_count):
                    if self._stop_event.is_set():
                        break
                    samples = source.read_frame(index)
                    frame = NormalizedIQFrame(
                        self._sequence,
                        self._config.sample_rate_hz,
                        self._config.center_frequency_hz,
                        samples,
                        "LIVE HACKRF" if capture.backend_kind == "real" else "DETERMINISTIC TEST",
                    )
                    self._sequence = (self._sequence + 1) & 0xFFFFFFFF
                    try:
                        self._queue.put(frame, timeout=0.05)
                        self._frames_produced += 1
                    except queue.Full:
                        self._dropped_frames += 1
                source.close()
            except Exception as exc:
                code = str(getattr(exc, "code", "capture_error"))
                if self._stop_event.is_set() and code == "operation_cancelled":
                    break
                self._capture_errors += 1
                self._last_error_code = code
                self._state = "DISCONNECTED" if code in {"device_not_found", "capture_process_failed"} else "ERROR"
                break
        if self._state == "RUNNING":
            self._state = "STOPPED"

    def read(self, timeout_seconds: float = 1.0) -> NormalizedIQFrame | None:
        if self._thread is None:
            self.start()
        if self._stop_event.is_set() and self._queue.empty():
            return None
        try:
            frame = self._queue.get(timeout=timeout_seconds)
        except queue.Empty:
            if self._last_error_code is not None:
                from .contracts import AcquisitionError

                raise AcquisitionError(self._last_error_code, "HackRF RX worker capture üretemedi.")
            return None
        self._frames_read += 1
        return frame

    def stop(self) -> None:
        self._stop_event.set()
        self._backend.cancel()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._state = "STOPPED"

    @property
    def statistics(self) -> RXSourceStatistics:
        return RXSourceStatistics(
            self._state,
            self._frames_produced,
            self._frames_read,
            self._dropped_frames,
            self._capture_errors,
            self._queue.qsize(),
            self._last_error_code,
        )
