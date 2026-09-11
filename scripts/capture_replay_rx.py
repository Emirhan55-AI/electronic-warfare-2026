"""KTR-4.2: bağımsız Replay vericisi için sonlu RX kaydı; TX başlatmaz."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import re
import subprocess
import time

import numpy as np


def capture(output, seconds, state, gain=16):
    if not 1 <= seconds <= 30 or gain not in (0, 8, 16, 24, 32):
        raise ValueError('Sonlu süre ve desteklenen alıcı kazancı gerekli.')
    output.mkdir(parents=True, exist_ok=False)
    tool = Path('C:/msys64/ucrt64/bin/hackrf_transfer.exe')
    raw = output / 'rx.ci8'
    command = [str(tool), '-d', '0000000000000000a32868dc35138247', '-r', str(raw.resolve()),
               '-f', '825300000', '-s', '8000000', '-n', str(seconds * 8000000),
               '-l', str(gain), '-g', str(gain), '-a', '0', '-p', '0', '-B']
    report = {'requirements': ['KTR-4.2', 'KTR-4.2-F1'], 'command': command,
              'started_utc': datetime.now(timezone.utc).isoformat(),
              'external_tx_context': state, 'tx_controlled_by_script': False,
              'sample_rate_hz': 8000000, 'center_frequency_hz': 825300000,
              'gain_db': gain, 'requested_seconds': seconds,
              'tool_sha256': hashlib.sha256(tool.read_bytes()).hexdigest(),
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'product_acceptance': False, 'dbm_calibrated': False}
    (output / 'capture.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with (output / 'transfer.log').open('wb') as log:
        proc = subprocess.Popen(command, stdout=log, stderr=log)
        deadline = time.monotonic() + 5
        while proc.poll() is None and time.monotonic() < deadline:
            if raw.exists() and raw.stat().st_size >= 262144:
                print('RX_RECORDING', flush=True)
                break
            time.sleep(.05)
        try:
            report['returncode'] = proc.wait(timeout=seconds + 10)
        except subprocess.TimeoutExpired:
            proc.kill()
            report['returncode'] = proc.wait()
            report['timeout'] = True
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    report['bytes'] = raw.stat().st_size if raw.exists() else 0
    report['complete'] = report['returncode'] == 0 and report['bytes'] == seconds * 16000000
    log_text = (output / 'transfer.log').read_text(encoding='utf-8', errors='replace')
    overruns = re.findall(r'(\d+) overruns, longest (\d+) bytes', log_text)
    report['usb_overruns'] = max((int(v[0]) for v in overruns), default=None)
    report['longest_overrun_bytes'] = max((int(v[1]) for v in overruns), default=None)
    report['transport_valid'] = report['complete'] and report['usb_overruns'] == 0
    h = hashlib.sha256()
    if raw.exists():
        with raw.open('rb') as stream:
            for block in iter(lambda: stream.read(1048576), b''):
                h.update(block)
        report['raw_sha256'] = h.hexdigest()
        if report['bytes'] > 1048576:
            samples = np.memmap(raw, dtype=np.int8, mode='r')[1048576:]
            report['settled_rail_components'] = int(np.count_nonzero((samples == -128) | (samples == 127)))
            report['settled_components'] = len(samples)
    (output / 'capture.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return report['transport_valid']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=int, required=True)
    parser.add_argument('--state', required=True)
    parser.add_argument('--gain', type=int, default=16)
    args = parser.parse_args()
    raise SystemExit(0 if capture(args.output, args.seconds, args.state, args.gain) else 1)
