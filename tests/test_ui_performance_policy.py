from __future__ import annotations

import copy
import json
import unittest

from scripts.verify_ui_performance import EVIDENCE, check, evaluate


class UIPerformancePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_recorded_same_machine_characterization_passes(self) -> None:
        self.assertTrue(check())
        result = evaluate(self.document)
        self.assertEqual([27, 26, 29, 27, 26], result["baseline_counts"])
        self.assertEqual([20, 24, 25, 26, 29], result["candidate_counts"])
        self.assertFalse(result["material_regression"])

    def test_material_statistical_slowdown_fails(self) -> None:
        changed = copy.deepcopy(self.document)
        for run in changed["candidate"]["runs"]:
            run["thirty_fps"]["rendered_frames"] = 1
        self.assertEqual("failed", evaluate(changed)["status"])

    def test_queue_or_heartbeat_failure_remains_mandatory(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["candidate"]["runs"][0]["thirty_fps"]["maximum_pending_intents"] = 2
        with self.assertRaises(ValueError):
            evaluate(changed)


if __name__ == "__main__":
    unittest.main()
