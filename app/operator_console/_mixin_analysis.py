"""Analiz çalışma alanı mixin'i."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .spectrum_view import AnalysisSpectrumView
from .ui_text import TEXT

class AnalysisWorkspaceMixin:
    def _build_analysis_workspace(self) -> QWidget:
        """Create the focused parameter analysis workspace with ONE clean panel."""
        self.analysis_spectrum = AnalysisSpectrumView()
        panel = QFrame()
        panel.setObjectName("analysisPanel")
        panel.setMinimumWidth(280)
        panel.setMaximumWidth(340)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        heading = QLabel("Parametreler")
        heading.setObjectName("selectedSignalTitle")
        heading.setWordWrap(True)
        layout.addWidget(heading)

        self.analysis_freq_val = QLabel("—")
        self.analysis_freq_val.setObjectName("selectedSignalFreq")
        self.analysis_freq_val.setWordWrap(True)
        layout.addWidget(self.analysis_freq_val)

        self.analysis_event_value = QLabel("Sinyal seçilmedi")
        self.analysis_event_value.setObjectName("selectedSignalBadge")
        self.analysis_event_value.setWordWrap(True)
        layout.addWidget(self.analysis_event_value)

        sep = QFrame()
        sep.setObjectName("subtleSeparator")
        layout.addWidget(sep)

        # Clean 2-column parameter table
        grid = QGridLayout()
        grid.setContentsMargins(0, 2, 0, 2)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        self.parameter_values: dict[str, QLabel] = {}

        primary_fields = (
            ("p0_bandwidth", "Bant Genişliği"),
            ("p0_lower", "Alt Frekans"),
            ("p0_upper", "Üst Frekans"),
            ("p0_snr", "SNR"),
            ("p0_peak_power", "Seviye"),
            ("p0_domain", "Sinyal Türü"),
            ("p0_detection", "Durum"),
        )
        for row, (key, caption) in enumerate(primary_fields):
            label = QLabel(caption, panel)
            label.setProperty("class", "propCaption")
            label.setWordWrap(True)
            value = QLabel("—", panel)
            value.setProperty("class", "propValue")
            value.setWordWrap(True)
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(label, row, 0)
            grid.addWidget(value, row, 1)
            self.parameter_values[key] = value
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        # Technical details (collapsed by default)
        sep2 = QFrame()
        sep2.setObjectName("subtleSeparator")
        layout.addWidget(sep2)

        self.analysis_tech_toggle = QToolButton()
        self.analysis_tech_toggle.setObjectName("collapseToggle")
        self.analysis_tech_toggle.setText("▸ Teknik Ayrıntılar")
        self.analysis_tech_toggle.setCheckable(True)
        layout.addWidget(self.analysis_tech_toggle)

        self.analysis_tech_widget = QWidget()
        tech_layout = QGridLayout(self.analysis_tech_widget)
        tech_layout.setContentsMargins(0, 4, 0, 0)
        tech_layout.setHorizontalSpacing(10)
        tech_layout.setVerticalSpacing(4)

        secondary_fields = (
            ("p0_center", "Emisyon Merkez Frekansı"),
            ("p0_bandwidth_method", "Yöntem"),
            ("p0_coarse_span", "Kaba Aralık"),
            ("p0_power", "Kanal Gücü"),
            ("p0_region", "Frekans Bölgesi"),
            ("p0_backend", "Hesaplama Kaynağı"),
            ("p0_source", "Veri Kaynağı"),
            ("emission_center", TEXT["emission_center"]),
            ("carrier_line", TEXT["carrier_line"]),
            ("lower_edge", TEXT["lower_band_edge"]),
            ("upper_edge", TEXT["upper_band_edge"]),
            ("bandwidth", TEXT["occupied_bandwidth"]),
            ("peak_power", TEXT["peak_power"]),
            ("channel_power", TEXT["channel_power"]),
            ("domain", TEXT["signal_domain"]),
        )
        for row, (key, caption) in enumerate(secondary_fields):
            label = QLabel(caption, self.analysis_tech_widget)
            label.setProperty("class", "propCaption")
            label.setWordWrap(True)
            value = QLabel(TEXT["not_validated"], self.analysis_tech_widget)
            value.setProperty("class", "propValue")
            value.setWordWrap(True)
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            tech_layout.addWidget(label, row, 0)
            tech_layout.addWidget(value, row, 1)
            self.parameter_values[key] = value

        self.analysis_tech_widget.hide()
        layout.addWidget(self.analysis_tech_widget)

        self.analysis_tech_toggle.toggled.connect(
            lambda checked: [
                self.analysis_tech_widget.setVisible(checked),
                self.analysis_tech_toggle.setText("▾ Teknik Ayrıntılar" if checked else "▸ Teknik Ayrıntılar"),
            ]
        )

        self.span_value = QLabel(TEXT["no_analysis_span"])
        self.span_value.setWordWrap(True)
        self.span_value.hide()
        self.measurement_state = QLabel(TEXT["measurement_not_started"])
        self.measurement_state.setObjectName("parameterState")
        self.measurement_state.setWordWrap(True)
        self.measurement_state.hide()
        self.parameter_state = QLabel(TEXT["no_parameter"])
        self.parameter_state.setObjectName("measurementResultStatus")
        self.parameter_state.setWordWrap(True)
        self.parameter_state.hide()
        self.quality_value = QLabel(TEXT["quality_not_available"])
        self.quality_value.setWordWrap(True)
        self.quality_value.hide()
        layout.addWidget(self.span_value)
        layout.addWidget(self.measurement_state)
        layout.addWidget(self.parameter_state)
        layout.addWidget(self.quality_value)

        calibration = QLabel(TEXT["uncalibrated_e1"])
        calibration.setObjectName("calibrationNote")
        calibration.setWordWrap(True)
        layout.addWidget(calibration)

        button_row = QHBoxLayout()
        self.measure_button = QPushButton(TEXT["start_measurement"])
        self.measure_button.setObjectName("primaryButton")
        self.measure_button.setEnabled(False)
        self.measure_button.hide()
        self._measurement_run_count = 0
        self.clear_measurement_button = QPushButton(TEXT["clear_measurement"])
        button_row.addWidget(self.measure_button)
        button_row.addWidget(self.clear_measurement_button)
        layout.addLayout(button_row)
        layout.addStretch(1)

        scroll = self._scroll_panel(panel, "analysisScroll")
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.analysis_spectrum)
        splitter.addWidget(scroll)
        splitter.setSizes([1050, 310])
        splitter.setStretchFactor(0, 1)
        splitter.setChildrenCollapsible(False)
        workspace = QWidget()
        outer = QVBoxLayout(workspace)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(splitter)
        return workspace
