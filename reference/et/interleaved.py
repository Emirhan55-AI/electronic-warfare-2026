"""Deterministic offline Listen → Decide → Task → Guard model.

It evaluates synthetic local analysis windows.  The model has no signal-output
or transmission code and is intended to exercise the task state machine only.
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
        if abs(self.target_offset_hz) + self.analysis_bandwidth_hz / 2 >= self.sample_rate_hz / 2:
            raise ValueError("analysis band exceeds Nyquist")


@dataclass(frozen=True)
class InterleavedWindow:
    index: int
    measured_band_power: float
    decision: str
    confirmation_count: int
    task_active: bool


@dataclass(frozen=True)
class InterleavedResult:
    samples: npt.NDArray[np.complex128]
    sample_rate_hz: int
    scenario: str
    windows: tuple[InterleavedWindow, ...]
    timeline: tuple[str, ...]
    task_activation_count: int
    final_state: str
    provenance: str = "DETERMİNİSTİK OFFLINE GİRİŞ"

    @property
    def duration_seconds(self) -> float:
        return self.samples.size / self.sample_rate_hz


class InterleavedJammingEngine:
    """Energy-threshold task controller over deterministic local baseband."""

    def run(self, config: InterleavedConfig) -> InterleavedResult:
        rng = np.random.default_rng(config.seed)
        active = False
        confirmations = 0
        activations = 0
        frames: list[npt.NDArray[np.complex128]] = []
        results: list[InterleavedWindow] = []
        timeline: list[str] = ["DİNLE"]
        for index, amplitude in enumerate(self._scenario_amplitudes(config)):
            frame = self._build_input_frame(config, rng, index, amplitude)
            frames.append(frame)
            measured = self._measure_band_power(frame, config)
            threshold = config.threshold_off if active else config.threshold_on
            detected = measured >= threshold
            confirmations = confirmations + 1 if detected else 0
            task_active = confirmations >= config.consecutive_windows
            decision = "AKTİF" if detected else "PASİF"
            timeline.append("KARAR")
            if task_active:
                activations += 1
                timeline.extend(("GÖREV", "GUARD", "DİNLE"))
                # The guard closes the current task cycle, while hysteresis is
                # retained for the next measurement decision.
                confirmations = 0
                active = True
            else:
                timeline.append("DİNLE")
                active = detected
            results.append(InterleavedWindow(index, measured, decision, confirmations, task_active))
        samples = np.concatenate(frames).astype(np.complex128, copy=False)
        samples.setflags(write=False)
        return InterleavedResult(
            samples=samples,
            sample_rate_hz=config.sample_rate_hz,
            scenario=config.scenario,
            windows=tuple(results),
            timeline=tuple(timeline),
            task_activation_count=activations,
            final_state="DİNLE",
        )

    @staticmethod
    def _scenario_amplitudes(config: InterleavedConfig) -> tuple[float, ...]:
        patterns: dict[str, tuple[float, ...]] = {
            "absent": (0.0,),
            "present": (0.50,),
            "intermittent": (0.50, 0.0, 0.50, 0.50, 0.0, 0.50, 0.50),
            # 0.36 is above the on threshold and 0.30 stays above the lower
            # hysteresis threshold once a target has become active.
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
    def _measure_band_power(frame: npt.NDArray[np.complex128], config: InterleavedConfig) -> float:
        spectrum = np.fft.fftshift(np.fft.fft(frame)) / frame.size
        frequencies = np.fft.fftshift(np.fft.fftfreq(frame.size, d=1.0 / config.sample_rate_hz))
        in_band = np.abs(frequencies - config.target_offset_hz) <= config.analysis_bandwidth_hz / 2.0
        return float(np.sum(np.abs(spectrum[in_band]) ** 2))
