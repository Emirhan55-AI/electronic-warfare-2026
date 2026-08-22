"""Lossless HackRF replay wrapping and recorded amplitude-DF tests."""

from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from reference.p0 import RECORDED_DF_SOURCE, RecordedDFError, RecordedDFReport, analyze_recorded_df
from reference.sigmf import HACKRF_REPLAY_DESCRIPTION, wrap_hackrf_iq_as_sigmf
from reference.sigmf.contract import inspect_sigmf
from reference.spectrum import SigMFFrameSource


class HackRFRecordedIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_wrapper_copies_signed_ci8_bytes_and_writes_required_sigmf_metadata(self) -> None:
        raw = self.root / "detection.iq"
        payload = bytes([0, 0, 127, 128, 255, 1, 10, 246])
        raw.write_bytes(payload)

        data, metadata = wrap_hackrf_iq_as_sigmf(
            raw,
            sample_rate_hz="8000000",
            center_frequency_hz="433920000",
            output_basename=self.root / "detection",
        )

        self.assertEqual(payload, data.read_bytes())
        document = json.loads(metadata.read_text(encoding="utf-8"))
        self.assertEqual("ci8", document["global"]["core:datatype"])
        self.assertEqual(8_000_000.0, document["global"]["core:sample_rate"])
        self.assertEqual(1, document["global"]["core:num_channels"])
        self.assertEqual(HACKRF_REPLAY_DESCRIPTION, document["global"]["core:description"])
        self.assertEqual(433_920_000.0, document["captures"][0]["core:frequency"])
        self.assertTrue(inspect_sigmf(metadata, mode="standard").valid)
        self.assertEqual(HACKRF_REPLAY_DESCRIPTION, SigMFFrameSource(metadata).source_description)

    def test_wrapper_refuses_incomplete_iq_pair_without_creating_output(self) -> None:
        raw = self.root / "broken.iq"
        raw.write_bytes(b"\x00")
        with self.assertRaises(ValueError):
            wrap_hackrf_iq_as_sigmf(
                raw,
                sample_rate_hz=8_000_000,
                center_frequency_hz=433_920_000,
                output_basename=self.root / "broken",
            )
        self.assertFalse((self.root / "broken.sigmf-data").exists())
        self.assertFalse((self.root / "broken.sigmf-meta").exists())

    @staticmethod
    def _ci8_tone(*, amplitude: float, frame_count: int = 12) -> bytes:
        sample_count = 4096 * frame_count
        index = np.arange(sample_count, dtype=np.float64)
        phase = 2.0 * math.pi * 512.0 * index / 4096.0
        i = np.rint(amplitude * 127.0 * np.cos(phase)).astype(np.int8)
        q = np.rint(amplitude * 127.0 * np.sin(phase)).astype(np.int8)
        packed = np.empty(sample_count * 2, dtype=np.int8)
        packed[0::2] = i
        packed[1::2] = q
        return packed.tobytes()

    def test_recorded_df_uses_many_frames_and_emits_actual_angle_power_points(self) -> None:
        paths: list[Path] = []
        amplitudes = {0: 0.10, 45: 0.15, 90: 0.40, 135: 0.18, 180: 0.11, 225: 0.09, 270: 0.08, 315: 0.12}
        for angle, amplitude in amplitudes.items():
            raw = self.root / f"df_{angle:03d}.iq"
            raw.write_bytes(self._ci8_tone(amplitude=amplitude))
            _, metadata = wrap_hackrf_iq_as_sigmf(
                raw,
                sample_rate_hz=4096,
                center_frequency_hz=100_000_000,
                output_basename=self.root / f"df_{angle:03d}",
            )
            paths.append(metadata)

        report = analyze_recorded_df(
            paths,
            target_frequency_hz=100_000_512,
            channel_bandwidth_hz=8,
            maximum_frames=32,
        )

        self.assertEqual(RECORDED_DF_SOURCE, report.source)
        self.assertEqual(tuple(float(angle) for angle in range(0, 360, 45)), tuple(point.angle_deg for point in report.points))
        self.assertTrue(all(point.analyzed_frame_count == 11 for point in report.points))
        self.assertTrue(all(point.discarded_frame_count == 1 for point in report.points))
        self.assertEqual(90.0, max(report.points, key=lambda point: point.measured_power_dbfs).angle_deg)
        self.assertEqual(report, RecordedDFReport.from_document(report.to_document()))

    def test_recorded_df_refuses_target_outside_recorded_spectrum(self) -> None:
        paths = []
        for angle in range(0, 360, 45):
            raw = self.root / f"df_{angle:03d}.iq"
            raw.write_bytes(self._ci8_tone(amplitude=0.1))
            _, metadata = wrap_hackrf_iq_as_sigmf(
                raw,
                sample_rate_hz=4096,
                center_frequency_hz=100_000_000,
                output_basename=self.root / f"df_{angle:03d}",
            )
            paths.append(metadata)
        with self.assertRaises(RecordedDFError):
            analyze_recorded_df(paths, target_frequency_hz=101_000_000, channel_bandwidth_hz=8)


if __name__ == "__main__":
    unittest.main()
