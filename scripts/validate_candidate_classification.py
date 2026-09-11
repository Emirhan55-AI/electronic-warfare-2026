"""KTR-4.2-F1: eğitimden ayrı üreticiyle sabit adayın sınıf sınaması."""
from pathlib import Path
from collections import Counter
from dataclasses import asdict
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algorithms.parameters.refined_candidate import measure_candidate, classify_candidate
from scripts.validate_candidate_numeric import waveform

FAMILIES = ('CW', 'AM', 'NFM', 'FSK', 'BPSK', 'QPSK')


def summarize(rows):
    """Retler toplamda kalır; yanlış kesin kararlar kapsamı başarı yapmaz."""
    result = {}
    for family in FAMILIES:
        selected = [r for r in rows if r['reference']['family'] == family]
        expected = 'Belirsiz' if family == 'CW' else 'Analog' if family in ('AM', 'NFM') else 'Sayısal'
        counts = Counter(r['decision'] for r in selected)
        total = len(selected)
        definite = total - counts['Belirsiz']
        correct = counts[expected]
        wrong = definite if family == 'CW' else definite - correct
        coverage = definite / total if total else 0
        precision = (correct / definite if definite else None) if family != 'CW' else None
        result[family] = {
            'total': total, 'decisions': dict(counts), 'correct': correct,
            'wrong_definite': wrong, 'abstained': counts['Belirsiz'],
            'decision_coverage': coverage, 'definite_precision': precision,
            'gate_pass': bool(total and (correct == total if family == 'CW' else
                              coverage >= .8 and precision is not None and precision >= .9)),
        }
    return result


def run(output, model_path, model_sha256, seed_base=26000000):
    model_bytes = model_path.read_bytes()
    if hashlib.sha256(model_bytes).hexdigest() != model_sha256:
        raise ValueError('Model özeti eşleşmiyor.')
    model = json.loads(model_bytes)
    output.mkdir(parents=True, exist_ok=False)
    # Protokol sonuçlardan önce yazılır. Aynı tohumun SNR varyantları bağımsız değildir.
    protocol = {'families': FAMILIES, 'snr_db': [12, 24, 36], 'seeds_per_family': 8,
                'seed_base': seed_base, 'coverage_min': .8, 'precision_min': .9,
                'model_sha256': model_sha256, 'model_threshold': model['threshold']}
    (output / 'protocol.json').write_text(json.dumps(protocol, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'candidate-model.json').write_bytes(model_bytes)
    rows = []
    for fi, family in enumerate(FAMILIES):
        for snr in protocol['snr_db']:
            for i in range(8):
                frames, truth = waveform(family, seed_base + fi * 1000 + i, snr)
                measurement = measure_candidate(frames, sample_rate_hz=2000000,
                    center_frequency_hz=700000000, lower_bin=truth['lower_bin'], upper_bin=truth['upper_bin'])
                rows.append({'reference': truth, 'iq_sha256': hashlib.sha256(frames.astype('<c16').tobytes()).hexdigest(),
                             'measurement': asdict(measurement), 'decision': classify_candidate(measurement, model)})
    summary = summarize(rows)
    source_names = ['scripts/validate_candidate_classification.py', 'scripts/validate_candidate_numeric.py',
                    'algorithms/parameters/refined_candidate.py']
    report = {'requirements': ['KTR-4.2', 'KTR-4.2-F1'], 'protocol': protocol,
              'summary': summary, 'by_snr': {str(snr): summarize([r for r in rows if r['reference']['snr_db'] == snr])
                                           for snr in protocol['snr_db']}, 'rows': rows,
              'software_gate': all(r['gate_pass'] for r in summary.values()),
              'product_acceptance': False, 'hardware_acceptance': False,
              'limits': ['Eğitimden ayrı mevcut sayısal üretici; bağımsız RF kabulü değildir.',
                         '48 dalga biçimi tohumu, 144 SNR varyantı; OOK/QAM ve kapsam dışı aileler bu koşuda yok.',
                         'Gerçek alıcı nicemleme, saat ve kanal bozulmaları bu üreticide temsil edilmez.'],
              'source_hashes': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in source_names}}
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--model-sha256', required=True)
    parser.add_argument('--seed-base', type=int, default=26000000)
    args = parser.parse_args()
    report = run(args.output, args.model, args.model_sha256, args.seed_base)
    sys.exit(0 if report['software_gate'] else 1)
