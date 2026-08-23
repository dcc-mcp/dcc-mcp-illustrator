"""Install SOP v1 compatibility values for the Illustrator adapter."""

from __future__ import annotations

import importlib.metadata
import os
import re
from pathlib import Path

try:
    from dcc_mcp_core.deployment import (
        INSTALL_EXIT_ACQUIRE,
        INSTALL_EXIT_INSTALL,
        INSTALL_EXIT_OK,
        INSTALL_EXIT_PREFLIGHT,
        INSTALL_EXIT_REQUIRES_RESTART,
        INSTALL_EXIT_VERIFY,
    )
except ImportError:  # Core #2320 compatibility until the shared exports are released.
    INSTALL_EXIT_OK = 0
    INSTALL_EXIT_PREFLIGHT = 10
    INSTALL_EXIT_ACQUIRE = 20
    INSTALL_EXIT_INSTALL = 30
    INSTALL_EXIT_VERIFY = 40
    INSTALL_EXIT_REQUIRES_RESTART = 50

MIN_CORE_VERSION = "0.19.91"
MIN_PYTHON_VERSION = (3, 9)
MIN_ILLUSTRATOR_VERSION = (23, 0)


def package_version(distribution: str, default: str = "unknown") -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return default


def version_tuple(value: str | None) -> tuple[int, ...]:
    if not value:
        return ()
    match = re.match(r"\s*(\d+(?:\.\d+)*)", value)
    return tuple(int(part) for part in match.group(1).split(".")) if match else ()


def redact(value: object) -> str:
    """Remove environment secrets and URL userinfo from public diagnostics."""
    result = str(value)
    for name in ("ADOBEPY_TOKEN", "ADOBE_TOKEN"):
        secret = os.environ.get(name, "")
        if secret:
            result = result.replace(secret, "<redacted>")
    return re.sub(r"((?:https?|wss?)://)[^/@\s]+@", r"\1<redacted>@", result, flags=re.I)


def redact_payload(value: object) -> object:
    """Recursively redact strings immediately before public JSON serialization."""
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
    configured = os.environ.get("DCC_MCP_ILLUSTRATOR_INSTALL_STATE_DIR")
    return Path(configured).expanduser() if configured else Path.home() / ".dcc-mcp" / "illustrator"


__all__ = [
    "INSTALL_EXIT_ACQUIRE",
    "INSTALL_EXIT_INSTALL",
    "INSTALL_EXIT_OK",
    "INSTALL_EXIT_PREFLIGHT",
    "INSTALL_EXIT_REQUIRES_RESTART",
    "INSTALL_EXIT_VERIFY",
    "MIN_CORE_VERSION",
    "MIN_ILLUSTRATOR_VERSION",
    "MIN_PYTHON_VERSION",
    "package_version",
    "redact",
    "redact_payload",
    "state_dir",
    "version_tuple",
]
