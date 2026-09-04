"""Measure receive-only ST-04 search profiles without changing detector thresholds."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from algorithms.p0.channelizer import P0ChannelizerProfile
from algorithms.p0.hackrf_search import HackRFSearchPlanner, HackRFTuningProfile
from algorithms.p0.search import SearchRequest
from app.operator_console.rx_survey import SurveyConfig


SOURCES = (
    "algorithms/p0/channelizer.py",
    "algorithms/p0/coarse_detection.py",
    "algorithms/p0/hackrf_search.py",
    "app/operator_console/rx_survey.py",
    "scripts/measure_st04_search_profiles.py",
)


@dataclass(frozen=True)
class SweepCsvSummary:
    rows: int
    power_bins: int
    covered_lower_hz: int
    covered_upper_hz: int
    covered_hz: int
    gap_count: int
    gap_hz: int
    bin_widths_hz: tuple[float, ...]
    first_timestamp: str
    last_timestamp: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_sweep_csv(
    path: Path,
    *,
    expected_lower_hz: int,
    expected_upper_hz: int,
) -> SweepCsvSummary:
    """Validate and summarize one text-mode ``hackrf_sweep`` capture."""
    intervals: list[tuple[int, int]] = []
    timestamps: list[str] = []
    bin_widths: set[float] = set()
    power_bins = 0
    with path.open("r", encoding="utf-8", newline="") as stream:
        for line_number, row in enumerate(csv.reader(stream), start=1):
            if len(row) < 7:
                raise ValueError(f"Sweep satırı {line_number} eksik.")
            try:
                lower_hz = int(row[2].strip())
                upper_hz = int(row[3].strip())
                bin_width_hz = float(row[4].strip())
                sample_count = int(row[5].strip())
                powers = tuple(float(value.strip()) for value in row[6:])
            except ValueError as exc:
                raise ValueError(f"Sweep satırı {line_number} sayısal değil.") from exc
            if lower_hz >= upper_hz or bin_width_hz <= 0.0 or sample_count <= 0:
                raise ValueError(f"Sweep satırı {line_number} sınırları geçersiz.")
            expected_bins = int(round((upper_hz - lower_hz) / bin_width_hz))
            if expected_bins != len(powers) or not all(math.isfinite(value) for value in powers):
                raise ValueError(f"Sweep satırı {line_number} güç hücreleriyle uyuşmuyor.")
            intervals.append((lower_hz, upper_hz))
            timestamps.append(f"{row[0].strip()}T{row[1].strip()}")
            bin_widths.add(bin_width_hz)
            power_bins += len(powers)

    if not intervals:
        raise ValueError("Sweep çıktısı boş.")
    merged: list[list[int]] = []
    for lower_hz, upper_hz in sorted(intervals):
        if not merged or lower_hz > merged[-1][1]:
            merged.append([lower_hz, upper_hz])
        else:
            merged[-1][1] = max(merged[-1][1], upper_hz)
    gaps = [
        (merged[index - 1][1], merged[index][0])
        for index in range(1, len(merged))
        if merged[index][0] > merged[index - 1][1]
    ]
    covered_lower_hz = min(lower for lower, _ in intervals)
    covered_upper_hz = max(upper for _, upper in intervals)
    if covered_lower_hz > expected_lower_hz or covered_upper_hz < expected_upper_hz:
        raise ValueError("Sweep istenen frekans aralığını bütünüyle kapsamıyor.")
    return SweepCsvSummary(
        rows=len(intervals),
        power_bins=power_bins,
        covered_lower_hz=covered_lower_hz,
        covered_upper_hz=covered_upper_hz,
        covered_hz=sum(upper - lower for lower, upper in merged),
        gap_count=len(gaps),
        gap_hz=sum(upper - lower for lower, upper in gaps),
        bin_widths_hz=tuple(sorted(bin_widths)),
        first_timestamp=min(timestamps),
        last_timestamp=max(timestamps),
    )


def estimate_profiles(lower_hz: int, upper_hz: int) -> dict[str, object]:
    """Return raw-sample lower bounds; retune and processing are excluded."""
    channelizer = P0ChannelizerProfile()
    detailed = SurveyConfig(lower_hz=lower_hz, upper_hz=upper_hz)
    detailed_windows = len(detailed.windows())
    detailed_seconds_per_window = (
        detailed.frames_per_window
        * channelizer.input_samples_per_frame
        / channelizer.input_sample_rate_hz
    )

    coarse_profile = HackRFTuningProfile()
    coarse_plan = HackRFSearchPlanner(
        profile=coarse_profile,
        unknown_ranges_hz=((lower_hz, upper_hz),),
    ).plan(SearchRequest.unknown())
    coarse_observations_per_window = 3
    coarse_seconds_per_window = (
        coarse_observations_per_window
        * coarse_profile.sample_count
        / coarse_profile.sample_rate_hz
    )
    return {
        "detailed_2msps_fpga_survey": {
            "decision_owner": "FPGA_PL_and_ARM_PS",
            "window_count": detailed_windows,
            "responsibility_width_hz": detailed.windows()[0].upper_hz - detailed.windows()[0].lower_hz,
            "frames_per_window": detailed.frames_per_window,
            "raw_sample_seconds_per_window": detailed_seconds_per_window,
            "raw_sample_seconds_full_range": detailed_windows * detailed_seconds_per_window,
        },
        "bounded_8msps_coarse_plan": {
            "decision_owner": "host_candidate_only",
            "window_count": len(coarse_plan.windows),
            "analysis_bandwidth_hz": coarse_profile.analysis_bandwidth_hz,
            "maximum_dc_safe_interval_hz": coarse_profile.maximum_dc_safe_interval_hz,
            "observations_per_window": coarse_observations_per_window,
            "raw_sample_seconds_per_window": coarse_seconds_per_window,
            "raw_sample_seconds_full_range": len(coarse_plan.windows) * coarse_seconds_per_window,
        },
    }


def _run_sweep(args: argparse.Namespace, destination: Path) -> tuple[float, str]:
    executable = args.hackrf_sweep or shutil.which("hackrf_sweep")
    if not executable:
        raise RuntimeError("hackrf_sweep bulunamadı.")
    command = [
        executable,
        "-d", args.serial,
        "-a", "0",
        "-p", "0",
        "-l", str(args.lna_gain_db),
        "-g", str(args.vga_gain_db),
        "-f", f"{args.lower_hz / 1_000_000:g}:{args.upper_hz / 1_000_000:g}",
        "-w", str(args.bin_width_hz),
        "-N", "1",
        "-r", str(destination),
    ]
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=args.timeout_seconds,
        check=False,
    )
    elapsed_seconds = time.perf_counter() - started
    output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    if completed.returncode != 0:
        raise RuntimeError(f"hackrf_sweep başarısız oldu ({completed.returncode}): {output[-1000:]}")
    return elapsed_seconds, output


def build_report(args: argparse.Namespace, raw_csv: Path, elapsed_seconds: float) -> dict[str, object]:
    summary = parse_sweep_csv(
        raw_csv,
        expected_lower_hz=args.lower_hz,
        expected_upper_hz=args.upper_hz,
    )
    return {
        "schema": "phase08-st04-search-profile-baseline-v1",
        "status": "baseline_measured",
        "phase08_complete": False,
        "st04_complete": False,
        "transmit_enabled": False,
        "requested_range_hz": [args.lower_hz, args.upper_hz],
        "receiver": {
            "serial": args.serial,
            "rf_amp_enabled": False,
            "antenna_port_power_enabled": False,
            "lna_gain_db": args.lna_gain_db,
            "vga_gain_db": args.vga_gain_db,
        },
        "profile_estimates": estimate_profiles(args.lower_hz, args.upper_hz),
        "physical_host_sweep": {
            "tool": "hackrf_sweep",
            "requested_bin_width_hz": args.bin_width_hz,
            "process_elapsed_seconds": elapsed_seconds,
            "csv_sha256": _sha256(raw_csv),
            **asdict(summary),
        },
        "limits": [
            "Bu tek, pasif ve operatör truth bilgisi olmayan ölçüm Pd/Pfa veya RF doğruluk kabulü değildir.",
            "hackrf_sweep sonucu yalnız hızlı host kaba arama karşılaştırma tabanıdır; FPGA doğrulaması değildir.",
            "Profil tahminleri yalnız ham örnek toplama alt sınırıdır; LO yerleşmesi, USB, filtre, Ethernet, FPGA/ARM ve arayüz süresi dahil değildir.",
            "Tek sweep tekrarlanabilir tarama süresi veya kısa yayın yakalama olasılığı kanıtlamaz.",
            "ST-04; tekrarlı zamanlama, kayıtlı aynı-IQ karşılaştırması ve kontrollü yayın matrisi tamamlanana kadar açık kalır.",
        ],
        "source_sha256": {
            name: _sha256(ROOT / name)
            for name in SOURCES
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--lower-hz", type=int, default=20_000_000)
    parser.add_argument("--upper-hz", type=int, default=6_000_000_000)
    parser.add_argument("--bin-width-hz", type=int, default=1_000_000)
    parser.add_argument("--lna-gain-db", type=int, default=16)
    parser.add_argument("--vga-gain-db", type=int, default=16)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--hackrf-sweep", default=None)
    args = parser.parse_args()
    if not 1_000_000 <= args.lower_hz < args.upper_hz <= 6_000_000_000:
        parser.error("Frekans aralığı 1 MHz–6 GHz içinde olmalıdır.")
    if args.output.exists() or args.raw_output.exists():
        parser.error("Önceki ST-04 kanıtının üzerine yazılmaz.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="baz-st04-") as temporary:
        captured = Path(temporary) / "sweep.csv"
        elapsed_seconds, _ = _run_sweep(args, captured)
        report = build_report(args, captured, elapsed_seconds)
        shutil.copyfile(captured, args.raw_output)
        report["physical_host_sweep"]["csv_sha256"] = _sha256(args.raw_output)  # type: ignore[index]
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps({
        "status": report["status"],
        "st04_complete": report["st04_complete"],
        "process_elapsed_seconds": report["physical_host_sweep"]["process_elapsed_seconds"],  # type: ignore[index]
        "gap_count": report["physical_host_sweep"]["gap_count"],  # type: ignore[index]
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
