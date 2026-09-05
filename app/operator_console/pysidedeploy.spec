[app]
title = BÂZ
project_dir = .
input_file = __main__.py
exec_directory = ../../dist/operator-console
icon = assets/baz-logo.ico

[python]
python_path =
packages = nuitka==4.0,ordered_set,zstandard

[qt]
qml_files = qml/Main.qml,qml/StartupIntro.qml,qml/RxSurveyView.qml,qml/ETWorkspace.qml,qml/HackRFControls.qml,qml/BazTheme.qml,qml/Panel.qml,qml/SectionTitle.qml,qml/PrimaryButton.qml,qml/QuietButton.qml,qml/AppCombo.qml,qml/AppField.qml,qml/StateBadge.qml,qml/EtChart.qml,qml/NavIcon.qml
excluded_qml_plugins = QtQuick3D,QtCharts,QtWebEngine,QtTest,QtSensors
modules = Core,Gui,Multimedia,Positioning,Qml,Quick,WebEngineCore,WebEngineWidgets,Widgets
plugins = platforms,imageformats,styles

[nuitka]
mode = standalone
extra_args = --quiet --noinclude-qt-translations --nofollow-import-to=platforms.acquisition.mock --nofollow-import-to=app.operator_console.laboratory --nofollow-import-to=algorithms.p0.df_fixtures --include-data-files=assets/baz-logo-intro.png=app/operator_console/assets/baz-logo-intro.png --include-data-files=assets/baz-logo-glow.png=app/operator_console/assets/baz-logo-glow.png --include-data-files=assets/baz-logo-metal-red.png=app/operator_console/assets/baz-logo-metal-red.png --include-data-files=../../profiles/phase04f5/operation-default.json=profiles/phase04f5/operation-default.json --include-data-files=../../datasets/fixtures/phase04f1/domain-model.json=datasets/fixtures/phase04f1/domain-model.json --include-data-files=../../datasets/fixtures/phase04f2/domain-model-v3.json=datasets/fixtures/phase04f2/domain-model-v3.json --include-data-files=../../datasets/fixtures/phase04f4/domain-model-v5.json=datasets/fixtures/phase04f4/domain-model-v5.json --include-data-files=../../build/native/p0_channelizer/Release/p0_channelizer.dll=algorithms/p0/native/bin/p0_channelizer.dll
