"""Bounded, read-only SigMF frame source for the reference processor."""

from __future__ import annotations

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

    def close(self) -> None:
        """Retained for source-interface symmetry; reads use scoped handles."""

    def __enter__(self) -> "SigMFFrameSource":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
