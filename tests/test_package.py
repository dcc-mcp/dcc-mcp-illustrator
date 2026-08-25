import importlib.metadata
import re
from pathlib import Path

import yaml
from packaging.requirements import Requirement
from packaging.version import Version

from dcc_mcp_illustrator import __version__


def test_runtime_version_matches_project_version():
    text = (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    project_version = re.search(r'^version = "([^"]+)"$', text, re.MULTILINE)

    assert project_version is not None
    assert __version__ == project_version.group(1)


def test_package_declares_runtime_entry_points():
    text = (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    assert 'dcc-mcp-illustrator = "dcc_mcp_illustrator.cli:main"' in text
    assert 'illustrator = "dcc_mcp_illustrator:IllustratorMcpServer"' in text


def test_ci_inspects_built_lifecycle_payload():
    workflow = (Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    assert "python tools/check_distribution.py" in workflow


def test_distribution_binds_audited_adobepy_and_compatible_core_range():
    requirements = {
        Requirement(item).name: Requirement(item)
        for item in importlib.metadata.requires("dcc-mcp-illustrator") or ()
        if "extra ==" not in item
    }

    assert str(requirements["adobepy"].specifier) == "==0.8.0"
    assert requirements["adobepy"].specifier.contains(
        Version(importlib.metadata.version("adobepy")), prereleases=False
    )
    assert str(requirements["dcc-mcp-core"].specifier) in {
        "<1.0.0,>=0.20.14",
        ">=0.20.14,<1.0.0",
    }
    assert requirements["dcc-mcp-core"].specifier.contains(
        Version(importlib.metadata.version("dcc-mcp-core")), prereleases=False
    )


def test_ci_has_bounded_jobs_and_explicit_floor_and_latest_core_lanes():
    workflow = yaml.safe_load(
        (Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    )

    assert all(1 <= job["timeout-minutes"] <= 30 for job in workflow["jobs"].values())
    compatibility = workflow["jobs"]["dependency-compatibility"]
    assert compatibility["strategy"]["matrix"]["core-spec"] == [
        "dcc-mcp-core==0.20.14",
        "dcc-mcp-core>=0.20.14,<1.0.0",
    ]
    runs = "\n".join(
        step.get("run", "") for step in compatibility["steps"] if isinstance(step, dict)
    )
    assert 'python -m pip install --upgrade "${{ matrix.core-spec }}"' in runs
    assert "python -m pip check" in runs
    assert "python tools/check_dependencies.py" in runs


def test_flow_mapping_descriptions_do_not_create_phantom_schema_keywords():
    skills = Path(__file__).parents[1] / "src" / "dcc_mcp_illustrator" / "skills"
    export = yaml.safe_load((skills / "illustrator-export" / "tools.yaml").read_text())
    advanced = yaml.safe_load((skills / "illustrator-advanced" / "tools.yaml").read_text())

    export_format = export["tools"][1]["input_schema"]["properties"]["format"]
    dom_member = advanced["tools"][0]["input_schema"]["properties"]["member"]

    assert set(export_format) == {"type", "description"}
    assert set(dom_member) == {"description"}
