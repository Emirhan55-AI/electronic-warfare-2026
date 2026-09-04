from __future__ import annotations

import json
from pathlib import Path

import pytest

from algorithms.ps.candidate_transport import encode_packet
from scripts.verify_p0_physical_candidate_packet import (
    INPUT_SHA256,
    expected_reduction,
    expected_service_frames,
    verify,
    verify_service,
)


ROOT = Path(__file__).resolve().parents[2]
KNOWN_CAPTURE = ROOT / "datasets/fixtures/phase01/known-tone-ci8.sigmf-data"


def _known_frame(tmp_path: Path) -> Path:
    frame = tmp_path / "known-tone-frame0.ci8"
    frame.write_bytes(KNOWN_CAPTURE.read_bytes()[:8_192])
    return frame


def test_known_tone_reference_has_final_reducer_counts() -> None:
    reduction = expected_reduction()

    assert len(reduction.os_candidates) == 321
    assert len(reduction.recovery_candidates) == 19
    assert len(reduction.candidates) == 104
    assert sum(
        candidate.weak_evidence and not candidate.single_frame_confident
        for candidate in reduction.candidates
    ) == 54


def test_exact_physical_packet_is_accepted(tmp_path: Path) -> None:
    reduction = expected_reduction()
    packet = tmp_path / "candidate.packet"
    packet.write_bytes(encode_packet(37, reduction.candidates))

    result = verify(packet, _known_frame(tmp_path))

    assert result["status"] == "passed"
    assert result["input"]["sha256"] == INPUT_SHA256
    assert result["packet"]["frame_id"] == 37
    assert result["observed"]["final_candidates"] == 104
    assert result["observed"]["candidate_field_equivalence"] is True


def test_candidate_mismatch_fails_closed(tmp_path: Path) -> None:
    reduction = expected_reduction()
    packet = tmp_path / "candidate.packet"
    packet.write_bytes(encode_packet(0, reduction.candidates[:-1]))

    with pytest.raises(AssertionError):
        verify(packet, _known_frame(tmp_path))


def _service_results(tmp_path: Path, packet: Path) -> list[Path]:
    paths: list[Path] = []
    for index, frame in enumerate(expected_service_frames(packet)):
        path = tmp_path / f"service-frame{index}.json"
        path.write_text(
            json.dumps({**frame, "dma_status_flags": 7}),
            encoding="utf-8",
        )
        paths.append(path)
    return paths


def test_candidate_service_lifecycle_matches_temporal_oracle(tmp_path: Path) -> None:
    packet = tmp_path / "candidate.packet"
    packet.write_bytes(encode_packet(0, expected_reduction().candidates))

    result = verify_service(packet, _service_results(tmp_path, packet))

    assert result["status"] == "passed"
    assert result["event_field_equivalence"] is True
    assert [frame["active_count"] for frame in result["frames"]] == [50, 50, 50, 50, 0]
    assert [frame["ended_count"] for frame in result["frames"]] == [0, 0, 0, 0, 50]


def test_candidate_service_lifecycle_fails_on_event_mismatch(tmp_path: Path) -> None:
    packet = tmp_path / "candidate.packet"
    packet.write_bytes(encode_packet(0, expected_reduction().candidates))
    paths = _service_results(tmp_path, packet)
    document = json.loads(paths[1].read_text(encoding="utf-8"))
    document["active"][0]["peak_bin"] += 1
    paths[1].write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(AssertionError):
        verify_service(packet, paths)
