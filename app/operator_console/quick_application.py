"""Release entry point for the Qt Quick operator console."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import sys

from PySide6.QtCore import QLocale, QLockFile, QStandardPaths, QTimer, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

from .quick_view_model import OperatorViewModel
from .spectral_display import SpectrumTrace, WaterfallImage


QML_PATH = Path(__file__).with_name("qml") / "Main.qml"
_SPECTRAL_TYPES_REGISTERED = False


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
    auto_probe_hackrf: bool = False,
    show_startup_intro: bool = False,
) -> tuple[QGuiApplication, QQmlApplicationEngine, OperatorViewModel]:
    global _SPECTRAL_TYPES_REGISTERED
    if not _SPECTRAL_TYPES_REGISTERED:
        qmlRegisterType(SpectrumTrace, "Teknofest.Display", 1, 0, "SpectrumTrace")
        qmlRegisterType(WaterfallImage, "Teknofest.Display", 1, 0, "WaterfallImage")
        _SPECTRAL_TYPES_REGISTERED = True
    app = QGuiApplication.instance() or QGuiApplication(argv or [])
    app.setApplicationName("BÂZ")
    app.setOrganizationName("TEKNOFEST 2026 Elektronik Harp")
    app.setWindowIcon(QIcon(str(Path(__file__).with_name("assets") / "baz-logo.ico")))
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
    engine.rootContext().setContextProperty("startupIntroRequested", bool(show_startup_intro))
    engine.load(QUrl.fromLocalFile(str(QML_PATH)))
    if not engine.rootObjects():
        view_model.shutdown()
        raise RuntimeError("Operatör QML arayüzü yüklenemedi.")
    # QML's ``visible: true`` is normally sufficient, but explicitly showing
    # and activating the root window prevents a silent background launch on
    # Windows desktop sessions.
    root_window = engine.rootObjects()[0]
    root_window.setProperty("visible", True)
    root_window.show()
    root_window.raise_()
    root_window.requestActivate()
    if auto_probe_hackrf:
        QTimer.singleShot(0, view_model.probeHackrf)
    app.aboutToQuit.connect(view_model.shutdown)
    return app, engine, view_model


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Elektronik Harp operatör uygulaması")
    parser.add_argument("--smoke-test", action="store_true", help="pencereyi kısa süre açıp kapat")
    parser.add_argument("--no-intro", action="store_true", help="açılış görselini gösterme")
    args = parser.parse_args(argv)
    lock_path = Path(QStandardPaths.writableLocation(QStandardPaths.TempLocation)) / "baz-operator-console.lock"
    instance_lock = QLockFile(str(lock_path))
    instance_lock.setStaleLockTime(0)
    if not instance_lock.tryLock(100):
        logging.warning("BÂZ zaten açık; ikinci uygulama örneği başlatılmadı.")
        return 0
    # Keep the QML engine and view model alive for the full event loop. Using
    # the same throwaway name for both drops the engine reference immediately,
    # which destroys the root window before it reaches the desktop.
    app, engine, view_model = build_quick_application(
        [sys.argv[0]],
        auto_probe_hackrf=False,
        show_startup_intro=not args.no_intro,
    )
    if args.smoke_test:
        QTimer.singleShot(350, app.quit)
    exit_code = app.exec()
    _ = (engine, view_model, instance_lock)
    return exit_code
