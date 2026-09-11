import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st06-runtime-fft-feasibility-20260910.json"


def test_runtime_fft_feasibility_is_bounded_to_ooc_synthesis() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert evidence["schema"] == "phase08-st06-runtime-fft-feasibility-v1"
    assert evidence["status"] == "passed"
    assert evidence["profiles"]["runtime16384"]["supported_lengths"] == [4096, 8192, 16384]
    assert evidence["profiles"]["runtime16384"]["config_nfft_values"] == {
        "4096": 12,
        "8192": 13,
        "16384": 14,
    }
    assert all(evidence["checks"]["estimated_capacity"].values())
    assert evidence["conclusions"]["fft_ip_runtime_length_feasible"] is True
    assert evidence["conclusions"]["full_design_routed"] is False
    assert evidence["conclusions"]["hardware_verified"] is False
    assert evidence["conclusions"]["ui_may_claim_fpga_runtime_fft"] is False


def test_runtime_fft_resource_delta_matches_same_tool_ooc_reports() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert evidence["profiles"]["fixed4096"]["resources"] == {
        "slice_luts": 4005,
        "slice_registers": 7196,
        "bram_tiles": 14.5,
        "dsps": 30,
    }
    assert evidence["profiles"]["runtime16384"]["resources"] == {
        "slice_luts": 6641,
        "slice_registers": 9947,
        "bram_tiles": 49,
        "dsps": 38,
    }
    assert evidence["resource_delta"] == {
        "slice_luts": 2636,
        "slice_registers": 2751,
        "bram_tiles": 34.5,
        "dsps": 8,
    }
