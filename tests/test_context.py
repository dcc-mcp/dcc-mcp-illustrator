from types import SimpleNamespace

from dcc_mcp_illustrator.context import collect_context


def test_context_is_bounded_and_omits_document_path():
    document = SimpleNamespace(
        name="Demo.ai",
        path="private/demo.ai",
        selection_count=2,
        artboard_count=1,
        layer_count=3,
        page_item_count=5,
    )
    snapshot = collect_context(
        broker_url="http://127.0.0.1:47391",
        token="secret",
        target="default",
        timeout=1.0,
        client_factory=lambda **_kwargs: object(),
        app_factory=lambda **_kwargs: SimpleNamespace(
            active_document=document,
            version="30.0.0",
        ),
    ).to_dict()
    assert snapshot == {
        "dcc": "illustrator",
        "document": {"name": "Demo.ai"},
        "selection": {"count": 2},
        "counts": {"artboards": 1, "layers": 3, "page_items": 5},
        "metadata": {"version": "30.0.0", "target": "default"},
    }
