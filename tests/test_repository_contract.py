"""Standard-library tests for the PHASE-00 repository contract."""

from __future__ import annotations

import hashlib
import importlib.util
import json
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
            | set(VERIFY.APPROVED_PHASE08A_FILES)
            | set(VERIFY.APPROVED_PHASE05_FILES)
            | set(VERIFY.APPROVED_PHASE06A_FILES)
            | set(VERIFY.APPROVED_PHASE06B_FILES)
            | set(VERIFY.APPROVED_PHASE06C_FILES)
            | set(VERIFY.APPROVED_PHASE06D_FILES)
            | set(VERIFY.APPROVED_PHASE06E_FILES)
            | set(VERIFY.APPROVED_PHASE06F_FILES)
            | set(VERIFY.APPROVED_PHASE06G_FILES)
            | set(VERIFY.APPROVED_PHASE06H_FILES)
            | set(VERIFY.APPROVED_PHASE06I_FILES)
            | set(VERIFY.APPROVED_TEST_INFRASTRUCTURE_FILES)
            | set(VERIFY.APPROVED_PHASE06J_FILES)
            | set(VERIFY.APPROVED_P0_FILES)
        )
        self.assertEqual(31, len(VERIFY.APPROVED_PHASE03_FILES))
        self.assertEqual(37, len(VERIFY.APPROVED_PHASE04_BASE_FILES))
        self.assertEqual(9, len(VERIFY.PHASE04_SUCCESS_ONLY_FILES))
        self.assertEqual(26, len(VERIFY.APPROVED_PHASE04_D1_FILES))
        self.assertEqual(47, len(VERIFY.APPROVED_PHASE04_E1_FILES))
        self.assertEqual(1, len(VERIFY.PHASE04_E1_SUCCESS_ONLY_FILES))
        self.assertEqual(120, len(VERIFY.APPROVED_PHASE04_FILES))
        self.assertEqual(19, len(VERIFY.APPROVED_PHASE08A_FILES))
        self.assertEqual(32, len(VERIFY.APPROVED_PHASE05_FILES))
        self.assertEqual(24, len(VERIFY.APPROVED_PHASE06A_FILES))
        self.assertEqual(25, len(VERIFY.APPROVED_PHASE06B_FILES))
        self.assertEqual(26, len(VERIFY.APPROVED_PHASE06C_FILES))
        self.assertEqual(2, len(VERIFY.APPROVED_PHASE06D_PLANNING_FILES))
        self.assertEqual(30, len(VERIFY.APPROVED_PHASE06D_FILES))
        self.assertEqual(17, len(VERIFY.APPROVED_PHASE06E_FILES))
        self.assertEqual(24, len(VERIFY.APPROVED_PHASE06F_FILES))
        self.assertEqual(34, len(VERIFY.APPROVED_PHASE06G_FILES))
        self.assertEqual(29, len(VERIFY.APPROVED_PHASE06H_FILES))
        self.assertEqual(30, len(VERIFY.APPROVED_PHASE06I_FILES))
        self.assertEqual(4, len(VERIFY.APPROVED_TEST_INFRASTRUCTURE_FILES))
        self.assertEqual(22, len(VERIFY.APPROVED_PHASE06J_FILES))
        self.assertEqual(44, len(VERIFY.APPROVED_P0_FILES))
        self.assertEqual(set(), VERIFY._repository_files() - allowed)

    def test_phase04_frozen_catalog_is_byte_stable(self) -> None:
        catalog = ROOT / "datasets" / "fixtures" / "phase04" / "parameter-scenes.json"
        self.assertEqual(
            "8f15ca7a5eba5b3313ada215bbd178279b7d93a8dab83dd667777c88e92a910c",
            hashlib.sha256(catalog.read_bytes()).hexdigest(),
        )

    def test_phase04_r2_method_lock_is_present_and_path_stable(self) -> None:
        lock = ROOT / "datasets" / "fixtures" / "phase04" / "r2-method-lock.json"
        self.assertTrue(lock.is_file())
        self.assertIn("datasets/fixtures/phase04/r2-method-lock.json", VERIFY.APPROVED_PHASE04_BASE_FILES)

    def test_phase04_visual_artifacts_are_complete_or_absent(self) -> None:
        visual = set(VERIFY.PHASE04_SUCCESS_ONLY_FILES) - {"profiles/phase04/operation-default.json"}
        present = visual & VERIFY._repository_files()
        self.assertIn(present, (set(), visual))

    def test_phase04e1_failed_evaluation_has_no_validated_profile(self) -> None:
        expected_evidence = {
            "results/evidence/phase04e1/golden-parameters.json",
            "results/evidence/phase04e1/binding-results.json",
            "results/evidence/phase04e1/oos-results.json",
            "results/evidence/phase04e1/parameter-comparison.json",
            "results/evidence/phase04e1/verification-summary.json",
            "results/evidence/phase04e1/visual-summary.json",
        }
        self.assertTrue(expected_evidence <= set(VERIFY.APPROVED_PHASE04_E1_FILES))
        self.assertFalse((ROOT / "profiles/phase04e1/operation-default.json").exists())
        comparison = json.loads(
            (ROOT / "results/evidence/phase04e1/parameter-comparison.json").read_text(encoding="utf-8")
        )
        self.assertEqual("failed", comparison["status"])
        self.assertEqual([], comparison["validated_fields"])

    def test_phase06a_adds_only_the_approved_rtl_foundation(self) -> None:
        roadmap = (ROOT / "docs" / "plans" / "IMPLEMENTATION_ROADMAP.md").read_text(encoding="utf-8")
        for text in ("SystemVerilog", "AXI4-Stream", "PHASE-03 `regional`", "AMD/Xilinx FFT IP"):
            self.assertIn(text, roadmap)
        self.assertEqual(
            {
                "rtl/phase06a/rtl/phase06a_pkg.sv",
                "rtl/phase06a/rtl/axis_skid_buffer.sv",
                "rtl/phase06a/rtl/axis_ci8_frame_stats.sv",
                "rtl/phase06a/tb/tb_axis_ci8_frame_stats.sv",
                "rtl/phase06b/rtl/phase06b_pkg.sv",
                "rtl/phase06b/rtl/axis_hann_window.sv",
                "rtl/phase06b/tb/tb_axis_hann_window.sv",
                "rtl/phase06c/rtl/phase06c_pkg.sv",
                "rtl/phase06c/rtl/axis_fft_wrapper.sv",
                "rtl/phase06c/tb/fft_ip_transport_stub.sv",
                "rtl/phase06c/tb/tb_axis_fft_wrapper.sv",
                "rtl/phase06d/rtl/amd_xfft_adapter.sv",
                "rtl/phase06d/tb/tb_phase06d_fft_vendor.sv",
                "rtl/phase06e/rtl/phase06e_fft_implementation_top.sv",
                "rtl/phase06e/tb/tb_phase06e_axis_input_register_slice.sv",
                "rtl/phase06f/rtl/axis_fft_linear_power.sv",
                "rtl/phase06f/tb/tb_axis_fft_linear_power.sv",
                "rtl/phase06g/rtl/phase06g_pkg.sv",
                "rtl/phase06g/rtl/axis_regional_detector.sv",
                "rtl/phase06g/rtl/phase06g_detector_synthesis_top.sv",
                "rtl/phase06g/tb/tb_axis_regional_detector.sv",
                "rtl/phase06h/rtl/phase06h_pkg.sv",
                "rtl/phase06h/rtl/phase06h_candidate_ram.sv",
                "rtl/phase06h/rtl/axis_candidate_grouping.sv",
                "rtl/phase06h/rtl/phase06h_candidate_synthesis_top.sv",
                "rtl/phase06h/tb/tb_axis_candidate_grouping.sv",
                "rtl/phase06i/rtl/phase06i_pkg.sv",
                "rtl/phase06i/rtl/axis_candidate_packetizer.sv",
                "rtl/phase06i/tb/tb_axis_candidate_packetizer.sv",
                "rtl/p0/rtl/p0_dsp_runtime_top.sv",
            },
            {path for path in VERIFY._repository_files() if path.endswith(".sv")},
        )
        self.assertEqual([], [path for path in VERIFY._repository_files() if path.endswith(".svh")])

    def test_phase06b_is_hann_only_and_keeps_fft_for_later(self) -> None:
        roadmap = (ROOT / "docs" / "plans" / "IMPLEMENTATION_ROADMAP.md").read_text(encoding="utf-8")
        contract = (ROOT / "docs" / "interfaces" / "RTL_HANN_WINDOW_CONTRACT.md").read_text(encoding="utf-8")
        self.assertIn("PHASE-06B — Sabit Nokta Hann Pencereleme ve FFT Arayüz Temeli", roadmap)
        self.assertIn("Gerçek 4096 nokta FFT", roadmap)
        self.assertIn("UQ1.15", contract)
        self.assertIn("SQ1.15", contract)
        self.assertIn("gerçek fft", contract.casefold())

    def test_phase06c_is_wrapper_only_and_real_amd_ip_remains_unexercised(self) -> None:
        roadmap = (ROOT / "docs" / "plans" / "IMPLEMENTATION_ROADMAP.md").read_text(encoding="utf-8")
        contract = (ROOT / "docs" / "interfaces" / "RTL_FFT_INTERFACE_CONTRACT.md").read_text(encoding="utf-8")
        self.assertIn("PHASE-06C — 4096 Nokta FFT Mimarisi, Ölçekleme Sözleşmesi ve AMD IP Wrapper Temeli", roadmap)
        self.assertIn("transport stub", contract)
        self.assertIn("Gerçek AMD IP generation/simulation", contract)
        self.assertIn("64 bit", contract)
        self.assertIn("natural unshifted", contract)

    def test_phase06d_is_real_vendor_functional_verification_only(self) -> None:
        roadmap = (ROOT / "docs" / "plans" / "IMPLEMENTATION_ROADMAP.md").read_text(encoding="utf-8")
        decision = (
            ROOT / "docs" / "decisions" / "ADR-0014-PHASE06D-VENDOR-VERIFICATION-GATE.md"
        ).read_text(encoding="utf-8")
        gate = json.loads(
            (ROOT / "results" / "evidence" / "phase06d" / "toolchain-gate.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("PHASE-06D — Gerçek AMD FFT IP Entegrasyonu ve Vendor Doğrulaması", roadmap)
        self.assertIn("Synthesis, implementation", decision)
        self.assertIn("bit-eşit", decision)
        self.assertEqual("planning_toolchain_gate", gate["evidence_kind"])
        self.assertEqual("READY", gate["implementation_readiness"])
        self.assertFalse(gate["ip_catalog"]["generated_ip"])
        self.assertFalse(gate["ip_catalog"]["xci_created"])
        xci_files = [path for path in VERIFY._repository_files() if path.endswith(".xci")]
        self.assertEqual(1, len(xci_files))
        summary = json.loads(
            (ROOT / "results" / "evidence" / "phase06d" / "verification-summary.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("passed", summary["overall"])
        self.assertEqual("not_exercised", summary["synthesis"])

    def test_phase08a_is_an_explicit_preparation_exception(self) -> None:
        roadmap = (ROOT / "docs" / "plans" / "IMPLEMENTATION_ROADMAP.md").read_text(encoding="utf-8")
        for text in (
            "P0 öncesindeki kayıtlı ana açık fazlar: PHASE-04 ve PHASE-06",
            "PHASE-08A",
            "PHASE-06–07'nin başladığı, atlandığı veya tamamlandığı anlamına gelmez",
            "Gerçek cihaz keşfi, gerçek sweep, canlı I/Q, RF performansı ve donanım evidence'ı",
        ):
            self.assertIn(text, roadmap)
        self.assertFalse((ROOT / "profiles" / "phase04e1" / "operation-default.json").exists())

    def test_phase05_scope_is_recorded_only_and_truthful(self) -> None:
        roadmap = (ROOT / "docs" / "plans" / "IMPLEMENTATION_ROADMAP.md").read_text(encoding="utf-8")
        self.assertIn("PHASE-05 kayıtlı/sentetik I/Q", roadmap)
        self.assertIn("Gerçek canlı HackRF dinleme", roadmap)
        self.assertIn("PHASE-04 parametre doğrulamasının tamamlandığı anlamına gelmez", roadmap)

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
