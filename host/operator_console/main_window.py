"""Main window for the permanent spectrum, detection, and parameter console."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QLocale, QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
import numpy as np
import pyqtgraph as pg

from reference.sigmf.contract import ContractReport
from reference.detection import DetectionEvent, DetectionFrameResult
from reference.parameters import EventParameterEstimate, ParameterFrameResult
from reference.et import (
    AnalogDeceptionConfig,
    AnalogDeceptionEngine,
    ContinuousJammingConfig,
    ContinuousJammingEngine,
    ETMissionController,
    SafetyMode,
)
from reference.p0 import DFMeasurement, ManualAmplitudeDF, P0ParameterResult

from .spectrum_view import AnalysisSpectrumView, SpectrumView
from .ui_text import TEXT


class MainWindow(QMainWindow):
    """Task-focused Turkish spectrum review window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(TEXT["window_title"])
        self.setMinimumSize(960, 600)
        self.resize(1440, 900)
        self.locale = QLocale(QLocale.Language.Turkish, QLocale.Country.Turkey)

        self.open_button = QPushButton(TEXT["open_sigmf"])
        self.open_button.setObjectName("primaryButton")
        self.source_value = QLabel(TEXT["no_source"])
        self.source_value.setObjectName("sourceValue")
        self.source_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.source_value.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        title = QLabel(TEXT["application_title"])
        title.setObjectName("applicationTitle")
        source_caption = QLabel(TEXT["source"])
        source_caption.setObjectName("caption")
        self.source_type_combo = QComboBox()
        self.source_type_combo.setObjectName("sourceTypeCombo")
        self.source_type_combo.addItem(TEXT["source_sigmf"], "sigmf")
        self.source_type_combo.addItem(TEXT["source_hackrf"], "hackrf")
        self.source_type_combo.addItem(TEXT["source_deterministic"], "deterministic_test")
        self.source_type_combo.setAccessibleName(TEXT["source_type"])
        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(12)
        header_layout.addWidget(title)
        header_layout.addSpacing(12)
        header_layout.addWidget(source_caption)
        header_layout.addWidget(self.source_type_combo)
        header_layout.addWidget(self.source_value, 1)
        header_layout.addWidget(self.open_button)

        self.notification = QLabel()
        self.notification.setObjectName("notification")
        self.notification.setWordWrap(True)
        self.notification.hide()

        self.spectrum_view = SpectrumView()
        self.spectrum_view.setMinimumSize(700, 300)
        metadata_panel = self._scroll_panel(self._build_metadata_panel(), "operationScroll")
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setObjectName("mainSplitter")
        main_splitter.addWidget(self.spectrum_view)
        main_splitter.addWidget(metadata_panel)
        main_splitter.setSizes([1040, 300])
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)
        main_splitter.setChildrenCollapsible(False)

        controls = self._build_controls()
        operation = QWidget()
        operation_layout = QVBoxLayout(operation)
        operation_layout.setContentsMargins(0, 0, 0, 0)
        operation_layout.setSpacing(8)
        operation_layout.addWidget(main_splitter, 1)
        operation_layout.addWidget(controls)
        analysis = self._build_analysis_workspace()
        self.workspace_tabs = QTabWidget()
        self.workspace_tabs.setObjectName("workspaceTabs")
        self.workspace_tabs.addTab(operation, TEXT["operation_workspace"])
        self.workspace_tabs.addTab(analysis, TEXT["analysis_workspace"])
        self.workspace_tabs.addTab(self._build_listening_workspace(), TEXT["listening_workspace"])
        self.workspace_tabs.addTab(self._build_df_workspace(), TEXT["direction_finding_workspace"])
        self.workspace_tabs.addTab(self._build_system_workspace(), TEXT["system_status_workspace"])
        self.workspace_tabs.addTab(self._build_et_workspace(), TEXT["et_workspace"])
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(header)
        layout.addWidget(self.notification)
        layout.addWidget(self.workspace_tabs, 1)
        self.setCentralWidget(central)
        self.show_empty()
        self.set_acquisition_mode("sigmf")

    def _build_metadata_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("metadataPanel")
        panel.setMinimumWidth(260)
        panel.setMaximumWidth(360)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        heading = QLabel(TEXT["metadata"])
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)

        self.hackrf_panel = QFrame()
        self.hackrf_panel.setObjectName("hackrfPanel")
        hackrf_layout = QVBoxLayout(self.hackrf_panel)
        hackrf_layout.setContentsMargins(0, 0, 0, 8)
        hackrf_layout.setSpacing(6)
        hackrf_heading = QLabel(TEXT["hackrf_controls"])
        hackrf_heading.setObjectName("sectionTitle")
        hackrf_layout.addWidget(hackrf_heading)
        self.hackrf_status = QLabel(TEXT["hardware_acceptance_pending"])
        self.hackrf_status.setObjectName("hackrfStatus")
        self.hackrf_status.setWordWrap(True)
        hackrf_layout.addWidget(self.hackrf_status)
        hackrf_grid = QGridLayout()
        self.hackrf_center_spin = QDoubleSpinBox()
        self.hackrf_center_spin.setRange(1.0, 6000.0)
        self.hackrf_center_spin.setDecimals(3)
        self.hackrf_center_spin.setValue(100.0)
        self.hackrf_sample_combo = QComboBox()
        for label, value in (("8", 8_000_000), ("10", 10_000_000), ("20", 20_000_000)):
            self.hackrf_sample_combo.addItem(label, value)
        self.hackrf_lna_spin = QSpinBox()
        self.hackrf_lna_spin.setRange(0, 40)
        self.hackrf_lna_spin.setSingleStep(8)
        self.hackrf_lna_spin.setValue(16)
        self.hackrf_vga_spin = QSpinBox()
        self.hackrf_vga_spin.setRange(0, 62)
        self.hackrf_vga_spin.setSingleStep(2)
        self.hackrf_vga_spin.setValue(16)
        self.hackrf_amp_checkbox = QCheckBox(TEXT["rf_amplifier"])
        for row, (caption, widget) in enumerate(
            (
                (TEXT["center_frequency_mhz"], self.hackrf_center_spin),
                (TEXT["sample_rate_msps"], self.hackrf_sample_combo),
                (TEXT["lna_gain"], self.hackrf_lna_spin),
                (TEXT["vga_gain"], self.hackrf_vga_spin),
            )
        ):
            hackrf_grid.addWidget(QLabel(caption), row, 0)
            hackrf_grid.addWidget(widget, row, 1)
        hackrf_grid.addWidget(self.hackrf_amp_checkbox, 4, 0, 1, 2)
        hackrf_layout.addLayout(hackrf_grid)
        self.hackrf_refresh_button = QPushButton(TEXT["refresh_hardware"])
        self.hackrf_start_button = QPushButton(TEXT["start_capture"])
        self.hackrf_stop_button = QPushButton(TEXT["stop_capture"])
        hackrf_buttons = QGridLayout()
        hackrf_buttons.addWidget(self.hackrf_refresh_button, 0, 0, 1, 2)
        hackrf_buttons.addWidget(self.hackrf_start_button, 1, 0)
        hackrf_buttons.addWidget(self.hackrf_stop_button, 1, 1)
        hackrf_layout.addLayout(hackrf_buttons)
        layout.addWidget(self.hackrf_panel)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)
        self.metadata_values: dict[str, QLabel] = {}
        fields = (
            ("center_frequency", TEXT["center_frequency"]),
            ("sample_rate", TEXT["sample_rate"]),
            ("datatype", TEXT["datatype"]),
            ("frame_length", TEXT["frame_length"]),
            ("frame_position", TEXT["frame_position"]),
            ("channel", TEXT["channel"]),
        )
        for row, (key, caption) in enumerate(fields):
            caption_label = QLabel(caption)
            caption_label.setObjectName("metadataCaption")
            value_label = QLabel("—")
            value_label.setObjectName("metadataValue")
            value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            value_label.setWordWrap(True)
            grid.addWidget(caption_label, row, 0)
            grid.addWidget(value_label, row, 1)
            self.metadata_values[key] = value_label
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        profile_heading = QLabel(TEXT["profile"])
        profile_heading.setObjectName("sectionTitle")
        layout.addWidget(profile_heading)
        self.profile_value = QLabel("—")
        self.profile_value.setObjectName("profileValue")
        self.profile_value.setWordWrap(True)
        self.profile_value.setMinimumHeight(72)
        self.profile_value.setToolTip(TEXT["validated_envelope"])
        layout.addWidget(self.profile_value)

        detection_heading = QLabel(TEXT["detections"])
        detection_heading.setObjectName("sectionTitle")
        layout.addWidget(detection_heading)
        self.detection_state = QLabel(TEXT["no_detection"])
        self.detection_state.setObjectName("detectionState")
        layout.addWidget(self.detection_state)
        self.detection_list = QListWidget()
        self.detection_list.setObjectName("detectionList")
        self.detection_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.detection_list.setMinimumHeight(110)
        layout.addWidget(self.detection_list, 1)
        self.detection_note = QLabel(TEXT["detection_detail"])
        self.detection_note.setObjectName("detectionNote")
        self.detection_note.setWordWrap(True)
        layout.addWidget(self.detection_note)
        layout.addStretch(1)
        return panel

    @staticmethod
    def _scroll_panel(panel: QWidget, name: str) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName(name)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(panel)
        scroll.setMinimumWidth(280)
        scroll.setMaximumWidth(390)
        return scroll

    def _build_analysis_workspace(self) -> QWidget:
        self.analysis_spectrum = AnalysisSpectrumView()
        panel = QFrame()
        panel.setObjectName("analysisPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        heading = QLabel(TEXT["analysis_workspace"])
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)
        self.analysis_event_value = QLabel(TEXT["select_confirmed_event"])
        self.analysis_event_value.setWordWrap(True)
        self.analysis_event_value.setAccessibleDescription(TEXT["select_confirmed_event"])
        layout.addWidget(self.analysis_event_value)
        self.span_value = QLabel(TEXT["no_analysis_span"])
        self.span_value.setWordWrap(True)
        layout.addWidget(self.span_value)
        self.measurement_state = QLabel(TEXT["measurement_not_started"])
        self.parameter_state = QLabel(TEXT["no_parameter"])
        self.measurement_state.setObjectName("parameterState")
        self.measurement_state.setWordWrap(True)
        layout.addWidget(self.measurement_state)
        grid = QGridLayout()
        self.parameter_values = {}
        fields = (
            ("p0_detection", "Tespit"),
            ("p0_carrier", "Taşıyıcı Frekansı"),
            ("p0_bandwidth", "Bant Genişliği"),
            ("p0_power", "Güç Seviyesi"),
            ("p0_snr", "SNR"),
            ("p0_domain", "Analog/Sayısal"),
            ("p0_region", "Peak/Bölge"),
            ("p0_backend", "Backend"),
            ("p0_source", "Sonuç Kaynağı"),
            ("emission_center", TEXT["emission_center"]),
            ("carrier_line", TEXT["carrier_line"]),
            ("lower_edge", TEXT["lower_band_edge"]),
            ("upper_edge", TEXT["upper_band_edge"]),
            ("bandwidth", TEXT["occupied_bandwidth"]),
            ("peak_power", TEXT["peak_power"]),
            ("channel_power", TEXT["channel_power"]),
            ("domain", TEXT["signal_domain"]),
        )
        for row, (key, caption) in enumerate(fields):
            label = QLabel(caption)
            label.setObjectName("metadataCaption")
            label.setWordWrap(True)
            value = QLabel(TEXT["not_validated"])
            value.setObjectName("parameterValue")
            value.setWordWrap(True)
            grid.addWidget(label, row, 0)
            grid.addWidget(value, row, 1)
            self.parameter_values[key] = value
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        self.quality_value = QLabel(TEXT["quality_not_available"])
        self.quality_value.setWordWrap(True)
        layout.addWidget(self.quality_value)
        calibration = QLabel(TEXT["uncalibrated_e1"])
        calibration.setObjectName("calibrationNote")
        calibration.setWordWrap(True)
        layout.addWidget(calibration)
        button_row = QHBoxLayout()
        self.measure_button = QPushButton(TEXT["start_measurement"])
        self.measure_button.setObjectName("primaryButton")
        self.measure_button.setEnabled(False)
        self.clear_measurement_button = QPushButton(TEXT["clear_measurement"])
        button_row.addWidget(self.measure_button)
        button_row.addWidget(self.clear_measurement_button)
        layout.addLayout(button_row)
        layout.addStretch(1)
        scroll = self._scroll_panel(panel, "analysisScroll")
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.analysis_spectrum)
        splitter.addWidget(scroll)
        splitter.setSizes([1000, 340])
        splitter.setStretchFactor(0, 1)
        splitter.setChildrenCollapsible(False)
        workspace = QWidget()
        outer = QVBoxLayout(workspace)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(splitter)
        return workspace

    def _build_df_workspace(self) -> QWidget:
        self.df_model = ManualAmplitudeDF()
        workspace = QWidget()
        layout = QHBoxLayout(workspace)
        panel = QFrame()
        panel_layout = QVBoxLayout(panel)
        heading = QLabel("Manuel Genlik Tabanlı Yön Bulma")
        heading.setObjectName("sectionTitle")
        panel_layout.addWidget(heading)
        grid = QGridLayout()
        self.df_angle_spin = QDoubleSpinBox()
        self.df_angle_spin.setRange(0.0, 359.9)
        self.df_angle_spin.setSuffix("°")
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
        for row, (caption, widget) in enumerate((("Anten Açısı", self.df_angle_spin), ("Bounded Göreli Güç", self.df_power_spin), ("Frekans", self.df_frequency_spin), ("Ölçüm Güveni", self.df_confidence_spin))):
            grid.addWidget(QLabel(caption), row, 0)
            grid.addWidget(widget, row, 1)
        panel_layout.addLayout(grid)
        self.df_add_button = QPushButton("Ölçüm Noktasını Kaydet")
        self.df_clear_button = QPushButton("DF Ölçümlerini Temizle")
        panel_layout.addWidget(self.df_add_button)
        panel_layout.addWidget(self.df_clear_button)
        self.df_result_label = QLabel("LOB için en az üç farklı açı ölçün.")
        self.df_result_label.setWordWrap(True)
        panel_layout.addWidget(self.df_result_label)
        self.df_points_list = QListWidget()
        panel_layout.addWidget(self.df_points_list, 1)
        self.df_plot = pg.PlotWidget()
        self.df_plot.setTitle("Açı–Güç Eğrisi")
        self.df_plot.setLabel("bottom", "Anten Açısı", units="°")
        self.df_plot.setLabel("left", "Göreli Güç", units="dBFS")
        self.df_plot.showGrid(x=True, y=True, alpha=0.2)
        self.df_curve = self.df_plot.plot(pen=pg.mkPen("#3A9DFF", width=2), symbol="o")
        layout.addWidget(self.df_plot, 1)
        layout.addWidget(self._scroll_panel(panel, "dfScroll"))
        self.df_add_button.clicked.connect(self._add_df_measurement)
        self.df_clear_button.clicked.connect(self._clear_df_measurements)
        return workspace

    def _build_system_workspace(self) -> QWidget:
        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        heading = QLabel("P0 Sistem Durumu ve Sonuç Kaynağı")
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)
        self.system_status_values: dict[str, QLabel] = {}
        rows = (
            ("processing", "Algoritma Yürütücüsü", "HOST REFERENCE · host üzerinde doğrulama"),
            ("fpga", "ZedBoard FPGA", "FUTURE ZEDBOARD HARDWARE · kartta çalıştırılmadı"),
            ("transport", "PC↔ZedBoard Taşıması", "BAĞLI DEĞİL · yerel loopback hazır"),
            ("hackrf", "HackRF-1 RX", "BLOCKED_TOOLCHAIN · araçlar bulunamadı"),
            ("petalinux", "PetaLinux / ARM", "BLOCKED / ÇALIŞTIRILMADI"),
            ("calibration", "RF Güç Kalibrasyonu", TEXT["calibration_pending"]),
            ("et", "HackRF-2 TX", "HARDWARE_TX_LOCKED · OFFLINE/LOOPBACK"),
        )
        grid = QGridLayout()
        for row, (key, caption, value) in enumerate(rows):
            label = QLabel(value)
            label.setWordWrap(True)
            grid.addWidget(QLabel(caption), row, 0)
            grid.addWidget(label, row, 1)
            self.system_status_values[key] = label
        layout.addLayout(grid)
        layout.addStretch(1)
        return workspace

    def _build_et_workspace(self) -> QWidget:
        self.et_mission = ETMissionController()
        self.jamming_engine = ContinuousJammingEngine()
        self.deception_engine = AnalogDeceptionEngine()
        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        controls = QGridLayout()
        self.et_mode_combo = QComboBox()
        self.et_mode_combo.addItem("OFFLINE", SafetyMode.OFFLINE)
        self.et_mode_combo.addItem("LOOPBACK", SafetyMode.LOOPBACK)
        self.et_mode_combo.addItem("CABLED_LAB · KİLİTLİ", SafetyMode.CABLED_LAB)
        self.et_mode_combo.addItem("HARDWARE_TX_LOCKED", SafetyMode.HARDWARE_TX_LOCKED)
        self.et_family_combo = QComboBox()
        for label, value in (("Tekli", "single"), ("Çoklu", "multiple"), ("Barrage", "barrage")):
            self.et_family_combo.addItem(label, value)
        self.et_duration_spin = QDoubleSpinBox()
        self.et_duration_spin.setRange(0.1, 30.0)
        self.et_duration_spin.setValue(1.0)
        self.et_duration_spin.setSuffix(" s")
        self.et_jam_start = QPushButton("Sürekli Karıştırma · Başlat")
        self.et_jam_stop = QPushButton("Durdur")
        self.et_deception_mode = QComboBox()
        self.et_deception_mode.addItems(["NFM", "FM"])
        self.et_audio_scenario = QComboBox()
        self.et_audio_scenario.addItems(["1 kHz kayıtlı test senaryosu", "Konuşma bandı çoklu ton senaryosu"])
        self.et_audio_level = QDoubleSpinBox()
        self.et_audio_level.setRange(0.1, 0.9)
        self.et_audio_level.setValue(0.7)
        self.et_deception_start = QPushButton("Analog Aldatma · Başlat")
        self.et_deception_stop = QPushButton("Durdur")
        rows = (("Güvenlik Modu", self.et_mode_combo), ("Karıştırma Türü", self.et_family_combo), ("Görev Süresi", self.et_duration_spin), ("Ses/Scenario", self.et_audio_scenario), ("FM/NFM", self.et_deception_mode), ("Çıkış Normalizasyonu", self.et_audio_level))
        for row, (caption, widget) in enumerate(rows):
            controls.addWidget(QLabel(caption), row, 0)
            controls.addWidget(widget, row, 1)
        controls.addWidget(self.et_jam_start, 0, 2)
        controls.addWidget(self.et_jam_stop, 1, 2)
        controls.addWidget(self.et_deception_start, 3, 2)
        controls.addWidget(self.et_deception_stop, 4, 2)
        self.et_emergency_stop = QPushButton("ACİL DURDURMA")
        controls.addWidget(self.et_emergency_stop, 5, 2)
        self.et_state_label = QLabel("HAZIR · Donanım TX yolu uygulanmadı")
        self.et_state_label.setWordWrap(True)
        layout.addLayout(controls)
        layout.addWidget(self.et_state_label)
        plots = QHBoxLayout()
        self.et_waveform_plot = pg.PlotWidget()
        self.et_waveform_plot.setTitle("Kompleks Taban Bant Önizleme · I")
        self.et_waveform_curve = self.et_waveform_plot.plot(pen=pg.mkPen("#3A9DFF"))
        self.et_spectrum_plot = pg.PlotWidget()
        self.et_spectrum_plot.setTitle("Spektrum Önizleme")
        self.et_spectrum_curve = self.et_spectrum_plot.plot(pen=pg.mkPen("#FFB020"))
        plots.addWidget(self.et_waveform_plot)
        plots.addWidget(self.et_spectrum_plot)
        layout.addLayout(plots, 1)
        self.et_jam_start.clicked.connect(self._start_jamming_preview)
        self.et_jam_stop.clicked.connect(self._stop_et_mission)
        self.et_deception_start.clicked.connect(self._start_deception_preview)
        self.et_deception_stop.clicked.connect(self._stop_et_mission)
        self.et_emergency_stop.clicked.connect(self._emergency_stop_et)
        return workspace

    def _build_controls(self) -> QFrame:
        controls = QFrame()
        controls.setObjectName("controls")
        layout = QGridLayout(controls)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        self.start_button = QPushButton(TEXT["start"])
        self.pause_button = QPushButton(TEXT["pause"])
        self.stop_button = QPushButton(TEXT["stop"])
        self.frame_spin = QSpinBox()
        self.frame_spin.setMinimum(1)
        self.frame_spin.setMaximum(1)
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(1, 30)
        self.speed_spin.setValue(10)
        self.speed_spin.setSuffix(" çerçeve/s")
        self.axis_combo = QComboBox()
        self.axis_combo.addItems([TEXT["axis_offset"], TEXT["axis_absolute"]])
        self.metric_combo = QComboBox()
        self.metric_combo.addItems([TEXT["bin_power"], TEXT["psd"]])
        self.dc_checkbox = QCheckBox(TEXT["remove_dc"])
        self.average_checkbox = QCheckBox(TEXT["average"])
        self.detection_layer_checkbox = QCheckBox(TEXT["detection_layer"])
        self.detection_layer_checkbox.setChecked(True)
        self.pfa_combo = QComboBox()
        for label, value in (("1e-3", 1e-3), ("1e-4", 1e-4), ("1e-5", 1e-5)):
            self.pfa_combo.addItem(label, value)
        self.pfa_combo.setCurrentIndex(1)
        self.pfa_combo.setToolTip(TEXT["validated_envelope"])
        self.center_checkbox = QCheckBox(TEXT["evaluate_center"])
        self.center_checkbox.setChecked(True)
        self.state_value = QLabel(TEXT["empty"])
        self.state_value.setObjectName("stateValue")
        self.state_value.setWordWrap(True)
        frame_caption = QLabel(TEXT["frame_position"])
        speed_caption = QLabel(TEXT["review_speed"])
        axis_caption = QLabel(TEXT["axis"])
        display_caption = QLabel(TEXT["display"])
        pfa_caption = QLabel(TEXT["pfa"])
        for caption in (frame_caption, speed_caption, axis_caption, display_caption, pfa_caption):
            caption.setWordWrap(True)

        layout.addWidget(self.start_button, 0, 0)
        layout.addWidget(self.pause_button, 0, 1)
        layout.addWidget(self.stop_button, 0, 2)
        layout.addWidget(frame_caption, 0, 3)
        layout.addWidget(self.frame_spin, 0, 4)
        layout.addWidget(speed_caption, 0, 5)
        layout.addWidget(self.speed_spin, 0, 6)
        layout.addWidget(self.state_value, 0, 7, 1, 2)
        layout.addWidget(axis_caption, 1, 0)
        layout.addWidget(self.axis_combo, 1, 1, 1, 2)
        layout.addWidget(display_caption, 1, 3)
        layout.addWidget(self.metric_combo, 1, 4, 1, 2)
        layout.addWidget(self.dc_checkbox, 1, 6)
        layout.addWidget(self.average_checkbox, 1, 7, 1, 2)
        layout.addWidget(self.detection_layer_checkbox, 2, 0, 1, 2)
        layout.addWidget(pfa_caption, 2, 2)
        layout.addWidget(self.pfa_combo, 2, 3)
        layout.addWidget(self.center_checkbox, 2, 4, 1, 3)
        layout.setColumnStretch(8, 1)
        return controls

    def _build_listening_workspace(self) -> QWidget:
        self.listening_spectrum = AnalysisSpectrumView()
        panel = QFrame()
        panel.setObjectName("listeningPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        heading = QLabel(TEXT["listening_workspace"])
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)
        self.listening_source_value = QLabel(TEXT["no_source"])
        self.listening_source_value.setWordWrap(True)
        layout.addWidget(self.listening_source_value)
        self.listening_event_value = QLabel(TEXT["listening_select_event"])
        self.listening_event_value.setWordWrap(True)
        layout.addWidget(self.listening_event_value)
        grid = QGridLayout()
        self.demod_combo = QComboBox()
        self.demod_combo.addItem("AM", "am")
        self.demod_combo.addItem(TEXT["nfm"], "nfm")
        self.listen_offset_spin = QDoubleSpinBox()
        self.listen_offset_spin.setRange(-100_000.0, 100_000.0)
        self.listen_offset_spin.setDecimals(3)
        self.listen_offset_spin.setSuffix(" kHz")
        self.listen_bandwidth_spin = QDoubleSpinBox()
        self.listen_bandwidth_spin.setRange(2.0, 200.0)
        self.listen_bandwidth_spin.setDecimals(1)
        self.listen_bandwidth_spin.setValue(16.0)
        self.listen_bandwidth_spin.setSuffix(" kHz")
        self.listen_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.listen_volume_slider.setRange(0, 100)
        self.listen_volume_slider.setValue(80)
        for row, (caption, widget) in enumerate(
            (
                (TEXT["demodulation"], self.demod_combo),
                (TEXT["listening_offset"], self.listen_offset_spin),
                (TEXT["listening_bandwidth"], self.listen_bandwidth_spin),
                (TEXT["volume"], self.listen_volume_slider),
            )
        ):
            label = QLabel(caption)
            label.setWordWrap(True)
            grid.addWidget(label, row, 0)
            grid.addWidget(widget, row, 1)
        layout.addLayout(grid)
        self.listening_state = QLabel(TEXT["listening_not_prepared"])
        self.listening_state.setObjectName("listeningState")
        self.listening_state.setWordWrap(True)
        layout.addWidget(self.listening_state)
        self.audio_backend_state = QLabel(TEXT["audio_backend_pending"])
        self.audio_backend_state.setWordWrap(True)
        layout.addWidget(self.audio_backend_state)
        self.fixture_live_warning = QLabel()
        self.fixture_live_warning.setObjectName("fixtureLiveWarning")
        self.fixture_live_warning.setWordWrap(True)
        self.fixture_live_warning.hide()
        layout.addWidget(self.fixture_live_warning)
        self.prepare_listening_button = QPushButton(TEXT["prepare_listening"])
        self.prepare_listening_button.setObjectName("primaryButton")
        self.play_audio_button = QPushButton(TEXT["play_audio"])
        self.pause_audio_button = QPushButton(TEXT["pause_audio"])
        self.stop_audio_button = QPushButton(TEXT["stop_audio"])
        self.export_wav_button = QPushButton(TEXT["export_wav"])
        buttons = QGridLayout()
        buttons.addWidget(self.prepare_listening_button, 0, 0, 1, 2)
        buttons.addWidget(self.play_audio_button, 1, 0)
        buttons.addWidget(self.pause_audio_button, 1, 1)
        buttons.addWidget(self.stop_audio_button, 2, 0)
        buttons.addWidget(self.export_wav_button, 2, 1)
        layout.addLayout(buttons)
        layout.addStretch(1)
        scroll = self._scroll_panel(panel, "listeningScroll")
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.listening_spectrum)
        splitter.addWidget(scroll)
        splitter.setSizes([1000, 340])
        splitter.setStretchFactor(0, 1)
        splitter.setChildrenCollapsible(False)
        workspace = QWidget()
        outer = QVBoxLayout(workspace)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(splitter)
        self.clear_listening()
        return workspace

    def show_empty(self) -> None:
        self.source_value.setText(TEXT["no_source"])
        self.listening_source_value.setText(TEXT["no_source"])
        for value in self.metadata_values.values():
            value.setText("—")
        self.state_value.setText(TEXT["empty"])
        self.spectrum_view.clear_all()
        self.clear_detections()
        self.clear_parameters()
        self.clear_listening()
        self.set_source_controls_enabled(False)
        self.hide_notification()

    def set_acquisition_mode(self, mode: str) -> None:
        """Expose only controls belonging to the selected, honestly labelled source."""
        is_hackrf = mode == "hackrf"
        self.hackrf_panel.setVisible(is_hackrf)
        self.open_button.setVisible(not is_hackrf)
        self.open_button.setText(TEXT["open_test_source"] if mode == "deterministic_test" else TEXT["open_sigmf"])
        if is_hackrf:
            self.set_hackrf_state("acceptance_pending")

    def set_hackrf_state(self, state: str) -> None:
        mapping = {
            "acceptance_pending": TEXT["hardware_acceptance_pending"],
            "tools_missing": TEXT["hackrf_tools_missing"] + " · " + TEXT["live_rx_unavailable"],
            "searching": TEXT["device_searching"],
            "device_missing": TEXT["hackrf_device_missing"] + " · " + TEXT["live_rx_unavailable"],
            "device_ready": TEXT["device_ready"],
            "capture_starting": TEXT["capture_starting"],
            "live": TEXT["live_capture"],
            "stopped": TEXT["capture_stopped"],
            "disconnected": TEXT["device_disconnected"],
            "timeout": TEXT["operation_timeout"],
            "test_source": TEXT["deterministic_source_active"],
            "cli_error": TEXT["hackrf_cli_error"],
        }
        self.hackrf_status.setText(mapping[state])
        ready = state in {"device_ready", "stopped"}
        busy = state in {"searching", "capture_starting", "live"}
        self.hackrf_refresh_button.setEnabled(not busy)
        self.hackrf_start_button.setEnabled(ready)
        self.hackrf_stop_button.setEnabled(busy)
        for widget in (
            self.hackrf_center_spin,
            self.hackrf_sample_combo,
            self.hackrf_lna_spin,
            self.hackrf_vga_spin,
            self.hackrf_amp_checkbox,
        ):
            widget.setEnabled(ready)

    @property
    def source_kind(self) -> str:
        return str(self.source_type_combo.currentData())

    @property
    def hackrf_settings(self) -> dict[str, int | bool]:
        return {
            "center_frequency_hz": round(self.hackrf_center_spin.value() * 1_000_000),
            "sample_rate_hz": int(self.hackrf_sample_combo.currentData()),
            "sample_count": 16_384,
            "rf_amplifier": self.hackrf_amp_checkbox.isChecked(),
            "lna_gain_db": self.hackrf_lna_spin.value(),
            "vga_gain_db": self.hackrf_vga_spin.value(),
        }

    def show_opening(self) -> None:
        """Show a bounded busy state while retaining any valid source details."""
        self.state_value.setText(TEXT["opening_source"])
        self.set_source_controls_enabled(False)
        self.hide_notification()

    def finish_opening(self, *, source_available: bool) -> None:
        """Restore controls after a source-open result has been handled."""
        self.set_source_controls_enabled(source_available)
        self.state_value.setText(TEXT["ready"] if source_available else TEXT["empty"])

    def set_source(self, filename: str, report: ContractReport) -> None:
        self.source_value.setText(Path(filename).name)
        self.listening_source_value.setText(Path(filename).name)
        self.metadata_values["center_frequency"].setText(self._frequency(report.center_frequency))
        self.metadata_values["sample_rate"].setText(self._sample_rate(report.sample_rate))
        self.metadata_values["datatype"].setText(report.source_datatype or "—")
        self.metadata_values["frame_length"].setText(
            self.locale.toString(report.frame_length) + " karmaşık örnek"
        )
        self.metadata_values["channel"].setText(
            "1 (varsayılan)" if report.channel_count_source == "defaulted" else "1"
        )
        frame_count = report.full_frame_count or 0
        self.frame_spin.setMaximum(max(frame_count, 1))
        self.set_frame_position(0, frame_count)
        self.set_source_controls_enabled(frame_count > 0)
        self.state_value.setText(TEXT["ready"])

    def set_frame_position(self, zero_based_index: int, frame_count: int) -> None:
        blocker = QSignalBlocker(self.frame_spin)
        self.frame_spin.setValue(zero_based_index + 1)
        del blocker
        self.metadata_values["frame_position"].setText(
            f"{self.locale.toString(zero_based_index + 1)} / {self.locale.toString(frame_count)}"
        )

    def set_state(self, state: str) -> None:
        self.state_value.setText(TEXT[state])

    def set_profile_summary(self, summary: str, *, validated: bool) -> None:
        suffix = TEXT["validated_envelope"] if validated else TEXT["parameter_error"]
        self.profile_value.setText(f"{summary}\n{suffix}")
        self.profile_value.setToolTip(f"{summary}\n{suffix}")

    def clear_detections(self) -> None:
        self.detection_state.setText(TEXT["no_detection"])
        self.detection_list.clear()
        self.detection_note.setText(TEXT["detection_detail"])

    def clear_parameters(self) -> None:
        self.measurement_state.setText(TEXT["measurement_not_started"])
        self.parameter_state.setText(TEXT["no_parameter"])
        for value in self.parameter_values.values():
            value.setText(TEXT["not_validated"])
        self.quality_value.setText(TEXT["quality_not_available"])

    def set_parameter_result(self, result: ParameterFrameResult | None) -> None:
        del result

    def set_detection_result(self, result: DetectionFrameResult) -> None:
        active = list(result.active_events)
        confirmed = [event for event in active if event.state == "confirmed"]
        tentative = [event for event in active if event.state == "tentative"]
        if confirmed or tentative:
            self.detection_state.setText(
                f"{len(confirmed)} {TEXT['confirmed'].casefold()} · "
                f"{len(tentative)} {TEXT['tentative'].casefold()}"
            )
        else:
            self.detection_state.setText(TEXT["no_detection"])

        ended = list(reversed(result.ended_history))
        ordered = sorted(confirmed, key=self._event_sort_key) + sorted(
            tentative, key=self._event_sort_key
        ) + ended
        visible = ordered[:12]
        self.detection_list.clear()
        for event in visible:
            item = QListWidgetItem(self._event_text(event))
            item.setToolTip(self._event_tooltip(event))
            item.setData(Qt.ItemDataRole.UserRole, event.event_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, event.state)
            if event.state != "confirmed" or not event.observed_this_frame:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, self._event_tooltip(event))
            self.detection_list.addItem(item)
        notes: list[str] = [TEXT["detection_detail"]]
        if result.dropped_candidates:
            notes.append(TEXT["candidate_limit"].format(count=result.dropped_candidates))
        if result.evicted_history_count:
            notes.append(TEXT["history_evicted"].format(count=result.evicted_history_count))
        hidden = max(0, len(ordered) - len(visible))
        if hidden:
            notes.append(TEXT["events_hidden"].format(count=hidden))
        self.detection_note.setText(" ".join(notes))

    def set_analysis_event(self, event: DetectionEvent | None) -> None:
        if event is None:
            self.analysis_event_value.setText(TEXT["select_confirmed_event"])
            self.measure_button.setEnabled(False)
            return
        self.analysis_event_value.setText(self._event_text(event))
        self.analysis_event_value.setToolTip(self._event_tooltip(event))
        self.measure_button.setEnabled(event.state == "confirmed" and event.observed_this_frame)

    def set_analysis_span(self, lower: int, upper: int, provenance: str) -> None:
        label = TEXT[provenance]
        self.span_value.setText(f"{lower}–{upper} bin · {label}")
        self.clear_measurement_result()

    def clear_analysis(self) -> None:
        self.set_analysis_event(None)
        self.span_value.setText(TEXT["no_analysis_span"])
        self.analysis_spectrum.clear_span()
        self.clear_measurement_result()

    def set_listening_event(self, event: DetectionEvent | None, *, offset_hz: float | None = None) -> None:
        if event is None or event.state != "confirmed" or not event.observed_this_frame:
            self.listening_event_value.setText(TEXT["listening_select_event"])
            self.prepare_listening_button.setEnabled(False)
            return
        self.listening_event_value.setText(self._event_tooltip(event))
        self.listening_event_value.setToolTip(self._event_tooltip(event))
        if offset_hz is not None:
            with QSignalBlocker(self.listen_offset_spin):
                self.listen_offset_spin.setValue(offset_hz / 1000.0)
        self.prepare_listening_button.setEnabled(True)

    def clear_listening(self) -> None:
        self.listening_event_value.setText(TEXT["listening_select_event"])
        self.listening_state.setText(TEXT["listening_not_prepared"])
        self.prepare_listening_button.setEnabled(False)
        self.play_audio_button.setEnabled(False)
        self.pause_audio_button.setEnabled(False)
        self.stop_audio_button.setEnabled(False)
        self.export_wav_button.setEnabled(False)
        if hasattr(self, "listening_spectrum"):
            self.listening_spectrum.clear_span()

    def set_listening_busy(self) -> None:
        self.listening_state.setText(TEXT["listening_preparing"])
        for button in (
            self.prepare_listening_button,
            self.play_audio_button,
            self.pause_audio_button,
            self.stop_audio_button,
            self.export_wav_button,
        ):
            button.setEnabled(False)

    def set_listening_result(self, result: object, *, audio_available: bool) -> None:
        tone = float(getattr(result, "dominant_tone_hz"))
        self.listening_state.setText(
            TEXT["listening_ready"].format(tone_hz=self.locale.toString(tone, "f", 1))
        )
        self.prepare_listening_button.setEnabled(True)
        self.play_audio_button.setEnabled(audio_available)
        self.pause_audio_button.setEnabled(audio_available)
        self.stop_audio_button.setEnabled(audio_available)
        self.export_wav_button.setEnabled(True)

    def set_audio_availability(self, available: bool) -> None:
        self.audio_backend_state.setText(
            TEXT["audio_backend_ready"] if available else TEXT["audio_backend_unavailable"]
        )

    def set_fixture_source(self, active: bool) -> None:
        self.fixture_live_warning.setVisible(active)
        self.fixture_live_warning.setText(TEXT["fixture_not_live"] if active else "")

    def clear_measurement_result(self) -> None:
        self.clear_parameters()

    def set_measurement_busy(self) -> None:
        self.measurement_state.setText(TEXT["measurement_running"])
        self.measure_button.setEnabled(False)

    def set_operator_measurement(self, result: object, validated_fields: tuple[str, ...]) -> None:
        from reference.parameters import OperatorAssistedParameterResult
        if not isinstance(result, OperatorAssistedParameterResult):
            self.clear_measurement_result()
            return
        self.measurement_state.setText(TEXT["measurement_complete"] if result.quality.state == "valid" else TEXT["measurement_failed"])
        mapping = {
            "emission_center": ("emission_center_frequency", result.emission_center_frequency),
            "carrier_line": ("carrier_line_frequency", result.carrier_line_frequency),
            "lower_edge": ("occupied_bandwidth", result.lower_band_edge),
            "upper_edge": ("occupied_bandwidth", result.upper_band_edge),
            "bandwidth": ("occupied_bandwidth", result.occupied_bandwidth),
            "peak_power": ("uncalibrated_power_dbfs", result.peak_power_dbfs_per_bin),
            "channel_power": ("uncalibrated_power_dbfs", result.channel_power_dbfs),
            "domain": ("signal_domain", result.signal_domain),
        }
        for key, (capability, field) in mapping.items():
            if capability not in validated_fields:
                self.parameter_values[key].setText(TEXT["not_validated"])
            elif field.state != "valid" or field.value is None:
                self.parameter_values[key].setText(TEXT.get(field.state, TEXT["measurement_failed"]))
            elif field.unit == "Hz":
                self.parameter_values[key].setText(self._frequency(float(field.value)) if key not in {"bandwidth"} else self.locale.toString(float(field.value) / 1000.0, "f", 2) + " kHz")
            elif isinstance(field.value, float):
                self.parameter_values[key].setText(self.locale.toString(field.value, "f", 2) + (f" {field.unit}" if field.unit else ""))
            else:
                self.parameter_values[key].setText(str(field.value))
        reasons = ", ".join(TEXT.get(reason, reason) for reason in result.quality.reasons) if result.quality.reasons else TEXT["quality_passed"]
        self.quality_value.setText(reasons)

    def set_p0_parameter_result(self, result: P0ParameterResult | None) -> None:
        """Bind only immutable P0 result fields; no placeholder is presented as a result."""
        if result is None:
            for key in ("p0_detection", "p0_carrier", "p0_bandwidth", "p0_power", "p0_snr", "p0_domain", "p0_region", "p0_backend", "p0_source"):
                self.parameter_values[key].setText(TEXT["not_validated"])
            return
        locale = self.locale
        self.parameter_values["p0_detection"].setText("Doğrulanmış" if result.confirmed else "Doğrulanmamış")
        self.parameter_values["p0_carrier"].setText(self._frequency(result.carrier_frequency_hz))
        self.parameter_values["p0_bandwidth"].setText(locale.toString(result.bandwidth_hz / 1000.0, "f", 3) + " kHz")
        self.parameter_values["p0_power"].setText(locale.toString(result.relative_power_dbfs, "f", 2) + " dBFS · " + result.calibration_state)
        self.parameter_values["p0_snr"].setText(locale.toString(result.snr_db, "f", 2) + " dB")
        self.parameter_values["p0_domain"].setText(result.signal_domain)
        self.parameter_values["p0_region"].setText(f"{result.candidate.start_bin}–{result.candidate.end_bin} · peak {result.candidate.peak_bin}")
        self.parameter_values["p0_backend"].setText(result.backend)
        self.parameter_values["p0_source"].setText(result.provenance)
        self.quality_value.setText(" · ".join(result.classification_reasons))

    def set_p0_detection_summary(self, result: P0ParameterResult) -> None:
        self.detection_list.clear()
        state = "Doğrulanmış" if result.confirmed else "Doğrulanmamış"
        item = QListWidgetItem(
            f"P0 · {state} · {self._frequency(result.carrier_frequency_hz)} · SNR {self.locale.toString(result.snr_db, 'f', 1)} dB"
        )
        item.setToolTip(
            f"OS-CFAR bölgesi {result.candidate.start_bin}–{result.candidate.end_bin}; "
            f"peak {result.candidate.peak_bin}; kaynak {result.provenance}; backend {result.backend}"
        )
        self.detection_list.addItem(item)
        self.detection_state.setText(f"1 {state.casefold()} · P0 OS-CFAR")
        self.detection_note.setText("Yetkili P0 kararı: PS hedefli OS-CFAR · Bu demo HOST REFERENCE sonucudur.")

    def _add_df_measurement(self) -> None:
        measurement = DFMeasurement.create(
            angle_deg=self.df_angle_spin.value(),
            relative_power_db=self.df_power_spin.value(),
            frequency_hz=self.df_frequency_spin.value() * 1_000_000.0,
            confidence=self.df_confidence_spin.value(),
        )
        self.df_model.add(measurement)
        self.df_points_list.addItem(f"{measurement.angle_deg:.1f}° · {measurement.relative_power_db:.2f} dBFS · güven {measurement.confidence:.2f}")
        points = self.df_model.measurements
        self.df_curve.setData([item.angle_deg for item in points], [item.relative_power_db for item in points])
        estimate = self.df_model.estimate()
        self.df_result_label.setText(
            f"{estimate.status} · Ham maksimum/LOB: {estimate.raw_maximum_angle_deg:.1f}° · "
            f"Güven: {estimate.confidence:.2f} · {estimate.measurement_count} ölçüm"
        )

    def _clear_df_measurements(self) -> None:
        self.df_model.clear()
        self.df_points_list.clear()
        self.df_curve.setData([], [])
        self.df_result_label.setText("LOB için en az üç farklı açı ölçün.")

    def _selected_et_mode(self) -> SafetyMode:
        mode = self.et_mode_combo.currentData()
        return mode if isinstance(mode, SafetyMode) else SafetyMode(str(mode))

    def _start_jamming_preview(self) -> None:
        duration = self.et_duration_spin.value()
        family = str(self.et_family_combo.currentData())
        offsets = {"single": (4_000.0,), "multiple": (-8_000.0, 0.0, 8_000.0), "barrage": (0.0,)}[family]
        try:
            self.et_mission.set_mode(self._selected_et_mode())
            self.et_mission.start(duration_seconds=duration, detail=f"continuous/{family}")
            preview_duration = min(duration, 0.1)
            result = self.jamming_engine.generate(ContinuousJammingConfig(family, 48_000, preview_duration, offsets))
            self._plot_et_preview(result.samples, result.sample_rate_hz)
            self.et_state_label.setText(f"{self.et_mission.state} · {family} · OFFLINE taban bant önizlemesi · RF TX yok")
        except (ValueError, RuntimeError, PermissionError) as exc:
            self.et_state_label.setText(f"GÜVENLİK KİLİDİ · {exc}")

    def _start_deception_preview(self) -> None:
        duration = self.et_duration_spin.value()
        audio_rate = 48_000
        preview_duration = min(duration, 0.25)
        time = np.arange(round(audio_rate * preview_duration), dtype=np.float64) / audio_rate
        if self.et_audio_scenario.currentIndex() == 0:
            audio = np.sin(2.0 * np.pi * 1_000.0 * time)
        else:
            audio = 0.65 * np.sin(2.0 * np.pi * 700.0 * time) + 0.35 * np.sin(2.0 * np.pi * 1_900.0 * time)
        try:
            self.et_mission.set_mode(self._selected_et_mode())
            self.et_mission.start(duration_seconds=duration, detail=f"analog/{self.et_deception_mode.currentText()}")
            result = self.deception_engine.generate(
                audio,
                AnalogDeceptionConfig(
                    mode=self.et_deception_mode.currentText(),
                    duration_seconds=preview_duration,
                    output_peak=self.et_audio_level.value(),
                ),
            )
            self._plot_et_preview(result.samples, result.sample_rate_hz)
            self.et_state_label.setText(
                f"{self.et_mission.state} · {result.mode} analog aldatma · loopback korelasyonu {result.loopback_correlation:.4f} · RF TX yok"
            )
        except (ValueError, RuntimeError, PermissionError) as exc:
            self.et_state_label.setText(f"GÜVENLİK KİLİDİ · {exc}")

    def _plot_et_preview(self, samples: np.ndarray, sample_rate_hz: float) -> None:
        visible = np.asarray(samples[: min(samples.size, 2048)])
        self.et_waveform_curve.setData(np.arange(visible.size) / sample_rate_hz * 1000.0, visible.real)
        fft_size = min(4096, samples.size)
        spectrum = np.abs(np.fft.fftshift(np.fft.fft(samples[:fft_size]))) ** 2
        frequencies = np.fft.fftshift(np.fft.fftfreq(fft_size, d=1.0 / sample_rate_hz)) / 1000.0
        spectrum_db = 10.0 * np.log10(np.maximum(spectrum / max(float(np.max(spectrum)), 1e-30), 1e-12))
        self.et_spectrum_curve.setData(frequencies, spectrum_db)

    def _stop_et_mission(self) -> None:
        self.et_mission.stop()
        self.et_state_label.setText("DURDURULDU · RF TX yok")

    def _emergency_stop_et(self) -> None:
        self.et_mission.emergency_stop()
        self.et_state_label.setText("ACİL DURDURMA · Fail-closed kilit etkin")

    def _event_text(self, event: DetectionEvent) -> str:
        label = TEXT[event.state]
        peak_mhz = self.locale.toString(event.region.peak_frequency_hz / 1_000_000.0, "f", 4)
        delta = self.locale.toString(event.region.peak_to_noise_db, "f", 1)
        return f"#{event.event_id} · {label} · {peak_mhz} MHz · +{delta} dB"

    def _event_tooltip(self, event: DetectionEvent) -> str:
        start = self.locale.toString(event.region.start_frequency_hz / 1_000_000.0, "f", 4)
        end = self.locale.toString(event.region.end_frequency_hz / 1_000_000.0, "f", 4)
        return (
            f"Kaba bölge: {start}–{end} MHz\n"
            f"İlk/son çerçeve: {event.first_frame + 1}/{event.last_seen_frame + 1}\n"
            f"Görülme sayısı: {event.seen_count}"
        )

    @staticmethod
    def _event_sort_key(event: DetectionEvent) -> tuple[float, int]:
        return (-event.region.peak_to_noise_db, event.event_id)

    def show_warning(self, message: str) -> None:
        self._show_notification(message, "warning")

    def show_error(self, message: str) -> None:
        self._show_notification(message, "error")

    def _show_notification(self, message: str, kind: str) -> None:
        self.notification.setProperty("kind", kind)
        self.notification.setText(message)
        self.notification.style().unpolish(self.notification)
        self.notification.style().polish(self.notification)
        self.notification.show()

    def hide_notification(self) -> None:
        self.notification.hide()
        self.notification.setText("")

    def set_source_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self.start_button,
            self.pause_button,
            self.stop_button,
            self.frame_spin,
            self.speed_spin,
            self.axis_combo,
            self.metric_combo,
            self.dc_checkbox,
            self.average_checkbox,
            self.detection_layer_checkbox,
            self.pfa_combo,
            self.center_checkbox,
        ):
            widget.setEnabled(enabled)

    @property
    def axis_mode(self) -> str:
        return "offset" if self.axis_combo.currentIndex() == 0 else "absolute"

    @property
    def metric(self) -> str:
        return "bin" if self.metric_combo.currentIndex() == 0 else "psd"

    @property
    def pfa(self) -> float:
        return float(self.pfa_combo.currentData())

    def _frequency(self, value: int | float | None) -> str:
        if value is None:
            return "—"
        return self.locale.toString(float(value) / 1_000_000.0, "f", 3) + " MHz"

    def _sample_rate(self, value: int | float | None) -> str:
        if value is None:
            return "—"
        return self.locale.toString(float(value) / 1_000_000.0, "f", 3) + " MS/s"

    def keyPressEvent(self, event: object) -> None:
        key = event.key()  # type: ignore[attr-defined]
        if self.workspace_tabs.currentIndex() == 1 and key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            step = 4 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1  # type: ignore[attr-defined]
            self.analysis_spectrum.nudge(-step if key == Qt.Key.Key_Left else step)
            event.accept()  # type: ignore[attr-defined]
            return
        super().keyPressEvent(event)  # type: ignore[arg-type]
