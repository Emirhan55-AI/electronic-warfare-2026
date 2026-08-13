#!/usr/bin/env python3
"""Run the locked, non-selecting PHASE-04-R2 out-of-sample characterization once."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.parameters import characterize_phase04_r2_oos  # noqa: E402
from reference.parameters.evaluation import canonical_json_bytes  # noqa: E402


def _atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    target = args.output.resolve()
    if target == ROOT or ROOT in target.parents:
        parser.error("OOS output must remain outside the repository")
    payload = characterize_phase04_r2_oos()
    if payload.get("used_for_selection") is not False or payload.get("used_for_gate_changes") is not False:
        raise RuntimeError("OOS characterization cannot influence selection or gates")
    data = canonical_json_bytes(payload)
    _atomic(target, data)
    print(f"PHASE-04-R2 OOS SHA-256: {hashlib.sha256(data).hexdigest()}")
    print(f"PHASE-04-R2 OOS rows: {len(payload['rows'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
