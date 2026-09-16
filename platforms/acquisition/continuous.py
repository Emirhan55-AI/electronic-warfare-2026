"""Bounded, receive-only HackRF stdout streaming for the live ED path."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import subprocess
import threading
import time
from typing import Iterator

from .contracts import AcquisitionError, RXConfig


# 878,906 input frames correspond to just under 30 minutes at 8 MS/s with
# 16,384 complex samples per frame. The process remains bounded by frame count,
# watchdog time and the fixed-size stdout/stderr consumers.
MAX_STREAM_FRAMES = 878_906
# A product session may capture a small, discarded tuner-settling prefix while
# still delivering MAX_STREAM_FRAMES usable frames. The total process remains
# explicitly bounded; this allowance cannot extend the presented session.
MAX_CAPTURE_FRAMES = MAX_STREAM_FRAMES + 64
STDERR_LIMIT_BYTES = 262_144


def _reserve_hackrf_process_cores(process: subprocess.Popen[bytes]) -> int | None:
    """Keep the libusb child on dedicated physical cores on Windows."""
    if os.name != "nt" or (logical_processors := (os.cpu_count() or 1)) < 4:
        return None
    import ctypes
    from ctypes import wintypes

    class _LogicalProcessorInformation(ctypes.Structure):
        _fields_ = (
            ("processor_mask", ctypes.c_size_t),
            ("relationship", ctypes.c_int),
            ("reserved", ctypes.c_byte * 16),
        )

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_topology = kernel32.GetLogicalProcessorInformation
    get_topology.argtypes = (
        ctypes.POINTER(_LogicalProcessorInformation), ctypes.POINTER(wintypes.DWORD),
    )
    get_topology.restype = wintypes.BOOL
    byte_count = wintypes.DWORD()
    get_topology(None, ctypes.byref(byte_count))
    if not byte_count.value:
        raise OSError(ctypes.get_last_error(), "Windows işlemci topolojisi okunamadı.")
    topology_buffer = (ctypes.c_byte * byte_count.value)()
    if not get_topology(
        ctypes.cast(topology_buffer, ctypes.POINTER(_LogicalProcessorInformation)),
        ctypes.byref(byte_count),
    ):
        raise OSError(ctypes.get_last_error(), "Windows işlemci topolojisi okunamadı.")
    entry_size = ctypes.sizeof(_LogicalProcessorInformation)
    core_masks = []
    for offset in range(0, byte_count.value, entry_size):
        entry = ctypes.cast(
            ctypes.byref(topology_buffer, offset),
            ctypes.POINTER(_LogicalProcessorInformation),
        ).contents
        if entry.relationship == 0:  # RelationProcessorCore
            core_masks.append(int(entry.processor_mask))
    if len(core_masks) < 2:
        return None
    reserved_mask = 0
    # hackrf_transfer has separate USB/device and output work.  Three physical
    # cores leave this six-core target enough room for those threads while the
    # GUI, channelizer and Python capture threads remain on the other three.
    # On smaller hosts always leave at least one physical core to the parent.
    for core_mask in core_masks[-min(3, len(core_masks) - 1):]:
        reserved_mask |= core_mask
    set_affinity = ctypes.WinDLL("kernel32", use_last_error=True).SetProcessAffinityMask
    set_affinity.argtypes = (wintypes.HANDLE, ctypes.c_size_t)
    set_affinity.restype = wintypes.BOOL
    if not set_affinity(wintypes.HANDLE(process._handle), reserved_mask):  # type: ignore[attr-defined]
        raise OSError(ctypes.get_last_error(), "HackRF süreç çekirdek ayrımı uygulanamadı.")
    get_affinity = ctypes.WinDLL("kernel32", use_last_error=True).GetProcessAffinityMask
    get_affinity.argtypes = (
        wintypes.HANDLE, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t),
    )
    get_affinity.restype = wintypes.BOOL
    current_process = ctypes.WinDLL("kernel32", use_last_error=True).GetCurrentProcess()
    previous = ctypes.c_size_t()
    system = ctypes.c_size_t()
    if not get_affinity(current_process, ctypes.byref(previous), ctypes.byref(system)):
        raise OSError(ctypes.get_last_error(), "Uygulama süreç çekirdek maskesi okunamadı.")
    application_mask = previous.value & ~reserved_mask
    if not application_mask or not set_affinity(current_process, application_mask):
        raise OSError(ctypes.get_last_error(), "Uygulama süreç çekirdek ayrımı uygulanamadı.")
    return int(previous.value)


def _restore_host_process_cores(previous_mask: int | None) -> None:
    if os.name != "nt" or previous_mask is None:
        return
    import ctypes
    from ctypes import wintypes
    set_affinity = ctypes.WinDLL("kernel32", use_last_error=True).SetProcessAffinityMask
    set_affinity.argtypes = (wintypes.HANDLE, ctypes.c_size_t)
    set_affinity.restype = wintypes.BOOL
    current_process = ctypes.WinDLL("kernel32", use_last_error=True).GetCurrentProcess()
    set_affinity(current_process, previous_mask)


def build_continuous_receive_argv(
    executable: str,
    config: RXConfig,
    frame_count: int,
) -> list[str]:
    """Build a serial-bound RX-only stdout command for whole 16,384-sample frames."""
    if Path(executable).name.casefold().removesuffix(".exe") != "hackrf_transfer":
        raise AcquisitionError("command_not_allowed", "Canlı RX yalnız hackrf_transfer kullanabilir.")
    if config.device_serial is None:
        raise AcquisitionError("device_serial_unassigned", "ED_RX HackRF seri kimliği atanmamış.")
    if not 1 <= frame_count <= MAX_CAPTURE_FRAMES:
        raise AcquisitionError("invalid_stream_length", "Canlı RX kare sayısı güvenli sınırın dışındadır.")
    total_samples = config.sample_count * frame_count
    return [
        executable,
        "-d",
        config.device_serial,
        "-r",
        "-",
        "-f",
        str(config.center_frequency_hz),
        "-s",
        str(config.sample_rate_hz),
        "-n",
        str(total_samples),
        "-a",
        "1" if config.rf_amplifier else "0",
        "-l",
        str(config.lna_gain_db),
        "-g",
        str(config.vga_gain_db),
        "-B",
    ]


@dataclass(frozen=True)
class HackRFStreamStatistics:
    frames_received: int
    bytes_received: int
    elapsed_seconds: float
    overruns: int
    longest_overrun_bytes: int
    process_returncode: int
    stderr_text: str


class _BoundedCollector(threading.Thread):
    def __init__(self, stream: object) -> None:
        super().__init__(daemon=True)
        self.stream = stream
        self.data = bytearray()
        self.truncated = False

    def run(self) -> None:
        while True:
            block = self.stream.read(4096)  # type: ignore[attr-defined]
            if not block:
                return
            remaining = STDERR_LIMIT_BYTES - len(self.data)
            if remaining > 0:
                self.data.extend(block[:remaining])
            if len(block) > remaining:
                self.truncated = True


def parse_hackrf_buffer_statistics(stderr_text: str) -> tuple[int, int]:
    matches = re.findall(r"(?m)^\s*(\d+) overruns, longest (\d+) bytes\s*$", stderr_text)
    if not matches:
        raise AcquisitionError(
            "buffer_statistics_missing",
            "HackRF RX tampon istatistiği doğrulanamadı.",
        )
    overruns, longest = matches[-1]
    return int(overruns), int(longest)


class HackRFContinuousRX:
    """One bounded hackrf_transfer process whose stdout is consumed frame by frame."""

    def __init__(
        self,
        executable: str,
        config: RXConfig,
        frame_count: int,
        *,
        cancellation: threading.Event | None = None,
    ) -> None:
        self.argv = build_continuous_receive_argv(executable, config, frame_count)
        self._binary_pipe = None
        self._output = None
        self.frame_count = frame_count
        self.frame_bytes = config.sample_count * 2
        self.cancellation = cancellation or threading.Event()
        self._process: subprocess.Popen[bytes] | None = None
        self._stderr: _BoundedCollector | None = None
        self._started = 0.0
        self._frames_received = 0
        self._bytes_received = 0
        self._finished = False
        expected_seconds = config.sample_count * frame_count / config.sample_rate_hz
        self._maximum_seconds = max(2.0, expected_seconds * 2.0 + 2.0)
        self._watchdog: threading.Timer | None = None
        self._timed_out = False
        self._host_affinity_mask: int | None = None
        self.statistics: HackRFStreamStatistics | None = None

    def __enter__(self) -> HackRFContinuousRX:
        if self._process is not None:
            raise AcquisitionError("stream_already_started", "Canlı RX akışı zaten başlatıldı.")
        try:
            if os.name == "nt":
                from .windows_pipe import BinaryReceivePipe
                self._binary_pipe = BinaryReceivePipe()
                self.argv[self.argv.index("-r") + 1] = self._binary_pipe.path
            process = subprocess.Popen(
                self.argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL if self._binary_pipe is not None else subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                bufsize=0,
                creationflags=(
                    getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    # The bounded RX child owns the time-sensitive libusb
                    # callback. HIGH is still below Windows REALTIME and ends
                    # with this receive-only process.
                    | getattr(subprocess, "HIGH_PRIORITY_CLASS", 0)
                ),
            )
            self._host_affinity_mask = _reserve_hackrf_process_cores(process)
        except Exception as exc:
            if "process" in locals() and process.poll() is None:
                process.terminate()
                process.wait(timeout=1.0)
            if self._binary_pipe is not None:
                self._binary_pipe.close()
            _restore_host_process_cores(self._host_affinity_mask)
            self._host_affinity_mask = None
            raise AcquisitionError("process_start_failed", "HackRF canlı RX başlatılamadı.") from exc
        assert process.stderr is not None
        self._process = process
        self._output = self._binary_pipe if self._binary_pipe is not None else process.stdout
        self._stderr = _BoundedCollector(process.stderr)
        self._stderr.start()
        self._started = time.perf_counter()
        self._watchdog = threading.Timer(self._maximum_seconds, self._expire)
        self._watchdog.daemon = True
        self._watchdog.start()
        if self._binary_pipe is not None:
            try:
                self._binary_pipe.connect(process)
            except OSError as exc:
                self.close()
                raise AcquisitionError("binary_pipe_failed", "HackRF ikili alım bağlantısı kurulamadı.") from exc
        return self

    def __iter__(self) -> Iterator[bytes]:
        if self._process is None or self._output is None:
            raise AcquisitionError("stream_not_started", "Canlı RX akışı başlatılmadı.")
        if self._frames_received:
            raise AcquisitionError("stream_already_consumed", "Canlı RX akışı yalnız bir kez tüketilebilir.")
        for _ in range(self.frame_count):
            if self.cancellation.is_set():
                raise AcquisitionError("operation_cancelled", "HackRF canlı RX iptal edildi.")
            payload = self._read_exact(self.frame_bytes)
            self._frames_received += 1
            self._bytes_received += len(payload)
            yield payload
        self._finish()

    def _read_exact(self, byte_count: int) -> bytes:
        assert self._process is not None and self._output is not None
        payload = bytearray()
        while len(payload) < byte_count:
            block = self._output.read(byte_count - len(payload))
            if not block:
                if self._timed_out:
                    raise AcquisitionError("stream_timeout", "HackRF canlı RX zaman aşımına uğradı.")
                raise self._short_stream_error()
            payload.extend(block)
        return bytes(payload)

    def _short_stream_error(self) -> AcquisitionError:
        """Preserve the child diagnostic when its RX pipe closes early."""
        assert self._process is not None
        self._cancel_watchdog()
        try:
            returncode = self._process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            # EOF makes this stream unusable even if the child has not fully
            # exited. End the bounded RX child so its stderr collector can
            # finish and the actual transfer failure is not discarded.
            self._terminate()
            returncode = self._process.poll()
        stderr_text = ""
        if self._stderr is not None:
            self._stderr.join(timeout=1.0)
            stderr_text = bytes(self._stderr.data).decode("utf-8", errors="replace")
        diagnostic_lines = [line.strip() for line in stderr_text.splitlines() if line.strip()]
        diagnostic = diagnostic_lines[-1][:500] if diagnostic_lines else "HackRF tanı çıktısı yok."
        return AcquisitionError(
            "short_stream",
            "HackRF USB akışı erken kesildi: "
            f"{self._frames_received}/{self.frame_count} kare alındı, "
            f"süreç kodu {returncode}; son tanı: {diagnostic}",
        )

    def _finish(self) -> None:
        if self._finished:
            return
        assert self._process is not None and self._output is not None
        # Inspect EOF while the watchdog is active; waiting before draining the
        # pipe can deadlock a producer that emitted unexpected extra bytes.
        extra = self._output.read(1)
        if extra:
            raise AcquisitionError("long_stream", "HackRF canlı RX beklenenden uzun veri üretti.")
        try:
            returncode = self._process.wait(timeout=5.0)
        except subprocess.TimeoutExpired as exc:
            self._terminate()
            raise AcquisitionError("stream_finish_timeout", "HackRF canlı RX süreci kapanmadı.") from exc
        self._cancel_watchdog()
        assert self._stderr is not None
        self._stderr.join(timeout=1.0)
        if self._stderr.is_alive() or self._stderr.truncated:
            raise AcquisitionError("stream_diagnostics_invalid", "HackRF RX tanı çıktısı tamamlanamadı.")
        stderr_text = bytes(self._stderr.data).decode("utf-8", errors="replace")
        overruns, longest = parse_hackrf_buffer_statistics(stderr_text)
        if returncode != 0:
            raise AcquisitionError("capture_process_failed", "HackRF canlı RX süreci başarısız oldu.")
        self.statistics = HackRFStreamStatistics(
            frames_received=self._frames_received,
            bytes_received=self._bytes_received,
            elapsed_seconds=time.perf_counter() - self._started,
            overruns=overruns,
            longest_overrun_bytes=longest,
            process_returncode=returncode,
            stderr_text=stderr_text,
        )
        self._finished = True

    def _expire(self) -> None:
        self._timed_out = True
        self._terminate()

    def _cancel_watchdog(self) -> None:
        if self._watchdog is not None:
            self._watchdog.cancel()
            self._watchdog = None

    def _terminate(self) -> None:
        if self._process is None or self._process.poll() is not None:
            return
        self._process.terminate()
        try:
            self._process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait(timeout=1.0)

    def close(self) -> None:
        self._cancel_watchdog()
        self._terminate()
        if self._binary_pipe is not None:
            self._binary_pipe.close()
        if self._stderr is not None:
            self._stderr.join(timeout=1.0)
        if self._process is not None:
            if self._process.stdout is not None:
                self._process.stdout.close()
            if self._process.stderr is not None:
                self._process.stderr.close()
        _restore_host_process_cores(self._host_affinity_mask)
        self._host_affinity_mask = None

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        del exc_type, exc_value, traceback
        self.close()
