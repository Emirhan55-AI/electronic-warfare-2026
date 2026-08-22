"""Extract robust angle–power points from eight wrapped HackRF DF recordings."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.p0.recorded_df import RecordedDFError, analyze_recorded_df, write_recorded_df_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path, help="df_000…df_315 SigMF çiftlerinin dizini")
    parser.add_argument("--target-frequency", required=True, help="Ölçülecek gerçek hedef kanal frekansı (Hz)")
    parser.add_argument("--channel-bandwidth", required=True, help="Ölçülecek gerçek hedef kanal bant genişliği (Hz)")
    parser.add_argument("--output", required=True, type=Path, help="YÖN paneline yüklenecek yeni JSON raporu")
    parser.add_argument("--discard-seconds", type=float, default=1.0, help="Kayıt yeterliyse baştan atılacak süre (varsayılan: 1)")
    parser.add_argument("--maximum-frames", type=int, default=256, help="Her açı için en çok FFT karesi (varsayılan: 256)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata_paths = tuple(args.input_dir / f"df_{angle:03d}.sigmf-meta" for angle in range(0, 360, 45))
    try:
        report = analyze_recorded_df(
            metadata_paths,
            target_frequency_hz=args.target_frequency,
            channel_bandwidth_hz=args.channel_bandwidth,
            discard_seconds=args.discard_seconds,
            maximum_frames=args.maximum_frames,
        )
        write_recorded_df_report(args.output, report)
    except (RecordedDFError, FileExistsError, OSError, ValueError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
