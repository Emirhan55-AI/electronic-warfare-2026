"""Conservative, explicitly uncalibrated HackRF input-power estimate."""

from __future__ import annotations

from dataclasses import dataclass
import math


MODEL_ID = "hackrf-one-uncalibrated-input-power-v1"
NOMINAL_FULL_SCALE_INPUT_DBM = -5.0
NOMINAL_RF_AMPLIFIER_GAIN_DB = 11.0


@dataclass(frozen=True)
class PowerEstimate:
    power_dbm: float
    uncertainty_db: float
    method_id: str = MODEL_ID


def estimate_hackrf_input_power_dbm(
    channel_power_dbfs: float,
    *,
    frequency_hz: float,
    lna_gain_db: int,
    vga_gain_db: int,
    rf_amplifier: bool,
    output_amplitude_scale: float,
) -> PowerEstimate | None:
    """Estimate SMA-input power without presenting it as a calibration result.

    The model uses HackRF One's documented -5 dBm maximum input as a deliberately
    coarse zero-gain/full-scale anchor, removes the configured nominal gain and
    channelizer amplitude scale, and exposes a wide uncertainty.  It is useful
    for operator-level ordering only; it is not a substitute for a measured
    receiver-specific calibration profile.
    """

    numeric = (
        channel_power_dbfs,
        frequency_hz,
        lna_gain_db,
        vga_gain_db,
        output_amplitude_scale,
    )
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in numeric):
        return None
    if not all(math.isfinite(float(value)) for value in numeric):
        return None
    if not 1_000_000.0 <= float(frequency_hz) <= 6_000_000_000.0:
        return None
    if int(lna_gain_db) not in range(0, 41, 8) or int(vga_gain_db) not in range(0, 63, 2):
        return None
    if type(rf_amplifier) is not bool or float(output_amplitude_scale) <= 0.0:
        return None

    scale_gain_db = 20.0 * math.log10(float(output_amplitude_scale))
    configured_gain_db = float(lna_gain_db + vga_gain_db)
    if rf_amplifier:
        configured_gain_db += NOMINAL_RF_AMPLIFIER_GAIN_DB
    power_dbm = (
        NOMINAL_FULL_SCALE_INPUT_DBM
        + float(channel_power_dbfs)
        - configured_gain_db
        - scale_gain_db
    )
    if not math.isfinite(power_dbm):
        return None

    uncertainty_db = 15.0
    if rf_amplifier:
        uncertainty_db += 3.0
    if frequency_hz < 100_000_000.0 or frequency_hz > 4_000_000_000.0:
        uncertainty_db += 3.0
    if power_dbm < -100.0:
        uncertainty_db += 3.0
    return PowerEstimate(power_dbm=power_dbm, uncertainty_db=min(uncertainty_db, 24.0))
