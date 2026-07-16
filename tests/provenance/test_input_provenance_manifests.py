# Research context: TDA-Research/03-Papers/P01-A-JRSSA/_project.md
# Purpose: Binding test for the input-provenance-manifest-coherence contract
#   (R-C). Re-asserts every enforced input-provenance manifest against disk at
#   commit time, and exercises the rejection paths the contract claims.
"""Commit-time enforcement of input-provenance manifests.

Bound by ``contracts/data-provenance/input-provenance-manifest-coherence.yaml``.
The single bound function checks the three rejection cases the contract names
(missing input, sha256 mismatch, vintage-spread violation) against synthetic
manifests, then asserts every manifest currently marked ``enforced: true``
passes against the working tree.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import os
from pathlib import Path
import subprocess

from shared.input_provenance import (
    check_manifest,
    discover_manifests,
    load_manifest,
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("repo root (.git) not found above test file")


def _write_file(path: Path, content: bytes, vintage: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    ts = _dt.datetime.fromisoformat(f"{vintage}T12:00:00").timestamp()
    os.utime(path, (ts, ts))


def _init_git_repo(path: Path) -> None:
    """Create a tiny repository whose text files are checked out as CRLF."""
    for args in (
        ["init"],
        ["config", "user.email", "provenance@example.test"],
        ["config", "user.name", "Provenance Test"],
        ["config", "core.autocrlf", "true"],
    ):
        subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, text=True)


def _git_stdout(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_active_input_provenance_manifests_match_disk(tmp_path: Path) -> None:
    """Reject missing/mismatched/incoherent inputs; pass enforced manifests."""
    import hashlib

    good = b'{"gmm_labels": [0, 1, 2]}'
    good_sha = hashlib.sha256(good).hexdigest()
    _write_file(tmp_path / "a.json", good, "2026-04-08")
    _write_file(tmp_path / "b.json", b'{"seq": 1}', "2026-04-08")

    # (a) a declared input absent from disk is rejected.
    res_missing = check_manifest(
        {
            "id": "syn-missing",
            "inputs": [
                {"path": "a.json", "role": "present"},
                {"path": "does_not_exist.json", "role": "absent"},
            ],
        },
        tmp_path,
    )
    assert not res_missing.all_present
    assert not res_missing.ok

    # (b) an input whose recorded sha256 does not match the on-disk file.
    res_badhash = check_manifest(
        {
            "id": "syn-badhash",
            "inputs": [
                {"path": "a.json", "role": "labels", "expected": {"sha256": "deadbeef"}},
            ],
        },
        tmp_path,
    )
    assert not res_badhash.signatures_ok
    assert not res_badhash.ok

    # (b2) a proj_root input whose pinned vintage_date does not match its on-disk
    # mtime is rejected (b.json was written with mtime 2026-04-08).
    res_bad_vintage = check_manifest(
        {
            "id": "syn-badvintage",
            "inputs": [
                {
                    "path": "b.json",
                    "role": "seq",
                    "root": "proj_root",
                    "expected": {"vintage_date": "2026-04-07"},
                },
            ],
        },
        tmp_path,
        proj_root=tmp_path,
    )
    assert not res_bad_vintage.signatures_ok
    assert not res_bad_vintage.ok

    # (c) a co-consumed set of proj_root inputs whose vintage spread exceeds the
    # declared bound (vintage coherence applies only to proj_root inputs, where
    # mtime is meaningful — worktree mtimes are reset on checkout).
    _write_file(tmp_path / "late.json", b'{"seq": 2}', "2026-05-02")
    res_incoherent = check_manifest(
        {
            "id": "syn-incoherent",
            "coherence": {"max_vintage_spread_days": 1},
            "inputs": [
                {"path": "a.json", "role": "apr", "root": "proj_root"},
                {"path": "late.json", "role": "may", "root": "proj_root"},
            ],
        },
        tmp_path,
        proj_root=tmp_path,
    )
    assert not res_incoherent.coherent
    assert not res_incoherent.ok

    # A fully-coherent manifest passes: a worktree input signed by sha256 plus a
    # proj_root input pinned by vintage_date.
    res_good = check_manifest(
        {
            "id": "syn-good",
            "coherence": {"max_vintage_spread_days": 1},
            "inputs": [
                {"path": "a.json", "role": "labels", "expected": {"sha256": good_sha}},
                {
                    "path": "b.json",
                    "role": "seq",
                    "root": "proj_root",
                    "expected": {"vintage_date": "2026-04-08"},
                },
            ],
        },
        tmp_path,
        proj_root=tmp_path,
    )
    assert res_good.ok

    # Every real manifest marked enforced:true must pass against the working tree.
    repo_root = _repo_root()
    for manifest_path in discover_manifests(repo_root):
        manifest = load_manifest(manifest_path)
        if not manifest.get("enforced", False):
            continue
        result = check_manifest(manifest, repo_root)
        assert result.ok, f"enforced manifest {result.manifest_id} failed against disk: {result.violations}"


def test_worktree_blob_signature_ignores_checkout_line_endings_but_detects_content_drift(
    tmp_path: Path,
) -> None:
    """A git blob signature is invariant to CRLF checkout bytes, not content."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    tracked = repo / "tracked.txt"
    tracked.write_bytes(b"same text\n")
    _git_stdout(repo, "add", "tracked.txt")
    _git_stdout(repo, "commit", "-m", "add tracked text")
    blob_sha = _git_stdout(repo, "rev-parse", "HEAD:tracked.txt")

    # Reproduce the old false positive: identical text written with CRLF no
    # longer has the sha256 pin made from its LF working-tree bytes.
    tracked.write_bytes(b"same text\r\n")
    old_rule = check_manifest(
        {
            "id": "old-working-tree-sha256",
            "inputs": [
                {
                    "path": "tracked.txt",
                    "expected": {"sha256": hashlib.sha256(b"same text\n").hexdigest()},
                }
            ],
        },
        repo,
    )
    assert not old_rule.ok

    # The new signature is the clean Git object, so the equivalent CRLF text
    # validates identically in a fresh checkout.
    new_rule = check_manifest(
        {
            "id": "new-git-blob",
            "inputs": [{"path": "tracked.txt", "expected": {"blob_sha": blob_sha}}],
        },
        repo,
    )
    assert new_rule.ok
    assert new_rule.inputs[0].disk_blob_sha == blob_sha

    # It is not a lookup of HEAD alone: changed content must still fail.
    tracked.write_bytes(b"different text\r\n")
    changed = check_manifest(
        {
            "id": "changed-git-blob",
            "inputs": [{"path": "tracked.txt", "expected": {"blob_sha": blob_sha}}],
        },
        repo,
    )
    assert not changed.signatures_ok
    assert not changed.ok
