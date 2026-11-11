"""The closed-reference acceptance's environment checks: LR-016 and LR-020 (WP9.3 note §7.2, §10.1, §10.3, §10.4).

Replay checks everything the ledger determines (``replay/reducers.py``, ``check_acceptance``). This module adds what
only the environment can show, at LR-016 and again at LR-020 against the binding at resolution:

- **the window** (§7.2, O-33): every item's source re-read equals its observation, and, for an ``untracked_file`` or
  ``vault_file`` item, its frozen copy still hashes to the recorded bytes. A ``restricted_untracked_file`` item is
  re-read by hash only and has no copy. The runtime runs these again at commit, under the lock, after the shadow step;
- **the anchors** (§10.3; O-25, W9-T16; owner point G): each ``git_commit`` anchor is an ancestor of the binding's
  ``git_head`` and adds or changes a file whose bytes hash to the anchored SHA-256;
- **the change list** (§10.4; O-32): the committed list at ``git_head``, and, for each entry and each item whose
  registration it affects, the item is ``git_tracked`` and its observation's commit descends from the entry's merge
  commit;
- **the detector controls** (§10.1, §4.5's closed-reference column), re-read as LR-003 read them.

Two readings of the note, recorded in the WP9.3-2 record: a ``git_tracked`` item's re-read is compared by location and
bytes, not by ``git_commit``, because a later binding's head moves the commit but not the blob, and the recorded bytes
"cannot move" (§7.2); and "the commit adds or changes a file" is read against the commit's first parent, or the empty
tree for a root commit.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from research_system.errors import IntegrityError
from research_system.legacy import evidence
from research_system.legacy.reader import ReadRefused, _git

_FROZEN_COPY_KINDS = frozenset({"untracked_file", "vault_file"})
_ANCHORED_FIELDS = {
    "threshold_preregistration": "threshold_preregistration_sha256",
    "governing_record_set": "governing_record_set_sha256",
}


def batch_sources(legacy: Mapping[str, Any], record: Mapping[str, Any]) -> list[tuple[Mapping[str, Any], Any]]:
    """Each item's (registration, observation), from the replayed projection."""

    sources = []
    for item in record.get("items", []):
        observation = legacy["records"].get("legacy_observation", {}).get(item["observation_ref"]["id"])
        if observation is None:
            raise IntegrityError("W9 acceptance names no recorded observation")
        registration = legacy["records"]["legacy_path_registration"][observation["registration_ref"]["id"]]
        sources.append((registration, observation))
    return sources


def _comparable(identity: Mapping[str, Any]) -> dict[str, Any]:
    compared = {key: value for key, value in identity.items() if key != "frozen_copy_ref"}
    if compared.get("identity_kind") == "git_tracked":
        compared.pop("git_commit", None)
    return compared


def reread_items(environment: Any, legacy: Mapping[str, Any], record: Mapping[str, Any]) -> None:
    """§7.2: every item's source re-reads to its observation, and each frozen copy still holds the recorded bytes."""

    from research_system.legacy.preparers import _need_reader, check_frozen_copy

    reader = _need_reader(environment)
    for registration, observation in batch_sources(legacy, record):
        recorded = observation["source_identity"]
        try:
            read = reader.read(registration)
        except ReadRefused as exc:
            raise IntegrityError(f"W9 acceptance item's source cannot be read: {exc}") from exc
        if _comparable(read.source_identity) != _comparable(recorded):
            raise IntegrityError("W9 acceptance item's source re-reads differently from its observation")
        if recorded.get("identity_kind") in _FROZEN_COPY_KINDS:
            check_frozen_copy(environment, recorded["frozen_copy_ref"], recorded["sha256"], recorded["byte_length"])


def _introduced_blobs(repository_root: Path, commit: str) -> list[str]:
    """The blobs ``commit`` adds or modifies against its first parent, or all of its tree for a root commit."""

    try:
        parent = str(_git(repository_root, "rev-parse", "--verify", "--quiet", f"{commit}^1")).strip()
    except ReadRefused:
        parent = ""
    if parent:
        listing = str(_git(repository_root, "diff-tree", "-r", "--no-renames", "--diff-filter=AM", parent, commit))
        return [line.split()[3] for line in listing.splitlines() if line.startswith(":")]
    listing = str(_git(repository_root, "ls-tree", "-r", commit))
    return [line.split()[2] for line in listing.splitlines() if line.split()[1:2] == ["blob"]]


def check_anchors(repository_root: Path, git_head: str | None, record: Mapping[str, Any]) -> None:
    """§10.3 (W9-T16): each ``git_commit`` anchor is an ancestor of ``git_head`` that introduces the anchored bytes."""

    if not git_head:
        raise IntegrityError("W9 acceptance anchors are checked at the binding's git_head")
    for anchor in record.get("anchors", []):
        if anchor.get("anchor_kind") != "git_commit":
            raise IntegrityError("W9 acceptance anchor must be a git_commit anchor (owner point G)")
        commit = str(anchor.get("value"))
        if not evidence.is_ancestor(repository_root, commit, git_head):
            raise IntegrityError("W9 acceptance anchor commit is not an ancestor of git_head")
        wanted = record.get(_ANCHORED_FIELDS[str(anchor.get("anchored"))])
        if not any(
            hashlib.sha256(_git(repository_root, "cat-file", "blob", blob, text=False)).hexdigest() == wanted
            for blob in _introduced_blobs(repository_root, commit)
        ):
            raise IntegrityError("W9 acceptance anchor commit does not introduce the anchored bytes")


def check_change_list(
    repository_root: Path, git_head: str | None, legacy: Mapping[str, Any], record: Mapping[str, Any]
) -> None:
    """§10.4 (O-32): the list at ``git_head``, and no affected item older than the change that affects it."""

    entries = evidence.require_change_list(repository_root, git_head, record.get("enforcement_change_list"))
    for registration, observation in batch_sources(legacy, record):
        key = {name: registration.get(name) for name in ("root_kind", "root_id", "normalized_path")}
        for entry in entries:
            if key not in entry["affected_registrations"]:
                continue
            source = observation["source_identity"]
            if source.get("identity_kind") != "git_tracked":
                raise IntegrityError("W9 acceptance item affected by a shared-surface change is not git_tracked")
            if not evidence.is_ancestor(repository_root, entry["merge_commit"], str(source.get("git_commit"))):
                raise IntegrityError("W9 acceptance item predates a shared-surface change that affects it")


def check_environment(
    environment: Any, legacy: Mapping[str, Any], record: Mapping[str, Any]
) -> list[Callable[[], None]]:
    """LR-016 and LR-020: every environment check, once now. Returns the window re-reads the runtime runs at commit."""

    from research_system.legacy.preparers import _need_reader

    reader = _need_reader(environment)
    evidence.require_detector_controls(
        evidence.read_evidence(reader.repository_root, reader.git_head, evidence.DETECTOR_CONTROLS)
    )
    check_anchors(reader.repository_root, reader.git_head, record)
    check_change_list(reader.repository_root, reader.git_head, legacy, record)
    reread_items(environment, legacy, record)
    return [lambda: reread_items(environment, legacy, record)]
