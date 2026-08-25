from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from yaml.resolver import BaseResolver

ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
SHA = re.compile(r"^[0-9a-f]{40}$")
HEAD_SOURCE_BINDING = 'test "$(git rev-parse HEAD)" = "$source_sha"'

PINNED_ACTIONS = {
    "googleapis/release-please-action": "45996ed1f6d02564a971a2fa1b5860e934307cf7",
    "actions/checkout": "d23441a48e516b6c34aea4fa41551a30e30af803",
    "actions/setup-python": "ece7cb06caefa5fff74198d8649806c4678c61a1",
    "actions/upload-artifact": "ea165f8d65b6e75b540449e92b4886f43607fa02",
    "actions/download-artifact": "d3f86a106a0bac45b974a628896c90dbdf5c8093",
    "pypa/gh-action-pypi-publish": "dc37677b2e1c63e2034f94d8a5b11f265b73ba33",
}


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key, value in loader.construct_pairs(node, deep=deep):
        if key in mapping:
            raise AssertionError(f"duplicate YAML mapping key: {key}")
        mapping[key] = value
    return mapping


_UniqueKeyLoader.add_constructor(BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping)


def _load_workflow(text: str) -> dict:
    workflow = yaml.load(text, Loader=_UniqueKeyLoader)
    assert isinstance(workflow, dict)
    return workflow


def _steps(job: dict) -> list[dict]:
    return [step for step in job["steps"] if isinstance(step, dict)]


def _step(job: dict, name: str) -> tuple[int, dict]:
    matches = [(index, step) for index, step in enumerate(_steps(job)) if step.get("name") == name]
    assert len(matches) == 1, f"expected exactly one structured step: {name}"
    return matches[0]


def _assert_unique_steps(job_name: str, job: dict) -> None:
    names = [step["name"] for step in _steps(job) if "name" in step]
    ids = [step["id"] for step in _steps(job) if "id" in step]
    assert len(names) == len(set(names)), f"duplicate step name in {job_name}"
    assert len(ids) == len(set(ids)), f"duplicate step id in {job_name}"


def _validate_release_contract(text: str) -> None:
    workflow = _load_workflow(text)
    assert workflow["permissions"] == {}
    jobs = workflow["jobs"]
    assert all(1 <= job["timeout-minutes"] <= 30 for job in jobs.values())
    for job_name, job in jobs.items():
        _assert_unique_steps(job_name, job)

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
    source_index, source = _step(build, "Capture immutable source identity")
    assert source["run"].count(HEAD_SOURCE_BINDING) == 1
    assert build_runs.count("python -m build") == 1
    assert all_runs.count("python -m build") == 1
    assert all_runs.count("gh release upload") == 1
    assert "--clobber" not in all_runs
    assert source_index < upload_index
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
        assert verify["env"]["ARTIFACT_DIGEST"] == (
            "${{ needs.build-release-artifact.outputs.artifact_digest }}"
        )
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

    all_uses = [step["uses"] for job in jobs.values() for step in _steps(job) if step.get("uses")]
    assert (
        all_uses.count("pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33") == 1
    )
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


def test_release_source_binding_ignores_comment_decoy():
    text = WORKFLOW.read_text(encoding="utf-8")
    tampered = text.replace(f"          {HEAD_SOURCE_BINDING}\n", "", 1)
    tampered += f"\n# {HEAD_SOURCE_BINDING}\n"

    with pytest.raises(AssertionError):
        _validate_release_contract(tampered)


def test_release_contract_rejects_duplicate_mapping_key():
    text = WORKFLOW.read_text(encoding="utf-8")
    tampered = text.replace("jobs:\n", "jobs:\n  release-please: {}\n", 1)

    with pytest.raises(AssertionError):
        _validate_release_contract(tampered)


def test_release_contract_rejects_duplicate_and_unbound_upload_mutations():
    text = WORKFLOW.read_text(encoding="utf-8")
    marker = "      - name: Attach exact release artifacts without clobber\n"
    duplicate = (
        "      - name: Attach exact release artifacts without clobber\n"
        "        run: echo duplicate\n"
    )
    unbound = (
        "      - name: Shadow release mutation\n"
        '        run: gh release upload "$TAG" dist/* --clobber\n'
    )

    with pytest.raises(AssertionError):
        _validate_release_contract(text.replace(marker, duplicate + marker, 1))
    with pytest.raises(AssertionError):
        _validate_release_contract(text.replace(marker, unbound + marker, 1))


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def _bash_executable() -> str:
    git = shutil.which("git")
    assert git is not None
    if os.name == "nt":
        candidate = Path(git).resolve().parent.parent / "bin" / "bash.exe"
        if candidate.is_file():
            return str(candidate)
    bash = shutil.which("bash")
    assert bash is not None
    return bash


def test_release_source_capture_rejects_tag_move_after_checkout(tmp_path: Path):
    workflow = _load_workflow(WORKFLOW.read_text(encoding="utf-8"))
    _, source_step = _step(
        workflow["jobs"]["build-release-artifact"], "Capture immutable source identity"
    )
    script = source_step["run"]

    remote = tmp_path / "remote.git"
    seed = tmp_path / "seed"
    checkout = tmp_path / "checkout"
    _git(tmp_path, "init", "--bare", str(remote))
    seed.mkdir()
    _git(seed, "init", "--initial-branch=main")
    _git(seed, "config", "user.name", "Release Contract")
    _git(seed, "config", "user.email", "release-contract@example.invalid")
    (seed / "payload.txt").write_text("A", encoding="utf-8")
    _git(seed, "add", "payload.txt")
    _git(seed, "commit", "-m", "A")
    commit_a = _git(seed, "rev-parse", "HEAD")
    _git(seed, "tag", "v0.3.0")
    _git(seed, "remote", "add", "origin", str(remote))
    _git(seed, "push", "origin", "main", "refs/tags/v0.3.0")
    _git(tmp_path, "clone", str(remote), str(checkout))
    _git(checkout, "checkout", "--detach", "v0.3.0")

    environment = os.environ.copy()
    environment.update({"TAG": "v0.3.0", "GITHUB_OUTPUT": "source.out"})
    stable = subprocess.run(
        [_bash_executable(), "--noprofile", "--norc", "-euo", "pipefail", "-c", script],
        cwd=checkout,
        env=environment,
        text=True,
        capture_output=True,
    )
    assert stable.returncode == 0, stable.stderr
    assert f"sha={commit_a}" in (checkout / "source.out").read_text(encoding="utf-8")

    (seed / "payload.txt").write_text("B", encoding="utf-8")
    _git(seed, "commit", "-am", "B")
    _git(seed, "tag", "--force", "v0.3.0")
    _git(seed, "push", "--force", "origin", "refs/tags/v0.3.0")

    moved = subprocess.run(
        [_bash_executable(), "--noprofile", "--norc", "-euo", "pipefail", "-c", script],
        cwd=checkout,
        env=environment,
        text=True,
        capture_output=True,
    )
    assert moved.returncode != 0, "moved release tag must fail before build"
