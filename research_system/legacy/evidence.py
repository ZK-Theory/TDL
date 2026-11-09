"""The W9 evidence area's reader-side formats (WP9.3 note §11.1; owner point D; P-081 item 4).

The W9 evidence area is ``.research-system/evidence/w9/``. WP9.3 fixes the formats of the files it reads there as
closed JSON, validated here; WP9.5 writes them. They are not ``ars://legacy/`` schemas, because the W9 schema directory
is pinned to its 19 owned files. Every file is read from Git at the binding's ``git_head``
(``git show <git_head>:<path>``), never from the working tree, and a row whose file is absent refuses.

WP9.3-1 reads two of them:

- the **registration manifest** (06v M-6), at LR-015: the observation's registration must be listed;
- the **detector control outputs** (D-5, O-13), at LR-003: every W9 §4.4 detector's negative control is recorded as
  watched to fail (the ruleset's control is a recorded read of its configuration, as W9 §4.4 says).

The shared-surface change list and the Computational-Log export are WP9.3-2's.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from research_system.errors import IntegrityError
from research_system.legacy.reader import ReadRefused, _git

EVIDENCE_DIRECTORY = ".research-system/evidence/w9"
REGISTRATION_MANIFEST = f"{EVIDENCE_DIRECTORY}/registration-manifest.json"
DETECTOR_CONTROLS = f"{EVIDENCE_DIRECTORY}/detector-controls.json"
REGISTRATION_MANIFEST_FORMAT = "w9-registration-manifest/1"
DETECTOR_CONTROLS_FORMAT = "w9-detector-controls/1"
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
