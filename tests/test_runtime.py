from types import SimpleNamespace

from dcc_mcp_illustrator.runtime import REQUIRED_METHODS, probe_illustrator


def capability_payload(host="illustrator", methods=None, features=None):
    return [
        {
            "target": "default",
            "capabilities": {
                "host": host,
                "methods": methods
                or {namespace: list(values) for namespace, values in REQUIRED_METHODS.items()},
                "features": features if features is not None else ["officialDom"],
            },
        }
    ]


def test_probe_rejects_other_adobe_sessions():
    client = SimpleNamespace(capabilities=lambda: capability_payload(host="after-effects"))
    status = probe_illustrator(client=client)
    assert status.ready is False
    assert status.reason == "Illustrator bridge session is not connected"


def test_probe_requires_complete_bridge_contract():
    client = SimpleNamespace(
        capabilities=lambda: capability_payload(methods={"app": ["getVersion"]})
    )
    status = probe_illustrator(client=client)
    assert status.ready is False
    assert "document.getActive" in status.reason


def test_probe_calls_real_host_version():
    client = SimpleNamespace(capabilities=lambda: capability_payload())
    status = probe_illustrator(
        client=client,
        app_factory=lambda **_kwargs: SimpleNamespace(version="30.0.0"),
    )
    assert status.ready is True
    assert status.version == "30.0.0"


def test_probe_reports_host_rpc_failure():
    client = SimpleNamespace(capabilities=lambda: capability_payload())

    def fail(**_kwargs):
        raise RuntimeError("host RPC failed")

    status = probe_illustrator(client=client, app_factory=fail)
    assert status.ready is False
    assert status.reason == "host RPC failed"
