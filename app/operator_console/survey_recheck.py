"""One bounded automatic revisit pass; never infer absence from RX failure."""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path


def recheck_signals(survey, observations, audit_path, source_audit, callback):
    started = time.monotonic()
    state = "completed"
    with Path(audit_path).open("x", encoding="utf-8") as stream:
        def record(value):
            stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
        record({"type": "begin", "schema": "survey-recheck-v1",
                "source_audit": str(source_audit),
                "source_audit_sha256": hashlib.sha256(Path(source_audit).read_bytes()).hexdigest(),
                "count": len(observations)})
        for item in observations:
            if survey._cancel.is_set():
                state = "cancelled"
                break
            update = {"type": "check", "key": item["key"],
                      "frequency_hz": item["frequency_hz"]}
            try:
                verified = survey._verify_observation(item)
                if survey._cancel.is_set():
                    state = "cancelled"
                    break
                update.update(state="seen" if verified is not None else "not_seen",
                              verification=verified.get("verification") if verified else None)
            except Exception as exc:
                if survey._cancel.is_set():
                    state = "cancelled"
                    break
                update.update(state="error", error_code=str(getattr(exc, "code", type(exc).__name__)))
            update["checked_at"] = datetime.now(timezone.utc).isoformat()
            update["elapsed_seconds"] = time.monotonic() - started
            record(update)
            callback(update)
        record({"type": "end", "state": state, "elapsed_seconds": time.monotonic() - started})
    return state
