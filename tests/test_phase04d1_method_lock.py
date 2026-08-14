"""Pre-binding identity and repository-safety tests for PHASE-04-D1."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from reference.parameters.obw99_reference import ROOT, canonical_json_bytes
from reference.pipeline.profile import resolve_default_operation_profile


LOCK = ROOT / "datasets" / "fixtures" / "phase04d1" / "method-lock.json"


class Phase04D1MethodLockTests(unittest.TestCase):
    def test_method_lock_identity_and_scope(self) -> None:
        document = json.loads(LOCK.read_text(encoding="utf-8"))
        identity = document.pop("identity_sha256")
        self.assertEqual(hashlib.sha256(canonical_json_bytes(document)).hexdigest(), identity)
        self.assertEqual(document["status"], "locked-pre-binding")
        self.assertEqual(document["comparison_id"], "phase04-d1-obw99-selection-v1")
        self.assertEqual(document["method"]["block_id"], "analysis.occupied-bandwidth/v1")
        self.assertEqual(document["method"]["output_type"], "parameters.occupied-bandwidth/v1")
        self.assertFalse(document["binding_or_oos_executed"])

    def test_contract_and_implementation_hashes_match(self) -> None:
        document = json.loads(LOCK.read_text(encoding="utf-8"))
        mapping = {
            "adr_0007_sha256": "docs/decisions/ADR-0007-OCCUPIED-BANDWIDTH-SEMANTICS.md",
            "interface_contract_sha256": "docs/interfaces/OCCUPIED_BANDWIDTH_CONTRACT.md",
            "acceptance_gates_sha256": "datasets/fixtures/phase04d1/acceptance-gates.json",
            "reference_contract_sha256": "datasets/fixtures/phase04d1/reference-contract.json",
            "scene_catalog_sha256": "datasets/fixtures/phase04d1/obw99-scenes.json",
            "clean_reference_sha256": "datasets/fixtures/phase04d1/clean-reference.json",
            "clean_reference_generator_sha256": "scripts/generate_phase04d1_reference.py",
            "phase03_profile_sha256": "profiles/phase03/operation-default.json",
        }
        for key, relative in mapping.items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), document["contracts"][key])
        for item in document["implementation_manifest"]["sources"]:
            self.assertEqual(hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest(), item["sha256"])

    def test_phase03_remains_the_runtime_default_and_old_methods_are_not_bound(self) -> None:
        resolved = resolve_default_operation_profile()
        self.assertEqual(resolved.profile.profile_id, "phase03-operation-default")
        self.assertEqual(resolved.profile.detector_block.type_id, "detector.regional")
        self.assertIsNone(resolved.profile.parameter_block)
        self.assertFalse((ROOT / "profiles/phase04/operation-default.json").exists())

    def test_protected_evidence_and_phase03_profile_match_head(self) -> None:
        paths = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", "HEAD", "--", "results/evidence"],
            cwd=ROOT,
            text=True,
        ).splitlines()
        paths.append("profiles/phase03/operation-default.json")
        for relative in paths:
            worktree = subprocess.check_output(["git", "hash-object", "--", relative], cwd=ROOT, text=True).strip()
            head = subprocess.check_output(["git", "rev-parse", f"HEAD:{relative}"], cwd=ROOT, text=True).strip()
            self.assertEqual(worktree, head, relative)


if __name__ == "__main__":
    unittest.main()
