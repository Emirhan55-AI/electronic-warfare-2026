"""Measured-power extraction from a controlled set of recorded DF captures."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import re
from typing import Iterable

import numpy as np

from reference.spectrum import SigMFFrameSource, SpectrumProcessor


RECORDED_DF_SOURCE = "HACKRF KAYDI / GERÇEK AÇI-GÜÇ ÖLÇÜMÜ"
_ANGLE_NAME = re.compile(r"^df_(\d{3})\.sigmf-meta$", re.IGNORECASE)
_EXPECTED_ANGLES = tuple(range(0, 360, 45))


class RecordedDFError(ValueError):
    """A recording set cannot support an honest amplitude-DF measurement."""


def _positive_finite(value: object, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise RecordedDFError(f"{field} sayısal olmalıdır") from exc
    if not math.isfinite(number) or number <= 0.0:
        raise RecordedDFError(f"{field} pozitif ve sonlu olmalıdır")
    return number


@dataclass(frozen=True)
class RecordedDFPoint:
    angle_deg: float
    measured_power_dbfs: float
    confidence: float
    analyzed_frame_count: int
    discarded_frame_count: int
    robust_spread_db: float
    metadata_name: str


@dataclass(frozen=True)
class RecordedDFReport:
    """Portable report that the YÖN panel can load without reprocessing bytes."""

    source: str
    target_frequency_hz: float
    channel_bandwidth_hz: float
    sample_rate_hz: float
    center_frequency_hz: float
    robust_method: str
    points: tuple[RecordedDFPoint, ...]

    def to_document(self) -> dict[str, object]:
        return {
            "schema": "teknofest.recorded-amplitude-df.v1",
            "source": self.source,
            "target_frequency_hz": self.target_frequency_hz,
            "channel_bandwidth_hz": self.channel_bandwidth_hz,
            "sample_rate_hz": self.sample_rate_hz,
            "center_frequency_hz": self.center_frequency_hz,
            "robust_method": self.robust_method,
            "points": [asdict(point) for point in self.points],
        }

    @classmethod
    def from_document(cls, document: object) -> "RecordedDFReport":
        if not isinstance(document, dict) or document.get("schema") != "teknofest.recorded-amplitude-df.v1":
            raise RecordedDFError("tanınmayan kayıtlı DF raporu")
        source = document.get("source")
        if source != RECORDED_DF_SOURCE:
            raise RecordedDFError("rapor gerçek HackRF açı–güç kaynağı olarak işaretlenmemiş")
        raw_points = document.get("points")
        if not isinstance(raw_points, list):
            raise RecordedDFError("raporda ölçüm noktaları yok")
        points: list[RecordedDFPoint] = []
        for raw in raw_points:
            if not isinstance(raw, dict):
                raise RecordedDFError("geçersiz ölçüm noktası")
            try:
                point = RecordedDFPoint(
                    angle_deg=float(raw["angle_deg"]),
                    measured_power_dbfs=float(raw["measured_power_dbfs"]),
                    confidence=float(raw["confidence"]),
                    analyzed_frame_count=int(raw["analyzed_frame_count"]),
                    discarded_frame_count=int(raw["discarded_frame_count"]),
                    robust_spread_db=float(raw["robust_spread_db"]),
                    metadata_name=str(raw["metadata_name"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise RecordedDFError("raporda geçersiz ölçüm alanı") from exc
            if (
                not all(math.isfinite(value) for value in (point.angle_deg, point.measured_power_dbfs, point.confidence, point.robust_spread_db))
                or point.analyzed_frame_count < 1
                or point.discarded_frame_count < 0
                or not 0.0 <= point.confidence <= 1.0
            ):
                raise RecordedDFError("raporda ölçüm değeri geçersiz")
            points.append(point)
        report = cls(
            source=source,
            target_frequency_hz=_positive_finite(document.get("target_frequency_hz"), "hedef frekans"),
            channel_bandwidth_hz=_positive_finite(document.get("channel_bandwidth_hz"), "kanal bant genişliği"),
            sample_rate_hz=_positive_finite(document.get("sample_rate_hz"), "örnekleme hızı"),
            center_frequency_hz=_positive_finite(document.get("center_frequency_hz"), "merkez frekansı"),
            robust_method=str(document.get("robust_method")),
            points=tuple(sorted(points, key=lambda item: item.angle_deg)),
        )
        if tuple(point.angle_deg for point in report.points) != tuple(float(angle) for angle in _EXPECTED_ANGLES):
            raise RecordedDFError("rapor 0°–315° arasındaki sekiz kayıtlı açıyı içermelidir")
        return report

    @classmethod
    def read(cls, path: Path) -> "RecordedDFReport":
        try:
            document = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RecordedDFError("kayıtlı DF raporu okunamadı") from exc
        return cls.from_document(document)


def _angle_from_metadata_name(path: Path) -> int:
    match = _ANGLE_NAME.fullmatch(path.name)
    if match is None:
        raise RecordedDFError(f"DF metadata adı df_000…df_315 olmalıdır: {path.name}")
    angle = int(match.group(1))
    if angle not in _EXPECTED_ANGLES:
        raise RecordedDFError(f"desteklenmeyen DF açısı: {angle}")
    return angle


def _selected_frame_indices(
    source: SigMFFrameSource,
    *,
    discard_seconds: float,
    maximum_frames: int,
    minimum_frames: int,
) -> tuple[tuple[int, ...], int]:
    if maximum_frames < minimum_frames or minimum_frames < 1:
        raise RecordedDFError("kare sınırları geçersiz")
    requested_discard = int(math.floor(source.sample_rate_hz * discard_seconds / source.frame_length))
    # The first second is discarded only when many complete frames remain.
    start = requested_discard if source.frame_count - requested_discard >= minimum_frames else 0
    available = source.frame_count - start
    if available < minimum_frames:
        raise RecordedDFError(
            f"{source.metadata_path.name}: güvenilir ölçüm için en az {minimum_frames} tam kare yok"
        )
    count = min(available, maximum_frames)
    indexes = np.linspace(start, source.frame_count - 1, num=count, dtype=np.int64)
    return tuple(int(index) for index in indexes), start


def _channel_bin_mask(
    source: SigMFFrameSource,
    *,
    target_frequency_hz: float,
    channel_bandwidth_hz: float,
) -> np.ndarray:
    lower = target_frequency_hz - channel_bandwidth_hz / 2.0
    upper = target_frequency_hz + channel_bandwidth_hz / 2.0
    first = source.center_frequency_hz - source.sample_rate_hz / 2.0
    last = source.center_frequency_hz + source.sample_rate_hz / 2.0 - source.sample_rate_hz / source.frame_length
    if lower < first or upper > last:
        raise RecordedDFError("hedef kanal bu kaydın görünür spektrumunun dışında")
    axis = np.fft.fftshift(np.fft.fftfreq(source.frame_length, d=1.0 / source.sample_rate_hz)) + source.center_frequency_hz
    mask = (axis >= lower) & (axis <= upper)
    if not np.any(mask):
        raise RecordedDFError("hedef kanal hiçbir FFT hücresine karşılık gelmiyor")
    return mask


def _confidence_from_spread(power_db: np.ndarray) -> tuple[float, float]:
    median = float(np.median(power_db))
    median_absolute_deviation = float(np.median(np.abs(power_db - median)))
    robust_spread = 1.4826 * median_absolute_deviation
    # This only feeds the existing estimator's confidence display.  It never
    # changes a measured median or introduces a bearing.
    confidence = 1.0 / (1.0 + robust_spread)
    return max(0.0, min(1.0, confidence)), robust_spread


def analyze_recorded_df(
    metadata_paths: Iterable[Path],
    *,
    target_frequency_hz: float | int | str,
    channel_bandwidth_hz: float | int | str,
    discard_seconds: float = 1.0,
    maximum_frames: int = 256,
    minimum_frames: int = 8,
) -> RecordedDFReport:
    """Measure every supplied angle from many Hann/4096 FFT frames."""

    target_frequency = _positive_finite(target_frequency_hz, "hedef frekans")
    bandwidth = _positive_finite(channel_bandwidth_hz, "kanal bant genişliği")
    if not math.isfinite(discard_seconds) or discard_seconds < 0.0:
        raise RecordedDFError("atılacak süre sıfır veya pozitif sonlu olmalıdır")
    paths = tuple(Path(path) for path in metadata_paths)
    if len(paths) != len(_EXPECTED_ANGLES):
        raise RecordedDFError("sekiz DF metadata kaydı gereklidir")
    by_angle = {_angle_from_metadata_name(path): path for path in paths}
    if len(by_angle) != len(paths) or tuple(sorted(by_angle)) != _EXPECTED_ANGLES:
        raise RecordedDFError("DF kayıtları df_000…df_315 olarak tekil olmalıdır")

    processor = SpectrumProcessor()
    first_sample_rate: float | None = None
    first_center_frequency: float | None = None
    points: list[RecordedDFPoint] = []
    for angle in _EXPECTED_ANGLES:
        source = SigMFFrameSource(by_angle[angle])
        if first_sample_rate is None:
            first_sample_rate = source.sample_rate_hz
            first_center_frequency = source.center_frequency_hz
        elif source.sample_rate_hz != first_sample_rate or source.center_frequency_hz != first_center_frequency:
            raise RecordedDFError("tüm DF kayıtları aynı örnekleme ve merkez frekansına sahip olmalıdır")
        mask = _channel_bin_mask(source, target_frequency_hz=target_frequency, channel_bandwidth_hz=bandwidth)
        indexes, discarded_frames = _selected_frame_indices(
            source,
            discard_seconds=discard_seconds,
            maximum_frames=maximum_frames,
            minimum_frames=minimum_frames,
        )
        powers_db: list[float] = []
        for index in indexes:
            result = processor.process(
                source.read_frame(index),
                sample_rate_hz=source.sample_rate_hz,
                center_frequency_hz=source.center_frequency_hz,
            )
            channel_power = float(np.sum(result.display.bin_power_fs2[mask], dtype=np.float64))
            powers_db.append(10.0 * math.log10(max(channel_power, 1e-300)))
        frame_powers = np.asarray(powers_db, dtype=np.float64)
        confidence, robust_spread = _confidence_from_spread(frame_powers)
        points.append(
            RecordedDFPoint(
                angle_deg=float(angle),
                measured_power_dbfs=float(np.median(frame_powers)),
                confidence=confidence,
                analyzed_frame_count=len(indexes),
                discarded_frame_count=discarded_frames,
                robust_spread_db=robust_spread,
                metadata_name=by_angle[angle].name,
            )
        )
    assert first_sample_rate is not None and first_center_frequency is not None
    return RecordedDFReport(
        source=RECORDED_DF_SOURCE,
        target_frequency_hz=target_frequency,
        channel_bandwidth_hz=bandwidth,
        sample_rate_hz=first_sample_rate,
        center_frequency_hz=first_center_frequency,
        robust_method="çoklu Hann/4096 FFT; hedef kanal lineer gücü; medyan dBFS",
        points=tuple(points),
    )


def write_recorded_df_report(path: Path, report: RecordedDFReport) -> None:
    destination = Path(path)
    if destination.exists():
        raise FileExistsError("DF rapor çıktısı zaten var; mevcut rapor değiştirilmedi")
    destination.write_text(
        json.dumps(report.to_document(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
