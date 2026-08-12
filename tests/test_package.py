import re
from pathlib import Path

import yaml

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


def test_flow_mapping_descriptions_do_not_create_phantom_schema_keywords():
    skills = Path(__file__).parents[1] / "src" / "dcc_mcp_illustrator" / "skills"
    export = yaml.safe_load((skills / "illustrator-export" / "tools.yaml").read_text())
    advanced = yaml.safe_load((skills / "illustrator-advanced" / "tools.yaml").read_text())

    export_format = export["tools"][1]["input_schema"]["properties"]["format"]
    dom_member = advanced["tools"][0]["input_schema"]["properties"]["member"]

    assert set(export_format) == {"type", "description"}
    assert set(dom_member) == {"description"}
