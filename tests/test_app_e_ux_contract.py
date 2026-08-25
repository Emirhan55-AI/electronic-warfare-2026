"""APP-E terminology, presentation evidence and release-copy gates."""

from __future__ import annotations

import os
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QAbstractButton, QComboBox, QDockWidget, QLabel, QTabWidget, QTableWidget

from app.operator_console.main_window import MainWindow
from algorithms.p0.field_df import PositionSource
from scripts.verify_app_e_ui_technology import check_evidence


ROOT = Path(__file__).resolve().parents[1]


def visible_copy(window: MainWindow) -> str:
    values: list[str] = [window.windowTitle()]
    values.extend(widget.text() for widget in window.findChildren(QLabel))
    values.extend(widget.text() for widget in window.findChildren(QAbstractButton))
    values.extend(widget.windowTitle() for widget in window.findChildren(QDockWidget))
    values.extend(action.text() for action in window.findChildren(QAction))
    for combo in window.findChildren(QComboBox):
        values.extend(combo.itemText(index) for index in range(combo.count()))
    for tabs in window.findChildren(QTabWidget):
        values.extend(tabs.tabText(index) for index in range(tabs.count()))
    for table in window.findChildren(QTableWidget):
        for column in range(table.columnCount()):
            item = table.horizontalHeaderItem(column)
            if item is not None:
                values.append(item.text())
    return "\n".join(values)


class AppEUXContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(["app-e-ux-contract"])

    def test_product_and_laboratory_copy_uses_frozen_terms(self) -> None:
        banned = (
            "HOST/SYNTHETIC",
            "EĞİTİM",
            "Coğrafi Azimut",
            "Coğ. azimut",
            "Manuel Baş",
            "LIVE GNSS",
            "Yön çizgisi",
            "Otomatik öneri",
            "Yayın Merkez Frekansı",
            "Taşıyıcı Çizgisi Frekansı",
            "Sinyal Alanı",
            "KALİBRASYON BEKLİYOR",
        )
        for laboratory_mode in (False, True):
            window = MainWindow(laboratory_mode=laboratory_mode)
            try:
                copy = visible_copy(window)
                for phrase in banned:
                    self.assertNotIn(phrase, copy, f"{phrase!r} remains visible in laboratory={laboratory_mode}")
            finally:
                window.close()

    def test_unimplemented_gnss_source_is_not_offered(self) -> None:
        window = MainWindow()
        try:
            sources = [window.map_source_combo.itemData(index) for index in range(window.map_source_combo.count())]
            self.assertNotIn(PositionSource.LIVE_GNSS_RESERVED, sources)
            self.assertEqual([PositionSource.AUTO_PC, "MANUEL", "REPLAY"], sources)
        finally:
            window.close()

    def test_scroll_panels_have_dark_viewport_contract(self) -> None:
        stylesheet = (ROOT / "app" / "operator_console" / "theme.qss").read_text(encoding="utf-8")
        self.assertIn("QScrollArea > QWidget > QWidget", stylesheet)
        self.assertIn("background-color: #0B1118", stylesheet)

    def test_public_application_sources_have_no_development_tool_attribution(self) -> None:
        markers = ("co" + "dex", "chat" + "gpt", "open" + "ai", "cop" + "ilot", "cla" + "ude", "gem" + "ini")
        source_root = ROOT / "app" / "operator_console"
        for path in source_root.rglob("*"):
            if not path.is_file() or "map_assets" in path.parts or path.suffix not in {".py", ".qss", ".spec", ".md"}:
                continue
            content = path.read_text(encoding="utf-8").lower()
            for marker in markers:
                self.assertNotIn(marker, content, path.as_posix())

    def test_frozen_glossary_and_task_flows_are_present(self) -> None:
        glossary = (ROOT / "docs" / "ux" / "OPERATOR_TERMINOLOGY.md").read_text(encoding="utf-8")
        flows = (ROOT / "docs" / "ux" / "OPERATOR_TASK_FLOWS.md").read_text(encoding="utf-8")
        for term in ("Bağıl Geliş Açısı", "Anten Referans Yönü", "Gerçek Kuzeye Göre Kerteriz", "Kerteriz Hattı (LOB)"):
            self.assertIn(term, glossary)
        for flow in (
            "Kaynağı hazırlama",
            "Sinyal tespiti",
            "Parametre ölçümü",
            "Akış 4 — Analog dinleme",
            "Akış 5 — Yön bulma",
            "Sistem denetimi",
        ):
            self.assertIn(flow, flows)

    def test_map_copy_uses_bearing_contract(self) -> None:
        copy = (ROOT / "app" / "operator_console" / "map_assets" / "map.html").read_text(encoding="utf-8")
        for required in ("Anten referans yönü", "Gerçek kuzeye göre kerteriz", "kerteriz hattı yalnız doğrultudur"):
            self.assertIn(required, copy)
        for banned in ("Coğrafi azimut", "Bağıl yön", "yön çizgisi"):
            self.assertNotIn(banned, copy)

    def test_repeatable_technology_evidence_passes(self) -> None:
        self.assertTrue(check_evidence())


if __name__ == "__main__":
    unittest.main()
