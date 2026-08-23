from __future__ import annotations

import json
import os
import subprocess
import sys

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

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["dcc_type"] == "illustrator"
    assert payload["verb"] == "status"
    assert payload["mode"] == "plan"
    assert payload["status"] == "ok"
    assert payload["installed_state"] == "fresh"
    assert payload["steps"] == [{"id": "inspect_receipt", "status": "fresh"}]
    assert payload["verify"] == {
        "directly_usable": False,
        "failure_stage": "install_state",
        "failure_reason": "No receipt-backed Illustrator bridge is installed",
    }
    assert payload["receipt_path"] is None
    assert payload["next_steps"] == []


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
