"""PHASE-04 core parameter extraction reference API."""

from .classification import FEATURE_HISTORY_BYTES, FeatureHistoryStore, classify_features
from .evaluation import evaluate_parameter_methods
from .extraction import (
    ANALYSIS_METHODS,
    BANDWIDTH_METHODS,
    POWER_SNR_METHODS,
    MethodSelection,
    ParameterExtractor,
    build_analysis_candidates,
    compute_transient_guard,
    estimate_band_support,
    extract_frame_features,
)
from .models import (
    AnalysisCandidate,
    BandSupportResult,
    BandwidthEstimate,
    EventParameterEstimate,
    FieldState,
    FrequencyEstimate,
    ParameterFrameResult,
    ParameterInvalidReason,
    RelativePowerEstimate,
    SignalDomainEstimate,
)
from .scenes import ParameterSceneFrame, generate_parameter_scene, load_parameter_catalog

__all__ = [
    "ANALYSIS_METHODS",
    "AnalysisCandidate",
    "BANDWIDTH_METHODS",
    "BandSupportResult",
    "BandwidthEstimate",
    "EventParameterEstimate",
    "FEATURE_HISTORY_BYTES",
    "FeatureHistoryStore",
    "FieldState",
    "FrequencyEstimate",
    "MethodSelection",
    "POWER_SNR_METHODS",
    "ParameterExtractor",
    "ParameterFrameResult",
    "ParameterInvalidReason",
    "ParameterSceneFrame",
    "RelativePowerEstimate",
    "SignalDomainEstimate",
    "classify_features",
    "build_analysis_candidates",
    "compute_transient_guard",
    "evaluate_parameter_methods",
    "estimate_band_support",
    "extract_frame_features",
    "generate_parameter_scene",
    "load_parameter_catalog",
]
