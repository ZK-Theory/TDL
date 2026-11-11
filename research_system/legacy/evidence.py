"""The W9 evidence area's reader-side formats (WP9.3 note §11.1; owner point D; P-081 item 4).

The W9 evidence area is ``.research-system/evidence/w9/``. WP9.3 fixes the formats of the files it reads there as
closed JSON, validated here; WP9.5 writes them. They are not ``ars://legacy/`` schemas, because the W9 schema directory
is pinned to its 19 owned files. Every file is read from Git at the binding's ``git_head``
(``git show <git_head>:<path>``), never from the working tree, and a row whose file is absent refuses.

WP9.3-1 reads two of them:

- the **registration manifest** (06v M-6), at LR-015: the observation's registration must be listed;
- the **detector control outputs** (D-5, O-13), at LR-003: every W9 §4.4 detector's negative control is recorded as
  watched to fail (the ruleset's control is a recorded read of its configuration, as W9 §4.4 says).

WP9.3-2 fixes two more:

- the **shared-surface change list** (06v O-32; note §10.4), at LR-016 and LR-020. Its file name is fixed here and in
  the W9 paths addendum's row for it;
- the **Computational-Log export** (D-7; note §12.2), which the reference implementation produces at L-0b and the
  runtime segmenter rechecks. Its file name is pinned per entry by ``ACCEPTED_CL_EXPORT``, not here.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any

from research_system.errors import IntegrityError
from research_system.legacy.reader import ReadRefused, _git

EVIDENCE_DIRECTORY = ".research-system/evidence/w9"
REGISTRATION_MANIFEST = f"{EVIDENCE_DIRECTORY}/registration-manifest.json"
DETECTOR_CONTROLS = f"{EVIDENCE_DIRECTORY}/detector-controls.json"
SHARED_SURFACE_CHANGES = f"{EVIDENCE_DIRECTORY}/shared-surface-changes.json"
REGISTRATION_MANIFEST_FORMAT = "w9-registration-manifest/1"
DETECTOR_CONTROLS_FORMAT = "w9-detector-controls/1"
SHARED_SURFACE_CHANGES_FORMAT = "w9-shared-surface-changes/1"
CL_EXPORT_FORMAT = "w9-cl-export/1"
# Note §12.2 and P-068: the export's only admitted producer is the reference implementation at its accepted blob. The
# runtime segmenter rechecks the export and must never have produced it.
CL_EXPORT_PRODUCER = MappingProxyType(
    {"repository_path": "tools/w9_segmentation.py", "git_blob": "43e1454de09b61e274954c42b21d6ae533857a24"}
)
RUNTIME_SEGMENTER_PATH = "research_system/legacy/segmentation.py"
_SEGMENTATION_CONTRACT = "w9-segmentation/1.0.0"
_SHA1 = re.compile(r"[0-9a-f]{40}\Z")
# W9 §4.4: each detector, and the kind of control it must record before the first registration.
REQUIRED_DETECTOR_CONTROLS = {
    "main_ruleset": "recorded_read",
    "post_merge_first_parent": "watched_to_fail",
    "vault_computational_log": "watched_to_fail",
    "conventions_repository_check": "watched_to_fail",
}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?Z\Z")


class EvidenceRefused(IntegrityError):
    """A W9 evidence file is absent at the binding's ``git_head``, malformed, or does not show what a row needs."""


def read_evidence(repository_root: Path, git_head: str | None, path: str) -> Any:
    """Read one evidence file from Git at the binding's ``git_head``.

    Raises:
        EvidenceRefused: If there is no ``git_head``, the file is absent there, or it is not JSON.
    """

    if not git_head:
        raise EvidenceRefused("W9 evidence is read at the binding's git_head")
    try:
        raw = _git(repository_root, "show", f"{git_head}:{path}", text=False)
    except ReadRefused as exc:
        raise EvidenceRefused(f"W9 evidence file is absent at git_head: {path}") from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceRefused(f"W9 evidence file is not JSON: {path}") from exc


def _closed(value: Any, keys: set[str], what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise EvidenceRefused(f"W9 {what} does not have the fixed format")
    return value


def require_registered(manifest: Any, registration: Mapping[str, Any]) -> None:
    """LR-015 (06v WP9.5, M-6): the registration is listed in the committed registration manifest.

    Format: ``{"format": "w9-registration-manifest/1", "registrations": [{"root_kind", "root_id",
    "normalized_path"}, ...]}``.
    """

    body = _closed(manifest, {"format", "registrations"}, "registration manifest")
    if body["format"] != REGISTRATION_MANIFEST_FORMAT or not isinstance(body["registrations"], list):
        raise EvidenceRefused("W9 registration manifest does not have the fixed format")
    entries = [
        _closed(entry, {"root_kind", "root_id", "normalized_path"}, "registration manifest entry")
        for entry in body["registrations"]
    ]
    wanted = {key: registration.get(key) for key in ("root_kind", "root_id", "normalized_path")}
    if wanted not in [dict(entry) for entry in entries]:
        raise EvidenceRefused("W9 registration is not in the registration manifest at git_head")


def require_detector_controls(controls: Any) -> None:
    """LR-003 (W9 §4.4; O-13; D-5): every detector's negative control watched to fail, before the first registration.

    Format: ``{"format": "w9-detector-controls/1", "detectors": [{"detector", "control", "output_sha256",
    "recorded_at"}, ...]}``.
    """

    body = _closed(controls, {"format", "detectors"}, "detector control file")
    if body["format"] != DETECTOR_CONTROLS_FORMAT or not isinstance(body["detectors"], list):
        raise EvidenceRefused("W9 detector control file does not have the fixed format")
    recorded: dict[str, str] = {}
    for entry in body["detectors"]:
        row = _closed(entry, {"detector", "control", "output_sha256", "recorded_at"}, "detector control entry")
        if not _SHA256.match(str(row["output_sha256"])) or not _UTC.match(str(row["recorded_at"])):
            raise EvidenceRefused("W9 detector control entry does not have the fixed format")
        if row["detector"] in recorded:
            raise EvidenceRefused("W9 detector control file names a detector twice")
        recorded[str(row["detector"])] = str(row["control"])
    for detector, control in REQUIRED_DETECTOR_CONTROLS.items():
        if recorded.get(detector) != control:
            raise EvidenceRefused(f"W9 detector {detector} has no recorded control of kind {control}")


# --- WP9.3-2 --------------------------------------------------------------------------------------------------------


def is_ancestor(repository_root: Path, ancestor: str, descendant: str) -> bool:
    """Whether ``ancestor`` is ``descendant`` or one of its ancestors (``git merge-base --is-ancestor``).

    Raises:
        EvidenceRefused: If Git cannot order the two, for example because a commit is unknown.
    """

    try:
        result = subprocess.run(
            ["git", "-C", str(repository_root), "merge-base", "--is-ancestor", ancestor, descendant],
            capture_output=True,
            timeout=60,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise EvidenceRefused("W9 evidence cannot order commits") from exc
    if result.returncode not in (0, 1):
        raise EvidenceRefused("W9 evidence cannot order commits")
    return result.returncode == 0


def blob_at(repository_root: Path, commit: str, path: str) -> str | None:
    """The Git blob ID of ``path`` at ``commit``, or ``None`` when the commit does not hold it."""

    try:
        return str(_git(repository_root, "rev-parse", "--verify", "--quiet", f"{commit}:{path}")).strip() or None
    except ReadRefused:
        return None


def require_change_list(repository_root: Path, git_head: str | None, declared: Any) -> list[dict[str, Any]]:
    """LR-016 and LR-020 (06v O-32; note §10.4): the acceptance's change list is the committed list at ``git_head``.

    ``declared`` is the acceptance's ``enforcement_change_list``. Read as: its ``git_blob`` is the list's blob at
    ``git_head``, and its ``git_commit`` is an ancestor of ``git_head`` (or ``git_head`` itself) holding that blob. A
    ``null`` is refused, because "no list" cannot be told apart from "no changes recorded".

    Format: ``{"format": "w9-shared-surface-changes/1", "entries": [{"merge_commit", "surface",
    "affected_registrations": [{"root_kind", "root_id", "normalized_path"}, ...]}, ...]}``.

    Returns:
        The list's entries.

    Raises:
        EvidenceRefused: For a ``null`` or malformed declaration, an absent or malformed list, or a declared commit or
            blob that is not the list at ``git_head``.
    """

    if declared is None:
        raise EvidenceRefused("W9 acceptance names no shared-surface change list")
    ref = _closed(declared, {"git_commit", "git_blob"}, "acceptance change-list ref")
    entries = _change_entries(read_evidence(repository_root, git_head, SHARED_SURFACE_CHANGES))
    if blob_at(repository_root, str(git_head), SHARED_SURFACE_CHANGES) != ref["git_blob"]:
        raise EvidenceRefused("W9 shared-surface change list is not the list at git_head")
    if not is_ancestor(repository_root, str(ref["git_commit"]), str(git_head)):
        raise EvidenceRefused("W9 shared-surface change list commit is not an ancestor of git_head")
    if blob_at(repository_root, str(ref["git_commit"]), SHARED_SURFACE_CHANGES) != ref["git_blob"]:
        raise EvidenceRefused("W9 shared-surface change list commit does not hold the declared list")
    return entries


def _change_entries(raw: Any) -> list[dict[str, Any]]:
    if (
        not isinstance(raw, Mapping)
        or set(raw) != {"format", "entries"}
        or raw["format"] != SHARED_SURFACE_CHANGES_FORMAT
        or not isinstance(raw["entries"], list)
    ):
        raise EvidenceRefused("W9 shared-surface change list does not have the fixed format")
    entries = []
    for item in raw["entries"]:
        row = _closed(item, {"merge_commit", "surface", "affected_registrations"}, "shared-surface change list entry")
        if (
            not _SHA1.match(str(row["merge_commit"]))
            or not isinstance(row["surface"], str)
            or not row["surface"]
            or not isinstance(row["affected_registrations"], list)
        ):
            raise EvidenceRefused("W9 shared-surface change list entry does not have the fixed format")
        for registration in row["affected_registrations"]:
            key = _closed(
                registration,
                {"root_kind", "root_id", "normalized_path"},
                "shared-surface change list affected registration",
            )
            # A null or empty member would match no registration, so the affected item's freshness check would never
            # run. Each member is a non-empty string.
            if not all(isinstance(value, str) and value for value in key.values()):
                raise EvidenceRefused(
                    "W9 shared-surface change list affected registration does not have the fixed format"
                )
        entries.append(json.loads(json.dumps(row)))
    return entries


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not _UTC.match(value):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:  # the right shape but no calendar date, such as 2026-02-30
        return None


def _in_evidence_area(path: Any) -> bool:
    """Addendum row 28: the retained copy is a file in the W9 evidence area, named in normal POSIX form."""
    if not isinstance(path, str):
        return False
    parts = PurePosixPath(path).parts
    return (
        str(PurePosixPath(path)) == path
        and parts[:3] == tuple(EVIDENCE_DIRECTORY.split("/"))
        and len(parts) > 3
        and not any(part in {".", ".."} for part in parts)
    )


def require_cl_export(export: Any) -> Mapping[str, Any]:
    """The Computational-Log export's fixed format, ``w9-cl-export/1`` (D-7; note §12.2).

    ``segmentation`` is the reference implementation's ``segment()`` output, verbatim. The other members are what L-0b
    records around it: the selector and region it segmented, the read, the retained copy's identity, one classification
    slot per row (P-068 item 4), and the producer. This checks shape and internal agreement only. Whether the producer
    is the reference implementation, and whether the runtime segmenter reproduces the rows, is the recheck's question.

    Raises:
        EvidenceRefused: For any departure from the format, naming the member.
    """

    body = _closed(
        export,
        {"format", "selector", "segmentation", "read", "retained_copy", "classifications", "producer"},
        "Computational-Log export",
    )
    if body["format"] != CL_EXPORT_FORMAT:
        raise EvidenceRefused("W9 Computational-Log export does not have the fixed format")
    selector = _closed(body["selector"], {"selector_kind", "region"}, "Computational-Log export selector")
    region = _closed(selector["region"], {"first_line", "last_line"}, "Computational-Log export selector")
    first, last = region["first_line"], region["last_line"]
    if (
        selector["selector_kind"] != "computational_log_entry"
        or not all(isinstance(value, int) and not isinstance(value, bool) for value in (first, last))
        or not 1 <= first <= last
    ):
        raise EvidenceRefused("W9 Computational-Log export selector does not have the fixed format")
    segmentation = _closed(
        body["segmentation"],
        {
            "segmentation_contract",
            "selector_kind",
            "file_sha256",
            "file_bytes",
            "file_facts",
            "rows",
            "suppressed_anchors",
        },
        "Computational-Log export segmentation",
    )
    if (
        segmentation["segmentation_contract"] != _SEGMENTATION_CONTRACT
        or segmentation["selector_kind"] != "computational_log_entry"
        or not isinstance(segmentation["rows"], list)
        or not isinstance(segmentation["suppressed_anchors"], list)
        or not isinstance(segmentation["file_facts"], Mapping)
    ):
        raise EvidenceRefused("W9 Computational-Log export segmentation does not have the fixed format")
    read = _closed(body["read"], {"started_at", "ended_at", "path_form", "limits"}, "Computational-Log export read")
    started, ended = _utc(read["started_at"]), _utc(read["ended_at"])
    if (
        started is None
        or ended is None
        or not isinstance(read["path_form"], Mapping)
        or not isinstance(read["limits"], list)
        or not all(isinstance(limit, str) for limit in read["limits"])
    ):
        raise EvidenceRefused("W9 Computational-Log export read does not have the fixed format")
    if ended < started:
        raise EvidenceRefused("W9 Computational-Log export read ends before it starts")
    copy = _closed(
        body["retained_copy"], {"repository_path", "git_blob", "sha256", "byte_length"}, "Computational-Log export copy"
    )
    if not _SHA1.match(str(copy["git_blob"])) or not _SHA256.match(str(copy["sha256"])):
        raise EvidenceRefused("W9 Computational-Log export copy does not have the fixed format")
    if not _in_evidence_area(copy["repository_path"]):
        raise EvidenceRefused(f"W9 Computational-Log export copy is not in the evidence area {EVIDENCE_DIRECTORY}/")
    if copy["sha256"] != segmentation["file_sha256"] or copy["byte_length"] != segmentation["file_bytes"]:
        raise EvidenceRefused("W9 Computational-Log export segmentation does not match its retained copy")
    ordinals = [row.get("row_ordinal") if isinstance(row, Mapping) else None for row in segmentation["rows"]]
    slots = body["classifications"]
    if (
        not isinstance(slots, list)
        or len(slots) != len(ordinals)
        or any(
            not isinstance(slot, Mapping)
            or set(slot) != {"ordinal", "class"}
            or slot["ordinal"] != ordinal
            or not (slot["class"] is None or isinstance(slot["class"], str))
            for slot, ordinal in zip(slots, ordinals, strict=False)
        )
    ):
        raise EvidenceRefused("W9 Computational-Log export classifications do not match its rows")
    _closed(body["producer"], {"repository_path", "git_blob"}, "Computational-Log export producer")
    return body
