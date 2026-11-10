# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-1 §7)
# Purpose: the W9 reader's read modes and handle-bound refusals, on scratch Git repositories under tmp_path.
"""W9 reader tests (WP9.3 note §7.1, §7.4, §7.5). No live legacy file, vault or restricted byte is read (§17)."""

from __future__ import annotations

import hashlib
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

import research_system.legacy.reader as reader_module
from research_system.legacy.reader import LegacyReader, ReadRefused, git_blob_id, handle_bound_read

CLOCK = lambda: datetime(2026, 9, 1, tzinfo=UTC)  # noqa: E731


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    (root / "results").mkdir(parents=True)
    (root / "results" / "x.json").write_bytes(b'{"a": 1}\n')
    (root / "CONVENTIONS.md").write_bytes(b"# Conventions\n")
    _git(root, "init", "-q")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "fixture")
    return root, _git(root, "rev-parse", "HEAD")


def _registration(path: str, kind: str = "git_tracked", role: str = "legacy_research_result", target: str = "x"):
    return {
        "normalized_path": path,
        "source_identity_kind": kind,
        "role": role,
        "physical_identity": {"canonical_target": target},
    }


def test_a_git_tracked_read_is_the_working_tree_and_the_blob_at_git_head(repo) -> None:
    root, head = repo
    read = LegacyReader(repository_root=root, git_head=head, clock=CLOCK).read(_registration("results/x.json"))
    assert read.raw == b'{"a": 1}\n'
    assert read.source_identity == {
        "identity_kind": "git_tracked",
        "repository_path": "results/x.json",
        "git_commit": head,
        "git_blob": git_blob_id(b'{"a": 1}\n'),
        "sha256": hashlib.sha256(b'{"a": 1}\n').hexdigest(),
        "byte_length": 9,
    }
    assert read.read_started_at == "2026-09-01T00:00:00.000000Z"
    assert read.non_inferences == ("no authority from file presence (W0 §4)",)
    assert read.physical_identity["link_count"] == 1


def test_a_dirty_working_tree_is_refused(repo) -> None:
    root, head = repo
    (root / "results" / "x.json").write_bytes(b'{"a": 2}\n')
    with pytest.raises(ReadRefused, match="the working tree differs from the bytes at the binding's git_head"):
        LegacyReader(repository_root=root, git_head=head).read(_registration("results/x.json"))


def test_a_git_tracked_read_without_git_head_is_refused(repo) -> None:
    root, _ = repo
    with pytest.raises(ReadRefused, match="a git_tracked read needs the binding's git_head"):
        LegacyReader(repository_root=root, git_head=None).read(_registration("results/x.json"))


def test_an_untracked_and_a_restricted_read_record_hash_size_and_path(repo) -> None:
    root, head = repo
    (root / "notes.md").write_bytes(b"note\n")
    (root / "data.pkl").write_bytes(b"\x80\x04")
    reader = LegacyReader(repository_root=root, git_head=head)
    untracked = reader.read(_registration("notes.md", "untracked_file"))
    assert set(untracked.source_identity) == {"identity_kind", "path", "sha256", "byte_length"}
    assert untracked.non_inferences == ("no authority from file presence (W0 §4)", "no Git identity")
    restricted = reader.read(_registration("data.pkl", "restricted_untracked_file"))
    assert restricted.source_identity["byte_length"] == 2
    assert "no frozen copy in the ARS store" in restricted.non_inferences


def test_a_second_hard_link_is_refused(repo) -> None:
    root, head = repo
    (root / "notes.md").write_bytes(b"note\n")
    os.link(root / "notes.md", root / "alias.md")
    with pytest.raises(ReadRefused, match="the registered file has more than one link"):
        handle_bound_read(root, "notes.md")


def test_a_symlink_leaf_is_refused(repo) -> None:
    root, _ = repo
    (root / "target.md").write_bytes(b"t\n")
    try:
        os.symlink(root / "target.md", root / "link.md")
    except OSError:
        pytest.skip("symbolic links need Developer Mode or privileges on this host")
    with pytest.raises(ReadRefused, match="the registered path is a symlink or junction"):
        handle_bound_read(root, "link.md")


@pytest.mark.parametrize("path", ["../x", "/abs", "a\\b", "", "a/./b"])
def test_a_non_canonical_path_is_refused(repo, path: str) -> None:
    root, _ = repo
    with pytest.raises(ReadRefused, match="registered path is not a canonical relative path"):
        handle_bound_read(root, path)


def test_a_missing_file_is_refused(repo) -> None:
    root, _ = repo
    with pytest.raises(ReadRefused, match="the registered file is missing"):
        handle_bound_read(root, "nothing.md")


def test_the_conventions_lock_reads_only_its_pinned_blob(repo, monkeypatch) -> None:
    root, head = repo
    blob = _git(root, "rev-parse", f"{head}:CONVENTIONS.md")
    monkeypatch.setattr(
        reader_module, "CONVENTIONS_LOCK", {**reader_module.CONVENTIONS_LOCK, "git_commit": head, "git_blob": blob}
    )
    read = LegacyReader(repository_root=root, git_head=head).read(
        _registration("CONVENTIONS.md", role="conventions_lock")
    )
    assert read.source_identity["git_blob"] == blob and read.raw == b"# Conventions\n"
    monkeypatch.setattr(reader_module, "CONVENTIONS_LOCK", {**reader_module.CONVENTIONS_LOCK, "git_blob": "0" * 40})
    with pytest.raises(ReadRefused, match="CONVENTIONS.md is read only from blob 4620c716"):
        LegacyReader(repository_root=root, git_head=head).read(_registration("CONVENTIONS.md", role="conventions_lock"))


def test_a_computational_log_entry_needs_an_accepted_export(repo) -> None:
    root, head = repo
    registration = _registration("04-Methods/Computational-Log.md", "vault_file", "legacy_decision_log_entry")
    with pytest.raises(ReadRefused, match="no accepted Computational-Log export"):
        LegacyReader(repository_root=root, git_head=head).read(registration)


def test_a_vault_read_resolves_to_its_registered_target(repo, tmp_path: Path) -> None:
    root, head = repo
    vault = tmp_path / "vault"
    (vault / "notes").mkdir(parents=True)
    (vault / "notes" / "a.md").write_bytes(b"a\n")
    target = (vault / "notes" / "a.md").resolve().as_posix()
    reader = LegacyReader(repository_root=root, git_head=head, vault_root=vault)
    read = reader.read(_registration("notes/a.md", "vault_file", target=target))
    assert read.source_identity == {
        "identity_kind": "vault_file",
        "vault_path": "notes/a.md",
        "sha256": read.source_identity["sha256"],
        "byte_length": 2,
    }
    with pytest.raises(ReadRefused, match="does not resolve to the registration's canonical target"):
        reader.read(_registration("notes/a.md", "vault_file", target="C:/elsewhere/a.md"))


def test_a_vault_read_of_the_repositorys_conventions_is_refused(repo, tmp_path: Path) -> None:
    root, head = repo
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Conventions.md").write_bytes(b"# Conventions\n")
    reader = LegacyReader(repository_root=root, git_head=head, vault_root=vault)
    with pytest.raises(ReadRefused, match="resolves to the repository's CONVENTIONS.md"):
        reader.read(_registration("Conventions.md", "vault_file", target="x"))


def test_the_vault_is_never_read_through_the_repository(repo) -> None:
    root, head = repo
    (root / "vault").mkdir()
    with pytest.raises(ReadRefused, match="the vault is read through its real path, never through the repository"):
        LegacyReader(repository_root=root, git_head=head, vault_root=root / "vault")


def test_the_importer_identity_hashes_the_reader_and_segmenter_blobs_at_git_head(tmp_path: Path) -> None:
    from research_system.canonical import canonical_bytes, sha256_hex

    code = tmp_path / "code"
    for path in reader_module.IMPORTER_MODULES:
        (code / path).parent.mkdir(parents=True, exist_ok=True)
        (code / path).write_bytes(f"# {path}\n".encode())
    _git(code, "init", "-q")
    _git(code, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    _git(code, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "code")
    head = _git(code, "rev-parse", "HEAD")
    identity = LegacyReader(repository_root=code, git_head=head).importer_identity("act_x")
    blobs = {path: git_blob_id(f"# {path}\n".encode()) for path in reader_module.IMPORTER_MODULES}
    assert identity == {
        "actor_id": "act_x",
        "tool_id": "research_system.legacy.reader",
        "tool_version": "1.0.0",
        "tool_sha256": sha256_hex(canonical_bytes(blobs)),
    }
