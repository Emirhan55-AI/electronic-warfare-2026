"""Standard-library tests for the PHASE-00 repository contract."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "scripts" / "verify_phase00.py"
SPEC = importlib.util.spec_from_file_location("verify_phase00", VERIFY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load verifier from {VERIFY_PATH}")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class RepositoryContractTests(unittest.TestCase):
    def test_phase00_baseline_files_remain_required(self) -> None:
        self.assertEqual(19, len(VERIFY.REQUIRED_FILES))

    def test_only_approved_phase01_paths_extend_the_baseline(self) -> None:
        allowed = set(VERIFY.REQUIRED_FILES) | set(VERIFY.APPROVED_PHASE01_FILES)
        self.assertEqual(set(), VERIFY._repository_files() - allowed)

    def test_every_repository_contract_check_passes(self) -> None:
        failures = [
            f"{result['id']}: {result['detail']}"
            for result in VERIFY.run_checks()
            if result["status"] != "passed"
        ]
        self.assertEqual([], failures, "\n".join(failures))

    def test_tool_absence_is_not_a_contract_failure(self) -> None:
        inventory = VERIFY.check_toolchain_inventory()
        self.assertEqual("passed", inventory["status"], inventory["detail"])

    def test_all_declared_files_are_text_clean(self) -> None:
        integrity = VERIFY.check_text_integrity()
        self.assertEqual("passed", integrity["status"], integrity["detail"])


if __name__ == "__main__":
    unittest.main()
