"""Executable dependency rules for the APP-D source layout."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "verification" / "architecture-boundaries.json"


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.partition(".")[0])
    return roots


class ArchitectureBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_source_roots_and_verification_ownership_are_explicit(self) -> None:
        self.assertEqual({"app", "algorithms", "platforms"}, set(self.document["source_roots"]))
        for relative in self.document["verification_owned_roots"]:
            self.assertTrue((ROOT / relative).exists(), relative)

    def test_python_imports_follow_the_declared_direction(self) -> None:
        violations: list[str] = []
        for source_root, policy in self.document["source_roots"].items():
            forbidden = set(policy["forbidden_import_roots"])
            for path in sorted((ROOT / source_root).rglob("*.py")):
                blocked = sorted(imported_roots(path) & forbidden)
                if blocked:
                    violations.append(f"{path.relative_to(ROOT).as_posix()}: {', '.join(blocked)}")
        self.assertEqual([], violations)

    def test_legacy_roots_are_not_tracked_or_imported(self) -> None:
        tracked = {
            path.replace("\\", "/")
            for path in __import__("subprocess").check_output(
                ["git", "ls-files"], cwd=ROOT, text=True, encoding="utf-8"
            ).splitlines()
        }
        legacy = tuple(self.document["removed_legacy_roots"])
        self.assertFalse(any(path.startswith(tuple(f"{root}/" for root in legacy)) for path in tracked))
        for source_root in self.document["source_roots"]:
            for path in (ROOT / source_root).rglob("*.py"):
                self.assertTrue(imported_roots(path).isdisjoint(legacy), path)

    def test_operator_console_keeps_large_responsibilities_split(self) -> None:
        required_modules = {
            "app/operator_console/quick_runtime.py",
            "app/operator_console/quick_scan_actions.py",
            "app/operator_console/quick_measurement_actions.py",
            "app/operator_console/quick_listening_actions.py",
            "app/operator_console/quick_direction_actions.py",
            "app/operator_console/quick_et_actions.py",
            "app/operator_console/quick_detection_state.py",
            "app/operator_console/_mixin_controls.py",
            "app/operator_console/_mixin_navigation.py",
            "app/operator_console/qml/ETWorkspace.qml",
            "app/operator_console/qml/HackRFControls.qml",
            "app/operator_console/qml/Panel.qml",
            "app/operator_console/qml/PrimaryButton.qml",
            "app/operator_console/qml/DetectionGuidePainter.js",
            "app/operator_console/qml/MainNavigation.js",
        }
        self.assertEqual([], sorted(path for path in required_modules if not (ROOT / path).is_file()))

        line_limits = {
            "app/operator_console/main_window.py": 400,
            "app/operator_console/quick_view_model.py": 2_000,
            "app/operator_console/qml/Main.qml": 2_200,
        }
        for relative, maximum in line_limits.items():
            line_count = len((ROOT / relative).read_text(encoding="utf-8").splitlines())
            self.assertLessEqual(line_count, maximum, f"{relative}: {line_count} satır")


if __name__ == "__main__":
    unittest.main()
