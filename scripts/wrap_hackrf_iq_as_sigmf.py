"""Wrap one raw HackRF signed-ci8 recording as a lossless SigMF pair."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.sigmf.hackrf import HackRFSigMFWrapError, wrap_hackrf_iq_as_sigmf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Ham HackRF ci8 I/Q dosyası")
    parser.add_argument("--sample-rate", required=True, help="Kayıt sırasında kullanılan gerçek örnekleme hızı (Hz)")
    parser.add_argument("--center-frequency", required=True, help="Kayıt sırasında kullanılan gerçek merkez frekansı (Hz)")
    parser.add_argument("--output-basename", required=True, type=Path, help="Uzantısız SigMF çıktı tabanı")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data_path, metadata_path = wrap_hackrf_iq_as_sigmf(
            args.input,
            sample_rate_hz=args.sample_rate,
            center_frequency_hz=args.center_frequency,
            output_basename=args.output_basename,
        )
    except (HackRFSigMFWrapError, FileExistsError, OSError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2
    print(data_path)
    print(metadata_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
