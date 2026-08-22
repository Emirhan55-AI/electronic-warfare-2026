"""Lossless wrapping of recorded HackRF ``ci8`` I/Q into SigMF."""

from __future__ import annotations

import json
import math
from pathlib import Path
import shutil


HACKRF_REPLAY_DESCRIPTION = "HackRF recorded IQ replay"


class HackRFSigMFWrapError(ValueError):
    """Raised when a raw HackRF recording cannot be represented faithfully."""


def _positive_finite(value: float | int | str, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise HackRFSigMFWrapError(f"{field} sayısal olmalıdır") from exc
    if not math.isfinite(number) or number <= 0.0:
        raise HackRFSigMFWrapError(f"{field} pozitif ve sonlu olmalıdır")
    return number


def wrap_hackrf_iq_as_sigmf(
    input_path: Path,
    *,
    sample_rate_hz: float | int | str,
    center_frequency_hz: float | int | str,
    output_basename: Path,
) -> tuple[Path, Path]:
    """Copy signed interleaved ``ci8`` bytes and write their SigMF metadata.

    The input bytes are never decoded, scaled, or otherwise transformed.  The
    output pair is intentionally non-overwriting so a video capture cannot
    silently replace an earlier recording.
    """

    source = Path(input_path)
    if not source.is_file():
        raise HackRFSigMFWrapError(f"girdi I/Q dosyası bulunamadı: {source}")
    if source.stat().st_size % 2:
        raise HackRFSigMFWrapError("girdi sonu eksik I/Q çifti içeriyor")

    sample_rate = _positive_finite(sample_rate_hz, "sample rate")
    center_frequency = _positive_finite(center_frequency_hz, "center frequency")
    basename = Path(output_basename)
    data_path = Path(str(basename) + ".sigmf-data")
    metadata_path = Path(str(basename) + ".sigmf-meta")
    if not basename.parent.is_dir():
        raise HackRFSigMFWrapError(f"çıktı dizini bulunamadı: {basename.parent}")
    if data_path.exists() or metadata_path.exists():
        raise FileExistsError("SigMF çıktısı zaten var; mevcut kayıt değiştirilmedi")
    if source.resolve() in {data_path.resolve(), metadata_path.resolve()}:
        raise HackRFSigMFWrapError("girdi ve çıktı aynı dosya olamaz")

    metadata = {
        "global": {
            "core:version": "1.0.0",
            "core:datatype": "ci8",
            "core:sample_rate": sample_rate,
            "core:num_channels": 1,
            "core:description": HACKRF_REPLAY_DESCRIPTION,
        },
        "captures": [
            {
                "core:sample_start": 0,
                "core:frequency": center_frequency,
            }
        ],
        "annotations": [],
    }
    try:
        shutil.copyfile(source, data_path)
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:
        # Only a file created by this call is removed; source bytes are never
        # touched.  This avoids leaving a pair whose metadata was not written.
        if data_path.exists() and not metadata_path.exists():
            data_path.unlink()
        raise
    return data_path, metadata_path
