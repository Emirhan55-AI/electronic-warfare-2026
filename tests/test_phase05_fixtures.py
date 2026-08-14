"""Deterministic SigMF fixture contract tests for PHASE-05."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from reference.monitoring import build_fixture_files
from reference.spectrum import SigMFFrameSource


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "datasets" / "fixtures" / "phase05"


class Phase05FixtureTests(unittest.TestCase):
    def test_every_fixture_is_byte_deterministic_and_parseable(self) -> None:
        expected, manifest = build_fixture_files()
        for name, payload in expected.items():
            with self.subTest(name=name):
                self.assertEqual(payload, (FIXTURE_DIR / name).read_bytes())
        self.assertEqual("Deterministik sentetik I/Q; gerçek RF kaydı değildir.", manifest["claim_boundary"])
        for row in manifest["fixtures"]:
            source = SigMFFrameSource(FIXTURE_DIR / f"{row['fixture_id']}.sigmf-meta")
            self.assertEqual(8, source.frame_count)
            self.assertEqual(192_000.0, source.sample_rate_hz)
            self.assertEqual(row["data_sha256"], hashlib.sha256(source.data_path.read_bytes()).hexdigest())

    def test_manifest_has_no_path_or_hardware_claim(self) -> None:
        document = json.loads((FIXTURE_DIR / "fixture-manifest.json").read_text(encoding="utf-8"))
        text = json.dumps(document, ensure_ascii=False)
        self.assertNotIn("C:\\Users", text)
        self.assertNotIn("canlı RF kaydı", text)


if __name__ == "__main__":
    unittest.main()
