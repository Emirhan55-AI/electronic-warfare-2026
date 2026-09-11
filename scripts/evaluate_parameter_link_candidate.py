"""KTR-4.2: bağlantı kaydında sabit v9 adayı; aralık taraması yalnız tanıdır."""
import argparse
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np
from scipy.signal import resample_poly

from analyze_parameter_rf_readiness import ROOT, FS, SPANS, BAND_CENTER, digest
from algorithms.parameters.refined_candidate import measure_candidate, classify_candidate

MODEL_SHA = 'afa2872c6363d25e5322b6c382db32a0b9ec3d85260ef4b6ce37d9606ebc67c9'


def run(folder, link_report, model_path, output):
    link = json.loads(link_report.read_text(encoding='utf-8'))
    if digest(folder / 'rx.ci8') != link['capture']['raw_sha256']:
        raise ValueError('Ham I/Q raporla eşleşmiyor.')
    if digest(model_path) != MODEL_SHA:
        raise ValueError('Dondurulmuş model özeti eşleşmiyor.')
    if not link['capture']['transport_valid'] or link['capture']['settled_rail_components'] != 0:
        raise ValueError('Sınıflandırma karşılaştırması için taşmasız/kırpılmasız kayıt gerekli.')
    model = json.loads(model_path.read_text(encoding='utf-8'))
    raw = np.memmap(folder / 'rx.ci8', dtype=np.int8, mode='r').reshape(-1, 2)
    observed_bin = round(2048 + (BAND_CENTER - 825_300_000) / (2_000_000 / 4096))
    rows = []
    for row in link['rows']:
        at = row['quality']['start_s']
        first = round(at * FS)
        values = raw[first:first + 73728].astype(float)
        x = resample_poly((values[:, 0] + 1j * values[:, 1]) / 128, 1, 4)[256:256 + 16384]
        for width in SPANS:
            half = round(width / (2 * 2_000_000 / 4096))
            measurement = measure_candidate(x.reshape(4, 4096), sample_rate_hz=2_000_000,
                center_frequency_hz=825_300_000, lower_bin=observed_bin-half, upper_bin=observed_bin+half)
            rows.append({'time_s': at, 'requested_span_hz': width,
                'effective_span_hz': (2*half+1)*2_000_000/4096,
                'decision': classify_candidate(measurement, model), 'measurement': asdict(measurement)})
    summary = [{'span_hz': width,
        'decisions': dict(Counter(r['decision'] for r in rows if r['requested_span_hz'] == width)),
        'reasons': dict(Counter(str(r['measurement']['reason']) for r in rows if r['requested_span_hz'] == width))}
        for width in SPANS]
    report = {'requirements': ['KTR-4.2', 'KTR-4.2-F1'], 'summary': summary, 'rows': rows,
        'raw_sha256': link['capture']['raw_sha256'], 'link_report_sha256': digest(link_report),
        'model_sha256': MODEL_SHA, 'source_sha256': digest(Path(__file__)),
        'candidate_source_sha256': digest(ROOT / 'algorithms/parameters/refined_candidate.py'),
        'physical_acceptance': False, 'product_acceptance': False,
        'limits': 'Tek RF koşusunun on penceresi ve beş aralık tanısı; elli bağımsız test değildir. Yöntem/eşik değiştirilmedi.'}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--link-report', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.folder, args.link_report, args.model, args.output)
