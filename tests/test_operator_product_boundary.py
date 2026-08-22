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
        self.assertEqual("host.operator_console.__main__", document["entry_point"])
        self.assertEqual("product", document["application_mode"])
        self.assertEqual(
            {
                "mock_backend": False,
                "training_mode": False,
                "offline_et_console": False,
                "embedded_demo_data": False,
                "hardcoded_recording_paths": False,
            },
            document["release_assertions"],
        )
        excluded = set(document["excluded_paths"])
        for required in (
            "host/acquisition/mock.py",
            "host/operator_console/laboratory.py",
            "reference/et",
            "reference/p0/df_fixtures.py",
            "datasets",
            "results",
            "scripts",
            "tests",
        ):
            self.assertIn(required, excluded)

    def test_deploy_spec_enforces_the_same_import_boundary(self) -> None:
        spec = (ROOT / "host" / "operator_console" / "pysidedeploy.spec").read_text(encoding="utf-8")
        for module in (
            "host.acquisition.mock",
            "host.operator_console.laboratory",
            "reference.et",
            "reference.p0.df_fixtures",
        ):
            self.assertIn(f"--nofollow-import-to={module}", spec)

    def test_product_runtime_has_only_real_source_modes_and_loads_no_lab_modules(self) -> None:
        code = r'''
import json
import os
import sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from host.operator_console.application import build_application
app, window, controller = build_application(["product-boundary-test"])
payload = {
    "sources": [window.source_type_combo.itemData(i) for i in range(window.source_type_combo.count())],
    "tabs": [window.workspace_tabs.tabText(i) for i in range(window.workspace_tabs.count())],
    "map_sources": [window.map_source_combo.itemData(i) for i in range(window.map_source_combo.count())],
    "laboratory_mode": window.laboratory_mode,
    "has_training_control": hasattr(window, "df_training_button") or hasattr(window, "map_training_button"),
    "has_et_workspace": hasattr(window, "et_workspace"),
    "lab_modules": sorted(name for name in sys.modules if name == "reference.et" or name.startswith("reference.et.") or name in {"host.acquisition.mock", "reference.p0.df_fixtures"}),
}
controller.close()
window.close()
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
        self.assertEqual(["sigmf", "hackrf"], payload["sources"])
        self.assertFalse(payload["laboratory_mode"])
        self.assertFalse(payload["has_training_control"])
        self.assertFalse(payload["has_et_workspace"])
        self.assertNotIn("HOST/SYNTHETIC", payload["map_sources"])
        self.assertEqual([], payload["lab_modules"])
        self.assertFalse(any("ET" in tab or "Taarruz" in tab for tab in payload["tabs"]))

    def test_product_sources_have_no_hardcoded_demo_recording_path(self) -> None:
        for relative in (
            "host/operator_console/application.py",
            "host/operator_console/controller.py",
            "host/operator_console/main_window.py",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("video_data/", text, relative)


if __name__ == "__main__":
    unittest.main()
