"""Main window for the permanent PHASE-03 operation console."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QLocale, QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from reference.sigmf.contract import ContractReport
from reference.detection import DetectionEvent, DetectionFrameResult

from .spectrum_view import SpectrumView
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
        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(12)
        header_layout.addWidget(title)
        header_layout.addSpacing(12)
        header_layout.addWidget(source_caption)
        header_layout.addWidget(self.source_value, 1)
        header_layout.addWidget(self.open_button)

        self.notification = QLabel()
        self.notification.setObjectName("notification")
        self.notification.setWordWrap(True)
        self.notification.hide()

        self.spectrum_view = SpectrumView()
        metadata_panel = self._build_metadata_panel()
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setObjectName("mainSplitter")
        main_splitter.addWidget(self.spectrum_view)
        main_splitter.addWidget(metadata_panel)
        main_splitter.setSizes([1040, 300])
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)
        main_splitter.setChildrenCollapsible(False)

        controls = self._build_controls()
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(header)
        layout.addWidget(self.notification)
        layout.addWidget(main_splitter, 1)
        layout.addWidget(controls)
        self.setCentralWidget(central)
        self.show_empty()

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
        note = QLabel(TEXT["uncalibrated"])
        note.setObjectName("calibrationNote")
        note.setWordWrap(True)
        layout.addWidget(note)
        return panel

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

    def show_empty(self) -> None:
        self.source_value.setText(TEXT["no_source"])
        for value in self.metadata_values.values():
            value.setText("—")
        self.state_value.setText(TEXT["empty"])
        self.spectrum_view.clear_all()
        self.clear_detections()
        self.set_source_controls_enabled(False)
        self.hide_notification()

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
