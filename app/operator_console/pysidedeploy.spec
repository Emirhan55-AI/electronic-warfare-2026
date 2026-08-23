[app]
title = TEKNOFEST Elektronik Harp Operatör Konsolu
project_dir = .
input_file = __main__.py
exec_directory = ../../dist/operator-console

[python]
python_path =
packages = nuitka==4.0,ordered_set,zstandard

[qt]
qml_files = qml/Main.qml
excluded_qml_plugins = QtQuick3D,QtCharts,QtWebEngine,QtTest,QtSensors
modules = Core,Gui,Qml,Quick,QuickControls2,Widgets
plugins = platforms,imageformats,styles

[nuitka]
mode = standalone
extra_args = --quiet --noinclude-qt-translations=True --nofollow-import-to=platforms.acquisition.mock --nofollow-import-to=app.operator_console.laboratory --nofollow-import-to=algorithms.et --nofollow-import-to=algorithms.p0.df_fixtures
