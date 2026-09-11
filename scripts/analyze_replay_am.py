"""KTR-4.2: Replay AM kaydını sabit aday ve bağımsız zarf tanısıyla değerlendir."""
from pathlib import Path
from collections import Counter
from dataclasses import asdict
import argparse
import hashlib
import json
import sys

import numpy as np
from scipy.signal import resample_poly, welch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algorithms.parameters.refined_candidate import classify_candidate, measure_candidate

MODEL_SHA256 = 'afa2872c6363d25e5322b6c382db32a0b9ec3d85260ef4b6ce37d9606ebc67c9'


def run(folder, output):
    model_path = ROOT / 'build/acceptance/parameter-candidate-v9-20260909/candidate-model.json'
    model_bytes = model_path.read_bytes()
    if hashlib.sha256(model_bytes).hexdigest() != MODEL_SHA256:
        raise ValueError('Sabit aday model özeti eşleşmiyor.')
    model = json.loads(model_bytes)
    capture = json.loads((folder / 'capture.json').read_text(encoding='utf-8'))
    activity = json.loads((folder / 'activity.json').read_text(encoding='utf-8'))
    if not capture.get('transport_valid') or capture.get('settled_rail_components') != 0:
        raise ValueError('Taşmasız ve kırpılmasız kayıt gerekli.')
    if activity['on_sha256'] != capture['raw_sha256'] or not activity['segments']:
        raise ValueError('Ham kayıt bağı veya etkin yayın bölümü eksik.')
    segment = max(activity['segments'], key=lambda item: item['sampled_span_s'])
    if segment['sampled_span_s'] < .4:
        raise ValueError('AM tanısı için yeterli kesintisiz etkin bölüm yok.')
    start = segment['first_s'] + .05
    step = min(.04, (segment['sampled_span_s'] - .15) / 10)
    data = np.memmap(folder / 'rx.ci8', dtype=np.int8, mode='r').reshape(-1, 2)
    rows = []
    for index in range(10):
        at = start + index * step
        first = int(at * 8_000_000)
        values = data[first:first + 73728].astype(float)
        iq = resample_poly((values[:, 0] + 1j * values[:, 1]) / 128, 1, 4)[256:256 + 16384]
        measurement = measure_candidate(iq.reshape(4, 4096), sample_rate_hz=2_000_000,
            center_frequency_hz=825_300_000, lower_bin=1334, upper_bin=1534)
        rows.append({'time_s': at, 'measurement': asdict(measurement),
                     'decision': classify_candidate(measurement, model)})
    # Ayrı 0,25 s zarf tanısı; sınıf kararına geri beslenmez.
    values = data[int(start * 8_000_000):int((start + .25) * 8_000_000)].astype(float)
    iq = (values[:, 0] + 1j * values[:, 1]) / 128
    offset = segment['median_frequency_hz'] - 825_300_000
    mixed = iq * np.exp(-2j * np.pi * offset * np.arange(len(iq)) / 8_000_000)
    baseband = resample_poly(mixed, 1, 400)[100:-100]
    frequency, power = welch(abs(baseband), fs=20_000, nperseg=4096)
    mask = (frequency >= 500) & (frequency <= 4000)
    peak = np.flatnonzero(mask)[np.argmax(power[mask])]
    report = {
        'requirements': ['KTR-4.2', 'KTR-4.2-F1'],
        'selection': {'independent_activity_segment': segment, 'first_window_s': start,
                      'window_step_s': step, 'window_count': 10},
        'summary': dict(Counter(row['decision'] for row in rows)),
        'rows': rows,
        'envelope_peak_hz': float(frequency[peak]),
        'envelope_bin_hz': 20_000 / 4096,
        'raw_sha256': capture['raw_sha256'],
        'model_sha256': MODEL_SHA256,
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'product_acceptance': False,
        'physical_acceptance': False,
        'limits': ['Tek RF koşusundan on pencere; bağımsız on koşu değildir.',
                   'Etkin bölüm, sınıflandırmadan bağımsız spektrum eşiğiyle seçilir.',
                   'PC adayıdır; ürün F5, ARM ve FPGA kullanılmadı.'],
    }
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'summary': report['summary'], 'envelope_peak_hz': report['envelope_peak_hz'],
                      'snr_db': [r['measurement']['snr_db'] for r in rows],
                      'reasons': dict(Counter(r['measurement']['reason'] for r in rows))},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    run(arguments.folder, arguments.output)
