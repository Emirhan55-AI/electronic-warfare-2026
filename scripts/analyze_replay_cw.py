"""KTR-4.2: kapalı referansa göre sonlu CW zaman çizelgesi; kabul değildir."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np


def timeline(folder):
    metadata = json.loads((folder / 'capture.json').read_text(encoding='utf-8'))
    if not metadata.get('complete'):
        raise ValueError('Tamamlanmış RX kaydı gerekli.')
    raw = folder / 'rx.ci8'
    digest = hashlib.sha256()
    with raw.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    if digest.hexdigest() != metadata['raw_sha256']:
        raise ValueError('Ham kayıt özeti eşleşmiyor.')
    data = np.memmap(raw, mode='r', dtype=np.int8).reshape(-1, 2)
    fs = metadata['sample_rate_hz']
    n = 65536
    window = np.hanning(n)
    f = np.fft.fftshift(np.fft.fftfreq(n, 1 / fs)) + metadata['center_frequency_hz']
    mask = abs(f - 825000000) <= 50000
    rows = []
    for start in range(fs // 10, len(data) - n, fs // 20):
        v = data[start:start+n].astype(float)
        x = (v[:, 0] + 1j*v[:, 1]) / 128
        p = abs(np.fft.fftshift(np.fft.fft(x * window))) ** 2 / window.sum() ** 2
        idx = np.flatnonzero(mask)[np.argmax(p[mask])]
        rows.append({'time_s': start/fs, 'peak_frequency_hz': float(f[idx]),
                     'peak_dbfs': float(10*np.log10(max(p[idx], 1e-30)))})
    return metadata, rows


def run(off, on, output):
    before, baseline = timeline(off)
    observed, rows = timeline(on)
    for field in ('gain_db', 'sample_rate_hz', 'center_frequency_hz'):
        if before[field] != observed[field]:
            raise ValueError('Karşılaştırılan alıcı ayarları eşleşmiyor.')
    threshold = float(np.quantile([r['peak_dbfs'] for r in baseline], .99) + 6)
    active = [r for r in rows if r['peak_dbfs'] > threshold]
    segments = []
    for r in active:
        if not segments or r['time_s'] - segments[-1][-1]['time_s'] > .075:
            segments.append([])
        segments[-1].append(r)
    result = {'requirements': ['KTR-4.2', 'KTR-4.2-F1'], 'threshold_dbfs': threshold,
              'method': '825 MHz ±50 kHz, 65536 Hann FFT, 50 ms adım; kapalı q99 +6 dB tanı eşiği.',
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'off_sha256': before['raw_sha256'], 'on_sha256': observed['raw_sha256'],
              'active_windows': len(active), 'total_windows': len(rows),
              'segments': [{'first_s': s[0]['time_s'], 'last_s': s[-1]['time_s'],
                            'sampled_span_s': s[-1]['time_s'] - s[0]['time_s'] + .05,
                            'median_frequency_hz': float(np.median([r['peak_frequency_hz'] for r in s])),
                            'peak_dbfs': max(r['peak_dbfs'] for r in s)} for s in segments],
              'baseline': baseline, 'rows': rows,
              'acceptance': False, 'limits': 'Aralıklı spektrum tanısı; sürekli RF yokluğu, kalibre frekans/dBm veya ürün kabulü değildir.'}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('baseline', 'rows')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--off', type=Path, required=True)
    parser.add_argument('--on', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.off, args.on, args.output)
