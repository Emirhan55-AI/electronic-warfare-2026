"""Bounded in-memory ci8 frame adapter for the existing processing pipeline."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from reference.sigmf.contract import ContractReport

from .contracts import AcquisitionError, CaptureResult


def decode_ci8(payload: bytes, *, expected_complex_samples: int) -> npt.NDArray[np.complex128]:
    if len(payload) % 2:
        raise AcquisitionError("malformed_iq_pair", "Capture eksik bir I/Q çifti içeriyor.")
    expected_bytes = expected_complex_samples * 2
    if len(payload) < expected_bytes:
        raise AcquisitionError("short_capture", "Capture beklenen örnek sayısından kısa.")
    if len(payload) > expected_bytes:
        raise AcquisitionError("long_capture", "Capture beklenen örnek sayısından uzun.")
    values = np.frombuffer(payload, dtype=np.int8).reshape(-1, 2)
    frame = values[:, 0].astype(np.float64) / 128.0 + 1j * values[:, 1].astype(np.float64) / 128.0
    result = np.asarray(frame, dtype=np.complex128)
    result.setflags(write=False)
    return result


class BoundedCI8FrameSource:
    """Expose one bounded capture through the existing frame-source interface."""

    def __init__(self, capture: CaptureResult, *, frame_length: int = 4096) -> None:
        if capture.status != "passed":
            raise AcquisitionError("capture_not_available", "Başarılı bir bounded capture bulunamadı.")
        if len(capture.payload) != capture.config.sample_count * 2:
            decode_ci8(capture.payload, expected_complex_samples=capture.config.sample_count)
        if capture.config.sample_count % frame_length:
            raise AcquisitionError("capture_frame_mismatch", "Capture tam çerçevelere ayrılamıyor.")
        self._payload = bytes(capture.payload)
        self._frame_length = frame_length
        self.backend_kind = capture.backend_kind
        frame_count = capture.config.sample_count // frame_length
        self.report = ContractReport(
            source_datatype="ci8",
            channel_count=1,
            channel_count_source="explicit",
            bytes_per_complex_sample=2,
            total_complex_samples=capture.config.sample_count,
            frame_length=frame_length,
            frame_size_bytes=frame_length * 2,
            full_frame_count=frame_count,
            dropped_complex_samples=0,
            dropped_bytes=0,
            sample_rate=capture.config.sample_rate_hz,
            center_frequency=capture.config.center_frequency_hz,
            duration_seconds=capture.config.sample_count / capture.config.sample_rate_hz,
            frequency_bin_spacing_hz=capture.config.sample_rate_hz / frame_length,
            metadata_filename_compliant=False,
            license_text=None,
            warnings=(),
            errors=(),
        )

    @property
    def frame_count(self) -> int:
        return self.report.full_frame_count or 0

    @property
    def frame_length(self) -> int:
        return self._frame_length

    @property
    def sample_rate_hz(self) -> float:
        return float(self.report.sample_rate or 0)

    @property
    def center_frequency_hz(self) -> float:
        return float(self.report.center_frequency or 0)

    def read_frame(self, index: int) -> npt.NDArray[np.complex128]:
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < self.frame_count:
            raise AcquisitionError("frame_index_out_of_range", "Çerçeve konumu capture sınırının dışında.")
        size = self._frame_length * 2
        payload = self._payload[index * size : (index + 1) * size]
        return decode_ci8(payload, expected_complex_samples=self._frame_length)

    def close(self) -> None:
        self._payload = b""
