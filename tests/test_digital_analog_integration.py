"""PC Analog/Sayısal adaptörünün sınırlı ürün bağlantısı."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from digital_analog_detection import classify_parameter_frames


FS = 2_000_000.0
N = 4 * 4096


def _frames(samples):
    return tuple(np.asarray(samples, dtype=np.complex128).reshape(4, 4096))


def test_high_confidence_analog_and_digital_are_automatic() -> None:
    rng = np.random.default_rng(20260912)
    time_axis = np.arange(N) / FS
    carrier = np.exp(2j * np.pi * 25_000.0 * time_axis)
    noise = 0.03 * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    analog = (1.0 + 0.65 * np.cos(2.0 * np.pi * 1_800.0 * time_axis)) * carrier + noise
    analog_result = classify_parameter_frames(
        _frames(analog), sample_rate_hz=FS,
        lower_shifted_bin=2030, upper_shifted_bin=2170, snr_db=15.0,
    )

    symbols = rng.choice((-1.0, 1.0), size=(N + 19) // 20)
    digital = np.repeat(symbols, 20)[:N].astype(np.complex128) * carrier + noise
    digital_result = classify_parameter_frames(
        _frames(digital), sample_rate_hz=FS,
        lower_shifted_bin=1900, upper_shifted_bin=2220, snr_db=15.0,
    )

    assert (analog_result.state, analog_result.value) == ("valid", "Analog")
    assert (digital_result.state, digital_result.value) == ("valid", "Sayısal")
    assert analog_result.confidence >= 0.90
    assert digital_result.confidence >= 0.90
    assert not analog_result.physical_acceptance
    assert not digital_result.product_acceptance


def test_low_snr_and_unsupported_rate_fail_closed() -> None:
    samples = _frames(np.ones(N, dtype=np.complex128))
    low_snr = classify_parameter_frames(
        samples, sample_rate_hz=FS,
        lower_shifted_bin=2000, upper_shifted_bin=2100, snr_db=3.99,
    )
    wrong_rate = classify_parameter_frames(
        samples, sample_rate_hz=1_000_000.0,
        lower_shifted_bin=2000, upper_shifted_bin=2100, snr_db=20.0,
    )
    assert low_snr.state == wrong_rate.state == "uncertain"
    assert low_snr.value is wrong_rate.value is None


def test_wide_analysis_span_is_processed_on_pc() -> None:
    samples = _frames(np.exp(2j * np.pi * 17_000.0 * np.arange(N) / FS))
    result = classify_parameter_frames(
        samples, sample_rate_hz=FS,
        lower_shifted_bin=1045, upper_shifted_bin=3458, snr_db=20.0,
    )
    assert result.state in {"valid", "uncertain"}
    assert "henüz doğrulanmadı" not in result.reason


def test_invalid_frame_shape_is_rejected() -> None:
    with pytest.raises(ValueError, match="dört ölçüm karesi"):
        classify_parameter_frames(
            (np.ones(4096),), sample_rate_hz=FS,
            lower_shifted_bin=2000, upper_shifted_bin=2100, snr_db=20.0,
        )


def test_parameter_panel_exposes_domain_as_primary_result() -> None:
    source = (Path(__file__).resolve().parents[1]
              / "app/operator_console/qml/ParameterMeasurementPanel.qml").read_text(encoding="utf-8")
    assert '"channel_power_dbfs", "estimated_power_dbm", "signal_domain"' in source
    assert "return mainKeys.indexOf(row.key) < 0" in source
    assert '"Sinyal Türü"' in source
    assert "Sinyal türü (PC, deneysel)" not in source
    assert "Alımı Durdur ve Parametreleri Çıkar" in source


def test_recorded_development_evidence_is_reproducible() -> None:
    from scripts.verify_automatic_domain_integration import check

    assert check()
