#!/usr/bin/env python3
"""Verify the hardware-independent PHASE-07 channelizer and wire protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.p0 import IQFrameCodec, LoopbackIQTransport, P0Channelizer


EVIDENCE_PATH = ROOT / "results/evidence/p0/phase07-host-loopback.json"
P0_INCLUDE = ROOT / "platforms/embedded/p0/include"
C_PROTOCOL = ROOT / "platforms/embedded/p0/src/p0_iq_transport.c"
C_HARNESS = ROOT / "tests/p0/p0_iq_transport_test.c"
BRIDGE_SOURCE = ROOT / "platforms/embedded/p0/src/p0_ed_network_bridge.c"
SERVICE_PROTOCOL = ROOT / "platforms/embedded/p0/src/p0_ed_service_protocol.c"
PHASE06I_INCLUDE = ROOT / "platforms/embedded/phase06i/include"
PHASE06J_INCLUDE = ROOT / "platforms/embedded/phase06j/include"
BRIDGE_HARNESS = ROOT / "tests/p0/p0_iq_bridge_loopback_test.py"
PETALINUX_RECIPE = ROOT / "platforms/embedded/p0/petalinux/p0-dma_1.0.bb"
BRIDGE_INIT = ROOT / "platforms/embedded/p0/petalinux/p0-ed-network-bridge.init"
BRIDGE_DEFAULT = ROOT / "platforms/embedded/p0/petalinux/p0-ed-network-bridge.default"
MEASURED_FRAMES = 1024
WARMUP_FRAMES = 64
REPEAT_RUNS = 3
REQUIRED_FRAMES_PER_SECOND = 2_000_000 / 4096


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _msvc_vcvars() -> Path | None:
    finder = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
    if not finder.is_file():
        return None
    query = subprocess.run(
        [
            str(finder),
            "-latest",
            "-products",
            "*",
            "-requires",
            "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property",
            "installationPath",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if query.returncode != 0 or not query.stdout.strip():
        return None
    candidate = Path(query.stdout.strip()) / "VC/Auxiliary/Build/vcvars64.bat"
    return candidate if candidate.is_file() else None


def _compile_c_protocol(directory: Path) -> tuple[str, str]:
    if os.name == "nt" and (vcvars := _msvc_vcvars()) is not None:
        executable = directory / "p0-iq-transport-test.exe"
        command = (
            f'call "{vcvars}" >nul && cl /nologo /std:c11 /O2 /W4 /WX '
            f'/I"{P0_INCLUDE}" "{C_PROTOCOL}" "{C_HARNESS}" /Fe:"{executable}"'
        )
        build = subprocess.run(
            command,
            cwd=directory,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        compiler = "MSVC C11"
    else:
        cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
        if cc is None:
            raise FileNotFoundError("C11 derleyicisi bulunamadı.")
        executable = directory / "p0-iq-transport-test"
        build = subprocess.run(
            [
                cc,
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                f"-I{P0_INCLUDE}",
                str(C_PROTOCOL),
                str(C_HARNESS),
                "-o",
                str(executable),
            ],
            cwd=directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        compiler = Path(cc).name
    if build.returncode != 0 or not executable.is_file():
        raise RuntimeError(f"C11 transport derlemesi başarısız:\n{build.stdout}\n{build.stderr}")
    run = subprocess.run(
        [str(executable)],
        cwd=directory,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if run.returncode != 0 or "P0_IQ_TRANSPORT_TEST=PASS" not in run.stdout:
        raise RuntimeError(f"C11 transport testi başarısız:\n{run.stdout}\n{run.stderr}")
    return compiler, run.stdout.strip()


def _wsl_path(path: Path) -> str:
    resolved = path.resolve().as_posix()
    if len(resolved) < 3 or resolved[1:3] != ":/":
        raise ValueError(f"Windows yolu WSL biçimine çevrilemedi: {resolved}")
    return f"/mnt/{resolved[0].lower()}/{resolved[3:]}"


def _compile_and_run_bridge(directory: Path) -> tuple[str, str]:
    sources = (C_PROTOCOL, SERVICE_PROTOCOL, BRIDGE_SOURCE)
    includes = (P0_INCLUDE, PHASE06I_INCLUDE, PHASE06J_INCLUDE)
    if os.name == "nt":
        wsl = shutil.which("wsl.exe")
        if wsl is None:
            raise FileNotFoundError("Linux ağ köprüsü testi için WSL bulunamadı.")
        executable = f"/tmp/p0-ed-network-bridge-{os.getpid()}"
        port = 47000 + os.getpid() % 1000
        compile_parts = [
            "cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
            '-DP0_NETWORK_SERVICE_ACCOUNT="root"',
            "-DP0_IQ_USE_SERVICE_CRC32",
            *(f"-I{_wsl_path(path)}" for path in includes),
            *(_wsl_path(path) for path in sources),
            "-lm", "-o", executable,
        ]
        run_parts = ["python3", _wsl_path(BRIDGE_HARNESS), executable, str(port)]
        command = " ".join(shlex.quote(item) for item in compile_parts)
        command += " && " + " ".join(shlex.quote(item) for item in run_parts)
        command += f"; status=$?; rm -f {shlex.quote(executable)}; exit $status"
        run = subprocess.run(
            [wsl, "sh", "-lc", command],
            cwd=directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        compiler = "GCC C11 / WSL2 Linux"
    else:
        cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
        if cc is None:
            raise FileNotFoundError("Linux C11 derleyicisi bulunamadı.")
        executable_path = directory / "p0-ed-network-bridge"
        build = subprocess.run(
            [
                cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                f'-DP0_NETWORK_SERVICE_ACCOUNT="{os.environ.get("USER", "root")}"',
                "-DP0_IQ_USE_SERVICE_CRC32",
                *(f"-I{path}" for path in includes),
                *(str(path) for path in sources),
                "-lm", "-o", str(executable_path),
            ],
            cwd=directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if build.returncode != 0:
            raise RuntimeError(f"Linux ağ köprüsü derlenemedi:\n{build.stdout}\n{build.stderr}")
        port = 47000 + os.getpid() % 1000
        run = subprocess.run(
            [sys.executable, str(BRIDGE_HARNESS), str(executable_path), str(port)],
            cwd=directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        compiler = Path(cc).name
    if run.returncode != 0 or "P0_IQ_BRIDGE_LOOPBACK_TEST=PASS" not in run.stdout:
        raise RuntimeError(f"Linux ağ köprüsü loopback testi başarısız:\n{run.stdout}\n{run.stderr}")
    return compiler, run.stdout.strip()


def _filter_metrics(channelizer: P0Channelizer) -> dict[str, float]:
    response = np.abs(np.fft.rfft(channelizer.taps, 262_144))
    frequency = np.fft.rfftfreq(262_144, 1.0 / 8_000_000)
    passband = response[frequency <= 800_000]
    stopband = response[frequency >= 1_000_000]
    return {
        "passband_ripple_db": float(20.0 * np.log10(np.max(passband) / np.min(passband))),
        "stopband_peak_db": float(20.0 * np.log10(np.max(stopband))),
    }


def _run_once(samples: np.ndarray) -> dict[str, object]:
    channelizer = P0Channelizer()
    transport = LoopbackIQTransport(queue_capacity=4)
    transport.connect()
    saturated_components = 0
    for frame_id in range(WARMUP_FRAMES):
        result = channelizer.process(
            samples,
            sequence_number=frame_id,
            frame_id=frame_id,
            input_sample_rate_hz=8_000_000,
            input_center_frequency_hz=100_000_000,
            output_center_frequency_hz=101_500_000,
        )
        IQFrameCodec.validate_processing_frame(result.frame)
        if not transport.send(result.frame) or transport.receive() is None:
            raise RuntimeError("Loopback ısınma çerçevesi kabul edilmedi.")

    started = time.perf_counter()
    for index in range(MEASURED_FRAMES):
        frame_id = WARMUP_FRAMES + index
        result = channelizer.process(
            samples,
            sequence_number=frame_id,
            frame_id=frame_id,
            input_sample_rate_hz=8_000_000,
            input_center_frequency_hz=100_000_000,
            output_center_frequency_hz=101_500_000,
        )
        IQFrameCodec.validate_processing_frame(result.frame)
        saturated_components += result.saturated_components
        if not transport.send(result.frame):
            raise RuntimeError("Bounded loopback kuyruğu ölçüm sırasında çerçeve düşürdü.")
        received = transport.receive()
        if received != result.frame:
            raise RuntimeError("Loopback çerçevesi byte-tam eşleşmedi.")
    elapsed = time.perf_counter() - started
    frames_per_second = MEASURED_FRAMES / elapsed
    stats = transport.stats
    return {
        "measured_frames": MEASURED_FRAMES,
        "elapsed_seconds": elapsed,
        "frames_per_second": frames_per_second,
        "real_time_margin": frames_per_second / REQUIRED_FRAMES_PER_SECOND,
        "frames_sent": stats.frames_sent - WARMUP_FRAMES,
        "frames_received": stats.frames_received - WARMUP_FRAMES,
        "sequence_errors": stats.sequence_errors,
        "queue_drops": stats.queue_drops,
        "saturated_components": saturated_components,
    }


def evaluate() -> dict[str, object]:
    rng = np.random.default_rng(0x5007)
    sample_index = np.arange(16_384, dtype=np.float64)
    desired = 0.25 * np.exp(2j * np.pi * 1_700_000 * sample_index / 8_000_000)
    noise = 0.015 * (
        rng.standard_normal(sample_index.size) + 1j * rng.standard_normal(sample_index.size)
    )
    samples = np.asarray(desired + noise, dtype=np.complex128)
    channelizer = P0Channelizer()
    metrics = _filter_metrics(channelizer)
    runs = [_run_once(samples) for _ in range(REPEAT_RUNS)]
    with tempfile.TemporaryDirectory(prefix="p0-iq-transport-") as raw:
        directory = Path(raw)
        compiler, c_result = _compile_c_protocol(directory)
        bridge_compiler, bridge_result = _compile_and_run_bridge(directory)
    recipe = PETALINUX_RECIPE.read_text(encoding="utf-8")
    init_script = BRIDGE_INIT.read_text(encoding="utf-8")
    default_config = BRIDGE_DEFAULT.read_text(encoding="utf-8")
    packaging_tokens = (
        "p0_iq_transport.c",
        "p0_ed_network_bridge.c",
        "p0-ed-network-bridge.init",
        "p0-ed-network-bridge.default",
        "${sbindir}/p0-ed-network-bridge",
    )
    if any(token not in recipe for token in packaging_tokens):
        raise AssertionError("PetaLinux ağ köprüsü paket bağı eksik.")
    if 'P0_ED_NETWORK_ENABLED=0' not in default_config:
        raise AssertionError("Ağ köprüsü fiziksel kabul öncesinde varsayılan kapalı olmalıdır.")
    for token in ("ip address replace", "P0_ED_NETWORK_PEER_IP", "start-stop-daemon"):
        if token not in init_script:
            raise AssertionError(f"Ağ köprüsü init sınırı eksik: {token}")

    passed = (
        metrics["passband_ripple_db"] <= 0.01
        and metrics["stopband_peak_db"] <= -65.0
        and all(
            run["frames_per_second"] >= REQUIRED_FRAMES_PER_SECOND
            and run["frames_sent"] == MEASURED_FRAMES
            and run["frames_received"] == MEASURED_FRAMES
            and run["sequence_errors"] == 0
            and run["queue_drops"] == 0
            and run["saturated_components"] == 0
            for run in runs
        )
    )
    sources = (
        ROOT / "algorithms/p0/channelizer.py",
        ROOT / "algorithms/p0/transport.py",
        ROOT / "platforms/embedded/p0/include/p0_iq_transport.h",
        C_PROTOCOL,
        C_HARNESS,
        BRIDGE_SOURCE,
        BRIDGE_HARNESS,
        PETALINUX_RECIPE,
        BRIDGE_INIT,
        BRIDGE_DEFAULT,
        ROOT / "tests/test_p0_channelizer.py",
        ROOT / "tests/test_p0_transport.py",
    )
    return {
        "schema_version": 1,
        "status": "passed" if passed else "failed",
        "scope": "PHASE-07 donanımdan bağımsız kanal seçici ve Ethernet paket sözleşmesi",
        "profile": {
            "input_sample_rate_hz": 8_000_000,
            "input_complex_samples": 16_384,
            "output_sample_rate_hz": 2_000_000,
            "output_complex_samples": 4_096,
            "output_payload_bytes": 8_192,
            "tuning_offset_hz": 1_500_000,
            "passband_edge_hz": 800_000,
            "stopband_edge_hz": 1_000_000,
            "fir_taps": 193,
            "transport_version": 2,
            "transport_header_bytes": 48,
        },
        "filter_acceptance": metrics,
        "throughput_acceptance": {
            "warmup_frames": WARMUP_FRAMES,
            "measured_frames_per_run": MEASURED_FRAMES,
            "repeat_runs": REPEAT_RUNS,
            "required_frames_per_second": REQUIRED_FRAMES_PER_SECOND,
            "minimum_frames_per_second": min(float(run["frames_per_second"]) for run in runs),
            "minimum_real_time_margin": min(float(run["real_time_margin"]) for run in runs),
            "runs": runs,
        },
        "portable_decoder": {"compiler": compiler, "result": c_result},
        "network_bridge_loopback": {
            "compiler": bridge_compiler,
            "result": bridge_result,
            "pipeline_depth": 4,
            "tcp_listener": "IPv4 exact bind and peer allowlist",
            "local_boundary": "AF_UNIX SOCK_SEQPACKET",
        },
        "petalinux_packaging": {
            "sources_declared": True,
            "binary_and_configuration_installed": True,
            "default_enabled": False,
            "target_build_exercised": False,
        },
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in sources
        },
        "physical_ethernet_exercised": False,
        "zedboard_network_service_exercised": False,
        "hackrf_continuous_stream_exercised": False,
        "claim_boundary": (
            "Bu kanıt 8→2 MS/s kanal seçme, anti-alias süzme, CI8/4096 çerçeveleme, "
            "başlık ve payload CRC, sıra ve bounded loopback hızını doğrular. Fiziksel Ethernet, "
            "ZedBoard ağ hizmeti, kesintisiz HackRF akışı veya canlı FPGA sonucu değildir."
        ),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = evaluate()
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE_PATH.write_bytes(serialized.encode("utf-8"))
    elif not EVIDENCE_PATH.is_file():
        print("PHASE-07 host loopback kanıtı bulunamadı.")
        return 1
    print(serialized, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
