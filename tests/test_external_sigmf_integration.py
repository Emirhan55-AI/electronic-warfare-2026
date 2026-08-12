"""Optional, bounded integration test for the external ism_band_24 dataset."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reference.sigmf.contract import inspect_sigmf


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_external_sigmf_slice import extract_slice  # noqa: E402
from verify_phase01 import external_environment  # noqa: E402


METADATA_ENV = "PHASE01_EXTERNAL_METADATA"
DATA_ENV = "PHASE01_EXTERNAL_DATA"


class ExternalSigMFIntegrationTests(unittest.TestCase):
    def test_external_environment_requires_both_variables(self) -> None:
        clean_environment = {METADATA_ENV: "", DATA_ENV: ""}
        with patch.dict(os.environ, clean_environment, clear=False):
            _, _, configuration = external_environment()
        self.assertEqual("passed", configuration["status"])

        partial_environment = {METADATA_ENV: "metadata-only", DATA_ENV: ""}
        with patch.dict(os.environ, partial_environment, clear=False):
            _, _, configuration = external_environment()
        self.assertEqual("failed", configuration["status"])
        self.assertIn(DATA_ENV, configuration["detail"])

    def test_source_native_extractor_is_deterministic_and_non_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata_path = root / "source.sigmf-meta.txt"
            data_path = root / "source.sigmf-data"
            output_one = root / "output-one"
            output_two = root / "output-two"
            metadata = {
                "global": {
                    "core:version": "1.0.0",
                    "core:datatype": "ci16_le",
                    "core:sample_rate": 12_000_000,
                    "core:author": "Example Author",
                    "core:license": "Example License",
                },
                "captures": [{"core:sample_start": 0, "core:frequency": 915_000_000}],
                "annotations": [],
            }
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            pattern = b"\x01\x00\xff\xff"
            data_path.write_bytes(pattern * 16_384)
            before = data_path.stat()
            manifest_one = extract_slice(metadata_path, data_path, output_one)
            manifest_two = extract_slice(metadata_path, data_path, output_two)
            after = data_path.stat()
            self.assertEqual(65_536, manifest_one["slice_size_bytes"])
            self.assertEqual(manifest_one["slice_sha256"], manifest_two["slice_sha256"])
            self.assertEqual(manifest_one["slice_sha512"], manifest_two["slice_sha512"])
            self.assertEqual("unverified", manifest_one["license_status"])
            self.assertNotIn(str(root), json.dumps(manifest_one))
            self.assertEqual(before.st_size, after.st_size)
            self.assertEqual(before.st_mtime_ns, after.st_mtime_ns)
            with self.assertRaises(FileExistsError):
                extract_slice(metadata_path, data_path, output_one)

    def test_external_dataset_when_configured(self) -> None:
        metadata_value = os.environ.get(METADATA_ENV)
        data_value = os.environ.get(DATA_ENV)
        if bool(metadata_value) != bool(data_value):
            missing = DATA_ENV if metadata_value else METADATA_ENV
            self.fail(f"both external dataset variables are required; missing {missing}")
        if not metadata_value:
            self.skipTest("external dataset unavailable")

        metadata_path = Path(metadata_value)
        data_path = Path(data_value)
        before = data_path.stat()
        report = inspect_sigmf(metadata_path, data_path, mode="explicit")
        self.assertTrue(report.valid, report.errors)
        self.assertEqual("ci16_le", report.source_datatype)
        self.assertEqual(56_000_000, report.sample_rate)
        self.assertEqual(2_430_000_000, report.center_frequency)
        self.assertEqual("defaulted", report.channel_count_source)
        self.assertEqual(2_828_312_576, report.total_complex_samples)
        self.assertEqual(690_506, report.full_frame_count)
        self.assertEqual(0, report.dropped_complex_samples)
        self.assertIn("nonstandard_metadata_extension", {issue.code for issue in report.warnings})

        with data_path.open("rb") as source:
            first = source.read(65_536)
        with data_path.open("rb") as source:
            repeat = source.read(65_536)
        self.assertEqual(65_536, len(first))
        self.assertEqual(hashlib.sha256(first).digest(), hashlib.sha256(repeat).digest())
        after = data_path.stat()
        self.assertEqual(before.st_size, after.st_size)
        self.assertEqual(before.st_mtime_ns, after.st_mtime_ns)


if __name__ == "__main__":
    unittest.main()
