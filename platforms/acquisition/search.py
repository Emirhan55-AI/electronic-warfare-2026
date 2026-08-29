"""HackRF receive adapter for the platform-independent search planner."""

from __future__ import annotations

from typing import Callable

from algorithms.p0.hackrf_search import HackRFSearchPlanner, HackRFTuningWindowPlan
from algorithms.p0.search import SearchRequest, TuningWindow

from .contracts import HackRFBackend, RXConfig
from .rx_sources import HackRFHostRxSource


class HackRFSearchBackend:
    """Run a search plan through a real, bounded HackRF receive source."""

    backend_name = "HACKRF/HOST"

    def __init__(
        self,
        backend: HackRFBackend,
        *,
        device_serial: str,
        planner: HackRFSearchPlanner,
        progress_callback: Callable[[int, int, HackRFTuningWindowPlan], None] | None = None,
    ) -> None:
        if backend.backend_kind != "real":
            raise ValueError("HackRF arama backend'i yalnız gerçek RX backend sözleşmesini kabul eder.")
        self.backend = backend
        self.device_serial = device_serial
        self.planner = planner
        self.progress_callback = progress_callback
        self.last_progress = (0, 0)

    def acquire(self, request: SearchRequest) -> tuple[TuningWindow, ...]:
        plan = self.planner.plan(request)
        windows: list[TuningWindow] = []
        self.last_progress = (0, len(plan.windows))
        for item in plan.windows:
            config = RXConfig(
                center_frequency_hz=item.center_frequency_hz,
                sample_rate_hz=self.planner.profile.sample_rate_hz,
                sample_count=self.planner.profile.sample_count,
                device_serial=self.device_serial,
            )
            source = HackRFHostRxSource(self.backend, config, queue_capacity=4)
            try:
                frames = tuple(source.read() for _ in range(config.sample_count // 4096))
            finally:
                source.stop()
            if any(frame is None for frame in frames):
                raise RuntimeError("HackRF bounded RX beklenen frame sayısını üretmedi.")
            windows.append(
                TuningWindow(
                    f"hackrf-window-{item.index:04d}",
                    item.center_frequency_hz,
                    self.planner.profile.sample_rate_hz,
                    tuple(frame.samples for frame in frames if frame is not None),
                    provenance="LIVE_HACKRF",
                    excluded_frequency_ranges_hz=((
                        item.center_frequency_hz - self.planner.profile.dc_exclusion_hz,
                        item.center_frequency_hz + self.planner.profile.dc_exclusion_hz,
                    ),),
                )
            )
            self.last_progress = (len(windows), len(plan.windows))
            if self.progress_callback is not None:
                self.progress_callback(len(windows), len(plan.windows), item)
        return tuple(windows)
