"""Reproduce one bounded parameter record using the matching current runtime."""

import argparse
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.operator_console.measurement_record import digest, replay_measurement, result_fields


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--sha256", help="Ölçüm günlüğünde kaydedilen arşiv SHA-256 özeti")
    args = parser.parse_args()
    try:
        result = replay_measurement(args.archive, expected_sha256=args.sha256)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(f"Ölçüm kaydı doğrulanamadı: {exc}")
        return 1
    print(json.dumps({
        "status": "reproduced", "archive_sha256": digest(args.archive.read_bytes()),
        "fields": result_fields(result), "accuracy_proven": False,
    }, ensure_ascii=False, allow_nan=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
