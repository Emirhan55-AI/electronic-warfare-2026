from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from host.operator_console.main_window import MainWindow
from reference.et import SafetyMode
from reference.p0 import SearchMode
from scripts.run_p0_demo import populate
from qt_test_support import isolate_qt_module


class P0OperatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(["p0-operator-test"])
        cls.window = MainWindow(laboratory_mode=True)
        populate(cls.window)
        cls.window.show()
        cls.app.processEvents()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.window.close()
        cls.app.processEvents()

    def test_required_ed_areas_and_real_result_binding(self) -> None:
        labels = [self.window.workspace_tabs.tabText(index) for index in range(self.window.workspace_tabs.count())]
        combined = " ".join(labels)
        for required in ("Arama", "Parametre", "Dinleme", "Yön", "Sistem", "ET"):
            self.assertIn(required, combined)
        self.assertEqual("deterministic_test", self.window.source_kind)
        self.assertIn("ALGORİTMA TESTİ", self.window.source_value.text())
        self.assertIn("ANALOG DİNLEME TEST VERİSİ", self.window.listening_source_value.text())
        self.assertEqual("REPLAY", self.window.parameter_values["p0_source"].text())
        self.assertIn("REPLAY", self.window.parameter_values["p0_backend"].text())
        self.assertIn("KALİBRASYON BEKLİYOR", self.window.parameter_values["p0_power"].text())
        self.assertNotIn("FPGA RESULT", self.window.parameter_values["p0_source"].text())
        self.assertIn("RTL / VIVADO DOĞRULAMA", self.window.system_status_values["fpga"].text())
        self.assertIn("FİZİKSEL ZEDBOARD TESTİ", self.window.system_status_values["zedboard"].text())

    def test_df_and_et_controls_use_models_and_fail_closed(self) -> None:
        self.assertEqual("75°", self.window.df_result_values["relative"].text())
        self.assertEqual(24, self.window.df_curve.xData.size)
        self.assertGreater(self.window.et_waveform_curve.xData.size, 0)
        self.window._stop_et_mission()
        index = self.window.et_mode_combo.findData(SafetyMode.HARDWARE_TX_LOCKED)
        self.window.et_mode_combo.setCurrentIndex(index)
        self.window._start_jamming_preview()
        self.assertIn("GÜVENLİK KİLİDİ", self.window.et_state_label.text())

    def test_df_training_fixture_is_independent_and_truthfully_labelled(self) -> None:
        self.window.df_training_button.click()
        self.app.processEvents()
        self.assertEqual(24, self.window.df_curve.xData.size)
        self.assertIn("EĞİTİM / ALGORİTMA TESTİ", self.window.df_result_label.text())
        self.assertEqual("75°", self.window.df_result_values["relative"].text())
        self.assertEqual("HOST/SYNTHETIC", self.window.df_result_values["source"].text())

    def test_three_judge_modes_execute_real_replay_backend_and_validate_input(self) -> None:
        self.assertEqual(self.window.search_mode_combo.count(), 3)
        for index, mode in enumerate((SearchMode.UNKNOWN, SearchMode.JUDGE_BAND, SearchMode.JUDGE_FREQUENCY)):
            self.window.search_mode_combo.setCurrentIndex(index)
            self.window.search_start_button.click()
            self.app.processEvents()
            self.assertIsNotNone(self.window.last_search_result)
            assert self.window.last_search_result is not None
            self.assertIs(self.window.last_search_result.request.mode, mode)
            self.assertEqual(len(self.window.last_search_result.parameters), 1)
        self.window.search_mode_combo.setCurrentIndex(1)
        self.window.judge_band_lower_spin.setValue(100.100)
        self.window.judge_band_upper_spin.setValue(100.080)
        self.window.search_start_button.click()
        self.assertIn("GİRDİ HATASI", self.window.active_search_mode_label.text())


def load_tests(_: unittest.TestLoader, tests: unittest.TestSuite, __: str | None) -> unittest.TestSuite:
    return isolate_qt_module(__name__, tests)


if __name__ == "__main__":
    unittest.main()
