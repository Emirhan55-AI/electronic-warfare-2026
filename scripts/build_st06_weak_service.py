"""Cross-compile the current ARM service and record its exact source identity."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/p0/st06-weak-power-20260910"
P0 = "platforms/embedded/p0"
SOURCES = [f"{P0}/src/{name}.c" for name in (
    "p0_dma_runtime", "p0_parameter_runtime", "p0_amplitude_df", "p0_ed_pipeline",
    "p0_ed_service_protocol", "p0_ed_service", "p0_os_cfar", "p0_pl_os_cfar",
    "p0_multiscale_detector", "p0_candidate_packet", "p0_persistent_weak",
    "p0_st05_wideband", "p0_st05_stream",
)] + ["platforms/embedded/phase06j/src/phase06j_temporal.c"]
INCLUDES = [f"{P0}/include", "platforms/embedded/phase06i/include",
            "platforms/embedded/phase06j/include"]


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    prefix = ["wsl.exe"] if os.name == "nt" else []
    compiler = "arm-linux-gnueabihf-gcc"
    flags = ["-std=c11", "-O3", "-mcpu=cortex-a9", "-mfpu=neon", "-mfloat-abi=hard",
             "-Wall", "-Wextra", "-Werror", "-pedantic"]
    target = "build/p0/st06-weak-power-20260910/p0-ed-service"
    command = [*prefix, compiler, *flags, *(f"-I{path}" for path in INCLUDES),
               *SOURCES, "-lm", "-pthread", "-o", target]
    subprocess.run(command, cwd=ROOT, check=True)
    version = subprocess.run([*prefix, compiler, "-dumpfullversion"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
    files = SOURCES + [str(path.relative_to(ROOT)).replace("\\", "/")
                       for directory in INCLUDES for path in sorted((ROOT / directory).glob("*.h"))]
    result = {"status": "compiled", "hardware_executed": False,
              "compiler": f"{compiler} {version}", "flags": flags,
              "binary": {"path": target, "sha256": hashlib.sha256((ROOT / target).read_bytes()).hexdigest()},
              "sources": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in files}}
    (OUTPUT / "service-build.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    result = build()
    print(json.dumps({"status": result["status"], "binary": result["binary"]}, indent=2))
