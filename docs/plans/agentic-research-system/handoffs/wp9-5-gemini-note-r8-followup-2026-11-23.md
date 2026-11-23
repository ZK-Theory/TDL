# Follow-up 7: WP9.5 design note, revision 8 (final narrow revision)

For: the Gemini agent that wrote revisions 1 to 7 of the WP9.5 design note. Written by the reviewing Claude session
on 2026-11-23.

A seventh fresh reviewer attacked revision 7 (`08840c3e`). The verdict is **REWORK REQUIRED**, but the note is
close: 0 Blocking, 1 Major, 10 Minor and 7 Info, plus one statement for the owner (R7-d1). The report is committed
on your branch at `docs/plans/agentic-research-system/reviews/wp9-5-note-r7-review-2026-11-23.md` (`c4c62b3b`).

The three R6 Majors are resolved in substance. The reviewer re-ran every §21.1 check verbatim and found nothing
against Stephen's pin decision.

**Stephen has chosen a final narrow revision.** It covers only the design statements listed in §2 below. Each is a
sentence or two, plus the named test cases. Everything else the review lists (R7-m3, m4, m6, m7, m8, and R7-i1 to
i7) is implementation detail. It goes into the WP9.5 code brief as named obligations. **Do not change the note for
those items**, except that §3 asks you to list them.

Same worktree (`C:\Users\steph\TDL\.apm\worktrees\wp9-5-note`), same branch (`docs/w9-wp9-5-design-note`). Before any
write, confirm the branch, that HEAD is `c4c62b3b`, and that `git status --short` is clean.

## 1. Scope rules

1. **Change only what §2 and §3 name.** Add no mechanism, and do not restructure the note.
2. **The note must not grow** beyond 226,884 bytes by more than the added sentences need. Report bytes and lines
   before and after.
3. **Nothing unverified, and no overclaim.** Follow-ups 1 to 6 still apply. Do not re-run or rewrite §21.1 unless an
   edit changes something it checks.
4. Stephen's pin decision stands. Read-only `gh api` GETs only. Do not run the U-3 probe or the U-4 dry run, and
   never read vault file contents.

## 2. The design statements to fix

Use the review's proposed text for each, adjusted only where the code at `dbd54fe3` requires it. Record any
departure in the change log.

1. **R7-M1.** Scope `test_recorded_detector_import_closure_covers_ast_walk` and `test_detector_closure_is_stdlib_only`
   to the tree assembled from `HEAD`'s `baselines[-1]` (and to synthetic repositories), never to the checkout's
   non-code-owned closure modules. Put the review's sentence in §6.2.3 item 2 and §10.3. Extend the R6-M3 test row
   with two edits that leave the lane green: a new internal import, and a third-party import, each in a non-code-owned
   closure module.
2. **R7-m1.** Make the exit-code classification total.
   - Under `--verdict-json`, every exit 1 carries at least one `(rule, path)` pair. An evidence-validation failure is
     either `["Rule 0.2", <path>]` or exit 2; say which, for a missing required file and for a known-format field
     failure.
   - Name the exception classes that separate "unknown format" from "closed-key failure".
   - Append to the §8.2 message: "(if L-0b has landed, the pinned copy predates it: advance the pin)".
   - Replace row 1316's "Tool `main()`" with a per-tool list, and say the entry shims import inside the guarded
     function.
3. **R7-m2.** Correct "new keys exit 0":
   - new files, rules and constants lag silently;
   - a new key under a known format is an evidence-validation failure (R7-m1);
   - every known evidence file present at `<head>` is parsed on every run.

   Fix it at each place the review lists (note 466, 597, 1366, 1431, 1498).
4. **R7-m5.** In the comparison procedure, reading the step 3 diff is a precondition of step 4. Step 4 runs
   untrusted code: run it with `--pr-map` from a prior run, or with a token limited to `pull-requests: read`.
5. **R7-m9.**
   - State plainly in HR-3 and Owner Point I that a pin advance takes in the whole current tree, including earlier
     unreviewed edits that the PR's own diff does not show.
   - Narrow HR-3 (b): the lane does run the tool's unit tests and `--verify-watched-to-fail`, and Rule 0 judges the
     row. What is missing is a machine old-versus-new comparison.
   - Say in Option I2 that a pin advance is then an ordinary PR.
6. **R7-m10.** Change §19's "entered in `P-090`" to "to be entered in `P-090`".
7. **R7-d1.** Add to HR-3 and to Owner Point C's list of causes: "After L-1 an evidence format moves by a new file
   path, or by a hash-bound exemption row, not in place." Say that Options A1 and D3 are unaffected because they land
   before code.

## 3. Carried obligations for the code task

Add one short subsection at the end of §15 (or in §3, wherever obligations are listed), headed "Carried to the WP9.5
code task from the r7 review". List R7-m3, R7-m4, R7-m6, R7-m7, R7-m8 and R7-i1 to R7-i7, each with a one-line
statement of what the code and its tests must settle. Copy the review's wording; do not design the answers.

## 4. The change log

Add a compact "Change log: revision 7 to revision 8" in the same form as §20. List every R7 finding ID and R7-d1, with
the section changed or "carried to code task".

## 5. What to hand back

1. **Status** first, on its own line: `COMPLETE` or `PARTIAL - <exact gap>`.
2. Whether you committed (subject `[PIPELINE] P06: WP9.5 design note revision 8`, via `git commit -F` with a UTF-8
   file without a byte-order mark), the new HEAD, and `git status --short`.
3. Bytes and lines before and after.
4. For each item in §2: what changed, with the section, and any departure from the review's proposed text.
5. The list of carried obligations as you wrote it.

Do not describe the note as reviewed or accepted. A final focused review checks only these changes next.
