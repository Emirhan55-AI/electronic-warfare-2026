"""Bounded subprocess runner used only by the real HackRF CLI backend."""

from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .contracts import AcquisitionError


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    stdout_truncated: bool
    stderr_truncated: bool


class _BoundedReader(threading.Thread):
    def __init__(self, stream: object, limit: int) -> None:
        super().__init__(daemon=True)
        self.stream = stream
        self.limit = limit
        self.data = bytearray()
        self.truncated = False

    def run(self) -> None:
        while True:
            chunk = self.stream.read(4096)  # type: ignore[attr-defined]
            if not chunk:
                return
            remaining = self.limit - len(self.data)
            if remaining > 0:
                self.data.extend(chunk[:remaining])
            if len(chunk) > remaining:
                self.truncated = True


class SafeProcessRunner:
    """Run an explicit argv with bounded streams, cancellation, and hard cleanup."""

    def __init__(
        self,
        *,
        allowed_executables: Iterable[str] = ("hackrf_info", "hackrf_transfer", "hackrf_sweep"),
        output_limit_bytes: int = 32_768,
        terminate_grace_seconds: float = 0.25,
    ) -> None:
        self.allowed_executables = frozenset(item.casefold().removesuffix(".exe") for item in allowed_executables)
        self.output_limit_bytes = output_limit_bytes
        self.terminate_grace_seconds = terminate_grace_seconds
        self._lock = threading.Lock()
        self._active: subprocess.Popen[bytes] | None = None

    @property
    def active(self) -> bool:
        with self._lock:
            return self._active is not None

    def _terminate(self, process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=self.terminate_grace_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1.0)

    def run(
        self,
        argv: list[str],
        *,
        timeout_seconds: float,
        cancellation: threading.Event | None = None,
    ) -> ProcessResult:
        if not argv or not all(isinstance(item, str) and item and "\x00" not in item for item in argv):
            raise AcquisitionError("invalid_command", "Haricî süreç argümanları geçersizdir.")
        executable = Path(argv[0]).name.casefold().removesuffix(".exe")
        if executable not in self.allowed_executables:
            raise AcquisitionError("command_not_allowed", "Haricî süreç allowlist dışında kaldı.")
        if not 0.05 <= timeout_seconds <= 30.0:
            raise AcquisitionError("invalid_timeout", "Süreç zaman aşımı güvenli sınırın dışındadır.")
        with self._lock:
            if self._active is not None:
                raise AcquisitionError("process_busy", "Başka bir HackRF işlemi hâlâ çalışıyor.")
            try:
                process = subprocess.Popen(
                    argv,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except OSError as exc:
                raise AcquisitionError("process_start_failed", "HackRF aracı başlatılamadı.") from exc
            self._active = process
        assert process.stdout is not None and process.stderr is not None
        stdout_reader = _BoundedReader(process.stdout, self.output_limit_bytes)
        stderr_reader = _BoundedReader(process.stderr, self.output_limit_bytes)
        stdout_reader.start()
        stderr_reader.start()
        deadline = time.monotonic() + timeout_seconds
        state = "completed"
        try:
            while process.poll() is None:
                if cancellation is not None and cancellation.is_set():
                    state = "cancelled"
                    self._terminate(process)
                    break
                if time.monotonic() >= deadline:
                    state = "timeout"
                    self._terminate(process)
                    break
                time.sleep(0.01)
            returncode = process.wait(timeout=1.0)
        finally:
            if process.poll() is None:
                self._terminate(process)
            stdout_reader.join(timeout=1.0)
            stderr_reader.join(timeout=1.0)
            process.stdout.close()
            process.stderr.close()
            with self._lock:
                if self._active is process:
                    self._active = None
        if state == "cancelled":
            raise AcquisitionError("operation_cancelled", "HackRF işlemi iptal edildi.")
        if state == "timeout":
            raise AcquisitionError("operation_timeout", "HackRF işlemi zaman aşımına uğradı.")
        return ProcessResult(
            returncode=returncode,
            stdout=bytes(stdout_reader.data),
            stderr=bytes(stderr_reader.data),
            stdout_truncated=stdout_reader.truncated,
            stderr_truncated=stderr_reader.truncated,
        )

    def close(self) -> None:
        with self._lock:
            process = self._active
        if process is not None:
            self._terminate(process)
