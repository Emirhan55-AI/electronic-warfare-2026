from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    candidate = Path("C:/msys64/ucrt64/bin") / f"{name}.exe"
    return str(candidate) if candidate.exists() else None


def test_weak_nomination_rtl_classifies_5x_and_10x_cells(tmp_path: Path) -> None:
    iverilog = _tool("iverilog")
    vvp = _tool("vvp")
    if iverilog is None or vvp is None:
        pytest.skip("Icarus Verilog bulunamadı.")
    output = tmp_path / "weak_nomination.vvp"
    subprocess.run([
        iverilog, "-g2012", "-s", "tb_p0_os_cfar_weak_nomination",
        "-o", str(output),
        str(ROOT / "algorithms/fpga/p0/rtl/p0_os_cfar_pkg.sv"),
        str(ROOT / "algorithms/fpga/p0/rtl/p0_os_cfar_decision_engine.sv"),
        str(ROOT / "algorithms/fpga/p0/tb/tb_p0_os_cfar_weak_nomination.sv"),
    ], check=True, cwd=ROOT)
    completed = subprocess.run(
        [vvp, str(output)], check=True, cwd=ROOT, capture_output=True, text=True
    )
    assert "P0 WEAK NOMINATION RTL PASS" in completed.stdout
