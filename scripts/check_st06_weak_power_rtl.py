"""Exercise current v2 RTL in an isolated directory, preserving frozen evidence."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algorithms.rtl.p0_os_cfar_vectors import build_vector_files
from algorithms.rtl.p0_os_cfar import detect_frame, WEAK_ALPHA_Q32


def check():
    compiler = shutil.which("iverilog") or "C:/msys64/ucrt64/bin/iverilog.exe"
    runtime = str(Path(compiler).with_name("vvp.exe" if os.name == "nt" else "vvp"))
    sources = ["algorithms/fpga/p0/rtl/p0_os_cfar_pkg.sv",
               "algorithms/fpga/p0/rtl/axis_p0_os_cfar.sv",
               "algorithms/fpga/p0/tb/tb_axis_p0_os_cfar.sv"]
    with tempfile.TemporaryDirectory(prefix="st06-weak-v2-") as raw:
        directory = Path(raw)
        fixtures = directory / "datasets/fixtures/p0_os_cfar"
        fixtures.mkdir(parents=True)
        files = build_vector_files()
        # Exact weak equality/floor boundary plus a persistent-path 5x stimulus.
        baseline = 1 << 30
        shifted = [baseline] * 4096
        shifted[1000] = (baseline * WEAK_ALPHA_Q32) >> 32
        shifted[2000] = shifted[1000] + 1
        shifted[3000] = 5 * baseline
        natural = [shifted[n ^ 2048] for n in range(4096)]
        reference = detect_frame(natural)
        assert not reference.weak_shifted[1000] and reference.weak_shifted[2000]
        assert reference.weak_shifted[3000] and not reference.detected_shifted[3000]
        files["axis-power-input.mem"] += "".join(
            f"{power | (n << 58) | (int(n == 4095) << 70):018x}\n"
            for n, power in enumerate(natural)).encode("ascii")
        files["dma-expected.mem"] += "".join(f"{word:016x}\n" for word in reference.dma_words_natural).encode("ascii")
        for name, payload in files.items():
            (fixtures / name).write_bytes(payload)
        executable = directory / "test.vvp"
        testbench = directory / "tb.sv"
        testbench.write_text((ROOT / sources[-1]).read_text().replace(
            "localparam int FRAME_COUNT = 11;", "localparam int FRAME_COUNT = 12;"))
        subprocess.run([compiler, "-g2012", "-s", "tb_axis_p0_os_cfar", "-o", str(executable),
                        *(str(ROOT / source) for source in sources[:-1]), str(testbench)], check=True, capture_output=True)
        result = subprocess.run([runtime, str(executable)], cwd=directory,
                                capture_output=True, text=True, check=True, timeout=180)
        assert "P0 OS-CFAR TB PASS: 49152 DMA words checked" in result.stdout, result.stdout
    return {"status": "passed", "scope": "RTL v2 / integer reference; no hardware or RF acceptance",
            "stdout": result.stdout,
            "sources": {source: hashlib.sha256((ROOT / source).read_bytes()).hexdigest() for source in sources + [
                "algorithms/rtl/p0_os_cfar.py", "algorithms/rtl/p0_os_cfar_vectors.py", "scripts/check_st06_weak_power_rtl.py"]},
            "vector_sha256": hashlib.sha256(files["dma-expected.mem"]).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
