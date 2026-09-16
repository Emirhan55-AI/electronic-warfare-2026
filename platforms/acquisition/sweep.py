"""Bounded, serial-bound HackRF sweep screening; never a confirmed detection."""

from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path
import shutil
import threading

from .contracts import AcquisitionError, RXConfig
from .hackrf import _help_options
from .process import SafeProcessRunner


SWEEP_BIN_HZ = 25_000
SWEEP_CONTRAST_DB = 6.0
SWEEP_CHUNK_HZ = 100_000_000
SWEEP_OUTPUT_LIMIT = 2_000_000
SWEEP_OPTIONS = frozenset(("-d", "-f", "-w", "-N", "-n", "-a", "-p", "-l", "-g"))


def parse_sweep_csv(payload: bytes, lower_hz: int, upper_hz: int):
    """Require two complete sweeps; retain repeatable local power candidates.

    CLI rows are interleaved, not frequency ordered. The sixth column is sample
    count, not the number of power columns. Validate actual frequency coverage
    independently for each sweep timestamp before reporting screening coverage.
    """
    if len(payload) > SWEEP_OUTPUT_LIMIT:
        raise AcquisitionError("sweep_output_too_large", "Kaba tarama çıktı sınırını aştı.")
    sweeps = {}
    try:
        for row in csv.reader(payload.decode("utf-8").splitlines()):
            if not row:
                continue
            if len(row) < 7:
                raise ValueError("columns")
            stamp = (row[0].strip(), row[1].strip())
            lo, hi = int(row[2]), int(row[3])
            width, samples = float(row[4]), int(row[5])
            powers = [float(value) for value in row[6:]]
            if (not all(math.isfinite(p) for p in powers)
                    or not math.isfinite(width) or width <= 0 or samples <= 0
                    or not 0 <= lo < hi <= 6_020_000_000
                    or not math.isclose(width, SWEEP_BIN_HZ, rel_tol=.01)
                    or abs(len(powers) * width - (hi - lo)) > max(1., width * .01)):
                raise ValueError("geometry")
            sweep = sweeps.setdefault(stamp, {"intervals": [], "candidates": []})
            if len(sweeps) > 2 or len(sweep["intervals"]) >= 128:
                raise ValueError("row limit")
            # A low quantile avoids letting a few strong bins raise the baseline.
            baseline = sorted(powers)[int(.2 * (len(powers) - 1))]
            sweep["intervals"].append((lo, hi))
            for index, power in enumerate(powers):
                center = lo + (index + .5) * width
                if lower_hz <= center < upper_hz and power >= baseline + SWEEP_CONTRAST_DB:
                    sweep["candidates"].append(int(round(center)))
        if len(sweeps) != 2:
            raise ValueError("incomplete sweep count")
        candidates = []
        for sweep in sweeps.values():
            cursor = lower_hz
            for lo, hi in sorted(sweep["intervals"]):
                if hi <= lower_hz or lo >= upper_hz:
                    continue
                if lo > cursor or lo < cursor and cursor != lower_hz:
                    raise ValueError("gap or overlap")
                cursor = max(cursor, min(hi, upper_hz))
            if cursor != upper_hz:
                raise ValueError("incomplete coverage")
            candidates.append(set(sweep["candidates"]))
        return tuple(sorted(candidates[0] & candidates[1]))
    except (ValueError, UnicodeError, OverflowError, csv.Error) as exc:
        raise AcquisitionError("sweep_malformed", "Kaba taramada iki tam ve tutarlı tur doğrulanamadı.") from exc


class HackRFSweepScreen:
    def __init__(self, transfer_executable: str, *, runner=None):
        suffix = ".exe" if Path(transfer_executable).suffix.lower() == ".exe" else ""
        sibling = Path(transfer_executable).with_name("hackrf_sweep" + suffix)
        self.executable = str(sibling) if sibling.is_file() else shutil.which("hackrf_sweep")
        self.runner = runner or SafeProcessRunner(output_limit_bytes=SWEEP_OUTPUT_LIMIT)

    def cancel(self):
        self.runner.close()

    def run(self, config, serial: str, cancellation: threading.Event, callback=None):
        RXConfig(center_frequency_hz=config.lower_hz, sample_rate_hz=20_000_000,
                 lna_gain_db=config.lna_gain_db, vga_gain_db=config.vga_gain_db,
                 device_serial=serial)
        if cancellation.is_set():
            raise AcquisitionError("operation_cancelled", "Kaba tarama iptal edildi.")
        if not self.executable:
            raise AcquisitionError("sweep_unavailable", "hackrf_sweep bulunamadı; tam tarama profilini seçin.")
        help_result = self.runner.run([self.executable, "-h"], timeout_seconds=2., cancellation=cancellation)
        options = set(_help_options(help_result.stdout + help_result.stderr))
        if (help_result.returncode not in (0, 1) or help_result.stdout_truncated
                or help_result.stderr_truncated
                or not SWEEP_OPTIONS <= options):
            raise AcquisitionError("sweep_unavailable", "Kurulu hızlı tarama aracı gerekli seçenekleri desteklemiyor.")
        lower = config.lower_hz // 1_000_000 * 1_000_000
        upper = math.ceil(config.upper_hz / 1_000_000) * 1_000_000
        selected = set()
        evidence = []
        window_count = len(config.windows())
        for start in range(lower, upper, SWEEP_CHUNK_HZ):
            if cancellation.is_set():
                raise AcquisitionError("operation_cancelled", "Kaba tarama iptal edildi.")
            end = min(start + SWEEP_CHUNK_HZ, upper)
            argv = [self.executable, "-d", serial, "-f", f"{start // 1_000_000}:{end // 1_000_000}",
                    "-w", str(SWEEP_BIN_HZ), "-N", "2", "-n", "-a", "0", "-p", "0",
                    "-l", str(config.lna_gain_db), "-g", str(config.vga_gain_db)]
            if "-P" in options:
                argv.extend(("-P", "estimate"))
            result = self.runner.run(argv, timeout_seconds=30., cancellation=cancellation)
            if cancellation.is_set():
                raise AcquisitionError("operation_cancelled", "Kaba tarama iptal edildi.")
            if result.returncode != 0 or result.stdout_truncated or result.stderr_truncated:
                raise AcquisitionError("sweep_failed", "Kaba tarama başarısız veya çıktısı eksik.")
            frequencies = parse_sweep_csv(result.stdout, start, end)
            # Include neighbouring responsibility cells to cover bin/edge uncertainty.
            for hz in frequencies:
                if config.lower_hz <= hz < config.upper_hz:
                    index = (hz - config.lower_hz) // 600_000
                    selected.update(i for i in (index - 1, index, index + 1)
                                    if 0 <= i < window_count)
            row = {"lower_hz": start, "upper_hz": end, "candidate_bins": len(frequencies),
                   "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                   "argv": argv, "csv": result.stdout.decode("utf-8")}
            evidence.append({key: value for key, value in row.items() if key != "csv"})
            if callback:
                callback(end, row)
        return tuple(sorted(selected)), evidence
