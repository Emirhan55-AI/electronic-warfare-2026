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


def test_weak_nomination_top_groups_sparse_candidates_with_backpressure(tmp_path: Path) -> None:
    iverilog = _tool("iverilog")
    vvp = _tool("vvp")
    if iverilog is None or vvp is None:
        pytest.skip("Icarus Verilog bulunamadı.")
    output = tmp_path / "weak_top.vvp"
    rtl = ROOT / "algorithms/fpga/p0/rtl"
    subprocess.run([
        iverilog, "-g2012", "-s", "tb_p0_weak_nomination_top", "-o", str(output),
        str(rtl / "p0_os_cfar_pkg.sv"),
        str(rtl / "p0_sparse_os_candidate_pkg.sv"),
        str(rtl / "p0_os_cfar_decision_engine.sv"),
        str(rtl / "p0_weak_candidate_grouping.sv"),
        str(rtl / "p0_weak_nomination_top.sv"),
        str(ROOT / "algorithms/fpga/p0/tb/tb_p0_weak_nomination_top.sv"),
    ], check=True, cwd=ROOT)
    completed = subprocess.run(
        [vvp, str(output)], check=True, cwd=ROOT, capture_output=True, text=True
    )
    assert "P0 WEAK NOMINATION TOP PASS" in completed.stdout
