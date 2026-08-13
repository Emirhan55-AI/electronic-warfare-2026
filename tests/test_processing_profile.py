"""Validation and runtime tests for the PHASE-03 block profile."""

from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch

from reference.pipeline import (
    ProfileError,
    RuntimePipeline,
    VerifiedProfileBinding,
    build_operation_profile,
    build_phase04_profile,
    canonical_profile_bytes,
    load_profile,
    load_verified_phase04_profile,
    resolve_default_operation_profile,
)
from reference.pipeline.profile import profile_from_document, profile_to_document


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "profiles" / "phase03" / "operation-default.json"
BINDING = VerifiedProfileBinding(
    "phase04-r1-parameter-selection",
    "1" * 64,
    "2" * 64,
    "3" * 64,
    "4" * 64,
    (
        ("analysis_window", "analysis.clustered-regions-v1"),
        ("noise", "noise.winsorized-mean-10"),
        ("bandwidth", "band.multi-component-excess-99-v1"),
        ("spectral_center", "center.band-midpoint"),
        ("carrier", "carrier.centroid-only"),
        ("power_snr", "power.psd-noise-subtract-v1"),
        ("signal_domain", "domain.conservative-consensus"),
    ),
)


class ProcessingProfileTests(unittest.TestCase):
    @staticmethod
    def _bound_pair(
        directory: Path,
        *,
        overall: str = "passed",
        mutate: Callable[[dict[str, Any]], None] | None = None,
    ) -> tuple[Path, Path]:
        from reference.parameters.evaluation import (
            _gate_applicability,
            canonical_json_bytes,
            phase04_implementation_manifest,
        )
        from reference.parameters.extraction import ANALYSIS_METHODS, BANDWIDTH_METHODS
        from reference.parameters.scenes import load_parameter_catalog

        manifest = phase04_implementation_manifest()
        catalog = load_parameter_catalog()
        selected = dict(BINDING.selected_methods)
        status = "passed" if overall == "passed" else "failed"
        band_records = [
            {
                "analysis_window_method": analysis,
                "noise_method": noise,
                "bandwidth_method": bandwidth,
                "eligible": (
                    analysis == selected["analysis_window"]
                    and noise == selected["noise"]
                    and bandwidth == selected["bandwidth"]
                ),
                "status": (
                    "passed"
                    if analysis == selected["analysis_window"]
                    and noise == selected["noise"]
                    and bandwidth == selected["bandwidth"]
                    else "failed"
                ),
            }
            for analysis in ANALYSIS_METHODS
            for noise in catalog["method_order"]["noise"]
            for bandwidth in BANDWIDTH_METHODS
        ]
        center_records = [
            {
                "spectral_center_method": center,
                "carrier_method": carrier,
                "eligible": center == selected["spectral_center"] and carrier == selected["carrier"],
                "status": (
                    "passed"
                    if center == selected["spectral_center"] and carrier == selected["carrier"]
                    else "failed"
                ),
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
        comparison = {
            "schema_version": 2,
            "phase": "PHASE-04",
            "comparison_id": "phase04-r1-parameter-selection",
            "overall": overall,
            "catalog_sha256": manifest["catalog_sha256"],
            "implementation_manifest_sha256": manifest["implementation_manifest_sha256"],
            "phase03_profile_sha256": manifest["phase03_profile_sha256"],
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
                "streamed_not_bulk_cached": True,
            },
            "noise_bandwidth_pairs": band_records,
            "noise_bandwidth_decision": {"status": status},
            "center_carrier_pairs": center_records,
            "center_carrier_decision": {"status": status},
            "power_snr_chain": {"method": selected["power_snr"], "status": status},
            "signal_domain_methods": domain_records,
            "signal_domain_decision": {"status": status},
            "selected_methods": selected,
            "combined_pipeline": {"status": status},
        }
        if mutate is not None:
            mutate(comparison)
        comparison_bytes = canonical_json_bytes(comparison)
        binding = VerifiedProfileBinding(
            "phase04-r1-parameter-selection",
            hashlib.sha256(comparison_bytes).hexdigest(),
            str(manifest["implementation_manifest_sha256"]),
            str(manifest["catalog_sha256"]),
            str(manifest["phase03_profile_sha256"]),
            tuple(selected.items()),
        )
        profile_path = directory / "operation-default.json"
        comparison_path = directory / "parameter-comparison.json"
        profile_path.write_bytes(canonical_profile_bytes(build_phase04_profile(selected, binding=binding)))
        comparison_path.write_bytes(comparison_bytes)
        return profile_path, comparison_path

    def test_tracked_profile_is_canonical_validated_and_executable(self) -> None:
        profile = load_profile(PROFILE)
        self.assertEqual("validated", profile.lifecycle)
        self.assertEqual("regional", profile.detector_method)
        self.assertEqual(PROFILE.read_bytes(), canonical_profile_bytes(profile))
        self.assertEqual("regional", RuntimePipeline(profile).detector_method)

    def test_detector_type_in_profile_changes_runtime_detector(self) -> None:
        for method in ("regional", "ca_cfar", "os_cfar"):
            profile = build_operation_profile(method, lifecycle="experimental")
            runtime = RuntimePipeline(profile, allow_experimental=True)
            self.assertEqual(method, runtime.detector_method)

    def test_broken_connection_or_port_type_is_rejected(self) -> None:
        document = profile_to_document(build_operation_profile("regional"))
        document["connections"][0]["source_port"] = "unknown"
        with self.assertRaises(ProfileError):
            profile_from_document(document)

    def test_experimental_profile_cannot_be_operation_default(self) -> None:
        profile = build_operation_profile("regional", lifecycle="experimental")
        with self.assertRaisesRegex(ProfileError, "validated"):
            RuntimePipeline(profile)

    def test_profile_contains_no_absolute_path_or_dynamic_code(self) -> None:
        document = json.loads(PROFILE.read_text(encoding="utf-8"))
        text = json.dumps(document, ensure_ascii=False).casefold()
        self.assertNotIn("c:\\users", text)
        self.assertNotIn("python", text)
        self.assertNotIn("plugin", text)

    def test_phase04_parameter_block_is_allowlisted_and_bounded(self) -> None:
        profile = build_phase04_profile(
            {
                "analysis_window": "analysis.clustered-regions-v1",
                "noise": "noise.winsorized-mean-10",
                "bandwidth": "band.multi-component-excess-99-v1",
                "spectral_center": "center.band-midpoint",
                "carrier": "carrier.centroid-only",
                "power_snr": "power.psd-noise-subtract-v1",
                "signal_domain": "domain.conservative-consensus",
            },
            binding=BINDING,
        )
        with self.assertRaisesRegex(ProfileError, "binding"):
            RuntimePipeline(profile)
        runtime = RuntimePipeline(profile, verified_binding=BINDING)
        self.assertIsNotNone(runtime.parameters)
        self.assertEqual(runtime.parameters.history.payload_bytes, 67_840)  # type: ignore[union-attr]

    def test_phase04_runtime_rejects_wrong_comparison_binding(self) -> None:
        methods = {
            "analysis_window": "analysis.clustered-regions-v1",
            "noise": "noise.winsorized-mean-10",
            "bandwidth": "band.multi-component-excess-99-v1",
            "spectral_center": "center.band-midpoint",
            "carrier": "carrier.centroid-only",
            "power_snr": "power.psd-noise-subtract-v1",
            "signal_domain": "domain.conservative-consensus",
        }
        profile = build_phase04_profile(methods, binding=BINDING)
        wrong = VerifiedProfileBinding(
            "phase04-r1-parameter-selection",
            "5" * 64,
            "2" * 64,
            "3" * 64,
            "4" * 64,
            BINDING.selected_methods,
        )
        with self.assertRaisesRegex(ProfileError, "binding"):
            RuntimePipeline(profile, verified_binding=wrong)

    def test_verified_phase04_pair_rejects_missing_stale_and_failed_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            profile_path, comparison_path = self._bound_pair(directory)
            profile, binding = load_verified_phase04_profile(profile_path, comparison_path)
            self.assertIsNotNone(RuntimePipeline(profile, verified_binding=binding).parameters)

            original = comparison_path.read_bytes()
            comparison_path.unlink()
            with self.assertRaisesRegex(ProfileError, "comparison"):
                load_verified_phase04_profile(profile_path, comparison_path)
            comparison_path.write_bytes(original + b" ")
            with self.assertRaisesRegex(ProfileError, "digest"):
                load_verified_phase04_profile(profile_path, comparison_path)

            failed_profile, failed_comparison = self._bound_pair(directory, overall="failed")
            with self.assertRaisesRegex(ProfileError, "passed"):
                load_verified_phase04_profile(failed_profile, failed_comparison)

    def test_stale_phase04_default_falls_back_to_phase03_without_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            profile_path, comparison_path = self._bound_pair(directory)
            comparison_path.write_bytes(comparison_path.read_bytes() + b" ")
            with (
                patch("reference.pipeline.profile.PHASE04_PROFILE_PATH", profile_path),
                patch("reference.pipeline.profile.PHASE04_COMPARISON_PATH", comparison_path),
            ):
                resolved = resolve_default_operation_profile()
            self.assertIsNotNone(resolved.fallback_code)
            self.assertEqual("regional", resolved.profile.detector_method)
            self.assertIsNone(RuntimePipeline(resolved.profile).parameters)

    def test_verified_pair_rejects_gate_candidate_and_schedule_contract_drift(self) -> None:
        def invalidate_selected_band(document: dict[str, Any]) -> None:
            selected = document["selected_methods"]
            record = next(
                item
                for item in document["noise_bandwidth_pairs"]
                if item["analysis_window_method"] == selected["analysis_window"]
                and item["noise_method"] == selected["noise"]
                and item["bandwidth_method"] == selected["bandwidth"]
            )
            record["eligible"] = False
            record["status"] = "failed"

        mutations: tuple[tuple[str, Callable[[dict[str, Any]], None]], ...] = (
            (
                "gate",
                lambda document: document["gate_applicability"][0].__setitem__("value", -1),
            ),
            (
                "band-candidate",
                lambda document: document["noise_bandwidth_pairs"].pop(),
            ),
            (
                "center-candidate",
                lambda document: document["center_carrier_pairs"].pop(),
            ),
            (
                "domain-candidate",
                lambda document: document["signal_domain_methods"].pop(),
            ),
            ("selected-candidate", invalidate_selected_band),
            (
                "schedule",
                lambda document: document["sample_counts"].__setitem__("noise_sequences", 127),
            ),
        )
        for name, mutation in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                profile_path, comparison_path = self._bound_pair(Path(temporary), mutate=mutation)
                with self.assertRaises(ProfileError):
                    load_verified_phase04_profile(profile_path, comparison_path)


if __name__ == "__main__":
    unittest.main()
