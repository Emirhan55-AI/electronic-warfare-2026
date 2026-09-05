"""Measure repeated receive-only HackRF sweep timings for ST-04."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from typing import Iterable
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.measure_st04_search_profiles import SweepCsvSummary, parse_sweep_csv


DEFAULT_BIN_WIDTHS_HZ = (1_000_000, 100_000, 25_000)
SOURCES = (
    "scripts/measure_st04_search_profiles.py",
    "scripts/measure_st04_sweep_resolution.py",
)
_TIMING_PATTERN = re.compile(
    r"Total sweeps:\s*(?P<count>\d+)\s+in\s+"
    r"(?P<seconds>[0-9]+(?:\.[0-9]+)?)\s+seconds\s+"
    r"\((?P<rate>[0-9]+(?:\.[0-9]+)?)\s+sweeps/second\)"
)
_SHORTFALL_PATTERN = re.compile(r"Number of shortfalls:\s*(\d+)")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _percentile(values: Iterable[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("Yüzdelik hesabı için ölçüm yok.")
    if not 0.0 <= percentile <= 1.0:
        raise ValueError("Yüzdelik 0–1 aralığında olmalıdır.")
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def parse_hackrf_timing(output: str) -> tuple[int, float, float]:
    """Return total sweeps, internal seconds and reported sweeps/second."""
    matches = tuple(_TIMING_PATTERN.finditer(output))
    if len(matches) != 1:
        raise ValueError("hackrf_sweep toplam zaman satırı tekil değil.")
    match = matches[0]
    return (
        int(match.group("count")),
        float(match.group("seconds")),
        float(match.group("rate")),
    )


def parse_shortfalls(output: str) -> int:
    match = _SHORTFALL_PATTERN.search(output)
    if not match:
        raise ValueError("HackRF shortfall sayacı okunamadı.")
    return int(match.group(1))


def split_and_summarize_sweeps(
    path: Path,
    *,
    expected_lower_hz: int,
    expected_upper_hz: int,
    expected_sweeps: int,
    workspace: Path,
) -> tuple[SweepCsvSummary, ...]:
    """Split ``hackrf_sweep -n`` output by timestamp and validate every sweep."""
    grouped: dict[str, list[list[str]]] = {}
    with path.open("r", encoding="utf-8", newline="") as stream:
        for line_number, row in enumerate(csv.reader(stream), start=1):
            if len(row) < 7:
                raise ValueError(f"Sweep satırı {line_number} eksik.")
            timestamp = f"{row[0].strip()}T{row[1].strip()}"
            grouped.setdefault(timestamp, []).append(row)
    if len(grouped) != expected_sweeps:
        raise ValueError(
            f"Beklenen {expected_sweeps} tam sweep yerine {len(grouped)} zaman grubu bulundu."
        )

    summaries: list[SweepCsvSummary] = []
    for index, rows in enumerate(grouped.values(), start=1):
        single_path = workspace / f"single-{index:02d}.csv"
        with single_path.open("w", encoding="utf-8", newline="") as stream:
            csv.writer(stream, lineterminator="\n").writerows(rows)
        summaries.append(
            parse_sweep_csv(
                single_path,
                expected_lower_hz=expected_lower_hz,
                expected_upper_hz=expected_upper_hz,
            )
        )
    return tuple(summaries)


def _run_tool(command: list[str], *, timeout_seconds: float) -> tuple[float, str]:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
        check=False,
    )
    elapsed_seconds = time.perf_counter() - started
    output = "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Komut başarısız oldu ({completed.returncode}): {output[-1200:]}"
        )
    return elapsed_seconds, output


def _resolve_tool(explicit: str | None, name: str) -> str:
    executable = explicit or shutil.which(name)
    if not executable:
        raise RuntimeError(f"{name} bulunamadı.")
    return executable


def _run_sweep(
    args: argparse.Namespace,
    *,
    executable: str,
    bin_width_hz: int,
    destination: Path,
) -> tuple[float, str]:
    command = [
        executable,
        "-d", args.serial,
        "-a", "0",
        "-p", "0",
        "-l", str(args.lna_gain_db),
        "-g", str(args.vga_gain_db),
        "-f", f"{args.lower_hz / 1_000_000:g}:{args.upper_hz / 1_000_000:g}",
        "-w", str(bin_width_hz),
        "-P", "measure",
        "-n",
        "-N", str(args.sweeps_per_trial),
        "-r", str(destination),
    ]
    return _run_tool(command, timeout_seconds=args.timeout_seconds)


def _summary_stats(values: list[float]) -> dict[str, float]:
    return {
        "minimum": min(values),
        "median": statistics.median(values),
        "p95": _percentile(values, 0.95),
        "maximum": max(values),
        "mean": statistics.fmean(values),
    }


def summarize_profile(
    *,
    bin_width_hz: int,
    sweeps_per_trial: int,
    trials: list[dict[str, object]],
) -> dict[str, object]:
    process_per_sweep = [
        float(trial["process_elapsed_seconds"]) / sweeps_per_trial for trial in trials
    ]
    internal_per_sweep = [
        float(trial["hackrf_internal_seconds"]) / sweeps_per_trial for trial in trials
    ]
    bytes_per_sweep = [
        float(trial["csv_bytes"]) / sweeps_per_trial for trial in trials
    ]
    bins_per_sweep = {
        int(sweep["power_bins"])
        for trial in trials
        for sweep in trial["sweeps"]  # type: ignore[union-attr]
    }
    gap_counts = [
        int(sweep["gap_count"])
        for trial in trials
        for sweep in trial["sweeps"]  # type: ignore[union-attr]
    ]
    actual_bin_widths_hz = {
        float(width)
        for trial in trials
        for sweep in trial["sweeps"]  # type: ignore[union-attr]
        for width in sweep["bin_widths_hz"]
    }
    return {
        "requested_bin_width_hz": bin_width_hz,
        "actual_bin_widths_hz": sorted(actual_bin_widths_hz),
        "trial_count": len(trials),
        "sweeps_per_trial": sweeps_per_trial,
        "validated_sweep_count": len(trials) * sweeps_per_trial,
        "all_sweeps_gap_free": all(value == 0 for value in gap_counts),
        "power_bins_per_sweep": sorted(bins_per_sweep),
        "process_seconds_per_sweep": _summary_stats(process_per_sweep),
        "hackrf_internal_seconds_per_sweep": _summary_stats(internal_per_sweep),
        "csv_bytes_per_sweep": _summary_stats(bytes_per_sweep),
        "trials": trials,
    }


def build_report(
    args: argparse.Namespace,
    *,
    profiles: list[dict[str, object]],
    archive_path: Path,
    archive_entries: list[str],
    hackrf_info_output: str,
    shortfalls_before: int,
    shortfalls_after: int,
) -> dict[str, object]:
    fastest = min(
        profiles,
        key=lambda profile: profile["process_seconds_per_sweep"]["median"],  # type: ignore[index]
    )
    process_medians = [
        float(profile["process_seconds_per_sweep"]["median"])  # type: ignore[index]
        for profile in profiles
    ]
    smallest_output = min(
        profiles,
        key=lambda profile: profile["csv_bytes_per_sweep"]["median"],  # type: ignore[index]
    )
    largest_output = max(
        profiles,
        key=lambda profile: profile["csv_bytes_per_sweep"]["median"],  # type: ignore[index]
    )
    process_median_spread_ratio = max(process_medians) / min(process_medians) - 1.0
    output_size_ratio = (
        float(largest_output["csv_bytes_per_sweep"]["median"])  # type: ignore[index]
        / float(smallest_output["csv_bytes_per_sweep"]["median"])  # type: ignore[index]
    )
    return {
        "schema": "phase08-st04-sweep-resolution-v1",
        "status": "timing_characterized",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
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
            "hackrf_info_sha256": _sha256_bytes(hackrf_info_output.encode("utf-8")),
        },
        "method": {
            "tool": "hackrf_sweep",
            "sample_rate_hz": 20_000_000,
            "baseband_filter_bandwidth_hz": 15_000_000,
            "planner": "measure",
            "constant_timestamp_per_sweep": True,
            "independent_process_trials": args.trials,
            "sweeps_per_trial": args.sweeps_per_trial,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "usb_shortfall_counter": {
            "before": shortfalls_before,
            "after": shortfalls_after,
            "after_is_zero": shortfalls_after == 0,
        },
        "profiles": profiles,
        "timing_only_result": {
            "lowest_process_median_bin_width_hz": fastest["requested_bin_width_hz"],
            "process_median_spread_ratio": process_median_spread_ratio,
            "all_process_medians_within_5_percent": process_median_spread_ratio <= 0.05,
            "largest_to_smallest_csv_size_ratio": output_size_ratio,
            "selected_for_rf_detection": False,
            "reason": (
                "Zaman ve kapsama ölçümü tek başına RF tespit profili seçmez; "
                "aynı kayıt ve kontrollü kör yayın matrisi gereklidir."
            ),
        },
        "raw_archive": {
            "path": archive_path.resolve().relative_to(ROOT.resolve()).as_posix(),
            "sha256": _sha256(archive_path),
            "entries": archive_entries,
        },
        "limits": [
            "Ölçüm pasif alımdır; verici işlevi, RF yükselteci ve anten portu beslemesi kullanılmamıştır.",
            "Zamanlama ve boşluksuz frekans kapsaması ölçülmüştür; yayın doğruluğu, Pd/Pfa ve hassasiyet ölçülmemiştir.",
            "hackrf_sweep host kaba arama aracıdır; FPGA/ARM karar zincirinin yerine geçmez.",
            "FFT güç hücresi genişliği tek başına dar veya geniş bant yayın yakalama başarısını kanıtlamaz.",
            "ST-04 aynı kayıt karşılaştırması ve kontrollü kör yayın matrisi tamamlanana kadar açık kalır.",
        ],
        "source_sha256": {name: _sha256(ROOT / name) for name in SOURCES},
    }


def _write_archive(source_dir: Path, destination: Path) -> list[str]:
    entries = sorted(
        path.relative_to(source_dir).as_posix()
        for path in source_dir.rglob("*")
        if path.is_file()
    )
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in entries:
            archive.write(source_dir / entry, entry)
    return entries


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if not 1_000_000 <= args.lower_hz < args.upper_hz <= 6_000_000_000:
        parser.error("Frekans aralığı 1 MHz–6 GHz içinde olmalıdır.")
    if args.trials < 2 or args.sweeps_per_trial < 2:
        parser.error("Tekrarlanabilirlik için en az iki süreç ve süreç başına iki sweep gerekir.")
    if len(set(args.bin_width_hz)) != len(args.bin_width_hz):
        parser.error("Güç hücresi genişlikleri tekil olmalıdır.")
    if any(not 2_445 <= width <= 5_000_000 for width in args.bin_width_hz):
        parser.error("Güç hücresi genişliği 2.445–5.000.000 Hz içinde olmalıdır.")
    if args.output.exists() or args.raw_archive.exists():
        parser.error("Önceki ST-04 kanıtının üzerine yazılmaz.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-archive", type=Path, required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--lower-hz", type=int, default=20_000_000)
    parser.add_argument("--upper-hz", type=int, default=6_000_000_000)
    parser.add_argument(
        "--bin-width-hz",
        type=int,
        action="append",
        default=None,
        help="Tekrarlanabilir; verilmezse 1 MHz, 100 kHz ve 25 kHz ölçülür.",
    )
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--sweeps-per-trial", type=int, default=3)
    parser.add_argument("--lna-gain-db", type=int, default=16)
    parser.add_argument("--vga-gain-db", type=int, default=16)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--hackrf-sweep", default=None)
    parser.add_argument("--hackrf-info", default=None)
    parser.add_argument("--hackrf-debug", default=None)
    args = parser.parse_args()
    args.bin_width_hz = args.bin_width_hz or list(DEFAULT_BIN_WIDTHS_HZ)
    _validate_args(parser, args)

    sweep_executable = _resolve_tool(args.hackrf_sweep, "hackrf_sweep")
    info_executable = _resolve_tool(args.hackrf_info, "hackrf_info")
    debug_executable = _resolve_tool(args.hackrf_debug, "hackrf_debug")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.raw_archive.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="baz-st04-resolution-") as temporary:
        temporary_path = Path(temporary)
        raw_dir = temporary_path / "raw"
        raw_dir.mkdir()
        _, hackrf_info_output = _run_tool(
            [info_executable, "-d", args.serial], timeout_seconds=args.timeout_seconds
        )
        _, shortfalls_before_output = _run_tool(
            [debug_executable, "-d", args.serial, "-S"],
            timeout_seconds=args.timeout_seconds,
        )
        (raw_dir / "hackrf-info.txt").write_text(
            hackrf_info_output + "\n", encoding="utf-8", newline="\n"
        )
        (raw_dir / "shortfalls-before.txt").write_text(
            shortfalls_before_output + "\n", encoding="utf-8", newline="\n"
        )

        profiles: list[dict[str, object]] = []
        for bin_width_hz in args.bin_width_hz:
            trials: list[dict[str, object]] = []
            for trial_index in range(1, args.trials + 1):
                stem = f"bin-{bin_width_hz:07d}-trial-{trial_index:02d}"
                capture_path = raw_dir / f"{stem}.csv"
                process_seconds, output = _run_sweep(
                    args,
                    executable=sweep_executable,
                    bin_width_hz=bin_width_hz,
                    destination=capture_path,
                )
                log_path = raw_dir / f"{stem}.txt"
                log_path.write_text(output + "\n", encoding="utf-8", newline="\n")
                reported_sweeps, internal_seconds, reported_rate = parse_hackrf_timing(output)
                if reported_sweeps != args.sweeps_per_trial:
                    raise ValueError("hackrf_sweep istenen sweep sayısını tamamlamadı.")
                group_workspace = temporary_path / f"groups-{stem}"
                group_workspace.mkdir()
                summaries = split_and_summarize_sweeps(
                    capture_path,
                    expected_lower_hz=args.lower_hz,
                    expected_upper_hz=args.upper_hz,
                    expected_sweeps=args.sweeps_per_trial,
                    workspace=group_workspace,
                )
                trials.append(
                    {
                        "trial": trial_index,
                        "csv_entry": capture_path.relative_to(raw_dir).as_posix(),
                        "csv_sha256": _sha256(capture_path),
                        "csv_bytes": capture_path.stat().st_size,
                        "log_entry": log_path.relative_to(raw_dir).as_posix(),
                        "process_elapsed_seconds": process_seconds,
                        "hackrf_internal_seconds": internal_seconds,
                        "reported_sweeps_per_second": reported_rate,
                        "sweeps": [asdict(summary) for summary in summaries],
                    }
                )
            profiles.append(
                summarize_profile(
                    bin_width_hz=bin_width_hz,
                    sweeps_per_trial=args.sweeps_per_trial,
                    trials=trials,
                )
            )

        _, shortfalls_after_output = _run_tool(
            [debug_executable, "-d", args.serial, "-S"],
            timeout_seconds=args.timeout_seconds,
        )
        (raw_dir / "shortfalls-after.txt").write_text(
            shortfalls_after_output + "\n", encoding="utf-8", newline="\n"
        )
        archive_entries = _write_archive(raw_dir, args.raw_archive)
        report = build_report(
            args,
            profiles=profiles,
            archive_path=args.raw_archive,
            archive_entries=archive_entries,
            hackrf_info_output=hackrf_info_output,
            shortfalls_before=parse_shortfalls(shortfalls_before_output),
            shortfalls_after=parse_shortfalls(shortfalls_after_output),
        )
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    print(
        json.dumps(
            {
                "status": report["status"],
                "st04_complete": report["st04_complete"],
                "profile_count": len(report["profiles"]),
                "validated_sweep_count": sum(
                    profile["validated_sweep_count"] for profile in report["profiles"]
                ),
                "shortfalls_after": report["usb_shortfall_counter"]["after"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
