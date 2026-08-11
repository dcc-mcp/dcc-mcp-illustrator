"""Typed Illustrator operations shared by bundled MCP skills."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from adobe.core.dom import DomObject
from adobe.core.errors import HostScriptError
from adobe.illustrator import Illustrator

TOOL_NAMESPACE_COVERAGE = {
    "app": ("inspect_document",),
    "document": ("inspect_document",),
    "artboard": ("list_artboards",),
    "layer": ("list_layers",),
    "pageItem": ("list_items", "inspect_item"),
    "pathItem": ("list_items", "inspect_item", "mutate_path"),
    "compoundPath": ("list_items", "inspect_item"),
    "placedItem": ("list_items", "inspect_item"),
    "rasterItem": ("list_items", "inspect_item"),
    "textFrame": ("list_items", "inspect_item", "set_text_contents"),
    "story": ("list_items", "inspect_item"),
    "swatch": ("list_items", "inspect_item"),
    "export": ("save_document", "export_document"),
    "dom": ("official_dom",),
    "raw": ("evaluate_extend_script",),
}


def _document(app: Any) -> Any:
    document = app.active_document
    if document is None:
        raise HostScriptError("Illustrator has no active document")
    return document


def _absolute_path(value: str) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError(f"Expected an absolute path: {value}")
    return str(path)


def _clean(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _artboard_data(value: Any) -> dict[str, Any]:
    return _clean(
        {
            "index": value.index,
            "name": value.name,
            "rect": value.artboard_rect,
            "ruler_origin": value.ruler_origin,
            "ruler_par": value.ruler_par,
            "show_center": value.show_center,
            "show_cross_hairs": value.show_cross_hairs,
            "show_safe_areas": value.show_safe_areas,
        }
    )


def _layer_data(value: Any) -> dict[str, Any]:
    return _clean(
        {
            "id": value.id,
            "index": value.index,
            "name": value.name,
            "visible": value.visible,
            "locked": value.locked,
            "printable": value.printable,
            "preview": value.preview,
            "opacity": value.opacity,
            "has_selected_artwork": value.has_selected_artwork,
            "parent_name": value.parent_name,
            "parent_type": value.parent_typename,
            "layer_count": value.layer_count,
            "page_item_count": value.page_item_count,
        }
    )


def _item_data(value: Any) -> dict[str, Any]:
    return _clean(
        {
            "id": value.id,
            "index": value.index,
            "name": value.name,
            "type": value.item_type,
            "hidden": value.hidden,
            "locked": value.locked,
            "selected": value.selected,
            "editable": value.editable,
            "position": value.position,
            "geometric_bounds": value.geometric_bounds,
            "visible_bounds": value.visible_bounds,
            "control_bounds": value.control_bounds,
            "width": value.width,
            "height": value.height,
            "opacity": value.opacity,
            "parent_name": value.parent_name,
            "parent_type": value.parent_typename,
            "layer_name": value.layer_name,
            "note": value.note,
            "url": value.url,
            "typename": value.typename,
        }
    )


def _path_data(value: Any) -> dict[str, Any]:
    return {
        **_item_data(value),
        **_clean(
            {
                "area": value.area,
                "closed": value.closed,
                "clipping": value.clipping,
                "filled": value.filled,
                "fill_color": value.fill_color,
                "stroked": value.stroked,
                "stroke_color": value.stroke_color,
                "stroke_width": value.stroke_width,
                "guides": value.guides,
                "length": value.length,
                "path_point_count": value.path_point_count,
                "selected_path_point_count": value.selected_path_point_count,
            }
        ),
    }


def _text_data(value: Any) -> dict[str, Any]:
    return _clean(
        {
            "id": value.id,
            "index": value.index,
            "name": value.name,
            "contents": value.contents,
            "kind": value.kind,
            "orientation": value.orientation,
            "position": value.position,
            "geometric_bounds": value.geometric_bounds,
            "visible_bounds": value.visible_bounds,
            "width": value.width,
            "height": value.height,
            "selected": value.selected,
            "layer_name": value.layer_name,
            "character_count": value.character_count,
            "word_count": value.word_count,
            "paragraph_count": value.paragraph_count,
        }
    )


def _story_data(value: Any) -> dict[str, Any]:
    return _clean(
        {
            "id": value.id,
            "index": value.index,
            "name": value.name,
            "contents": value.contents,
            "length": value.length,
            "text_frame_count": value.text_frame_count,
            "word_count": value.word_count,
            "paragraph_count": value.paragraph_count,
        }
    )


def _swatch_data(value: Any) -> dict[str, Any]:
    return _clean(
        {
            "index": value.index,
            "name": value.name,
            "color": value.color,
            "color_type": value.color_typename,
        }
    )


def _serialize(kind: str, value: Any) -> dict[str, Any]:
    if kind == "path":
        return _path_data(value)
    if kind == "text":
        return _text_data(value)
    if kind == "story":
        return _story_data(value)
    if kind == "swatch":
        return _swatch_data(value)
    data = _item_data(value)
    if kind == "compound":
        data["path_item_count"] = value.path_item_count
        data["path_items"] = [_path_data(path) for path in value.path_items]
    elif kind in {"placed", "raster"}:
        data.update(
            _clean(
                {
                    "file_name": value.file_name,
                    "file_path": value.file_path,
                    "embedded": getattr(value, "embedded", None),
                }
            )
        )
    return data


def inspect_document(*, app_factory=Illustrator) -> dict[str, Any]:
    app = app_factory()
    document = _document(app)
    active = document.active_artboard
    return {
        "version": app.version,
        "document": {
            "name": document.name,
            "width": document.width,
            "height": document.height,
        },
        "counts": {
            "artboards": document.artboard_count,
            "layers": document.layer_count,
            "page_items": document.page_item_count,
            "path_items": document.path_item_count,
            "compound_paths": document.compound_path_item_count,
            "placed_items": document.placed_item_count,
            "raster_items": document.raster_item_count,
            "text_frames": document.text_frame_count,
            "stories": document.story_count,
            "swatches": document.swatch_count,
            "selection": document.selection_count,
        },
        "active_artboard": _artboard_data(active) if active else None,
        "active_artboard_index": document.active_artboard_index,
    }


def list_artboards(*, app_factory=Illustrator) -> dict[str, Any]:
    document = _document(app_factory())
    values = document.artboards
    return {
        "artboards": [_artboard_data(value) for value in values],
        "count": len(values),
        "active_index": document.active_artboard_index,
    }


def list_layers(parent: str | None = None, *, app_factory=Illustrator) -> dict[str, Any]:
    document = _document(app_factory())
    if parent is None:
        values = document.layers
    else:
        layer = document.get_layer_by_name(parent)
        if layer is None:
            raise HostScriptError(f"Illustrator layer was not found: {parent}")
        values = layer.layers
    return {"layers": [_layer_data(value) for value in values], "count": len(values)}


def _items(document: Any, kind: str, *, selected: bool, layer: str | None) -> list[Any]:
    if kind == "page":
        if layer:
            target = document.get_layer_by_name(layer)
            return target.page_items if target else []
        return document.selection if selected else document.page_items
    if kind == "path":
        if layer:
            target = document.get_layer_by_name(layer)
            return target.path_items if target else []
        return document.selected_path_items if selected else document.path_items
    if kind == "compound":
        if layer:
            target = document.get_layer_by_name(layer)
            return target.compound_path_items if target else []
        return document.selected_compound_path_items if selected else document.compound_path_items
    if kind == "placed":
        if layer:
            target = document.get_layer_by_name(layer)
            return target.placed_items if target else []
        return document.selected_placed_items if selected else document.placed_items
    if kind == "raster":
        if layer:
            target = document.get_layer_by_name(layer)
            return target.raster_items if target else []
        return document.selected_raster_items if selected else document.raster_items
    if kind == "text":
        values = document.selected_text_frames if selected else document.text_frames
        return [value for value in values if layer is None or value.layer_name == layer]
    if kind == "story":
        return document.stories
    if kind == "swatch":
        return document.swatches
    raise ValueError(f"Unsupported Illustrator item kind: {kind}")


def _by_name(document: Any, kind: str, name: str) -> Any:
    getters = {
        "page": document.get_page_item_by_name,
        "path": document.get_path_item_by_name,
        "compound": document.get_compound_path_item_by_name,
        "placed": document.get_placed_item_by_name,
        "raster": document.get_raster_item_by_name,
        "text": document.get_text_frame_by_name,
        "story": document.get_story_by_name,
        "swatch": document.get_swatch_by_name,
    }
    if kind not in getters:
        raise ValueError(f"Unsupported Illustrator item kind: {kind}")
    return getters[kind](name)


def list_items(
    kind: str = "page",
    *,
    selected: bool = False,
    layer: str | None = None,
    name: str | None = None,
    app_factory=Illustrator,
) -> dict[str, Any]:
    document = _document(app_factory())
    if name is not None:
        value = _by_name(document, kind, name)
        values = [value] if value is not None else []
    else:
        values = _items(document, kind, selected=selected, layer=layer)
    return {
        "kind": kind,
        "items": [_serialize(kind, value) for value in values],
        "count": len(values),
    }


def inspect_item(kind: str, name: str, *, app_factory=Illustrator) -> dict[str, Any]:
    document = _document(app_factory())
    value = _by_name(document, kind, name)
    if value is None:
        raise HostScriptError(f"Illustrator {kind} item was not found: {name}")
    return {"kind": kind, "item": _serialize(kind, value)}


def mutate_path(
    name: str,
    operation: str,
    *,
    path_points: list[list[float]] | None = None,
    delta_x: float | None = None,
    delta_y: float | None = None,
    scale_x: float | None = None,
    scale_y: float | None = None,
    angle: float | None = None,
    options: dict[str, Any] | None = None,
    app_factory=Illustrator,
) -> dict[str, Any]:
    path = _document(app_factory()).get_path_item_by_name(name)
    if path is None:
        raise HostScriptError(f"Illustrator path item was not found: {name}")
    settings = dict(options or {})
    if operation == "set_path":
        if path_points is None:
            raise ValueError("path_points is required for set_path")
        path = path.set_entire_path(path_points, **settings)
    elif operation == "translate":
        path = path.translate(delta_x, delta_y, **settings)
    elif operation == "resize":
        if scale_x is None or scale_y is None:
            raise ValueError("scale_x and scale_y are required for resize")
        path = path.resize(scale_x, scale_y, **settings)
    elif operation == "rotate":
        if angle is None:
            raise ValueError("angle is required for rotate")
        path = path.rotate(angle, **settings)
    else:
        raise ValueError(f"Unsupported path operation: {operation}")
    return {"operation": operation, "path": _path_data(path), "updated": True}


def set_text_contents(name: str, contents: str, *, app_factory=Illustrator) -> dict[str, Any]:
    frame = _document(app_factory()).get_text_frame_by_name(name)
    if frame is None:
        raise HostScriptError(f"Illustrator text frame was not found: {name}")
    return {"text_frame": _text_data(frame.set_contents(contents)), "updated": True}


def _export_data(result: Any) -> dict[str, Any]:
    return _clean(
        {
            "ok": result.ok,
            "path": result.path,
            "format": result.format,
            "preset": result.preset,
            "options": result.options,
            "document_name": result.document_name,
        }
    )


def save_document(
    path: str | None = None,
    *,
    format: str = "ai",
    options: dict[str, Any] | None = None,
    app_factory=Illustrator,
) -> dict[str, Any]:
    document = _document(app_factory())
    result = (
        document.save_as(_absolute_path(path), format=format, options=options)
        if path
        else document.save()
    )
    return {"result": _export_data(result), "saved": bool(result.ok)}


def export_document(
    format: str,
    path: str,
    *,
    options: dict[str, Any] | None = None,
    app_factory=Illustrator,
) -> dict[str, Any]:
    document = _document(app_factory())
    result = (
        document.save_as(_absolute_path(path), format=format, options=options)
        if format in {"ai", "pdf", "eps"}
        else document.export_file(format, _absolute_path(path), options=options)
    )
    return {"result": _export_data(result), "exported": bool(result.ok)}


def _decode_dom_input(value: Any, namespace: Any) -> Any:
    if isinstance(value, list):
        return [_decode_dom_input(item, namespace) for item in value]
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str):
            return DomObject(namespace, reference, value.get("$type"))
        return {key: _decode_dom_input(item, namespace) for key, item in value.items()}
    return value


def _encode_dom_output(value: Any) -> Any:
    if isinstance(value, DomObject):
        result = {"$ref": value.reference}
        if value.type_name:
            result["$type"] = value.type_name
        return result
    if isinstance(value, list):
        return [_encode_dom_output(item) for item in value]
    if isinstance(value, dict):
        return {key: _encode_dom_output(item) for key, item in value.items()}
    return value


def official_dom(
    operation: str,
    *,
    receiver: dict[str, Any] | None = None,
    member: str | int | None = None,
    value: Any = None,
    args: list[Any] | None = None,
    members: list[str | int] | None = None,
    root: str = "app",
    command_name: str | None = None,
    mutating: bool = False,
    app_factory=Illustrator,
) -> dict[str, Any]:
    namespace = app_factory().dom
    if operation == "root":
        result = namespace.root(root)
    else:
        if receiver is None:
            raise ValueError("receiver is required for this DOM operation")
        target = _decode_dom_input(receiver, namespace)
        if not isinstance(target, DomObject):
            raise ValueError("receiver must contain a $ref")
        decoded_args = _decode_dom_input(args or [], namespace)
        if operation == "get":
            result = namespace.get(target, member)
        elif operation == "set":
            result = namespace.set(
                target, member, _decode_dom_input(value, namespace), command_name=command_name
            )
        elif operation == "call":
            result = namespace.call(
                target,
                member,
                *decoded_args,
                command_name=command_name,
                mutating=mutating,
            )
        elif operation == "construct":
            result = namespace.construct(
                target, str(member), *decoded_args, command_name=command_name
            )
        elif operation == "keys":
            result = namespace.keys(target)
        elif operation == "snapshot":
            result = namespace.snapshot(target, *(members or []))
        elif operation == "release":
            result = namespace.release(target)
        else:
            raise ValueError(f"Unsupported DOM operation: {operation}")
    return {"operation": operation, "result": _encode_dom_output(result)}


def evaluate_extend_script(
    source: str,
    *,
    args: list[Any] | None = None,
    timeout_ms: int | None = None,
    app_factory=Illustrator,
) -> dict[str, Any]:
    result = app_factory().raw.eval_extend_script(source, *(args or []), timeout_ms=timeout_ms)
    return {"result": result}


__all__ = [
    "TOOL_NAMESPACE_COVERAGE",
    "evaluate_extend_script",
    "export_document",
    "inspect_document",
    "inspect_item",
    "list_artboards",
    "list_items",
    "list_layers",
    "mutate_path",
    "official_dom",
    "save_document",
    "set_text_contents",
]
