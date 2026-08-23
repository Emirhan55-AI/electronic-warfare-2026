"""Validate archived PHASE-04 evidence after the APP-D source relocation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "verification" / "phase04-source-relocation.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_relocation_manifest() -> dict[str, Any]:
    document = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("PHASE-04 relocation manifest is invalid")
    return document


def archived_implementation_digest(artifact_id: str, expected_digest: str) -> str:
    document = load_relocation_manifest()
    entry = next(
        (item for item in document.get("artifacts", ()) if item.get("artifact_id") == artifact_id),
        None,
    )
    if not isinstance(entry, dict):
        raise ValueError("PHASE-04 relocation entry is missing")
    if entry.get("historical_implementation_manifest_sha256") != expected_digest:
        raise ValueError("PHASE-04 historical implementation digest differs")
    if entry.get("runtime_equivalence_claimed") is not False:
        raise ValueError("PHASE-04 relocation must not claim runtime equivalence")
    for record in entry.get("protected_evidence", ()):
        path = ROOT / str(record.get("path", ""))
        if not path.is_file() or _sha256(path) != record.get("sha256"):
            raise ValueError("PHASE-04 protected evidence differs")
    return expected_digest

