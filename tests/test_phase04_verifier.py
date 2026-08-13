"""PHASE-04 deterministic evidence schema tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import scripts.render_phase04_ui as renderer
import scripts.verify_phase04 as verifier


ROOT = Path(__file__).resolve().parents[1]


class Phase04VerifierTests(unittest.TestCase):
    @staticmethod
    def _render_result(
        *, carrier_state: str = "valid", domain_state: str = "valid", domain_value: str = "Analog",
    ) -> SimpleNamespace:
        estimate = SimpleNamespace(
            frequency=SimpleNamespace(
                spectral_center_state="valid",
                observed_carrier_state=carrier_state,
                observed_carrier_frequency_hz=None if carrier_state == "not_observed" else 100_000_000.0,
            ),
            bandwidth=SimpleNamespace(
                lower_edge_state="valid",
                upper_edge_state="valid",
                bandwidth_state="valid",
            ),
            power=SimpleNamespace(relative_power_state="valid", snr_state="valid"),
            signal_domain=SimpleNamespace(state=domain_state, value=domain_value),
        )
        return SimpleNamespace(parameters=SimpleNamespace(events=(estimate,)))

    def test_evidence_files_are_deterministic_when_present(self) -> None:
        directory = ROOT / "results" / "evidence" / "phase04"
        for name in ("parameter-comparison.json", "golden-parameters.json", "verification-summary.json", "visual-summary.json"):
            path = directory / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            document = json.loads(text)
            self.assertNotIn("timestamp", text.casefold())
            self.assertNotIn("C:\\Users", text)
            self.assertEqual(document["phase"], "PHASE-04")

    def test_catalog_contains_fixed_success_gates(self) -> None:
        document = json.loads((ROOT / "datasets" / "fixtures" / "phase04" / "parameter-scenes.json").read_text(encoding="utf-8"))
        gates = document["success_gates"]
        self.assertEqual(gates["bandwidth_q95_relative_error_maximum"], 0.2)
        self.assertEqual(gates["classification_wrong_definite_total_maximum"], 0.02)
        self.assertEqual(gates["power_q95_error_db_maximum"], 1.5)

    def test_missing_or_corrupt_comparison_cannot_validate_a_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            profile = directory / "operation-default.json"
            comparison = directory / "parameter-comparison.json"
            with patch.object(verifier, "PROFILE", profile), patch.object(verifier, "COMPARISON", comparison):
                golden, summary, passed = verifier.build()
                self.assertFalse(passed)
                self.assertEqual("failed", golden["binding_status"])
                self.assertEqual("profile_not_established", golden["binding_error_code"])
                self.assertEqual("failed", summary["overall"])

                comparison.write_text("{bozuk", encoding="utf-8")
                golden, summary, passed = verifier.build()
                self.assertFalse(passed)
                self.assertEqual("comparison_unreadable", golden["binding_error_code"])
                self.assertEqual("failed", summary["overall"])

    def test_renderer_requires_real_named_pipeline_states(self) -> None:
        renderer._assert_scene_state(self._render_result(), "parameters-valid")
        renderer._assert_scene_state(
            self._render_result(carrier_state="not_observed"),
            "carrier-not-observed",
        )
        renderer._assert_scene_state(
            self._render_result(domain_state="uncertain", domain_value="Belirsiz"),
            "classification-uncertain",
        )
        with self.assertRaises(RuntimeError):
            renderer._assert_scene_state(self._render_result(), "carrier-not-observed")


if __name__ == "__main__":
    unittest.main()
