"""Standard-library tests for the PHASE-00 repository contract."""

from __future__ import annotations

import hashlib
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

    def test_only_approved_later_phase_paths_extend_the_baseline(self) -> None:
        allowed = (
            set(VERIFY.REQUIRED_FILES)
            | set(VERIFY.APPROVED_PHASE01_FILES)
            | set(VERIFY.APPROVED_PHASE02_FILES)
            | set(VERIFY.APPROVED_PHASE03_FILES)
            | set(VERIFY.APPROVED_PHASE04_FILES)
        )
        self.assertEqual(31, len(VERIFY.APPROVED_PHASE03_FILES))
        self.assertEqual(21, len(VERIFY.APPROVED_PHASE04_BASE_FILES))
        self.assertEqual(9, len(VERIFY.PHASE04_SUCCESS_ONLY_FILES))
        self.assertEqual(30, len(VERIFY.APPROVED_PHASE04_FILES))
        self.assertEqual(set(), VERIFY._repository_files() - allowed)

    def test_phase04_frozen_catalog_is_byte_stable(self) -> None:
        catalog = ROOT / "datasets" / "fixtures" / "phase04" / "parameter-scenes.json"
        self.assertEqual(
            "8f15ca7a5eba5b3313ada215bbd178279b7d93a8dab83dd667777c88e92a910c",
            hashlib.sha256(catalog.read_bytes()).hexdigest(),
        )

    def test_phase04_visual_artifacts_are_complete_or_absent(self) -> None:
        visual = set(VERIFY.PHASE04_SUCCESS_ONLY_FILES) - {"profiles/phase04/operation-default.json"}
        present = visual & VERIFY._repository_files()
        self.assertIn(present, (set(), visual))

    def test_phase06_direction_does_not_add_rtl_early(self) -> None:
        roadmap = (ROOT / "docs" / "plans" / "IMPLEMENTATION_ROADMAP.md").read_text(encoding="utf-8")
        for text in ("SystemVerilog", "AXI4-Stream", "PHASE-03 `regional`", "AMD/Xilinx FFT IP"):
            self.assertIn(text, roadmap)
        self.assertEqual([], list(ROOT.rglob("*.sv")))
        self.assertEqual([], list(ROOT.rglob("*.svh")))

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
