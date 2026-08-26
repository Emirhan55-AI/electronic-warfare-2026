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
extra_args = --quiet --noinclude-qt-translations=True --nofollow-import-to=platforms.acquisition.mock --nofollow-import-to=app.operator_console.laboratory --nofollow-import-to=algorithms.p0.df_fixtures --include-data-files=../../profiles/phase04f5/operation-default.json=profiles/phase04f5/operation-default.json --include-data-files=../../datasets/fixtures/phase04f1/domain-model.json=datasets/fixtures/phase04f1/domain-model.json --include-data-files=../../datasets/fixtures/phase04f2/domain-model-v3.json=datasets/fixtures/phase04f2/domain-model-v3.json --include-data-files=../../datasets/fixtures/phase04f4/domain-model-v5.json=datasets/fixtures/phase04f4/domain-model-v5.json
