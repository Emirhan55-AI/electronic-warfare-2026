"""Qt-independent bounded analog monitoring reference API."""

from .dsp import (
    AUDIO_SAMPLE_RATE_HZ,
    MAX_AUDIO_SECONDS,
    MAX_IQ_FRAMES,
    OBSERVATION_INTERVAL_SECONDS,
    AnalogMonitor,
    AudioRingBuffer,
    StreamingAnalogMonitor,
    aligned_correlation,
    dominant_tone_hz,
    nfm_deemphasis,
    pcm16_bytes,
    wav_bytes,
    write_wav,
)
from .evaluation import build_phase05_evidence
from .fixtures import FIXTURE_SPECS, build_fixture_files, generate_iq
from .models import (
    AnalogMonitorConfig,
    AnalogMonitorResult,
    ListeningIntent,
    MonitoringError,
)
from .signaling import decode_dtmf

__all__ = [
    "AUDIO_SAMPLE_RATE_HZ",
    "MAX_AUDIO_SECONDS",
    "MAX_IQ_FRAMES",
    "OBSERVATION_INTERVAL_SECONDS",
    "AnalogMonitor",
    "AnalogMonitorConfig",
    "AnalogMonitorResult",
    "AudioRingBuffer",
    "StreamingAnalogMonitor",
    "FIXTURE_SPECS",
    "ListeningIntent",
    "MonitoringError",
    "aligned_correlation",
    "build_fixture_files",
    "build_phase05_evidence",
    "dominant_tone_hz",
    "decode_dtmf",
    "nfm_deemphasis",
    "generate_iq",
    "pcm16_bytes",
    "wav_bytes",
    "write_wav",
]
