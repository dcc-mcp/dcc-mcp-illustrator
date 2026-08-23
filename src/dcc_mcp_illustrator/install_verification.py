"""Verify the installed adapter through the real Illustrator readiness path."""

from __future__ import annotations

import os
import subprocess
from typing import Any, Callable

from .runtime_probe import probe_broker, probe_typed_illustrator

PythonProbe = Callable[[str, float], dict[str, Any]]
BrokerProbe = Callable[[str, float], dict[str, Any]]
IllustratorProbe = Callable[[str, str, str, float], dict[str, Any]]


def probe_target_import(executable: str, timeout: float) -> dict[str, Any]:
    env = os.environ.copy()
    env.pop("ADOBEPY_TOKEN", None)
    env.pop("ADOBE_TOKEN", None)
    try:
        result = subprocess.run(
            [
                executable,
                "-c",
                "import dcc_mcp_illustrator; from adobe.illustrator import Illustrator",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return {"ok": False}
    return {"ok": result.returncode == 0}


def verify_illustrator_rpc(
    broker_url: str,
    *,
    python_executable: str,
    token: str,
    target: str = "default",
    python_probe: PythonProbe = probe_target_import,
    broker_probe: BrokerProbe = probe_broker,
    illustrator_probe: IllustratorProbe = probe_typed_illustrator,
) -> dict[str, Any]:
    if not python_probe(python_executable, 10.0).get("ok"):
        return {
            "directly_usable": False,
            "failure_stage": "target_import",
            "failure_reason": "The selected Python cannot import the adapter and typed Illustrator facade",
        }
    broker = broker_probe(broker_url, 5.0)
    if not broker.get("ok"):
        return {
            "directly_usable": False,
            "failure_stage": "broker_health",
            "failure_reason": "The adobepy broker health probe failed",
        }
    if int(broker.get("sessions", 0)) < 1:
        return {
            "directly_usable": False,
            "failure_stage": "cep_session",
            "failure_reason": "The broker has no connected Illustrator CEP session",
        }
    illustrator = illustrator_probe(broker_url, token, target, 5.0)
    if not illustrator.get("ok"):
        failure_stage = (
            "cep_session"
            if illustrator.get("failure_stage") == "cep_session"
            else "illustrator_rpc"
        )
        return {
            "directly_usable": False,
            "failure_stage": failure_stage,
            "failure_reason": (
                "The broker has no matching Illustrator CEP session"
                if failure_stage == "cep_session"
                else "A real typed Illustrator readiness RPC failed"
            ),
        }
    return {
        "directly_usable": True,
        "failure_stage": None,
        "failure_reason": None,
    }


__all__ = ["probe_target_import", "verify_illustrator_rpc"]
