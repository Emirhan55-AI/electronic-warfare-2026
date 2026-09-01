"""Arama çalışma alanı mixin'i."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from algorithms.p0.search import SearchMode, SearchRequest
from .spectrum_view import SpectrumView
from .ui_text import TEXT

class SearchWorkspaceMixin:
    def _build_search_main_workspace(self) -> QWidget:
        """Create the primary, high-visibility search workspace."""
        workspace = QWidget()
        workspace.setObjectName("workspaceArea")
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Main Spectrum and Waterfall
        self.spectrum_view = SpectrumView()
        self.spectrum_view.setMinimumSize(600, 300)

        # Clean Signal List (Sinyaller)
        signal_list_panel = self._build_signal_list_panel()

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setObjectName("searchSplitter")
        splitter.addWidget(self.spectrum_view)
        splitter.addWidget(signal_list_panel)
        splitter.setSizes([600, 110])
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)
        splitter.setChildrenCollapsible(False)

        # Unified 3-Group Bottom Controls
        self.controls_panel = self._build_bottom_controls()

        layout.addWidget(splitter, 1)
        layout.addWidget(self.controls_panel, 0)
        return workspace

    def _build_signal_list_panel(self) -> QFrame:
        """Create the clean signal list container on the Sinyal Tespiti workspace."""
        panel = QFrame()
        panel.setObjectName("signalListContainer")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(3)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        self.signal_list_title = QLabel("Sinyaller")
        self.signal_list_title.setObjectName("selectedSignalTitle")
        self.signal_list_title.setWordWrap(True)
        self.detection_state = QLabel(TEXT["no_detection"])
        self.detection_state.setProperty("class", "propCaption")
        self.detection_state.setWordWrap(True)
        self.detection_state.hide()
        self.detection_note = QLabel("")
        self.detection_note.setProperty("class", "propCaption")
        self.detection_note.setWordWrap(True)
        header_row.addWidget(self.signal_list_title)
        header_row.addStretch(1)
        header_row.addWidget(self.detection_note)
        layout.addLayout(header_row)

        self.detection_list = QListWidget()
        self.detection_list.setObjectName("detectionList")
        self.detection_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.detection_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.detection_list.setMinimumHeight(60)
        self.detection_list.setMaximumHeight(130)
        self.detection_list.itemSelectionChanged.connect(self._on_detection_selection_changed)
        layout.addWidget(self.detection_list, 1)
        return panel

    def _build_selected_signal_panel(self) -> QFrame:
        """Create a compact, non-intrusive inspector for the selected signal."""
        panel = QFrame()
        panel.setObjectName("selectedSignalCard")
        panel.setMinimumWidth(260)
        panel.setMaximumWidth(310)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Header Title
        title = QLabel("Seçili Sinyal")
        title.setObjectName("selectedSignalTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        # Big Frequency
        self.card_freq_val = QLabel("—")
        self.card_freq_val.setObjectName("selectedSignalFreq")
        self.card_freq_val.setWordWrap(True)
        layout.addWidget(self.card_freq_val)

        # State Badge
        self.selected_signal_badge = QLabel("Sinyal seçilmedi")
        self.selected_signal_badge.setObjectName("selectedSignalBadge")
        self.selected_signal_badge.setProperty("state", "empty")
        self.selected_signal_badge.setWordWrap(True)
        layout.addWidget(self.selected_signal_badge)

        sep = QFrame()
        sep.setObjectName("subtleSeparator")
        layout.addWidget(sep)

        # Clean Key-Value Grid
        grid = QGridLayout()
        grid.setContentsMargins(0, 4, 0, 4)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        def make_row(caption: str) -> tuple[QLabel, QLabel]:
            lbl_c = QLabel(caption)
            lbl_c.setProperty("class", "propCaption")
            lbl_c.setWordWrap(True)
            lbl_v = QLabel("—")
            lbl_v.setProperty("class", "propValue")
            lbl_v.setWordWrap(True)
            lbl_v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return lbl_c, lbl_v

        c_bw, self.card_bw_val = make_row("Bant Genişliği")
        c_snr, self.card_snr_val = make_row("SNR")
        c_pwr, self.card_power_val = make_row("Seviye")
        c_dom, self.card_domain_val = make_row("Sinyal Türü")
        c_brg, self.card_bearing_val = make_row("Yön")

        props = (
            (c_bw, self.card_bw_val),
            (c_snr, self.card_snr_val),
            (c_pwr, self.card_power_val),
            (c_dom, self.card_domain_val),
            (c_brg, self.card_bearing_val),
        )
        for row, (c_lbl, v_lbl) in enumerate(props):
            grid.addWidget(c_lbl, row, 0)
            grid.addWidget(v_lbl, row, 1)

        layout.addLayout(grid)

        sep2 = QFrame()
        sep2.setObjectName("subtleSeparator")
        layout.addWidget(sep2)

        # On-Demand Technical Details
        self.card_details_toggle = QToolButton()
        self.card_details_toggle.setObjectName("collapseToggle")
        self.card_details_toggle.setText("▸ Teknik Ayrıntılar")
        self.card_details_toggle.setCheckable(True)
        layout.addWidget(self.card_details_toggle)

        self.card_details_widget = QWidget()
        details_layout = QVBoxLayout(self.card_details_widget)
        details_layout.setContentsMargins(0, 4, 0, 0)
        details_layout.setSpacing(3)
        self.card_details_text = QLabel("Ayrıntı görmek için sinyal seçin.")
        self.card_details_text.setProperty("class", "propCaption")
        self.card_details_text.setWordWrap(True)
        details_layout.addWidget(self.card_details_text)
        self.card_details_widget.hide()
        layout.addWidget(self.card_details_widget)

        self.card_details_toggle.toggled.connect(
            lambda checked: [
                self.card_details_widget.setVisible(checked),
                self.card_details_toggle.setText("▾ Teknik Ayrıntılar" if checked else "▸ Teknik Ayrıntılar"),
            ]
        )

        layout.addStretch(1)
        return panel

    def _build_metadata_panel(self) -> QFrame:
        """Build the on-demand Hardware & Source settings panel."""
        panel = QFrame()
        panel.setObjectName("metadataPanel")
        panel.setMinimumWidth(260)
        panel.setMaximumWidth(340)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        heading = QLabel("KAYNAK VE DONANIM AYARLARI")
        heading.setObjectName("selectedSignalTitle")
        layout.addWidget(heading)

        self.hackrf_panel = QFrame()
        self.hackrf_panel.setObjectName("hackrfPanel")
        hackrf_layout = QVBoxLayout(self.hackrf_panel)
        hackrf_layout.setContentsMargins(0, 0, 0, 6)
        hackrf_layout.setSpacing(6)
        hackrf_heading = QLabel(TEXT["hackrf_controls"])
        hackrf_heading.setObjectName("selectedSignalTitle")
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
            c_lbl = QLabel(caption)
            c_lbl.setProperty("class", "propCaption")
            hackrf_grid.addWidget(c_lbl, row, 0)
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

        self.source_summary = QLabel("Kaynak seçilmedi")
        self.source_summary.setObjectName("sourceSummary")
        self.source_summary.setWordWrap(True)
        layout.addWidget(self.source_summary)

        grid_holder = QWidget()
        grid = QGridLayout(grid_holder)
        grid.setHorizontalSpacing(10)
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
            caption_label.setProperty("class", "propCaption")
            caption_label.setWordWrap(True)
            value_label = QLabel("—")
            value_label.setProperty("class", "propValue")
            value_label.setWordWrap(True)
            value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(caption_label, row, 0)
            grid.addWidget(value_label, row, 1)
            self.metadata_values[key] = value_label
        grid.setColumnStretch(1, 1)
        layout.addWidget(grid_holder)

        profile_heading = QLabel("PROFİL")
        profile_heading.setObjectName("selectedSignalTitle")
        layout.addWidget(profile_heading)
        self.profile_value = QLabel("—")
        self.profile_value.setObjectName("profileValue")
        self.profile_value.setWordWrap(True)
        self.profile_value.setMinimumHeight(0)
        self.profile_value.setMaximumHeight(48)
        self.profile_value.setToolTip(TEXT["validated_envelope"])
        layout.addWidget(self.profile_value)
        layout.addStretch(1)
        return panel

    def _on_detection_selection_changed(self) -> None:
        items = self.detection_list.selectedItems()
        if not items:
            return
        item = items[0]
        text = item.text()
        tooltip = item.toolTip()
        self.selected_signal_badge.setText(text)
        self.selected_signal_badge.setProperty("state", "active")
        self.card_details_text.setText(tooltip)

    @staticmethod
    def _scroll_panel(panel: QWidget, name: str) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName(name)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(panel)
        scroll.setMinimumWidth(260)
        scroll.setMaximumWidth(360)
        return scroll

    def _build_controls(self) -> QFrame:
        return self._build_bottom_controls()

    def _build_search_workflow(self) -> QFrame:
        return QFrame()

    def _search_mode_changed(self, index: int) -> None:
        self.search_inputs.setCurrentIndex(max(0, min(index, self.search_inputs.count() - 1)))

    def _selected_search_request(self) -> SearchRequest:
        raw_mode = self.search_mode_combo.currentData()
        mode = raw_mode if isinstance(raw_mode, SearchMode) else SearchMode(str(raw_mode))
        if mode is SearchMode.UNKNOWN:
            return SearchRequest.unknown()
        if mode is SearchMode.JUDGE_BAND:
            return SearchRequest.judge_band_mhz(
                self.judge_band_lower_spin.value(),
                self.judge_band_upper_spin.value(),
            )
        if mode is SearchMode.JUDGE_FREQUENCY:
            return SearchRequest.judge_frequency_mhz(self.judge_frequency_spin.value())
        raise ValueError("Desteklenmeyen arama modu seçildi.")

    def _start_competition_search(self) -> None:
        if self.p0_search_engine is None:
            self.active_search_mode_label.setText("● Kaynak yok")
            return
        try:
            request = self._selected_search_request()
            result = self.p0_search_engine.execute(request)
        except ValueError as exc:
            self.active_search_mode_label.setText(f"● GİRDİ HATASI · {exc}")
            return
        self.last_search_result = result
        has_canonical_rows = any(
            isinstance(self.detection_list.item(row).data(Qt.ItemDataRole.UserRole), int)
            for row in range(self.detection_list.count())
        )
        if result.parameters:
            primary = result.parameters[0]
            self.set_p0_parameter_result(primary)
            if not has_canonical_rows:
                self.set_p0_detection_summary(primary)
            self.active_search_mode_label.setText(f"● {len(result.parameters)} sinyal")
        else:
            self.set_p0_parameter_result(None)
            if not has_canonical_rows:
                self.clear_detections()
                self.active_search_mode_label.setText("● Sinyal yok")
            else:
                self.active_search_mode_label.setText("● Aralıkta sinyal yok")
