"""ST-06 optimizasyon kanıt bütünlüğü; başarısız hız kapısını başarıya çevirmez."""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.operator_console.live_ed import decode_live_ed_response

EVIDENCE = ROOT / "results/evidence/phase08/st06-product-optimization-v1.json"


def load_report():
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    archive = ROOT / report["archive"]["path"]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == report["archive"]["sha256"]
    return report, archive


def verify_historical_sources(evidence):
    """Verify former source bytes as historical, never as current acceptance."""
    _, archive = load_report()
    with zipfile.ZipFile(archive) as z:
        for relative, expected in evidence["source_sha256"].items():
            current = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            if current != expected:
                candidates = [prefix + relative for prefix in ("previous-sources/", "current-sources/")
                              if prefix + relative in z.namelist()]
                assert any(hashlib.sha256(z.read(name)).hexdigest() == expected
                           for name in candidates), relative


def verify_historical_statistics(module_name, evidence):
    verify_historical_sources(evidence)
    module = importlib.import_module(module_name)
    recalculated = module.evaluate(str(evidence["generated_at_utc"]))
    # Recompute the old measurement statistics, keeping its original source binding.
    # No report is rewritten and no physical result is assigned to new code.
    assert {k: v for k, v in recalculated.items() if k != "source_sha256"} == {
        k: v for k, v in evidence.items() if k != "source_sha256"}


def verify(*, historical=False):
    report, archive = load_report()
    if historical:
        verify_historical_sources(report)
    else:
        for relative, expected in report["source_sha256"].items():
            assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
    for artifact in report["product_artifacts"].values():
        path = ROOT / artifact["path"]
        assert path.stat().st_size == artifact["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
    baseline = json.loads((ROOT / report["baseline_response_evidence"]).read_text(encoding="utf-8"))
    baseline_cases = baseline["runs"]["physical-independent-v2"]["cases"]
    speeds = []
    with zipfile.ZipFile(archive) as z:
        for i, run in enumerate(report["physical_runs"], 1):
            for case, summary in run["cases"].items():
                raw = z.read(f"physical-run-{i}/{case}.responses.bin")
                stimulus = z.read(f"physical-run-{i}/{case}.ci8")
                assert hashlib.sha256(raw).hexdigest() == summary["response_sha256"]
                assert hashlib.sha256(stimulus).hexdigest() == summary["input_sha256"]
                assert summary["response_sha256"] == baseline_cases[case]["response_sha256"]
                assert summary["input_sha256"] == baseline_cases[case]["input_sha256"]
                offset = 0
                frames = []
                while offset < len(raw):
                    size = int.from_bytes(raw[offset:offset + 4], "little")
                    assert 68 <= size <= 16384
                    offset += 4
                    frames.append(decode_live_ed_response(raw[offset:offset + size], len(frames)))
                    offset += size
                assert offset == len(raw)
                assert len(frames) == summary["received_frames"]
                assert len(stimulus) == len(frames) * 8192
                assert all(f.dma_status_flags == 7 and f.dropped_candidates == 0 for f in frames)
                assert not frames[-1].active
            speeds.append(run["cases"]["repeated_tone_throughput"]["measured_fps_after_64_warmup"])
        assert hashlib.sha256(z.read("package/p0-ed-service")).hexdigest() == report["build"]["rootfs_extracted_service_sha256"]
        assert "Attempted 5679 tasks" in z.read("package/package-build.txt").decode()
        assert "Successfully built p0-dma" in z.read("package/package-build.txt").decode()
        assert "Attempted 6090 tasks" in z.read("package/image-build.txt").decode()
        assert "Successfully built project" in z.read("package/image-build.txt").decode()
        stream = json.loads(z.read("diagnostic/stream-optimized-equivalence.json"))
        assert stream["status"] == "passed" and stream["stream_mismatches"] == 0
        if historical:
            verify_historical_sources(stream)
        else:
            for rel, expected in stream["source_sha256"].items():
                assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == expected
    assert speeds == report["throughput"]["fps"]
    assert report["throughput"]["minimum_fps"] == min(speeds)
    assert report["throughput"]["pass"] == (min(speeds) >= 2000000 / 4096)
    assert report["gates"]["product_throughput"] is False
    assert report["gates"]["ST06_complete"] is False
    assert report["build"]["SD_boot_files_changed"] is False
    return report


if __name__ == "__main__":
    result = verify()
    print(json.dumps({"evidence_integrity": "passed", "throughput": result["throughput"],
                      "ST06_complete": False}, ensure_ascii=False))
