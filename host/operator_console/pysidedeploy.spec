[app]
title = TEKNOFEST Elektronik Harp Operatör Konsolu
project_dir = .
input_file = __main__.py
exec_directory = ../../dist/operator-console

[python]
python_path =
packages = nuitka==4.0,ordered_set,zstandard

[qt]
qml_files =
excluded_qml_plugins = QtQuick,QtQuick3D,QtCharts,QtWebEngine,QtTest,QtSensors
modules = Core,Gui,Widgets
plugins = platforms,imageformats,styles

[nuitka]
mode = standalone
extra_args = --quiet --noinclude-qt-translations=True --nofollow-import-to=host.acquisition.mock --nofollow-import-to=host.operator_console.laboratory --nofollow-import-to=reference.et --nofollow-import-to=reference.p0.df_fixtures
