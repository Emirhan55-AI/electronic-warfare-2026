"""Normalized replay and HackRF-host RX sources for the P0 PC boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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
    """Bounded receive-only adapter; callers run `read` outside the UI thread."""

    def __init__(self, backend: HackRFBackend, config: RXConfig) -> None:
        self._backend = backend
        self._config = config
        self._capture_source: BoundedCI8FrameSource | None = None
        self._capture_index = 0
        self._sequence = 0
        self._stopped = False

    def read(self) -> NormalizedIQFrame | None:
        if self._stopped:
            return None
        if self._capture_source is None or self._capture_index >= self._capture_source.frame_count:
            capture = self._backend.capture(self._config)
            self._capture_source = BoundedCI8FrameSource(capture)
            self._capture_index = 0
        samples = self._capture_source.read_frame(self._capture_index)
        self._capture_index += 1
        frame = NormalizedIQFrame(
            self._sequence,
            self._config.sample_rate_hz,
            self._config.center_frequency_hz,
            samples,
            "LIVE HACKRF",
        )
        self._sequence = (self._sequence + 1) & 0xFFFFFFFF
        return frame

    def stop(self) -> None:
        self._stopped = True
        self._backend.cancel()
