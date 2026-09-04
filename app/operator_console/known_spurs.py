"""Load receiver-specific spur frequencies established by physical tests."""

from __future__ import annotations

import json
from pathlib import Path


DEFAULT_PROFILE_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "p0" / "hackrf_spurs.json"
)


def load_known_spurs(
    serial: str | None,
    path: Path | None = None,
) -> tuple[int, ...]:
    if serial is None:
        return ()
    profile_path = path or DEFAULT_PROFILE_PATH
    try:
        document = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ()
    profiles = document.get("profiles") if isinstance(document, dict) else None
    if not isinstance(profiles, list):
        return ()
    for profile in profiles:
        if not isinstance(profile, dict) or profile.get("serial") != serial:
            continue
        frequencies = profile.get("frequencies_hz")
        if not isinstance(frequencies, list):
            return ()
        parsed = []
        for value in frequencies:
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 1_000_000 <= value <= 6_000_000_000
            ):
                return ()
            parsed.append(value)
        return tuple(sorted(set(parsed)))
    return ()
