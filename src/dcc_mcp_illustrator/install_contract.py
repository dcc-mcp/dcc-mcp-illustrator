"""Pinned shared Adapter Install SOP v1 contract."""

from __future__ import annotations

import importlib.metadata
import os
import re
from pathlib import Path

from dcc_mcp_core.deployment import install_sop as _install_sop


def _report_schema_version() -> int:
    """Return the value every report document's ``schema_version`` field must carry.

    This is an independent counter from the published schema *artifact* revision.
    ``INSTALL_SOP_SCHEMA_VERSION`` (now ``INSTALL_SOP_SCHEMA_REVISION``) names
    the artifact and is 2 since core 0.20.34, while the artifact pins a report's
    ``schema_version`` to 1 because revisions only add optional members.
    Emitting the artifact revision made every status/verify/install report fail
    validation against the very schema it claims to follow, so read the value
    from the schema instead of copying the artifact revision.

    Core 0.20.41 answers this directly with
    ``install_sop_report_schema_version()``. Cores in the supported range below
    that expose only ``load_install_sop_schema``, whose ``const`` is the same
    answer read one level down, so the fallback keeps the declared floor working.

    Neither read may propagate: a partially installed, tampered, or otherwise
    unhealthy Core is exactly the situation this CLI exists to report on, so a
    failure to read the document degrades to ``1`` rather than raising at import.
    """
    # ``KeyError`` is how a misshapen document reports itself -- it is what the
    # bare ``loader()[...][...][...]`` chain below raises when ``properties``,
    # ``schema_version`` or ``const`` is absent. Catching it keeps the existing
    # silent-degradation contract instead of letting an import-time error take
    # the whole CLI down. Deliberately no logging here: the local path already
    # degraded silently to the fallback before this change.
    reader = getattr(_install_sop, "install_sop_report_schema_version", None)
    if callable(reader):
        try:
            return int(reader())
        except (RuntimeError, OSError, ValueError, TypeError, KeyError):
            # Fall through to the local read rather than losing the report.
            pass
    loader = getattr(_install_sop, "load_install_sop_schema", None)
    if callable(loader):
        try:
            return int(loader()["properties"]["schema_version"]["const"])
        except (RuntimeError, OSError, ValueError, TypeError, KeyError):
            return 1
    return 1


SCHEMA_VERSION = _report_schema_version()
EXIT_OK = _install_sop.INSTALL_EXIT_OK
EXIT_PREFLIGHT = _install_sop.INSTALL_EXIT_PREFLIGHT
EXIT_ACQUIRE = _install_sop.INSTALL_EXIT_ACQUIRE
EXIT_INSTALL = _install_sop.INSTALL_EXIT_INSTALL
EXIT_VERIFY = _install_sop.INSTALL_EXIT_VERIFY
EXIT_REQUIRES_RESTART = _install_sop.INSTALL_EXIT_REQUIRES_RESTART
INSTALL_SOP_SCHEMA_ID = "https://dcc-mcp.github.io/schemas/adapter-install-sop-v1.schema.json"

# Every published revision of that artifact this adapter accepts, as
# ``(size, sha256)`` pairs. Core 0.20.30 rewrote ``-v1`` in place -- same ``$id``,
# different bytes -- so the id alone no longer names one byte sequence: releases
# up to 0.20.29 ship 4261 bytes, and 0.20.30 and later ship the frozen 4899-byte
# copy. Accepting both keeps the declared core range installable while still
# refusing any byte sequence this adapter has not reviewed.
INSTALL_SOP_SCHEMA_ANCHORS = (
    (4_261, "3ca25788439917b4d4c0617230a762f9797756b5b54f45c8c4149f975b90f904"),
    (4_899, "2b3a8a101384a5163c7569c4a2b0de6586c672c5ee291735f94334a33b7d37a0"),
)
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
    "INSTALL_SOP_SCHEMA_ANCHORS",
    "INSTALL_SOP_SCHEMA_ID",
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
