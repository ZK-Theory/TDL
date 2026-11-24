# Follow-up 3: WP9.5 design note, revision 4

For: the Gemini agent that wrote revisions 1 to 3 of the WP9.5 design note. Written by the reviewing Claude session
on 2026-11-22.

A third fresh reviewer attacked revision 3 (`092db1f1`). The verdict is **REWORK REQUIRED**: 0 Blocking, 3 Major, 13
Minor and 4 Info. The report is committed on your branch at
`docs/plans/agentic-research-system/reviews/wp9-5-note-r3-review-2026-11-21.md` (`1bd4ecff`). Read all of it before
you change anything.

The facts are now right. The reviewer reproduced every number it could check:
- the 22-row first-parent table;
- the 15 / 20 / 22 import closure, with all 13 recorded blobs;
- the `CONVENTIONS.md` counts;
- 16 of 16 live ruleset pins.

Both YAML blocks parse, and the U-4 script ran cleanly against a synthetic vault. About 253 citations resolve and 2
are wrong. The review's §6 lists what was found sound; do not rework it.

All three Major findings are in mechanisms revision 3 added: the pin-advance protocol, checkpoints, and Rule 3
acknowledgements. Each round so far has fixed the last round's Majors by adding machinery, and the new machinery has
carried the next round's Majors. So revision 4 is narrow, and §1 below sets how narrow.

Same worktree (`C:\Users\steph\TDL\.apm\worktrees\wp9-5-note`), same branch (`docs/w9-wp9-5-design-note`), same rules
as the handover (`handoffs/wp9-5-gemini-note-handover-2026-11-21.md` §4) and follow-ups 1 and 2. Before any write,
confirm the branch, that HEAD is `1bd4ecff`, and that `git status --short` is clean.

## 1. Scope rules for this revision

1. **Add no new mechanism** beyond what §2 prescribes. If you think a finding needs something else, say so in the
   change log and leave it for the reviewer and Stephen; do not build it.
2. **Delete superseded text; do not layer.** Where revision 4 replaces a mechanism (the commit pin, the checkpoints),
   remove the old text from §1 to §17 and keep its history only in the change logs. The note must not describe two
   designs for the same thing.
3. **Nothing unverified, and no overclaim.** Follow-up 1 §1 and follow-up 2 §1 still apply. In particular, do not say
   a figure was reproduced by a review unless that review reproduced it (R3-m7 (c)).
4. Read-only `gh api` GETs only, for the same endpoints as before. Do not run the U-3 probe or the U-4 dry run, and
   never read vault file contents.

## 2. What to change

1. **R3-M1: pin the detector by content, not by commit.** Take the review's form (A):
   - replace `tool_pin_commit` with the recorded blob map (`detector_closure_blobs`) plus the `pyproject.toml` and
     `uv.lock` blobs;
   - the workflow assembles `$RUNNER_TEMP/w9-detector` with `git cat-file blob <recorded blob>` for each recorded
     path, then runs `uv sync --locked` there. A same-PR row is satisfiable because blob ids are content hashes. An
     import outside the recorded closure fails with `ImportError`, so the closure must be exact. Say how package
     `__init__.py` files are included;
   - add to Rule 0.2 a validation of every appended `baselines` row: its blobs equal the head's blobs for those paths
     at the commit that appends it; its decision reference is hash-bound and resolves at `P1`; and the slice names
     every path whose blob differs from the previous row, with `new_blob[:8]`. A row that changes no blob, or that
     restores an older blob map, must name that in its slice too;
   - add the positive control (a closure edit with its row in the same PR ends green), and negative controls for a
     row with no decision reference, a row whose slice omits a changed path, and a rollback row not named in the
     slice;
   - reword MC-2, note 714 and claim 2: preventive for code-owned paths, detective for the rest.

   If you find form (A) cannot work, stop. Say why in the change log, and use form (B) as the review states it.
2. **R3-M2: remove checkpoints.** Every run re-walks from `baselines[0]["baseline_commit"]` with the pinned tool.
   Delete `checkpoints`, `--record-checkpoint` and `--full-rewalk`. To keep R2-M2 (b), so that a tool change cannot
   silently re-judge history:
   - for each `baselines` row after the first, the detector also assembles the previous row's tool and walks the
     commits before that row with both tools;
   - any commit whose verdict differs must be named in the row's decision slice, or the run fails with
     `ERROR: Rule 0: pin advance changes verdicts`;
   - this is recomputed on every run, and no stored verdict is trusted;
   - add the negative control: a pin advance that turns a red commit green, not named in the slice, fails;
   - state the cost. Measure one full walk of `4b143c92..dbd54fe3` with a stand-in for the walk loop if no tool
     exists yet, or mark the cost UNVERIFIED and add it to §15.1.
3. **R3-M3: a Rule 3 acknowledgement needs the late change-list entry.** It is valid only if
   `shared-surface-changes.json` at head holds the entry for that change (`pr_number`, `surface`, `old_blob`,
   `new_blob`, `affected_registrations`). State why a late entry is safe: WP9.3 reads the list at the store's
   `git_head`. Add the control: an acknowledgement without the late entry fails.
4. **R3-m1 to R3-m13.** Each as the review states it. In particular:
   - I3: an empty `vars.W9_DETECTOR_PIN` is an error once I3 is chosen; cite who can write repository variables, or
     mark it UNVERIFIED (R3-m1). Under form (A), say what I3 pins: a blob-map digest, not a commit;
   - pin the operator-machine batch-gate runs too (a wrapper that runs from the assembled tree), and add
     `research_system/legacy/accepted_w9.py` to the I1 CODEOWNERS list (R3-m2);
   - state the cost of the closure rule, and give Stephen the option of narrowing the closure by moving the reader
     helpers the detectors use into `tools/` (R3-m3);
   - correct the integration-test lane for `tools/`-only PRs, or move the T7 replay under `tests/tools/` in
     `admission-controls` (R3-m4);
   - make §15.1 item 4 (the scratch-store profile) unconditional (R3-m5);
   - add the three §4.3.2 root checks to the U-4 script as printed booleans (R3-m6);
   - the two citation fixes, the provenance sentence in the header and §20.1, and "closure digest" (R3-m7);
   - compare only the checked-out branch's ref and the tag list in the snapshot, not the shared ref files (R3-m8);
   - complete the I1 edit list: the CODEOWNERS header, when the new paths exist relative to the test, no `is_dir()`
     on the directory pattern, and the `Bypass reason:` line in the cost (R3-m9);
   - fix the disposed and walked intervals, and give the refresh rule for the §6.2.1 table at L-1 (R3-m10);
   - a row schema and Rule 0 validation for `ruleset_gap_acknowledgements`, a positive test for
     `--acknowledge-gap`, and the D-8 gate test in §12.1 (R3-m11);
   - a unit test that runs the workflow's pin script against a scratch repository with synthetic rows, and a
     throwaway-PR rehearsal of the workflow before L-1 as for U-3 (R3-m12);
   - name the WP9.4 files Option A1 changes (`w9_runtime_harness.py:451-466`, `test_w9_wp9_4_1_runtime.py:95-109`,
     `test_w9_wp9_4_2_runtime.py:86-100`), and say whether that reopens WP9.4's review (R3-m13).
5. **R3-i1 to R3-i4.**
   - The tripwire test loads YAML with `yaml.BaseLoader` (R3-i1).
   - For R3-i2 (the `CONVENTIONS.md` check is not on pull requests although `06v:491-492` says "a CI job"), give
     Stephen the choice as a new Owner Point K: add it to `admission-controls`, or state why not.
   - Record R3-i3 and R3-i4.

## 3. Owner points

Put them to Stephen; do not decide them. Keep the order I first, then C, A, B, D, E, F, G, H, J, and add K
(R3-i2). Update I for the content pin, the closure cost and narrowing option, `accepted_w9.py`, and the I3 rule. Update
C for the removal of checkpoints. Update A for R3-m13.

## 4. The change log

Add a section "Change log: revision 3 to revision 4" after the revision 2 to 3 log. List every R3 finding ID, with
what changed and where, or why it was not taken. Renumber the Verification appendix after it.

## 5. What to hand back

1. **Status** first, on its own line: `COMPLETE` or `PARTIAL - <exact gap>`.
2. Whether you committed (subject `[PIPELINE] P06: WP9.5 design note revision 4`, via `git commit -F` with a UTF-8
   file without a byte-order mark), the new HEAD, and `git status --short`.
3. The note's line count before and after, and which sections you deleted text from.
4. For each R3 finding ID: what changed, with the section.
5. Owner points A to K, one line each, with your recommendation.
6. The Verification appendix's summary: what you ran, and every statement you marked UNVERIFIED.

Do not describe the note as reviewed or accepted. It goes to a fourth independent review next.
