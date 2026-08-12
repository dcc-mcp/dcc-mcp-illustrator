import runpy
from pathlib import Path
from unittest import mock

import pytest


@pytest.mark.parametrize(
    ("skill", "script", "operation_name", "arguments"),
    [
        (
            "illustrator-document",
            "create_document",
            "create_document",
            {"width": 640, "height": 360, "color_space": "rgb"},
        ),
        ("illustrator-document", "list_layers", "list_layers", {"parent": "Nested"}),
        (
            "illustrator-document",
            "list_items",
            "list_items",
            {"kind": "text", "selected": True},
        ),
        (
            "illustrator-artwork",
            "create_rectangle",
            "create_rectangle",
            {
                "name": "Card",
                "left": 40,
                "top": 320,
                "width": 560,
                "height": 240,
                "fill_rgb": [35, 120, 210],
            },
        ),
        (
            "illustrator-artwork",
            "create_text",
            "create_text",
            {
                "name": "Headline",
                "contents": "DCC MCP",
                "position": [80, 180],
                "font_size": 32,
                "fill_rgb": [255, 255, 255],
            },
        ),
        (
            "illustrator-artwork",
            "inspect_item",
            "inspect_item",
            {"kind": "path", "name": "Logo"},
        ),
        (
            "illustrator-artwork",
            "mutate_path",
            "mutate_path",
            {"name": "Logo", "operation": "rotate", "angle": 15},
        ),
        (
            "illustrator-artwork",
            "set_text_contents",
            "set_text_contents",
            {"name": "Title", "contents": "Hello"},
        ),
        (
            "illustrator-export",
            "save_document",
            "save_document",
            {"path": "C:/tmp/example.ai", "format": "ai"},
        ),
        (
            "illustrator-export",
            "export_document",
            "export_document",
            {"format": "svg", "path": "C:/tmp/example.svg"},
        ),
        (
            "illustrator-advanced",
            "official_dom",
            "official_dom",
            {"operation": "root", "root": "app"},
        ),
        (
            "illustrator-advanced",
            "evaluate_extend_script",
            "evaluate_extend_script",
            {"source": "app.version"},
        ),
    ],
)
def test_parameterized_skill_script_forwards_arguments(
    skill: str, script: str, operation_name: str, arguments: dict[str, object]
):
    scripts = (
        Path(__file__).parents[1] / "src" / "dcc_mcp_illustrator" / "skills" / skill / "scripts"
    )
    namespace = runpy.run_path(str(scripts / f"{script}.py"))
    entrypoint = namespace["main"].__wrapped__
    operation = mock.Mock(return_value={"ok": True})
    entrypoint.__globals__[operation_name] = operation

    result = entrypoint(**arguments)

    assert result["success"] is True
    operation.assert_called_once_with(**arguments)
