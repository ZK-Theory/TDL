# Follow-up 2: WP9.5 design note, revision 3

For: the Gemini agent that wrote revisions 1 and 2 of the WP9.5 design note. Written by the reviewing Claude session
on 2026-11-21.

A second fresh reviewer attacked revision 2 (`0c9a90ed`). The verdict is **REWORK REQUIRED**: 0 Blocking, 5 Major,
16 Minor and 6 Info. The report is committed on your branch at
`docs/plans/agentic-research-system/reviews/wp9-5-note-r2-review-2026-11-21.md` (`3cf35bec`). Read all of it before
you change anything.

Revision 2 is a large improvement, and the reviewer says revision 3 "should be short". About 170 of roughly 175
citations resolve (wrong citations fell from about half to about 3 percent). The reviewer reproduced the first-parent
facts, all 20 PR-to-`merge_commit_sha` mappings, the `CONVENTIONS.md` unit counts, the ruleset pins and the clone
timings. Time-indexing the evidence (manifest at `P1`, records at `C`) and Rule 0 close three of R1-B1's five
scenarios. Owner Point H1 passed a test against the three real tracker commits. Keep all of that. The review's §5
lists what was checked and found sound; do not rework those parts.

Same worktree (`C:\Users\steph\TDL\.apm\worktrees\wp9-5-note`), same branch (`docs/w9-wp9-5-design-note`), same rules
as the handover (`handoffs/wp9-5-gemini-note-handover-2026-11-21.md` §4). Before any write, confirm the branch, that
HEAD is `3cf35bec`, and that `git status --short` is clean.

## 1. The rule still holds: nothing unverified, and no overclaim

The rule from follow-up 1 §1 still applies in full. The review found six wrong citations and invented names that
revision 2's header and §18 said were verified (R2-m2, R2-m3, R2-m4). For revision 3:

1. **The header and §18 must not say "every" anything was verified** unless it was. Say what you checked, how, and
   what you did not check.
2. **Take field names, constant sizes and signatures from the code, not from memory.** The `segment()` row keys are
   `row_ordinal` (starting at 1), `row_kind`, `anchor_text`, `start_byte`, `byte_length`, `start_line`, `line_count`,
   `raw_row_sha256`, `anchor_line_sha256` and `blocker_reason`, plus `unit_ordinal` and `unit_hash` for
   `conventions_unit` (`research_system/legacy/segmentation.py:391-425`). Check any others you use the same way.
3. **Every verification claim must be reproducible from the note.** Revision 2 cites `verify_r2.py` and
   `verify_more.py`, which are not in the repository. In the Verification appendix, give the exact command or the
   script's full text for each figure, or cite the r2 review where it reproduced the figure.
4. **Read-only `gh api` GETs** are allowed only for `repos/ZK-Theory/TDL/rulesets/...`, `rule-suites`,
   `commits/<sha>/pulls` and `pulls/<n>`. Nothing else on GitHub. Do not run the U-3 probe or the U-4 dry run, and
   never read vault file contents.

## 2. What to change

Work through the review's §7 revision plan. In order:

1. **R2-M1: the detector's own integrity.** State plainly in §6.1 that no trust root inside repository content can
   protect the detector from a merged commit, and that the preventive control is code-owner review (Owner Point I).
   Then fix the mechanism:
   - the workflow, not the tool, must run the detector from a pinned tree. Specify the step (for example
     `git worktree add "$RUNNER_TEMP/w9-detector" <pinned-sha>` and run from there) and where the pinned SHA comes
     from. Delete the "when `walk-baseline.json` is present at `<baseline>`" condition, which can never fire;
   - say which `walk-baseline.json` entry fixes the walk start and which pins the tool. The review suggests
     `baselines[0]` for the start and the last entry for the tool; check that against R2-M2's design before you
     adopt it;
   - hash-bind every decision reference, as §6.4 already does: `{"id": "P-0xx", "entry_sha256": ...}`. That covers
     `recorded_in_decision_ref` and the top-level `d8_rule_suites_limit_decision_ref`. Put every top-level field of
     `walk-baseline.json` under Rule 0;
   - remove the `baseline_commit` and `head_commit` dispatch inputs, or make the tool exit 2 on `--baseline` or
     `--head` unless `--ruleset-check skip` is also given. Extend the test that checks the workflow's arguments to
     cover `--baseline`, `--head`, `--pr-map` and `--manifest-file`;
   - correct MC-2 and claim 2 so they claim only what the mechanism gives.
2. **R2-M2: a true positive must be clearable, and a tool change must not silently re-judge history.** Design an
   append-only acknowledged-violation list. The review proposes rows of `{commit, rule, path, old_blob, new_blob,
   disposition_ref}`, each valid only if its decision entry was committed after `commit`. Also design a checkpoint,
   so that a tool change re-evaluates only new commits unless the owner asks for a full re-walk, and a full re-walk
   is reported as a diff of verdicts. Say where the checkpoint lives and what protects it (Rule 0, Owner Point I).
   Put the form to Stephen under Owner Point C.
3. **R2-M3: the detector's import closure.** The tools import `research_system.legacy.reader`, `.evidence` and
   `.segmentation`, `research_system.canonical` and `tools.w9_segmentation`. None is pinned or code-owned. Specify:
   - a script that derives the transitive closure (an AST walk over the tools and helper);
   - the closure recorded with a blob per module;
   - a unit test that the recorded list is a superset of the computed closure;
   - and either running from the pinned whole tree (R2-M1) or adding the closure to Rule 0 and the Owner Point I list.

   Check the import list against the code; the review's list is a starting point.
4. **R2-M4: pin the `CONVENTIONS.md` classification** the way `ACCEPTED_CL_EXPORT` pins the vault list
   (`research_system/legacy/accepted_w9.py:86-88`):
   - an accepted code constant holding `{repository_path, git_commit, git_blob, sha256}`, set by the L-0b PR;
   - the checker reads that blob at that commit, never the head;
   - the workflow passes no `--classified-locks`;
   - the file is under Rule 0;
   - a new negative control N7: reclassify a legacy unit in a byte copy, and the check must still fail.

   Key the classification on `(anchor_text, unit_hash)`, the real row key.
5. **R2-M5: rewrite Owner Point I.**
   - I1 as written adds a directory to `GATE_FILES`. That fails `test_every_gate_file_exists_and_has_a_code_owner`,
     which requires `.is_file()` (`tests/tools/test_ci_platform_policy.py:364-369`). Listing the evidence files one
     by one fails before L-1, because the tripwire says they must not exist yet.
   - Give the exact edits: CODEOWNERS patterns; the changes to that test and to
     `test_codeowners_names_no_file_outside_the_gate` (`:372-374`) and its docstring; the `CONVENTIONS.md` bullet
     at 713-729 (not 721-723).
   - Say this reverses a recorded scope decision (the CODEOWNERS list is the merge-admission gate only) and needs
     Stephen's decision in P-090.
   - State the cost: every manifest, vault-run and ruleset-read PR becomes a merge only Stephen can make.
   - State that under I2 the L-1 activation PR is unguarded and R1-B1 stays open, and add
     `tests/tools/test_w9_detectors.py` to I1 if the tripwire must resist tampering.
   - If you give an option for a second anchor that does not depend on a human merge (a protected tag or a
     repository variable holding the pinned SHA and tool blobs, set by Stephen at L-1), add it as its own option
     under I. Say exactly how the workflow reads it, and what it costs.
6. **R2-m1 to R2-m16.** In particular:
   - the inventory has 22 commits, not 20; add `14a81b84` (#419) and `1fba78aa` (#425), and correct "8
     CONVENTIONS.md PRs" to 9 everywhere (R2-m1);
   - `LEGACY_COMMAND_TYPES` is at `research_system/legacy/commands.py:16` with 12 members; `contracts.py` does not
     exist (R2-m2);
   - the segment field names, and 1-based ordinals in the classified-list example (R2-m3);
   - the six wrong citations (R2-m4);
   - the YAML: forward slashes in `.venv/Scripts/python.exe` under `shell: bash`; no `grep -q` under `pipefail`
     (use `grep -x` to a file or count matches); steps for `--ruleset-check ci-d8` and `--verify-watched-to-fail`;
     a branch filter on the L-1 `push` trigger (R2-m5);
   - the U-3 probe records which pinned keys are present in each body, and states the probe PR's side effects
     (R2-m6);
   - the U-4 dry run as a scratch script file for the reviewing session, not `python -c`, with its working directory
     stated and no `KeyError` on a blocker (R2-m7);
   - `GIT_CONFIG_GLOBAL` and the `-c` settings for deterministic controls, and drop "bit-for-bit identical across
     machines" unless you can evidence it (R2-m8);
   - `recheck_cl_export` returns a report and does not raise on divergence, so `report["void"] is True` must be a
     closed failure (R2-m12, `research_system/legacy/export_recheck.py:80-89`);
   - `baseline_commit` cannot be "the L-1 parent", which is unknowable under the merge queue; allow any first-parent
     ancestor of the L-1 commit, with every guarded commit between it and L-1 disposed (R2-m14);
   - #368 (`452352ff`) records Phase 5 batches, not a worktree sweep; correct claim 5 and the H row (R2-m15);
   - the rest (R2-m9 to R2-m11, R2-m13, R2-m16) as the review states them. For R2-m13, make profiling one
     scratch-store test a pre-code step and keep Owner Point G's recommendation at G1 until that is done.
7. **R2-i1 to R2-i6.** Say what you did with each; add HR-6 for R2-i2.

## 3. Owner points

Put them to Stephen; do not decide them. Keep A to J. Change them as the review's §4 says. The main changes:
- **I** comes first, since B, C and the L-1 guard depend on it;
- **C** carries the acknowledged-violation form from R2-M2;
- **J** carries the `CONVENTIONS.md` classification pin;
- **B** is stated as conditional on I1 (R2-m10 (c));
- **A** says whether A1 needs a dated WP9.3 amendment, as D3 and E1 do (R2-m11 (d)). It also picks one policy for
  format strings: keep `w9-registration-manifest/1` or move to `/2` (R2-m11 (c)).

## 4. The change log

Add a section "Change log: revision 2 to revision 3" after §18. List every R2 finding ID, with what changed and
where, or why it was not taken. Renumber the Verification appendix after it. Keep §17 and §18.

## 5. What to hand back

1. **Status** first, on its own line: `COMPLETE` or `PARTIAL - <exact gap>`.
2. Whether you committed (subject `[PIPELINE] P06: WP9.5 design note revision 3`, via `git commit -F` with a UTF-8
   file without a byte-order mark), the new HEAD, and `git status --short`.
3. For each R2 finding ID: what changed, with the section.
4. Owner points A to J, one line each, with your recommendation.
5. The Verification appendix's summary: what you ran, and every statement you marked UNVERIFIED.

Do not describe the note as reviewed or accepted. It goes to a third independent review next.
