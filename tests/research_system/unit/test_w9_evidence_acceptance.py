# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-2 §10.4, §11.1, §12.2)
# Purpose: the two evidence formats WP9.3-2 fixes: the shared-surface change list (O-32) and the Computational-Log
# export (D-7). Synthetic Git repositories and logs under tmp_path only; the export is built by the reference tool.
"""W9 evidence formats for the acceptance (WP9.3 note §10.4, §12.2). Each refusal asserts its own message."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from research_system.legacy import evidence
from research_system.legacy.evidence import EvidenceRefused, is_ancestor, require_change_list, require_cl_export

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRATION = {"root_kind": "repository_root", "root_id": "repository", "normalized_path": "results/x.json"}
SYNTHETIC_LOG = (
    b"---\ntitle: synthetic log\n---\n\n"
    b"## 2026-01-02 First entry\nA line.\n\n"
    b"## 2026-01-03 Second entry\nAnother line.\n\n"
    b"### 2026-01-04 Third entry\nLast line.\n"
)


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def commit_file(root: Path, relative: str, content: str, message: str) -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))
    git(root, "add", relative)
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


def change_list(*entries: dict[str, Any]) -> str:
    return json.dumps({"format": evidence.SHARED_SURFACE_CHANGES_FORMAT, "entries": list(entries)})


def entry(merge_commit: str, *registrations: dict[str, Any]) -> dict[str, Any]:
    return {"merge_commit": merge_commit, "surface": "a shared surface", "affected_registrations": list(registrations)}


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-q")
    commit_file(root, "README.md", "base\n", "base")
    return root


def _declared(root: Path, commit: str) -> dict[str, str]:
    return {"git_commit": commit, "git_blob": git(root, "rev-parse", f"{commit}:{evidence.SHARED_SURFACE_CHANGES}")}


# --- The shared-surface change list (O-32) ------------------------------------------------------------------------------


def test_the_change_list_at_git_head_is_returned(repository: Path) -> None:
    merged = git(repository, "rev-parse", "HEAD")
    listed = commit_file(repository, evidence.SHARED_SURFACE_CHANGES, change_list(entry(merged, REGISTRATION)), "list")
    head = commit_file(repository, "other.md", "later\n", "later")
    entries = require_change_list(repository, head, _declared(repository, listed))
    assert entries == [entry(merged, REGISTRATION)]


def test_an_absent_or_null_change_list_is_refused(repository: Path) -> None:
    head = git(repository, "rev-parse", "HEAD")
    with pytest.raises(EvidenceRefused, match="W9 acceptance names no shared-surface change list"):
        require_change_list(repository, head, None)
    with pytest.raises(EvidenceRefused, match="W9 evidence file is absent at git_head"):
        require_change_list(repository, head, {"git_commit": head, "git_blob": "0" * 40})


def test_a_declared_blob_other_than_the_list_at_git_head_is_refused(repository: Path) -> None:
    first = commit_file(repository, evidence.SHARED_SURFACE_CHANGES, change_list(), "list v1")
    old = _declared(repository, first)
    commit_file(repository, evidence.SHARED_SURFACE_CHANGES, change_list(entry(first)), "list v2")
    head = git(repository, "rev-parse", "HEAD")
    with pytest.raises(EvidenceRefused, match="W9 shared-surface change list is not the list at git_head"):
        require_change_list(repository, head, old)


def test_a_declared_commit_that_is_not_an_ancestor_of_git_head_is_refused(repository: Path) -> None:
    listed = commit_file(repository, evidence.SHARED_SURFACE_CHANGES, change_list(), "list")
    git(repository, "checkout", "-q", "-b", "side")
    side = commit_file(repository, "side.md", "side\n", "side")
    git(repository, "checkout", "-q", "-")
    head = commit_file(repository, "main.md", "main\n", "main")
    declared = {**_declared(repository, listed), "git_commit": side}
    with pytest.raises(EvidenceRefused, match="W9 shared-surface change list commit is not an ancestor of git_head"):
        require_change_list(repository, head, declared)


def test_a_declared_commit_that_does_not_hold_the_declared_list_is_refused(repository: Path) -> None:
    before = git(repository, "rev-parse", "HEAD")
    listed = commit_file(repository, evidence.SHARED_SURFACE_CHANGES, change_list(), "list")
    declared = {**_declared(repository, listed), "git_commit": before}
    with pytest.raises(EvidenceRefused, match="W9 shared-surface change list commit does not hold the declared list"):
        require_change_list(repository, listed, declared)


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"format": "other/1", "entries": []}, "W9 shared-surface change list does not have the fixed format"),
        ({"format": evidence.SHARED_SURFACE_CHANGES_FORMAT}, "W9 shared-surface change list does not have the fixed"),
        (
            {"format": evidence.SHARED_SURFACE_CHANGES_FORMAT, "entries": [{"merge_commit": "x"}]},
            "W9 shared-surface change list entry does not have the fixed format",
        ),
        (
            {"format": evidence.SHARED_SURFACE_CHANGES_FORMAT, "entries": [entry("X" * 40)]},
            "W9 shared-surface change list entry does not have the fixed format",
        ),
        (
            {"format": evidence.SHARED_SURFACE_CHANGES_FORMAT, "entries": [entry("a" * 40, {"root_kind": "x"})]},
            "W9 shared-surface change list affected registration does not have the fixed format",
        ),
        (
            {"format": evidence.SHARED_SURFACE_CHANGES_FORMAT, "entries": [{**entry("a" * 40), "surface": ""}]},
            "W9 shared-surface change list entry does not have the fixed format",
        ),
    ],
    ids=["format", "no-entries", "entry-keys", "commit", "registration", "empty-surface"],
)
def test_a_malformed_change_list_is_refused(repository: Path, body: dict[str, Any], message: str) -> None:
    listed = commit_file(repository, evidence.SHARED_SURFACE_CHANGES, json.dumps(body), "list")
    with pytest.raises(EvidenceRefused, match=message):
        require_change_list(repository, listed, _declared(repository, listed))


def test_is_ancestor_answers_and_refuses_an_unknown_commit(repository: Path) -> None:
    base = git(repository, "rev-parse", "HEAD")
    later = commit_file(repository, "later.md", "later\n", "later")
    assert is_ancestor(repository, base, later) is True
    assert is_ancestor(repository, later, base) is False
    assert is_ancestor(repository, base, base) is True
    with pytest.raises(EvidenceRefused, match="W9 evidence cannot order commits"):
        is_ancestor(repository, "f" * 40, later)


# --- The Computational-Log export (D-7) -------------------------------------------------------------------------------


def reference_segment(raw: bytes, region: tuple[int, int]) -> dict[str, Any]:
    """The export's segmentation, produced by the accepted reference tool (note §12.2), never the runtime segmenter."""
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    try:
        import w9_segmentation
    finally:
        sys.path.remove(str(REPO_ROOT / "tools"))
    return w9_segmentation.segment(raw, "computational_log_entry", region=region)


def reference_export(raw: bytes = SYNTHETIC_LOG, region: tuple[int, int] | None = None) -> dict[str, Any]:
    """A ``w9-cl-export/1`` export of ``raw``, as L-0b would assemble it around the reference tool's output."""
    region = region or (5, raw.count(b"\n"))
    segmentation = reference_segment(raw, region)
    return {
        "format": evidence.CL_EXPORT_FORMAT,
        "selector": {
            "selector_kind": "computational_log_entry",
            "region": {"first_line": region[0], "last_line": region[1]},
        },
        "segmentation": segmentation,
        "read": {
            "started_at": "2026-11-11T00:00:00Z",
            "ended_at": "2026-11-11T00:00:01Z",
            "path_form": {"form": "real_vault_path"},
            "limits": ["no live vault page read after the export"],
        },
        "retained_copy": {
            "repository_path": ".research-system/evidence/w9/cl-retained-copy.md",
            "git_blob": hashlib.sha1(b"blob %d\0" % len(raw) + raw, usedforsecurity=False).hexdigest(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_length": len(raw),
        },
        "classifications": [{"ordinal": row["row_ordinal"], "class": None} for row in segmentation["rows"]],
        "producer": dict(evidence.CL_EXPORT_PRODUCER),
    }


def test_the_admitted_producer_is_the_accepted_reference_blob() -> None:
    """P-068: blob ``43e1454d``. Independent literal: the prefix P-068 and P-082 item 2 record, checked against Git."""
    blob = git(REPO_ROOT, "rev-parse", "HEAD:tools/w9_segmentation.py")
    assert evidence.CL_EXPORT_PRODUCER["git_blob"] == blob
    assert blob.startswith("43e1454d")
    assert evidence.CL_EXPORT_PRODUCER["repository_path"] == "tools/w9_segmentation.py"


def test_a_reference_export_has_the_fixed_format() -> None:
    export = reference_export()
    assert export["segmentation"]["rows"], "the synthetic log must give rows"
    assert require_cl_export(export) == export


def _drop(key: str):
    return lambda value: value.pop(key)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.update(format="other/1"), "W9 Computational-Log export does not have the fixed format"),
        (_drop("producer"), "W9 Computational-Log export does not have the fixed format"),
        (
            lambda value: value["selector"].update(selector_kind="heading_section"),
            "W9 Computational-Log export selector does not have the fixed format",
        ),
        (
            lambda value: value["selector"]["region"].update(first_line=0),
            "W9 Computational-Log export selector does not have the fixed format",
        ),
        (
            lambda value: value["segmentation"].update(segmentation_contract="w9-segmentation/2.0.0"),
            "W9 Computational-Log export segmentation does not have the fixed format",
        ),
        (
            lambda value: value["segmentation"].update(selector_kind="tracker_task_row"),
            "W9 Computational-Log export segmentation does not have the fixed format",
        ),
        (
            lambda value: value["read"].update(started_at="yesterday"),
            "W9 Computational-Log export read does not have the fixed format",
        ),
        (
            lambda value: value["read"].update(ended_at="2026-11-10T00:00:00Z"),
            "W9 Computational-Log export read ends before it starts",
        ),
        (
            lambda value: value["retained_copy"].update(sha256="0" * 64),
            "W9 Computational-Log export segmentation does not match its retained copy",
        ),
        (
            lambda value: value["retained_copy"].update(byte_length=1),
            "W9 Computational-Log export segmentation does not match its retained copy",
        ),
        (
            lambda value: value["classifications"].pop(),
            "W9 Computational-Log export classifications do not match its rows",
        ),
        (
            lambda value: value["classifications"][0].update(ordinal=99),
            "W9 Computational-Log export classifications do not match its rows",
        ),
        (
            lambda value: value["classifications"][0].update(**{"class": 3}),
            "W9 Computational-Log export classifications do not match its rows",
        ),
        (
            lambda value: value["producer"].update(extra=1),
            "W9 Computational-Log export producer does not have the fixed format",
        ),
    ],
    ids=[
        "format",
        "missing-key",
        "selector-kind",
        "region",
        "contract",
        "segmentation-kind",
        "read-time",
        "read-order",
        "copy-hash",
        "copy-length",
        "classification-count",
        "classification-ordinal",
        "classification-class",
        "producer-keys",
    ],
)
def test_a_malformed_export_is_refused(mutate, message: str) -> None:
    export = copy.deepcopy(reference_export())
    mutate(export)
    with pytest.raises(EvidenceRefused, match=message):
        require_cl_export(export)
