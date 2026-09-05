"""Compare detector FFT resolutions on identical recorded physical CI8 data."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from algorithms.spectrum import SpectrumConfig, SpectrumProcessor
from app.operator_console.integrated_spectrum import integrated_spectrum_candidates


DEFAULT_FFT_SIZES = (4_096, 8_192, 16_384, 32_768, 65_536)
SOURCES = (
    "algorithms/spectrum/dsp.py",
    "app/operator_console/integrated_spectrum.py",
    "scripts/evaluate_st04_same_iq_resolution.py",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_prefix(path: Path, byte_count: int) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        remaining = byte_count
        while remaining:
            block = stream.read(min(remaining, 1024 * 1024))
            if not block:
                raise ValueError(f"{path} karşılaştırma öneki için kısa.")
            digest.update(block)
            remaining -= len(block)
    return digest.hexdigest()


def load_ci8_prefix(path: Path, *, complex_samples: int) -> np.ndarray:
    expected_components = complex_samples * 2
    raw = np.fromfile(path, dtype=np.int8, count=expected_components)
    if raw.size != expected_components:
        raise ValueError(f"{path} tam {complex_samples} kompleks örnek içermiyor.")
    components = raw.reshape(complex_samples, 2).astype(np.float64)
    return (components[:, 0] + 1j * components[:, 1]) / 128.0


def process_recording(
    path: Path,
    *,
    fft_size: int,
    complex_samples: int,
    sample_rate_hz: float,
    center_frequency_hz: float,
    scope_lower_hz: float,
    scope_upper_hz: float,
) -> dict[str, object]:
    if complex_samples % fft_size:
        raise ValueError("Karşılaştırma örnek sayısı FFT uzunluğuna tam bölünmelidir.")
    samples = load_ci8_prefix(path, complex_samples=complex_samples)
    frames = samples.reshape(-1, fft_size)
    processor = SpectrumProcessor(SpectrumConfig(frame_length=fft_size))
    frame_power: list[np.ndarray] = []
    frequencies: np.ndarray | None = None
    started = time.perf_counter()
    for frame in frames:
        result = processor.process(
            frame,
            sample_rate_hz=sample_rate_hz,
            center_frequency_hz=center_frequency_hz,
        )
        frame_power.append(result.display.bin_power_fs2)
        if frequencies is None:
            frequencies = result.display.frequency_absolute_hz
    assert frequencies is not None
    candidates = integrated_spectrum_candidates(
        frequencies,
        np.asarray(frame_power),
        lower_hz=scope_lower_hz,
        upper_hz=scope_upper_hz,
    )
    elapsed_seconds = time.perf_counter() - started
    return {
        "frame_count": len(frames),
        "analyzed_seconds": complex_samples / sample_rate_hz,
        "processing_seconds": elapsed_seconds,
        "processing_realtime_ratio": elapsed_seconds / (complex_samples / sample_rate_hz),
        "candidates": [asdict(candidate) | {"occupancy": candidate.occupancy} for candidate in candidates],
    }


def associate_candidates(
    first: list[dict[str, object]],
    second: list[dict[str, object]],
    *,
    tolerance_hz: float,
) -> list[dict[str, object]]:
    """Greedily pair absolute-RF peaks across two independent LO recordings."""
    matches: list[dict[str, object]] = []
    available = set(range(len(second)))
    for left in first:
        left_frequency = float(left["peak_frequency_hz"])
        options = [
            (abs(left_frequency - float(second[index]["peak_frequency_hz"])), index)
            for index in available
        ]
        if not options:
            continue
        delta_hz, index = min(options)
        if delta_hz > tolerance_hz:
            continue
        available.remove(index)
        right = second[index]
        matches.append({
            "frequency_hz": (left_frequency + float(right["peak_frequency_hz"])) / 2.0,
            "separation_hz": delta_hz,
            "first_peak_frequency_hz": left_frequency,
            "second_peak_frequency_hz": float(right["peak_frequency_hz"]),
            "minimum_peak_to_noise_db": min(
                float(left["peak_to_noise_db"]), float(right["peak_to_noise_db"])
            ),
            "minimum_occupancy": min(float(left["occupancy"]), float(right["occupancy"])),
        })
    return matches


def _target_match(
    candidates: list[dict[str, object]], target_hz: float, tolerance_hz: float
) -> dict[str, object] | None:
    matches = [
        item for item in candidates
        if abs(float(item["frequency_hz"]) - target_hz) <= tolerance_hz
    ]
    return min(
        matches,
        key=lambda item: abs(float(item["frequency_hz"]) - target_hz),
        default=None,
    )


def evaluate_profile(
    *,
    fft_size: int,
    recordings: dict[str, dict[str, object]],
    target_hz: float,
    sample_rate_hz: float,
) -> dict[str, object]:
    bin_spacing_hz = sample_rate_hz / fft_size
    association_tolerance_hz = max(2_000.0, 2.1 * bin_spacing_hz)
    on_matches = associate_candidates(
        recordings["first_on"]["candidates"],  # type: ignore[arg-type]
        recordings["second_on"]["candidates"],  # type: ignore[arg-type]
        tolerance_hz=association_tolerance_hz,
    )
    off_matches = associate_candidates(
        recordings["first_off"]["candidates"],  # type: ignore[arg-type]
        recordings["second_off"]["candidates"],  # type: ignore[arg-type]
        tolerance_hz=association_tolerance_hz,
    )
    target_tolerance_hz = max(5_000.0, 2.1 * bin_spacing_hz)
    target_match = _target_match(on_matches, target_hz, target_tolerance_hz)
    off_target_match = _target_match(off_matches, target_hz, target_tolerance_hz)
    return {
        "fft_size": fft_size,
        "bin_spacing_hz": bin_spacing_hz,
        "association_tolerance_hz": association_tolerance_hz,
        "recordings": recordings,
        "two_lo_on_matches": on_matches,
        "two_lo_off_matches": off_matches,
        "evaluation_truth": {
            "target_frequency_hz": target_hz,
            "target_tolerance_hz": target_tolerance_hz,
            "target_recovered_in_two_lo_on": target_match is not None,
            "target_frequency_error_hz": (
                abs(float(target_match["frequency_hz"]) - target_hz)
                if target_match is not None else None
            ),
            "target_present_in_two_lo_off": off_target_match is not None,
        },
        "recording_pair_clean": target_match is not None and not off_matches,
    }


def _input_manifest(
    paths: dict[str, tuple[Path, float]], *, analyzed_complex_samples: int
) -> dict[str, object]:
    byte_count = analyzed_complex_samples * 2
    return {
        key: {
            "path": path.resolve().relative_to(ROOT.resolve()).as_posix(),
            "center_frequency_hz": center,
            "full_file_bytes": path.stat().st_size,
            "full_file_sha256": _sha256(path),
            "analyzed_prefix_bytes": byte_count,
            "analyzed_prefix_sha256": _sha256_prefix(path, byte_count),
        }
        for key, (path, center) in paths.items()
    }


def build_report(
    args: argparse.Namespace,
    *,
    profiles: list[dict[str, object]],
    inputs: dict[str, object],
) -> dict[str, object]:
    clean_profiles = [profile["fft_size"] for profile in profiles if profile["recording_pair_clean"]]
    return {
        "schema": "phase08-st04-same-iq-resolution-v1",
        "status": "recorded_resolution_characterized",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase08_complete": False,
        "st04_complete": False,
        "transmit_enabled": False,
        "blind_acceptance": False,
        "sample_rate_hz": args.sample_rate_hz,
        "analyzed_complex_samples_per_recording": args.analyzed_complex_samples,
        "analyzed_seconds_per_recording": args.analyzed_complex_samples / args.sample_rate_hz,
        "analysis_scope_hz": [args.scope_lower_hz, args.scope_upper_hz],
        "candidate_generation_uses_target_truth": False,
        "evaluation_truth_hz": args.target_hz,
        "inputs": inputs,
        "profiles": profiles,
        "same_recording_result": {
            "clean_fft_sizes_on_this_recording": clean_profiles,
            "preferred_fft_size_on_this_recording": (
                min(clean_profiles) if clean_profiles else None
            ),
            "selected_for_product": False,
            "reason": (
                "Tek açıklanmış frekansın açık/kapalı kaydı ürün profili seçmek için yeterli değildir; "
                "farklı frekans, bant genişliği, seviye ve kör holdout gerekir."
            ),
        },
        "limits": [
            "Aday üretimi hedef frekansı kullanmaz; target truth yalnız sonuç değerlendirmesinde kullanılır.",
            "Kayıt 955,7 MHz frekansı açıklandıktan sonra alındığı için kör kabul değildir.",
            "Aynı fiziksel CI8 öneki bütün FFT profillerinde kullanılır; profiller arası RF ortamı değişmez.",
            "Karşılaştırma host Python referans süresidir; FPGA kaynak/hız kabulü değildir.",
            "Tek frekans ve tek yayın ailesi tüm 20 MHz–6 GHz algılama doğruluğunu veya Pd/Pfa'yı kanıtlamaz.",
        ],
        "source_sha256": {name: _sha256(ROOT / name) for name in SOURCES},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--first-on", type=Path, required=True)
    parser.add_argument("--first-off", type=Path, required=True)
    parser.add_argument("--first-center-hz", type=float, required=True)
    parser.add_argument("--second-on", type=Path, required=True)
    parser.add_argument("--second-off", type=Path, required=True)
    parser.add_argument("--second-center-hz", type=float, required=True)
    parser.add_argument("--target-hz", type=float, required=True)
    parser.add_argument("--scope-lower-hz", type=float, required=True)
    parser.add_argument("--scope-upper-hz", type=float, required=True)
    parser.add_argument("--sample-rate-hz", type=float, default=8_000_000.0)
    parser.add_argument("--analyzed-complex-samples", type=int, default=4_063_232)
    parser.add_argument("--fft-size", type=int, action="append", default=None)
    args = parser.parse_args()
    args.fft_size = args.fft_size or list(DEFAULT_FFT_SIZES)
    if args.output.exists():
        parser.error("Önceki ST-04 kanıtının üzerine yazılmaz.")
    if not math.isfinite(args.sample_rate_hz) or args.sample_rate_hz <= 0.0:
        parser.error("Örnekleme hızı pozitif ve sonlu olmalıdır.")
    if not args.scope_lower_hz < args.target_hz < args.scope_upper_hz:
        parser.error("Değerlendirme truth frekansı analiz aralığında olmalıdır.")
    if any(
        size < 4_096
        or size & (size - 1)
        or args.analyzed_complex_samples % size
        for size in args.fft_size
    ):
        parser.error("FFT uzunlukları en az 4096, iki kuvveti ve örnek sayısının böleni olmalıdır.")

    paths = {
        "first_on": (args.first_on, args.first_center_hz),
        "first_off": (args.first_off, args.first_center_hz),
        "second_on": (args.second_on, args.second_center_hz),
        "second_off": (args.second_off, args.second_center_hz),
    }
    if any(not path.is_file() for path, _ in paths.values()):
        parser.error("Dört fiziksel CI8 kaydının tümü gereklidir.")

    profiles: list[dict[str, object]] = []
    for fft_size in args.fft_size:
        recordings = {
            key: process_recording(
                path,
                fft_size=fft_size,
                complex_samples=args.analyzed_complex_samples,
                sample_rate_hz=args.sample_rate_hz,
                center_frequency_hz=center,
                scope_lower_hz=args.scope_lower_hz,
                scope_upper_hz=args.scope_upper_hz,
            )
            for key, (path, center) in paths.items()
        }
        profiles.append(evaluate_profile(
            fft_size=fft_size,
            recordings=recordings,
            target_hz=args.target_hz,
            sample_rate_hz=args.sample_rate_hz,
        ))

    report = build_report(
        args,
        profiles=profiles,
        inputs=_input_manifest(paths, analyzed_complex_samples=args.analyzed_complex_samples),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "status": report["status"],
        "st04_complete": report["st04_complete"],
        "clean_fft_sizes_on_this_recording": report["same_recording_result"]["clean_fft_sizes_on_this_recording"],
        "selected_for_product": report["same_recording_result"]["selected_for_product"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
