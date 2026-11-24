REWORK REQUIRED

# Independent adversarial review: WP9.5 design note, revision 1

| Field | Value |
|---|---|
| Subject | `docs/plans/agentic-research-system/transition/w9/wp9-5-design-note.md`, revision 1, commit `65363e27`, base `dbd54fe3` |
| Worktree | `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note` (read-only; `git status --short` empty at the end) |
| Reviewer | fresh session, no author context; skill `adversarial-design-review` |
| Date | 2026-11-21 |
| Verdict | **REWORK REQUIRED**: 1 Blocking, 12 Major, 14 Minor, 6 Info |

Citations of the form "note NNN" are line numbers in the note at `65363e27`. All other `path:line` values are at `dbd54fe3`.

## 0. Summary

The note is thorough and correct on several hard points. The first-parent mechanics, the `merge_commit_sha == C` PR mapping, the genealogy of `5df0c001` and `#215`, the `CONVENTIONS.md` baseline and its 68 legacy units, the ruleset facts and the O-32 squash-SHA contradiction are all verified below. Four things stop it being a basis for code.

1. **The detector's bar is defined by files the same commit can edit (R1-B1).** Every rule reads the registration manifest and the §4.2 records "at `<head>`" and walks from a fixed baseline. A single squash commit can remove a manifest entry and edit the file. The same design flags legitimate pre-registration edits forever. This lets the detector pass while a registered file changes.
2. **Several mechanisms are specified against code and data that do not exist (R1-M1 to R1-M3).** Examples: `_is_reparse_or_symlink`, `LegacyReplayEngine`, `state["store_binding"]`, `segment_bytes(profile=...)`, `AcceptedClExport`, and Computational-Log census figures that contradict the contract the note cites. The header says "every `path:line` citation was read directly". That is not so.
3. **The fail-closed check in §6.6 and Rule 1 misfire on states W9 itself creates (R1-M4, R1-M5).** These include untracked and restricted registrations, `results/ars/` before it exists, the `conventions_lock` registration, and routine `.apm/tracker.md` appends.
4. **Owner points C, D, E and F are framed on incomplete or wrong premises (R1-M6 to R1-M9).** The O-32 diagnosis (D) is right but D1 is unsound, and a simpler blob-keyed option is missing. The F2 recommendation leaves every new test unrun in any PR lane.

Nothing here needs Stephen to reverse an accepted decision. It does need a revision 2 before the owner points go to him.

## 1. Findings

### Blocking

#### R1-B1. Every rule evaluates historical commits against evidence read at `<head>`, so one commit can disarm the detector and the baseline cannot be both fixed and correct

- **Where:** note 376-380 (inputs read "at `<head>`"), 477 and 495-497 (Rule 1 matches against `registration-manifest.json` at `<head>`), 507, 516-518 and 538-545 (records and change list "at `<head>`"), 382-397 (Owner Point C: baseline "pinned at L-1", "a pinned field or constant"), §16 C.
- **Evidence:**
  - Note 380 and 410-412: the walk visits each first-parent commit `C` and diffs `P1` to `C`. Nothing evaluates the manifest at `P1` or at `C`.
  - `research_system/legacy/evidence.py:92-105`, `read_evidence`, reads one file "from Git at the binding's `git_head`". The detector copies that convention without its reason. WP9.3 wants a single bound head. A detector must judge each commit by the evidence in force when it landed.
- **Failure scenarios.**
  1. *Atomic disarm.* One squash commit `C` deletes (or rewrites) the entry for registered file `F` in `registration-manifest.json` and edits `F`. At `<head>` the manifest has no `F`, so Rule 1 never fires. No rule protects the manifest itself. `--check` against the store (note 352-356) runs only by hand before a batch.
  2. *Retroactive false positives.* Registration of `.apm/tracker.md` happens at `T1`. Commits between the L-1 baseline `T0` and `T1` were legal. The head manifest lists `.apm/tracker.md`, so every later run from the pinned baseline flags them with no record possible. Option C1 pins the baseline at L-1 and never says how it advances.
  3. *Retroactive blessing.* Records are read at `<head>`. A later PR that adds a `legacy-write-records.json` row for an earlier violation turns a red detector green. 06v says "the PR making the change carries its own entry" (06v:479-481, 486), which means the record is in `C`, not in a later commit. The note's own text (note 393) rejects "fabricated retroactive records" for pre-W9 commits, then enables the same thing post-L-1.
  4. *Detector self-edit.* `tools/check_legacy_writes.py` is read from the checkout at `<head>`, so a commit that weakens the tool and writes a legacy file is judged by the weakened tool (see R1-M10).
  5. The baseline commit is "a pinned field or constant" in the tool (note 396). Advancing it past a bad commit is a one-line PR to an unguarded file.
- **Impact:** the detector can be disarmed by the very commit it should catch, and can fail permanently on legitimate history. Both defeat W9 §4.4's purpose.
- **Change needed (proposed text for the note):**
  - Rule 1 and Rule 3 evaluate commit `C` against the manifest **at `P1`** (registered before the commit). Rule 2 needs no manifest.
  - §4.2 and §4.3 records are read **at `C`**: the PR carries its own record, as 06v says. Nothing later can bless `C`.
  - Add **Rule 0**, a monotonicity rule. Any commit that changes `registration-manifest.json` other than by appending entries fails. Any commit that touches `legacy-write-records.json`, `shared-surface-changes.json`, `detector-controls.json`, the four detector tools, or `legacy-write-detector.yml` other than by appending fails unless it carries an owner-attested record (owner decision H, R1-M10).
  - The baseline is a committed, append-only evidence row (for example `walk-baseline.json`), added in the L-1 PR and advanced only by a reviewed PR that names the new commit. Add a check that the baseline lies on `head`'s first-parent chain, not only that it is an ancestor (note 404).
  - The workflow runs the detector tool from the **baseline** commit, or compares its blob with the committed pin. A weakened tool cannot clear the commit that weakened it.

### Major

#### R1-M1. Fabricated Computational-Log census figures attributed to the segmentation contract

- **Where:** note 275 (also 303, 736-737), the U-4 "prior recorded evidence" column and the §8.4 report example.
- **Claim:** the contract (`w9-segmentation-contract-v1.md:235-236,242,254-256`) records the live log at 376,784 bytes, SHA-256 `4c1898aa…`, "143 rows: 141 item, 1 structural, 1 blocker at lines 541-545", "105 rows in the legacy tail from line 662".
- **Evidence:** `grep -rn "376,784\|4c1898aa"` over `docs/`, `research_system/`, `tools/`, `tests/` finds only the note. The cited lines say the opposite. §8 row 1 (line 242): 700,632 bytes, SHA-256 `de44a67b…`, 255 dated entries and 1 structural block at L4436, "**no blockers**". Lines 254-256: 703,531 bytes, `19ad5c4d…`, 256 entries, structural block at L4476, "with no blockers".
- **Why it matters:** the note builds §8.2 Check 1b on a pre-existing blocker that does not exist. The U-4 dry run would compare the live file with a baseline that was never recorded. The header (note 12) says every citation was read directly.
- **Change needed:** replace the figures with the contract's, labelled "WP9.2 census, not a baseline". Delete the invented blocker discussion. Remove the unedited "Wait:" text at note 691. Re-derive the report example (`legacy_items_verified`, `live_file_byte_length`) from the contract or mark it a placeholder.

#### R1-M2. The note specifies mechanisms against code that does not exist

Each row is "note says" against "code at `dbd54fe3`". An implementer following the note would write the wrong code.

| Note | Cited | Actual |
|---|---|---|
| 278, 285, 4.3.2 | `_is_reparse_or_symlink` (`reader.py:109-116`), `FILE_ATTRIBUTE_REPARSE_POINT = 0x0400` (`reader.py:41`), `_is_within`, `os.path.realpath` on the open fd (`reader.py:182`) | None exist. `reader.py:108-114` is `_relative`; `:41` is a comment about `IMPORTER_MODULES`; `:182` is a tuple of stat fields. The code uses `candidate.is_symlink() or candidate.is_junction()` (`:168`), per-directory anchors, and `candidate.resolve(strict=True)` (`:192`). |
| 14 item 9, 276 | `handle_bound_read` "refuses the repository junction" | It does not. `open_registered_root_anchor` "may themselves be junctions … follows the root alias" (`research_system/store/anchor.py:1934-1950`, `reject_reparse=False`). The only refusal is `LegacyReader.__init__` (`reader.py:241-248`), which is **lexical** (`os.path.abspath` then `relative_to(repository_root)`), so a junction placed outside the repository would pass. The detector must write its own check. |
| 328, 351 | `LegacyReplayEngine(...).replay()` in `research_system/legacy/replay/engine.py` | No such class or file. `research_system/legacy/replay/` holds `__init__.py`, `driver.py`, `reducers.py`. The read-only seam is `_legacy_projection` (`cli.py:1648-1659`) calling `replay_legacy` (`replay/driver.py:147`). |
| 353 | `state["store_binding"]` | No such key. The binding comes from `load_current_binding` (`research_system/store/current_binding.py:801`; `cli.py:1666-1688` `_legacy_current_binding`), and `binding.binding["git_head"]`. |
| 351 | `canonical_bytes` is "2-space pretty JSON with trailing `\n`", in `research_system/core/canonical.py` | No such path. `research_system/canonical.py:36-43`: compact, `sort_keys`, `separators=(',', ':')`, ASCII keys, rejects floats. |
| 567, 681 | `segment_bytes(..., profile="conventions_unit", region=None)` | `segment(data, selector_kind, *, level, region, structural)` (`segmentation.py:429`; `tools/w9_segmentation.py:461`). |
| 677 | `evidence.require_cl_export(repository_root, git_commit, export_path, expected_export_blob=..., expected_retained_blob=...)` | `require_cl_export(export: Any)` is a pure shape check (`evidence.py:277`). |
| 719 | `AcceptedClExport(version=…, export_path=…, export_git_blob=…, retained_copy_path=…, accepted_in=…)` | A mapping `{"export": {...}, "retained_copy": {...}, "classified_list": {...}}`, each member `{repository_path, git_commit, git_blob, sha256, byte_length}` (`accepted_w9.py:86-88`). |
| 377, 379 | `require_registered` and `require_change_list` "validate" the manifest and the change list | `require_registered(manifest, registration)` needs a registration to look up (`evidence.py:114`). `require_change_list(root, head, declared)` needs an acceptance's `enforcement_change_list` (`:190`). The detector has neither. |
| 354 (and 691) | `require_cl_export` "forbids any blocker row in the export" (`evidence.py:322,354`) | Not so. Those lines check `suppressed_anchors` and the classification slot keys. Segmentation contract §6.4 (line 177) says the export carries blockers. |
| 691 | `export["region"]["kind"] == "whole_file"` / `"line_range"` | No such field. `selector.region` is `{first_line, last_line}` (`evidence.py:296-298`). |
| 151, 314, 320, 832 | `prepare_path_registration` at `preparers.py:114`; `prepare_observation` at `preparers.py:216` | `prepare_proposal` (`preparers.py:676`), controls check at `:686-690`; `prepare_observation` at `:1200`, `require_registered` at `:1215`. |
| 83, 1025 | segmenter pin at `accepted_w9.py:67` | The pin is `evidence.py:52-54`; `accepted_w9.py:67` is a decision-ref domain string. |

The detector's reader surface (§2.3 list, note 90-97) is therefore also incomplete. WP9.5 needs: a manifest loader that returns entries; a change-list loader that does not need an acceptance reference; a records reader (named); and the junction-refusing vault read. Each lives in `research_system/legacy/` under P-089's "a reader WP9.5 needs, and the note names it". Name them all, or place them in `tools/` and keep `research_system/legacy/` untouched, which would be a better reading of P-089's boundary.

#### R1-M3. Wrong facts in the replay-commit genealogy and fixtures (W9-T7 acceptance text is wrong as written)

- **Where:** note 385-392 (§6.2), 419-422, 905-912, §12.1 row 1, Option C2.
- **Evidence (all `git`/`gh api` GET):**
  - `811d5a2b` is committed 2026-08-07 00:12 +0100, not 2026-08-05 (note 421). `#219` is merge `b132406e`, merged 2026-08-08T21:23Z, not 2026-08-06 (note 388-389, 422). The W0 re-review the note cites says "811d5a2b (2026-08-07)" and "3bfb279c (2026-08-08 …)".
  - `5df0c001` touches 11 files: 7 `results/` files and four others (`.claude/CLAUDE.md`, two `.codacy/*`, `.repowise-workspace.yaml`). Only 3 of the 7 results files are under `results/trajectory_tda_integration/stage1/`. The paths the note prints (`…/stage1/bhps_nonoverlap_reanalysis_2026-06-09.json` and `…/stage1/01_trajectories.json`, note 907-908) do not exist. The real paths are `results/panel_methodology/bhps_nonoverlap/bhps_nonoverlap_reanalysis_2026-06-09.json` and `results/trajectory_tda_integration/01_trajectories.json`.
  - `811d5a2b` touches 9 files: 3 manifests plus 6 others.
  - §6.2 and Option C2 name five of the post-freeze writer commits wrongly. `2ef7d8fc`, `17fb5f4d`, `3c64a021` exist in no object store. #168 is `9016b663`, #169 is `2111ce62`, #277 is `1dbf6b7b`, #368 is `452352ff`. `3fa437a1` is **#387**, not #368. `1af52f6d` is `[DATA] P01-B: commit Markov-2 alpha=1 cell JSONs (H6 ruling)` (parent `02ebcaf6`, merged by #129 `5795a18b`), not "#127, 32-file P01-B reconciliation merge". #127 is `60148663` (a `CLAUDE.md` symlink fix).
  - §7.4 item 4 (note 623) says `## Always` and `## Never` hold inserted successor bullets. Segmentation at `dbd54fe3` gives Always 24 to 24 units, Never 13 to 13. Only `## Computational Environment` grew (8 to 15). The `inserted_successor_units: 31` example (note 636) is also wrong: inserted units inside the nine legacy sections number 7.
  - Examples `contracts/Validation-Table.md` and `contracts/schemas/meta_contract_schema.yaml` (note 514) do not exist; the note's "Validation-Table.md precision edit (#368)" has no counterpart.
- **Why it matters:** W9-T7 asserts "all 7 stage-1 files" and "10 files". Written from the note it fails on real data. Option C2's historical table would commit three nonexistent hashes.
- **Change needed:** derive the file lists with `git diff-tree` in the test (the note already says to) and delete the hard-coded paths. Correct the dates and the commit map from `gh api pulls/N` (`merge_commit_sha`). The handover's "5df0c001 is a merge commit (#215)" was wrong; the note's correction (single parent `a426b731`) is right.

#### R1-M4. The "unreadable registered file" check (§6.6 item 2) fails permanently on states W9 creates

- **Where:** note 540-542.
- **Evidence:** for every `repository_root` manifest entry the detector requires `git cat-file -e <head>:<path>` and, for files, `cat-file -t == blob`. Registrations also include:
  - `untracked_file` and `restricted_untracked_file` (`*.csv`, `*.pkl`, `.apm/memory/stage-NN/` logs, `.apm/bus/`: W9 §3.1, §5.4; registration schema `source_identity_kind` enum; restricted-suffix rule forces `restricted_untracked_file`). They are not in Git.
  - `successor_results_root`, normalized path exactly `results/ars/` (schema `allOf`). `git ls-tree origin/main results/ars/` is empty today, so the check fails on the first batch that registers it.
  - `legacy_read_only_projection`, path `^\.research-system/projections/legacy/`, `source_identity_kind: untracked_file`.
  - `legacy_manuscript_root` directories (the note covers these with "blob/tree").
- The manifest carries only `root_kind`, `root_id`, `normalized_path` (`evidence.py:125`), so the detector cannot tell tracked from untracked.
- **Why it matters:** the detector would be red from the first batch that registers any CSV or the successor root.
- **Change needed:** the manifest must carry `role` and `source_identity_kind` (owner point A, widened). The existence check applies only to `git_tracked` registrations and exempts `successor_results_root`. Say what the detector does for an untracked registration (nothing it can see; the vault and pre-batch checks cover it).

#### R1-M5. Rule 1 ignores the `conventions_lock` registration and routine `.apm/tracker.md` appends

- **Where:** note 495-497 (Rule 1 matching; exclusions limited to `successor_results_root` and `shared_enforcement_surface`).
- **Evidence:**
  - W9 §7.3 (last paragraph): "`CONVENTIONS.md` is repository-canonical … It is registered at its repository path only." The registration schema has role `conventions_lock` with `normalized_path: CONVENTIONS.md`. Under Rule 1 every successor edit to `CONVENTIONS.md` (the insertion-only path W9 §4.4 permits) fires Rule 1 and needs a §4.2 record. §7 of the note never mentions `conventions_lock`.
  - Since the freeze, three first-parent commits touched a legacy-owned coordination file with no record: `#388` `e3519ba7` (2026-10-22, `.apm/tracker.md`), `#433` `a6a98966` (2026-11-12), and `#368` before them. W9 §4.1 lists "session Working Note through a reviewed PR" as an observed writer. W9 §4.2 and the note's allowance kinds (note 481-485) list none. With `.apm/tracker.md` registered whole-file, each Working Note PR fires Rule 1 and also triggers O-33 re-observation. The project's own rules append to it at every worktree sweep.
- **Why it matters:** the detector would be red on routine work, which teaches operators to ignore it, or forces a §4.2(b) note per append.
- **Change needed:** Rule 1 excludes `role == conventions_lock` (governed by §7). Add a new owner point (H): how are tracker Working Notes handled? Options: a W9 amendment adding a mechanically checked "pure append under `## Working Notes`" allowance (the `working_note_entry` segmenter already exists); or register the tracker at a granularity that excludes appends; or accept a record per append.

#### R1-M6. Owner point D: the O-32 diagnosis is correct, but the options are incomplete and D1 is unsound

- **Verified:** `evidence.py:231` closes entries to `{merge_commit, surface, affected_registrations}`, with `merge_commit` a 40-hex SHA (`_SHA1`, `:233`). `acceptance.py:135` tests `is_ancestor(entry["merge_commit"], source.git_commit)`. A PR cannot name its own squash SHA (06v:90-91). The PR branch head is not an ancestor of `main` after a squash. `git merge-base --is-ancestor P1 P1` returns true, so naming `P1` lets a pre-change observation pass. 06v WP9.5 says "WP9.3 reads the list unchanged (06v:481)" and O-32 says the entry names "the contract and its old and new blobs" (06v:212). The first statement is false as built. The note's analysis is right and its decision to surface it is right (handover §5).
- **Gaps:**
  - **Missing option D3 (blob-keyed freshness, simpler).** Entry is `{pr_number, surface, old_blob, new_blob, affected_registrations}`, with no commit field. Freshness becomes tree-state: the item's observation commit holds `surface` at `new_blob`, or at a later entry's `new_blob` for the same surface. That uses `evidence.blob_at` (`evidence.py:179`), already present. There is no SHA to know in advance, no history walk, and no reflexive-ancestor trap. A variant derives the change commit post hoc as the first commit on `git_head`'s first-parent chain where `blob_at(c, surface) == new_blob`.
  - **D1 as written is unsound.** `base_commit` is "the `main` commit the PR is based on / queued against" (note 1042). Under the merge queue (`merge_queue.max_entries_to_merge = 1`, strict required checks, rule read at 2026-11-21) base moves, so a stale `base_commit` is an ancestor of observations taken **between** it and the squash commit. `obs != base and is_ancestor(base, obs)` then passes a pre-change observation. The blob test D1 adds ("`<obs_commit>:<surface>` has blob `new_blob` (or a later successor blob)") is what does the work, and "later successor blob" is undefined. `base_commit` adds false assurance.
  - **D2's window.** The detector is red after every shared-surface change until the follow-up PR lands. The acceptance preparer has no way to know a change is missing (no entry means no check). "Before the binding advances" is not enforced by anything.
  - **What D1 or D3 changes in accepted WP9.3:** `evidence.py:_change_entries` (the closed `w9-shared-surface-changes/1` format needs a version bump or a tagged union, because P-081 item 4 fixed it); `acceptance.py:check_change_list` (`:121-136`); `require_change_list`'s docstring; WP9.3's tests and note §10.4; and the LR-016/LR-020 acceptance-preparer behaviour. These modules are not in `IMPORTER_MODULES` (`reader.py:42`, which lists `reader.py` and `segmentation.py` only), so `tool_sha256` does not move. They are a gate, not "a reader", so they exceed P-089's boundary and need a dated WP9.3 amendment, an independent review and a register entry.
- **Disposition:** reframe (see §3).

#### R1-M7. Owner point F: F2 is nominal compliance and the stated CODEOWNERS facts are wrong

- **Where:** note 98-101, §10.2 item 4, §16 F.
- **Evidence:**
  - `.github/CODEOWNERS` lists exactly eight paths: itself, `merge-admission.yml` (config), `merge-admission.yml` and `merge-admission-sweep.yml` (workflows), `ci.yml`, `tools/check_merge_admission.py`, `.claude/hooks/admin-bypass-guard.sh`, `.claude/settings.json`. `GATE_FILES` (`tests/tools/test_ci_platform_policy.py:341-350`) is the same eight; `test_codeowners_names_no_file_outside_the_gate` (`:372-374`) asserts equality. `tools/check_test_commit_literals.py` and `tests/tools/test_ci_platform_policy.py` are **not** owned (note 99-100 and F1 say they are, citing `CONVENTIONS.md:721-723`, which lists neither). The owner login is `@stephendor`, not `@stephen`. Only `ci.yml` makes F1 need Stephen's bypass.
  - `test_every_tools_and_contracts_test_runs_in_a_workflow` (`:286-303`) checks **string presence** of the module path in any `run:` script. F2 satisfies it by naming `tests/tools/test_w9_detectors.py` in the `workflow_dispatch`-only detector workflow. That workflow never runs on a PR, so the new unit tests, including `test_legacy_write_detector_workflow_is_inactive_until_l1`, run in no PR lane. This is the failure the test's own docstring and obs `2026-11-03-gate-controls-outside-the-hook-glob-run-in-no-lane` exist to stop.
  - F2's companion `tests/research_system/unit/…` "wired in `tools/affected_research_tests.py`" has no mechanism. The selector picks tests that import changed `research_system` modules or pinned `.research-system` paths. Edits to `tools/check_*.py` select nothing.
  - The tripwire (note 879-881) asserts `on == {workflow_dispatch}` and that `detector-controls.json` does not exist. The L-1 activation PR changes both, so it fails the tripwire. The note does not say how L-1 edits it. If the tests do not run on PRs (F2), nothing trips and a normal PR can activate the workflow, which defeats "L-1 is a separate owner decision".
  - Precedent: `tests/tools/test_w9_segmentation.py` is already in `ADMISSION_CONTROL_MODULES` (`:226`) behind one gate-file bypass.
- **Change needed:** correct the CODEOWNERS list and owner login. Present F1 honestly as the only option that puts the controls in a PR lane, noting Stephen performs the bypass himself (the `admin-bypass-guard` forbids agents, `admin-bypass-guard.sh:13-18,67-68`). Specify how the tripwire is switched at L-1 (an explicit constant edited by the L-1 PR and reviewed by Stephen). Consider adding the workflow to CODEOWNERS/`GATE_FILES` as part of F1.

#### R1-M8. Owner point E: D-5 enforcement is placed too late, has an undefined reset, and is self-attested

- **Where:** note 759-767, §16 E.
- **Evidence:**
  - E1 hooks `check_environment` (`acceptance.py:139-153`), which runs at **LR-016/LR-020** (`preparers.py:706`, `:1029`): closed-reference acceptance. A "batch" starts with LR-003 registration and LR-015 observation (06v §7 batch checklist, "Before every batch"). By acceptance time the batch's registrations and observations are recorded. The gate is proven after the work it governs.
  - Rule (b) ("any two consecutive runs > 7 days apart", since L-1 "or the most recent explicit owner cadence reset `owner_reset_ref`") makes one missed run a permanent block. `owner_reset_ref` is not in the `w9-vault-detector-runs/1` format shown (note 743-757). D-5 says a missed run "blocks the next batch", not every later batch.
  - Runs are read at the binding's `git_head` (`evidence.read_evidence`). Each weekly record is therefore a reviewed PR **and** an `ars store advance-binding` (06v §6 D-1: "each by Stephen's authorization"). The note does not state this weekly cost.
  - `run_at` and `output_sha256` are written by the same operator machine that produces them; nothing independent checks that a run happened. CI cannot see the vault.
  - A cadence check "gated on `ACCEPTED_CL_EXPORT` being populated or the runs file being present" (note 1043): gating on "file present" lets deleting the file disable the check.
- **Change needed:** put the freshness gate at LR-003 and LR-015 (batch start) as well as, or instead of, LR-016/LR-020. Define the reset (a recorded owner entry) or drop rule (b). State the weekly PR and advance cost. Say plainly that the cadence is self-attested.

#### R1-M9. The legacy/successor classification source for both content detectors is unsettled

- **Where:** note 692-696 (Check 2), 598-599 and 587-599 (§7.3).
- **Vault detector:** the note reads `export["classifications"]` and requires every slot to be `legacy` or `successor`. `ACCEPTED_CL_EXPORT` carries a **separate** accepted `classified_list` (`accepted_w9.py:86-87`), and D-7/L-0b produce the export first, "then the classified legacy-entry list, accepted by Stephen" (06v §7, L-0b). `require_cl_export` allows `class: None` and any string (`evidence.py:353-357`). No WP9.3 reader or format exists for `classified_list`. The note never mentions it, so the format and where legacy/successor lives are unsettled, and the "no code change when L-0b lands" claim (note 721) is unsupported.
- **`CONVENTIONS.md` check:** it hard-codes nine sections as wholly legacy. W9 §7.3 item 1 makes the legacy set "decided by object, then date", with "ARS-lane entries and locks … successor regardless of date", and says the baseline observer classifies every lock for Stephen's acceptance. L-0b's row records "the `CONVENTIONS.md` baseline". Section-wholesale is the stricter reading and may flag a successor amendment of an ARS-lane unit inside a legacy section.
- **Change needed:** state that the nine-section partition is provisional until L-0b's accepted classification. Define the `classified_list` input. Make the checker take the accepted classification as an argument rather than a hard-coded set.

#### R1-M10. Records and the detector itself have no integrity beyond a human merge

- **Where:** note 477-487 (§4.2 record validation), 516-518, §13.2, §14.
- **Evidence:** the §4.2 record names `owner_note.author == "stephen"`, a `source_ref` and hashes. The detector checks that the referenced files exist and the hashes match. A PR author can write `"author": "stephen"` and a review file of their own in the same PR. W9 §4.2(b) requires Stephen's attributed note and an *independent* review, and says "the writer's own note does not qualify". The repository merges with zero required approvals (`required_approving_review_count: 0`, read live) and 33 of 57 rule-suite entries on `refs/heads/main` in the last month are `result: bypass`. `.research-system/evidence/w9/*` is not code-owned.
- **Why it matters:** this is the "self-definition of the bar" pattern. HR-1 admits semantic equivalence is human-only, but the attribution, the independence and the owner ruling's existence are presented as checked and are only self-asserted.
- **Change needed:** at minimum require `source_ref` to name a register entry that exists **at `P1`** (before the PR), with `note_sha256` matching that entry. For the independent review, require the review commit to precede `C`. Add owner decision H below: CODEOWNERS and `GATE_FILES` coverage for the detector's own files and evidence files, so editing them takes Stephen's bypass.

#### R1-M11. U-3 probe is not runnable as specified, and the workflow's token does not cover what the detector calls

- **Where:** note 198-251, 195-196, 370, 855-861.
- **Evidence:**
  - A workflow with `on: workflow_dispatch` only cannot be dispatched until its file is on the **default branch**. It is not even listed on GitHub's API before then. A probe from the PR branch is not possible. Merging a probe workflow to `main` is itself a new act P-089 does not authorize ("any write to `main`"). `tools/check_workflow_liveness.py:61-67` already records this for new workflows.
  - The probe covers the two ruleset GETs only. The detector also calls `commits/<C>/pulls`. The workflow skeleton declares `permissions: contents: read` only (note 849-850); every existing workflow that reads PR data declares `pull-requests: read` (`merge-admission.yml:52-55`, plus `checks: read`). Under `contents: read` alone `pull-requests` is `none`. The repository is public (`gh api repos/ZK-Theory/TDL`: `private: false`), so this may still work, but it is unprobed, and the PR mapping is load-bearing for Rules 1 to 3.
  - The note asserts as fact that the REST API requires administration permission for both ruleset endpoints (note 194). Only `tools/check_bypass_merges.py:20-21` is cited, and it says **rule suites**, not rulesets. The configuration read may be possible anonymously or with `metadata: read` on a public repo; this is unverified.
- **Change needed:** specify the probe as a `pull_request`-triggered temporary workflow on a throwaway, never-merged PR (token scoped by the `permissions:` block), or as a `workflow_dispatch` workflow merged by Stephen. Add the third call (`commits/<sha>/pulls` under `permissions: contents: read` and under `pull-requests: read`). Record `X-Accepted-GitHub-Permissions` from `gh api -i`. State which call decides D-8. Remove the claim at note 194 or mark it unverified.

#### R1-M12. Owner point C's rationale is false for three post-audit writes

- **Where:** note 393-397, §16 C.
- **Evidence:** Option C1 argues the pre-L-1 period is closed by G7-A §11. G7-A's evidence snapshot is `3fa437a1` (2026-10-21). Since then three first-parent commits wrote legacy-owned files with no §4.2 record: `e3519ba7` (#388, `.apm/tracker.md`), `633ed58e` (#401, 2026-10-27, `results/trajectory_tda_integration/stage1/SUPERSEDED.md`, a registered-class `legacy_supersession_manifest`), `a6a98966` (#433, `.apm/tracker.md`). `wp9-3-design-note.md:978` itself names #401. The note's §6.2 list and C2 table name none of #388, #401, #433, nor `#125`/`02ebcaf6` (3 `results/` files, merged right after the freeze), and misname several that they do list (R1-M3).
- **Change needed:** record a disposition for each first-parent commit between `4b143c92` and the chosen baseline that touches a guarded path (the loop in §5 below lists them), and decide whether the L-1 baseline is after them. Define the baseline record (R1-B1). C2 needs a corrected list.

### Minor

- **R1-m1. D-8 quote and citation (§4.2.3, note 255-258).** The quoted text is exact against 06v:571, but it is 06v's text. P-064 item 8 (`03-decisions-and-open-questions.md:4232`) is a paraphrase ("This applies only if U-3 shows the CI token cannot read rule-suites. Bypass use between batches is then a known limit, seen at the next pre-batch read."). `:3996` is an unrelated entry. The note widens the trigger to "or `rulesets/20822054`", which D-8 does not. The `--ruleset-check ci-d8` flag is selectable by whoever edits the workflow; 06v's U-3 row says "It is not a package-level fallback", so activation should require a recorded owner acknowledgement in the evidence area.
- **R1-m2. Ruleset read is under-pinned (§4.1).** The real ruleset also fixes `allowed_merge_methods: ["squash"]`, `merge_queue.merge_method: SQUASH`, `max_entries_to_merge: 1`, `strict_required_status_checks_policy: true`, `required_review_thread_resolution: true`, and four required contexts. The one-at-a-time squash assumption (06v:90-91, `check_merge_admission.py:700-737` with `max_entries`) rests on the first three, which the read does not pin. The example `target_include: ["~DEFAULT_BRANCH"]` is wrong: the live ruleset has `["refs/heads/main"]`. The rule-suites API reads at most one month (`check_bypass_merges.py:24,57-58`), so a gap between reads longer than 30 days is invisible. Say so, and fail closed if the previous recorded read is older than 30 days.
- **R1-m3. Immutability proof (§11.3) is weaker than claimed.** `git status --porcelain` does not list ignored files and itself refreshes `.git/index`. `HEAD` plus `show-ref` miss new loose objects, `config`, hooks, `FETCH_HEAD`, and writes outside git (the vault, `.ars`). Prefer a recursive `(relpath, size, mtime_ns)` snapshot of `.git` and of the tracked/ignored working tree taken with `--no-optional-locks`, plus `GIT_DIR`/cwd pinned to the scratch clone in every detector invocation. `--no-hardlinks` is adequate for the clone itself (verified: a bare `--local --no-hardlinks` clone of the worktree has the pack copied, includes `5df0c001`, and carries hundreds of local-branch refs but no `refs/remotes/origin/*`).
- **R1-m4. Control output hashes are not bound to the detector they certify (§9.2).** `require_detector_controls` checks shape only (`evidence.py:133-154`). A later weakening of a detector tool leaves the committed hash valid. The transcripts include `<C>` SHAs of commits synthesized in `tmp_path`, which vary with timestamps and identity unless `GIT_AUTHOR_*`/`GIT_COMMITTER_*` dates are pinned, so "deterministic" does not hold for case 3 and 4. Include each tool's blob in the transcript, pin Git dates, and re-run the controls in CI to compare with the committed hash.
- **R1-m5. PR mapping failure modes (§6.3, §6.6 item 3).** The `merge_commit_sha == C` rule is sound (verified: `dbd54fe3`→#446, `e053462a`→#447, `1b2cebf7`→#445 all match; `5df0c001` and `811d5a2b` return an empty list; `a426b731` is #215's `merge_commit_sha`). But a freshly pushed commit may transiently return `[]`, and an API error is indistinguishable from "no PR" (both print `pr=none`). Specify retry with back-off, treat API errors as exit 2 (cannot read), and add a direct `pulls/<N>` lookup using the `(#N)` subject only as a hint, verified by `merge_commit_sha == C`.
- **R1-m6. Test-only flags in a security tool (§6.3, §11.2).** `--pr-map` and `--manifest-file` let a caller choose the PR mapping and manifest. Require them to be rejected unless `--ruleset-check skip`, and add a test that the workflow passes none.
- **R1-m7. Workflow skeleton (§10.2).** `steps: ...` is elided. The detector refuses shallow clones, so the checkout needs `fetch-depth: 0` (compare `test_admission_controls_check_out_full_history_for_the_pin_check`, `test_ci_platform_policy.py:318-328`). A `workflow_dispatch` on a non-`main` ref makes `--head HEAD` a feature branch: the walk then passes trivially. Require `<head>` to equal `origin/main`'s tip or to be on its first-parent chain.
- **R1-m8. §4.3 / U-4.** The three PowerShell commands read metadata and hash only. U-4's purpose (06v §2.8) is "junction behaviour for the Computational-Log detector", "recorded from a dry run". Add a dry run that runs `handle_bound_read(<real vault>, "04-Methods/Computational-Log.md")` and the segmenter in a process and prints only length, SHA-256, `st_nlink`, row counts and blocker count. That is what would reveal `nlink != 1`, a redirected `Documents` folder, or an anchor failure. P-089 item 4 already allows U-4 to read the vault, so "Stephen authorizes" is not needed for reads. The vault detector also requires `line_ending == "LF"` of the whole live page (note 685), which a successor entry written by Obsidian with CRLF would trip even though no legacy byte changed. Check legacy rows by hash instead.
- **R1-m9. M-6 exporter (§5).** The note says the `ars legacy` CLI helper "if selected under Owner Point A" (note 59). A does not concern a CLI. D-1 names the store `C:/Users/steph/TDL-ARS-G7-Control` (06v:563). The note's `C:\Users\steph\.ars\stores\w9-production\` (note 311) is invented. The census file `docs/plans/agentic-research-system/contracts/runtime-binding-census.yaml` (note 78) does not exist; the census lives in the 06h manifest and its smoke test.
- **R1-m10. Option A1's "3-line change" is incomplete (§5.3, §16 A).** Widening `_closed` at `evidence.py:125` is not enough. `require_registered` then compares `wanted` (three keys, `:128`) with `dict(entry)` (four keys, `:129`) and never matches, so LR-015 refuses every observation. The membership test must compare on the three identity keys only.
- **R1-m11. `§7` structural bytes.** Ordered-subsequence preservation of unit hashes is the W9 insertion-only rule for bullets and paragraphs, but it accepts inserted **tables** and ignores structural bytes (headings inside a section, rule lines, the footer). W9 says "pure insertion of successor bullets or paragraphs". State the accepted exceptions explicitly or add a unit kind filter.
- **R1-m12. §14 claims list.** It omits the claims most likely to be wrong: Rule 1's matching and exclusions, the record keying, the allowance kinds, the PR mapping, and the control-run mechanics. Claim 9 (junction refusal by `handle_bound_read`) and claim 12's CODEOWNERS premise are false (R1-M2, R1-M7).
- **R1-m13. Stray artefacts.** The unedited "Wait:" at note 691; the header's "every `path:line` citation … was read directly" (note 12), contradicted by §2 of this review; `06v:629` cited (note 1029) for a stop rule that is not in 06v §8 (the plan has no "detector control fails to fire" stop rule; it is the note's own addition).
- **R1-m14. T7b mechanics (§11.2).** "Synthesises commits via `git hash-object -w` + `git mktree` + `git commit-tree` that replay the exact tree deltas" is unspecified for nested directories and unaffordable in a time budget that was never measured. Use a throwaway index (`GIT_INDEX_FILE`) with `read-tree` and `update-index --index-info`, or drop T7b in favour of T7a plus a synthetic repo test.

### Info

- **R1-i1. Rule 2's `results/ars/` exemption is hard-coded** (note 504). W9-D14 says "register `results/ars/` as the `successor_results_root` so the detector exempts exactly that prefix". Hard-coding is simpler and safe; record it as a deliberate reading.
- **R1-i2. Mode-only changes.** A registered file with the same blob and a different mode appears in `diff-tree` but cannot satisfy the record schema (`old_blob != new_blob`), so it can never be authorized. Fine (closed), but say so.
- **R1-i3. Observed 2026-11-21, owner `gh` login, GET only.** `gh api repos/ZK-Theory/TDL/rulesets/20822054`: HTTP 200, `enforcement: active`, bypass actor `{actor_id: 5, actor_type: RepositoryRole, bypass_mode: pull_request}`, rules `pull_request`, `required_status_checks`, `merge_queue`, `non_fast_forward`, `required_approving_review_count: 0`, `require_code_owner_review: true`. `gh api "…/rulesets/rule-suites?ref=refs/heads/main&time_period=month&per_page=100"`: 57 entries, 33 `bypass` and 24 `pass`, newest `after_sha` `dbd54fe3` (pushed by `stephendor`, `result: bypass`). Merges through the queue are routinely `bypass` in this repository, so the §4.1 report will list many entries a month and D-8's "known limit" is wider than it reads. These fill the two "owner `gh`" U-3 rows (the rows for `GITHUB_TOKEN` stay open).
- **R1-i4.** `.gitattributes` sets `* text=auto eol=lf` (line 14), so a Windows runner checkout gives LF; the CRLF risk to the `CONVENTIONS.md` check does not arise in CI.
- **R1-i5.** `merge_commit_sha` is the squash commit for queue merges and `allow_merge_commit: true` is set in the repository, so true merge commits are possible (by admin) and §6.3's two-parent handling is needed. The note handles it.
- **R1-i6.** The empty-state handling is sound: `legacy-write-records.json` absent before L-1 is a failure only if a guarded write exists.

## 2. Citation audit (item 1)

Method: every `path:line` in the note was resolved and the first line compared with the claim; the 06v/register/code sets were scripted (`cites.py`, `cites2.py`, scratchpad). Where the text at the line supports the claim the citation is "ok". Counts below are for distinct citations checked.

**Wrong or approximate: 06v (`06v-w9-implementation-plan.md`)**

| Note cites | Says | Actual |
|---|---|---|
| `06v:123` (U-3) | row U-3 | `:159` |
| `06v:124` (U-4) | row U-4 | `:160` |
| `06v:160-164` (O-9 to O-13) | rows | `:189-193` |
| `06v:228` (W9-T7) | row | `:230` |
| `06v:240` (W9-T19) | row | `:242` |
| `06v:565` (D-4) | row | `:566` (565 is D-3) |
| `06v:570` (D-7) | row | `:569` (570 is D-9) |
| `06v:89-90` | squash merges | `:90-91` |
| `06v:623-633` | stop rules | `:610-620` |
| `06v:629` | "detector control fails" stop rule | not in 06v; 629 is the acceptance checkbox |
| ok | `06v:470-499`, `:477-488`, `:567`, `:571`, `:602`, `:212` | |

**Wrong or approximate: register (`03-decisions-and-open-questions.md`)**

| Note cites | Says | Actual |
|---|---|---|
| `:6057-6156` | P-089 | P-089 is `:6071-~6160` |
| `:6080-6114`, `:6081-6083` | decision items | the decision (items 1 to 6) starts at `:6090-6091`; item 3 at `:6104` |
| `:6085-6091` | "Not authorized" | `:6127-6140` |
| `:6094-6095` | U-3/U-4 recorded before code | item 3, `:6104-6115` |
| `:6103-6104` | merging not live | `:6104-6115` (item 3 last bullet) |
| `:6105-6106` | boundary | `:6141-6143` |
| `:6064-6066,6138-6140` | protected identities | P-089 evidence block, not those lines |
| `:5913-5916` | P-087 item 7 (5-minute budget) | item 7 is `:5919-5923` |
| `:3996` | P-064 item 8 | P-064 item 8 is `:4232` |

**Wrong or approximate: code and workflows**

| Note cites | Actual |
|---|---|
| `evidence.py:86-99` (`read_evidence`) | `:92-105` |
| `evidence.py:224-252` (`_change_entries`) | `:221-252` |
| `evidence.py:322,354` (blocker rows forbidden) | lines do not say that (R1-M2) |
| `preparers.py:114`, `:216` | `:686-690`, `:1200-1216` |
| `accepted_w9.py:67` (segmenter pin) | `evidence.py:52-54` |
| `reader.py:41`, `:109-116`, `:179-197`, `:182` | helpers/behaviour do not exist (R1-M2) |
| `replay/reducers.py:66` | registration mapping is `:70` and `:571` |
| `ci.yml:17`, `merge-admission.yml:17`, `merge-admission-sweep.yml:14-16`, `ars-artefact-currency.yml:14`, `ars-artefact-currency-watchdog.yml:22`, `research-system-suite.yml:28` (permissions) | permissions blocks are at `ars-artefact-currency-watchdog.yml:14-16` (`actions: read`, `contents: read`), `ars-artefact-currency.yml:12-13`, `merge-admission-sweep.yml:58-59` (`contents: read` only), `merge-admission.yml:52-55` (`contents`, `pull-requests`, `checks`), `research-system-suite.yml:30-31`. `ci.yml`'s watchdog job also has `actions: read` (`:239-241`). The note says the *sweep* has `pull-requests`/`checks: read`; it is `merge-admission.yml`. |
| `ci.yml:249-252` | `:263,276` |
| `check_workflow_liveness.py:61-93` `evaluate_workflow_liveness`, `:80-83` | function is `inactive_tracked_workflows` (`:78-92`); the state test is `:90-91` |
| `check_bypass_merges.py:98-100/101-110` | exact match at `:109`, fallback in the same expression at `:110` |
| `check_merge_admission.py:703-709` | docstring of `evaluate_merge_group_size` (`:700-737`), which enforces `total <= max_entries`, not `total_commits <= 1` |
| `wp9-4-design-note.md:1487-1495` | that range is the owner-points table; the carry sentence is at `:703` and `:1419` |
| `01-current-system-evidence.md:283` | unrelated bullet |
| ok (verified) | `acceptance.py:121-137,135,147-152`, `reader.py:140-206,240-248,43-49`, `cli.py:1648-1659`, `export_recheck.py:32-89`, `evidence.py:59-64,114-131,125,133-154,190-252,231-238,277-362`, `segmentation.py:429-488`, `w9_segmentation.py:388-458,461-518`, `test_ci_platform_policy.py:175-229,286-303,341-375`, `check_bypass_merges.py:20-21,93-111,152-180`, `admin-bypass-guard.sh:18,96-106`, `merge-admission.yml:127-130`, `ars-artefact-currency-watchdog.yml:91-112,95-97` |

About 55 of roughly 110 distinct citations in the sets checked are wrong or approximate. The pattern (06v table rows offset by about 30, register entries offset by 14 to 40) suggests citations were taken from another revision or by memory.

## 3. Owner points A to G: disposition

| Point | Disposition | Why |
|---|---|---|
| A | **Reframe**, agree in direction | A1 (carry `role`) is right. It must also carry `source_identity_kind` (R1-M4) and `conventions_lock` must be handled (R1-M5). The reader change is not "3 lines" (R1-m10). A2 (a separate list) has no enforcement. Both fields are already on the registration record, so projecting them is faithful. |
| B | **Reframe** | A committed JSON file is right (offline-testable, in the evidence area). Records must be evaluated **at `C`**, not `<head>` (R1-B1), the schema must carry provenance that can be checked beyond a self-asserted `author` (R1-M10), and allowance kinds miss Working-Note appends (R1-M5). B2 (PR bodies) is correctly dismissed. The new row in the paths addendum edits an accepted dated document, so it needs Stephen's dated addendum. |
| C | **Disagree with the rationale; keep C1 in principle** | C1's premise ("G7-A §11 already closes the pre-L-1 period") is false for #388, #401, #433 (R1-M12). C1 needs a committed append-only baseline record, a disposition for every first-parent guarded write since `4b143c92`, and time-indexed evidence (R1-B1). C2's list needs correcting (R1-M3). |
| D | **Reframe** | Diagnosis verified. Add D3 (blob-keyed, tree-state freshness, no commit field). D1's `base_commit` is unsound under the merge queue; D2 leaves a red window and an unenforced gap. Name what changes in WP9.3: `evidence.py:_change_entries`, `acceptance.py:check_change_list`, a format version, tests, and a dated WP9.3 amendment with independent review (R1-M6). |
| E | **Reframe** | Place the freshness gate at LR-003/LR-015 (batch start), not only LR-016/LR-020; define the reset or drop rule (b); state the weekly PR plus `advance-binding` cost; call the cadence self-attested; do not gate on "file present" (R1-M8). E2 (CLI only) does not enforce "blocks the next batch"; if chosen, say it is a checklist convention. |
| F | **Disagree with F2 as recommended** | F2 satisfies a string-presence test and leaves the new tests, including the inactivity tripwire, in no PR lane. F1 follows the `test_w9_segmentation.py` precedent but needs Stephen's own bypass for `ci.yml`; the guard forbids an agent bypass. The CODEOWNERS facts are wrong (R1-M7). |
| G | **Agree in kind, reframe** | A budget with an over-budget-is-Partial rule is right (P-087 item 7). 120 s is unmeasured (the pack is 335 MiB, 28 packs, 58,133 objects: a clone copies it on every module-scoped fixture). Either adopt P-087's 5 minutes, or measure before fixing 120 s, and state that slow-marked tests count toward the budget. |

**Missing owner points** the note should add: **H**, how tracker Working Notes are handled (R1-M5); **I**, whether the detector's own surface and the evidence files are code-owned or covered by Rule 0 (R1-B1, R1-M10); **J**, the source of legacy/successor classification for the vault and `CONVENTIONS.md` detectors (R1-M9).

## 4. Coverage of the handover's 17 items

| # | Item | Result |
|---|---|---|
| 1 | Scope, protected identities | Settled. Verified the census (275 rows, `82eab93a…1d58`), 06h manifest blob `1066404a` and segmenter blob `43e1454d` against P-089's evidence block. §2.3's reader list is incomplete (R1-M2); E1/D1 change accepted WP9.3 gate behaviour, which is beyond "a reader". |
| 2 | Ruleset read | Settled in shape; under-pinned and example wrong (R1-m2). |
| 3 | U-3 | Probe not runnable as specified; third call and permissions missing (R1-M11). D-8 text exact against 06v, mis-cited (R1-m1). The note could not run the two GETs; they are recorded in R1-i3. |
| 4 | First-parent detector | Mechanics verified; evidence-timing defect (R1-B1); PR mapping sound, failure modes thin (R1-m5); baseline unsettled (R1-M12). |
| 5 | M-6 export | Phantom APIs (R1-M2). Direction right. |
| 6 | O-32 detector half | Contradiction diagnosed correctly; options incomplete (R1-M6). Which paths are shared surfaces: only via role (A); examples invented (R1-M3). |
| 7 | `CONVENTIONS.md` check | Mechanics and numbers verified; classification hard-coded (R1-M9); `conventions_lock` unhandled in Rule 1 (R1-M5). |
| 8 | Vault detector and D-5 | Rule set sound given the segmenter; production-mode API and classification source wrong (R1-M2, R1-M9); fabricated census (R1-M1); enforcement placement (R1-M8). |
| 9 | U-4 | Left open as the handover allows, but the dry run does not exercise the reader (R1-m8). |
| 10 | Detector-controls file | Settled; control not bound to the tool, SHAs nondeterministic (R1-m4). |
| 11 | Merging is not going live | Mechanism right (verified below); test is not run anywhere under F2 and breaks at L-1 (R1-M7). |
| 12 | Where controls run | Clone verified; immutability proof weak (R1-m3). |
| 13 | Tests and budget | Inventory covers W9-T7, W9-T19, M-6, O-13. Estimates are unmeasured. |
| 14 | Research assurance | HR/MC split reasonable; omits self-attestation and detector self-edit (R1-M10). |
| 15 | Claims for review | Incomplete (R1-m12). |
| 16 | Stop rules | Preconditions correct; item 5 cites 06v:629 wrongly. |
| 17 | Owner points | Seven given, three missing. |

## 5. What was checked and found sound

- **Baseline.** `git cat-file`: `4b143c92:CONVENTIONS.md` is blob `4620c71607ca3a06c6df3b8e96a6bddffc783960`, 33,645 bytes, SHA-256 `d04fe97e…8589`. `reader.py:43-49` pins the same.
- **Unit counts.** Both `tools/w9_segmentation.py` and `research_system/legacy/segmentation.py` (agree byte for byte on both blobs) give 70 `conventions_unit` items in 10 sections, no blockers, LF, no BOM, 575 lines. The nine non-governance sections hold 3+2+5+4+24+13+6+3+8 = 68 units; "ARS Foundation Governance" holds 2. At `dbd54fe3` (90 units, 822 lines) every baseline unit in the nine sections is preserved in order. The section first-appearance order is preserved even though "Repo-Wide CI…" was inserted third. Ordered-subsequence preservation is exactly the insertion-only rule W9 §7.3 item 4 states for units; see R1-m11 for its edges.
- **First-parent claims.** `5df0c001` has one parent `a426b731` and the subject "Merge pull request #215 …". `a426b731` has two parents and touches no `results/`, `papers/`, `.apm/` or `contracts/` path. `gh api pulls/215`: `merge_commit_sha` is `a426b731`, merged 2026-08-05T03:44Z. `commits/5df0c001…/pulls` and `commits/811d5a2b…/pulls` return empty lists. `b132406e` has two parents `811d5a2b` and `3bfb279c`. In a scratch bare clone (`git clone --bare --local --no-hardlinks`, then deleted), single-argument `git diff-tree -r b132406e` printed nothing and `diff-tree -r --no-renames <P1> <C>` printed the real changes, as §6.3 says. `git rev-list --first-parent 4b143c92..origin/main` gives 320 commits and `4b143c92`, `5df0c001`, `811d5a2b`, `a426b731`, `b132406e` are all on `origin/main`'s first-parent chain.
- **PR mapping rule.** `merge_commit_sha == C` matches the squash commit for `dbd54fe3`, `e053462a` and `1b2cebf7`. The earliest-merged fallback in `tools/check_bypass_merges.py:106-110` is real and rightly not copied.
- **Ruleset facts and D-8 context.** Verified live (R1-i3). `check_bypass_merges.py:20-21` says rule suites need the owner's token (R1-M11 for what it does not say).
- **Merging is not going live (mechanism).** A `workflow_dispatch`-only workflow carries no `push`, `schedule`, `pull_request` or `merge_group` trigger. By reading `tools/check_workflow_liveness.py:78-92` (state only) it passes `--all-tracked` once the file is on the default branch; `ars-artefact-currency-watchdog.yml:98-112` runs the check against the base set on PRs. `test_no_job_runs_on_linux` and `test_bash_scripts_declare_bash` are satisfied by `windows-latest` plus `defaults.run.shell: bash`. The mechanism is sound; the test and wiring are not (R1-M7). Not run empirically: no workflow was run or committed.
- **Policy test facts.** `test_every_tools_and_contracts_test_runs_in_a_workflow` is a string-presence check (`:286-303`). `ADMISSION_CONTROL_MODULES` (`:175-229`) already includes `tests/tools/test_w9_segmentation.py`.
- **Scratch-clone controls.** A bare `--local --no-hardlinks` clone of the worktree copies the 335 MiB pack, contains `5df0c001`, supports `rev-list`/`diff-tree`/`show`/`cat-file`, and has no remote-tracking refs (tests must pass SHAs, as the note does).
- **O-32.** Diagnosis of the squash-SHA contradiction (R1-M6).
- **No D-4 trigger.** Nothing in the note's WP9.5 code scope touches the census, the 06h manifest, the schemas or `tools/w9_segmentation.py`. It does name changes to `evidence.py` and `acceptance.py` (not protected identities, not in `IMPORTER_MODULES`, but accepted WP9.3 gate code).
- **Check on `.gitattributes`.** LF is enforced repo-wide (R1-i4).

## 6. Revision plan

**Immediate corrections (author, no owner decision needed):**
1. Fix R1-B1: time-indexed evidence (manifest at `P1`, records at `C`), Rule 0 monotonicity, a committed append-only baseline record, a detector pinned to the baseline.
2. Re-derive §4.3, §5.3, §8.2 and §2.3 against actual code (R1-M2). Remove every symbol listed there. Decide whether the new readers live in `tools/` or `research_system/legacy/`.
3. Replace the fabricated census (R1-M1) and the genealogy/fixture facts (R1-M3). Delete the "Wait:" paragraph.
4. Fix R1-M4 and R1-M5 (manifest fields; Rule 1 exclusions; §6.6 scope).
5. Rewrite the U-3 probe (R1-M11) and add the `commits/<sha>/pulls` call.
6. Correct all citations (§2 above) or drop line numbers where a symbol name suffices.
7. Fix R1-m1 to R1-m14.

**Owner decisions to put to Stephen after revision 2:** A (widened), B (records at `C`), C (baseline record and dispositions), D (add D3), E (gate placement), F (F1 versus the tripwire), G, plus H, I, J.

**Later-work dependencies:** L-0b classified-list format (R1-M9); a dated WP9.3 amendment if D1/D3 or E1 are chosen; a dated amendment to the paths addendum for the new evidence rows.

**Residual risks the note should state:** the detector is post-merge and a human merge remains the only preventive control (R1-M10); rule-suites visibility is limited to 30 days (R1-m2); under D-8 bypass use between batches is unseen, and 33 of 57 main updates last month were bypass results (R1-i3).

## 7. Commands run

All read-only. `git status --short` in the worktree was empty after each stage and at the end. No file under the repository was written. No vault file was read.

- `git` (worktree `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note`): `rev-parse`, `cat-file -t/-s`, `log -1 --format`, `show <rev>:<path>` (redirected into the scratchpad), `ls-tree`, `ls-files`, `rev-list --first-parent --reverse 4b143c92..origin/main`, `rev-list --parents`, `diff-tree -r --no-renames --name-status/--name-only/--stat`, `count-objects -vH`, `config --get-all core.autocrlf`.
- `gh api` GET only: `repos/ZK-Theory/TDL` (visibility, merge methods), `…/rulesets/20822054`, `…/rulesets/rule-suites?ref=refs/heads/main&time_period=month&per_page=100`, `…/pulls/{127,168,169,215,219,277,368}`, `…/commits/{5df0c001…,811d5a2b…,b132406e…,dbd54fe3…,e053462a…,1b2cebf7}/pulls`.
- Scratch clone: `git clone --bare --local --no-hardlinks <worktree> <scratchpad>\scratch-bare.git`, then `for-each-ref`, `cat-file`, `rev-list`, `diff-tree` against it, then `rm -rf`. Never pushed from.
- `python -I` scripts in the scratchpad: `seg_check.py` and `seg_check2.py` (both segmenters over the baseline and head `CONVENTIONS.md` blobs, written by `git show`), `cites.py` and `cites2.py` (citation resolution). Data copies `conv_base.md` and `conv_head.md` are in the scratchpad.
- File reads: the note, the handover, P-089, P-064, P-087, 06v (§2.4, §2.8, §3, §4, §5 WP9.5, §6, §7, §8), W9 §3.1, §4, §5.4, §5.5, §7.3, the segmentation contract (§3, §4, §6, §8), `research_system/legacy/{evidence,acceptance,reader,accepted_w9,export_recheck,preparers(parts),segmentation(parts)}.py`, `research_system/store/anchor.py:1934-1950`, `research_system/canonical.py`, `research_system/cli.py:1640-1720`, the W9 registration schema, `tools/{w9_segmentation,check_bypass_merges,check_merge_admission(parts),check_workflow_liveness,affected_research_tests(head)}.py`, all of `.github/workflows/*.yml` (grep, plus the watchdog, ci.yml watchdog job, merge-admission and suite), `.github/CODEOWNERS`, `.gitattributes`, `.claude/hooks/admin-bypass-guard.sh`, `tests/tools/test_ci_platform_policy.py`, `CONVENTIONS.md:700-735`, the W0 addendum and its re-review (cited lines).
