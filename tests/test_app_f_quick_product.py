"""APP-F release UI and real-source presentation boundary tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "datasets" / "fixtures" / "phase01" / "known-tone-ci8.sigmf-meta"
LISTENING_FIXTURE = ROOT / "datasets" / "fixtures" / "phase05" / "am-tone-ci8.sigmf-meta"
QML = ROOT / "app" / "operator_console" / "qml" / "Main.qml"


class QuickProductTests(unittest.TestCase):
    def run_qml(self, body: str, *, timeout: float = 20.0) -> dict[str, object]:
        code = "\n".join(
            (
                "import json, os, time",
                "from pathlib import Path",
                "os.environ.pop('EH_CONSOLE_DEVELOPER_MODE', None)",
                "os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')",
                "os.environ.setdefault('QT_QUICK_BACKEND', 'software')",
                "from PySide6.QtCore import QObject",
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

    def test_qml_product_loads_at_minimum_screen(self) -> None:
        payload = self.run_qml(
            """
root = engine.rootObjects()[0]
root.setWidth(1180); root.setHeight(680); app.processEvents()
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
root.setProperty("workspace",3); app.processEvents()
payload = {"width": root.width(), "height": root.height(), "workspace": root.property("workspace"),"zoomed":zoomed,"back":back,"forward":forward,"reset":[root.property("spectrumViewStart"),root.property("spectrumViewEnd")],"workspaces":workspaces,"task_tab":task_tab,"measurement_scroll":root.findChild(QObject,"measurementScroll") is not None,"detection_list":root.findChild(QObject,"detectionList") is not None,"listening_scroll":root.findChild(QObject,"listeningSettingsScroll") is not None,"pipeline_list":root.findChild(QObject,"pipelineList") is not None,"system_log":root.findChild(QObject,"systemLog") is not None}
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
        self.assertTrue(payload["measurement_scroll"])
        self.assertTrue(payload["detection_list"])
        self.assertTrue(payload["listening_scroll"])
        self.assertTrue(payload["pipeline_list"])
        self.assertTrue(payload["system_log"])

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
        self.assertEqual("Kullanılmıyor", payload["initial"][0]["state"])
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
        self.assertEqual("Doğrulandı", payload["selected_state"])
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
        text = QML.read_text(encoding="utf-8")
        for required in (
            "Accessible.name",
            'sequence: "Ctrl+O"',
            'sequence: "Space"',
            "Hareketi azalt",
            "SigMF Kaydı",
            "HackRF Canlı RX",
            "SPEKTRUMLA BAĞLI",
            "zoomSpectrum",
            "panSpectrum",
            "spectrumViewBack",
            "setAnalysisSpanDraftNormalized",
            "property int spectrumTaskTab: 0",
            "onPressed: operatorViewModel.selectDetection",
            'objectName: "detectionList"',
            'objectName: "measurementScroll"',
            'objectName: "listeningSettingsScroll"',
            'objectName: "listeningTransport"',
            'objectName: "listeningResultList"',
            "Oynatma konumu, salt okunur",
            'objectName: "pipelineList"',
            'objectName: "systemLog"',
            "SALT OKUNUR SİSTEM DURUMU",
            "BİLEŞEN DENETÇİSİ",
            "Salt okunur · komut çalıştırmaz",
            'sequence: "Alt+Left"',
            "Kanal Sesini Hazırla",
            "WAV Dışa Aktar",
        ):
            self.assertIn(required, text)
        for forbidden in ("LIVE GNSS", "HOST/SYNTHETIC", "Simülasyon", "demo", "mock"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
