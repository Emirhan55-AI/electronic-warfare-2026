"""ET laboratuvar çalışma alanı mixin'i."""

from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import QSignalBlocker, QTimer, Qt
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSplitter, QStackedWidget, QToolButton, QVBoxLayout, QWidget)
import numpy as np
import pyqtgraph as pg

if TYPE_CHECKING:
    from algorithms.et import (AnalogDeceptionConfig, AnalogDeceptionEngine, ContinuousJammingConfig, ContinuousJammingEngine, ETTaskResult, ETMissionController, GNSSScenario, GNSSScenarioValidator, InterleavedConfig, InterleavedTaskController, SafetyMode, new_task_result)


def load_laboratory_et_dependencies() -> None:
    """Load validation-only ET models for the explicit laboratory UI."""

    global AnalogDeceptionConfig, AnalogDeceptionEngine, ContinuousJammingConfig
    global ContinuousJammingEngine, ETTaskResult, ETMissionController, GNSSScenario
    global GNSSScenarioValidator, InterleavedConfig, InterleavedTaskController
    global SafetyMode, new_task_result
    from algorithms.et import (
        AnalogDeceptionConfig,
        AnalogDeceptionEngine,
        ContinuousJammingConfig,
        ContinuousJammingEngine,
        ETTaskResult,
        ETMissionController,
        GNSSScenario,
        GNSSScenarioValidator,
        InterleavedConfig,
        InterleavedTaskController,
        SafetyMode,
        new_task_result,
    )


class ETWorkspaceMixin:
    def _build_et_workspace(self) -> QWidget:
        load_laboratory_et_dependencies()
        self.et_mission = ETMissionController()
        self.jamming_engine = ContinuousJammingEngine()
        self.deception_engine = AnalogDeceptionEngine()
        self.interleaved_engine = InterleavedTaskController()
        self.gnss_validator = GNSSScenarioValidator()
        self.last_et_result: ETTaskResult | None = None
        self._et_pipeline_blocks: dict[str, list[QLabel]] = {}
        self._et_animation: dict[str, object] | None = None
        self.et_animation_timer = QTimer(self)
        self.et_animation_timer.setInterval(40)
        self.et_animation_timer.timeout.connect(self._advance_et_animation)
        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header = QFrame()
        header.setObjectName("etStatusHeader")
        header_layout = QGridLayout(header)
        header_layout.setContentsMargins(12, 7, 12, 7)
        header_layout.setHorizontalSpacing(14)
        self.et_header_values: dict[str, QLabel] = {}
        for column, (key, title, value) in enumerate(
            (
                ("mode", "MOD", "OFFLINE"),
                ("task", "GÖREV", "Sürekli"),
                ("status", "DURUM", "HAZIR"),
                ("source", "KAYNAK", "Simülasyon"),
                ("tx_lock", "TX", "TX KİLİTLİ"),
                ("rf_tx", "RF", "RF TX YOK"),
            )
        ):
            caption = QLabel(title)
            caption.setProperty("class", "propCaption")
            caption.setWordWrap(True)
            value_label = QLabel(value)
            value_label.setProperty("class", "propValue")
            value_label.setWordWrap(True)
            header_layout.addWidget(caption, 0, column)
            header_layout.addWidget(value_label, 1, column)
            self.et_header_values[key] = value_label
        layout.addWidget(header)

        cards = QFrame()
        cards_layout = QGridLayout(cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setHorizontalSpacing(8)
        cards_layout.setVerticalSpacing(8)
        self.et_task_card_buttons: dict[str, QPushButton] = {}
        task_cards = (
            ("continuous", "Sürekli Karıştırma", "Tekli · Çoklu · Baraj"),
            ("interleaved", "Arabakışlı Karıştırma", "Dinle · Karar · Görev"),
            ("analog", "Analog Aldatma", "Test sesi · NFM"),
            ("gnss", "GPS L1 C/A", "Metadata doğrulama"),
        )
        for index, (key, title, detail) in enumerate(task_cards):
            card = QPushButton(f"{title}\n{detail}")
            card.setCheckable(True)
            card.setMinimumHeight(45)
            card.setToolTip(title)
            card.clicked.connect(lambda _checked=False, task_key=key: self._select_et_task(task_key))
            cards_layout.addWidget(card, index // 2, index % 2)
            self.et_task_card_buttons[key] = card
        layout.addWidget(cards)

        body = QSplitter(Qt.Orientation.Horizontal)
        body.setObjectName("etTaskBody")
        self.et_visual_stack = QStackedWidget()
        self.et_visual_stack.addWidget(self._build_et_continuous_visual())
        self.et_visual_stack.addWidget(self._build_et_interleaved_visual())
        self.et_visual_stack.addWidget(self._build_et_analog_visual())
        self.et_visual_stack.addWidget(self._build_et_gnss_visual())
        body.addWidget(self.et_visual_stack)
        body.addWidget(self._build_et_right_panel())
        body.setSizes([1050, 350])
        body.setStretchFactor(0, 3)
        body.setStretchFactor(1, 1)
        body.setChildrenCollapsible(False)
        layout.addWidget(body, 1)

        self.et_task_index = {"continuous": 0, "interleaved": 1, "analog": 2, "gnss": 3}
        self.et_task_card_buttons["continuous"].setChecked(True)
        self._select_et_task("continuous")
        return workspace

    def _build_et_pipeline(self, task_key: str, blocks: tuple[str, ...]) -> QFrame:
        flow = QFrame()
        flow_layout = QHBoxLayout(flow)
        flow_layout.setContentsMargins(4, 2, 4, 2)
        flow_layout.setSpacing(4)
        task_blocks: list[QLabel] = []
        for index, title in enumerate(blocks):
            block = QLabel(title)
            block.setProperty("class", "propCaption")
            block.setWordWrap(True)
            block.setAlignment(Qt.AlignmentFlag.AlignCenter)
            flow_layout.addWidget(block, 1)
            task_blocks.append(block)
            if index < len(blocks) - 1:
                arrow = QLabel("›")
                arrow.setProperty("class", "propCaption")
                arrow.setWordWrap(True)
                flow_layout.addWidget(arrow)
        self._et_pipeline_blocks[task_key] = task_blocks
        return flow

    def _build_et_continuous_visual(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._build_et_pipeline("continuous", ("Görev", "Üreteç", "Filtre", "Normalize", "Önizleme")))
        plots = QSplitter(Qt.Orientation.Horizontal)
        self.et_waveform_plot = pg.PlotWidget()
        self.et_waveform_plot.setTitle("Zaman Alanı", color="#E2EEF8", size="10.5pt")
        self.et_waveform_plot.setLabel("bottom", "Zaman", units="ms")
        self.et_waveform_plot.setLabel("left", "Genlik")
        self.et_waveform_curve = self.et_waveform_plot.plot(pen=pg.mkPen("#38BDF8", width=1.5))
        self.et_waveform_cursor = self.et_waveform_plot.plot(
            pen=None, symbol="o", symbolSize=8, symbolBrush="#F59E0B", symbolPen="#F59E0B"
        )
        self.et_spectrum_plot = pg.PlotWidget()
        self.et_spectrum_plot.setTitle("Spektrum", color="#E2EEF8", size="10.5pt")
        self.et_spectrum_plot.setLabel("bottom", "Ofset", units="kHz")
        self.et_spectrum_plot.setLabel("left", "Güç", units="dB")
        self.et_spectrum_curve = self.et_spectrum_plot.plot(pen=pg.mkPen("#F59E0B", width=1.5))
        plots.addWidget(self.et_waveform_plot)
        plots.addWidget(self.et_spectrum_plot)
        plots.setSizes([520, 520])
        layout.addWidget(plots, 1)
        self.et_continuous_visual_result = QLabel("Örnek akışı başlatıldığında burada gösterilir.")
        self.et_continuous_visual_result.setProperty("class", "propCaption")
        self.et_continuous_visual_result.setWordWrap(True)
        layout.addWidget(self.et_continuous_visual_result)
        self.et_sweep_plot = pg.PlotWidget()
        self.et_sweep_plot.setTitle("Süpürme Görünümü", color="#E2EEF8", size="10.5pt")
        self.et_sweep_plot.setLabel("bottom", "Zaman")
        self.et_sweep_plot.setLabel("left", "Ofset", units="kHz")
        self.et_sweep_image = pg.ImageItem()
        self.et_sweep_plot.addItem(self.et_sweep_image)
        self.et_sweep_plot.hide()
        layout.addWidget(self.et_sweep_plot, 1)
        return panel

    def _build_et_interleaved_visual(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._build_et_pipeline("interleaved", ("Dinle", "Güç Ölç", "Karar", "Gecikme", "Görev", "Koruma")))
        self.et_interleaved_values: dict[str, QLabel] = {}
        status_grid = QGridLayout()
        for row, (key, caption) in enumerate((
            ("state", "DURUM"),
            ("energy", "GÜÇ"),
            ("threshold", "EŞİK"),
            ("decision", "KARAR"),
            ("duration", "SÜRE"),
        )):
            l = QLabel(caption)
            l.setProperty("class", "propCaption")
            l.setWordWrap(True)
            status_grid.addWidget(l, row, 0)
            value = QLabel("—")
            value.setProperty("class", "propValue")
            value.setWordWrap(True)
            status_grid.addWidget(value, row, 1)
            self.et_interleaved_values[key] = value
        layout.addLayout(status_grid)
        plots = QSplitter(Qt.Orientation.Horizontal)
        self.et_interleaved_timeline_plot = pg.PlotWidget()
        self.et_interleaved_timeline_plot.setTitle("Bant Gücü", color="#E2EEF8", size="10.5pt")
        self.et_interleaved_timeline_plot.setLabel("bottom", "Pencere")
        self.et_interleaved_timeline_plot.setLabel("left", "Güç")
        self.et_interleaved_timeline_plot.showGrid(x=True, y=True, alpha=0.15)
        self.et_interleaved_timeline_curve = self.et_interleaved_timeline_plot.plot(pen=pg.mkPen("#38BDF8", width=2), symbol="o", symbolSize=5)
        self.et_interleaved_threshold_curve = self.et_interleaved_timeline_plot.plot(
            pen=pg.mkPen("#F59E0B", width=1.4, style=Qt.PenStyle.DashLine)
        )
        self.et_interleaved_task_marker = self.et_interleaved_timeline_plot.plot(
            pen=None, symbol="o", symbolSize=12, symbolBrush="#10B981", symbolPen="#10B981"
        )
        self.et_interleaved_spectrum_plot = pg.PlotWidget()
        self.et_interleaved_spectrum_plot.setTitle("Offline Görev Spektrumu", color="#E2EEF8", size="10.5pt")
        self.et_interleaved_spectrum_plot.setLabel("bottom", "Ofset", units="kHz")
        self.et_interleaved_spectrum_plot.setLabel("left", "Güç", units="dB")
        self.et_interleaved_spectrum_curve = self.et_interleaved_spectrum_plot.plot(pen=pg.mkPen("#F59E0B", width=1.5))
        plots.addWidget(self.et_interleaved_timeline_plot)
        plots.addWidget(self.et_interleaved_spectrum_plot)
        plots.setSizes([520, 520])
        layout.addWidget(plots, 1)
        self.et_interleaved_summary = QLabel("Durum geçişleri başlatıldığında gösterilir.")
        self.et_interleaved_summary.setProperty("class", "propCaption")
        self.et_interleaved_summary.setWordWrap(True)
        layout.addWidget(self.et_interleaved_summary)
        return panel

    def _build_et_analog_visual(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._build_et_pipeline("analog", ("Ses", "Normalize", "Modülasyon", "I/Q", "Demodülasyon")))
        self.et_analog_mode_badge = QLabel("OFFLINE · TX KİLİTLİ · RF TX YOK")
        self.et_analog_mode_badge.setProperty("class", "propCaption")
        self.et_analog_mode_badge.setWordWrap(True)
        layout.addWidget(self.et_analog_mode_badge)
        plots = QSplitter(Qt.Orientation.Horizontal)
        self.et_analog_audio_plot = pg.PlotWidget()
        self.et_analog_audio_plot.setTitle("Ses Dalga Şekli", color="#E2EEF8", size="10.5pt")
        self.et_analog_audio_plot.setLabel("bottom", "Örnek")
        self.et_analog_audio_plot.setLabel("left", "Seviye")
        self.et_analog_audio_curve = self.et_analog_audio_plot.plot(pen=pg.mkPen("#38BDF8", width=1.5))
        self.et_analog_spectrum_plot = pg.PlotWidget()
        self.et_analog_spectrum_plot.setTitle("Spektrum", color="#E2EEF8", size="10.5pt")
        self.et_analog_spectrum_plot.setLabel("bottom", "Ofset", units="kHz")
        self.et_analog_spectrum_plot.setLabel("left", "Güç", units="dB")
        self.et_analog_spectrum_curve = self.et_analog_spectrum_plot.plot(pen=pg.mkPen("#F59E0B", width=1.5))
        plots.addWidget(self.et_analog_audio_plot)
        plots.addWidget(self.et_analog_spectrum_plot)
        plots.setSizes([520, 520])
        layout.addWidget(plots, 1)
        self.et_analog_visual_result = QLabel("Ses işleme ve modülasyon sonuçları burada gösterilir.")
        self.et_analog_visual_result.setProperty("class", "propCaption")
        self.et_analog_visual_result.setWordWrap(True)
        layout.addWidget(self.et_analog_visual_result)
        return panel

    def _build_et_gnss_visual(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._build_et_pipeline("gnss", ("Girdi", "Doğrulama", "Sözleşme")))
        notice = QLabel("GPS L1 C/A için yalnız offline metadata doğrulanır. RF çıkışı üretilmez.")
        notice.setProperty("class", "propCaption")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self.et_gnss_visual_result = QLabel("Doğrulama bekleniyor.")
        self.et_gnss_visual_result.setProperty("class", "propValue")
        self.et_gnss_visual_result.setWordWrap(True)
        self.et_gnss_visual_result.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.et_gnss_visual_result)
        self.et_gnss_signal_status = QLabel("DURUM: Waveform yok · RF TX YOK")
        self.et_gnss_signal_status.setProperty("class", "propCaption")
        self.et_gnss_signal_status.setWordWrap(True)
        layout.addWidget(self.et_gnss_signal_status)
        self.et_gnss_visual_status = QLabel("Yalnız girilen konum ve zaman doğrulanır.")
        self.et_gnss_visual_status.setProperty("class", "propCaption")
        self.et_gnss_visual_status.setWordWrap(True)
        layout.addWidget(self.et_gnss_visual_status)
        return panel

    def _build_et_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(280)
        panel.setMaximumWidth(340)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)
        self.et_control_stack = QStackedWidget()
        self.et_control_stack.addWidget(self._build_et_continuous_controls())
        self.et_control_stack.addWidget(self._build_et_interleaved_controls())
        self.et_control_stack.addWidget(self._build_et_analog_controls())
        self.et_control_stack.addWidget(self._build_et_gnss_controls())
        layout.addWidget(self.et_control_stack, 1)

        result_card = QFrame()
        result_card.setObjectName("selectedSignalCard")
        result_layout = QGridLayout(result_card)
        result_layout.setContentsMargins(10, 8, 10, 8)
        self.et_result_values: dict[str, QLabel] = {}
        for row, (key, caption, value) in enumerate((
            ("status", "DURUM", "—"),
            ("mode", "MOD", "—"),
            ("metric", "SONUÇ", "—"),
            ("detail", "AYRINTI", "—"),
        )):
            label = QLabel(caption)
            label.setProperty("class", "propCaption")
            label.setWordWrap(True)
            value_label = QLabel(value)
            value_label.setProperty("class", "propValue")
            value_label.setWordWrap(True)
            result_layout.addWidget(label, row, 0)
            result_layout.addWidget(value_label, row, 1)
            self.et_result_values[key] = value_label
        layout.addWidget(result_card)

        safety = QFrame()
        safety.setObjectName("selectedSignalCard")
        safety_layout = QGridLayout(safety)
        safety_layout.setContentsMargins(10, 8, 10, 8)
        c_lbl = QLabel("Mod")
        c_lbl.setProperty("class", "propCaption")
        c_lbl.setWordWrap(True)
        safety_layout.addWidget(c_lbl, 0, 0)
        self.et_mode_combo = QComboBox()
        self.et_mode_combo.addItem("SİMÜLASYON", SafetyMode.OFFLINE)
        self.et_mode_combo.addItem("YEREL DÖNGÜ", SafetyMode.LOOPBACK)
        self.et_mode_combo.addItem("KAYIT YENİDEN OYNAT", SafetyMode.REPLAY)
        self.et_mode_combo.addItem("KABLOLU LAB · KİLİTLİ", SafetyMode.CABLED_LAB)
        self.et_mode_combo.addItem("DONANIM TX · KİLİTLİ", SafetyMode.HARDWARE_TX_LOCKED)
        self.et_mode_combo.currentIndexChanged.connect(self._update_et_mode_badge)
        self.et_mode_combo.hide()
        self.et_mode_summary = QLabel("OFFLINE · TX KİLİTLİ · RF TX YOK")
        self.et_mode_summary.setProperty("class", "propValue")
        self.et_mode_summary.setWordWrap(True)
        safety_layout.addWidget(self.et_mode_summary, 0, 1)
        self.et_emergency_stop = QPushButton("GÖREVİ DURDUR")
        self.et_emergency_stop.setObjectName("etEmergencyStop")
        self.et_emergency_stop.clicked.connect(self._stop_et_mission)
        safety_layout.addWidget(self.et_emergency_stop, 1, 0, 1, 2)
        self.et_state_label = QLabel("HAZIR")
        self.et_state_label.setProperty("class", "propValue")
        self.et_state_label.setWordWrap(True)
        safety_layout.addWidget(self.et_state_label, 2, 0, 1, 2)
        layout.addWidget(safety)

        self.et_log_toggle = QToolButton()
        self.et_log_toggle.setObjectName("collapseToggle")
        self.et_log_toggle.setText("Görev Günlüğü")
        self.et_log_toggle.setCheckable(True)
        self.et_log_toggle.toggled.connect(self._toggle_et_log)
        layout.addWidget(self.et_log_toggle)
        self.et_log_content = QLabel("Henüz kayıtlı olay yok.")
        self.et_log_content.setProperty("class", "propCaption")
        self.et_log_content.setWordWrap(True)
        self.et_log_content.hide()
        layout.addWidget(self.et_log_content)
        return panel

    @staticmethod
    def _et_control_panel(title: str) -> tuple[QFrame, QVBoxLayout, QGridLayout]:
        panel = QFrame()
        panel.setObjectName("selectedSignalCard")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 9, 10, 9)
        layout.setSpacing(7)
        heading = QLabel(title)
        heading.setObjectName("selectedSignalTitle")
        heading.setWordWrap(True)
        layout.addWidget(heading)
        form = QGridLayout()
        form.setHorizontalSpacing(7)
        form.setVerticalSpacing(5)
        layout.addLayout(form)
        return panel, layout, form

    def _build_et_continuous_controls(self) -> QWidget:
        panel, layout, form = self._et_control_panel("SÜREKLİ")
        self.et_family_combo = QComboBox()
        for label, value in (("Tekli", "single"), ("Çoklu", "multiple"), ("Baraj", "barrage")):
            self.et_family_combo.addItem(label, value)
        self.et_family_combo.currentIndexChanged.connect(self._update_continuous_hint)
        self.et_duration_spin = QDoubleSpinBox()
        self.et_duration_spin.setRange(0.1, 30.0)
        self.et_duration_spin.setValue(1.0)
        self.et_duration_spin.setSuffix(" s")
        self.et_continuous_level = QDoubleSpinBox()
        self.et_continuous_level.setRange(0.1, 0.9)
        self.et_continuous_level.setValue(0.7)
        self.et_continuous_level.setSingleStep(0.05)
        for row, (caption, widget) in enumerate((("Tip", self.et_family_combo), ("Süre", self.et_duration_spin), ("Seviye", self.et_continuous_level))):
            l = QLabel(caption)
            l.setProperty("class", "propCaption")
            l.setWordWrap(True)
            form.addWidget(l, row, 0)
            form.addWidget(widget, row, 1)
        self.et_continuous_hint = QLabel("Tek baskın bileşen")
        self.et_continuous_hint.setProperty("class", "propCaption")
        self.et_continuous_hint.setWordWrap(True)
        layout.addWidget(self.et_continuous_hint)
        self.et_jam_start = QPushButton("BAŞLAT")
        self.et_jam_start.setObjectName("primaryButton")
        self.et_jam_stop = QPushButton("Durdur")
        self.et_jam_start.clicked.connect(self._start_jamming_preview)
        self.et_jam_stop.clicked.connect(self._stop_et_mission)
        layout.addWidget(self.et_jam_start)
        layout.addWidget(self.et_jam_stop)
        layout.addStretch(1)
        return panel

    def _build_et_interleaved_controls(self) -> QWidget:
        panel, layout, form = self._et_control_panel("ARABAKIŞLI")
        self.et_interleaved_scenario = QComboBox()
        for label, value in (("Hedef yok", "absent"), ("Hedef sürekli", "present"), ("Kesintili hedef", "intermittent"), ("Eşik kenarı", "edge")):
            self.et_interleaved_scenario.addItem(label, value)
        self.et_interleaved_threshold = QLabel(
            "Eşik aç/kapat: 0,12 / 0,08 · Onay: 2 pencere\n"
            "Gecikme / görev / koruma: 1 / 1 / 1 pencere"
        )
        self.et_interleaved_threshold.setProperty("class", "propCaption")
        self.et_interleaved_threshold.setWordWrap(True)
        t_lbl = QLabel("Analiz girdisi")
        t_lbl.setProperty("class", "propCaption")
        t_lbl.setWordWrap(True)
        form.addWidget(t_lbl, 0, 0)
        form.addWidget(self.et_interleaved_scenario, 0, 1)
        layout.addWidget(self.et_interleaved_threshold)
        self.et_interleaved_run = QPushButton("BAŞLAT")
        self.et_interleaved_run.setObjectName("primaryButton")
        self.et_interleaved_run.clicked.connect(self._run_interleaved_test)
        layout.addWidget(self.et_interleaved_run)
        layout.addStretch(1)
        return panel

    def _build_et_analog_controls(self) -> QWidget:
        panel, layout, form = self._et_control_panel("ANALOG")
        self.et_deception_mode = QComboBox()
        self.et_deception_mode.addItems(["NFM", "FM", "AM"])
        self.et_audio_scenario = QComboBox()
        self.et_audio_scenario.addItem("1 kHz Test Sesi")
        self.et_analog_duration_spin = QDoubleSpinBox()
        self.et_analog_duration_spin.setRange(0.1, 30.0)
        self.et_analog_duration_spin.setValue(1.0)
        self.et_analog_duration_spin.setSuffix(" s")
        self.et_audio_level = QDoubleSpinBox()
        self.et_audio_level.setRange(0.1, 0.9)
        self.et_audio_level.setValue(0.7)
        for row, (caption, widget) in enumerate((("Senaryo", self.et_audio_scenario), ("Mod", self.et_deception_mode), ("Süre", self.et_analog_duration_spin), ("Seviye", self.et_audio_level))):
            l = QLabel(caption)
            l.setProperty("class", "propCaption")
            l.setWordWrap(True)
            form.addWidget(l, row, 0)
            form.addWidget(widget, row, 1)
        self.et_deception_start = QPushButton("BAŞLAT")
        self.et_deception_start.setObjectName("primaryButton")
        self.et_deception_stop = QPushButton("Durdur")
        self.et_deception_start.clicked.connect(self._start_deception_preview)
        self.et_deception_stop.clicked.connect(self._stop_et_mission)
        layout.addWidget(self.et_deception_start)
        layout.addWidget(self.et_deception_stop)
        layout.addStretch(1)
        return panel

    def _build_et_gnss_controls(self) -> QWidget:
        panel, layout, form = self._et_control_panel("GPS L1 C/A")
        self.et_gnss_service = QLabel("GPS L1 C/A")
        self.et_gnss_service.setWordWrap(True)
        self.et_gnss_latitude = QDoubleSpinBox()
        self.et_gnss_latitude.setRange(-90.0, 90.0)
        self.et_gnss_latitude.setDecimals(5)
        self.et_gnss_latitude.setValue(39.93340)
        self.et_gnss_longitude = QDoubleSpinBox()
        self.et_gnss_longitude.setRange(-180.0, 180.0)
        self.et_gnss_longitude.setDecimals(5)
        self.et_gnss_longitude.setValue(32.85970)
        self.et_gnss_time = QLineEdit("2026-08-16T12:00:00Z")
        self.et_gnss_satellites = QLineEdit("3, 8, 14")
        for row, (caption, widget) in enumerate((("Servis", self.et_gnss_service), ("Enlem", self.et_gnss_latitude), ("Boylam", self.et_gnss_longitude), ("UTC", self.et_gnss_time), ("PRN kodları", self.et_gnss_satellites))):
            l = QLabel(caption)
            l.setProperty("class", "propCaption")
            l.setWordWrap(True)
            form.addWidget(l, row, 0)
            form.addWidget(widget, row, 1)
        self.et_gnss_validate = QPushButton("DOĞRULA")
        self.et_gnss_validate.setObjectName("primaryButton")
        self.et_gnss_validate.clicked.connect(self._run_gnss_validation)
        layout.addWidget(self.et_gnss_validate)
        layout.addStretch(1)
        return panel

    def _selected_et_mode(self) -> SafetyMode:
        mode = self.et_mode_combo.currentData()
        return mode if isinstance(mode, SafetyMode) else SafetyMode(str(mode))

    def _select_et_task(self, task_key: str) -> None:
        if task_key not in self.et_task_index:
            raise ValueError(f"bilinmeyen ET görevi: {task_key}")
        if self._et_animation is not None:
            self._cancel_et_animation("Görev değiştirildi")
        names = {
            "continuous": "Sürekli Karıştırma",
            "interleaved": "Arabakışlı Karıştırma",
            "analog": "Analog Aldatma",
            "gnss": "GPS L1 C/A",
        }
        index = self.et_task_index[task_key]
        self.et_visual_stack.setCurrentIndex(index)
        self.et_control_stack.setCurrentIndex(index)
        for key, button in self.et_task_card_buttons.items():
            blocker = QSignalBlocker(button)
            button.setChecked(key == task_key)
            del blocker
        self.et_header_values["task"].setText(names[task_key])
        self.et_header_values["mode"].setText("OFFLINE")
        self.et_header_values["status"].setText("HAZIR")
        self.et_header_values["source"].setText("Simülasyon")
        self.et_result_values["status"].setText("—")
        self.et_result_values["mode"].setText("—")
        self.et_result_values["metric"].setText("Görev seçildi")
        self.et_result_values["detail"].setText("OFFLINE · TX KİLİTLİ")
        self.et_state_label.setText("HAZIR")
        self._set_et_pipeline_progress(task_key, -1)

    def _update_et_mode_badge(self) -> None:
        if not hasattr(self, "et_header_values"):
            return
        self.et_header_values["mode"].setText("OFFLINE")
        self.et_mode_summary.setText("OFFLINE · TX KİLİTLİ · RF TX YOK")

    def _update_continuous_hint(self) -> None:
        family = str(self.et_family_combo.currentData())
        hints = {
            "single": "Tek baskın bileşen",
            "multiple": "Hedefler: #1 · #2 · #3",
            "barrage": "Bant-sınırlı gürültü",
            "sweep": "Süpürme",
        }
        self.et_continuous_hint.setText(hints[family])

    def _set_et_pipeline_progress(self, task_key: str, stage: int) -> None:
        blocks = self._et_pipeline_blocks.get(task_key, ())
        for index, block in enumerate(blocks):
            state = "idle" if stage < 0 else "complete" if index < stage or stage >= len(blocks) else "active" if index == stage else "idle"
            if block.property("etStage") != state:
                block.setProperty("etStage", state)
                block.style().unpolish(block)
                block.style().polish(block)

    def _set_et_controls_busy(self, busy: bool) -> None:
        controls = (
            self.et_family_combo, self.et_duration_spin, self.et_continuous_level, self.et_jam_start,
            self.et_interleaved_scenario, self.et_interleaved_run,
            self.et_deception_mode, self.et_audio_scenario, self.et_analog_duration_spin,
            self.et_audio_level, self.et_deception_start, self.et_gnss_validate,
            self.et_mode_combo,
        )
        for control in controls:
            control.setEnabled(not busy)
        self.et_jam_stop.setEnabled(True)
        self.et_deception_stop.setEnabled(True)

    @staticmethod
    def _et_animation_window(samples: np.ndarray, *, size: int, progress: float) -> tuple[np.ndarray, int]:
        values = np.asarray(samples)
        width = min(size, values.size)
        end = min(values.size, max(width, int(round(progress * values.size))))
        start = max(0, end - width)
        return values[start:end], start

    def _start_et_animation(
        self,
        *,
        task_key: str,
        samples: np.ndarray,
        sample_rate_hz: float,
        task_result: ETTaskResult,
        metric: str,
        completion_detail: str,
        audio: np.ndarray | None = None,
        timeline: tuple[str, ...] = (),
        windows: tuple[object, ...] = (),
    ) -> None:
        if self._et_animation is not None:
            raise RuntimeError("önceki görev tamamlanmadan yeni görev başlatılamaz")
        self.last_et_result = task_result
        self._et_animation = {
            "task_key": task_key, "samples": np.asarray(samples), "sample_rate_hz": float(sample_rate_hz),
            "task_result": task_result, "metric": metric, "completion_detail": completion_detail,
            "audio": None if audio is None else np.asarray(audio), "timeline": timeline, "windows": windows,
            "step": 0, "total_steps": 37,
        }
        self._set_et_controls_busy(True)
        self.et_header_values["mode"].setText("OFFLINE")
        self.et_header_values["status"].setText("SONUÇ HAZIR · GÖRÜNTÜLENİYOR")
        self.et_header_values["source"].setText("Simülasyon")
        self.et_result_values["status"].setText("✓ PASS" if task_result.validation_status == "PASS" else "✕ FAIL")
        self.et_result_values["mode"].setText("OFFLINE")
        self.et_result_values["metric"].setText(metric)
        self.et_state_label.setText("SONUÇ GÖSTERİLİYOR")
        self._set_et_pipeline_progress(task_key, 0)
        self.et_animation_timer.start()
        self._advance_et_animation()

    def _advance_et_animation(self) -> None:
        animation = self._et_animation
        if animation is None:
            self.et_animation_timer.stop()
            return
        step = min(int(animation["step"]) + 1, int(animation["total_steps"]))
        animation["step"] = step
        progress = step / int(animation["total_steps"])
        task_key = str(animation["task_key"])
        samples = np.asarray(animation["samples"])
        sample_rate_hz = float(animation["sample_rate_hz"])
        task_result = animation["task_result"]
        assert isinstance(task_result, ETTaskResult)
        blocks = self._et_pipeline_blocks[task_key]
        self._set_et_pipeline_progress(task_key, min(int(progress * len(blocks)), len(blocks) - 1))
        percent = int(round(progress * 100.0))
        self.et_header_values["status"].setText(f"SONUÇ HAZIR · GÖRÜNTÜLENİYOR %{percent}")

        if task_key == "continuous":
            visible, start = self._et_animation_window(samples, size=384, progress=progress)
            self._plot_et_preview(visible, sample_rate_hz, start_sample=start, spectrum_samples=samples)
            if task_result.waveform_type == "sweep" and (step % 4 == 0 or progress >= 1.0):
                self._plot_sweep_waterfall(samples[: min(samples.size, max(512, int(round(progress * samples.size))))], sample_rate_hz, visible=True)
            status = f"{animation['metric']}"
            self.et_continuous_visual_result.setText(status)
        elif task_key == "analog":
            audio = animation["audio"]
            assert isinstance(audio, np.ndarray)
            audio_visible, audio_start = self._et_animation_window(audio, size=2048, progress=progress)
            self._plot_analog_preview(audio_visible, samples, sample_rate_hz, task_result.waveform_type, start_sample=audio_start)
            status = f"{animation['metric']}"
            self.et_analog_visual_result.setText(status)
        else:
            timeline = animation["timeline"]
            windows = animation["windows"]
            assert isinstance(timeline, tuple) and isinstance(windows, tuple)
            visible, _ = self._et_animation_window(samples, size=4096, progress=progress)
            window_count = min(len(windows), max(1, int(round(progress * len(windows)))))
            self._plot_interleaved_result(visible, sample_rate_hz, windows[:window_count])
            current = windows[window_count - 1]
            measured_value = getattr(current, "measured_band_power")
            decision = str(getattr(current, "decision"))
            state = str(getattr(current, "state"))
            self._set_et_pipeline_progress("interleaved", {"DİNLE": 0, "GECİKME": 3, "GÖREV": 4, "KORUMA": 5}.get(state, 0))
            self.et_interleaved_values["state"].setText(state)
            self.et_interleaved_values["energy"].setText("—" if measured_value is None else f"{float(measured_value):.4f}")
            self.et_interleaved_values["threshold"].setText("0,12 / 0,08")
            self.et_interleaved_values["decision"].setText(decision)
            self.et_interleaved_values["duration"].setText(f"{len(samples) / max(len(windows), 1) / sample_rate_hz * 1000.0:.1f} ms")
            self.et_interleaved_summary.setText(f"Pencere {window_count}/{len(windows)} · {decision}")
            status = f"{animation['metric']}"
        self.et_result_values["metric"].setText(status)
        if progress >= 1.0:
            animation["step"] = 0

    def _finish_et_animation(self) -> None:
        animation = self._et_animation
        if animation is None:
            return
        self.et_animation_timer.stop()
        self._et_animation = None
        task_result = animation["task_result"]
        assert isinstance(task_result, ETTaskResult)
        try:
            self.et_mission.complete(detail=str(animation["completion_detail"]))
            self._show_et_result(task_result, metric=str(animation["metric"]))
            self._set_et_pipeline_progress(str(animation["task_key"]), len(self._et_pipeline_blocks[str(animation["task_key"])]))
            if task_result.task_type == "continuous_jamming":
                self.et_continuous_visual_result.setText(
                    f"Tamamlandı · Bant: {float(task_result.details['occupied_bandwidth_hz']) / 1000.0:.2f} kHz"
                )
            elif task_result.task_type == "analog_deception":
                self.et_analog_visual_result.setText(
                    f"Tamamlandı · Uyum: {float(task_result.details['loopback_correlation']):.4f}"
                )
        except RuntimeError as exc:
            self._show_et_error(exc)
        finally:
            self._set_et_controls_busy(False)

    def _cancel_et_animation(self, _reason: str) -> None:
        self.et_animation_timer.stop()
        self._et_animation = None
        if self.et_mission.state == "ÇALIŞIYOR":
            self.et_mission.stop()
        self._set_et_controls_busy(False)

    def _toggle_et_log(self, visible: bool) -> None:
        self.et_log_content.setVisible(visible)

    def _refresh_et_log(self) -> None:
        if not self.et_mission.log:
            self.et_log_content.setText("Henüz kayıtlı olay yok.")
            return
        entries = self.et_mission.log[-8:]
        lines = []
        for entry in entries:
            timestamp = entry.timestamp_utc[11:19]
            detail = entry.detail if entry.detail else entry.state
            lines.append(f"{timestamp}  {entry.action:<10} {detail}")
        self.et_log_content.setText("\n".join(lines))

    def _begin_et_task(self, *, duration: float, detail: str) -> SafetyMode:
        mode = self._selected_et_mode()
        self.et_mission.set_mode(mode)
        self.et_mission.start(duration_seconds=duration, detail=detail)
        return mode

    def _show_et_result(self, result: ETTaskResult, *, metric: str) -> None:
        self.last_et_result = result
        self.et_header_values["mode"].setText("OFFLINE")
        self.et_header_values["status"].setText("TAMAMLANDI" if result.validation_status == "PASS" else "HATA")
        self.et_header_values["source"].setText(result.source)
        self.et_result_values["status"].setText("✓ PASS" if result.validation_status == "PASS" else "✕ FAIL")
        self.et_result_values["mode"].setText("OFFLINE")
        self.et_result_values["metric"].setText(metric)
        state = "TAMAMLANDI" if result.validation_status == "PASS" else "HATA"
        self.et_state_label.setText(state)
        self._refresh_et_log()

    def _show_et_error(self, exc: Exception) -> None:
        self._cancel_et_animation("Görev hatası")
        state = self.et_mission.state
        self.et_header_values["status"].setText("HATA")
        self.et_result_values["status"].setText("✕ FAIL")
        self.et_result_values["metric"].setText(str(exc))
        self.et_state_label.setText(f"{state} · {exc}")
        self._refresh_et_log()

    def _start_jamming_preview(self) -> None:
        self._run_continuous_task(preview=True)

    def _run_continuous_test(self) -> None:
        self._run_continuous_task(preview=False)

    def _run_continuous_task(self, *, preview: bool) -> None:
        duration = self.et_duration_spin.value()
        family = str(self.et_family_combo.currentData())
        offsets = {
            "single": (4_000.0,),
            "multiple": (-8_000.0, 0.0, 8_000.0),
            "barrage": (0.0,),
            "sweep": (0.0,),
        }[family]
        try:
            mode = self._begin_et_task(duration=duration, detail=f"continuous/{family}")
            result = self.jamming_engine.generate(
                ContinuousJammingConfig(
                    family=family,
                    sample_rate_hz=48_000,
                    duration_seconds=duration,
                    offsets_hz=offsets,
                    output_peak=self.et_continuous_level.value(),
                )
            )
            finite = bool(np.all(np.isfinite(result.samples)))
            validation = "PASS" if finite and result.peak_magnitude <= self.et_continuous_level.value() + 1e-9 else "FAIL"
            task_result = new_task_result(
                task_type="continuous_jamming",
                mode=mode.value,
                source="DETERMİNİSTİK TABAN BANT",
                duration=result.duration_seconds,
                waveform_type=family,
                sample_rate=result.sample_rate_hz,
                sample_count=result.samples.size,
                normalization_status="PASS" if finite else "FAIL",
                validation_status=validation,
                details={
                    "occupied_bandwidth_hz": result.occupied_bandwidth_hz,
                    "peak_magnitude": result.peak_magnitude,
                    "center_frequency_hz": 0.0,
                    "offsets_hz": offsets if family in {"single", "multiple"} else (),
                    "preview_action": preview,
                },
            )
            self.et_mission.complete(detail=f"continuous/{family} tamamlandı")
            self._plot_et_preview(result.samples[:384], result.sample_rate_hz, spectrum_samples=result.samples)
            self.et_sweep_plot.hide()
            offset_text = (
                "Ofset: " + ", ".join(f"{offset / 1000.0:.1f} kHz" for offset in offsets)
                if family in {"single", "multiple"}
                else "Merkez: 0 kHz · Baraj: ±8.0 kHz"
            )
            self.et_result_values["detail"].setText(f"{offset_text} · {result.duration_seconds:.1f} s")
            self._start_et_animation(
                task_key="continuous",
                samples=result.samples,
                sample_rate_hz=result.sample_rate_hz,
                task_result=task_result,
                metric=f"Bant: {result.occupied_bandwidth_hz / 1000.0:.2f} kHz",
                completion_detail=f"continuous/{family} tamamlandı",
            )
        except (ValueError, RuntimeError, PermissionError) as exc:
            self._show_et_error(exc)

    def _start_deception_preview(self) -> None:
        self._run_analog_task(loopback=False)

    def _run_analog_loopback_test(self) -> None:
        self._run_analog_task(loopback=True)

    def _run_analog_task(self, *, loopback: bool) -> None:
        duration = self.et_analog_duration_spin.value()
        audio_rate = 48_000
        source_duration = min(duration, 1.0)
        time = np.arange(round(audio_rate * source_duration), dtype=np.float64) / audio_rate
        audio = np.sin(2.0 * np.pi * 1_000.0 * time)
        try:
            mode = self._begin_et_task(duration=duration, detail=f"analog/{self.et_deception_mode.currentText()}")
            result = self.deception_engine.generate(
                audio,
                AnalogDeceptionConfig(
                    mode=self.et_deception_mode.currentText(),
                    duration_seconds=duration,
                    output_peak=self.et_audio_level.value(),
                ),
            )
            finite = bool(np.all(np.isfinite(result.samples)) and np.all(np.isfinite(result.normalized_audio)))
            validation = "PASS" if finite and result.loopback_correlation >= 0.999 and result.peak_magnitude <= self.et_audio_level.value() + 1e-9 else "FAIL"
            task_result = new_task_result(
                task_type="analog_deception",
                mode=mode.value,
                source="TEST SESİ · YEREL DÖNGÜ",
                duration=result.duration_seconds,
                waveform_type=result.mode,
                sample_rate=result.sample_rate_hz,
                sample_count=result.samples.size,
                normalization_status="PASS" if finite else "FAIL",
                validation_status=validation,
                details={
                    "input_audio_duration_seconds": source_duration,
                    "loopback_correlation": result.loopback_correlation,
                    "audio_bandwidth_hz": result.audio_bandwidth_hz,
                    "peak_magnitude": result.peak_magnitude,
                    "loopback_action": loopback,
                },
            )
            self.et_mission.complete(detail=f"analog/{result.mode} loopback tamamlandı")
            self._plot_analog_preview(result.normalized_audio[:2048], result.samples, result.sample_rate_hz, result.mode)
            self.et_result_values["detail"].setText(f"Modülasyon: {result.mode} · Uyum: {result.loopback_correlation:.4f}")
            self._start_et_animation(
                task_key="analog",
                samples=result.samples,
                sample_rate_hz=result.sample_rate_hz,
                audio=result.normalized_audio,
                task_result=task_result,
                metric=f"Uyum: {result.loopback_correlation:.4f}",
                completion_detail=f"analog/{result.mode} tamamlandı",
            )
        except (ValueError, RuntimeError, PermissionError) as exc:
            self._show_et_error(exc)

    def _run_interleaved_test(self) -> None:
        scenario = str(self.et_interleaved_scenario.currentData())
        try:
            result = self.interleaved_engine.run(InterleavedConfig(scenario=scenario))
            mode = self._begin_et_task(duration=result.duration_seconds, detail=f"interleaved/{scenario}")
            last_window = result.windows[-1]
            measured_windows = [window for window in result.windows if window.measured_band_power is not None]
            last_measured = measured_windows[-1].measured_band_power if measured_windows else None
            expected = 0 if scenario == "absent" else 1
            validation = "PASS" if (result.task_activation_count == 0 if expected == 0 else result.task_activation_count >= expected) else "FAIL"
            task_result = new_task_result(
                task_type="interleaved_task_control",
                mode=mode.value,
                source="DETERMİNİSTİK OFFLINE GÖREV TAMPONU",
                duration=result.duration_seconds,
                waveform_type="ZAMAN-PAYLAŞIMLI TON",
                sample_rate=result.sample_rate_hz,
                sample_count=result.task_output_samples.size,
                normalization_status="PASS",
                validation_status=validation,
                details={
                    "scenario": result.scenario,
                    "analysis_input_sample_rate": result.sample_rate_hz,
                    "analysis_input_sample_count": result.analysis_samples.size,
                    "task_activation_count": result.task_activation_count,
                    "listen_window_count": result.listen_window_count,
                    "response_delay_window_count": result.response_delay_window_count,
                    "task_window_count": result.task_window_count,
                    "guard_window_count": result.guard_window_count,
                    "task_duty_cycle": result.task_duty_cycle,
                    "active_output_sample_count": int(np.count_nonzero(result.task_gate)),
                    "last_band_power": last_measured,
                    "last_decision": last_window.decision,
                    "state_sequence": result.timeline,
                },
            )
            self.et_mission.complete(detail=f"interleaved/{scenario} tamamlandı")
            self.et_result_values["detail"].setText("Dizi: DİNLE → GECİKME → GÖREV → KORUMA")
            self._start_et_animation(
                task_key="interleaved",
                samples=result.task_output_samples,
                sample_rate_hz=result.sample_rate_hz,
                task_result=task_result,
                metric=f"{result.task_activation_count} çevrim · %{result.task_duty_cycle * 100.0:.1f} görev çevrimi",
                completion_detail=f"interleaved/{scenario} tamamlandı",
                timeline=result.timeline,
                windows=result.windows,
            )
        except (ValueError, RuntimeError, PermissionError) as exc:
            self._show_et_error(exc)

    def _run_gnss_validation(self) -> None:
        raw_ids = self.et_gnss_satellites.text().strip()
        try:
            satellite_ids = tuple(int(value.strip()) for value in raw_ids.split(",") if value.strip())
        except ValueError:
            satellite_ids = (0,)
        scenario = GNSSScenario(
            latitude_deg=self.et_gnss_latitude.value(),
            longitude_deg=self.et_gnss_longitude.value(),
            scenario_time_utc=self.et_gnss_time.text().strip(),
            satellite_ids=satellite_ids,
        )
        try:
            mode = self._begin_et_task(duration=min(scenario.duration_seconds, 30.0), detail="gnss/validation")
            validation = self.gnss_validator.validate(scenario)
            status = "PASS" if validation.valid else "FAIL"
            task_result = new_task_result(
                task_type="gnss_scenario",
                mode=mode.value,
                source="METADATA DOĞRULAMA",
                duration=0.0,
                waveform_type="METADATA",
                sample_rate=0,
                sample_count=0,
                normalization_status="UYGULANMAZ",
                validation_status=status,
                details={
                    "service": validation.service,
                    "position_time_consistent": validation.position_time_consistent,
                    "scenario_data_available": validation.scenario_data_available,
                    "metadata_contract_valid": validation.metadata_contract_valid,
                    "waveform_available": validation.waveform_available,
                    "errors": validation.errors,
                },
            )
            self.et_mission.complete(detail=f"gnss/{status.lower()}")
            if validation.valid:
                self.et_gnss_visual_result.setText(
                    f"Servis: {validation.service}\n"
                    f"Konum: {scenario.latitude_deg:.5f}, {scenario.longitude_deg:.5f}\n"
                    f"Zaman: {scenario.scenario_time_utc}\n"
                    "Doğrulama: PASS\n"
                    "OFFLINE · TX KİLİTLİ · RF TX YOK"
                )
                self.et_gnss_visual_status.setText("Metadata doğrulandı.")
                self.et_result_values["detail"].setText("GPS L1 C/A · Doğrulandı")
                metric = "GPS L1 C/A doğrulandı"
            else:
                self.et_gnss_visual_result.setText("✕ Doğrulama başarısız\n" + "\n".join(validation.errors))
                metric = validation.errors[0] if validation.errors else "Doğrulama başarısız"
            self._show_et_result(task_result, metric=metric)
        except (ValueError, RuntimeError, PermissionError) as exc:
            self._show_et_error(exc)

    def _plot_et_preview(
        self, samples: np.ndarray, sample_rate_hz: float, *, start_sample: int = 0, spectrum_samples: np.ndarray | None = None
    ) -> None:
        visible = np.asarray(samples[: min(samples.size, 2048)])
        time_ms = np.arange(visible.size) / sample_rate_hz * 1000.0
        self.et_waveform_curve.setData(time_ms, visible.real)
        self.et_waveform_cursor.setData([time_ms[-1]], [visible.real[-1]])
        frequencies, spectrum_db = self._et_spectrum_data(samples if spectrum_samples is None else spectrum_samples, sample_rate_hz)
        self.et_spectrum_curve.setData(frequencies, spectrum_db)

    @staticmethod
    def _et_spectrum_data(samples: np.ndarray, sample_rate_hz: float) -> tuple[np.ndarray, np.ndarray]:
        fft_size = min(4096, samples.size)
        values = np.asarray(samples[:fft_size], dtype=np.complex128)
        spectrum = np.abs(np.fft.fftshift(np.fft.fft(values))) ** 2
        frequencies = np.fft.fftshift(np.fft.fftfreq(fft_size, d=1.0 / sample_rate_hz)) / 1000.0
        spectrum_db = 10.0 * np.log10(np.maximum(spectrum / max(float(np.max(spectrum)), 1e-30), 1e-12))
        return frequencies, spectrum_db

    def _plot_sweep_waterfall(self, samples: np.ndarray, sample_rate_hz: float, *, visible: bool) -> None:
        self.et_sweep_plot.setVisible(visible)
        if not visible:
            return
        window = min(512, samples.size)
        hop = max(window // 2, 1)
        maximum_start = max(samples.size - window, 0)
        frame_count = min(128, maximum_start // hop + 1)
        starts = np.linspace(0, maximum_start, frame_count, dtype=np.int64)
        frames = [samples[int(start) : int(start) + window] for start in starts]
        if not frames:
            return
        power = np.asarray([np.abs(np.fft.fftshift(np.fft.fft(frame))) ** 2 for frame in frames], dtype=np.float64).T
        image = 10.0 * np.log10(np.maximum(power / max(float(np.max(power)), 1e-30), 1e-12))
        self.et_sweep_image.setImage(image, autoLevels=True)

    def _plot_analog_preview(self, audio: np.ndarray, samples: np.ndarray, sample_rate_hz: float, mode: str, *, start_sample: int = 0) -> None:
        visible = np.asarray(audio[: min(audio.size, 2048)])
        self.et_analog_audio_curve.setData(start_sample + np.arange(visible.size), visible)
        frequencies, spectrum_db = self._et_spectrum_data(samples, sample_rate_hz)
        self.et_analog_spectrum_curve.setData(frequencies, spectrum_db)
        self.et_analog_spectrum_plot.setTitle(f"{mode} Spektrumu")

    def _plot_interleaved_result(self, samples: np.ndarray, sample_rate_hz: float, windows: tuple[object, ...]) -> None:
        power = np.asarray(
            [np.nan if getattr(item, "measured_band_power") is None else float(getattr(item, "measured_band_power")) for item in windows],
            dtype=np.float64,
        )
        indices = np.arange(power.size, dtype=np.float64) + 1.0
        self.et_interleaved_timeline_curve.setData(indices, power)
        self.et_interleaved_threshold_curve.setData(indices, np.full(power.size, 0.12, dtype=np.float64))
        active_indices = np.asarray(
            [index for index, item in enumerate(windows, start=1) if bool(getattr(item, "task_active"))], dtype=np.float64
        )
        task_levels = np.full(active_indices.size, 0.138, dtype=np.float64)
        self.et_interleaved_task_marker.setData(active_indices, task_levels)
        frequencies, spectrum_db = self._et_spectrum_data(samples, sample_rate_hz)
        self.et_interleaved_spectrum_curve.setData(frequencies, spectrum_db)

    def _stop_et_mission(self) -> None:
        self._cancel_et_animation("Görev durduruldu")
        if self.et_mission.state == "ÇALIŞIYOR":
            self.et_mission.stop()
        self.et_header_values["status"].setText("DURDURULDU")
        self.et_state_label.setText("DURDURULDU")
        self._refresh_et_log()

    def _emergency_stop_et(self) -> None:
        self._cancel_et_animation("Acil durdurma")
        self.et_mission.emergency_stop()
        self.et_mission.reset_emergency_stop()
        self.et_header_values["status"].setText("DURDURULDU")
        self.et_state_label.setText("DURDURULDU")
        self._refresh_et_log()
