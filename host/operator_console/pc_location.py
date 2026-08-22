"""One-shot, user-initiated desktop location adapter.

Qt Positioning is optional at runtime.  This adapter never manufactures a
coordinate: a result exists only when the operating system provider reports a
valid fix after the operator presses the location button.
"""

from __future__ import annotations

from datetime import datetime, timezone
import math

from PySide6.QtCore import QObject, Signal

from reference.p0.field_df import LocationFix, PositionSource


LOCATION_FAILURE_TEXT = "Bilgisayar konumu alınamadı. Manuel konum girebilirsiniz."


class PCPositionProvider(QObject):
    """Request exactly one PC position update through Qt Positioning."""

    pending = Signal()
    acquired = Signal(object)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._source: object | None = None
        self._request_active = False

    def request_once(self) -> None:
        if self._request_active:
            return
        self._request_active = True
        self.pending.emit()
        try:
            from PySide6.QtPositioning import QGeoPositionInfoSource

            source = QGeoPositionInfoSource.createDefaultSource(self)
            if source is None:
                self._finish_failure(LOCATION_FAILURE_TEXT)
                return
            self._source = source
            source.positionUpdated.connect(self._position_updated)
            source.errorOccurred.connect(self._position_error)
            source.requestUpdate(10_000)
        except Exception:
            self._finish_failure(LOCATION_FAILURE_TEXT)

    def _position_updated(self, info: object) -> None:
        try:
            coordinate = info.coordinate()
            if not coordinate.isValid():
                raise ValueError("invalid coordinate")
            accuracy = info.attribute(info.Attribute.HorizontalAccuracy)
            altitude = float(coordinate.altitude())
            fix = LocationFix(
                latitude_deg=float(coordinate.latitude()),
                longitude_deg=float(coordinate.longitude()),
                altitude_m=altitude if math.isfinite(altitude) else None,
                accuracy_m=float(accuracy) if accuracy == accuracy and accuracy >= 0.0 else None,
                source=PositionSource.AUTO_PC,
                timestamp_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            )
        except Exception:
            self._finish_failure(LOCATION_FAILURE_TEXT)
            return
        self._cleanup()
        self.acquired.emit(fix)

    def _position_error(self, error: object) -> None:
        # AccessError is intentionally surfaced as a permission refusal; all
        # other provider errors retain the safe manual fallback message.
        try:
            from PySide6.QtPositioning import QGeoPositionInfoSource

            if error == QGeoPositionInfoSource.Error.AccessError:
                self._finish_failure("Konum izni reddedildi. Manuel konum girebilirsiniz.")
                return
        except Exception:
            pass
        self._finish_failure(LOCATION_FAILURE_TEXT)

    def _finish_failure(self, text: str) -> None:
        self._cleanup()
        self.failed.emit(text)

    def _cleanup(self) -> None:
        source = self._source
        self._source = None
        self._request_active = False
        if source is not None:
            try:
                source.stopUpdates()
            except Exception:
                pass
            source.deleteLater()
