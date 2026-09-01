"""Operator application main window."""

from __future__ import annotations

import logging

from PySide6.QtCore import QLocale, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from algorithms.p0.search import P0SearchEngine, SearchExecutionResult

from .pc_location import PCPositionProvider
from .ui_text import TEXT

from ._mixin_navigation import NavigationMixin
from ._mixin_search import SearchWorkspaceMixin
from ._mixin_analysis import AnalysisWorkspaceMixin
from ._mixin_listening import ListeningWorkspaceMixin
from ._mixin_df import DFWorkspaceMixin, load_laboratory_df_dependencies
from ._mixin_map import MapWorkspaceMixin
from ._mixin_controls import ControlsMixin
from ._mixin_state import StateMixin
from ._mixin_et import ETWorkspaceMixin, load_laboratory_et_dependencies


LOGGER = logging.getLogger(__name__)


def _source_display_name(value: str) -> str:
    return {
        "REPLAY": "KAYIT OYNATMA",
        "HOST/SYNTHETIC": "YAZILIM REFERANS VERİSİ",
    }.get(value, value)


def _load_laboratory_dependencies() -> None:
    """Load validation-only models only for the explicit laboratory entry point."""

    load_laboratory_et_dependencies()
    load_laboratory_df_dependencies()


class MainWindow(
    SearchWorkspaceMixin,
    AnalysisWorkspaceMixin,
    ListeningWorkspaceMixin,
    DFWorkspaceMixin,
    MapWorkspaceMixin,
    ETWorkspaceMixin,
    ControlsMixin,
    StateMixin,
    NavigationMixin,
    QMainWindow,
):
    """RF spectrum, detection, parameter and direction-finding console."""

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
        self._replay_source_badge = "KAYIT OYNATMA"

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
        self.workspace_tabs.addTab(self.direction_workspace, "Yön Bulma")

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
