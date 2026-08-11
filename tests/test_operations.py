from types import SimpleNamespace
from unittest import mock

from adobe.core.dom import DomObject

from dcc_mcp_illustrator.operations import (
    TOOL_NAMESPACE_COVERAGE,
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
    document.save_as.assert_called_once_with(str(ai_path), format="ai", options=None)
    document.export_file.assert_called_once_with("png24", str(png_path), options=None)


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
