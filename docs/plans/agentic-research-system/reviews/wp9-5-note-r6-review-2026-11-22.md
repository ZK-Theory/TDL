REWORK REQUIRED

# Independent adversarial review: WP9.5 design note, revision 6

| Field | Value |
|---|---|
| Subject | `docs/plans/agentic-research-system/transition/w9/wp9-5-design-note.md`, revision 6, commit `95dfefe7`, blob `7dc592b9` (2,012 lines, 237,726 bytes; `wc -lc` and `git rev-parse` match the brief), base `dbd54fe3` |
| Prior reviews | `wp9-5-note-r5-review-2026-11-22.md` (`d6938710`): REWORK REQUIRED, 0 Blocking, 3 Major, 11 Minor, 6 Info; r1 to r4 for background |
| Brief | `handoffs/wp9-5-gemini-note-r6-followup-2026-11-22.md` (the owner's pin decision, §1; scope rules, §2; other findings, §3), handover `wp9-5-gemini-note-handover-2026-11-21.md` |
| Worktree | `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note`, branch `docs/w9-wp9-5-design-note`, HEAD `95dfefe7` (read-only; `git status --short` empty before this report was written and after every scratch run) |
| Reviewer | fresh session, no author context; skill `adversarial-design-review`. The session was cut off once by an API rate limit and resumed; the worktree was re-checked clean on resumption |
| Date | 2026-11-22 (resumed 2026-11-23) |
| Verdict | **REWORK REQUIRED**: 0 Blocking, 3 Major, 9 Minor, 6 Info |

"note NNN" is a line number in the note at `95dfefe7`. Other `path:line` values are at `dbd54fe3` (`origin/main` is `4ca375a3`; its only code change since is a comment in `research_system/legacy/citations.py`, which is not a closure module; I re-read `git ls-remote origin refs/heads/main` and it still returns `4ca375a3`).

## 0. Summary

Revision 6 implements the owner's decision in the places the brief names, and it is much smaller (237,726 bytes against 258,423, 2,012 lines against 2,063; sections 1 to 16 fell from 221,935 to 200,393 bytes, 12 lines over 1,000 characters became 5, and the 4,336-character test row became eight rows). Rule 0.3 is gone as a rule (14 lines still mention it, 10 of them in sections 1 to 16 as "no Rule 0.3"; none states it as a requirement). The PR-time gate is gone from `admission-controls` (note 499, 618, 1283, 1371, 1514); nothing in that job calls `gh`, sets `GH_TOKEN`, adds a permission or changes `timeout-minutes: 20` (`ci.yml:137-140` confirms the current values and `fetch-depth: 0`). Post-merge runs make one walk with `baselines[-1]` (note 614). The facts reproduce: the 22 guarded commits in the 320-commit walk, 70 and 90 `CONVENTIONS.md` units, the 15-module closure with all recorded blobs equal to `git rev-parse dbd54fe3:<path>`, ruleset `20822054` (all pins), 56 evaluations and 32 bypasses in the live month window, the bare-clone time, the parent-and-child `python -S -P` isolation probe (script and `-m` forms), the 14-of-178 and 7-in-4-weeks edit rates, and 0 out-of-range citations (231 distinct pairs, 295 ranges, 456 range occurrences; 366 pair occurrences by my count against the author's 361, which is a counting difference, not a failure). The pin step rejected every traversal, absolute, backslash, dot, trailing-dot, trailing-space and device-name key I fed it (section 6). The two YAML blocks parse, every `run:` script passes `bash -n`, and the detector workflow has `on: workflow_dispatch` only, no `inputs`, `contents: read, pull-requests: read`.

Three defects remain, all in the owner's decision as carried into the note, none in the decision itself.

1. **R6-M1. "Incompatibility exits 2" is not what the note specifies.** The one place the note says what a tool does with an evidence file it cannot accept (§6.6 item 1, note 757) says exit `1`, which the owner ruled out ("never 0 and never 1"). The `main()` wrapper only catches exceptions that nothing handles, and the note handles this one. No test feeds an unknown format string.
2. **R6-M2. The old-versus-new comparison is not a runnable procedure, and its slice rule is still written as a gate.** The assembly step is an inline CI heredoc, the wrapper cannot assemble an arbitrary row, `<candidate>` is undefined, nothing computes the diff or matches the slice, yet Rule 0.2 (iv) and a §12.1 row assert pass/fail outcomes for a manual review.
3. **R6-M3. The retained `--verify-watched-to-fail` in `admission-controls` has no code root.** Run against the checkout, which is the natural reading, it recomputes hashes that bind the closure modules' bytes, so the first unrowed edit of any closure module turns the PR lane red for every PR. That is Rule 0.3 back as a PR-time gate, through a control the brief told the author to keep.

Nothing here asks Stephen to reverse his decision (section 1.4). Two omissions in "what it gives up" are put to him as plain statements (R6-m7, R6-m8), not as challenges.

### 0.1 Scope and size

**Unprescribed mechanisms.** None of substance. The "optional advisory Rule 0.2 row report" is allowed by brief §1.6, but it is unspecified and has a test row (R6-i4). `Option I1-include-seg` and `Option I1-py-minor` are the two choices R5-m5 and R5-i2 asked for. Nothing was added to the walk, the pin or the comparison beyond the brief.

**Superseded designs.** `tool_pin_commit`, `checkpoint`, `--record-checkpoint`, `--full-rewalk`, `verdict_digest`, `I1-narrow` and `walk_start` occur only in §18 to §20 (note 1615, 1616, 1683, 1701, 1713). `uv sync` occurs in negations (note 49, 1113, 1342) and in §18 (note 1642). `last_verified_commit`, `git worktree add` and `T_cand` do not occur. `Rule 0.2 (v)` occurs in the verdict sentence as a negation (note 616) and in §18 to §20.

**Do §1, §13, §14 and §16 match the body?** Mostly. They match its one defect: "exiting 2 on incompatibility" is restated at note 26, 498, 599, 603, 629, 1379 and 1444 while §6.6 item 1 says exit 1 (R6-M1). §1's first column calls rows "Handover §3 item"; its numbers diverge from the handover from item 14 (R6-i2).

## 1. Findings

### 1.1 Blocking

None.

### 1.2 Major

#### R6-M1. Incompatibility does not reach exit 2 under the note's own text

- **Claim (note 26, 498, 599, 603, 629, 1379, 1444; brief §1.4):** a pinned tool that cannot read production evidence "exits `2` (`ERROR`)", "never `0` and never `1`"; this "depends on R5-m1: every tool wraps `main()` and exits 2 on any uncaught exception". HR-3 (a): "exiting `2` cleanly on format incompatibility".
- **Evidence:**
  1. *The mechanism the brief relies on is an uncaught exception. The note replaces it with a handled one.* §6.6 item 1 (note 757): "if any evidence file present at `P1` or `C` fails JSON/schema validation, `tools/check_legacy_writes.py` fails closed (exit `1`) with `ERROR: post_merge_first_parent: invalid evidence file at <commit>:<path>: <reason>`". A manifest or ledger with a `format` string the pinned tool does not know (`w9-registration-manifest/3`, `w9-walk-baseline/2`) fails that validation by construction. The production readers already behave this way: `require_registered` raises `EvidenceRefused("W9 registration manifest does not have the fixed format")` at `evidence.py:122-123`, and a detector helper that calls it or its twin would have that exception caught and mapped to the line above, so the wrapper in note 659 never sees it.
  2. *The same ambiguity at the vault detector.* Note 902 says only "fails closed" for an empty `ACCEPTED_CL_EXPORT`; note 954 says production mode "reads `ACCEPTED_CL_EXPORT[-1]` ... without needing a detector rewrite". The nearby controls (note 1025) "must exit `1`". No exit code is stated for the stale-pin case.
  3. *No test.* §12.1 row 1325 covers "every tool's `main()` wrapper catches uncaught exceptions and exits `2`", the `"error"` key, one-sided and identical `ERROR`. Nothing feeds a known evidence file with an unknown `format`, or a malformed file, and asserts exit `2`. Row 1324 covers Rule 0 positives and negatives only.
  4. *`--verdict-json` has no representation for exit `1` "invalid evidence".* Note 616 gives an `"error"` key only for exit `2`. An old tool that meets a candidate with a new format and exits `1` has no `(rule, path)` pair to report, so its verdict can read as empty, and the diff against the new tool shows "new tool removed a violation", the opposite of "old tool could not read it".
- **Failure scenario:** a production PR bumps `registration-manifest.json` to a new format and nobody advances the pin. The post-merge run exits `1` with a message that looks like a rule violation. The owner expected a run that is red as `ERROR`; the operator cannot tell a stale tool from a real violation, and in a later comparison a stale `T_old` reads as clean. The run is red either way, so this is not a silent pass; the harm is classification, which is what the owner's "never 1" was written to protect. What would downgrade this finding: a sentence in §6.6 and a test that make unknown-format and unparseable evidence exit `2`.
- **Disposition:** fix now.
- **Proposed text:** in §6.6 item 1, replace "fails closed (exit `1`)" by: "An evidence file that cannot be parsed, or whose `format` string this tool does not know, is `ERROR`: exit `2` with `--verdict-json` printing the `error` key. Exit `1` is reserved for violations of Rules 0 to 3 on evidence the tool read." State the exit code of the empty-`ACCEPTED_CL_EXPORT` case in §8.2 as `1` when `ACCEPTED_CL_EXPORT` is empty at the pinned copy and the head is pre-L-0b, and see R6-m8 for the post-L-0b case. Add to §12.1 row 1325: "a synthetic evidence file with an unknown `format` at `C` exits `2` and, with `--verdict-json`, prints `error`; the same for unparseable JSON". Reword HR-3 (a).
- **Affected:** brief §1.4, R5-m1; note §1 (26), §6.2.2 item 2, §6.6, §8.2, §12.1, §13.2 HR-3, §14 claim 2, §16.1.

#### R6-M2. The comparison is not a runnable procedure, and its slice rule is still a gate

- **Claim (note 615 to 617, 722, 1325; brief §1.5):** "Specify it as a documented procedure using the detector's own output (assemble row `k-1` and row `k`, run each with `--verdict-json` over `(baselines[0]["baseline_commit"], candidate]`, and diff)"; "A test exercises the procedure on synthetic rows, including a difference, and both sides failing identically." The review evidence is "not a gate" (note 615).
- **Evidence:**
  1. *Assembly.* Note 615: "Assemble `baselines[k-1]` and `baselines[k]` via §6.2.3's confined `python -S -P` assembly." The only assemblers are the inline pin step in `legacy-write-detector.yml` (note 1163 to 1233) and the wrapper (note 630 to 635). The wrapper reads `origin/main`, takes only `--repo-root`, and also launches the three detectors and the controls, so it cannot assemble row `k` (that row exists only on the PR candidate). The CI step can: its heredoc takes `argv = <commit> <dir>` (note 1171). I confirmed this by extracting the heredoc verbatim and running it with two commits and two directories (`r6_two_rows.py`: row 0 gave `print('v1')`, row 1 gave `print('v2')`). So the procedure is feasible by hand-copying a heredoc out of a YAML `run:` step, and the note does not say so.
  2. *`<candidate>` is undefined.* On a PR branch tip, `rev-list --first-parent <b0>..<candidate>` walks the PR's own commits one by one, each mapped through `commits/<C>/pulls` with the 1, 2, 4 s retry (note 653) to "no merged PR". A merge ref or a `git commit-tree` squash is needed, and the note names neither.
  3. *Nothing computes the diff or matches the slice, yet the tests and Rule 0.2 (iv) assert outcomes.* Note 615 says "diff outputs, and attach to the PR" (manual). Row 1325 says a named `V[:8] | <rule> | <path>` difference "passes while unnamed or malformed line fails". Rule 0.2 (iv), evaluated by the pinned post-merge tool at every appended row, now includes "and lists every old-vs-new verdict difference (including Rule 0) one per line" (note 722). In revision 5 that clause was outside Rule 0.2 ("runs in `admission-controls`, not inside Rule 0.2"). A post-merge tool holds one tool's verdict; it cannot know the other's, so it can check line grammar at most. No component in the note has the two verdicts and a slice in hand.
  4. *The landing commit's SHA cannot be named.* The slice is a hash-bound register entry that must exist on `main` before the PR (Rule 0.2 (iii), `source_commit` an ancestor of `P1`). A squash or queue merge creates a new commit after review, so a difference at the candidate itself (the commit that introduces the new tool, the case R4-M1 item 3 cared about) has no `V[:8]` to write.
  5. *The success shape of `--verdict-json` is not defined,* so "diff" has no stable object to compare (key per commit, sorted pairs, no timings, no retry counts).
- **Failure scenario:** the first pin advance. Stephen, or an agent, cannot follow note 615 without reverse-engineering the CI step. A coder implements (iv) as "slice contains at least one verdict line or says none"; a difference in the candidate commit cannot be named; a typo in a slice line becomes a Rule 0 violation after merge, which cannot be acknowledged and stays red unless Stephen picks the exemption row (Owner Point C). Alternatively the coder builds a hidden comparator inside `test_w9_detectors.py` so the row 1325 outcomes can be asserted, which is the gate the owner removed, and the brief said to add no mechanism.
- **Disposition:** fix now (text and one test row, no new tool file).
- **Proposed text:**
  1. Write the procedure as numbered steps. (1) `git fetch origin pull/<N>/merge` and name it `<candidate>`, or build the squash candidate with `git commit-tree <PR tree> -p <pr_base>`. (2) Assemble two directories by running the §10.2 pin step body with `argv = <pr_base> <dirA>` and `argv = <candidate> <dirB>`, or add `--assemble-only --rev <rev> --out <dir>` to the existing wrapper (a flag on an existing file; say which). (3) Run the §6.2.2 command from each directory with `PYTHONPATH`, `PYTHONSAFEPATH=1` and `python -S -P`. (4) Diff the two JSON objects. (5) Write one slice line per difference.
  2. Define the JSON: `{"format": "w9-verdict/1", "error": null, "verdicts": {"<40-hex>": [["Rule 1", "path"], ...]}}`, sorted, no timing; on failure `{"format": "w9-verdict/1", "error": "<text>"}` and exit `2`.
  3. For a difference at the candidate itself, write `candidate | <rule> | <path>`; use `V[:8]` for older commits.
  4. Rule 0.2 (iv): delete the verdict clause or write "the slice also contains the verdict lines of the §6.2.2 procedure (their completeness is a review matter, `HR-3` (b))", and say the post-merge tool checks only that each line has the `V[:8] | <rule> | <path>` grammar and that `V` resolves in `(b0, C_k]`.
  5. Row 1325: replace "unnamed or malformed line fails" by a test of the procedure: two synthetic rows assembled, a difference reported, identical failure on both sides reported as `ERROR`, `ERROR` on one side reported as `ERROR`, row 0 skipping the comparison. Move "unnamed difference" to review.
- **Affected:** brief §1.5, R5-M1, R5-M2, R5-m1, R5-m2; note §6.2.2 item 4, §6.5 Rule 0.2 (iv), §12.1 row 1325, §13.1 MC-2, §14 claim 2.

#### R6-M3. `--verify-watched-to-fail` under `L1_LIVE` has no code root, and on the checkout it brings the lockstep back

- **Claim (note 499, 1283, 1371, 1514; brief §1.6):** "The `L1_LIVE` tripwire, the F1 tests, `--verify-watched-to-fail` and K1 stay in that job." An edit to a closure module without a new row "is **not** a violation" (brief §1.2, note 498).
- **Evidence:**
  1. §9.2 item 2 (note 1079 to 1099): each detector's hashed transcript includes `tool_git_blob` and `closure_blobs`, "the `{path: git_blob_id}` map of every module in `compute_detector_import_closure`". `--verify-watched-to-fail` recomputes the transcripts and fails "on mismatch" (note 1100). The recomputation depends on the bytes under `--code-root`.
  2. Note 1283: when `L1_LIVE is True`, the real `.research-system/evidence/w9/{detector-controls,walk-baseline,registration-manifest}.json` "exist and pass schema checks + `--verify-watched-to-fail`" in `admission-controls`. Note 1328 describes the True branch as "synthetic True", so the test passes in its own fixture.
  3. Nothing says which code root `admission-controls` uses. The assembly (note 1163 to 1233) exists only in the detector workflow and the wrapper. Note 1100 says "`--code-root` ... defaulting to `--repo-root` when omitted", a garbled sentence whose natural repair is "`--code-root` defaults to `--repo-root`", that is the checkout. The tools are standard-library only, so `PYTHONPATH=. python -S -P tools/run_w9_detector_controls.py` against the checkout works and needs no assembly step.
  4. With the checkout as code root, any PR that changes any of the 14 non-code-owned closure modules (14 of 178 first-parent commits in 90 days, 7 in the last four weeks, reproduced) or any WP9.5 tool changes a recomputed `closure_blobs` or `tool_git_blob`, so `output_sha256` no longer equals the recorded value, and the real-state test fails on that PR and on every later one until a pin advance re-records `detector-controls.json`.
- **Failure scenario:** after L-1, an ordinary PR edits `research_system/legacy/reader.py`. The detector is unaffected (it runs its pinned copy, as the owner wanted). `admission-controls` is red for that PR and every PR after it, because the F1 test recomputes against the checkout. The per-edit pin-advance burden and the unrelated-PR red (R5-i1) are back, through a control the brief told the author to keep. The note's controls do not catch it: the True branch is synthetic, so the fixture's checkout equals its pin.
- **Disposition:** fix now (one sentence and one test).
- **Proposed text:** in §9.2 item 3 and §10.3: "In `admission-controls`, `--verify-watched-to-fail` runs with `--code-root` set to a tree assembled from `HEAD`'s `baselines[-1]` by the §10.2 pin step body, never the checkout; `--code-root` has no default." Define "schema checks" in note 1283 as the top-level shape of the three files only (not rows, which would be a gating row check). Add a test: a synthetic repository with `L1_LIVE` true, a valid pin, and one non-code-owned closure module edited without a row, where the lane stays green. Repair the garbled sentence in note 1100.
- **Affected:** brief §1.2, §1.6; note §9.2, §10.3, §12.1 row 1328, §13.1 MC-9, MC-10, §14 claim 15, §16.7.

### 1.3 Minor

- **R6-m1. The pin step's post-write check passes when a later key aliases an earlier destination (note 1203 to 1230).** The check hashes each file right after writing it, so a second key that maps to the same file overwrites a file already verified and the step exits `0` with a tree that differs from the pin. I reproduced both forms. Keys `tools/Dup.py` and `tools/dup.py` with different blobs: exit `0`, one file on disk holding the second blob, so the first key's blob is absent (`r6_yaml_pin.py` case `case_collision`). Keys `tools/check_legacy_writes.py` and `tools/CHECK_~1.PY`: exit `0`, the long-name file holds the alias key's blob (case `shortname`; 8.3 names are enabled on this machine's `C:`, unknown on the hosted runner). R5-m7 asked that "the assembly is the control that must not depend on Rule 0.2 (ii)"; this is the same class (trailing-dot aliasing) one step on. Fix: after the loop, re-hash every key and require every `dest` to equal its pinned blob; reject keys that are equal under `casefold()` and any segment containing `~`.
- **R6-m2. The wrapper command is Git Bash only (note 632 to 633, 1955).** Run from Windows PowerShell 5.1, Stephen's primary shell, `git show ... | python -S -P - --repo-root .` re-encodes the stream: a wrapper containing `é—ü→` ran with ten `?` characters instead (`r6_wrap_test.py`: Git Bash received code points `0xe9 0x2014 0xfc 0x2192`; PowerShell received `0x3f` ten times; both exited `0` and printed the same flags, so nothing signals the change). A silently altered "pinned" wrapper is the thing R5-m6 set out to prevent. Fix: state `Git Bash` (or `cmd /c "<pipeline>"`) next to the command, and add `test_pinned_wrapper_is_ascii_only` beside `test_pinned_wrapper_is_self_contained_stdlib_only`.
- **R6-m3. The compared verdict names Rule 0.1 and Rule 0.2 only (note 616).** §6.5 has three Rule 0 items; item 3 (`detector-controls.json` monotonicity, note 727 to 728) has no label, and "Rule 0.3" is both the deleted lockstep and the natural label for item 3. A pin advance re-records `detector-controls.json` (note 1447), so item 3 is the Rule 0 check a tool change is most likely to touch, and it is the one the verdict cannot name. Fix: label the three items `Rule 0.1`, `Rule 0.2`, `Rule 0.3` in §6.5, say item 3 keeps the name, and delete "Rule 0.3" from the deleted-lockstep sentences ("the lockstep rule").
- **R6-m4. `tools/check_bypass_merges.py:160` points at `]` (note 658).** The `encoding="utf-8"` precedent is at `:141` (`_gh`, `subprocess.run(["gh", *args], ..., encoding="utf-8", ...)`). The bounds check passes; the meaning does not. The wrong line came from the R5 review's own text (R5-m9), so this is the reviewer's copy-forward error. Fix: cite `:140-144`.
- **R6-m5. The §12.3 estimates for unwritten code are unlabelled, and measurement contradicts two (note 1343, 1347).** "synthetic Git/pin/comparison/wrapper controls (`< 5s`)", "`--verify-watched-to-fail` (`< 2s`)" and "segmentation (`< 0.5s`)" are estimates, not measurements, and R5-m10 asked for labels. Measured: the pin step alone costs a mean 0.32 s per case (32 runs, 10.28 s, `r6_yaml_pin.py`), so the 19 cases the header counts cost about 6.1 s, above the `< 5s` allowed for pin, comparison and wrapper controls together. `--verify-watched-to-fail` includes the replay controls (note 1090 to 1095), and the bare clone alone is 1.99 to 2.07 s on this machine, so `< 2s` cannot hold if the replays are among the recomputed controls. The stand-in noise is stated as about 15% (note 619, 1343, 1996); three independent runs give 12.97, 44.03 and 77.7 s against 14.05, 34.46 and 62.84 s in the note (and 11.79, 34.85, 61.58 s in R5), a spread of up to 28%. None of this approaches Owner Point G's 300 s; the defect is the unlabelled number. Fix: mark the estimates "estimate, unwritten code" and drop "about 15%" for "up to about 25% in three runs".
- **R6-m6. The header lists verification that §21.1 does not contain (note 13, 1955).** "Checked here (`dbd54fe38` / worktree `HEAD`, §21.1)" includes "19 pin-heredoc cases" and a "stdin pipe wrapper" test. §21.1 has ten items and no pin-heredoc item; the wrapper test is one sentence in item 9 whose script (`wrap.py`) and meaning of "`1 True`" are not given. The 19 cases cannot be reproduced from the note. Fix: add §21.1 item 11 (the pin-step script and the case list) and give the wrapper script, or remove the two claims from the header.
- **R6-m7. "What it gives up" omits three consequences of keeping Rule 0.2 (ii) without the lockstep (note 720, 722, 1379, 1444).** (ii) requires every pinned blob to equal the tree at the appending commit, so: (a) a pin advance always snaps to the whole current tree, including unreviewed edits to the 13 or 14 non-code-owned modules that landed earlier, which the PR diff does not show (the PR changes one JSON file), so "judged by Stephen's review of the PR and its comparison output alone" means he reviews no code diff unless the procedure says to; (b) (iv)'s "rollback plus restored paths" cannot be satisfied unless production modules are reverted too; (c) a concurrent merge that changes any of the 13 or 14 modules between computing the row and landing it makes (ii) fail at `C_k`, and a Rule 0 violation stays red unless Stephen picks the exemption row. Owner Point C names no cause. This is not a challenge to the decision: the brief keeps (i) to (iv). Fix: add to §13.2 HR-3 and Owner Point I one sentence each for (a) to (c); add to the §6.2.2 procedure "attach `git diff <blob_{k-1}> <blob_k>` for every path in the slice" and "re-record `detector-controls.json` in the same PR" (note 1447 mentions the second only as a cost); list (c) and slice typos as the likely causes in Owner Point C.
- **R6-m8. "Fails loudly" is narrower than the note says, and L-0b needs a paired pin advance (note 629, 954, 1379).** A new evidence file, a new registration role or a new rule that the pinned tool does not read produces exit `0`, not an error. L-0b populates `ACCEPTED_CL_EXPORT` and `ACCEPTED_CONVENTIONS_CLASSIFICATION` in `accepted_w9.py`, which is in the pin; the pinned copy stays empty after L-0b, so the weekly vault run and the pre-batch wrapper stop with "ACCEPTED_CL_EXPORT is empty" (`check_legacy_log_baseline.py`) and the conventions check keeps the conservative 68-unit partition silently, until a pin advance. Note 954 ("without needing a detector rewrite") reads as if nothing else is needed. Fix: HR-3 and Owner Point I state that lag is silent for anything the pinned tool does not read, and §8.3 says the L-0b PR is paired with a pin advance.
- **R6-m9. "Code-owned, so Stephen merges it himself" holds only under Option I1 (note 497, 1444, 1450).** `walk-baseline.json` is code-owned only because I1 adds `/.research-system/evidence/w9/`. Under I2 (the eight current paths) a pin advance is an ordinary PR. The note makes B1 conditional on I1 but not the pin decision. Fix: one sentence in §6.1 and in the I2 option.

### 1.4 Findings against the owner's decision

None. I found nothing in the note's text showing that the pin, no-lockstep design cannot be carried out as decided, and nothing creating a failure the owner was not told about that is not already in R6-m7 and R6-m8. Those two are statements for §13.2 and Owner Point I ("what it gives up"), kept separate here: they are not requests to reverse any part of the decision. I also tried, and failed, to find a Blocking route to a silent pass: the pinned tool's own Rule 0.2 judgement of its own introducing row, and a rewritten history, are both accepted by the decision ("no machine checks a change of tool").

### 1.5 Info

- **R6-i1. The workflow blob in `detector_closure_blobs` is vestigial.** The assembled copy of `.github/workflows/legacy-write-detector.yml` is never executed; GitHub runs the pushed commit's workflow, and without the lockstep nothing compares the pinned blob with the tree. §1 (note 26) and §6.2.3 call the 22 entries "stdlib-only blobs". Say it is a record of what Stephen reviewed, or drop it (21 entries, one count change).
- **R6-i2. Restatements remain.** "no Rule 0.3" is repeated at ten body sites (note 26, 49, 498, 508, 616, 728, 1324, 1363, 1392, 1444); once in §6.1 and §20 is enough. §1's "Handover §3 item" column does not match the handover (items 14 and 15 are merged into row 14, 16 and 17 into row 15, and row 16 "Change logs and verification" is not a handover item). §15.2 item 5 is not labelled "added by this design note" although item 6 is (note 1431 to 1432).
- **R6-i3. The device-name check is narrower than `ntpath.isreserved` (note 1208).** A space before the extension (`CON .py`, `NUL .txt`), `CONIN$`, `CONOUT$` and superscript digits (`COM¹`, `LPT³`) are reserved by Python 3.13's own predicate and pass the heredoc's check. I ran them (`r6_pin_extra.py`): the first five reach the write and fail only because `git hash-object` exits `128` (an uncaught `CalledProcessError`, exit `1`, a raw traceback instead of the named refusal); `COM¹` and `LPT³.txt` were written as ordinary files on this Windows 11. Fail-closed by accident. Use `os.path.isreserved` and catch `CalledProcessError`.
- **R6-i4. The advisory Rule 0.2 row report has no specification (note 499, 618, 1283, 1325, 1371, 1514).** No trigger (it needs a base to find appended rows), no output path, no exit code; row 1325 and MC-10 assert it. Either give it one sentence (`HEAD` against `HEAD^1`, text to the job summary, exit `0`) or drop it from the tests.
- **R6-i5. Exit-code aggregation is unspecified.** The wrapper launches the three detectors and the controls (note 635); the note does not say that it preserves a child's `2` rather than collapsing to `1`. The pin heredoc exits `1` through `SystemExit(str)` and, on a malformed `walk-baseline.json`, a `KeyError` traceback (`format_drift` case); it is not one of the "tools" and the step is red either way, but the "never 1" sentence should say it applies to the tools.
- **R6-i6. Live re-check at review time.** Ruleset `20822054`: enforcement active, include `refs/heads/main`, `bypass_actors` one entry (`actor_id: 5`, `RepositoryRole`, `pull_request`), `pull_request` (`required_approving_review_count: 0`, `require_code_owner_review: true`, thread resolution true, `squash` only), `required_status_checks` (four contexts, `integration_id: 15368`, strict), `merge_queue` (`SQUASH`, 1, 1, 1, `ALLGREEN`, `check_response_timeout_minutes: 20`), `non_fast_forward`. Month window: 56 evaluations, 32 bypass, 24 pass; newest `4ca375a3` (bypass, `2026-11-21T22:00:56Z`); oldest `e3519ba7`. `commits/dbd54fe3.../pulls` returns `#446` with `merge_commit_sha` equal to the commit; `commits/4ca375a3/pulls` returns `#448`. The note's 57/33 (note 173, 292) is the earlier window and is dated as such (note 1869).

## 2. Citation and checks audit

**Citations.** `r6_cites.py` resolved every `path:line` form in the note (aliasing `06v`, `W9`, bare file names) against `git show dbd54fe3:<path>` (review and handoff files at the branch head or the main checkout) and bounds-checked every range including each part of a comma list: 231 distinct (file, spec) pairs, 295 ranges, 456 range occurrences, 366 pair occurrences, 0 unresolved files, 0 out of range. The same script on revision 5 returns the R5 review's 247 pairs, 312 ranges, 497 range occurrences, 404 pair occurrences, so the counts are comparable and the author's "361" is a different counting rule. Four pairs are new in revision 6 (`06v:190,594,603`, `evidence.py:179-218`, `check_bypass_merges.py:160`, the R5 review's `:19,112`). I read the first line of every citation on the 308 lines new or changed since revision 5 (`r6_changed_cites.py`) and the four new pairs: all correct except `check_bypass_merges.py:160` (R6-m4). `evidence.py:122-130` and `test_w9_evidence.py:62` (the `require_registered` closure and its extra-key refusal), `.github/CODEOWNERS` (eight paths equal to `GATE_FILES`, `test_ci_platform_policy.py:341-350`), `ci.yml:135-148` (`fetch-depth: 0`, `timeout-minutes: 20`, `permissions: contents: read`) and `06v:598-620` (the batch checklist and stop rules behind §15.2 items 1 to 4) were read and match.

**Section 21.1, run verbatim from the note (`r6_extract_items.py` writes each script to scratch unchanged):**

| Item | Note | Mine |
|---|---|---|
| 3 walk | 320 commits, 22 guarded, listed | 320 and 22, the same 22 hashes in the same order |
| 4 counts | 70 and 90 units; `[3,2,5,4,24,13,6,3,2,8]`, `[3,2,6,5,4,24,13,6,3,9,15]` | identical, 0 blockers |
| 5 closure | 15 modules | 15; every recorded blob equals `git rev-parse dbd54fe3:<path>` (13 shown in the note, `accepted_w9.py` and `evidence.py` placeholders by design) |
| 6 clone | `1.57` to `1.99` s; 58,133 objects, 28 packs, 335.09 MiB | 1.99 to 2.07 s; same counts |
| 8 ruleset | 16 pins; 56 and 32 | all pins match; 56 and 32 (R6-i6) |
| 9 isolation | script and `-m`, parent and child | reproduced: parent and child `no_site 1`, `safe_path true`, no `site-packages`, `research_system` and `tools` resolve inside the scratch tree, `research_system.cli`, `tools.check_merge_admission`, `yaml`, `pytest` raise `ModuleNotFoundError`; 0 non-stdlib imports in the 15 modules |
| 10 stand-in | 14.05, 34.46, 62.84 s; `24.04` measured, `68.92` and `125.68` extrapolated | 12.97, 44.03, 77.7 s; `26.35` measured at 60 commits; the extrapolated figures are `2 x` and labelled so (R6-m5) |
| edit rate | 14 of 178 in 90 days; 7 in 4 weeks | 14 of 178 (window from 2026-08-21), 7 |

**Pin step (`r6_yaml_pin.py`, the workflow's assemble step extracted verbatim, 32 runs, Git Bash, scratch repositories).** Valid keys assemble and exit `0`. Refused with a named message and no file outside the assembly directory: `../escaped.txt`, `/escaped_abs.txt`, `C:/escaped_drive.txt`, `tools\a.py`, `./tools/a.py`, `tools//a.py`, `tools/a.py/`, the empty key, `tools/a.py:evil`, an absent object, a tree object, a baseline commit off the first-parent chain, `tools/a.py.` (trailing dot), `tools/a.py ` (trailing space), `tools./a.py`, `tools /a.py`, `tools/nul`, `tools/CON.py`, `tools/aux.txt`, `tools/COM1`, `tools/LPT9.tar.gz`, `tools/prn/a.py`, an empty, wrong-digest or wrong-baseline I3 variable under `REQUIRE_I3_PIN=true`. Right I3 digest: exit `0`. Not refused by name: the alias, extra device-name and superscript cases (R6-m1, R6-i3). `walk-baseline.json` with an unknown shape: `KeyError` traceback, exit `1` (R6-i5). The env file and the `GITHUB_ENV` parse are unchanged from the case R5 closed.

**Stdin-pipe wrapper (`r6_wrap_test.py`).** `git --no-replace-objects show refs/remotes/origin/main:wrap.py | python -S -P - --repo-root .` works under Git Bash: `argv[0]` is `-`, `no_site 1`, `safe_path True`, the child launched as `[sys.executable, "-S", "-P", ...]` has the same flags, non-ASCII bytes arrive unchanged. Under Windows PowerShell 5.1 the stream is re-encoded (R6-m2).

**YAML.** Both blocks parse with `safe_load` (key `on` becomes `True`) and with `BaseLoader` (`on` is `{workflow_dispatch: ''}` for the detector and `{pull_request: ''}` for the U-3 probe); no `inputs`; detector `permissions: contents: read, pull-requests: read`, job `timeout-minutes: 15`, `actions/setup-python@v5` `3.13.5`; the five `run:` scripts pass `bash -n`; the 69-line heredoc parses. I did not run the U-3 probe or the U-4 script.

## 3. Disposition of every R5 finding

| ID | Disposition | Evidence |
|---|---|---|
| R5-M1 | **Resolved by the decision** | No PR-time gate to skip: note 499, 618, 1283, 1371, 1514. Pin advances are bypass merges by design (note 497); the landed commit is judged by the post-merge run on the new tool. The comparison is review evidence, not a gate. Residual: the procedure is not runnable (R6-M2). |
| R5-M2 | **Partly resolved** | Rule 0 is in the compared verdict (note 616) and Rule 0 differences cannot be acknowledged (note 617, 1702). Item 3 has no verdict label (R6-m3). The third Owner Point C exit is closed by the decision. |
| R5-M3 | **Resolved by the decision** | Nothing in `admission-controls` calls `gh`, sets `GH_TOKEN`, adds `pull-requests: read` or changes `timeout-minutes` (note 1514; `ci.yml:137-140`). The detector workflow sets `GH_TOKEN` and `pull-requests: read` itself (note 1113, 1240). New residual in the same job: R6-M3. |
| R5-m1 | **Partly resolved** | Wrapper and `"error"` key (note 657 to 659), both-sides-identical case (note 1325). The incompatibility path is handled and exits `1` (R6-M1). |
| R5-m2 | **Partly resolved** | One line per difference (note 617, 722); same-PR `acknowledged` for Rules 1 to 3 (note 617). The check cannot be what the note says it is (R6-M2 item 3). |
| R5-m3 | Resolved | Pre-code and rehearsal measurement rule, remedy is a design amendment (note 619, 1431), reconciled with G1 `300s` "excluding full-history walks" (note 1350, 1524). |
| R5-m4 | Resolved | Row 0 skips the comparison and keeps (i) to (iv) (note 615, 1325). |
| R5-m5 | Resolved | `I1-include-seg` (recommended: 11 patterns plus directory, 13 non-code-owned modules, 0 exemption) and `I1-exempt-seg` (10 patterns, 14 modules, exemption) (note 1448); the counts reproduce from `ci.yml`, `CODEOWNERS` and the 15-module list. |
| R5-m6 | **Resolved, with minor** | Self-contained wrapper, `test_pinned_wrapper_is_self_contained_stdlib_only`, exact command (note 52, 632 to 633). Shell dependence (R6-m2). |
| R5-m7 | **Resolved for the listed cases, with minor** | Post-write `is_file()` and `hash-object --no-filters`, trailing dot and space, device names (note 1208, 1223 to 1230); all listed cases reproduce. Alias collisions (R6-m1) and the narrower name list (R6-i3). |
| R5-m8 | Resolved | Child case in the probe (note 1955); reproduced. |
| R5-m9 | Resolved | `encoding="utf-8"` in the specification and the heredoc (note 658, 1172 to 1228) and a non-ASCII test (note 1327). |
| R5-m10 | **Resolved, with minor** | Extrapolated figures labelled (note 619, 1343, 1997); `walk_start` replaced. Noise stated as about 15% against up to 28% measured (R6-m5). |
| R5-m11 | **Partly resolved** | Bytes down 8.0%, long lines 12 to 5, the 4,336-character row split into eight; "verdict" lines 31 to 19. Restatements remain (R6-i2); "exits 2 on incompatibility" is restated at seven sites and is wrong at one (R6-M1). |
| R5-i1 | Resolved | Post-merge Rule 0 permanence scoped to the post-merge detector (note 1379, 1463). |
| R5-i2 | Resolved | `I1-py-minor` and `I1-py-patch` (note 1449); the wrapper's exact-patch check is gone. |
| R5-i3 | **Partly resolved** | `--verify-watched-to-fail` and the snapshot are in the §12.3 row (note 1347); the `objects/` and `refs/` scan is gone (note 1311). The figures are unlabelled estimates (R6-m5). |
| R5-i4 | Resolved | `404` and `497` match my count of the R5 note. |
| R5-i5 | Resolved | `check_response_timeout_minutes: 20` and the live values are in §21.1 item 8 (note 1869); they reproduce (R6-i6). |
| R5-i6 | Resolved | Parent `-P` and child `PYTHONSAFEPATH` plus explicit child flags (note 628). |

## 4. Owner points A to K

| Point | Premises checked | Recommendation | Missing or wrong |
|---|---|---|---|
| I (first) | CODEOWNERS has eight paths equal to `GATE_FILES`; ten patterns plus `w9_segmentation` and the directory; nine new files; 14 of 178, 7 in four weeks; the decision is recorded as decided by Stephen, 2026-11-22, for `P-090` (note 496, 613, 1438, 1444) | I1 with `I1-include-seg` and `I1-py-minor` is sound | The gives-up text omits R6-m7 and R6-m8; the pin decision is conditional on I1 (R6-m9); needs `P-090` and the `CONVENTIONS.md` amendment (stated) |
| C | 22 guarded commits and 320-commit walk reproduce; Rule 0 exit narrowed to a hash-bound exemption row or "detector stays red" (note 1463) | C1 with Stephen's choice between the two exits | The exits are put without the likely causes (R6-m7 (c), slice typos); the exemption is "not specified or built", as the brief says |
| A | `evidence.py:114-131`, `test_w9_evidence.py:62`, the three WP9.4 files, `wp9-4-1-record.md:114,130` | A1 sound | none new |
| B | Conditional on I1 (stated) | B1 sound | none new |
| D | `evidence.py:190-252`, `acceptance.py:121-136` | D3 sound | none new |
| E | Four gate sites by citation | E1 sound | none new |
| F | `ci.yml:166-216`, `:210`, `ADMISSION_CONTROL_MODULES`, `test_ci_platform_policy.py:226,228`; the smaller edit list (a module added, a unit-lane departure row) | F1 sound once the code-root sentence is added | `--verify-watched-to-fail` code root (R6-M3); the advisory report is unspecified (R6-i4) |
| G | `03-decisions-and-open-questions.md:5919-5923` | G1 until profiled | none new (the 600 s walk rule is separate, note 1524) |
| H | Unchanged | H1 sound | none new |
| J | `accepted_w9.py:86-88` mirror; leaf module | J1 sound | L-0b needs a paired pin advance (R6-m8) |
| K | `06v:491-492`; self-judgement stated honestly | K1 sound | none new |

Register entries each option needs, as the note states them, are complete and unchanged in kind: A1, D3 and E1 each need a dated WP9.3 amendment, an independent review and a `P-090` entry; H1 a dated W9 §4.2 amendment; I1 the `CONVENTIONS.md` amendment; C, B and the evidence formats rows in `06v-addendum-2026-11-10-w9-paths.md`; F1 and K1 edit code-owned `ci.yml`. None of A, D, E, I or F falls inside P-089's Boundary sentence (`03-decisions-and-open-questions.md:6141-6143`).

## 5. Consistency matrix for the revision 6 mechanisms

| Invariant | Enforcement point | Test | Result |
|---|---|---|---|
| An incompatible pinned copy exits 2, never 0 or 1 | `main()` wrapper; §6.6 item 1 | Row 1325 (uncaught exceptions only) | Contradicted by §6.6 item 1 (R6-M1) |
| A closure edit without a row is not a violation | Rule 0.3 deleted; `baselines[-1]` pin | Row 1324 | Sound for the post-merge tool; broken for the `L1_LIVE` lane (R6-M3) |
| A pin-advance row is valid when appended | Rule 0.2 (i) to (iv) post-merge | Row 1324 | (i) to (iii) sound; (iv)'s verdict clause cannot be checked (R6-M2); (ii) has consequences not stated (R6-m7) |
| The comparison is review evidence and includes Rule 0 | §6.2.2 item 4 | Row 1325 | Not a runnable procedure (R6-M2); Rule 0 item 3 unlabelled (R6-m3) |
| The PR-time gate is gone and nothing needs a token | §10.3, §16.7 F1 | `L1_LIVE` test | Sound for `gh`, token, permissions, timeout; `--verify-watched-to-fail` is the exception (R6-M3) |
| The post-merge run makes one walk with `baselines[-1]` | §6.2.2 item 4; §10.2 | Pin-step controls | Sound (section 2 and my 32 runs) |
| The pin step writes only the assembled tree and verifies it | §10.2 heredoc | Row 1328 | Sound for traversal, absolute, dot, space, device names; alias keys pass (R6-m1) |
| The detector and its children are isolated | `python -S -P`, `PYTHONSAFEPATH`, explicit child flags | `test_detector_closure_is_stdlib_only`; §21.1 item 9 | Sound; reproduced |
| The wrapper is one stdlib file run from `origin/main` | `test_pinned_wrapper_is_self_contained_stdlib_only`; the command | Row 1328 | Sound under Git Bash; PowerShell 5.1 alters non-ASCII (R6-m2) |
| The walk cost is bounded | 600 s pre-code and rehearsal rule; remedy a design amendment | `UNVERIFIED-5` | Sound; reconciled with G1 |
| Rule 0 exits are rare and put to Stephen | Owner Point C | none | Sound; causes not named (R6-m7) |
| Detector controls bind the pinned code | §9.2; `--verify-watched-to-fail` | Row 1328, `L1_LIVE` | Needs the code root (R6-M3) |
| Row 0 creation has no previous pin | §6.2.2 item 4 | Row 1325 | Sound |

## 6. What was checked and found sound

- **Rule 0.3 and the PR-time gate are gone as requirements.** Every remaining "Rule 0.3" is a negation or history; every "PR-time" in sections 1 to 16 describes what was removed. Owner Point F no longer edits `permissions`, `env` or `timeout-minutes`; I read `ci.yml` and confirmed those three would not need to change for anything the job still runs.
- **One walk, one tool.** The workflow assembles `baselines[-1]` only, the wrapper does the same, and no second tool, checkpoint or stored verdict remains outside §17 to §20.
- **The pin step.** The 32-run battery, the parent-and-child probe and the heredoc's `argv = <commit> <dir>` form (which makes assembly of any row possible) all behave as described.
- **Owner Point C is narrowed correctly** to the post-merge Rule 0 exit (note 1463), and the exemption is described, not built, as the brief says.
- **Attacks that failed.** (1) Writing outside the assembly directory through a traversal, absolute, drive-letter, backslash or alternate-data-stream key: refused. (2) A pinned tool reading checkout code through `sys.path`: parent and child isolated. (3) A hidden second gate through `admission-controls` needing a token: none found. (4) `admission-controls` lacking history for the retained tests: `fetch-depth: 0`. (5) The stop rule contradicting Owner Point G: reconciled, "excluding full-history walks". (6) A restatement that narrows the "no machine checks a tool change" statement: none; §13.2 HR-3, §16.1 and §6.1 agree. (7) A superseded design left in the body: none.

## 7. Coverage of the handover's 17 items and §15.1's gates

| # | Item | Result |
|---|---|---|
| 1 | Scope, protected identities | Settled (§2.2). |
| 2 | Ruleset read | Settled; pins verified live. |
| 3 | U-3 | Probe specified; gate in §15.1 item 1; `commits/<sha>/pulls` is still read only by the detector workflow, which has `pull-requests: read`. |
| 4 | First-parent detector | Evidence timing, Rules 0 to 3, pin and one walk settled; exit-2 semantics (R6-M1) and the comparison (R6-M2) not. |
| 5 | M-6 export | Settled; residual `HR-7`. |
| 6 | Shared-surface rule | Settled. |
| 7 | `CONVENTIONS.md` check | Settled; K put to Stephen. |
| 8 | Vault detector, D-5 | Settled; L-0b pin advance unstated (R6-m8). |
| 9 | U-4 | Metadata equals the brief; script unchanged; gate in §15.1 item 2. |
| 10 | Controls file | Code root for the `L1_LIVE` lane missing (R6-M3). |
| 11 | Merging is not going live | Settled; green `workflow_dispatch` on the L-1 commit is an exit criterion (note 1272, 1422). |
| 12 | Where controls run | Settled. |
| 13 | Tests and budget | Inventory split into eight rows; estimates unlabelled (R6-m5). |
| 14 | Research assurance | MC and HR split; HR-3 overstates "exit 2" (R6-M1). |
| 15 | Claims for review | 16 claims; claim 2 carries R6-M1 and R6-M2. |
| 16 | Stop rules | §15.1 (five items) and §15.2 (six) match `06v:610-620` for items 1 to 4; items 5 and 6 are added and item 5 is not labelled (R6-i2). |
| 17 | Owner points | Eleven, in the brief's order I, C, A, B, D, E, F, G, H, J, K. |

§15.1 gates: U-3 (item 1), U-4 dry run (item 2), Owner Points decided (item 3), single scratch-store profile (item 4) and the hosted walk time (item 5, `UNVERIFIED-5`) are all present; the wording "all four items below" counts four and names a fifth, which is a slip (note 1414).

## 8. Revision plan

**Immediate corrections (author, no owner decision):**
1. R6-M1: §6.6 item 1 and §8.2 exit codes, one §12.1 case, HR-3 (a) and the six restatements.
2. R6-M2: write the comparison as numbered steps with `<candidate>`, the assembly command, the JSON shape and the candidate-commit slice rule; narrow Rule 0.2 (iv); rewrite row 1325 as a test of the procedure.
3. R6-M3: code-root sentence in §9.2 and §10.3, a "schema checks" definition, one test, repair of note 1100.
4. R6-m1 to R6-m6, R6-m9, and R6-i1 to R6-i5 as written.

**Owner decisions after revision 7:** I first (with the gives-up additions R6-m7, R6-m8, R6-m9), then C (with causes), F (with the code root), then A, B, D, E, G, H, J, K unchanged.

**Later-work dependencies:** unchanged from revision 5: the U-3 probe and the U-4 dry run before code; the unconditional scratch-store profile; a full-walk time with real rules, PR mapping and the whole detector workflow on `windows-latest` (`UNVERIFIED-5`); dated WP9.3 amendments and independent reviews for A1, D3 and E1; a dated W9 §4.2 amendment for H1; the L-0b export and classified list (with a paired pin advance); the pre-L-1 rehearsal and a green dispatch run on the L-1 commit.

**Residual risks the note should keep stating:** the detector is post-merge and a human merge is the only preventive control for every pin advance and for the code-owned paths; a pin advance is judged by Stephen's review alone and snaps to the whole current tree; lag is silent for anything the pinned tool does not read; a post-merge Rule 0 violation stays red unless Stephen picks the exemption row; the weekly vault run is self-attested; the CI token may not read `rule-suites` (D-8); the `CONVENTIONS.md` check does not see sub-heading or ordering edits outside units; the M-6 exporter runs from the checkout.

## 9. Commands run

All read-only on the repository. `git status --short` was empty at the start, after the resumption and after the last scratch run; this report is the only file added. No vault file was read or opened, the U-3 probe and the U-4 script were not run, no workflow was run, no repository variable was read, nothing was pushed, and every `gh api` call was a GET.

- `gh api` GETs: `repos/ZK-Theory/TDL/rulesets/20822054` (with `--jq`), `rulesets/rule-suites?ref=refs/heads/main&time_period=month&per_page=100` (`--paginate --slurp`, saved to scratch), `commits/dbd54fe3.../pulls`, `commits/4ca375a3/pulls`. `git ls-remote origin refs/heads/main` (read).
- `git` in the worktree: `rev-parse`, `show <rev>:<path>` (note at `83b4ae6f` and `95dfefe7`, `ci.yml`, `CODEOWNERS`, `evidence.py`, `test_w9_evidence.py`, `check_bypass_merges.py`, `test_ci_platform_policy.py`, the 06v plan, `wp9-4-1-record.md`), `log --first-parent --since` (edit rates), `diff --stat 83b4ae6f 95dfefe7`, `count-objects -vH`, `status --short`. Scratch repositories were created and committed under the scratch directory only.
- Scratch scripts in `C:\Users\steph\AppData\Local\Temp\claude\e088a017a981a492\f302c5e4-50e0-4fcc-b0af-3a36e9983c74\scratchpad\r6`, written with the Write tool and run with the worktree `.venv` Python or the base 3.13.5 interpreter with `PYTHONDONTWRITEBYTECODE=1`: `r6_size.py`, `r6_cites.py`, `r6_newcites.py`, `r6_changed_cites.py`, `r6_suites.py`, `r6_yaml_pin.py`, `r6_pin_extra.py`, `r6_reserved.py`, `r6_two_rows.py`, `r6_wrap_test.py` (with `wrap_payload.py`), `r6_extract_items.py`, and the extracted `item_3.py`, `item_4.py`, `item_5.py`, `item_6.py`, `item_9.py`, `item_10.py` run unchanged. Note copies `note_r6.md` and `note_r5.md` are in the scratch directory.
- One deviation to disclose: I ran one `python -c` inspection command (to summarize the saved rule-suites JSON). It wrote nothing and failed on a path; I replaced it with `r6_suites.py`. No file was composed with `python -c` or a heredoc.
- File reads: the note in full (all 2,012 lines), the r5 review, the brief, the handover's item list, `ci.yml` (`1-30`, `130-222`), `CODEOWNERS`, `test_ci_platform_policy.py:341-375`, `06v:598-622`.
- Not run, as instructed: the U-3 probe; the U-4 dry run; anything reading the vault; the Actions variable read.
- Not verifiable here: `private: false` (note 256); who may write Actions variables (`UNVERIFIED-4`); how the hosted runner parses a CRLF `GITHUB_ENV` file; whether 8.3 short names are enabled on the hosted runner's temp drive (R6-m1 reproduced on this machine's `C:`); the current wall time of the detector workflow on `windows-latest` (`UNVERIFIED-5`); the behaviour of the six unwritten tools (exit codes, JSON shape, `--code-root` default), which I could only read from the note; PowerShell 5.1 behaviour on any machine but this one; the scratch-store profile (`UNVERIFIED-3`); the weekly operator run.
