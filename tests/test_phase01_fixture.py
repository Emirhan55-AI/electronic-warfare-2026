"""Determinism and contract tests for the tracked PHASE-01 fixture."""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_phase01_fixture as fixture  # noqa: E402

from reference.sigmf.contract import decode_iq_pairs, inspect_sigmf  # noqa: E402


class Phase01FixtureTests(unittest.TestCase):
    def test_generated_outputs_match_tracked_files(self) -> None:
        self.assertEqual([], fixture.check_outputs(fixture.serialized_outputs()))

    def test_fixture_contract_and_hashes(self) -> None:
        data = fixture.DATA_PATH.read_bytes()
        manifest = json.loads(fixture.MANIFEST_PATH.read_text(encoding="utf-8"))
        report = inspect_sigmf(fixture.METADATA_PATH, mode="standard")
        self.assertTrue(report.valid, report.errors)
        self.assertEqual(32_768, len(data))
        self.assertEqual(16_384, report.total_complex_samples)
        self.assertEqual(4, report.full_frame_count)
        self.assertEqual(hashlib.sha256(data).hexdigest(), manifest["sha256"])
        self.assertEqual(hashlib.sha512(data).hexdigest(), manifest["sha512"])

    def test_fixture_repeats_the_engineering_lookup_table(self) -> None:
        pairs = list(decode_iq_pairs(fixture.DATA_PATH.read_bytes()[:32], "ci8"))
        self.assertEqual(list(fixture.TONE_TABLE), pairs)
        self.assertEqual(100, fixture.PEAK_AMPLITUDE_COUNTS)
        self.assertEqual(256, fixture.SIGNED_FFT_BIN)
        self.assertEqual(256, fixture.UNSHIFTED_FFT_INDEX)


if __name__ == "__main__":
    unittest.main()
