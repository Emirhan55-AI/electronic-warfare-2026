"""Main window for the permanent spectrum, detection, and parameter console.
Refactored for low visual noise, clean copy, operator-focused language, and calm layout.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QLocale, QSettings, QSignalBlocker, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTabBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
import numpy as np
import pyqtgraph as pg

from reference.sigmf.contract import ContractReport
from reference.detection import DetectionEvent, DetectionFrameResult
from reference.parameters import EventParameterEstimate, ParameterFrameResult
from reference.p0.df import DFEstimate, DFMeasurement, ManualAmplitudeDF
from reference.p0.field_df import AntennaReference, LocationFix, PositionSource, geographic_bearing_from_manual_reference
from reference.p0.map_direction import DirectionPresentation, SensorPosition, build_direction_presentation
from reference.p0.models import P0ParameterResult
from reference.p0.recorded_df import RECORDED_DF_SOURCE, RecordedDFReport
from reference.p0.search import P0SearchEngine, SearchExecutionResult, SearchMode, SearchRequest

from .map_direction import DirectionMapView
from .map_providers import MapProviderMode
from .pc_location import LOCATION_FAILURE_TEXT, PCPositionProvider
from .spectrum_view import AnalysisSpectrumView, SpectrumView
from .ui_text import TEXT


LOGGER = logging.getLogger(__name__)


def _load_laboratory_dependencies() -> None:
    """Load validation-only models only for the explicit laboratory entry point."""

    global AnalogDeceptionConfig, AnalogDeceptionEngine, ContinuousJammingConfig
    global ContinuousJammingEngine, ETTaskResult, ETMissionController, GNSSScenario
    global GNSSScenarioValidator, InterleavedConfig, InterleavedJammingEngine
    global SafetyMode, new_task_result, REAL_TWO_POINT_SOURCE, TwoPointDFResult
    global analyze_two_point_hackrf_df, build_synthetic_df_scene

    from reference.et import (
        AnalogDeceptionConfig,
        AnalogDeceptionEngine,
        ContinuousJammingConfig,
        ContinuousJammingEngine,
        ETTaskResult,
        ETMissionController,
        GNSSScenario,
        GNSSScenarioValidator,
        InterleavedConfig,
        InterleavedJammingEngine,
        SafetyMode,
        new_task_result,
    )
    from reference.p0.df_fixtures import build_synthetic_df_scene
    from reference.p0.two_point_df import REAL_TWO_POINT_SOURCE, TwoPointDFResult, analyze_two_point_hackrf_df


class MainWindow(QMainWindow):
    """Calm, human-oriented operator console for RF spectrum, detection, and electronic warfare."""

    df_power_measure_requested = Signal()

    def __init__(self, *, laboratory_mode: bool = False) -> None:
        super().__init__()
        self.laboratory_mode = bool(laboratory_mode)
        if self.laboratory_mode:
            _load_laboratory_dependencies()
        self.setWindowTitle(TEXT["window_title"])
        self.setMinimumSize(960, 600)
        self.resize(1440, 900)
        self.locale = QLocale(QLocale.Language.Turkish, QLocale.Country.Turkey)
        self.setDockNestingEnabled(True)

        self.pc_location_provider = PCPositionProvider(self)
        self.pc_location_provider.pending.connect(self._pc_location_pending)
        self.pc_location_provider.acquired.connect(self._pc_location_acquired)
        self.pc_location_provider.failed.connect(self._pc_location_failed)

        # ------------------------------------------------------------------
        # Header: Instrument Toolbar Style (Clean, Compact)
        # ------------------------------------------------------------------
        self.open_button = QPushButton("Kaynak Aç")
        self.open_button.setObjectName("primaryButton")

        self.source_settings_button = QPushButton("Kaynak Ayarları")
        self.source_settings_button.setToolTip("Donanım ve kaynak ayarları")
        self.source_settings_button.clicked.connect(self._toggle_source_settings)

        self.source_value = QLabel(TEXT["no_source"])
        self.source_value.setObjectName("sourceValue")
        self.source_value.setWordWrap(True)
        self.source_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._replay_source_badge = "REPLAY"

        title = QLabel(TEXT["application_title"])
        title.setObjectName("applicationTitle")
        title.setWordWrap(True)

        self.source_type_combo = QComboBox()
        self.source_type_combo.setObjectName("sourceTypeCombo")
        self.source_type_combo.addItem(TEXT["source_sigmf"], "sigmf")
        self.source_type_combo.addItem(TEXT["source_hackrf"], "hackrf")
        if self.laboratory_mode:
            self.source_type_combo.addItem(TEXT["source_deterministic"], "deterministic_test")
        self.source_type_combo.setAccessibleName(TEXT["source_type"])

        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 6, 16, 6)
        header_layout.setSpacing(12)
        header_layout.addWidget(title)
        header_layout.addSpacing(10)
        header_layout.addWidget(self.source_type_combo)
        header_layout.addWidget(self.source_value)
        header_layout.addStretch(1)
        header_layout.addWidget(self.source_settings_button)
        header_layout.addWidget(self.open_button)

        self.notification = QLabel()
        self.notification.setObjectName("notification")
        self.notification.setWordWrap(True)
        self.notification.hide()

        # ------------------------------------------------------------------
        # Left Navigation Sidebar (Natural, Short Labels)
        # ------------------------------------------------------------------
        self.nav_sidebar = self._build_nav_sidebar()

        # ------------------------------------------------------------------
        # Workspaces Container
        # ------------------------------------------------------------------
        self.p0_search_engine: P0SearchEngine | None = None
        self.last_search_result: SearchExecutionResult | None = None

        self.workspace_tabs = QTabWidget()
        self.workspace_tabs.setObjectName("workspaceTabs")
        self.workspace_tabs.tabBar().hide()  # Driven by left sidebar

        # 0: Arama
        self.search_workspace = self._build_search_main_workspace()
        self.workspace_tabs.addTab(self.search_workspace, TEXT["operation_workspace"])

        # 1: Parametre
        self.analysis_workspace = self._build_analysis_workspace()
        self.workspace_tabs.addTab(self.analysis_workspace, TEXT["analysis_workspace"])

        # 2: Dinleme
        self.listening_workspace = self._build_listening_workspace()
        self.workspace_tabs.addTab(self.listening_workspace, TEXT["listening_workspace"])

        # 3: Yön
        self.direction_workspace = self._build_direction_workspace()
        self.workspace_tabs.addTab(self.direction_workspace, "Yön")

        # 4: Sistem
        self.system_workspace = self._build_system_workspace()
        self.workspace_tabs.addTab(self.system_workspace, TEXT["system_status_workspace"])

        if self.laboratory_mode:
            self.et_workspace = self._build_et_workspace()
            self.workspace_tabs.addTab(self.et_workspace, "ET — Offline Laboratuvar")

        self.workspace_tabs.currentChanged.connect(self._on_workspace_tab_changed)

        # ------------------------------------------------------------------
        # Right Selected Signal Inspector (Only active on Arama page)
        # ------------------------------------------------------------------
        self.selected_signal_panel = self._build_selected_signal_panel()

        # ------------------------------------------------------------------
        # Central Body
        # ------------------------------------------------------------------
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        body_layout.addWidget(self.nav_sidebar)
        body_layout.addWidget(self.workspace_tabs, 1)

        central = QWidget()
        central.setObjectName("centralWidget")
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(header)
        central_layout.addWidget(self.notification)
        central_layout.addLayout(body_layout, 1)
        self.setCentralWidget(central)

        # ------------------------------------------------------------------
        # Dockable Panels
        # ------------------------------------------------------------------
        self._setup_dock_widgets()

        # Setup Menu Bar & Status Bar
        self._setup_menu_bar()
        self._setup_status_bar()

        # Layout Persistence
        self._default_geometry = self.saveGeometry()
        self._default_state = self.saveState()
        self._restore_layout_state()

        self.show_empty()
        self.set_acquisition_mode("sigmf")

    def _build_nav_sidebar(self) -> QFrame:
        """Create a clean, vertical navigation rail with natural short labels."""
        sidebar = QFrame()
        sidebar.setObjectName("navSidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)

        self.nav_button_group = QButtonGroup(sidebar)
        self.nav_buttons: list[QPushButton] = []
        nav_items = [
            ("Sinyal Tespiti", 0),
            ("Parametreler", 1),
            ("Dinleme", 2),
            ("Yön", 3),
            ("Konum", 4),
            ("Sistem", 5),
        ]
        if self.laboratory_mode:
            nav_items.append(("ET Laboratuvarı", 6))
        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setProperty("class", "navButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.nav_button_group.addButton(btn, index)
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        self.nav_button_group.idClicked.connect(self._on_nav_button_clicked)
        self.nav_buttons[0].setChecked(True)
        self.nav_buttons[0].setProperty("active", "true")

        layout.addStretch(1)
        return sidebar

    def _on_nav_button_clicked(self, nav_id: int) -> None:
        if nav_id == 3:  # Yön
            self.workspace_tabs.setCurrentWidget(self.direction_workspace)
            self.direction_workspace.setCurrentIndex(0)
        elif nav_id == 4:  # Konum
            self.workspace_tabs.setCurrentWidget(self.direction_workspace)
            self.direction_workspace.setCurrentIndex(1)
        elif nav_id == 5:  # Sistem
            self.workspace_tabs.setCurrentWidget(self.system_workspace)
        elif nav_id == 6 and self.laboratory_mode:
            self.workspace_tabs.setCurrentWidget(self.et_workspace)
        else:
            self.workspace_tabs.setCurrentIndex(nav_id)

    def _on_workspace_tab_changed(self, index: int) -> None:
        current_widget = self.workspace_tabs.widget(index)
        # Determine which sidebar button is active
        active_nav_id = index
        if current_widget == self.direction_workspace:
            active_nav_id = 4 if self.direction_workspace.currentIndex() == 1 else 3
        elif current_widget == self.system_workspace:
            active_nav_id = 5
        elif self.laboratory_mode and current_widget == self.et_workspace:
            active_nav_id = 6

        for idx, btn in enumerate(self.nav_buttons):
            is_active = (idx == active_nav_id)
            btn.setChecked(is_active)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Show selected signal inspector dock only on Arama page
        if hasattr(self, "dock_signal_card"):
            self.dock_signal_card.setVisible(index == 0)

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

    def _setup_dock_widgets(self) -> None:
        """Configure lightweight, floating dock widgets."""
        self.dock_signal_card = QDockWidget("Secili Sinyal", self)
        self.dock_signal_card.setObjectName("dockSignalCard")
        self.dock_signal_card.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.dock_signal_card.setWidget(self.selected_signal_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_signal_card)

        self.dock_metadata = QDockWidget("Kaynak Ayarlari", self)
        self.dock_metadata.setObjectName("dockMetadata")
        self.dock_metadata.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.dock_metadata.setWidget(self._scroll_panel(self._build_metadata_panel(), "dockMetadataScroll"))
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_metadata)
        self.dock_metadata.hide()

        # Gelismis Ayarlar dock — alt panel, spectrum'u itmez
        # advanced_settings widget _build_bottom_controls icinde tanimlanir;  bu dock
        # _build_bottom_controls cagrisinin ardindan _setup_dock_widgets'ta eklenir.
        # Widget henuz yaratilmamis olabilir, bu yuzden lazy ekleme yapiyoruz.
        self.dock_advanced: QDockWidget | None = None  # _late_setup_advanced_dock'ta tamamlanir

        self.dock_widgets = [self.dock_signal_card, self.dock_metadata]

    def _toggle_source_settings(self) -> None:
        self.dock_metadata.setVisible(not self.dock_metadata.isVisible())

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

    def _setup_menu_bar(self) -> None:
        menubar = self.menuBar()

        # Dosya Menüsü
        self.menu_file = menubar.addMenu("Dosya")
        act_open_sigmf = self.menu_file.addAction(TEXT["open_sigmf"])
        act_open_sigmf.setShortcut(QKeySequence("Ctrl+O"))
        act_open_sigmf.triggered.connect(self.open_button.click)

        act_export_wav = self.menu_file.addAction(TEXT["export_wav"])
        act_export_wav.setShortcut(QKeySequence("Ctrl+E"))
        act_export_wav.triggered.connect(self.export_wav_button.click)

        self.menu_file.addSeparator()
        act_quit = self.menu_file.addAction("Çıkış")
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(self.close)

        # Görünüm Menüsü
        self.menu_view = menubar.addMenu("Görünüm")
        for dock in getattr(self, "dock_widgets", []):
            self.menu_view.addAction(dock.toggleViewAction())

        self.menu_view.addSeparator()
        act_reset_layout = self.menu_view.addAction("Varsayılan Düzeni Geri Yükle")
        act_reset_layout.triggered.connect(self.restore_default_layout)

        self.menu_view.addSeparator()
        act_toggle_fs = self.menu_view.addAction("Tam Ekran")
        act_toggle_fs.setShortcut(QKeySequence("F11"))
        act_toggle_fs.setCheckable(True)
        act_toggle_fs.triggered.connect(self._toggle_fullscreen)

        # Görev Menüsü
        self.menu_task = menubar.addMenu("Görev")
        tasks = (
            ("Sinyal Tespiti", 0),
            ("Parametreler", 1),
            ("Dinleme", 2),
            ("Yön", 3),
            ("Konum", 4),
            ("Sistem", 5),
            ("Elektronik Taarruz", 6),
        )
        for label, nav_id in tasks:
            act = self.menu_task.addAction(label)
            act.triggered.connect(lambda _=False, n_id=nav_id: self._on_nav_button_clicked(n_id))

        # Yardım Menüsü
        self.menu_help = menubar.addMenu("Yardım")
        act_about = self.menu_help.addAction("Hakkında")
        act_about.triggered.connect(self._show_about_dialog)

    def _setup_status_bar(self) -> None:
        """Create status labels for internal state tracking and hide the bottom status bar."""
        status = self.statusBar()
        self.status_source_label = QLabel("Kaynak: " + TEXT["no_source"])
        self.status_source_label.setWordWrap(True)
        self.status_state_label = QLabel("Durum: " + TEXT["empty"])
        self.status_state_label.setWordWrap(True)

        self.status_tx_lock_label = QLabel("TX KİLİTLİ · RF TX YOK")
        self.status_tx_lock_label.setObjectName("statusTxLock")
        self.status_tx_lock_label.setWordWrap(True)

        status.addWidget(self.status_source_label, 2)
        status.addWidget(self.status_state_label, 1)
        status.addPermanentWidget(self.status_tx_lock_label)
        status.hide()

    def _save_layout_state(self) -> None:
        settings = QSettings("TEKNOFEST", "OperatorConsole")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

    def _restore_layout_state(self) -> None:
        settings = QSettings("TEKNOFEST", "OperatorConsole")
        geom = settings.value("geometry")
        state = settings.value("windowState")
        if geom is not None and isinstance(geom, (bytes, bytearray)):
            self.restoreGeometry(geom)
        if state is not None and isinstance(state, (bytes, bytearray)):
            self.restoreState(state)

    def closeEvent(self, event: object) -> None:
        self._save_layout_state()
        super().closeEvent(event)  # type: ignore[arg-type]

    def _toggle_fullscreen(self, checked: bool) -> None:
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def _show_about_dialog(self) -> None:
        QMessageBox.about(
            self,
            "Hakkında · TEKNOFEST 2026",
            "TEKNOFEST 2026 Elektronik Harp Operatör Konsolu\n\n"
            "SDR spektrum inceleme, tespit, parametre çıkarımı, "
            "yön bulma ve offline elektronik taarruz arayüzü.",
        )

    def restore_default_layout(self) -> None:
        if hasattr(self, "_default_state") and hasattr(self, "_default_geometry"):
            self.restoreGeometry(self._default_geometry)
            self.restoreState(self._default_state)
        else:
            self.resize(1440, 900)
            if hasattr(self, "dock_signal_card"):
                self.dock_signal_card.show()
            if hasattr(self, "dock_metadata"):
                self.dock_metadata.hide()
        self.workspace_tabs.setCurrentIndex(0)
        LOGGER.info("Arayüz varsayılan düzenine geri yüklendi.")

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
            ("p0_carrier", "Merkez Frekansı"),
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

    def _build_direction_workspace(self) -> QTabWidget:
        """Direction and Map views unified."""
        views = QTabWidget()
        views.setObjectName("directionViews")
        views.addTab(self._build_df_workspace(), "Ölçüm")
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
        self.current_df_source = "REPLAY"
        workspace = QWidget()
        layout = QHBoxLayout(workspace)
        layout.setContentsMargins(8, 8, 8, 8)
        grid = QGridLayout()
        self.df_angle_spin = QDoubleSpinBox()
        self.df_angle_spin.setRange(0.0, 359.9)
        self.df_angle_spin.setSuffix("°")
        self.df_zero_reference_combo = QComboBox()
        self.df_zero_reference_combo.addItem("KUZEY / 0° COĞRAFİ", AntennaReference.NORTH)
        self.df_zero_reference_combo.addItem("MANUEL COĞRAFİ BAŞ", AntennaReference.MANUAL_GEOGRAPHIC)
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
            self.df_mode_combo.addItem("EĞİTİM", "training")
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
            ("Manuel Baş", self.df_manual_reference_spin),
            ("Anten Açısı", self.df_angle_spin),
        )):
            l = QLabel(c_text)
            l.setProperty("class", "propCaption")
            l.setWordWrap(True)
            grid.addWidget(l, row, 0)
            grid.addWidget(w, row, 1)
        panel_layout.addLayout(grid)
        self.df_power_measure_button = QPushButton("GÜÇ ÖLÇ")
        self.df_power_measure_button.setObjectName("primaryButton")
        self.df_import_button = QPushButton("GERÇEK AÇI–GÜÇ KAYDINI YÜKLE")
        self.df_zero_recording_path: Path | None = None
        self.df_ninety_recording_path: Path | None = None
        self.df_pair_result: TwoPointDFResult | None = None
        self.df_pair_reference_azimuth_deg = 0.0
        self.df_add_button = QPushButton("Manuel Gücü Kaydet")
        self.df_clear_button = QPushButton("DF Ölçümlerini Temizle")
        if self.laboratory_mode:
            self.df_training_button = QPushButton("HOST/SYNTHETIC Eğitim Verisini Yükle")
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
            real_data_notice = QLabel("Yön analizi için gerçek açı–güç raporu veya saha ölçümü gereklidir.")
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
            ("relative", "Tahmini Bağıl Yön"),
            ("azimuth", "Coğrafi Azimut"),
            ("power", "Tepe Güç"),
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
        self.df_points_list.setHorizontalHeaderLabels(("Açı", "Coğ. azimut", "Güç", "Kaynak"))
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
        self.map_heading_reference_check = QCheckBox("Manuel baş referansı geçerli")
        self.map_source_combo = QComboBox()
        self.map_source_combo.addItem("AUTO / BİLGİSAYAR", PositionSource.AUTO_PC)
        self.map_source_combo.addItem("MANUEL", "MANUEL")
        if self.laboratory_mode:
            self.map_source_combo.addItem("HOST/SYNTHETIC", "HOST/SYNTHETIC")
        self.map_source_combo.addItem("REPLAY", "REPLAY")
        self.map_source_combo.addItem("LIVE GNSS (rezerve — bağlı değil)", PositionSource.LIVE_GNSS_RESERVED)
        self.map_source_combo.model().item(self.map_source_combo.count() - 1).setFlags(Qt.ItemFlag.NoItemFlags)
        self.map_source_combo.setCurrentIndex(self.map_source_combo.findData("MANUEL"))
        sensor_fields = (
            ("Sensör", self.map_sensor_name),
            ("Enlem", self.map_latitude_spin),
            ("Boylam", self.map_longitude_spin),
            ("Yükseklik", self.map_altitude_spin),
            ("Manuel Baş", self.map_heading_spin),
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
            ("azimuth", "Coğrafi Azimut"),
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
        self.map_live_note = QLabel("LIVE GNSS: rezerve — bağlı değil.")
        self.map_live_note.setProperty("class", "propCaption")
        self.map_live_note.setWordWrap(True)
        panel_layout.addWidget(self.map_live_note)

        self.map_show_sensor_button = QPushButton("Sensörü Haritada Göster")
        self.map_show_df_button = QPushButton("Mevcut DF Sonucunu Göster")
        self.map_clear_lob_button = QPushButton("Yön Çizgisini Temizle")
        panel_layout.addWidget(self.map_show_sensor_button)
        panel_layout.addWidget(self.map_show_df_button)
        panel_layout.addWidget(self.map_clear_lob_button)
        if self.laboratory_mode:
            self.map_training_scenario_combo = QComboBox()
            self.map_training_scenario_combo.addItem("Senaryo A: Baş 0° + bağıl 75° = 75°", (0.0, 75.0))
            self.map_training_scenario_combo.addItem("Senaryo B: Baş 300° + bağıl 75° = 15°", (300.0, 15.0))
            self.map_training_button = QPushButton("Eğitim Senaryosu Yükle")
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
        note_lbl = QLabel("Yön çizgisi doğrultuyu gösterir.")
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
            (
                "et",
                "ET / TX",
                "Offline laboratuvar · RF TX yok" if self.laboratory_mode else "Uygulanmadı · RF TX yok",
            ),
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

    def _build_et_workspace(self) -> QWidget:
        self.et_mission = ETMissionController()
        self.jamming_engine = ContinuousJammingEngine()
        self.deception_engine = AnalogDeceptionEngine()
        self.interleaved_engine = InterleavedJammingEngine()
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
        layout.addWidget(self._build_et_pipeline("interleaved", ("Dinle", "Güç Ölç", "Karar", "Görev", "Koruma")))
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
        self.et_interleaved_spectrum_plot.setTitle("Spektrum", color="#E2EEF8", size="10.5pt")
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
        self.et_interleaved_threshold = QLabel("Aç: 0,12 · Kapat: 0,08")
        self.et_interleaved_threshold.setProperty("class", "propCaption")
        self.et_interleaved_threshold.setWordWrap(True)
        t_lbl = QLabel("Test")
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
        for row, (caption, widget) in enumerate((("Servis", self.et_gnss_service), ("Enlem", self.et_gnss_latitude), ("Boylam", self.et_gnss_longitude), ("UTC", self.et_gnss_time), ("Uydular", self.et_gnss_satellites))):
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

    def _build_controls(self) -> QFrame:
        return self._build_bottom_controls()

    def _build_search_workflow(self) -> QFrame:
        return QFrame()

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

    def show_empty(self) -> None:
        self.source_value.setText(TEXT["no_source"])
        self.listening_source_value.setText(TEXT["no_source"])
        for value in self.metadata_values.values():
            value.setText("—")
        self._refresh_source_summary()
        self.state_value.setText(TEXT["empty"])
        if hasattr(self, "status_source_label"):
            self.status_source_label.setText("Kaynak: " + TEXT["no_source"])
            self.status_state_label.setText("Durum: " + TEXT["empty"])
        self.spectrum_view.clear_all()
        self.clear_detections()
        self.clear_parameters()
        self.clear_listening()
        self.set_source_controls_enabled(False)
        self.hide_notification()

    def set_acquisition_mode(self, mode: str) -> None:
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
            "serial_unassigned": "HackRF bulundu; ED_RX seri kimliği atanmadı. Canlı alım kapalı.",
            "configured_device_missing": "Yapılandırılmış ED_RX seri kimliği bağlı cihazlar arasında bulunamadı.",
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

        tools_ready = state not in {"acceptance_pending", "tools_missing"}
        self.system_status_values["hackrf_tools"].setText("Hazır" if tools_ready else "Kullanılamıyor" if state == "tools_missing" else "Denetlenmedi")
        if state in {"device_ready", "capture_starting", "live", "stopped"}:
            self.system_status_values["hackrf"].setText("Bağlı")
        elif state == "serial_unassigned":
            self.system_status_values["hackrf"].setText("Seri Seçimi Gerekli")
        elif state == "configured_device_missing":
            self.system_status_values["hackrf"].setText("Yapılandırılmış Cihaz Yok")
        else:
            self.system_status_values["hackrf"].setText("Bağlı Değil")
        self.system_status_values["rx"].setText("Aktif" if state == "live" else "Durduruldu")
        self.system_status_values["source"].setText(
            "HackRF Canlı RX" if state == "live" else "HackRF Canlı RX · Etkin değil"
        )
        if state in {"device_missing", "tools_missing", "acceptance_pending"}:
            self.system_status_values["center"].setText("—")
            self.system_status_values["sampling"].setText("—")

    def set_hackrf_configuration(self, serial: str | None) -> None:
        self._configured_hackrf_serial = serial
        self.system_status_values["serial"].setText(serial if serial is not None else "Atanmadı")

    def set_hackrf_runtime(self, *, center_frequency_hz: int, sample_rate_hz: int, dropped_frames: int = 0) -> None:
        self.system_status_values["center"].setText(self._frequency(float(center_frequency_hz)))
        self.system_status_values["sampling"].setText(self._sample_rate(float(sample_rate_hz)))
        self.system_status_values["dropped"].setText(str(dropped_frames))

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
        self.state_value.setText(TEXT["opening_source"])
        if hasattr(self, "status_state_label"):
            self.status_state_label.setText("Durum: " + TEXT["opening_source"])
        self.set_source_controls_enabled(False)
        self.hide_notification()

    def finish_opening(self, *, source_available: bool) -> None:
        self.set_source_controls_enabled(source_available)
        self.state_value.setText(TEXT["ready"] if source_available else TEXT["empty"])
        if hasattr(self, "status_state_label"):
            self.status_state_label.setText("Durum: " + (TEXT["ready"] if source_available else TEXT["empty"]))

    def set_replay_source_badge(self, badge: str) -> None:
        self._replay_source_badge = badge.strip() or "REPLAY"
        if self.metadata_values["center_frequency"].text() != "—":
            self._refresh_source_summary()

    def set_source(self, filename: str, report: ContractReport) -> None:
        self.source_value.setText(Path(filename).name)
        self.listening_source_value.setText(Path(filename).name)
        if hasattr(self, "status_source_label"):
            self.status_source_label.setText(f"Kaynak: {Path(filename).name}")
        self.metadata_values["center_frequency"].setText(self._frequency(report.center_frequency))
        self.metadata_values["sample_rate"].setText(self._sample_rate(report.sample_rate))
        self.metadata_values["datatype"].setText(report.source_datatype or "—")
        self.metadata_values["frame_length"].setText(
            self.locale.toString(report.frame_length) + " örnek"
        )
        self.metadata_values["channel"].setText("1")
        frame_count = report.full_frame_count or 0
        self.frame_spin.setMaximum(max(frame_count, 1))
        self.set_frame_position(0, frame_count)
        self.set_source_controls_enabled(frame_count > 0)
        self._refresh_source_summary()
        self.state_value.setText(TEXT["ready"])
        if hasattr(self, "status_state_label"):
            self.status_state_label.setText("Durum: " + TEXT["ready"])
        self.system_status_values["source"].setText(
            "HACKRF KAYDI / REPLAY · Aktif" if self._replay_source_badge == "HACKRF KAYDI / REPLAY" else "SigMF / Replay · Aktif"
        )
        self.system_status_values["center"].setText(self._frequency(report.center_frequency))
        self.system_status_values["sampling"].setText(self._sample_rate(report.sample_rate))
        self.system_status_values["rx"].setText("Replay aktif")
        self.system_status_values["processing"].setText("HOST REFERENCE · Aktif")
        self.system_status_values["hackrf"].setText("Bağlı Değil · Replay için kullanılmıyor")
        self.system_status_values["zedboard"].setText("Bağlı Değil · Replay için kullanılmıyor")
        self.system_status_values["fpga"].setText("Fiziksel olarak doğrulanmadı")
        self.system_status_values["petalinux"].setText("Fiziksel ARM çalıştırması doğrulanmadı")

    def set_frame_position(self, zero_based_index: int, frame_count: int) -> None:
        blocker = QSignalBlocker(self.frame_spin)
        self.frame_spin.setValue(zero_based_index + 1)
        del blocker
        self.metadata_values["frame_position"].setText(
            f"{self.locale.toString(zero_based_index + 1)} / {self.locale.toString(frame_count)}"
        )
        self._refresh_source_summary()

    def _refresh_source_summary(self) -> None:
        values = self.metadata_values
        if values["center_frequency"].text() == "—":
            self.source_summary.setText("Kaynak seçilmedi")
            return
        self.source_summary.setText(
            f"{self._replay_source_badge}\n{values['center_frequency'].text()} · {values['sample_rate'].text()}\n"
            f"{values['datatype'].text()} · Çerçeve {values['frame_position'].text()}"
        )

    def set_state(self, state: str) -> None:
        self.state_value.setText(TEXT[state])
        if hasattr(self, "status_state_label"):
            self.status_state_label.setText("Durum: " + TEXT.get(state, state))

    def set_profile_summary(self, summary: str, *, validated: bool) -> None:
        suffix = TEXT["validated_envelope"] if validated else TEXT["parameter_error"]
        self.profile_value.setText(f"{summary}\n{suffix}")
        self.profile_value.setToolTip(f"{summary}\n{suffix}")

    def clear_detections(self) -> None:
        self.detection_state.setText(TEXT["no_detection"])
        self.detection_list.clear()
        self.detection_note.setText("")
        # Reset diff cache so next real frame rebuilds unconditionally.
        self._prev_event_snapshot: dict[int, str] = {}
        self._prev_selected_id: int | None = None
        if hasattr(self, "signal_list_title"):
            self.signal_list_title.setText("Sinyaller")
        if hasattr(self, "selected_signal_badge"):
            self.selected_signal_badge.setText("Sinyal seçilmedi")
            self.selected_signal_badge.setProperty("state", "empty")
            self.card_freq_val.setText("—")
            self.card_bw_val.setText("—")
            self.card_power_val.setText("—")
            self.card_snr_val.setText("—")
            self.card_domain_val.setText("—")
            self.card_bearing_val.setText("—")
            self.card_details_text.setText("Ayrıntı görmek için sinyal seçin.")

    def clear_parameters(self) -> None:
        self.measurement_state.setText(TEXT["measurement_not_started"])
        self.parameter_state.setText(TEXT["no_parameter"])
        for value in self.parameter_values.values():
            value.setText(TEXT["not_validated"])
        self.quality_value.setText(TEXT["quality_not_available"])
        if hasattr(self, "analysis_freq_val"):
            self.analysis_freq_val.setText("—")
            self.analysis_event_value.setText(TEXT["select_confirmed_event"])

    def set_parameter_result(self, result: ParameterFrameResult | None) -> None:
        del result

    def set_detection_result(
        self,
        result: DetectionFrameResult,
        *,
        selected_event_id: int | None = None,
    ) -> None:
        active = list(result.active_events)
        confirmed = [event for event in active if event.state == "confirmed"]
        tentative = [event for event in active if event.state == "tentative"]
        total_count = len(confirmed) + len(tentative)
        if hasattr(self, "signal_list_title"):
            self.signal_list_title.setText(f"Sinyaller ({total_count})" if total_count else "Sinyaller")

        if confirmed or tentative:
            self.detection_state.setText(
                f"{len(confirmed)} {TEXT['confirmed'].casefold()} · "
                f"{len(tentative)} {TEXT['tentative'].casefold()}"
            )
        else:
            self.detection_state.setText(TEXT["no_detection"])

        ordered = sorted(confirmed, key=self._event_sort_key) + sorted(
            tentative, key=self._event_sort_key
        )
        visible = ordered[:12]

        # --- Diff guard: skip costly clear+rebuild if nothing changed ---------
        new_snapshot = {
            int(event.event_id): self._event_text(event)
            for event in visible
        }
        if not hasattr(self, "_prev_event_snapshot"):
            self._prev_event_snapshot: dict[int, str] = {}
            self._prev_selected_id: int | None = None
        if new_snapshot == self._prev_event_snapshot and selected_event_id == self._prev_selected_id:
            # Only refresh the signal card in case real-time values changed.
            self._update_selected_signal_card(ordered[0] if ordered else None)
            return
        self._prev_event_snapshot = new_snapshot
        self._prev_selected_id = selected_event_id
        # ---------------------------------------------------------------------

        blocker = QSignalBlocker(self.detection_list)
        self.detection_list.clear()
        selected_item: QListWidgetItem | None = None
        for event in visible:
            item = QListWidgetItem(self._event_text(event))
            item.setToolTip(self._event_tooltip(event))
            item.setData(Qt.ItemDataRole.UserRole, event.event_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, event.state)
            item.setForeground(QColor("#10B981") if event.state == "confirmed" else QColor("#F59E0B"))
            if event.state != "confirmed" or not event.observed_this_frame:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            elif selected_event_id == int(event.event_id):
                selected_item = item
            item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, self._event_tooltip(event))
            self.detection_list.addItem(item)
        if selected_item is not None:
            selected_item.setSelected(True)
            self.detection_list.setCurrentItem(selected_item)
            self._update_selected_signal_card(ordered[0] if ordered else None)
        elif ordered:
            self._update_selected_signal_card(ordered[0])
        del blocker
        notes: list[str] = []
        hidden = max(0, len(ordered) - len(visible))
        if hidden:
            notes.append(f"+{hidden} sinyal")
        self.detection_note.setText(" · ".join(notes))

    # ── helper ──────────────────────────────────────────────────────────────
    @staticmethod
    def _set_label_if_changed(label: "QLabel", text: str) -> None:
        """Only call setText when value actually changes (eliminates redundant repaints)."""
        if label.text() != text:
            label.setText(text)

    def _update_selected_signal_card(self, event: DetectionEvent | None) -> None:
        if not hasattr(self, "card_freq_val") or event is None:
            return
        state_label = TEXT.get(event.state, event.state)
        self._set_label_if_changed(self.selected_signal_badge, f"{state_label}")
        self.selected_signal_badge.setProperty("state", "active")
        self._set_label_if_changed(
            self.card_freq_val, f"{event.region.peak_frequency_hz / 1_000_000.0:.3f} MHz"
        )
        bw_khz = (event.region.end_frequency_hz - event.region.start_frequency_hz) / 1000.0
        self._set_label_if_changed(self.card_bw_val, f"{max(bw_khz, 0.1):.1f} kHz")
        self._set_label_if_changed(self.card_power_val, f"{event.region.peak_power:.1f} dBFS")
        self._set_label_if_changed(self.card_snr_val, f"+{event.region.peak_to_noise_db:.1f} dB")
        self._set_label_if_changed(
            self.card_domain_val, "Izleniyor" if event.state == "tentative" else "Dogrulandi"
        )
        self.card_details_text.setText(
            f"Frekans: {event.region.start_frequency_hz/1e6:.3f} - {event.region.end_frequency_hz/1e6:.3f} MHz\n"
            f"Bolge: {event.region.start_bin}..{event.region.end_bin}\n"
            f"Cerceve: #{event.first_frame+1}-#{event.last_seen_frame+1} ({event.seen_count} kez)"
        )

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
        self.listening_values["carrier"].setText(self._frequency(event.region.peak_frequency_hz))
        self.listening_values["bandwidth"].setText(
            self.locale.toString(self.listen_bandwidth_spin.value(), "f", 1) + " kHz"
        )
        self.listening_values["backend"].setText("Replay")

    def clear_listening(self) -> None:
        self.listening_event_value.setText(TEXT["listening_select_event"])
        self.listening_state.setText(TEXT["listening_not_prepared"])
        self.prepare_listening_button.setEnabled(False)
        self.play_audio_button.setEnabled(False)
        self.pause_audio_button.setEnabled(False)
        self.stop_audio_button.setEnabled(False)
        self.export_wav_button.setEnabled(False)
        if hasattr(self, "listening_values"):
            for value in self.listening_values.values():
                value.setText("—")
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

    def set_listening_result(
        self,
        result: object,
        *,
        audio_available: bool,
        source_sample_rate_hz: float,
        carrier_frequency_hz: float,
        channel_bandwidth_hz: float,
        backend: str,
    ) -> None:
        tone = float(getattr(result, "dominant_tone_hz"))
        audio = np.asarray(getattr(result, "audio"), dtype=np.float64)
        peak = float(np.max(np.abs(audio), initial=0.0))
        rms = float(np.sqrt(np.mean(np.square(audio))))
        sample_rate = int(getattr(result, "sample_rate_hz"))
        mode = str(getattr(result, "mode")).upper()
        duration = audio.size / sample_rate
        self.listening_state.setText(f"Hazır · {self.locale.toString(tone, 'f', 1)} Hz")
        self.listening_values["mode"].setText(mode)
        self.listening_values["carrier"].setText(self._frequency(carrier_frequency_hz))
        self.listening_values["bandwidth"].setText(
            self.locale.toString(channel_bandwidth_hz / 1000.0, "f", 1) + " kHz"
        )
        self.listening_values["iq_rate"].setText(self._sample_rate(source_sample_rate_hz))
        self.listening_values["audio_rate"].setText(
            f"{self.locale.toString(sample_rate / 1000.0, 'f', 1)} kHz mono PCM16"
        )
        self.listening_values["duration"].setText(self.locale.toString(duration, "f", 2) + " s")
        rf_power = float(getattr(result, "rf_power_dbfs", float("nan")))
        self.listening_values["levels"].setText(
            self.locale.toString(rf_power, "f", 1) + " dBFS"
        )
        self.listening_values["backend"].setText(backend)
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
        self.measure_button.setText(TEXT["start_measurement"])

    def set_measurement_busy(self) -> None:
        self.measurement_state.setText("Ölçülüyor…")
        self.parameter_state.setText("Sonuç bekleniyor")
        self.measure_button.setText("Ölçülüyor…")
        self.measure_button.setEnabled(False)

    def set_measurement_complete(self) -> None:
        self._measurement_run_count += 1
        self.measurement_state.setText(f"● Ölçüm tamamlandı · #{self._measurement_run_count}")
        self.parameter_state.setText(f"Sonuçlar güncellendi · Ölçüm #{self._measurement_run_count}")
        self.measure_button.setText(TEXT["start_measurement"])
        self.measure_button.setEnabled(True)

    def show_measurement_rejected(self, message: str) -> None:
        self.measurement_state.setText(message)
        self.parameter_state.setText("Ölçüm başlatılmadı")
        self.measure_button.setText(TEXT["start_measurement"])
        self.show_warning(message)

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
        self.parameter_state.setText("Sonuçlar güncellendi")
        self.measure_button.setText(TEXT["start_measurement"])
        self.measure_button.setEnabled(True)

    def set_p0_parameter_result(self, result: P0ParameterResult | None) -> None:
        if result is None:
            for key in (
                "p0_detection", "p0_carrier", "p0_bandwidth", "p0_lower", "p0_upper",
                "p0_bandwidth_method", "p0_coarse_span", "p0_peak_power", "p0_power",
                "p0_snr", "p0_domain", "p0_region", "p0_backend", "p0_source",
                "emission_center", "carrier_line", "lower_edge", "upper_edge", "bandwidth",
                "peak_power", "channel_power", "domain",
            ):
                self.parameter_values[key].setText(TEXT["not_validated"])
            self.quality_value.setText(TEXT["quality_not_available"])
            if hasattr(self, "analysis_freq_val"):
                self.analysis_freq_val.setText("—")
                self.analysis_event_value.setText("Sinyal seçilmedi")
            return
        locale = self.locale
        status_str = "● Doğrulandı" if result.confirmed else "İzleniyor"
        self.parameter_values["p0_detection"].setText(status_str)
        self.parameter_values["p0_carrier"].setText(self._frequency(result.carrier_frequency_hz))
        self.parameter_values["p0_bandwidth"].setText(locale.toString(result.bandwidth_hz / 1000.0, "f", 2) + " kHz")
        self.parameter_values["p0_lower"].setText(self._frequency(result.lower_frequency_hz))
        self.parameter_values["p0_upper"].setText(self._frequency(result.upper_frequency_hz))
        method_text = "Eşik sınırları" if result.bandwidth_method == "threshold_edges" else "%98 güç"
        self.parameter_values["p0_bandwidth_method"].setText(method_text)
        self.parameter_values["p0_coarse_span"].setText(
            locale.toString(result.coarse_candidate_bandwidth_hz / 1000.0, "f", 2) + " kHz"
        )
        self.parameter_values["p0_peak_power"].setText(locale.toString(result.peak_power_dbfs_per_bin, "f", 1) + " dBFS/bin · " + result.calibration_state)
        self.parameter_values["p0_power"].setText(locale.toString(result.channel_power_dbfs, "f", 1) + " dBFS · " + result.calibration_state)
        self.parameter_values["p0_snr"].setText(locale.toString(result.snr_db, "f", 1) + " dB")
        self.parameter_values["p0_domain"].setText(result.signal_domain)
        self.parameter_values["p0_region"].setText(f"{result.candidate.start_bin}–{result.candidate.end_bin}")
        self.parameter_values["p0_backend"].setText(result.backend)
        self.parameter_values["p0_source"].setText(result.provenance)
        self.parameter_values["emission_center"].setText(self._frequency(result.carrier_frequency_hz))
        self.parameter_values["carrier_line"].setText(TEXT["carrier_line_not_separate"])
        self.parameter_values["lower_edge"].setText(self._frequency(result.lower_frequency_hz))
        self.parameter_values["upper_edge"].setText(self._frequency(result.upper_frequency_hz))
        self.parameter_values["bandwidth"].setText(locale.toString(result.bandwidth_hz / 1000.0, "f", 2) + " kHz")
        self.parameter_values["peak_power"].setText(locale.toString(result.peak_power_dbfs_per_bin, "f", 1) + " dBFS/bin")
        self.parameter_values["channel_power"].setText(locale.toString(result.channel_power_dbfs, "f", 1) + " dBFS")
        self.parameter_values["domain"].setText(result.signal_domain)
        self.quality_value.setText(" · ".join(result.classification_reasons))
        self.parameter_state.setText("Sonuçlar güncellendi")

        if hasattr(self, "analysis_freq_val"):
            self.analysis_freq_val.setText(f"{result.carrier_frequency_hz / 1_000_000.0:.3f} MHz")
            self.analysis_event_value.setText(status_str)

        if hasattr(self, "card_freq_val"):
            self.card_freq_val.setText(f"{result.carrier_frequency_hz / 1_000_000.0:.3f} MHz")
            self.card_bw_val.setText(f"{result.bandwidth_hz / 1000.0:.2f} kHz")
            self.card_power_val.setText(f"{result.peak_power_dbfs_per_bin:.1f} dBFS")
            self.card_snr_val.setText(f"+{result.snr_db:.1f} dB")
            self.card_domain_val.setText(result.signal_domain)
            self.selected_signal_badge.setText(status_str)
            self.selected_signal_badge.setProperty("state", "active")
            self.card_details_text.setText(
                f"Frekans: {result.lower_frequency_hz/1e6:.3f} - {result.upper_frequency_hz/1e6:.3f} MHz\n"
                f"Yöntem: {method_text}\n"
                f"Kaynak: {result.provenance}"
            )

    def set_p0_detection_summary(self, result: P0ParameterResult) -> None:
        self.detection_list.clear()
        state = "Hazır" if result.confirmed else "İzleniyor"
        freq_str = f"{result.carrier_frequency_hz / 1_000_000.0:.3f} MHz"
        snr_str = f"+{result.snr_db:.1f} dB"
        item = QListWidgetItem(f"{freq_str}    {snr_str}    {state}")
        item.setToolTip(
            f"Frekans: {result.carrier_frequency_hz/1e6:.3f} MHz\n"
            f"Bant: {result.bandwidth_hz/1000.0:.2f} kHz\n"
            f"Kaynak: {result.provenance}"
        )
        self.detection_list.addItem(item)
        self.detection_state.setText(f"1 {state.casefold()}")
        if hasattr(self, "signal_list_title"):
            self.signal_list_title.setText("Sinyaller (1)")

    def set_p0_search_engine(self, engine: P0SearchEngine | None) -> None:
        self.p0_search_engine = engine
        self.last_search_result = None
        self.search_start_button.setEnabled(engine is not None)
        self.active_search_mode_label.setText("● Hazır" if engine is not None else "● Bekliyor")

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
        return sources[0] if len(sources) == 1 else "Karma"

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
            measurement.source,
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
        self.current_df_source = "HOST/SYNTHETIC"
        error = ManualAmplitudeDF.angular_error_deg(estimate.estimated_angle_deg, scene.truth_bearing_deg)
        self.df_result_label.setText(f"EĞİTİM / ALGORİTMA TESTİ · hata {error:.1f}° · {estimate.status}")
        self._update_df_plot_and_summary()

    def _clear_df_measurements(self) -> None:
        self.df_model.clear()
        self.current_df_estimate = None
        self.current_df_source = "REPLAY"
        self.df_points_list.setRowCount(0)
        self.df_result_label.setText("Ölçüm bekleniyor")
        self._update_df_plot_and_summary()

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

    def _peak_df_measurement(self, estimate: DFEstimate) -> DFMeasurement | None:
        return next(
            (item for item in self.df_model.measurements if item.angle_deg == estimate.raw_maximum_angle_deg),
            None,
        )

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
        self.map_status_label.setText("Yön çizgisi temizlendi.")
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
            f"Eğitim · HOST/SYNTHETIC TEST · {TEXT['synthetic_direction_notice']} · {float(expected_azimuth):.1f}° · "
            + TEXT["direction_line_showing"]
        )

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
            measured = float(getattr(current, "measured_band_power"))
            decision = str(getattr(current, "decision"))
            state = str(timeline[(step - 1) % len(timeline)]).replace("GUARD", "KORUMA")
            self._set_et_pipeline_progress("interleaved", {"DİNLE": 0, "KARAR": 2, "GÖREV": 3, "KORUMA": 4}.get(state, 0))
            self.et_interleaved_values["state"].setText(state)
            self.et_interleaved_values["energy"].setText(f"{measured:.4f}")
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
            expected = 0 if scenario == "absent" else 1
            validation = "PASS" if (result.task_activation_count == 0 if expected == 0 else result.task_activation_count >= expected) else "FAIL"
            task_result = new_task_result(
                task_type="interleaved_jamming",
                mode=mode.value,
                source="ANALİZ GİRİŞİ",
                duration=result.duration_seconds,
                waveform_type="ANALİZ",
                sample_rate=result.sample_rate_hz,
                sample_count=result.samples.size,
                normalization_status="UYGULANMAZ",
                validation_status=validation,
                details={
                    "scenario": result.scenario,
                    "task_activation_count": result.task_activation_count,
                    "last_band_power": last_window.measured_band_power,
                    "last_decision": last_window.decision,
                    "state_sequence": result.timeline,
                },
            )
            self.et_mission.complete(detail=f"interleaved/{scenario} tamamlandı")
            self.et_result_values["detail"].setText(f"Dizi: DİNLE → KARAR → GÖREV")
            self._start_et_animation(
                task_key="interleaved",
                samples=result.samples,
                sample_rate_hz=result.sample_rate_hz,
                task_result=task_result,
                metric=f"{result.task_activation_count} çevrim · {last_window.decision}",
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
                    "waveform_source_contract_valid": validation.waveform_source_contract_valid,
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
        power = np.asarray([float(getattr(item, "measured_band_power")) for item in windows], dtype=np.float64)
        indices = np.arange(power.size, dtype=np.float64) + 1.0
        self.et_interleaved_timeline_curve.setData(indices, power)
        self.et_interleaved_threshold_curve.setData(indices, np.full(power.size, 0.12, dtype=np.float64))
        active_indices = np.asarray(
            [index for index, item in enumerate(windows, start=1) if bool(getattr(item, "task_active"))], dtype=np.float64
        )
        self.et_interleaved_task_marker.setData(active_indices, power[active_indices.astype(np.int64) - 1] if active_indices.size else np.array([]))
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

    def _event_text(self, event: DetectionEvent) -> str:
        label = TEXT[event.state]
        peak_mhz = self.locale.toString(event.region.peak_frequency_hz / 1_000_000.0, "f", 3)
        delta = self.locale.toString(event.region.peak_to_noise_db, "f", 1)
        return f"{peak_mhz} MHz    +{delta} dB    {label}"

    def _event_tooltip(self, event: DetectionEvent) -> str:
        start = self.locale.toString(event.region.start_frequency_hz / 1_000_000.0, "f", 3)
        end = self.locale.toString(event.region.end_frequency_hz / 1_000_000.0, "f", 3)
        return (
            f"Frekans: {start}–{end} MHz\n"
            f"Çerçeve: #{event.first_frame + 1}–#{event.last_seen_frame + 1}\n"
            f"Görülme: {event.seen_count}"
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
