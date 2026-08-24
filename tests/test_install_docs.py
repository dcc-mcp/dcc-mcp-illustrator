from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_root_install_guide_documents_canonical_lifecycle_and_platform_truth():
    text = (ROOT / "install.md").read_text(encoding="utf-8")

    for heading in (
        "## Requirements",
        "## Supported versions and platforms",
        "## Agent quick path",
        "## Manual path",
        "## Verify",
        "## Upgrade",
        "## Uninstall",
        "## Troubleshooting",
    ):
        assert heading in text
    for verb in ("install", "status", "verify", "upgrade", "uninstall"):
        assert f"dcc-mcp-illustrator {verb}" in text
    assert "Windows" in text
    assert "macOS" in text
    assert "Linux" in text
    assert "ADOBEPY_TOKEN" in text
    assert "dcc-mcp-core` 0.20.14" in text
    assert "dcc-mcp/adobepy#70" in text
    assert "licensed live Illustrator" in text
    assert "--token" not in text
    assert "directly_usable" in text
    assert "CEP" in text


def test_readme_routes_installation_to_the_canonical_guide_without_token_argv():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "install.md" in text
    assert "dcc-mcp-illustrator install --json --dry-run" in text
    assert "--token" not in text


def test_wheel_configuration_includes_the_install_guide():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.hatch.build.targets.wheel.force-include]" in text
    assert '"install.md" = "dcc_mcp_illustrator/install.md"' in text
