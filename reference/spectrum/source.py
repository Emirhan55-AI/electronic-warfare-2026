"""Bounded, read-only SigMF frame source for the reference processor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import numpy as np
import numpy.typing as npt

from reference.sigmf.contract import ContractReport, inspect_sigmf


class SigMFSourceError(ValueError):
    """Raised when a SigMF source cannot provide a requested frame."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class SigMFFrameSource:
    """Read exactly one complete complex frame per request."""

    def __init__(
        self,
        metadata_path: Path,
        data_path: Path | None = None,
        *,
        mode: Literal["standard", "explicit"] = "standard",
        frame_length: int = 4096,
    ) -> None:
        self.metadata_path = Path(metadata_path)
        explicit_data_path = Path(data_path) if data_path is not None else None
        self.report: ContractReport = inspect_sigmf(
            self.metadata_path,
            explicit_data_path,
            mode=mode,
            frame_length=frame_length,
        )
        if not self.report.valid:
            codes = ", ".join(issue.code for issue in self.report.errors)
            raise SigMFSourceError("invalid_sigmf_contract", f"SigMF contract failed: {codes}")
        if (
            self.report.source_datatype not in {"ci8", "ci16_le"}
            or self.report.frame_size_bytes is None
            or self.report.full_frame_count is None
            or self.report.sample_rate is None
            or self.report.center_frequency is None
        ):
            raise SigMFSourceError("incomplete_contract_report", "SigMF report lacks frame information")
        self.data_path = self._resolve_data_path(self.metadata_path, explicit_data_path, mode)
        self.source_description = self._read_source_description()

    def _read_source_description(self) -> str | None:
        """Retain optional provenance without relaxing the SigMF contract."""
        try:
            document = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        global_object = document.get("global") if isinstance(document, dict) else None
        description = global_object.get("core:description") if isinstance(global_object, dict) else None
        return description if isinstance(description, str) else None

    @staticmethod
    def _resolve_data_path(
        metadata_path: Path,
        data_path: Path | None,
        mode: Literal["standard", "explicit"],
    ) -> Path:
        if data_path is not None:
            return Path(data_path)
        if metadata_path.name.endswith(".sigmf-meta"):
            stem = metadata_path.name[: -len(".sigmf-meta")]
            return metadata_path.with_name(stem + ".sigmf-data")
        if mode == "explicit":
            return metadata_path.with_name("__explicit_data_path_required__")
        return metadata_path.with_name("__standard_data_path_unresolved__")

    @property
    def frame_count(self) -> int:
        assert self.report.full_frame_count is not None
        return self.report.full_frame_count

    @property
    def frame_length(self) -> int:
        return self.report.frame_length

    @property
    def sample_rate_hz(self) -> float:
        assert self.report.sample_rate is not None
        return float(self.report.sample_rate)

    @property
    def center_frequency_hz(self) -> float:
        assert self.report.center_frequency is not None
        return float(self.report.center_frequency)

    def read_frame(self, index: int) -> npt.NDArray[np.complex128]:
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < self.frame_count:
            raise SigMFSourceError("frame_index_out_of_range", "frame index is outside the complete-frame range")
        assert self.report.frame_size_bytes is not None
        offset = index * self.report.frame_size_bytes
        try:
            with self.data_path.open("rb") as stream:
                stream.seek(offset)
                payload = stream.read(self.report.frame_size_bytes)
        except OSError as exc:
            raise SigMFSourceError("frame_read_failed", f"frame could not be read: {type(exc).__name__}") from exc
        if len(payload) != self.report.frame_size_bytes:
            raise SigMFSourceError("short_frame_read", "data source returned an incomplete frame")

        if self.report.source_datatype == "ci8":
            values = np.frombuffer(payload, dtype=np.int8).reshape(-1, 2)
            scale = 128.0
        else:
            values = np.frombuffer(payload, dtype=np.dtype("<i2")).reshape(-1, 2)
            scale = 32768.0
        real = values[:, 0].astype(np.float64) / scale
        imag = values[:, 1].astype(np.float64) / scale
        frame = np.asarray(real + 1j * imag, dtype=np.complex128)
        frame.setflags(write=False)
        return frame

    def read_samples(self, start_sample: int, sample_count: int) -> npt.NDArray[np.complex128]:
        """Read one contiguous I/Q range without resetting a DSP stream."""
        if (
            not isinstance(start_sample, int)
            or isinstance(start_sample, bool)
            or not isinstance(sample_count, int)
            or isinstance(sample_count, bool)
            or start_sample < 0
            or sample_count < 1
        ):
            raise SigMFSourceError("sample_range_invalid", "I/Q örnek aralığı geçersizdir.")
        total_samples = self.frame_count * self.frame_length
        if start_sample + sample_count > total_samples:
            raise SigMFSourceError("sample_range_out_of_range", "I/Q örnek aralığı kayıt dışına taşıyor.")
        assert self.report.frame_size_bytes is not None
        bytes_per_sample = self.report.frame_size_bytes // self.frame_length
        offset = start_sample * bytes_per_sample
        byte_count = sample_count * bytes_per_sample
        try:
            with self.data_path.open("rb") as stream:
                stream.seek(offset)
                payload = stream.read(byte_count)
        except OSError as exc:
            raise SigMFSourceError("sample_read_failed", f"I/Q aralığı okunamadı: {type(exc).__name__}") from exc
        if len(payload) != byte_count:
            raise SigMFSourceError("short_sample_read", "I/Q aralığı eksik okundu.")
        if self.report.source_datatype == "ci8":
            values = np.frombuffer(payload, dtype=np.int8).reshape(-1, 2)
            scale = 128.0
        else:
            values = np.frombuffer(payload, dtype=np.dtype("<i2")).reshape(-1, 2)
            scale = 32768.0
        result = np.asarray(
            values[:, 0].astype(np.float64) / scale + 1j * values[:, 1].astype(np.float64) / scale,
            dtype=np.complex128,
        )
        result.setflags(write=False)
        return result

    def close(self) -> None:
        """Retained for source-interface symmetry; reads use scoped handles."""

    def __enter__(self) -> "SigMFFrameSource":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
