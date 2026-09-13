"""Dinleme çalışma alanı mixin'i."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .spectrum_view import AnalysisSpectrumView
from .ui_text import TEXT

class ListeningWorkspaceMixin:
    def _build_system_workspace(self) -> QWidget:
        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(16, 16, 16, 16)
        heading = QLabel("Sistem Durumu")
        heading.setObjectName("selectedSignalTitle")
        heading.setWordWrap(True)
        layout.addWidget(heading)
        self.system_status_values: dict[str, QLabel] = {}
        rows = (
            ("source", "Veri Kaynağı", "HackRF Canlı RX · Etkin değil"),
            ("hackrf_tools", "HackRF Araçları", "Denetlenmedi"),
            ("hackrf", "HackRF", "Bağlı Değil"),
            ("serial", "Seri No", "Atanmadı"),
            ("center", "Merkez Frekansı", "—"),
            ("sampling", "Örnekleme Hızı", "—"),
            ("rx", "RX Durumu", "Durduruldu"),
            ("dropped", "Kayıp Çerçeve", "0"),
            ("processing", "İşleme", "Bilgisayar Referansı"),
            ("zedboard", "ZedBoard", "Kullanılmıyor"),
            ("fpga", "FPGA Sonucu", "Kullanılmıyor"),
            ("transport", "Taşıma", "Bağlı Değil"),
            ("petalinux", "PetaLinux / ARM", "Çalıştırılmadı"),
            ("calibration", "RF Kalibrasyonu", TEXT["calibration_pending"]),
        )
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)
        for row, (key, caption, value) in enumerate(rows):
            label = QLabel(value)
            label.setProperty("class", "propValue")
            label.setWordWrap(True)
            c_lbl = QLabel(caption)
            c_lbl.setProperty("class", "propCaption")
            c_lbl.setWordWrap(True)
            grid.addWidget(c_lbl, row, 0)
            grid.addWidget(label, row, 1)
            self.system_status_values[key] = label
        layout.addLayout(grid)
        layout.addStretch(1)
        return workspace

    def _build_listening_workspace(self) -> QWidget:
        self.listening_spectrum = AnalysisSpectrumView()
        panel = QFrame()
        panel.setObjectName("listeningPanel")
        panel.setMinimumWidth(280)
        panel.setMaximumWidth(340)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        heading = QLabel("Dinleme")
        heading.setObjectName("selectedSignalTitle")
        heading.setWordWrap(True)
        layout.addWidget(heading)
        self.listening_source_value = QLabel(TEXT["no_source"])
        self.listening_source_value.setProperty("class", "propValue")
        self.listening_source_value.setWordWrap(True)
        layout.addWidget(self.listening_source_value)
        self.listening_event_value = QLabel(TEXT["listening_select_event"])
        self.listening_event_value.setProperty("class", "propCaption")
        self.listening_event_value.setWordWrap(True)
        layout.addWidget(self.listening_event_value)
        self.listening_values: dict[str, QLabel] = {}
        status_grid = QGridLayout()
        status_grid.setHorizontalSpacing(14)
        status_grid.setVerticalSpacing(6)
        status_rows = (
            ("mode", "Mod"),
            ("carrier", "Taşıyıcı"),
            ("bandwidth", "Kanal BW"),
            ("iq_rate", "IQ Hızı"),
            ("audio_rate", "Ses Hızı"),
            ("duration", "Süre"),
            ("levels", "Seviye"),
            ("backend", "Kaynak"),
        )
        for row, (key, caption) in enumerate(status_rows):
            value = QLabel("—")
            value.setProperty("class", "propValue")
            value.setWordWrap(True)
            c_lbl = QLabel(caption)
            c_lbl.setProperty("class", "propCaption")
            c_lbl.setWordWrap(True)
            status_grid.addWidget(c_lbl, row, 0)
            status_grid.addWidget(value, row, 1)
            self.listening_values[key] = value
        layout.addLayout(status_grid)
        grid = QGridLayout()
        self.demod_combo = QComboBox()
        self.demod_combo.addItem("AM", "am")
        self.demod_combo.addItem(TEXT["nfm"], "nfm")
        self.listen_offset_spin = QDoubleSpinBox()
        self.listen_offset_spin.setRange(-100_000.0, 100_000.0)
        self.listen_offset_spin.setDecimals(3)
        self.listen_offset_spin.setSuffix(" kHz")
        self.listen_bandwidth_spin = QDoubleSpinBox()
        self.listen_bandwidth_spin.setRange(12.5, 25.0)
        self.listen_bandwidth_spin.setDecimals(1)
        self.listen_bandwidth_spin.setValue(12.5)
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
            label.setProperty("class", "propCaption")
            label.setWordWrap(True)
            grid.addWidget(label, row, 0)
            grid.addWidget(widget, row, 1)
        layout.addLayout(grid)
        self.listening_state = QLabel(TEXT["listening_not_prepared"])
        self.listening_state.setObjectName("listeningState")
        self.listening_state.setProperty("class", "propValue")
        self.listening_state.setWordWrap(True)
        layout.addWidget(self.listening_state)
        self.audio_backend_state = QLabel(TEXT["audio_backend_pending"])
        self.audio_backend_state.setProperty("class", "propCaption")
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
        splitter.setSizes([1050, 310])
        splitter.setStretchFactor(0, 1)
        splitter.setChildrenCollapsible(False)
        workspace = QWidget()
        outer = QVBoxLayout(workspace)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(splitter)
        self.clear_listening()
        return workspace
