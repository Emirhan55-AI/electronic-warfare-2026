"""KTR-4.2: 825 MHz sonlu Replay bağlantısını gerçek kayıttan incele."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.signal import resample_poly, welch

from analyze_parameter_rf_readiness import (
    ROOT, FS, SPANS, DURATION, BAND_CENTER, spectrum, band_diagnostic, digest, finite_range,
)
from analyze_replay_cw import timeline


def run(folder, output):
    output.mkdir(parents=True, exist_ok=False)
    capture, trace = timeline(folder)
    if capture['sample_rate_hz'] != FS or capture['center_frequency_hz'] != 825_300_000:
        raise ValueError('825,3 MHz merkez ve 8 MS/s kayıt gerekli.')
    baseline = [row['peak_dbfs'] for row in trace if .1 <= row['time_s'] <= 5]
    if len(baseline) < 50:
        raise ValueError('İlk beş saniyelik yayın öncesi referans eksik.')
    threshold = float(np.quantile(baseline, .99) + 6)
    groups = []
    for row in trace:
        if row['time_s'] <= 5 or row['peak_dbfs'] <= threshold:
            continue
        if not groups or row['time_s'] - groups[-1][-1]['time_s'] > .075:
            groups.append([])
        groups[-1].append(row)
    segments = [{'first_s': group[0]['time_s'], 'last_s': group[-1]['time_s'],
                 'sampled_span_s': group[-1]['time_s'] - group[0]['time_s'] + .05,
                 'peak_frequency_median_hz': float(np.median([r['peak_frequency_hz'] for r in group]))}
                for group in groups]
    usable = [s for s in segments if s['sampled_span_s'] >= .75]
    report = {'requirements': ['KTR-4.2', 'KTR-4.2-F1'], 'capture': capture,
        'threshold_dbfs': threshold, 'segments': segments, 'rows': [], 'summary': [],
        'physical_acceptance': False, 'product_acceptance': False, 'dbm_calibrated': False,
        'classification_status': 'not_evaluated',
        'selection_note': 'İlk beş saniye yayın öncesi referans olmalıdır; 825 MHz ±50 kHz çizgi etkinliği yalnız zaman seçer.',
        'method_source_sha256': {name: digest(ROOT / 'scripts' / name) for name in
            ('analyze_parameter_link_capture.py', 'analyze_parameter_rf_readiness.py', 'analyze_replay_cw.py')},
        'shared_source_sha256': {'algorithms/parameters/operator_assisted.py':
            digest(ROOT / 'algorithms/parameters/operator_assisted.py')},
        'capture_manifest_sha256': digest(folder / 'capture.json'),
    }
    if usable:
        selected = max(usable, key=lambda s: s['sampled_span_s'])
        report['selected'] = selected
        raw = np.memmap(folder / 'rx.ci8', dtype=np.int8, mode='r').reshape(-1, 2)
        times = np.linspace(selected['first_s'] + .15, selected['last_s'] - DURATION - .10, 10)
        spectra = []
        for at in times:
            frequency, psd, quality = spectrum(raw, float(at))
            report['rows'].append({'quality': quality,
                'bands': [band_diagnostic(frequency, psd, width) for width in SPANS]})
            spectra.append(psd)
        np.savez_compressed(output / 'spectra.npz', frequency_hz=frequency,
            psd_fs2_per_hz=spectra, times_s=times)
        # Sınıflandırma değildir: zarf mesajının ölçülebilir en güçlü
        # 0,5–4 kHz bileşeni, mevcut AM kaynak tanısıyla karşılaştırılır.
        first = round((selected['first_s'] + .2) * FS)
        values = raw[first:first + round(.5 * FS)].astype(float)
        iq = (values[:, 0] + 1j * values[:, 1]) / 128
        offset = selected['peak_frequency_median_hz'] - 825_300_000
        channel = resample_poly(iq * np.exp(-2j * np.pi * offset * np.arange(len(iq)) / FS), 1, 400)[100:-100]
        f, p = welch(abs(channel), fs=20_000, nperseg=4096)
        mask = (f >= 500) & (f <= 4000)
        report['envelope_peak_hz'] = float(f[np.flatnonzero(mask)[np.argmax(p[mask])]])
        for index, width in enumerate(SPANS):
            bands = [row['bands'][index] for row in report['rows']]
            report['summary'].append({'span_hz': width,
                'snr_db_min_median_max': finite_range([b['snr_db'] for b in bands]),
                'power_dbfs_min_median_max': finite_range([b['signal_excess_dbfs'] for b in bands]),
                'conditional_obw_hz_min_median_max': finite_range([b['conditional_in_span_obw99_hz'] for b in bands])})
        del raw
    with (output / 'report.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({k: report[k] for k in ('segments', 'summary')}, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.folder, args.output)
