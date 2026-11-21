REWORK REQUIRED

# Independent adversarial review: WP9.5 design note, revision 2

| Field | Value |
|---|---|
| Subject | `docs/plans/agentic-research-system/transition/w9/wp9-5-design-note.md`, revision 2, commit `0c9a90ed`, blob `68b0cb69` (1,495 lines by `wc -l`; the brief said 1,289, the blob id matches), base `dbd54fe3` |
| Prior review | `docs/plans/agentic-research-system/reviews/wp9-5-note-r1-review-2026-11-21.md` (`edb9acc6`): REWORK REQUIRED, 1 Blocking, 12 Major, 14 Minor, 6 Info |
| Worktree | `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note` (read-only; `git status --short` empty before this report was written) |
| Reviewer | fresh session, no author context; skill `adversarial-design-review` |
| Date | 2026-11-21 |
| Verdict | **REWORK REQUIRED**: 0 Blocking, 5 Major, 16 Minor, 6 Info |

"note NNN" is a line number in the note at `0c9a90ed`. Other `path:line` values are at `dbd54fe3` (`origin/main` is now `4ca375a3`; its only code change, `research_system/legacy/citations.py` in #448, is irrelevant here).

## 0. Summary

Revision 2 is a large improvement. Almost everything I could check against bytes is correct: the 22-row first-parent inventory facts, all 20 PR to `merge_commit_sha` mappings, the `CONVENTIONS.md` unit counts, the ruleset pins, the U-4 table, the code symbols for the readers, the timings, and about 170 of about 175 distinct `path:line` citations. The fabrication rate fell from about half of citations to about 3 percent. The time-indexing of evidence (manifest at `P1`, records at `C`) and Rule 0 do close the three R1-B1 scenarios that were about evidence timing. Owner Point H1 passes a test I ran against the three real tracker commits.

It is still not a basis for code, for five reasons.

1. **R1-B1 scenarios 4 and 5 (the detector disarming itself, the baseline moving) are not closed (R2-M1, R2-M2, R2-M3, R2-M4).** The workflow in §10.2 runs the tool from the checkout at the head being judged. The "pin to the baseline" is circular, vacuous (the pin file is absent at the baseline by construction) and ambiguous (first entry or last). The decision reference that authorizes a tool change is checked for existence only. The walk is stateless and always starts at `baselines[0]`, so one honest true positive is red forever and a tool edit silently changes the verdict on history. The detector's import closure and the `CONVENTIONS.md` classification input sit outside every pin, Rule 0 and the CODEOWNERS list. The note's closure rests entirely on Owner Point I1, but Option I2 is presented as sufficient.
2. **Owner Point I1 as written breaks an existing test and contradicts the note's own tripwire (R2-M5).**
3. **Residual wrong names and citations remain while the header and §18 say everything was verified** (R2-m1 to R2-m4): a nonexistent `contracts.py`, "five" commands where there are 12, invented segment row fields (`byte_start`, `line_start`) that would make the U-4 dry-run command fail exactly when it finds a blocker, and wrong register and W9 lines.
4. **The §10.2 workflow YAML has defects** that would stop it running (R2-m5).
5. **The inventory the baseline decision rests on is incomplete**: it says 20 first-parent commits, there are 22 (R2-m1).

Nothing here needs Stephen to reverse an accepted decision. A revision 3 should be short: it is mostly a trust-root paragraph, an acknowledged-violation mechanism, a pin set, an I1 correction and the residual factual fixes.

## 1. Findings

### Blocking

None. R2-M1 would be Blocking if Stephen accepts Option I2 as the note frames it; see R2-M1.

### Major

#### R2-M1. The detector's own integrity is circular: the workflow runs the head's tool, the baseline pin is vacuous and ambiguous, and the authorizing reference is existence-only (R1-B1 scenarios 4 and 5 remain)

- **Claim (note 1210, 523, 582, 687, 1432):** "Self-integrity against detector weakening: ... the tool compares its own running file bytes against `<baseline>:tools/check_legacy_writes.py`"; "pinned to `<baseline>`"; R1-B1 "adopted in full".
- **Evidence:**
  1. The YAML (note 1198-1204) runs `.venv\Scripts\python.exe tools/check_legacy_writes.py` from the checkout. `actions/checkout@v4` with no `ref:` checks out the dispatched ref or, after L-1, the pushed commit; a push-triggered run executes that commit's workflow. Nothing extracts the tool from `<baseline>`. The text of §6.1 (note 523, "extracts or verifies the detector scripts at `<baseline>`") is not in the YAML.
  2. The in-tool check (note 1210) runs only "when `walk-baseline.json` is present at `<baseline>`". The file is "added at L-1" with `baseline_commit` the L-1 parent (note 562, 569), so it is absent at `<baseline>` by construction and the check never fires. A weakened tool that omits the check is not constrained by a check it contains.
  3. Which baseline entry pins the tool is not stated. Note 582 uses `baselines[0]` for the walk start. Rule 0.3 (note 687) requires a "newly appended baseline entry" to carry `detector_tool_blobs`. If `[0]` pins the tool, no detector fix can ever run; if the latest entry pins it, any PR that appends an entry replaces the tool.
  4. The authority for a tool change is `recorded_in_decision_ref` that "exists in `<P1>:...03-decisions-and-open-questions.md`" (note 582, 687): existence only. Compare §6.4 (note 629-630, 635), which binds `entry_sha256` and ancestry. The same existence-only shape is used for the top-level `d8_rule_suites_limit_decision_ref` (note 350, 566), which is also not an "entry" and so is outside Rule 0 item 2.
  5. The workflow offers `baseline_commit` and `head_commit` dispatch inputs and passes `--baseline` (note 1133-1140, 1195-1197) without `--ruleset-check skip`. Note 582 says `--baseline` is for `skip` tests only; the unit test that guards this (note 614) forbids only `--pr-map`, `--manifest-file` and `--ruleset-check skip`.
- **Failure scenarios.** (a) A PR weakens Rule 1 in `check_legacy_writes.py`, edits registered file `F`, appends a baseline entry citing an existing unrelated entry such as `P-001`, and is merged. The push-triggered run is judged by the PR's tool and workflow: green. (b) Anyone with write access dispatches the workflow with `baseline_commit` equal to a recent commit: the walk is empty, the run is green and looks like a pass. (c) A PR sets `d8_rule_suites_limit_decision_ref` to any string and CI stops reading rule-suites.
- **Impact:** R1-B1 failure scenario 4 and 5 stand under Option I2. MC-2 (note 1327) claims "no commit can ... edit a detector tool/workflow without an owner decision ref ... existing at `P1`", which is a weaker property than its wording suggests.
- **Disposition:** fix now.
- **Proposed text:**
  - Add to §6.1: "There is no trust root inside the repository content that a merged commit can change. The preventive control is Owner Point I1 (CODEOWNERS on the workflow, the detector tools and `.research-system/evidence/w9/`). Option I2 does not close R1-B1 and is withdrawn, or is kept with that sentence." If Stephen wants a second anchor that does not depend on a human merge, name it: a protected tag or a repository variable holding the baseline SHA and the three tool blobs, set by Stephen at L-1, read by the workflow before checkout of the head, with the tool executed from `git worktree add "$RUNNER_TEMP/w9-detector" <pinned-sha>`.
  - Replace "the tool compares its own bytes" with the workflow step above; delete the "present at `<baseline>`" condition.
  - State that `baselines[0]` fixes the walk start and the LAST entry pins the tool, and that each entry's `recorded_in_decision_ref` is `{"id": "P-0xx", "entry_sha256": "<sha of the ### slice at P1>"}`, hash-bound as in §6.4.
  - Put every top-level field of `walk-baseline.json` under Rule 0 item 2 (immutable once non-null), and validate `d8_rule_suites_limit_decision_ref` the same way.
  - Remove the dispatch inputs, or make the tool exit 2 on `--baseline` or `--head` unless `--ruleset-check skip`; extend the test at note 614 to assert that the workflow passes none of `--baseline`, `--head`, `--pr-map`, `--manifest-file`.
- **Affected:** R1-B1, R1-M10, R1-m1, R1-m6; note §6.1, §6.2.2, §10.2, MC-2, claim 2; Owner Points C, I.

#### R2-M2. The walk is stateless and always starts at `baselines[0]`: a true positive can never be cleared, and a tool change retroactively changes past verdicts

- **Claim:** note 582 (the walk "takes `baseline = baselines[0]`"; later entries only append) and §6.3 (every run walks `baseline..head`).
- **Evidence:** R1's prescription for B1 was a baseline "advanced only by a reviewed PR that names the new commit" (R1 §1, R1-B1 "Change needed"). Revision 2 chose the opposite: the start never moves. Three guarded first-parent commits after the freeze already landed with no record (`e3519ba7`, `633ed58e`, `a6a98966`, from my inventory), so honest unrecorded writes do occur.
- **Failure scenarios.** (a) The first honest true positive after L-1 makes every later run red. There is no sanctioned way to acknowledge it; the only exits are weakening the detector or disabling the workflow. This is the "teaches operators to ignore it" outcome R1-M5 warned about. (b) The reverse: because the whole history is re-judged by whichever tool is current, an edit that narrows a rule turns old red commits green without any recorded decision about those commits.
- **Impact:** operational (the control gets bypassed) and integrity (verdicts are not stable). Owner Point C's recommendation C1 depends on this mechanism.
- **Disposition:** fix now; Owner Point C to decide the form.
- **Proposed text:** add to `walk-baseline.json` an append-only `acknowledged` list of `{commit, rule, path, old_blob, new_blob, disposition_ref: {id, entry_sha256}}` rows, each valid only if its `disposition_ref` entry was committed after `commit` and before the row (Rule 0 enforces order). The detector exempts exactly those tuples. Add a per-run checkpoint `{last_verified_commit, verdict_digest}` kept by the operator-machine run or the workflow, so that a tool change re-evaluates only new commits unless the owner requests a full re-walk (a full re-walk against the new tool is then reported as a diff of verdicts, not silently applied).
- **Affected:** R1-B1, R1-M12; note §6.2.2, §6.3, §16 C.

#### R2-M3. The detector's import closure is outside the governed set (pins, Rule 0, I1)

- **Claim (note 99-104, 571-575, 687, 1412):** the detector surface is "the six tools, the helper and the workflow".
- **Evidence:** the tools import `research_system.legacy.reader` (`handle_bound_read`, `git_blob_id`, the `CONVENTIONS_LOCK` constants, `reader.py:43-49,75-77,140-206`), `research_system.legacy.segmentation` (`segmentation.py:429`), `research_system.legacy.evidence` (`is_ancestor` `:159`, `blob_at` `:179`, `require_detector_controls` `:133`), `research_system.canonical` (`canonical.py:40-52`) and `tools.w9_segmentation` (note 65, 786, 893-895). `detector_tool_blobs` pins three tools (note 571-575). Rule 0.3 lists six tools plus the helper plus the workflow (note 687). I1 adds the same list to CODEOWNERS (note 1412). None names a `research_system/` module. Those modules are edited in ordinary PRs.
- **Failure scenario:** a PR makes `evidence.is_ancestor` return `True`. Every ancestry provenance check in §6.4 (`source_commit`, `review_commit` precede `P1`) passes for fabricated references, with no detector tool blob, no Rule 0 surface and no CODEOWNERS path touched. `tools/w9_segmentation.py` has its own blob pin and a test; `reader.py`, `evidence.py` and `canonical.py` have none that the detector consults.
- **Impact:** the pin set is not closed under the detector's own dependencies, which is the "closure of the governed set" failure. HR-1 and HR-3 do not mention it.
- **Disposition:** fix now.
- **Proposed text:** derive the import closure with a script (AST walk of the six tools plus helper, transitive over `research_system` and `tools`), record it as a list in `walk-baseline.json` with a blob per module, add a unit test that the recorded list is a superset of the computed closure, and either run the detector from a whole-tree `git worktree` at the pinned commit (R2-M1) or add the closure to Rule 0 and the I1 CODEOWNERS list.
- **Affected:** R1-B1, R1-M10; note §2.3, §6.1, §6.2.2, §6.5 Rule 0, §16 I.

#### R2-M4. The `CONVENTIONS.md` classification that defines the bar is an unpinned, editable input

- **Claim (note 810, 1413):** the checker "accepts an optional `--classified-locks <path>` (or reads a committed `.research-system/evidence/w9/conventions-legacy-locks.json` once pinned at L-0b)" mapping `(anchor_text, raw_row_sha256)` to `legacy` or `successor`; Option J1 repeats it with the format `w9-conventions-classified-locks/1`.
- **Evidence:** no path is fixed in `06v-addendum-2026-11-10-w9-paths.md`, no code constant pins a blob (contrast `ACCEPTED_CL_EXPORT`, `accepted_w9.py:86-88`, which pins the vault list by `git_blob` and `sha256`), the file is not in Rule 0 (note 677-688) and not in the §6.2.2 pins. `conventions_unit` rows are keyed `(anchor_text = section title, unit_hash)` (`segmentation.py:391-402`), so the key in the note should name `unit_hash`.
- **Failure scenario:** after L-0b, a PR flips one legacy unit to `successor` in the classification file and edits that unit in the same commit. The check passes. This is self-definition of the bar by the producer, the pattern the skill puts above self-approval.
- **Impact:** after L-0b the `CONVENTIONS.md` lock is only as strong as an unpinned JSON file. Before L-0b the conservative default holds.
- **Disposition:** fix now (design); the pin is decided at L-0b.
- **Proposed text:** the classification file is pinned exactly like the vault list: an accepted code constant (for example `ACCEPTED_CONVENTIONS_CLASSIFICATION`) holding `{repository_path, git_commit, git_blob, sha256}`, populated by the L-0b PR; the checker reads that blob at that commit, never the head; the workflow passes no `--classified-locks`; add the file to Rule 0; add negative control N7 (reclassify a legacy unit in a byte copy: must still fail).
- **Affected:** R1-M9; note §7.3, §7.4, §16 J.

#### R2-M5. Owner Point I1 as written fails an existing test and contradicts the L1 tripwire; the I2 and F1 interplay is mis-stated

- **Claim (note 1412):** I1 "edits `.github/CODEOWNERS`, `GATE_FILES` in `tests/tools/test_ci_platform_policy.py:341-350`, and `CONVENTIONS.md:721-723` (pure successor update)". I2 "rely on Rule 0 ... without expanding CODEOWNERS".
- **Evidence:**
  - `test_every_gate_file_exists_and_has_a_code_owner` asserts `(REPO_ROOT / path).is_file()` for every `GATE_FILES` entry and `rules.get(f"/{path}")` (`test_ci_platform_policy.py:364-369`); `test_codeowners_names_no_file_outside_the_gate` asserts exact set equality (`:372-374`). I1 adds a directory (`.research-system/evidence/w9/`): `is_file()` is false. Listing the evidence files individually fails the same test before L-1, because the note's tripwire requires those files not to exist (note 1225).
  - `CONVENTIONS.md:727-729` says the test "fails if a gate file lacks an owner, or if CODEOWNERS reaches beyond the gate", and the CODEOWNERS header records Stephen's 2026-09-11 decision that the list is the merge-admission gate only. I1 reverses that scope. It is a policy amendment to a recorded decision, not "a pure successor update" of lines 721-723 (those lines are the "reason is structural" paragraph; the relevant sentence is at 727-729).
  - I1 makes every per-batch manifest PR, every weekly vault-run PR and every ruleset-read PR a PR that needs Stephen's own bypass merge (`admin-bypass-guard.sh:13-18,67-68` forbids agents). The live month already has 34 `bypass` of 58 rule-suite results on `refs/heads/main`. The cost is not stated; §8.4 states only the weekly PR and `advance-binding`.
  - Under F1 plus I2, the L-1 activation PR flips `L1_LIVE` and the workflow triggers. `tests/tools/test_w9_detectors.py` and `legacy-write-detector.yml` are not CODEOWNED under I2, so P-089 item 3 ("L-1 is a separate owner decision") is not preventively enforced. The note says I2 "relies on Rule 0", but Rule 0 covers neither the test file nor the constant.
- **Impact:** the option Stephen is asked to pick would fail CI on the WP9.5 PR; the alternative is presented as safe and is not.
- **Disposition:** fix now (re-frame the row).
- **Proposed text for §16 I:** list the exact edits: add `.research-system/evidence/w9/` (directory pattern) and the tools to CODEOWNERS; change `test_every_gate_file_exists_and_has_a_code_owner` to accept directory patterns and to skip existence for evidence files not yet created; change `test_codeowners_names_no_file_outside_the_gate` and its docstring; amend the `CONVENTIONS.md` bullet at 713-729 as a modification of that bullet (successor section) with Stephen's decision recorded in `P-090`; state the bypass-merge cost per batch; state that under I2 the L-1 activation is not guarded and that I2 does not close R1-B1; add `tests/tools/test_w9_detectors.py` to the I1 list if the tripwire is to be tamper-resistant.
- **Affected:** R1-M7, R1-M10; Owner Points F, I; note §2.3, §10.3.

### Minor

- **R2-m1. The 20-commit inventory is 22 (R1-M12 partly open).** Note 531 says "exactly 20" and §16 C (note 1406) says 20 and "8 CONVENTIONS.md successor-insertion PRs". My first-parent walk over `4b143c92..dbd54fe3` (320 commits, matching the note) finds 22 commits touching `CONVENTIONS.md`, `results/`, `papers/`, `contracts/` or `.apm/`. The two missing from the table are `14a81b84` (#419, 2026-11-08, `CONVENTIONS.md` `baceabd6 -> 14d39755`) and `1fba78aa` (#425, 2026-11-10, `14d39755 -> 1db03819`). The footnote (note 556) refers to a "full 20-commit list from `verify_r2.py`", a script that is not in the repository, and Appendix A row 4 (note 1480) says "22 total". CONVENTIONS-only commits are 9 (plus #277 mixed), not 8. Fix: add the two rows, correct "20" to "22" and "8" to "9" everywhere, and cite a committed or reproducible command.
- **R2-m2. §2.2 names a nonexistent file and the wrong count.** Note 76: "The five W9 commands in `LEGACY_COMMAND_TYPES` (`research_system/legacy/contracts.py`)". `research_system/legacy/contracts.py` does not exist at `dbd54fe3`. `LEGACY_COMMAND_TYPES` is at `research_system/legacy/commands.py:16` and has 12 members (I imported it). `LEGACY_ROUTED_ROWS` (49) and `LEGACY_DEFERRED_ROWS` (12) are correct but live in `research_system/legacy/routes.py:446,454`.
- **R2-m3. Invented segment row fields, and an off-by-one ordinal.** `segment()` rows carry `row_ordinal` (starting at 1), `row_kind`, `anchor_text`, `start_byte`, `byte_length`, `start_line`, `line_count`, `raw_row_sha256`, `anchor_line_sha256`, `blocker_reason`, and for `conventions_unit` also `unit_ordinal` and `unit_hash` (`segmentation.py:391-425`; same in `tools/w9_segmentation.py`). The note uses `byte_start`, `byte_end`, `line_start`, `line_end` (note 421, 827-830, 907). Effects: the U-4 dry-run command (note 421) raises `KeyError` exactly when a blocker exists, the case it is meant to report; the table filter in §7.4 item 5 slices with nonexistent keys. The classified-list example (note 946, 964) numbers ordinals `0..N-1`; `require_cl_export` requires `slot["ordinal"] == row["row_ordinal"]`, which starts at 1 (`evidence.py:347-358`; `segmentation.py:408`).
- **R2-m4. Residual wrong citations; the verification claim is overstated.** Note 80, 81, 83 cite `03-decisions-and-open-questions.md:6064`, `:6065`, `:6066` for the census, the 06h manifest and the schema-registry blobs. Lines 6086 and 6087 are right (P-089's evidence block); 6064-6066 are P-088's "Not authorized", "Capability status" and "Boundary" lines; the blobs `e32cb408` and `9b56b322` are at `:6024`. Note 719 cites `09-migration-compatibility-and-pilot.md:754` for W9-D14; line 754 is W9-D3, W9-D14 is `:768`. Note 1412 cites `CONVENTIONS.md:721-723` for the CODEOWNERS policy (R2-M5). With R2-m2 that is 6 wrong of about 175 distinct citations (3 percent, against about 50 percent in revision 1). The header (note 13) says "every named code symbol, file path, commit hash, date, unit count, and line number was verified"; §18 says every citation was corrected. Both are false in a handful of places. Reword to say what was and was not checked.
- **R2-m5. §10.2 workflow YAML defects.** (a) `.venv\Scripts\python.exe` inside a `shell: bash` step (note 1198, 1202): Git Bash drops the backslashes (I ran `echo .venv\Scripts\python.exe`: it printed `.venvScriptspython.exe`), so the step exits 127. The repository's bash steps use `.venv/Scripts/python.exe` (`ars-artefact-currency.yml:64`, `research-system-suite.yml:71`); `ci.yml` uses backslashes only under the default shell. (b) `git rev-list ... | tr | grep -qx "$target_head"` under `set -o pipefail` (note 1189): `grep -q` exits at the first match, the producer gets SIGPIPE, the pipeline status is 141, and `if !` takes the error branch for a head that is on the chain (I reproduced this in Git Bash with a long stream). (c) There is no step for `--ruleset-check ci-d8` and none for `run_w9_detector_controls.py --verify-watched-to-fail` (note 1112), although §4.2.3 and §9.2 describe both; the default `--ruleset-check require` would fail in CI if U-3 shows the token cannot read rule-suites. (d) The L-1 `push` trigger has no branch filter (note 1227).
- **R2-m6. U-3 probe records status only (note 299-302, 321-324).** The detector pins fields (`bypass_actors`, `rules[].parameters`, `conditions`: note 157-173) that GitHub may omit from a response to a non-admin token. A 200 would then be recorded as PASS while the pin check could not run. Record which pinned keys are present in the body under each token. Also state the probe PR's side effects: it triggers `merge-admission`, `ci` and the other `pull_request` workflows.
- **R2-m7. The U-4 dry-run recipe (note 406-423)** is a multi-line `python -c` in PowerShell (the project's rule is no generated code through `python -c`), imports `tools.w9_segmentation` with no stated working directory, and has the `KeyError` of R2-m3. Specify it as a scratch script file the reviewing session writes, and keep the output list (length, SHA-256, `link_count`, row counts, blocker count).
- **R2-m8. Control determinism (§9.2, note 1082-1092).** Only `GIT_CONFIG_NOSYSTEM=1` is set. A user-level `commit.gpgsign` or `core.autocrlf` changes commit and blob bytes. Add `GIT_CONFIG_GLOBAL` pointing at an empty file and `-c core.autocrlf=false -c commit.gpgsign=false`. "Bit-for-bit identical across machines" (note 1092) is not evidenced.
- **R2-m9. `main_ruleset` read.** The 30-day failure text says "without an owner reset" (note 179, 231), but no reset exists for `detector-controls.json` (compare `owner_cadence_reset` for the vault runs). Each pre-batch read is a reviewed PR plus `advance-binding`, unstated. The pinned contexts are names only; the live ruleset carries `integration_id: 15368` per check (my GET), which a ruleset edit could change.
- **R2-m10. §6.4 record integrity.** (a) The owner-note check says the slice must "contain each touched tuple (or the ruling reference)" (note 630): the matching grammar is unspecified (the register uses 8-character blob ids, for example `fecfc1da`), and "or the ruling reference" is an undefined escape. (b) The independent review is bound only by path and hash (note 631-635), not to the change, so any review committed earlier passes. (c) `P1` ancestry proves the entry is older than the PR, not that Stephen wrote it: the register and `reviews/` are not CODEOWNED and the ruleset requires zero approvals. B1's integrity therefore comes from I1, not from the `P1` anchor. State B1 as conditional on I1. (d) The `P1` ordering is stricter than W9 §4.2(b) (note and review before the PR); say it is the note's reading.
- **R2-m11. Option mechanics for A1, D3.** (a) D3 freshness by blob equality is not an ordering test: with entries `A -> B` and `B -> A`, an observation made before the first change satisfies the first entry through the later entry's `new_blob` (note 740). State the intent. (b) D3 names `tests/research_system/unit/test_w9_evidence.py` (note 1407); the change-list tests are `test_w9_evidence_acceptance.py` and `tests/research_system/integration/test_w9_wp9_3_2_runtime.py`. (c) A1 keeps the format string `w9-registration-manifest/1` for a 5-key shape and leaves `test_w9_evidence.py:62` (refuses an extra key) to change, while D3 proposes `/2`. Pick one policy. (d) A1 changes the LR-015 gate (`require_registered`), as D3 and E1 change LR-016; say whether A1 needs the same dated amendment.
- **R2-m12. `recheck_cl_export` does not raise on divergence.** It returns a report with `void` (`export_recheck.py:80-89`); only a malformed export or wrong producer raises. §8.2 (note 895) says the detector "runs" it. State that `report["void"] is True` is a closed failure.
- **R2-m13. Test lane and budget.** `tests/research_system/integration/test_w9_wp9_5_detectors.py` (W9-T7, M-6, O-13) has no stated lane; `research-system-suite.yml` runs selected tests with `-m "not live_store"`. The 20-35 s scratch-store estimate (note 1311) is cited to "WP9.4-2's single-store fixture timing" with no source I can find, and P-087 item 7 says profile one slow test alone before adding a scratch-store flow. Owner Point G's 120 s recommendation hangs on it (note 1410 also gives G1 as an alternative recommendation). Make the profile a pre-code step.
- **R2-m14. Baseline SHA authorship.** `baseline_commit` is "the L-1 parent commit" (note 569), which cannot be known when the PR is written under the queue, the reason the note rejects D1's `base_commit`. Allow any first-parent ancestor of the L-1 commit, with every guarded commit between it and L-1 disposed.
- **R2-m15. Claim 5 and the H row.** #368 (`452352ff`) is "record L5, A6, A7 and step 3 batches 1-3 of the 06s Phase 5 run", not a worktree sweep (note 1357, 1411).
- **R2-m16. Immutability snapshot (§11.3).** Exact equality of a recursive snapshot of the shared `.git` common directory is flaky when another session works in a sibling worktree, which is the project's normal state. I timed it: 3,305 files in 0.05 s, `status --ignored` 0.26 s, so cost is not the issue. Restrict the compare to what the test could write (`HEAD`, refs, `config`, `hooks`, the main index) or run it in CI only.

### Info

- **R2-i1.** `commits/<C>/pulls` "can transiently return `[]`" (note 605) is stated as fact; R1 raised it as a possibility and nothing evidences it. It is safe either way (retry, then the `pulls/<N>` hint).
- **R2-i2.** The `CONVENTIONS.md` check ignores `###` headings, rule lines, blank lines and the footer (note 831). A legacy `###` sub-heading can be edited or a legacy bullet moved under another sub-heading without a flag. R1-m11 asked for the exceptions to be stated; they are. Add them to the human-review table as HR-6.
- **R2-i3.** The live ruleset has parameters the pin ignores (`require_extra_approval_for_unattributed_changes: true`, queue `grouping_strategy: ALLGREEN`, `check_response_timeout_minutes: 20`, `dismiss_stale_reviews_on_push: false`). Optional.
- **R2-i4.** Check 1 of the vault detector rejects duplicate and unparseable headings among successor entries too (note 906); W9 §4.4 names "duplicated legacy heading anchors". Stricter than the spec; defensible, but say so.
- **R2-i5.** Rule-suite counts moved from 57 (33 bypass) to 58 (34 bypass) when #448 merged (`4ca375a3`, `bypass`); the note's 57 and 33 are correct as of its read and are dated.
- **R2-i6.** The `git count-objects` figures in §12.3 (58,133 objects, 28 packs, 335 MiB) and the clone timing are verified (below).

## 2. Citation audit

Method: `r2_cites.py` (scratchpad) resolved every `path:line(-line)` form in the note, including `06v:`, `W9:` and basenames, against `git show dbd54fe3:<path>` and printed the first cited line; I then read the load-bearing ones in full (`reader.py:140-206,241-262,285-300`, `evidence.py:92-154,221-252,277-362`, `acceptance.py:121-153`, `preparers.py:676-712,1198-1222`, `cli.py:1646-1722`, `segmentation.py:355-500`, `export_recheck.py:32-89`, `check_workflow_liveness.py:55-95`, the three CODEOWNERS and `GATE_FILES` blocks, the P-089 text, W9 §4.1-4.4 and §7.3, 06v D-4, the registration schema). A second script (`r2_symbols.py`) extracted 176 identifier-like backticked tokens and searched the tree at `dbd54fe3`; 38 are absent, of which only the ones listed under R2-m2 and R2-m3 are presented as existing code (the rest are new proposed names, JSON data keys, shell variables or PowerShell property names).

Counts: about 175 distinct code, plan and register citations resolved; 6 wrong (R2-m2 `contracts.py`; R2-m4 `03:6064`, `:6065`, `:6066`, `W9:754`; R2-M5 `CONVENTIONS.md:721-723` as the policy sentence). Seven reference the review, handover and follow-up files (resolved against the branch; all correct: R1 review `:116-124,183,198,299,300`; follow-up `:49-56,57-60`; handover `:175`).

Verified correct (selection, all at `dbd54fe3`): §2.3 `.github/CODEOWNERS:14-24` (eight paths, owner `@stephendor`), `GATE_FILES` `:341-350`, `test_codeowners_names_no_file_outside_the_gate` `:372-374`, `test_every_tools_and_contracts_test_runs_in_a_workflow` `:286-303`, `ADMISSION_CONTROL_MODULES` `:175-229` with `test_w9_segmentation.py` at `:226`, `ci.yml:166-216,210,239-241`, `admin-bypass-guard.sh:13-18`; §4 the permissions blocks of all five workflows (`ci.yml:88-89,139-140,239-241`, `merge-admission.yml:52-55,70-83`, sweep `:58-59,74-80`, currency `:12-13`, watchdog `:14-16`, suite `:30-31`), `check_bypass_merges.py:20-21,24,57-58,141-166`, `check_workflow_liveness.py:64-67,78-92`, `check_merge_admission.py:700-737`, `reader.py:152,160,168,241-248,157-204`, `anchor.py:1934-1950`, the P-064, 06v `U-3`, `U-4`, `D-1`, `D-5`, `D-7`, `D-8`, `O-9` to `O-13`, `O-32`, `W9-T7`, `W9-T19`, `L-0b`, `L-1` rows (`:159,160,563,567,569,571,189-193,212,230,242,593,594`); §5.3 `cli.py:1648-1659,1662-1684,1714`, `current_binding.py:801`, `identity.py:636-651`, `driver.py:147`, `reducers.py:70,571`, schema `:54-94,70-76,78-94`; §6 `acceptance.py:89-90`, `evidence.py:179-188`, `reader.py:51,289-299`, `segmentation.py:470-473`, `check_bypass_merges.py:25`; §7.3 and §7.4 `reader.py:43-49`, `segmentation.py:357-426`, `w9_segmentation.py:388-458`, W9 `:385-393,388-390,404-407,416-417`; §8 `accepted_w9.py:86-88`, `evidence.py:277-362,296-298,347-360`, `export_recheck.py:32-89`, contract `:100-105,168-169,184-192,242,254-258`; §16 `evidence.py:42,190-252`, `acceptance.py:121-136`, `preparers.py:686-690,1215-1218`, `acceptance.py:147-152`, addendum `:14-15,28,29`.

### The 22-commit first-parent table (§6.2.1)

I re-ran the same first-parent walk (`git --no-replace-objects rev-list --first-parent --reverse 4b143c92..dbd54fe3` gives 320) with `diff-tree -r --no-renames -z <P1> <C>` over `CONVENTIONS.md`, `results/`, `papers/`, `contracts/`, `.apm/`.

| Check | Result |
|---|---|
| All 20 table rows: SHA, parent count, first parent, `%cI` date, subject, touched guarded paths and `old -> new` blobs | Match the note exactly (including the 7 `results/` paths of `5df0c001`, the 3 manifests of `811d5a2b`, and the revert pairing in `b132406e`) |
| Total guarded first-parent commits | **22**, not 20 (R2-m1): `14a81b84` (#419), `1fba78aa` (#425) are missing |
| `gh api pulls/N` `merge_commit_sha` for 125, 129, 168, 169, 172, 178, 183, 215, 219, 277, 278, 334, 345, 368, 376, 384, 387, 388, 401, 419, 425, 433 | All equal the table's first-parent SHA; `#387` is `3fa437a1`; `#215` is `a426b731`; `#219` is `b132406e` |
| `commits/<sha>/pulls`: `dbd54fe3` | `#446`, `merge_commit_sha == dbd54fe3`; `5df0c001` and `811d5a2b` return `[]`; `4ca375a3` returns `#448` |
| `1af52f6d` | 2026-07-18T19:05:13+01:00, parent `02ebcaf6`, subject `[DATA] P01-B: ...` |
| `5df0c001`, `811d5a2b` file counts | 11 and 9 (`diff-tree` in a bare scratch clone) |

### `CONVENTIONS.md` unit counts

`research_system.legacy.segmentation.segment` and `tools.w9_segmentation.segment` over `4620c716` and `dbd54fe3:CONVENTIONS.md` (script `r2_seg.py`, run with `python -X utf8 -I`):

| | Baseline `4620c716` | `dbd54fe3` |
|---|---|---|
| Bytes / SHA-256 | 33,645 / `d04fe97e...8589` | 51,774 / `2ce15910...ff97c` |
| Lines (LF, no BOM) | 575 | 822 |
| Segmenters equal | yes | yes |
| Rows | 70 items, no blockers | 90 items, no blockers |
| Sections | 3, 2, 5, 4, 24, 13, 6, 3, 2, 8 (10 sections) | adds Repo-Wide CI (6); ARS Foundation Governance 9; Computational Environment 15 |
| Baseline units present in order at head | n/a | 70 of 70 |
| Inserted units | n/a | 20 = 6 (Repo-Wide CI) + 7 (ARS Foundation Governance) + 7 (Computational Environment); 0 in the other eight sections |

The 68 units in the nine non-governance sections, the 90 total and the "7 inserted in legacy sections" all match the note. Inserted units start with `**`, `- `, `Th`, `Re`: no table, so Control N6 behaves as described. `Always` 24 to 24 and `Never` 13 to 13 are correct.

## 3. Disposition of every R1 finding

| ID | Disposition | Evidence |
|---|---|---|
| R1-B1 | **Partly resolved** | Evidence timing is fixed: manifest at `P1` with union `C` (note 519, 692), records at `C` (note 520), Rule 0 (note 677-688), append-only baseline file (note 558-587), first-parent chain check (note 583-586). Not fixed: the tool that judges is the head's (R2-M1), pins and authority are circular or existence-only (R2-M1), the walk is stateless (R2-M2), the closure is open (R2-M3). |
| R1-M1 | Resolved | §4.3.1 and §4.3.3 figures equal the contract (`w9-segmentation-contract-v1.md:242,254-258`); the "Wait:" and the invented census are gone (grep of the note: only §18 mentions them); the §8.4 report example is labelled illustrative (note 992). |
| R1-M2 | Partly resolved | Every listed phantom symbol is gone; readers re-derived and checked (`reader.py:140-206`, `anchor.py:1934-1950`, `cli.py:1648-1684`, `evidence.py:277-362`, `accepted_w9.py:86-88`, `preparers.py:686-690,1200,1215`). New wrong names: R2-m2, R2-m3. Readers placed in `tools/` as R1 suggested (note 99-104). |
| R1-M3 | Resolved | Dates, parents, PR numbers, file lists and the `CONVENTIONS.md` per-section counts verified (section 2). W9-T7 derives paths with `git diff-tree`. |
| R1-M4 | Resolved | Rule 1 exclusions (note 693-700) and §6.6 scope (note 750-758) are consistent with the registration schema roles and `source_identity_kind` enum (`legacy-path-registration.schema.json:70-94`). |
| R1-M5 | Resolved | `conventions_lock` excluded (note 697, 776); Owner Point H added. I tested H1 on the three real tracker commits (section 5). |
| R1-M6 | Resolved with minors | D3 added with correct premises (`evidence.py:231-238`, `acceptance.py:135`, `blob_at` `:179`); WP9.3 changes named; D1 and D2 dismissed on verified grounds. R2-m11. |
| R1-M7 | Partly resolved | CODEOWNERS list, owner login, F1 vs F2, tripwire and its switch are correct. R2-M5 (I1 and I2 interplay), R2-m13 (integration test lane). |
| R1-M8 | Resolved | E1 gates at LR-003, LR-015, LR-016, LR-020 (sites verified), gates on `accepted_cl_export` not on file presence, defines `owner_cadence_reset`, states the weekly PR plus `advance-binding` cost and the self-attestation limit (HR-4). R2-m9 for the ruleset-read reset. |
| R1-M9 | Resolved with a defect | J1 defines the list and makes the 9-section partition provisional. R2-M4 (conventions classification unpinned), R2-m3 (ordinals 0-based). |
| R1-M10 | Partly resolved | `P1`-anchored `source_commit` and `review_commit`, Rule 0, Owner Point I, HR-3. The review is not bound to the change, `P1` age does not bind to Stephen (R2-m10); I1's mechanics (R2-M5). |
| R1-M11 | Resolved (design) | Runnable `pull_request` probe on a throwaway PR, third call, `pull-requests: read`, `X-Accepted-GitHub-Permissions`, which call decides D-8, the unverified claim marked. U-3 itself stays an open pre-code gate (note 1381, correct under the handover). R2-m6. |
| R1-M12 | Partly resolved | Dispositions for the post-audit writes `e3519ba7`, `633ed58e`, `a6a98966` are present; the table is incomplete by two commits (R2-m1). |
| R1-m1 | Resolved with a defect | D-8 quotes exact against `06v:571` and `P-064` item 8 `:4232-4233`; trigger restricted to rule-suites; gate is the `d8_...` field, which is existence-only and unprotected (R2-M1). |
| R1-m2 | Resolved | Pins match my live GET of ruleset `20822054` (section 5); 30-day rule added. R2-m9, R2-i3. |
| R1-m3 | Resolved | `os.scandir` snapshot plus `--no-optional-locks status --ignored`; costs 0.3 s. R2-m16. |
| R1-m4 | Resolved with a defect | Tool blob in the transcript, pinned dates, `--verify-watched-to-fail`. R2-m8; the verify step is not in the workflow (R2-m5). |
| R1-m5 | Resolved | Retry, `pulls/<N>` hint verified by `merge_commit_sha`, exit 2 vs 1. |
| R1-m6 | Partly resolved | `--pr-map`, `--manifest-file` locked to `skip`; the new `--baseline` and `--head` dispatch inputs are not (R2-M1). |
| R1-m7 | Partly resolved | `fetch-depth: 0`, head guard, `pull-requests: read`, `workflow_dispatch` only: correct. R2-m5 defects. |
| R1-m8 | Resolved with defects | Dry run specified; LF-only requirement dropped for the vault file. R2-m3, R2-m7. |
| R1-m9 | Resolved | D-1 path `C:/Users/steph/TDL-ARS-G7-Control` (`06v:563`); census from the 06h manifest and smoke test (blobs `1066404a`, `3b1eec6e` confirmed). |
| R1-m10 | Resolved | A1's projection to the three identity keys is right against `evidence.py:124-130`; `test_w9_evidence.py:62` must change and is named. |
| R1-m11 | Resolved | Table filter and explicit structural exceptions. Field names wrong (R2-m3); HR entry missing (R2-i2). |
| R1-m12 | Resolved | 16 claims; the false ones (claim 9 and the CODEOWNERS premise of 12) were corrected. |
| R1-m13 | Partly resolved | "Wait:" removed; stop rule 5 labelled as the note's own (note 1394). The header claim is again overstated (R2-m4). |
| R1-m14 | Resolved | T7-2 uses `GIT_INDEX_FILE` (note 1274); clone timing 1.71-1.79 s measured and reproduced (section 5); store-flow time is not measured (R2-m13). |
| R1-i1 to R1-i6 | Resolved (recorded or retained) | `.gitattributes:14` is `* text=auto eol=lf`; the live ruleset rows are in §4.2.2 and match my GETs. |
| R1 review section 2 (citations) | Mostly adopted | Section 2 of this review. |

## 4. Owner points A to J

| Point | Premises | Recommendation | Missing or wrong |
|---|---|---|---|
| A | Correct (`evidence.py:125,129`; `test_w9_evidence.py:62`) | A1 sound | R2-m11 (c), (d): format string and LR-015 gate treatment |
| B | Correct | B1 sound only with I1 | R2-m10 (c): B1 is conditional on I1; W9 §4.2(b) does not require the before-the-PR order |
| C | Partly wrong: "20 commits", and an unknowable baseline SHA | C1 acceptable | R2-M2 (no clear path), R2-m1, R2-m14 |
| D | Correct; D1 and D2 dismissals verified | D3 sound | R2-m11 (a), (b) |
| E | Correct against all four sites | E1 sound | none beyond R2-m9 |
| F | Correct (eight paths; string-presence test; precedent at `ci.yml:210`) | F1 sound | Interplay with I (R2-M5); lane of the integration test (R2-m13) |
| G | Correct (P-087 item 7) | Two recommendations (G2 or G1) | R2-m13: keep G1 until the store flow is profiled |
| H | Verified by test (section 5) | H1 sound | Define "outside the entries" (each real append adds one blank separator line, +1 byte, inside the section); R2-m15 |
| I | Wrong: I2 presented as sufficient; I1 fails an existing test | I1 needed, but incomplete | R2-M1, R2-M3, R2-M5 |
| J | Correct for the vault list (it is pinned through `ACCEPTED_CL_EXPORT`) | J1 sound for the vault | R2-M4 (conventions classification unpinned), R2-m3 (ordinals) |

## 5. What was checked and found sound

- **Ruleset facts.** My `gh api repos/ZK-Theory/TDL/rulesets/20822054` GET matches every pin in §4.1: `allowed_merge_methods: ["squash"]`, queue `merge_method: SQUASH`, `max_entries_to_build`, `min_entries_to_merge` and `max_entries_to_merge` all 1, `strict_required_status_checks_policy: true`, `require_code_owner_review: true`, `required_approving_review_count: 0`, `required_review_thread_resolution: true`, four contexts, `non_fast_forward`, bypass actor `{5, RepositoryRole, pull_request}`, include `["refs/heads/main"]`. Rule-suites: 57 (33 bypass) at the note's read, 58 (34) now.
- **Scratch clone.** `git clone --bare --local --no-hardlinks` of the worktree takes 1.78 s here, matches the note's 1.71-1.79 s, is 354 MiB, contains the replay commits, and `diff-tree` in it gives 11 and 9 files. `git count-objects`: 58,133 objects, 28 packs, 335.09 MiB. Immutability snapshot cost: 0.3 s.
- **H1 on real history.** On `452352ff`, `e3519ba7` and `a6a98966` (script `r2_tracker.py`): `working_note_entry` rows 112 to 113, 113 to 114, 114 to 115, zero blockers; all 95 `tracker_task_row` rows byte-identical; every earlier note preserved in order. The only other byte difference is one blank separator line inside the section and outside every entry.
- **B1 scenarios that revision 2 closes** (given a trustworthy tool): atomic disarm (an entry present at `P1` cannot be removed by `C`, Rule 0.1); retroactive false positives (a path registered later was not in `Manifest(P1)`); retroactive blessing (records at `C`, `pr_number` match); first commit after the baseline (`P1` is the baseline, the manifest is absent, treated as empty); a commit that adds a registration and edits the file (flagged, conservative); a 2-parent commit (`diff-tree <P1> <C>`); `walk-baseline.json` deletion (entries missing at `C`).
- **The 06v and W9 chains** the note relies on: the O-32 contradiction (`06v:90-91,212,479-481` against `evidence.py:231-238`, `acceptance.py:135`) is real as stated; P-089's boundary and item 3 quotes are verbatim.
- **Merging is not going live (mechanism).** `workflow_dispatch` only; `check_workflow_liveness.py:64-67` confirms a workflow registers only once on the default branch; permissions block and `fetch-depth: 0` are correct. The defects are in the steps (R2-m5), not in the trigger design.
- **No D-4 trigger** from the WP9.5 code scope as the note scopes it; the protected blobs (`schema_registry.py` `e32cb408`, `authority.py` `9b56b322`, 06h manifest `1066404a`, smoke test `3b1eec6e`, `w9_segmentation.py` `43e1454d`) are confirmed with `git rev-parse`. Options A1, D3 and E1 change accepted WP9.3 code and the note says so for D3 and E1 (R2-m11 (d) for A1).
- **`handle_bound_read`** reads exactly as §4.3.1 states (`st_nlink`, leaf junction refusal, root `reject_reparse=False`); `LegacyReader.__init__` is lexical, so the explicit junction check in §4.3.2 is needed.
- **`conventions_unit` mechanics.** A table unit begins with `|` (`segmentation.py:378`); duplicate `(section, unit_hash)` is a blocker (`:402`); unit identity is the unit's bytes. The insertion-only rule over ordered `unit_hash` per section is the W9 §7.3 item 4 rule for units.

## 6. Coverage of the handover's 17 items

| # | Item | Result |
|---|---|---|
| 1 | Scope, protected identities | Settled; R2-m2 (command count and file). |
| 2 | Ruleset read | Settled; pins verified live; R2-m9. |
| 3 | U-3 | Probe designed and runnable; gate in §15.1 item 1; R2-m6. |
| 4 | First-parent detector | Time-indexing sound; integrity of the tool, statelessness, closure open (R2-M1 to R2-M3). |
| 5 | M-6 export | Settled against real seams (`cli.py:1648-1684`). |
| 6 | Shared-surface rule | Settled; D3 premises verified; R2-m11. |
| 7 | `CONVENTIONS.md` check | Settled and verified numerically; classification input (R2-M4). |
| 8 | Vault detector, D-5 | Settled; ordinals (R2-m3), `void` (R2-m12). |
| 9 | U-4 | Metadata recorded (matches the brief); dry run specified; gate in §15.1 item 2; R2-m3, R2-m7. |
| 10 | Controls file | Settled; R2-m8; the verify step is not in the workflow (R2-m5). |
| 11 | Merging is not going live | Settled; tripwire switch specified; R2-M5 for I2. |
| 12 | Where the controls run | Settled; R2-m16. |
| 13 | Tests and budget | Inventory and timings given; clone and segmentation timings verified; store-flow time unmeasured (R2-m13). |
| 14 | Research assurance | MC and HR split; add HR-6 (R2-i2); MC-2 overclaims (R2-M1). |
| 15 | Claims for review | 16 claims; claim 2 is the one R2-M1 to R2-M3 attack. |
| 16 | Stop rules | §15.1 includes U-3, the U-4 reader and segmenter dry run, and Owner Points A to J decided in `P-090` (free: no `### P-090` on `origin/main`); §15.2 matches `06v:610-620`. |
| 17 | Owner points | Ten given, with options, recommendations and impact; see section 4. |

## 7. Revision plan

**Immediate corrections (author, no owner decision):**
1. R2-M1: add the trust-root paragraph; fix the YAML to run the pinned tree; define which baseline entry pins the tool; hash-bind decision references; put top-level fields under Rule 0; remove or lock the dispatch inputs.
2. R2-M2: add the `acknowledged` list and checkpoint mechanism, or an equivalent; say how a full re-walk is requested and reported.
3. R2-M3: compute and pin the detector's import closure; add the closure test.
4. R2-M4: pin the `CONVENTIONS.md` classification as an accepted code constant; add Rule 0 and control N7.
5. R2-M5: rewrite §16 I with the exact test, CODEOWNERS and `CONVENTIONS.md` edits and the bypass cost; state the I2 and F1 consequences.
6. R2-m1 to R2-m16, in particular: the 22-row table, `commands.py:16` and the count 12, the segment field names and 1-based ordinals, the wrong citation lines, the YAML defects, the dry-run script, and a header that says what was and was not verified.

**Owner decisions to put to Stephen after revision 3:** I first (B, C and the L-1 guard depend on it), then C (with the acknowledged-violation form), A, B, D (D3), E, F, G (G1 until the store flow is profiled), H (H1), J.

**Later-work dependencies:** the L-0b export and classified list (formats and pins); a dated WP9.3 amendment and independent review for D3, E1 and, if Stephen agrees it is a gate change, A1; a dated paths-addendum row for each new evidence file; a dated W9 §4.2 amendment if H1 is chosen; the U-3 probe result and the U-4 dry run before code.

**Residual risks the note should state:** the detector is post-merge and a human merge is the only preventive control; after I1 that human is Stephen, and the evidence and tool changes become bypass merges; rule-suites show 30 days only; under D-8 CI cannot see bypass use between batches; the weekly vault run is self-attested; the `CONVENTIONS.md` check does not see sub-heading or ordering edits outside units.

## 8. Commands run

All read-only. `git status --short` was empty before this report was written; the report is the only file added. No vault file was read; the vault junction and `Computational-Log.md` were not touched (the U-4 values in the note equal the brief's and were not re-read). No workflow was run, no probe was run, no `gh` call was other than a GET.

- `git` in the worktree: `rev-parse`, `show <rev>:<path>` (to stdout or scratchpad), `show -s --format`, `ls-tree`, `rev-list --first-parent --reverse 4b143c92..dbd54fe3`, `rev-list --parents -n 1`, `diff-tree -r --no-renames -z <P1> <C>`, `count-objects -vH`, `grep` at `dbd54fe3`, `diff --stat dbd54fe3 origin/main`, and a bare scratch clone (`git clone --bare --local --no-hardlinks <worktree> <scratchpad>\r2clone.git`, timed twice, then deleted).
- `gh api` GET only: `repos/ZK-Theory/TDL/rulesets/20822054`; `.../rulesets/rule-suites?ref=refs/heads/main&time_period=month&per_page=100` (with `--paginate --slurp`); `.../pulls/{125,129,168,169,172,178,183,215,219,277,278,334,345,368,376,384,387,388,401,419,425,433}`; `.../commits/{dbd54fe3,5df0c001,811d5a2b,4ca375a3}/pulls`.
- `python -X utf8 -I` scripts in the scratchpad (`C:\Users\steph\AppData\Local\Temp\claude\e088a017a981a492\f302c5e4-50e0-4fcc-b0af-3a36e9983c74\scratchpad`): `r2_inventory.py` (first-parent walk, 22 commits), `r2_cites.py` and `r2_cites_full.out` (citation resolver), `r2_symbols.py` (identifier search), `r2_seg.py` (both segmenters over the two `CONVENTIONS.md` blobs), `r2_tracker.py` (H1 against three tracker commits), `r2_snapshot_timing.py` (snapshot cost). Also a one-off `python -c` inside the repository's venv to print the row keys of one `segment()` row and the sizes of `LEGACY_COMMAND_TYPES`, `LEGACY_ROUTED_ROWS`, `LEGACY_DEFERRED_ROWS` (diagnostic only; nothing was composed into a file).
- Bash: `echo .venv\Scripts\python.exe` and a `set -o pipefail` `grep -q` pipeline, to confirm R2-m5.
- File reads: the note, the R1 review, the handover, the follow-up brief, P-089, P-087 item 7, 06v (D-4, §8, cited rows), W9 §4 and §7.3, `research_system/legacy/{reader,evidence,acceptance,preparers,segmentation,export_recheck,commands,routes}.py` (cited ranges), `research_system/cli.py:1646-1722`, `research_system/canonical.py`, `tools/check_workflow_liveness.py`, the registration schema, `.github/CODEOWNERS`, `tests/tools/test_ci_platform_policy.py` (policy tests and `GATE_FILES`), `.github/workflows/{ci,merge-admission,merge-admission-sweep,research-system-suite}.yml` (permissions, shells, python invocations), `CONVENTIONS.md:700-735` and section headings, `.gitattributes`, `06v-addendum-2026-11-10-w9-paths.md`.
- Not run, as instructed: the U-3 probe, the U-4 dry run, anything that reads the vault. Not verifiable here: how GitHub treats a `GITHUB_TOKEN` for the three U-3 endpoints (R2-m6), the 20-35 s scratch-store estimate (R2-m13), and the behaviour of the weekly D-5 flow on the operator machine.
