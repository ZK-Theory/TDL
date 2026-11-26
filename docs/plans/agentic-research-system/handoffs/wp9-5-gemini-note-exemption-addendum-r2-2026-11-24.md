# Follow-up 9: WP9.5 design note, the exemption-row addendum, revision 2

For: the Gemini agent that wrote the Rule 0 exemption-row addendum (`b3500098`). Written by the reviewing Claude
session on 2026-11-24.

A fresh reviewer attacked the addendum. The verdict is **REWORK REQUIRED**: 0 Blocking, 2 Major, 7 Minor and 7 Info.
The rework is narrow and additive. The report is on the amendments branch (PR #451), at
`docs/plans/agentic-research-system/reviews/wp9-5-note-exemption-addendum-review-2026-11-24.md`. Read it with
`git show origin/docs/w9-wp9-5-amendments:docs/plans/agentic-research-system/reviews/wp9-5-note-exemption-addendum-review-2026-11-24.md`.

The reviewer confirmed what holds:
- forgery by ordering fails;
- `null` handling for creation and deletion is correct;
- the pinned-copy rule is consistent;
- the sections you said you left untouched are untouched.

Keep all of that.

Stephen has since decided the review's owner questions. They are **P-090 item 5** in
`03-decisions-and-open-questions.md` on your branch:
1. **Any PR that appends a `rule0_exemptions` row carries a pre-merge run** of the pinned tool against its candidate
   (`--head <candidate>`), attached to the PR, showing that the row validates. **A later row cannot clear a validity
   fault in an earlier one.** Do not add a `rule0_exemptions[k]` location.
2. **`walk-baseline.json` changes format only by a new file path**, as your addendum already says.
3. **`d8_rule_suites_limit_decision_ref` stays unexemptable**, its first transition included. The L-1 PR gets a
   pre-merge `--head <candidate>` run.
4. (For W9 §4.2 (d), not this addendum: H1's carve-out ends at the writer revocation.)

Same worktree (`C:\Users\steph\TDL\.apm\worktrees\wp9-5-note`), same branch (`docs/w9-wp9-5-design-note`). It now
includes a merge from `main`, the CodeRabbit fixes and P-090 item 5. Before any write, confirm the branch, that HEAD is
`813088e9`, and that `git status --short` is clean.

## 1. What to change

Use the review's proposed text for each item, adjusted only where the code at `dbd54fe3` requires it, and log any
departure.

1. **X-M1, malformed intermediate versions.** Add the review's three sentences to §6.5.1 item 4 and §6.6 item 1:
   - **Malformed intermediates.** When an evidence file fails parsing or schema validation at `P1` or `C`, Rule 0.2's
     append-only and immutability comparisons, including every unexemptable invariant, run on raw reads between the
     nearest earlier version that parses and the first later version that parses. A violation found there is reported
     at the commit that produced the later version, and no row clears it. A `"$"` row clears only the schema fault.
   - **A parse or unknown-format failure at a commit other than `<head>`** is a `Rule 0.2` fault at that commit,
     with location `"$"`, exit 1, and exemptable. At `<head>` it stays exit 2.
   - **A pin that replaces an evidence format in place** keeps the superseded reader for as long as the walk covers the
     superseded versions.

   Add the review's three controls:
   - X adds a stray key, F removes it and rewrites `baselines[0].baseline_commit`, with rows for both X and F: exit 1 at
     F;
   - a conflict marker at X, fixed at F, with rows for both: exit 0;
   - a pin that drops the old reader: exit 2.
2. **X-M2, an invalid row is unrecoverable.** Write Stephen's decision 1 into §6.5.1 item 3 as a required step. Use the
   review's text: the PR description carries the step 4 command's output showing no new `Rule 0.2` fault at
   `<candidate>`, and the slice's SHA-256 is recomputed against `<pr_base>` after the last rebase. Add to HR-3 that a
   row which still lands invalid, by bypass or a race, is recoverable only by a re-baseline at a new path, which is not
   designed here.
3. **X-m1:** `fp_index[b0] = -1`, and a row whose violating commit's first parent is `b0` is invalid. Say the rule is
   "stricter than" `is_ancestor`, not "consistent with" it.
4. **X-m2 (a):** add the failed check to the location, for example `baselines[3]#iii`, so one row clears one fault,
   not a whole fault site. Add a sibling-sub-check control. X-m2 (b) and (c) go to the code task (step 9).
5. **X-m3:** correct the `format` rationale. §10.2 does not read `format`; its unexemptability rests on §6.6 item 1
   alone.
6. **X-m4:** in §6.2.2 step 6, "never the same commit" becomes "never the same commit as the violation".
7. **X-m5:**
   - reword "moves by a new file path, or by a hash-bound exemption row ... not in place" to "never in place without a
     cleared Rule 0 fault";
   - note that `walk-baseline.json` is narrowed by Stephen's decision 2;
   - for deleted-then-restored files, either require the deletion row's register line to name the restoring commit
     and blob, or state the laundering risk in HR-3. Say which you chose.
8. **X-m7:** fix "non-empty `[]`", the §16 intro and §15.1 item 3 (which still say the owner points are undecided), and
   the "(not yet reviewed)" label. Write d8 as decided (Stephen's decision 3).
9. **X-m6, controls.** Rebuild the controls row in §12.1 as the review's §4 table says:
   - one guard per control, each on an otherwise-valid row;
   - the paired no-row run for the positive control;
   - a constructible replacement for the same-commit control;
   - the deletion fixture fixed;
   - the six missing controls added.

   Name X-m2 (b, c), X-i5 and X-i7 as code-task obligations in §15.3.
10. **X-i2:** one output line per cleared tuple, naming the row index. **X-i1, X-i3, X-i4:** one sentence each in
    HR-3 or §6.5.1.

## 2. Scope rules

1. Add only what §1 names. No new mechanism, and no `rule0_exemptions[k]` location.
2. Keep it compact, and report bytes and lines before and after.
3. Nothing unverified, and no overclaim. Follow-ups 1 to 8 still apply.
4. Do not touch §4.2.2, §4.3.3, §10.2, §10.3, §15.1's recorded results or §21. Read-only `gh api` GETs only, and never
   read vault file contents.
5. Add a compact "Change log: exemption-row addendum, revision 2" entry, listing each X finding ID with what changed
   and where.

## 3. What to hand back

1. **Status** first, on its own line: `COMPLETE` or `PARTIAL - <exact gap>`.
2. Whether you committed (subject `[PIPELINE] P06: WP9.5 design note, exemption-row addendum revision 2`, via
   `git commit -F`, UTF-8 without a byte-order mark), the new HEAD, and `git status --short`. Do not push.
3. Bytes and lines before and after.
4. For each X finding ID: what changed, with the section, and any departure from the review's text.

Do not describe the addendum as reviewed or accepted. A focused review follows.
