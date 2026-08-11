from pathlib import Path

from dcc_mcp_illustrator import __version__


def test_bootstrap_version():
    assert __version__ == "0.0.0"


def test_package_declares_runtime_entry_points():
    text = (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    assert 'dcc-mcp-illustrator = "dcc_mcp_illustrator.cli:main"' in text
    assert 'illustrator = "dcc_mcp_illustrator:IllustratorMcpServer"' in text
