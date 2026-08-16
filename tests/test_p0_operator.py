from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from host.operator_console.main_window import MainWindow
from reference.et import SafetyMode
from scripts.run_p0_demo import populate
from qt_test_support import isolate_qt_module


class P0OperatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(["p0-operator-test"])
        cls.window = MainWindow()
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
        for required in ("GÖREV", "SPEKTRUM", "WATERFALL", "TESPİTLER", "PARAMETRELER", "YÖN BULMA", "SİSTEM DURUMU"):
            self.assertIn(required, combined)
        self.assertEqual("HOST REFERENCE", self.window.parameter_values["p0_source"].text())
        self.assertIn("REPLAY", self.window.parameter_values["p0_backend"].text())
        self.assertIn("KALİBRASYON BEKLİYOR", self.window.parameter_values["p0_power"].text())
        self.assertNotIn("FPGA RESULT", self.window.parameter_values["p0_source"].text())

    def test_df_and_et_controls_use_models_and_fail_closed(self) -> None:
        self.assertIn("60.0°", self.window.df_result_label.text())
        self.assertGreater(self.window.df_curve.xData.size, 0)
        self.assertGreater(self.window.et_waveform_curve.xData.size, 0)
        self.window._stop_et_mission()
        index = self.window.et_mode_combo.findData(SafetyMode.HARDWARE_TX_LOCKED)
        self.window.et_mode_combo.setCurrentIndex(index)
        self.window._start_jamming_preview()
        self.assertIn("GÜVENLİK KİLİDİ", self.window.et_state_label.text())


def load_tests(_: unittest.TestLoader, tests: unittest.TestSuite, __: str | None) -> unittest.TestSuite:
    return isolate_qt_module(__name__, tests)


if __name__ == "__main__":
    unittest.main()
