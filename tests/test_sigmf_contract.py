"""Contract tests for PHASE-01 SigMF metadata and binary layout."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reference.sigmf.contract import ContractValidationError, decode_iq_pairs, inspect_sigmf


class SigMFContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_dataset(
        self,
        *,
        datatype: str = "ci8",
        sample_rate: int | float = 8_000_000,
        frequency: int | float = 100_000_000,
        channels: int | None = 1,
        captures: list[dict[str, object]] | None = None,
        data: bytes | None = None,
        metadata_name: str = "sample.sigmf-meta",
        version: str = "1.0.0",
    ) -> tuple[Path, Path]:
        global_object: dict[str, object] = {
            "core:version": version,
            "core:datatype": datatype,
            "core:sample_rate": sample_rate,
        }
        if channels is not None:
            global_object["core:num_channels"] = channels
        metadata = {
            "global": global_object,
            "captures": captures
            if captures is not None
            else [{"core:sample_start": 0, "core:frequency": frequency}],
            "annotations": [],
        }
        metadata_path = self.root / metadata_name
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        base = metadata_name[: -len(".sigmf-meta")] if metadata_name.endswith(".sigmf-meta") else "sample"
        data_path = self.root / f"{base}.sigmf-data"
        if data is None:
            bytes_per_sample = 2 if datatype == "ci8" else 4
            data = bytes(4096 * bytes_per_sample)
        data_path.write_bytes(data)
        return metadata_path, data_path

    def error_codes(self, report: object) -> set[str]:
        return {issue.code for issue in report.errors}

    def warning_codes(self, report: object) -> set[str]:
        return {issue.code for issue in report.warnings}

    def test_ci8_contract_uses_metadata_sample_rate(self) -> None:
        metadata, _ = self.write_dataset(sample_rate=10_000_000)
        report = inspect_sigmf(metadata, mode="standard")
        self.assertTrue(report.valid, report.errors)
        self.assertEqual("ci8", report.source_datatype)
        self.assertEqual(2, report.bytes_per_complex_sample)
        self.assertEqual(8192, report.frame_size_bytes)
        self.assertEqual(2441.40625, report.frequency_bin_spacing_hz)

    def test_ci16_le_contract_and_little_endian_decode(self) -> None:
        metadata, data_path = self.write_dataset(
            datatype="ci16_le",
            sample_rate=12_000_000,
            frequency=915_000_000,
            data=b"\x34\x12\xfe\xff" + bytes(16_380),
        )
        report = inspect_sigmf(metadata, data_path, mode="standard")
        self.assertTrue(report.valid, report.errors)
        self.assertEqual(4, report.bytes_per_complex_sample)
        self.assertEqual(16_384, report.frame_size_bytes)
        self.assertEqual((0x1234, -2), next(decode_iq_pairs(b"\x34\x12\xfe\xff", "ci16_le")))

    def test_signed_ci8_interleaving(self) -> None:
        self.assertEqual([(100, -100), (-1, 1)], list(decode_iq_pairs(b"\x64\x9c\xff\x01", "ci8")))

    def test_channel_count_default_and_explicit_sources(self) -> None:
        default_metadata, default_data = self.write_dataset(channels=None)
        default_report = inspect_sigmf(default_metadata, default_data, mode="standard")
        self.assertEqual(1, default_report.channel_count)
        self.assertEqual("defaulted", default_report.channel_count_source)
        self.assertIn("channel_count_defaulted", self.warning_codes(default_report))

        explicit_metadata, explicit_data = self.write_dataset(metadata_name="explicit.sigmf-meta", channels=1)
        explicit_report = inspect_sigmf(explicit_metadata, explicit_data, mode="standard")
        self.assertEqual("explicit", explicit_report.channel_count_source)

    def test_multichannel_dataset_is_rejected(self) -> None:
        metadata, data_path = self.write_dataset(channels=2)
        report = inspect_sigmf(metadata, data_path, mode="standard")
        self.assertIn("unsupported_channel_count", self.error_codes(report))

    def test_capture_count_and_start_are_strict(self) -> None:
        metadata, data_path = self.write_dataset(captures=[])
        self.assertIn("unsupported_capture_count", self.error_codes(inspect_sigmf(metadata, data_path, mode="standard")))
        metadata, data_path = self.write_dataset(
            metadata_name="multiple.sigmf-meta",
            captures=[
                {"core:sample_start": 0, "core:frequency": 1},
                {"core:sample_start": 4096, "core:frequency": 2},
            ],
        )
        self.assertIn("unsupported_capture_count", self.error_codes(inspect_sigmf(metadata, data_path, mode="standard")))
        metadata, data_path = self.write_dataset(
            metadata_name="offset.sigmf-meta",
            captures=[{"core:sample_start": 1, "core:frequency": 1}],
        )
        self.assertIn("invalid_capture_start", self.error_codes(inspect_sigmf(metadata, data_path, mode="standard")))

    def test_standard_and_explicit_filename_rules(self) -> None:
        metadata, data_path = self.write_dataset(metadata_name="sample.sigmf-meta.txt")
        standard = inspect_sigmf(metadata, data_path, mode="standard")
        self.assertIn("metadata_extension_not_standard", self.error_codes(standard))
        explicit_missing = inspect_sigmf(metadata, mode="explicit")
        self.assertIn("data_path_required", self.error_codes(explicit_missing))
        explicit = inspect_sigmf(metadata, data_path, mode="explicit")
        self.assertTrue(explicit.valid, explicit.errors)
        self.assertIn("nonstandard_metadata_extension", self.warning_codes(explicit))

    def test_invalid_metadata_fields_are_rejected(self) -> None:
        metadata, data_path = self.write_dataset(version="2.0.0")
        self.assertIn("unsupported_core_version", self.error_codes(inspect_sigmf(metadata, data_path, mode="standard")))
        metadata, data_path = self.write_dataset(metadata_name="rate.sigmf-meta", sample_rate=0)
        self.assertIn("invalid_field_value", self.error_codes(inspect_sigmf(metadata, data_path, mode="standard")))
        metadata, data_path = self.write_dataset(metadata_name="type.sigmf-meta", datatype="cf32_le")
        self.assertIn("unsupported_datatype", self.error_codes(inspect_sigmf(metadata, data_path, mode="standard")))
        metadata, data_path = self.write_dataset(metadata_name="frequency.sigmf-meta", frequency="100 MHz")
        self.assertIn("invalid_field_value", self.error_codes(inspect_sigmf(metadata, data_path, mode="standard")))

    def test_missing_required_metadata_fields_are_rejected(self) -> None:
        metadata, data_path = self.write_dataset()
        document = json.loads(metadata.read_text(encoding="utf-8"))
        for field in ("core:version", "core:datatype", "core:sample_rate"):
            modified = json.loads(json.dumps(document))
            del modified["global"][field]
            metadata.write_text(json.dumps(modified), encoding="utf-8")
            report = inspect_sigmf(metadata, data_path, mode="standard")
            self.assertIn("missing_required_field", self.error_codes(report), field)
        modified = json.loads(json.dumps(document))
        del modified["captures"][0]["core:frequency"]
        metadata.write_text(json.dumps(modified), encoding="utf-8")
        self.assertIn(
            "missing_required_field",
            self.error_codes(inspect_sigmf(metadata, data_path, mode="standard")),
        )

    def test_invalid_utf8_and_json_are_rejected(self) -> None:
        metadata = self.root / "bad.sigmf-meta"
        data = self.root / "bad.sigmf-data"
        data.write_bytes(bytes(8192))
        metadata.write_bytes(b"\xff")
        self.assertIn("metadata_invalid_utf8", self.error_codes(inspect_sigmf(metadata, data, mode="standard")))
        metadata.write_text("{", encoding="utf-8")
        self.assertIn("metadata_invalid_json", self.error_codes(inspect_sigmf(metadata, data, mode="standard")))

    def test_malformed_pair_and_incomplete_frame(self) -> None:
        metadata, data_path = self.write_dataset(data=bytes(8193))
        malformed = inspect_sigmf(metadata, data_path, mode="standard")
        self.assertIn("malformed_iq_pair", self.error_codes(malformed))
        with self.assertRaises(ContractValidationError) as context:
            list(decode_iq_pairs(b"\x00", "ci8"))
        self.assertEqual("malformed_iq_pair", context.exception.code)

        metadata, data_path = self.write_dataset(metadata_name="partial.sigmf-meta", data=bytes(8192 + 20))
        partial = inspect_sigmf(metadata, data_path, mode="standard")
        self.assertTrue(partial.valid, partial.errors)
        self.assertEqual(1, partial.full_frame_count)
        self.assertEqual(10, partial.dropped_complex_samples)
        self.assertEqual(20, partial.dropped_bytes)
        self.assertIn("incomplete_frame_dropped", self.warning_codes(partial))


if __name__ == "__main__":
    unittest.main()
