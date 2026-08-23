"""Canonical Install SOP v1 entry point for Illustrator."""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Callable

from .install_contract import INSTALL_EXIT_OK, redact_payload
from .install_planning import build_install_report
from .install_service import apply_install, inspect_existing_install
from .install_verification import probe_target_import
from .runtime_probe import probe_broker, probe_typed_illustrator


def run_install_lifecycle(
    args: Any,
    *,
    platform_name: str | None = None,
    external_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    atomic_replace: Callable[[Any, Any], Any] = os.replace,
    python_probe: Callable[[str, float], dict[str, Any]] = probe_target_import,
    broker_probe: Callable[[str, float], dict[str, Any]] = probe_broker,
    illustrator_probe: Callable[[str, str, str, float], dict[str, Any]] = probe_typed_illustrator,
) -> int:
    """Execute one public lifecycle command and emit exactly one result document."""
    if args.command in {"status", "verify", "uninstall"}:
        report, exit_code = inspect_existing_install(
            verb=args.command,
            yes=args.yes,
            dry_run=args.dry_run,
            python=args.python,
            platform_name=platform_name,
            python_probe=python_probe,
            broker_probe=broker_probe,
            illustrator_probe=illustrator_probe,
        )
    else:
        report, exit_code = build_install_report(
            verb=args.command,
            dcc_path=args.dcc_path,
            python=args.python,
            dry_run=args.dry_run,
            platform_name=platform_name,
        )
        if exit_code == INSTALL_EXIT_OK and args.yes and not args.dry_run:
            report, exit_code = apply_install(
                report,
                runner=external_runner,
                replacer=atomic_replace,
                python_probe=python_probe,
                broker_probe=broker_probe,
                illustrator_probe=illustrator_probe,
            )
    if args.json:
        print(json.dumps(redact_payload(report), indent=2, sort_keys=True))
    else:
        print(f"Illustrator {args.command}: {report['status']} (exit {exit_code})")
    return exit_code


__all__ = ["run_install_lifecycle"]
