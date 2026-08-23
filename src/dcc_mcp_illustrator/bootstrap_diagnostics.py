"""Bounded bootstrap diagnostics for the Illustrator adapter."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from .install_contract import redact, state_dir


def capture_bootstrap_error(stage: str, message: str) -> str:
    """Persist a redacted rolling diagnostic without raising into host startup."""
    safe_message = redact(message)
    path = state_dir() / "bootstrap-errors.json"
    errors: list[dict[str, str]] = []
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(current, dict) and isinstance(current.get("errors"), list):
            errors = [item for item in current["errors"] if isinstance(item, dict)][-19:]
    except (OSError, json.JSONDecodeError):
        pass
    errors.append(
        {
            "stage": str(stage),
            "message": safe_message,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"errors": errors}, indent=2), encoding="utf-8")
        os.replace(temporary, path)
    except OSError:
        pass
    return safe_message


__all__ = ["capture_bootstrap_error"]
