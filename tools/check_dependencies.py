"""Fail closed when installed runtime dependencies drift from package metadata."""

from __future__ import annotations

import argparse
import importlib.metadata

from packaging.requirements import Requirement
from packaging.version import Version


def _runtime_requirements() -> dict[str, Requirement]:
    return {
        requirement.name: requirement
        for raw in importlib.metadata.requires("dcc-mcp-illustrator") or ()
        if "extra ==" not in raw
        for requirement in (Requirement(raw),)
    }


def _require_satisfied(requirement: Requirement) -> Version:
    installed = Version(importlib.metadata.version(requirement.name))
    if not requirement.specifier.contains(installed, prereleases=False):
        raise SystemExit(f"{requirement.name} {installed} does not satisfy {requirement.specifier}")
    return installed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-core", default="dcc-mcp-core>=0.20.14,<1.0.0")
    args = parser.parse_args(argv)

    requirements = _runtime_requirements()
    core = requirements["dcc-mcp-core"]
    adobepy = requirements["adobepy"]
    if str(adobepy.specifier) != "==0.8.0":
        raise SystemExit(f"adobepy must be exactly bound to the audited release: {adobepy}")
    if str(core.specifier) not in {"<1.0.0,>=0.20.14", ">=0.20.14,<1.0.0"}:
        raise SystemExit(f"unexpected dcc-mcp-core package range: {core}")

    installed_core = _require_satisfied(core)
    installed_adobepy = _require_satisfied(adobepy)
    expected_core = Requirement(args.expected_core)
    if expected_core.name != "dcc-mcp-core" or not expected_core.specifier.contains(
        installed_core, prereleases=False
    ):
        raise SystemExit(
            f"resolved dcc-mcp-core {installed_core} does not satisfy lane {expected_core}"
        )
    print(f"dcc-mcp-core={installed_core} adobepy={installed_adobepy}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
