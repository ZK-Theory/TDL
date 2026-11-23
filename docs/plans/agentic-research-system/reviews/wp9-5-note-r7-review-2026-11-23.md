REWORK REQUIRED

# Independent adversarial review: WP9.5 design note, revision 7

| Field | Value |
|---|---|
| Subject | `docs/plans/agentic-research-system/transition/w9/wp9-5-design-note.md`, revision 7, commit `08840c3e`, blob `1b82e1d6` (2,039 lines, 226,884 bytes; `wc -lc` and `git rev-parse` match the brief), base `dbd54fe3` |
| Prior reviews | `wp9-5-note-r6-review-2026-11-22.md` (`d47a8e72`): REWORK REQUIRED, 0 Blocking, 3 Major, 9 Minor, 6 Info; r1 to r5 for background |
| Brief | `handoffs/wp9-5-gemini-note-r7-followup-2026-11-23.md` (adopt the r6 review's text for the three Majors, log departures); the owner's pin decision, `handoffs/wp9-5-gemini-note-r6-followup-2026-11-22.md` section 1; handover `wp9-5-gemini-note-handover-2026-11-21.md` |
| Worktree | `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note`, branch `docs/w9-wp9-5-design-note`, HEAD `08840c3e` (read-only; `git status --short` empty before this report was written and after every scratch run) |
| Reviewer | fresh session, no author context; skill `adversarial-design-review` |
| Date | 2026-11-23 |
| Verdict | **REWORK REQUIRED**: 0 Blocking, 1 Major, 10 Minor, 7 Info, plus one statement for the owner (R7-d1) |

"note NNN" is a line number in the note at `08840c3e`. Other `path:line` values are at `dbd54fe3` (`origin/main` is `4ca375a3`; `git ls-remote origin refs/heads/main` still returns it; its only code change since is a comment in `research_system/legacy/citations.py`, not a closure module).

## 0. Summary

Revision 7 does what the brief asked in the places the brief names, and the note is smaller (226,884 bytes against 237,726; sections 1 to 16 fell from 200,394 to 184,859 bytes; 2,039 lines against 2,012). Every fact I re-ran reproduced: the 22 guarded commits in the 320-commit walk, 70 and 90 `CONVENTIONS.md` units, the 15-module closure with all recorded blobs equal to `git rev-parse dbd54fe3:<path>`, ruleset `20822054` (all pins), the parent-and-child `python -S -P` isolation probe (script and `-m` forms), the Git Bash stdin-pipe wrapper test, the 27-case pin script (item 11: `PIN_CASES_OK: 27`), and 0 out-of-range citations (219 distinct pairs, 284 ranges, 437 range occurrences, 347 pair occurrences by my count). Both YAML blocks parse, every `run:` script passes `bash -n`, and the detector workflow has `on: workflow_dispatch` only, no `inputs`, `contents: read, pull-requests: read`, `timeout-minutes: 15`.

The three R6 Majors are resolved in substance:

- **R6-M1.** Unparseable evidence and unknown `format` strings now exit 2 with a defined `--verdict-json` `error` form, in section 1, 2.1, 6.2.2, 6.3, 6.6, 8.2, 12.1, 13, 14 and 16. Every restatement of the old "exit 1" claim is corrected. Residual Minors only (R7-m1, R7-m2).
- **R6-M2.** The comparison is now six numbered steps with a defined candidate, a defined `w9-verdict/1` shape, Rule 0 in the verdict, a `candidate | rule | path` slice form, and a grammar-only Rule 0.2 (iv). I ran the section 10.2 pin-step body with `argv = <rev> <dir>` on a candidate commit that is not on `origin/main`: it assembled row k-1 at `pr_base` and row k at the candidate (section 2). The procedure is runnable once a few placeholders and wrapper semantics are fixed (R7-m3, R7-m4, R7-m5, R7-m6).
- **R6-M3.** `--verify-watched-to-fail` now runs on a tree assembled from `HEAD`'s `baselines[-1]`, `--code-root` has no default, and "schema checks" is defined. That part is sound.

One Major remains, and it is the same class as R6-M3 one test over. **R7-M1.** The R6-M3 rule ("never the checkout") is stated for `--verify-watched-to-fail` only. `test_recorded_detector_import_closure_covers_ast_walk` and `test_detector_closure_is_stdlib_only`, which also run in `admission-controls` on every PR, are specified in terms the note's own check script (item 9) implements against the checkout. A production PR that adds an import to any of the 13 non-code-owned closure modules goes red, and the only exit is a pin advance in the same PR: the per-edit burden the owner removed. The fix is one sentence, one test case and, if Stephen wants the freeze, one line in Owner Point I.

Nothing asks Stephen to reverse his decision. Section 1.4 records one statement the owner does not yet have (R7-d1: an in-place evidence-format move is a Rule 0 violation that a pin advance cannot clear) and one place where two statements of the decision collide in the note's test design (R7-M1).

### 0.1 Scope and size

**Unprescribed mechanisms.** None of substance. `--assemble-only --rev <rev> --out <dir>` on `run_w9_pinned_detectors.py` is the option the brief allowed (note 55, 580 to 581, 603); the change log records the choice and the other departures (note 1673). The re-record of `detector-controls.json` in the same PR (note 582) is R6-m7's own text. `test_pinned_wrapper_is_ascii_only` and the advisory report sentence are briefed. No new file, no gate.

**Superseded designs.** `tool_pin_commit`, `checkpoint` and `I1-narrow` occur only in section 18 (note 1566, 1567, 1625). `uv sync` occurs in negations (note 52, 1079) and section 18 (note 1593). `Rule 0.2 (v)` occurs as a negation (note 585) and section 18 (note 1594). `record-checkpoint`, `full-rewalk`, `verdict_digest`, `walk_start`, `last_verified_commit`, `T_cand` do not occur.

**"Rule 0.3".** It occurs only as the label of the `detector-controls.json` monotonicity item (note 476, 585, 678, 694, 1315, 1677). It is not the lockstep outside sections 17 to 20. The lockstep is called "the lockstep rule" (note 466).

**Do sections 1, 13, 14 and 16 match the body?** Yes on exit 2, the pin decision, the 17 handover items (section 1's first column now equals handover section 3 item for item) and the Owner Point order. They share the body's residuals (R7-M1, R7-m2). Long lines over 1,000 characters rose from 5 to 8 (note 13, 448, 868, 1066, 1366, 1431, 1433, 1697), a small readability regression against a shorter note (R7-i7).

**P-090.** It does not exist in the register (`git grep P-090` on `origin/main` and in the worktree register finds nothing). Every use is prospective ("for `P-090`") except one past-tense statement (R7-m10, note 1639).

## 1. Findings

### 1.1 Blocking

None.

### 1.2 Major

#### R7-M1. The closure tests that run on every PR are not scoped to the pinned tree, so import edits to non-code-owned modules bring the lockstep back

- **Claim.** An edit to a closure module without a new `baselines` row "is **not** a violation" and the detector "keeps running its pinned copy" (follow-up 5 section 1.2; note 466, 597, 1273). The owner also keeps "the F1 tests" in `admission-controls` (follow-up 5 section 1.6). The R6-M3 rule is "`--code-root` set to a tree assembled from `HEAD`'s `baselines[-1]`, never the checkout" (note 1066, 1273).
- **Evidence.**
  1. Two unit tests in `tests/tools/test_w9_detectors.py` compare the closure to something: `test_recorded_detector_import_closure_covers_ast_walk` ("checks AST completeness", detects "an unpinned import", note 594, 1419) and `test_detector_closure_is_stdlib_only` ("15 existing = 0 third-party imports", note 594). Both are in the `admission-controls` unit row (note 1319) and in MC-2 (note 1350). `admission-controls` is a required status check on the live ruleset (four contexts, `integration_id` 15368, re-read today).
  2. The note never says which tree they read. The only implementation it shows, item 9 (note 1858 to 1870), parses `wt / rel` for the 15 modules, where `wt` is the worktree checkout. The r3 review recorded the first test as "PR-time and preventive for new imports" (`wp9-5-note-r3-review-2026-11-21.md:180`), which was right under the lockstep and is the opposite of the decision now.
  3. The R6-M3 test (note 1319, "unrowed non-code-owned closure edit stays green") does not say what the edit is. A byte-only edit passes; an edit that adds an import does not.
- **Failure scenario.** After L-1, a production PR splits a helper out of `research_system/store/anchor.py` into a new module, or adds a third-party import to `reader.py`. `compute_detector_import_closure` on the checkout now finds `research_system/store/<new>.py`, which is not a key of `baselines[-1]` (or finds a non-stdlib import). The first test, or the second, fails; `admission-controls` is red. The detector is unaffected (it runs its pinned copy). Because Rule 0.2 (ii) needs row k's blobs to equal the tree at the appending commit, the production edit and the pin advance must land in one bypass-merged PR, or the edit cannot land. Thirteen first-parent commits in the 90 days to `dbd54fe3` touched the 13 non-owned modules (14 touched all 15; reproduced), so the class is not rare while W9 work continues. The note's controls do not catch this: the R6-M3 test is bytes-only as written, and Owner Point I's cost line counts edits, not import-graph edits.
- **Impact.** The per-edit pin-advance burden that follow-up 5 removed, for one class of production edits, plus an import freeze on 13 production modules that Stephen has not been told about. Not a silent pass; a blocked PR.
- **Disposition.** Fix now (one sentence, one test case, one owner statement). Not a reversal of the decision: the two statements of the decision are consistent only if these tests are scoped to the pin.
- **Proposed text.** In section 6.2.3 item 2 and section 10.3 add: "`test_recorded_detector_import_closure_covers_ast_walk` and `test_detector_closure_is_stdlib_only` run on the tree assembled from `HEAD`'s `baselines[-1]` by the section 10.2 pin step body (and on synthetic repositories), never on the checkout's non-code-owned closure modules. They assert a property of the pin: it is closed under its own imports and uses the standard library only. A production edit that adds an import to a non-code-owned closure module is not a violation and leaves `admission-controls` green; it surfaces at the next pin advance, where the row's own tests and the section 6.2.2 comparison judge it." Extend the R6-M3 test row with two edits: a new internal import and a third-party import in a non-code-owned closure module, lane green. If Stephen prefers the freeze, add it to Owner Point I as a cost ("(e) adding a non-stdlib or new internal import to a closure module needs a pin advance in the same PR") and name the tests as the F1 tests that enforce it.
- **Affected.** Note 594, 1066, 1273, 1319, 1350, 1419; MC-2, MC-9; claim 16; Owner Points I and F; follow-up 5 section 1.2 and 1.6.

### 1.3 Minor

- **R7-m1. The exit-code classification is not total, so a stale pinned tool can still read as a violation (R6-M1 residual).**
  1. Section 6.6 item 1 bullet 2 (note 723) keeps exit 1 for "missing required `walk-baseline.json` or `registration-manifest.json`" and for "known-`format` field-level validation failures", with the message `invalid evidence file at <commit>:<path>`. Neither is a Rule 0 to 3 violation in the brief's sense, and under `--verdict-json` neither yields a `(rule, path)` pair, so the old side of a comparison can print an exit-1 object with an empty `verdicts` map, which is R6-M1 item 4 again. The production closed-key readers raise the same exception text for an unknown format and for an extra key (`evidence.py:108-111`, "does not have the fixed format"; `test_w9_evidence.py:62`), so the tool must tell the two apart by exception class, which the note does not say.
  2. Section 8.2 (note 868) gives `exit 1` and "ACCEPTED_CL_EXPORT is empty; L-0b baseline export has not been accepted yet" for the stale-pin case after an unpaired L-0b (the parenthesis names the case). The pinned tool cannot know L-0b landed, so the message says the opposite of the truth.
  3. Only `check_legacy_writes.py` and the vault tool's JSON inputs have an explicit exit-2 statement. The other tools get it from the global sentence (note 627): `check_conventions_legacy_locks.py` on a bad pinned classification blob (note 787), `run_w9_detector_controls.py --verify-watched-to-fail` on a mismatch or an unknown `detector-controls.json` format (note 1066), `export_w9_registration_manifest.py --check` on an unknown committed format (note 456). Row 1316 says "Tool `main()`" once.
  4. `main()` wrapping does not cover an import-time failure of the assembled tree (module-level imports run before `main()`); that exits 1 with a traceback.
  - **Fix.** One sentence: "Under `--verdict-json` every exit 1 carries at least one `(rule, path)` pair; an evidence-validation failure is either `["Rule 0.2", <path>]` or exit 2." Name the exception classes for "unknown format" and "closed-key failure". Append to the section 8.2 message "(if L-0b has landed, the pinned copy predates it: advance the pin)". Replace row 1316's "Tool" by a per-tool list, and say the entry shims import inside the guarded function.
- **R7-m2. "New evidence keys exit 0" is wrong for closed-key objects, and the loud path is lazy (R6-M1, R6-m8).** HR-3 (a), section 6.1 and 6.2.3 item 3 and the Owner Point I and J text say new evidence keys, files and rules "lag silently (`exit 0`)" (note 466, 597, 1366, 1431, 1498). Every W9 evidence object is closed (`walk-baseline.json` top level, note 566; the `/1` records, note 639; the A1 entries, note 445), and the readers the closure carries reject an extra key. A new key under a known `format` therefore lands in R7-m1 item 1 (exit 1 or exit 2), not exit 0. The silent set is new files, new rules and new constants. Separately, an unknown format exits 2 only when the file is parsed. `legacy-write-records.json` is read at `C` only when `C` touches a guarded path (note 634), so a format move there is silent until the next guarded commit. Fix: say "new files, rules and constants lag silently; a new key under a known format is an evidence-validation failure (R7-m1)", and add "every known evidence file present at `<head>` is parsed on every run".
- **R7-m3. The comparison procedure still has undefined placeholders and a bash-only step list (R6-M2 residual).** Following note 578 to 586 literally:
  1. `<pr_base>` (note 579, 581, 584, 586) and `<PR_tree>` (note 579) are never defined, and `<b0>` (note 584) is not tied to a command. For the merge-ref form `<pr_base>` is `candidate^1`. For the `git commit-tree` form the tree must be the PR head's tree and the parent the PR's merge base, or the "candidate" reverts later main changes and the diff shows spurious Rule 1 to 3 differences. State "the PR must be up to date with `main`", which Rule 0.2 (ii) needs anyway.
  2. Step 2's command omits `--repo-root .` (note 581), which the normal wrapper command carries (note 601), and the procedure never fetches `origin/main`; the pipeline reads `refs/remotes/origin/main` (note 600 has the fetch).
  3. "(or `cmd /c`)" (note 578) holds for step 2's pipe only. Step 1's `candidate=$(...)` and step 4's `PYTHONPATH=<dir> python ...` and "`PYTHONHOME`/`VIRTUAL_ENV` unset" are POSIX shell. Say "Git Bash" for the procedure and keep `cmd /c` for the wrapper command.
  4. Step 5 says "diff sorted JSON" but gives no pretty form; two single-line objects diff as one changed line. Add "printed with `indent=2, sort_keys=True`".
- **R7-m4. `--assemble-only` semantics are not stated (R6-M2 residual).**
  1. The wrapper's normal mode verifies `origin/main == git ls-remote`, checks `W9_DETECTOR_PIN` under I3 and launches the detectors (note 603). Step 2 needs only the assembly. I ran the section 10.2 body with `REQUIRE_I3_PIN=true` and a `W9_DETECTOR_PIN` that equals row 0: row k-1 assembles (rc 0), and the candidate's row k fails with `ERROR: closure_blobs_sha256 ... != W9_DETECTOR_PIN` (rc 1). So under I3 the procedure fails at row k unless `--assemble-only` skips the I3 and freshness checks. Say it does.
  2. The heredoc contains `shutil.rmtree(detector_dir, ignore_errors=True)` (note 1168). On CI that is a fresh `RUNNER_TEMP` path. If the wrapper copies it, `--out .` or an existing directory deletes the operator's files. Say `--out` must not exist or be empty, else exit 2.
  3. `os.path.isreserved` exists from Python 3.13. The wrapper runs under whatever `python` Git Bash finds. Say the minimum interpreter, or that an older one exits 2 with a named message (it would exit 2 through `main()` anyway).
- **R7-m5. Step 4 runs candidate tool code on the operator's machine with his credentials, before the review gate (R6-M2 residual, trust boundary).** Step 4 executes `<dirB>`, assembled from PR-supplied blobs, on Stephen's machine; the tool calls `gh api commits/<C>/pulls` (note 621) under his login unless `--pr-map` is given. The note puts the code diff in step 3 but does not make reading it a precondition of step 4. An agent-authored pin-advance PR is the case the code-owned rule exists for. Fix: "Read the step 3 diff before step 4. Step 4 runs untrusted code: run it with `--pr-map` from a prior run, or with a token limited to `pull-requests: read`."
- **R7-m6. The tests of the procedure name two behaviours nothing implements (R6-M2 residual).** Row 1316 (note 1316) lists "row 0 skips diff" and "one-sided or identical `ERROR` -> `ERROR`". No tool skips anything: the procedure is manual, and `ERROR` reporting is a human act (note 585). The observable is: `--assemble-only --rev <pre-L-1 rev>` exits 2 with a named "no walk-baseline" message (row 0), and `--verdict-json` prints the `error` object on each side. Say that the diff helper that classifies the two outputs lives in the test file only, ships nowhere and is called by no workflow, so the tests are not a gate in disguise.
- **R7-m7. Pin-assembly code exists in up to three copies and the mechanism for the third is not given (R6-M3).** The detector workflow carries the heredoc (note 1119 to 1224), the wrapper must carry the same logic inline (self-contained, note 603), and `admission-controls` is told to use "the section 10.2 pin step body" (note 1066, 1273) with no mechanism: the bash around the body is hard-wired to `refs/remotes/origin/main` (note 1127), `ci.yml` would need a copy, and Owner Point F's edit list names only `ci.yml:212` and `test_ci_platform_policy.py:228` (note 1480). My run shows the body is reusable if called as `python - <HEAD> <dir>` with `REQUIRE_I3_PIN` and `W9_DETECTOR_PIN_VAR` unset (section 2). Say how: the unit test extracts the heredoc from the workflow YAML (as item 11 does) and runs it, or the lane calls the checkout's wrapper with `--assemble-only --rev HEAD`. Add a test that the copies are the same bytes, and run the item 11 cases against the wrapper's assembly too; today the 27 cases cover the heredoc only.
- **R7-m8. The Rule 0.2 (iv) verdict-line grammar is not defined (R6-M2).** Note 689 says the post-merge tool checks "`V[:8] | <rule> | <path>` or `candidate | <rule> | <path>` grammar and that `V` resolves in `(b0, C_k]`". The slice is free text in a decision-register entry, which may contain markdown tables with `|`. The note does not say how a verdict line is recognised, whether a near-miss line is ignored or a violation, or the `<rule>` set. A mismatch is a Rule 0 violation that cannot be acknowledged (note 586, 1447). Give the pattern ("a line that begins with `candidate | ` or eight lowercase hex digits then ` | `; other lines are not checked") and the `<rule>` set (`Rule 0.1` to `Rule 0.3`, `Rule 1` to `Rule 3`); put both in row 1315.
- **R7-m9. The "what it gives up" statements are still partly missing (R6-m7).** The brief asked for plain statements in HR-3 and Owner Point I. (b) rollback and (c) the concurrent-merge cause are present (note 1366, 1431, 1447). (a), that a pin advance takes in the whole current tree including earlier unreviewed edits that the PR's own diff does not show, is only implicit in "(c) snaps to the whole current tree" and in step 3's parenthesis (note 582). HR-3 (b) also says "no machine gate checks tool edits" (note 1366), which is wider than the truth: the lane runs the tool's unit tests and `--verify-watched-to-fail`, and Rule 0 judges the row. What is missing is the old-versus-new comparison. The Option I2 text (note 1436) says "un-owned" but not that a pin advance is then an ordinary PR. Fix: one sentence each.
- **R7-m10. One sentence says the decision is already in `P-090` (note 1639).** Section 19's header reads "decision (*entered in `P-090` with the other owner points*)". `P-090` does not exist. Follow-up 5 asked for "to be entered". The same slip would mislead a reader who treats section 19 as the record.

### 1.4 Findings against the owner's decision

I found nothing showing the decision cannot be carried out as decided. Two points are recorded here, apart from the findings above, because they bear on what Stephen decided. Neither asks him to reverse any part of it.

- **R7-d1 (a statement, not a challenge). An in-place change of an evidence file's format cannot be absorbed by a pin advance.** The decision's incompatibility story is "evidence formats move on, the pinned tool exits 2, a pin advance follows" (follow-up 5 section 1.4). As written, the post-merge Rule 0 text forbids the move itself: Rule 0.1 requires every entry at `P1` to remain "with identical fields" (note 681), Rule 0.2 requires ledger entries to be "byte-identical" (note 683) and `format` to be immutable (note 684), and Rule 0 cannot be acknowledged (note 586). A commit that rewrites `registration-manifest.json` from `/2` to a later format changes every entry's key set, so the new tool, after the advance, judges that commit a Rule 0.1 violation and the run stays red until the exemption row (Option C-R0-exemption, "not built", note 1447) or a design amendment. Options A1 and D3 are not affected because they are decided before code dispatch (note 426, 1405), so no `/1` file is live. Owner Point C's examples (note 1447) are concurrent merges and slice typos; this is a third. Suggested statement for HR-3 and Owner Point C: "After L-1 an evidence format moves by a new file path, or by a hash-bound exemption row, not in place."
- **R7-M1 (above) is where two statements of the decision meet.** "An unrowed closure edit is not a violation" and "the F1 tests stay in the lane" hold together only if the closure tests are scoped to the pin. Scoping them is within the decision; it needs no new mechanism.

### 1.5 Info

- **R7-i1. The comparison is least informative when it is needed most.** If the advance is motivated by a format move (the case the decision names), the old side exits 2 (`ERROR`) on the candidate and the "difference" is the new tool's whole verdict. Step 5 reports that as `ERROR`, correctly, but say so, so that Stephen reads the new tool's verdict list alone in that case.
- **R7-i2. The pin step accepts root-level keys that shadow the standard library.** `PYTHONPATH` entries precede the stdlib, and the heredoc has no allowlist on the first path segment. I assembled a key `json.py` and a key `sitecustomize.py` (rc 0 both) and confirmed `import json` under `PYTHONPATH=<dir> python -S -P` loads the assembled `json.py`. The keys come from `compute_detector_import_closure` (only `research_system`, `tools` and the workflow) and Rule 0.2 (ii) needs the file at the repository root, so this needs a reviewed row; it is defence in depth. Add "first segment must be `tools`, `research_system` or `.github`" to the refusals.
- **R7-i3. Timings.** The note's labels are right. On this machine the bare clone took 2.17 and 2.65 s (note: `1.57` to `2.07`); the note's own 27-case harness took 18.7 s end to end (0.69 s a case, including repository set-up; the note budgets 8.6 s from the pin step alone); the 6-call stand-ins were 10.80, 32.58 and 58.0 s (note 14.05, 34.46, 62.84), so the spread across four independent runs is about 34%, not "up to about 28%". The sum of the unit-lane estimates is still under 40 s against Owner Point G's 300 s. Nothing to change but the percentage.
- **R7-i4. Live re-check at review time.** Ruleset `20822054`: enforcement active, include `refs/heads/main`, one bypass actor (`actor_id` 5, `RepositoryRole`, `pull_request`), `pull_request` (`required_approving_review_count` 0, code-owner review true, thread resolution true, `squash`), `required_status_checks` (`strict` true, four contexts, `integration_id` 15368), `merge_queue` (`SQUASH`, 1, 1, 1, `ALLGREEN`, `check_response_timeout_minutes` 20), `non_fast_forward`. The month window now holds 50 entries (26 bypass, 24 pass; oldest `5d325c5b`, newest `4ca375a3`), which is the sliding window the note describes (its 56 and 32 are dated 2026-11-21). `commits/4ca375a3/pulls` returns #448 and `commits/dbd54fe3/pulls` returns #446, each with `merge_commit_sha` equal to the commit.
- **R7-i5. The PowerShell claim holds only under the default `$OutputEncoding`.** In a clean `powershell.exe` 5.1 child, a wrapper containing four non-ASCII characters arrives as four `0x3f`. In this tool host (`$OutputEncoding` is UTF-8) it arrives intact; under Git Bash and `cmd /c` it arrives intact. The ASCII-only test makes the difference moot. No change needed.
- **R7-i6. Item 11's "malformed JSON" is the case `{}`.** The header (note 13) lists "malformed JSON". I ran six genuinely bad `walk-baseline.json` variants through the step (`{not json`, `[]`, `null`, `{"baselines": []}`, a non-string `baseline_commit`, a list for `detector_closure_blobs`): each exits 1 with a named `ERROR:` and no traceback, which is the pin step's contract (R6-i5). An empty `detector_closure_blobs` mapping exits 0 and assembles nothing; the next step then fails to open its script.
- **R7-i7. The advisory row report has no flag, tool or trigger.** Note 587, 1274 and 1479 give one sentence (`HEAD` against `HEAD^1`, job summary, exit 0). No tool or flag is named, and section 6.3 item 4's flag list does not include one. It is optional; either name the invocation or drop the sentence. Long lines over 1,000 characters rose from 5 to 8 (note 13, 448, 868, 1066, 1366, 1431, 1433, 1697) while the note shrank.

## 2. Citation and checks audit

**Citations.** `r7_cites.py` (the r6 review's method; run on the r6 note it returns the r6 review's counts exactly, 231 pairs, 295 ranges, 456 and 366 occurrences) resolved every `file:line` form in the note against `git show dbd54fe3:<path>` (reviews and handoffs at the branch head or the main checkout), including each part of a comma list: 219 distinct pairs, 284 ranges, 437 range occurrences, 347 pair occurrences, 0 unresolved, 0 out of range. The author's "342" is a counting difference. Revision 7 adds three pairs (`06v:610-620`, the r6 review's `:19,113,117`, `check_bypass_merges.py:140-144`) and drops 15 that are now written in the anaphoric form ("`ci.yml` ... `:239-241`"); I checked those against the base (`ci.yml:239-241`, `merge-admission.yml:52-55,70-83` (start of the second range read), `merge-admission-sweep.yml:58-59`, `ars-artefact-currency.yml:12-13`, `ars-artefact-currency-watchdog.yml:14-16`, `research-system-suite.yml:30-31`, `ci.yml:263,276`, `test_ci_platform_policy.py:364-369,372-374`): all correct. I read the first line of every citation on the 405 lines new or changed since revision 6 (`r7_changed_cites.py`, 94 distinct pairs): all point at what the note says. `check_bypass_merges.py:140-144` is `_gh` with `encoding="utf-8"`, as R6-m4 required. `tests/tools/test_ars_currency_workflow_controls.py:19-22` (`yaml.BaseLoader`), `evidence.py:108-131` (`_closed`, `require_registered`), `test_w9_evidence.py:62` and the CODEOWNERS count (8 paths equal to `GATE_FILES`, `test_ci_platform_policy.py:341-350`) match. The `ci.yml` admission-controls job (`:137-148`: `fetch-depth: 0`, `timeout-minutes: 20`, `permissions: contents: read`) is as the note states; nothing the lane would now run needs a token. `06v:610-620` is "8. Stop rules"; section 15.2 items 1 to 3 cite `06v:614,616-619` (checked against that list), item 4 cites P-087 item 7, and items 5 and 6 are labelled as added. The 13 non-owned and 14 non-owned module counts (13 with `I1-include-seg`) and the rates "14 of 178 in 90 days, 7 in four weeks" reproduce over the 15 modules (`git log --first-parent --since=2026-08-21`).

**Section 21.1, run verbatim from the note (`r7_extract_items.py` writes each script unchanged).**

| Item | Note | Mine |
|---|---|---|
| 3 walk | 320 commits, 22 guarded, listed | 320 and 22, the same 22 hashes in the same order |
| 4 counts | 70 and 90 units; `[3,2,5,4,24,13,6,3,2,8]`, `[3,2,6,5,4,24,13,6,3,9,15]` | identical, 0 blockers |
| 5 closure | 15 modules, blobs in the row | 15; every recorded blob equals `git rev-parse dbd54fe3:<path>` |
| 6 clone | `1.57` to `2.07` s; 58,133 objects, 28 packs, 335.09 MiB | 2.17 and 2.65 s (R7-i3); same counts |
| 8 ruleset | 16 pins | all match; month window 50 entries today (R7-i4) |
| 9 isolation | script and `-m`, parent and child | reproduced: `no_site 1`, `safe_path true`, no `site-packages`, `research_system` and `tools` inside the scratch tree, `research_system.cli`, `tools.check_merge_admission`, `yaml`, `pytest` raise `ModuleNotFoundError`; 0 non-stdlib imports in the 15 modules |
| 9 wrapper | `WRAP_OK ... 1 True` then `CHILD 1 True` | reproduced under Git Bash (`item_9_wrap0.sh` run unchanged) |
| 10 stand-in | 14.05, 34.46, 62.84 s | 10.80, 32.58, 58.0 s (R7-i3) |
| 11 pin step | `PIN_CASES_OK: 27` | `PIN_CASES_OK: 27` (18.7 s) |

**Pin step, my own cases (`r7_pin_extra.py`, the workflow's assemble step extracted from the note, Git Bash, scratch repositories, 27 cases).** Refused with a named `ERROR:` and no traceback, no file outside the assembly directory: a NUL, `?`, `*`, `|`, `<`, `>`, `"`, `\x01` and a newline in a key; the case-fold duplicates `tools/\u212a.py` against `tools/k.py` (Kelvin sign), `tools/stra\u00dfe.py` against `tools/STRASSE.py`, and `tools/a.py` against `tools/A.PY` with identical content; `tools/a.py::$DATA`; a 300-character path (named `hash-object` failure); a "blob" given as `HEAD:seed.txt` (post-write mismatch); and six malformed `walk-baseline.json` variants (R7-i6). Accepted: `tools/\u0131.py` and `tools/I.py` (NTFS keeps them distinct on this machine), `.git/config` as a key, an empty mapping, and root-level `json.py` and `sitecustomize.py` (R7-i2). The author's 27 cases include the case-fold duplicate (`tools/Dup.py`, `tools/dup.py`), the `~` short name (`tools/CHECK_~1.PY`), `tools/CON .py`, `tools/NUL .txt`, `tools/CONIN$`, `tools/COM\u00b9`, `tools/LPT\u00b3.txt`, traversal (`../escaped.txt`), absolute keys (`/escaped_abs.txt`, `C:/escaped_drive.txt`), a backslash, a double slash, a trailing dot and space, and three I3 variants; all reproduce.

**Two rows, one off `origin/main` (`r7_two_rows.py`).** A scratch repository with row 0 on `main` and row 1 on a side branch that is never merged. The extracted section 10.2 body with `argv = <rev> <dir>` assembled `print('v1')` at `pr_base` and `print('v2')` at the candidate. With `REQUIRE_I3_PIN=true` and a variable that equals row 0, the candidate failed on the I3 digest (R7-m4 item 1).

**YAML.** Both blocks parse with `safe_load` (key `on` becomes `True`) and `BaseLoader` (`on` is `{workflow_dispatch: ''}` for the detector and `{pull_request: ''}` for the U-3 probe); no `inputs`; detector `permissions: contents: read, pull-requests: read`, job `timeout-minutes: 15`; the five `run:` scripts pass `bash -n`. One non-ASCII character (`U+00A7`, in a comment) is in the detector block. I did not run the U-3 probe or the U-4 script.

## 3. Disposition of every R6 finding

| ID | Disposition | Evidence |
|---|---|---|
| R6-M1 | **Resolved, residual Minors** | Note 722 adopts the review's text; restatements corrected at note 26, 466, 569, 597, 627, 1366, 1379, 1431; section 8.2 names exit 1 for the empty export; row 1316 tests unknown format and unparseable JSON. Classification is not total (R7-m1); the silent-lag statement is wrong for closed keys (R7-m2). |
| R6-M2 | **Resolved in substance, residual Minors** | Six steps, candidate by merge ref or `commit-tree`, `w9-verdict/1` defined (note 585), Rule 0.1 to 0.3 in the verdict, `candidate | rule | path`, grammar-only (iv) (note 689). The assembly works on an off-main candidate (section 2). Placeholders, wrapper semantics, ordering, tests, grammar: R7-m3 to R7-m6, R7-m8. |
| R6-M3 | **Resolved for `--verify-watched-to-fail`; same class leaks** | Note 1066, 1273, 1319, 1357 state the assembled `--code-root`, no default, top-level-shape schema checks, and the unrowed-edit test. The closure tests are not scoped (R7-M1); the mechanism for the assembly in the lane is unstated (R7-m7). |
| R6-m1 | Resolved | Post-loop re-hash of every written key, `casefold()` refusal, `~` refusal (note 1171 to 1189, 1207 to 1218); my aliases and Kelvin, sharp-s and same-content cases all refused. |
| R6-m2 | Resolved | Git Bash or `cmd /c` stated (note 598); `test_pinned_wrapper_is_ascii_only` in section 6.2.3, 12.1, MC-2, 15.2; PowerShell claim verified (R7-i5). |
| R6-m3 | Resolved | `Rule 0.1`, `0.2`, `0.3` labelled (note 678 to 694), the verdict names all three (note 585), the lockstep is "the lockstep rule" (note 466). |
| R6-m4 | Resolved | `:140-144` (note 626); line 140 is `_gh`, 141 holds `encoding="utf-8"`. |
| R6-m5 | Resolved | Estimates labelled "estimate, unwritten code" (note 1334); 0.32 s a case and the 2 s clone reconciled; noise stated as measured (note 588, 1330). My figures are in R7-i3. |
| R6-m6 | Resolved | Item 11 (note 1985 to 2029) and the wrapper script (note 1926 to 1941) are in section 21.1; both run. |
| R6-m7 | **Partly resolved** | (b) and (c) present; (a) only implicit; HR-3 (b) too wide (R7-m9). |
| R6-m8 | Resolved, one wrong sentence | L-0b paired with a pin advance (note 920, 1498); note 954's "without needing a detector rewrite" is gone. "New keys exit 0" is inaccurate (R7-m2). |
| R6-m9 | Resolved | Note 465, 1366, 1431 (d). The I2 option does not say a pin advance is then an ordinary PR (R7-m9). |
| R6-i1 | Resolved | The workflow blob is "a review record only", 21 executed plus 1 recorded (note 592). |
| R6-i2 | Resolved | Section 1's first column equals the handover's 17 items; section 15.2 items 5 and 6 are both labelled (note 1418, 1419); the lockstep sentences are fewer (they now state the decision, not a rule). |
| R6-i3 | Resolved | `os.path.isreserved(rel_path)` and `(part)`, `CalledProcessError` caught with named refusals (note 1185 to 1218); `CON .py`, `CONIN$`, `COM\u00b9` reproduced. |
| R6-i4 | **Partly resolved** | One sentence at note 587, 1274, 1479; no invocation (R7-i7). |
| R6-i5 | Resolved | The wrapper propagates a child's exit 2; "never 1" is scoped to the WP9.5 tools (note 52, 569, 603, 627). The pin step exits 1 with a named `ERROR:` (R7-i6). Import-time failures: R7-m1 item 4. |
| R6-i6 | Resolved | Recorded in section 21.1 item 8 (note 1838); reproduced, and the window has since slid (R7-i4). |

## 4. Owner points A to K

| Point | Premises checked | Recommendation | Missing or wrong |
|---|---|---|---|
| I (first) | CODEOWNERS has 8 paths equal to `GATE_FILES`; 10 owned files plus `w9_segmentation.py` (11), 13 non-owned modules (14 under `I1-exempt-seg`); 14 of 178 and 7 in four weeks (reproduced); the pin decision recorded as decided 2026-11-22 for `P-090` (note 464, 1431) | I1 with `I1-include-seg` and `I1-py-minor` is sound | Gives-up (a) is implicit (R7-m9); the import freeze or its removal is not stated (R7-M1); I2 wording (R7-m9); R7-d1 |
| C | 22 guarded commits and the 320-commit walk reproduce; Rule 0 exit narrowed to the exemption row or "stays red"; concurrent closure merges and slice typos are named causes (note 1447) | C1 with Stephen's choice of exit | Add in-place format moves as a cause (R7-d1); slice-grammar typos are only as safe as the grammar is defined (R7-m8) |
| A | `evidence.py:108-131` closed readers, `test_w9_evidence.py:62`, the four fixture builders, `wp9-4-1-record.md:114,130` | A1 sound | none new; A1 lands before L-1, so R7-d1 does not touch it |
| B | Conditional on I1 (stated) | B1 sound | none new |
| D | `evidence.py:190-252`, `acceptance.py:121-136` | D3 sound | none new |
| E | Four gate sites by citation | E1 sound | none new |
| F | `ci.yml:166-216`, `:212`, `ADMISSION_CONTROL_MODULES`; zero `gh`, token, permission or timeout change (confirmed: the lane needs none) | F1 sound once the closure tests are scoped | The assembly mechanism in the lane and its edit list (R7-m7); R7-M1 |
| G | `03-decisions-and-open-questions.md:5919-5923`; my sum of the unit-lane estimates and my 18.7 s harness stay near 40 s | G1 until profiled | none new |
| H | Unchanged | H1 sound | none new |
| J | `accepted_w9.py:86-88` mirror; leaf module; pairing with a pin advance (note 1498) | J1 sound | Note 1498 repeats "new keys exit 0" (R7-m2) |
| K | `06v:491-492`; self-judgement stated | K1 sound | none new |

Register entries each option needs are as the note states them and unchanged in kind: A1, D3 and E1 each need a dated WP9.3 amendment, an independent review and a `P-090` entry; H1 a dated W9 section 4.2 amendment; I1 the `CONVENTIONS.md` amendment; C, B and the evidence-format rows in `06v-addendum-2026-11-10-w9-paths.md`; F1 and K1 edit code-owned `ci.yml`. None of A, D, E, I or F falls inside the register's Boundary sentence (`03-decisions-and-open-questions.md:6141-6143`) except as owner decisions (`:6111`).

## 5. Consistency matrix for the revision 7 mechanisms

| Invariant | Enforcement point | Test | Result |
|---|---|---|---|
| Unparseable or unknown-`format` evidence exits 2; `--verdict-json` prints `error` | `main()` wrapper; note 627, 722 | Row 1316 | Sound for `check_legacy_writes.py`; classification not total (R7-m1) |
| Exit 1 only for Rules 0 to 3 on evidence the tool read | Note 722, 723 | none | Bucket 2 of note 723 is outside it (R7-m1) |
| Closure of the exit-2 clause over the six tools and the M-6 exporter | Global sentence, note 627 | Row 1316 names "Tool" | `check_legacy_writes.py` and the vault tool explicit; the other four by the global sentence only (R7-m1) |
| A stale pin is loud, not silent | HR-3 (a); note 466, 597 | none | Silent set stated wrongly for keys (R7-m2); lazy parse (R7-m2) |
| An unrowed non-code-owned closure edit is not a violation | No lockstep; `baselines[-1]` | Row 1315, row 1319 | Sound post-merge and for `--verify-watched-to-fail`; leaks through the closure tests (R7-M1) |
| The comparison is a runnable procedure, not a gate | Note 578 to 586 | Row 1316 | Runnable (section 2); R7-m3 to R7-m6 |
| Rule 0.2 (iv) checks grammar only; completeness is review | Note 689; HR-3 (b) | Row 1315 | Grammar undefined (R7-m8) |
| Pin assembly cannot write outside the tree and the tree equals the pin | Note 1119 to 1224 | Item 11 (27), mine (27) | Sound; shadowing hardening (R7-i2); copies (R7-m7) |
| The wrapper is one stdlib, ASCII-only file run from `origin/main` | Tests named in note 594 | Row 1319 | Sound; `--assemble-only` semantics (R7-m4) |
| `--code-root` has no default; the lane assembles from `HEAD`'s `baselines[-1]` | Note 1066, 1273 | Row 1319 | Sound; mechanism (R7-m7) |
| Nothing in `admission-controls` calls `gh`, sets a token, adds permissions or changes the timeout | Note 467, 1479 | none | Sound (`ci.yml:137-148`) |
| Post-merge runs make one walk with `baselines[-1]` | Note 577 | Pin-step tests | Sound |
| L-0b is paired with a pin advance | Note 920, 1498 | none (human) | Stated; message misleads (R7-m1) |
| `P-090` is prospective | Note 464, 1425, 1431 | none | One past-tense slip (R7-m10) |
| An evidence format can move after L-1 | Rule 0.1, 0.2 | none | As written it cannot, without a violation (R7-d1) |

## 6. What was checked and found sound

- **The three R6 texts were traced through the code they rely on, not only compared with the brief.** The pin-step body assembles two rows and an off-main candidate; the closed-key readers refuse extra keys; `os.path.isreserved` rejects the illegal-character and device names I fed it; `-S -P`, `PYTHONSAFEPATH` and the explicit child flags isolate parent and child; the stdin pipe delivers the wrapper bytes intact under Git Bash and `cmd /c`.
- **Rule 0.3 as the lockstep is gone.** Every remaining "Rule 0.3" is the `detector-controls.json` item. The PR-time gate is gone from `admission-controls`: no `gh`, token, `pull-requests: read` or timeout change; the lane's `fetch-depth: 0` supplies the history `--verify-watched-to-fail` and the assembly need.
- **Attacks that failed.** (1) Writing outside the assembly directory through a traversal, absolute, drive, backslash, stream, device, illegal-character or long-path key: refused. (2) An alias collision surviving the post-loop check: case-fold, `~` and the re-hash all refuse. (3) A short or ref-name "blob" passing the object-type test: the post-write hash refuses it. (4) A hidden second gate in the retained lane through a token or a walk: none; the added cost is a few seconds. (5) A superseded design left in the body: none. (6) A restatement narrowing the "no machine checks a tool change" statement: HR-3, section 6.1, section 14 claim 2 and Owner Point I agree, apart from the wording in R7-m9. (7) P-089's Boundary sentence contradicted by an owner point: each change under `research_system/legacy/` or `ci.yml` is put as an owner decision with a `P-090` entry. (8) A pin advance judged by a tool that cannot read the row's format: the new tool judges its own row by the owner's decision.

## 7. Coverage of the handover's 17 items and section 15.1's gates

| # | Item | Result |
|---|---|---|
| 1 | Scope, protected identities | Settled (section 2.2). |
| 2 | Ruleset read | Settled; pins verified live today. |
| 3 | U-3 | Probe specified (note 184 to 267); gate in 15.1 item 1; `commits/<sha>/pulls` read only by the detector workflow, which has `pull-requests: read`. |
| 4 | First-parent detector | Evidence timing, Rules 0 to 3, pin, one walk, exit-2 semantics and the comparison settled; residuals R7-m1 to R7-m8. |
| 5 | M-6 export | Settled; residual `HR-7`. |
| 6 | Shared-surface rule | Settled. |
| 7 | `CONVENTIONS.md` check | Settled; K put to Stephen. |
| 8 | Vault detector, D-5 | Settled; the L-0b pairing is stated (R7-m1 item 2 on the message). |
| 9 | U-4 | Metadata equals the brief; script unchanged; gate in 15.1 item 2. |
| 10 | Controls file | Code root settled; closure tests (R7-M1). |
| 11 | Merging is not going live | Settled; a green `workflow_dispatch` on the L-1 commit is an exit criterion (note 1260). |
| 12 | Where controls run | Settled. |
| 13 | Tests and budget | Inventory in nine rows; estimates labelled; budget near 40 s (R7-i3). |
| 14 | Research assurance | MC-1 to MC-10 and HR-1 to HR-7; HR-3 carries R7-m9. |
| 15 | Claims for review | 16 claims; claim 2 and claim 16 carry R7-M1. |
| 16 | Stop rules | Section 15.1 (five items) and 15.2 (six): items 1 to 3 cite `06v:614,616-619`, item 4 cites P-087 item 7, items 5 and 6 are labelled as added. |
| 17 | Owner points | Eleven, in the order I, C, A, B, D, E, F, G, H, J, K. |

Section 15.1's gates are all present: U-3 (item 1), U-4 dry run (item 2), Owner Points decided (item 3), single scratch-store profile (item 4) and the hosted walk time (item 5, `UNVERIFIED-5`). The "items 1 to 4 ... and item 5 acknowledged" wording (note 1401) fixes the r6 count slip.

## 8. Revision plan

**Immediate corrections (author, no owner decision):**
1. R7-M1: scope the two closure tests to the assembled `baselines[-1]` tree in sections 6.2.3, 10.3 and the F1 text; add the two import-adding edits to the R6-M3 test row.
2. R7-m1, R7-m2: make the exit classification total, fix the "new keys exit 0" sentence, say the known evidence files are parsed every run, per-tool test list, section 8.2 message.
3. R7-m3 to R7-m8: define `<pr_base>`, `<PR_tree>`, `<b0>`; add `--repo-root .` and the `origin/main` fetch; fix the shell statement; state `--assemble-only` skips freshness and I3 and refuses a non-empty `--out`; read-before-run in step 4; restate row 1316 in observable terms; name the assembly mechanism in the lane and the copy-equality test; define the verdict-line grammar.
4. R7-m9, R7-m10 and R7-i1 to R7-i7 as written.

**Owner decisions after revision 8:** I first (with the gives-up additions, and the import-freeze line if Stephen wants it), then C (with R7-d1), F (with the assembly mechanism), then A, B, D, E, G, H, J, K unchanged.

**Later-work dependencies (unchanged):** U-3 probe and the U-4 dry run before code; the unconditional scratch-store profile; a full-walk time with real rules, PR mapping and the whole detector workflow on `windows-latest` (`UNVERIFIED-5`); dated WP9.3 amendments and independent reviews for A1, D3 and E1; a dated W9 section 4.2 amendment for H1; the L-0b export and classified list with its paired pin advance; the pre-L-1 rehearsal and a green dispatch run on the L-1 commit.

**What a code task's tests would settle, once R7-M1 is fixed.** R7-m3, R7-m4, R7-m6 and R7-m7's copy-equality test, R7-m8's pattern, R7-i2's allowlist and R7-i3 are implementation detail with tests. R7-m1 and R7-m2 are one-sentence design statements plus tests. R7-m5 and R7-m9 are one sentence each. Only R7-M1 and R7-d1 touch what Stephen was told.

**Residual risks the note should keep stating:** the detector is post-merge and a human merge is the only preventive control for a pin advance and for the code-owned paths; a pin advance is judged by Stephen's review alone and snaps to the whole current tree; lag is silent for new files, rules and constants; a post-merge Rule 0 violation stays red unless Stephen picks the exemption row; the weekly vault run is self-attested; the CI token may not read `rule-suites` (D-8); the `CONVENTIONS.md` check does not see sub-heading or ordering edits outside units; the M-6 exporter runs from the checkout.

## 9. Commands run

All read-only on the repository. `git status --short` in the worktree was empty at the start, after each scratch run, and before this report was written; this report is the only file added. No vault file was read or opened, the U-3 probe and the U-4 script were not run, no workflow was run, no repository variable was read, nothing was pushed, and every `gh api` call was a GET.

- `gh api` GETs: `repos/ZK-Theory/TDL/rulesets/20822054`, `rulesets/rule-suites?ref=refs/heads/main&time_period=month&per_page=100` (`--paginate --slurp`, saved to scratch), `commits/4ca375a3.../pulls`, `commits/dbd54fe3.../pulls`. `git ls-remote origin refs/heads/main`.
- `git` in the worktree: `rev-parse`, `show <rev>:<path>` (the note at `08840c3e` and `95dfefe7`, `ci.yml`, `CODEOWNERS`, `evidence.py`, `test_w9_evidence.py`, `check_bypass_merges.py`, `test_ci_platform_policy.py`, the 06v plan, the register), `log --first-parent --since` (edit rates), `diff --stat`, `count-objects -vH`, `grep` on `origin/main` for `P-090`, `status --short`. Scratch repositories were created and committed under the scratch directory only.
- Scratch scripts in `C:\Users\steph\AppData\Local\Temp\claude\e088a017a981a492\f302c5e4-50e0-4fcc-b0af-3a36e9983c74\scratchpad\r7`, written with the Write tool and run with the worktree `.venv` Python or the base 3.13.5 interpreter with `PYTHONDONTWRITEBYTECODE=1`: `r7_cites.py`, `r7_newcites.py`, `r7_changed_cites.py`, `r7_extract_items.py` (writes `item_3.py`, `item_4.py`, `item_5.py`, `item_6.py`, `item_9.py`, `item_9_wrap0.sh`, `item_10.py`, `item_11.py`, all run unchanged), `r7_pin_extra.py`, `r7_two_rows.py`, `r7_yaml.py`, `r7_ruleset.py`, and `wrap_src/wrap.py`. Note copies `note_r7.md` and `note_r6.md` are in the scratch directory.
- Shell checks: `bash -n` on each extracted `run:` script; the stdin-pipe wrapper under Git Bash, `cmd /c` and a clean `powershell.exe` 5.1 child; one `python -S -P -c "import json; print(json.__file__)"` with `PYTHONPATH` pointing at a scratch directory holding a `json.py` (no file composed with it).
- Deviation to disclose: one Bash command of mine started an interactive `python -` through an empty heredoc, which hung in a console error loop; I stopped it with `TaskStop` and it wrote nothing. No file was composed with `python -c` or a heredoc.
- File reads: the note in full (all 2,039 lines), the r6 review, the r7 brief, follow-up 5, the handover items, `ci.yml` (`1-30`, `128-222`), `CODEOWNERS`, the register lines naming WP9.5, `06v:598-622`, `claims-checklist.md`.
- Not run, as instructed: the U-3 probe; the U-4 dry run; anything reading the vault; the Actions variable read.
- Not verifiable here: `private: false` (note 256); who may write Actions variables (`UNVERIFIED-4`); how the hosted runner parses a CRLF `GITHUB_ENV` file; the hosted `windows-latest` wall time of the detector workflow (`UNVERIFIED-5`); the behaviour of the six unwritten tools (exit codes, JSON shape, `--assemble-only`, `--out` handling), which I could only read from the note and simulate with the heredoc body; PowerShell 5.1 behaviour on machines other than this one; the scratch-store profile (`UNVERIFIED-3`); the weekly operator run.
