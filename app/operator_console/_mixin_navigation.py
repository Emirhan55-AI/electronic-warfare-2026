"""Navigasyon, menü ve layout yönetimi mixin'i."""

from __future__ import annotations

import logging
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QButtonGroup,
    QDockWidget,
    QFrame,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from .ui_text import TEXT

LOGGER = logging.getLogger(__name__)


class NavigationMixin:
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
            ("Yön Bulma", 3),
            ("Konum", 4),
            ("Sistem", 5),
        ]
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

        for idx, btn in enumerate(self.nav_buttons):
            is_active = (idx == active_nav_id)
            btn.setChecked(is_active)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Show selected signal inspector dock only on Arama page
        if hasattr(self, "dock_signal_card"):
            self.dock_signal_card.setVisible(index == 0)

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

        status.addWidget(self.status_source_label, 2)
        status.addWidget(self.status_state_label, 1)
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
            "sinyal dinleme ve yön bulma arayüzü.",
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
