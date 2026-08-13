"""Bounded-read and datatype tests for the PHASE-02 SigMF frame source."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from reference.spectrum import SigMFFrameSource, SigMFSourceError, SpectrumProcessor


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_META = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-meta"


class RecordingStream(io.BytesIO):
    def __init__(self, payload: bytes) -> None:
        super().__init__(payload)
        self.read_sizes: list[int] = []
        self.seek_offsets: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return super().read(size)

    def seek(self, offset: int, whence: int = 0) -> int:
        self.seek_offsets.append(offset)
        return super().seek(offset, whence)

    def __enter__(self) -> "RecordingStream":
        return self

    def __exit__(self, *_: object) -> None:
        pass


class RecordingPath:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.streams: list[RecordingStream] = []

    def open(self, mode: str) -> RecordingStream:
        if mode != "rb":
            raise AssertionError(f"unexpected mode: {mode}")
        stream = RecordingStream(self.payload)
        self.streams.append(stream)
        return stream


class SigMFFrameSourceTests(unittest.TestCase):
    def test_reads_only_the_requested_complete_frame(self) -> None:
        source = SigMFFrameSource(FIXTURE_META)
        with source.data_path.open("rb") as stream:
            actual_payload = stream.read()
        recording_path = RecordingPath(actual_payload)
        source.data_path = recording_path  # type: ignore[assignment]
        frame = source.read_frame(2)
        self.assertEqual((4096,), frame.shape)
        self.assertEqual([16_384], recording_path.streams[0].seek_offsets)
        self.assertEqual([8192], recording_path.streams[0].read_sizes)
        self.assertFalse(frame.flags.writeable)

    def test_frame_range_is_limited_to_complete_frames(self) -> None:
        source = SigMFFrameSource(FIXTURE_META)
        self.assertEqual(4, source.frame_count)
        with self.assertRaises(SigMFSourceError) as context:
            source.read_frame(4)
        self.assertEqual("frame_index_out_of_range", context.exception.code)

    def test_ci8_and_equivalent_ci16_have_the_same_spectrum(self) -> None:
        ci8_source = SigMFFrameSource(FIXTURE_META)
        ci8_frame = ci8_source.read_frame(0)
        integers = np.empty((4096, 2), dtype=np.dtype("<i2"))
        integers[:, 0] = np.rint(ci8_frame.real * 32768.0).astype(np.int16)
        integers[:, 1] = np.rint(ci8_frame.imag * 32768.0).astype(np.int16)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata_path = root / "equivalent.sigmf-meta"
            data_path = root / "equivalent.sigmf-data"
            metadata = {
                "global": {
                    "core:version": "1.0.0",
                    "core:datatype": "ci16_le",
                    "core:sample_rate": 8_000_000,
                    "core:num_channels": 1,
                },
                "captures": [{"core:sample_start": 0, "core:frequency": 100_000_000}],
                "annotations": [],
            }
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            data_path.write_bytes(integers.tobytes())
            ci16_source = SigMFFrameSource(metadata_path)
            ci16_frame = ci16_source.read_frame(0)

        np.testing.assert_allclose(ci8_frame, ci16_frame, rtol=0.0, atol=0.0)
        processor = SpectrumProcessor()
        ci8_result = processor.process(ci8_frame, sample_rate_hz=8_000_000, center_frequency_hz=100_000_000)
        ci16_result = processor.process(ci16_frame, sample_rate_hz=8_000_000, center_frequency_hz=100_000_000)
        np.testing.assert_allclose(ci8_result.fft_unshifted, ci16_result.fft_unshifted, rtol=1e-10, atol=1e-12)

    def test_short_read_is_rejected(self) -> None:
        source = SigMFFrameSource(FIXTURE_META)
        source.data_path = RecordingPath(bytes(10))  # type: ignore[assignment]
        with self.assertRaises(SigMFSourceError) as context:
            source.read_frame(0)
        self.assertEqual("short_frame_read", context.exception.code)

    def test_nonstandard_explicit_metadata_requires_a_data_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            metadata = Path(directory) / "recording.sigmf-meta.txt"
            metadata.write_text(
                json.dumps(
                    {
                        "global": {
                            "core:version": "1.0.0",
                            "core:datatype": "ci8",
                            "core:sample_rate": 8_000_000,
                        },
                        "captures": [{"core:sample_start": 0, "core:frequency": 100_000_000}],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(SigMFSourceError) as context:
                SigMFFrameSource(metadata, mode="explicit")
            self.assertIn("data_path_required", str(context.exception))


if __name__ == "__main__":
    unittest.main()
