"""Display the preserved survey with current presentation; no acquisition."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.operator_console.quick_application import build_quick_application
from app.operator_console.rx_survey import SurveyConfig, SurveyWindow, SurveyUpdate

app, engine, view = build_quick_application(['survey-history'], auto_probe_hackrf=False)
root = engine.rootObjects()[0]
root.setTitle('BÂZ · Kayıtlı tarama incelemesi')
view.setSourceMode('hackrf')
controller = view.survey
audit = Path(__file__).with_name('1de7f3a9efe041398957c8784acd78e2.jsonl')
records = [json.loads(line) for line in audit.read_text(encoding='utf8').splitlines()]
controller._config = SurveyConfig(**records[0]['config'])
controller._windows = controller._config.windows()
controller._states = [0] * len(controller._windows)
for record in records:
    if record['type'] == 'window_complete':
        controller._update(SurveyUpdate(SurveyWindow(**record['window']), 'complete', 0,
            tuple(record['observations']), window_metrics=record['window_metrics'],
            timing=record.get('timing')))
controller._elapsed = records[-1]['elapsed_seconds']
controller._state = 'Kayıtlı tur · Durduruldu'
controller._audit = str(audit)
controller.changed.emit()
root.setProperty('rfSearchMode', True)
from PySide6.QtCore import QObject
root.findChild(QObject, 'surveyLnaInput').setProperty('currentIndex', controller._config.lna_gain_db // 8)
root.findChild(QObject, 'surveyVgaInput').setProperty('currentIndex', controller._config.vga_gain_db // 2)
root.showMaximized()
groups = controller.observationGroups
rows = controller._grouped_model._rows
Path(__file__).with_name('presentation-review.json').write_text(json.dumps({
    'groups': groups,
    'visible_frequencies_mhz': [row['frequencyHz'] / 1e6 for row in rows],
    'visible_messages': [{'frequency_mhz': row['frequencyHz'] / 1e6,
                          'message': row.get('statusText', '')}
                         for row in rows],
    'source': str(audit), 'new_acquisition': False,
}, ensure_ascii=False, indent=2), encoding='utf8')
if '--snapshot' in sys.argv:
    from PySide6.QtCore import QTimer
    def snapshot():
        root.grabWindow().save(str(Path(__file__).with_name('grouped-list.png')))
        view.shutdown()
        app.quit()
    QTimer.singleShot(1500, snapshot)
sys.exit(app.exec())
