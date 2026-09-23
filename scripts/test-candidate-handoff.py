#!/usr/bin/env python3
"""Exercise source candidate metadata, trusted publication, and rejection paths."""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
CREATE = ROOT / "scripts/create-candidate-build-metadata.py"
FINALIZE = ROOT / "scripts/finalize-source-candidate.py"
REPOSITORY = "The-Pipeline-Framework/rag-turnkey"
SHA = "0123456789abcdef0123456789abcdef01234567"


def build_artifact(path: pathlib.Path, event: str) -> dict[str, str]:
    source_repository = "Contributor/rag-turnkey" if event == "pull_request" else REPOSITORY
    environment = os.environ | {
        "GITHUB_REPOSITORY": REPOSITORY,
        "SOURCE_REPOSITORY": source_repository,
        "SOURCE_SHA": SHA,
        "PULL_REQUEST_NUMBER": "42" if event == "pull_request" else "",
        "GITHUB_EVENT_NAME": event,
        "GITHUB_RUN_ID": "1234",
        "GITHUB_RUN_ATTEMPT": "2",
    }
    subprocess.run(["python3", str(CREATE), str(path)], check=True, cwd=ROOT, env=environment)
    return environment


def publisher_environment(event: str, pr_path: pathlib.Path, associated: str | None = None) -> dict[str, str]:
    is_pr = event == "pull_request"
    if associated is None:
        associated = json.dumps([{
            "number": 42,
            "head": {"sha": SHA, "repo": {"full_name": "Contributor/rag-turnkey"}},
            "base": {"repo": {"full_name": REPOSITORY}},
        }]) if is_pr else "[]"
    return os.environ | {
        "BUILD_RUN_ID": "1234",
        "BUILD_RUN_ATTEMPT": "2",
        "BUILD_RUN_CONCLUSION": "success",
        "BUILD_RUN_EVENT": event,
        "BUILD_RUN_HEAD_SHA": SHA if not is_pr else "fedcba9876543210fedcba9876543210fedcba98",
        "BUILD_RUN_HEAD_BRANCH": "candidate-branch" if is_pr else "main",
        "BUILD_RUN_DEFAULT_BRANCH": "main",
        "BUILD_RUN_PATH": ".github/workflows/tpf-candidate-build.yml",
        "BUILD_RUN_REPOSITORY": REPOSITORY,
        "BUILD_ASSOCIATED_PRS": associated,
        "CURRENT_PR_JSON": str(pr_path),
        "GITHUB_RUN_ID": "5678",
        "GITHUB_RUN_ATTEMPT": "1",
    }


def pr_fixture(*, sha: str = SHA, labels: list[str] | None = None) -> dict:
    return {
        "state": "open",
        "number": 42,
        "head": {
            "sha": sha,
            "ref": "candidate-branch",
            "repo": {"full_name": "Contributor/rag-turnkey"},
        },
        "base": {"repo": {"full_name": REPOSITORY}},
        "labels": [{"name": label} for label in (labels if labels is not None else ["safe-to-system-test"])],
    }


def run_publisher(path: pathlib.Path, env: dict[str, str], pr: dict | None) -> subprocess.CompletedProcess:
    pathlib.Path(env["CURRENT_PR_JSON"]).write_text(json.dumps(pr or {}))
    return subprocess.run(["python3", str(FINALIZE), str(path), env["CURRENT_PR_JSON"]], cwd=ROOT,
                          env=env, capture_output=True, text=True)


def copy_build(source: pathlib.Path, destination: pathlib.Path) -> pathlib.Path:
    destination.mkdir()
    for name in ("build-metadata.json", "build-metadata.sha256"):
        shutil.copy2(source / name, destination / name)
    return destination


with tempfile.TemporaryDirectory(prefix="tpf-rag-source-handoff-") as temporary:
    root = pathlib.Path(temporary)
    pr_build = root / "pr-build"
    build_artifact(pr_build, "pull_request")
    pr_file = root / "current-pr.json"
    publish_env = publisher_environment("pull_request", pr_file)
    result = run_publisher(pr_build, publish_env, pr_fixture())
    assert result.returncode == 0, result.stderr
    manifest_bytes = (pr_build / "candidate-manifest/candidate-manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    event = json.loads((pr_build / "candidate-event/event.json").read_text())
    assert manifest["repository"] == REPOSITORY and manifest["component"] == "ragTurnkey"
    assert manifest["pullRequestNumber"] == 42
    assert manifest["provenance"]["build"]["runId"] == 1234
    assert manifest["provenance"]["publication"]["runId"] == 5678
    assert manifest["mavenArtifacts"] == [] and manifest["images"] == []
    assert event["manifest_sha256"] == hashlib.sha256(manifest_bytes).hexdigest()
    assert event["source_repository"] == REPOSITORY and event["source_sha"] == SHA
    assert event["component"] == "ragTurnkey"

    for case, association, pr in [
        ("missing-associated-pr", "[]", pr_fixture()),
        ("fork-without-safe-label", None, pr_fixture(labels=[])),
        ("stale-pr-head", None, pr_fixture(sha="fedcba9876543210fedcba9876543210fedcba98")),
    ]:
        case_build = copy_build(pr_build, root / case)
        env = publisher_environment("pull_request", root / f"{case}-pr.json", association)
        assert run_publisher(case_build, env, pr).returncode != 0, f"{case} must be rejected"

    checksum_build = copy_build(pr_build, root / "checksum-mismatch")
    metadata_path = checksum_build / "build-metadata.json"
    metadata_path.write_bytes(metadata_path.read_bytes() + b" ")
    checksum_env = publisher_environment("pull_request", root / "checksum-pr.json")
    assert run_publisher(checksum_build, checksum_env, pr_fixture()).returncode != 0

    main_build = root / "main-build"
    build_artifact(main_build, "push")
    main_env = publisher_environment("push", root / "main-pr.json", "[]")
    main_result = run_publisher(main_build, main_env, None)
    assert main_result.returncode == 0, main_result.stderr
    main_manifest = json.loads((main_build / "candidate-manifest/candidate-manifest.json").read_text())
    assert main_manifest["pullRequestNumber"] is None
    assert main_manifest["candidateVersion"].endswith(f"-main.{SHA[:12]}")

    mismatched_build = copy_build(main_build, root / "main-sha-mismatch")
    mismatched_env = main_env | {"BUILD_RUN_HEAD_SHA": "fedcba9876543210fedcba9876543210fedcba98"}
    assert run_publisher(mismatched_build, mismatched_env, None).returncode != 0

print("RAG Turnkey source candidate handoff, provenance, checksum, and rejection fixtures passed")
