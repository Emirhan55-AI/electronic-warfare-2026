from __future__ import annotations

import json
import hashlib
import unittest
from pathlib import Path

from reference.parameters.operator_evaluation import compare


ROOT = Path(__file__).resolve().parents[1]


class Phase04E1EvaluationTests(unittest.TestCase):
    def test_acceptance_contract_is_locked_before_results(self) -> None:
        document = json.loads((ROOT / "datasets/fixtures/phase04e1/acceptance-gates.json").read_text(encoding="utf-8"))
        self.assertEqual(document["status"], "locked-before-evaluation")
        self.assertFalse(document["authority"]["results_must_not_change_thresholds"] is False)
        self.assertEqual(document["pre_binding_invariants"]["maximum_persistent_payload_bytes"], 34_084)

    def test_compare_requires_binding_and_oos_for_each_field(self) -> None:
        fields = ["automatic_span", "emission_center_frequency", "carrier_line_frequency", "occupied_bandwidth", "uncalibrated_power_dbfs", "signal_domain"]
        binding = {"field_decisions": {name: {"status": "passed"} for name in fields}}
        oos = {"field_decisions": {name: {"status": "passed"} for name in fields}}
        oos["field_decisions"]["signal_domain"]["status"] = "failed"
        result = compare(binding, oos)
        self.assertNotIn("signal_domain", result["validated_fields"])
        self.assertIn("occupied_bandwidth", result["validated_fields"])

    def test_failed_automatic_span_does_not_close_manual_fields(self) -> None:
        fields = ["automatic_span", "emission_center_frequency", "carrier_line_frequency", "occupied_bandwidth", "uncalibrated_power_dbfs", "signal_domain"]
        binding = {"field_decisions": {name: {"status": "passed"} for name in fields}}
        oos = {"field_decisions": {name: {"status": "passed"} for name in fields}}
        binding["field_decisions"]["automatic_span"]["status"] = "failed"
        result = compare(binding, oos)
        self.assertFalse(result["automatic_span_validated"])
        self.assertEqual(fields[1:], result["validated_fields"])
        self.assertEqual("passed", result["status"])
        self.assertEqual("independent-fields-v2", result["protocol_revision"])

    def test_evidence_applies_every_locked_subgate(self) -> None:
        binding = json.loads(
            (ROOT / "results/evidence/phase04e1/binding-results.json").read_text(encoding="utf-8")
        )
        oos = json.loads((ROOT / "results/evidence/phase04e1/oos-results.json").read_text(encoding="utf-8"))
        acceptance = json.loads(
            (ROOT / "datasets/fixtures/phase04e1/acceptance-gates.json").read_text(encoding="utf-8")
        )
        current_lock_sha = hashlib.sha256(
            (ROOT / "datasets/fixtures/phase04e1/method-lock.json").read_bytes()
        ).hexdigest()
        if binding.get("method_lock_sha256") != current_lock_sha:
            self.skipTest("active evidence is the archived pre-v2 run; full evaluation has not executed")
        self.assertEqual(0.05, acceptance["binding"]["signal_domain"]["zero_snr_wrong_definite_maximum"])
        self.assertEqual(0.90, acceptance["binding"]["signal_domain"]["low_snr_abstention_minimum"])
        for document in (binding, oos):
            power = document["field_decisions"]["uncalibrated_power_dbfs"]
            self.assertIn("channel_power_q95_db", power)
            self.assertIn("peak_power_q95_db", power)
            bandwidth = document["field_decisions"]["occupied_bandwidth"]
            self.assertIn("lower_edge_q95_bins", bandwidth)
            self.assertIn("upper_edge_q95_bins", bandwidth)
            self.assertIn("clipping_count", bandwidth)
            self.assertIn("noise_domain_definite_count", document["diagnostics"])
            self.assertIn("stage_counters", document["diagnostics"])
            forced_noise = document["diagnostics"].get("forced_measurement_noise")
            if document.get("protocol_revision") == "independent-fields-v2" and document.get("schema_version") == 2:
                self.assertIsNotNone(forced_noise)
                self.assertEqual(document["diagnostics"]["noise_sequences"], forced_noise["trial_count"])
                self.assertEqual(4, forced_noise["frames_per_trial"])
                self.assertTrue(all(value == 0 for value in forced_noise["field_valid_counts"].values()))
                self.assertEqual(
                    document["diagnostics"]["clipping_count"],
                    document["diagnostics"]["stage_counters"]["occupied_bandwidth"]["reason_counts"].get("span_edge_clipping", 0),
                )
            for counters in document["diagnostics"]["stage_counters"].values():
                self.assertGreater(counters["field_math_reached"], 0)
                self.assertEqual(counters["total"], counters["operator_span_received"])
            self.assertTrue(
                all(
                    {"domain_correct_count", "domain_wrong_count"} <= set(item)
                    for item in document["family_results"]
                )
            )
        self.assertIn("temporal_edge_q95_bins", binding["field_decisions"]["occupied_bandwidth"])
        self.assertIn("false_carrier_count", oos["field_decisions"]["carrier_line_frequency"])


if __name__ == "__main__":
    unittest.main()
