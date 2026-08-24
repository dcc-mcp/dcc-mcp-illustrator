from __future__ import annotations

import importlib.resources
import json
import os
import subprocess
import sys

from jsonschema import Draft202012Validator

from dcc_mcp_illustrator.install_contract import redact_payload


def test_public_status_reports_machine_readable_not_installed_contract(tmp_path):
    env = os.environ.copy()
    env["DCC_MCP_ILLUSTRATOR_INSTALL_STATE_DIR"] = str(tmp_path / "state")

    result = subprocess.run(
        [sys.executable, "-m", "dcc_mcp_illustrator", "status", "--json"],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )

    assert result.returncode == 10
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["dcc_type"] == "illustrator"
    schema = json.loads(
        importlib.resources.files("dcc_mcp_illustrator.schemas")
        .joinpath("adapter-install-sop-v1.schema.json")
        .read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)
    assert payload["plan"]["mode"] == "status"
    assert payload["status"] in {"ok", "failed"}
    assert payload["installation_state"] in {"fresh", "unknown"}
    assert payload["verify"]["directly_usable"] is False
    assert payload["receipt_path"] is None
    assert isinstance(payload["next_steps"], list)


def test_nested_public_payload_redaction_preserves_json_types(monkeypatch):
    monkeypatch.setenv("ADOBEPY_TOKEN", "nested-secret")
    payload = {
        "ok": False,
        "count": 3,
        "diagnostics": [
            "nested-secret",
            {"url": "wss://operator:password@127.0.0.1:47391"},
        ],
    }

    redacted = redact_payload(payload)

    assert redacted["ok"] is False
    assert redacted["count"] == 3
    assert redacted["diagnostics"] == [
        "<redacted>",
        {"url": "wss://<redacted>@127.0.0.1:47391"},
    ]
