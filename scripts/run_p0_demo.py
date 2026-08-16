"""Launch the deterministic P0 ED/DF/ET operator demonstration."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
from PySide6.QtCore import QTimer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from host.operator_console.application import build_application
from reference.p0 import (
    P0_DETECTOR_PROFILE,
    OSCFARDetector,
    ParameterExtractor,
    TemporalConfirmation,
)
from reference.p0.fixtures import CENTER_FREQUENCY_HZ, SAMPLE_RATE_HZ, build_fixtures, build_judge_demo_engine
from reference.spectrum import SpectrumProcessor


def populate(window: object) -> None:
    fixture = next(item for item in build_fixtures() if item.fixture_id == "nfm-like")
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
        provenance="HOST REFERENCE",
        backend="REPLAY → p0.os_cfar + p0.parameters",
        neighboring_candidates=detection.candidates,
    )
    window.source_value.setText("P0 deterministik NFM-benzeri replay")
    window.metadata_values["center_frequency"].setText("100,000 MHz")
    window.metadata_values["sample_rate"].setText("1,024 MS/s")
    window.metadata_values["datatype"].setText("complex128 sentetik replay")
    window.metadata_values["frame_length"].setText("4096 karmaşık örnek")
    window.metadata_values["frame_position"].setText("2 / 2")
    window.metadata_values["channel"].setText("1")
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
    for angle, power in ((0, -30), (30, -20), (60, -8), (90, -19), (120, -29)):
        window.df_angle_spin.setValue(angle)
        window.df_power_spin.setValue(power)
        window.df_confidence_spin.setValue(0.9)
        window._add_df_measurement()
    window._start_jamming_preview()
    window.system_status_values["processing"].setText("HOST REFERENCE · ALGORİTMA DOĞRULANDI")
    window.system_status_values["transport"].setText("YEREL LOOPBACK HAZIR · ZedBoard sunucusu uygulanmadı")


def main() -> int:
    parser = argparse.ArgumentParser(description="P0 zorunlu EH çekirdeği deterministik operatör demosu")
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    app, window, _ = build_application([sys.argv[0]])
    populate(window)
    window.show()
    if args.smoke_test:
        QTimer.singleShot(300, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
