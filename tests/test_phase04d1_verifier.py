"""Read-only ownership tests for the PHASE-04-D1F verifier."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts.run_phase04d1_evaluation import FILES


ROOT = Path(__file__).resolve().parents[1]


class Phase04D1VerifierTests(unittest.TestCase):
    def test_verifier_is_check_only_and_evidence_ownership_is_exact(self) -> None:
        source = (ROOT / "scripts/verify_phase04d1.py").read_text(encoding="utf-8")
        self.assertNotIn("--write", source)
        self.assertEqual(
            {path.name for path in FILES.values()},
            {
                "obw99-comparison.json",
                "obw99-binding-results.json",
                "obw99-oos-results.json",
                "golden-obw99.json",
                "verification-summary.json",
            },
        )


if __name__ == "__main__":
    unittest.main()
