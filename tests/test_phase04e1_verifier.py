from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.verify_phase04e1 import build_summary


class Phase04E1VerifierTests(unittest.TestCase):
    def test_summary_has_no_timestamp_or_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch("scripts.verify_phase04e1.EVIDENCE", root), patch("scripts.verify_phase04e1.SUMMARY", root / "verification-summary.json"):
                summary = build_summary()
            encoded = json.dumps(summary, ensure_ascii=False)
            self.assertNotIn("timestamp", encoded.casefold())
            self.assertNotIn("C:\\Users", encoded)

    def test_status_vocabulary_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch("scripts.verify_phase04e1.EVIDENCE", root):
                summary = build_summary()
            self.assertTrue(all(item["status"] in {"passed", "failed", "skipped"} for item in summary["checks"]))


if __name__ == "__main__":
    unittest.main()
