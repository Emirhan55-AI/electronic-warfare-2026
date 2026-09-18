from __future__ import annotations

from scripts.verify_phase09_amplitude_df_arm import EVIDENCE, verify


def test_portable_amplitude_df_matches_python_reference() -> None:
    result = verify()
    assert result["status"] == "passed"
    assert len(result["cases"]) == 8
    assert result["maximum_equivalence_error"] <= 1.0e-10
    assert result["duplicate_frame_gate"] == "passed"


def test_portable_amplitude_df_evidence_is_current() -> None:
    assert EVIDENCE.is_file()
