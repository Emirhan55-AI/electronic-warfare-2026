"""Bounded direct CI8 adapter for buffered wideband FPGA observations."""

from __future__ import annotations

from dataclasses import dataclass
import time

import numpy as np

from .channelizer import ChannelizedFrame
from .transport import IQFrame


@dataclass(frozen=True)
class DirectP0Profile:
    """A 10 MS/s burst reaches PL unchanged; no host frequency conversion occurs."""

    input_sample_rate_hz: int = 10_000_000
    output_sample_rate_hz: int = 10_000_000
    input_samples_per_frame: int = 4_096
    output_samples_per_frame: int = 4_096
    passband_edge_hz: int = 4_000_000
    stopband_edge_hz: int = 5_000_000
    filter_taps: int = 0
    kaiser_beta: float = 0.0
    minimum_dc_safe_offset_hz: int = 0
    maximum_tuning_offset_hz: int = 0
    output_amplitude_scale: float = 1.0

    def __post_init__(self) -> None:
        if (
            self.input_sample_rate_hz != 10_000_000
            or self.output_sample_rate_hz != self.input_sample_rate_hz
            or self.input_samples_per_frame != self.output_samples_per_frame
            or self.input_samples_per_frame not in {4_096, 8_192, 16_384}
        ):
            raise ValueError("Doğrudan FPGA profili 10 MS/s ve eşit giriş/çıkış boyu gerektirir.")

    @property
    def decimation_factor(self) -> int:
        return 1

    @property
    def group_delay_input_samples(self) -> int:
        return 0


class DirectP0FrameAdapter:
    """Validate and wrap one buffered HackRF frame without host-side DSP."""

    backend_name = "direct-ci8"

    def __init__(self, profile: DirectP0Profile | None = None) -> None:
        self.profile = profile or DirectP0Profile()

    def reset(self) -> None:
        return None

    def process_ci8(
        self,
        payload: bytes,
        *,
        sequence_number: int,
        frame_id: int,
        input_sample_rate_hz: int,
        input_center_frequency_hz: int,
        output_center_frequency_hz: int,
        require_dc_safe_tuning: bool = False,
    ) -> tuple[ChannelizedFrame, int]:
        del require_dc_safe_tuning
        started = time.perf_counter()
        profile = self.profile
        if input_sample_rate_hz != profile.input_sample_rate_hz:
            raise ValueError("Doğrudan FPGA girişi kilitli 10 MS/s profiliyle eşleşmiyor.")
        if input_center_frequency_hz != output_center_frequency_hz:
            raise ValueError("Doğrudan FPGA yolunda giriş ve çıktı merkezleri aynı olmalıdır.")
        expected_bytes = profile.input_samples_per_frame * 2
        if len(payload) != expected_bytes:
            raise ValueError(
                f"Doğrudan FPGA yolu tam {profile.input_samples_per_frame} kompleks CI8 örnek gerektirir."
            )
        if not 0 <= sequence_number <= 0xFFFFFFFF or not 0 <= frame_id <= 0xFFFFFFFF:
            raise ValueError("Çerçeve ve sıra kimliği uint32 sınırında olmalıdır.")
        if input_center_frequency_hz <= 0:
            raise ValueError("Merkez frekansı pozitif olmalıdır.")
        raw = np.frombuffer(payload, dtype=np.int8)
        saturated = int(np.count_nonzero((raw == -128) | (raw == 127)))
        frame = IQFrame(
            sequence_number=sequence_number,
            sample_rate_hz=profile.output_sample_rate_hz,
            center_frequency_hz=output_center_frequency_hz,
            payload=bytes(payload),
            frame_id=frame_id,
        )
        return (
            ChannelizedFrame(
                frame=frame,
                saturated_components=0,
                processing_seconds=time.perf_counter() - started,
                input_center_frequency_hz=input_center_frequency_hz,
                tuning_offset_hz=0,
                filter_group_delay_input_samples=0,
                output_amplitude_scale=1.0,
            ),
            saturated,
        )
