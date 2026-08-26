"""ET offline verifier and stored-evidence regression tests."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "scripts" / "verify_p0_et.py"
SPEC = importlib.util.spec_from_file_location("verify_p0_et", VERIFY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("ET verifier could not be loaded")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class ETVerifierTests(unittest.TestCase):
    def test_all_ktr_gates_pass_without_rf_claims(self) -> None:
        result = VERIFY.evaluate()
        self.assertEqual("passed", result["status"])
        self.assertEqual("ET-B", result["work_package"])
        self.assertEqual(5, len(result["gates"]))
        self.assertTrue(all(result["gates"].values()))
        self.assertEqual("not_implemented", result["safety"]["real_tx_backend"])
        self.assertFalse(result["safety"]["transmit_method_present"])
        self.assertNotIn("timestamp", json.dumps(result, ensure_ascii=False).casefold())

    def test_stored_evidence_is_current_and_check_is_read_only(self) -> None:
        before = VERIFY.EVIDENCE.read_bytes()
        self.assertTrue(VERIFY.check())
        self.assertEqual(before, VERIFY.EVIDENCE.read_bytes())


if __name__ == "__main__":
    unittest.main()
