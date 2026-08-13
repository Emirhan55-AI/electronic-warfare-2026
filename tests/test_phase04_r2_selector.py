"""PHASE-04-R2 method-lock, selector and runtime-binding tests."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reference.parameters.evaluation import _gate_applicability, canonical_json_bytes, phase04_implementation_manifest
from reference.parameters.r2 import build_method_lock
from reference.parameters.scenes import load_parameter_catalog
from reference.pipeline import RuntimePipeline, VerifiedProfileBinding, build_phase04_profile, canonical_profile_bytes
from reference.pipeline.profile import ProfileError, load_verified_phase04_profile


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "datasets" / "fixtures" / "phase04" / "r2-method-lock.json"


def _passed_comparison() -> dict[str, object]:
    catalog = load_parameter_catalog()
    manifest = phase04_implementation_manifest()
    selected = {
        "analysis_window": "analysis.clustered-regions-v1",
        "noise": "noise.trimmed-mean-20-hann-calibrated-v1",
        "bandwidth": "band.temporal-morphology-envelope-v1",
        "spectral_center": "center.excess-power-centroid",
        "carrier": "carrier.peak-gated",
        "power_snr": "power.psd-noise-subtract-v1",
        "signal_domain": "domain.explainable-rules",
    }
    center_records = [
        {
            "spectral_center_method": center,
            "carrier_method": carrier,
            "eligible": center == selected["spectral_center"] and carrier == selected["carrier"],
            "status": "passed" if center == selected["spectral_center"] and carrier == selected["carrier"] else "failed",
        }
        for center in catalog["method_order"]["spectral_center"]
        for carrier in catalog["method_order"]["carrier"]
    ]
    domain_records = [
        {
            "method": method,
            "eligible": method == selected["signal_domain"],
            "status": "passed" if method == selected["signal_domain"] else "failed",
        }
        for method in catalog["method_order"]["signal_domain"]
    ]
    return {
        "schema_version": 3,
        "phase": "PHASE-04-R2",
        "comparison_id": "phase04-r2-band-recovery",
        "overall": "passed",
        "catalog_sha256": manifest["catalog_sha256"],
        "implementation_manifest_sha256": manifest["implementation_manifest_sha256"],
        "phase03_profile_sha256": manifest["phase03_profile_sha256"],
        "method_lock_sha256": hashlib.sha256(LOCK.read_bytes()).hexdigest(),
        "selection_contract": catalog["selection_contract"],
        "gate_applicability": _gate_applicability(catalog),
        "sample_counts": {
            "trials_per_condition": 128,
            "continuous_frames_per_sequence": 4,
            "continuous_binding_frame": 3,
            "burst_frames_per_sequence": 6,
            "burst_binding_frame": 4,
            "noise_sequences": 128,
            "noise_frames_per_sequence": 32,
            "r2_locked_band_candidate_count": 1,
            "r2_phase03_unique_frames": 23_552,
            "r2_extractor_evaluations": 23_552,
            "streamed_not_bulk_cached": True,
        },
        "noise_bandwidth_pairs": [{
            "analysis_window_method": selected["analysis_window"],
            "noise_method": selected["noise"],
            "bandwidth_method": selected["bandwidth"],
            "eligible": True,
            "status": "passed",
        }],
        "noise_bandwidth_decision": {"status": "passed"},
        "center_carrier_pairs": center_records,
        "center_carrier_decision": {"status": "passed"},
        "power_snr_chain": {"method": selected["power_snr"], "status": "passed"},
        "signal_domain_methods": domain_records,
        "signal_domain_decision": {"status": "passed"},
        "selected_methods": selected,
        "combined_pipeline": {"status": "passed"},
    }


class Phase04R2SelectorTests(unittest.TestCase):
    def test_method_lock_is_canonical_and_reproducible(self) -> None:
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        rebuilt = build_method_lock(
            lock["noise_calibration"],
            lock["noise_end_to_end_validation"],
            lock["morphology_calibration"],
        )
        self.assertEqual(lock, rebuilt)
        self.assertEqual(LOCK.read_bytes(), canonical_json_bytes(lock))
        self.assertFalse(lock["nominal_ratios"]["exact_pfa_claimed"])

    def test_exact_r2_pair_loads_and_carries_bounded_history(self) -> None:
        comparison = _passed_comparison()
        data = canonical_json_bytes(comparison)
        selected = comparison["selected_methods"]
        assert isinstance(selected, dict)
        manifest = phase04_implementation_manifest()
        binding = VerifiedProfileBinding(
            "phase04-r2-band-recovery",
            hashlib.sha256(data).hexdigest(),
            str(manifest["implementation_manifest_sha256"]),
            str(manifest["catalog_sha256"]),
            str(manifest["phase03_profile_sha256"]),
            tuple((str(key), str(value)) for key, value in selected.items()),
            hashlib.sha256(LOCK.read_bytes()).hexdigest(),
        )
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            comparison_path = directory / "comparison.json"
            profile_path = directory / "profile.json"
            comparison_path.write_bytes(data)
            profile_path.write_bytes(canonical_profile_bytes(build_phase04_profile(selected, binding=binding)))
            profile, loaded = load_verified_phase04_profile(profile_path, comparison_path)
            runtime = RuntimePipeline(profile, verified_binding=loaded)
            assert runtime.parameters is not None
            self.assertEqual(67_840, runtime.parameters.history.payload_bytes)
            self.assertEqual(6_528, runtime.parameters.band_history.payload_bytes)
            self.assertEqual(
                74_368,
                runtime.parameters.history.payload_bytes + runtime.parameters.band_history.payload_bytes,
            )

    def test_method_lock_or_selected_downstream_drift_is_rejected(self) -> None:
        comparison = _passed_comparison()
        data = canonical_json_bytes(comparison)
        selected = comparison["selected_methods"]
        assert isinstance(selected, dict)
        manifest = phase04_implementation_manifest()
        binding = VerifiedProfileBinding(
            "phase04-r2-band-recovery",
            hashlib.sha256(data).hexdigest(),
            str(manifest["implementation_manifest_sha256"]),
            str(manifest["catalog_sha256"]),
            str(manifest["phase03_profile_sha256"]),
            tuple((str(key), str(value)) for key, value in selected.items()),
            hashlib.sha256(LOCK.read_bytes()).hexdigest(),
        )
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            comparison_path = directory / "comparison.json"
            profile_path = directory / "profile.json"
            profile_path.write_bytes(canonical_profile_bytes(build_phase04_profile(selected, binding=binding)))
            comparison_path.write_bytes(data)
            drifted_lock = directory / "lock.json"
            lock = json.loads(LOCK.read_text(encoding="utf-8"))
            lock["nominal_ratios"]["seed"] += 1.0
            drifted_lock.write_bytes(canonical_json_bytes(lock))
            with patch("reference.pipeline.profile.PHASE04_R2_METHOD_LOCK_PATH", drifted_lock):
                with self.assertRaisesRegex(ProfileError, "lock"):
                    load_verified_phase04_profile(profile_path, comparison_path)

            changed = json.loads(data.decode("utf-8"))
            chosen = next(item for item in changed["center_carrier_pairs"] if item["eligible"])
            chosen["eligible"] = False
            changed_data = canonical_json_bytes(changed)
            changed_binding = VerifiedProfileBinding(
                "phase04-r2-band-recovery",
                hashlib.sha256(changed_data).hexdigest(),
                str(manifest["implementation_manifest_sha256"]),
                str(manifest["catalog_sha256"]),
                str(manifest["phase03_profile_sha256"]),
                tuple((str(key), str(value)) for key, value in selected.items()),
                hashlib.sha256(LOCK.read_bytes()).hexdigest(),
            )
            comparison_path.write_bytes(changed_data)
            profile_path.write_bytes(canonical_profile_bytes(build_phase04_profile(selected, binding=changed_binding)))
            with self.assertRaisesRegex(ProfileError, "frequency"):
                load_verified_phase04_profile(profile_path, comparison_path)


if __name__ == "__main__":
    unittest.main()
