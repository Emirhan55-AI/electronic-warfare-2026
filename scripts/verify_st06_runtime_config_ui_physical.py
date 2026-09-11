"""Exercise the operator view-model CFAR controls against the connected card."""
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QGuiApplication
from algorithms.p0.detection_config import (
    DetectionProfile, NORMAL_DEFAULT, WEAK_DEFAULT, exchange_profile,
)
from app.operator_console.quick_view_model import OperatorViewModel


def wait(app, view, timeout=5.0):
    deadline = time.monotonic() + timeout
    while view.busy and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    if view.busy:
        raise TimeoutError('Arayüz kart ayarı zaman aşımına uğradı.')


def main(output: Path):
    app = QGuiApplication.instance() or QGuiApplication([])
    view = OperatorViewModel()
    snapshots = {}
    fft_checks = {}
    try:
        view.refreshCardDetectionProfile()
        wait(app, view)
        snapshots['read'] = dict(view.cardDetectionProfile)
        if not view.cardDetectionProfile['ready']:
            raise RuntimeError(view.cardDetectionProfile['message'])

        if not view.applyCardDetectionProfile('9,0', '3,0'):
            raise RuntimeError(view.cardDetectionProfile['message'])
        wait(app, view)
        snapshots['applied'] = dict(view.cardDetectionProfile)
        card_applied = exchange_profile('192.168.7.2')
        if card_applied.runtime_fft_supported:
            for size in (8192, 16384, 4096):
                if not view.applyCardDetectionProfileWithFFT(size, '9,0', '3,0'):
                    raise RuntimeError(view.cardDetectionProfile['message'])
                wait(app, view)
                readback = exchange_profile('192.168.7.2')
                snapshots[f'fft_{size}'] = dict(view.cardDetectionProfile)
                fft_checks[f'ui_fft_{size}_reached_card'] = (
                    readback.fft_size == size
                    and view.cardDetectionProfile['fftSize'] == size
                    and view.cardDetectionProfile['generation'] == readback.generation
                )

        if not view.restoreCardDetectionProfile():
            raise RuntimeError(view.cardDetectionProfile['message'])
        wait(app, view)
        snapshots['restored'] = dict(view.cardDetectionProfile)
        card_restored = exchange_profile('192.168.7.2')
    finally:
        actual = exchange_profile('192.168.7.2')
        if (actual.alpha_q32, actual.weak_alpha_q32, actual.fft_size) != (NORMAL_DEFAULT, WEAK_DEFAULT, 4096):
            actual = exchange_profile('192.168.7.2', profile=DetectionProfile(
                actual.generation, NORMAL_DEFAULT, WEAK_DEFAULT, 4096, actual.runtime_fft_supported))
        view.shutdown()

    checks = {
        **fft_checks,
        'ui_read_ready': snapshots['read']['ready'],
        'ui_apply_reached_card': (card_applied.alpha_q32, card_applied.weak_alpha_q32) ==
            (9 * (1 << 32), 3 * (1 << 32)),
        'ui_apply_generation_visible': snapshots['applied']['generation'] == card_applied.generation,
        'ui_restore_reached_card': (card_restored.alpha_q32, card_restored.weak_alpha_q32) ==
            (NORMAL_DEFAULT, WEAK_DEFAULT),
        'ui_restore_generation_visible': snapshots['restored']['generation'] == card_restored.generation,
        'final_card_defaults': (actual.alpha_q32, actual.weak_alpha_q32) ==
            (NORMAL_DEFAULT, WEAK_DEFAULT),
    }
    result = {
        'schema': 'phase08-st06-runtime-config-ui-physical-v1',
        'status': 'passed' if all(checks.values()) else 'failed',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'OperatorViewModel read/apply/restore slots over the real card control service',
        'snapshots': snapshots,
        'card_applied': card_applied.__dict__,
        'card_restored': card_restored.__dict__,
        'checks': checks,
        'hackrf_used': False,
        'rf_acceptance': False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'checks': checks}, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(0 if main(args.output)['status'] == 'passed' else 1)
