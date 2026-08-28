from __future__ import annotations

import json

from scripts.verify_p0_os_cfar_pl_runtime import EVIDENCE, check


def test_pl_runtime_integration_evidence_is_current() -> None:
    assert check()
    document = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert document["status"] == "passed"
    assert document["decode_mismatches"] == 0
    assert document["combined_candidate_mismatches"] == 0
    assert document["malformed_frames_rejected"] == 3
    assert document["legacy_power_only_frame_compatibility"] == "passed"


def test_pipeline_selects_pl_path_only_after_format_decode() -> None:
    source = (
        EVIDENCE.parents[3] / "platforms/embedded/p0/src/p0_ed_pipeline.c"
    ).read_text(encoding="utf-8")
    decode_position = source.index("p0_pl_os_cfar_decode(")
    pl_position = source.index("p0_multiscale_process_pl(")
    legacy_position = source.index("p0_multiscale_process(")
    assert decode_position < pl_position
    assert decode_position < legacy_position
    assert "memcpy(pipeline->temporal_state, pipeline->temporal_backup" in source
