"""16 kareli ARM hesabını kayıtlı güç ve bağımsız Python modeliyle denetle."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verify_p0_parameter_runtime import _build, _ci8
from algorithms.spectrum import SpectrumProcessor
from algorithms.parameters.extended_obw import extended_obw_reference


def verify():
    processor = SpectrumProcessor()
    fs = 2_000_000
    cases = []
    with tempfile.TemporaryDirectory(prefix="extended-parameter-") as raw:
        directory = Path(raw)
        exe, state_exe, compiler = _build(directory)
        subprocess.run([str(state_exe)], check=True, capture_output=True)
        def run(samples, lower, upper):
            paths, psd = [], []
            for i, frame in enumerate(samples):
                iq, decoded = _ci8(frame)
                spectrum = processor.process(decoded, sample_rate_hz=fs, center_frequency_hz=820_000_000.)
                power = np.rint(np.asarray(spectrum.fft_power_unshifted) * (1 << 30)).astype('<u8')
                # Runner shifts unshifted PL-format powers before observation.
                psd.append(np.fft.fftshift(power.astype(float)) / (1 << 30) / (fs * 1536))
                ip, pp = directory / f'{i}.iq', directory / f'{i}.power'
                ip.write_bytes(iq); pp.write_bytes(power.tobytes()); paths += [ip, pp]
            out = directory / 'result.json'
            subprocess.run([str(exe), str(fs), '820000000', str(lower), str(upper),
                            *map(str, paths), str(out)], check=True, capture_output=True)
            return json.loads(out.read_text()), np.asarray(psd)
        for seed in range(12):
            rng = np.random.default_rng(2026091600 + seed)
            snr = (10., 20., 30.)[seed % 3]
            frequency = np.zeros((16, 4096), complex)
            frequency[:, 1700:2300] = rng.normal(size=(16,600)) + 1j * rng.normal(size=(16,600))
            clean = np.fft.ifft(np.fft.ifftshift(frequency, axes=1), axis=1)
            clean *= .12 / np.sqrt(np.mean(abs(clean)**2))
            noise = .12 * 10**(-snr/20) / np.sqrt(2) * (rng.normal(size=clean.shape)+1j*rng.normal(size=clean.shape))
            frames = clean + noise
            long, psd = run(frames, 1560, 2450)
            short, _ = run(frames[:4], 1560, 2450)
            reference = extended_obw_reference(psd, 1560, 2450)
            actual = long['occupied_bandwidth_hz']
            if long['emission_center_frequency_hz']['state'] == 1 and actual['reason'] != 7:
                assert abs(reference['temporal_edge_range_bins'] - long['quality']['temporal_edge_range_bins']) < 1e-8
                assert actual['state'] == (1 if reference['reason'] is None else 3)
                if actual['state'] == 1:
                    expected = (reference['upper_bin'] - reference['lower_bin']) * fs / 4096
                    assert abs(actual['value'] - expected) < 1e-6
                    assert abs(actual['value'] / (.99 * 600 * fs / 4096) - 1) < .05
            assert long['observation_count'] == 16
            cases.append({'seed': seed, 'snr_db': snr, 'short': short, 'extended': long, 'reference': reference})
        clipped, _ = run(frames, 1850, 2150)
        noise_only, _ = run(noise, 1560, 2450)
        # Aynı merkezde bant genişliği dört ardışık grupta değişir.
        varying = np.zeros((16,4096), complex)
        for group, width in enumerate((180, 360, 600, 1000)):
            lo = 2000 - width // 2
            varying[group*4:(group+1)*4, lo:lo+width] = rng.normal(size=(4,width))+1j*rng.normal(size=(4,width))
        varying = np.fft.ifft(np.fft.ifftshift(varying,axes=1),axis=1)
        varying *= .12 / np.sqrt(np.mean(abs(varying)**2))
        unstable, _ = run(varying + noise, 1400, 2600)
        assert clipped['occupied_bandwidth_hz']['state'] != 1
        assert noise_only['occupied_bandwidth_hz']['state'] != 1
        assert unstable['occupied_bandwidth_hz']['state'] != 1
        valid = sum(case['extended']['occupied_bandwidth_hz']['state'] == 1 for case in cases)
        assert valid >= 10, f'Geniş bant geliştirme kapısı geçmedi: {valid}/12'
    return {'status':'passed', 'compiler':compiler, 'physical_execution':False, 'rf_accuracy_acceptance':False,
            'cases': cases, 'extended_valid':valid,
            'short_valid':sum(case['short']['occupied_bandwidth_hz']['state']==1 for case in cases),
            'clipped':clipped, 'noise_only':noise_only, 'unstable':unstable,
            'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
                'platforms/embedded/p0/src/p0_parameter_runtime.c', 'platforms/embedded/p0/include/p0_parameter_runtime.h',
                'platforms/embedded/p0/src/p0_parameter_run.c', 'algorithms/parameters/extended_obw.py',
                'scripts/verify_extended_parameter.py')}}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=verify()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2)
    print(json.dumps({k:report[k] for k in ('status','extended_valid','short_valid')},ensure_ascii=False))
