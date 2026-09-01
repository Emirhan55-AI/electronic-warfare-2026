"""Compare complete TX-off and TX-on receive survey audit records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.operator_console.survey_evidence import compare_completed_surveys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path, help="TX kapalı tamamlanmış tarama kaydı")
    parser.add_argument("active", type=Path, help="TX açık tamamlanmış tarama kaydı")
    parser.add_argument("--output", type=Path, help="Yeni JSON kanıt dosyası; mevcut dosyanın üzerine yazılmaz")
    args = parser.parse_args()
    result = compare_completed_surveys(args.reference, args.active)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
