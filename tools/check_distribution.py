"""Verify that release archives carry the public install lifecycle surface."""

from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path


def main() -> None:
    dist = Path(__file__).parents[1] / "dist"
    wheels = list(dist.glob("dcc_mcp_illustrator-*.whl"))
    sdists = list(dist.glob("dcc_mcp_illustrator-*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit("expected exactly one Illustrator wheel and one source archive")

    required_wheel = {
        "dcc_mcp_illustrator/install.md",
        "dcc_mcp_illustrator/install_lifecycle.py",
        "dcc_mcp_illustrator/install_service.py",
        "dcc_mcp_illustrator/install_verification.py",
        "dcc_mcp_illustrator/bootstrap_diagnostics.py",
    }
    with zipfile.ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())
    missing = sorted(required_wheel - names)
    if missing:
        raise SystemExit(f"wheel is missing lifecycle payload: {missing}")

    with tarfile.open(sdists[0], "r:gz") as archive:
        names = archive.getnames()
    if not any(name.endswith("/install.md") for name in names):
        raise SystemExit("source archive is missing install.md")


if __name__ == "__main__":
    main()
