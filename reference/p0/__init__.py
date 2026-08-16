"""Platform-independent P0 mandatory ED reference contracts."""

from .detection import OSCFARConfig, OSCFARDetector, OSCFARFrameResult
from .df import DFEstimate, DFMeasurement, ManualAmplitudeDF
from .models import CandidateRegion, P0ParameterResult, Provenance
from .parameters import ParameterExtractor, ParameterProfile
from .temporal import TemporalConfirmation, TrackedCandidate
from .transport import (
    BoundedIQQueue,
    IQFrame,
    IQFrameCodec,
    IQTransport,
    LoopbackIQTransport,
    TCPClientIQTransport,
    TransportError,
    TransportStats,
)

__all__ = [
    "BoundedIQQueue",
    "CandidateRegion",
    "DFEstimate",
    "DFMeasurement",
    "IQFrame",
    "IQFrameCodec",
    "IQTransport",
    "LoopbackIQTransport",
    "ManualAmplitudeDF",
    "OSCFARConfig",
    "OSCFARDetector",
    "OSCFARFrameResult",
    "P0ParameterResult",
    "ParameterExtractor",
    "ParameterProfile",
    "Provenance",
    "TransportError",
    "TransportStats",
    "TemporalConfirmation",
    "TCPClientIQTransport",
    "TrackedCandidate",
]
