"""KTR-4.2: PortaPack için sonlu, referansı kayıtlı laboratuvar I/Q paketi.

Yalnız dosya üretir. RF, ürün algoritması veya model eğitimi çalıştırmaz.
"""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import zipfile

import numpy as np
import scipy
from scipy.signal import fftconvolve, firwin, welch

FS = 500_000
RF = 825_000_000
RATE = 20_000
SEED = 27000000
FAMILIES = ('CW', 'AM', 'NFM', 'BPSK', 'QPSK', 'FSK')


def make_wave(family, duration, seed):
    if family not in FAMILIES or duration not in (2, 6):
        raise ValueError('Desteklenen aile ve 2/6 saniyelik süre gerekli.')
    n = FS * duration
    t = np.arange(n) / FS
    rng = np.random.default_rng(seed)
    reference = {'family': family, 'seed': seed, 'sample_rate_hz': FS,
                 'center_frequency_hz': RF, 'duration_s': duration}
    if family == 'CW':
        x = np.ones(n, dtype=complex)
    elif family == 'AM':
        x = 1 + .7 * np.cos(2 * np.pi * 1700 * t)
        reference.update(tone_hz=1700, modulation_depth=.7)
    elif family == 'NFM':
        x = np.exp(1j * (6000 / 1700) * np.sin(2 * np.pi * 1700 * t))
        reference.update(tone_hz=1700, peak_deviation_hz=6000)
    else:
        sps = FS // RATE
        labels = rng.integers(0, 4 if family == 'QPSK' else 2, n // sps + 24, dtype=np.uint8)
        symbols = ((2 * (labels // 2).astype(float) - 1) +
                   1j * (2 * (labels % 2).astype(float) - 1)) / np.sqrt(2) if family == 'QPSK' else 2 * labels.astype(float) - 1
        repeated = np.repeat(symbols, sps)
        if family == 'FSK':
            x = np.exp(2j * np.pi * np.cumsum(repeated[:n]) * 10000 / FS)
            reference.update(peak_deviation_hz=10000, pulse_shape='Dikdörtgen frekans darbeli sürekli faz FSK')
        else:
            taps = firwin(12 * sps + 1, 1.1 / sps, window='blackman')
            x = fftconvolve(repeated, taps, mode='same')[12 * sps:12 * sps + n]
            reference.update(pulse_shape='NRZ ardından Blackman pencereli FIR; RRC değildir', fir_taps=len(taps), cutoff_hz=RATE * .55)
        reference.update(symbol_rate_baud=RATE, symbols_sha256=hashlib.sha256(labels.tobytes()).hexdigest(),
                         symbol_counts=np.bincount(labels).tolist())
    x = np.asarray(x, dtype=complex)
    x *= .25 / np.sqrt(np.mean(abs(x) ** 2))
    # Yumuşak dosya sınırları; RF stop yerine geçmez.
    ramp = FS // 200
    envelope = np.sin(np.linspace(0, np.pi / 2, ramp)) ** 2
    x[:ramp] *= envelope
    x[-ramp:] *= envelope[::-1]
    return x, reference


def encode(x):
    iq = np.column_stack((x.real, x.imag))
    if not np.all(np.isfinite(iq)) or np.max(abs(iq)) >= 1:
        raise ValueError('I/Q sonlu ve kırpılmasız olmalıdır.')
    # Replay >>8 uygular: alt baytı sıfır tutarak C8 karşılığını açık kıl.
    ci8 = np.rint(iq * 128).astype(np.int16)
    if np.max(abs(ci8)) >= 127:
        raise ValueError('C8 baş boşluğu yetersiz.')
    return (ci8 * 256).astype('<i2').tobytes()


def inspect(data):
    raw = np.frombuffer(data, '<i2').reshape(-1, 2)
    if np.any(raw % 256):
        raise ValueError('Beklenmeyen C16 ölçeği.')
    x = (raw[:, 0].astype(float) + 1j * raw[:, 1]) / 32768
    stable = x[FS // 10:-FS // 10]
    f, p = welch(stable, fs=FS, window='hann', nperseg=65536, return_onesided=False, detrend=False)
    if not np.isfinite(p.sum()) or p.sum() <= 0:
        raise ValueError('Referans spektrum gücü pozitif ve sonlu olmalıdır.')
    f, p = np.fft.fftshift(f), np.fft.fftshift(p)
    cdf = np.cumsum(p) / p.sum()
    edges = np.interp([.005, .995], cdf, f)
    return {'samples': len(x), 'duration_s': len(x) / FS,
            'digital_power_dbfs': float(10 * np.log10(np.mean(abs(stable) ** 2))),
            'reference_obw99_hz': float(edges[1] - edges[0]),
            'reference_edges_baseband_hz': edges.tolist(), 'reference_fft_bin_hz': FS / 65536,
            'peak_component': float(np.max(abs(raw.astype(float))) / 32768),
            'first_last_zero': bool(np.all(raw[[0, -1]] == 0)),
            'reference_method': 'Dosyadan Welch/Hann; iki uçta %0,5. RF ölçümü değildir.'}


def build(output):
    output.mkdir(parents=True, exist_ok=False)
    captures = output / 'CAPTURES' / 'PARAMTEST'
    captures.mkdir(parents=True)
    rows = []
    for index, family in enumerate(FAMILIES):
        name = f'{index:02d}_{family}'
        x, truth = make_wave(family, 2 if family == 'CW' else 6, SEED + index)
        data = encode(x)
        path = captures / (name + '.C16')
        path.write_bytes(data)
        path.with_suffix('.TXT').write_bytes(f'center_frequency={RF}\nsample_rate={FS}\n'.encode('ascii'))
        stats = inspect(path.read_bytes())
        assert stats['first_last_zero'] and stats['duration_s'] == truth['duration_s']
        rows.append({'file': path.relative_to(output).as_posix(), 'reference': truth, 'file_measurement': stats})
    files = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in captures.iterdir()}
    report = {'requirements': ['KTR-4.2', 'KTR-4.2-F1'], 'rows': rows, 'files': files,
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'runtime': {'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__},
              'rf_transmitted': False, 'dbm_calibrated': False, 'physical_acceptance': False,
              'limits': ['Sabit tohumlu rastgele veri; sınıflandırıcı eğitimi için kullanılmaz.',
                         'PortaPack sürümü, SD akışı, C8 dönüşümü ve RF filtreleri fiziksel doğrulama ister.',
                         '825 MHz nominal ayardır; gerçek frekans ve dBm bu dosyalarla kalibre olmaz.']}
    (output / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    guide = Path(__file__).resolve().parents[1] / 'docs/plans/PARAMETER_REPLAY_LAB_GUIDE.md'
    (output / 'TALIMAT.md').write_bytes(guide.read_bytes())
    with zipfile.ZipFile(output / 'PARAMTEST_SD.zip', 'x', zipfile.ZIP_DEFLATED) as z:
        for name in files:
            z.write(output / name, name)
        z.write(output / 'TALIMAT.md', 'TALIMAT.md')
        z.write(output / 'manifest.json', 'manifest.json')
    with zipfile.ZipFile(output / 'PARAMTEST_SD.zip') as z:
        assert all(hashlib.sha256(z.read(n)).hexdigest() == digest for n, digest in files.items())
    print(json.dumps({'files': len(files), 'iq_files': len(rows), 'archive': str(output / 'PARAMTEST_SD.zip'),
                      'reference': {r['reference']['family']: r['file_measurement'] for r in rows}}, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    build(parser.parse_args().output)
