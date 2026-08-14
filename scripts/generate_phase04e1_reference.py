"""Generate or check deterministic PHASE-04-E1 clean reference evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.parameters.operator_reference import build_golden_reference, canonical_json_bytes
OUTPUT = ROOT / "results" / "evidence" / "phase04e1" / "golden-parameters.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    expected = canonical_json_bytes(build_golden_reference())
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(expected)
        return 0
    return 0 if OUTPUT.exists() and OUTPUT.read_bytes() == expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
