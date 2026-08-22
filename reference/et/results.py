"""Structured, transmit-disabled ET task result contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ETTaskResult:
    """Common record returned by every completed ET software task.

    This is deliberately data, not user-interface text.  ``tx_state`` is
    fixed to the lock state because no ET model owns or accesses an RF sink.
    """

    task_type: str
    mode: str
    source: str
    started_at: str
    duration: float
    waveform_type: str
    sample_rate: int
    sample_count: int
    normalization_status: str
    validation_status: str
    tx_state: str = "KİLİTLİ"
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def new_task_result(
    *,
    task_type: str,
    mode: str,
    source: str,
    duration: float,
    waveform_type: str,
    sample_rate: int,
    sample_count: int,
    normalization_status: str,
    validation_status: str,
    details: dict[str, Any] | None = None,
) -> ETTaskResult:
    """Create the result record at completion without pretending hardware ran."""

    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return ETTaskResult(
        task_type=task_type,
        mode=mode,
        source=source,
        started_at=started_at,
        duration=duration,
        waveform_type=waveform_type,
        sample_rate=sample_rate,
        sample_count=sample_count,
        normalization_status=normalization_status,
        validation_status=validation_status,
        details={} if details is None else dict(details),
    )
