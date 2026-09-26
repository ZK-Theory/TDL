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
    assert "identical closing text on a, b" in borrowed.stderr
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


LEDGER_HEAD = "## Completeness ledger\n\n| Group | Count | IDs |\n|---|---:|---|\n"


def _packet(tmp_path: Path, rows: str) -> str:
    packet = tmp_path / "packet.md"
    packet.write_text(LEDGER_HEAD + rows, encoding="utf-8")
    return str(packet)


def test_a_complete_ledger_passes(tmp_path: Path) -> None:
    packet = _packet(tmp_path, "| A | 2 | a · b |\n| **Total** | **2** | |\n")
    result = _run(tmp_path, _obs("a", "OPEN") + _obs("b", "OPEN — ESCALATED"), "--packet", packet)
    assert result.returncode == 0, result.stderr
    assert "ledger matches the 2 OPEN observation(s)" in result.stdout


def test_an_unknown_id_in_the_ledger_fails(tmp_path: Path) -> None:
    """A typo or invented id was filtered out before comparison, so the ledger 'matched'."""
    result = _run(tmp_path, _obs("a", "OPEN"), "--packet", _packet(tmp_path, "| A | 2 | a · typo-id |\n"))
    assert result.returncode == 1
    assert "not an observation id in the log: typo-id" in result.stderr


def test_a_wrong_row_count_or_total_fails(tmp_path: Path) -> None:
    log = _obs("a", "OPEN") + _obs("b", "OPEN")
    row = _run(tmp_path, log, "--packet", _packet(tmp_path, "| A | 99 | a · b |\n"))
    total = _run(tmp_path, log, "--packet", _packet(tmp_path, "| A | 2 | a · b |\n| **Total** | **3** | |\n"))
    assert row.returncode == 1 and "declares '99' but lists 2" in row.stderr
    assert total.returncode == 1 and "total 3 does not equal the 2 ids" in total.stderr


def test_a_count_cell_is_not_read_as_a_numeric_id(tmp_path: Path) -> None:
    """With legacy numeric id 1 OPEN, a row counting 1 must not stand in for it."""
    result = _run(tmp_path, _obs("1", "OPEN") + _obs("a", "OPEN"), "--packet", _packet(tmp_path, "| A | 1 | a |\n"))
    assert result.returncode == 1
    assert "OPEN but missing from the ledger: 1" in result.stderr


def test_an_empty_or_unparsable_log_fails(tmp_path: Path) -> None:
    result = _run(tmp_path, "## Observation a: wrong heading level\n\n**Status:** OPEN\n")
    assert result.returncode == 1
    assert "no observations parsed" in result.stderr


def test_an_observation_without_a_status_line_fails(tmp_path: Path) -> None:
    result = _run(tmp_path, _obs("a", "OPEN") + "### Observation b: title\n\n**Stauts:** OPEN\n\n")
    assert result.returncode == 1
    assert "b: no **Status:** line" in result.stderr


def test_identical_resolution_text_under_bare_statuses_fails(tmp_path: Path) -> None:
    resolution = "**Resolution:** fixed by PR #283, and the records were refreshed across the phase.\n"
    result = _run(tmp_path, _obs("a", "CLOSED", resolution) + _obs("b", "CLOSED", resolution))
    assert result.returncode == 1
    assert "identical closing text on a, b" in result.stderr


def test_a_progress_note_is_not_closure_evidence(tmp_path: Path) -> None:
    """An abandoned PR named in interim progress does not show the resolution happened."""
    result = _run(tmp_path, _obs("a", "CLOSED", "**Progress:** tried PR #12, abandoned.\n"))
    assert result.returncode == 1
    assert "a: closing status names no checkable artifact" in result.stderr


def test_a_ledger_without_a_count_column_fails(tmp_path: Path) -> None:
    packet = tmp_path / "packet.md"
    packet.write_text("## Completeness ledger\n\n| Group | IDs |\n|---|---|\n| A | a |\n", encoding="utf-8")
    result = _run(tmp_path, _obs("a", "OPEN"), "--packet", str(packet))
    assert result.returncode == 1 and "no Count column" in result.stderr


def test_a_total_row_is_checked_against_the_whole_ledger(tmp_path: Path) -> None:
    """A Total placed mid-table was compared only with the rows above it."""
    log = _obs("a", "OPEN") + _obs("b", "OPEN")
    early = _run(
        tmp_path, log, "--packet", _packet(tmp_path, "| A | 1 | a |\n| **Total** | **1** | |\n| B | 1 | b |\n")
    )
    assert early.returncode == 1
    assert "not its last row" in early.stderr and "total 1 does not equal the 2 ids" in early.stderr


def test_a_pull_request_url_is_closure_evidence(tmp_path: Path) -> None:
    status = "ACTIONED — merged as [PR 306](https://github.com/ZK-Theory/TDL/pull/306)."
    assert _run(tmp_path, _obs("a", status)).returncode == 0


def test_headings_inside_fenced_code_are_not_observations(tmp_path: Path) -> None:
    fenced = "Template:\n\n```markdown\n### Observation fake: example\n\n**Status:** OPEN\n```\n"
    packet = _packet(tmp_path, "| A | 1 | a |\n")
    result = _run(tmp_path, _obs("a", "OPEN", fenced), "--packet", packet)
    assert result.returncode == 0, result.stderr
    assert "1 observation(s): 1 OPEN" in result.stdout


def test_an_unrecognised_status_fails(tmp_path: Path) -> None:
    """`OPEM` is neither OPEN nor closed, so it vanished from the ledger while the lint passed."""
    packet = _packet(tmp_path, "| A | 1 | a |\n")
    result = _run(tmp_path, _obs("a", "OPEN") + _obs("b", "OPEM"), "--packet", packet)
    assert result.returncode == 1
    assert "b: unrecognised status" in result.stderr


def test_a_digit_only_number_is_not_a_commit(tmp_path: Path) -> None:
    dated = _run(tmp_path, _obs("a", "ACTIONED — completed on 20260925."))
    commit = _run(tmp_path, _obs("a", "ACTIONED — landed in commit 1234567."))
    assert dated.returncode == 1
    assert commit.returncode == 0, commit.stderr
