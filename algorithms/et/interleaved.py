"""Deterministic offline listen/decide/task scheduling model.

The controller separates analysis and task windows in time. It produces a
bounded complex baseband task buffer for mathematical verification only; no
device, transport, or RF transmit backend is present in this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt


InterleavedScenario = Literal["absent", "present", "intermittent", "edge"]


@dataclass(frozen=True)
class InterleavedConfig:
    scenario: InterleavedScenario = "present"
    sample_rate_hz: int = 48_000
    target_offset_hz: float = 4_000.0
    analysis_bandwidth_hz: float = 750.0
    window_samples: int = 512
    windows: int = 8
    threshold_on: float = 0.12
    threshold_off: float = 0.08
    consecutive_windows: int = 2
    response_delay_windows: int = 1
    task_windows: int = 1
    guard_windows: int = 1
    output_peak: float = 0.70
    seed: int = 2026

    def __post_init__(self) -> None:
        if self.sample_rate_hz < 8_000 or self.window_samples < 64 or not 1 <= self.windows <= 128:
            raise ValueError("offline interleaved frame bounds are invalid")
        if not 0 < self.analysis_bandwidth_hz < self.sample_rate_hz:
            raise ValueError("analysis band is invalid")
        if not 0 < self.threshold_off <= self.threshold_on:
            raise ValueError("hysteresis thresholds are invalid")
        if not 1 <= self.consecutive_windows <= self.windows:
            raise ValueError("confirmation window bound is invalid")
        if not 1 <= self.response_delay_windows <= self.windows:
            raise ValueError("response delay window bound is invalid")
        if not 1 <= self.task_windows <= self.windows or not 1 <= self.guard_windows <= self.windows:
            raise ValueError("task or guard window bound is invalid")
        if not 0.0 < self.output_peak <= 0.90:
            raise ValueError("offline task output peak is invalid")
        if abs(self.target_offset_hz) + self.analysis_bandwidth_hz / 2 >= self.sample_rate_hz / 2:
            raise ValueError("analysis band exceeds Nyquist")


@dataclass(frozen=True)
class InterleavedWindow:
    index: int
    state: str
    measured_band_power: float | None
    decision: str
    confirmation_count: int
    task_active: bool
    output_peak: float


@dataclass(frozen=True)
class InterleavedResult:
    analysis_samples: npt.NDArray[np.complex128]
    task_output_samples: npt.NDArray[np.complex128]
    task_gate: npt.NDArray[np.bool_]
    sample_rate_hz: int
    scenario: str
    windows: tuple[InterleavedWindow, ...]
    timeline: tuple[str, ...]
    task_activation_count: int
    task_window_count: int
    listen_window_count: int
    response_delay_window_count: int
    guard_window_count: int
    final_state: str
    provenance: str = "DETERMİNİSTİK OFFLINE GİRİŞ"

    @property
    def duration_seconds(self) -> float:
        return self.analysis_samples.size / self.sample_rate_hz

    @property
    def task_duty_cycle(self) -> float:
        return self.task_window_count / len(self.windows)

    @property
    def samples(self) -> npt.NDArray[np.complex128]:
        """Compatibility alias for the deterministic analysis input."""

        return self.analysis_samples


class InterleavedTaskController:
    """Windowed task controller over deterministic local analysis input."""

    def run(self, config: InterleavedConfig) -> InterleavedResult:
        rng = np.random.default_rng(config.seed)
        target_latched = False
        confirmations = 0
        remaining_delay = 0
        remaining_task = 0
        remaining_guard = 0
        activations = 0
        analysis_frames: list[npt.NDArray[np.complex128]] = []
        output_frames: list[npt.NDArray[np.complex128]] = []
        gate_frames: list[npt.NDArray[np.bool_]] = []
        results: list[InterleavedWindow] = []
        timeline: list[str] = []

        for index, amplitude in enumerate(self._scenario_amplitudes(config)):
            analysis_frame = self._build_input_frame(config, rng, index, amplitude)
            output_frame = np.zeros(config.window_samples, dtype=np.complex128)
            output_gate = np.zeros(config.window_samples, dtype=np.bool_)
            measured: float | None = None
            task_active = False

            if remaining_task:
                state = "GÖREV"
                decision = "GÖREV ETKİN"
                task_active = True
                activations += int(remaining_task == config.task_windows)
                output_frame = self._build_task_frame(config, index)
                output_gate.fill(True)
                remaining_task -= 1
                if remaining_task == 0:
                    remaining_guard = config.guard_windows
            elif remaining_guard:
                state = "KORUMA"
                decision = "ÇIKIŞ KAPALI"
                confirmations = 0
                target_latched = False
                remaining_guard -= 1
            elif remaining_delay:
                state = "GECİKME"
                decision = "GÖREV BEKLİYOR"
                confirmations = 0
                remaining_delay -= 1
                if remaining_delay == 0:
                    remaining_task = config.task_windows
            else:
                state = "DİNLE"
                measured = self._measure_band_power(analysis_frame, config)
                threshold = config.threshold_off if target_latched else config.threshold_on
                detected = measured >= threshold
                confirmations = confirmations + 1 if detected else 0
                decision = "AKTİF" if detected else "PASİF"
                target_latched = detected
                if confirmations >= config.consecutive_windows:
                    required = config.response_delay_windows + config.task_windows + config.guard_windows
                    available = config.windows - index - 1
                    if available >= required:
                        remaining_delay = config.response_delay_windows
                        decision = "ONAYLANDI"
                    else:
                        decision = "SÜRE YETERSİZ"
                    confirmations = 0

            timeline.append(state)
            results.append(
                InterleavedWindow(
                    index=index,
                    state=state,
                    measured_band_power=measured,
                    decision=decision,
                    confirmation_count=confirmations,
                    task_active=task_active,
                    output_peak=float(np.max(np.abs(output_frame))),
                )
            )
            analysis_frames.append(analysis_frame)
            output_frames.append(output_frame)
            gate_frames.append(output_gate)

        analysis_samples = np.concatenate(analysis_frames).astype(np.complex128, copy=False)
        task_output_samples = np.concatenate(output_frames).astype(np.complex128, copy=False)
        task_gate = np.concatenate(gate_frames).astype(np.bool_, copy=False)
        analysis_samples.setflags(write=False)
        task_output_samples.setflags(write=False)
        task_gate.setflags(write=False)
        state_counts = {state: timeline.count(state) for state in ("DİNLE", "GECİKME", "GÖREV", "KORUMA")}
        return InterleavedResult(
            analysis_samples=analysis_samples,
            task_output_samples=task_output_samples,
            task_gate=task_gate,
            sample_rate_hz=config.sample_rate_hz,
            scenario=config.scenario,
            windows=tuple(results),
            timeline=tuple(timeline),
            task_activation_count=activations,
            task_window_count=state_counts["GÖREV"],
            listen_window_count=state_counts["DİNLE"],
            response_delay_window_count=state_counts["GECİKME"],
            guard_window_count=state_counts["KORUMA"],
            final_state=timeline[-1],
        )

    @staticmethod
    def _scenario_amplitudes(config: InterleavedConfig) -> tuple[float, ...]:
        patterns: dict[str, tuple[float, ...]] = {
            "absent": (0.0,),
            "present": (0.50,),
            "intermittent": (0.50, 0.0, 0.50, 0.50, 0.0, 0.50, 0.50),
            "edge": (0.36, 0.30, 0.36, 0.30, 0.36, 0.30),
        }
        values = patterns[config.scenario]
        return tuple(values[index % len(values)] for index in range(config.windows))

    @staticmethod
    def _build_input_frame(
        config: InterleavedConfig,
        rng: np.random.Generator,
        index: int,
        amplitude: float,
    ) -> npt.NDArray[np.complex128]:
        time = (np.arange(config.window_samples, dtype=np.float64) + index * config.window_samples) / config.sample_rate_hz
        noise = 0.035 * (rng.normal(size=config.window_samples) + 1j * rng.normal(size=config.window_samples))
        target = amplitude * np.exp(2j * np.pi * config.target_offset_hz * time)
        return np.asarray(noise + target, dtype=np.complex128)

    @staticmethod
    def _build_task_frame(config: InterleavedConfig, index: int) -> npt.NDArray[np.complex128]:
        time = (np.arange(config.window_samples, dtype=np.float64) + index * config.window_samples) / config.sample_rate_hz
        return np.asarray(config.output_peak * np.exp(2j * np.pi * config.target_offset_hz * time), dtype=np.complex128)

    @staticmethod
    def _measure_band_power(frame: npt.NDArray[np.complex128], config: InterleavedConfig) -> float:
        spectrum = np.fft.fftshift(np.fft.fft(frame)) / frame.size
        frequencies = np.fft.fftshift(np.fft.fftfreq(frame.size, d=1.0 / config.sample_rate_hz))
        in_band = np.abs(frequencies - config.target_offset_hz) <= config.analysis_bandwidth_hz / 2.0
        return float(np.sum(np.abs(spectrum[in_band]) ** 2))


# Compatibility import for existing laboratory callers.
InterleavedJammingEngine = InterleavedTaskController
