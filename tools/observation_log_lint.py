#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign H)
# Purpose: Lint the shared observation log and compute a review packet's completeness ledger,
# so neither a borrowed resolution stamp nor a hand-assembled "every item accounted for" can pass.
"""Lint ``~/.claude/skill-observations/log.md`` and, optionally, a review packet's ledger.

Checks:

* **A parse that finds nothing fails**, as does an observation with no ``**Status:**`` line: either
  would otherwise drop out of every ledger silently.
* **An unterminated code fence fails**, naming the line that opened it. It would otherwise turn every
  later heading into quoted code and drop every later observation; the later entries are still counted.
* **Fenced text is never a field.** A ``**Status:**`` or ``**Resolution:**`` inside a code fence is a
  quoted example; it is dropped before the fields are read.
* **Duplicate ids.** Concurrent sessions have collided on plain-integer numbering before.
* **Evidence-free closing stamps.** An ACTIONED/CLOSED/DECLINED status must name something a
  reader can check (a commit, PR, Jira key, file path or archive) on its Status line or in a
  ``**Resolution:**`` paragraph. ``**Progress:**`` notes do not count: they record interim work.
  The borrowed stamps of the 2026-09-08 reconciliation pass (obs
  2026-09-08-reconciliation-stamped-a-borrowed-resolution) read like resolutions and named
  nothing. DEFERRED is exempt: it claims no fix.
* **Identical closing text.** The same substantive Status or Resolution text on two ids is the
  borrowing shape, unless the text declares itself a ``batch disposition``.
* **OPEN means open work.** A status beginning OPEN, ESCALATED or PARTIALLY is in the OPEN set (owner
  default): an escalated entry awaits a decision and a partial one is half done, so neither may drop out
  of a ledger. DEFERRED claims no fix and stays outside it.
* **Completeness ledger** (``--packet``). The IDs column of the packet's "Completeness ledger"
  table must equal the log's OPEN set, computed rather than assembled (obs
  2026-09-01-completeness-ledger-missed-six-live-items: a hand ledger was wrong by six). Unknown,
  repeated and missing ids are named, and each row's Count, and the Total, must match its ids. The
  table must end with one row labelled Total: a ledger that omits it states no count to check.
* **Reachability** (``--reachability REPO``). Every commit an OPEN, ESCALATED or PARTIALLY entry cites
  must be on a remote-tracking ref or a tag the remote has (``tools/commit_reachability.py``); a commit that
  exists only on a local branch or a local tag has not been delivered (obs 2026-10-06-owner-decided-work-stranded-on-local-branches). A hash written as
  ``was <sha>`` was carried onto a new commit and is skipped. Hashes that are not commits in REPO are
  counted in the summary, not dropped. An unpublished commit whose changed files all sit on a remote branch at the
  bytes it gave them landed by content, through another commit, and is noted rather than reported (obs
  2026-11-03-log-lint-judges-delivery-by-hash-and-pr-state: four of four findings in one review were such commits).
* **Close conditions** (``--close-conditions REPO``). An OPEN entry whose "close when #N merges" clause names
  only merged PRs is reported: six entries sat open for nine days after their PRs merged (obs
  2026-10-15-close-conditions-met-but-entries-left-open). Pull URLs and ``owner/repo#N`` are resolved in their own
  repository; a bare ``#N`` in an entry about another tree is reported as ambiguous (obs
  2026-10-20-close-conditions-lint-blind-to-cross-repo-prs). Only the Status, Progress, Resolution and Closed fields
  are read, since an Issue paragraph may quote another entry's condition; a PR introduced by "after #N" is a
  precondition, not the condition; and a PR merged into a base other than the default branch has not been delivered
  (obs 2026-10-27-stacked-pr-merged-into-a-dead-base-reads-as-delivered).
* **Intake rows** (``--intake FILE``). A DEFERRED entry whose status sends a limb to a gate's intake or planning pass
  ("Gate 7+ intake", "the next Gate 7 planning pass") must have a row naming its id in FILE, the list planning
  sessions read (obs 2026-11-03-gate7-intake-deferrals-have-no-landing-record).

Usage: python tools/observation_log_lint.py LOG.md [--packet PACKET.md] [--reachability REPO] [--close-conditions REPO]
       [--intake FILE]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commit_reachability import Publication, merged_pull_request  # noqa: E402

_CLOSING = ("ACTIONED", "CLOSED", "DECLINED")
# A commit hash must carry a hex letter, or be introduced by the word "commit": an all-digit run is
# far more often a date or a count (`completed on 20260925`) than a hash.
_ARTIFACT = re.compile(
    r"github\.com/[\w.-]+/[\w.-]+/(?:pull|commit|issues)/\w+"
    r"|\b(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b|\bcommit\s+`?[0-9a-f]{7,40}\b|#\d+|\b[A-Z][A-Z0-9]+-\d+\b|archive/log-"
    r"|[\w-]+(?:/[\w.-]+)+\.[A-Za-z0-9]{1,12}\b"
    r"|\b[\w-]+\.(?:py|ps1|md|sh|yml|yaml|json|toml|txt|ts|js|lean|tex|parquet|csv|pkl|ipynb)\b"
)
# A bare status word ("CLOSED", "ACTIONED (2026-09-09)") is not borrowable text; the borrowed
# stamps were full sentences. Only substantive closing text is compared across ids.
_SUBSTANTIVE = 40
# Only the paragraphs that state the closure are evidence for it. A Progress paragraph records interim
# work, which may name an abandoned PR; it does not show that the resolution happened.
# The capture ends at a blank line or at the next ``**Field:**`` line, so an adjacent Progress field
# written directly under the Resolution is not read as part of it.
_RESOLUTION = re.compile(r"(?ms)^\*\*(?:Resolution|Closed)[^*]*:\*\*(.*?)(?=\n\s*\n|\n\*\*[^*\n]+:\*\*|\Z)")


_STATUSES = ("OPEN", "ACTIONED", "CLOSED", "DECLINED", "DEFERRED", "ESCALATED", "PARTIALLY")
# Open work: a status that has not been resolved. ESCALATED (an owner decision is awaited) and
# PARTIALLY (half the work is done) count (owner default from the 2026-10-02 dispatch): DEFERRED does not.
_OPEN_STATUSES = ("OPEN", "ESCALATED", "PARTIALLY")
_HEADING = "### Observation "


_FENCE = re.compile(r"\s*(`{3,}|~{3,})(.*)$")


def _fence_opener(line: str) -> str | None:
    """Return the fence run (``` or ~~~, any length of three or more) that opens a fenced block on this line."""
    match = _FENCE.match(line.rstrip("\r\n"))
    if match and not (match.group(1)[0] == "`" and "`" in match.group(2)):
        return match.group(1)
    return None


def _closes_fence(line: str, opener: str) -> bool:
    """A fence closes only on the same character, at least as long as the opener, with no text after it."""
    match = _FENCE.match(line.rstrip("\r\n"))
    return bool(
        match and match.group(1)[0] == opener[0] and len(match.group(1)) >= len(opener) and not match.group(2).strip()
    )


def _split(lines: list[str], ignored: set[int]) -> tuple[list[str], int | None]:
    """Split at observation headings outside fenced code; also return the line index of a fence left open, if any."""
    blocks: list[list[str]] = []
    opener: str | None = None
    opened_at = 0
    for index, line in enumerate(lines):
        # Fenced lines (the fences included) are quoted text, not fields of the entry: left in the block,
        # a quoted ``**Status:**`` or ``**Resolution:**`` was read as the entry's own.
        if opener is not None:
            if _closes_fence(line, opener):
                opener = None
            continue
        found = None if index in ignored else _fence_opener(line)
        if found:
            opener, opened_at = found, index
        elif line.startswith(_HEADING):
            blocks.append([line[len(_HEADING) :]])
        elif blocks:
            blocks[-1].append(line)
    return ["".join(block) for block in blocks], (opened_at if opener is not None else None)


def scan(log_text: str) -> tuple[list[str], list[str]]:
    """Split the log into observation blocks; also return a problem for every fence that is never closed.

    An unclosed fence made every later heading look like quoted code, so every later observation
    dropped out of the parse, the OPEN count and every ledger, silently. Each unterminated opener is
    reported with its line number, then the log is split again with that opener read as plain text,
    so the observations after it are still counted.
    """
    lines = log_text.splitlines(keepends=True)
    problems: list[str] = []
    ignored: set[int] = set()
    while True:
        blocks, opened_at = _split(lines, ignored)
        if opened_at is None:
            return blocks, problems
        ignored.add(opened_at)
        shown = lines[opened_at].strip()[:30]
        problems.append(
            f"unterminated fence {shown!r} opened at log line {opened_at + 1}: every observation after it "
            "would read as quoted code; close it, or the earlier fence that should have closed"
        )


def _blocks(log_text: str) -> list[str]:
    """Split the log at observation headings that sit outside fenced code, so a quoted template is not an entry."""
    return scan(log_text)[0]


def parse(log_text: str) -> list[tuple[str, str, str]]:
    """Return (id, status line, whole block) for every observation in order; the status is "" when absent."""
    return _entries(_blocks(log_text))


def _entries(blocks: list[str]) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    for block in blocks:
        heading = block.split("\n", 1)[0]
        ident = re.split(r":\s", heading, maxsplit=1)[0].strip().strip("[]").rstrip(":")
        status = re.search(r"(?m)^\*\*Status:\*\*\s*(.*)$", block)
        entries.append((ident, status.group(1).strip() if status else "", block))
    return entries


def status_word(status: str) -> str:
    """Return the leading status word upper-cased, ignoring bold markers (``**OPEN**``); "" when there is none."""
    word = re.match(r"[*\s]*([A-Za-z]+)", status)
    return word.group(1).upper() if word else ""


def is_open(status: str) -> bool:
    """True for a status that is still open work: OPEN, and (owner default) ESCALATED or PARTIALLY.

    Only a leading OPEN counted before, so a standalone ESCALATED or PARTIALLY entry (an owner decision
    awaited, or half the work done) reached no ledger and no OPEN count: obs
    2026-09-30-system-review-prs-stopping-rule-follow-ups.
    """
    return status_word(status) in _OPEN_STATUSES


def lint(entries: list[tuple[str, str, str]]) -> list[str]:
    problems = [f"duplicate id {ident}" for ident, n in Counter(i for i, _, _ in entries).items() if n > 1]
    same: defaultdict[str, list[str]] = defaultdict(list)
    for ident, status, block in entries:
        if not status:
            # Neither OPEN nor closed, so it would silently drop out of every ledger.
            problems.append(f"{ident}: no **Status:** line")
            continue
        if status_word(status) not in _STATUSES:
            # A misspelt status (`OPEM`) is neither OPEN nor closed, so it would drop out of the ledger.
            problems.append(f"{ident}: unrecognised status {status[:40]!r}; expected one of {', '.join(_STATUSES)}")
            continue
        if status_word(status) not in _CLOSING:
            continue
        resolutions = [text.strip() for text in _RESOLUTION.findall(block)]
        if not _ARTIFACT.search(" ".join([status, *resolutions])):
            problems.append(f"{ident}: closing status names no checkable artifact: {status[:100]!r}")
        for text in (status, *resolutions):
            normalised = " ".join(text.split())
            if len(normalised) >= _SUBSTANTIVE and "batch disposition" not in normalised.lower():
                same[normalised].append(ident)
    problems += [
        f"identical closing text on {', '.join(sorted(set(ids)))}: {s[:80]!r}"
        for s, ids in same.items()
        if len(set(ids)) > 1
    ]
    return problems


def _cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def _count(cell: str) -> int | None:
    digits = cell.replace("*", "").strip()
    return int(digits) if digits.isdigit() else None


def parse_ledger(packet_text: str) -> tuple[list[str], list[str]]:
    """Return (every id listed in the ledger's IDs column, in order, problems with the table itself).

    Only the IDs column is read, so counts and group names are never mistaken for ids. Each row's
    Count must equal the ids it lists, and the row labelled Total (a Count with no ids) must be present,
    last, and equal their sum.
    """
    match = re.search(r"(?ms)^#+\s*Completeness ledger\s*$(.*?)(?=^#+\s|\Z)", packet_text)
    if not match:
        return [], ["the packet has no Completeness ledger section"]
    rows = [line for line in match.group(1).splitlines() if line.strip().startswith("|")]
    header = next((i for i, row in enumerate(rows) if "ids" in [c.lower() for c in _cells(row)]), None)
    if header is None:
        return [], ["the Completeness ledger has no table with an IDs column"]
    names = [c.lower() for c in _cells(rows[header])]
    if "count" not in names:
        return [], ["the Completeness ledger table has no Count column, so its rows cannot be checked"]
    id_col, count_col = names.index("ids"), names.index("count")
    listed: list[str] = []
    problems: list[str] = []
    totals: list[tuple[int, int | None]] = []  # (data-row position, declared total)
    position = 0
    for row in rows[header + 1 :]:
        cells = _cells(row)
        if all(re.fullmatch(r":?-+:?", c) for c in cells if c):
            continue
        position += 1
        ids = [t.strip("`") for t in re.split(r"[\s·,]+", cells[id_col] if id_col < len(cells) else "") if t.strip("`")]
        count = _count(cells[count_col]) if count_col < len(cells) else None
        if re.sub(r"[*`\s]", "", cells[0]).lower() == "total":
            # The Total is the row labelled Total. Any row with a count and no ids was read as one,
            # whatever it was called, and an unlabelled omission passed as a ledger with no Total.
            if ids:
                problems.append("the ledger's Total row lists ids; it must state only the count")
            totals.append((position, count))
            continue
        if count != len(ids):
            problems.append(f"ledger row {cells[0]!r} declares {cells[count_col]!r} but lists {len(ids)} id(s)")
        listed += ids
    # One Total, as the last row, checked against every id listed: a Total placed mid-table was
    # compared only with the rows above it. A ledger with no Total row stated no count to check.
    if not totals:
        problems.append("the ledger has no Total row; end the table with a row labelled Total giving the id count")
    elif len(totals) > 1:
        problems.append(f"the ledger has {len(totals)} Total rows; expected one")
    else:
        where, declared = totals[0]
        if where != position:
            problems.append("the ledger's Total row is not its last row")
        if declared != len(listed):
            problems.append(f"ledger total {declared} does not equal the {len(listed)} ids listed")
    return listed, problems


def ledger_ids(packet_text: str, known: set[str]) -> set[str]:
    """Return the ids listed in the packet's Completeness ledger that are known observation ids."""
    listed, _ = parse_ledger(packet_text)
    return {ident for ident in listed if ident in known}


_COMMIT = re.compile(r"\b(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b")
# A hash written as ``was <sha>`` names a commit carried onto a new one; the new hash is the one checked.
_CARRIED = re.compile(r"\bwas\s+`?([0-9a-f]{7,40})\b")


def _git_out(repo: Path, *args: str) -> str | None:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    return done.stdout.strip() if done.returncode == 0 else None


# "Close when #333 and #340 merge", "close when #341 merges": the clause up to the end of its sentence.
_CLOSE_WHEN = re.compile(r"(?i)\bclose[sd]?\s+when\b([^.\n]*)")
# A PR reference: a GitHub pull URL, ``owner/repo#N``, or a bare ``#N`` (this repository). The URL keeps its
# own dots, so it is matched against the whole paragraph, not the sentence-bounded clause.
_PR_REF = re.compile(
    r"github\.com/(?P<url_repo>[\w.-]+/[\w.-]+)/pull/(?P<url_n>\d+)"
    r"|(?<![\w/])(?P<repo>[\w.-]+/[\w.-]+)#(?P<n>\d+)\b"
    r"|(?<![\w/])#(?P<bare>\d+)\b"
)
# "Close when both merge", "close when that PR merges": the PRs are named earlier in the same paragraph.
_BACK_REFERENCE = re.compile(r"(?i)\b(?:both|all|they|these|each)\b.*\bmerge|\b(?:that|the|this)\s+PRs?\b")
# Only the fields that state where an entry stands carry its close condition. An Issue paragraph may quote another
# entry's condition, and one did: obs 2026-11-03-log-lint-judges-delivery-by-hash-and-pr-state.
_STATE_FIELD = re.compile(
    r"(?ms)^\*\*(?:Status|Progress|Resolution|Closed)\b[^*\n]*:\*\*.*?(?=\n\s*\n|\n\*\*[^*\n]+:\*\*|\Z)"
)
# "Close when the ruleset requires X (after #385 merges)": #385 is a precondition the condition waits on, not the
# condition itself, so its merge does not meet the clause.
_PRECONDITION = re.compile(r"(?i)\bafter\s+(?:PR\s+)?#(\d+)\b")
# A PR delivers only when it merges into the default branch. A stacked PR that merged into an already-merged base
# reached no path to main, though GitHub calls it merged (obs 2026-10-27-stacked-pr-merged-into-a-dead-base-...).
_DEFAULT_BRANCHES = ("main", "master")
_MERGED_ELSEWHERE = "MERGED into "
# Trees the shared log covers besides TDL (owner decisions 2026-09-25 and 2026-10-02). A bare ``#N`` in an
# entry about one of them cannot be resolved here.
_OTHER_TREES = re.compile(r"(?i)zktheoryweb|mathuni|counting lives|codex_workflow")
_FIELD = re.compile(r"(?m)^\*\*(?:Target|Environment):\*\*\s*(.*)$")

PullRef = tuple[str | None, int]


def _refs(text: str) -> list[PullRef]:
    found: list[PullRef] = []
    for m in _PR_REF.finditer(text):
        if m.group("url_n"):
            found.append((m.group("url_repo"), int(m.group("url_n"))))
        elif m.group("n"):
            found.append((m.group("repo"), int(m.group("n"))))
        else:
            found.append((None, int(m.group("bare"))))
    return list(dict.fromkeys(found))


def _label(ref: PullRef) -> str:
    repo, number = ref
    return f"{repo}#{number}" if repo else f"#{number}"


def _gh_pr_state(repo: Path, number: int, slug: str | None = None) -> str | None:
    """Return OPEN, CLOSED or MERGED, or ``MERGED into <base>`` for a PR merged anywhere but the default branch.

    A PR merged into another base still counts as delivered when its merge commit is an ancestor of ``origin/main``
    in ``repo``; that is checked only for this repository's PRs, since another repository's commits are not here.
    """
    command = ["gh", "pr", "view", str(number), "--json", "state,baseRefName,mergeCommit"]
    if slug:
        command += ["--repo", slug]
    done = subprocess.run(command, cwd=repo, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        return None
    view = json.loads(done.stdout)
    state, base = view.get("state"), view.get("baseRefName")
    if state != "MERGED" or base in _DEFAULT_BRANCHES:
        return state
    merge_commit = (view.get("mergeCommit") or {}).get("oid")
    if not slug and merge_commit and _git_out(repo, "merge-base", "--is-ancestor", merge_commit, "origin/main") == "":
        return "MERGED"
    return f"{_MERGED_ELSEWHERE}{base}"


def close_conditions(
    entries: list[tuple[str, str, str]], state_of: Callable[[str | None, int], str | None]
) -> tuple[list[str], str]:
    """Report every OPEN entry whose "close when #N merges" condition names only merged PRs.

    Obs 2026-10-15-close-conditions-met-but-entries-left-open: six entries carried such conditions for nine
    days after every PR they named had merged. The session that wrote the condition had ended before the
    merge, so nobody was present to act on it. A condition that names no PR (``close when the lane is
    required``) is counted, not judged.

    Obs 2026-10-20-close-conditions-lint-blind-to-cross-repo-prs: a zktheoryweb entry named its PR by URL and
    stayed open three days after it merged, and a bare ``#N`` there would have been judged by this repository's
    PR of that number. So URLs and ``owner/repo#N`` are resolved in their own repository, and a bare ``#N`` in
    an entry whose Target or Environment names another tree is reported as ambiguous, not judged.

    Obs 2026-11-03-log-lint-judges-delivery-by-hash-and-pr-state and its twin: a quoted sentence in an Issue
    paragraph and a precondition ("after #385 merges") were judged as conditions, and a PR merged into a dead base
    counted as delivered. So only the state fields are read, "after #N" is skipped, and a PR merged elsewhere is
    reported as undelivered rather than met.
    """
    problems: list[str] = []
    checked = unnumbered = met = ambiguous = elsewhere = 0
    for ident, status, block in entries:
        if not is_open(status):
            continue
        other_tree = any(_OTHER_TREES.search(field) for field in _FIELD.findall(block))
        for field in _STATE_FIELD.finditer(block):
            text = field.group(0)
            for match in _CLOSE_WHEN.finditer(text):
                # The clause runs to the end of its sentence: a full stop that ends a line or precedes a space, so
                # the dots inside a pull URL do not cut it short.
                end = re.search(r"\.(?=\s|$)|\n", text[match.start(1) :])
                clause = text[match.start(1) : match.start(1) + end.start()] if end else text[match.start(1) :]
                waits_on = {int(n) for n in _PRECONDITION.findall(clause)}
                refs = [ref for ref in _refs(clause) if not (ref[0] is None and ref[1] in waits_on)]
                if not refs and not waits_on and _BACK_REFERENCE.search(clause):
                    # A clause about something unbuilt ("closes when that slice merges") names no PR, unjudged.
                    refs = _refs(text[: match.end()])
                if not refs:
                    unnumbered += 1
                    continue
                bare = [ref for ref in refs if ref[0] is None]
                if other_tree and bare:
                    ambiguous += 1
                    problems.append(
                        f"{ident}: close condition names {', '.join(_label(r) for r in bare)} in an entry about "
                        "another tree; write it as owner/repo#N or a pull URL so it is checked in the right repository"
                    )
                    continue
                checked += 1
                states = {ref: state_of(*ref) for ref in refs}
                landed_elsewhere = {r: s for r, s in states.items() if s and s.startswith(_MERGED_ELSEWHERE)}
                if landed_elsewhere:
                    elsewhere += 1
                    for ref, state in landed_elsewhere.items():
                        base = state[len(_MERGED_ELSEWHERE) :]
                        problems.append(
                            f"{ident}: {_label(ref)} merged into {base}, not the default branch, so its work is on no "
                            "path to main; re-land it and name the new PR"
                        )
                elif all(state == "MERGED" for state in states.values()):
                    met += 1
                    named = ", ".join(_label(r) for r in refs)
                    problems.append(
                        f"{ident}: close condition met ({named} merged); close it, naming the merge commit(s)"
                    )
    summary = f"close conditions: {checked} naming PRs checked, {met} met; {unnumbered} name no PR"
    if elsewhere:
        summary += f"; {elsewhere} merged into a base other than main"
    if ambiguous:
        summary += f"; {ambiguous} ambiguous"
    return problems, summary


def reachability(entries: list[tuple[str, str, str]], repo: Path) -> tuple[list[str], str]:
    """Report every commit an open entry cites that is on no remote-tracking ref or remote tag of ``repo``.

    Obs 2026-10-06-owner-decided-work-stranded-on-local-branches: a gate and a proposal described as
    built and awaiting a decision existed only on never-pushed local branches for four weeks. A hash that
    is not a commit in ``repo`` (another repository's, or a content digest) cannot be checked here; it is
    counted in the summary rather than dropped silently.

    Obs 2026-11-03-log-lint-judges-delivery-by-hash-and-pr-state: four of four "stranded" findings in one review
    were review commits on never-pushed branches whose one file another PR had carried byte for byte. A commit is
    published when a remote ref contains it; its content is published when a remote ref holds every file it
    changed at the bytes it gave them. Such a commit is noted as landed by content, not reported.
    """
    problems: list[str] = []
    landed: list[str] = []
    checked = foreign = 0
    # A squash-merged PR's commits reached their reader: its head is refs/pull/<n>/head, and a commit inside it
    # is found through GitHub's commit-to-PR association (obs 2026-10-17-squash-merge-strands-the-pr-commits-...).
    publication = Publication(repo, pulls_lookup=merged_pull_request)
    for ident, status, block in entries:
        if not is_open(status):
            continue
        carried = set(_CARRIED.findall(block))
        for sha in dict.fromkeys(_COMMIT.findall(block)):
            if sha in carried:
                continue
            if _git_out(repo, "cat-file", "-t", f"{sha}^{{commit}}") != "commit":
                foreign += 1
                continue
            checked += 1
            if publication.published_by(sha) is not None:
                continue
            holder = landed_by_content(repo, sha)
            if holder:
                landed.append(f"{ident} cites {sha}, whose files are on {holder}; write it as 'was {sha}'")
                continue
            problems.append(
                f"{ident}: cites commit {sha}, which is on no remote-tracking ref or remote tag; "
                "push it or say where it went"
            )
    summary = f"reachability: {checked} commit hash(es) checked, {len(problems)} stranded"
    if landed:
        summary += f"; {len(landed)} landed by content"
    if foreign:
        summary += f"; {foreign} not a commit in this repository"
    if problems and publication.tag_note:
        summary += f"; {publication.tag_note}"
    return problems, "\n".join([summary, *(f"  landed by content: {note}" for note in landed)])


# A deferral sent to a gate's intake: "goes to Gate 7+ intake", "deferred to the next Gate 7 planning pass".
_INTAKE = re.compile(r"(?i)\bgate[ -]?\d+\+?\s+intake\b|\bgate \d+ planning pass\b")


def intake_rows(entries: list[tuple[str, str, str]], intake_text: str) -> tuple[list[str], str]:
    """Report every DEFERRED entry sent to a gate's intake whose id has no table row in the intake list.

    Obs 2026-11-03-gate7-intake-deferrals-have-no-landing-record: four approved deferrals to "Gate 7+ intake"
    were recorded only in the observation log, which planning sessions do not read, while Gate 7 was already open.
    """
    rows = [line for line in intake_text.splitlines() if line.lstrip().startswith("|")]
    problems: list[str] = []
    sent = 0
    for ident, status, _ in entries:
        if status_word(status) != "DEFERRED" or not _INTAKE.search(status):
            continue
        sent += 1
        if not any(ident in row for row in rows):
            problems.append(f"{ident}: DEFERRED to a gate's intake, but the intake list has no row naming it")
    return problems, f"intake: {sent} deferral(s) to an intake checked, {len(problems)} without a row"


def landed_by_content(repo: Path, sha: str) -> str | None:
    """Return the first remote-tracking ref that holds every file ``sha`` changed, at the bytes ``sha`` gave them.

    A file ``sha`` deleted must be absent from that ref. ``refs/remotes/origin/main`` is tried first. A commit that
    changes no file, or a path git cannot pass through ``cat-file --batch-check``, never counts as landed.
    """
    listing = _git_out(
        repo, "diff-tree", "-r", "-z", "--no-commit-id", "--name-only", "--root", "-m", "--first-parent", sha
    )
    paths = [path for path in (listing or "").split("\0") if path]
    if not paths or any("\n" in path for path in paths):
        return None
    refs = [line for line in (_git_out(repo, "for-each-ref", "--format=%(refname)", "refs/remotes") or "").splitlines()]
    refs = [ref for ref in refs if not ref.endswith("/HEAD")]
    refs.sort(key=lambda ref: ref != "refs/remotes/origin/main")
    queries = [f"{rev}:{path}" for rev in [sha, *refs] for path in paths]
    done = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "--batch-check=%(objectname)"],
        input="\n".join(queries) + "\n",
        capture_output=True,
        text=True,
        check=False,
    )
    lines = done.stdout.splitlines()
    if done.returncode != 0 or len(lines) != len(queries):
        return None
    # "<query> missing" for an absent path: a deleted file matches a ref that lacks it too.
    found = [None if line.endswith(" missing") else line for line in lines]
    width = len(paths)
    expected = found[:width]
    if all(blob is None for blob in expected):
        return None  # a commit that only deletes files would match every ref that never had them
    for index, ref in enumerate(refs, start=1):
        if found[index * width : (index + 1) * width] == expected:
            return ref
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint the observation log and a review packet's ledger.")
    parser.add_argument("log", type=Path)
    parser.add_argument("--packet", type=Path, help="Review packet whose Completeness ledger must equal the OPEN set.")
    parser.add_argument(
        "--reachability",
        type=Path,
        metavar="REPO",
        help="Git checkout in which every commit an OPEN entry cites must be on a remote branch or remote tag.",
    )
    parser.add_argument(
        "--close-conditions",
        type=Path,
        metavar="REPO",
        help="Report OPEN entries whose 'close when #N merges' PRs have all merged (reads PR state with gh in REPO).",
    )
    parser.add_argument(
        "--pr-states",
        type=Path,
        metavar="JSON",
        help=(
            'With --close-conditions: read PR states from {"<number>" or "<owner/repo>#<number>": '
            '"MERGED"|"OPEN"|"CLOSED"|"MERGED into <base>"} instead of gh.'
        ),
    )
    parser.add_argument(
        "--intake",
        type=Path,
        metavar="FILE",
        help="Intake list in which every DEFERRED entry sent to a gate's intake must have a table row naming its id.",
    )
    args = parser.parse_args(argv)

    blocks, fence_problems = scan(args.log.read_text(encoding="utf-8"))
    entries = _entries(blocks)
    if not entries:
        # An empty, truncated or re-formatted log must not read as a clean one.
        print(
            f"ERROR: no observations parsed from {args.log}; the log is empty or its headings changed", file=sys.stderr
        )
        return 1
    problems = fence_problems + lint(entries)
    known = {ident for ident, _, _ in entries}
    open_ids = {ident for ident, status, _ in entries if is_open(status)}
    print(f"{len(entries)} observation(s): {len(open_ids)} OPEN")

    if args.packet:
        listed, table_problems = parse_ledger(args.packet.read_text(encoding="utf-8"))
        problems += table_problems
        unknown = sorted({ident for ident in listed if ident not in known})
        repeated = sorted(ident for ident, n in Counter(listed).items() if n > 1)
        listed_known = {ident for ident in listed if ident in known}
        missing, stale = sorted(open_ids - listed_known), sorted(listed_known - open_ids)
        if missing:
            problems.append("OPEN but missing from the ledger: " + ", ".join(missing))
        if stale:
            problems.append("in the ledger but not OPEN: " + ", ".join(stale))
        if unknown:
            problems.append("in the ledger but not an observation id in the log: " + ", ".join(unknown))
        if repeated:
            problems.append("listed more than once in the ledger: " + ", ".join(repeated))
        if not (missing or stale or unknown or repeated or table_problems):
            print(f"ledger matches the {len(open_ids)} OPEN observation(s)")

    if args.reachability:
        stranded, summary = reachability(entries, args.reachability)
        problems += stranded
        print(summary)

    if args.close_conditions:
        if args.pr_states:
            known_states = json.loads(args.pr_states.read_text(encoding="utf-8"))

            def state_of(repo: str | None, number: int) -> str | None:
                return known_states.get(f"{repo}#{number}" if repo else str(number))
        else:

            def state_of(repo: str | None, number: int) -> str | None:
                return _gh_pr_state(args.close_conditions, number, repo)

        met, summary = close_conditions(entries, state_of)
        problems += met
        print(summary)

    if args.intake:
        missing_rows, summary = intake_rows(entries, args.intake.read_text(encoding="utf-8"))
        problems += missing_rows
        print(summary)

    for line in problems:
        print(f"ERROR: {line}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
