"""Filesystem and external-process ownership for Illustrator installation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from dcc_mcp_core.install_lifecycle import inspect_install_root

from .install_contract import redact

ExternalRunner = Callable[..., subprocess.CompletedProcess[str]]


def _replace_with_retry(replacer: Callable[[Any, Any], Any], source: Any, destination: Any) -> None:
    for attempt in range(3):
        try:
            replacer(source, destination)
            return
        except OSError:
            if attempt == 2:
                raise
            time.sleep(0.05 * (attempt + 1))


def _is_lock_error(error: OSError) -> bool:
    return isinstance(error, PermissionError) or getattr(error, "winerror", None) in {5, 32, 33}


def stage_bridge(
    *,
    executable: Path,
    staging_parent: Path,
    token: str,
    target: str,
    runner: ExternalRunner,
) -> tuple[Path | None, str | None]:
    """Generate a CEP bundle through adobepy with authentication only in env."""
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".illustrator-stage-", dir=str(staging_parent)))
    command = [
        str(executable),
        "install-bridge",
        "illustrator",
        "--dest",
        str(staging),
        "--kind",
        "cep",
        "--target",
        target,
        "--json",
    ]
    env = os.environ.copy()
    env["ADOBEPY_TOKEN"] = token
    try:
        result = runner(command, env=env, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        shutil.rmtree(staging, ignore_errors=True)
        return None, "adobepy bridge staging failed"
    output = f"{result.stdout or ''}\n{result.stderr or ''}"
    if token and token in output:
        shutil.rmtree(staging, ignore_errors=True)
        return None, "adobepy emitted sensitive output; installation stopped"
    if result.returncode != 0:
        shutil.rmtree(staging, ignore_errors=True)
        return None, "adobepy bridge staging failed"
    required = (
        staging / "CSXS" / "manifest.xml",
        staging / "dist" / "main.js",
        staging / "dist" / "dom.jsx",
        staging / "adobepy.config.js",
    )
    if not all(path.is_file() for path in required):
        shutil.rmtree(staging, ignore_errors=True)
        return None, "adobepy did not produce a complete Illustrator CEP bundle"
    return staging, None


def _file_receipts(root: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if path.name == "adobepy.config.js":
            files.append({"path": relative, "sensitive": True})
        else:
            files.append(
                {
                    "path": relative,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    return files


def load_receipt(receipt_path: Path, expected_bridge_root: Path) -> dict[str, Any] | None:
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(receipt, dict):
        return None
    if receipt.get("schema_version") != 1 or receipt.get("dcc_type") != "illustrator":
        return None
    try:
        recorded = Path(receipt["bridge_root"]).resolve()
    except (KeyError, OSError, TypeError):
        return None
    return receipt if recorded == expected_bridge_root.resolve() else None


def receipt_files_match(receipt: dict[str, Any], bridge_root: Path) -> bool:
    items = receipt.get("files")
    if not isinstance(items, list) or not items:
        return False
    root = bridge_root.resolve()
    paths: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            return False
        relative = item["path"]
        path = (bridge_root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            return False
        if not path.is_file():
            return False
        paths.add(relative)
        digest = item.get("sha256")
        if digest and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            return False
    return {"CSXS/manifest.xml", "adobepy.config.js"}.issubset(paths)


def commit_bridge(
    *,
    staging: Path,
    destination: Path,
    receipt_path: Path,
    receipt: dict[str, Any],
    replacer: Callable[[Any, Any], Any] = os.replace,
) -> tuple[str, str | None]:
    """Atomically swap the CEP directory and preserve the previous install on failure."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and inspect_install_root(destination).get("requires_restart"):
        shutil.rmtree(staging, ignore_errors=True)
        return "requires_restart", "A loaded native artifact prevents CEP replacement"
    backup = destination.with_name(f".{destination.name}.backup-{os.getpid()}")
    moved_previous = False
    try:
        if destination.exists():
            _replace_with_retry(replacer, destination, backup)
            moved_previous = True
        _replace_with_retry(replacer, staging, destination)
        receipt["files"] = _file_receipts(destination)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = receipt_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
        _replace_with_retry(replacer, temporary, receipt_path)
    except OSError as exc:
        if destination.exists():
            shutil.rmtree(destination, ignore_errors=True)
        if moved_previous and backup.exists():
            try:
                _replace_with_retry(replacer, backup, destination)
            except OSError:
                return (
                    "failed",
                    "CEP commit and rollback both failed; preserve the backup for repair",
                )
        shutil.rmtree(staging, ignore_errors=True)
        if _is_lock_error(exc):
            return "requires_restart", "CEP files are locked; restart Illustrator and retry"
        return "failed", "CEP commit failed and the previous installation was restored"
    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)
    return "ok", None


def remove_receipt_install(
    *,
    bridge_root: Path,
    receipt_path: Path,
) -> tuple[str, str | None]:
    receipt = load_receipt(receipt_path, bridge_root)
    if receipt is None:
        if not bridge_root.exists() and not receipt_path.exists():
            return "ok", None
        return "failed", "A valid Illustrator install receipt is required"
    if bridge_root.exists():
        inspection = inspect_install_root(bridge_root)
        if inspection.get("requires_restart"):
            return (
                "requires_restart",
                "A loaded artifact requires Illustrator restart before uninstall",
            )
        quarantine = bridge_root.with_name(f".{bridge_root.name}.uninstall-{os.getpid()}")
        try:
            os.replace(bridge_root, quarantine)
            shutil.rmtree(quarantine)
        except OSError as exc:
            if quarantine.exists() and not bridge_root.exists():
                os.replace(quarantine, bridge_root)
            if _is_lock_error(exc):
                return "requires_restart", "CEP files are locked; restart Illustrator and retry"
            return "failed", redact(exc)
    try:
        receipt_path.unlink(missing_ok=True)
    except OSError:
        return "failed", "CEP files were removed but the receipt could not be deleted"
    return "ok", None


__all__ = [
    "commit_bridge",
    "load_receipt",
    "receipt_files_match",
    "remove_receipt_install",
    "stage_bridge",
]
