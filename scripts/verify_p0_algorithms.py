"""Evaluate mandatory P0 ED fixtures and emit measured, non-fabricated errors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.p0 import CandidateRegion, OSCFARDetector, ParameterExtractor, TemporalConfirmation
from reference.p0.fixtures import CENTER_FREQUENCY_HZ, FRAME_LENGTH, SAMPLE_RATE_HZ, build_fixtures
from reference.spectrum import SpectrumProcessor


FREQUENCY_TOLERANCES_HZ = {"wideband-noise-like": 1_000.0}
BANDWIDTH_TOLERANCES_HZ = {
    "single-tone": 300.0,
    "am-like": 1_000.0,
    "nfm-like": 1_250.0,
    "digital-ook-burst": 1_000.0,
    "wideband-noise-like": 500.0,
    "two-adjacent-signals": 300.0,
}


def _nearest(candidates: tuple[CandidateRegion, ...], frequency_hz: float) -> CandidateRegion | None:
    expected_bin = FRAME_LENGTH // 2 + round((frequency_hz - CENTER_FREQUENCY_HZ) / (SAMPLE_RATE_HZ / FRAME_LENGTH))
    plausible = [candidate for candidate in candidates if abs(candidate.peak_bin - expected_bin) <= 4]
    return min(plausible, key=lambda item: abs(item.peak_bin - expected_bin)) if plausible else None


def evaluate() -> dict[str, object]:
    detector = OSCFARDetector()
    extractor = ParameterExtractor()
    processor = SpectrumProcessor()
    scene_results: list[dict[str, object]] = []
    overall = True
    for scene_index, fixture in enumerate(build_fixtures()):
        spectrum = processor.process(fixture.iq, sample_rate_hz=SAMPLE_RATE_HZ, center_frequency_hz=CENTER_FREQUENCY_HZ)
        power = np.abs(np.fft.fftshift(np.fft.fft(fixture.iq * np.hanning(FRAME_LENGTH)))) ** 2
        detection = detector.process(power, frame_id=scene_index)
        tracker = TemporalConfirmation()
        tracker.update(detection.candidates, frame_id=0)
        tracks = tracker.update(detection.candidates, frame_id=1)
        confirmed_bins = {track.candidate.peak_bin for track in tracks if track.state == "confirmed"}
        measurements: list[dict[str, object]] = []
        target_detection_count = 0
        if fixture.parameter_mode == "known_region":
            start = FRAME_LENGTH // 2 + 300
            end = FRAME_LENGTH // 2 + 380
            region = power[start : end + 1]
            peak = start + int(np.argmax(region))
            candidate_list = [CandidateRegion(start, end, peak, float(power[peak]), float(np.median(power[:128])), float(np.median(power[:128]) * 7.5))]
        else:
            candidate_list = [_nearest(detection.candidates, frequency) for frequency in fixture.target_frequencies_hz]
        for truth_frequency, candidate in zip(fixture.target_frequencies_hz, candidate_list):
            if candidate is None:
                measurements.append({"ground_truth_frequency_hz": truth_frequency, "status": "not_detected"})
                continue
            target_detection_count += 1
            result = extractor.extract(
                frame_id=scene_index,
                iq=fixture.iq,
                shifted_power=power,
                sample_rate_hz=SAMPLE_RATE_HZ,
                center_frequency_hz=CENTER_FREQUENCY_HZ,
                candidate=candidate,
                confirmed=candidate.peak_bin in confirmed_bins or fixture.parameter_mode == "known_region",
                provenance="HOST REFERENCE",
                backend="p0.os_cfar+parameter.reference",
            )
            frequency_error = result.carrier_frequency_hz - truth_frequency
            bandwidth_error = None if fixture.expected_bandwidth_hz is None else result.bandwidth_hz - fixture.expected_bandwidth_hz
            frequency_tolerance = FREQUENCY_TOLERANCES_HZ.get(fixture.fixture_id, 300.0)
            passed = abs(frequency_error) <= frequency_tolerance
            if bandwidth_error is not None:
                passed = passed and abs(bandwidth_error) <= BANDWIDTH_TOLERANCES_HZ[fixture.fixture_id]
            if fixture.expected_domain is not None:
                passed = passed and result.signal_domain == fixture.expected_domain
            overall = overall and passed
            measurements.append({
                "ground_truth_frequency_hz": truth_frequency,
                "measured_frequency_hz": result.carrier_frequency_hz,
                "frequency_error_hz": frequency_error,
                "frequency_tolerance_hz": frequency_tolerance,
                "expected_bandwidth_hz": fixture.expected_bandwidth_hz,
                "measured_bandwidth_hz": result.bandwidth_hz,
                "bandwidth_error_hz": bandwidth_error,
                "bandwidth_tolerance_hz": BANDWIDTH_TOLERANCES_HZ.get(fixture.fixture_id),
                "relative_power_dbfs": result.relative_power_dbfs,
                "snr_db": result.snr_db,
                "expected_domain": fixture.expected_domain,
                "measured_domain": result.signal_domain,
                "classification_reasons": result.classification_reasons,
                "confirmed": result.confirmed,
                "calibration": result.calibration_state,
                "status": "passed" if passed else "failed",
            })
        expected_count = len(fixture.target_frequencies_hz)
        if fixture.fixture_id == "wideband-noise-like":
            expected_count = 1
        detected_ok = target_detection_count == expected_count
        overall = overall and detected_ok
        scene_results.append({
            "fixture": fixture.fixture_id,
            "target_detection_count": target_detection_count,
            "expected_target_count": expected_count,
            "measurements": measurements,
            "status": "passed" if detected_ok and all(item.get("status") == "passed" for item in measurements) else "failed",
        })
    return {
        "schema_version": 1,
        "checkpoint": "P0 Mandatory EH Core",
        "status": "passed" if overall else "failed",
        "profile_parameters": {
            "reference_cells_per_side": 16,
            "guard_cells_per_side": 4,
            "order_statistic_rank": 24,
            "threshold_coefficient": 7.5,
            "constants_source": "P0 test configuration; not a KTR constant",
        },
        "scenes": scene_results,
        "claim_boundary": "Deterministic synthetic host fixtures; not RF calibration, ARM, ZedBoard, or live HackRF evidence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.parse_args()
    result = evaluate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
