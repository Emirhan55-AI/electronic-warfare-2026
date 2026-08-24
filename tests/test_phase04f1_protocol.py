from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from scripts.reveal_phase04f1_seeds import verify_reveal
from scripts.verify_phase04f1_protocol import FIXTURES, build_summary


ROOT = Path(__file__).resolve().parents[1]


class Phase04F1ProtocolTests(unittest.TestCase):
    def test_protocol_is_locked_before_method_development(self) -> None:
        reveal_path = FIXTURES / "evaluation-seeds.json"
        if reveal_path.is_file():
            historical = json.loads(
                (ROOT / "results" / "evidence" / "phase04f1" / "f1b-verification.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual("passed", historical["status"])
            self.assertFalse(historical["binding_seed_revealed"])
            self.assertFalse(historical["oos_seed_revealed"])
            self.assertTrue(verify_reveal(json.loads(reveal_path.read_text(encoding="utf-8"))))
        else:
            summary = build_summary()
            self.assertEqual("passed", summary["status"])
            self.assertFalse(summary["binding_seed_revealed"])
            self.assertFalse(summary["oos_seed_revealed"])
            self.assertFalse(summary["method_implementation_locked"])

    def test_local_sealed_preimages_match_public_commitments_when_available(self) -> None:
        sealed_path = ROOT / "build" / "phase04f1" / "sealed-seeds.json"
        if not sealed_path.is_file():
            self.skipTest("local sealed seed preimages are intentionally not repository-owned")
        sealed = json.loads(sealed_path.read_text(encoding="utf-8"))
        commitments = json.loads((FIXTURES / "evaluation-commitments.json").read_text(encoding="utf-8"))
        expected = {item["role"]: item["seed_commitment_sha256"] for item in commitments["populations"]}
        for item in sealed["seeds"]:
            payload = json.dumps(
                {"role": item["role"], "salt": item["salt"], "seed": item["seed"]},
                sort_keys=True,
                separators=(",", ":"),
            ) + "\n"
            self.assertEqual(expected[item["role"]], hashlib.sha256(payload.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    unittest.main()
