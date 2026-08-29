#!/usr/bin/env python3
"""Verify the PHASE-00 repository contract using only the standard library."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "results" / "evidence" / "phase00" / "verification-summary.json"

REQUIRED_FILES = (
    ".editorconfig",
    ".gitignore",
    "AGENTS.md",
    "README.md",
    "datasets/README.md",
    "docs/architecture/SYSTEM_BASELINE.md",
    "docs/decisions/ADR-0001-REFERENCE-HARDWARE.md",
    "docs/plans/IMPLEMENTATION_ROADMAP.md",
    "docs/requirements/KTR_TRACEABILITY.md",
    "docs/safety/RF_TEST_BOUNDARIES.md",
    "app/README.md",
    "algorithms/README.md",
    "results/evidence/phase00/toolchain.json",
    "results/evidence/phase00/verification-summary.json",
    "algorithms/fpga/README.md",
    "scripts/phase00_doctor.py",
    "scripts/verify_phase00.py",
    "tests/test_repository_contract.py",
    "verification/README.md",
)

# PHASE-00 remains a historical baseline. Later files are permitted only when
# their paths were explicitly approved by the next phase plan.
APPROVED_PHASE01_FILES = (
    "datasets/external/README.md",
    "datasets/fixtures/phase01/README.md",
    "datasets/fixtures/phase01/known-tone-ci8.sigmf-data",
    "datasets/fixtures/phase01/known-tone-ci8.sigmf-meta",
    "docs/decisions/ADR-0002-SIGMF-DATA-PROFILES.md",
    "docs/interfaces/SIGMF_INPUT_CONTRACT.md",
    "algorithms/sigmf/__init__.py",
    "algorithms/sigmf/contract.py",
    "results/evidence/phase01/external-dataset-manifest.example.json",
    "results/evidence/phase01/fixture-manifest.json",
    "results/evidence/phase01/verification-summary.json",
    "scripts/extract_external_sigmf_slice.py",
    "scripts/generate_phase01_fixture.py",
    "scripts/verify_phase01.py",
    "tests/test_external_sigmf_integration.py",
    "tests/test_phase01_fixture.py",
    "tests/test_sigmf_contract.py",
)

APPROVED_PHASE02_FILES = (
    "docs/decisions/ADR-0003-OPERATOR-APPLICATION-STACK.md",
    "docs/interfaces/SPECTRUM_REFERENCE_CONTRACT.md",
    "app/operator_console/__init__.py",
    "app/operator_console/__main__.py",
    "app/operator_console/application.py",
    "app/operator_console/controller.py",
    "app/operator_console/main_window.py",
    "app/operator_console/pysidedeploy.spec",
    "app/operator_console/spectrum_view.py",
    "app/operator_console/theme.qss",
    "app/operator_console/ui_text.py",
    "algorithms/spectrum/__init__.py",
    "algorithms/spectrum/dsp.py",
    "algorithms/spectrum/source.py",
    "requirements/phase02.txt",
    "results/evidence/phase02/golden-spectrum.json",
    "results/evidence/phase02/screenshots/empty-1366x768-scale100.png",
    "results/evidence/phase02/screenshots/error-1366x768-scale100.png",
    "results/evidence/phase02/screenshots/loaded-1366x768-scale100.png",
    "results/evidence/phase02/screenshots/loaded-1920x1080-scale150.png",
    "results/evidence/phase02/screenshots/warning-1366x768-scale100.png",
    "results/evidence/phase02/verification-summary.json",
    "results/evidence/phase02/visual-summary.json",
    "scripts/render_phase02_ui.py",
    "scripts/verify_phase02.py",
    "tests/test_operator_console.py",
    "tests/test_phase02_verifier.py",
    "tests/test_sigmf_frame_source.py",
    "tests/test_spectrum_reference.py",
)

APPROVED_PHASE03_FILES = (
    "datasets/fixtures/phase03/detection-scenes.json",
    "docs/decisions/ADR-0004-ADAPTIVE-DETECTION.md",
    "docs/interfaces/DETECTION_CONTRACT.md",
    "docs/interfaces/PROCESSING_PROFILE_CONTRACT.md",
    "profiles/phase03/operation-default.json",
    "algorithms/detection/__init__.py",
    "algorithms/detection/cfar.py",
    "algorithms/detection/pipeline.py",
    "algorithms/detection/scenes.py",
    "algorithms/pipeline/__init__.py",
    "algorithms/pipeline/profile.py",
    "results/evidence/phase03/detector-comparison.json",
    "results/evidence/phase03/golden-detection.json",
    "results/evidence/phase03/screenshots/confirmed-1366x768-scale100.png",
    "results/evidence/phase03/screenshots/confirmed-1920x1080-scale150.png",
    "results/evidence/phase03/screenshots/empty-1366x768-scale100.png",
    "results/evidence/phase03/screenshots/error-1366x768-scale100.png",
    "results/evidence/phase03/screenshots/noise-only-1366x768-scale100.png",
    "results/evidence/phase03/screenshots/tentative-1366x768-scale100.png",
    "results/evidence/phase03/screenshots/warning-1366x768-scale100.png",
    "results/evidence/phase03/verification-summary.json",
    "results/evidence/phase03/visual-summary.json",
    "scripts/render_phase03_ui.py",
    "scripts/select_phase03_profile.py",
    "scripts/verify_phase03.py",
    "tests/test_detection_reference.py",
    "tests/test_detection_statistics.py",
    "tests/test_operator_detection.py",
    "tests/test_phase03_selector.py",
    "tests/test_phase03_verifier.py",
    "tests/test_processing_profile.py",
)

APPROVED_PHASE04_BASE_FILES = (
    "datasets/fixtures/phase04/parameter-scenes.json",
    "datasets/fixtures/phase04/r2-method-lock.json",
    "docs/decisions/ADR-0005-CORE-PARAMETER-EXTRACTION.md",
    "docs/decisions/ADR-0006-PHASE04-R2-BAND-RECOVERY.md",
    "docs/interfaces/PARAMETER_EXTRACTION_CONTRACT.md",
    "algorithms/parameters/__init__.py",
    "algorithms/parameters/models.py",
    "algorithms/parameters/extraction.py",
    "algorithms/parameters/classification.py",
    "algorithms/parameters/scenes.py",
    "algorithms/parameters/evaluation.py",
    "algorithms/parameters/r2.py",
    "scripts/select_phase04_profile.py",
    "scripts/select_phase04_r2_profile.py",
    "scripts/diagnose_phase04_r2.py",
    "scripts/characterize_phase04_r2_oos.py",
    "scripts/verify_phase04_r2.py",
    "scripts/verify_phase04.py",
    "scripts/render_phase04_ui.py",
    "tests/test_parameter_reference.py",
    "tests/test_parameter_scenes.py",
    "tests/test_parameter_statistics.py",
    "tests/test_phase04_selector.py",
    "tests/test_phase04_verifier.py",
    "tests/test_phase04_r2_diagnostics.py",
    "tests/test_phase04_r2_reference.py",
    "tests/test_phase04_r2_selector.py",
    "tests/test_phase04_r2_verifier.py",
    "tests/test_operator_parameters.py",
    "results/evidence/phase04/parameter-comparison.json",
    "results/evidence/phase04/golden-parameters.json",
    "results/evidence/phase04/verification-summary.json",
    "results/evidence/phase04/r2-family-diagnostic.json",
    "results/evidence/phase04/r2-parameter-comparison.json",
    "results/evidence/phase04/r2-out-of-sample.json",
    "results/evidence/phase04/r2-golden-parameters.json",
    "results/evidence/phase04/r2-verification-summary.json",
)

PHASE04_SUCCESS_ONLY_FILES = (
    "profiles/phase04/operation-default.json",
    "results/evidence/phase04/visual-summary.json",
    "results/evidence/phase04/empty-1366x768-scale100.png",
    "results/evidence/phase04/parameters-valid-1366x768-scale100.png",
    "results/evidence/phase04/carrier-unavailable-1366x768-scale100.png",
    "results/evidence/phase04/classification-uncertain-1366x768-scale100.png",
    "results/evidence/phase04/warning-1366x768-scale100.png",
    "results/evidence/phase04/error-1366x768-scale100.png",
    "results/evidence/phase04/parameters-valid-1920x1080-scale150.png",
)

APPROVED_PHASE04_D1_FILES = (
    "datasets/fixtures/phase04d1/acceptance-gates.json",
    "datasets/fixtures/phase04d1/clean-reference.json",
    "datasets/fixtures/phase04d1/evaluation-lock.json",
    "datasets/fixtures/phase04d1/method-lock.json",
    "datasets/fixtures/phase04d1/obw99-scenes.json",
    "datasets/fixtures/phase04d1/reference-contract.json",
    "docs/decisions/ADR-0007-OCCUPIED-BANDWIDTH-SEMANTICS.md",
    "docs/interfaces/OCCUPIED_BANDWIDTH_CONTRACT.md",
    "algorithms/parameters/obw99.py",
    "algorithms/parameters/obw99_evaluation.py",
    "algorithms/parameters/obw99_reference.py",
    "scripts/generate_phase04d1_reference.py",
    "scripts/lock_phase04d1_evaluation.py",
    "scripts/lock_phase04d1_method.py",
    "scripts/run_phase04d1_evaluation.py",
    "scripts/verify_phase04d1.py",
    "results/evidence/phase04d1/golden-obw99.json",
    "results/evidence/phase04d1/obw99-binding-results.json",
    "results/evidence/phase04d1/obw99-comparison.json",
    "results/evidence/phase04d1/obw99-oos-results.json",
    "results/evidence/phase04d1/verification-summary.json",
    "tests/test_phase04d1_evaluation.py",
    "tests/test_phase04d1_estimator.py",
    "tests/test_phase04d1_method_lock.py",
    "tests/test_phase04d1_reference.py",
    "tests/test_phase04d1_verifier.py",
)

APPROVED_PHASE04_E1_FILES = (
    "datasets/fixtures/phase04e1/acceptance-gates.json",
    "datasets/fixtures/phase04e1/operator-scenes.json",
    "datasets/fixtures/phase04e1/method-lock.json",
    "docs/decisions/ADR-0008-OPERATOR-ASSISTED-PARAMETERS.md",
    "docs/interfaces/OPERATOR_ASSISTED_PARAMETER_CONTRACT.md",
    "algorithms/parameters/operator_assisted.py",
    "algorithms/parameters/operator_classification.py",
    "algorithms/parameters/operator_evaluation.py",
    "algorithms/parameters/operator_reference.py",
    "scripts/generate_phase04e1_reference.py",
    "scripts/lock_phase04e1_method.py",
    "scripts/run_phase04e1_evaluation.py",
    "scripts/verify_phase04e1.py",
    "scripts/render_phase04e1_ui.py",
    "tests/test_phase04e1_algorithms.py",
    "tests/test_phase04e1_evaluation.py",
    "tests/test_phase04e1_profile.py",
    "tests/test_operator_analysis.py",
    "tests/test_phase04e1_verifier.py",
    "results/evidence/phase04e1/golden-parameters.json",
    "results/evidence/phase04e1/binding-results.json",
    "results/evidence/phase04e1/oos-results.json",
    "results/evidence/phase04e1/parameter-comparison.json",
    "results/evidence/phase04e1/verification-summary.json",
    "results/evidence/phase04e1/visual-summary.json",
    "results/evidence/phase04e1/invalid-protocol-run1/binding-results.json",
    "results/evidence/phase04e1/invalid-protocol-run1/oos-results.json",
    "results/evidence/phase04e1/invalid-protocol-run1/parameter-comparison.json",
    "results/evidence/phase04e1/invalid-protocol-run1/golden-parameters.json",
    "results/evidence/phase04e1/invalid-protocol-run1/verification-summary.json",
    "results/evidence/phase04e1/invalid-protocol-run1/method-lock.json",
    "results/evidence/phase04e1/invalid-protocol-run1/invalid-run-manifest.json",
    "results/evidence/phase04e1/empty-1280x720.png",
    "results/evidence/phase04e1/loading-1366x768.png",
    "results/evidence/phase04e1/no-detection-1920x1080.png",
    "results/evidence/phase04e1/tentative-1366x768.png",
    "results/evidence/phase04e1/confirmed-selected-1366x768.png",
    "results/evidence/phase04e1/auto-span-1280x720.png",
    "results/evidence/phase04e1/operator-span-1366x768.png",
    "results/evidence/phase04e1/fields-disabled-1920x1080.png",
    "results/evidence/phase04e1/validation-unavailable-1366x768.png",
    "results/evidence/phase04e1/uncertain-1366x768.png",
    "results/evidence/phase04e1/unmeasured-1280x720.png",
    "results/evidence/phase04e1/warning-1366x768.png",
    "results/evidence/phase04e1/error-1366x768.png",
    "results/evidence/phase04e1/multiple-events-1920x1080.png",
    "results/evidence/phase04e1/scale150-1920x1080.png",
)

PHASE04_E1_SUCCESS_ONLY_FILES = (
    "profiles/phase04e1/operation-default.json",
)

APPROVED_PHASE04_F1_FILES = (
    "algorithms/parameters/f1_evaluation.py",
    "algorithms/parameters/f1_development.py",
    "algorithms/parameters/f1_domain.py",
    "algorithms/parameters/f1_estimator.py",
    "datasets/fixtures/phase04f1/acceptance-gates.json",
    "datasets/fixtures/phase04f1/development-scenes.json",
    "datasets/fixtures/phase04f1/domain-model.json",
    "datasets/fixtures/phase04f1/evaluation-commitments.json",
    "datasets/fixtures/phase04f1/evaluation-runner-lock.json",
    "datasets/fixtures/phase04f1/evaluation-seeds.json",
    "datasets/fixtures/phase04f1/method-lock.json",
    "datasets/fixtures/phase04f1/protocol-lock.json",
    "docs/interfaces/PHASE04_F1_PARAMETER_CONTRACT.md",
    "docs/plans/PHASE04_RECOVERY_PLAN.md",
    "docs/reviews/PHASE04_PARAMETER_AUDIT.md",
    "results/evidence/phase04f1/f1a-verification.json",
    "results/evidence/phase04f1/f1b-verification.json",
    "results/evidence/phase04f1/development-results.json",
    "results/evidence/phase04f1/binding-results.json",
    "results/evidence/phase04f1/f1d-run-started.json",
    "results/evidence/phase04f1/f1d-verification.json",
    "results/evidence/phase04f1/oos-results.json",
    "results/evidence/phase04f1/parameter-comparison.json",
    "scripts/develop_phase04f1_domain.py",
    "scripts/lock_phase04f1_evaluation_runner.py",
    "scripts/lock_phase04f1_method.py",
    "scripts/reveal_phase04f1_seeds.py",
    "scripts/run_phase04f1_evaluation.py",
    "scripts/verify_phase04f1_evaluation.py",
    "scripts/verify_phase04f1_development.py",
    "scripts/verify_phase04f1_protocol.py",
    "tests/test_phase04_relocation.py",
    "tests/test_phase04f1_protocol.py",
    "tests/test_phase04f1_development.py",
    "tests/test_phase04f1_estimator.py",
    "tests/test_phase04f1_evaluation_runner.py",
    "tests/test_phase04f1_method_lock.py",
    "verification/__init__.py",
    "verification/phase04-source-relocation.json",
    "verification/phase04_relocation.py",
)

APPROVED_PHASE04_F2_FILES = (
    "algorithms/parameters/f2_development.py",
    "algorithms/parameters/f2_domain.py",
    "algorithms/parameters/f2_estimator.py",
    "algorithms/parameters/f2_evaluation.py",
    "datasets/fixtures/phase04f2/acceptance-gates.json",
    "datasets/fixtures/phase04f2/development-catalog.json",
    "datasets/fixtures/phase04f2/domain-model-v3.json",
    "datasets/fixtures/phase04f2/evaluation-runner-lock-v3.json",
    "datasets/fixtures/phase04f2/evaluation-seeds.json",
    "datasets/fixtures/phase04f2/evaluation-commitments.json",
    "datasets/fixtures/phase04f2/method-lock-v3.json",
    "datasets/fixtures/phase04f2/protocol-lock.json",
    "docs/interfaces/PHASE04_F2_PARAMETER_CONTRACT.md",
    "docs/plans/PHASE04_F2_RECOVERY_PLAN.md",
    "docs/reviews/PHASE04_F2A_FAILURE_ANALYSIS.md",
    "docs/reviews/PHASE04_F2C_METHOD_DEVELOPMENT.md",
    "docs/reviews/PHASE04_F2D_EVALUATION.md",
    "results/evidence/phase04f2/binding-results-v3.json",
    "results/evidence/phase04f2/carrier-threshold-analysis-v3.json",
    "results/evidence/phase04f2/development-results-v3.json",
    "results/evidence/phase04f2/f2a-analysis.json",
    "results/evidence/phase04f2/f2b-verification.json",
    "results/evidence/phase04f2/f2d-run-started.json",
    "results/evidence/phase04f2/f2d-verification.json",
    "results/evidence/phase04f2/obw-ablation-v3.json",
    "results/evidence/phase04f2/oos-results-v3.json",
    "results/evidence/phase04f2/parameter-comparison-v3.json",
    "scripts/develop_phase04f2_carrier.py",
    "scripts/develop_phase04f2_domain.py",
    "scripts/develop_phase04f2_obw.py",
    "scripts/lock_phase04f2_evaluation_runner.py",
    "scripts/lock_phase04f2_method.py",
    "scripts/lock_phase04f2_protocol.py",
    "scripts/prepare_phase04f2_protocol.py",
    "scripts/reveal_phase04f2_seeds.py",
    "scripts/run_phase04f2_evaluation.py",
    "scripts/verify_phase04f2a.py",
    "scripts/verify_phase04f2_protocol.py",
    "scripts/verify_phase04f2_development.py",
    "scripts/verify_phase04f2_evaluation.py",
    "tests/test_phase04f2a_analysis.py",
    "tests/test_phase04f2_estimator.py",
    "tests/test_phase04f2_evaluation_runner.py",
    "tests/test_phase04f2_method_lock.py",
    "tests/test_phase04f2_protocol.py",
    "verification/phase04f2_analysis.py",
    "verification/phase04f2_scoring.py",
)

APPROVED_PHASE04_F3_FILES = (
    "algorithms/parameters/f3_development.py",
    "algorithms/parameters/f3_domain.py",
    "algorithms/parameters/f3_estimator.py",
    "algorithms/parameters/f3_evaluation.py",
    "datasets/fixtures/phase04f3/acceptance-gates.json",
    "datasets/fixtures/phase04f3/development-catalog.json",
    "datasets/fixtures/phase04f3/domain-model-v4.json",
    "datasets/fixtures/phase04f3/evaluation-commitments.json",
    "datasets/fixtures/phase04f3/evaluation-runner-lock-v4.json",
    "datasets/fixtures/phase04f3/evaluation-seeds.json",
    "datasets/fixtures/phase04f3/method-lock-v4.json",
    "datasets/fixtures/phase04f3/protocol-lock.json",
    "docs/interfaces/PHASE04_F3_PARAMETER_CONTRACT.md",
    "docs/plans/PHASE04_F3_RECOVERY_PLAN.md",
    "docs/reviews/PHASE04_F3A_FAILURE_ANALYSIS.md",
    "docs/reviews/PHASE04_F3C_METHOD_DEVELOPMENT.md",
    "docs/reviews/PHASE04_F3D_EVALUATION.md",
    "results/evidence/phase04f3/binding-results-v4.json",
    "results/evidence/phase04f3/carrier-analysis-v4.json",
    "results/evidence/phase04f3/development-results-v4.json",
    "results/evidence/phase04f3/f3a-analysis.json",
    "results/evidence/phase04f3/f3b-verification.json",
    "results/evidence/phase04f3/f3d-run-started.json",
    "results/evidence/phase04f3/f3d-verification.json",
    "results/evidence/phase04f3/oos-results-v4.json",
    "results/evidence/phase04f3/parameter-comparison-v4.json",
    "scripts/develop_phase04f3_carrier.py",
    "scripts/develop_phase04f3_domain.py",
    "scripts/lock_phase04f3_evaluation_runner.py",
    "scripts/lock_phase04f3_method.py",
    "scripts/lock_phase04f3_protocol.py",
    "scripts/prepare_phase04f3_protocol.py",
    "scripts/reveal_phase04f3_seeds.py",
    "scripts/run_phase04f3_evaluation.py",
    "scripts/verify_phase04f3_development.py",
    "scripts/verify_phase04f3_evaluation.py",
    "scripts/verify_phase04f3_protocol.py",
    "scripts/verify_phase04f3a.py",
    "tests/test_phase04f3_development.py",
    "tests/test_phase04f3_estimator.py",
    "tests/test_phase04f3_evaluation_runner.py",
    "tests/test_phase04f3_method_lock.py",
    "tests/test_phase04f3_protocol.py",
    "tests/test_phase04f3a_analysis.py",
    "verification/phase04f3_analysis.py",
    "verification/phase04f3_scoring.py",
)

APPROVED_PHASE04_F4_FILES = (
    "algorithms/parameters/f4_development.py",
    "algorithms/parameters/f4_domain.py",
    "algorithms/parameters/f4_estimator.py",
    "algorithms/parameters/f4_evaluation.py",
    "datasets/fixtures/phase04f4/acceptance-gates.json",
    "datasets/fixtures/phase04f4/development-catalog.json",
    "datasets/fixtures/phase04f4/domain-model-v5.json",
    "datasets/fixtures/phase04f4/evaluation-commitments.json",
    "datasets/fixtures/phase04f4/evaluation-seeds.json",
    "datasets/fixtures/phase04f4/evaluation-runner-lock-v5.json",
    "datasets/fixtures/phase04f4/method-lock-v5.json",
    "datasets/fixtures/phase04f4/protocol-lock.json",
    "results/evidence/phase04f4/binding-results-v5.json",
    "results/evidence/phase04f4/carrier-analysis-v5.json",
    "results/evidence/phase04f4/development-results-v5.json",
    "results/evidence/phase04f4/f4a-analysis.json",
    "results/evidence/phase04f4/f4b-verification.json",
    "results/evidence/phase04f4/f4d-run-started.json",
    "results/evidence/phase04f4/f4d-verification.json",
    "results/evidence/phase04f4/oos-results-v5.json",
    "results/evidence/phase04f4/parameter-comparison-v5.json",
    "scripts/develop_phase04f4_carrier.py",
    "scripts/develop_phase04f4_domain.py",
    "scripts/lock_phase04f4_evaluation_runner.py",
    "scripts/lock_phase04f4_method.py",
    "scripts/lock_phase04f4_protocol.py",
    "scripts/prepare_phase04f4_protocol.py",
    "scripts/reveal_phase04f4_seeds.py",
    "scripts/run_phase04f4_evaluation.py",
    "scripts/verify_phase04f4_development.py",
    "scripts/verify_phase04f4_evaluation.py",
    "scripts/verify_phase04f4a.py",
    "scripts/verify_phase04f4_protocol.py",
    "tests/test_phase04f4_development.py",
    "tests/test_phase04f4_estimator.py",
    "tests/test_phase04f4_evaluation_runner.py",
    "tests/test_phase04f4_method_lock.py",
    "tests/test_phase04f4a_analysis.py",
    "tests/test_phase04f4_protocol.py",
    "verification/phase04f4_analysis.py",
    "verification/phase04f4_scoring.py",
)

APPROVED_PHASE04_F5_FILES = (
    "algorithms/parameters/f5_development.py",
    "algorithms/parameters/f5_estimator.py",
    "algorithms/parameters/f5_evaluation.py",
    "datasets/fixtures/phase04f5/acceptance-gates.json",
    "datasets/fixtures/phase04f5/development-catalog.json",
    "datasets/fixtures/phase04f5/evaluation-runner-lock-v6.json",
    "datasets/fixtures/phase04f5/evaluation-commitments.json",
    "datasets/fixtures/phase04f5/evaluation-seeds.json",
    "datasets/fixtures/phase04f5/method-lock-v6.json",
    "datasets/fixtures/phase04f5/protocol-lock.json",
    "docs/plans/PHASE04_F5_RECOVERY_PLAN.md",
    "results/evidence/phase04f5/carrier-analysis-v6.json",
    "results/evidence/phase04f5/binding-results-v6.json",
    "results/evidence/phase04f5/development-results-v6.json",
    "results/evidence/phase04f5/f5a-analysis.json",
    "results/evidence/phase04f5/f5b-verification.json",
    "results/evidence/phase04f5/f5d-run-started.json",
    "results/evidence/phase04f5/f5d-verification.json",
    "results/evidence/phase04f5/f5e-verification.json",
    "results/evidence/phase04f5/obw-candidate-analysis-v6.json",
    "results/evidence/phase04f5/obw-edge-expansion-candidates-v6.json",
    "results/evidence/phase04f5/obw-structural-candidates-v6.json",
    "results/evidence/phase04f5/obw-structure-diagnostics-v6.json",
    "results/evidence/phase04f5/obw-temporal-candidates-v6.json",
    "results/evidence/phase04f5/oos-results-v6.json",
    "results/evidence/phase04f5/parameter-comparison-v6.json",
    "profiles/phase04f5/operation-default.json",
    "scripts/analyze_phase04f5_obw_structure.py",
    "scripts/develop_phase04f5_carrier.py",
    "scripts/develop_phase04f5_obw.py",
    "scripts/develop_phase04f5_structural_obw.py",
    "scripts/establish_phase04f5_product_profile.py",
    "scripts/lock_phase04f5_evaluation_runner.py",
    "scripts/lock_phase04f5_method.py",
    "scripts/lock_phase04f5_protocol.py",
    "scripts/prepare_phase04f5_protocol.py",
    "scripts/reveal_phase04f5_seeds.py",
    "scripts/run_phase04f5_evaluation.py",
    "scripts/verify_phase04f5a.py",
    "scripts/verify_phase04f5_development.py",
    "scripts/verify_phase04f5_evaluation.py",
    "scripts/verify_phase04f5_product_integration.py",
    "scripts/verify_phase04f5_protocol.py",
    "tests/test_phase04f5_development.py",
    "tests/test_phase04f5_evaluation_runner.py",
    "tests/test_phase04f5_method_lock.py",
    "tests/test_phase04f5a_analysis.py",
    "tests/test_phase04f5_obw_candidates.py",
    "tests/test_phase04f5_protocol.py",
    "tests/test_phase04f5_product_profile.py",
    "verification/phase04f5_analysis.py",
    "verification/phase04f5_scoring.py",
)

APPROVED_PHASE04_FILES = (
    APPROVED_PHASE04_BASE_FILES
    + PHASE04_SUCCESS_ONLY_FILES
    + APPROVED_PHASE04_D1_FILES
    + APPROVED_PHASE04_E1_FILES
    + PHASE04_E1_SUCCESS_ONLY_FILES
    + APPROVED_PHASE04_F1_FILES
    + APPROVED_PHASE04_F2_FILES
    + APPROVED_PHASE04_F3_FILES
    + APPROVED_PHASE04_F4_FILES
    + APPROVED_PHASE04_F5_FILES
)

APPROVED_PHASE08A_FILES = (
    "docs/decisions/ADR-0009-HACKRF-RX-HOST-PREPARATION.md",
    "docs/interfaces/HACKRF_RX_HOST_CONTRACT.md",
    "platforms/acquisition/__init__.py",
    "platforms/acquisition/contracts.py",
    "platforms/acquisition/hackrf.py",
    "platforms/acquisition/process.py",
    "platforms/acquisition/source.py",
    "scripts/render_phase08a_ui.py",
    "scripts/verify_phase08a.py",
    "tests/test_hackrf_acquisition.py",
    "tests/test_operator_hackrf.py",
    "tests/test_phase08a_verifier.py",
    "results/evidence/phase08a/verification-summary.json",
    "results/evidence/phase08a/visual-summary.json",
    "results/evidence/phase08a/tools-missing-1366x768.png",
    "results/evidence/phase08a/device-missing-1366x768.png",
    "results/evidence/phase08a/deterministic-source-1366x768.png",
    "results/evidence/phase08a/cli-error-1366x768.png",
    "results/evidence/phase08a/tools-missing-1920x1080-scale150.png",
)

APPROVED_PHASE05_FILES = (
    "datasets/fixtures/phase05/am-tone-ci8.sigmf-data",
    "datasets/fixtures/phase05/am-tone-ci8.sigmf-meta",
    "datasets/fixtures/phase05/fixture-manifest.json",
    "datasets/fixtures/phase05/nfm-tone-ci8.sigmf-data",
    "datasets/fixtures/phase05/nfm-tone-ci8.sigmf-meta",
    "datasets/fixtures/phase05/noise-only-ci8.sigmf-data",
    "datasets/fixtures/phase05/noise-only-ci8.sigmf-meta",
    "docs/decisions/ADR-0010-RECORDED-ANALOG-MONITORING.md",
    "docs/interfaces/ANALOG_MONITORING_CONTRACT.md",
    "app/operator_console/audio_playback.py",
    "algorithms/monitoring/__init__.py",
    "algorithms/monitoring/dsp.py",
    "algorithms/monitoring/evaluation.py",
    "algorithms/monitoring/fixtures.py",
    "algorithms/monitoring/models.py",
    "results/evidence/phase05/am-ready-1366x768.png",
    "results/evidence/phase05/am-ready-1920x1080-scale150.png",
    "results/evidence/phase05/audio-unavailable-1366x768.png",
    "results/evidence/phase05/fixture-manifest.json",
    "results/evidence/phase05/golden-monitoring.json",
    "results/evidence/phase05/nfm-ready-1366x768.png",
    "results/evidence/phase05/noise-no-event-1366x768.png",
    "results/evidence/phase05/no-source-1280x720.png",
    "results/evidence/phase05/verification-summary.json",
    "results/evidence/phase05/visual-summary.json",
    "scripts/generate_phase05_fixtures.py",
    "scripts/render_phase05_ui.py",
    "scripts/verify_phase05.py",
    "tests/test_operator_listening.py",
    "tests/test_phase05_fixtures.py",
    "tests/test_phase05_monitoring.py",
    "tests/test_phase05_verifier.py",
)

APPROVED_PHASE06A_FILES = (
    "datasets/fixtures/phase06a/axis-expected.mem",
    "datasets/fixtures/phase06a/axis-input.hex",
    "datasets/fixtures/phase06a/fixture-manifest.json",
    "datasets/fixtures/phase06a/golden-vectors.json",
    "docs/decisions/ADR-0011-SYSTEMVERILOG-RTL-FOUNDATION.md",
    "docs/interfaces/RTL_FRAME_STATS_CONTRACT.md",
    "algorithms/rtl/__init__.py",
    "algorithms/rtl/frame_stats.py",
    "algorithms/rtl/vectors.py",
    "results/evidence/phase06a/fixed-point-contract.json",
    "results/evidence/phase06a/golden-frame-results.json",
    "results/evidence/phase06a/python-model-result.json",
    "results/evidence/phase06a/rtl-simulation.json",
    "results/evidence/phase06a/toolchain.json",
    "results/evidence/phase06a/verification-summary.json",
    "algorithms/fpga/phase06a/rtl/axis_ci8_frame_stats.sv",
    "algorithms/fpga/phase06a/rtl/axis_skid_buffer.sv",
    "algorithms/fpga/phase06a/rtl/phase06a_pkg.sv",
    "algorithms/fpga/phase06a/tb/tb_axis_ci8_frame_stats.sv",
    "scripts/generate_phase06a_vectors.py",
    "scripts/verify_phase06a.py",
    "tests/test_phase06a_model.py",
    "tests/test_phase06a_vectors.py",
    "tests/test_phase06a_verifier.py",
)

APPROVED_PHASE06B_FILES = (
    "datasets/fixtures/phase06b/axis-expected.mem",
    "datasets/fixtures/phase06b/axis-input.hex",
    "datasets/fixtures/phase06b/fixture-manifest.json",
    "datasets/fixtures/phase06b/golden-vectors.json",
    "datasets/fixtures/phase06b/hann-coefficients.mem",
    "docs/decisions/ADR-0012-FIXED-POINT-HANN-FFT-BOUNDARY.md",
    "docs/interfaces/RTL_HANN_WINDOW_CONTRACT.md",
    "algorithms/rtl/hann_vectors.py",
    "algorithms/rtl/hann_window.py",
    "results/evidence/phase06b/fixed-point-contract.json",
    "results/evidence/phase06b/golden-frame-results.json",
    "results/evidence/phase06b/latency.json",
    "results/evidence/phase06b/python-model-result.json",
    "results/evidence/phase06b/rtl-simulation.json",
    "results/evidence/phase06b/toolchain.json",
    "results/evidence/phase06b/verification-summary.json",
    "results/evidence/phase06b/word-length-study.json",
    "algorithms/fpga/phase06b/rtl/axis_hann_window.sv",
    "algorithms/fpga/phase06b/rtl/phase06b_pkg.sv",
    "algorithms/fpga/phase06b/tb/tb_axis_hann_window.sv",
    "scripts/generate_phase06b_vectors.py",
    "scripts/verify_phase06b.py",
    "tests/test_phase06b_model.py",
    "tests/test_phase06b_vectors.py",
    "tests/test_phase06b_verifier.py",
)

APPROVED_PHASE06C_FILES = (
    "datasets/fixtures/phase06c/axis-input.mem",
    "datasets/fixtures/phase06c/fft-expected.mem",
    "datasets/fixtures/phase06c/fixture-manifest.json",
    "datasets/fixtures/phase06c/golden-vectors.json",
    "datasets/fixtures/phase06c/stub-expected.mem",
    "docs/decisions/ADR-0013-FFT-ARCHITECTURE-AND-AMD-IP-BOUNDARY.md",
    "docs/interfaces/RTL_FFT_INTERFACE_CONTRACT.md",
    "algorithms/rtl/fft_model.py",
    "algorithms/rtl/fft_vectors.py",
    "results/evidence/phase06c/architecture-decision-study.json",
    "results/evidence/phase06c/fixed-point-contract.json",
    "results/evidence/phase06c/latency.json",
    "results/evidence/phase06c/numerical-study.json",
    "results/evidence/phase06c/python-model-result.json",
    "results/evidence/phase06c/toolchain.json",
    "results/evidence/phase06c/verification-summary.json",
    "results/evidence/phase06c/wrapper-simulation.json",
    "algorithms/fpga/phase06c/rtl/axis_fft_wrapper.sv",
    "algorithms/fpga/phase06c/rtl/phase06c_pkg.sv",
    "algorithms/fpga/phase06c/tb/fft_ip_transport_stub.sv",
    "algorithms/fpga/phase06c/tb/tb_axis_fft_wrapper.sv",
    "scripts/generate_phase06c_vectors.py",
    "scripts/verify_phase06c.py",
    "tests/test_phase06c_model.py",
    "tests/test_phase06c_vectors.py",
    "tests/test_phase06c_verifier.py",
)

APPROVED_PHASE06D_PLANNING_FILES = (
    "docs/decisions/ADR-0014-PHASE06D-VENDOR-VERIFICATION-GATE.md",
    "results/evidence/phase06d/toolchain-gate.json",
)

APPROVED_PHASE06D_FILES = APPROVED_PHASE06D_PLANNING_FILES + (
    "datasets/fixtures/phase06d/axis-input.mem",
    "datasets/fixtures/phase06d/cmodel-expected.mem",
    "datasets/fixtures/phase06d/fixture-manifest.json",
    "datasets/fixtures/phase06d/golden-vectors.json",
    "docs/interfaces/RTL_AMD_FFT_BINDING_CONTRACT.md",
    "algorithms/rtl/amd_xfft_cmodel_driver.cpp",
    "algorithms/rtl/phase06d_vectors.py",
    "results/evidence/phase06d/cmodel-result.json",
    "results/evidence/phase06d/fixed-point-contract.json",
    "results/evidence/phase06d/generated-ip.json",
    "results/evidence/phase06d/golden-equivalence.json",
    "results/evidence/phase06d/interface-events.json",
    "results/evidence/phase06d/latency.json",
    "results/evidence/phase06d/numerical-characterization.json",
    "results/evidence/phase06d/throughput.json",
    "results/evidence/phase06d/toolchain.json",
    "results/evidence/phase06d/verification-summary.json",
    "results/evidence/phase06d/xsim-result.json",
    "algorithms/fpga/phase06d/ip/phase06d_fft_4096/phase06d_fft_4096.xci",
    "algorithms/fpga/phase06d/rtl/amd_xfft_adapter.sv",
    "algorithms/fpga/phase06d/tb/tb_phase06d_fft_vendor.sv",
    "scripts/generate_phase06d_ip.tcl",
    "scripts/generate_phase06d_vectors.py",
    "scripts/phase06d_ip_config.tcl",
    "scripts/run_phase06d_xsim.tcl",
    "scripts/verify_phase06d.py",
    "tests/test_phase06d_vectors.py",
    "tests/test_phase06d_verifier.py",
)

APPROVED_PHASE06E_FILES = (
    "docs/decisions/ADR-0015-PHASE06E-VIVADO-IMPLEMENTATION-GATE.md",
    "docs/interfaces/RTL_VIVADO_IMPLEMENTATION_CONTRACT.md",
    "results/evidence/phase06e/implementation.json",
    "results/evidence/phase06e/resource-utilization.json",
    "results/evidence/phase06e/rtl-boundary-test.json",
    "results/evidence/phase06e/source-manifest.json",
    "results/evidence/phase06e/synthesis.json",
    "results/evidence/phase06e/timing.json",
    "results/evidence/phase06e/toolchain.json",
    "results/evidence/phase06e/verification-summary.json",
    "results/evidence/phase06e/warnings.json",
    "algorithms/fpga/phase06e/constraints/phase06e_fft_100mhz.xdc",
    "algorithms/fpga/phase06e/rtl/phase06e_fft_implementation_top.sv",
    "algorithms/fpga/phase06e/tb/tb_phase06e_axis_input_register_slice.sv",
    "scripts/run_phase06e_vivado.tcl",
    "scripts/verify_phase06e.py",
    "tests/test_phase06e_verifier.py",
)

APPROVED_PHASE06F_FILES = (
    "datasets/fixtures/phase06f/edge-expected.mem",
    "datasets/fixtures/phase06f/edge-input.mem",
    "datasets/fixtures/phase06f/fixture-manifest.json",
    "datasets/fixtures/phase06f/golden-vectors.json",
    "datasets/fixtures/phase06f/real-power-expected.mem",
    "docs/decisions/ADR-0016-PHASE06F-FFT-LINEAR-POWER.md",
    "docs/interfaces/RTL_FFT_POWER_CONTRACT.md",
    "algorithms/rtl/fft_power.py",
    "algorithms/rtl/power_vectors.py",
    "results/evidence/phase06f/fixed-point-contract.json",
    "results/evidence/phase06f/integration.json",
    "results/evidence/phase06f/latency.json",
    "results/evidence/phase06f/python-model-result.json",
    "results/evidence/phase06f/rtl-simulation.json",
    "results/evidence/phase06f/source-manifest.json",
    "results/evidence/phase06f/toolchain.json",
    "results/evidence/phase06f/verification-summary.json",
    "algorithms/fpga/phase06f/rtl/axis_fft_linear_power.sv",
    "algorithms/fpga/phase06f/tb/tb_axis_fft_linear_power.sv",
    "scripts/generate_phase06f_vectors.py",
    "scripts/verify_phase06f.py",
    "tests/test_phase06f_model.py",
    "tests/test_phase06f_vectors.py",
    "tests/test_phase06f_verifier.py",
)

APPROVED_PHASE06G_FILES = (
    "datasets/fixtures/phase06g/axis-power-input.mem",
    "datasets/fixtures/phase06g/detector-expected.mem",
    "datasets/fixtures/phase06g/fixture-manifest.json",
    "datasets/fixtures/phase06g/golden-vectors.json",
    "docs/decisions/ADR-0017-PHASE06G-REGIONAL-DETECTOR.md",
    "docs/decisions/ADR-0018-UI-PERFORMANCE-BASELINE-POLICY.md",
    "docs/interfaces/RTL_REGIONAL_DETECTOR_CONTRACT.md",
    "algorithms/rtl/detector_vectors.py",
    "algorithms/rtl/regional_detector.py",
    "results/evidence/phase06g/algorithm-contract.json",
    "results/evidence/phase06g/architecture-study.json",
    "results/evidence/phase06g/coefficient-study.json",
    "results/evidence/phase06g/integration.json",
    "results/evidence/phase06g/latency.json",
    "results/evidence/phase06g/phase03-comparison.json",
    "results/evidence/phase06g/python-model-result.json",
    "results/evidence/phase06g/resource-feasibility.json",
    "results/evidence/phase06g/rtl-simulation.json",
    "results/evidence/phase06g/source-manifest.json",
    "results/evidence/phase06g/toolchain.json",
    "results/evidence/phase06g/ui-performance-characterization.json",
    "results/evidence/phase06g/verification-summary.json",
    "algorithms/fpga/phase06g/rtl/axis_regional_detector.sv",
    "algorithms/fpga/phase06g/rtl/phase06g_detector_synthesis_top.sv",
    "algorithms/fpga/phase06g/rtl/phase06g_pkg.sv",
    "algorithms/fpga/phase06g/tb/tb_axis_regional_detector.sv",
    "scripts/generate_phase06g_vectors.py",
    "scripts/run_phase06g_synthesis.tcl",
    "scripts/verify_phase06g.py",
    "scripts/verify_ui_performance.py",
    "tests/test_phase06g_model.py",
    "tests/test_phase06g_vectors.py",
    "tests/test_phase06g_verifier.py",
    "tests/test_ui_performance_policy.py",
)

APPROVED_PHASE06H_FILES = (
    "datasets/fixtures/phase06h/axis-detector-input.mem",
    "datasets/fixtures/phase06h/candidate-expected.mem",
    "datasets/fixtures/phase06h/fixture-manifest.json",
    "datasets/fixtures/phase06h/golden-vectors.json",
    "docs/decisions/ADR-0019-PHASE06H-CANDIDATE-GROUPING-BOUNDARY.md",
    "docs/interfaces/RTL_CANDIDATE_GROUPING_CONTRACT.md",
    "algorithms/rtl/candidate_grouping.py",
    "algorithms/rtl/candidate_vectors.py",
    "results/evidence/phase06h/algorithm-contract.json",
    "results/evidence/phase06h/architecture.json",
    "results/evidence/phase06h/authoritative-comparison.json",
    "results/evidence/phase06h/integration.json",
    "results/evidence/phase06h/latency-throughput.json",
    "results/evidence/phase06h/resource-feasibility.json",
    "results/evidence/phase06h/rtl-simulation.json",
    "results/evidence/phase06h/source-manifest.json",
    "results/evidence/phase06h/toolchain.json",
    "results/evidence/phase06h/verification-summary.json",
    "algorithms/fpga/phase06h/rtl/axis_candidate_grouping.sv",
    "algorithms/fpga/phase06h/rtl/phase06h_candidate_ram.sv",
    "algorithms/fpga/phase06h/rtl/phase06h_candidate_synthesis_top.sv",
    "algorithms/fpga/phase06h/rtl/phase06h_pkg.sv",
    "algorithms/fpga/phase06h/tb/tb_axis_candidate_grouping.sv",
    "scripts/generate_phase06h_vectors.py",
    "scripts/run_phase06h_synthesis.tcl",
    "scripts/verify_phase06h.py",
    "tests/test_phase06h_model.py",
    "tests/test_phase06h_vectors.py",
    "tests/test_phase06h_verifier.py",
)

APPROVED_PHASE06I_FILES = (
    "datasets/fixtures/phase06i/candidate-axis-input.mem",
    "datasets/fixtures/phase06i/fixture-manifest.json",
    "datasets/fixtures/phase06i/golden-vectors.json",
    "datasets/fixtures/phase06i/transport-axis64-expected.mem",
    "datasets/fixtures/phase06i/transport-packets.bin",
    "docs/decisions/ADR-0020-PHASE06I-PL-PS-CANDIDATE-TRANSPORT.md",
    "docs/interfaces/PL_PS_CANDIDATE_TRANSPORT_ABI.md",
    "algorithms/ps/__init__.py",
    "algorithms/ps/candidate_transport.py",
    "algorithms/ps/transport_vectors.py",
    "platforms/embedded/README.md",
    "platforms/embedded/phase06i/include/phase06i_transport_abi.h",
    "platforms/embedded/phase06i/src/phase06i_decode.c",
    "results/evidence/phase06i/abi-contract.json",
    "results/evidence/phase06i/architecture.json",
    "results/evidence/phase06i/physical-parameter-boundary.json",
    "results/evidence/phase06i/python-abi-result.json",
    "results/evidence/phase06i/rtl-simulation.json",
    "results/evidence/phase06i/source-manifest.json",
    "results/evidence/phase06i/temporal-boundary.json",
    "results/evidence/phase06i/toolchain.json",
    "results/evidence/phase06i/verification-summary.json",
    "algorithms/fpga/phase06i/rtl/axis_candidate_packetizer.sv",
    "algorithms/fpga/phase06i/rtl/phase06i_pkg.sv",
    "algorithms/fpga/phase06i/tb/tb_axis_candidate_packetizer.sv",
    "scripts/generate_phase06i_vectors.py",
    "scripts/verify_phase06i.py",
    "tests/test_phase06i_transport.py",
    "tests/test_phase06i_vectors.py",
    "tests/test_phase06i_verifier.py",
)

APPROVED_TEST_INFRASTRUCTURE_FILES = (
    "docs/testing/QT_NATIVE_TEST_POLICY.md",
    "scripts/verify_qt_lifecycle.py",
    "tests/qt_test_support.py",
    "tests/test_qt_test_support.py",
)

APPROVED_PHASE06J_FILES = (
    "datasets/fixtures/phase06j/fixture-manifest.json",
    "datasets/fixtures/phase06j/golden-sequences.json",
    "datasets/fixtures/phase06j/packets.bin",
    "docs/decisions/ADR-0021-PHASE06J-PS-TEMPORAL-CONFIRMATION.md",
    "docs/interfaces/PS_TEMPORAL_CANDIDATE_CONTRACT.md",
    "platforms/embedded/phase06j/include/phase06j_temporal.h",
    "platforms/embedded/phase06j/src/phase06j_temporal.c",
    "algorithms/ps/temporal_confirmation.py",
    "algorithms/ps/temporal_vectors.py",
    "results/evidence/phase06j/algorithm-contract.json",
    "results/evidence/phase06j/golden-equivalence.json",
    "results/evidence/phase06j/host-build.json",
    "results/evidence/phase06j/physical-boundary.json",
    "results/evidence/phase06j/source-manifest.json",
    "results/evidence/phase06j/system-limitations.json",
    "results/evidence/phase06j/toolchain.json",
    "results/evidence/phase06j/verification-summary.json",
    "scripts/generate_phase06j_vectors.py",
    "scripts/verify_phase06j.py",
    "tests/test_phase06j_model.py",
    "tests/test_phase06j_vectors.py",
    "tests/test_phase06j_verifier.py",
)

APPROVED_P0_FILES = (
    "config/p0/hackrf_ed_rx.json",
    "datasets/fixtures/p0/README.md",
    "docs/architecture/P0_SYSTEM_ARCHITECTURE.md",
    "docs/architecture/P0_THROUGHPUT.md",
    "docs/decisions/ADR-0022-P0-MANDATORY-EH-CORE.md",
    "docs/interfaces/P0_BANDWIDTH_CONTRACT.md",
    "docs/interfaces/P0_DETECTOR_PROFILE.md",
    "docs/interfaces/P0_FPGA_RUNTIME_CONTRACT.md",
    "docs/interfaces/P0_JUDGE_SEARCH_CONTRACT.md",
    "docs/interfaces/P0_HACKRF_B0_READINESS.md",
    "docs/interfaces/P0_PC_ZEDBOARD_IQ_TRANSPORT.md",
    "docs/learning/AMPLITUDE_DIRECTION_FINDING.md",
    "docs/learning/ANALOG_RADIO_RECEIVER.md",
    "docs/requirements/P0_REQUIREMENT_MATRIX.md",
    "docs/testing/P0_USER_DEMO.md",
    "platforms/acquisition/rx_sources.py",
    "app/operator_console/map_direction.py",
    "app/operator_console/map_providers.py",
    "app/operator_console/pc_location.py",
    "app/operator_console/map_assets/README.md",
    "app/operator_console/map_assets/map.html",
    "app/operator_console/map_assets/licenses/MAPLIBRE-GL-JS-BSD-3-CLAUSE.txt",
    "app/operator_console/map_assets/licenses/PMTILES-BSD-3-CLAUSE.txt",
    "app/operator_console/map_assets/maplibre/maplibre-gl-worker.mjs",
    "app/operator_console/map_assets/maplibre/maplibre-gl.css",
    "app/operator_console/map_assets/maplibre/maplibre-gl.js",
    "app/operator_console/map_assets/maplibre/maplibre-gl.mjs",
    "app/operator_console/map_assets/maplibre/maplibre-gl-shared.mjs",
    "app/operator_console/map_assets/pmtiles/pmtiles.js",
    "app/operator_console/map_assets/styles/competition-style.template.json",
    "platforms/embedded/p0/include/p0_os_cfar.h",
    "platforms/embedded/p0/include/p0_dma_uapi.h",
    "platforms/embedded/p0/petalinux/Makefile",
    "platforms/embedded/p0/petalinux/p0-dma_1.0.bb",
    "platforms/embedded/p0/petalinux/system-user.dtsi",
    "platforms/embedded/p0/src/p0_dma_client.c",
    "platforms/embedded/p0/src/p0_dma_run.c",
    "platforms/embedded/p0/src/p0_os_cfar.c",
    "platforms/embedded/p0/src/p0_os_cfar_run.c",
    "algorithms/et/__init__.py",
    "algorithms/et/deception.py",
    "algorithms/et/mission.py",
    "algorithms/et/waveforms.py",
    "algorithms/p0/__init__.py",
    "algorithms/p0/bandwidth.py",
    "algorithms/p0/detection.py",
    "algorithms/p0/df.py",
    "algorithms/p0/df_fixtures.py",
    "algorithms/p0/field_df.py",
    "algorithms/p0/fixtures.py",
    "algorithms/p0/hackrf_search.py",
    "algorithms/p0/map_direction.py",
    "algorithms/p0/models.py",
    "algorithms/p0/parameters.py",
    "algorithms/p0/search.py",
    "algorithms/p0/temporal.py",
    "algorithms/p0/transport.py",
    "results/evidence/p0/bandwidth-ground-truth.json",
    "results/evidence/p0/closure.json",
    "results/evidence/p0/detector-profile.json",
    "results/evidence/p0/df-golden.json",
    "results/evidence/p0/et-golden.json",
    "results/evidence/p0/judge-workflow.json",
    "results/evidence/p0/hackrf-b0-readiness.json",
    "results/evidence/p0/parameter-golden.json",
    "results/evidence/p0/training-functional-acceptance-v1.json",
    "results/evidence/p0/petalinux-dma-length16-build.json",
    "results/evidence/p0/vivado-100mhz-attempt.json",
    "results/evidence/p0/vivado-50mhz.json",
    "algorithms/fpga/p0/rtl/p0_dsp_runtime_bd.v",
    "algorithms/fpga/p0/rtl/p0_dsp_runtime_top.sv",
    "scripts/create_p0_vivado_project.tcl",
    "scripts/check_hackrf_rx_ready.py",
    "scripts/run_p0_demo.py",
    "scripts/run_p0_vivado.tcl",
    "scripts/verify_p0_algorithms.py",
    "scripts/verify_p0_bandwidth.py",
    "scripts/verify_p0_detector_profile.py",
    "scripts/verify_p0_df.py",
    "scripts/verify_p0_et.py",
    "scripts/verify_p0_judge_workflow.py",
    "scripts/verify_p0_os_cfar.py",
    "scripts/verify_p0_training_acceptance.py",
    "tests/test_p0_detection_parameters.py",
    "tests/test_p0_df.py",
    "tests/test_p0_field_df.py",
    "tests/test_p0_et.py",
    "tests/test_p0_hackrf_search.py",
    "tests/test_p0_map_direction.py",
    "tests/test_operator_map_direction.py",
    "tests/test_map_providers.py",
    "tests/test_p0_operator.py",
    "tests/test_p0_rx_sources.py",
    "tests/test_p0_search.py",
    "tests/test_p0_transport.py",
    "tests/test_p0_training_acceptance.py",
)

# The ET console extension is explicitly limited to deterministic local models
# and validation metadata.  It is not a phase-completion or RF-TX approval.
APPROVED_ET_OFFLINE_FILES = (
    "docs/decisions/ADR-0023-ET-OFFLINE-TASK-CONSOLE.md",
    "docs/reviews/ET_OFFLINE_ACCEPTANCE_AUDIT.md",
    "algorithms/et/gnss.py",
    "algorithms/et/interleaved.py",
    "algorithms/et/results.py",
    "results/evidence/et-offline/analog-nfm-loopback-1920x1080.png",
    "results/evidence/et-offline/continuous-barrage-1920x1080.png",
    "results/evidence/et-offline/continuous-multiple-1920x1080.png",
    "results/evidence/et-offline/gnss-validation-1920x1080.png",
    "results/evidence/et-offline/interleaved-timeline-1920x1080.png",
    "tests/test_et_offline_models.py",
    "tests/test_operator_et.py",
    "tests/test_p0_et_verifier.py",
)

# APP sağlamlaştırma çalışması mevcut PHASE sırasını ilerletmez.  Bu dosyalar
# yalnız repository/ürün sınırını ve sonraki onay kapılarını tanımlar.
APPROVED_APP_HARDENING_FILES = (
    "algorithms/__init__.py",
    "app/__init__.py",
    "config/app/product-package.json",
    "docs/decisions/ADR-0024-PRODUCT-VERIFICATION-RUNTIME-BOUNDARY.md",
    "docs/decisions/ADR-0025-APPLICATION-ALGORITHM-PLATFORM-BOUNDARIES.md",
    "docs/decisions/ADR-0026-OPERATOR-UI-PRESENTATION-STACK.md",
    "docs/decisions/ADR-0027-OPERATOR-QML-RUNTIME-ARCHITECTURE.md",
    "docs/plans/APP_HARDENING_WORK_PACKAGES.md",
    "docs/reviews/APP_CODE_REVIEW_BASELINE.md",
    "docs/reviews/REPOSITORY_DISPOSITION.md",
    "docs/reviews/UI_REFERENCE_RESEARCH.md",
    "docs/reviews/APP_E_UX_AUDIT.md",
    "docs/reviews/APP_F_RELEASE_UI_REVIEW.md",
    "docs/ux/OPERATOR_TASK_FLOWS.md",
    "docs/ux/OPERATOR_TERMINOLOGY.md",
    "platforms/acquisition/mock.py",
    "platforms/acquisition/search.py",
    "platforms/__init__.py",
    "app/operator_console/laboratory.py",
    "app/operator_console/qml/Main.qml",
    "app/operator_console/quick_application.py",
    "app/operator_console/quick_view_model.py",
    "tests/test_architecture_boundaries.py",
    "tests/test_operator_product_boundary.py",
    "tests/test_app_e_ux_contract.py",
    "tests/test_app_f_quick_product.py",
    "verification/architecture-boundaries.json",
    "verification/app_e/OperatorShell.qml",
    "verification/app_e/README.md",
    "scripts/verify_app_e_ui_technology.py",
    "scripts/verify_app_f_release_ui.py",
    "results/evidence/app-e/ui-technology-comparison.json",
    "results/evidence/app-e/qt-widgets-prototype.png",
    "results/evidence/app-e/qt-quick-prototype.png",
    "results/evidence/app-f/fullhd-1920x1080.png",
    "results/evidence/app-f/measurement-1280x720.png",
    "results/evidence/app-f/minimum-1280x720.png",
    "results/evidence/app-f/release-ui-verification.json",
    "results/evidence/app-f/scale-150-percent.png",
    "results/evidence/app-f/standard-1366x768.png",
    "results/evidence/app-f/et-continuous-1280x720.png",
    "results/evidence/app-f/et-gnss-1180x680.png",
    "results/evidence/app-f/et-interleaved-1440x900.png",
    "results/evidence/app-f/empty-1280x720.png",
)

# P0 kart güvenlik sınırı ile gerçek, operatörce sağlanan kayıtların çevrimdışı
# analizi.  Yerel kayıt byte'ları bu listede değildir ve release'e girmez.
APPROVED_P0_PLATFORM_AND_RECORDED_FILES = (
    "docs/decisions/ADR-0028-P0-MULTISCALE-DETECTION.md",
    "docs/decisions/ADR-0029-P0-SUSTAINED-THROUGHPUT-ACCEPTANCE.md",
    "docs/decisions/ADR-0030-P0-OS-CFAR-PL-OFFLOAD.md",
    "docs/decisions/ADR-0031-P0-ARM-HOT-PATH-OPTIMIZATION.md",
    "docs/decisions/ADR-0032-P0-VALIDATED-CANDIDATE-SHORTCUT.md",
    "docs/decisions/ADR-0033-P0-SPARSE-MULTISCALE-CANDIDATE-BOUNDARY.md",
    "docs/interfaces/P0_ARM_PARAMETER_RUNTIME_CONTRACT.md",
    "docs/interfaces/P0_ED_LOCAL_SERVICE_ABI.md",
    "docs/interfaces/P0_PL_OS_CFAR_CONTRACT.md",
    "algorithms/rtl/p0_os_cfar.py",
    "algorithms/rtl/p0_os_cfar_vectors.py",
    "algorithms/rtl/p0_candidate_reducer.py",
    "algorithms/rtl/p0_candidate_reducer_vectors.py",
    "algorithms/rtl/p0_wideband_recovery_vectors.py",
    "algorithms/rtl/p0_sparse_os_candidate_vectors.py",
    "algorithms/rtl/p0_final_candidate_vectors.py",
    "algorithms/fpga/p0/constraints/p0_os_cfar_50mhz.xdc",
    "algorithms/fpga/p0/constraints/p0_candidate_reducer_50mhz.xdc",
    "algorithms/fpga/p0/rtl/p0_os_cfar_pkg.sv",
    "algorithms/fpga/p0/rtl/axis_p0_os_cfar.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_reducer_pkg.sv",
    "algorithms/fpga/p0/rtl/p0_parallel_region_median.sv",
    "algorithms/fpga/p0/rtl/p0_wideband_recovery_pkg.sv",
    "algorithms/fpga/p0/rtl/p0_wideband_recovery.sv",
    "algorithms/fpga/p0/rtl/p0_sparse_os_candidate_pkg.sv",
    "algorithms/fpga/p0/rtl/p0_os_cfar_decision_engine.sv",
    "algorithms/fpga/p0/rtl/p0_os_candidate_ram.sv",
    "algorithms/fpga/p0/rtl/p0_os_candidate_grouping.sv",
    "algorithms/fpga/p0/rtl/p0_sparse_os_candidate_top.sv",
    "algorithms/fpga/p0/rtl/p0_region_bank.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_record_ram.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_fusion.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_reducer_top.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_reducer_synthesis_top.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_reducer_packetizer_top.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_dsp_runtime_top.sv",
    "algorithms/fpga/p0/rtl/p0_candidate_dsp_runtime_bd.v",
    "algorithms/fpga/p0/rtl/p0_os_cfar_synthesis_top.sv",
    "algorithms/fpga/p0/tb/tb_axis_p0_os_cfar.sv",
    "algorithms/fpga/p0/tb/tb_p0_parallel_region_median.sv",
    "algorithms/fpga/p0/tb/tb_p0_wideband_recovery.sv",
    "algorithms/fpga/p0/tb/tb_p0_sparse_os_candidate.sv",
    "algorithms/fpga/p0/tb/tb_p0_candidate_reducer.sv",
    "algorithms/fpga/p0/tb/tb_p0_candidate_guards.sv",
    "algorithms/fpga/p0/tb/tb_p0_candidate_reducer_packetizer.sv",
    "algorithms/fpga/p0/tb/tb_p0_candidate_dsp_runtime.sv",
    "datasets/fixtures/p0_candidate_reducer/axis-power-input.mem",
    "datasets/fixtures/p0_candidate_reducer/region-median-twice-expected.mem",
    "datasets/fixtures/p0_candidate_reducer/golden-vectors.json",
    "datasets/fixtures/p0_candidate_reducer/fixture-manifest.json",
    "datasets/fixtures/p0_wideband_recovery/axis-power-input.mem",
    "datasets/fixtures/p0_wideband_recovery/candidate-expected.mem",
    "datasets/fixtures/p0_wideband_recovery/expected-record-counts.mem",
    "datasets/fixtures/p0_wideband_recovery/golden-vectors.json",
    "datasets/fixtures/p0_wideband_recovery/fixture-manifest.json",
    "datasets/fixtures/p0_sparse_os_candidate/candidate-expected.mem",
    "datasets/fixtures/p0_sparse_os_candidate/expected-record-counts.mem",
    "datasets/fixtures/p0_sparse_os_candidate/golden-vectors.json",
    "datasets/fixtures/p0_sparse_os_candidate/fixture-manifest.json",
    "datasets/fixtures/p0_final_candidate/candidate-expected.mem",
    "datasets/fixtures/p0_final_candidate/expected-record-counts.mem",
    "datasets/fixtures/p0_final_candidate/golden-vectors.json",
    "datasets/fixtures/p0_final_candidate/fixture-manifest.json",
    "datasets/fixtures/p0_candidate_reducer_packetizer/transport-axis64-expected.mem",
    "datasets/fixtures/p0_candidate_reducer_packetizer/golden-vectors.json",
    "datasets/fixtures/p0_candidate_reducer_packetizer/fixture-manifest.json",
    "datasets/fixtures/p0_os_cfar/axis-power-input.mem",
    "datasets/fixtures/p0_os_cfar/dma-expected.mem",
    "datasets/fixtures/p0_os_cfar/golden-vectors.json",
    "datasets/fixtures/p0_os_cfar/fixture-manifest.json",
    "platforms/embedded/p0/include/p0_fclk_guard_logic.h",
    "platforms/embedded/p0/include/p0_fclk_guard_uapi.h",
    "platforms/embedded/p0/petalinux/p0-fclk-guard.Makefile",
    "platforms/embedded/p0/petalinux/p0-fclk-guard_1.0.bb",
    "platforms/embedded/p0/petalinux/p0-fclk-guardctl_1.0.bb",
    "platforms/embedded/p0/src/p0_fclk_guard.c",
    "platforms/embedded/p0/src/p0_fclk_guardctl.c",
    "algorithms/p0/recorded_df.py",
    "algorithms/p0/two_point_df.py",
    "algorithms/sigmf/hackrf.py",
    "results/evidence/p0/fclk-guard-build.json",
    "results/evidence/p0/zedboard-dma-physical-acceptance.json",
    "results/evidence/p0/ed-local-service-host-acceptance.json",
    "results/evidence/p0/ed-local-service-petalinux-build.json",
    "results/evidence/p0/ed-local-service-physical-acceptance.json",
    "results/evidence/p0/ed-stage-profile-adr0032-transient-arm.json",
    "results/evidence/p0/ed-stage-profile-adr0033-bottleneck-split-arm.json",
    "results/evidence/p0/candidate-reducer-reference.json",
    "results/evidence/p0/candidate-reducer-median-rtl.json",
    "results/evidence/p0/candidate-reducer-wideband-rtl.json",
    "results/evidence/p0/candidate-reducer-final-rtl.json",
    "results/evidence/p0/candidate-reducer-vivado.json",
    "results/evidence/p0/candidate-reducer-packetizer.json",
    "results/evidence/p0/candidate-dsp-runtime.json",
    "scripts/analyze_hackrf_amplitude_df.py",
    "scripts/wrap_hackrf_iq_as_sigmf.py",
    "tests/p0/test_p0_fclk_guard_logic.c",
    "tests/p0/test_p0_fclk_guard_source.py",
    "tests/p0/test_p0_os_cfar_runtime_source.py",
    "platforms/embedded/p0/include/p0_candidate_packet.h",
    "platforms/embedded/p0/include/p0_dma_runtime.h",
    "platforms/embedded/p0/include/p0_ed_pipeline.h",
    "platforms/embedded/p0/include/p0_ed_service_protocol.h",
    "platforms/embedded/p0/include/p0_parameter_runtime.h",
    "platforms/embedded/p0/include/p0_multiscale_detector.h",
    "platforms/embedded/p0/include/p0_pl_os_cfar.h",
    "platforms/embedded/p0/src/p0_candidate_packet.c",
    "platforms/embedded/p0/src/p0_dma_runtime.c",
    "platforms/embedded/p0/src/p0_ed_client.c",
    "platforms/embedded/p0/src/p0_ed_pipeline.c",
    "platforms/embedded/p0/src/p0_ed_runtime_run.c",
    "platforms/embedded/p0/src/p0_ed_service.c",
    "platforms/embedded/p0/src/p0_ed_service_protocol.c",
    "platforms/embedded/p0/src/p0_parameter_client.c",
    "platforms/embedded/p0/src/p0_parameter_run.c",
    "platforms/embedded/p0/src/p0_parameter_runtime.c",
    "platforms/embedded/p0/src/p0_multiscale_detector.c",
    "platforms/embedded/p0/src/p0_pl_os_cfar.c",
    "platforms/embedded/p0/src/p0_ed_throughput_run.c",
    "platforms/embedded/p0/src/p0_ed_stage_profile_run.c",
    "platforms/embedded/p0/petalinux/p0-ed-service.init",
    "scripts/verify_p0_ed_service.py",
    "scripts/verify_p0_ed_service_linux.py",
    "scripts/verify_p0_ed_service_physical.py",
    "scripts/verify_p0_parameter_runtime.py",
    "scripts/verify_p0_parameter_runtime_physical.py",
    "scripts/verify_p0_temporal_runtime.py",
    "scripts/verify_p0_multiscale_detection.py",
    "scripts/verify_p0_ed_throughput_physical.py",
    "scripts/generate_p0_os_cfar_vectors.py",
    "scripts/run_p0_os_cfar_vivado.tcl",
    "scripts/verify_p0_os_cfar_pl.py",
    "scripts/verify_p0_os_cfar_pl_runtime.py",
    "scripts/verify_p0_candidate_reducer.py",
    "scripts/generate_p0_candidate_reducer_vectors.py",
    "scripts/verify_p0_candidate_reducer_rtl.py",
    "scripts/generate_p0_wideband_recovery_vectors.py",
    "scripts/verify_p0_wideband_recovery_rtl.py",
    "scripts/generate_p0_sparse_os_candidate_vectors.py",
    "scripts/generate_p0_final_candidate_vectors.py",
    "scripts/verify_p0_final_candidate_rtl.py",
    "scripts/run_p0_candidate_reducer_vivado.tcl",
    "scripts/verify_p0_candidate_reducer_vivado.py",
    "scripts/generate_p0_candidate_reducer_packetizer_vectors.py",
    "scripts/verify_p0_candidate_reducer_packetizer.py",
    "scripts/verify_p0_candidate_dsp_runtime.py",
    "scripts/verify_p0_vivado_build.py",
    "tests/p0/p0_ed_service_protocol_test.c",
    "tests/p0/p0_parameter_runtime_test.c",
    "results/evidence/p0/parameter-runtime-host-acceptance.json",
    "results/evidence/p0/parameter-runtime-petalinux-build.json",
    "results/evidence/p0/parameter-runtime-physical-acceptance.json",
    "results/evidence/p0/multiscale-detector-host-acceptance.json",
    "results/evidence/p0/multiscale-detector-physical-acceptance.json",
    "results/evidence/p0/ed-throughput-physical-acceptance.json",
    "results/evidence/p0/ed-stage-profile-physical.json",
    "results/evidence/p0/os-cfar-pl-runtime-integration.json",
    "results/evidence/p0/os-cfar-pl/algorithm-contract.json",
    "results/evidence/p0/os-cfar-pl/architecture-study.json",
    "results/evidence/p0/os-cfar-pl/coefficient-validation.json",
    "results/evidence/p0/os-cfar-pl/rtl-simulation.json",
    "results/evidence/p0/os-cfar-pl/source-manifest.json",
    "results/evidence/p0/os-cfar-pl/throughput-capacity.json",
    "results/evidence/p0/os-cfar-pl/toolchain.json",
    "results/evidence/p0/os-cfar-pl/vivado-implementation.json",
    "results/evidence/p0/os-cfar-pl/verification-summary.json",
    "tests/p0/p0_ed_fake_dma_runtime.c",
    "tests/p0/test_p0_ed_service.py",
    "tests/p0/test_p0_temporal_runtime.py",
    "tests/test_p0_multiscale_detection.py",
    "tests/p0/test_p0_ed_throughput.py",
    "tests/p0/test_p0_os_cfar_pl_model.py",
    "tests/p0/test_p0_os_cfar_pl_vectors.py",
    "tests/p0/test_p0_os_cfar_pl_verifier.py",
    "tests/p0/test_p0_os_cfar_pl_runtime.py",
    "tests/p0/test_p0_candidate_reducer.py",
    "tests/p0/test_p0_candidate_reducer_rtl.py",
    "tests/p0/test_p0_wideband_recovery_rtl.py",
    "tests/p0/test_p0_final_candidate_rtl.py",
    "tests/p0/test_p0_candidate_reducer_packetizer.py",
    "tests/p0/test_p0_candidate_dsp_runtime.py",
    "tests/test_hackrf_recorded_integration.py",
    "tests/test_two_point_df.py",
)

EXPECTED_TOOLS = (
    "Git",
    "Python",
    "NumPy",
    "SciPy",
    "pytest",
    "CMake",
    "Ninja",
    "C/C++ compiler",
    "Qt",
    "GHDL",
    "VUnit",
    "Verilator",
    "Icarus Verilog",
    "Vivado",
    "XSim",
    "HackRF command-line tools",
)


def _result(identifier: str, passed: bool, detail: str) -> dict[str, object]:
    return {"id": identifier, "status": "passed" if passed else "failed", "detail": detail}


def check_required_files() -> dict[str, object]:
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    return _result(
        "required-files",
        not missing,
        "all required files are present" if not missing else "missing: " + ", ".join(missing),
    )


def _repository_files() -> set[str]:
    files: set[str] = set()
    skipped_directories = {
        ".git", ".pytest_cache", ".venv", ".Xil", "__pycache__",
        "build", "dist", "venv", "xsim.dir",
    }
    skipped_names = {"dfx_runtime.txt"}
    skipped_suffixes = {".fst", ".jou", ".log", ".pyc", ".pyo", ".str", ".vcd", ".wdb"}
    for path in ROOT.rglob("*"):
        relative_parts = path.relative_to(ROOT).parts
        if any(part in skipped_directories for part in relative_parts):
            continue
        if relative_parts[:3] == ("datasets", "external", "local"):
            continue
        if path.is_file() and path.name not in skipped_names and path.suffix not in skipped_suffixes:
            files.add(path.relative_to(ROOT).as_posix())
    return files


def check_allowed_tree() -> dict[str, object]:
    allowed = (
        set(REQUIRED_FILES)
        | set(APPROVED_PHASE01_FILES)
        | set(APPROVED_PHASE02_FILES)
        | set(APPROVED_PHASE03_FILES)
        | set(APPROVED_PHASE04_FILES)
        | set(APPROVED_PHASE08A_FILES)
        | set(APPROVED_PHASE05_FILES)
        | set(APPROVED_PHASE06A_FILES)
        | set(APPROVED_PHASE06B_FILES)
        | set(APPROVED_PHASE06C_FILES)
        | set(APPROVED_PHASE06D_FILES)
        | set(APPROVED_PHASE06E_FILES)
        | set(APPROVED_PHASE06F_FILES)
        | set(APPROVED_PHASE06G_FILES)
        | set(APPROVED_PHASE06H_FILES)
        | set(APPROVED_PHASE06I_FILES)
        | set(APPROVED_TEST_INFRASTRUCTURE_FILES)
        | set(APPROVED_PHASE06J_FILES)
        | set(APPROVED_P0_FILES)
        | set(APPROVED_ET_OFFLINE_FILES)
        | set(APPROVED_APP_HARDENING_FILES)
        | set(APPROVED_P0_PLATFORM_AND_RECORDED_FILES)
    )
    unexpected = sorted(_repository_files() - allowed)
    return _result(
        "minimal-file-tree",
        not unexpected,
        "repository contains the PHASE-00 baseline and approved later-phase paths"
        if not unexpected
        else "unexpected files: " + ", ".join(unexpected),
    )


def check_text_integrity() -> dict[str, object]:
    problems: list[str] = []
    for relative in REQUIRED_FILES:
        path = ROOT / relative
        if not path.is_file():
            continue
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            problems.append(f"{relative}: invalid UTF-8 at byte {exc.start}")
            continue
        if "\x00" in text:
            problems.append(f"{relative}: NUL byte")
        if "\r" in text:
            problems.append(f"{relative}: non-LF line ending")
        if text and not text.endswith("\n"):
            problems.append(f"{relative}: missing final newline")
        for line_number, line in enumerate(text.split("\n"), start=1):
            if line.endswith((" ", "\t")):
                problems.append(f"{relative}:{line_number}: trailing whitespace")
    return _result(
        "text-integrity",
        not problems,
        "all PHASE-00 text files are valid UTF-8 with LF endings and no trailing whitespace"
        if not problems
        else "; ".join(problems),
    )


def check_adr() -> dict[str, object]:
    text = (ROOT / "docs/decisions/ADR-0001-REFERENCE-HARDWARE.md").read_text(encoding="utf-8")
    required = (
        "Accepted",
        "2× HackRF One",
        "ZedBoard Zynq-7000",
        "Laptop",
        "MUSIC",
        "PA",
        "yüksek güçlü ET",
    )
    missing = [value for value in required if value.casefold() not in text.casefold()]
    return _result(
        "reference-hardware-adr",
        not missing,
        "accepted reference hardware decision and limitations are documented"
        if not missing
        else "ADR missing: " + ", ".join(missing),
    )


def check_ktr_traceability() -> dict[str, object]:
    text = (ROOT / "docs/requirements/KTR_TRACEABILITY.md").read_text(encoding="utf-8")
    identifiers = tuple(f"KTR-{item}" for item in ("4.1", "4.2", "4.3", "4.4", "4.5", "5.1", "5.2", "5.3", "5.4", "6"))
    missing = [identifier for identifier in identifiers if f"| {identifier} |" not in text]
    completed = re.findall(r"\|\s*(?:Tamamlandı|Doğrulandı)\s*\|", text, flags=re.IGNORECASE)
    passed = not missing and not completed
    detail = "all required KTR rows are present and remain planned/not implemented"
    if missing:
        detail = "missing KTR rows: " + ", ".join(missing)
    elif completed:
        detail = "KTR rows must not claim completion"
    return _result("ktr-traceability", passed, detail)


def check_roadmap() -> dict[str, object]:
    text = (ROOT / "docs/plans/IMPLEMENTATION_ROADMAP.md").read_text(encoding="utf-8")
    phase_positions = [text.find(f"| PHASE-{number:02d} |") for number in range(14)]
    ordered = all(position >= 0 for position in phase_positions) and phase_positions == sorted(phase_positions)
    baseline_present = "| PHASE-00 | Repository ve mühendislik temeli |" in text
    current_phase_present = "**P0 öncesindeki kayıtlı ana açık fazlar: PHASE-04 ve PHASE-06**" in text
    return _result(
        "phase-roadmap",
        ordered and baseline_present and current_phase_present,
        "roadmap retains the PHASE-00 baseline and preserves PHASE-00 through PHASE-13 order"
        if ordered and baseline_present and current_phase_present
        else "roadmap phase order, baseline, or current-phase marker is invalid",
    )


def check_readme_truthfulness() -> dict[str, object]:
    text = (ROOT / "README.md").read_text(encoding="utf-8").casefold()
    required = (
        "yalnız ölçülmüş veya tekrarlanabilir testle doğrulanmış",
        "zedboard üzerinde dma ve tespit zinciri",
        "önceki güç→arm yolu fiziksel kartta doğrulandı",
        "sürekli 2 ms/s kabulünde 4.096/4.096 kare",
        "am/nfm izleme zinciri",
        "qml ürün akışında doğrulandı",
        "canlı hackrf/ses saha kabulü bekliyor",
        "rf yayın yolu yok",
        "kalibrasyonsuz `dbfs`",
    )
    missing = [value for value in required if value not in text]
    return _result(
        "readme-current-state",
        not missing,
        "README distinguishes verified capabilities from live hardware, calibration, and RF-TX limits"
        if not missing
        else "README lacks explicit current-state markers: " + ", ".join(missing),
    )


def check_rf_boundaries() -> dict[str, object]:
    text = (ROOT / "docs/safety/RF_TEST_BOUNDARIES.md").read_text(encoding="utf-8").casefold()
    required = (
        "phase-00 kapsamında rf yayını yoktur",
        "antene bağlı kontrolsüz tx testi yapılmaz",
        "gnss aldatma",
        "pa bulunmadığından",
        "hackrf-2 bu aşamada kullanılmaz",
        "tx kodu eklenmez",
    )
    missing = [value for value in required if value not in text]
    return _result(
        "rf-test-boundaries",
        not missing,
        "all mandatory PHASE-00 RF safety boundaries are documented"
        if not missing
        else "RF boundary text missing: " + ", ".join(missing),
    )


def check_no_future_sources() -> dict[str, object]:
    implementation_directories = ("algorithms", "app", "verification", "datasets", "platforms")
    allowed = set(APPROVED_PHASE01_FILES) | set(APPROVED_PHASE02_FILES) | set(APPROVED_PHASE03_FILES) | set(APPROVED_PHASE04_FILES) | set(APPROVED_PHASE08A_FILES) | set(APPROVED_PHASE05_FILES) | set(APPROVED_PHASE06A_FILES) | set(APPROVED_PHASE06B_FILES) | set(APPROVED_PHASE06C_FILES) | set(APPROVED_PHASE06D_FILES) | set(APPROVED_PHASE06E_FILES) | set(APPROVED_PHASE06F_FILES) | set(APPROVED_PHASE06G_FILES) | set(APPROVED_PHASE06H_FILES) | set(APPROVED_PHASE06I_FILES) | set(APPROVED_TEST_INFRASTRUCTURE_FILES) | set(APPROVED_PHASE06J_FILES) | set(APPROVED_P0_FILES) | set(APPROVED_ET_OFFLINE_FILES) | set(APPROVED_APP_HARDENING_FILES) | set(APPROVED_P0_PLATFORM_AND_RECORDED_FILES) | {
        "algorithms/fpga/README.md",
        "algorithms/README.md",
        "verification/README.md",
        "app/README.md",
        "datasets/README.md",
    }
    unexpected: list[str] = []
    for directory in implementation_directories:
        for path in (ROOT / directory).rglob("*"):
            if path.is_file():
                relative = path.relative_to(ROOT).as_posix()
                if path.relative_to(ROOT).parts[:3] == ("datasets", "external", "local"):
                    continue
                if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                    continue
                if relative not in allowed:
                    unexpected.append(relative)
    return _result(
        "no-future-phase-sources",
        not unexpected,
        "implementation directories contain only approved later-phase additions"
        if not unexpected
        else "future-phase files found: " + ", ".join(sorted(unexpected)),
    )


def check_toolchain_inventory() -> dict[str, object]:
    path = ROOT / "results/evidence/phase00/toolchain.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _result("toolchain-inventory", False, f"inventory cannot be read: {type(exc).__name__}: {exc}")

    tools = payload.get("tools")
    if not isinstance(tools, list):
        return _result("toolchain-inventory", False, "tools must be a list")
    names = tuple(tool.get("name") for tool in tools if isinstance(tool, dict))
    if names != EXPECTED_TOOLS:
        return _result("toolchain-inventory", False, "inventory entries are missing, extra, or out of order")

    allowed_statuses = {"available", "unavailable", "unknown"}
    problems: list[str] = []
    for tool in tools:
        status = tool.get("status")
        evidence = tool.get("evidence")
        if status not in allowed_statuses:
            problems.append(f"{tool.get('name')}: invalid status {status!r}")
        if not isinstance(evidence, str) or not evidence.strip():
            problems.append(f"{tool.get('name')}: missing evidence")
        if status == "available" and not (
            isinstance(evidence, str)
            and (evidence.startswith("executable: ") or evidence.startswith("python-module: "))
        ):
            problems.append(f"{tool.get('name')}: available status lacks detection evidence")
        if status == "unknown" and "failed" not in str(evidence).casefold():
            problems.append(f"{tool.get('name')}: unknown status lacks a reason")

    return _result(
        "toolchain-inventory",
        not problems,
        "all toolchain entries have valid statuses and detection evidence; unavailable/unknown are informational"
        if not problems
        else "; ".join(problems),
    )


CHECKS: tuple[Callable[[], dict[str, object]], ...] = (
    check_required_files,
    check_allowed_tree,
    check_text_integrity,
    check_adr,
    check_ktr_traceability,
    check_roadmap,
    check_readme_truthfulness,
    check_rf_boundaries,
    check_no_future_sources,
    check_toolchain_inventory,
)


def run_checks() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for check in CHECKS:
        try:
            results.append(check())
        except (OSError, UnicodeDecodeError) as exc:
            results.append(_result(check.__name__, False, f"check could not run: {type(exc).__name__}: {exc}"))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PHASE-00 repository sözleşmesini doğrula")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Tarihsel kanıt dosyasını değiştirmeden yalnız doğrulama yap",
    )
    args = parser.parse_args(argv)
    checks = run_checks()
    passed = all(check["status"] == "passed" for check in checks)
    payload = {
        "schema_version": 1,
        "phase": "PHASE-00",
        "overall": "passed" if passed else "failed",
        "checks": checks,
    }
    if not args.check:
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    for check in checks:
        print(f"[{check['status'].upper()}] {check['id']}: {check['detail']}")
    if args.check:
        print("Salt-okunur doğrulama tamamlandı; tarihsel kanıt değiştirilmedi.")
    else:
        print(f"Verification summary written to {SUMMARY}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
