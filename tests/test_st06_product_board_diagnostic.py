"""Fiziksel tanı kaydının bütünlüğü; kart veya RF testi yerine geçmez."""
import hashlib
import json
from pathlib import Path
import zipfile

from app.operator_console.live_ed import decode_live_ed_response

ROOT = Path(__file__).resolve().parents[1]


def test_physical_diagnostic_preserves_raw_responses_and_failed_speed_gate():
    evidence = ROOT / "results/evidence/phase08/st06-product-board-diagnostic-v1.json"
    report = json.loads(evidence.read_text(encoding="utf-8"))
    archive = ROOT / report["archive"]["path"]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == report["archive"]["sha256"]
    current = json.loads((ROOT / "results/evidence/phase08/st06-parallel-product-v1.json").read_text(encoding="utf-8"))
    historical_sources = ROOT / current["archive"]["path"]
    assert hashlib.sha256(historical_sources.read_bytes()).hexdigest() == current["archive"]["sha256"]
    with zipfile.ZipFile(historical_sources) as sources:
        old_script = sources.read("previous-sources/scripts/diagnose_st06_product_board.py")
        assert hashlib.sha256(old_script).hexdigest() == report["diagnostic_script_sha256"]
    assert report["acceptance"]["product_throughput"] is False
    assert report["acceptance"]["st06_complete"] is False
    with zipfile.ZipFile(archive) as z:
        for run, data in report["runs"].items():
            for case, summary in data["cases"].items():
                stimulus = z.read(f"{run}/{case}.ci8")
                raw = z.read(f"{run}/{case}.responses.bin")
                assert hashlib.sha256(stimulus).hexdigest() == summary["input_sha256"]
                assert hashlib.sha256(raw).hexdigest() == summary["response_sha256"]
                frames = []
                offset = 0
                while offset < len(raw):
                    size = int.from_bytes(raw[offset:offset + 4], "little")
                    assert 68 <= size <= 16384
                    offset += 4
                    frames.append(decode_live_ed_response(raw[offset:offset + size], len(frames)))
                    offset += size
                assert offset == len(raw)
                assert len(stimulus) == len(frames) * 8192
                assert len(frames) == summary["received_frames"]
                assert sum(f.dropped_candidates for f in frames) == 0
                assert all(f.dma_status_flags == 7 for f in frames)
                assert not frames[-1].active
                confirmed = {e.event_id for f in frames[:summary["stimulus_frames"]]
                             for e in f.active if e.state == "confirmed"}
                assert len(confirmed) == summary["distinct_confirmed_events"]
                if case in {"zero", "independent_noise"}:
                    assert not confirmed
                if case == "repeated_tone_throughput":
                    assert summary["measured_fps_after_64_warmup"] < summary["required_fps"]
        for case in report["runs"]["physical-independent-v1"]["cases"]:
            assert z.read(f"physical-independent-v1/{case}.responses.bin") == z.read(
                f"physical-independent-v2/{case}.responses.bin")
