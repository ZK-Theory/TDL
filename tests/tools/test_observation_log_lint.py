# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign H)
# Purpose: Controls for the observation-log lint: duplicate ids, closing stamps without evidence,
# borrowed identical stamps, and a computed completeness ledger for review packets.
"""Controls for ``tools/observation_log_lint.py``.

Obs 2026-09-08-reconciliation-stamped-a-borrowed-resolution: a reconciliation pass copied
resolution stamps onto unrelated observations. Obs 2026-09-01-completeness-ledger-missed-six-live-items:
a handoff's "every item is accounted for" was assembled by hand and was wrong by six.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "observation_log_lint.py"


def _obs(ident: str, status: str, extra: str = "") -> str:
    return f"### Observation {ident}: title\n\n**Status:** {status}\n**Date:** 2026-09-01\n{extra}\n**Issue:** x\n\n"


def _run(tmp_path: Path, log: str, *args: str) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "log.md"
    path.write_text("# Log\n\n" + log, encoding="utf-8", newline="\n")
    return subprocess.run([sys.executable, str(TOOL), str(path), *args], capture_output=True, text=True, check=False)


def test_a_clean_log_passes(tmp_path: Path) -> None:
    log = _obs("a", "ACTIONED — fixed in PR #300 (4a5349fd).") + _obs("b", "OPEN") + _obs("c", "DEFERRED — external.")
    result = _run(tmp_path, log)
    assert result.returncode == 0, result.stderr
    assert "3 observation(s): 1 OPEN" in result.stdout


def test_a_duplicate_id_fails(tmp_path: Path) -> None:
    result = _run(tmp_path, _obs("a", "OPEN") + _obs("a", "OPEN"))
    assert result.returncode == 1
    assert "duplicate id a" in result.stderr


def test_a_closing_stamp_without_an_artifact_fails(tmp_path: Path) -> None:
    """The borrowed stamps read like resolutions but named nothing a reader could check."""
    result = _run(tmp_path, _obs("a", "ACTIONED — Phase 0 reconciliation: records refreshed plan state."))
    assert result.returncode == 1
    assert "a: closing status names no checkable artifact" in result.stderr


def test_evidence_on_a_resolution_line_or_a_jira_key_counts(tmp_path: Path) -> None:
    log = _obs("a", "CLOSED", "**Resolution:** `scripts/check_citations.py` swept the corpus.\n") + _obs(
        "b", "ACTIONED — Jira readback recorded on KAN-65."
    )
    assert _run(tmp_path, log).returncode == 0


def test_identical_closing_stamps_on_two_ids_fail_unless_declared_a_batch(tmp_path: Path) -> None:
    stamp = "ACTIONED — Phase 0 reconciliation: fixed by PR #283 and the records were refreshed."
    borrowed = _run(tmp_path, _obs("a", stamp) + _obs("b", stamp))
    declared = _run(tmp_path, _obs("a", stamp + " Batch disposition.") + _obs("b", stamp + " Batch disposition."))

    assert borrowed.returncode == 1
    assert "identical closing status on a, b" in borrowed.stderr
    assert declared.returncode == 0, declared.stderr


def test_the_packet_ledger_is_computed_against_the_log(tmp_path: Path) -> None:
    """The ledger must list exactly the OPEN observations: missing and stale rows are both named."""
    log = _obs("a", "OPEN") + _obs("b", "OPEN") + _obs("c", "ACTIONED — PR #1.")
    packet = tmp_path / "packet.md"
    packet.write_text(
        "# Packet\n\nProse may mention `b` and `c` freely.\n\n## Completeness ledger\n\n"
        "| Group | Count | IDs |\n|---|---:|---|\n| A | 2 | a · c |\n\n## Skills pass\n\nmentions b\n",
        encoding="utf-8",
    )

    result = _run(tmp_path, log, "--packet", str(packet))

    assert result.returncode == 1
    assert "OPEN but missing from the ledger: b" in result.stderr
    assert "in the ledger but not OPEN: c" in result.stderr


def test_a_complete_ledger_passes(tmp_path: Path) -> None:
    packet = tmp_path / "packet.md"
    packet.write_text("## Completeness ledger\n\n| A | 2 | a · b |\n", encoding="utf-8")
    result = _run(tmp_path, _obs("a", "OPEN") + _obs("b", "OPEN — ESCALATED"), "--packet", str(packet))
    assert result.returncode == 0, result.stderr
    assert "ledger matches the 2 OPEN observation(s)" in result.stdout
