REWORK REQUIRED

# Independent adversarial review: WP9.5 design note, revision 3

| Field | Value |
|---|---|
| Subject | `docs/plans/agentic-research-system/transition/w9/wp9-5-design-note.md`, revision 3, commit `092db1f1`, blob `3c6931b7` (1,847 lines; `wc -l` and `git rev-parse` match the brief), base `dbd54fe3` |
| Prior reviews | `wp9-5-note-r2-review-2026-11-21.md` (`3cf35bec`): REWORK REQUIRED, 0 Blocking, 5 Major, 16 Minor, 6 Info; `wp9-5-note-r1-review-2026-11-21.md` (`edb9acc6`) for background |
| Worktree | `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note` (read-only; `git status --short` empty before this report was written; the branch adds only the note and the two earlier reviews) |
| Reviewer | fresh session, no author context; skill `adversarial-design-review` |
| Date | 2026-11-22 (file name follows the brief) |
| Verdict | **REWORK REQUIRED**: 0 Blocking, 3 Major, 13 Minor, 4 Info |

"note NNN" is a line number in the note at `092db1f1`. Other `path:line` values are at `dbd54fe3` (`origin/main` is `4ca375a3`; its only code change is a comment in `research_system/legacy/citations.py`).

## 0. Summary

Revision 3 is a second large step forward, and almost everything that can be checked against bytes is now right. I re-derived the 22-row first-parent table (all 22 rows, including the new #419 and #425), the 15 / 20 / 22 import-closure figures with an independent AST walker (all 13 recorded blobs equal `git rev-parse dbd54fe3:<path>`), the `CONVENTIONS.md` unit counts, the ruleset pins (live GET), the U-4 dry-run script (run against a synthetic vault), the two YAML blocks (parse; `bash -n` on every `run:` script; the embedded heredoc parses) and about 250 `path:line` citations. Two citation slips and one provenance overclaim remain (R3-m7). The fabrication problem of revision 1 is gone.

The remaining defects are all in the mechanisms revision 3 added to answer R2-M1 and R2-M2, and they are design defects, not wrong facts.

1. **The detector's upgrade path cannot run (R3-M1).** Rule 0.3 requires a closure edit to be accompanied by a `baselines` row that names a `tool_pin_commit`, but under the squash queue that commit does not exist until the edit has merged. The note says both "same PR" (note 817) and "a subsequent pin-advance PR" (note 685). Under the second reading the edit commit stays red for ever. Separately, an appended `baselines` row is validated only when the same commit edits a closure file, so a commit that only re-points the tool is unconstrained, and no test shows a legitimate upgrade ending green. The wording of MC-2, §6.2.3 and claim 2 ("no commit can modify ... without ...") describes prevention that does not exist for the closure modules that are not code-owned.
2. **The checkpoint is a free, unverified skip (R3-M2).** A `checkpoints` row is accepted on append-only alone, is read from the head being judged, and so lets any merged PR make every earlier commit unreachable without the decision reference that `acknowledged` rows need. The `--full-rewalk` diff has nothing to diff against.
3. **An acknowledged Rule 3 violation waives the WP9.3 half of O-32 (R3-M3).** The acknowledgement silences the detector but nothing adds the missing `shared-surface-changes.json` entry that WP9.3's acceptance gate reads.

Nothing here asks Stephen to reverse an accepted decision. Revision 4 should be short: one rule for appended `baselines` rows and the upgrade sequence, one rule for checkpoint validity, one sentence for Rule 3 acknowledgements, and the minors below.

## 1. Findings

### Blocking

None.

### Major

#### R3-M1. The detector upgrade protocol is unsatisfiable under the squash queue, contradictory, under-enforced for appended `baselines` rows, and untested for the legitimate case

- **Claim (note 572, 685, 714, 817, 1509, 1537):** a closure change needs "a hash-bound pre-existing decision ref"; "a subsequent pin-advance PR appends a new entry" (685); Rule 0.3 requires that "`walk-baseline.json` at `C` carries a newly appended `baselines` entry ... updates `tool_pin_commit`" (817); "no commit can modify `evidence.is_ancestor` ... without both changing a Rule-0-guarded file and passing an updated whole-tree pin" (714); MC-2 and claim 2 say the mechanism, with I1, closes all five R1-B1 / R2-M1 to M3 surfaces.
- **Evidence:**
  1. The workflow accepts a pin only if `tool_pin_commit` is on `origin/main`'s first-parent chain and every `detector_closure_blobs` entry equals `git rev-parse <pin>:<path>` (note 1340-1347). A row naming the new tool can therefore only be written after the commit that carries the new tool has merged. A same-commit row can only name `P1` (old tree; the blob check fails) or the squash commit itself, which the PR cannot know. This is the argument the note itself uses to reject D1 (note 867).
  2. Note 685 and note 817 cannot both hold. Under 685, the closure edit `M` has no row at `M`. Rule 0.3 is evaluated at `M` on every later run (the new tool walks from `checkpoints[-1]` or `baselines[0]`, note 701), so it stays red. The `acknowledged` list is specified for `Rule 1`, `Rule 2` and `Rule 3` (note 660, 692); acknowledging a Rule 0 violation is not specified. `--record-checkpoint` needs every commit clean (note 702).
  3. Rule 0.2 says `baselines` is "strictly append-only" (note 812) and nothing more. The validation of a new row (hash-bound reference at `P1`, slice names each changed path with `new_blob[:8]`, strictly later pin) exists only as prose in note 685 and as a side condition of a same-commit closure edit in note 817. A commit that edits only `walk-baseline.json` to append a row re-pointing `tool_pin_commit` to any older on-chain commit, with any existing reference, triggers neither rule.
  4. `tests/tools/test_w9_detectors.py` (note 1476, row 4) lists negative controls for closure edits. No control shows that edit `M` followed by pin-advance `A` ends green, and none attacks a re-pointing-only row or a rollback to an older pin.
  5. The 14 `research_system/` closure modules are not code-owned (note 1589: "or optionally added to CODEOWNERS too"); `tools/w9_segmentation.py` has its D-4 blob pin and `test_w9_segmentation.py` instead. For the 14, Rule 0.3 is detective, and by (1) and (2) it cannot clear. Seven W9 package PRs since 2026-10-28 (`31f675fe`, `23f8f737`, `6aeb3b31`, `baea2c13`, `cc81b733`, `95871b38`, `dbd54fe3`) edited the 15 existing closure modules; 14 of 178 first-parent commits in 90 days touched them (my `git log --first-parent --since=2026-08-21`).
- **Failure scenario:** after L-1, WP9.6 edits `research_system/legacy/evidence.py` as WP9.3 and WP9.4 did. `main` goes red at that merge. No sequence of PRs turns the walk green except weakening Rule 0.3 or disabling the workflow. This is R2-M2(a) and R1-M5 again, applied to the control's own maintenance, and the operator response R1-M5 warned about (ignore the red) follows.
- **Impact:** operational bypass; the integrity of the pinned-tree design that closes R2-M1 depends on a protocol that cannot run. B, C and the L-1 guard all assume it.
- **Disposition:** fix now (design text and tests); no owner decision beyond Owner Points C and I.
- **Proposed text, either of two forms:**
  - **(A) Pin by content, not by commit.** Replace `tool_pin_commit` with the recorded blob map plus the `pyproject.toml` and `uv.lock` blobs. The workflow assembles `$RUNNER_TEMP/w9-detector` with `git cat-file blob <recorded blob>` for each recorded path, then `uv sync --locked` there. Blob IDs are content hashes, so a same-PR row is satisfiable, and an import outside the recorded closure fails with `ImportError` (closure exactness for free).
  - **(B) Keep the commit pin and state the acceptance rule.** A closure edit at `M` is accepted iff `walk-baseline.json` at head holds a row appended at some `A` in `(M, head]` with `tool_pin_commit == M`, blobs equal at `M`, and a reference that resolves at `P1(A)`. The window `M..A` is red by design and blocks batch start. Rule 0.3 is evaluated against head's rows.
  - **In both:** add to Rule 0.2 "every appended `baselines` row: pin on the chain and strictly later than the previous row (or an identical-or-newer blob map under A), blobs equal, reference hash-bound at `P1`, slice names every path whose blob differs from the previous row's with `new_blob[:8]`"; add the positive control (edit then pin-advance ends green) and negative controls (re-pointing-only row; rollback to an older pin); reword MC-2, note 714 and claim 2 to "preventive for code-owned paths, detective for the rest".
- **Affected:** R2-M1, R2-M3; note §6.2.2 item 2, §6.2.3, §6.5 Rule 0, §10.2, §12.1, MC-2, claim 2; Owner Points C and I.

#### R3-M2. A checkpoint is an unverified, reference-free skip of every earlier commit; the `--full-rewalk` diff has nothing to compare

- **Claim (note 699-703, 1537):** checkpoints let "a reviewed tool upgrade ... re-evaluate only new commits", protected by Rule 0.2 and I1; `--full-rewalk` reports "a structured diff".
- **Evidence:**
  1. Rule 0.2 requires only that `checkpoints` be append-only (note 812). Nothing recomputes `verdict_digest` or re-walks the range a new row skips. `--record-checkpoint` is a convenience of the tool, not a gate on what a PR may commit.
  2. The run for head `C_cp` reads the new row from head (note 701) and starts at `last_verified_commit`. A row naming `P1(C_cp)` makes every earlier commit unreachable, including a red one. It needs no `disposition_ref`, unlike an `acknowledged` row (note 696-697). It is therefore a blanket acknowledgement that bypasses the accountability R2-M2 asked `acknowledged` to provide.
  3. While `checkpoints == []` a pin advance re-walks from `baselines[0]` with the new tool and no diff (note 701). R2-M2(b), "a tool edit silently changes the verdict on history", is open until the first checkpoint exists.
  4. `--full-rewalk` "compares per-commit `(commit, rule, path, verdict)` results against the stored checkpoint summary" (note 703). The stored summary is a SHA-256 digest (note 700). No old verdicts are stored, and re-deriving them needs the tool at `checkpoints[i].tool_pin_commit`, which the note does not specify.
- **Failure scenario:** a violating commit `V` is red. A later PR (code-owned, Stephen merges) appends a checkpoint naming its own parent. The next run starts after `V` and is green. The register shows nothing about `V`.
- **Impact:** integrity (history can be cleared without a record) and R2-M2's second half not closed.
- **Disposition:** fix now.
- **Proposed text:** "A checkpoint row is valid only if, in the first run that sees it, the detector walks `previous.last_verified_commit..row.last_verified_commit` with the pinned tool, honouring `acknowledged`, and the recomputed `verdict_digest` equals the row's. A mismatch is `ERROR: Rule 0: checkpoint digest mismatch`." Require a checkpoint row in the same PR as every pin advance (no un-checkpointed advance). Store the per-commit verdict tuples (small) beside the digest, or define the old verdicts as the output of the old pin's tool; `--full-rewalk` diffs against them. Add the negative control "a checkpoint that skips a known red commit fails".
- **Affected:** R2-M2; note §6.2.2 item 4, §6.5 Rule 0.2, §12.1, claim 2; Owner Point C.

#### R3-M3. Acknowledging a Rule 3 violation clears the detector but leaves WP9.3's O-32 half blind

- **Claim (note 692-698, 862-864):** an `acknowledged` row exempts the exact tuple `(commit, rule, path, old_blob, new_blob)`. Rule 3 requires a W9 §4.3 record and a `shared-surface-changes.json` entry (note 862-864).
- **Evidence:** O-32 has two halves (`06v:212`): the detector fails when the entry is missing, and WP9.3's acceptance reads the list at the store's `git_head` and refuses stale observations of affected results (`acceptance.py:121-136`, `evidence.py:190-252`; note 872). The acknowledgement rules (note 696-697) check the register slice only. Nothing makes the missing list entry appear.
- **Failure scenario:** a shared-surface PR merges without an entry; Rule 3 goes red; Stephen acknowledges it; the detector is green. The list still has no entry for that change, so `check_change_list` finds nothing for the affected registrations and admits observations taken before the change. P-089 item 3 ("a merged shared-surface change with no entry ... fails the detector") is met in letter only.
- **Impact:** validity of closed-reference acceptance for results read under a changed contract.
- **Disposition:** fix now.
- **Proposed text:** "An acknowledgement of Rule 3 is valid only if `shared-surface-changes.json` at head holds an entry `(pr_number(commit), s, b_old, b_new, affected_registrations)`. A late entry is allowed because WP9.3 reads the list at the store's `git_head`; its append is a Rule 0.2 append." Add the control "acknowledgement without the late entry fails".
- **Affected:** R2-M2, R1-M6; note §6.2.2 item 3, §6.5 Rule 3, §12.1; Owner Points C and D.

### Minor

- **R3-m1. Option I3 fails open, and its premises are unverified (note 1313-1336, 1589).** The workflow skips the anchor when `vars.W9_DETECTOR_PIN` is empty (`if var_raw:`), so deleting or never setting the variable silently disables the second anchor that I3 exists to provide. Post-L-1 an empty value must be an error when I3 is selected. The claim that the variable is "admin-only" is uncited. I could not verify who can write repository variables (no variable read was permitted, and the note gives no source). The pin-resolution script is inline in the YAML and no test executes it (R3-m12).
- **R3-m2. Operator-machine detector runs are not pinned (note 1536, 1589; `06v:603-604`).** The pre-batch runs are the ones that gate a batch (D-5, "run all four detectors"). The note pins only the CI workflow. On the operator machine the detectors, and `tools/export_w9_registration_manifest.py` with its 161-module import closure (`research_system/cli.py` seed, my walker), run from whatever is checked out. `research_system/legacy/accepted_w9.py`, which holds `ACCEPTED_CL_EXPORT` and the new `ACCEPTED_CONVENTIONS_CLASSIFICATION` (the objects that define the baselines), is in the closure but not code-owned. Specify a wrapper that runs the batch gate from the pinned tree, and add `accepted_w9.py` to the I1 CODEOWNERS list (it is already governed code under the WP9.3 binding-advance fixtures, `test_w9_wp9_3_binding_head.py:199-217`).
- **R3-m3. The cost of the closure rule is not stated (Owner Points I and C).** R2-M5 asked for the bypass-merge cost; the closure adds another. Every edit to any of the 14 `research_system/` modules after L-1 needs a register entry naming the path and blob, a pin-advance PR, a controls re-record (`--verify-watched-to-fail` binds `closure_blobs`, note §9.2) and a bypass merge. Seven W9 PRs touched the closure in the last four weeks (R3-M1 evidence 5). State the cost, and let Stephen weigh narrowing the closure (for example, by moving the few reader helpers the detectors use into `tools/`).
- **R3-m4. The integration-test lane is mis-described (note 1477, 1493).** "Selected on PRs via `tools/affected_research_tests.py`" is true only when a `research_system/` source or a `tests/research_system` helper changes. A PR that edits only `tools/check_legacy_writes.py` or `tools/_w9_detector_evidence.py` selects nothing (`affected_research_tests.py:120-143`: `module_name` returns None for `tools/`, and the `pinned` branch needs a `.research-system` pin). The W9-T7 replay and the O-13 end-to-end control therefore run for detector edits only in the nightly run, which is advisory (`research-system-suite.yml:8-9,15,17`). Conversely every `.research-system/evidence/w9/` PR (each weekly vault-run PR) selects every contract test. State both, or place the T7 replay under `tests/tools/` in `admission-controls`.
- **R3-m5. Section 15.1 item 4 is conditional (note 1569-1570).** It reads "If considering tightening Owner Point G ...". The follow-up asked for the scratch-store profile as an unconditional pre-code step (R2-m13), and the lead sentence of §15.1 says all four items are required. Make item 4 unconditional or say G1 needs no profile.
- **R3-m6. The U-4 dry-run script omits the detector's root checks (note 447-477 against 416-428).** It asserts only `not is_symlink() and not is_junction()`. The three checks in §4.3.2 that the detector applies (abspath equals `resolve(strict=True)` under `normcase`, disjointness from `repository_root`) are not exercised, so a clean dry run does not predict a detector refusal caused by an ancestor reparse point. Add them to the script as printed booleans. (The script itself runs as written: I ran the note's text against a synthetic vault; it printed only counts, hashes, `link_count`, `canonical_target`, `file_facts` and `(row_ordinal, start_line, end_line, blocker_reason)` for two duplicate-anchor blockers, and raised no `KeyError`.)
- **R3-m7. Citation and provenance slips.** (a) Note 1595: "`.github/workflows/ci.yml:18` is in `.github/CODEOWNERS`" should read `.github/CODEOWNERS:18`; line 18 of `ci.yml` is a comment. (b) Note 1823 cites `wp9-5-note-r2-review-2026-11-21.md:162` for the bare-clone timing; that line is the CONVENTIONS "Inserted units" row; the timing is at `:218`. (c) The header (note 13) and the §20.1 introduction (note 1695: "items 1-6 and 8-9") say the 15-module AST closure was "independently reproduced" in the R2 review. R2 reviewed `0c9a90ed`, which had no closure; R2-M3 asked for it. I have now reproduced 15 modules and every recorded blob, so the figure is right and the provenance sentence is wrong. This is the R2-m4 pattern in a smaller form. (d) Note 41 and note 1232 say "closure digest"; the transcript carries the `closure_blobs` map, not a digest.
- **R3-m8. The immutability snapshot still includes shared refs (note 1464).** It records `refs/heads/` and `refs/tags/` under `--git-common-dir` by `(size, mtime_ns)`. A sibling worktree committing on its own branch (the project's normal state) changes a file there during the test. This is the flake R2-m16 describes. Compare the value of the checked-out branch's ref and the tag list, or run the full snapshot in CI only.
- **R3-m9. The I1 edit list is incomplete (note 1589).** (a) `.github/CODEOWNERS` lines 1-12 record the 2026-09-11 scope decision and the test's role; the header is not in the edit list. (b) The 8 tool, workflow and test patterns must exist when `test_every_gate_file_exists_and_has_a_code_owner` runs (`:364-369`, `.is_file()`), so the CODEOWNERS edit must land in the same PR as the files or the test must skip not-yet-created paths; say which. The directory pattern must not be asserted with `is_dir()` (`.research-system/evidence/` has no tracked file at `dbd54fe3`). (c) `tools/check_bypass_merges.py:41,135` reports every bypass whose PR text has no `Bypass reason:` line; each evidence PR will be a bypass, so add that line to the stated cost. (d) The `CONVENTIONS.md` bullet at 713-729 is in `## ARS Foundation Governance` (line 614 to 783), a successor section, so the amendment does not touch a legacy unit (checked).
- **R3-m10. Baseline wording inverts the disposed and walked intervals (note 684, 654).** Commits between `4b143c92` and `baselines[0]["baseline_commit"]` are the pre-baseline commits that §6.2.1 disposes; commits between `baseline_commit` and L-1 are walked and must be clean or acknowledged. Note 684 says the latter are "disposed in §6.2.1". The table is complete only as of `dbd54fe3`, so `pre_baseline_dispositions_ref` (note 654) needs a refresh rule: append every guarded first-parent commit from `dbd54fe3` to `baseline_commit` to the L-1 decision entry.
- **R3-m11. Test and schema gaps for the new governed fields (note 184, 387-389, 619, 1476).** `ruleset_gap_acknowledgements` has no row schema or Rule 0 validation (prose at note 184 only) and no positive test for `--acknowledge-gap`; the D-8 gate ("`--ruleset-check ci-d8` fails without a verified `d8_rule_suites_limit_decision_ref`", note 389) is not in §12.1; `checkpoints` rows have no negative control (R3-M2).
- **R3-m12. The workflow cannot execute before L-1, and its pin logic is untested (note 1310-1356, 1406-1407).** With no `walk-baseline.json` at `origin/main` the pin step fails closed by design, so the first real execution of this YAML is the L-1 activation merge. The unit tests read the YAML text (triggers, forbidden flags) and never run the pin script. Run the heredoc in a unit test against a scratch repository with synthetic `walk-baseline.json` rows (valid; off-chain pin; blob mismatch; I3 mismatch; empty variable under I3), and rehearse the workflow once on a throwaway `pull_request` trigger as for U-3.
- **R3-m13. Option A's blast radius is understated (note 107, 541, 1591).** Option A1 names `tests/research_system/unit/test_w9_evidence.py` only. The 3-key entry shape is also built by the shared harness `tests/research_system/integration/w9_runtime_harness.py:451-466` and appended by `test_w9_wp9_4_1_runtime.py:95-109` and `test_w9_wp9_4_2_runtime.py:86-100` (read from `dbd54fe3`). A1 therefore edits WP9.4 acceptance tests as well. Name them and say whether the amendment reopens WP9.4's review. (A2 avoids this.)

### Info

- **R3-i1.** The note's tripwire test reads `doc["on"]` (note 1406, 1409). Under `yaml.safe_load` the key is the boolean `True` (I confirmed `KeyError` on both YAML blocks). The repository's workflow tests load with `yaml.BaseLoader` (`test_ars_currency_workflow_controls.py:19-22`); say the test uses that loader.
- **R3-i2.** `06v` says the `CONVENTIONS.md` check runs "as a CI job" (`06v:491-492`). The note runs it post-merge, on the operator machine and in unit tests, never on pull requests. Adding it to the required `admission-controls` job would make it preventive for `CONVENTIONS.md` at no ruleset change (it costs under 0.15 s). Either state why not or put it to Stephen.
- **R3-i3.** After L-1 nothing watches that the detector workflow keeps firing; `ci.yml` `watchdog-schedule-liveness` covers two other workflows only (`ci.yml:255-285`). Optional: add the detector's schedule.
- **R3-i4.** Live re-check at review time: ruleset `20822054` matches every pin (all 16 comparisons true, including `integration_id: 15368`); the month window is now 56 evaluations, 32 bypass (newest `4ca375a3`), consistent with the note's dated 56 / 32 at 23:03Z (note 1836). The unpinned parameters the note lists are as stated.

## 2. Citation audit

Method. `r2_cites.py` (rerun against revision 3) resolved every `path:line` form against `git show dbd54fe3:<path>`: 253 distinct references, about 40 new since revision 2. Fifteen could not resolve by alias because they name files outside the base commit (the two reviews, two handoffs) or a test file by basename; I resolved those by hand with `r3_reviewcites.py` and `git show`. I then read the load-bearing new ranges.

Result: every R2 citation defect is fixed (`commands.py:16` with 12 members; `routes.py:446,454` with 49 and 12 (imported and counted); `03-decisions-and-open-questions.md:6022-6025,6086-6087`; `W9:768`; `CONVENTIONS.md:713-729` and `:721-725`). New citations I checked and found correct: `CONVENTIONS.md:713-729` (the bullet is lines 713 to 729), `.github/CODEOWNERS:14-24,18`, `test_ci_platform_policy.py:341-375,364-369,372-374`, `ci.yml:210`, `ADMISSION_CONTROL_MODULES` `:175,226`, `preparers.py:686-690,702-706,1215-1218`, `acceptance.py:121-136,147-152`, `evidence.py:40,42,114-131,190-252,347-358`, `export_recheck.py:80-89`, `segmentation.py:391-425,398,408,418-419`, `reader.py:42-49,237,300-312`, `accepted_w9.py:86-88`, `check_workflow_liveness.py:60-95`, `ars-artefact-currency-watchdog.yml:98-112`, `research-system-suite.yml:8-9,15,17`, `admin-bypass-guard.sh:13-18`, `test_w9_evidence.py:62`, the 15 citations to the two reviews and two handoffs (14 correct). Wrong: two in all (R3-m7 (a) and (b)).

### The 22-commit first-parent table (§6.2.1)

`r3_inventory.py` walked `4b143c92..dbd54fe3` (320 first-parent commits) with `diff-tree -r --no-renames -z <P1> <C>` over `CONVENTIONS.md`, `results/`, `papers/`, `contracts/`, `.apm/`.

| Check | Result |
|---|---|
| Guarded first-parent commits | **22**; the set equals the table's 22 rows exactly |
| SHA, parent count, first parent, `%cI` date for all 22 rows | Match |
| `CONVENTIONS.md` and `.apm/tracker.md` `old -> new` blobs on every row that has them | Match, including #419 `baceabd6 -> 14d39755` and #425 `14d39755 -> 1db03819` |
| Split | 9 `CONVENTIONS.md`-only first-parent commits (`7347ae95`, `9795ee5f`, `f52f52f4`, `85c7a02e`, `65f4da4b`, `3a14a97c`, `53b7c5be`, `14a81b84`, `1fba78aa`) plus 1 mixed (`1dbf6b7b`); the footnote's 9 + 1 + 3 + 3 + 3 + 2 + 1 = 22 |
| `gh api pulls/419` and `pulls/425` | `merge_commit_sha` `14a81b84...` and `1fba78aa...`; merged 2026-11-08T23:42:29Z and 2026-11-10T21:25:35Z; `commits/<sha>/pulls` returns `[419]` and `[425]` |

### Import closure (R2-M3 figures)

`r3_closure.py` (independent AST walker with an exact file list from `git ls-tree`, parent-package `__init__` handling, relative imports, in-function and `TYPE_CHECKING` imports) over the note's seven seeds gives exactly the note's 15 existing modules, and removing `TYPE_CHECKING`-only imports changes nothing. Recorded blobs equal `git rev-parse dbd54fe3:<path>` for all 13 that the note pins (`41de4e49`, `98705180`, `a50550e3`, `25552c51`, `a90b88fe`, `8a6cc1ba`, `d92c4dcf`, `83e1969c`, `bcf9f6c0`, `be598aeb`, `9ccd930d`, `4e625416`, and `43e1454d` for `tools/w9_segmentation.py`); `accepted_w9.py` and `evidence.py` are placeholders because Options A, D, E and J change them. The count is coherent: 15 existing + 5 new runtime modules = 20; plus the exporter and the workflow = 22; the JSON example has 22 keys (7 `tools/` files, 1 workflow, 14 `research_system/` files). The 15 depends on the five unwritten tools importing nothing beyond the seeds; the superset test would catch a miss. The exporter's own closure (161 modules through `research_system/cli.py`) is not pinned; the note says so (note 104, 711).

### `CONVENTIONS.md` unit counts

Both segmenters over `4620c716` and `dbd54fe3:CONVENTIONS.md` (`r3_conv.py`): 70 and 90 units, 0 blockers, equal dicts, section sizes `[3,2,5,4,24,13,6,3,2,8]` and `[3,2,6,5,4,24,13,6,3,9,15]`, all 70 baseline units preserved in order, 14 inserted units in sections that existed at the baseline (7 in `ARS Foundation Governance`, 7 in `Computational Environment`) and 6 in the new `Repo-Wide CI` section. Matches the §7.3 table and the note's totals.

### Workflow YAML and U-4 script

`r3_yaml_check.py`: both YAML blocks parse; the detector workflow has 6 `run:` scripts and every one passes `bash -n`; the embedded 31-line Python heredoc parses; the U-3 probe's 2 scripts pass `bash -n`. `r3_u4_extract.py` ran the note's U-4 script text (lines 447-477, vault literal replaced by a synthetic directory that the script builds) from the worktree with `PYTHONPATH=.`: exit 0; output as described under R3-m6. No real vault path was opened.

## 3. Disposition of every R2 finding

| ID | Disposition | Evidence |
|---|---|---|
| R2-M1 | **Partly resolved** | Trust root stated plainly (note 557) and covered by I1; workflow runs a detached worktree at `baselines[-1]["tool_pin_commit"]` with `uv sync --locked` run inside it, so the pinned `uv.lock` is the one used (by reading; not executed); the vacuous "present at `<baseline>`" clause is gone; `baselines[0]` starts the walk and `[-1]` pins the tool; references are hash-bound; every top-level field is under Rule 0.2; dispatch `inputs:` removed; `--baseline`/`--head` locked behind `--ruleset-check skip` with a workflow-text test. Not resolved: appended `baselines` rows are not validated and the upgrade sequence cannot run (R3-M1); the workflow YAML itself still runs from the head, stated honestly in note 557 and 1392 and covered by I1; I3 fails open (R3-m1). |
| R2-M2 | **Partly resolved** | `acknowledged` list is sound as a mechanism (SHA-prefix naming in the slice makes a pre-dated disposition impossible; the exact-tuple scope is right) except for Rule 3 (R3-M3). Checkpoints leak a skip (R3-M2); `--full-rewalk` is reported as a structured diff but has no data to diff (R3-M2 item 4). |
| R2-M3 | **Resolved** | Closure derived by a stated AST method, recorded with a blob per module, superset test named (note 713), whole-tree execution chosen (the first of R2's two options). 15 / 20 / 22 reproduced. Residuals: detective-only for non-code-owned modules and its cost (R3-M1 item 4, R3-m3). |
| R2-M4 | **Resolved** | `ACCEPTED_CONVENTIONS_CLASSIFICATION: tuple[MappingProxyType[str, Any], ...] = ()` mirrors `ACCEPTED_CL_EXPORT` (`accepted_w9.py:86-88`; entry has the same five fields); `accepted_w9.py` is not in `IMPORTER_MODULES` (`reader.py:42`) and no source or test pins its blob (grep at `dbd54fe3`; only a binding-advance fixture treats it as governed code), so no D-4 trigger; keyed `(anchor_text, unit_hash)`; read at the pinned commit only; `--classified-locks` locked; Rule 0.2 and control N7. Residual: the file that holds the pin is not code-owned (R3-m2). |
| R2-M5 | **Resolved with minors** | Exact CODEOWNERS list (8 patterns plus `/.research-system/evidence/w9/`), the two policy tests and the `CONVENTIONS.md` bullet at 713-729 are right against `dbd54fe3`; the reversal of the 2026-09-11 scope decision is stated and routed to `P-090`; the bypass-merge cost is stated (note 195, 1525, 1589); I2's consequences stated. Would the edited tests pass? Yes if directory patterns skip existence and the new files land with the CODEOWNERS edit (R3-m9 (b)). |
| R2-m1 | Resolved | 22 rows, 9 + 1 split, no stale "20" (grep), reproducible command in §20.1 item 3. |
| R2-m2 | Resolved | `commands.py:16` (12), `routes.py` (49, 12) imported and counted. |
| R2-m3 | Resolved | Row keys match `segmentation.py:391-425`; ordinals 1-based in the classified-list example and in `require_cl_export`'s rule. |
| R2-m4 | **Partly resolved** | The six wrong citations are fixed; the header was rewritten to say what was and was not checked, but it now overclaims in one place (R3-m7 (c)). |
| R2-m5 | Resolved | Forward slashes; no `grep -q`; `--ruleset-check` and `--verify-watched-to-fail` steps present; `push` branch filter in the L-1 test. YAML verified by parse and `bash -n`. First real execution is L-1 (R3-m12). |
| R2-m6 | Resolved | Probe records pinned-key presence per body and states the probe PR's side effects. |
| R2-m7 | Resolved | Scratch-script form, working directory and `PYTHONPATH` stated, no `KeyError` (run on a synthetic vault). R3-m6. |
| R2-m8 | Resolved | `GIT_CONFIG_GLOBAL`, `-c core.autocrlf=false -c commit.gpgsign=false`; the bit-identical claim dropped. |
| R2-m9 | Partly resolved | `integration_id` pinned; reset path `--acknowledge-gap` and the per-read PR cost stated; the gap row has no schema (R3-m11). |
| R2-m10 | Resolved | Matching grammar given; review bound to the change; B1 stated as conditional on I1; the `P1` ordering labelled as the note's reading. |
| R2-m11 | Resolved | Revert-cycle intent stated; test names corrected; uniform `/2`; A1 needs the dated amendment. R3-m13 for A's file list. |
| R2-m12 | Resolved | `report["void"] is True` is a closed failure. |
| R2-m13 | **Partly resolved** | Lane stated, but inaccurate for `tools/` edits (R3-m4); profile step is conditional (R3-m5); the 20-35 s estimate was removed. |
| R2-m14 | Partly resolved | Any first-parent ancestor allowed; wording of the disposed interval is wrong (R3-m10). |
| R2-m15 | Resolved | #368 caption, claim 5 and the H row corrected. |
| R2-m16 | **Partly resolved** | Narrowed to checkout-local state, but still includes shared `refs/heads/` and `refs/tags/` (R3-m8). |
| R2-i1 to R2-i6 | Resolved / recorded | HR-6 added; strictness note on blockers; unpinned parameters listed; dated counts kept (live window is now 56 / 32). |

## 4. Owner points A to J

| Point | Premises | Recommendation | Missing or wrong |
|---|---|---|---|
| I (first) | Verified: CODEOWNERS has 8 paths all `@stephendor`; both tests assert as quoted; the bullet at 713-729; bypass cost real (33 of 57 rule-suite results were `bypass` at the note's read, 32 of 56 now; `check_bypass_merges.py:41,135` needs a reason line) | I1 required; I2 correctly demoted; I3 optional | R3-m1 (I3 fails open, "admin-only" unverified), R3-m2 (add `accepted_w9.py`; pin the operator run), R3-m3 (closure cost), R3-m9 (edit list), R3-M1 (what I1 cannot do for closure modules) |
| C | 22 commits verified; baseline semantics fixed | C1 acceptable only after R3-M1, R3-M2, R3-M3 | R3-m10; "depends on I1" is right |
| A | `evidence.py:40,114-131`, `test_w9_evidence.py:62` verified | A1 sound; needs the dated WP9.3 amendment (stated) | R3-m13 (three more files; WP9.4 tests) |
| B | Conditional on I1 (stated) | B1 sound | none new |
| D | `evidence.py:231-238`, `acceptance.py:121-136`, test names verified; D1 and D2 dismissals stand | D3 sound | R3-M3 (acknowledgement interplay) |
| E | Four gate sites verified (`preparers.py:686-690,702-706,1215-1218`, `acceptance.py:147-152`); cost stated | E1 sound | none new |
| F | Precedent `ci.yml:210`, `:226` verified | F1 sound | mis-cite at note 1595 (R3-m7); lane (R3-m4) |
| G | P-087 item 7 | G1 until profiled | R3-m5 |
| H | Verified by R2 on three real tracker commits | H1 sound | none new |
| J | Mirror of `ACCEPTED_CL_EXPORT` verified; leaf module; no D-4 | J1 sound | R3-m2 |

Register and review entries each option needs, as the note states them: A1, D3, E1 each need a dated WP9.3 amendment, an independent review and a `P-090` entry; H1 needs a dated W9 §4.2 amendment; I1 needs the `CONVENTIONS.md` amendment recorded in `P-090`. I find these complete except that A1 also touches WP9.4-era tests (R3-m13). None of A, D, E, I or F lies inside `P-089`'s "Boundary" sentence (`03-decisions-and-open-questions.md:6141-6143`), and the note says each is an owner decision recorded in `P-090`; that is the right handling.

## 5. Consistency matrix for the revision 3 mechanisms

| Invariant | Enforcement point | Test | Result |
|---|---|---|---|
| Judgement runs the pinned tool | Workflow pin step (note 1310-1356); I1 and I3 for the workflow itself | YAML-text tests only | Pin script untested (R3-m12); I3 fails open (R3-m1) |
| The pin covers the detector's imports | `compute_detector_import_closure`, `RECORDED_DETECTOR_CLOSURE`, blob check in the workflow | `test_recorded_detector_import_closure_covers_ast_walk` | Sound; PR-time and preventive for new imports |
| A closure edit is authorised | Rule 0.3 | Negative only | Unsatisfiable (R3-M1) |
| An appended `baselines` row is valid | Prose (note 685) | None | Not enforced (R3-M1) |
| A violation can be cleared once, with a record | Rule 0.2 on `acknowledged` | valid, backdated, same-commit | Sound except Rule 3 (R3-M3) |
| History is not silently re-judged or skipped | `checkpoints` | positive only | Open (R3-M2) |
| Top-level fields are immutable | Rule 0.2 | yes | Sound |
| The classification pin cannot be reclassified by the head | Constant, pinned read, Rule 0.2, N7 | N7 | Sound |
| No dispatch override reaches production | Tool exit 2; workflow-text test | yes | Sound |
| `L1_LIVE` cannot be flipped without the owner | Tripwire test in `admission-controls` (F1) plus CODEOWNERS (I1) | yes | Sound under I1; loader note R3-i1 |

## 6. What was checked and found sound

- **First-parent facts, closure, counts, ruleset pins** as in section 2 and R3-i4.
- **The trust-root statement** (note 557) is honest: it says no repository content stops a merged commit, names I1 as the preventive control, and says I2 does not close R1-B1. The residual that the workflow YAML runs from the head is stated (note 557, 1392) and is within I1's list.
- **The pinned-tree mechanics that do exist** (read from the YAML; the workflow was not executed): `uv sync --locked` inside the pinned tree uses the pinned `uv.lock`; `PYTHONPATH` and the script-directory `sys.path[0]` mean the head's `research_system` is not imported; the first-parent membership check is in Python, not `grep -q`; the dispatch surface has no inputs.
- **R2-M4's mirror** and the absence of a D-4 trigger (no source or test pins `accepted_w9.py`; the file is outside `IMPORTER_MODULES`).
- **R2-M5's edits** against the real CODEOWNERS file, `GATE_FILES`, both tests and the `CONVENTIONS.md` bullet.
- **U-4 script and §4.3.2 checks** at the code level (`handle_bound_read`, `LegacyReader`, `segment` row keys and `file_facts`).
- **`test_w9_detectors.py` in `admission-controls`**: the job installs the full lockfile (`ci.yml:150-160`), so the new tests can import `research_system`; `check_test_commit_literals.py` is satisfied by commits that are on `main`.
- **The attack on acknowledged rows that failed:** I tried to forge an acknowledgement by writing the decision entry after the offending commit with a back-dated `source_commit`. The slice must name `commit[:8]`, which a PR cannot know before its squash commit exists, so the ordering property holds without reading the slice at `source_commit`. (Reading it there anyway would make the rule self-evident.)

## 7. Coverage of the handover's 17 items

| # | Item | Result |
|---|---|---|
| 1 | Scope, protected identities | Settled (§2.2). |
| 2 | Ruleset read | Settled; pins verified live. |
| 3 | U-3 | Probe designed; gate in §15.1 item 1. |
| 4 | First-parent detector | Evidence timing and Rule 0 sound; upgrade path, checkpoints, acknowledgement of Rule 3 open (R3-M1 to R3-M3). |
| 5 | M-6 export | Settled; R3-m13 for A1's file list. |
| 6 | Shared-surface rule | Settled; R3-M3. |
| 7 | `CONVENTIONS.md` check | Settled and verified numerically; classification pinned. R3-i2. |
| 8 | Vault detector, D-5 | Settled. |
| 9 | U-4 | Metadata recorded (equals the brief); dry run specified; gate in §15.1 item 2; R3-m6. |
| 10 | Controls file | Settled; verify step is in the workflow. |
| 11 | Merging is not going live | Settled; first execution of the workflow is L-1 (R3-m12). |
| 12 | Where controls run | Settled; R3-m8. |
| 13 | Tests and budget | Inventory given; lane inaccurate for `tools/` edits (R3-m4); profile step conditional (R3-m5). |
| 14 | Research assurance | MC and HR split; MC-2 overclaims (R3-M1). |
| 15 | Claims for review | 16 claims; claim 2 overclaims. |
| 16 | Stop rules | §15.1 holds U-3, the U-4 dry run, `P-090`, and the profile (conditional); §15.2 matches `06v:610-620`. |
| 17 | Owner points | Ten, with options, recommendations and impact (section 4). |

## 8. Revision plan

**Immediate corrections (author, no owner decision):**
1. R3-M1: choose form A or B; add the Rule 0.2 validation of appended `baselines` rows; add the positive and negative controls; reword MC-2, note 714 and claim 2.
2. R3-M2: define checkpoint validity by recomputation; require a checkpoint with every pin advance; store or re-derive verdicts for `--full-rewalk`; add the negative control.
3. R3-M3: add the late-entry requirement to Rule 3 acknowledgements; add the control.
4. R3-m1 to R3-m13, in particular the two citation fixes and the header sentence (R3-m7), the I3 empty-variable rule, the unconditional profile step, the lane statement, the dry-run root checks, the I1 edit list, the A1 file list.

**Owner decisions after revision 4:** I first (with the closure cost stated), then C (with the corrected protocol), A, B, D, E, F, G (G1 until profiled), H, J.

**Later-work dependencies:** the U-3 probe result and the U-4 dry run before code; a dated WP9.3 amendment and independent review for A1, D3 and E1; a dated W9 §4.2 amendment for H1; the L-0b export and classified list; an L-0 refresh of the §6.2.1 table.

**Residual risks the note should keep stating:** the detector is post-merge and a human merge is the only preventive control; closure modules that are not code-owned are detective only; the weekly vault run is self-attested; the CI token may not read rule-suites (D-8); the `CONVENTIONS.md` check does not see sub-heading or ordering edits outside units.

## 9. Commands run

All read-only. `git status --short` was empty before this report was written; the report is the only file added to the worktree. No vault file was read or opened; the vault junction and `Computational-Log.md` were not touched (the U-4 values in the note equal the brief's). No workflow was run, no probe was run, no repository variable was read, and every `gh api` call was a GET.

- `git` in the worktree: `rev-parse`, `show <rev>:<path>`, `ls-tree`, `log --first-parent` (counts and per-path unions), `diff-tree -r --no-renames -z <P1> <C>`, `diff --stat dbd54fe3..092db1f1`, `grep` at `dbd54fe3`, `rev-list --first-parent --count`.
- `gh api` GET only: `repos/ZK-Theory/TDL/rulesets/20822054`; `.../rulesets/rule-suites?ref=refs/heads/main&time_period=month&per_page=100` (`--paginate --slurp`); `.../pulls/419`, `.../pulls/425`; `.../commits/14a81b84.../pulls`, `.../commits/1fba78aa.../pulls`.
- Scratch scripts in `C:\Users\steph\AppData\Local\Temp\claude\e088a017a981a492\f302c5e4-50e0-4fcc-b0af-3a36e9983c74\scratchpad`, all run with the worktree's `.venv` Python: `r3_closure.py`, `r3_inventory.py`, `r3_conv.py`, `r3_yaml_check.py`, `r3_u4_extract.py`, `r3_reviewcites.py`, `r3_ruleset.py`, and `r2_cites.py` (the existing resolver, rerun against revision 3 with output in `r3_cites_full.out`). One diagnostic `python -c` printed `len(LEGACY_COMMAND_TYPES)`, `len(LEGACY_ROUTED_ROWS)` and `len(LEGACY_DEFERRED_ROWS)` (12, 49, 12); nothing was composed into a file that way.
- File reads: the note in full, the R2 review, the r3 follow-up brief, the handover's item list, P-089, P-087 item 7, `06v` (WP9.5, L-rows, batch checklist, stop rules, O-32), W9 §4.1 to §4.4, `research_system/legacy/{reader,evidence,accepted_w9,segmentation,preparers,acceptance}.py` (cited ranges), `tools/{check_bypass_merges,affected_research_tests,check_workflow_liveness}.py`, `.github/CODEOWNERS`, `tests/tools/test_ci_platform_policy.py` (policy tests), `.github/workflows/{ci,research-system-suite,ars-artefact-currency-watchdog}.yml`, `CONVENTIONS.md:700-735`, the WP9.3 and WP9.4 integration-test harness lines named in R3-m13.
- Not run, as instructed: the U-3 probe, the U-4 dry run against the vault, anything reading the vault. Not verifiable here: how GitHub treats `GITHUB_TOKEN` for the three U-3 endpoints; who may write repository variables (R3-m1); the claim `private: false` (note 256), which would need a `repos/ZK-Theory/TDL` GET that the brief does not allow; whether a `workflow_dispatch`-only workflow registers as `active` after merge (note 1394; plausible from `check_workflow_liveness.py:64-67`); the scratch-store test timing (`UNVERIFIED-3`); the operator-machine weekly D-5 run.
