# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-1 §11.1; owner point D)
# Purpose: the W9 evidence area's reader-side formats: the registration manifest and the detector control outputs.
"""W9 evidence formats (WP9.3 note §11.1). Each refusal asserts its own message."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from research_system.legacy import evidence
from research_system.legacy.evidence import (
    EvidenceRefused,
    read_evidence,
    require_detector_controls,
    require_registered,
)

CONTROLS = {
    "format": evidence.DETECTOR_CONTROLS_FORMAT,
    "detectors": [
        {"detector": name, "control": kind, "output_sha256": "d" * 64, "recorded_at": "2026-08-31T00:00:00Z"}
        for name, kind in evidence.REQUIRED_DETECTOR_CONTROLS.items()
    ],
}
REGISTRATION = {"root_kind": "repository_root", "root_id": "repository", "normalized_path": "results/x.json"}
MANIFEST = {"format": evidence.REGISTRATION_MANIFEST_FORMAT, "registrations": [REGISTRATION]}


def test_complete_controls_and_a_listed_registration_pass() -> None:
    require_detector_controls(CONTROLS)
    require_registered(MANIFEST, {**REGISTRATION, "role": "legacy_research_result"})


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value["detectors"].pop(1), "W9 detector post_merge_first_parent has no recorded control"),
        (
            lambda value: value["detectors"][2].update(control="recorded_read"),
            "W9 detector vault_computational_log has no recorded control of kind watched_to_fail",
        ),
        (lambda value: value["detectors"].append(dict(value["detectors"][0])), "names a detector twice"),
        (lambda value: value["detectors"][0].update(output_sha256="x"), "entry does not have the fixed format"),
        (lambda value: value.update(format="other/1"), "W9 detector control file does not have the fixed format"),
    ],
    ids=["missing", "wrong-kind", "twice", "bad-hash", "format"],
)
def test_detector_controls_refusals(mutate, message: str) -> None:
    value = json.loads(json.dumps(CONTROLS))
    mutate(value)
    with pytest.raises(EvidenceRefused, match=message):
        require_detector_controls(value)


def test_an_unlisted_registration_is_refused() -> None:
    with pytest.raises(EvidenceRefused, match="W9 registration is not in the registration manifest at git_head"):
        require_registered(MANIFEST, {**REGISTRATION, "normalized_path": "results/y.json"})
    with pytest.raises(EvidenceRefused, match="registration manifest entry does not have the fixed format"):
        require_registered({**MANIFEST, "registrations": [{**REGISTRATION, "extra": 1}]}, REGISTRATION)


def test_evidence_is_read_from_git_at_git_head_and_an_absent_file_refuses(tmp_path: Path) -> None:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t", *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    path = tmp_path / evidence.DETECTOR_CONTROLS
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(CONTROLS), encoding="utf-8")
    git("init", "-q")
    git("add", ".")
    git("commit", "-q", "-m", "evidence")
    head = git("rev-parse", "HEAD")
    path.write_text("{}", encoding="utf-8")  # the working tree is never read
    assert read_evidence(tmp_path, head, evidence.DETECTOR_CONTROLS) == CONTROLS
    with pytest.raises(EvidenceRefused, match="W9 evidence file is absent at git_head"):
        read_evidence(tmp_path, head, evidence.REGISTRATION_MANIFEST)
    with pytest.raises(EvidenceRefused, match="W9 evidence is read at the binding's git_head"):
        read_evidence(tmp_path, None, evidence.DETECTOR_CONTROLS)
