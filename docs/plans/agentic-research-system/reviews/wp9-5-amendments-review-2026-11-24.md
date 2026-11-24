REWORK REQUIRED

# Independent review: WP9.5 owner-decision amendments (2026-11-24)

| Field | Value |
|---|---|
| Subject | `docs/plans/agentic-research-system/transition/w9/wp9-5-owner-decision-amendments-2026-11-24.md`, commit `7b55454d`, branch `docs/w9-wp9-5-amendments` |
| Sources read | P-090 (`03-decisions-and-open-questions.md:6147-6261`); WP9.5 design note revision 8 (§2.3, §5.3, §6.2.2, §6.2.3, §6.5, §6.6, §7.3, §8.2 to §8.4, §13.2, §16.1 to §16.11); WP9.3 note §10.4; W9 §4.1 to §4.4, §5.2, §7.3, §13.3; `CONVENTIONS.md` 696 to 782; `.github/CODEOWNERS`; `tests/tools/test_ci_platform_policy.py`; the 06v addendum; 06v lines 90, 230, 566, 567 |
| Code read | `git show dbd54fe3:<path>` for `evidence.py`, `acceptance.py`, `preparers.py`, `accepted_w9.py`, `reader.py`, `segmentation.py`, `export_recheck.py`, `cli.py`, `replay/reducers.py`, `store/governed_code.py`, `tools/w9_schema_gen.py`, the registration schema, and the tests the amendment names |
| Method | Skill `adversarial-design-review`. Read-only. The only file written to the repository is this report. |

## 1. Summary

The amendment is a faithful transcription of P-090 for A1, E1, H1 and I1, and its "Now" statements are accurate against
`dbd54fe3` (every cited `path:line` resolved; two are off by one). The code cited is unchanged at the branch head
(`git diff dbd54fe3 HEAD` touches only `research_system/legacy/citations.py`, which nothing here depends on).

One defect needs a text fix before Stephen accepts: **D3's freshness rule says "a later entry for the same surface"
without defining "later"** (A-M1). Read by list position, which is the natural reading, it admits an item that predates
a surface change whenever a Rule 3 late entry is appended out of chronological order. P-090 D designs exactly that
late-entry flow. A model of the rule (scratch script, section 6) shows the wrong verdict. The fix is one definitional
sentence plus tests.

Everything else is Minor or Info: a missing `now` parameter at `check_environment`, an unspecified placement of the
classified-list validator that touches callers outside P-090's boundary, an H1 rule without a reviewed-PR condition or
an end, a CONVENTIONS sentence that claims more than I1 decided, and a missing section 4 row. No Blocking finding. No
D-4 or `IMPORTER_MODULES` touch was found.

## 2. Verdict per section

| Section | Verdict | Findings |
|---|---|---|
| 1.1 A1, manifest `/2` | CONFIRM WITH FINDINGS | A-m5, A-m6 |
| 1.2 D3, blob-keyed list `/2` | **REWORK REQUIRED** | A-M1, A-m1 |
| 1.3 E1, cadence gate | CONFIRM WITH FINDINGS | A-m2, A-m3 |
| 1.4 J1, classified list and constant | CONFIRM WITH FINDINGS | A-m4 |
| Section 1 as a whole | **REWORK REQUIRED** (A-M1 only; A-m6 is the preamble) | A-M1, A-m1 to A-m6 |
| 2 H1, W9 4.2 (d) | CONFIRM WITH FINDINGS | A-m7, A-m8 |
| 3 I1, `CONVENTIONS.md` | CONFIRM WITH FINDINGS | A-m9 |
| 4 addendum rows | CONFIRM WITH FINDINGS | A-m10 |
| **Overall** | **REWORK REQUIRED** | 0 Blocking, 1 Major, 10 Minor, 7 Info |

Scope of re-review once A-M1 is fixed: section 1.2 only.

## 3. Findings

### Major

**A-M1 [section 1.2, D3] "A later entry for the same surface" is undefined, and the list-position reading admits a
stale item.**

1. *Claim.* An affected item passes only if the surface's blob at the observation commit equals the entry's `new_blob`,
   "or the `new_blob` of a later entry for the same surface".
2. *Evidence.* Amendment 1.2, lines 68 to 71. The same words are in note section 6.5, line 713. Neither defines
   "later". `_change_entries` (`evidence.py:221-252`) keeps list order and nothing else. P-090 D3 says only "tests
   freshness by tree state". Note section 6.2.2 item 3.4 (line 575) says WP9.3 "accepts late entries": a Rule 3
   acknowledgement adds an entry after the change, and the list is append-only (Rule 0.2), so a late entry always lands
   after entries for later changes.
3. *Failure scenario.* Surface S. PR 10 changes S from blob A to B and adds no entry (a Rule 3 violation). PR 11
   changes S from B to C and lists `e2 = (old B, new C)`. Stephen later acknowledges PR 10 and the list gets the late
   entry `e3 = (old A, new B)`. The list is `[e2, e3]`. An item observed after PR 10 and before PR 11 has S at B. For
   `e2` it must be refused (it predates B to C). By list position, `e3` is "later" than `e2` and `e3.new_blob == B`, so
   the item passes `e2`. The scratch model returns `e2 positional: True`; the chain reading returns `False`. A looser
   implementation ("any entry for the surface has this `new_blob`") also passes it with an in-order list. The unit
   tests cannot tell which was meant, because the text does not say.
4. *Impact.* LR-016 and LR-020 accept an item observed under an enforcement state that a listed change has since
   replaced. That is the O-32 failure the list exists to prevent, reached through the recovery path P-090 D provides.
5. *Disposition.* Fix now, in this amendment.
6. *Proposed text* (replaces the last clause of the "After" bullet):

   > An affected item passes an entry only if `blob_at(repository_root, <observation git_commit>, entry["surface"])`
   > is in `Accept(entry)`: the entry's `new_blob`, and the `new_blob` of every entry for the same surface reachable
   > from it by following links where one entry's `old_blob` equals the previous entry's `new_blob`. List position is
   > never used, because a Rule 3 late entry is appended after entries for later changes. Link-following stops at a
   > blob already collected. An entry no other entry's `old_blob` equals has `Accept = {new_blob}`.

   Tests to name: the scenario above (e2 refused, e3 passes); an earlier-listed entry's `new_blob` does not count for a
   later change; a revert `A to B to A` still passes (the HR-2 limit, kept); a cycle terminates; the surface absent at
   the observation commit refuses.
7. *Affects.* P-090 item 2 D; WP9.3 `check_change_list`; LR-016, LR-020; 06v O-32; note section 6.5 Rule 3.

### Minor

**A-m1 [section 1.2, D3] Three format details the gate cannot settle from this text.**
(a) `pr_number` "may be null only on an entry that backs a Rule 3 acknowledgement": `_change_entries` cannot know
whether an entry backs an acknowledgement. That is the detector's check (note 6.2.2 item 3.4). Say so, and say the
gate accepts a positive integer or null and excludes `bool` (as `require_cl_export` does at `evidence.py:301`).
(b) `surface` becomes a path used as `f"{commit}:{surface}"` (`evidence.py:184`). The existing check is "non-empty
string" (`evidence.py:234`), and every current fixture uses `"a shared surface"`
(`test_w9_evidence_acceptance.py:60`, `test_w9_wp9_3_2_runtime.py:377`), which under D3 can only refuse. Require a
canonical relative path (the module already has `_is_canonical_relpath`, `evidence.py:446`) and update the fixtures.
(c) A surface created or deleted by the change has no 40-hex blob on one side; a deletion can never pass
(`blob_at` is `None`). State that creation and deletion use the all-zero id and that a deletion entry never admits an
item, or that they are out of scope. Disposition: fix now (three sentences).

**A-m2 [section 1.3, E1] `check_environment` has no `now`, and the inert path must skip the read.**
`require_vault_detector_cadence` needs `now`. `prepare_proposal` (`preparers.py:677`), `prepare_observation`
(`preparers.py:1204`) and `prepare_resolution` (`preparers.py:958`) all have it, and the reader (`_need_reader`).
`check_environment(environment, legacy, record)` (`acceptance.py:139-141`) has the reader but no `now`, and is called
from `preparers.py:706` (LR-016) and `:1029` (LR-020). Its signature must change at both. Separately, the existing
pattern is `require_x(read_evidence(...))` (`preparers.py:688`, `:1215`). If E1 copies it, `read_evidence` raises on the
absent file before the inert test runs, and every existing WP9.3 and WP9.4 test fails. The inert test and the read must
both sit inside the new function: `require_vault_detector_cadence(reader, now)`, with `now` timezone-aware, as
`_utc()` returns (`evidence.py:259`). Disposition: fix now (one sentence), or state it as a code-task obligation.

**A-m3 [section 1.3, E1] The format and rule leave edge cases open.**
(a) The key lists omit `kind` and the top-level `format` and `entries`; they defer to note section 8.4 item 2, which
shows them but gives no types. (b) `status`: the rule says only the last run needs `status == "ok"`. If a non-`ok`
`run` can exist, it counts as a run for the gap rule and can bridge a gap. Either admit only `"ok"` in the file or
count only `ok` runs. (c) `decision_ref` is unchecked by any code, so "Stephen's reset" is Stephen's code-owner merge
under I1 and nothing else; say so. (d) `accepted_cl_export[-1]["classified_list"]["git_blob"]` raises `KeyError`, not
`EvidenceRefused`, on a malformed entry, and no code validates the shape of a populated `ACCEPTED_CL_EXPORT` or
`ACCEPTED_CONVENTIONS_CLASSIFICATION` entry (the WP9.3 reader reads only `retained_copy`, `reader.py:309`;
replay only `retained_copy`, `reducers.py:631-634`). Add a shape test for populated entries, which is a constant defined
but enforced by nothing. (e) The module docstring's rule "a row whose file is absent refuses" (`evidence.py:6`) no
longer holds for this file before L-0b; update it with the code. Disposition: fix (a) to (d) in the amendment.

**A-m4 [section 1.4, J1] "`require_cl_export` also validates the classified list" is not implementable as written, and
it decides a placement the note left open.**
`require_cl_export(export)` takes one argument (`evidence.py:277`). A classified list is checked against the export's
rows, so it needs both. `require_cl_export` is called by `export_recheck.py:46` and `cli.py:1850`, and tested at
`test_w9_evidence_acceptance.py:296,400`; none is in P-090's boundary ("Nothing else under `research_system/`
changes"). A required second parameter breaks them. Note section 8.3 (line 890) leaves the validator in
`tools/_w9_detector_evidence.py` or `evidence.py`; the amendment's own preamble says it will not fill in what the note
leaves to the code task. Also: the note's list entries use the key `ordinal` (lines 899, 907), not `row_ordinal` (the
export's row key, `segmentation.py:408`); and "Its entries have the same five fields as `ACCEPTED_CL_EXPORT`'s" is wrong
for the entry shape, since an `ACCEPTED_CL_EXPORT` entry is three members of five fields each
(`accepted_w9.py:86-87`), while a classification entry is one flat five-field descriptor (note line 788).
Proposed text: "WP9.5 adds a separate `require_cl_classified_list(classified, export)`; `require_cl_export` is unchanged.
Whether it lives in `evidence.py` or `tools/_w9_detector_evidence.py` is a code-task choice; the second needs no WP9.3
change." Disposition: fix now.

**A-m5 [section 1.1, A1] The matching rule is sound; four details need stating.**
(a) The amendment makes the `role` and `source_identity_kind` equality unconditional and adds "more than one matching
entry is malformed". The note (section 5.3 item 3) says "when present on `registration`", and puts uniqueness at
export time. Both additions are stricter and correct (the store already forbids two registrations on one root kind and
path, `reducers.py:540-585`, and the schema requires both fields), but they are additions; say they are deliberate.
(b) "LR-015's meaning is unchanged" is not literally true: a manifest entry with the right triple and the wrong role
now refuses. (c) Tests that break, beyond the closed-key test at line 62: the `REGISTRATION` and `MANIFEST` constants
(`test_w9_evidence.py:28-29`), the positive case at line 34, and the refusal case at line 60. The harness and the two
WP9.4 builders key a manifest entry on path alone (`w9_runtime_harness.py:450-466`, the `manifest_paths` parameter at
`test_w9_wp9_4_1_runtime.py:92` and `test_w9_wp9_4_2_runtime.py:80`; 8 call sites). Role and kind are chosen at each
`register(path, role=, kind=)` call (`w9_runtime_harness.py:142-166`; 33 call sites in three of the files). The builder
must take role and kind from the registration it serves, not guess per path. Add negative controls for a role
mismatch, a kind mismatch, and a duplicated triple. (d) Say the new manifest-entry tests are not read from the
store, so they certify the gate and not the exporter (the exporter's `--check` is the store-equals-manifest check).
Disposition: fix (a) and (b) in the text; (c) and (d) as code-task obligations.

**A-m6 [section 1 preamble, records] The preamble overclaims the boundary, and the records scope is narrower than
the files that change.**
(a) "P-090's boundary allows exactly these changes ... and the test builders A1 names". P-090 names only "the WP9.3 and
WP9.4 test builders A1 names". D3's test files (`test_w9_evidence_acceptance.py`, `test_w9_wp9_3_2_runtime.py`) and E1's
integration cases are not A1-named. P-089's boundary covers "its tests", and note section 16.5 lists D3's test files
under "Records", so this is likely fine, but the sentence should cite those two sources and ask Stephen to confirm.
(b) The "protected set" parenthetical omits `IMPORTER_MODULES` and the census and T2 identities that note section 2.2
lists; section 1.4 does address `IMPORTER_MODULES`. (c) P-090 A re-records "both WP9.4 integration files". The WP9.4-1
record also cites unit counts that A1 and E1 change: `test_w9_evidence.py: 9 passed` and
`test_w9_evidence_acceptance.py: 38 passed` (`wp9-4-1-record.md:110,127,128`), and `test_w9_wp9_3_runtime.py` plus
`test_w9_wp9_3_2_runtime.py: 42 passed` (`:129`). State whether those are re-recorded or left as historical, and
append a dated re-record to the two WP9.4 records rather than overwrite the original counts. (d) Citation: the
`git_tracked` requirement is `acceptance.py:133-134`, not 132-133. Disposition: fix.

**A-m7 [section 2, H1] (d) has no reviewed-PR condition and no writer-class home.**
(a) W9 4.2 item 2, which the amendment leaves "unchanged", prohibits "any unreviewed write, including a direct push
with no PR". Note section 6.5 Rule 1's H1 branch passes a qualifying append without a mapped `pr_number`; every other
Rule 1 branch requires one. A qualifying append that arrives with no PR would pass the detector silently. The server
ruleset blocks a direct push, but (d) should still say "through a reviewed pull request" so item 2 and (d) agree.
(b) The registration schema's `writer_classes` is a closed enum, and for `legacy_owned` roles it is exactly 4.2 (a) to
(c) (`tools/w9_schema_gen.py:327,452`; W9 5.2 line 242, "writer classes (4.2)"). (d) is not representable there. Say that
(d) is a detector-side carve-out, adds no writer class, and changes no pinned W9 schema (so no D-4 consequence).
(c) Say which segmenter ("the segmenter" is both `segmentation.py` and `tools/w9_segmentation.py`; note 7.2 requires them
to agree). Disposition: fix now.

**A-m8 [section 2, H1] (d) has no end, against W9 13.3 item 4.**
W9 13.3 item 4 plans a Stephen-recorded "writer revocation": sessions stop writing Working Notes to `.apm/tracker.md`,
"the 4.4 detector watches the path". After the revocation, (d) and the note's unconditional H1 branch still pass a
qualifying append, so the detector goes blind on that path when it matters. P-090 H has no sunset, so this is an
**owner-decision gap**, not an error in transcription. Disposition: defer with dependency. Record, as an obligation on
the revocation record, that it must end (d) and name the mechanism (a code constant flipped by a pin advance is the
smallest). The code brief should not implement the H1 branch as unconditional without Stephen choosing.

**A-m9 [section 3, I1] The proposed `CONVENTIONS.md` text claims more than I1 decided or the tests can enforce.**
(a) "A new file in the detector's import closure must be added to CODEOWNERS and to the test's detector list." Of the
15 existing closure modules, 13 are deliberately not code-owned (`evidence.py`, `reader.py`, `segmentation.py`,
`canonical.py`, the `store/` modules and others; note 6.2.3, 16.1; the amendment's own list omits them). P-090 item 1
says an edit to such a module without a new row "is not a violation", and the note's closure test is scoped to the
assembled tree. As written, an agent adding a helper that `evidence.py` imports is told to code-own it; no test
requires it and the other 13 are not. Restate: "A new `tools/` file in the detector's import closure must be added to
CODEOWNERS and to the test's detector list (`test_derived_closure_tools_and_accepted_w9_are_codeowned`). Other closure
modules are pinned, not owned (P-090 item 1)." Similarly "A PR could otherwise change the detector that judges it" is
true only for the owned files; the pinned run is the independent check for the rest.
(b) The bullet runs from line 713 to 758, not 729 (the next bullet starts at 759). The edits are confined to paragraphs
1 and 3, so the instruction is workable, but "the bullet at lines 713 to 729" (P-090 and the amendment) is paragraphs 1
to 3 of a longer bullet.
(c) Convention locks end with a decision and lock date (line 758; the heading style "locked ..., amended ..."). The
After text should end the changed paragraph with "Amended 2026-11-23 by P-090 item 2 (Option I1)" or the code PR's
date.
(d) The next bullet (lines 759 to 771) rests on bypasses being rare: "While bypasses stay the exception", the bypass audit
"declined, since bypasses are rare again", "kept for the gate-file edits above". I1 makes a weekly bypass routine.
Change "stay the exception" to say that W9 evidence PRs are expected bypasses carrying a `Bypass reason:` line, so the
weekly review (`tools/check_bypass_merges.py:41,135`) is not read as an anomaly list.
(e) "Every PR that changes a shared surface" also needs a bypass under I1, because it must edit the code-owned list.
"Evidence PR" in the accepted-cost sentence should say so.
Timing: applying the text in the code PR, not now, is right. The sentence "Since P-090 it also owns ..." would be false
until CODEOWNERS and the tests change, and the bullet describes what those tests enforce. The section is successor
(W9 7.3 item 1 names "ARS Foundation Governance" successor), so the legacy-lock check is unaffected. Disposition: fix
(a) to (e) in the text.

**A-m10 [section 4, addendum rows] One row is missing and three conventions of the addendum are not followed.**
(a) J1 introduces `w9-cl-classified-list/1` and its file, but there is no row, and row 29 ("Computational-Log export and
its retained copy ... file name not yet fixed", addendum line 29) is not listed as changed. Note section 8.3 line 922
fixes "the three paths" at L-0b. Add a row or a change to row 29 naming the classified list and its format.
(b) The addendum's table has a "06v reference" column the section 4 table drops; the code PR needs the references
(O-9, O-32, D-5, M-6).
(c) The addendum's header says it "changes no requirement of 06v" and "Amends: Nothing" (lines 6 to 7). The W9-T7 lane
note changes 06v line 230's lane. The code PR must amend those two cells, or P-090's own text (item 3) conflicts with
the addendum's status.
(d) The addendum's practice for a changed row is a dated "Amendments" entry that records the old cells (lines 48 to
58). Say the code PR does that for the two changed rows, and re-cites the `evidence.py` line numbers it moves.
Disposition: fix (a); (b) to (d) as code-task obligations.

### Info

- **A-i1.** Section 2's evidence reproduces. On `452352ff`, `e3519ba7` and `a6a98966` the runtime segmenter gives 95
  identical `tracker_task_row` rows, 0 blockers, working-note counts 112 to 113, 113 to 114, 114 to 115, every earlier
  note a subsequence of the later set, and `git diff --numstat` shows 26, 29 and 43 added lines with 0 deleted. The
  tracker's last section is `## Working Notes` (line 148).
- **A-i2.** P-090 D requires a Rule 3 acknowledgement to carry "a non-empty `affected_registrations`". Note
  6.2.2 item 3.4 allows an empty list with "none derived" in both slice and review. The amendment is silent (the gate
  keeps `[]` permitted, `evidence.py:236`). The WP9.5 detector brief should settle which governs.
- **A-i3.** D3 keeps `git_tracked` as a condition (`acceptance.py:133-134`). Its reason, "cannot be ordered against a
  commit" (WP9.3 note 10.4), no longer applies under a tree-state test; the behaviour is kept conservatively, which is
  right. No change.
- **A-i4.** The 7-day window is measured from the operator's run, not the binding advance, so the PR merge and
  `advance-binding` latency eats into it. This is inside the cost Stephen accepted (P-090 E).
- **A-i5.** No D-4 or `IMPORTER_MODULES` touch found. `reader.py` is only read (`accepted_cl_export`, and `clock` if
  used). The 06h append-site scan lists one legacy module, `research_system/legacy/runtime.py`
  (`wp6_1_06h_current_append_manifest.yaml:41`), and none of the four files changed here appends to a ledger. I did not
  run the 275-row census test.
- **A-i6.** `store/governed_code.py:60-70` classifies every `.research-system/**` file as governed
  `operational_config` and every `research_system/**/*.py` as governed code. Each evidence PR is therefore a
  governed-code change that needs `advance-binding`, which matches E1's stated cost. The code brief should carry this
  so no one reads the weekly cycle as a one-PR step.
- **A-i7.** Currency: `main` is `4ca375a3`; between `dbd54fe3` and `origin/main` the only difference under
  `research_system`, `tests`, `tools`, `.github` and `CONVENTIONS.md` is three lines of `citations.py`. No addendum is
  needed.

## 4. Per-section reading, in brief

**1.1 A1.** Faithful to P-090 A and note 5.3, 16.3. Verified: closed three-key check (`evidence.py:124-127`), membership
at `:128-130`, the call at `preparers.py:1215-1218`, the enums at schema lines 70 to 94. The gate cannot reach a
registration whose role the store holds differently, because the equality check is against the replayed record. A
mislabelled manifest entry for a never-observed registration is not caught at LR-015; the exporter's `--check` and
review under I1 catch it (human-review, as note HR-7).

**1.2 D3.** Faithful in its format and in keeping `require_change_list` unchanged. The tree-state test is sound for one
entry per surface. It is unsound as worded for several (A-M1). A surface absent at the observation commit returns
`None` (`evidence.py:186-187`) and refuses, which is the right direction; the message is "predates", which is
misleading for a surface not yet created (cosmetic).

**1.3 E1.** Faithful to P-090 E and note 8.4. The four call sites are right. Inert-before-L-0b is correct: no test
builds a reader with a non-empty export (the only `accepted_cl_export=` in tests is the replay driver,
`test_w9_wp9_4_2_replay.py:1462,1536`), and `LegacyRuntime` defaults to the code constant (`runtime.py:303-305`).
Deleting the file cannot disable the check once the constant is non-empty, because the read is at `git_head` and an
absent file raises.

**1.4 J1.** Faithful to P-090 J on the two constants and on pairing the L-0b PR with a pin advance. Placement and the
`require_cl_export` sentence are the problem (A-m4).

**2 H1.** Faithful to P-090 H and note 6.5 (the blocker and separator conditions come from the note). Evidence verified.
Gaps are in how (d) sits against 4.2 items 2 and 13.3 (A-m7, A-m8).

**3 I1.** Quotes of "Now" are verbatim (`CONVENTIONS.md:713` and `:727-729`). The list matches P-090 and the note's
eleven files plus the directory. Findings are about what the sentences claim (A-m9).

**4 rows.** Complete for the evidence files the note adds except the classified list (A-m10). The `detector-controls.json`
row needs no change.

## 5. Decision audit (P-090 item 3 and the owner points the amendment touches)

| Item | Disposition |
|---|---|
| Item 3, WP9.3 amendment for A1, D3, E1 | Covered by section 1; D3 needs A-M1. J1 is added to it, as P-090's boundary requires. |
| Item 3, W9 4.2 amendment for H1 | Covered by section 2; A-m7, A-m8. |
| Item 3, `CONVENTIONS.md` amendment for I1 | Covered by section 3; apply in the code PR; A-m9. |
| Item 3, addendum rows and the W9-T7 lane | Covered by section 4; A-m10. |
| Owner point A (records re-recorded) | Covered; A-m6 (c). |
| Owner points B, C, F, G, K | Not WP9.3 gate changes; nothing in the amendment contradicts them. |
| Not decided by the amendment, correctly | CODEOWNERS file list and test restructuring, order of landing, exemption row design. |

## 6. Citations checked

- `evidence.py:40,42,114-131,179-188,190-218,221-252,277-362,347-358,446`; `acceptance.py:121-153`;
  `preparers.py:686-690,706,958-962,1029,1200-1218`; `accepted_w9.py:78-88`; `reader.py:42,209-240,286-340`;
  `segmentation.py:391-408`; `export_recheck.py:46`; `cli.py:1842-1858`.
- `legacy-path-registration.schema.json:54-94`; `tools/w9_schema_gen.py:327-333,452`; `reducers.py:540-585,631-634`.
- Tests: `test_w9_evidence.py:28-62`; `test_w9_evidence_acceptance.py:54-164,296,400`;
  `test_w9_wp9_3_2_runtime.py:365-430`; `w9_runtime_harness.py:142-166,430-476`;
  `test_w9_wp9_4_1_runtime.py:87-115`; `test_w9_wp9_4_2_runtime.py:76-105`.
- `CONVENTIONS.md:696-782` and `:614,784`; `.github/CODEOWNERS:1-24`; `test_ci_platform_policy.py:340-375`;
  `tools/check_bypass_merges.py:41,135`; `.claude/hooks/admin-bypass-guard.sh:13-18`.
- 06v lines 90 to 91, 230, 566, 567; W9 lines 157 to 200, 242, 379 to 417, 639 to 662; note sections listed in the
  table above; P-090 lines 6147 to 6261; WP9.4-1 record lines 110 to 130.
- Off by one: `acceptance.py:132-133` is `:133-134`. All other cited lines in the amendment resolved.

## 7. Commands run (all read-only)

- `git show dbd54fe3:<path> | cat -n` for the files above; `git grep -n ... dbd54fe3 -- <paths>` for callers of
  `check_environment`, `require_cl_export`, `require_registered`, `require_change_list`, `accepted_cl_export`,
  `accepted_w9`, `manifest_paths`, `writer_classes`; `git diff --stat dbd54fe3 HEAD` and `dbd54fe3 origin/main`;
  `git diff --quiet dbd54fe3 HEAD -- CONVENTIONS.md .github/CODEOWNERS tests/tools/test_ci_platform_policy.py`;
  `git log`, `git rev-parse`, `git diff --numstat` on `.apm/tracker.md` commits.
- Scratch scripts in the session scratchpad (outside the repository): `h1_check.py` (runs
  `research_system.legacy.segmentation.segment` on `git show` bytes of three tracker commits) and `d3_later.py` (a
  twelve-line model of the two readings of "later"). Neither writes to the repository. No tests were run; no `gh` call
  was made; no vault file was read.

## 8. Not verified

- The 275-row census and the 06h smoke test were not run; the no-D-4 conclusion rests on reading the append-site scan
  and the four files.
- Whether the live ruleset enforces code-owner review as the note records (I relied on the r2 review's GET).
- `git_tracked` observation commits other than the binding head (the `legacy_decision_log_entry` and `conventions_lock`
  roles read at pinned old commits, `reader.py:306-327`) under D3's tree-state test. Neither is expected to be an
  "affected registration"; I did not confirm that.
- The exact set of tests E1 and D3 will add; the amendment does not fix it.

## 9. Revision plan

**Immediate (author, no owner decision):** A-M1; A-m1; A-m2; A-m3 (a) to (d); A-m4; A-m5 (a), (b); A-m6; A-m7;
A-m9; A-m10 (a).

**Owner decision:** A-m8 (whether and how H1 ends; the smallest mechanism is a code constant).

**Code-task obligations to carry into the brief:** A-m5 (c), (d); A-m3 (e); A-m10 (b) to (d); A-i2; A-i6.

**Change log:** none; no file other than this report was written to the repository.
