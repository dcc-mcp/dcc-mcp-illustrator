"""Preflight and plan construction for Illustrator Install SOP v1."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .install_contract import (
    INSTALL_EXIT_ACQUIRE,
    INSTALL_EXIT_OK,
    INSTALL_EXIT_PREFLIGHT,
    MIN_CORE_VERSION,
    MIN_ILLUSTRATOR_VERSION,
    MIN_PYTHON_VERSION,
    package_version,
    state_dir,
    version_tuple,
)
from .install_discovery import (
    discover_illustrator_executable,
    host_version,
    resolve_cep_extension_root,
)
from .install_io import load_receipt, receipt_files_match


def _host_supported(version: str | None) -> bool:
    value = version_tuple(version)
    if not value:
        return False
    if value[0] >= 2000:
        return value[0] >= 2019
    return value >= MIN_ILLUSTRATOR_VERSION


def _python_version(executable: Path) -> str | None:
    try:
        result = subprocess.run(
            [str(executable), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    value = (result.stdout or result.stderr).strip()
    return value.removeprefix("Python ")


def _adobepy_cli() -> Path | None:
    configured = os.environ.get("ADOBEPY_CLI")
    if configured:
        return Path(configured).expanduser()
    discovered = shutil.which("adobepy")
    return Path(discovered) if discovered else None


def _selected_interpreter(verb: str, explicit: str, receipt: dict[str, Any] | None) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    configured = os.environ.get("DCC_MCP_INSTALL_PYTHON")
    if configured:
        return Path(configured).expanduser()
    if verb == "upgrade" and receipt:
        runtime = receipt.get("python")
        if isinstance(runtime, dict) and runtime.get("executable"):
            return Path(runtime["executable"]).expanduser()
    return Path(sys.executable)


def build_install_report(
    *,
    verb: str,
    dcc_path: str,
    python: str,
    dry_run: bool,
    platform_name: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Resolve a complete read-only plan without creating target or state files."""
    system = platform_name or platform.system()
    lifecycle_state = state_dir()
    receipt_path = lifecycle_state / "receipts" / "illustrator.json"
    bridge_root = resolve_cep_extension_root(system)
    receipt = load_receipt(receipt_path, bridge_root) if bridge_root is not None else None
    receipt_host = receipt.get("host") if receipt else None
    receipt_host = receipt_host if isinstance(receipt_host, dict) else {}

    if dcc_path:
        host = Path(dcc_path).expanduser()
        detected_host_version = host_version(host)
    elif verb == "upgrade" and receipt_host.get("executable"):
        host = Path(receipt_host["executable"]).expanduser()
        detected_host_version = str(receipt_host.get("version") or "") or None
    else:
        discovered, detected_host_version = discover_illustrator_executable(system)
        host = discovered or Path()

    interpreter = _selected_interpreter(verb, python, receipt)
    python_version = _python_version(interpreter) if interpreter.is_file() else None
    core_version = package_version("dcc-mcp-core")
    adobepy_cli = _adobepy_cli()
    target = os.environ.get("ADOBEPY_TARGET", "default").strip() or "default"

    if receipt:
        installed_state = (
            "installed"
            if bridge_root and bridge_root.is_dir() and receipt_files_match(receipt, bridge_root)
            else "repair"
        )
    elif receipt_path.exists() or (bridge_root is not None and bridge_root.exists()):
        installed_state = "partial"
    else:
        installed_state = "fresh"

    failures: list[tuple[str, str]] = []
    broker_url = os.environ.get("ADOBEPY_BROKER_URL", "http://127.0.0.1:47391")
    parsed_broker = urlparse(broker_url)
    if parsed_broker.username is not None or parsed_broker.password is not None:
        failures.append(
            (
                "security",
                "Broker URL credentials are forbidden; use ADOBEPY_TOKEN in the environment",
            )
        )
    if installed_state == "partial":
        failures.append(("partial_state", "Unreceipted or incomplete CEP state requires repair"))
    if version_tuple(core_version) < version_tuple(MIN_CORE_VERSION):
        failures.append(("core_version", f"dcc-mcp-core {MIN_CORE_VERSION} or newer is required"))
    if bridge_root is None:
        failures.append(
            ("platform", "Illustrator host integration supports Windows and macOS only")
        )
    if not host.is_file():
        failures.append(("host", "Illustrator executable was not found"))
    elif not _host_supported(detected_host_version):
        failures.append(("host_version", "Illustrator 23.0 (2019) or newer is required"))
    if python_version is None:
        failures.append(("python", "Target Python could not be executed"))
    elif version_tuple(python_version)[:2] < MIN_PYTHON_VERSION:
        failures.append(("python_version", "Python 3.9 or newer is required"))
    if adobepy_cli is None or not adobepy_cli.is_file():
        failures.append(
            ("acquire", "A supported adobepy runtime CLI is required to stage the CEP bridge")
        )
    if not os.environ.get("ADOBEPY_TOKEN"):
        failures.append(("authentication", "ADOBEPY_TOKEN must be configured in the environment"))

    failure_stage, failure_reason = failures[0] if failures else (None, None)
    exit_code = (
        INSTALL_EXIT_ACQUIRE
        if failure_stage == "acquire"
        else INSTALL_EXIT_PREFLIGHT
        if failure_stage
        else INSTALL_EXIT_OK
    )
    host_value = str(host) if host.is_file() else None
    python_value = str(interpreter) if interpreter.is_file() else None
    retry = ["dcc-mcp-illustrator", verb, "--json", "--dry-run"]
    if host_value:
        retry.extend(["--dcc-path", host_value])
    if python_value:
        retry.extend(["--python", python_value])
    execute = ["dcc-mcp-illustrator", verb, "--json", "--yes"]
    if host_value:
        execute.extend(["--dcc-path", host_value])
    if python_value:
        execute.extend(["--python", python_value])

    next_steps = []
    if failure_stage:
        next_steps.append(
            {
                "id": f"retry-{verb}-plan",
                "description": f"Retry the Illustrator {verb} plan after resolving preflight",
                "command": retry,
                "why": failure_reason,
            }
        )
    elif verb in {"install", "upgrade"}:
        next_steps.append(
            {
                "id": f"execute-{verb}",
                "description": f"Apply the validated Illustrator {verb} plan",
                "command": execute,
                "why": "Install and upgrade plan by default and require explicit --yes to mutate",
            }
        )

    report: dict[str, Any] = {
        "schema_version": 1,
        "status": "failed" if failure_stage else "planned",
        "dcc_type": "illustrator",
        "adapter_version": package_version("dcc-mcp-illustrator"),
        "core_version": core_version,
        "steps": [
            {"id": "preflight", "status": "failed" if failure_stage else "ok"},
            {"id": "stage_cep", "status": "blocked" if failure_stage else "planned"},
            {"id": "verify", "status": "blocked" if failure_stage else "planned"},
        ],
        "next_steps": next_steps,
        "receipt_path": str(receipt_path),
        "verify": {
            "directly_usable": False,
            "failure_stage": failure_stage or "not_applied",
            "failure_reason": failure_reason or "The validated plan has not been applied",
        },
        "verb": verb,
        "mode": "plan",
        "exit_code": exit_code,
        "installed_state": installed_state,
        "plan": {
            "host": {
                "executable": host_value,
                "version": detected_host_version,
                "platform": system,
            },
            "python": {"executable": python_value, "version": python_version},
            "bridge": {
                "kind": "cep",
                "destination": str(bridge_root) if bridge_root else None,
                "source": str(adobepy_cli) if adobepy_cli and adobepy_cli.is_file() else None,
                "target": target,
            },
        },
    }
    return report, exit_code


__all__ = ["build_install_report"]
