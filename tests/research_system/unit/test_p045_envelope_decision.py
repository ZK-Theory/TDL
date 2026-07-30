from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DECISIONS_PATH = "docs/plans/agentic-research-system/03-decisions-and-open-questions.md"
EVENT_PATH = ".research-system/schemas/core/event.schema.json"
EVENT_BLOB = "bc3efc0fd41e3d9f24c383f2d0d196e26ba0d1e5"
EVENT_RAW_SHA256 = "3aaaa6d609dce1271db3e22d8620935929fc272add1fe5c06badb77050f6d021"
PRIOR_UNACTIVATED_BLOB = "188deb32ce833cec9a59ab74026762eb93f5a607"


def _git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    ).stdout


def _source_bytes(path: str, revision: str) -> bytes:
    if revision == "WORKTREE":
        return (REPO_ROOT / path).read_bytes()
    return _git("show", f"{revision}:{path}")


def _blob_id(path: str, revision: str) -> str:
    if revision == "WORKTREE":
        return _git("hash-object", "--no-filters", "--", path).decode().strip()
    return _git("rev-parse", f"{revision}:{path}").decode().strip()


def test_p045_binds_generic_event_envelope_exact_bytes_and_clean_start_ruling() -> None:
    revision = os.environ.get("P045_BINDING_REVISION", "HEAD")
    decisions = _source_bytes(DECISIONS_PATH, revision).decode("utf-8")
    event_bytes = _source_bytes(EVENT_PATH, revision)
    start = decisions.index("### P-045 - Generic event envelope clean-start activation")
    end = decisions.index("\n## ", start)
    decision = decisions[start:end]
    schema = json.loads(event_bytes)

    assert schema["$id"] == "ars://core/event"
    assert schema["properties"]["schema_version"] == {"const": "1.0.0"}
    assert _blob_id(EVENT_PATH, revision) == EVENT_BLOB
    assert hashlib.sha256(event_bytes).hexdigest() == EVENT_RAW_SHA256
    for literal in (
        EVENT_PATH,
        "ars://core/event",
        "`1.0.0`",
        EVENT_BLOB,
        EVENT_RAW_SHA256,
        PRIOR_UNACTIVATED_BLOB,
        "global position `0`",
        "No configured external history was",
        "If an undisclosed external store",
        "stop replay and migration",
        "new owner decision selecting explicit",
        "versioned readers or a separately reviewed migration",
        "Never silently widen the",
        "non-certifying",
    ):
        assert literal in decision
