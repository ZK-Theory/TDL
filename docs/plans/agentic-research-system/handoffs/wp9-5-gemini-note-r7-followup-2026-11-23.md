# Follow-up 6: WP9.5 design note, revision 7

For: the Gemini agent that wrote revisions 1 to 6 of the WP9.5 design note. Written by the reviewing Claude session
on 2026-11-23.

A sixth fresh reviewer attacked revision 6 (`95dfefe7`). The verdict is **REWORK REQUIRED**: 0 Blocking, 3 Major, 9
Minor and 6 Info. The report is committed on your branch at
`docs/plans/agentic-research-system/reviews/wp9-5-note-r6-review-2026-11-22.md` (`d47a8e72`). Read it before you
change anything.

Revision 6 carried out Stephen's pin decision. The reviewer found nothing showing that the decision cannot be
carried out, and filed no finding against it. Rule 0.3 and the PR-time gate are gone, the note shrank, and the
facts, citations, path confinement and isolation all reproduced.

The three Majors are places where the text does not yet do what the decision says. Each has a concrete fix, and the
review gives proposed text for all three. **Adopt the review's proposed text** for R6-M1, R6-M2 and R6-M3, adjusted
only where the code at `dbd54fe3` requires it. Say in the change log wherever you depart from it, and why.

Same worktree (`C:\Users\steph\TDL\.apm\worktrees\wp9-5-note`), same branch (`docs/w9-wp9-5-design-note`). Before any
write, confirm the branch, that HEAD is `d47a8e72`, and that `git status --short` is clean.

## 1. Scope rules

1. **Stephen's decision stands** (follow-up 5 §1). Do not reopen it, and add no mechanism beyond what this brief
   names.
2. **The note must not grow** beyond 237,726 bytes. Report bytes and lines before and after.
3. **Nothing unverified, and no overclaim.** Every figure for code that does not exist yet is labelled as an
   estimate. Every check the header lists must appear in §21.1 with enough detail to reproduce it (R6-m6).
4. Read-only `gh api` GETs only, for the same endpoints as before. Do not run the U-3 probe or the U-4 dry run, and
   never read vault file contents. Scratch work goes outside the repository.

## 2. The three Majors

1. **R6-M1: "fails loudly" must hold.**
   - An evidence file that cannot be parsed, or whose `format` the tool does not know, is `ERROR`: exit 2, and
     `--verdict-json` prints the `error` key.
   - Exit 1 is only for violations of Rules 0 to 3 on evidence the tool read.
   - Fix §6.6 item 1, the empty-`ACCEPTED_CL_EXPORT` case in §8.2, and HR-3 (a).
   - Add tests: an unknown `format` exits 2, and so does unparseable JSON.
   - Correct every restatement of the old claim (the review lists note 26, 498, 599, 603, 629, 1379, 1444).
2. **R6-M2: make the comparison a runnable procedure, and keep it out of any gate.**
   - Write it as numbered steps, as the review proposes:
     1. the candidate, built from the PR merge ref or as a `git commit-tree` squash;
     2. assembling two directories;
     3. running each;
     4. diffing;
     5. writing the slice lines.
   - For step 2, pick one way and say which: run the §10.2 pin step body with `<rev> <dir>`, or add
     `--assemble-only --rev <rev> --out <dir>` to the existing wrapper. Add no new file.
   - Add one step for R6-m7 (a): list the closure paths whose blob changed between row `k-1` and row `k`, with
     `git diff <old_blob> <new_blob>`, so Stephen reviews the code a pin advance takes in, not just the JSON row.
   - Define the `--verdict-json` shape (format string, sorted, no timings, the `error` form).
   - Write a difference at the candidate itself as `candidate | <rule> | <path>`, since its squash SHA cannot be
     known in advance.
   - Rule 0.2 (iv) checks only the line grammar, and that each `V` resolves in `(b0, C_k]`. Whether the lines are
     complete is a matter for review, under HR-3.
   - Replace the §12.1 test's "unnamed difference fails" with tests of the procedure itself:
     - two rows assembled and a difference reported;
     - both sides failing identically, reported as `ERROR`;
     - one side failing, reported as `ERROR`;
     - row 0 skipping the comparison.
3. **R6-M3: `--verify-watched-to-fail` must not bring the lockstep back.**
   - In `admission-controls` it runs with `--code-root` set to a tree assembled from `HEAD`'s `baselines[-1]`,
     never the checkout. `--code-root` has no default.
   - "Schema checks" means the top-level shape of the three files only, not their rows.
   - Add the test the review names: a non-code-owned closure module edited without a row leaves the lane green.
   - Repair the garbled sentence at note 1100.

## 3. What the decision gives up: state it plainly

Add these to HR-3 and Owner Point I as statements, not as new choices:
- **R6-m7.**
  - (a) A pin advance takes in the whole current tree, including earlier unreviewed edits to the non-code-owned
    modules, which the PR diff does not show. The step in §2.2 above is how Stephen sees them.
  - (b) The "rollback" clause in Rule 0.2 (iv) cannot be satisfied unless production code is reverted too. Delete
    it, or say so.
  - (c) A concurrent merge that changes a closure module between writing the row and landing it makes Rule 0.2 (ii)
    fail. Name this as a cause in Owner Point C's Rule 0 exit question.
- **R6-m8.** Lag is silent for anything the pinned tool does not read: new evidence files, roles or rules exit 0.
  The L-0b PR must be paired with a pin advance (§8.3), because the pinned `accepted_w9.py` stays empty until then.
  Correct note 954.
- **R6-m9.** "Code-owned, so Stephen merges it" holds only under Option I1. Say so in §6.1 and in Option I2.

## 4. The other findings

- **R6-m1:** after the loop, re-hash every key and require each destination to equal its pinned blob. Reject keys
  that are equal under `casefold()`, and any path segment containing `~`. Add both cases.
- **R6-m2:** state Git Bash (or `cmd /c`) for the wrapper pipe command, and add `test_pinned_wrapper_is_ascii_only`.
- **R6-m3:** label the three Rule 0 items 0.1, 0.2 and 0.3 in §6.5. Item 3 keeps the name. Call the deleted rule "the
  lockstep rule" everywhere.
- **R6-m4:** cite `tools/check_bypass_merges.py:140-144`.
- **R6-m5:** label the §12.3 estimates, reconcile them with the measured 0.32 s per pin-step case and the 2 s clone,
  and state the stand-in noise as measured (up to about 28%).
- **R6-m6:** add §21.1 item 11 (the pin-step script and its case list) and the wrapper test script. Otherwise remove
  both claims from the header.
- **R6-i1:** say the workflow blob is a record of what Stephen reviewed, or drop it (21 entries).
- **R6-i2:** keep "the lockstep rule is deleted" once in §6.1 and once in the change log, and remove the other
  restatements. Fix §1's handover item column, and label §15.2 item 5.
- **R6-i3:** use `os.path.isreserved`, and catch `CalledProcessError` with a named refusal.
- **R6-i4:** give the advisory row report one sentence (`HEAD` against `HEAD^1`, to the job summary, exit 0), or drop
  it from the tests.
- **R6-i5:** the wrapper preserves a child's exit 2. "Never 1" applies to the tools, not to the pin step.
- **R6-i6:** record it.

## 5. Owner points

Same order: I first, then C, A, B, D, E, F, G, H, J, K. The pin design stays marked as decided. Update I with §3,
C with the concurrent-merge cause, and F if R6-M3 changes the `admission-controls` edit list.

## 6. What to hand back

1. **Status** first, on its own line: `COMPLETE` or `PARTIAL - <exact gap>`.
2. Whether you committed (subject `[PIPELINE] P06: WP9.5 design note revision 7`, via `git commit -F` with a UTF-8
   file without a byte-order mark), the new HEAD, and `git status --short`.
3. Bytes and lines before and after.
4. For each R6 finding ID: what changed, with the section, and any departure from the review's proposed text.
5. Owner points A to K, one line each.
6. The Verification appendix's summary, and every statement marked UNVERIFIED.

Do not describe the note as reviewed or accepted. It goes to a seventh independent review next.
