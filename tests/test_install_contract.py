from __future__ import annotations

import importlib.resources
import json
import os
import subprocess
import sys

from jsonschema import Draft202012Validator

from dcc_mcp_illustrator import install_contract
from dcc_mcp_illustrator.install_contract import SCHEMA_VERSION, redact_payload


def _schema_document(const: int) -> dict:
    """A minimal Install SOP schema pinning ``schema_version`` to ``const``."""
    return {"properties": {"schema_version": {"const": const}}}


def test_report_schema_version_is_the_value_the_published_schema_pins() -> None:
    """The report field tracks the schema's ``const``, not the artifact revision.

    ``INSTALL_SOP_SCHEMA_VERSION``/``INSTALL_SOP_SCHEMA_REVISION`` count
    published schema *artifacts* and move when core ships ``-v(N+1)``, while the
    value the artifact pins on a report document stays put because revisions only
    add optional members. Reading the const here turns a core that drifts into a
    red build instead of reports that fail validation in a user's install.
    """
    from dcc_mcp_core.deployment import install_sop

    reader = getattr(install_sop, "install_sop_report_schema_version", None)
    published = int(reader()) if callable(reader) else None
    if published is None:
        loader = getattr(install_sop, "load_install_sop_schema", None)
        published = int(loader()["properties"]["schema_version"]["const"])

    assert SCHEMA_VERSION == published


def test_report_schema_version_prefers_cores_answer(monkeypatch) -> None:
    """When Core can answer, Core's answer wins over the local read.

    Forced-branch case: it substitutes Core's symbol instead of relying on which
    core version pip resolved, so this branch is exercised on every CI lane.
    """
    monkeypatch.setattr(
        install_contract._install_sop,
        "install_sop_report_schema_version",
        lambda: 7,
        raising=False,
    )
    monkeypatch.setattr(
        install_contract._install_sop,
        "load_install_sop_schema",
        lambda: _schema_document(1),
        raising=False,
    )

    assert install_contract._report_schema_version() == 7


def test_report_schema_version_falls_back_when_core_cannot_answer(monkeypatch) -> None:
    """When Core cannot answer, the local read is the one that decides.

    Forced-branch case: substituting ``None`` reproduces an older core on any
    resolved core, so the fallback branch is covered everywhere.
    """
    monkeypatch.setattr(
        install_contract._install_sop,
        "install_sop_report_schema_version",
        None,
        raising=False,
    )
    monkeypatch.setattr(
        install_contract._install_sop,
        "load_install_sop_schema",
        lambda: _schema_document(9),
        raising=False,
    )

    assert install_contract._report_schema_version() == 9


def test_report_schema_version_survives_a_misshapen_document(monkeypatch) -> None:
    """A schema document with the wrong shape degrades instead of raising.

    Core's one-liner indexes straight to the ``const``, so a document missing
    ``properties``/``schema_version``/``const`` raises ``KeyError``. Raising at
    import time would take the CLI down on a broken install -- exactly the case
    the report exists to describe -- so the fallback value wins.
    """
    monkeypatch.setattr(
        install_contract._install_sop,
        "install_sop_report_schema_version",
        None,
        raising=False,
    )
    monkeypatch.setattr(
        install_contract._install_sop,
        "load_install_sop_schema",
        lambda: {"properties": {}},
        raising=False,
    )

    assert install_contract._report_schema_version() == 1


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
