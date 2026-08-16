"""Platform-independent P0 mandatory ED reference contracts."""

from .bandwidth import BandwidthEstimate, BandwidthEstimator, BandwidthProfile
from .detection import (
    P0_DETECTOR_PROFILE,
    OSCFARConfig,
    OSCFARDetector,
    OSCFARFrameResult,
    P0DetectorProfile,
    derive_os_cfar_threshold_coefficient,
    order_statistic_expected_ratio,
    os_cfar_false_alarm_probability,
)
from .df import DFEstimate, DFMeasurement, ManualAmplitudeDF
from .models import CandidateRegion, P0ParameterResult, Provenance
from .parameters import ParameterExtractor, ParameterProfile
from .search import (
    P0SearchEngine,
    ReplaySearchBackend,
    SearchAcquisitionBackend,
    SearchExecutionResult,
    SearchMode,
    SearchRequest,
    TuningWindow,
)
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
    "BandwidthEstimate",
    "BandwidthEstimator",
    "BandwidthProfile",
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
    "P0DetectorProfile",
    "P0_DETECTOR_PROFILE",
    "P0ParameterResult",
    "P0SearchEngine",
    "ParameterExtractor",
    "ParameterProfile",
    "Provenance",
    "ReplaySearchBackend",
    "SearchAcquisitionBackend",
    "SearchExecutionResult",
    "SearchMode",
    "SearchRequest",
    "TransportError",
    "TransportStats",
    "TemporalConfirmation",
    "TCPClientIQTransport",
    "TrackedCandidate",
    "TuningWindow",
    "derive_os_cfar_threshold_coefficient",
    "order_statistic_expected_ratio",
    "os_cfar_false_alarm_probability",
]
