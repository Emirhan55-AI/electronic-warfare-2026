"""Same-snapshot listening comparison and measured speech filter regressions."""

from dataclasses import replace
from unittest.mock import patch

import numpy as np
import pytest

from algorithms.monitoring import AnalogMonitor, AnalogMonitorConfig, MonitoringError
from algorithms.monitoring.dsp import _remove_voice_rumble
from app.operator_console.quick_listening_actions import _prepare_audio


def test_voice_filter_rejects_rumble_and_preserves_speech_band():
    time = np.arange(48_000) / 48_000
    frequencies = (50, 100, 300, 1000, 2500)
    source = sum(np.sin(2 * np.pi * f * time) for f in frequencies)
    filtered = _remove_voice_rumble(source)
    for frequency in frequencies:
        basis = np.exp(-2j * np.pi * frequency * time[4800:-4800])
        gain = abs(np.mean(filtered[4800:-4800] * basis)) / abs(np.mean(source[4800:-4800] * basis))
        gain_db = 20 * np.log10(gain)
        assert gain_db < -40 if frequency <= 100 else abs(gain_db) < 0.2


@pytest.mark.parametrize("mode", ["am", "nfm"])
def test_voice_filter_is_applied_and_chunk_independent(mode):
    rate = 48_000
    time = np.arange(5 * rate) / rate
    voice = np.sin(2 * np.pi * 1000 * time)
    hum = np.sin(2 * np.pi * 100 * time)
    iq = ((0.6 + 0.1 * (voice + hum)) * np.exp(2j * np.pi * 8000 * time)
          if mode == "am" else
          0.6 * np.exp(2j * np.pi * (8000 * time + np.cumsum(500 * (voice + hum)) / rate)))
    config = AnalogMonitorConfig(mode, rate, 8000, 16000, voice_filter=True)
    monitor = AnalogMonitor()
    filtered = monitor.process_continuous(iq, config)
    chunked = monitor.process_continuous(tuple(iq[i:i + 4096] for i in range(0, len(iq), 4096)), config)
    unfiltered = monitor.process_continuous(iq, replace(config, voice_filter=False))
    assert filtered.voice_filter and filtered.clipping_count == 0
    assert filtered.pcm16 == chunked.pcm16
    # Independent DFT projections: normalization cancels in the hum/voice ratio.
    def ratio(audio):
        audio = audio[4800:-4800]
        t = np.arange(audio.size) / 48000
        amplitude = lambda f: abs(np.mean(audio * np.exp(-2j * np.pi * f * t)))
        return amplitude(100) / amplitude(1000)
    assert ratio(filtered.audio) < 0.02 * ratio(unfiltered.audio)
    assert filtered.channel_power_dbfs_trace == unfiltered.channel_power_dbfs_trace
    assert filtered.residual_frequency_hz_trace == unfiltered.residual_frequency_hz_trace


def test_comparison_uses_same_iq_and_preserves_configuration():
    blocks = (np.ones(4096, dtype=complex),) * 4
    config = AnalogMonitorConfig("nfm", 192000, 24000, 16000, voice_filter=True)
    with patch.object(AnalogMonitor, "process", side_effect=["am result", "nfm result"]) as process:
        assert _prepare_audio(blocks, config, 0.7, continuous=False, compare=True) == {
            "am": "am result", "nfm": "nfm result"}
    for call, mode in zip(process.call_args_list, ("am", "nfm")):
        assert call.args[0] is blocks
        assert call.args[1] == replace(config, mode=mode)
        assert call.kwargs == {"volume": 0.7}


def test_silent_branch_does_not_hide_other_result_but_bad_iq_is_rejected():
    config = AnalogMonitorConfig("am", 192000, 24000, 16000)
    with patch.object(AnalogMonitor, "process", side_effect=[MonitoringError("insufficient_audio", "Sessiz"), "FM"]):
        assert _prepare_audio((), config, 1, continuous=False, compare=True) == {"nfm": "FM"}
    with patch.object(AnalogMonitor, "process", side_effect=MonitoringError("nonfinite_iq", "Geçersiz")):
        with pytest.raises(MonitoringError, match="Geçersiz"):
            _prepare_audio((), config, 1, continuous=False, compare=True)


def test_qml_comparison_prepares_switches_and_clears_same_recording():
    from test_app_f_quick_product import QuickProductTests, LISTENING_FIXTURE

    payload = QuickProductTests().run_qml(f'''
root = engine.rootObjects()[0]
root.setProperty("workspace", 1)
mode = root.findChild(QObject, "listeningMode")
offset = root.findChild(QObject, "listeningOffset")
default_mode = mode.property("currentIndex")
hidden_offset = not offset.property("visible")
view_model.openSigmf({str(LISTENING_FIXTURE)!r})
deadline = time.perf_counter() + 8
while time.perf_counter() < deadline and (view_model.busy or not view_model.sourceReady):
    app.processEvents(); time.sleep(.002)
view_model.startScan()
while time.perf_counter() < deadline and not any(x["stateKey"] == "confirmed" for x in view_model.detections):
    app.processEvents(); time.sleep(.002)
view_model.pause()
while view_model.busy and time.perf_counter() < deadline: app.processEvents(); time.sleep(.002)
confirmed = next(x for x in view_model.detections if x["stateKey"] == "confirmed")
view_model.selectDetection(int(confirmed["eventId"]))
from PySide6.QtCore import QMetaObject
QMetaObject.invokeMethod(root.findChild(QObject, "prepareListening"), "clicked")
while view_model.busy and time.perf_counter() < deadline: app.processEvents(); time.sleep(.002)
am_pcm = view_model._listening_result.pcm16
view_model.selectListeningComparison("nfm")
nfm_mode = view_model._listening_result.mode
voice_filter = view_model._listening_result.voice_filter
view_model.selectListeningComparison("am")
same_pcm = am_pcm == view_model._listening_result.pcm16
payload = dict(default_mode=default_mode, hidden_offset=hidden_offset,
               modes=view_model.listeningComparisonModes, state=view_model.listeningState,
               nfm_mode=nfm_mode, same_pcm=same_pcm, voice_filter=voice_filter)
view_model._listening_measured_bandwidth_hz = 120000
payload["wide_warning"] = view_model.listeningBandwidthWarning
view_model._clear_listening_parameter_basis()
payload["warning_cleared"] = view_model.listeningBandwidthWarning == ""
view_model._clear_listening("Yeni kaynak")
payload["cleared"] = view_model.listeningComparisonModes == [] and not view_model.listeningReady
view_model.shutdown(); root.close()
print(json.dumps(payload, ensure_ascii=False))
''')
    assert payload["default_mode"] == 2 and payload["hidden_offset"]
    assert payload["modes"] == ["am", "nfm"]
    assert payload["nfm_mode"] == "nfm" and payload["same_pcm"]
    assert payload["voice_filter"] and payload["cleared"]
    assert "yayın türü belirlenmedi" in payload["state"]
    assert "25 kHz" in payload["wide_warning"] and payload["warning_cleared"]
