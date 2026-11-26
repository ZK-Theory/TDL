CONFIRM WITH FINDINGS

# Re-review: WP9.5 owner-decision amendments (2026-11-24), fixes at 4a114625

| Field | Value |
|---|---|
| Subject | `docs/plans/agentic-research-system/transition/w9/wp9-5-owner-decision-amendments-2026-11-24.md` at `4a114625` (reviewed first at `7b55454d`) |
| First review | `reviews/wp9-5-amendments-review-2026-11-24.md` (REWORK REQUIRED: 0 Blocking, 1 Major, 10 Minor, 7 Info). The report is committed unchanged. |
| Scope asked | Section 1.2 (D3) in full against A-M1 and A-m1; a brief check that the fixes for A-m2 to A-m7, A-m9 and A-m10 do what was asked and add nothing new. A-m8 is an owner decision and was left open on purpose. |
| Method | `git diff 7b55454d HEAD` on the amendment (170 lines changed), re-reads of the cited code at `dbd54fe3`, and a scratch model of the new D3 rule. Read-only; the only file written is this report. |

## 1. Verdict

**CONFIRM WITH FINDINGS.** A-M1 is closed. The new D3 rule gives the right verdict on the scenario that broke the old
wording, on in-order lists, and on the HR-2 revert case. A-m1 is closed apart from one edge in how it encodes surface
deletion (R-m1). The other fixes do what was asked. There is no Blocking or Major finding. Four new Minor findings are
drafting and consistency points, none of which changes direction (R-m1 to R-m4).

| Section | Verdict | Findings |
|---|---|---|
| 1.2 D3 | CONFIRM WITH FINDINGS (R-m1 is a one-sentence edit) | R-m1, R-i3, R-i4 |
| 1.1 A1, 1.3 E1, 1.4 J1 | CONFIRM WITH FINDINGS | R-i1, R-i2 |
| 2 H1 | CONFIRM WITH FINDINGS (A-m8 still open for Stephen) | R-m2 |
| 3 I1 | CONFIRM WITH FINDINGS | R-m3 |
| 4 rows | CONFIRM WITH FINDINGS | R-m4 |
| **Overall** | **CONFIRM WITH FINDINGS** | 0 Blocking, 0 Major, 4 Minor, 4 Info |

## 2. A-M1 and A-m1: section 1.2 (D3), in full

### A-M1 (Major): closed

The "After" text (lines 91 to 102) now defines the test: for each entry that affects the item, take
`b = blob_at(repo, <observation git_commit>, entry["surface"])`; the item passes only if `b` is in `Accept(entry)`.
`Accept(entry)` is the entry's `new_blob` plus the `new_blob` of every same-surface entry reachable by following links
where a later entry's `old_blob` equals the previous entry's `new_blob`. It says list position is never used and gives
the reason (Rule 3 late entries are appended out of order). Cycles stop at a blob already collected. An absent surface
(`b is None`) refuses.

I modelled this rule (scratch script, section 5) and ran the amendment's own test list:

| Case | Entries and item | Result | Wanted |
|---|---|---|---|
| Late entry | `[e2=(B,C), e3=(A,B)]`, item at B | e2 refuses, e3 passes | same |
| In order | `[(A,B),(B,C)]`, item at B | first passes, second refuses | same |
| Revert (HR-2) | `[(A,B),(B,A)]`, item at original A | both pass | the documented limit |
| Two surfaces | S and T entries | no cross-talk | same |
| Cycle | revert case above | terminates | same |

The text fixes the failure I described. It also fixes the looser reading (any entry with this `new_blob`), because
"reachable by links" excludes an earlier-listed entry. The test list (lines 110 to 119) names the late-entry scenario, an
earlier-listed entry not admitting an item for a later change, the revert, a cycle, an absent surface and a deletion. That
is the set I asked for.

### A-m1 (Minor): closed, with one edge (R-m1)

- (a) `pr_number` is "a positive integer or `null`, never a `bool`", the bool check cited at `evidence.py:301` (verified:
  that line is `isinstance(value, int) and not isinstance(value, bool)`). The ack-only condition is stated to be the
  detector's check (note 6.2.2 item 3.4). Closed.
- (b) `surface` is a canonical repository-relative path via `_is_canonical_relpath` (`evidence.py:446`, verified; it
  rejects empty segments, `.`, `..`, a leading or trailing `/`, `\` and `:`), with the reason (`evidence.py:184`) and the
  fixtures that change (`test_w9_evidence_acceptance.py:60` and `test_w9_wp9_3_2_runtime.py`, both verified as the
  placeholder `"a shared surface"`; in the second file the literal is at line 378, the amendment cites 377). Closed.
- (c) Creation and deletion: the all-zero id as `old_blob` for a created surface and as `new_blob` for a deleted one, and
  "such an entry never admits an affected item". Mostly closed; see R-m1.

**R-m1 [1.2, Minor] The all-zero id is a shared node in the link graph, so "a deletion entry never admits an item" is
not always true, and repeated delete and create cycles conflate.** A deletion entry `(X, zero)` has `new_blob = zero`.
Any later creation entry `(zero, Y)` has `old_blob = zero`, so it is "reachable by following links" from every earlier
deletion entry of the same surface. Model: `[D1=(A,0), C1=(0,X), D2=(X,0), C2=(0,Y)]`, item observed at X, before D2.
`Accept(D2) = {0, X, Y}` (via C1), so the item passes D2 although it predates the deletion. Also, a deletion entry
followed by a re-creation entry does admit items observed after the re-creation, which contradicts "never admits".
Failure needs a shared surface that is deleted and re-created more than once, which is unlikely for four contract files
and fails in the stale direction only through that path. Disposition: fix now, one sentence. Proposed text: "Links are
not followed through the all-zero id: a deletion entry has `Accept = {zero id}` and admits nothing, and a creation entry
starts its own chain." The deletion test then stays as written.

## 3. Brief check of the other fixes

| Finding | Fixed? | What I checked | New issue |
|---|---|---|---|
| A-m2 (E1 `now`, inert before read) | Yes | `require_vault_detector_cadence(reader, now)`, `now` timezone-aware, inert test inside before any read, with the reason; `check_environment` gains `now`, callers `preparers.py:706` and `:1029` (both verified; `prepare_proposal` and `prepare_resolution` have `now`). | None |
| A-m3 (E1 edge cases) | Yes | File closed on `{format, entries}`, each entry on `kind` plus its keys; `_utc()` timestamps; 40-hex and 64-hex; only `status == "ok"` admitted (so a failed run cannot bridge a gap); `decision_ref` unchecked, ownership is the I1 merge; malformed `accepted_cl_export` entry refuses with `EvidenceRefused`; docstring exception. | R-i2 |
| A-m4 (J1) | Yes | New `require_cl_classified_list(classified, export)`; `require_cl_export` unchanged with the out-of-boundary callers named (`export_recheck.py:46`, `cli.py:1850`); key is `ordinal`, equal to the row's `row_ordinal`; flat descriptor versus the three-descriptor `ACCEPTED_CL_EXPORT` entry; placement left to the code task. | None |
| A-m5 (A1) | Yes | Stricter-than-note rules called deliberate, "LR-015 now also refuses ..." replaces "unchanged", the test lines (28, 29, 34, 60, 62) and builder lines are right, builders take role and kind from the registration, three negative controls, "certify the gate, not the exporter". | None |
| A-m6 (preamble) | Yes | P-089 "its tests" cited and "Stephen to confirm"; protected list matches note 2.2; dated re-records appended with originals kept; `acceptance.py:133-134` corrected. | R-i1 |
| A-m7 (H1) | Mostly | (d) says "through a reviewed pull request", names both segmenters, and states it adds no writer class (`tools/w9_schema_gen.py:327,452`; W9 5.2) and so no D-4 consequence. | R-m2 |
| A-m8 (H1 end) | Left open, as agreed | The "Open" paragraph records the gap, names the owner decision, and proposes a default (a code constant a pin advance flips). | R-i2 |
| A-m9 (I1) | Yes | Closure sentence now limited to `tools/` files and `test_derived_closure_tools_and_accepted_w9_are_codeowned`; the 13 pinned modules called "pinned, not owned (P-090 item 1)"; bullet range 713 to 758 stated; amendment stamp added; next-bullet sentence changed; shared-surface PRs listed as bypass PRs. | R-m3 |
| A-m10 (rows) | Yes | Row 29 changed to cover the classified list and its format; the 06v reference column, the header cells and the dated Amendments entries are carried as code-PR duties. | R-m4 |

### New findings

**R-m2 [section 2, H1, Minor] "Through a reviewed pull request" is not a condition the detector's H1 branch checks.**
Note 6.5 (line 700) passes a qualifying append on the byte tests alone; every other Rule 1 branch requires a mapped
`pr_number` (line 701). The amendment closes the text gap I raised but still says "the post-merge detector checks this".
A direct push of a qualifying append would pass. The ruleset blocks a direct push, so the exposure is small. Say which
part the detector checks: "the detector requires a mapped `pr_number` for (d), as it does for the other Rule 1 branches;
that the PR was reviewed is human review". The code brief then carries the `pr_number` requirement. Disposition: fix now.

**R-m3 [section 3, I1, Minor] The next-bullet replacement leaves a broken sentence, and the header still cites the old
range.** The text replaces only the clause "While bypasses stay the exception" (`CONVENTIONS.md:763-764`). The original
continues ", rule insights can single one out, which the bullet above relies on." After the swap the sentence reads
"Apart from those, bypasses stay the exception, rule insights can single one out", which does not parse. Give the full
replacement sentence, for example: "W9 evidence PRs are expected bypasses, each carrying a `Bypass reason:` line, so the
weekly bypass review does not read them as anomalies. While other bypasses stay the exception, rule insights can single
one out, which the bullet above relies on." Separately, the header cell "Amends" (line 7) still says "the `CONVENTIONS.md`
bullet at lines 713 to 729"; §3's body now covers paragraphs of the bullet at 713 to 758 and a sentence of the next. Make
the two agree. Disposition: fix now.

**R-m4 [section 4, Minor] The changed row 29 drops a reader and misnames the classified list's producer.** The new row
(line 309) lists the reader as "WP9.3, LR-011 and LR-015; the vault detector"; the existing row 29 also names "WP9.3-2's
recheck" (the export recheck), which still reads the export. The producer is given as `tools/w9_segmentation.py` at
L-0b, which produces the export; W9 7.3 item 1 has the baseline observer produce the classified list and Stephen accept
it. Disposition: fix now (reader cell: add the recheck; producer cell: add "the baseline observer; accepted by Stephen").

### Info

- **R-i1.** Preamble line 29 says the unit and WP9.3 files in the WP9.4-1 record are re-run "which A1 and E1 change".
  The files at record lines 128 and 129 (`test_w9_evidence_acceptance.py` and the WP9.3 runtime files) are D3's. Say
  "A1, D3 and E1".
- **R-i2.** Two statements promise a test or a default the text does not make operational. (a) "A shape test covers
  populated `ACCEPTED_CL_EXPORT` and `ACCEPTED_CONVENTIONS_CLASSIFICATION` entries" passes vacuously while both are
  empty, and the second constant does not exist yet ("today nothing enforces either constant's shape"). The test must
  feed the validator synthetic entries, so it bites before L-0b. (b) The "Open" paragraph for A-m8 states a default design
  ("a code constant that a pin advance flips"). That is fine as a default pending Stephen, but the code brief must not
  implement the H1 branch as unconditional or as constant-gated until he decides.
- **R-i3.** Section 1.2 is clear on the rule, with three trivia: "an entry links to the next when that entry's `old_blob`
  equals its `new_blob`" has ambiguous pronouns (suggest: "entry F follows entry E when F's `old_blob` equals E's
  `new_blob`"); the absent-surface bullet precedes "Otherwise it refuses with ...", so the message for that case is not
  stated; and the revert test says "(the limit below, kept)" while the Known limit paragraph is above it.
- **R-i4.** Case not in the test list: a chain with a gap, where an intermediate change was never listed (`[(A,B),(C,D)]`,
  item at D). The first entry refuses it ("predates"), which is a false refusal in the safe direction and is what the
  detector's Rule 3 would flag. No change needed; a one-line test would document it.

## 4. Decision audit

| Item | Disposition |
|---|---|
| A-M1 | Closed (section 2). |
| A-m1 | Closed apart from R-m1. |
| A-m2 to A-m7, A-m9, A-m10 | Closed; new points R-m2, R-m3, R-m4, R-i1, R-i2. |
| A-m8 | Open for Stephen, by design. |
| Authority and boundary | The amendment still decides nothing P-090 does not, except where it marks "Stephen to confirm" (test-change boundary) or "Open" (A-m8). |

## 5. Evidence, commands and limits

- **Read:** the amendment at `4a114625` in full; `git diff 7b55454d HEAD` for it; `evidence.py` lines 184, 301, 446;
  `acceptance.py` 133-134, 139-141; `preparers.py` 706, 1029; `reader.py` 309; `reducers.py` 631-634; `CONVENTIONS.md`
  759 to 771; note lines 700 to 701 and 788; W9 7.3 item 1.
- **Model:** `d3_accept_model.py` in the session scratchpad (outside the repository): a pure-Python model of
  `Accept(entry)`. It covers the five table cases above and the delete and create cycle in R-m1. It does not call the
  repository.
- **Not run:** no tests, no `gh`, no vault reads. The model checks the text's logic, not any implementation.
- **Drift:** `git diff dbd54fe3 HEAD` still shows only `research_system/legacy/citations.py` under `research_system`,
  `tests`, `tools`, `.github` and `CONVENTIONS.md`.
- **Repository state:** `git status --short` was clean before this report was written. This report is the only file
  added.
