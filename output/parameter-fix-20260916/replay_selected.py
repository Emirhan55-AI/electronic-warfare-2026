"""Özgün dört karelik kayıtları yeni sınıflandırıcıyla salt okunur değerlendirir."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.operator_console.measurement_record import read_measurement
from digital_analog_detection.selected_integration import classify_parameter_frames

directory = Path(os.environ['LOCALAPPDATA']) / 'TEKNOFEST 2026 Elektronik Harp' / 'BÂZ' / 'parameter-records'
results = []
for identifier in ('15c7774e15594edb8bae9e73429b43e5', 'a2f955bbea2f40dd87360498e91e0b4f'):
    path = directory / (identifier + '.zip')
    doc, frames = read_measurement(path)
    span = doc['intent']['span']
    value = classify_parameter_frames(frames, sample_rate_hz=doc['sample_rate_hz'],
        lower_shifted_bin=span['lower_shifted_bin'], upper_shifted_bin=span['upper_shifted_bin'],
        snr_db=doc['fields']['snr_estimate_db']['value'])
    results.append(dict(record_id=identifier, record_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        old_domain=doc['automatic_signal_domain'], new_domain=value.as_record()))
report = dict(physical_execution=False, rf_accuracy_acceptance=False, records=results,
    limitation='Özgün kayıtlar dört karedir; 16 karelik sayısal sonuç üretilemez. Sinyallerin gerçek türü bilinmiyor.')
with Path(sys.argv[1]).open('x', encoding='utf-8') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
for result in results:
    print(result['record_id'], result['new_domain']['state'], result['new_domain']['value'], result['new_domain']['confidence'])
