"""Qt-independent PHASE-03 adaptive detection reference model."""

from .cfar import (
    ALLOWED_PFA_VALUES,
    COST_MODELS,
    OS_EXPECTED_RATIO,
    CellDetectionResult,
    DetectionError,
    DetectorConfig,
    LinearPowerDetector,
    ca_threshold_multiplier,
    os_threshold_multiplier,
    regional_threshold_multiplier,
)
from .pipeline import (
    DetectionEvent,
    DetectionFrameResult,
    DetectionPipeline,
    DetectionRegion,
)

__all__ = [
    "ALLOWED_PFA_VALUES",
    "COST_MODELS",
    "OS_EXPECTED_RATIO",
    "CellDetectionResult",
    "DetectionError",
    "DetectionEvent",
    "DetectionFrameResult",
    "DetectionPipeline",
    "DetectionRegion",
    "DetectorConfig",
    "LinearPowerDetector",
    "ca_threshold_multiplier",
    "os_threshold_multiplier",
    "regional_threshold_multiplier",
]
