from __future__ import annotations

from pathlib import Path

import pytest

from algorithms.ps.candidate_transport import encode_packet
from scripts.verify_p0_physical_candidate_packet import (
    INPUT_SHA256,
    expected_reduction,
    verify,
)


ROOT = Path(__file__).resolve().parents[2]
KNOWN_CAPTURE = ROOT / "datasets/fixtures/phase01/known-tone-ci8.sigmf-data"


def _known_frame(tmp_path: Path) -> Path:
    frame = tmp_path / "known-tone-frame0.ci8"
    frame.write_bytes(KNOWN_CAPTURE.read_bytes()[:8_192])
    return frame


def test_known_tone_reference_has_final_reducer_counts() -> None:
    reduction = expected_reduction()

    assert len(reduction.os_candidates) == 147
    assert len(reduction.recovery_candidates) == 19
    assert len(reduction.candidates) == 54


def test_exact_physical_packet_is_accepted(tmp_path: Path) -> None:
    reduction = expected_reduction()
    packet = tmp_path / "candidate.packet"
    packet.write_bytes(encode_packet(37, reduction.candidates))

    result = verify(packet, _known_frame(tmp_path))

    assert result["status"] == "passed"
    assert result["input"]["sha256"] == INPUT_SHA256
    assert result["packet"]["frame_id"] == 37
    assert result["observed"]["final_candidates"] == 54
    assert result["observed"]["candidate_field_equivalence"] is True


def test_candidate_mismatch_fails_closed(tmp_path: Path) -> None:
    reduction = expected_reduction()
    packet = tmp_path / "candidate.packet"
    packet.write_bytes(encode_packet(0, reduction.candidates[:-1]))

    with pytest.raises(AssertionError):
        verify(packet, _known_frame(tmp_path))
