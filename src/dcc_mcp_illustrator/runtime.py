"""Host-specific readiness for the adobepy-backed Illustrator adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from adobe.core import BrokerClient
from adobe.illustrator import Illustrator

REQUIRED_METHODS: Mapping[str, tuple[str, ...]] = {
    "app": ("getVersion",),
    "document": ("getActive",),
    "artboard": ("getArtboards", "getActive", "getActiveIndex"),
    "layer": ("getLayers", "getByName", "getChildren"),
    "pageItem": ("getPageItems", "getSelected", "getByName", "getLayerItems"),
    "pathItem": (
        "getPathItems",
        "getSelected",
        "getByName",
        "getLayerItems",
        "setEntirePath",
        "translate",
        "resize",
        "rotate",
    ),
    "compoundPath": (
        "getCompoundPathItems",
        "getSelected",
        "getByName",
        "getLayerItems",
        "getPathItems",
    ),
    "placedItem": ("getPlacedItems", "getSelected", "getByName", "getLayerItems"),
    "rasterItem": ("getRasterItems", "getSelected", "getByName", "getLayerItems"),
    "textFrame": ("getTextFrames", "getSelected", "getByName", "setContents"),
    "story": ("getStories", "getByName"),
    "swatch": ("getSwatches", "getByName"),
    "export": ("save", "saveAs", "exportFile"),
    "dom": ("root", "get", "set", "call", "construct", "keys", "snapshot", "release"),
    "raw": ("evalExtendScript",),
}


@dataclass(frozen=True)
class IllustratorStatus:
    ready: bool
    reason: str = ""
    version: str | None = None
    target: str = "default"


def _matching_session(payloads: list[Mapping[str, Any]], target: str) -> Mapping[str, Any] | None:
    for payload in payloads:
        capabilities = payload.get("capabilities", {})
        if capabilities.get("host") == "illustrator" and payload.get("target", "default") == target:
            return payload
    return None


def _missing_methods(capabilities: Mapping[str, Any]) -> list[str]:
    advertised = capabilities.get("methods", {})
    return [
        f"{namespace}.{method}"
        for namespace, methods in REQUIRED_METHODS.items()
        for method in methods
        if method not in advertised.get(namespace, ())
    ]


def probe_illustrator(
    *,
    broker_url: str | None = None,
    token: str | None = None,
    target: str = "default",
    timeout: float = 5.0,
    client: BrokerClient | None = None,
    app_factory: Callable[..., Any] = Illustrator,
) -> IllustratorStatus:
    """Require a complete Illustrator capability session and one real host RPC."""
    active_client = client or BrokerClient(
        broker_url=broker_url,
        token=token,
        target=target,
        timeout=timeout,
    )
    try:
        session = _matching_session(active_client.capabilities(), target)
    except Exception as exc:  # noqa: BLE001
        return IllustratorStatus(False, str(exc), target=target)
    if session is None:
        return IllustratorStatus(
            False, "Illustrator bridge session is not connected", target=target
        )
    capabilities = session.get("capabilities", {})
    missing = _missing_methods(capabilities)
    if missing:
        return IllustratorStatus(
            False,
            "missing bridge methods: " + ", ".join(missing),
            target=target,
        )
    if "officialDom" not in capabilities.get("features", ()):
        return IllustratorStatus(False, "official DOM capability is unavailable", target=target)
    try:
        version = str(app_factory(client=active_client).version)
    except Exception as exc:  # noqa: BLE001
        return IllustratorStatus(False, str(exc), target=target)
    return IllustratorStatus(True, version=version, target=target)


__all__ = ["IllustratorStatus", "REQUIRED_METHODS", "probe_illustrator"]
