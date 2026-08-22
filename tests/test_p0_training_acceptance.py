from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_p0_training_acceptance.py"
SPEC = importlib.util.spec_from_file_location("verify_p0_training_acceptance", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class P0TrainingAcceptanceTests(unittest.TestCase):
    def test_compact_evidence_is_current_and_all_host_gates_pass(self) -> None:
        document, _ = VERIFY.evaluate()
        self.assertEqual("PASS", document["status"])
        self.assertEqual("NOT EXECUTED", document["correctness_levels"]["physical_df"])
        self.assertEqual(VERIFY.canonical_bytes(document), VERIFY.EVIDENCE.read_bytes())

    def test_audio_and_df_use_independent_oracles(self) -> None:
        document, _ = VERIFY.evaluate()
        for key in ("am_audio", "nfm_audio"):
            row = document["results"][key]
            self.assertGreaterEqual(row["independent_oracle"]["normalized_correlation"], 0.95)
            self.assertEqual("PASS", row["status"])
        for row in document["results"]["df"]:
            self.assertEqual(row["independent_oracle"]["measured_argmax_deg"], row["actual_algorithm"]["estimated_bearing_deg"])
            self.assertEqual("PASS", row["status"])


if __name__ == "__main__":
    unittest.main()
