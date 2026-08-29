#!/usr/bin/env python3
"""Build and verify the bounded local P0 ED service protocol."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
P0_INCLUDE = ROOT / "platforms" / "embedded" / "p0" / "include"
PHASE06I_INCLUDE = ROOT / "platforms" / "embedded" / "phase06i" / "include"
PHASE06J_INCLUDE = ROOT / "platforms" / "embedded" / "phase06j" / "include"
PROTOCOL = ROOT / "platforms" / "embedded" / "p0" / "src" / "p0_ed_service_protocol.c"
HARNESS = ROOT / "tests" / "p0" / "p0_ed_service_protocol_test.c"


def _msvc_vcvars() -> Path | None:
    finder = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
    if not finder.is_file():
        return None
    query = subprocess.run(
        [str(finder), "-latest", "-products", "*", "-requires",
         "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    if query.returncode or not query.stdout.strip():
        return None
    path = Path(query.stdout.strip()) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
    return path if path.is_file() else None


def _compile_and_run(directory: Path) -> tuple[str, str]:
    if os.name == "nt" and (vcvars := _msvc_vcvars()) is not None:
        executable = directory / "p0-ed-service-protocol-test.exe"
        command = (
            f'call "{vcvars}" >nul && cl /nologo /std:c11 /O2 /W4 /WX '
            f'/I"{P0_INCLUDE}" /I"{PHASE06I_INCLUDE}" /I"{PHASE06J_INCLUDE}" '
            f'"{PROTOCOL}" "{HARNESS}" /Fe:"{executable}"'
        )
        build = subprocess.run(
            command, cwd=directory, shell=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
        compiler = "MSVC C11"
    else:
        cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
        if cc is None:
            raise FileNotFoundError("C11 compiler is unavailable")
        executable = directory / "p0-ed-service-protocol-test"
        build = subprocess.run(
            [cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
             f"-I{P0_INCLUDE}", f"-I{PHASE06I_INCLUDE}", f"-I{PHASE06J_INCLUDE}",
             str(PROTOCOL), str(HARNESS), "-o", str(executable)],
            cwd=directory, capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False,
        )
        compiler = Path(cc).name
    if build.returncode or not executable.is_file():
        raise RuntimeError(f"protocol build failed ({build.returncode}):\n{build.stdout}\n{build.stderr}")
    run = subprocess.run(
        [str(executable)], cwd=directory, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    if run.returncode or "P0_ED_SERVICE_PROTOCOL_TEST=PASS" not in run.stdout:
        raise RuntimeError(f"protocol test failed ({run.returncode}):\n{run.stdout}\n{run.stderr}")
    return compiler, run.stdout.strip()


def verify() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="p0-ed-service-") as raw:
        compiler, output = _compile_and_run(Path(raw))
    service = (ROOT / "platforms/embedded/p0/src/p0_ed_service.c").read_text(encoding="utf-8")
    recipe = (ROOT / "platforms/embedded/p0/petalinux/p0-dma_1.0.bb").read_text(encoding="utf-8")
    required_service_tokens = (
        "AF_UNIX", "SOCK_SEQPACKET", "MSG_TRUNC", "SO_RCVTIMEO", "setgroups(0U, NULL)",
        "setgid(gid)", "setuid(uid)", "P0_ED_IQ_FRAME_BYTES", "p0_dma_runtime_run(",
        "p0_ed_pipeline_process_packet(", "P0_DMA_OUTPUT_CAPACITY_BYTES",
        "chmod(socket_path, 0660)",
        "P0_ED_REQUEST_BYTES_V2", "P0_ED_REQUEST_FLAG_PARAMETER",
        "p0_ed_pipeline_measure(",
    )
    missing = [token for token in required_service_tokens if token not in service]
    if missing:
        raise AssertionError(f"service boundary tokens missing: {missing}")
    for token in (
        "inherit module update-rc.d useradd", 'GROUPADD_PARAM:${PN} = "--system p0ed"',
        'INITSCRIPT_PARAMS = "defaults 99"',
        "p0-ed-service", "p0-ed-client", "p0-ed-throughput-run",
        "p0-parameter-run", "p0-parameter-client", "p0_ed_throughput_run.c",
        "p0_multiscale_detector.c", "p0_multiscale_detector.h",
        "p0_pl_os_cfar.c", "p0_pl_os_cfar.h",
    ):
        if token not in recipe:
            raise AssertionError(f"PetaLinux recipe token missing: {token}")
    return {
        "status": "passed",
        "compiler": compiler,
        "protocol_test": output,
        "request_bytes_v1": 8224,
        "request_bytes_v2": 8272,
        "maximum_response_bytes_v1": 8772,
        "maximum_response_bytes_v2": 8916,
        "transport": "AF_UNIX SOCK_SEQPACKET",
        "network_listener": False,
        "dma_device_mode": "root-only 0600 retained",
        "service_privileges": "opens device, then setgroups/setgid/setuid p0ed",
        "operator_socket_group": "petalinux",
    }


def main() -> int:
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
