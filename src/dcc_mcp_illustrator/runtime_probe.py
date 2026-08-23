"""Redacted broker and typed Illustrator readiness probes."""

from __future__ import annotations

import json
from urllib.request import Request, urlopen

from .install_contract import redact
from .runtime import probe_illustrator


def probe_broker(broker_url: str, timeout: float) -> dict:
    url = f"{broker_url.rstrip('/')}/health"
    try:
        with urlopen(Request(url, method="GET"), timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - public result is bounded and redacted
        return {"ok": False, "sessions": 0, "url": redact(url), "error": redact(exc)}
    return {
        "ok": payload.get("status") == "ok",
        "sessions": int(payload.get("sessions", 0)),
        "url": redact(url),
    }


def probe_typed_illustrator(broker_url: str, token: str, target: str, timeout: float) -> dict:
    status = probe_illustrator(
        broker_url=broker_url,
        token=token,
        target=target,
        timeout=timeout,
    )
    return {
        "ok": status.ready,
        "version": status.version,
        "failure_stage": (
            "cep_session"
            if status.reason == "Illustrator bridge session is not connected"
            else "illustrator_rpc"
        )
        if not status.ready
        else None,
        "error": redact(status.reason) if not status.ready else None,
    }


__all__ = ["probe_broker", "probe_typed_illustrator"]
