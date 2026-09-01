"""Deterministic vectors for the P0 wideband-recovery RTL."""

from __future__ import annotations

import hashlib

from .candidate_grouping import axis_candidate_records
from .p0_candidate_reducer import reduce_candidates
from .p0_os_cfar_vectors import canonical_bytes, p0_os_cfar_vectors


FRAME_LENGTH = 4096


def _natural_from_shifted(shifted: list[int]) -> tuple[int, ...]:
    return tuple(shifted[index ^ 0x800] for index in range(FRAME_LENGTH))


def _wideband_frame(
    spans: tuple[tuple[int, int, int], ...], peaks: tuple[tuple[int, int], ...]
) -> tuple[int, ...]:
    baseline = 1 << 30
    shifted = [baseline + ((index * 17) % 101) * 1000 for index in range(FRAME_LENGTH)]
    for start, stop, power in spans:
        for index in range(start, stop):
            shifted[index] = power
    for index, power in peaks:
        shifted[index] = power
    return _natural_from_shifted(shifted)


def _colored_step_frame() -> tuple[int, ...]:
    shifted = [1 << 30] * FRAME_LENGTH
    shifted[FRAME_LENGTH // 2 :] = [16 << 30] * (FRAME_LENGTH // 2)
    return _natural_from_shifted(shifted)


def selected_vectors() -> tuple[tuple[str, tuple[int, ...], str], ...]:
    by_id = {vector.vector_id: vector.natural_power for vector in p0_os_cfar_vectors()}
    return (
        ("all_zero", by_id["all_zero"], "deterministic empty frame"),
        ("multiple_tones", by_id["multiple_tones"], "deterministic narrowband tones"),
        (
            "real_phase06f_representative_hann",
            by_id["real_phase06f_representative_hann"],
            "frozen PHASE-06F AMD FFT linear-power output",
        ),
        (
            "single_wideband",
            _wideband_frame(((600, 700, 8 << 30),), ((650, 13 << 30),)),
            "deterministic regional wideband support",
        ),
        (
            "two_wideband",
            _wideband_frame(
                ((600, 700, 7 << 30), (1200, 1300, 9 << 30)),
                ((650, 13 << 30), (1250, 14 << 30)),
            ),
            "deterministic separated wideband supports",
        ),
        (
            "broad_512",
            _wideband_frame(((1792, 2304, 8 << 30),), ((2048, 13 << 30),)),
            "flanked 512-bin support that contaminates two regional medians",
        ),
        (
            "broad_2048",
            _wideband_frame(((1024, 3072, 8 << 30),), ((2048, 13 << 30),)),
            "flanked 2048-bin support that contaminates eight regional medians",
        ),
        (
            "colored_step_negative",
            _colored_step_frame(),
            "12 dB spectral step without two independent low-noise flanks",
        ),
    )


def _pack_input(natural: tuple[int, ...]) -> bytes:
    lines = []
    for natural_index, power in enumerate(natural):
        word = power | (natural_index << 58)
        word |= int(natural_index == FRAME_LENGTH - 1) << 70
        lines.append(f"{word:018x}\n".encode("ascii"))
    return b"".join(lines)


def _pack_expected(natural: tuple[int, ...]) -> tuple[bytes, dict[str, object]]:
    result = reduce_candidates(natural)
    axis = axis_candidate_records(result.recovery_candidates)
    lines = []
    for record in axis:
        candidate = record.candidate
        word = 0
        if candidate is not None:
            word |= candidate.peak_power
            word |= candidate.start_shifted_bin << 58
            word |= candidate.end_shifted_bin << 70
            word |= candidate.peak_shifted_bin << 82
            word |= candidate.coarse_span_bins << 94
            word |= candidate.regional_noise << 106
            word |= candidate.threshold << 164
            word |= candidate.pfa_select << 226
            word |= int(candidate.evaluate_center) << 228
        word |= int(record.candidate_valid) << 229
        word |= int(record.tlast) << 230
        lines.append(f"{word:058x}\n".encode("ascii"))
    return b"".join(lines), {
        "region_median_twice": list(result.region_median_twice),
        "integrated_detections": sum(result.integrated_detections),
        "regional_integrated_detections": sum(result.regional_integrated_detections),
        "broad_integrated_detections": sum(result.broad_integrated_detections),
        "frame_reference_twice": result.frame_reference_twice,
        "semantic_candidates": len(result.recovery_candidates),
        "axis_records": len(axis),
        "candidates": [
            {
                "start_shifted_bin": candidate.start_shifted_bin,
                "end_shifted_bin": candidate.end_shifted_bin,
                "peak_shifted_bin": candidate.peak_shifted_bin,
                "coarse_span_bins": candidate.coarse_span_bins,
                "peak_power": candidate.peak_power,
                "regional_noise": candidate.regional_noise,
                "threshold": candidate.threshold,
            }
            for candidate in result.recovery_candidates
        ],
    }


def build_vector_files() -> dict[str, bytes]:
    inputs = []
    expected = []
    counts = []
    rows = []
    for vector_id, natural, source in selected_vectors():
        inputs.append(_pack_input(natural))
        candidate_payload, summary = _pack_expected(natural)
        expected.append(candidate_payload)
        counts.append(f"{int(summary['axis_records']):02x}\n".encode("ascii"))
        rows.append({"vector_id": vector_id, "source": source, **summary})

    files = {
        "axis-power-input.mem": b"".join(inputs),
        "candidate-expected.mem": b"".join(expected),
        "expected-record-counts.mem": b"".join(counts),
        "golden-vectors.json": canonical_bytes(
            {
                "schema_version": 1,
                "status": "passed",
                "frame_length": FRAME_LENGTH,
                "frame_count": len(rows),
                "output_records": sum(int(row["axis_records"]) for row in rows),
                "semantic_candidates": sum(int(row["semantic_candidates"]) for row in rows),
                "vectors": rows,
            }
        ),
    }
    files["fixture-manifest.json"] = canonical_bytes(
        {
            "schema_version": 1,
            "status": "passed",
            "files": {
                name: {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
                for name, payload in files.items()
            },
        }
    )
    return files
