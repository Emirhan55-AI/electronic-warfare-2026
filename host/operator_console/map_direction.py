"""Offline-safe real-map presentation widget for an existing DF result."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from reference.p0.map_direction import DirectionPresentation, SensorPosition, destination_point, geographic_lob_geometry

from .map_providers import MapProvider, MapProviderMode, map_assets_root, select_map_providers


FALLBACK_TEXT = "Harita motoru kullanılamıyor. Yön bilgisi metinsel olarak görüntüleniyor."


def resolve_web_engine_view() -> type[QWidget] | None:
    """Import WebEngine only for a real GUI session, never for headless Qt tests."""
    if QGuiApplication.platformName().casefold() == "offscreen":
        return None
    try:
        from PySide6.QtWebEngineWidgets import QWebEngineView
    except ImportError:
        return None
    return QWebEngineView


class DirectionMapView(QFrame):
    """Present one DF LOB on a real map, falling back without affecting DF."""

    def __init__(
        self,
        *,
        web_engine_factory: type[QWidget] | None = None,
        providers: tuple[MapProvider, ...] | None = None,
        asset_root: Path | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("directionMapView")
        self.presentation: DirectionPresentation | None = None
        self.measurement_rays: tuple[dict[str, object], ...] = ()
        self.sensor: SensorPosition | None = None
        self.using_web_engine = False
        self._web_view: QWidget | None = None
        self._asset_root = map_assets_root() if asset_root is None else asset_root
        self._providers = providers if providers is not None else select_map_providers(asset_root=self._asset_root)
        self._selected_mode = self._providers[0].mode
        self._fallback = QLabel(FALLBACK_TEXT)
        self._fallback.setObjectName("mapFallback")
        self._fallback.setWordWrap(True)
        self._fallback.setStyleSheet("padding: 24px; color: #d8e7f4;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        factory = resolve_web_engine_view() if web_engine_factory is None else web_engine_factory
        page_path = self._asset_root / "map.html"
        if factory is not None and page_path.is_file():
            try:
                self._web_view = factory()
                self._web_view.setObjectName("geographicDirectionMap")
                settings = self._web_view.settings()  # type: ignore[attr-defined]
                from PySide6.QtWebEngineCore import QWebEngineSettings

                settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
                settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
                self._web_view.loadFinished.connect(self._on_map_loaded)  # type: ignore[attr-defined]
                self._web_view.setUrl(QUrl.fromLocalFile(str(page_path)))  # type: ignore[attr-defined]
                layout.addWidget(self._web_view)
                self.using_web_engine = True
            except Exception:
                self._web_view = None
        if self._web_view is None:
            layout.addWidget(self._fallback)
        else:
            self._fallback.hide()

    @property
    def fallback_visible(self) -> bool:
        return not self.using_web_engine

    @property
    def providers(self) -> tuple[MapProvider, ...]:
        return self._providers

    @property
    def selected_mode(self) -> MapProviderMode:
        return self._selected_mode

    def refresh_providers(self) -> None:
        self._providers = select_map_providers(asset_root=self._asset_root)
        if self._selected_mode not in {provider.mode for provider in self._providers}:
            self._selected_mode = self._providers[0].mode
        self._update_map()

    def select_provider(self, mode: MapProviderMode | str) -> None:
        selected = MapProviderMode(mode)
        if selected not in {provider.mode for provider in self._providers}:
            raise ValueError("map provider is unavailable")
        self._selected_mode = selected
        self._update_map()

    def set_sensor(self, sensor: SensorPosition) -> None:
        self.sensor = sensor
        self.presentation = None
        self.measurement_rays = ()
        self._update_map()

    def set_presentation(self, presentation: DirectionPresentation) -> None:
        self.presentation = presentation
        self.sensor = presentation.sensor
        self.measurement_rays = ()
        self._update_map()

    def set_measurement_rays(
        self,
        sensor: SensorPosition,
        *,
        reference_azimuth_deg: float,
        measurements: tuple[tuple[int, float], ...],
    ) -> None:
        """Render known antenna directions only; never infer a transmitter."""
        rays: list[dict[str, object]] = []
        for angle_deg, power_dbfs in measurements:
            azimuth = (float(reference_azimuth_deg) + float(angle_deg)) % 360.0
            end_latitude, end_longitude = destination_point(sensor.latitude_deg, sensor.longitude_deg, azimuth, 2_500.0)
            left_latitude, left_longitude = destination_point(end_latitude, end_longitude, azimuth + 150.0, 180.0)
            right_latitude, right_longitude = destination_point(end_latitude, end_longitude, azimuth - 150.0, 180.0)
            rays.append({
                "angle": int(angle_deg), "azimuth": azimuth, "power": float(power_dbfs),
                "line": [[sensor.longitude_deg, sensor.latitude_deg], [end_longitude, end_latitude]],
                "arrowhead": [[end_longitude, end_latitude], [left_longitude, left_latitude], [right_longitude, right_latitude], [end_longitude, end_latitude]],
                "color": "#55d6be" if angle_deg == 0 else "#f2c46d",
            })
        self.sensor = sensor
        self.presentation = None
        self.measurement_rays = tuple(rays)
        self._update_map()

    def clear_lob(self) -> None:
        self.presentation = None
        self.measurement_rays = ()
        self._update_map()

    def _on_map_loaded(self, _: bool) -> None:
        self._update_map()

    def _ordered_providers(self) -> tuple[MapProvider, ...]:
        selected = [provider for provider in self._providers if provider.mode == self._selected_mode]
        remainder = [provider for provider in self._providers if provider.mode != self._selected_mode]
        return tuple(selected + remainder)

    def _payload(self) -> dict[str, object] | None:
        if self.sensor is None:
            return None
        presentation = self.presentation
        if presentation is None:
            body: dict[str, object] = {
                "sensor": {"name": self.sensor.name, "latitude": self.sensor.latitude_deg, "longitude": self.sensor.longitude_deg, "heading": self.sensor.heading_deg, "source": self.sensor.source},
                "relativeAngle": 0.0,
                "azimuth": None,
                "frequency": "—",
                "power": "—",
                "confidence": "—",
                "source": self.sensor.source,
                "timestamp": "—",
                "lob": None,
                "rays": list(self.measurement_rays),
            }
        else:
            geometry = geographic_lob_geometry(presentation)
            body = {
                "sensor": {"name": presentation.sensor.name, "latitude": presentation.sensor.latitude_deg, "longitude": presentation.sensor.longitude_deg, "heading": presentation.sensor.heading_deg, "source": presentation.sensor.source},
                "relativeAngle": presentation.relative_antenna_angle_deg,
                "azimuth": presentation.geographic_azimuth_deg,
                "frequency": f"{presentation.frequency_hz / 1_000_000.0:.6f} MHz",
                "power": f"{presentation.peak_power_db:.2f} dBFS",
                "confidence": f"{presentation.confidence:.2f}",
                "source": presentation.source,
                "timestamp": presentation.measurement_timestamp_utc,
                "lob": None if geometry is None else {
                    "line": [[geometry.start_longitude_deg, geometry.start_latitude_deg], [geometry.render_endpoint_longitude_deg, geometry.render_endpoint_latitude_deg]],
                    "arrowhead": [list(point) for point in geometry.arrowhead_coordinates],
                },
                "rays": [],
            }
        return {
            "presentation": body,
            "zoom": 13,
            "providers": [
                {"mode": provider.mode.value, "label": provider.label, "styleUrl": provider.style_url, "googleMapsApiKey": provider.google_maps_api_key}
                for provider in self._ordered_providers()
            ],
        }

    def _update_map(self) -> None:
        payload = self._payload()
        if payload is None or self._web_view is None:
            return
        try:
            self._web_view.page().runJavaScript("window.updateMapPayload(" + json.dumps(payload) + ");")  # type: ignore[attr-defined]
        except Exception:
            pass
