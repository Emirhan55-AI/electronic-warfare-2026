"""Release entry point for the Qt Quick operator console."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import sys

from PySide6.QtCore import QLocale, QTimer, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from .quick_view_model import OperatorViewModel


QML_PATH = Path(__file__).with_name("qml") / "Main.qml"


def _ui_font() -> QFont:
    family = "Segoe UI"
    if not QFontDatabase.hasFamily(family):
        windows_directory = Path(os.environ.get("WINDIR", "C:/Windows"))
        for filename in ("segoeui.ttf", "arial.ttf"):
            font_path = windows_directory / "Fonts" / filename
            if not font_path.is_file():
                continue
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id >= 0:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    family = families[0]
                    break
    return QFont(family, 10)


def build_quick_application(
    argv: list[str] | None = None,
    *,
    acquisition_backend: object | None = None,
    source_factory: object | None = None,
) -> tuple[QGuiApplication, QQmlApplicationEngine, OperatorViewModel]:
    app = QGuiApplication.instance() or QGuiApplication(argv or [])
    app.setApplicationName("Elektronik Harp Operatör Konsolu")
    app.setOrganizationName("TEKNOFEST 2026 Elektronik Harp")
    app.setFont(_ui_font())
    QLocale.setDefault(QLocale(QLocale.Language.Turkish, QLocale.Country.Turkey))

    view_model_kwargs: dict[str, object] = {}
    if acquisition_backend is not None:
        view_model_kwargs["acquisition_backend"] = acquisition_backend
    if source_factory is not None:
        view_model_kwargs["source_factory"] = source_factory
    view_model = OperatorViewModel(**view_model_kwargs)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("operatorViewModel", view_model)
    engine.load(QUrl.fromLocalFile(str(QML_PATH)))
    if not engine.rootObjects():
        view_model.shutdown()
        raise RuntimeError("Operatör QML arayüzü yüklenemedi.")
    app.aboutToQuit.connect(view_model.shutdown)
    return app, engine, view_model


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Elektronik Harp operatör uygulaması")
    parser.add_argument("--smoke-test", action="store_true", help="pencereyi kısa süre açıp kapat")
    args = parser.parse_args(argv)
    app, _, _ = build_quick_application([sys.argv[0]])
    if args.smoke_test:
        QTimer.singleShot(350, app.quit)
    return app.exec()
