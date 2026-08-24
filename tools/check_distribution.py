"""Verify that release archives carry the public install lifecycle surface."""

from __future__ import annotations

import hashlib
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
        "dcc_mcp_illustrator/install_contract.py",
        "dcc_mcp_illustrator/install_discovery.py",
        "dcc_mcp_illustrator/install_io.py",
        "dcc_mcp_illustrator/install_models.py",
        "dcc_mcp_illustrator/install_reporting.py",
        "dcc_mcp_illustrator/install_service.py",
        "dcc_mcp_illustrator/install_verification.py",
        "dcc_mcp_illustrator/bootstrap_diagnostics.py",
        "dcc_mcp_illustrator/schemas/adapter-install-sop-v1.schema.json",
    }
    with zipfile.ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())
    missing = sorted(required_wheel - names)
    if missing:
        raise SystemExit(f"wheel is missing lifecycle payload: {missing}")
    with zipfile.ZipFile(wheels[0]) as archive:
        schema = archive.read("dcc_mcp_illustrator/schemas/adapter-install-sop-v1.schema.json")
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        metadata = archive.read(metadata_name).decode("utf-8")
    if len(schema) != 4_261 or hashlib.sha256(schema).hexdigest() != (
        "3ca25788439917b4d4c0617230a762f9797756b5b54f45c8c4149f975b90f904"
    ):
        raise SystemExit("wheel carries a noncanonical Install SOP schema")
    if b"\r\n" in schema:
        raise SystemExit("wheel schema is not the canonical LF byte stream")
    if "Requires-Dist: dcc-mcp-core<1.0.0,>=0.20.14" not in metadata:
        raise SystemExit("wheel metadata does not require the released Core schema floor")

    with tarfile.open(sdists[0], "r:gz") as archive:
        names = archive.getnames()
    if not any(name.endswith("/install.md") for name in names):
        raise SystemExit("source archive is missing install.md")


if __name__ == "__main__":
    main()
