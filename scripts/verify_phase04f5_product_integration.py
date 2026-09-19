#!/usr/bin/env python3
"""Write or verify PHASE-04-F5E host product integration evidence."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.parameters import F5ParameterEstimator
from algorithms.parameters.operator_reference import canonical_json_bytes, sha256_file
from algorithms.pipeline import PHASE04F5_FIELDS, PHASE04F5_PROFILE_PATH, load_phase04f5_capability
from scripts.establish_phase04f5_product_profile import build_profile


SUMMARY_PATH = ROOT / "results" / "evidence" / "phase04f5" / "f5e-verification.json"
VIEW_MODEL_PATH = ROOT / "app" / "operator_console" / "quick_view_model.py"
MEASUREMENT_PATH = ROOT / "app" / "operator_console" / "quick_measurement_actions.py"
PANEL_PATH = ROOT / "app" / "operator_console" / "qml" / "ParameterMeasurementPanel.qml"
QML_PATH = ROOT / "app" / "operator_console" / "qml" / "Main.qml"
PACKAGE_PATH = ROOT / "config" / "app" / "product-package.json"
DEPLOY_SPEC_PATH = ROOT / "app" / "operator_console" / "pysidedeploy.spec"
REQUIRED_ASSETS = {
    "profiles/phase03/operation-default.json",
    "profiles/phase04f5/operation-default.json",
    "config/p0/hackrf_ed_rx.json",
    "config/p0/hackrf_spurs.json",
    "config/p0/rx_calibration.json",
    "datasets/fixtures/phase04f1/domain-model.json",
    "datasets/fixtures/phase04f2/domain-model-v3.json",
    "datasets/fixtures/phase04f4/domain-model-v5.json",
    "algorithms/p0/native/bin/p0_channelizer.dll",
    "app/operator_console/assets/baz-logo-metal-red.png",
    "app/operator_console/assets/baz-logo.ico",
    "app/operator_console/assets/baz-logo-intro.png",
    "app/operator_console/assets/baz-logo-glow.png",
}


def _check(identifier: str, passed: bool) -> dict[str, str]:
    return {"id": identifier, "status": "passed" if passed else "failed"}


def build_summary() -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    tracked = json.loads(PHASE04F5_PROFILE_PATH.read_text(encoding="utf-8"))
    expected = build_profile()
    checks.append(_check("profile-reproducible", tracked == expected))

    capability = load_phase04f5_capability()
    checks.append(
        _check(
            "runtime-capability",
            capability is not None
            and capability.validated_fields == PHASE04F5_FIELDS
            and capability.methods == tuple(F5ParameterEstimator.METHOD_IDS.items())
            and capability.frames_per_measurement == 4
            and capability.frame_length == 4096
            and capability.operator_confirmed_span_required
            and not capability.automatic_span_validated,
        )
    )

    with tempfile.TemporaryDirectory() as folder:
        tampered_path = Path(folder) / "operation-default.json"
        tampered = dict(tracked)
        tampered["status"] = "experimental"
        tampered_path.write_text(json.dumps(tampered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        checks.append(_check("profile-tamper-fail-closed", load_phase04f5_capability(tampered_path) is None))

    package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
    deploy_spec = DEPLOY_SPEC_PATH.read_text(encoding="utf-8")
    checks.append(
        _check(
            "release-assets",
            set(package.get("allowed_runtime_assets", ())) == REQUIRED_ASSETS
            and all(path in deploy_spec for path in REQUIRED_ASSETS),
        )
    )
    view_model = VIEW_MODEL_PATH.read_text(encoding="utf-8")
    measurement = MEASUREMENT_PATH.read_text(encoding="utf-8")
    qml = QML_PATH.read_text(encoding="utf-8")
    panel = PANEL_PATH.read_text(encoding="utf-8")
    checks.append(
        _check(
            "qml-f5-runtime-binding",
            "load_phase04f5_capability" in view_model
            and "F5ParameterEstimator" in view_model
            and "P0ParameterExtractor" not in view_model
            and "operator_confirmed_span_required" in tracked
            and "ParameterMeasurementPanel" in qml
            and "viewModel: operatorViewModel" in qml
            and "confirmAnalysisSpan" in panel
            and "panel.viewModel.measurementReady" in panel,
        )
    )
    required_terms = (
        "Emisyon merkez frekansı",
        "Gözlenen taşıyıcı frekansı",
        "Alt OBW sınırı",
        "Üst OBW sınırı",
        "Kanal gücü (dBFS)",
        "Bant içi SNR kestirimi",
        "Sinyal türü",
    )
    checks.append(
        _check(
            "field-scoped-presentation",
            all(term in measurement for term in required_terms)
            and "Tepe bin gücü" not in view_model
            and '"dBm"' not in view_model,
        )
    )
    passed = all(item["status"] == "passed" for item in checks)
    return {
        "schema_version": 1,
        "phase": "PHASE-04-F5E",
        "status": "passed" if passed else "failed",
        "checks": checks,
        "validated_fields": list(PHASE04F5_FIELDS) if passed else [],
        "artifacts": {
            "product_profile_sha256": sha256_file(PHASE04F5_PROFILE_PATH),
            "view_model_sha256": sha256_file(VIEW_MODEL_PATH),
            "measurement_actions_sha256": sha256_file(MEASUREMENT_PATH),
            "qml_sha256": sha256_file(QML_PATH),
            "parameter_panel_sha256": sha256_file(PANEL_PATH),
            "product_package_sha256": sha256_file(PACKAGE_PATH),
            "deploy_spec_sha256": sha256_file(DEPLOY_SPEC_PATH),
        },
        "claim_boundary": (
            "F5E yalnız digest bağlı host kestirimcisi ve QML ürün bağını doğrular; FPGA, gerçek canlı RF "
            "doğruluğu, dBm kalibrasyonu veya saha kabulü değildir."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        summary = build_summary()
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"PHASE-04-F5E verification rejected: {exc}")
        return 1
    payload = canonical_json_bytes(summary)
    if args.write:
        SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY_PATH.write_bytes(payload)
    elif not SUMMARY_PATH.is_file() or SUMMARY_PATH.read_bytes() != payload:
        print("PHASE-04-F5E verification evidence is missing or stale")
        return 1
    print(f"PHASE-04-F5E product integration: {summary['status']}")
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
