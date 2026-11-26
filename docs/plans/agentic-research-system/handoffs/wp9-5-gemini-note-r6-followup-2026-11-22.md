# Follow-up 5: WP9.5 design note, revision 6

For: the Gemini agent that wrote revisions 1 to 5 of the WP9.5 design note. Written by the reviewing Claude session
on 2026-11-22.

A fifth fresh reviewer attacked revision 5 (`83b4ae6f`). The verdict is **REWORK REQUIRED**: 0 Blocking, 3 Major, 11
Minor and 6 Info. The report is committed on your branch at
`docs/plans/agentic-research-system/reviews/wp9-5-note-r5-review-2026-11-22.md` (`d6938710`). Read it before you
change anything.

The facts, citations, `python -S -P` isolation and path confinement all reproduced. Two of the Majors (R5-M1, R5-M2)
came from the design the reviewing session prescribed in follow-up 4, not from your work.

## 1. Stephen's decision: pin, no lockstep

Since revision 3, every Major has been in the pin-advance machinery. Stephen has now decided its design himself
(2026-11-22, in the reviewing session). This is an owner decision, not a design for you to choose or extend. Record
it in the note as "decided by Stephen, 2026-11-22, to be entered in `P-090` with the other owner points".

1. **Keep the content pin.** The detector runs from the assembled copy recorded in `baselines[-1]`, under
   `python -S -P`, standard library only, with path confinement. That part stays as revision 5 has it, plus the
   fixes in §3.
2. **Drop the lockstep.** Delete Rule 0.3. An edit to a closure module without a new `baselines` row is **not** a
   violation. The detector keeps running its pinned copy until Stephen chooses to advance it.
3. **Pin advances are deliberate and rare.** A pin advance is a PR that appends a `baselines` row. It is code-owned,
   so Stephen merges it himself. Rule 0.2 checks (i) to (iv) still apply to every appended row.
4. **Incompatibility fails loudly.** If production code or evidence formats move on so that the pinned copy cannot
   read them (for example a `/2` manifest under Option A1), the pinned tool must exit 2 (`ERROR`), never 0 and never
   1. That turns the run red and prompts an advance. This depends on R5-m1: every tool wraps `main()` and exits 2 on
   any uncaught exception.
5. **The old-versus-new comparison is evidence, not a gate.** The pin-advance PR carries the comparison output, and
   Stephen reviews it with the PR.
   - Specify it as a documented procedure using the detector's own output (assemble row `k-1` and row `k`, run each
     with `--verdict-json` over `(baselines[0]["baseline_commit"], candidate]`, and diff). Do not add a new tool file
     unless the procedure cannot work without one, and if so say why.
   - Use a complete verdict: the set of `(rule, path)` violations per commit, **including Rule 0**, after the
     `acknowledged` rows at the PR's base. `ERROR` on either side is reported as `ERROR`, never as clean.
   - The decision slice lists each difference on its own line, `V[:8] | rule | path` (R5-m2).
   - A test exercises the procedure on synthetic rows, including a difference, and both sides failing identically.
6. **Remove the PR-time gate.** Delete the PR-time blob-equality check, the gating row checks and the verdict
   comparison from `admission-controls`. The `L1_LIVE` tripwire, the F1 tests, `--verify-watched-to-fail` and K1 stay
   in that job. The row checks may run there as an advisory report for the pin-advance PR, labelled as advisory,
   because every pin advance merges by bypass. This also removes R5-M3's token, permission and time-budget problem:
   nothing in `admission-controls` calls `gh`.
7. **Post-merge runs make one walk** with the tool pinned at head's `baselines[-1]`, as in revision 5.

What this gives up, which the note must state plainly in §13.2 and Owner Point I:
- the detector can lag production code until Stephen advances it. That lag is safe, because it keeps running
  reviewed code and fails loudly when it cannot read new data;
- no machine checks a change of tool. A pin advance is judged by Stephen's review of the PR and its comparison output
  alone.

What it removes: Rule 0.3, the unrowed-edit "permanent red", the per-edit pin-advance burden, the gating comparison
and its cost, and the `admission-controls` token and budget issues. Delete their text from §1 to §17.

**Owner Point C** keeps one question, now rare: what clears a Rule 0 violation on the post-merge walk (a bad row or a
broken append-only file). The options are a narrow hash-bound exemption row, or that the detector stays red. Re-word
it for that scope.

## 2. Scope rules

1. **Add no mechanism beyond §1 and §3.** If something seems to need more, say so in the change log and leave it.
2. **The note must get smaller in bytes again** (it is 258,423 now). Report bytes and lines before and after.
3. **Nothing unverified, and no overclaim.** Follow-ups 1 to 4 still apply. Label every extrapolated figure as
   extrapolated (R5-m10).
4. Read-only `gh api` GETs only, for the same endpoints as before. Do not run the U-3 probe or the U-4 dry run, and
   never read vault file contents. Scratch work goes in a directory outside the repository.

Same worktree (`C:\Users\steph\TDL\.apm\worktrees\wp9-5-note`), same branch (`docs/w9-wp9-5-design-note`). Before any
write, confirm the branch, that HEAD is `d6938710`, and that `git status --short` is clean.

## 3. The other findings

- **R5-M1, R5-M2, R5-M3:** answered by §1. In the change log, say how: there is no gate to skip; Rule 0 is in the
  comparison's verdict; and nothing in `admission-controls` needs a token.
- **R5-m1:** every tool wraps `main()` and exits 2 on any exception. `--verdict-json` always prints one JSON object,
  with an `error` key on failure. Add the case where both sides fail identically.
- **R5-m2:** per-line slice entries (§1.5). A named green-to-red difference that should not stay red needs its
  `acknowledged` row in the same PR; say so.
- **R5-m3:** the stop rule is a pre-code measurement rule (§15.2), now for one post-merge walk. Say what happens when
  it is exceeded: the remedy is a design amendment (for example a hash-bound `walk_start` row), not a runtime choice.
  Reconcile it with Owner Point G's 300 s.
- **R5-m4:** the L-1 PR has no previous pin, so there is no comparison. Rule 0.2 applies to row 0. Add the case to
  §12.1.
- **R5-m5:** either add `/tools/w9_segmentation.py` to I1 or state its exemption in the test and in the text. Put the
  choice in Owner Point I, with your recommendation.
- **R5-m6:** the operator wrapper is one self-contained standard-library file with no `tools.*` or `research_system.*`
  import, enforced by a test. Give the exact command that runs Stephen's copy from `origin/main`.
- **R5-m7:** after each write, the pin step checks the file exists and that `git hash-object --no-filters` equals the
  pinned blob. It rejects names ending in a dot or space, and Windows device names. Add the cases.
- **R5-m8:** child interpreters are launched as `[sys.executable, "-S", "-P", ...]`. Add a child case to the
  isolation probe.
- **R5-m9:** every `gh` and `git` subprocess decodes UTF-8 explicitly. Add a non-ASCII case.
- **R5-m10:** label the extrapolated figures, give the stand-in's noise, and replace `walk_start` with
  `baselines[0]["baseline_commit"]`.
- **R5-m11:** finish the restatement cut. Every rule appears once in its section, and §1, §13, §14 and §16 point to
  it. Split the 4,348-character row into one row per test group. Most restatements of the PR-time gate go with §1.6.
- **R5-i1:** mostly moot without the PR-time state check. Record what remains.
- **R5-i2:** the wrapper's exact-patch Python check makes each patch update a pin advance. Put "pin `3.13.x` or
  `3.13.5`" in Owner Point I.
- **R5-i3:** add `--verify-watched-to-fail` and the CI-only snapshot to the §12.3 budget.
- **R5-i4, R5-i5, R5-i6:** record them. R5-i5 adds the queue's `check_response_timeout_minutes: 20`.

## 4. Owner points

Put them to Stephen; do not decide them, except the pin design in §1, which he has decided. Keep the order I first,
then C, A, B, D, E, F, G, H, J, K. Update:
- I, for the decision and what it gives up, R5-m5 and R5-i2;
- C, for the narrowed Rule 0 exit question;
- F, for the smaller `admission-controls` edit list.

## 5. What to hand back

1. **Status** first, on its own line: `COMPLETE` or `PARTIAL - <exact gap>`.
2. Whether you committed (subject `[PIPELINE] P06: WP9.5 design note revision 6`, via `git commit -F` with a UTF-8
   file without a byte-order mark), the new HEAD, and `git status --short`.
3. Bytes and lines before and after, and what you deleted.
4. For each R5 finding ID: what changed, with the section.
5. Owner points A to K, one line each, with your recommendation; mark the pin design as decided.
6. The Verification appendix's summary: what you ran, and every statement you marked UNVERIFIED.

Do not describe the note as reviewed or accepted. It goes to a sixth independent review next.
