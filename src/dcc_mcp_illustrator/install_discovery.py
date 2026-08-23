"""Illustrator and CEP discovery for Install SOP preflight."""

from __future__ import annotations

import os
import platform
import re
from pathlib import Path
from typing import Iterable, Mapping

EXTENSION_ID = "com.adobepy.bridge.illustrator"


def host_version(path: Path) -> str | None:
    match = re.search(r"Illustrator(?:\.app)?[\\/\s-]+(20\d{2}|\d{2}(?:\.\d+)?)", str(path), re.I)
    return match.group(1) if match else None


def _default_roots(platform_name: str, environ: Mapping[str, str]) -> list[Path]:
    if platform_name == "Windows":
        roots = []
        for name in ("ProgramFiles", "ProgramFiles(x86)"):
            if environ.get(name):
                roots.append(Path(environ[name]) / "Adobe")
        return roots
    if platform_name == "Darwin":
        return [Path("/Applications")]
    return []


def discover_illustrator_executable(
    platform_name: str | None = None,
    roots: Iterable[Path] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> tuple[Path | None, str | None]:
    """Return the newest host matching Adobe's supported Windows/macOS layouts."""
    system = platform_name or platform.system()
    environment = os.environ if environ is None else environ
    search_roots = list(_default_roots(system, environment) if roots is None else roots)
    candidates: list[tuple[int, Path, str]] = []
    for root in search_roots:
        for product in root.glob("Adobe Illustrator *"):
            version = host_version(product)
            if not version:
                continue
            if system == "Windows":
                executable = product / "Support Files" / "Contents" / "Windows" / "Illustrator.exe"
            elif system == "Darwin":
                executable = (
                    product / "Adobe Illustrator.app" / "Contents" / "MacOS" / "Adobe Illustrator"
                )
            else:
                continue
            if executable.is_file():
                major = int(version.split(".", 1)[0])
                candidates.append((major, executable, version))
    if not candidates:
        return None, None
    _, executable, version = max(candidates, key=lambda item: item[0])
    return executable, version


def resolve_cep_extension_root(
    platform_name: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path | None:
    """Return the per-user CEP extension directory owned by this adapter."""
    system = platform_name or platform.system()
    environment = os.environ if environ is None else environ
    user_home = Path.home() if home is None else home
    if system == "Windows":
        appdata = environment.get("APPDATA")
        base = Path(appdata) if appdata else user_home / "AppData" / "Roaming"
        return base / "Adobe" / "CEP" / "extensions" / EXTENSION_ID
    if system == "Darwin":
        return (
            user_home
            / "Library"
            / "Application Support"
            / "Adobe"
            / "CEP"
            / "extensions"
            / EXTENSION_ID
        )
    return None


def cep_runtime_major(version: str | None) -> int | None:
    """Map Adobe's documented Illustrator versions to their CSXS preference owner."""
    if not version:
        return None
    parts = version.split(".", 1)
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        return None
    if major >= 2000:
        if major >= 2025:
            return 12
        if major >= 2021:
            return 11
        return 9 if major >= 2019 else None
    if major >= 29:
        return 12
    if major >= 26 or (major == 25 and minor >= 3):
        return 11
    if major == 25:
        return 10
    return 9 if major >= 23 else None


__all__ = [
    "EXTENSION_ID",
    "cep_runtime_major",
    "discover_illustrator_executable",
    "host_version",
    "resolve_cep_extension_root",
]
