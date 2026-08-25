from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
SHA = re.compile(r"^[0-9a-f]{40}$")

PINNED_ACTIONS = {
    "googleapis/release-please-action": "45996ed1f6d02564a971a2fa1b5860e934307cf7",
    "actions/checkout": "d23441a48e516b6c34aea4fa41551a30e30af803",
    "actions/setup-python": "ece7cb06caefa5fff74198d8649806c4678c61a1",
    "actions/upload-artifact": "ea165f8d65b6e75b540449e92b4886f43607fa02",
    "actions/download-artifact": "d3f86a106a0bac45b974a628896c90dbdf5c8093",
    "pypa/gh-action-pypi-publish": "dc37677b2e1c63e2034f94d8a5b11f265b73ba33",
}


def _steps(job: dict) -> list[dict]:
    return [step for step in job["steps"] if isinstance(step, dict)]


def _step(job: dict, name: str) -> tuple[int, dict]:
    for index, step in enumerate(_steps(job)):
        if step.get("name") == name:
            return index, step
    raise AssertionError(f"missing structured step: {name}")


def _validate_release_contract(text: str) -> None:
    workflow = yaml.safe_load(text)
    assert workflow["permissions"] == {}
    jobs = workflow["jobs"]
    assert all(1 <= job["timeout-minutes"] <= 30 for job in jobs.values())

    build = jobs["build-release-artifact"]
    assert set(build["needs"]) == {"release-please"}
    assert build["permissions"] == {"contents": "read"}
    upload_index, upload = _step(build, "Upload immutable release artifact")
    assert upload["uses"] == ("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02")
    assert upload["with"]["path"] == "dist/*"
    assert upload["with"]["if-no-files-found"] == "error"
    assert upload["with"]["overwrite"] is False
    assert build["outputs"] == {
        "source_sha": "${{ steps.source.outputs.sha }}",
        "artifact_id": "${{ steps.upload.outputs.artifact-id }}",
        "artifact_digest": "${{ steps.upload.outputs.artifact-digest }}",
    }

    build_runs = "\n".join(step.get("run", "") for step in _steps(build))
    all_runs = "\n".join(step.get("run", "") for job in jobs.values() for step in _steps(job))
    assert build_runs.count("python -m build") == 1
    assert all_runs.count("python -m build") == 1
    assert upload_index > 0

    for job_name in ("publish-pypi", "attach-github-release"):
        job = jobs[job_name]
        assert set(job["needs"]) == {"release-please", "build-release-artifact"}
        _, download = _step(job, "Download immutable release artifact")
        assert download["uses"] == (
            "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093"
        )
        assert download["with"]["artifact-ids"] == (
            "${{ needs.build-release-artifact.outputs.artifact_id }}"
        )
        assert download["with"]["path"] == "dist"

    publish = jobs["publish-pypi"]
    assert publish["permissions"] == {"contents": "read", "id-token": "write"}
    verify_pypi_index, verify_pypi = _step(publish, "Revalidate release immediately before PyPI")
    publish_steps = _steps(publish)
    assert publish_steps[verify_pypi_index + 1]["uses"] == (
        "pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33"
    )

    attach = jobs["attach-github-release"]
    assert attach["permissions"] == {"contents": "write"}
    verify_gh_index, verify_gh = _step(
        attach, "Revalidate release immediately before GitHub upload"
    )
    attach_steps = _steps(attach)
    mutation = attach_steps[verify_gh_index + 1]
    assert mutation["name"] == "Attach exact release artifacts without clobber"
    assert "gh release upload" in mutation["run"]
    assert "--clobber" not in mutation["run"]

    for verify in (verify_pypi, verify_gh):
        run = verify["run"]
        for required in (
            "gh api",
            "git fetch",
            "git rev-parse",
            "SOURCE_SHA",
            "ARTIFACT_ID",
            "ARTIFACT_DIGEST",
            "target_commitish",
        ):
            assert required in run

    for job in jobs.values():
        for step in _steps(job):
            uses = step.get("uses")
            if not uses:
                continue
            owner, value = uses.split("@", 1)
            assert SHA.fullmatch(value), uses
            assert value == PINNED_ACTIONS[owner], uses


def test_release_workflow_builds_once_and_reuses_one_identity_bound_artifact():
    _validate_release_contract(WORKFLOW.read_text(encoding="utf-8"))


def test_release_contract_ignores_adversarial_comment_and_decoy_text():
    text = WORKFLOW.read_text(encoding="utf-8")
    tampered = text.replace("python -m build", "python -m pip --version", 1)
    tampered += "\n# python -m build\n# gh release upload dist/*\n# SOURCE_SHA ARTIFACT_ID ARTIFACT_DIGEST target_commitish\n"

    with pytest.raises(AssertionError):
        _validate_release_contract(tampered)
