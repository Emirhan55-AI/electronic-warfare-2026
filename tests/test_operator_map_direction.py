from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from host.operator_console.main_window import MainWindow
from host.operator_console.map_direction import DirectionMapView, FALLBACK_TEXT
from reference.p0 import AntennaReference, LocationFix, PositionSource
from host.operator_console.ui_text import TEXT
from qt_test_support import isolate_qt_module


class OperatorMapDirectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(["map-direction-test"])

    def test_web_engine_fallback_is_clean_and_console_still_launches(self) -> None:
        with patch("host.operator_console.map_direction.resolve_web_engine_view", return_value=None):
            window = MainWindow(laboratory_mode=True)
            self.assertTrue(window.direction_map_view.fallback_visible)
            self.assertEqual(FALLBACK_TEXT, window.direction_map_view.findChild(type(window.map_engine_label), "mapFallback").text())
            window.close()

    def test_df_result_binds_to_map_without_a_second_estimator(self) -> None:
        window = MainWindow(laboratory_mode=True)
        window._load_df_training_fixture()
        window.map_latitude_spin.setValue(39.9334)
        window.map_longitude_spin.setValue(32.8597)
        window.map_heading_spin.setValue(300.0)
        window.map_heading_reference_check.setChecked(True)
        window.map_source_combo.setCurrentIndex(window.map_source_combo.findData("HOST/SYNTHETIC"))
        window._show_current_df_on_map()
        presentation = window.direction_map_view.presentation
        self.assertIsNotNone(presentation)
        assert presentation is not None
        self.assertEqual(75.0, presentation.relative_antenna_angle_deg)
        self.assertEqual(15.0, presentation.geographic_azimuth_deg)
        self.assertEqual("15,0°", window.map_result_values["azimuth"].text())
        self.assertIn("Yön çizgisi", window.map_status_label.text())
        self.assertEqual("Yön", window.workspace_tabs.tabText(window.workspace_tabs.currentIndex()))
        self.assertEqual("Harita", window.direction_workspace.tabText(window.direction_workspace.currentIndex()))
        window.close()

    def test_missing_heading_is_displayed_as_relative_and_does_not_draw_lob(self) -> None:
        window = MainWindow(laboratory_mode=True)
        window._load_df_training_fixture()
        window.map_heading_reference_check.setChecked(False)
        window._show_current_df_on_map()
        presentation = window.direction_map_view.presentation
        self.assertIsNotNone(presentation)
        assert presentation is not None
        self.assertIsNone(presentation.geographic_azimuth_deg)
        self.assertIn("Bağıl yön", window.map_result_values["azimuth"].text())
        self.assertIn("Bağıl yön", window.map_status_label.text())
        window.close()

    def test_synthetic_training_scenarios_keep_truthful_label_and_expected_bearing(self) -> None:
        window = MainWindow(laboratory_mode=True)
        window.map_training_scenario_combo.setCurrentIndex(1)
        window.map_training_button.click()
        presentation = window.direction_map_view.presentation
        self.assertIsNotNone(presentation)
        assert presentation is not None
        self.assertEqual("HOST/SYNTHETIC", presentation.source)
        self.assertEqual(15.0, presentation.geographic_azimuth_deg)
        self.assertIn("HOST/SYNTHETIC TEST", window.map_status_label.text())
        window.close()

    def test_manual_location_and_manual_reference_are_explicit(self) -> None:
        window = MainWindow()
        window.map_latitude_spin.setValue(39.9334)
        window.map_longitude_spin.setValue(32.8597)
        window._use_manual_location()
        self.assertEqual("MANUEL", window.map_source_combo.currentData())
        self.assertIn("canlı GNSS", window.map_location_status.text())
        window.df_zero_reference_combo.setCurrentIndex(
            window.df_zero_reference_combo.findData(AntennaReference.MANUAL_GEOGRAPHIC)
        )
        window.df_manual_reference_spin.setValue(300.0)
        window.df_angle_spin.setValue(75.0)
        self.assertEqual(15.0, window._manual_geographic_bearing(75.0))
        window.close()

    def test_pc_location_failure_is_truthful_and_offers_manual_fallback(self) -> None:
        window = MainWindow()
        window._pc_location_failed("Bilgisayar konumu alınamadı. Manuel konum girebilirsiniz.")
        self.assertIn("Manuel konum", window.map_location_status.text())
        self.assertEqual("Doğruluk: bilinmiyor", window.map_accuracy_label.text())
        window._pc_location_acquired(LocationFix(39.0, 32.0, None, 25.0, PositionSource.AUTO_PC))
        self.assertEqual(PositionSource.AUTO_PC, window.map_source_combo.currentData())
        self.assertIn("25.0 m", window.map_accuracy_label.text())
        window.close()

    def test_measurement_history_stores_angle_azimuth_power_and_source(self) -> None:
        window = MainWindow()
        window.df_zero_reference_combo.setCurrentIndex(
            window.df_zero_reference_combo.findData(AntennaReference.MANUAL_GEOGRAPHIC)
        )
        window.df_manual_reference_spin.setValue(300.0)
        window.df_angle_spin.setValue(75.0)
        window.save_selected_iq_power(
            relative_power_db=-13.0,
            frequency_hz=145_000_000.0,
            source="REPLAY",
        )
        self.assertEqual(1, window.df_points_list.rowCount())
        self.assertEqual("75.0°", window.df_points_list.item(0, 0).text())
        self.assertEqual("15.0°", window.df_points_list.item(0, 1).text())
        self.assertEqual("-13.00 dBFS", window.df_points_list.item(0, 2).text())
        self.assertEqual("REPLAY", window.df_points_list.item(0, 3).text())
        live_index = window.map_source_combo.findData(PositionSource.LIVE_GNSS_RESERVED)
        self.assertFalse(window.map_source_combo.model().item(live_index).isEnabled())
        window.close()

    def test_direction_workspace_merges_measurement_and_map_without_default_training_controls(self) -> None:
        window = MainWindow()
        self.assertEqual("Yön", window.workspace_tabs.tabText(3))
        self.assertEqual(("Ölçüm", "Harita"), tuple(window.direction_workspace.tabText(i) for i in range(2)))
        self.assertFalse(window.df_training_controls.isVisible())
        self.assertFalse(window.df_points_list.isVisible())
        window.close()


def load_tests(_: unittest.TestLoader, tests: unittest.TestSuite, __: str | None) -> unittest.TestSuite:
    return isolate_qt_module(__name__, tests)


if __name__ == "__main__":
    unittest.main()
