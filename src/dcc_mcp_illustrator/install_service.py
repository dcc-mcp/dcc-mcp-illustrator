"""Receipt-owned Illustrator install, verify, and uninstall operations."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .install_contract import (
    INSTALL_EXIT_INSTALL,
    INSTALL_EXIT_OK,
    INSTALL_EXIT_PREFLIGHT,
    INSTALL_EXIT_REQUIRES_RESTART,
    INSTALL_EXIT_VERIFY,
    package_version,
    state_dir,
)
from .install_discovery import cep_runtime_major, resolve_cep_extension_root
from .install_io import (
    commit_bridge,
    load_receipt,
    receipt_files_match,
    remove_receipt_install,
    stage_bridge,
)
from .install_verification import probe_target_import, verify_illustrator_rpc
from .runtime_probe import probe_broker, probe_typed_illustrator


def _installed_state(
    receipt_path: Path, bridge_root: Path | None
) -> tuple[str, dict[str, Any] | None]:
    receipt = load_receipt(receipt_path, bridge_root) if bridge_root is not None else None
    if receipt is not None:
        if bridge_root and bridge_root.is_dir() and receipt_files_match(receipt, bridge_root):
            return "installed", receipt
        return "repair", receipt
    if receipt_path.exists() or (bridge_root is not None and bridge_root.exists()):
        return "partial", None
    return "fresh", None


def _verification_recovery_step(
    report: dict[str, Any], verification: dict[str, Any]
) -> dict[str, Any]:
    stage = verification["failure_stage"]
    host = report["plan"].get("host")
    host = host if isinstance(host, dict) else {}
    if stage == "cep_session":
        csxs = cep_runtime_major(host.get("version"))
        if host.get("platform") == "Windows" and csxs is not None:
            command = [
                "reg.exe",
                "ADD",
                rf"HKCU\Software\Adobe\CSXS.{csxs}",
                "/v",
                "PlayerDebugMode",
                "/t",
                "REG_SZ",
                "/d",
                "1",
                "/f",
            ]
        elif host.get("platform") == "Darwin" and csxs is not None:
            command = [
                "defaults",
                "write",
                f"com.adobe.CSXS.{csxs}",
                "PlayerDebugMode",
                "1",
            ]
        else:
            command = ["dcc-mcp-illustrator", "verify", "--json"]
        return {
            "id": "enable-local-cep",
            "description": (
                "Enable the user-scoped Adobe CEP development policy for this host runtime; "
                "restart Illustrator, then rerun verify"
            ),
            "command": command,
            "why": (
                "The local bridge is unsigned and no Illustrator CEP session is connected; "
                "this command changes the user-scoped Adobe development policy"
            ),
        }
    if stage == "broker_health":
        return {
            "id": "start-adobepy-broker",
            "description": "Start the local adobepy broker with ADOBEPY_TOKEN already in the environment",
            "command": [report["plan"]["bridge"]["source"], "broker"],
            "why": verification["failure_reason"],
        }
    command = ["dcc-mcp-illustrator", "verify", "--json"]
    if isinstance(host.get("executable"), str) and host["executable"]:
        command.extend(["--dcc-path", host["executable"]])
    runtime = report["plan"].get("python")
    runtime = runtime if isinstance(runtime, dict) else {}
    if isinstance(runtime.get("executable"), str) and runtime["executable"]:
        command.extend(["--python", runtime["executable"]])
    return {
        "id": "retry-typed-verify",
        "description": "Retry the complete typed Illustrator readiness verification",
        "command": command,
        "why": verification["failure_reason"],
    }


def apply_install(
    report: dict[str, Any],
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]],
    replacer: Callable[[Any, Any], Any],
    python_probe: Callable[[str, float], dict[str, Any]],
    broker_probe: Callable[[str, float], dict[str, Any]],
    illustrator_probe: Callable[[str, str, str, float], dict[str, Any]],
) -> tuple[dict[str, Any], int]:
    """Stage and atomically commit one CEP bundle, then verify real readiness."""
    token = os.environ.get("ADOBEPY_TOKEN", "")
    source = Path(report["plan"]["bridge"]["source"])
    destination = Path(report["plan"]["bridge"]["destination"])
    staging, error = stage_bridge(
        executable=source,
        staging_parent=destination.parent,
        token=token,
        target=report["plan"]["bridge"]["target"],
        runner=runner,
    )
    if staging is None:
        report.update(status="failed", mode="apply", exit_code=INSTALL_EXIT_INSTALL)
        report["steps"][1] = {"id": "stage_cep", "status": "failed", "message": error}
        report["verify"] = {
            "directly_usable": False,
            "failure_stage": "stage_cep",
            "failure_reason": error,
        }
        report["next_steps"] = []
        return report, INSTALL_EXIT_INSTALL

    receipt_path = Path(report["receipt_path"])
    previous = load_receipt(receipt_path, destination)
    receipt = {
        "schema_version": 1,
        "dcc_type": "illustrator",
        "adapter_version": report["adapter_version"],
        "core_version": report["core_version"],
        "host": report["plan"]["host"],
        "python": report["plan"]["python"],
        "bridge_root": str(destination),
        "bridge_kind": "cep",
        "target": report["plan"]["bridge"]["target"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "upgrade_from": previous.get("adapter_version") if previous else None,
    }
    commit_status, commit_error = commit_bridge(
        staging=staging,
        destination=destination,
        receipt_path=receipt_path,
        receipt=receipt,
        replacer=replacer,
    )
    if commit_status != "ok":
        exit_code = (
            INSTALL_EXIT_REQUIRES_RESTART
            if commit_status == "requires_restart"
            else INSTALL_EXIT_INSTALL
        )
        report.update(status=commit_status, mode="apply", exit_code=exit_code)
        report["steps"][1] = {
            "id": "stage_cep",
            "status": commit_status,
            "message": commit_error,
        }
        report["verify"] = {
            "directly_usable": False,
            "failure_stage": "commit",
            "failure_reason": commit_error,
        }
        report["next_steps"] = []
        return report, exit_code

    verification = verify_illustrator_rpc(
        os.environ.get("ADOBEPY_BROKER_URL", "http://127.0.0.1:47391"),
        python_executable=report["plan"]["python"]["executable"],
        token=token,
        target=report["plan"]["bridge"]["target"],
        python_probe=python_probe,
        broker_probe=broker_probe,
        illustrator_probe=illustrator_probe,
    )
    report.update(mode="apply", installed_state="installed")
    report["steps"][0] = {"id": "preflight", "status": "ok"}
    report["steps"][1] = {"id": "stage_cep", "status": "ok"}
    report["verify"] = verification
    if verification["directly_usable"]:
        report.update(status="ok", exit_code=INSTALL_EXIT_OK)
        report["steps"][2] = {"id": "verify", "status": "ok"}
        report["next_steps"] = []
        return report, INSTALL_EXIT_OK

    report.update(status="failed", exit_code=INSTALL_EXIT_VERIFY)
    report["steps"][2] = {"id": "verify", "status": "failed"}
    report["next_steps"] = [_verification_recovery_step(report, verification)]
    return report, INSTALL_EXIT_VERIFY


def inspect_existing_install(
    *,
    verb: str,
    yes: bool = False,
    dry_run: bool = False,
    python: str = "",
    platform_name: str | None = None,
    python_probe: Callable[[str, float], dict[str, Any]] = probe_target_import,
    broker_probe: Callable[[str, float], dict[str, Any]] = probe_broker,
    illustrator_probe: Callable[[str, str, str, float], dict[str, Any]] = probe_typed_illustrator,
) -> tuple[dict[str, Any], int]:
    """Inspect, verify, or remove only the bridge bound by a valid receipt."""
    system = platform_name or platform.system()
    lifecycle_state = state_dir()
    receipt_path = lifecycle_state / "receipts" / "illustrator.json"
    bridge_root = resolve_cep_extension_root(system)
    installed_state, receipt = _installed_state(receipt_path, bridge_root)

    if installed_state == "installed" and not os.environ.get("ADOBEPY_TOKEN"):
        verification = {
            "directly_usable": False,
            "failure_stage": "authentication",
            "failure_reason": "ADOBEPY_TOKEN must be configured in the environment",
        }
    elif installed_state == "installed" and receipt is not None:
        receipt_python = receipt.get("python")
        receipt_python = receipt_python if isinstance(receipt_python, dict) else {}
        verification = verify_illustrator_rpc(
            os.environ.get("ADOBEPY_BROKER_URL", "http://127.0.0.1:47391"),
            python_executable=python or receipt_python.get("executable", sys.executable),
            token=os.environ["ADOBEPY_TOKEN"],
            target=str(receipt.get("target") or os.environ.get("ADOBEPY_TARGET") or "default"),
            python_probe=python_probe,
            broker_probe=broker_probe,
            illustrator_probe=illustrator_probe,
        )
    elif installed_state == "repair":
        verification = {
            "directly_usable": False,
            "failure_stage": "receipt_integrity",
            "failure_reason": "The receipted Illustrator CEP bridge needs repair",
        }
    elif installed_state == "partial":
        verification = {
            "directly_usable": False,
            "failure_stage": "partial_state",
            "failure_reason": "Unreceipted Illustrator CEP state cannot be mutated safely",
        }
    else:
        verification = {
            "directly_usable": False,
            "failure_stage": "install_state",
            "failure_reason": "No receipt-backed Illustrator bridge is installed",
        }

    report: dict[str, Any] = {
        "schema_version": 1,
        "status": "partial" if installed_state in {"partial", "repair"} else "ok",
        "dcc_type": "illustrator",
        "adapter_version": package_version("dcc-mcp-illustrator"),
        "core_version": package_version("dcc-mcp-core"),
        "steps": [{"id": "inspect_receipt", "status": installed_state}],
        "next_steps": [],
        "receipt_path": str(receipt_path) if receipt else None,
        "verify": verification,
        "verb": verb,
        "mode": (
            "plan"
            if verb in {"status", "verify"} or dry_run or (verb == "uninstall" and not yes)
            else "apply"
        ),
        "exit_code": INSTALL_EXIT_OK,
        "installed_state": installed_state,
    }
    if (
        receipt is not None
        and not verification["directly_usable"]
        and verification["failure_stage"]
        in {"target_import", "broker_health", "cep_session", "illustrator_rpc"}
    ):
        receipt_host = receipt.get("host")
        receipt_host = dict(receipt_host) if isinstance(receipt_host, dict) else {}
        receipt_host.setdefault("platform", system)
        receipt_python = receipt.get("python")
        receipt_python = dict(receipt_python) if isinstance(receipt_python, dict) else {}
        recovery_report = {
            "plan": {
                "host": receipt_host,
                "python": receipt_python,
                "bridge": {"source": os.environ.get("ADOBEPY_CLI") or "adobepy"},
            }
        }
        report["next_steps"] = [_verification_recovery_step(recovery_report, verification)]
    if verb == "status":
        return report, INSTALL_EXIT_OK
    if verb == "verify":
        if installed_state != "installed" or verification["failure_stage"] == "authentication":
            exit_code = INSTALL_EXIT_PREFLIGHT
        else:
            exit_code = INSTALL_EXIT_OK if verification["directly_usable"] else INSTALL_EXIT_VERIFY
        report.update(status="ok" if exit_code == 0 else "failed", exit_code=exit_code)
        report["steps"].append(
            {"id": "verify_illustrator_rpc", "status": "ok" if exit_code == 0 else "failed"}
        )
        return report, exit_code
    if verb != "uninstall":
        return report, INSTALL_EXIT_PREFLIGHT
    if not yes or dry_run:
        report.update(status="planned", mode="plan")
        report["steps"].append({"id": "uninstall", "status": "planned"})
        report["next_steps"] = [
            {
                "id": "execute-uninstall",
                "description": "Remove only the receipt-owned Illustrator CEP bridge",
                "command": ["dcc-mcp-illustrator", "uninstall", "--json", "--yes"],
                "why": "Uninstall plans by default and requires explicit confirmation",
            }
        ]
        return report, INSTALL_EXIT_OK
    if installed_state == "fresh":
        report.update(status="ok", installed_state="fresh", receipt_path=None)
        report["steps"].append({"id": "uninstall", "status": "skipped"})
        return report, INSTALL_EXIT_OK
    if receipt is None or bridge_root is None:
        report.update(status="failed", exit_code=INSTALL_EXIT_PREFLIGHT)
        report["steps"].append({"id": "uninstall", "status": "failed"})
        return report, INSTALL_EXIT_PREFLIGHT
    remove_status, remove_error = remove_receipt_install(
        bridge_root=bridge_root,
        receipt_path=receipt_path,
    )
    if remove_status != "ok":
        exit_code = (
            INSTALL_EXIT_REQUIRES_RESTART
            if remove_status == "requires_restart"
            else INSTALL_EXIT_INSTALL
        )
        report.update(status=remove_status, exit_code=exit_code)
        report["steps"].append(
            {"id": "uninstall", "status": remove_status, "message": remove_error}
        )
        return report, exit_code
    report.update(
        status="ok",
        exit_code=INSTALL_EXIT_OK,
        receipt_path=None,
        installed_state="fresh",
    )
    report["steps"].append({"id": "uninstall", "status": "ok"})
    report["verify"] = {
        "directly_usable": False,
        "failure_stage": "not_installed",
        "failure_reason": "The receipt-owned Illustrator bridge was uninstalled",
    }
    return report, INSTALL_EXIT_OK


__all__ = ["apply_install", "inspect_existing_install"]
