"""Host-specific readiness for the adobepy-backed Illustrator adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from adobe.core import BrokerClient
from adobe.core.errors import IdentityUnavailableError
from adobe.core.runtime_identity import RuntimeIdentityAttestation
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
    identity: Mapping[str, Any] | None = None
    error_type: str | None = None


def _matching_session(payloads: list[Mapping[str, Any]], target: str) -> Mapping[str, Any] | None:
    matches = []
    for payload in payloads:
        capabilities = payload.get("capabilities", {})
        if (
            capabilities.get("host") == "illustrator"
            and capabilities.get("bridgeKind") == "cep"
            and payload.get("target", "default") == target
        ):
            matches.append(payload)
    return matches[0] if len(matches) == 1 else None


def _missing_methods(capabilities: Mapping[str, Any]) -> list[str]:
    advertised = capabilities.get("methods", {})
    return [
        f"{namespace}.{method}"
        for namespace, methods in REQUIRED_METHODS.items()
        for method in methods
        if method not in advertised.get(namespace, ())
    ]


def _normalize_runtime_identity(value: object) -> dict[str, Any] | None:
    """Validate the published SDK attestation before adapting the receipt schema."""
    try:
        if isinstance(value, RuntimeIdentityAttestation):
            # Dataclasses can be constructed directly; validate them as strictly as wire data.
            value = value.to_wire()
        attestation = RuntimeIdentityAttestation.from_broker(value)
    except (AttributeError, TypeError, ValueError):
        return None
    broker, host, bridge = attestation.broker, attestation.host, attestation.bridge
    return {
        "host": "illustrator",
        "host_pid": host.pid,
        "process_start_identity": host.process_start_identity,
        "process_executable": host.executable_path,
        "host_version": host.host_version,
        "profile_id": host.profile_id,
        "target": bridge.target,
        "bridge_kind": bridge.bridge_kind,
        "bridge_version": bridge.bridge_version,
        "instance_id": bridge.instance_id,
        "plugin_root": bridge.installed_plugin_root,
        "plugin_module_origin": bridge.module_origin,
        "connected_at_epoch_ms": bridge.connected_at_epoch_ms,
        "broker": {
            "pid": broker.pid,
            "process_start_identity": broker.process_start_identity,
            "executable": broker.executable_path,
            "version": broker.runtime_version,
            "instance_id": broker.instance_id,
        },
    }


def probe_illustrator(
    *,
    broker_url: str | None = None,
    token: str | None = None,
    target: str = "default",
    timeout: float = 5.0,
    client: BrokerClient | None = None,
    app_factory: Callable[..., Any] = Illustrator,
) -> IllustratorStatus:
    """Require a complete Illustrator capability session and exact runtime identity."""
    active_client = client or BrokerClient(
        broker_url=broker_url,
        token=token,
        target=target,
        timeout=timeout,
    )
    try:
        session = _matching_session(active_client.capabilities(), target)
    except Exception:  # noqa: BLE001 - readiness must remain queryable
        return IllustratorStatus(
            False,
            "adobepy broker capability probe failed",
            target=target,
            error_type="broker_probe_failed",
        )
    if session is None:
        return IllustratorStatus(
            False,
            "illustrator bridge session is not connected",
            target=target,
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
        app = app_factory(client=active_client)
        version = str(app.version)
        runtime_identity = getattr(app, "runtime_identity", None)
        identity = runtime_identity() if callable(runtime_identity) else runtime_identity
    except IdentityUnavailableError:
        return IllustratorStatus(
            False,
            "adobepy has no trusted Illustrator CEP runtime identity",
            target=target,
            error_type="runtime_identity_unavailable",
        )
    except Exception:  # noqa: BLE001 - readiness reports stable host failures
        return IllustratorStatus(
            False,
            "typed Illustrator runtime probe failed",
            target=target,
            error_type="host_rpc_failed",
        )
    identity = _normalize_runtime_identity(identity)
    if identity is None:
        return IllustratorStatus(
            False,
            "adobepy did not attest the exact Illustrator CEP runtime identity",
            version=version,
            target=target,
            error_type="runtime_identity_unavailable",
        )
    if (
        identity["target"] != target
        or identity["bridge_kind"] != "cep"
        or identity["host_version"] != version
    ):
        return IllustratorStatus(
            False,
            "The runtime identity does not match the selected Illustrator session",
            version=version,
            target=target,
            error_type="runtime_identity_mismatch",
        )
    return IllustratorStatus(
        True,
        version=version,
        target=target,
        identity=dict(identity),
    )


__all__ = ["IllustratorStatus", "REQUIRED_METHODS", "probe_illustrator"]
