"""Evidence ownership and read-only behavior tests for PHASE-05."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtGui import QImage


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "verify_phase05.py"
SPEC = importlib.util.spec_from_file_location("verify_phase05", PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("PHASE-05 verifier could not be loaded")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class Phase05VerifierTests(unittest.TestCase):
    def test_stored_evidence_is_current_safe_and_honest(self) -> None:
        self.assertTrue(VERIFY.check())
        summary = json.loads(VERIFY.SUMMARY.read_text(encoding="utf-8"))
        self.assertEqual("passed", summary["status"])
        self.assertEqual("not_exercised", summary["hardware_status"])
        self.assertEqual("not_exercised", summary["live_rx_status"])
        self.assertIn("otomatik modülasyon sınıflandırması değildir", summary["claim_boundary"])

    def test_check_does_not_write_owned_files(self) -> None:
        before = {path: path.read_bytes() for path in (VERIFY.GOLDEN, VERIFY.SUMMARY)}
        self.assertTrue(VERIFY.check())
        self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_tampered_temporary_evidence_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "golden.json"
            bad.write_text("{}\n", encoding="utf-8")
            with patch.object(VERIFY, "GOLDEN", bad):
                self.assertFalse(VERIFY.check())

    def test_visual_evidence_inventory_and_dimensions(self) -> None:
        visual = json.loads((VERIFY.EVIDENCE / "visual-summary.json").read_text(encoding="utf-8"))
        self.assertEqual("passed", visual["status"])
        self.assertFalse(visual["byte_equality_gate"])
        self.assertEqual(
            ["no_source", "am_ready", "nfm_ready", "noise_no_event", "audio_unavailable", "scale150"],
            [item["state"] for item in visual["screenshots"]],
        )
        for item in visual["screenshots"]:
            image = QImage(str(VERIFY.EVIDENCE / item["file"]))
            self.assertFalse(image.isNull())
            self.assertEqual((item["width"], item["height"]), (image.width(), image.height()))


if __name__ == "__main__":
    unittest.main()
