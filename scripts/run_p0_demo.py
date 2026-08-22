"""Launch the deterministic P0 ED/DF/ET operator demonstration."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
from PySide6.QtCore import QSignalBlocker, QTimer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from host.operator_console.laboratory import build_laboratory_application
from reference.monitoring import AnalogMonitor, AnalogMonitorConfig
from reference.p0 import (
    P0_DETECTOR_PROFILE,
    OSCFARDetector,
    ParameterExtractor,
    TemporalConfirmation,
)
from reference.p0.fixtures import CENTER_FREQUENCY_HZ, SAMPLE_RATE_HZ, build_fixtures, build_judge_demo_engine
from reference.spectrum import SigMFFrameSource, SpectrumProcessor


PHASE05_FIXTURES = ROOT / "datasets" / "fixtures" / "phase05"


def populate(window: object, controller: object | None = None) -> None:
    fixture = next(item for item in build_fixtures() if item.fixture_id == "nfm-like")
    source_index = window.source_type_combo.findData("deterministic_test")
    if source_index >= 0:
        blocker = QSignalBlocker(window.source_type_combo)
        window.source_type_combo.setCurrentIndex(source_index)
        del blocker
        window.set_acquisition_mode("deterministic_test")
    window.set_p0_search_engine(build_judge_demo_engine())
    spectrum = SpectrumProcessor().process(
        fixture.iq,
        sample_rate_hz=SAMPLE_RATE_HZ,
        center_frequency_hz=CENTER_FREQUENCY_HZ,
    )
    periodic_hann = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(fixture.iq.size, dtype=np.float64) / fixture.iq.size)
    shifted_power = np.abs(np.fft.fftshift(np.fft.fft(fixture.iq * periodic_hann))) ** 2
    detection = OSCFARDetector().process(shifted_power, frame_id=0)
    expected_bin = fixture.iq.size // 2 + round(90_000.0 / (SAMPLE_RATE_HZ / fixture.iq.size))
    candidate = min(detection.candidates, key=lambda item: abs(item.peak_bin - expected_bin))
    temporal = TemporalConfirmation()
    temporal.update(detection.candidates, frame_id=0)
    tracks = temporal.update(detection.candidates, frame_id=1)
    confirmed = any(track.state == "confirmed" and track.candidate.peak_bin == candidate.peak_bin for track in tracks)
    result = ParameterExtractor().extract(
        frame_id=1,
        iq=fixture.iq,
        shifted_power=shifted_power,
        sample_rate_hz=SAMPLE_RATE_HZ,
        center_frequency_hz=CENTER_FREQUENCY_HZ,
        candidate=candidate,
        confirmed=confirmed,
        provenance="REPLAY",
        backend="ALGORİTMA TESTİ · REPLAY → p0.os_cfar + p0.parameters",
        neighboring_candidates=detection.candidates,
    )
    window.source_value.setText("ALGORİTMA TESTİ · Deterministik NFM-benzeri I/Q REPLAY")
    window.listening_source_value.setText("ANALOG DİNLEME TEST VERİSİ · NFM SigMF REPLAY")
    window.metadata_values["center_frequency"].setText("100,000 MHz")
    window.metadata_values["sample_rate"].setText("1,024 MS/s")
    window.metadata_values["datatype"].setText("complex128 sentetik replay")
    window.metadata_values["frame_length"].setText("4096 karmaşık örnek")
    window.metadata_values["frame_position"].setText("2 / 2")
    window.metadata_values["channel"].setText("1")
    window._refresh_source_summary()
    window.set_fixture_source(True)
    window.set_profile_summary(
        f"{P0_DETECTOR_PROFILE.name} · G=4 · R=16/yan · rank=24/32 · "
        f"Pfa=1e-4 · α={P0_DETECTOR_PROFILE.threshold_coefficient:.6f}",
        validated=True,
    )
    for _ in range(16):
        window.spectrum_view.update_spectrum(spectrum.display, spectrum.display)
    window.analysis_spectrum.set_spectrum(spectrum.display)
    window.analysis_spectrum.set_span(candidate.start_bin, candidate.end_bin)
    window.set_p0_parameter_result(result)
    window.set_p0_detection_summary(result)
    listening_source = SigMFFrameSource(PHASE05_FIXTURES / "nfm-tone-ci8.sigmf-meta")
    listening = AnalogMonitor().process(
        tuple(listening_source.read_frame(index) for index in range(4)),
        AnalogMonitorConfig("nfm", listening_source.sample_rate_hz, -24_000.0, 16_000.0),
    )
    audio_playback = getattr(controller, "audio_playback", None)
    if audio_playback is not None:
        audio_playback.load(listening.pcm16)
    window.set_listening_result(
        listening,
        audio_available=bool(getattr(audio_playback, "available", False)),
        source_sample_rate_hz=listening_source.sample_rate_hz,
        carrier_frequency_hz=99_976_000.0,
        channel_bandwidth_hz=16_000.0,
        backend="ANALOG DİNLEME TEST VERİSİ · REPLAY / HOST · NumPy PHASE-05",
    )
    window.df_mode_combo.setCurrentIndex(window.df_mode_combo.findData("training"))
    window._load_df_training_fixture()
    window._load_map_training_scenario()
    window._start_jamming_preview()
    window.system_status_values["source"].setText("ALGORİTMA TESTİ · REPLAY")
    window.system_status_values["processing"].setText("HOST/REPLAY · OS-CFAR + Parametre")
    window.system_status_values["fpga"].setText("RTL / VIVADO DOĞRULAMA · 50 MHz timing PASS")
    window.system_status_values["zedboard"].setText("FİZİKSEL ZEDBOARD TESTİ · çalıştırılmadı")
    window.system_status_values["transport"].setText("Canlı DMA / FPGA işleme yok")


def main() -> int:
    parser = argparse.ArgumentParser(description="P0 zorunlu EH çekirdeği deterministik operatör demosu")
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    app, window, controller = build_laboratory_application([sys.argv[0]])
    populate(window, controller)
    window.show()
    if args.smoke_test:
        QTimer.singleShot(300, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
