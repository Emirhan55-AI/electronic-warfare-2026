"""Validation and runtime tests for the PHASE-03 block profile."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from reference.pipeline import (
    ProfileError,
    RuntimePipeline,
    build_operation_profile,
    canonical_profile_bytes,
    load_profile,
)
from reference.pipeline.profile import profile_from_document, profile_to_document


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "profiles" / "phase03" / "operation-default.json"


class ProcessingProfileTests(unittest.TestCase):
    def test_tracked_profile_is_canonical_validated_and_executable(self) -> None:
        profile = load_profile(PROFILE)
        self.assertEqual("validated", profile.lifecycle)
        self.assertEqual("regional", profile.detector_method)
        self.assertEqual(PROFILE.read_bytes(), canonical_profile_bytes(profile))
        self.assertEqual("regional", RuntimePipeline(profile).detector_method)

    def test_detector_type_in_profile_changes_runtime_detector(self) -> None:
        for method in ("regional", "ca_cfar", "os_cfar"):
            profile = build_operation_profile(method, lifecycle="experimental")
            runtime = RuntimePipeline(profile, allow_experimental=True)
            self.assertEqual(method, runtime.detector_method)

    def test_broken_connection_or_port_type_is_rejected(self) -> None:
        document = profile_to_document(build_operation_profile("regional"))
        document["connections"][0]["source_port"] = "unknown"
        with self.assertRaises(ProfileError):
            profile_from_document(document)

    def test_experimental_profile_cannot_be_operation_default(self) -> None:
        profile = build_operation_profile("regional", lifecycle="experimental")
        with self.assertRaisesRegex(ProfileError, "validated"):
            RuntimePipeline(profile)

    def test_profile_contains_no_absolute_path_or_dynamic_code(self) -> None:
        document = json.loads(PROFILE.read_text(encoding="utf-8"))
        text = json.dumps(document, ensure_ascii=False).casefold()
        self.assertNotIn("c:\\users", text)
        self.assertNotIn("python", text)
        self.assertNotIn("plugin", text)


if __name__ == "__main__":
    unittest.main()
