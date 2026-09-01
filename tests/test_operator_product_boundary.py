"""Release-boundary tests for the product operator application."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "app" / "product-package.json"


class OperatorProductBoundaryTests(unittest.TestCase):
    def test_product_manifest_excludes_validation_surfaces(self) -> None:
        document = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual("app.operator_console.__main__", document["entry_point"])
        self.assertEqual("product", document["application_mode"])
        self.assertEqual("qt_quick_qml", document["presentation"])
        self.assertEqual("app/operator_console/qml/Main.qml", document["presentation_entry"])
        self.assertEqual(
            {
                "mock_backend": False,
                "training_mode": False,
                "offline_et_console": True,
                "embedded_demo_data": False,
                "hardcoded_recording_paths": False,
            },
            document["release_assertions"],
        )
        excluded = set(document["excluded_paths"])
        for required in (
            "platforms/acquisition/mock.py",
            "app/operator_console/laboratory.py",
            "algorithms/p0/df_fixtures.py",
            "datasets",
            "results",
            "scripts",
            "tests",
        ):
            self.assertIn(required, excluded)
        self.assertIn("algorithms/et", document["allowed_source_roots"])
        self.assertNotIn("algorithms/et", excluded)
        self.assertEqual(
            {
                "profiles/phase04f5/operation-default.json",
                "datasets/fixtures/phase04f1/domain-model.json",
                "datasets/fixtures/phase04f2/domain-model-v3.json",
                "datasets/fixtures/phase04f4/domain-model-v5.json",
                "algorithms/p0/native/bin/p0_channelizer.dll",
                "app/operator_console/assets/baz-logo-metal-red.png",
            },
            set(document["allowed_runtime_assets"]),
        )

    def test_deploy_spec_enforces_the_same_import_boundary(self) -> None:
        spec = (ROOT / "app" / "operator_console" / "pysidedeploy.spec").read_text(encoding="utf-8")
        for module in (
            "platforms.acquisition.mock",
            "app.operator_console.laboratory",
            "algorithms.p0.df_fixtures",
        ):
            self.assertIn(f"--nofollow-import-to={module}", spec)
        self.assertNotIn("--nofollow-import-to=algorithms.et", spec)
        for asset in (
            "profiles/phase04f5/operation-default.json",
            "datasets/fixtures/phase04f1/domain-model.json",
            "datasets/fixtures/phase04f2/domain-model-v3.json",
            "datasets/fixtures/phase04f4/domain-model-v5.json",
            "algorithms/p0/native/bin/p0_channelizer.dll",
            "app/operator_console/assets/baz-logo-metal-red.png",
        ):
            self.assertIn(asset, spec)

    def test_product_runtime_uses_qml_and_loads_no_legacy_or_lab_modules(self) -> None:
        code = r'''
import json
import os
import sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
from app.operator_console.quick_application import build_quick_application
app, engine, view_model = build_quick_application(["product-boundary-test"])
root = engine.rootObjects()[0]
payload = {
    "source_mode": view_model.sourceMode,
    "workspace": root.property("workspace"),
    "root_type": root.metaObject().className(),
    "offline_et_loaded": "algorithms.et" in sys.modules,
    "forbidden_modules": sorted(name for name in sys.modules if name in {"platforms.acquisition.mock", "algorithms.p0.df_fixtures", "app.operator_console.main_window", "app.operator_console.controller"}),
}
view_model.shutdown()
root.close()
print(json.dumps(payload, ensure_ascii=False))
'''
        environment = os.environ.copy()
        environment["QT_QPA_PLATFORM"] = "offscreen"
        environment["PYTHONIOENCODING"] = "utf-8"
        process = subprocess.run(
            [sys.executable, "-B", "-c", code],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(0, process.returncode, process.stdout + process.stderr)
        payload = json.loads(process.stdout.strip().splitlines()[-1])
        self.assertEqual("hackrf", payload["source_mode"])
        self.assertEqual(0, payload["workspace"])
        self.assertIn("QMLTYPE", payload["root_type"])
        self.assertTrue(payload["offline_et_loaded"])
        self.assertEqual([], payload["forbidden_modules"])

    def test_product_sources_have_no_hardcoded_demo_recording_path(self) -> None:
        for relative in (
            "app/operator_console/__main__.py",
            "app/operator_console/quick_application.py",
            "app/operator_console/quick_view_model.py",
            "app/operator_console/qml/Main.qml",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("video_data/", text, relative)


if __name__ == "__main__":
    unittest.main()
