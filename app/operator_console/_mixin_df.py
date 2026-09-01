from __future__ import annotations
import typing
from pathlib import Path
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)
import pyqtgraph as pg
from algorithms.p0.df import DFEstimate, DFMeasurement, ManualAmplitudeDF
from algorithms.p0.field_df import AntennaReference, PositionSource, geographic_bearing_from_manual_reference
from algorithms.p0.map_direction import SensorPosition
from algorithms.p0.recorded_df import RECORDED_DF_SOURCE, RecordedDFReport
if typing.TYPE_CHECKING:
    from algorithms.p0.two_point_df import REAL_TWO_POINT_SOURCE, TwoPointDFResult, analyze_two_point_hackrf_df
    from algorithms.p0.df_fixtures import build_synthetic_df_scene


def load_laboratory_df_dependencies() -> None:
    """Load validation-only DF fixtures for the explicit laboratory UI."""

    global REAL_TWO_POINT_SOURCE, TwoPointDFResult, analyze_two_point_hackrf_df
    global build_synthetic_df_scene
    from algorithms.p0.df_fixtures import build_synthetic_df_scene
    from algorithms.p0.two_point_df import (
        REAL_TWO_POINT_SOURCE,
        TwoPointDFResult,
        analyze_two_point_hackrf_df,
    )

def _source_display_name(source: str) -> str:
    if source == RECORDED_DF_SOURCE:
        return "Kayıtlı Yön Bulma"
    from .main_window import _source_display_name
    return _source_display_name(source)

class DFWorkspaceMixin:
    """Yön bulma (DF) çalışma alanı mixin'i."""

    def _build_direction_workspace(self) -> QTabWidget:
        """Direction and Map views unified."""
        views = QTabWidget()
        views.setObjectName("directionViews")
        views.addTab(self._build_df_workspace(), "Kerteriz")
        views.addTab(self._build_map_direction_workspace(), "Harita")
        views.currentChanged.connect(self._direction_view_changed)
        return views

    def _direction_view_changed(self, index: int) -> None:
        if hasattr(self, "nav_buttons") and len(self.nav_buttons) >= 5:
            # Sync sidebar highlight (3 = Yön, 4 = Konum)
            active_btn_id = 4 if index == 1 else 3
            for idx, btn in enumerate(self.nav_buttons):
                is_active = (idx == active_btn_id)
                btn.setChecked(is_active)
                btn.setProperty("active", "true" if is_active else "false")
                btn.style().unpolish(btn)
                btn.style().polish(btn)

        if index != 1:
            return
        if self.current_df_estimate is not None:
            self._show_current_df_on_map(switch_view=False)
        elif self.map_location_status.text() != "Konum kaynağı seçilmedi.":
            self._show_sensor_on_map()

    def _build_df_workspace(self) -> QWidget:
        self.df_model = ManualAmplitudeDF()
        self.current_df_estimate: DFEstimate | None = None
        self.current_df_source = "KAYIT OYNATMA"
        workspace = QWidget()
        layout = QHBoxLayout(workspace)
        layout.setContentsMargins(8, 8, 8, 8)
        grid = QGridLayout()
        self.df_angle_spin = QDoubleSpinBox()
        self.df_angle_spin.setRange(0.0, 359.9)
        self.df_angle_spin.setSuffix("°")
        self.df_zero_reference_combo = QComboBox()
        self.df_zero_reference_combo.addItem("GERÇEK KUZEY / 0°", AntennaReference.NORTH)
        self.df_zero_reference_combo.addItem("ANTEN REFERANS YÖNÜ", AntennaReference.MANUAL_GEOGRAPHIC)
        self.df_zero_reference_combo.addItem("REFERANS YOK", AntennaReference.UNAVAILABLE)
        self.df_zero_reference_combo.setCurrentIndex(2)
        self.df_manual_reference_spin = QDoubleSpinBox()
        self.df_manual_reference_spin.setRange(0.0, 359.9)
        self.df_manual_reference_spin.setSuffix("°")
        self.df_manual_reference_spin.setEnabled(False)
        self.df_power_spin = QDoubleSpinBox()
        self.df_power_spin.setRange(-160.0, 20.0)
        self.df_power_spin.setValue(-40.0)
        self.df_power_spin.setSuffix(" dBFS")
        self.df_frequency_spin = QDoubleSpinBox()
        self.df_frequency_spin.setRange(1.0, 6000.0)
        self.df_frequency_spin.setValue(145.0)
        self.df_frequency_spin.setSuffix(" MHz")
        self.df_confidence_spin = QDoubleSpinBox()
        self.df_confidence_spin.setRange(0.0, 1.0)
        self.df_confidence_spin.setSingleStep(0.05)
        self.df_confidence_spin.setValue(0.8)

        panel = QFrame()
        panel.setObjectName("directionFieldPanel")
        panel.setMinimumWidth(300)
        panel.setMaximumWidth(360)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 14, 16, 14)
        heading = QLabel("Yön Ölçümü")
        heading.setObjectName("selectedSignalTitle")
        heading.setWordWrap(True)
        panel_layout.addWidget(heading)
        self.df_mode_combo = QComboBox()
        self.df_mode_combo.addItem("SAHA", "field")
        if self.laboratory_mode:
            self.df_mode_combo.addItem("DOĞRULAMA", "training")
        mode_row = QHBoxLayout()
        self.df_mode_caption = QLabel("Mod")
        self.df_mode_caption.setProperty("class", "propCaption")
        self.df_mode_caption.setWordWrap(True)
        mode_row.addWidget(self.df_mode_caption)
        mode_row.addWidget(self.df_mode_combo, 1)
        panel_layout.addLayout(mode_row)
        for row, (c_text, w) in enumerate((
            ("Frekans", self.df_frequency_spin),
            ("0° Referansı", self.df_zero_reference_combo),
            ("Anten Referans Yönü", self.df_manual_reference_spin),
            ("Anten Dönüş Açısı", self.df_angle_spin),
        )):
            l = QLabel(c_text)
            l.setProperty("class", "propCaption")
            l.setWordWrap(True)
            grid.addWidget(l, row, 0)
            grid.addWidget(w, row, 1)
        panel_layout.addLayout(grid)
        self.df_power_measure_button = QPushButton("GÜÇ ÖLÇ")
        self.df_power_measure_button.setObjectName("primaryButton")
        self.df_import_button = QPushButton("ANTEN AÇISI–GÜÇ KAYDINI YÜKLE")
        self.df_zero_recording_path: Path | None = None
        self.df_ninety_recording_path: Path | None = None
        self.df_pair_result: TwoPointDFResult | None = None
        self.df_pair_reference_azimuth_deg = 0.0
        self.df_add_button = QPushButton("Manuel Gücü Kaydet")
        self.df_clear_button = QPushButton("DF Ölçümlerini Temizle")
        if self.laboratory_mode:
            self.df_training_button = QPushButton("Yazılım Referans Verisini Yükle")
            direction_caption = QLabel("İKİ NOKTALI KAYIT İNCELEMESİ")
            direction_caption.setObjectName("selectedSignalTitle")
            direction_caption.setWordWrap(True)
            self.df_zero_recording_button = QPushButton("0° kaydını seç")
            self.df_ninety_recording_button = QPushButton("90° kaydını seç")
            self.df_analyze_pair_button = QPushButton("ANALİZ ET")
            self.df_analyze_pair_button.setObjectName("primaryButton")
            self.df_pair_status = QLabel("Kayıt seçilmedi")
            self.df_pair_status.setProperty("class", "propCaption")
            self.df_pair_status.setWordWrap(True)
            self.df_pair_values = QLabel("0° —\n90° —\nKARAR —")
            self.df_pair_values.setObjectName("directionHint")
            self.df_pair_values.setWordWrap(True)
            panel_layout.addWidget(direction_caption)
            panel_layout.addWidget(self.df_zero_recording_button)
            panel_layout.addWidget(self.df_ninety_recording_button)
            panel_layout.addWidget(self.df_analyze_pair_button)
            panel_layout.addWidget(self.df_pair_status)
            panel_layout.addWidget(self.df_pair_values)
        else:
            real_data_notice = QLabel("Kerteriz kestirimi için anten açısı–alınan güç kaydı veya saha ölçümü gereklidir.")
            real_data_notice.setProperty("class", "propCaption")
            real_data_notice.setWordWrap(True)
            panel_layout.addWidget(real_data_notice)
            panel_layout.addWidget(self.df_import_button)
        self.df_field_status_label = QLabel("Açı  MANUEL    Konum  —    Kaynak  —")
        self.df_field_status_label.setObjectName("dfFieldStatus")
        self.df_field_status_label.setWordWrap(True)
        panel_layout.addWidget(self.df_field_status_label)
        result_title = QLabel("SONUÇ")
        result_title.setObjectName("selectedSignalTitle")
        result_title.setWordWrap(True)
        panel_layout.addWidget(result_title)
        self.df_result_values: dict[str, QLabel] = {}
        result_grid = QGridLayout()
        for row, (key, caption) in enumerate((
            ("relative", "Bağıl Geliş Açısı"),
            ("azimuth", "Gerçek Kerteriz"),
            ("power", "Ölçülen Güç"),
            ("confidence", "Güven"),
            ("source", "Kaynak"),
        )):
            l = QLabel(caption)
            l.setProperty("class", "propCaption")
            l.setWordWrap(True)
            result_grid.addWidget(l, row, 0)
            value = QLabel("—")
            value.setProperty("class", "propValue")
            value.setWordWrap(True)
            result_grid.addWidget(value, row, 1)
            self.df_result_values[key] = value
        panel_layout.addLayout(result_grid)
        self.df_result_label = QLabel("Ölçüm bekleniyor")
        self.df_result_label.setObjectName("directionHint")
        self.df_result_label.setWordWrap(True)
        panel_layout.addWidget(self.df_result_label)

        self.df_technical_toggle = QToolButton()
        self.df_technical_toggle.setText("▸ Teknik Ayrıntılar")
        self.df_technical_toggle.setCheckable(True)
        panel_layout.addWidget(self.df_technical_toggle)
        self.df_technical_panel = QWidget()
        technical_layout = QVBoxLayout(self.df_technical_panel)
        technical_grid = QGridLayout()
        p_lbl = QLabel("Ölçülen Güç")
        p_lbl.setProperty("class", "propCaption")
        p_lbl.setWordWrap(True)
        c_lbl = QLabel("Ölçüm Güveni")
        c_lbl.setProperty("class", "propCaption")
        c_lbl.setWordWrap(True)
        technical_grid.addWidget(p_lbl, 0, 0)
        technical_grid.addWidget(self.df_power_spin, 0, 1)
        technical_grid.addWidget(c_lbl, 1, 0)
        technical_grid.addWidget(self.df_confidence_spin, 1, 1)
        technical_layout.addLayout(technical_grid)
        technical_layout.addWidget(self.df_add_button)
        self.df_training_controls = QWidget()
        training_layout = QVBoxLayout(self.df_training_controls)
        training_layout.setContentsMargins(0, 0, 0, 0)
        if self.laboratory_mode:
            training_layout.addWidget(self.df_training_button)
        self.df_training_controls.hide()
        technical_layout.addWidget(self.df_training_controls)
        self.df_technical_panel.hide()
        panel_layout.addWidget(self.df_technical_panel)
        self.df_history_toggle = QToolButton()
        self.df_history_toggle.setText("▸ Ölçümler (0)")
        self.df_history_toggle.setCheckable(True)
        panel_layout.addWidget(self.df_history_toggle)
        self.df_points_list = QTableWidget(0, 4)
        self.df_points_list.setHorizontalHeaderLabels(("Anten açısı", "Gerçek kerteriz", "Güç", "Kaynak"))
        self.df_points_list.verticalHeader().setVisible(False)
        self.df_points_list.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.df_points_list.horizontalHeader().setStretchLastSection(True)
        self.df_points_list.hide()
        panel_layout.addWidget(self.df_points_list)
        self.df_clear_button.hide()
        panel_layout.addWidget(self.df_clear_button)
        panel_layout.addStretch(1)

        self.df_plot = pg.PlotWidget()
        self.df_plot.setTitle("Açı–Güç", color="#E2EEF8", size="10.5pt")
        self.df_plot.setLabel("bottom", "Anten Açısı", units="°")
        self.df_plot.setLabel("left", "Güç", units="dBFS")
        self.df_plot.showGrid(x=True, y=True, alpha=0.15)
        self.df_curve = self.df_plot.plot(pen=pg.mkPen("#38BDF8", width=2), symbol="o")
        self.df_peak_marker = self.df_plot.plot(pen=None, symbol="o", symbolSize=13, symbolBrush="#10B981")
        self.df_plot.setXRange(0.0, 360.0, padding=0.0)
        self.df_plot.setLimits(xMin=0.0, xMax=360.0)
        layout.addWidget(self.df_plot, 1)
        layout.addWidget(panel)

        self.df_add_button.clicked.connect(self._add_df_measurement)
        self.df_power_measure_button.clicked.connect(self.df_power_measure_requested)
        self.df_import_button.clicked.connect(self._load_recorded_df_report)
        if self.laboratory_mode:
            self.df_zero_recording_button.clicked.connect(lambda: self._choose_df_pair_recording(0))
            self.df_ninety_recording_button.clicked.connect(lambda: self._choose_df_pair_recording(90))
            self.df_analyze_pair_button.clicked.connect(self._analyze_df_pair)
        self.df_zero_reference_combo.currentIndexChanged.connect(self._df_reference_changed)
        self.df_manual_reference_spin.valueChanged.connect(self._df_manual_reference_changed)
        if self.laboratory_mode:
            self.df_training_button.clicked.connect(self._load_df_training_fixture)
        self.df_clear_button.clicked.connect(self._clear_df_measurements)
        self.df_mode_combo.currentIndexChanged.connect(self._df_mode_changed)
        self.df_technical_toggle.toggled.connect(self._set_df_technical_visible)
        self.df_history_toggle.toggled.connect(self._set_df_history_visible)

        for widget in (
            self.df_mode_combo,
            self.df_mode_caption,
            self.df_power_measure_button,
            self.df_import_button,
            self.df_field_status_label,
            result_title,
            self.df_result_label,
            self.df_technical_toggle,
            self.df_technical_panel,
            self.df_history_toggle,
            self.df_points_list,
            self.df_clear_button,
        ):
            widget.hide()
        for index in range(grid.count()):
            item = grid.itemAt(index)
            if item is not None and item.widget() is not None:
                item.widget().hide()
        for index in range(result_grid.count()):
            item = result_grid.itemAt(index)
            if item is not None and item.widget() is not None:
                item.widget().hide()
        return workspace

    def _df_reference(self) -> AntennaReference:
        value = self.df_zero_reference_combo.currentData()
        return value if isinstance(value, AntennaReference) else AntennaReference(str(value))

    def _df_reference_changed(self) -> None:
        reference = self._df_reference()
        self.df_manual_reference_spin.setEnabled(reference is AntennaReference.MANUAL_GEOGRAPHIC)
        if reference is AntennaReference.NORTH:
            self.map_heading_spin.setValue(0.0)
            self.map_heading_reference_check.setChecked(True)
        elif reference is AntennaReference.MANUAL_GEOGRAPHIC:
            self.map_heading_spin.setValue(self.df_manual_reference_spin.value())
            self.map_heading_reference_check.setChecked(True)
        else:
            self.map_heading_reference_check.setChecked(False)

    def _df_manual_reference_changed(self, value: float) -> None:
        if self._df_reference() is AntennaReference.MANUAL_GEOGRAPHIC:
            self.map_heading_spin.setValue(value)
            self.map_heading_reference_check.setChecked(True)

    def _manual_geographic_bearing(self, angle_deg: float) -> float | None:
        reference = self._df_reference()
        if reference is AntennaReference.MANUAL_GEOGRAPHIC:
            return geographic_bearing_from_manual_reference(
                reference, angle_deg, self.df_manual_reference_spin.value()
            )
        if reference is AntennaReference.NORTH:
            return geographic_bearing_from_manual_reference(reference, angle_deg)
        return self.map_heading_spin.value() + angle_deg if self.map_heading_reference_check.isChecked() else None

    def _df_source_summary(self) -> str:
        sources = sorted({item.source for item in self.df_model.measurements})
        return _source_display_name(sources[0]) if len(sources) == 1 else "Karma"

    def _df_mode_changed(self) -> None:
        training = self.df_mode_combo.currentData() == "training"
        self.df_training_controls.setVisible(training and self.df_technical_toggle.isChecked())
        if training:
            self.df_technical_toggle.setChecked(True)

    def _set_df_technical_visible(self, visible: bool) -> None:
        self.df_technical_panel.setVisible(visible)
        self.df_technical_toggle.setText("▾ Teknik Ayrıntılar" if visible else "▸ Teknik Ayrıntılar")
        self.df_training_controls.setVisible(visible and self.df_mode_combo.currentData() == "training")

    def _set_df_history_visible(self, visible: bool) -> None:
        self.df_points_list.setVisible(visible)
        self.df_clear_button.setVisible(visible)
        self.df_history_toggle.setText(
            ("▾" if visible else "▸") + f" Ölçümler ({self.df_points_list.rowCount()})"
        )

    def _update_df_plot_and_summary(self) -> None:
        points = self.df_model.measurements
        angles = [item.angle_deg for item in points]
        powers = [item.relative_power_db for item in points]
        self.df_curve.setData(angles, powers)
        self.df_plot.setXRange(0.0, 360.0, padding=0.0)
        if not points:
            self.df_peak_marker.setData([], [])
            self.df_result_values["relative"].setText("—")
            self.df_result_values["azimuth"].setText("—")
            self.df_result_values["power"].setText("—")
            self.df_result_values["confidence"].setText("—")
            self.df_result_values["source"].setText("—")
            self.df_field_status_label.setText("Açı  MANUEL    Konum  —    Kaynak  —")
            self.df_history_toggle.setText("▸ Ölçümler (0)")
            return
        peak = max(points, key=lambda item: item.relative_power_db)
        self.df_peak_marker.setData([peak.angle_deg], [peak.relative_power_db])
        minimum, maximum = min(powers), max(powers)
        margin = max(3.0, (maximum - minimum) * 0.2)
        self.df_plot.setYRange(minimum - margin, maximum + margin, padding=0.0)
        estimate = self.current_df_estimate
        geographic = self._manual_geographic_bearing(estimate.estimated_angle_deg) if estimate else None
        self.df_result_values["relative"].setText("—" if estimate is None else f"{estimate.estimated_angle_deg:.0f}°")
        self.df_result_values["azimuth"].setText("—" if geographic is None else f"{geographic:.0f}°")
        self.df_result_values["power"].setText(f"{peak.relative_power_db:.1f} dBFS")
        self.df_result_values["confidence"].setText("—" if estimate is None else f"%{estimate.confidence * 100:.0f}")
        self.df_result_values["source"].setText(self.current_df_source)
        source = self.map_source_combo.currentData()
        location = "PC" if source is PositionSource.AUTO_PC else str(source or "—")
        self.df_field_status_label.setText(f"Açı  MANUEL    Konum  {location}    Kaynak  {self.current_df_source}")
        self.df_history_toggle.setText(
            ("▾" if self.df_history_toggle.isChecked() else "▸") + f" Ölçümler ({len(points)})"
        )
        if hasattr(self, "card_bearing_val"):
            self.card_bearing_val.setText("—" if estimate is None else f"{estimate.estimated_angle_deg:.0f}°")

    def _add_df_measurement(self, *, source: str = "MANUEL") -> None:
        geographic_bearing = self._manual_geographic_bearing(self.df_angle_spin.value())
        measurement = DFMeasurement.create(
            angle_deg=self.df_angle_spin.value(),
            relative_power_db=self.df_power_spin.value(),
            frequency_hz=self.df_frequency_spin.value() * 1_000_000.0,
            confidence=self.df_confidence_spin.value(),
            source=source,
            geographic_bearing_deg=geographic_bearing,
        )
        self.df_model.add(measurement)
        self.current_df_source = self._df_source_summary()
        geographic_text = "—" if geographic_bearing is None else f"{geographic_bearing:.1f}°"
        self._add_df_history_row(measurement, geographic_text)
        estimate = self.df_model.estimate()
        self.current_df_estimate = estimate
        self.df_result_label.setText(estimate.status)
        self._update_df_plot_and_summary()

    def save_selected_iq_power(self, *, relative_power_db: float, frequency_hz: float, source: str) -> None:
        self.df_power_spin.setValue(relative_power_db)
        self.df_frequency_spin.setValue(frequency_hz / 1_000_000.0)
        self._add_df_measurement(source=source)

    def _load_recorded_df_report(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Gerçek açı–güç raporunu seç",
            "",
            "DF raporu (*.json);;Tüm dosyalar (*)",
        )
        if not filename:
            return
        try:
            self._apply_recorded_df_report(RecordedDFReport.read(Path(filename)))
        except ValueError as exc:
            self.df_result_label.setText(f"DF Bloke: {exc}")

    def _choose_df_pair_recording(self, angle_deg: int) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            f"{angle_deg}° gerçek HackRF SigMF kaydını seç",
            "",
            "SigMF metadata (*.sigmf-meta);;Tüm dosyalar (*)",
        )
        if not filename:
            return
        path = Path(filename)
        if angle_deg == 0:
            self.df_zero_recording_path = path
            self.df_zero_recording_button.setText(f"0° · {path.name}")
        else:
            self.df_ninety_recording_path = path
            self.df_ninety_recording_button.setText(f"90° · {path.name}")
        self.df_pair_status.setText("İki kayıt da seçildi" if self.df_zero_recording_path and self.df_ninety_recording_path else "Diğer açı kaydı bekleniyor")

    def _analyze_df_pair(self) -> None:
        if self.df_zero_recording_path is None or self.df_ninety_recording_path is None:
            self.df_pair_status.setText("Analiz bloke: 0° ve 90° gerçek kayıtları seçilmelidir.")
            return
        try:
            result = analyze_two_point_hackrf_df(self.df_zero_recording_path, self.df_ninety_recording_path)
        except (OSError, ValueError) as exc:
            self.df_pair_status.setText(f"Analiz Bloke: {exc}")
            return
        self.df_pair_result = result
        self._clear_df_measurements()
        self.df_mode_combo.setCurrentIndex(self.df_mode_combo.findData("field"))
        self.df_frequency_spin.setValue(result.frequency_hz / 1_000_000.0)
        for point in (result.zero, result.ninety):
            measurement = DFMeasurement.create(
                angle_deg=float(point.angle_deg), relative_power_db=point.measured_power_dbfs,
                frequency_hz=result.frequency_hz, confidence=1.0, source=REAL_TWO_POINT_SOURCE,
            )
            self.df_model.add(measurement)
            self._add_df_history_row(measurement)
        self.current_df_source = REAL_TWO_POINT_SOURCE
        self.current_df_estimate = self.df_model.estimate()
        stronger = result.stronger
        stronger_label = "YÖN BELİRSİZ" if stronger is None else ("SOL" if stronger.angle_deg == 0 else "SAĞ")
        self.df_pair_values.setText(
            f"SOL / 0°    {result.zero.measured_power_dbfs:.3f} dBFS\n"
            f"SAĞ / 90°   {result.ninety.measured_power_dbfs:.3f} dBFS\n"
            + (
                f"DAHA GÜÇLÜ YÖN: {stronger_label}"
                if stronger is not None
                else f"YÖN BELİRSİZ · fark {abs(result.power_difference_db):.3f} dB"
            )
        )
        self.df_pair_status.setText("ÖLÇÜM SONUCU")
        if stronger is None:
            self.current_df_estimate = None
        self.df_result_label.setText(f"DAHA GÜÇLÜ YÖN: {stronger_label}")
        self._update_df_plot_and_summary()
        self.map_compact_summary.setText(f"Ölçüm Sonucu: {stronger_label}")
        self._show_df_pair_on_map(result)

    def _show_df_pair_on_map(self, result: TwoPointDFResult) -> None:
        try:
            sensor = SensorPosition(
                name="Sensör 1",
                latitude_deg=self.map_latitude_spin.value(),
                longitude_deg=self.map_longitude_spin.value(),
                altitude_m=self.map_altitude_spin.value(),
                heading_deg=self.df_pair_reference_azimuth_deg,
                source=str(self.map_source_combo.currentData()),
            )
        except ValueError as exc:
            self.map_status_label.setText(f"Ölçüm okları gösterilemedi: {exc}")
            return
        self.direction_map_view.set_measurement_rays(
            sensor,
            reference_azimuth_deg=self.df_pair_reference_azimuth_deg,
            measurements=((0, result.zero.measured_power_dbfs), (90, result.ninety.measured_power_dbfs)),
        )
        self.map_status_label.setText("Ölçüm okları gösteriliyor.")
        self._activate_map_view()

    def _apply_recorded_df_report(self, report: RecordedDFReport) -> None:
        if report.source != RECORDED_DF_SOURCE:
            raise ValueError("DF kaynağı doğrulanamadı")
        self._clear_df_measurements()
        self.df_mode_combo.setCurrentIndex(self.df_mode_combo.findData("field"))
        self.df_frequency_spin.setValue(report.target_frequency_hz / 1_000_000.0)
        for point in report.points:
            geographic_bearing = self._manual_geographic_bearing(point.angle_deg)
            measurement = DFMeasurement.create(
                angle_deg=point.angle_deg,
                relative_power_db=point.measured_power_dbfs,
                frequency_hz=report.target_frequency_hz,
                confidence=point.confidence,
                source=RECORDED_DF_SOURCE,
                geographic_bearing_deg=geographic_bearing,
            )
            self.df_model.add(measurement)
            self._add_df_history_row(
                measurement,
                "—" if geographic_bearing is None else f"{geographic_bearing:.1f}°",
            )
        self.current_df_source = RECORDED_DF_SOURCE
        self.current_df_estimate = self.df_model.estimate()
        self.df_result_label.setText(f"{len(report.points)} açı · {self.current_df_estimate.status}")
        self._update_df_plot_and_summary()

    def _add_df_history_row(self, measurement: DFMeasurement, geographic_text: str | None = None) -> None:
        row = self.df_points_list.rowCount()
        self.df_points_list.insertRow(row)
        geographic = geographic_text
        if geographic is None:
            geographic = "—" if measurement.geographic_bearing_deg is None else f"{measurement.geographic_bearing_deg:.1f}°"
        for column, value in enumerate((
            f"{measurement.angle_deg:.1f}°",
            geographic,
            f"{measurement.relative_power_db:.2f} dBFS",
            {
                "HOST/SYNTHETIC": "YAZILIM REFERANS VERİSİ",
                "REPLAY": "KAYIT OYNATMA",
            }.get(measurement.source, measurement.source),
        )):
            self.df_points_list.setItem(row, column, QTableWidgetItem(value))

    def set_df_power_measurement_unavailable(self, detail: str) -> None:
        self.df_result_label.setText(detail)

    def _load_df_training_fixture(self) -> None:
        if not self.laboratory_mode:
            raise RuntimeError("Eğitim verisi yalnız offline doğrulama uygulamasında kullanılabilir.")
        self._clear_df_measurements()
        scene = build_synthetic_df_scene(75.0)
        for index, (angle, power, confidence) in enumerate(scene.measurements):
            measurement = DFMeasurement.create(
                angle_deg=angle,
                relative_power_db=power,
                frequency_hz=self.df_frequency_spin.value() * 1_000_000.0,
                confidence=confidence,
                timestamp_utc=f"2026-01-01T00:00:{index:02d}Z",
                source="HOST/SYNTHETIC",
                geographic_bearing_deg=self._manual_geographic_bearing(angle),
            )
            self.df_model.add(measurement)
            geographic = self._manual_geographic_bearing(angle)
            self._add_df_history_row(
                measurement,
                "—" if geographic is None else f"{geographic:.1f}°",
            )
        estimate = self.df_model.estimate()
        self.current_df_estimate = estimate
        self.current_df_source = "YAZILIM REFERANS VERİSİ"
        error = ManualAmplitudeDF.angular_error_deg(estimate.estimated_angle_deg, scene.truth_bearing_deg)
        self.df_result_label.setText(f"YAZILIM REFERANS VERİSİ · hata {error:.1f}° · {estimate.status}")
        self._update_df_plot_and_summary()

    def _clear_df_measurements(self) -> None:
        self.df_model.clear()
        self.current_df_estimate = None
        self.current_df_source = "KAYIT OYNATMA"
        self.df_points_list.setRowCount(0)
        self.df_result_label.setText("Ölçüm bekleniyor")
        self._update_df_plot_and_summary()

    def _peak_df_measurement(self, estimate: DFEstimate) -> DFMeasurement | None:
        return next(
            (item for item in self.df_model.measurements if item.angle_deg == estimate.raw_maximum_angle_deg),
            None,
        )
