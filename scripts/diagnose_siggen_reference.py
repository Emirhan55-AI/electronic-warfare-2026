"""KTR-4.2-F1: periyodik PSK kaynak tanısı; sınıflandırma kabulü değildir.

Kaynak karşılaştırması upstream algoritması içindir; cihaz imajını doğrulamaz.
RF tepe aralıklarından ton tahmini yalnız bu kaynak hipotezinde geçerlidir.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
from scipy.signal import find_peaks, welch


def ambiguity_check():
    # Enumerate all 256 phase table addresses, as the upstream branch does.
    phase = np.arange(256, dtype=np.uint32)
    bpsk = np.where(phase & 128, 127, -128).astype(np.int8)
    square_message = np.where(phase & 128, 127, -128).astype(np.int8)
    dsb = square_message.copy()
    return {
        'phase_addresses': 256,
        'bpsk_equals_dsb_square': bool(np.array_equal(bpsk, dsb)),
        'maximum_sample_difference': int(np.max(abs(bpsk.astype(int)-dsb.astype(int)))),
        'implication': 'Aynı I/Q için kaynak menüsüne göre farklı kesin sınıf istenemez.',
    }


def inspect_record(path, family):
    data = path.read_bytes()
    raw = np.frombuffer(data, np.int8)[1048576:]
    x = (raw[::2].astype(float)+1j*raw[1::2].astype(float))/128
    center = int(path.stem.split('-')[1])
    frequency, power = welch(x, 8_000_000, nperseg=131072, return_onesided=False)
    frequency, power = np.fft.fftshift(frequency)+center, np.fft.fftshift(power)
    peaks, _ = find_peaks(power)
    peaks = [i for i in peaks if abs(frequency[i]-825_000_000)<50000]
    peaks = sorted(peaks, key=lambda i: power[i], reverse=True)[:8]
    strongest = sorted(peaks[:2], key=lambda i: frequency[i])
    spacing = float(np.diff(frequency[strongest])[0])
    # This source uses 2/tone cycles for BPSK, 4/tone for QPSK.
    divisor = 2 if family == 'BPSK' else 4
    return {
        'raw_path': path.as_posix(), 'raw_sha256': hashlib.sha256(data).hexdigest(),
        'declared_mode': family, 'frequency_resolution_hz': 8_000_000/131072,
        'strongest_two_spacing_hz': spacing,
        'tone_hypothesis_hz': spacing/divisor,
        'symbol_rate_hypothesis_baud': spacing,
        'hypothesis_is_independent_reference': False,
        'peaks': [{'frequency_hz': float(frequency[i]),
                   'relative_db': float(10*np.log10(power[i]/power[peaks[0]]))} for i in peaks],
        'note': 'Tepe frekansı taşıyıcı değildir; ton/sembol hızı yalnız kaynak hipotezidir.',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    records = []
    for family in ('BPSK', 'QPSK'):
        folder = Path(f'build/acceptance/parameter-rf-{family.lower()}825-g32-20260909')
        records.extend(inspect_record(path, family) for path in sorted(folder.glob('*.ci8')))
    if len(records) != 4:
        raise RuntimeError('İki mod için ikişer özgün kayıt gerekli.')
    result = {'requirements': ['KTR-4.2', 'KTR-4.2-F1'],
              'ambiguity': ambiguity_check(), 'rf_records': records,
              'product_acceptance': False, 'installed_tx_firmware_verified': False,
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'ambiguity': result['ambiguity'],
                      'tone_hypotheses_hz': [r['tone_hypothesis_hz'] for r in records]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
