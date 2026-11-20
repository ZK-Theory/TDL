# Research context: docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md (revision 8, §8, owner point H)
# Purpose: the W9 legacy open-item list format (w9-legacy-open-items/1) and Git-head reader under tmp_path.
"""Unit tests for the W9 open-item list reader (WP9.4-1 §8, owner point H). Each refusal asserts its own message."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from research_system.legacy import evidence
from research_system.legacy.evidence import (
    LEGACY_OPEN_ITEMS,
    LEGACY_OPEN_ITEMS_FORMAT,
    EvidenceRefused,
    has_open_item,
    require_open_items,
)


def _git(root: Path, *args: str) -> str:
    """Run Git in ``root`` with a fixed test identity and return its stripped standard output."""
    return subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _commit_file(root: Path, relative: str, content: str, message: str) -> str:
    """Write ``content`` to ``relative`` under ``root``, commit it alone, and return the new commit."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))
    _git(root, "add", relative)
    _git(root, "commit", "-q", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _entry(
    item_kind: str = "a001_item",
    item_id: str = "A001-01",
    source: str = "audit/w0-d1.md#L10",
    feeds_papers: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "item_kind": item_kind,
        "item_id": item_id,
        "source": source,
        "feeds_papers": ["P01-A"] if feeds_papers is None else feeds_papers,
    }


def _open_items(*entries: dict[str, Any]) -> str:
    return json.dumps({"format": LEGACY_OPEN_ITEMS_FORMAT, "items": list(entries)})


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _commit_file(root, "README.md", "base\n", "base")
    return root


def test_open_items_constants_match_paths_addendum() -> None:
    assert LEGACY_OPEN_ITEMS == ".research-system/evidence/w9/legacy-open-items.json"
    assert LEGACY_OPEN_ITEMS_FORMAT == "w9-legacy-open-items/1"
    assert evidence.EVIDENCE_DIRECTORY == ".research-system/evidence/w9"


def test_valid_open_items_at_git_head_are_returned_with_blob(repository: Path) -> None:
    items_payload = [
        _entry("a001_item", "A001-01", "audit/w0.md", ["P01-A"]),
        _entry("audit_hole", "HOLE-1", "audit/w0-hole.md", ["P01-A", "P01-B"]),
        _entry("review_finding", "RF-1", "reviews/r1.md", []),
    ]
    listed = _commit_file(repository, LEGACY_OPEN_ITEMS, _open_items(*items_payload), "open items")
    expected_blob = _git(repository, "rev-parse", f"{listed}:{LEGACY_OPEN_ITEMS}")
    # Uncommitted edits in the working tree must never leak into require_open_items.
    (repository / LEGACY_OPEN_ITEMS).write_text(
        _open_items(_entry("a001_item", "UNCOMMITTED", "x", [])), encoding="utf-8"
    )
    later = _commit_file(repository, "other.md", "later\n", "later")

    entries, blob = require_open_items(repository, later, expected_blob=expected_blob)
    assert blob == expected_blob
    assert entries == items_payload
    assert has_open_item(entries, "a001_item", "A001-01") is True
    assert has_open_item(entries, "audit_hole", "HOLE-1") is True
    assert has_open_item(entries, "review_finding", "RF-1") is True
    assert has_open_item(entries, "audit_hole", "A001-01") is False
    assert has_open_item(entries, "a001_item", "UNCOMMITTED") is False


def test_empty_open_items_list_at_git_head_is_admitted(repository: Path) -> None:
    listed = _commit_file(repository, LEGACY_OPEN_ITEMS, _open_items(), "empty list")
    blob = _git(repository, "rev-parse", f"{listed}:{LEGACY_OPEN_ITEMS}")
    entries, returned_blob = require_open_items(repository, listed, expected_blob=blob)
    assert entries == []
    assert returned_blob == blob


def test_missing_git_head_or_absent_file_even_in_working_tree_is_refused(repository: Path) -> None:
    head = _git(repository, "rev-parse", "HEAD")
    with pytest.raises(EvidenceRefused, match="W9 evidence is read at the binding's git_head"):
        require_open_items(repository, None)
    uncommitted = repository / LEGACY_OPEN_ITEMS
    uncommitted.parent.mkdir(parents=True, exist_ok=True)
    uncommitted.write_text(_open_items(_entry()), encoding="utf-8")
    with pytest.raises(EvidenceRefused, match="W9 evidence file is absent at git_head"):
        require_open_items(repository, head)


def test_wrong_expected_blob_is_refused(repository: Path) -> None:
    first = _commit_file(repository, LEGACY_OPEN_ITEMS, _open_items(_entry()), "v1")
    old_blob = _git(repository, "rev-parse", f"{first}:{LEGACY_OPEN_ITEMS}")
    second = _commit_file(repository, LEGACY_OPEN_ITEMS, _open_items(_entry(item_id="A001-02")), "v2")
    with pytest.raises(EvidenceRefused, match="W9 open-item list blob differs from the list at git_head"):
        require_open_items(repository, second, expected_blob=old_blob)


def test_non_json_open_items_file_is_refused(repository: Path) -> None:
    head = _commit_file(repository, LEGACY_OPEN_ITEMS, "{not json", "bad json")
    with pytest.raises(EvidenceRefused, match="W9 evidence file is not JSON"):
        require_open_items(repository, head)


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"format": "other/1", "items": []}, "W9 open-item list does not have the fixed format"),
        ({"format": LEGACY_OPEN_ITEMS_FORMAT}, "W9 open-item list does not have the fixed format"),
        (
            {"format": LEGACY_OPEN_ITEMS_FORMAT, "items": [], "extra": 1},
            "W9 open-item list does not have the fixed format",
        ),
        (
            {"format": LEGACY_OPEN_ITEMS_FORMAT, "items": "not-a-list"},
            "W9 open-item list does not have the fixed format",
        ),
        (
            {"format": LEGACY_OPEN_ITEMS_FORMAT, "items": [{"item_kind": "a001_item"}]},
            "W9 open-item list entry does not have the fixed format",
        ),
        (
            {"format": LEGACY_OPEN_ITEMS_FORMAT, "items": [{**_entry(), "extra": 1}]},
            "W9 open-item list entry does not have the fixed format",
        ),
        (
            {"format": LEGACY_OPEN_ITEMS_FORMAT, "items": [_entry(item_kind="unknown_kind")]},
            "W9 open-item list entry does not have the fixed format",
        ),
        (
            {"format": LEGACY_OPEN_ITEMS_FORMAT, "items": [_entry(item_id="")]},
            "W9 open-item list entry does not have the fixed format",
        ),
        (
            {"format": LEGACY_OPEN_ITEMS_FORMAT, "items": [_entry(source="")]},
            "W9 open-item list entry does not have the fixed format",
        ),
        (
            {"format": LEGACY_OPEN_ITEMS_FORMAT, "items": [{**_entry(), "feeds_papers": "P01-A"}]},
            "W9 open-item list entry does not have the fixed format",
        ),
        (
            {"format": LEGACY_OPEN_ITEMS_FORMAT, "items": [_entry(feeds_papers=["P01-C"])]},
            "W9 open-item list entry does not have the fixed format",
        ),
        (
            {"format": LEGACY_OPEN_ITEMS_FORMAT, "items": [_entry(feeds_papers=["P01-A", "P01-A"])]},
            "W9 open-item list entry does not have the fixed format",
        ),
        (
            {
                "format": LEGACY_OPEN_ITEMS_FORMAT,
                "items": [_entry("a001_item", "A001-01"), _entry("a001_item", "A001-01")],
            },
            "W9 open-item list names an item twice",
        ),
    ],
    ids=[
        "wrong-format",
        "missing-items",
        "extra-top-key",
        "items-not-list",
        "missing-entry-keys",
        "extra-entry-key",
        "bad-item-kind",
        "empty-item-id",
        "empty-source",
        "feeds-not-list",
        "unknown-paper",
        "duplicate-paper",
        "duplicate-item",
    ],
)
def test_malformed_open_items_file_is_refused(repository: Path, body: dict[str, Any], message: str) -> None:
    head = _commit_file(repository, LEGACY_OPEN_ITEMS, json.dumps(body), "malformed")
    with pytest.raises(EvidenceRefused, match=message):
        require_open_items(repository, head)


def test_same_item_id_with_different_item_kind_is_admitted(repository: Path) -> None:
    head = _commit_file(
        repository,
        LEGACY_OPEN_ITEMS,
        _open_items(_entry("a001_item", "ID-1"), _entry("audit_hole", "ID-1")),
        "distinct kinds",
    )
    entries, _ = require_open_items(repository, head)
    assert len(entries) == 2
    assert has_open_item(entries, "a001_item", "ID-1") is True
    assert has_open_item(entries, "audit_hole", "ID-1") is True
    assert has_open_item(entries, "review_finding", "ID-1") is False
