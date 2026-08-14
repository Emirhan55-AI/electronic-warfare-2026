from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reference.parameters.operator_reference import (
    ACCEPTANCE_PATH,
    METHOD_LOCK_PATH,
    PHASE03_PROFILE_PATH,
    canonical_json_bytes,
    implementation_manifest,
    load_json,
    sha256_file,
)
from reference.pipeline.profile import PHASE04E1_FIELDS, load_phase04e1_capability


class Phase04E1ProfileTests(unittest.TestCase):
    def test_missing_profile_is_safe_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(load_phase04e1_capability(Path(folder) / "missing.json", Path(folder) / "comparison.json"))

    def test_comparison_tamper_rejects_profile(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            comparison = {"schema_version": 1, "comparison_id": "phase04e1-operator-assisted-parameters", "status": "passed", "validated_fields": ["occupied_bandwidth"]}
            comparison_path = root / "comparison.json"
            comparison_path.write_bytes(canonical_json_bytes(comparison))
            profile = {
                "profile_id": "phase04e1-operator-assisted-parameters",
                "validated_fields": ["occupied_bandwidth"],
                "methods": {},
                "method_lock_sha256": "0" * 64,
                "comparison_sha256": hashlib.sha256(comparison_path.read_bytes()).hexdigest(),
                "implementation_manifest_sha256": implementation_manifest()["sha256"],
                "phase03_profile_sha256": "0" * 64,
                "acceptance_contract_sha256": "0" * 64,
            }
            profile_path = root / "profile.json"
            profile_path.write_bytes(canonical_json_bytes(profile))
            comparison["validated_fields"] = []
            comparison_path.write_bytes(canonical_json_bytes(comparison))
            self.assertIsNone(load_phase04e1_capability(profile_path, comparison_path))

    def test_manual_field_profile_does_not_require_automatic_span(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            comparison = {
                "schema_version": 2,
                "comparison_id": "phase04e1-operator-assisted-parameters",
                "protocol_revision": "independent-fields-v2",
                "status": "passed",
                "automatic_span_validated": False,
                "validated_fields": ["uncalibrated_power_dbfs"],
                "field_decisions": [
                    {"field": name, "status": "passed" if name == "uncalibrated_power_dbfs" else "failed"}
                    for name in ("automatic_span", *PHASE04E1_FIELDS)
                ],
            }
            comparison_path = root / "comparison.json"
            comparison_path.write_bytes(canonical_json_bytes(comparison))
            methods = dict(load_json(METHOD_LOCK_PATH)["methods"])
            methods.pop("automatic_span")
            profile = {
                "profile_id": "phase04e1-operator-assisted-parameters",
                "validated_fields": ["uncalibrated_power_dbfs"],
                "automatic_span_validated": False,
                "methods": methods,
                "method_lock_sha256": sha256_file(METHOD_LOCK_PATH),
                "comparison_sha256": hashlib.sha256(comparison_path.read_bytes()).hexdigest(),
                "implementation_manifest_sha256": implementation_manifest()["sha256"],
                "phase03_profile_sha256": sha256_file(PHASE03_PROFILE_PATH),
                "acceptance_contract_sha256": sha256_file(ACCEPTANCE_PATH),
            }
            profile_path = root / "profile.json"
            profile_path.write_bytes(canonical_json_bytes(profile))
            capability = load_phase04e1_capability(profile_path, comparison_path)
            self.assertIsNotNone(capability)
            self.assertFalse(capability.automatic_span_validated)


if __name__ == "__main__":
    unittest.main()
