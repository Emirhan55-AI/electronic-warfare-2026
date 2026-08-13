"""Safe PHASE-04 profile binding and selector ownership tests."""

from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reference.parameters.evaluation import canonical_json_bytes, phase04_implementation_manifest
from reference.pipeline import (
    RuntimePipeline,
    VerifiedProfileBinding,
    build_phase04_profile,
    canonical_profile_bytes,
    profile_from_document,
    profile_to_document,
)


METHODS = {
    "analysis_window": "analysis.clustered-regions-v1",
    "noise": "noise.winsorized-mean-10",
    "bandwidth": "band.multi-component-excess-99-v1",
    "spectral_center": "center.band-midpoint",
    "carrier": "carrier.centroid-only",
    "power_snr": "power.psd-noise-subtract-v1",
    "signal_domain": "domain.conservative-consensus",
}


def _binding() -> VerifiedProfileBinding:
    manifest = phase04_implementation_manifest()
    return VerifiedProfileBinding(
        comparison_id="phase04-r1-parameter-selection",
        comparison_sha256="a" * 64,
        implementation_manifest_sha256=str(manifest["implementation_manifest_sha256"]),
        catalog_sha256=str(manifest["catalog_sha256"]),
        phase03_profile_sha256=str(manifest["phase03_profile_sha256"]),
        selected_methods=tuple(METHODS.items()),
    )


def _selector_module():  # type: ignore[no-untyped-def]
    selector_path = Path(__file__).resolve().parents[1] / "scripts" / "select_phase04_profile.py"
    spec = importlib.util.spec_from_file_location("phase04_selector_under_test", selector_path)
    assert spec and spec.loader
    selector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selector)
    return selector


def _failed_payload() -> dict[str, object]:
    return {
        "schema_version": 2,
        "phase": "PHASE-04",
        "comparison_id": "phase04-r1-parameter-selection",
        "overall": "failed",
        "catalog_sha256": "b" * 64,
        "implementation_manifest_sha256": "c" * 64,
        "phase03_profile_sha256": "d" * 64,
        "selected_methods": None,
    }


class Phase04SelectorTests(unittest.TestCase):
    def test_profile_contains_bound_runtime_parameter_block(self) -> None:
        binding = _binding()
        profile = build_phase04_profile(METHODS, binding=binding)
        runtime = RuntimePipeline(profile, verified_binding=binding)
        self.assertIsNotNone(runtime.parameters)
        self.assertEqual(profile.parameter_block.parameters["feature_history_bytes"], 67840)  # type: ignore[union-attr]
        self.assertEqual(profile.detector_method, "regional")

    def test_profile_bytes_are_deterministic(self) -> None:
        binding = _binding()
        first = canonical_profile_bytes(build_phase04_profile(METHODS, binding=binding))
        second = canonical_profile_bytes(build_phase04_profile(METHODS, binding=binding))
        self.assertEqual(first, second)

    def test_broken_parameter_port_is_rejected(self) -> None:
        document = profile_to_document(build_phase04_profile(METHODS, binding=_binding()))
        connection = next(item for item in document["connections"] if item["target_block"] == "parameters" and item["target_port"] == "frame")
        connection["source_block"] = "spectrum"
        connection["source_port"] = "spectrum"
        document["connections"] = sorted(document["connections"], key=lambda item: (item["source_block"], item["source_port"], item["target_block"], item["target_port"]))
        with self.assertRaisesRegex(ValueError, "port data types"):
            profile_from_document(document)

    def test_validated_profile_requires_verified_binding(self) -> None:
        profile = build_phase04_profile(METHODS, binding=_binding())
        with self.assertRaisesRegex(ValueError, "verified comparison binding"):
            RuntimePipeline(profile)

    def test_evaluate_mode_does_not_read_or_write_established_files(self) -> None:
        selector = _selector_module()
        payload = _failed_payload()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            comparison = root / "comparison.json"
            profile = root / "profile.json"
            comparison.write_text("sentinel", encoding="utf-8")
            profile.write_text("sentinel", encoding="utf-8")
            with patch.object(selector, "COMPARISON_PATH", comparison), patch.object(selector, "PROFILE_PATH", profile), patch.object(selector, "evaluate_parameter_methods", return_value=(payload, None)):
                code, observed = selector.establish(full=False, evaluate=True)
            self.assertEqual(code, 1)
            self.assertIs(observed, payload)
            self.assertEqual(comparison.read_text(encoding="utf-8"), "sentinel")
            self.assertEqual(profile.read_text(encoding="utf-8"), "sentinel")

    def test_failed_reestablish_replaces_only_comparison_and_normal_write_is_noop(self) -> None:
        selector = _selector_module()
        payload = _failed_payload()
        expected = canonical_json_bytes(payload)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            comparison = root / "comparison.json"
            profile = root / "profile.json"
            comparison.write_text("old comparison", encoding="utf-8")
            profile.write_text("stale profile", encoding="utf-8")
            with patch.object(selector, "COMPARISON_PATH", comparison), patch.object(
                selector, "PROFILE_PATH", profile
            ), patch.object(selector, "evaluate_parameter_methods", return_value=(payload, None)):
                first_code, _ = selector.establish(full=False, reestablish=True)
                first_bytes = comparison.read_bytes()
                second_code, _ = selector.establish(full=False)
            self.assertEqual(first_code, 1)
            self.assertEqual(second_code, 1)
            self.assertEqual(first_bytes, expected)
            self.assertEqual(comparison.read_bytes(), expected)
            self.assertEqual(profile.read_text(encoding="utf-8"), "stale profile")

    def test_failed_normal_write_refuses_a_different_established_result(self) -> None:
        selector = _selector_module()
        payload = _failed_payload()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            comparison = root / "comparison.json"
            profile = root / "profile.json"
            comparison.write_text("established", encoding="utf-8")
            profile.write_text("profile", encoding="utf-8")
            with patch.object(selector, "COMPARISON_PATH", comparison), patch.object(
                selector, "PROFILE_PATH", profile
            ), patch.object(selector, "evaluate_parameter_methods", return_value=(payload, None)):
                code, _ = selector.establish(full=False)
            self.assertEqual(code, 2)
            self.assertEqual(comparison.read_text(encoding="utf-8"), "established")
            self.assertEqual(profile.read_text(encoding="utf-8"), "profile")


if __name__ == "__main__":
    unittest.main()
