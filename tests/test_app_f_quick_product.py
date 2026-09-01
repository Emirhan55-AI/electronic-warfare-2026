"""APP-F release UI and real-source presentation boundary tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

import numpy as np

from app.operator_console.quick_view_model import _reduce_display_max


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-meta"
LISTENING_FIXTURE = ROOT / "datasets" / "fixtures" / "phase05" / "am-tone-ci8.sigmf-meta"
QML = ROOT / "app" / "operator_console" / "qml" / "Main.qml"


class QuickProductTests(unittest.TestCase):
    def test_fpga_error_revokes_ready_controls_and_header_badge_is_hidden_only_on_detection(self) -> None:
        payload = self.run_qml(
            """
root = engine.rootObjects()[0]
root.setProperty("sourcePanelOpen", True)
view_model._hackrf_ready = True
view_model._hackrf_transfer_executable = "hackrf_transfer"
view_model._source_state = "Hazır"
view_model.stateChanged.emit(); app.processEvents()
header = root.findChild(QObject, "receiverHeaderBadge")
settings = root.findChild(QObject, "receiverSettingsBadge")
start = root.findChild(QObject, "liveStartButton")
before = {"ready": view_model.hackrfReady, "start": start.property("enabled"),
          "header_visible": header.property("visible"), "settings": settings.property("state")}
view_model._live_failed(view_model._generation, "connection_failed", "FPGA hizmetine bağlanılamadı.")
app.processEvents()
failed = {"ready": view_model.hackrfReady, "start": start.property("enabled"),
          "header_visible": header.property("visible"), "settings": settings.property("state"),
          "error": view_model.errorTitle}
root.setProperty("spectrumTaskTab", 1); app.processEvents()
parameter = {"header_visible": header.property("visible"), "header_state": header.property("state")}
root.setProperty("workspace", 1); app.processEvents()
listening = {"header_visible": header.property("visible"), "header_state": header.property("state")}
payload = {"before": before, "failed": failed, "parameter": parameter, "listening": listening}
view_model.shutdown(); root.close()
print(json.dumps(payload))
"""
        )
        self.assertEqual(
            {"ready": True, "start": True, "header_visible": False, "settings": "Hazır"},
            payload["before"],
        )
        self.assertEqual(
            {"ready": False, "start": False, "header_visible": False, "settings": "Hata", "error": "FPGA bağlantısı kurulamadı"},
            payload["failed"],
        )
        self.assertEqual({"header_visible": True, "header_state": "Hata"}, payload["parameter"])
        self.assertEqual({"header_visible": True, "header_state": "Hata"}, payload["listening"])

    def test_brand_logo_toggles_primary_task_navigation(self) -> None:
        payload = self.run_qml(
            """
from PySide6.QtCore import QMetaObject
root = engine.rootObjects()[0]
deadline = time.perf_counter() + .4
while time.perf_counter() < deadline: app.processEvents(); time.sleep(.002)
def find_item(item, name):
    if item.objectName() == name: return item
    for child in item.childItems():
        found = find_item(child, name)
        if found is not None: return found
    return None
button = find_item(root.contentItem(), "primaryMenuButton")
navigation = root.findChild(QObject, "primaryNavigation")
items = [find_item(root.contentItem(), "workspaceNavigation" + str(index)) for index in range(5)]
initial = {"open": root.property("navigationOpen"), "visible": navigation.property("visible"),
           "busy": view_model.busy, "playing": view_model.playing}
assert QMetaObject.invokeMethod(button, "clicked")
deadline = time.perf_counter() + .4
while time.perf_counter() < deadline: app.processEvents(); time.sleep(.002)
opened = {"open": root.property("navigationOpen"), "visible": navigation.property("visible"),
          "width": navigation.property("width"), "items": [item.property("visible") for item in items],
          "busy": view_model.busy, "playing": view_model.playing}
assert QMetaObject.invokeMethod(button, "clicked")
deadline = time.perf_counter() + .4
while time.perf_counter() < deadline: app.processEvents(); time.sleep(.002)
closed = {"open": root.property("navigationOpen"), "visible": navigation.property("visible"),
          "width": navigation.property("width")}
payload = {"initial": initial, "opened": opened, "closed": closed}
view_model.shutdown(); root.close()
print(json.dumps(payload))
"""
        )
        self.assertEqual({"open": False, "visible": False, "busy": False, "playing": False}, payload["initial"])
        self.assertTrue(payload["opened"]["open"])
        self.assertTrue(payload["opened"]["visible"])
        self.assertGreater(payload["opened"]["width"], 70)
        self.assertEqual([True] * 5, payload["opened"]["items"])
        self.assertFalse(payload["opened"]["busy"])
        self.assertFalse(payload["opened"]["playing"])
        self.assertFalse(payload["closed"]["open"])
        self.assertFalse(payload["closed"]["visible"])
        self.assertLess(payload["closed"]["width"], 1.0)

    def test_detection_symbol_toggles_receiver_options_without_starting_an_operation(self) -> None:
        payload = self.run_qml(
            """
from PySide6.QtCore import QMetaObject
root = engine.rootObjects()[0]
root.setProperty("navigationOpen", True)
deadline = time.perf_counter() + .4
while time.perf_counter() < deadline: app.processEvents(); time.sleep(.002)
def find_item(item, name):
    if item.objectName() == name: return item
    for child in item.childItems():
        found = find_item(child, name)
        if found is not None: return found
    return None
button = find_item(root.contentItem(), "workspaceNavigation0")
panel = root.findChild(QObject, "sourcePanel")
initial = {"open": root.property("sourcePanelOpen"), "visible": panel.property("visible"),
           "busy": view_model.busy, "playing": view_model.playing}
assert QMetaObject.invokeMethod(button, "clicked")
deadline = time.perf_counter() + .4
while time.perf_counter() < deadline: app.processEvents(); time.sleep(.002)
opened = {"open": root.property("sourcePanelOpen"), "visible": panel.property("visible"),
          "workspace": root.property("workspace"), "task": root.property("spectrumTaskTab"),
          "domain": root.property("operatingDomain"), "busy": view_model.busy,
          "playing": view_model.playing}
assert QMetaObject.invokeMethod(button, "clicked")
deadline = time.perf_counter() + .4
while time.perf_counter() < deadline: app.processEvents(); time.sleep(.002)
closed = {"open": root.property("sourcePanelOpen"), "visible": panel.property("visible")}
root.setProperty("workspace", 3); app.processEvents()
assert QMetaObject.invokeMethod(button, "clicked")
deadline = time.perf_counter() + .4
while time.perf_counter() < deadline: app.processEvents(); time.sleep(.002)
returned = {"open": root.property("sourcePanelOpen"), "workspace": root.property("workspace"),
            "task": root.property("spectrumTaskTab"), "domain": root.property("operatingDomain")}
payload = {"initial": initial, "opened": opened, "closed": closed, "returned": returned}
view_model.shutdown(); root.close()
print(json.dumps(payload))
"""
        )
        self.assertEqual({"open": False, "visible": False, "busy": False, "playing": False}, payload["initial"])
        self.assertEqual(
            {"open": True, "visible": True, "workspace": 0, "task": 0, "domain": "ED", "busy": False, "playing": False},
            payload["opened"],
        )
        self.assertEqual({"open": False, "visible": False}, payload["closed"])
        self.assertEqual({"open": True, "workspace": 0, "task": 0, "domain": "ED"}, payload["returned"])

    def test_application_starts_waiting_without_automatic_receiver_probe(self) -> None:
        payload = self.run_qml(
            """
root = engine.rootObjects()[0]
root.setProperty("sourcePanelOpen", True)
app.processEvents()
header_badge = root.findChild(QObject, "receiverHeaderBadge")
settings_badge = root.findChild(QObject, "receiverSettingsBadge")
payload = {"header": header_badge.property("state"), "settings": settings_badge.property("state"),
           "source_state": view_model.sourceState, "error": view_model.errorMessage,
           "status": view_model.statusMessage}
view_model.shutdown(); root.close()
print(json.dumps(payload))
"""
        )
        self.assertEqual("Bekliyor", payload["header"])
        self.assertEqual("Bekliyor", payload["settings"])
        self.assertEqual("Kullanılmıyor", payload["source_state"])
        self.assertEqual("", payload["error"])
        self.assertEqual("Alıcı bağlantısı bekleniyor.", payload["status"])

    def test_missing_receiver_state_is_rendered_as_error_in_both_badges(self) -> None:
        payload = self.run_qml(
            """
root = engine.rootObjects()[0]
root.setProperty("sourcePanelOpen", True)
view_model._source_state = "Hata"
view_model._error_title = "Alıcı bağlı değil"
view_model._error_message = "Yapılandırılmış alıcı bulunamadı. USB bağlantısını denetleyin."
view_model._status_message = view_model._error_message
view_model.stateChanged.emit(); app.processEvents()
header_badge = root.findChild(QObject, "receiverHeaderBadge")
settings_badge = root.findChild(QObject, "receiverSettingsBadge")
payload = {"header": header_badge.property("state"), "settings": settings_badge.property("state")}
view_model.shutdown(); root.close()
print(json.dumps(payload))
"""
        )
        self.assertEqual("Hata", payload["header"])
        self.assertEqual("Hata", payload["settings"])

    def test_live_status_guards_detection_fields_when_list_is_empty(self) -> None:
        source = QML.read_text(encoding="utf-8")
        self.assertIn("readonly property var leadingDetection:", source)
        self.assertIn('leadingDetection !== null ? "P/N "', source)

    def test_rx_only_status_hides_the_inapplicable_measurement_action(self) -> None:
        payload = self.run_qml(
            """
root = engine.rootObjects()[0]
root.setProperty("workspace", 0)
root.setProperty("sourcePanelOpen", False)
root.setProperty("spectrumTaskTab", 0)
button = root.findChild(QObject, "measurementOpenButton")
view_model.setSourceMode("hackrf")
view_model._live_fpga_enabled = False
view_model.stateChanged.emit(); app.processEvents()
rx_only_visible = button.property("visible")
payload = {"button_found": button is not None, "rx_only_visible": rx_only_visible}
view_model.shutdown(); root.close()
print(json.dumps(payload))
"""
        )
        self.assertTrue(payload["button_found"])
        self.assertFalse(payload["rx_only_visible"])

    def test_native_spectrum_keeps_full_bins_and_resize_does_not_append_history(self) -> None:
        payload = self.run_qml(
            """
view_model.openSigmf(str(fixture))
deadline=time.perf_counter()+6
while time.perf_counter()<deadline and (view_model.busy or not view_model.spectrumValues): app.processEvents(); time.sleep(.002)
before = view_model.spectralDisplay.count
view_model.setSpectrumViewportWidth(1200)
root = engine.rootObjects()[0]
root.setProperty("spectrumViewStart", .45)
root.setProperty("spectrumViewEnd", .55)
for _ in range(20): app.processEvents()
payload = {"bins": view_model.spectralDisplay.latest.size, "before": before,
           "after": view_model.spectralDisplay.count, "floor": view_model.spectrumMinDb,
           "ceiling": view_model.spectrumMaxDb, "peak": float(view_model.spectralDisplay.latest.max())}
view_model.shutdown(); root.close()
print(json.dumps(payload))
"""
        )
        self.assertEqual(4096, payload["bins"])
        self.assertEqual(payload["before"], payload["after"])
        self.assertGreater(payload["ceiling"], payload["peak"])

    def test_spectrum_display_reduction_preserves_interval_maxima(self) -> None:
        values = np.asarray([-9.0, -4.0, -8.0, -3.0, -7.0, -5.0, -6.0, -2.0, -10.0, -1.0])
        reduced = _reduce_display_max(values, 3)
        np.testing.assert_array_equal(np.asarray([-4.0, -3.0, -1.0]), reduced)

    def run_qml(self, body: str, *, timeout: float = 20.0) -> dict[str, object]:
        code = "\n".join(
            (
                "import json, os, time",
                "from pathlib import Path",
                "os.environ.pop('EH_CONSOLE_DEVELOPER_MODE', None)",
                "os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')",
                "os.environ.setdefault('QT_QUICK_BACKEND', 'software')",
                "from PySide6.QtCore import QObject",
                "from PySide6.QtQuick import QQuickWindow",
                "from app.operator_console.quick_application import build_quick_application",
                f"fixture = Path({str(FIXTURE)!r})",
                "app, engine, view_model = build_quick_application(['app-f-test'])",
                textwrap.dedent(body),
            )
        )
        environment = os.environ.copy()
        environment["QT_QPA_PLATFORM"] = "offscreen"
        environment["QT_QUICK_BACKEND"] = "software"
        environment["PYTHONIOENCODING"] = "utf-8"
        process = subprocess.run(
            [sys.executable, "-B", "-c", code],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            check=False,
        )
        self.assertEqual(0, process.returncode, process.stdout + process.stderr)
        return json.loads(process.stdout.strip().splitlines()[-1])

    def test_fixed_band_fields_follow_actual_requested_settings_after_manual_edit(self) -> None:
        payload = self.run_qml(
            """
root = engine.rootObjects()[0]
view_model.setSourceMode("hackrf")
root.setProperty("rfSearchMode", False)
app.processEvents()
center = root.findChild(QObject, "liveCenterInput")
lna = root.findChild(QObject, "liveLnaInput")
vga = root.findChild(QObject, "liveVgaInput")
center.setProperty("text", "104650000")
view_model._live_receive_settings = {"center_hz": 6_000_000_000, "lna_db": 8, "vga_db": 24}
view_model.liveReceiveSettingsChanged.emit()
view_model._busy = True
view_model.stateChanged.emit()
app.processEvents()
payload = {"center": center.property("text"), "lna": lna.property("currentText"), "vga": vga.property("currentText"),
           "enabled": [center.property("enabled"), lna.property("enabled"), vga.property("enabled")]}
view_model._busy = False
view_model.shutdown(); root.close()
print(json.dumps(payload))
"""
        )
        self.assertEqual("6000000000", payload["center"])
        self.assertEqual("8", payload["lna"])
        self.assertEqual("24", payload["vga"])
        self.assertEqual([False, False, False], payload["enabled"])

    def test_qml_product_loads_at_minimum_screen(self) -> None:
        payload = self.run_qml(
            """
root = engine.rootObjects()[0]
root.setProperty("navigationOpen", True)
root.setWidth(1180); root.setHeight(680); app.processEvents()
minimum_width=root.width(); minimum_height=root.height()
root.setProperty("spectrumCursorNormalized",.5); root.setProperty("spectrumCursorVisible",True); app.processEvents()
root.zoomSpectrum(.5,.5); app.processEvents()
zoomed=[root.property("spectrumViewStart"),root.property("spectrumViewEnd")]
root.spectrumViewBack(); app.processEvents()
back=[root.property("spectrumViewStart"),root.property("spectrumViewEnd")]
root.spectrumViewForward(); app.processEvents()
forward=[root.property("spectrumViewStart"),root.property("spectrumViewEnd")]
root.resetSpectrumView(); app.processEvents()
workspaces=[]
for index in range(4):
    root.setProperty("workspace",index); app.processEvents(); workspaces.append(root.property("workspace"))
root.setProperty("workspace",0); root.setProperty("spectrumTaskTab",1); app.processEvents()
task_tab=root.property("spectrumTaskTab")
root.setProperty("workspace",3)
for _ in range(3): app.processEvents()
workspace_focus=app.focusObject().objectName() if app.focusObject() is not None else ""
minimum_body_size=root.property("uiBodyTextSize")
root.setWidth(1920); app.processEvents()
fullhd_body_size=root.property("uiBodyTextSize")
payload = {"width": minimum_width, "height": minimum_height, "workspace": root.property("workspace"),"zoomed":zoomed,"back":back,"forward":forward,"reset":[root.property("spectrumViewStart"),root.property("spectrumViewEnd")],"workspaces":workspaces,"task_tab":task_tab,"workspace_focus":workspace_focus,"minimum_body_size":minimum_body_size,"fullhd_body_size":fullhd_body_size,"measurement_scroll":root.findChild(QObject,"measurementScroll") is not None,"detection_list":root.findChild(QObject,"detectionList") is not None,"listening_scroll":root.findChild(QObject,"listeningSettingsScroll") is not None,"pipeline_list":root.findChild(QObject,"pipelineList") is not None,"system_log":root.findChild(QObject,"systemLog") is not None}
view_model.shutdown(); root.close()
print(json.dumps(payload, ensure_ascii=False))
"""
        )
        self.assertGreaterEqual(payload["width"], 1180)
        self.assertGreaterEqual(payload["height"], 680)
        self.assertEqual(3, payload["workspace"])
        self.assertEqual([0.25, 0.75], payload["zoomed"])
        self.assertEqual([0.0, 1.0], payload["back"])
        self.assertEqual([0.25, 0.75], payload["forward"])
        self.assertEqual([0.0, 1.0], payload["reset"])
        self.assertEqual([0, 1, 2, 3], payload["workspaces"])
        self.assertEqual(1, payload["task_tab"])
        self.assertEqual("workspaceNavigation4", payload["workspace_focus"])
        self.assertEqual(10, payload["minimum_body_size"])
        self.assertEqual(11, payload["fullhd_body_size"])
        self.assertTrue(payload["measurement_scroll"])
        self.assertTrue(payload["detection_list"])
        self.assertTrue(payload["listening_scroll"])
        self.assertTrue(payload["pipeline_list"])
        self.assertTrue(payload["system_log"])

    def test_frequency_survey_screen_defaults_to_full_range_without_claiming_capture(self) -> None:
        payload = self.run_qml(
            """
root = engine.rootObjects()[0]
root.setWidth(1180); root.setHeight(680)
root.setProperty("rfSearchMode", True)
for _ in range(5): app.processEvents()
panel = root.findChild(QObject,"frequencySurveyView")
payload = {"visible":panel.property("visible"),
           "lower":root.findChild(QObject,"surveyLowerMHz").property("text"),
           "upper":root.findChild(QObject,"surveyUpperMHz").property("text"),
           "start":root.findChild(QObject,"surveyStart").property("enabled"),
           "stop":root.findChild(QObject,"surveyStop").property("enabled"),
           "monitor":root.findChild(QObject,"surveyMonitor").property("enabled"),
           "source_panel":root.findChild(QObject,"sourcePanel").property("visible"),
           "coverage":view_model.survey.coverageText,"count":view_model.survey.observationModel.rowCount()}
view_model.shutdown(); root.close()
print(json.dumps(payload,ensure_ascii=False))
"""
        )
        self.assertTrue(payload["visible"])
        self.assertEqual(("1", "6000"), (payload["lower"], payload["upper"]))
        self.assertFalse(payload["start"])
        self.assertFalse(payload["stop"])
        self.assertFalse(payload["monitor"])
        self.assertFalse(payload["source_panel"])
        self.assertEqual(0, payload["count"])
        self.assertEqual("0 / 9999 pencere tarandı · 0 hata", payload["coverage"])

    def test_parameter_navigation_preserves_selection_zoom_and_task_layout(self) -> None:
        payload = self.run_qml(
            """
from PySide6.QtCore import QMetaObject
root = engine.rootObjects()[0]
root.setWidth(1180); root.setHeight(680)
root.setProperty("navigationOpen", True)
root.setProperty("sourcePanelOpen", True)
def settle():
    deadline = time.perf_counter() + .4
    while time.perf_counter() < deadline: app.processEvents(); time.sleep(.002)
def click(name):
    def find_item(item):
        if item.objectName() == name: return item
        for child in item.childItems():
            found = find_item(child)
            if found is not None: return found
        return None
    button = find_item(root.contentItem())
    assert button is not None, name
    assert QMetaObject.invokeMethod(button, "clicked"), name
    settle()
def layout():
    return {
        "source": root.findChild(QObject, "sourcePanel").property("visible"),
        "waterfall": root.findChild(QObject, "waterfallPanel").property("visible"),
        "detections": root.findChild(QObject, "detectionList").property("visible"),
        "measurement": root.findChild(QObject, "measurementScroll").property("visible"),
        "width": root.findChild(QObject, "signalTaskPanel").property("width"),
    }
settle()
detection_layout = layout()
click("workspaceNavigation1")
empty_action = root.findChild(QObject, "measurementChooseDetection").property("text")
click("measurementChooseDetection")
returned_task = root.property("spectrumTaskTab")
view_model.openSigmf(str(fixture))
deadline = time.perf_counter() + 6
while time.perf_counter() < deadline and (view_model.busy or not view_model.sourceReady): app.processEvents(); time.sleep(.002)
view_model.startScan()
while time.perf_counter() < deadline and (view_model.frameIndex < 4 or not any(x["stateKey"] == "confirmed" for x in view_model.detections)): app.processEvents(); time.sleep(.002)
view_model.pause()
while view_model.busy and time.perf_counter() < deadline: app.processEvents(); time.sleep(.002)
selected = next(x["eventId"] for x in view_model.detections if x["stateKey"] == "confirmed")
view_model.selectDetection(int(selected))
root.zoomSpectrum(.5, .5)
click("workspaceNavigation1")
parameter_layout = layout()
parameter_focus = app.focusObject().objectName()
selected_action = root.findChild(QObject, "measurementChooseDetection").property("text")
click("workspaceNavigation2")
listening_workspace = root.property("workspace")
click("workspaceNavigation1")
selection_after = view_model.selectedDetectionId
zoom_after = [root.property("spectrumViewStart"), root.property("spectrumViewEnd")]
click("measurementChooseDetection")
payload = {"detection": detection_layout, "parameter": parameter_layout,
           "restored": layout(), "empty_action": empty_action, "selected_action": selected_action,
           "returned_task": returned_task, "parameter_focus": parameter_focus,
           "listening_workspace": listening_workspace, "selected": selected,
           "selection_after": selection_after, "zoom_after": zoom_after}
view_model.shutdown(); root.close()
print(json.dumps(payload, ensure_ascii=False))
"""
        )
        self.assertEqual("Tespit Seç", payload["empty_action"])
        self.assertEqual("Tespiti Değiştir", payload["selected_action"])
        self.assertEqual(0, payload["returned_task"])
        self.assertEqual(1, payload["listening_workspace"])
        self.assertEqual("workspaceNavigation1", payload["parameter_focus"])
        self.assertEqual(payload["selected"], payload["selection_after"])
        self.assertEqual([.25, .75], payload["zoom_after"])
        for key in ("source", "waterfall", "detections"):
            self.assertTrue(payload["detection"][key], key)
            self.assertFalse(payload["parameter"][key], key)
            self.assertTrue(payload["restored"][key], key)
        self.assertFalse(payload["detection"]["measurement"])
        self.assertTrue(payload["parameter"]["measurement"])
        self.assertFalse(payload["restored"]["measurement"])
        self.assertGreater(payload["parameter"]["width"], payload["detection"]["width"])

    def test_et_domain_binds_only_verified_offline_models(self) -> None:
        payload = self.run_qml(
            """
root = engine.rootObjects()[0]
root.setWidth(1180); root.setHeight(680); root.setProperty("operatingDomain", "ET"); app.processEvents()
surface={"domain":root.property("operatingDomain"),"workspace":root.property("workspace"),"workspace_item":root.findChild(QObject,"etWorkspace") is not None,"runs":[root.findChild(QObject,name) is not None for name in ("etContinuousRun","etInterleavedRun","etAnalogRun","etGnssValidate")]}
view_model.runETTask("continuous","barrage")
continuous={"status":view_model.etStatus,"title":view_model.etResultTitle,"primary":len(view_model.etPrimaryValues),"secondary":len(view_model.etSecondaryValues),"metrics":list(view_model.etMetricRows)}
view_model.runETTask("interleaved","present")
interleaved={"status":view_model.etStatus,"timeline":list(view_model.etTimeline),"metrics":list(view_model.etMetricRows),"has_gap":any(value is None for value in view_model.etPrimaryValues)}
view_model.runETTask("analog","NFM")
analog={"status":view_model.etStatus,"metrics":list(view_model.etMetricRows)}
view_model.validateETGNSS(39.9334,32.8597,"2026-08-16T12:00:00Z","3,8,63")
gnss={"status":view_model.etStatus,"detail":view_model.etResultDetail,"metrics":list(view_model.etMetricRows)}
payload={"surface":surface,"continuous":continuous,"interleaved":interleaved,"analog":analog,"gnss":gnss,"transmit":hasattr(view_model,"transmit")}
view_model.shutdown(); root.close()
print(json.dumps(payload,ensure_ascii=False))
"""
        )
        self.assertEqual({"domain": "ET", "workspace": 4, "workspace_item": True, "runs": [True] * 4}, payload["surface"])
        self.assertEqual("TAMAMLANDI", payload["continuous"]["status"])
        self.assertEqual(768, payload["continuous"]["primary"])
        self.assertEqual(768, payload["continuous"]["secondary"])
        self.assertEqual(["DİNLE", "DİNLE", "GECİKME", "GÖREV", "KORUMA", "DİNLE", "DİNLE", "DİNLE"], [item["state"] for item in payload["interleaved"]["timeline"]])
        self.assertTrue(payload["interleaved"]["has_gap"])
        self.assertIn({"label": "Görev çevrimi", "value": "%12.5"}, payload["interleaved"]["metrics"])
        self.assertIn({"label": "Loopback uyumu", "value": "1.000000"}, payload["analog"]["metrics"])
        self.assertEqual("TAMAMLANDI", payload["gnss"]["status"])
        self.assertIn("Dalga şekli üretilmedi", payload["gnss"]["detail"])
        self.assertIn({"label": "Dalga şekli", "value": "YOK"}, payload["gnss"]["metrics"])
        self.assertFalse(payload["transmit"])

    def test_system_diagnostics_use_real_runtime_state_and_safe_release_boundary(self) -> None:
        payload = self.run_qml(
            """
from unittest.mock import patch
from app.operator_console.quick_view_model import OperatorViewModel
initial_blocks=list(view_model.pipelineBlocks)
disabled_open=view_model.openImplementationLocation("source","host")
view_model.openSigmf(str(fixture))
deadline=time.perf_counter()+6
while time.perf_counter()<deadline and (view_model.busy or not view_model.sourceReady): app.processEvents(); time.sleep(.002)
ready_blocks=list(view_model.pipelineBlocks)
view_model.startScan(); app.processEvents()
running_blocks=list(view_model.pipelineBlocks)
view_model.pause(); app.processEvents()
developer_view_model=OperatorViewModel(developer_mode=True)
with patch("app.operator_console.quick_view_model.QDesktopServices.openUrl", return_value=True):
    enabled_host_open=developer_view_model.openImplementationLocation("source","host")
    enabled_rtl_open=developer_view_model.openImplementationLocation("preprocess","rtl")
    invalid_open=developer_view_model.openImplementationLocation("../../outside","host")
developer_view_model.shutdown()
payload={"developer_mode":view_model.developerMode,"disabled_open":disabled_open,"enabled_host_open":enabled_host_open,"enabled_rtl_open":enabled_rtl_open,"invalid_open":invalid_open,"initial":initial_blocks,"ready":ready_blocks,"running":running_blocks,"log":view_model.eventLog}
view_model.shutdown(); engine.rootObjects()[0].close()
print(json.dumps(payload,ensure_ascii=False))
"""
        )
        self.assertFalse(payload["developer_mode"])
        self.assertFalse(payload["disabled_open"])
        self.assertTrue(payload["enabled_host_open"])
        self.assertTrue(payload["enabled_rtl_open"])
        self.assertFalse(payload["invalid_open"])
        self.assertEqual(7, len(payload["initial"]))
        self.assertTrue(all(item["runtime"] == "HOST" for item in payload["ready"]))
        for item in payload["ready"]:
            for key in ("hostPath", "rtlPath"):
                if item[key]:
                    self.assertTrue((ROOT / item[key]).is_file(), item[key])
        self.assertEqual("Denetleniyor", payload["initial"][0]["state"])
        self.assertEqual("Hazır", payload["ready"][0]["state"])
        self.assertTrue(
            all(
                item["state"] == "Çalışıyor"
                for item in payload["running"]
                if item["id"] in {"preprocess", "fft_power", "regional", "temporal"}
            )
        )
        self.assertTrue(all({"sequence", "time", "level", "component", "message"} <= set(item) for item in payload["log"]))
        messages = [item["message"] for item in payload["log"]]
        self.assertIn("Sinyal taraması başlatıldı", messages)
        self.assertIn("Sinyal taraması duraklatıldı", messages)

    def test_real_sigmf_source_drives_bounded_spectrum_and_detection(self) -> None:
        payload = self.run_qml(
            """
view_model.openSigmf(str(fixture))
deadline=time.perf_counter()+6
while time.perf_counter()<deadline and (view_model.busy or not view_model.sourceReady or not view_model.spectrumValues): app.processEvents(); time.sleep(.002)
view_model.startScan()
while time.perf_counter()<deadline and not any(x["stateKey"]=="confirmed" for x in view_model.detections): app.processEvents(); time.sleep(.002)
view_model.pause()
payload={"name":view_model.sourceName,"center":view_model.centerFrequencyText,"points":len(view_model.spectrumValues),"confirmed":any(x["stateKey"]=="confirmed" for x in view_model.detections),"performance":view_model.performanceText}
view_model.shutdown(); engine.rootObjects()[0].close()
print(json.dumps(payload,ensure_ascii=False))
"""
        )
        self.assertEqual("known-tone-ci8.sigmf-meta", payload["name"])
        self.assertEqual("100 MHz", payload["center"])
        self.assertLessEqual(payload["points"], 1600)
        self.assertTrue(payload["confirmed"])
        self.assertTrue(payload["performance"].startswith("İşleme p95"))

    def test_parameter_values_require_explicit_operator_action(self) -> None:
        payload = self.run_qml(
            """
view_model.openSigmf(str(fixture))
deadline=time.perf_counter()+6
while time.perf_counter()<deadline and (view_model.busy or not view_model.sourceReady): app.processEvents(); time.sleep(.002)
view_model.startScan()
while time.perf_counter()<deadline and (view_model.frameIndex < 4 or not any(x["stateKey"]=="confirmed" for x in view_model.detections)): app.processEvents(); time.sleep(.002)
view_model.pause()
while view_model.busy and time.perf_counter()<deadline: app.processEvents(); time.sleep(.002)
confirmed=next(x for x in view_model.detections if x["stateKey"]=="confirmed")
view_model.selectDetection(int(confirmed["eventId"])); before=list(view_model.parameterRows)
selection=[view_model.selectedRegionStartNormalized,view_model.selectedRegionPeakNormalized,view_model.selectedRegionEndNormalized]
draft=[view_model.analysisSpanStartNormalized,view_model.analysisSpanEndNormalized]
view_model.setAnalysisSpanDraftNormalized(selection[1]-.004,selection[1]+.004)
drawn_draft=[view_model.analysisSpanStartNormalized,view_model.analysisSpanEndNormalized]
drawn_status=view_model.statusMessage
view_model.confirmAnalysisSpan(float(view_model.analysisLowerMHzText), float(view_model.analysisUpperMHzText))
view_model.requestMeasurement()
while view_model.busy and time.perf_counter()<deadline: app.processEvents(); time.sleep(.002)
payload={"before":before,"after":view_model.parameterRows,"span_confirmed":view_model.analysisSpanConfirmed,"selection":selection,"draft":draft,"drawn_draft":drawn_draft,"drawn_status":drawn_status,"selected_title":view_model.selectedDetectionTitle,"selected_frequency":view_model.selectedDetectionFrequencyText,"selected_contrast":view_model.selectedDetectionContrastText,"selected_state":view_model.selectedDetectionStateText}
view_model.shutdown(); engine.rootObjects()[0].close()
print(json.dumps(payload,ensure_ascii=False))
"""
        )
        self.assertEqual([], payload["before"])
        self.assertTrue(payload["span_confirmed"])
        self.assertTrue(payload["after"])
        self.assertLessEqual(payload["selection"][0], payload["selection"][1])
        self.assertLessEqual(payload["selection"][1], payload["selection"][2])
        self.assertGreaterEqual(payload["draft"][0], 0.0)
        self.assertLessEqual(payload["draft"][1], 1.0)
        self.assertLess(payload["drawn_draft"][0], payload["selection"][1])
        self.assertGreater(payload["drawn_draft"][1], payload["selection"][1])
        self.assertIn("spektrum üzerinden", payload["drawn_status"])
        self.assertTrue(payload["selected_title"].startswith("Tespit #"))
        self.assertNotEqual("—", payload["selected_frequency"])
        self.assertTrue(payload["selected_contrast"].endswith("dB"))
        self.assertEqual("Kararlı", payload["selected_state"])
        self.assertEqual("Emisyon merkez frekansı", payload["after"][0]["label"])
        labels = [row["label"] for row in payload["after"]]
        self.assertNotIn("Tepe bin gücü", labels)
        self.assertIn("Gözlenen taşıyıcı frekansı", labels)
        self.assertIn("SNR kestirimi", labels)
        self.assertIn("Sinyal türü", labels)
        self.assertIn("Güç referansı", labels)

    def test_direction_result_is_blocked_without_real_source(self) -> None:
        payload = self.run_qml(
            """
view_model.addDirectionMeasurement(90.0,"north",0.0)
payload={"points":view_model.directionPoints,"relative":view_model.relativeArrivalText,"status":view_model.statusMessage}
view_model.shutdown(); engine.rootObjects()[0].close()
print(json.dumps(payload,ensure_ascii=False))
"""
        )
        self.assertEqual([], payload["points"])
        self.assertEqual("—", payload["relative"])
        self.assertIn("gerçek bir kaynak", payload["status"])

    def test_direction_session_locks_reference_and_clears_on_source_change(self) -> None:
        payload = self.run_qml(
            f"""
view_model.openSigmf(str(fixture))
deadline=time.perf_counter()+8
while time.perf_counter()<deadline and (view_model.busy or not view_model.sourceReady or not view_model.spectrumValues): app.processEvents(); time.sleep(.002)
view_model.addDirectionMeasurement(0.0,"north",0.0)
first={{"count":view_model.directionMeasurementCount,"distinct":view_model.directionDistinctAngleCount,"reference":view_model.directionReferenceText,"power":view_model.directionFramePowerText,"row":view_model.directionPoints[0]}}
view_model.addDirectionMeasurement(90.0,"none",0.0)
locked={{"count":view_model.directionMeasurementCount,"status":view_model.statusMessage}}
view_model.openSigmf({str(LISTENING_FIXTURE)!r})
deadline=time.perf_counter()+8
while time.perf_counter()<deadline and (view_model.busy or not view_model.sourceReady or not view_model.spectrumValues): app.processEvents(); time.sleep(.002)
payload={{"first":first,"locked":locked,"cleared":view_model.directionMeasurementCount,"reference_after":view_model.directionReferenceText}}
view_model.shutdown(); engine.rootObjects()[0].close()
print(json.dumps(payload,ensure_ascii=False))
"""
        )
        self.assertEqual(1, payload["first"]["count"])
        self.assertEqual(1, payload["first"]["distinct"])
        self.assertEqual("Gerçek kuzey · anten 0°", payload["first"]["reference"])
        self.assertNotEqual("—", payload["first"]["power"])
        self.assertIn("known-tone-ci8.sigmf-meta", payload["first"]["row"]["source"])
        self.assertEqual("100 MHz", payload["first"]["row"]["frequency"])
        self.assertEqual(1, payload["locked"]["count"])
        self.assertIn("referansı değiştirilemez", payload["locked"]["status"])
        self.assertEqual(0, payload["cleared"])
        self.assertEqual("İlk ölçümde sabitlenir", payload["reference_after"])

    def test_confirmed_detection_prepares_truthfully_labeled_am_audio(self) -> None:
        payload = self.run_qml(
            f"""
listening_fixture=Path({str(LISTENING_FIXTURE)!r})
view_model.openSigmf(str(listening_fixture))
deadline=time.perf_counter()+6
while time.perf_counter()<deadline and (view_model.busy or not view_model.sourceReady): app.processEvents(); time.sleep(.002)
view_model.startScan()
while time.perf_counter()<deadline and not any(x["stateKey"]=="confirmed" for x in view_model.detections): app.processEvents(); time.sleep(.002)
view_model.pause()
while view_model.busy and time.perf_counter()<deadline: app.processEvents(); time.sleep(.002)
confirmed=next(x for x in view_model.detections if x["stateKey"]=="confirmed")
view_model.selectDetection(int(confirmed["eventId"]))
view_model.requestListening("am",view_model.selectedDetectionOffsetKHz,16.0,.8)
while view_model.busy and time.perf_counter()<deadline: app.processEvents(); time.sleep(.002)
payload={{"ready":view_model.listeningReady,"short":view_model.listeningShortPreview,"rows":view_model.listeningRows,"waveform":len(view_model.listeningWaveform),"state":view_model.listeningState,"playback_state":view_model.listeningPlaybackState,"playback_position":view_model.listeningPlaybackPositionText,"playback_duration":view_model.listeningPlaybackDurationText,"playback_progress":view_model.listeningPlaybackProgress,"output_state":view_model.listeningOutputState}}
view_model.shutdown(); engine.rootObjects()[0].close()
print(json.dumps(payload,ensure_ascii=False))
"""
        )
        self.assertTrue(payload["ready"], payload)
        self.assertTrue(payload["short"])
        self.assertGreater(payload["waveform"], 100)
        self.assertIn("Kısa önizleme", payload["state"])
        self.assertEqual("Oynatmaya hazır", payload["playback_state"])
        self.assertEqual("00:00.0", payload["playback_position"])
        self.assertNotEqual("00:00.0", payload["playback_duration"])
        self.assertEqual(0.0, payload["playback_progress"])
        self.assertIn(payload["output_state"], {"Ses çıkışı hazır", "Ses çıkışı yok · WAV kullanılabilir"})
        rows = {row["label"]: row["value"] for row in payload["rows"]}
        self.assertEqual("AM", rows["Demodülasyon"])
        self.assertEqual("48 kHz · mono PCM16", rows["Ses çıkışı"])

    def test_qml_has_keyboard_accessibility_and_no_future_source_controls(self) -> None:
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(QML.parent.glob("*.qml"))
        )
        for required in (
            "Accessible.name",
            'sequence: "Space"',
            'root.workspace === 0 && root.spectrumTaskTab === 0 && operatorViewModel.sourceReady',
            'objectName: "workspaceNavigation" + index',
            'Accessible.role: Accessible.StaticText',
            'property int uiBodyTextSize: width >= 1600 ? 11 : 10',
            "Bu filtreyle eşleşen olay yok",
            "Alıcıyı Denetle",
            "Taramayı Başlat",
            "Taramayı Durdur",
            'title: "BÂZ"',
            'text: "BÂZ"',
            'source: "../assets/baz-logo-glow.png"',
            "ALICI AYARLARI",
            "Taramayı başlatınca canlı spektrum burada görünür",
            "Taramayı başlatınca spektrogram burada görünür",
            "TESPİT ALANI",
            "SİNYAL TESPİT EDİLDİ",
            "doğrulanmış gözlem",
            "operatorViewModel.errorTitle",
            "zoomSpectrum",
            "panSpectrum",
            "spectrumViewBack",
            "setAnalysisSpanDraftNormalized",
            "property int spectrumTaskTab: 0",
            '"title": "Sinyal Tespiti"',
            '"title": "Parametre Çıkarımı"',
            "operatorViewModel.listeningSelectionReady",
            "operatorViewModel.liveListeningBufferText",
            "onPressed: operatorViewModel.selectDetection",
            'objectName: "detectionList"',
            "operatorViewModel.detectionModel",
            "paintDetectionGuides",
            'objectName: "measurementScroll"',
            'objectName: "listeningSettingsScroll"',
            'objectName: "listeningTransport"',
            'objectName: "listeningResultList"',
            "Oynatma konumu, salt okunur",
            'objectName: "directionSettingsScroll"',
            'objectName: "directionCompass"',
            'objectName: "directionMeasurementList"',
            "Kare Gücünü Kaydet",
            'objectName: "pipelineList"',
            'objectName: "systemLog"',
            "SALT OKUNUR",
            "BİLEŞEN AYRINTISI",
            "Salt okunur · komut çalıştırmaz",
            "Kanalı Hazırla",
            'objectName: "emptySpectrumMessage"',
            'objectName: "emptyDetectionMessage"',
            "WAV Dışa Aktar",
        ):
            self.assertIn(required, text)
        self.assertNotIn("Listeyi tut", text)
        self.assertNotIn("detectionHoldButton", text)
        for removed_operator_control in (
            "SigMF Kaydı",
            "HackRF Canlı RX",
            "Olay Konsolu",
            'objectName: "eventConsoleList"',
            'sequence: "Ctrl+O"',
            'sequence: "Alt+Left"',
            "FREKANS GÖRÜNÜMÜ",
            "Tepe Tut",
            "Ölçeği Uydur",
            "Animasyon\\nStandart",
            'sequence: "Ctrl+B"',
            "Kaynak panelini gizle",
            "ELEKTRONİK HARP",
            "Operatör Konsolu",
            "Canlı alım kuyruğu",
            "Alıcı bekleniyor",
            "Henüz ölçüm yok",
            "ANLIK · dBFS",
            "Görüntü verisi",
            "BAĞLANTI BEKLENİYOR",
            "FPGA tespit penceresi",
            "SPEKTRUMLA BAĞLI",
            'objectName: "detectionCandidateButton"',
            'fillText("İZLEME"',
        ):
            self.assertNotIn(removed_operator_control, text)
        no_data_guard = text.index("if (operatorViewModel.spectrumPointCount < 2) return")
        fpga_window_guide = text.index("operatorViewModel.liveDetectionStartNormalized")
        self.assertLess(no_data_guard, fpga_window_guide)
        for forbidden in ("LIVE GNSS", "HOST/SYNTHETIC", "Simülasyon", "demo", "mock"):
            self.assertNotIn(forbidden, text)
        self.assertNotIn("startHackrfCapture", text)

    def test_release_entry_point_does_not_probe_receiver_automatically(self) -> None:
        source = (ROOT / "app" / "operator_console" / "quick_application.py").read_text(encoding="utf-8")
        self.assertIn("auto_probe_hackrf=False", source)
        self.assertNotIn("build_quick_application([sys.argv[0]], auto_probe_hackrf=True)", source)


if __name__ == "__main__":
    unittest.main()
