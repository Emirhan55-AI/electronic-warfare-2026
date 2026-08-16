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

from reference.p0 import CandidateRegion, OSCFARDetector, P0_DETECTOR_PROFILE, ParameterExtractor, TemporalConfirmation
from reference.p0.fixtures import CENTER_FREQUENCY_HZ, FRAME_LENGTH, SAMPLE_RATE_HZ, build_fixtures
from reference.spectrum import SpectrumProcessor


EVIDENCE_PATH = ROOT / "results" / "evidence" / "p0" / "parameter-golden.json"
FREQUENCY_TOLERANCES_HZ = {"wideband-noise-like": 1_000.0}
BANDWIDTH_TOLERANCES_HZ = {
    "single-tone": 300.0,
    "am-like": 1_000.0,
    "nfm-like": 1_250.0,
    "digital-ook-burst": 1_000.0,
    "wideband-noise-like": 1_000.0,
    "digital-rectangular-spectrum": 750.0,
    "two-adjacent-signals": 300.0,
    "weak-near-threshold": 500.0,
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
            if fixture.known_region_bins is None:
                raise RuntimeError(f"{fixture.fixture_id} is missing a known-region contract")
            start, end = fixture.known_region_bins
            region = power[start : end + 1]
            peak = start + int(np.argmax(region))
            candidate_list = [CandidateRegion(start, end, peak, float(power[peak]), float(np.median(power[:128])), float(np.median(power[:128]) * P0_DETECTOR_PROFILE.threshold_coefficient))]
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
            bandwidth_absolute_error = None if bandwidth_error is None else abs(bandwidth_error)
            bandwidth_relative_error = None if bandwidth_error is None else bandwidth_absolute_error / fixture.expected_bandwidth_hz
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
                "bandwidth_absolute_error_hz": bandwidth_absolute_error,
                "bandwidth_relative_error": bandwidth_relative_error,
                "bandwidth_tolerance_hz": BANDWIDTH_TOLERANCES_HZ.get(fixture.fixture_id),
                "bandwidth_tolerance_bins": BANDWIDTH_TOLERANCES_HZ.get(fixture.fixture_id, 0.0) / (SAMPLE_RATE_HZ / FRAME_LENGTH),
                "bandwidth_method": result.bandwidth_method,
                "threshold_bandwidth_hz": result.threshold_bandwidth_hz,
                "occupied_bandwidth_hz": result.occupied_bandwidth_hz,
                "coarse_candidate_bandwidth_hz": result.coarse_candidate_bandwidth_hz,
                "relative_power_dbfs": result.relative_power_dbfs,
                "snr_db": result.snr_db,
                "expected_domain": fixture.expected_domain,
                "measured_domain": result.signal_domain,
                "classification_reasons": result.classification_reasons,
                "confirmed": result.confirmed,
                "calibration": result.calibration_state,
                "status": "passed" if passed else "failed",
                "failure_condition": None if passed else "not detected or bandwidth/parameter error exceeded the declared FFT-bin tolerance",
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
            "name": P0_DETECTOR_PROFILE.name,
            "method_source": "KTR method intent: local adaptive OS-CFAR",
            "engineering_profile_source": "P0 validated engineering configuration; not KTR constants",
            "reference_cells_per_side": P0_DETECTOR_PROFILE.reference_cells_per_side,
            "guard_cells_per_side": P0_DETECTOR_PROFILE.guard_cells_per_side,
            "order_statistic_rank": P0_DETECTOR_PROFILE.order_statistic_rank,
            "desired_pfa": P0_DETECTOR_PROFILE.desired_pfa,
            "threshold_coefficient": P0_DETECTOR_PROFILE.threshold_coefficient,
            "edge_policy": P0_DETECTOR_PROFILE.edge_policy,
            "comparison_rule": P0_DETECTOR_PROFILE.comparison_rule,
        },
        "scenes": scene_results,
        "claim_boundary": "Deterministic synthetic host fixtures; not RF calibration, ARM, ZedBoard, or live HackRF evidence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = evaluate()
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        EVIDENCE_PATH.write_bytes(serialized.encode("utf-8"))
    elif not EVIDENCE_PATH.is_file() or EVIDENCE_PATH.read_text(encoding="utf-8") != serialized:
        print("parameter evidence is missing or stale", file=sys.stderr)
        return 1
    print(serialized, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
