from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from dcc_mcp_illustrator.bootstrap_diagnostics import capture_bootstrap_error
from dcc_mcp_illustrator.cli import build_parser
from dcc_mcp_illustrator.install_discovery import (
    discover_illustrator_executable,
    resolve_cep_extension_root,
)
from dcc_mcp_illustrator.install_io import commit_bridge, load_receipt, stage_bridge
from dcc_mcp_illustrator.install_lifecycle import run_install_lifecycle
from dcc_mcp_illustrator.install_planning import build_install_report
from dcc_mcp_illustrator.install_verification import verify_illustrator_rpc


def _assert_sop_schema(report):
    assert {
        "schema_version",
        "status",
        "dcc_type",
        "adapter_version",
        "core_version",
        "steps",
        "next_steps",
        "receipt_path",
        "verify",
    }.issubset(report)
    assert report["schema_version"] == 1
    assert report["status"] in {
        "planned",
        "running",
        "ok",
        "failed",
        "partial",
        "requires_restart",
    }
    assert set(report["verify"]) == {
        "directly_usable",
        "failure_stage",
        "failure_reason",
    }
    assert all({"id", "status"}.issubset(step) for step in report["steps"])
    for step in report["next_steps"]:
        assert {"id", "description", "why"}.issubset(step)
        assert ("command" in step) ^ ("file_edit" in step)


def _write_windows_host(root: Path, year: int = 2025) -> Path:
    executable = (
        root
        / f"Adobe Illustrator {year}"
        / "Support Files"
        / "Contents"
        / "Windows"
        / "Illustrator.exe"
    )
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"")
    return executable


def test_discovers_supported_windows_and_macos_illustrator_layouts(tmp_path):
    windows_root = tmp_path / "Adobe"
    windows_host = _write_windows_host(windows_root)
    found, version = discover_illustrator_executable("Windows", [windows_root])
    assert (found, version) == (windows_host, "2025")

    applications = tmp_path / "Applications"
    mac_host = (
        applications
        / "Adobe Illustrator 2024"
        / "Adobe Illustrator.app"
        / "Contents"
        / "MacOS"
        / "Adobe Illustrator"
    )
    mac_host.parent.mkdir(parents=True)
    mac_host.write_bytes(b"")
    found, version = discover_illustrator_executable("Darwin", [applications])
    assert (found, version) == (mac_host, "2024")


def test_cep_destination_is_platform_specific_and_adapter_owned(tmp_path):
    windows = resolve_cep_extension_root(
        "Windows", environ={"APPDATA": str(tmp_path / "AppData"), "USERPROFILE": str(tmp_path)}
    )
    mac = resolve_cep_extension_root("Darwin", home=tmp_path)

    assert windows == (
        tmp_path / "AppData" / "Adobe" / "CEP" / "extensions" / "com.adobepy.bridge.illustrator"
    )
    assert mac == (
        tmp_path
        / "Library"
        / "Application Support"
        / "Adobe"
        / "CEP"
        / "extensions"
        / "com.adobepy.bridge.illustrator"
    )


def test_dry_run_builds_full_plan_without_writing_state(tmp_path, monkeypatch):
    state = tmp_path / "state"
    host = _write_windows_host(tmp_path / "Adobe")
    cli = tmp_path / "adobepy.exe"
    cli.write_bytes(b"")
    monkeypatch.setenv("DCC_MCP_ILLUSTRATOR_INSTALL_STATE_DIR", str(state))
    monkeypatch.setenv("ADOBEPY_TOKEN", "plan-secret")
    monkeypatch.setenv("ADOBEPY_CLI", str(cli))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))

    report, exit_code = build_install_report(
        verb="install",
        dcc_path=str(host),
        python=sys.executable,
        dry_run=True,
        platform_name="Windows",
    )

    assert exit_code == 0
    assert report["status"] == "planned"
    _assert_sop_schema(report)
    assert report["installed_state"] == "fresh"
    assert report["plan"]["host"] == {
        "executable": str(host),
        "version": "2025",
        "platform": "Windows",
    }
    assert report["plan"]["bridge"]["kind"] == "cep"
    destination_parts = tuple(
        part
        for part in report["plan"]["bridge"]["destination"].replace("\\", "/").split("/")
        if part
    )
    assert destination_parts[-4:] == (
        "Adobe",
        "CEP",
        "extensions",
        "com.adobepy.bridge.illustrator",
    )
    assert "plan-secret" not in json.dumps(report)
    assert not state.exists()


def test_bridge_staging_uses_environment_only_token(tmp_path):
    executable = tmp_path / "adobepy.exe"
    executable.write_bytes(b"")
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["env"] = kwargs["env"]
        destination = Path(command[command.index("--dest") + 1])
        (destination / "CSXS").mkdir(parents=True)
        (destination / "CSXS" / "manifest.xml").write_text("<ExtensionManifest />")
        (destination / "dist").mkdir()
        (destination / "dist" / "main.js").write_text("bridge")
        (destination / "dist" / "dom.jsx").write_text("dom")
        (destination / "adobepy.config.js").write_text("secret-bearing config")
        return subprocess.CompletedProcess(command, 0, stdout='{"success":true}', stderr="")

    staging, error = stage_bridge(
        executable=executable,
        staging_parent=tmp_path,
        token="environment-secret",
        target="illustrator-2025",
        runner=fake_run,
    )

    assert error is None
    assert staging is not None
    assert captured["command"][:3] == [str(executable), "install-bridge", "illustrator"]
    assert "--token" not in captured["command"]
    assert captured["command"][captured["command"].index("--target") + 1] == "illustrator-2025"
    assert captured["env"]["ADOBEPY_TOKEN"] == "environment-secret"


def test_receipt_round_trip_never_serializes_bridge_config(tmp_path):
    destination = tmp_path / "extension"
    staging = tmp_path / "stage"
    (staging / "CSXS").mkdir(parents=True)
    (staging / "CSXS" / "manifest.xml").write_text("manifest")
    (staging / "adobepy.config.js").write_text("top-secret")
    receipt_path = tmp_path / "state" / "receipts" / "illustrator.json"
    receipt = {
        "schema_version": 1,
        "dcc_type": "illustrator",
        "bridge_root": str(destination),
    }

    status, error = commit_bridge(
        staging=staging,
        destination=destination,
        receipt_path=receipt_path,
        receipt=receipt,
    )

    assert (status, error) == ("ok", None)
    serialized = receipt_path.read_text()
    assert "top-secret" not in serialized
    loaded = load_receipt(receipt_path, destination)
    assert loaded is not None
    config = next(item for item in loaded["files"] if item["path"] == "adobepy.config.js")
    assert config == {"path": "adobepy.config.js", "sensitive": True}


def test_verify_runs_target_import_broker_session_then_typed_rpc():
    calls = []

    def python_probe(executable, timeout):
        calls.append(("python", executable, timeout))
        return {"ok": True}

    def broker_probe(url, timeout):
        calls.append(("broker", url, timeout))
        return {"ok": True, "sessions": 1}

    def illustrator_probe(url, token, target, timeout):
        calls.append(("illustrator", url, token, target, timeout))
        return {"ok": True, "version": "29.0"}

    result = verify_illustrator_rpc(
        "http://127.0.0.1:47391",
        python_executable=sys.executable,
        token="verify-secret",
        target="illustrator-2025",
        python_probe=python_probe,
        broker_probe=broker_probe,
        illustrator_probe=illustrator_probe,
    )

    assert result["directly_usable"] is True
    assert [item[0] for item in calls] == ["python", "broker", "illustrator"]
    assert calls[-1][3] == "illustrator-2025"
    assert "verify-secret" not in json.dumps(result)


def test_verify_preserves_host_specific_missing_cep_session_stage():
    result = verify_illustrator_rpc(
        "http://127.0.0.1:47391",
        python_executable=sys.executable,
        token="verify-secret",
        python_probe=lambda *_: {"ok": True},
        broker_probe=lambda *_: {"ok": True, "sessions": 1},
        illustrator_probe=lambda *_: {"ok": False, "failure_stage": "cep_session"},
    )

    assert result["failure_stage"] == "cep_session"


def test_public_lifecycle_never_accepts_a_token_argument():
    args = SimpleNamespace(
        command="status",
        json=True,
        yes=False,
        dry_run=False,
        dcc_path="",
        python="",
    )
    assert run_install_lifecycle(args) == 0


def _lifecycle_args(command: str, host: Path, *, yes: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        command=command,
        json=True,
        yes=yes,
        dry_run=False,
        dcc_path=str(host),
        python=sys.executable,
    )


def _bridge_runner(command, **_kwargs):
    destination = Path(command[command.index("--dest") + 1])
    (destination / "CSXS").mkdir(parents=True)
    (destination / "CSXS" / "manifest.xml").write_text("manifest")
    (destination / "dist").mkdir()
    (destination / "dist" / "main.js").write_text("bridge")
    (destination / "dist" / "dom.jsx").write_text("dom")
    (destination / "adobepy.config.js").write_text("private-config")
    return subprocess.CompletedProcess(command, 0, stdout='{"success":true}', stderr="")


def test_public_install_and_receipt_only_uninstall_round_trip(tmp_path, monkeypatch, capsys):
    host = _write_windows_host(tmp_path / "Adobe")
    cli = tmp_path / "adobepy.exe"
    cli.write_bytes(b"")
    state = tmp_path / "state"
    monkeypatch.setenv("DCC_MCP_ILLUSTRATOR_INSTALL_STATE_DIR", str(state))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv("ADOBEPY_CLI", str(cli))
    monkeypatch.setenv("ADOBEPY_TOKEN", "round-trip-secret")

    installed = run_install_lifecycle(
        _lifecycle_args("install", host, yes=True),
        platform_name="Windows",
        external_runner=_bridge_runner,
        python_probe=lambda *_: {"ok": True},
        broker_probe=lambda *_: {"ok": True, "sessions": 1},
        illustrator_probe=lambda *_: {"ok": True, "version": "29.0"},
    )
    install_report = json.loads(capsys.readouterr().out)

    assert installed == 0
    _assert_sop_schema(install_report)
    assert install_report["verify"]["directly_usable"] is True
    receipt = state / "receipts" / "illustrator.json"
    assert receipt.is_file()
    bridge = Path(install_report["plan"]["bridge"]["destination"])
    assert bridge.is_dir()
    assert "round-trip-secret" not in receipt.read_text()

    verify_exit = run_install_lifecycle(
        _lifecycle_args("verify", host),
        platform_name="Windows",
        python_probe=lambda *_: {"ok": True},
        broker_probe=lambda *_: {"ok": True, "sessions": 0},
        illustrator_probe=lambda *_: {"ok": True, "version": "29.0"},
    )
    verify_report = json.loads(capsys.readouterr().out)
    assert verify_exit == 40
    _assert_sop_schema(verify_report)
    assert len(verify_report["next_steps"]) == 1
    assert verify_report["next_steps"][0]["command"][0] == "reg.exe"

    repeated = run_install_lifecycle(
        _lifecycle_args("install", host, yes=True),
        platform_name="Windows",
        external_runner=_bridge_runner,
        python_probe=lambda *_: {"ok": True},
        broker_probe=lambda *_: {"ok": True, "sessions": 1},
        illustrator_probe=lambda *_: {"ok": True, "version": "29.0"},
    )
    repeated_report = json.loads(capsys.readouterr().out)
    assert repeated == 0
    _assert_sop_schema(repeated_report)
    assert repeated_report["installed_state"] == "installed"

    upgrade = run_install_lifecycle(
        _lifecycle_args("upgrade", host),
        platform_name="Windows",
    )
    upgrade_report = json.loads(capsys.readouterr().out)
    assert upgrade == 0
    _assert_sop_schema(upgrade_report)
    assert upgrade_report["status"] == "planned"

    removed = run_install_lifecycle(
        _lifecycle_args("uninstall", host, yes=True),
        platform_name="Windows",
    )
    uninstall_report = json.loads(capsys.readouterr().out)
    assert removed == 0
    _assert_sop_schema(uninstall_report)
    assert uninstall_report["installed_state"] == "fresh"
    assert not bridge.exists()
    assert not receipt.exists()

    assert (
        run_install_lifecycle(
            _lifecycle_args("uninstall", host, yes=True),
            platform_name="Windows",
        )
        == 0
    )


def test_installed_but_disconnected_cep_fails_verify_without_fake_restart(
    tmp_path, monkeypatch, capsys
):
    host = _write_windows_host(tmp_path / "Adobe")
    cli = tmp_path / "adobepy.exe"
    cli.write_bytes(b"")
    monkeypatch.setenv("DCC_MCP_ILLUSTRATOR_INSTALL_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv("ADOBEPY_CLI", str(cli))
    monkeypatch.setenv("ADOBEPY_TOKEN", "session-secret")

    exit_code = run_install_lifecycle(
        _lifecycle_args("install", host, yes=True),
        platform_name="Windows",
        external_runner=_bridge_runner,
        python_probe=lambda *_: {"ok": True},
        broker_probe=lambda *_: {"ok": True, "sessions": 0},
        illustrator_probe=lambda *_: {"ok": True, "version": "29.0"},
    )
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 40
    assert report["status"] == "failed"
    assert report["verify"]["failure_stage"] == "cep_session"
    assert len(report["next_steps"]) == 1
    assert report["next_steps"][0]["command"][:3] == [
        "reg.exe",
        "ADD",
        r"HKCU\Software\Adobe\CSXS.12",
    ]
    assert report["exit_code"] == 40


def test_failed_commit_restores_previous_extension_and_receipt(tmp_path):
    destination = tmp_path / "extension"
    destination.mkdir()
    (destination / "old.txt").write_text("old")
    staging = tmp_path / "stage"
    staging.mkdir()
    (staging / "new.txt").write_text("new")
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text('{"old": true}')

    def fail_new_commit(source, target):
        if Path(source) == staging:
            raise OSError("injected commit failure")
        Path(source).replace(target)

    status, error = commit_bridge(
        staging=staging,
        destination=destination,
        receipt_path=receipt_path,
        receipt={
            "schema_version": 1,
            "dcc_type": "illustrator",
            "bridge_root": str(destination),
        },
        replacer=fail_new_commit,
    )

    assert status == "failed"
    assert "restored" in error
    assert (destination / "old.txt").read_text() == "old"
    assert receipt_path.read_text() == '{"old": true}'


def test_bootstrap_capture_redacts_tokens_and_url_userinfo(tmp_path, monkeypatch):
    monkeypatch.setenv("DCC_MCP_ILLUSTRATOR_INSTALL_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("ADOBEPY_TOKEN", "bootstrap-secret")

    message = capture_bootstrap_error(
        "startup", "bootstrap-secret at http://operator:password@127.0.0.1:47391 failed"
    )

    assert "bootstrap-secret" not in message
    assert "operator:password" not in message
    persisted = (tmp_path / "bootstrap-errors.json").read_text()
    assert "bootstrap-secret" not in persisted
    assert "operator:password" not in persisted


def test_receipted_damage_is_a_repair_plan_but_unowned_cep_is_refused(tmp_path, monkeypatch):
    host = _write_windows_host(tmp_path / "Adobe")
    cli = tmp_path / "adobepy.exe"
    cli.write_bytes(b"")
    state = tmp_path / "state"
    appdata = tmp_path / "AppData"
    monkeypatch.setenv("DCC_MCP_ILLUSTRATOR_INSTALL_STATE_DIR", str(state))
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("ADOBEPY_CLI", str(cli))
    monkeypatch.setenv("ADOBEPY_TOKEN", "repair-secret")
    destination = resolve_cep_extension_root("Windows")
    assert destination is not None
    staging = tmp_path / "stage"
    (staging / "CSXS").mkdir(parents=True)
    (staging / "CSXS" / "manifest.xml").write_text("original")
    (staging / "adobepy.config.js").write_text("private")
    receipt_path = state / "receipts" / "illustrator.json"
    status, _ = commit_bridge(
        staging=staging,
        destination=destination,
        receipt_path=receipt_path,
        receipt={
            "schema_version": 1,
            "dcc_type": "illustrator",
            "bridge_root": str(destination),
        },
    )
    assert status == "ok"
    (destination / "CSXS" / "manifest.xml").write_text("damaged")

    repair, repair_exit = build_install_report(
        verb="install",
        dcc_path=str(host),
        python=sys.executable,
        dry_run=True,
        platform_name="Windows",
    )
    assert repair_exit == 0
    assert repair["installed_state"] == "repair"
    assert repair["status"] == "planned"

    receipt_path.unlink()
    partial, partial_exit = build_install_report(
        verb="install",
        dcc_path=str(host),
        python=sys.executable,
        dry_run=True,
        platform_name="Windows",
    )
    assert partial_exit == 10
    assert partial["installed_state"] == "partial"
    assert partial["verify"]["failure_stage"] == "partial_state"
    assert destination.exists()


def test_public_parser_has_no_token_flag():
    with pytest.raises(SystemExit) as failure:
        build_parser().parse_args(["status", "--token", "must-not-enter-argv"])
    assert failure.value.code == 2


def test_preflight_and_acquire_exit_codes_are_stable(tmp_path, monkeypatch):
    host = _write_windows_host(tmp_path / "Adobe")
    monkeypatch.setenv("DCC_MCP_ILLUSTRATOR_INSTALL_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv("ADOBEPY_TOKEN", "exit-secret")
    monkeypatch.setattr("dcc_mcp_illustrator.install_planning._adobepy_cli", lambda: None)

    acquire, acquire_exit = build_install_report(
        verb="install",
        dcc_path=str(host),
        python=sys.executable,
        dry_run=True,
        platform_name="Windows",
    )
    assert acquire_exit == 20
    assert acquire["verify"]["failure_stage"] == "acquire"

    preflight, preflight_exit = build_install_report(
        verb="install",
        dcc_path=str(host),
        python=str(tmp_path / "stale-python"),
        dry_run=True,
        platform_name="Windows",
    )
    assert preflight_exit == 10
    assert preflight["verify"]["failure_stage"] == "python"
