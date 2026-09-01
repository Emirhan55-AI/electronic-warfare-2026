from __future__ import annotations

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QToolButton, QVBoxLayout, QWidget)

from algorithms.p0.field_df import AntennaReference, LocationFix, PositionSource
from algorithms.p0.map_direction import DirectionPresentation, SensorPosition, build_direction_presentation

from .map_direction import DirectionMapView
from .map_providers import MapProviderMode
from .pc_location import LOCATION_FAILURE_TEXT
from .ui_text import TEXT

class MapWorkspaceMixin:
    """Harita çalışma alanı ve konum işlemleri mixin'i."""

    def _build_map_direction_workspace(self) -> QWidget:
        workspace = QWidget()
        self.map_direction_workspace = workspace
        layout = QHBoxLayout(workspace)
        self.direction_map_view = DirectionMapView()
        self.direction_map_view.setMinimumWidth(560)
        layout.addWidget(self.direction_map_view, 1)

        panel = QFrame()
        panel.setObjectName("mapDirectionPanel")
        panel_layout = QVBoxLayout(panel)
        heading = QLabel("Harita & Sensör")
        heading.setObjectName("selectedSignalTitle")
        heading.setWordWrap(True)
        panel_layout.addWidget(heading)
        self.map_engine_label = QLabel(
            "Yerel harita görünümü"
            if self.direction_map_view.using_web_engine
            else TEXT["map_engine_fallback"]
        )
        self.map_engine_label.setProperty("class", "propCaption")
        self.map_engine_label.setWordWrap(True)
        panel_layout.addWidget(self.map_engine_label)
        self.map_provider_combo = QComboBox()
        self.map_provider_combo.setObjectName("mapProviderCombo")
        p_lbl = QLabel("Harita Arka Planı")
        p_lbl.setProperty("class", "propCaption")
        p_lbl.setWordWrap(True)
        panel_layout.addWidget(p_lbl)
        panel_layout.addWidget(self.map_provider_combo)
        self.map_provider_refresh_button = QPushButton("Harita Sağlayıcısını Yenile")
        panel_layout.addWidget(self.map_provider_refresh_button)
        self._populate_map_provider_combo()
        self.map_status_label = QLabel(TEXT["relative_direction_no_reference"])
        self.map_status_label.setObjectName("mapDirectionStatus")
        self.map_status_label.setWordWrap(True)
        panel_layout.addWidget(self.map_status_label)

        sensor_heading = QLabel("Sensör Bilgileri")
        sensor_heading.setObjectName("selectedSignalTitle")
        sensor_heading.setWordWrap(True)
        panel_layout.addWidget(sensor_heading)
        sensor_grid = QGridLayout()
        self.map_sensor_name = QLineEdit("Sensör 1")
        self.map_latitude_spin = QDoubleSpinBox()
        self.map_latitude_spin.setRange(-90.0, 90.0)
        self.map_latitude_spin.setDecimals(6)
        self.map_longitude_spin = QDoubleSpinBox()
        self.map_longitude_spin.setRange(-180.0, 180.0)
        self.map_longitude_spin.setDecimals(6)
        self.map_altitude_spin = QDoubleSpinBox()
        self.map_altitude_spin.setRange(-500.0, 15_000.0)
        self.map_altitude_spin.setSuffix(" m")
        self.map_heading_spin = QDoubleSpinBox()
        self.map_heading_spin.setRange(0.0, 360.0)
        self.map_heading_spin.setSuffix("°")
        self.map_heading_reference_check = QCheckBox("Anten referans yönü geçerli")
        self.map_source_combo = QComboBox()
        self.map_source_combo.addItem("BİLGİSAYAR KONUMU", PositionSource.AUTO_PC)
        self.map_source_combo.addItem("MANUEL", "MANUEL")
        if self.laboratory_mode:
            self.map_source_combo.addItem("YAZILIM REFERANS VERİSİ", "HOST/SYNTHETIC")
        self.map_source_combo.addItem("KAYIT OYNATMA", "REPLAY")
        self.map_source_combo.setCurrentIndex(self.map_source_combo.findData("MANUEL"))
        sensor_fields = (
            ("Sensör", self.map_sensor_name),
            ("Enlem", self.map_latitude_spin),
            ("Boylam", self.map_longitude_spin),
            ("Yükseklik", self.map_altitude_spin),
            ("Anten Referans Yönü", self.map_heading_spin),
            ("Kaynak", self.map_source_combo),
        )
        for row, (caption, widget) in enumerate(sensor_fields):
            l = QLabel(caption)
            l.setProperty("class", "propCaption")
            l.setWordWrap(True)
            sensor_grid.addWidget(l, row, 0)
            sensor_grid.addWidget(widget, row, 1)
        sensor_grid.addWidget(self.map_heading_reference_check, len(sensor_fields), 0, 1, 2)
        self.map_location_button = QPushButton("KONUMUMU AL")
        self.map_manual_location_button = QPushButton("MANUEL KONUMU KULLAN")
        self.map_location_status = QLabel("Konum kaynağı seçilmedi.")
        self.map_location_status.setObjectName("mapLocationStatus")
        self.map_location_status.setWordWrap(True)
        self.map_accuracy_label = QLabel("Doğruluk: bilinmiyor")
        self.map_accuracy_label.setProperty("class", "propCaption")
        self.map_accuracy_label.setWordWrap(True)
        self.map_location_time_label = QLabel("Zaman: —")
        self.map_location_time_label.setProperty("class", "propCaption")
        self.map_location_time_label.setWordWrap(True)
        self.map_pc_location_result_label = QLabel("Sonuç: denenmedi")
        self.map_pc_location_result_label.setProperty("class", "propCaption")
        self.map_pc_location_result_label.setWordWrap(True)
        sensor_grid.addWidget(self.map_location_button, len(sensor_fields) + 1, 0)
        sensor_grid.addWidget(self.map_manual_location_button, len(sensor_fields) + 1, 1)
        sensor_grid.addWidget(self.map_location_status, len(sensor_fields) + 2, 0, 1, 2)
        sensor_grid.addWidget(self.map_accuracy_label, len(sensor_fields) + 3, 0, 1, 2)
        sensor_grid.addWidget(self.map_location_time_label, len(sensor_fields) + 4, 0, 1, 2)
        sensor_grid.addWidget(self.map_pc_location_result_label, len(sensor_fields) + 5, 0, 1, 2)
        panel_layout.addLayout(sensor_grid)

        result_heading = QLabel("Yön Sonucu")
        result_heading.setObjectName("selectedSignalTitle")
        result_heading.setWordWrap(True)
        panel_layout.addWidget(result_heading)
        result_grid = QGridLayout()
        self.map_result_values: dict[str, QLabel] = {}
        for row, (key, caption) in enumerate((
            ("frequency", "Frekans"),
            ("relative_angle", "Bağıl Açı"),
            ("azimuth", "Gerçek Kerteriz"),
            ("confidence", "Güven"),
            ("power", "Güç"),
            ("time", "Zaman"),
            ("backend", "Kaynak"),
            ("sensor_source", "Konum Kaynağı"),
        )):
            l = QLabel(caption)
            l.setProperty("class", "propCaption")
            l.setWordWrap(True)
            result_grid.addWidget(l, row, 0)
            value = QLabel("—")
            value.setProperty("class", "propValue")
            value.setWordWrap(True)
            result_grid.addWidget(value, row, 1)
            self.map_result_values[key] = value
        result_grid.setColumnStretch(1, 1)
        panel_layout.addLayout(result_grid)
        self.map_live_note = QLabel("GNSS alıcısı bağlı değil.")
        self.map_live_note.setProperty("class", "propCaption")
        self.map_live_note.setWordWrap(True)
        panel_layout.addWidget(self.map_live_note)

        self.map_show_sensor_button = QPushButton("Sensörü Haritada Göster")
        self.map_show_df_button = QPushButton("Mevcut DF Sonucunu Göster")
        self.map_clear_lob_button = QPushButton("Kerteriz Hattını Temizle")
        panel_layout.addWidget(self.map_show_sensor_button)
        panel_layout.addWidget(self.map_show_df_button)
        panel_layout.addWidget(self.map_clear_lob_button)
        if self.laboratory_mode:
            self.map_training_scenario_combo = QComboBox()
            self.map_training_scenario_combo.addItem("Doğrulama A: referans 0° + bağıl 75° = 75°", (0.0, 75.0))
            self.map_training_scenario_combo.addItem("Doğrulama B: referans 300° + bağıl 75° = 15°", (300.0, 15.0))
            self.map_training_button = QPushButton("Doğrulama Verisini Yükle")
            panel_layout.addWidget(self.map_training_scenario_combo)
            panel_layout.addWidget(self.map_training_button)
        panel_layout.addStretch(1)
        map_scroll = self._scroll_panel(panel, "mapDirectionScroll")
        map_scroll.setMinimumWidth(380)
        map_scroll.setMaximumWidth(460)
        layout.addWidget(map_scroll)

        self.map_show_sensor_button.clicked.connect(self._show_sensor_on_map)
        self.map_location_button.clicked.connect(self._request_pc_location)
        self.map_manual_location_button.clicked.connect(self._use_manual_location)
        self.map_show_df_button.clicked.connect(self._show_current_df_on_map)
        self.map_clear_lob_button.clicked.connect(self._clear_map_lob)
        if self.laboratory_mode:
            self.map_training_button.clicked.connect(self._load_map_training_scenario)
        self.map_provider_combo.currentIndexChanged.connect(self._select_map_provider)
        self.map_provider_refresh_button.clicked.connect(self._refresh_map_providers)

        detail_widgets = [widget for widget in panel.findChildren(QWidget) if widget is not panel]
        self.map_technical_toggle = QToolButton()
        self.map_technical_toggle.setText("▸ Teknik Ayrıntılar")
        self.map_technical_toggle.setCheckable(True)
        compact = QWidget()
        compact_layout = QVBoxLayout(compact)
        compact_layout.setContentsMargins(0, 0, 0, 0)
        compact_heading = QLabel("Yön")
        compact_heading.setObjectName("selectedSignalTitle")
        compact_heading.setWordWrap(True)
        compact_layout.addWidget(compact_heading)
        self.map_compact_bearing = QLabel("—")
        self.map_compact_bearing.setObjectName("mapCompactBearing")
        self.map_compact_bearing.setWordWrap(True)
        compact_layout.addWidget(self.map_compact_bearing)
        self.map_compact_summary = QLabel("Frekans — · Güven —")
        self.map_compact_summary.setProperty("class", "propCaption")
        self.map_compact_summary.setWordWrap(True)
        compact_layout.addWidget(self.map_compact_summary)
        location_heading = QLabel("Konum")
        location_heading.setObjectName("selectedSignalTitle")
        location_heading.setWordWrap(True)
        compact_layout.addWidget(location_heading)
        self.map_compact_location = QLabel("Konum: —\nDoğruluk: —")
        self.map_compact_location.setProperty("class", "propCaption")
        self.map_compact_location.setWordWrap(True)
        compact_layout.addWidget(self.map_compact_location)
        compact_buttons = QHBoxLayout()
        self.map_compact_location_button = QPushButton("KONUMUMU AL")
        self.map_compact_manual_button = QPushButton("MANUEL")
        compact_buttons.addWidget(self.map_compact_location_button)
        compact_buttons.addWidget(self.map_compact_manual_button)
        compact_layout.addLayout(compact_buttons)
        self.map_manual_fields = QWidget()
        manual_grid = QGridLayout(self.map_manual_fields)
        manual_grid.setContentsMargins(0, 0, 0, 0)
        self.map_manual_latitude_spin = QDoubleSpinBox()
        self.map_manual_latitude_spin.setRange(-90.0, 90.0)
        self.map_manual_latitude_spin.setDecimals(6)
        self.map_manual_longitude_spin = QDoubleSpinBox()
        self.map_manual_longitude_spin.setRange(-180.0, 180.0)
        self.map_manual_longitude_spin.setDecimals(6)
        self.map_manual_apply_button = QPushButton("KONUMU KULLAN")
        lat_lbl = QLabel("Enlem")
        lat_lbl.setProperty("class", "propCaption")
        lat_lbl.setWordWrap(True)
        lon_lbl = QLabel("Boylam")
        lon_lbl.setProperty("class", "propCaption")
        lon_lbl.setWordWrap(True)
        manual_grid.addWidget(lat_lbl, 0, 0)
        manual_grid.addWidget(self.map_manual_latitude_spin, 0, 1)
        manual_grid.addWidget(lon_lbl, 1, 0)
        manual_grid.addWidget(self.map_manual_longitude_spin, 1, 1)
        manual_grid.addWidget(self.map_manual_apply_button, 2, 0, 1, 2)
        self.map_manual_fields.hide()
        compact_layout.addWidget(self.map_manual_fields)
        note_lbl = QLabel("Kerteriz hattı (LOB) doğrultuyu gösterir; hedef konumu değildir.")
        note_lbl.setProperty("class", "propCaption")
        note_lbl.setWordWrap(True)
        compact_layout.addWidget(note_lbl)
        compact_layout.addWidget(self.map_technical_toggle)
        compact_layout.addStretch(1)
        panel_layout.insertWidget(1, compact)
        for widget in detail_widgets:
            widget.hide()
        self.map_compact_location_button.clicked.connect(self._request_pc_location)
        self.map_compact_manual_button.clicked.connect(self._toggle_manual_location_fields)
        self.map_manual_apply_button.clicked.connect(self._apply_compact_manual_location)
        self.map_technical_toggle.toggled.connect(lambda checked: [widget.setVisible(checked) for widget in detail_widgets])
        self._refresh_map_compact_values()
        return workspace

    def _populate_map_provider_combo(self) -> None:
        blocker = QSignalBlocker(self.map_provider_combo)
        self.map_provider_combo.clear()
        for provider in self.direction_map_view.providers:
            self.map_provider_combo.addItem(provider.label, provider.mode)
        selected = self.map_provider_combo.findData(self.direction_map_view.selected_mode)
        self.map_provider_combo.setCurrentIndex(max(0, selected))
        del blocker
        if self.direction_map_view.fallback_visible:
            self.map_engine_label.setText(TEXT["map_engine_fallback"])
        elif self.direction_map_view.selected_mode is MapProviderMode.FALLBACK_CANVAS:
            self.map_engine_label.setText("Yerel harita görünümü hazır.")
        else:
            self.map_engine_label.setText("Harita: " + self.map_provider_combo.currentText())

    def _select_map_provider(self) -> None:
        mode = self.map_provider_combo.currentData()
        if mode is None:
            return
        try:
            self.direction_map_view.select_provider(MapProviderMode(mode))
        except ValueError:
            return
        self._populate_map_provider_combo()

    def _refresh_map_providers(self) -> None:
        self.direction_map_view.refresh_providers()
        self._populate_map_provider_combo()

    def _request_pc_location(self) -> None:
        self.map_location_button.setEnabled(False)
        self.map_compact_location_button.setEnabled(False)
        self.pc_location_provider.request_once()

    def _pc_location_pending(self) -> None:
        self.map_location_status.setText("Konum izni bekleniyor…")
        self.map_pc_location_result_label.setText("Sonuç: istek sürüyor")

    def _pc_location_acquired(self, fix: LocationFix) -> None:
        self.map_latitude_spin.setValue(fix.latitude_deg)
        self.map_longitude_spin.setValue(fix.longitude_deg)
        if fix.altitude_m is not None:
            self.map_altitude_spin.setValue(fix.altitude_m)
        self.map_source_combo.setCurrentIndex(self.map_source_combo.findData(PositionSource.AUTO_PC))
        self.map_location_status.setText("Bilgisayar konumu alındı.")
        self.map_accuracy_label.setText(
            "Doğruluk: bilinmiyor" if fix.accuracy_m is None else f"Doğruluk: {fix.accuracy_m:.1f} m"
        )
        self.map_location_time_label.setText("Zaman: " + (fix.timestamp_utc or "bilinmiyor"))
        self.map_pc_location_result_label.setText("Sonuç: başarı")
        self.map_location_button.setEnabled(True)
        self.map_compact_location_button.setEnabled(True)
        self._refresh_map_compact_values()
        if self.df_pair_result is not None:
            self._show_df_pair_on_map(self.df_pair_result)
        else:
            self._show_sensor_on_map()

    def _pc_location_failed(self, text: str) -> None:
        self.map_location_status.setText(text or LOCATION_FAILURE_TEXT)
        self.map_accuracy_label.setText("Doğruluk: bilinmiyor")
        self.map_location_time_label.setText("Zaman: —")
        self.map_pc_location_result_label.setText("Sonuç: " + (text or LOCATION_FAILURE_TEXT))
        self.map_location_button.setEnabled(True)
        self.map_compact_location_button.setEnabled(True)
        self._refresh_map_compact_values()

    def _toggle_manual_location_fields(self) -> None:
        visible = not self.map_manual_fields.isVisible()
        self.map_manual_latitude_spin.setValue(self.map_latitude_spin.value())
        self.map_manual_longitude_spin.setValue(self.map_longitude_spin.value())
        self.map_manual_fields.setVisible(visible)

    def _apply_compact_manual_location(self) -> None:
        self.map_latitude_spin.setValue(self.map_manual_latitude_spin.value())
        self.map_longitude_spin.setValue(self.map_manual_longitude_spin.value())
        self._use_manual_location()
        self.map_manual_fields.hide()

    def _refresh_map_compact_values(self) -> None:
        source = self.map_source_combo.currentData()
        source_label = "Bilgisayar" if source is PositionSource.AUTO_PC else str(source or "—")
        self.map_compact_location.setText(
            f"● {source_label}\n{self.map_latitude_spin.value():.6f}, {self.map_longitude_spin.value():.6f}\n"
            + self.map_accuracy_label.text().replace("Doğruluk: ", "")
        )

    def _use_manual_location(self) -> None:
        try:
            LocationFix(
                latitude_deg=self.map_latitude_spin.value(),
                longitude_deg=self.map_longitude_spin.value(),
                altitude_m=self.map_altitude_spin.value(),
                accuracy_m=None,
                source=PositionSource.MANUAL,
            )
        except ValueError as exc:
            self.map_location_status.setText(f"Manuel konum geçersiz: {exc}")
            return
        self.map_source_combo.setCurrentIndex(self.map_source_combo.findData("MANUEL"))
        self.map_location_status.setText("Manuel koordinat ayarlandı · canlı GNSS değildir.")
        self.map_accuracy_label.setText("Doğruluk: bilinmiyor")
        self.map_location_time_label.setText("Zaman: manuel")
        self._refresh_map_compact_values()
        if self.df_pair_result is not None:
            self._show_df_pair_on_map(self.df_pair_result)
        else:
            self._show_sensor_on_map()

    def _sensor_from_map_controls(self) -> SensorPosition:
        reference = self._df_reference()
        if reference is AntennaReference.NORTH:
            heading = 0.0
        elif reference is AntennaReference.MANUAL_GEOGRAPHIC:
            heading = self.df_manual_reference_spin.value()
        else:
            heading = self.map_heading_spin.value() if self.map_heading_reference_check.isChecked() else None
        source = str(self.map_source_combo.currentData())
        return SensorPosition(
            name=self.map_sensor_name.text().strip(),
            latitude_deg=self.map_latitude_spin.value(),
            longitude_deg=self.map_longitude_spin.value(),
            altitude_m=self.map_altitude_spin.value(),
            heading_deg=heading,
            source=source,
        )

    def _show_sensor_on_map(self) -> None:
        try:
            sensor = self._sensor_from_map_controls()
        except ValueError as exc:
            self.map_status_label.setText(f"Geçersiz sensör konumu: {exc}")
            return
        self.direction_map_view.set_sensor(sensor)
        self.map_status_label.setText("Sensör konumu gösteriliyor.")
        self._refresh_map_compact_values()

    def _activate_map_view(self) -> None:
        self.workspace_tabs.setCurrentWidget(self.direction_workspace)
        self.direction_workspace.setCurrentIndex(1)

    def _show_current_df_on_map(self, *, switch_view: bool = True) -> None:
        estimate = self.current_df_estimate
        if estimate is None:
            self.map_status_label.setText("Haritada gösterilecek DF sonucu yok.")
            if switch_view:
                self._activate_map_view()
            return
        try:
            sensor = self._sensor_from_map_controls()
        except ValueError as exc:
            self.map_status_label.setText(f"Geçersiz sensör konumu: {exc}")
            if switch_view:
                self._activate_map_view()
            return
        measurement = self._peak_df_measurement(estimate)
        if measurement is None:
            self.map_status_label.setText("DF sonucu bulunamadı.")
            if switch_view:
                self._activate_map_view()
            return
        presentation = build_direction_presentation(
            sensor=sensor,
            estimate=estimate,
            peak_measurement=measurement,
            backend="ManualAmplitudeDF",
            source=self._df_source_summary(),
        )
        self.direction_map_view.set_presentation(presentation)
        self._set_map_presentation_values(presentation)
        self.map_status_label.setText(
            presentation.geographic_status if not presentation.has_geographic_lob else TEXT["direction_line_showing"]
        )
        if switch_view:
            self._activate_map_view()

    def _set_map_presentation_values(self, presentation: DirectionPresentation) -> None:
        values = self.map_result_values
        values["frequency"].setText(self._frequency(presentation.frequency_hz))
        values["relative_angle"].setText(self.locale.toString(presentation.relative_antenna_angle_deg, "f", 1) + "°")
        values["azimuth"].setText(
            self.locale.toString(presentation.geographic_azimuth_deg, "f", 1) + "°"
            if presentation.geographic_azimuth_deg is not None
            else presentation.geographic_status
        )
        values["confidence"].setText(self.locale.toString(presentation.confidence, "f", 2))
        values["power"].setText(self.locale.toString(presentation.peak_power_db, "f", 2) + " dBFS")
        values["time"].setText(presentation.measurement_timestamp_utc)
        values["backend"].setText(presentation.source)
        values["sensor_source"].setText(presentation.sensor.source)
        self.map_compact_bearing.setText(
            self.locale.toString(presentation.geographic_azimuth_deg, "f", 0) + "°"
            if presentation.geographic_azimuth_deg is not None
            else self.locale.toString(presentation.relative_antenna_angle_deg, "f", 0) + "°"
        )
        self.map_compact_summary.setText(
            f"{self._frequency(presentation.frequency_hz)} · Güven %{presentation.confidence * 100:.0f}"
        )
        if hasattr(self, "card_bearing_val"):
            self.card_bearing_val.setText(
                self.locale.toString(presentation.geographic_azimuth_deg, "f", 1) + "°"
                if presentation.geographic_azimuth_deg is not None
                else self.locale.toString(presentation.relative_antenna_angle_deg, "f", 1) + "°"
            )

    def _clear_map_lob(self) -> None:
        self.direction_map_view.clear_lob()
        self.map_status_label.setText("Kerteriz hattı temizlendi.")
        self.map_result_values["azimuth"].setText("—")
        self.map_compact_bearing.setText("—")

    def _load_map_training_scenario(self) -> None:
        heading, expected_azimuth = self.map_training_scenario_combo.currentData()
        self.map_sensor_name.setText("Sensör 1")
        self.map_latitude_spin.setValue(39.9334)
        self.map_longitude_spin.setValue(32.8597)
        self.map_altitude_spin.setValue(900.0)
        self.map_heading_spin.setValue(float(heading))
        self.map_heading_reference_check.setChecked(True)
        self.map_source_combo.setCurrentIndex(self.map_source_combo.findData("HOST/SYNTHETIC"))
        self._load_df_training_fixture()
        self._show_current_df_on_map()
        self.map_status_label.setText(
            f"Doğrulama · YAZILIM REFERANS VERİSİ · {TEXT['synthetic_direction_notice']} · {float(expected_azimuth):.1f}° · "
            + TEXT["direction_line_showing"]
        )
