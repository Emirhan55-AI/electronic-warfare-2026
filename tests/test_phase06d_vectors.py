"""PHASE-06D vector inheritance and negative-frequency coverage tests."""

from __future__ import annotations

import unittest
from pathlib import Path

from reference.rtl.phase06d_vectors import build_frames, build_vector_files


ROOT = Path(__file__).resolve().parents[1]


class Phase06DVectorsTests(unittest.TestCase):
    def test_first_ten_frames_are_phase06c_byte_identical(self) -> None:
        generated = build_vector_files()
        phase06c = (ROOT / "datasets" / "fixtures" / "phase06c" / "axis-input.mem").read_bytes()
        self.assertEqual(phase06c, generated["axis-input.mem"][: len(phase06c)])

    def test_negative_frequency_exact_bin_is_added(self) -> None:
        frames = build_frames()
        self.assertEqual(11, len(frames))
        self.assertEqual(4096, len(frames["negative_frequency_tone"]))

    def test_stored_input_fixture_is_current(self) -> None:
        for name, payload in build_vector_files().items():
            self.assertEqual(payload, (ROOT / "datasets" / "fixtures" / "phase06d" / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
