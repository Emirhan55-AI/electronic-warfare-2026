"""KTR-4.2-F1: gerçek kayıtlarla sabit model/ön işleme bağlantısını değerlendir."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys
import zipfile

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algorithms.parameters.rf_observation import observe_rf
from algorithms.parameters.rf_channel_classifier import load_frozen_model, MODEL_SHA256
from analyze_parameter_rf_readiness import digest


FOLDERS = {
    'AM_new': ('teknofest-rx-am-linkcheck-20260909', 'capture'),
    'AM_previous': ('teknofest-rx-newport-amg8-rx24-20260909', 'teknofest-rx-newport-amg8-rx24-20260909'),
    'NFM': ('teknofest-rx-newport-nfmg8-rx24-20260909', 'capture'),
    'BPSK': ('teknofest-rx-newport-bpskg8-rx24-20260909', 'on'),
}


def run(output, model_path, captures_root):
    output.mkdir(parents=True, exist_ok=False)
    model = load_frozen_model(model_path)
    previous_manifest = ROOT / 'results/evidence/phase08/rf-observation-records-20260909.json'
    manifest = json.loads(previous_manifest.read_text(encoding='utf-8'))
    archive_path = previous_manifest.with_suffix('.zip')
    if digest(archive_path) != manifest['archive_sha256']:
        raise ValueError('Özgün ön işleme arşivi eşleşmiyor.')
    with zipfile.ZipFile(archive_path) as archive:
        data = archive.read('report.json')
    import hashlib
    if hashlib.sha256(data).hexdigest() != manifest['files']['report.json']:
        raise ValueError('Özgün rapor özeti eşleşmiyor.')
    baseline = json.loads(data)
    report = {'requirements': ['KTR-4.2', 'KTR-4.2-F1'],
        'scope': 'Önceden incelenmiş gerçek RF geliştirme verisi; yeni eğitim yok.',
        'model_sha256': MODEL_SHA256, 'model_threshold': model['threshold'],
        'baseline_manifest_sha256': digest(previous_manifest),
        'source_sha256': {p: digest(ROOT / p) for p in (
            'algorithms/parameters/rf_observation.py',
            'algorithms/parameters/rf_channel_classifier.py',
            'algorithms/parameters/refined_candidate.py',
            'scripts/analyze_parameter_rf_readiness.py',
            'scripts/evaluate_rf_channel_classifier.py')},
        'runtime': {'python': sys.version, 'numpy': np.__version__, 'scipy': scipy.__version__},
        'physical_acceptance': False, 'product_acceptance': False, 'cases': []}
    for old in baseline['cases']:
        label = old['label_for_reporting_only']
        folder, prefix = FOLDERS[label]
        evidence_path = ROOT / old['evidence']
        if digest(evidence_path) != old['evidence_sha256']:
            raise ValueError('Özgün RF kanıtı değişmiş.')
        evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
        raw_path = captures_root / folder / 'rx.ci8'
        if not raw_path.exists():
            raw_path = output / 'recovered' / folder / 'rx.ci8'
            raw_path.parent.mkdir(parents=True, exist_ok=False)
            with zipfile.ZipFile(evidence_path.with_suffix('.zip')) as archive:
                with archive.open(prefix + '/rx.ci8') as src, raw_path.open('xb') as dst:
                    while block := src.read(1048576):
                        dst.write(block)
        if digest(raw_path) != old['raw_sha256']:
            raise ValueError('Ham RF kaydı değişmiş.')
        raw = np.memmap(raw_path, dtype=np.int8, mode='r').reshape(-1, 2)
        rows = []
        for row in old['rows']:
            first = round(row['start_s'] * 8_000_000)
            codes = raw[first:first + 2_000_000].astype(float)
            if len(codes) != 2_000_000 or np.any((codes == -128) | (codes == 127)):
                raise ValueError('Eksik/kırpılmış gerçek RF penceresi.')
            x = (codes[:, 0] + 1j * codes[:, 1]) / 128
            lower, upper = row['result']['analysis_band_hz']
            result = observe_rf(x, sample_rate_hz=8_000_000, center_frequency_hz=825_300_000,
                lower_frequency_hz=lower, upper_frequency_hz=upper,
                classification_model=model).to_dict()
            result = json.loads(json.dumps(result, allow_nan=False))
            # Classification integration must not alter any numerical RF output.
            for key, expected in row['result'].items():
                if key not in ('signal_domain', 'classification_reason') and result[key] != expected:
                    raise ValueError(f'Ölçüm alanı değişti: {key}')
            rows.append({'start_s': row['start_s'], 'role': row['role'], 'result': result})
        case = {k: v for k, v in old.items() if k != 'rows'}
        case['rows'] = rows
        case['decisions'] = dict(Counter(r['result']['signal_domain'] for r in rows if r['role'] == 'on'))
        case['quality_pass_windows'] = sum(r['result']['quality_reason'] is None for r in rows if r['role'] == 'on')
        report['cases'].append(case)
        print(json.dumps({'record': label, 'decisions': case['decisions'],
                         'quality_pass': case['quality_pass_windows']}, ensure_ascii=False), flush=True)
        del raw
    report['numerical_outputs_unchanged'] = True
    report['pre_windows_all_unknown'] = all(r['result']['signal_domain'] == 'Belirsiz'
        for c in report['cases'] for r in c['rows'] if r['role'] == 'pre')
    if not report['pre_windows_all_unknown']:
        raise ValueError('Yayın öncesinde kesin sınıf üretildi.')
    with (output / 'report.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--captures-root', type=Path, default=Path(os.environ['TEMP']))
    args = parser.parse_args()
    run(args.output, args.model, args.captures_root)
