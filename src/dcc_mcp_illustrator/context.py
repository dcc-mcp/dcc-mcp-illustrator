"""Bounded Illustrator document context snapshots."""

from __future__ import annotations

from typing import Any, Callable

from adobe.core import BrokerClient
from adobe.illustrator import Illustrator
from dcc_mcp_core import DccContextSnapshot


def collect_context(
    *,
    broker_url: str | None,
    token: str | None,
    target: str,
    timeout: float,
    client_factory: Callable[..., Any] = BrokerClient,
    app_factory: Callable[..., Any] = Illustrator,
) -> DccContextSnapshot:
    client = client_factory(
        broker_url=broker_url,
        token=token,
        target=target,
        timeout=timeout,
    )
    app = app_factory(client=client)
    document = app.active_document
    return DccContextSnapshot(
        dcc="illustrator",
        document={"name": document.name} if document is not None else None,
        selection={"count": int(document.selection_count or 0)} if document is not None else None,
        counts={
            "artboards": int(document.artboard_count or 0),
            "layers": int(document.layer_count or 0),
            "page_items": int(document.page_item_count or 0),
        }
        if document is not None
        else {},
        metadata={"version": str(app.version), "target": target},
    )


__all__ = ["collect_context"]
