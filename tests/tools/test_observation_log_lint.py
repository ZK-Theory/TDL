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
    packet = _packet(tmp_path, "| A | 1 | a |\n| **Total** | **1** | |\n")
    result = _run(tmp_path, _obs("a", "OPEN", fenced), "--packet", packet)
    assert result.returncode == 0, result.stderr
    assert "1 observation(s): 1 OPEN" in result.stdout


def test_an_unrecognised_status_fails(tmp_path: Path) -> None:
    """`OPEM` is neither OPEN nor closed, so it vanished from the ledger while the lint passed."""
    packet = _packet(tmp_path, "| A | 1 | a |\n| **Total** | **1** | |\n")
    result = _run(tmp_path, _obs("a", "OPEN") + _obs("b", "OPEM"), "--packet", packet)
    assert result.returncode == 1
    assert "b: unrecognised status" in result.stderr


def test_a_digit_only_number_is_not_a_commit(tmp_path: Path) -> None:
    dated = _run(tmp_path, _obs("a", "ACTIONED — completed on 20260925."))
    commit = _run(tmp_path, _obs("a", "ACTIONED — landed in commit 1234567."))
    assert dated.returncode == 1
    assert commit.returncode == 0, commit.stderr


def test_an_unterminated_fence_fails_loudly_and_keeps_the_later_observations(tmp_path: Path) -> None:
    """An unclosed fence made every later heading look like quoted code, so the lint dropped them all.

    Obs 2026-09-30-system-review-prs-stopping-rule-follow-ups (PR #306): the later entries vanished
    from the parse, the OPEN count and every ledger, and the lint still exited 0.
    """
    log = (
        _obs("a", "OPEN", "Quote:\n\n```markdown\nan example that is never closed\n")
        + _obs("b", "OPEN")
        + _obs("c", "OPEN")
    )
    result = _run(tmp_path, log)
    assert result.returncode == 1, result.stdout
    assert "unterminated" in result.stderr and "```" in result.stderr
    assert "3 observation(s): 3 OPEN" in result.stdout


def test_a_status_inside_a_fenced_example_is_not_the_status(tmp_path: Path) -> None:
    """The first ``**Status:**`` in the block was read, quoted examples included.

    Obs 2026-09-30-system-review-prs-stopping-rule-follow-ups (PR #306): an entry that quotes the
    observation template before its own Status line was counted OPEN, and an entry with no real Status
    line took the quoted one instead of failing.
    """
    example = "Template:\n\n```markdown\n**Status:** OPEN\n```\n"
    quoted_first = f"### Observation a: title\n\n{example}\n**Status:** ACTIONED — fixed in PR #306.\n\n"
    only_quoted = f"### Observation b: title\n\n**Stauts:** OPEN\n\n{example}\n"
    quoted_resolution = (
        "### Observation c: title\n\n**Status:** CLOSED\n\n```\n**Resolution:** fixed in PR #12.\n```\n\n"
    )

    first = _run(tmp_path, quoted_first)
    assert first.returncode == 0, first.stderr
    assert "1 observation(s): 0 OPEN" in first.stdout

    missing = _run(tmp_path, only_quoted)
    assert missing.returncode == 1 and "b: no **Status:** line" in missing.stderr

    resolution = _run(tmp_path, quoted_resolution)
    assert resolution.returncode == 1
    assert "c: closing status names no checkable artifact" in resolution.stderr


def test_escalated_and_partially_statuses_count_as_open(tmp_path: Path) -> None:
    """A standalone ESCALATED or PARTIALLY entry was in no ledger: only a leading OPEN counted as open.

    Obs 2026-09-30-system-review-prs-stopping-rule-follow-ups (PR #306): the owner default is that a
    status beginning ESCALATED or PARTIALLY is still open work, so it must reach every ledger.
    """
    log = (
        _obs("a", "ESCALATED — owner decision pending.")
        + _obs("b", "PARTIALLY ADDRESSED — AWAITING OWNER DECISION (2026-09-08).")
        + _obs("c", "**OPEN**")
        + _obs("d", "ACTIONED — fixed in PR #1.")
        + _obs("e", "DEFERRED — external.")
    )
    counted = _run(tmp_path, log)
    assert counted.returncode == 0, counted.stderr
    assert "5 observation(s): 3 OPEN" in counted.stdout

    short = _run(tmp_path, log, "--packet", _packet(tmp_path, "| A | 2 | b · c |\n| **Total** | **2** | |\n"))
    assert short.returncode == 1
    assert "OPEN but missing from the ledger: a" in short.stderr

    whole = _run(tmp_path, log, "--packet", _packet(tmp_path, "| A | 3 | a · b · c |\n| **Total** | **3** | |\n"))
    assert whole.returncode == 0, whole.stderr
    assert "ledger matches the 3 OPEN observation(s)" in whole.stdout


def test_a_ledger_without_a_total_row_fails(tmp_path: Path) -> None:
    """The Total was checked only when present, so a ledger that simply omitted it passed.

    Obs 2026-09-30-system-review-prs-stopping-rule-follow-ups (PR #306): a hand-assembled count was
    the failure this ledger exists to end, and the row that states the count was optional.
    """
    log = _obs("a", "OPEN") + _obs("b", "OPEN")
    bare = _run(tmp_path, log, "--packet", _packet(tmp_path, "| A | 2 | a · b |\n"))
    assert bare.returncode == 1
    assert "no Total row" in bare.stderr


def test_the_total_row_is_identified_by_its_label(tmp_path: Path) -> None:
    """Any row with a count and no ids was read as the Total, whatever it was called."""
    log = _obs("a", "OPEN") + _obs("b", "OPEN")
    mislabelled = _run(tmp_path, log, "--packet", _packet(tmp_path, "| A | 2 | a · b |\n| Grand sum | 2 | |\n"))
    assert mislabelled.returncode == 1
    assert "no Total row" in mislabelled.stderr
    assert "ledger row 'Grand sum' declares '2' but lists 0 id(s)" in mislabelled.stderr

    listing = _run(tmp_path, log, "--packet", _packet(tmp_path, "| A | 1 | a |\n| **Total** | **2** | b |\n"))
    assert listing.returncode == 1
    assert "Total row lists ids" in listing.stderr

    empty_group = _run(
        tmp_path, log, "--packet", _packet(tmp_path, "| A | 2 | a · b |\n| B | 0 | |\n| **Total** | **2** | |\n")
    )
    assert empty_group.returncode == 0, empty_group.stderr


def test_a_progress_field_next_to_the_resolution_is_not_closure_evidence(tmp_path: Path) -> None:
    """The Resolution paragraph was captured up to the next blank line, so an adjacent field ran into it.

    Obs 2026-09-30-system-review-prs-stopping-rule-follow-ups (PR #306): a ``**Progress:**`` line
    written directly under ``**Resolution:**`` was read as part of the resolution, so the abandoned PR
    it names counted as the artifact that closed the entry.
    """
    adjacent = "**Resolution:** done, as agreed.\n**Progress:** tried PR #12, abandoned.\n"
    result = _run(tmp_path, _obs("a", "CLOSED", adjacent))
    assert result.returncode == 1
    assert "a: closing status names no checkable artifact" in result.stderr

    own_line = "**Resolution:** fixed in PR #12.\n**Progress:** tried PR #11 first.\n"
    kept = _run(tmp_path, _obs("b", "CLOSED", own_line))
    assert kept.returncode == 0, kept.stderr


def test_a_file_with_a_long_extension_is_closure_evidence(tmp_path: Path) -> None:
    """A path ending in ``.parquet`` named a real artifact but the extension pattern stopped at five characters.

    Obs 2026-09-30-system-review-prs-stopping-rule-follow-ups (PR #306).
    """
    pathed = _run(tmp_path, _obs("a", "CLOSED", "**Resolution:** wrote `results/p01/h1_2026-09-30.parquet`.\n"))
    bare = _run(tmp_path, _obs("b", "CLOSED", "**Resolution:** regenerated h1_table.parquet from the script.\n"))
    assert pathed.returncode == 0, pathed.stderr
    assert bare.returncode == 0, bare.stderr
    nothing = _run(tmp_path, _obs("c", "CLOSED", "**Resolution:** it was sorted out, see the notes.\n"))
    assert nothing.returncode == 1, "positive control: prose naming no artifact must still fail"


def _git(cwd: Path, *args: str) -> str:
    env_args = ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.hooksPath=/dev/null"]
    done = subprocess.run(["git", *env_args, *args], cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _repo_with_a_stranded_commit(tmp_path: Path) -> tuple[Path, str, str]:
    """A clone whose first commit is pushed to its origin and whose second exists only locally."""
    origin, clone = tmp_path / "origin.git", tmp_path / "clone"
    _git(tmp_path, "init", "-q", "--bare", str(origin))
    _git(tmp_path, "init", "-q", "-b", "main", str(clone))
    _git(clone, "remote", "add", "origin", str(origin))
    _git(clone, "commit", "-q", "--allow-empty", "-m", "pushed")
    pushed = _git(clone, "rev-parse", "HEAD")
    _git(clone, "push", "-q", "origin", "main")
    _git(clone, "fetch", "-q", "origin")
    _git(clone, "switch", "-q", "-c", "local-only")
    _git(clone, "commit", "-q", "--allow-empty", "-m", "stranded")
    return clone, pushed, _git(clone, "rev-parse", "HEAD")


def test_an_open_entry_citing_a_local_only_commit_is_reported(tmp_path: Path) -> None:
    """A "built" limb whose commit was never pushed must not read as delivered.

    Obs 2026-10-06-owner-decided-work-stranded-on-local-branches: two owner-decided deliverables sat on
    never-pushed branches for four weeks while the log, and two review packets, called them built.
    """
    clone, pushed, stranded = _repo_with_a_stranded_commit(tmp_path)
    log = _obs("a", f"OPEN — the gate is built on a branch (`{stranded[:9]}`).")
    result = _run(tmp_path, log, "--reachability", str(clone))
    assert result.returncode == 1
    assert f"a: cites commit {stranded[:9]}, which is on no remote-tracking ref" in result.stderr

    delivered = _run(tmp_path, _obs("b", f"OPEN — limb 1 merged in {pushed[:9]}."), "--reachability", str(clone))
    assert delivered.returncode == 0, delivered.stderr
    assert "reachability: 1 commit hash(es) checked, 0 stranded" in delivered.stdout


def test_reachability_reads_only_open_entries_and_skips_carried_hashes(tmp_path: Path) -> None:
    clone, pushed, stranded = _repo_with_a_stranded_commit(tmp_path)
    closed = _obs("a", f"ACTIONED — fixed in {stranded[:9]}.")
    carried = _obs("b", f"OPEN — carried as `{pushed[:9]}` (was `{stranded[:9]}`).")
    result = _run(tmp_path, closed + carried, "--reachability", str(clone))
    assert result.returncode == 0, result.stderr
    assert "1 commit hash(es) checked, 0 stranded" in result.stdout


def test_a_hash_that_is_not_a_commit_here_is_counted_not_dropped(tmp_path: Path) -> None:
    """Hashes from other repositories, or content digests, cannot be checked here; the count says so."""
    clone, _, _ = _repo_with_a_stranded_commit(tmp_path)
    result = _run(
        tmp_path, _obs("a", "OPEN — MathUni merge 4d057729 and digest dd085c86."), "--reachability", str(clone)
    )
    assert result.returncode == 0, result.stderr
    assert "0 commit hash(es) checked, 0 stranded; 2 not a commit in this repository" in result.stdout
