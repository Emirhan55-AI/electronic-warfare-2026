"""Alt kontroller ve gelişmiş ayarlar mixin'i."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDockWidget, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QStackedWidget, QToolButton, QVBoxLayout, QWidget)

from algorithms.p0.search import SearchMode
from .ui_text import TEXT


class ControlsMixin:

    def _build_bottom_controls(self) -> QFrame:
        """Single-row compact command bar replacing the previous 3-card layout."""
        panel = QFrame()
        panel.setObjectName("searchControlsContainer")
        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(10, 4, 10, 4)
        main_layout.setSpacing(3)

        # ── Single compact row ────────────────────────────────────────────────
        bar = QHBoxLayout()
        bar.setSpacing(8)

        # -- Arama modu --
        lbl_mode = QLabel("Mod:")
        lbl_mode.setProperty("class", "propCaption")
        self.search_mode_combo = QComboBox()
        self.search_mode_combo.addItem("Bilinmeyen Frekans", SearchMode.UNKNOWN)
        self.search_mode_combo.addItem("Bant Aralığı", SearchMode.JUDGE_BAND)
        self.search_mode_combo.addItem("Frekans Belirtildi", SearchMode.JUDGE_FREQUENCY)
        self.search_mode_combo.setMinimumHeight(28)
        bar.addWidget(lbl_mode)
        bar.addWidget(self.search_mode_combo)

        # -- Parametreli giriş (stacked, moda göre değişir) --
        self.search_inputs = QStackedWidget()
        self.search_inputs.setMinimumHeight(28)
        self.search_inputs.setMaximumHeight(34)

        unknown_page = QWidget()
        unknown_layout = QHBoxLayout(unknown_page)
        unknown_layout.setContentsMargins(0, 0, 0, 0)
        lbl_unk = QLabel("Tüm bant taranır")
        lbl_unk.setWordWrap(True)
        lbl_unk.setProperty("class", "propCaption")
        unknown_layout.addWidget(lbl_unk)
        unknown_layout.addStretch(1)
        self.search_inputs.addWidget(unknown_page)

        band_page = QWidget()
        band_layout = QHBoxLayout(band_page)
        band_layout.setContentsMargins(0, 0, 0, 0)
        band_layout.setSpacing(4)
        self.judge_band_lower_spin = QDoubleSpinBox()
        self.judge_band_upper_spin = QDoubleSpinBox()
        for widget in (self.judge_band_lower_spin, self.judge_band_upper_spin):
            widget.setRange(1.0, 6000.0)
            widget.setDecimals(6)
            widget.setSuffix(" MHz")
            widget.setMinimumHeight(28)
        self.judge_band_lower_spin.setValue(100.080)
        self.judge_band_upper_spin.setValue(100.100)
        lbl_alt = QLabel("Alt")
        lbl_alt.setProperty("class", "propCaption")
        lbl_ust = QLabel("Üst")
        lbl_ust.setProperty("class", "propCaption")
        band_layout.addWidget(lbl_alt)
        band_layout.addWidget(self.judge_band_lower_spin, 1)
        band_layout.addWidget(lbl_ust)
        band_layout.addWidget(self.judge_band_upper_spin, 1)
        self.search_inputs.addWidget(band_page)

        frequency_page = QWidget()
        frequency_layout = QHBoxLayout(frequency_page)
        frequency_layout.setContentsMargins(0, 0, 0, 0)
        frequency_layout.setSpacing(4)
        self.judge_frequency_spin = QDoubleSpinBox()
        self.judge_frequency_spin.setRange(1.0, 6000.0)
        self.judge_frequency_spin.setDecimals(6)
        self.judge_frequency_spin.setSuffix(" MHz")
        self.judge_frequency_spin.setValue(100.090)
        self.judge_frequency_spin.setMinimumHeight(28)
        lbl_merkez = QLabel("Merkez")
        lbl_merkez.setProperty("class", "propCaption")
        frequency_layout.addWidget(lbl_merkez)
        frequency_layout.addWidget(self.judge_frequency_spin, 1)
        self.search_inputs.addWidget(frequency_page)

        bar.addWidget(self.search_inputs, 2)

        # -- Separator --
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setObjectName("commandBarSep")
        bar.addWidget(sep1)

        # -- Kontroller --
        self.start_button = QPushButton(TEXT["start"])
        self.start_button.setObjectName("primaryButton")
        self.start_button.setMinimumHeight(28)
        self.pause_button = QPushButton(TEXT["pause"])
        self.pause_button.setMinimumHeight(28)
        self.pause_button.hide()
        self.stop_button = QPushButton(TEXT["stop"])
        self.stop_button.setMinimumHeight(28)
        bar.addWidget(self.start_button)
        bar.addWidget(self.pause_button)
        bar.addWidget(self.stop_button)

        # Taramayı Başlat: gizli tutulur ama referans korunur (controller bağlantısı için)
        self.search_start_button = QPushButton("Taramayı Başlat")
        self.search_start_button.setEnabled(False)
        self.search_start_button.hide()

        # -- Separator --
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setObjectName("commandBarSep")
        bar.addWidget(sep2)

        # -- Durum ve pozisyon --
        self.state_value = QLabel(TEXT["empty"])
        self.state_value.setObjectName("stateValue")
        self.state_value.setProperty("class", "propValueAccent")
        bar.addWidget(self.state_value)

        self.active_search_mode_label = QLabel("● Hazır")
        self.active_search_mode_label.setObjectName("searchStatus")
        self.active_search_mode_label.setProperty("class", "propValueAccent")
        bar.addWidget(self.active_search_mode_label)

        bar.addStretch(1)

        frame_caption = QLabel(TEXT["frame_position"])
        frame_caption.setProperty("class", "propCaption")
        frame_caption.setWordWrap(True)
        self.frame_spin = QSpinBox()
        self.frame_spin.setMinimum(1)
        self.frame_spin.setMaximum(1)
        self.frame_spin.setMinimumHeight(28)
        self.frame_spin.setMaximumWidth(90)
        speed_caption = QLabel(TEXT["review_speed"])
        speed_caption.setProperty("class", "propCaption")
        speed_caption.setWordWrap(True)
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(1, 30)
        self.speed_spin.setValue(10)
        self.speed_spin.setSuffix(" fps")
        self.speed_spin.setMinimumHeight(28)
        self.speed_spin.setMaximumWidth(80)
        bar.addWidget(frame_caption)
        bar.addWidget(self.frame_spin)
        bar.addWidget(speed_caption)
        bar.addWidget(self.speed_spin)

        main_layout.addLayout(bar)


        # -- Gelismis Ayarlar toggle (artik dock acar) --
        self.advanced_toggle = QToolButton()
        self.advanced_toggle.setObjectName("collapseToggle")
        self.advanced_toggle.setText("Gelismis")
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setToolTip("Gelismis Ayarlar panelini ac/kapat")
        self.advanced_toggle.toggled.connect(self._toggle_advanced_settings)
        bar.addWidget(self.advanced_toggle)

        # Gelismis Ayarlar widget'lari burada tanimlaniyor (dock icerigini olusturur)
        self.advanced_settings = QWidget()
        advanced = QGridLayout(self.advanced_settings)
        advanced.setContentsMargins(8, 6, 8, 6)
        advanced.setHorizontalSpacing(10)
        advanced.setVerticalSpacing(6)

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

        axis_caption = QLabel(TEXT["axis"])
        axis_caption.setProperty("class", "propCaption")
        display_caption = QLabel(TEXT["display"])
        display_caption.setProperty("class", "propCaption")
        pfa_caption = QLabel(TEXT["pfa"])
        pfa_caption.setProperty("class", "propCaption")

        advanced.addWidget(axis_caption, 0, 0)
        advanced.addWidget(self.axis_combo, 0, 1)
        advanced.addWidget(display_caption, 0, 2)
        advanced.addWidget(self.metric_combo, 0, 3)
        advanced.addWidget(self.dc_checkbox, 0, 4)
        advanced.addWidget(self.average_checkbox, 0, 5)
        advanced.addWidget(self.detection_layer_checkbox, 1, 0, 1, 2)
        advanced.addWidget(pfa_caption, 1, 2)
        advanced.addWidget(self.pfa_combo, 1, 3)
        advanced.addWidget(self.center_checkbox, 1, 4, 1, 2)

        self.search_mode_combo.currentIndexChanged.connect(self._search_mode_changed)
        self.search_start_button.clicked.connect(self._start_competition_search)
        self._search_mode_changed(0)
        return panel

    def _late_setup_advanced_dock(self) -> None:
        """Called after _build_bottom_controls creates advanced_settings."""
        if self.dock_advanced is not None or not hasattr(self, "advanced_settings"):
            return
        self.dock_advanced = QDockWidget("Gelismis Ayarlar", self)
        self.dock_advanced.setObjectName("dockAdvanced")
        self.dock_advanced.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.dock_advanced.setWidget(self.advanced_settings)
        self.dock_advanced.setMinimumHeight(80)
        self.dock_advanced.setMaximumHeight(120)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_advanced)
        self.dock_advanced.hide()
        self.dock_advanced.visibilityChanged.connect(
            lambda vis: self.advanced_toggle.setChecked(vis)
        )
        self.dock_widgets.append(self.dock_advanced)

    def _toggle_advanced_settings(self, expanded: bool) -> None:
        if self.dock_advanced is None:
            self._late_setup_advanced_dock()
        if self.dock_advanced is not None:
            self.dock_advanced.setVisible(expanded)
        self.advanced_toggle.setText("Gelismis *" if expanded else "Gelismis")

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
