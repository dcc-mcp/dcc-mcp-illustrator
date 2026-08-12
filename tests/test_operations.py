from types import SimpleNamespace
from unittest import mock

from adobe.core.dom import DomObject

from dcc_mcp_illustrator.operations import (
    TOOL_NAMESPACE_COVERAGE,
    create_document,
    create_rectangle,
    create_text,
    evaluate_extend_script,
    export_document,
    inspect_document,
    inspect_item,
    list_artboards,
    list_items,
    list_layers,
    mutate_path,
    official_dom,
    save_document,
    set_text_contents,
)
from dcc_mcp_illustrator.runtime import REQUIRED_METHODS


def page_item(**overrides):
    values = {
        "id": 1,
        "index": 1,
        "name": "Shape",
        "item_type": "PathItem",
        "hidden": False,
        "locked": False,
        "selected": True,
        "editable": True,
        "position": [10, 20],
        "geometric_bounds": [10, 20, 110, 120],
        "visible_bounds": [10, 20, 110, 120],
        "control_bounds": [10, 20, 110, 120],
        "width": 100,
        "height": 100,
        "opacity": 100,
        "parent_name": "Layer 1",
        "parent_typename": "Layer",
        "layer_name": "Layer 1",
        "note": "",
        "url": "",
        "typename": "PathItem",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def path_item(**overrides):
    values = {
        "area": 10000,
        "closed": True,
        "clipping": False,
        "filled": True,
        "fill_color": {"red": 255},
        "stroked": True,
        "stroke_color": {"black": 100},
        "stroke_width": 1,
        "guides": False,
        "length": 400,
        "path_point_count": 4,
        "selected_path_point_count": 0,
    }
    values.update(overrides)
    return page_item(**values)


def text_frame(**overrides):
    values = {
        "id": 2,
        "index": 1,
        "name": "Title",
        "contents": "Hello",
        "kind": "POINTTEXT",
        "orientation": "HORIZONTAL",
        "position": [20, 30],
        "geometric_bounds": [20, 30, 120, 60],
        "visible_bounds": [20, 30, 120, 60],
        "width": 100,
        "height": 30,
        "selected": False,
        "layer_name": "Layer 1",
        "character_count": 5,
        "word_count": 1,
        "paragraph_count": 1,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def document_fixture():
    artboard = SimpleNamespace(
        index=0,
        name="Artboard 1",
        artboard_rect=[0, 360, 640, 0],
        ruler_origin=[0, 0],
        ruler_par=1.0,
        show_center=False,
        show_cross_hairs=False,
        show_safe_areas=False,
    )
    layer = SimpleNamespace(
        id=1,
        index=1,
        name="Layer 1",
        visible=True,
        locked=False,
        printable=True,
        preview=True,
        opacity=100,
        has_selected_artwork=True,
        parent_name=None,
        parent_typename="Document",
        layer_count=0,
        page_item_count=1,
        layers=[],
        page_items=[],
        path_items=[],
        compound_path_items=[],
        placed_items=[],
        raster_items=[],
    )
    path = path_item()
    text = text_frame()
    result = SimpleNamespace(
        ok=True,
        path="output.ai",
        format="ai",
        preset=None,
        options={},
        document_name="Demo.ai",
    )
    values = {
        "name": "Demo.ai",
        "width": 640,
        "height": 360,
        "artboard_count": 1,
        "layer_count": 1,
        "page_item_count": 2,
        "path_item_count": 1,
        "compound_path_item_count": 0,
        "placed_item_count": 0,
        "raster_item_count": 0,
        "text_frame_count": 1,
        "story_count": 0,
        "swatch_count": 0,
        "selection_count": 1,
        "artboards": [artboard],
        "active_artboard": artboard,
        "active_artboard_index": 0,
        "layers": [layer],
        "page_items": [path, text],
        "selection": [path],
        "path_items": [path],
        "selected_path_items": [path],
        "compound_path_items": [],
        "selected_compound_path_items": [],
        "placed_items": [],
        "selected_placed_items": [],
        "raster_items": [],
        "selected_raster_items": [],
        "text_frames": [text],
        "selected_text_frames": [],
        "stories": [],
        "swatches": [],
        "get_layer_by_name": mock.Mock(return_value=layer),
        "get_page_item_by_name": mock.Mock(return_value=path),
        "get_path_item_by_name": mock.Mock(return_value=path),
        "get_compound_path_item_by_name": mock.Mock(return_value=None),
        "get_placed_item_by_name": mock.Mock(return_value=None),
        "get_raster_item_by_name": mock.Mock(return_value=None),
        "get_text_frame_by_name": mock.Mock(return_value=text),
        "get_story_by_name": mock.Mock(return_value=None),
        "get_swatch_by_name": mock.Mock(return_value=None),
        "save": mock.Mock(return_value=result),
        "save_as": mock.Mock(return_value=result),
        "export_file": mock.Mock(return_value=result),
    }
    return SimpleNamespace(**values), path, text


def test_tools_cover_every_advertised_bridge_namespace():
    assert set(TOOL_NAMESPACE_COVERAGE) == set(REQUIRED_METHODS)
    assert all(tools for tools in TOOL_NAMESPACE_COVERAGE.values())


def test_document_artboard_layer_and_item_inspection():
    document, path, _text = document_fixture()
    app_factory = mock.Mock(
        return_value=SimpleNamespace(active_document=document, version="30.0.0")
    )
    assert inspect_document(app_factory=app_factory)["counts"]["path_items"] == 1
    assert list_artboards(app_factory=app_factory)["active_index"] == 0
    assert list_layers(app_factory=app_factory)["layers"][0]["name"] == "Layer 1"
    assert list_items("path", selected=True, app_factory=app_factory)["count"] == 1
    assert inspect_item("path", "Shape", app_factory=app_factory)["item"]["area"] == 10000
    document.get_path_item_by_name.assert_called_with("Shape")
    assert path.name == "Shape"


def test_path_and_text_mutations_use_typed_facades():
    document, path, text = document_fixture()
    path.translate = mock.Mock(return_value=path)
    text.set_contents = mock.Mock(return_value=text_frame(contents="Updated"))
    app_factory = mock.Mock(return_value=SimpleNamespace(active_document=document))
    moved = mutate_path(
        "Shape",
        "translate",
        delta_x=10,
        delta_y=-5,
        options={"transform_objects": True},
        app_factory=app_factory,
    )
    assert moved["updated"] is True
    path.translate.assert_called_once_with(10, -5, transform_objects=True)
    updated = set_text_contents("Title", "Updated", app_factory=app_factory)
    assert updated["text_frame"]["contents"] == "Updated"
    text.set_contents.assert_called_once_with("Updated")


def test_save_and_export_use_absolute_paths(tmp_path):
    document, _path, _text = document_fixture()
    app_factory = mock.Mock(return_value=SimpleNamespace(active_document=document))
    ai_path = tmp_path / "demo.ai"
    png_path = tmp_path / "demo.png"
    assert save_document(str(ai_path), app_factory=app_factory)["saved"] is True
    assert export_document("png24", str(png_path), app_factory=app_factory)["exported"] is True
    assert app_factory.call_args_list == [mock.call(timeout=120), mock.call(timeout=300)]
    document.save_as.assert_called_once_with(
        str(ai_path), format="ai", options=None, timeout_ms=120_000
    )
    document.export_file.assert_called_once_with(
        "png24", str(png_path), options=None, timeout_ms=300_000
    )


def test_export_uses_a_long_operation_timeout_without_changing_health_probes(tmp_path):
    document, _path, _text = document_fixture()
    app_factory = mock.Mock(return_value=SimpleNamespace(active_document=document))
    svg_path = tmp_path / "demo.svg"

    result = export_document(
        "svg",
        str(svg_path),
        timeout_secs=180,
        app_factory=app_factory,
    )

    assert result["exported"] is True
    app_factory.assert_called_once_with(timeout=180)
    document.export_file.assert_called_once_with(
        "svg",
        str(svg_path),
        options=None,
        timeout_ms=180_000,
    )


def test_create_document_uses_structured_dom_and_explicit_dimensions():
    dom = mock.Mock()
    app_root = mock.Mock()
    global_root = mock.Mock()
    documents = mock.Mock()
    color_spaces = mock.Mock()
    document = mock.Mock()
    dom.root.side_effect = [app_root, global_root]
    app_root.get.return_value = documents
    global_root.get.return_value = color_spaces
    color_spaces.get.return_value = 42
    documents.call.return_value = document
    document.snapshot.return_value = {
        "name": "Untitled-1",
        "width": 640,
        "height": 360,
        "typename": "Document",
    }
    app_factory = mock.Mock(return_value=SimpleNamespace(dom=dom))

    result = create_document(640, 360, color_space="rgb", app_factory=app_factory)

    assert result["created"] is True
    assert result["document"]["width"] == 640
    documents.call.assert_called_once_with(
        "add",
        42,
        640.0,
        360.0,
        1,
        command_name="Create Illustrator document",
        mutating=True,
        timeout_ms=30_000,
    )


def test_create_rectangle_builds_rgb_color_without_raw_script():
    dom = mock.Mock()
    document = mock.Mock()
    global_root = mock.Mock()
    path_items = mock.Mock()
    rectangle = mock.Mock()
    color = mock.Mock()
    dom.root.side_effect = [document, global_root]
    document.get.return_value = path_items
    path_items.call.return_value = rectangle
    global_root.construct.return_value = color
    rectangle.snapshot.return_value = {
        "name": "Hero card",
        "typename": "PathItem",
        "geometricBounds": [72, 300, 568, 80],
    }
    app_factory = mock.Mock(return_value=SimpleNamespace(dom=dom))

    result = create_rectangle(
        "Hero card",
        left=72,
        top=300,
        width=496,
        height=220,
        fill_rgb=[35, 120, 210],
        app_factory=app_factory,
    )

    assert result["created"] is True
    path_items.call.assert_called_once_with(
        "rectangle",
        300.0,
        72.0,
        496.0,
        220.0,
        command_name="Create Illustrator rectangle",
        mutating=True,
        timeout_ms=30_000,
    )
    assert color.set.call_args_list == [
        mock.call("red", 35.0, command_name="Set Illustrator color", timeout_ms=30_000),
        mock.call("green", 120.0, command_name="Set Illustrator color", timeout_ms=30_000),
        mock.call("blue", 210.0, command_name="Set Illustrator color", timeout_ms=30_000),
    ]
    assert (
        mock.call(
            "fillColor",
            color,
            command_name="Style Illustrator rectangle",
            timeout_ms=30_000,
        )
        in rectangle.set.call_args_list
    )


def test_create_text_sets_contents_position_size_and_color():
    dom = mock.Mock()
    document = mock.Mock()
    global_root = mock.Mock()
    text_frames = mock.Mock()
    text = mock.Mock()
    text_range = mock.Mock()
    attributes = mock.Mock()
    color = mock.Mock()
    dom.root.side_effect = [document, global_root]
    document.get.return_value = text_frames
    text_frames.call.return_value = text
    text.get.return_value = text_range
    text_range.get.return_value = attributes
    global_root.construct.return_value = color
    text.snapshot.return_value = {
        "name": "Headline",
        "contents": "DCC MCP × Illustrator",
        "typename": "TextFrame",
        "position": [96, 180],
    }
    app_factory = mock.Mock(return_value=SimpleNamespace(dom=dom))

    result = create_text(
        "Headline",
        "DCC MCP × Illustrator",
        position=[96, 180],
        font_size=34,
        fill_rgb=[245, 247, 250],
        app_factory=app_factory,
    )

    assert result["created"] is True
    assert (
        mock.call(
            "size",
            34.0,
            command_name="Style Illustrator text",
            timeout_ms=30_000,
        )
        in attributes.set.call_args_list
    )
    assert (
        mock.call(
            "fillColor",
            color,
            command_name="Style Illustrator text",
            timeout_ms=30_000,
        )
        in attributes.set.call_args_list
    )


class FakeDom:
    def root(self, name):
        return DomObject(self, name, "Application")

    def get(self, receiver, member):
        assert receiver.reference == "app"
        return {"member": member, "child": DomObject(self, "document", "Document")}


def test_official_dom_round_trips_refs_and_raw_fallback():
    dom = FakeDom()
    raw = SimpleNamespace(eval_extend_script=mock.Mock(return_value="30.0.0"))
    app_factory = mock.Mock(return_value=SimpleNamespace(dom=dom, raw=raw))
    root = official_dom("root", app_factory=app_factory)
    assert root["result"] == {"$ref": "app", "$type": "Application"}
    result = official_dom(
        "get", receiver=root["result"], member="activeDocument", app_factory=app_factory
    )
    assert result["result"]["child"] == {"$ref": "document", "$type": "Document"}
    assert evaluate_extend_script("app.version", app_factory=app_factory) == {"result": "30.0.0"}
