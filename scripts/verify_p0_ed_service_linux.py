#!/usr/bin/env python3
"""Exercise the exact local ED daemon/client path on a root Linux host."""

from __future__ import annotations

import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
P0 = ROOT / "platforms" / "embedded" / "p0"
P06I = ROOT / "platforms" / "embedded" / "phase06i"
P06J = ROOT / "platforms" / "embedded" / "phase06j"


def _compile(cc: str, output: Path, sources: list[Path], extra: list[str] | None = None) -> None:
    command = [
        cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
        f"-I{P0 / 'include'}", f"-I{P06I / 'include'}", f"-I{P06J / 'include'}",
        *(str(source) for source in sources), *(extra or []), "-o", str(output),
    ]
    build = subprocess.run(command, capture_output=True, text=True, check=False)
    if build.returncode:
        raise RuntimeError(f"build failed ({build.returncode}):\n{build.stdout}\n{build.stderr}")


def _run_as_nobody(command: list[str]) -> subprocess.CompletedProcess[str]:
    nobody = pwd.getpwnam("nobody")

    def demote() -> None:
        os.setgroups([])
        os.setgid(nobody.pw_gid)
        os.setuid(nobody.pw_uid)

    return subprocess.run(command, capture_output=True, text=True, check=False, preexec_fn=demote)


def verify() -> dict[str, object]:
    if os.name != "posix" or os.geteuid() != 0:
        raise RuntimeError("this acceptance requires a root Linux host")
    cc = shutil.which("cc") or shutil.which("gcc")
    if cc is None:
        raise FileNotFoundError("C11 compiler is unavailable")
    with tempfile.TemporaryDirectory(prefix="p0-ed-linux-") as raw:
        directory = Path(raw)
        directory.chmod(0o755)
        nobody = pwd.getpwnam("nobody")
        service = directory / "p0-ed-service"
        client = directory / "p0-ed-client"
        parameter_client = directory / "p0-parameter-client"
        runtime_directory = directory / "run"
        output_directory = directory / "out"
        runtime_directory.mkdir(mode=0o750)
        output_directory.mkdir(mode=0o700)
        os.chown(runtime_directory, nobody.pw_uid, nobody.pw_gid)
        os.chown(output_directory, nobody.pw_uid, nobody.pw_gid)
        socket_path = runtime_directory / "p0-ed.sock"
        _compile(
            cc, service,
            [
                ROOT / "tests/p0/p0_ed_fake_dma_runtime.c",
                P0 / "src/p0_parameter_runtime.c",
                P0 / "src/p0_ed_pipeline.c",
                P0 / "src/p0_ed_service_protocol.c",
                P0 / "src/p0_ed_service.c",
                P0 / "src/p0_os_cfar.c",
                P0 / "src/p0_candidate_packet.c",
                P06J / "src/phase06j_temporal.c",
            ],
            ['-DP0_ED_SERVICE_ACCOUNT="nobody"', '-DP0_ED_OPERATOR_GROUP="nogroup"', "-lm"],
        )
        _compile(
            cc, client,
            [P0 / "src/p0_ed_service_protocol.c", P0 / "src/p0_ed_client.c"],
        )
        _compile(
            cc, parameter_client,
            [P0 / "src/p0_ed_service_protocol.c", P0 / "src/p0_parameter_client.c"],
        )
        tone = directory / "tone.ci8"
        empty = directory / "empty.ci8"
        invalid_power = directory / "invalid-power.ci8"
        tone.write_bytes(bytes((index * 17 + 3) & 0xFF for index in range(8192)))
        empty.write_bytes(bytes(8192))
        invalid_power.write_bytes(bytes([0x7E]) + bytes(8191))
        tone.chmod(0o644)
        empty.chmod(0o644)
        invalid_power.chmod(0o644)
        process = subprocess.Popen(
            [str(service), "/dev/test-p0-dma", str(socket_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            deadline = time.monotonic() + 5.0
            while not socket_path.exists() and time.monotonic() < deadline:
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    raise RuntimeError(f"service exited early:\n{stdout}\n{stderr}")
                time.sleep(0.02)
            if not socket_path.exists():
                raise TimeoutError("service socket was not created")
            frames: list[dict[str, object]] = []
            for frame_id, source in enumerate((tone, tone, tone, empty, empty)):
                if frame_id == 1:
                    rejected_output = output_directory / "rejected-pipeline.json"
                    rejected = _run_as_nobody(
                        [str(client), "1", str(invalid_power), str(rejected_output), str(socket_path)]
                    )
                    if rejected.returncode == 0 or rejected_output.exists():
                        raise AssertionError("invalid FPGA power was accepted or published")
                output = output_directory / f"frame-{frame_id}.json"
                command = [str(client), str(frame_id), str(source), str(output)]
                if frame_id == 0:
                    command.append("--reset")
                command.append(str(socket_path))
                run = _run_as_nobody(command)
                if run.returncode:
                    raise RuntimeError(
                        f"unprivileged client frame {frame_id} failed:\n{run.stdout}\n{run.stderr}"
                    )
                frames.append(json.loads(output.read_text(encoding="utf-8")))
            malformed = _run_as_nobody(
                 [str(client), "5", str(directory / "missing.ci8"),
                 str(output_directory / "must-not-exist.json"), str(socket_path)]
            )
            if malformed.returncode == 0 or (output_directory / "must-not-exist.json").exists():
                raise AssertionError("invalid input was accepted or published")

            reset_output = output_directory / "parameter-reset.json"
            reset = _run_as_nobody(
                [str(client), "10", str(tone), str(reset_output), "--reset", str(socket_path)]
            )
            if reset.returncode:
                raise RuntimeError(f"parameter precondition reset failed:\n{reset.stdout}\n{reset.stderr}")
            parameter_results: list[dict[str, object]] = []
            for offset in range(4):
                output = output_directory / f"parameter-{offset}.json"
                command = [
                    str(parameter_client), str(11 + offset), str(tone), str(output),
                    "91", "1", "2000000", "2600000000", "2280", "2328",
                ]
                if offset == 0:
                    command.append("--start")
                command.append(str(socket_path))
                run = _run_as_nobody(command)
                if run.returncode:
                    raise RuntimeError(
                        f"parameter client frame {offset} failed:\n{run.stdout}\n{run.stderr}"
                    )
                parameter_results.append(json.loads(output.read_text(encoding="utf-8")))
        finally:
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=5.0)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate(timeout=2.0)
        if process.returncode != 0:
            raise RuntimeError(f"service shutdown failed ({process.returncode}):\n{stdout}\n{stderr}")
        counts = [
            (frame["active_count"], frame["ended_count"],
             (frame["active"] or frame["ended"])[0]["state"])
            for frame in frames
        ]
        expected = [
            (1, 0, "tentative"), (1, 0, "confirmed"), (1, 0, "confirmed"),
            (1, 0, "confirmed"), (0, 1, "ended"),
        ]
        if counts != expected:
            raise AssertionError(f"temporal service sequence mismatch: {counts}")
        observations = [item["parameter"]["observation_count"] for item in parameter_results]
        if observations != [1, 2, 3, 4]:
            raise AssertionError(f"parameter accumulation mismatch: {observations}")
        final_parameter = parameter_results[-1]["parameter"]
        for field in ("emission_center_frequency_hz", "channel_power_dbfs", "snr_estimate_db"):
            if final_parameter[field]["state"] != "valid":
                raise AssertionError(f"final parameter field did not become valid: {field}")
        if socket_path.exists():
            raise AssertionError("service socket remained after clean shutdown")
    return {
        "status": "passed",
        "compiler": Path(cc).name,
        "service_source": "production p0_ed_service.c",
        "client_identity": "nobody without supplementary groups",
        "frames": 5,
        "first_confirmation_frame": 1,
        "expiry_frame": 4,
        "invalid_input_published": False,
        "pipeline_failure_preserved_state": True,
        "clean_shutdown_removed_socket": True,
        "parameter_observations": [1, 2, 3, 4],
        "parameter_numeric_fields_valid": True,
    }


def main() -> int:
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
