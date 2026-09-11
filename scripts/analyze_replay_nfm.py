"""KTR-4.2: Replay NFM kaydını sabit aday ve faz-farkı tanısıyla değerlendir."""
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
REFERENCE_FREQUENCY_HZ = 824_989_819.3359375  # Önceki temiz CW gözlemi.
REFERENCE_OBW99_HZ = 16_997.210371965244    # RF öncesi dosya manifesti.


def run(folder, output):
    capture = json.loads((folder / 'capture.json').read_text(encoding='utf-8'))
    activity = json.loads((folder / 'activity.json').read_text(encoding='utf-8'))
    if not capture.get('transport_valid') or capture.get('settled_rail_components') != 0:
        raise ValueError('Taşmasız ve kırpılmasız kayıt gerekli.')
    if activity['on_sha256'] != capture['raw_sha256'] or not activity['segments']:
        raise ValueError('Ham kayıt bağı veya kaba etkinlik işareti eksik.')
    model_path = ROOT / 'build/acceptance/parameter-candidate-v9-20260909/candidate-model.json'
    model_bytes = model_path.read_bytes()
    if hashlib.sha256(model_bytes).hexdigest() != MODEL_SHA256:
        raise ValueError('Sabit aday model özeti eşleşmiyor.')
    model = json.loads(model_bytes)
    data = np.memmap(folder / 'rx.ci8', dtype=np.int8, mode='r').reshape(-1, 2)

    # Kaba çizgi işaretinin ilk/son zamanı yalnız kayıt içindeki 6 s adayını bulur;
    # ölçüm aralığı önceki CW ve RF öncesi manifestten gelir.
    first_activity = min(item['first_s'] for item in activity['segments'])
    last_activity = max(item['last_s'] for item in activity['segments'])
    if not 4.5 <= last_activity - first_activity <= 8:
        raise ValueError('Beklenen sonlu NFM yayın aralığı bulunamadı.')
    start = first_activity + .25
    observed_bin = round(2048 + (REFERENCE_FREQUENCY_HZ - 825_300_000) / (2_000_000 / 4096))
    half_width = 32  # 31,74 kHz span; 17 kHz dosya OBW'sine önceden sabit margin.
    rows = []
    for index in range(10):
        at = start + index * .45
        first = int(at * 8_000_000)
        values = data[first:first + 73728].astype(float)
        iq = resample_poly((values[:, 0] + 1j * values[:, 1]) / 128, 1, 4)[256:256 + 16384]
        measurement = measure_candidate(iq.reshape(4, 4096), sample_rate_hz=2_000_000,
            center_frequency_hz=825_300_000, lower_bin=observed_bin-half_width,
            upper_bin=observed_bin+half_width)
        rows.append({'time_s': at, 'measurement': asdict(measurement),
                     'decision': classify_candidate(measurement, model)})

    # 0,5 s faz-farkı referansı; sınıf kararına geri beslenmez.
    diag_start = start + .5
    values = data[int(diag_start*8_000_000):int((diag_start+.5)*8_000_000)].astype(float)
    iq = (values[:, 0] + 1j * values[:, 1]) / 128
    offset = REFERENCE_FREQUENCY_HZ - 825_300_000
    mixed = iq * np.exp(-2j*np.pi*offset*np.arange(len(iq))/8_000_000)
    channel = resample_poly(mixed, 1, 160)[200:-200]
    discriminator = np.angle(channel[1:] * channel[:-1].conj()) * 50_000 / (2*np.pi)
    frequency, power = welch(discriminator, fs=50_000, nperseg=8192)
    mask = (frequency >= 500) & (frequency <= 4000)
    peak = np.flatnonzero(mask)[np.argmax(power[mask])]
    report = {
        'requirements': ['KTR-4.2', 'KTR-4.2-F1'],
        'selection': {'first_activity_s': first_activity, 'last_activity_s': last_activity,
                      'first_window_s': start, 'window_step_s': .45, 'window_count': 10,
                      'reference_frequency_hz': REFERENCE_FREQUENCY_HZ,
                      'reference_obw99_hz': REFERENCE_OBW99_HZ,
                      'analysis_span_hz': (2*half_width+1)*2_000_000/4096},
        'summary': dict(Counter(row['decision'] for row in rows)),
        'reasons': dict(Counter(row['measurement']['reason'] for row in rows)),
        'rows': rows,
        'discriminator_peak_hz': float(frequency[peak]),
        'discriminator_bin_hz': 50_000/8192,
        'raw_sha256': capture['raw_sha256'], 'model_sha256': MODEL_SHA256,
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'product_acceptance': False, 'physical_acceptance': False,
        'limits': ['Tek RF koşusunun on penceresi bağımsız koşu değildir.',
                   'Kaba zaman seçimi çizgi işaretlerinin ilk/son zamanını kullanır.',
                   'Frekans merkezi önceki CW, span RF öncesi dosya manifestinden gelir.',
                   'PC adayıdır; ürün F5, ARM ve FPGA kullanılmadı.'],
    }
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'summary': report['summary'], 'reasons': report['reasons'],
                      'discriminator_peak_hz': report['discriminator_peak_hz'],
                      'snr_db': [row['measurement']['snr_db'] for row in rows]},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.folder, args.output)
