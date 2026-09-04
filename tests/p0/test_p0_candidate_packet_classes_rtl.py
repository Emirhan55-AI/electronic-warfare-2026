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


def test_packetizer_marks_weak_and_single_frame_classes(tmp_path: Path) -> None:
    iverilog = _tool("iverilog")
    vvp = _tool("vvp")
    if iverilog is None or vvp is None:
        pytest.skip("Icarus Verilog bulunamadı.")
    output = tmp_path / "packet_classes.vvp"
    subprocess.run([
        iverilog, "-g2012", "-s", "tb_axis_candidate_packetizer_classes",
        "-o", str(output),
        str(ROOT / "algorithms/fpga/phase06i/rtl/phase06i_pkg.sv"),
        str(ROOT / "algorithms/fpga/phase06i/rtl/axis_candidate_packetizer.sv"),
        str(ROOT / "algorithms/fpga/phase06i/tb/tb_axis_candidate_packetizer_classes.sv"),
    ], check=True, cwd=ROOT)
    completed = subprocess.run(
        [vvp, str(output)], check=True, cwd=ROOT, capture_output=True, text=True
    )
    assert "P0 PACKET CLASS FLAGS PASS" in completed.stdout
