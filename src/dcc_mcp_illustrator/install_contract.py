"""Pinned shared Adapter Install SOP v1 contract."""

from __future__ import annotations

import importlib.metadata
import os
import re
from pathlib import Path

from dcc_mcp_core.deployment import install_sop as _install_sop

SCHEMA_VERSION = _install_sop.INSTALL_SOP_SCHEMA_VERSION
EXIT_OK = _install_sop.INSTALL_EXIT_OK
EXIT_PREFLIGHT = _install_sop.INSTALL_EXIT_PREFLIGHT
EXIT_ACQUIRE = _install_sop.INSTALL_EXIT_ACQUIRE
EXIT_INSTALL = _install_sop.INSTALL_EXIT_INSTALL
EXIT_VERIFY = _install_sop.INSTALL_EXIT_VERIFY
EXIT_REQUIRES_RESTART = _install_sop.INSTALL_EXIT_REQUIRES_RESTART
INSTALL_SOP_SCHEMA_ID = "https://dcc-mcp.github.io/schemas/adapter-install-sop-v1.schema.json"
INSTALL_SOP_SCHEMA_SIZE = 4_261
INSTALL_SOP_SCHEMA_SHA256 = "3ca25788439917b4d4c0617230a762f9797756b5b54f45c8c4149f975b90f904"
INSTALL_EXIT_OK = EXIT_OK
INSTALL_EXIT_PREFLIGHT = EXIT_PREFLIGHT
INSTALL_EXIT_ACQUIRE = EXIT_ACQUIRE
INSTALL_EXIT_INSTALL = EXIT_INSTALL
INSTALL_EXIT_VERIFY = EXIT_VERIFY
INSTALL_EXIT_REQUIRES_RESTART = EXIT_REQUIRES_RESTART
MIN_CORE_VERSION = "0.20.14"
MIN_PYTHON_VERSION = (3, 9)
MIN_ILLUSTRATOR_VERSION = (23, 0)


def runtime_core_version() -> str:
    import dcc_mcp_core

    return str(getattr(dcc_mcp_core, "__version__", "unavailable"))


def package_version(distribution: str, default: str = "unknown") -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return default


def version_tuple(value: str | None) -> tuple[int, ...]:
    if not isinstance(value, str) or len(value) > 39:
        return ()
    match = re.fullmatch(r"(0|[1-9][0-9]{0,8})(?:\.(0|[1-9][0-9]{0,8})){0,3}", value)
    return tuple(int(part) for part in value.split(".")) if match else ()


def redact(value: object) -> str:
    result = str(value)
    for name in ("ADOBEPY_TOKEN", "ADOBE_TOKEN"):
        secret = os.environ.get(name, "")
        if secret:
            result = result.replace(secret, "<redacted>")
    return re.sub(r"((?:https?|wss?)://)[^/@\s]+@", r"\1<redacted>@", result, flags=re.I)


def redact_payload(value: object) -> object:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_payload(item) for item in value)
    if isinstance(value, dict):
        return {key: redact_payload(item) for key, item in value.items()}
    return value


def state_dir() -> Path:
    configured = os.environ.get("DCC_MCP_ILLUSTRATOR_STATE_DIR") or os.environ.get(
        "DCC_MCP_ILLUSTRATOR_INSTALL_STATE_DIR"
    )
    return Path(configured).expanduser() if configured else Path.home() / ".dcc-mcp" / "illustrator"


__all__ = [
    "EXIT_ACQUIRE",
    "EXIT_INSTALL",
    "EXIT_OK",
    "EXIT_PREFLIGHT",
    "EXIT_REQUIRES_RESTART",
    "EXIT_VERIFY",
    "INSTALL_SOP_SCHEMA_ID",
    "INSTALL_SOP_SCHEMA_SHA256",
    "INSTALL_SOP_SCHEMA_SIZE",
    "INSTALL_EXIT_ACQUIRE",
    "INSTALL_EXIT_INSTALL",
    "INSTALL_EXIT_OK",
    "INSTALL_EXIT_PREFLIGHT",
    "INSTALL_EXIT_REQUIRES_RESTART",
    "INSTALL_EXIT_VERIFY",
    "MIN_CORE_VERSION",
    "MIN_ILLUSTRATOR_VERSION",
    "MIN_PYTHON_VERSION",
    "SCHEMA_VERSION",
    "package_version",
    "redact",
    "redact_payload",
    "runtime_core_version",
    "state_dir",
    "version_tuple",
]
