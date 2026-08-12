"""PHASE-01 SigMF metadata and binary-layout validation.

This module deliberately performs no DSP, normalization, resampling, or sample
value conversion. It uses only the Python standard library.
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator, Literal


SUPPORTED_CORE_VERSIONS = frozenset({"1.0.0"})
BYTES_PER_COMPLEX_SAMPLE = {"ci8": 2, "ci16_le": 4}


@dataclass(frozen=True)
class ContractIssue:
    code: str
    message: str
    field: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass(frozen=True)
class ContractReport:
    source_datatype: str | None
    channel_count: int | None
    channel_count_source: Literal["explicit", "defaulted"] | None
    bytes_per_complex_sample: int | None
    total_complex_samples: int | None
    frame_length: int
    frame_size_bytes: int | None
    full_frame_count: int | None
    dropped_complex_samples: int | None
    dropped_bytes: int | None
    sample_rate: int | float | None
    center_frequency: int | float | None
    duration_seconds: float | None
    frequency_bin_spacing_hz: float | None
    metadata_filename_compliant: bool
    license_text: str | None
    warnings: tuple[ContractIssue, ...]
    errors: tuple[ContractIssue, ...]

    @property
    def valid(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["warnings"] = [issue.to_dict() for issue in self.warnings]
        result["errors"] = [issue.to_dict() for issue in self.errors]
        result["valid"] = self.valid
        return result


class ContractValidationError(ValueError):
    """Raised when a bounded I/Q buffer violates its datatype layout."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _issue(code: str, message: str, field: str | None = None) -> ContractIssue:
    return ContractIssue(code=code, message=message, field=field)


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _empty_report(
    frame_length: int,
    filename_compliant: bool,
    warnings: list[ContractIssue],
    errors: list[ContractIssue],
) -> ContractReport:
    return ContractReport(
        source_datatype=None,
        channel_count=None,
        channel_count_source=None,
        bytes_per_complex_sample=None,
        total_complex_samples=None,
        frame_length=frame_length,
        frame_size_bytes=None,
        full_frame_count=None,
        dropped_complex_samples=None,
        dropped_bytes=None,
        sample_rate=None,
        center_frequency=None,
        duration_seconds=None,
        frequency_bin_spacing_hz=None,
        metadata_filename_compliant=filename_compliant,
        license_text=None,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def _standard_data_path(metadata_path: Path) -> Path:
    name = metadata_path.name
    return metadata_path.with_name(name[: -len(".sigmf-meta")] + ".sigmf-data")


def inspect_sigmf(
    metadata_path: Path,
    data_path: Path | None = None,
    *,
    mode: Literal["standard", "explicit"],
    frame_length: int = 4096,
) -> ContractReport:
    """Inspect metadata and data layout without reading the data payload."""
    metadata_path = Path(metadata_path)
    data_path = Path(data_path) if data_path is not None else None
    warnings: list[ContractIssue] = []
    errors: list[ContractIssue] = []

    if mode not in {"standard", "explicit"}:
        errors.append(_issue("invalid_field_value", "mode must be standard or explicit", "mode"))
    if not isinstance(frame_length, int) or isinstance(frame_length, bool) or frame_length <= 0:
        errors.append(_issue("invalid_field_value", "frame_length must be a positive integer", "frame_length"))
        frame_length = 4096

    filename_compliant = metadata_path.name.endswith(".sigmf-meta")
    if mode == "standard":
        if not filename_compliant:
            errors.append(
                _issue(
                    "metadata_extension_not_standard",
                    "standard discovery requires a .sigmf-meta filename",
                    "metadata_path",
                )
            )
        else:
            expected_data_path = _standard_data_path(metadata_path)
            if data_path is None:
                data_path = expected_data_path
            elif data_path.resolve(strict=False) != expected_data_path.resolve(strict=False):
                errors.append(
                    _issue(
                        "data_filename_mismatch",
                        "standard discovery requires the matching .sigmf-data filename",
                        "data_path",
                    )
                )
    elif mode == "explicit":
        if not filename_compliant:
            warnings.append(
                _issue(
                    "nonstandard_metadata_extension",
                    "explicit metadata path does not use the .sigmf-meta extension",
                    "metadata_path",
                )
            )
            if data_path is None:
                errors.append(
                    _issue(
                        "data_path_required",
                        "data_path is required with a nonstandard metadata extension",
                        "data_path",
                    )
                )
        elif data_path is None:
            data_path = _standard_data_path(metadata_path)

    if not metadata_path.is_file():
        errors.append(_issue("metadata_not_found", "metadata file was not found", "metadata_path"))
        return _empty_report(frame_length, filename_compliant, warnings, errors)

    try:
        metadata_text = metadata_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append(_issue("metadata_invalid_utf8", "metadata is not valid UTF-8", "metadata_path"))
        return _empty_report(frame_length, filename_compliant, warnings, errors)
    except OSError as exc:
        errors.append(_issue("metadata_not_found", f"metadata could not be read: {type(exc).__name__}", "metadata_path"))
        return _empty_report(frame_length, filename_compliant, warnings, errors)

    try:
        metadata = json.loads(metadata_text)
    except json.JSONDecodeError:
        errors.append(_issue("metadata_invalid_json", "metadata is not valid JSON", "metadata_path"))
        return _empty_report(frame_length, filename_compliant, warnings, errors)

    if not isinstance(metadata, dict):
        errors.append(_issue("metadata_invalid_json", "metadata root must be an object", "metadata_path"))
        return _empty_report(frame_length, filename_compliant, warnings, errors)

    global_object = metadata.get("global")
    if not isinstance(global_object, dict):
        errors.append(_issue("missing_required_field", "global must be an object", "global"))
        global_object = {}

    core_version = global_object.get("core:version")
    if core_version is None:
        errors.append(_issue("missing_required_field", "core:version is required", "core:version"))
    elif core_version not in SUPPORTED_CORE_VERSIONS:
        errors.append(
            _issue("unsupported_core_version", "core:version is not supported in PHASE-01", "core:version")
        )

    datatype = global_object.get("core:datatype")
    if datatype is None:
        errors.append(_issue("missing_required_field", "core:datatype is required", "core:datatype"))
    elif datatype not in BYTES_PER_COMPLEX_SAMPLE:
        errors.append(_issue("unsupported_datatype", "datatype is not supported in PHASE-01", "core:datatype"))

    sample_rate = global_object.get("core:sample_rate")
    if sample_rate is None:
        errors.append(_issue("missing_required_field", "core:sample_rate is required", "core:sample_rate"))
    elif not _is_finite_number(sample_rate) or sample_rate <= 0:
        errors.append(_issue("invalid_field_value", "core:sample_rate must be positive and finite", "core:sample_rate"))

    raw_channel_count = global_object.get("core:num_channels")
    if raw_channel_count is None:
        channel_count = 1
        channel_source: Literal["explicit", "defaulted"] = "defaulted"
        warnings.append(
            _issue(
                "channel_count_defaulted",
                "core:num_channels is absent; the SigMF default of one channel is used",
                "core:num_channels",
            )
        )
    else:
        channel_count = raw_channel_count
        channel_source = "explicit"
        if not isinstance(channel_count, int) or isinstance(channel_count, bool) or channel_count != 1:
            errors.append(
                _issue(
                    "unsupported_channel_count",
                    "PHASE-01 accepts exactly one channel",
                    "core:num_channels",
                )
            )

    captures = metadata.get("captures")
    center_frequency: int | float | None = None
    if not isinstance(captures, list) or len(captures) != 1:
        errors.append(
            _issue(
                "unsupported_capture_count",
                "PHASE-01 requires exactly one capture",
                "captures",
            )
        )
    elif not isinstance(captures[0], dict):
        errors.append(_issue("invalid_field_value", "capture must be an object", "captures[0]"))
    else:
        capture = captures[0]
        sample_start = capture.get("core:sample_start")
        if sample_start != 0 or isinstance(sample_start, bool):
            errors.append(
                _issue(
                    "invalid_capture_start",
                    "the single capture must start at complex sample zero",
                    "captures[0].core:sample_start",
                )
            )
        center_frequency = capture.get("core:frequency")
        if center_frequency is None:
            errors.append(
                _issue(
                    "missing_required_field",
                    "core:frequency is required on the capture",
                    "captures[0].core:frequency",
                )
            )
        elif not _is_finite_number(center_frequency):
            errors.append(
                _issue(
                    "invalid_field_value",
                    "core:frequency must be numeric and finite",
                    "captures[0].core:frequency",
                )
            )

    data_size: int | None = None
    if data_path is None:
        if not any(issue.code == "data_path_required" for issue in errors):
            errors.append(_issue("data_not_found", "data path could not be resolved", "data_path"))
    elif not data_path.is_file():
        errors.append(_issue("data_not_found", "data file was not found", "data_path"))
    else:
        try:
            data_size = data_path.stat().st_size
        except OSError as exc:
            errors.append(_issue("data_not_found", f"data could not be inspected: {type(exc).__name__}", "data_path"))

    bytes_per_sample = BYTES_PER_COMPLEX_SAMPLE.get(datatype)
    total_samples: int | None = None
    frame_size: int | None = None
    full_frames: int | None = None
    dropped_samples: int | None = None
    dropped_bytes: int | None = None
    duration: float | None = None
    bin_spacing: float | None = None

    if bytes_per_sample is not None:
        frame_size = frame_length * bytes_per_sample
    if data_size is not None and bytes_per_sample is not None:
        total_samples, trailing_bytes = divmod(data_size, bytes_per_sample)
        if trailing_bytes:
            errors.append(
                _issue(
                    "malformed_iq_pair",
                    "data ends with an incomplete complex I/Q sample",
                    "data_path",
                )
            )
        full_frames, dropped_samples = divmod(total_samples, frame_length)
        dropped_bytes = dropped_samples * bytes_per_sample + trailing_bytes
        if dropped_samples:
            warnings.append(
                _issue(
                    "incomplete_frame_dropped",
                    "the incomplete final frame is excluded from processing",
                    "data_path",
                )
            )
    if total_samples is not None and _is_finite_number(sample_rate) and sample_rate > 0:
        duration = total_samples / sample_rate
    if _is_finite_number(sample_rate) and sample_rate > 0:
        bin_spacing = sample_rate / frame_length

    license_value = global_object.get("core:license")
    license_text = license_value if isinstance(license_value, str) else None

    return ContractReport(
        source_datatype=datatype if isinstance(datatype, str) else None,
        channel_count=channel_count if isinstance(channel_count, int) and not isinstance(channel_count, bool) else None,
        channel_count_source=channel_source,
        bytes_per_complex_sample=bytes_per_sample,
        total_complex_samples=total_samples,
        frame_length=frame_length,
        frame_size_bytes=frame_size,
        full_frame_count=full_frames,
        dropped_complex_samples=dropped_samples,
        dropped_bytes=dropped_bytes,
        sample_rate=sample_rate if _is_finite_number(sample_rate) else None,
        center_frequency=center_frequency if _is_finite_number(center_frequency) else None,
        duration_seconds=duration,
        frequency_bin_spacing_hz=bin_spacing,
        metadata_filename_compliant=filename_compliant,
        license_text=license_text,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def decode_iq_pairs(data: bytes, datatype: Literal["ci8", "ci16_le"]) -> Iterator[tuple[int, int]]:
    """Decode a bounded byte buffer without converting sample values."""
    if datatype not in BYTES_PER_COMPLEX_SAMPLE:
        raise ContractValidationError("unsupported_datatype", "datatype is not supported in PHASE-01")
    bytes_per_sample = BYTES_PER_COMPLEX_SAMPLE[datatype]
    if len(data) % bytes_per_sample:
        raise ContractValidationError("malformed_iq_pair", "buffer ends with an incomplete complex I/Q sample")
    format_string = "bb" if datatype == "ci8" else "<hh"
    yield from struct.iter_unpack(format_string, data)
