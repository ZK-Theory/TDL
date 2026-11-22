# WP9.5 Design Note — W9 Detectors (W9-D5)

| Field | Value |
|---|---|
| Date | 2026-11-22 |
| Status | **Revision 6, for independent adversarial review. Nothing in it is implemented.** |
| Package | `06v` WP9.5 — "Detectors (W9-D5)" (`docs/plans/agentic-research-system/implementation/06v-w9-implementation-plan.md:470-503`) |
| Authority | Decision register entry `P-089` (`docs/plans/agentic-research-system/03-decisions-and-open-questions.md:6071-6146`) |
| Base | `origin/main` at `dbd54fe382e7b2849d3f2038393cbdb4d709477b` (`[PIPELINE] P06: WP9.4-2 follow-up: the independent review's Minor findings (P-088 item 5) (#446)`) |
| Worktree / Branch | `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note` on branch `docs/w9-wp9-5-design-note` |
| Prior reviews | Revision 1 (`65363e27`): `wp9-5-note-r1-review-2026-11-21.md` (`edb9acc6`; `REWORK REQUIRED`: 1 Blocking, 12 Major, 14 Minor, 6 Info)<br>Revision 2 (`0c9a90ed`): `wp9-5-note-r2-review-2026-11-21.md` (`3cf35bec`; `REWORK REQUIRED`: 0 Blocking, 5 Major, 16 Minor, 6 Info)<br>Revision 3 (`092db1f1`): `wp9-5-note-r3-review-2026-11-21.md` (`1bd4ecff`; `REWORK REQUIRED`: 0 Blocking, 3 Major, 13 Minor, 4 Info)<br>Revision 4 (`48b5e935`): `wp9-5-note-r4-review-2026-11-22.md` (`0e6d23e4`; `REWORK REQUIRED`: 0 Blocking, 2 Major, 11 Minor, 8 Info)<br>Revision 5 (`83b4ae6f`): `wp9-5-note-r5-review-2026-11-22.md` (`d6938710`; `REWORK REQUIRED`: 0 Blocking, 3 Major, 11 Minor, 6 Info) |
| Not authorized | WP9.5 code, WP9.6, WP9.7, live operations L-0 to L-5 (including L-0b and L-1), creating or binding the real control store, registering or observing any real file, or any write to a legacy file, `main`, or the vault (`03-decisions-and-open-questions.md:6127-6135`) |
| Verification scope | **Checked here (`dbd54fe38` / worktree `HEAD`, §21.1):** cited repository lines; 22-commit walk; `CONVENTIONS.md` counts (70/90 units); ruleset `20822054` pins; bare-clone timings; 15-module stdlib-only closure (0 third-party imports); parent + child `[sys.executable, "-S", "-P", ...]` isolation (`PYTHONPATH` + `PYTHONSAFEPATH=1`, script and `-m` forms, out-of-closure `ModuleNotFoundError`); stdin pipe wrapper (`git show <ref> \| python -S -P -`); 19 pin-heredoc cases (Windows trailing-dot/space/device refusal + `hash-object --no-filters` + I3); and `1x` walk stand-ins (`14.05s`/`34.46s`/`62.84s`; `24.04s` measured `2x` at 60 commits; `68.92s`/`125.68s` **extrapolated (`2 × 1x`)**). Independent reviews (`§21.1` intro) reproduced R2–R5 checks including R5 stand-ins (`11.79s`/`34.85s`/`61.58s` + `~11.3s` live `gh api`), `404` citations, and live ruleset `20822054`.<br>**NOT verified here (§15.1, §21.2):** CI `GITHUB_TOKEN` U-3 probe (`UNVERIFIED-1`), live vault U-4 dry run (`UNVERIFIED-2`), single scratch-store timing & weekly D-5 run (`UNVERIFIED-3`), I3 variable permissions (`UNVERIFIED-4`), and hosted `windows-latest` `1x` walk time (`UNVERIFIED-5`). |

---

## 1. What this note settles

WP9.5 builds the W9 detectors (`06v:470-503`; `W9` §4.4, `09-migration-compatibility-and-pilot.md:191-202`), specifying inputs, decision rules, outputs, closed `ERROR:` failures, execution lanes, negative controls, and tests. Each rule is specified once in its owning section below:

| Handover §3 item | Owning sections | Summary |
|---|---|---|
| 1. Scope & protected identities | §2, §3 | No D-4 trigger (§2.2); separates `tools/` readers from Owner Point changes under `research_system/legacy/` and WP9.4 test fixtures (§2.3). |
| 2. Ruleset read (`main_ruleset`) | §4.1 | Pins ruleset `20822054` and `rule-suites` history (`MAX_DAYS = 30`), outputting canonical `w9-main-ruleset-read/1` SHA-256. |
| 3. U-3 probe & D-8 fallback | §4.2, §15.1 | Pre-code draft-PR `pull_request` probe of `GITHUB_TOKEN` and pinned keys; `rule-suites` failure triggers hash-bound D-8 fallback. |
| 4. First-parent detector | §6, §10.2, §16.1–§16.2 | Content-pinned `python -S -P` execution over 22 stdlib-only blobs (`detector_closure_blobs`); time-indexed Rules 0–3 (**pin, no lockstep — Rule 0.3 & PR pin-advance gate deleted per Stephen's 2026-11-22 decision**); `1x` post-merge walk, exit-`2` uncaught errors/incompatibility, manual pin-advance comparison evidence, and pre-code `600s` walk stop rule. |
| 5. Registration manifest (M-6) | §5, §16.3 | `tools/export_w9_registration_manifest.py` exports `w9-registration-manifest/2` (Option A1) from `_legacy_projection` / `_legacy_current_binding`; `--check` verifies store equality at `git_head` (unpinned residual `HR-7`). |
| 6. Shared-surface rule (`O-32`, Rule 3) | §6.2.2, §6.5, §16.5 | In-commit §4.3 record + `w9-shared-surface-changes/2` (Option D3 blob-keyed freshness); Rule 3 acknowledgements also require `independent_review`, non-empty `affected_registrations` / `"none derived"`, and `pr_number: null` when unmapped. |
| 7. `CONVENTIONS.md` check | §7, §16.10–§16.11 | Segments baseline `4620c716` vs candidate via `conventions_unit`; 68-unit provisional partition or pinned L-0b classification (`ACCEPTED_CONVENTIONS_CLASSIFICATION`); bullet/paragraph insertions only; PR-lane choice (Owner Point K). |
| 8. Vault Computational-Log & D-5 | §8, §16.6, §16.10 | `tools/check_legacy_log_baseline.py` verifies live entries against accepted `w9-cl-export/1` + 1-based `w9-cl-classified-list/1` (`void == False` required); D-5 cadence gated at `LR-003`/`LR-015`/`LR-016`/`LR-020`. |
| 9. U-4 vault path & dry run | §4.3, §15.1 | Records `2026-11-21T21:06:44Z` metadata (`833,453` B) and pre-code `u4_dry_run.py` (`root_checks` + `handle_bound_read` + `segment`). |
| 10. Detector controls | §9 | `tools/run_w9_detector_controls.py` binds tool blobs + `closure_blobs` map under isolated `CONTROL_GIT_ENV` (`--code-root` / `--repo-root` split). |
| 11. Merging is not going live | §10, §16.1, §16.7 | `workflow_dispatch`-only commit until L-1; confined `python -S -P` assembly + post-write hash verification; `L1_LIVE = False` tripwire (`yaml.BaseLoader`) in `admission-controls` + CODEOWNERS; separate throwaway rehearsal + green L-1 `workflow_dispatch`. |
| 12. Scratch clones & isolation | §11 | Bare local scratch clones (`~1.57–1.99s`); `W9-T7` in `tests/tools/test_w9_detectors.py` (departure from `06v:230`); `REPO_ROOT` checkout-local snapshot (`--git-common-dir` `config`/`hooks/` in CI only). |
| 13. Tests & budget | §12, §16.7–§16.8 | Unit PR checks (`W9-T19`, `W9-T7`, stdlib/wrapper/CODEOWNERS/pin/comparison tests), integration `M-6`/`O-13` (`affected_research_tests.py` + nightly), `14.05s–62.84s` measured `1x` walk stand-ins, unconditional scratch-store profile (`§15.1`), G1 `300s` budget. |
| 14. Assurance & claims | §13, §14 | Machine-checkable claims (`MC-1`–`MC-10`), human-review limits (`HR-1`–`HR-7`), and 16 claims for adversarial review. |
| 15. Stop rules & Owner points | §15, §16 | Pre-code gates (`UNVERIFIED-1`–`5`), pre-code `600s` `1x` walk stop rule, and 11 Owner Points (pin design **decided by Stephen, 2026-11-22**; open choices in **I, C, A, B, D, E, F, G, H, J, K**). |
| 16. Change logs & verification | §17–§21 | Revision history (§17), compact R1–R4 index (§18), R4->R5 log (§19), R5->R6 log (§20), and reproducible Verification appendix (§21). |

---

## 2. Scope, package boundary, and protected identities

### 2.1 Deliverables in WP9.5

Under `06v` §5 (`06v-w9-implementation-plan.md:470-503`) and `P-089` (`03-decisions-and-open-questions.md:6091-6118,6141-6143`), WP9.5 delivers:

1. **`tools/export_w9_registration_manifest.py` (**new**, M-6, `06v:470-473`):** Reads `_legacy_projection` (`research_system/cli.py:1648-1659`) and `_legacy_current_binding` (`:1662-1684`) to export `.research-system/evidence/w9/registration-manifest.json` (`w9-registration-manifest/2` under A1, updating `research_system/legacy/evidence.py:37,40,114-131`); `--check` verifies equality with store `legacy_path_registration` (`research_system/legacy/replay/reducers.py:70,571`) at `binding.binding["git_head"]` (`research_system/cli.py:1714`; §5).
2. **`tools/check_legacy_writes.py` & `.github/workflows/legacy-write-detector.yml` (**new**, `O-9`, `O-10`, `O-32`, `06v:189-190,212,474-490`):** First-parent detector walking `<b0>..<head>` from `baselines[0]["baseline_commit"]` once (`1x`) per post-merge run with `baselines[-1]` (Rules 0–3, `acknowledged`, ruleset `20822054` / U-3/D-8; no Rule 0.3); every WP9.5 tool wraps `main()` to exit `2` on any uncaught exception and decodes `git`/`gh` with `encoding="utf-8"` (§6). Windows workflow committed `on: workflow_dispatch:` only, assembling `$RUNNER_TEMP/w9-detector` from `detector_closure_blobs` and running stdlib-only `python -S -P` (`PYTHONPATH="$DETECTOR_DIR"`, `PYTHONSAFEPATH=1` — no `uv sync`, §10).
3. **`tools/check_conventions_legacy_locks.py` (**new**, `O-12`, `06v:192,491-492`):** Verifies `CONVENTIONS.md` preserves every `conventions_unit` from `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (blob `4620c71607ca3a06c6df3b8e96a6bddffc783960`, 33,645 bytes, SHA-256 `d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589`, `CONVENTIONS_LOCK` `research_system/legacy/reader.py:43-49`) via `w9-segmentation/1.0.0` (`research_system/legacy/segmentation.py:429-488`, `tools/w9_segmentation.py:461-518`) and `ACCEPTED_CONVENTIONS_CLASSIFICATION` (`research_system/legacy/accepted_w9.py`, **new**; §7).
4. **`tools/check_legacy_log_baseline.py` (**new**, `O-11`, `D-5`, `D-7`, `06v:191,493-496,567,569`):** Refuses symlink/junction/in-repo `--vault-root`, reads `04-Methods/Computational-Log.md` via `handle_bound_read` (`research_system/legacy/reader.py:140-206`), requires `recheck_cl_export` `void == False`, and checks legacy rows against `ACCEPTED_CL_EXPORT` (`accepted_w9.py:86-88`; §8).
5. **`tools/run_w9_detector_controls.py` & `tools/run_w9_pinned_detectors.py` (**new**, `O-13`, `06v:193,497-502,603-604`):** Emits `.research-system/evidence/w9/detector-controls.json` (`w9-detector-controls/1`, `evidence.py:38,41,59-64,133-154`, `--code-root`/`--repo-root` split, §9). The pinned wrapper is one **self-contained stdlib-only file** (zero `tools.*`/`research_system.*` imports) piped by Stephen from `origin/main` via `git show ... | python -S -P -` (§6.2.3).
6. **Tests (`W9-T7`, `W9-T19`, `06v:230,242,503`):** `tests/tools/test_w9_detectors.py` (**new**, `unit` in `admission-controls`: `W9-T19`, `W9-T7` departure from `06v:230`, `L1_LIVE` tripwire, stdlib/wrapper/CODEOWNERS/pin/comparison/exit-`2`/UTF-8 controls) and `tests/research_system/integration/test_w9_wp9_5_detectors.py` (**new**, `slow`, `integration`: scratch-store `M-6` and `O-13`) (§12.1).

### 2.2 What WP9.5 does NOT touch and why no D-4 is expected

Per `P-089` item 1 (`03-decisions-and-open-questions.md:6091-6099`), WP9.5 adds **no W9 command**. The 12 W9 command types in `LEGACY_COMMAND_TYPES` (`research_system/legacy/commands.py:16-31`) and the route sets `LEGACY_ROUTED_ROWS` (`49` routed rows, `research_system/legacy/routes.py:446-453`) and `LEGACY_DEFERRED_ROWS` (`12` deferred rows, `research_system/legacy/routes.py:454-458`) from WP9.4-2 (`P-088`) are unchanged:

| Protected identity / surface | Current pinned value on `main` (`dbd54fe38`) | WP9.5 impact |
|---|---|---|
| Runtime-binding census (275 rows, enforced by `tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml` and `test_wp6_1_06h_append_path_closure.py`) | 275 rows; SHA-256 `82eab93a1b2ac81dd564581237f35e3dff19fee9e824ffff317d0f202b451d58` (`03-decisions-and-open-questions.md:6022-6023,6086`) | **Unchanged.** WP9.5 adds no contract or command row. |
| 06h append-path manifest (`tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml`) | Blob `1066404a` (`03-decisions-and-open-questions.md:6022,6087`) | **Unchanged.** WP9.5 detectors are read-only observers and never append to any store ledger. |
| 06h append-path closure smoke test (`tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py`) | Blob `3b1eec6e` (`03-decisions-and-open-questions.md:6024-6025,6087`) | **Unchanged.** |
| Schema registry & authority (`research_system/schema_registry.py`, `research_system/authority.py`) | Blobs `e32cb408` and `9b56b322` (`03-decisions-and-open-questions.md:6024`) | **Unchanged.** |
| Core schemas (`core/commands`, `core/events`), T2 expectations & seal, and the 19 `.research-system/schemas/contracts/w9/*.schema.json` files | Pinned at WP9.1 (`P-073`) | **Unchanged.** |
| Pre-code reference segmenter (`tools/w9_segmentation.py`) | Blob `43e1454de09b61e274954c42b21d6ae533857a24` (`CL_EXPORT_PRODUCER`, `research_system/legacy/evidence.py:52-54`; `03-decisions-and-open-questions.md:6088`) | **Unchanged.** Imported read-only; never modified. |
| Importer modules (`IMPORTER_MODULES`, `research_system/legacy/reader.py:42`) | `("research_system/legacy/reader.py", "research_system/legacy/segmentation.py")` | **Unchanged.** Neither module is modified by WP9.5, so `LegacyReader.importer_identity` (`reader.py:250-262`) `tool_sha256` does not move. |

**Consequence:** Because no runtime-binding row, command type, event type, append site, or schema changes, **no D-4 re-acceptance (`06v:566`) is triggered by WP9.5**. If any implementation choice during WP9.5 construction would alter any row of the table above, work stops immediately for an owner decision (§15).

### 2.3 Boundary between `tools/` and `research_system/legacy/`, and `.github/CODEOWNERS`

1. **`tools/` vs `research_system/legacy/` boundary (`P-089`, `03-decisions-and-open-questions.md:6110-6112,6141-6143`):**
   Per `P-089:6141-6143` and `:6110-6112`, nothing under `research_system/legacy/` changes except what this note names for an owner decision:
   - **All detector-only readers/helpers live in `tools/` (`tools/_w9_detector_evidence.py`, **new**):**
     - `load_registration_manifest_at(repo_root, commit)`, `load_shared_surface_changes_at(repo_root, commit)`, `load_legacy_write_records_at(repo_root, commit)`, and `load_walk_baseline_at(repo_root, commit)` read `<commit>:.research-system/evidence/w9/*.json` via `git --no-replace-objects show` (distinct from `evidence.require_registered` at `research_system/legacy/evidence.py:114-131` and `evidence.require_change_list` at `:190-218`).
     - `compute_detector_import_closure(repo_root, entry_scripts)` AST-walks the **6** runtime `tools/` scripts (`check_legacy_writes.py`, `check_conventions_legacy_locks.py`, `check_legacy_log_baseline.py`, `run_w9_detector_controls.py`, `run_w9_pinned_detectors.py`, `_w9_detector_evidence.py`) transitively across `research_system` and `tools`, deriving **21** stdlib-only runtime modules (`6` new `tools/` + `15` existing) which plus `.github/workflows/legacy-write-detector.yml` form the **22**-entry `detector_closure_blobs` map (`tools/export_w9_registration_manifest.py`, `pyproject.toml`, and `uv.lock` are omitted, §6.2.3, §13.2 `HR-7`).
     - `read_real_vault_log(vault_root, repository_root)` (in `tools/check_legacy_log_baseline.py`) enforces `is_symlink()`/`is_junction()` and `resolve(strict=True)` outside `repository_root` before calling `handle_bound_read` (§4.3.2).
   - **Optional Owner Point edits under `research_system/legacy/` (and WP9.4 test fixtures) in §16:**
     - **A (`Option A1`):** Updates `evidence.py:40,114-131` to `"w9-registration-manifest/2"` (5 closed keys, membership on 3 identity keys) + fixture builders in `test_w9_evidence.py`, `w9_runtime_harness.py:451-466`, `test_w9_wp9_4_1_runtime.py:95-109`, and `test_w9_wp9_4_2_runtime.py:86-100` (dated WP9.3 amendment, review, `P-090`; no WP9.4 production code changed; `docs/plans/agentic-research-system/transition/w9/wp9-4-1-record.md:114,130` `13 passed`/`688.11s` re-record question in §16.3).
     - **D (`Option D3`):** Updates `evidence.py:42,221-252` (`"w9-shared-surface-changes/2"`) and `acceptance.py:121-136` (`check_change_list`) (dated WP9.3 amendment, review, `P-090`; §16.5).
     - **E (`Option E1`):** Adds `VAULT_DETECTOR_RUNS` / `require_vault_detector_cadence` in `evidence.py` and hooks `preparers.py:686-690,1215-1218` + `acceptance.py:147-152` (dated WP9.3 amendment, review; §16.6).
     - **J (`Option J1`):** Adds `ACCEPTED_CONVENTIONS_CLASSIFICATION: tuple[MappingProxyType[str, Any], ...] = ()` in leaf module `research_system/legacy/accepted_w9.py` (`:86-88`; §16.10).

2. **`.github/CODEOWNERS`, `GATE_FILES`, and `test_ci_platform_policy.py` boundary (`.github/CODEOWNERS:1-24`; `tests/tools/test_ci_platform_policy.py:341-375`; `CONVENTIONS.md:713-729`):**
   - `.github/CODEOWNERS` currently lists **8** `@stephendor` paths matching `GATE_FILES` (`test_ci_platform_policy.py:341-350`), enforced equal by `test_every_gate_file_exists_and_has_a_code_owner` (`:364-369`, asserting `.is_file()`) and `test_codeowners_names_no_file_outside_the_gate` (`:372-374`). Under `CONVENTIONS.md:713-729` (inside `## ARS Foundation Governance`, `614-783`), expanding CODEOWNERS under **Owner Point I1** to the WP9.5 workflow, 7 `tools/` files, `test_w9_detectors.py`, `accepted_w9.py` (`11` files adding `/tools/w9_segmentation.py` under Recommended `I1-include-seg`, or `10` exempting it under `I1-exempt-seg`), and `/.research-system/evidence/w9/` requires the edits in §16.1. (`test_ci_platform_policy.py` and `check_test_commit_literals.py` are not in `GATE_FILES`.)
   - `tests/tools/test_w9_detectors.py` runs in `.github/workflows/ci.yml:166-216` `admission-controls` (`ADMISSION_CONTROL_MODULES` `test_ci_platform_policy.py:175-229`; precedent `:210`/`:226`; §10.3, §16.7). `.github/workflows/ci.yml` is in `.github/CODEOWNERS:18` and `.claude/hooks/admin-bypass-guard.sh:13-18,67-68` forbids agent bypass merges, so **Stephen merges PRs touching `ci.yml`, `CODEOWNERS`, or I1 paths himself** (§16.1, §16.7).

---

## 3. Carried obligations

| Source | ID | Obligation | Where settled in this note |
|---|---|---|---|
| `06v:159` | `U-3` | Verify whether the CI token (`GITHUB_TOKEN`) can read ruleset `20822054` and `rulesets/rule-suites`, and apply D-8 if not. Recorded before any WP9.5 code (`P-089` item 3, `03-decisions-and-open-questions.md:6105-6107`). | §4.2, §15.1 |
| `06v:160` | `U-4` | Verify the operator machine's path to the vault (`C:\Users\steph\Documents\TDA-Research` vs `C:\Users\steph\TDL\vault` junction) and record a read-only dry run before any WP9.5 code (`P-089` item 3, `03-decisions-and-open-questions.md:6105-6107`). | §4.3, §15.1 |
| `06v:189` | `O-9` | Post-merge first-parent walk on `main` (`tools/check_legacy_writes.py`, `.github/workflows/legacy-write-detector.yml`): checks registered files, `results/` outside `results/ars/`, and `shared_enforcement_surface` contracts. | §6 |
| `06v:190` | `O-10` | Ruleset `20822054` and `rule-suites` history read before every batch and in the post-merge detector (subject to U-3 / D-8). | §4.1, §4.2, §6.6 |
| `06v:191` | `O-11` | Vault `Computational-Log.md` baseline detector (`tools/check_legacy_log_baseline.py`) against accepted export; runs before every batch and weekly on the operator machine. | §8 |
| `06v:192` | `O-12` | `CONVENTIONS.md` legacy-lock check (`tools/check_conventions_legacy_locks.py`): insertion-only check against commit `4b143c92`. | §7 |
| `06v:193` | `O-13` | Negative controls for all four detectors (`recorded_read` for `main_ruleset`; `watched_to_fail` for the other three) run on scratch clones or byte copies; output hashes committed to `.research-system/evidence/w9/detector-controls.json` at L-1 before first registration. | §9, §11 |
| `06v:212` | `O-32` | Detector half of shared-surface enforcement: fail when a merged change to a `shared_enforcement_surface` contract lacks an entry in `shared-surface-changes.json` or lacks a W9 §4.3 owner note. | §6.5, §16 (Owner Points A, D) |
| `06v:470-473,483-484` | `M-6` | Export `registration-manifest.json` from the control store per registration batch before that batch's first observation; test that the manifest equals the store's registered set at the bound head. | §5 |
| `06v:230` | `W9-T7` | Replay `5df0c001` and `811d5a2b` on a scratch clone with a fixture registry listing the files they touched; assert both are flagged (`06v:230,503` classify as `slow`, `integration`; moved to `unit` PR lane `tests/tools/test_w9_detectors.py` under Owner Point F as a recorded departure + addendum row). | §11.2, §12.1, §16.7 |
| `06v:242` | `W9-T19` | Computational-Log and `CONVENTIONS.md` checks pass on clean successor insertions and fail on legacy edits, anchor renames, duplicate anchors, and unparseable headings (`unit`). | §7.6, §8.5, §12.1 |
| `06v:567` | `D-5` | Vault detector runs before every batch and weekly on the operator machine; each run files an output hash in the evidence area; a missed run blocks the next batch. | §8.4, §16 (Owner Point E) |
| `06v:569` | `D-7` | L-0b export is taken as soon as Stephen authorizes it, with the segmentation contract reviewed and accepted together with it, followed by the classified legacy-entry list accepted by Stephen; WP9.5 designs and tests the vault detector against a fixture export until L-0b is accepted. | §8.3, §16 (Owner Point J) |
| `06v:571` | `D-8` | Fallback if U-3 shows the CI token cannot read `rule-suites` (`P-064` item 8, `03-decisions-and-open-questions.md:4232-4233`). | §4.2.3 |
| `03-decisions-and-open-questions.md:6113-6115` | `P-089` (3) | Merging WP9.5 must not start any detector on `main` or the vault; L-1 is a separate owner decision. | §10 |
| `wp9-4-design-note.md:703,1419` | WP9.4 carry | Any unobserved edit to a registered legacy file after registration is caught by WP9.5's post-merge first-parent walk (`O-9`), vault log baseline check (`O-11`), or `CONVENTIONS.md` lock check (`O-12`), together with WP9.3's blob-continuity preparers (`LR-015`, `LR-016`, `LR-020`) and WP9.7's use-time comparison. | §6, §7, §8 |

---

## 4. Interface findings (`path:line` at `dbd54fe38`), ruleset read, U-3, and U-4

### 4.1 The ruleset read (`main_ruleset`, control kind `recorded_read`)

- **Authority & purpose:** `W9` §4.4 (`09-migration-compatibility-and-pilot.md:195,201-202`), `06v:190,594,603`, `REQUIRED_DETECTOR_CONTROLS["main_ruleset"] == "recorded_read"` (`research_system/legacy/evidence.py:59-64`).
- **What it reads (`gh api` GETs; `.claude/hooks/admin-bypass-guard.sh:18,96-106`; §21.1 item 8):**
  1. **Ruleset config (`gh api repos/ZK-Theory/TDL/rulesets/20822054`; `01-current-system-evidence.md:409`):** Verifies the 16 invariants shown in the report below (`id: 20822054`, `name`, `target == "branch"`, `enforcement == "active"`, `conditions.ref_name.include == ["refs/heads/main"]`, `exclude == []`, single `bypass_actors` entry `actor_id: 5`, and all 4 rule objects: `pull_request` [`require_code_owner_review: True`, `required_approving_review_count: 0`, `required_review_thread_resolution: True`, `allowed_merge_methods == ["squash"]`, `06v:90-91`], `merge_queue` [`SQUASH`, build/min/max `== 1`, `evaluate_merge_group_size` `tools/check_merge_admission.py:700-737`], `required_status_checks` [`strict_required_status_checks_policy: True`, 4 contexts with `integration_id == 15368`], and `non_fast_forward`). *(Unpinned per `R2-i3`: `require_extra_approval_for_unattributed_changes`, `grouping_strategy`, `check_response_timeout_minutes`, `dismiss_stale_reviews_on_push`.)*
  2. **Rule-suites history (`gh api --paginate --slurp "repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=month&per_page=100"`, matching `tools/check_bypass_merges.py:141-166`):**
     - **30-day API window (`MAX_DAYS = 30`, `tools/check_bypass_merges.py:24,57-58,73-90`):** If `detector-controls.json` holds a prior `"main_ruleset"` entry older than 30 days, the reader fails closed (`ERROR: main_ruleset: previous recorded read is older than 30 days (<previous_recorded_at>); rule-suites API window (MAX_DAYS=30) cannot cover the gap without a recorded P-0xx acknowledgement in walk-baseline.json`). Recovery uses `--acknowledge-gap <P-0xx>`, requiring a matching `walk-baseline.json` `ruleset_gap_acknowledgements` row (`{"previous_recorded_at", "acknowledged_through", "disposition_ref": {"id", "source_path", "source_commit", "entry_sha256"}}`) with `P1`-pre-existing hash-bound `disposition_ref` (§6.5) naming both timestamps and `acknowledged_through >= now - timedelta(days=30)`.
     - **`result == "bypass"` evaluation (§21.1 item 8):** Owner merges routinely log `"bypass"`, so `"bypass"` alone is not a failure. For every `refs/heads/main` entry after `<baseline>` on `<head>`, `check_legacy_writes.py` verifies Rules 0–3, and the reader records `{after_sha, pushed_at, actor_name, touched_guarded_paths}` per bypass entry.
- **Token & recording schedule (`06v:603`):** Uses Stephen's `gh` CLI via `tools/run_w9_pinned_detectors.py` locally (CI token governed by U-3/D-8, §4.2), run at L-1 (`LR-003`, `research_system/legacy/preparers.py:686-690`) and pre-batch. Because `research_system/legacy/evidence.py:92-105` reads `detector-controls.json` at `git_head`, each pre-batch update needs Stephen's `Bypass reason:` PR (`tools/check_bypass_merges.py:41,135`) + `ars store advance-binding`. Output report hashed via `sha256_hex(canonical_bytes(report))` (`research_system/canonical.py:40-52`) and stored under `"main_ruleset"` with `"control": "recorded_read"`, `"output_sha256"`, `"recorded_at"`:
    ```json
    {
      "format": "w9-main-ruleset-read/1",
      "repository": "ZK-Theory/TDL",
      "ruleset_id": 20822054,
      "ruleset_name": "P-049 Gate 6 main merge admission",
      "enforcement": "active",
      "target_include": ["refs/heads/main"],
      "target_exclude": [],
      "rule_types": ["merge_queue", "non_fast_forward", "pull_request", "required_status_checks"],
      "allowed_merge_methods": ["squash"],
      "merge_queue_merge_method": "SQUASH",
      "merge_queue_max_entries_to_build": 1,
      "merge_queue_min_entries_to_merge": 1,
      "merge_queue_max_entries_to_merge": 1,
      "require_code_owner_review": true,
      "required_approving_review_count": 0,
      "required_review_thread_resolution": true,
      "strict_required_status_checks_policy": true,
      "required_status_checks": [
        {"context": "admission-controls", "integration_id": 15368},
        {"context": "contract-and-session-currency", "integration_id": 15368},
        {"context": "merge-admission", "integration_id": 15368},
        {"context": "require-active-currency-workflow", "integration_id": 15368}
      ],
      "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}],
      "rule_suites_ref": "refs/heads/main",
      "rule_suites_time_period": "month",
      "rule_suites_checked_count": 57,
      "rule_suites_bypass_count": 33,
      "unrecorded_legacy_bypass_commits": []
    }
    ```
- **Closed failure modes (exit `1`, or `2` on `gh api` error, leaving `detector-controls.json` untouched):**
  - `gh api` non-JSON/error (`ERROR: main_ruleset: failed to read rulesets/20822054`);
  - pinned invariant or `integration_id` drift (`ERROR: main_ruleset: ruleset 20822054 configuration drift: <detail>`);
  - stale >30-day read without matching `ruleset_gap_acknowledgements` row (`ERROR: main_ruleset: previous recorded read is older than 30 days`); or
  - unrecorded bypass write (`ERROR: main_ruleset: bypass evaluation on refs/heads/main touched guarded path without §4.2 record: <after_sha>`).
- **Controls (`tests/tools/test_w9_detectors.py`):** Synthetic payloads assert exit `1` for disabled enforcement, `"merge"` allowed method, `max_entries_to_merge: 2`, missing code-owner/context/`integration_id` change, added bypass actor, >30-day gap without hash-bound ack row, and unrecorded `"bypass"` guarded write; `--acknowledge-gap <P-0xx>` with valid hash-bound row exits `0`.

---

### 4.2 U-3: CI token (`GITHUB_TOKEN`) ruleset, rule-suites, and PR-lookup probe, plus D-8 fallback

#### 4.2.1 Current repository evidence on U-3

1. **Owner's `gh` login (verified live on 2026-11-21 in both `wp9-5-note-r1-review-2026-11-21.md:198` and Appendix A §21.1):**
   - `gh api repos/ZK-Theory/TDL/rulesets/20822054` returns HTTP 200 with all ruleset invariants in §4.1.
   - `gh api --paginate --slurp "repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=month&per_page=100"` returns HTTP 200 with 57 entries at `dbd54fe38` (`33` `bypass`, `24` `pass`; newest `after_sha` `dbd54fe382e7b2849d3f2038393cbdb4d709477b`).
   - `gh api repos/ZK-Theory/TDL/commits/dbd54fe382e7b2849d3f2038393cbdb4d709477b/pulls` returns HTTP 200 with PR `#446` (`merge_commit_sha == "dbd54fe382e7b2849d3f2038393cbdb4d709477b"`).
2. **Existing codebase note on `GITHUB_TOKEN` (`tools/check_bypass_merges.py:20-21`):**
   `tools/check_bypass_merges.py:20-21` states:
   > *"Reading rule suites needs the repository owner's token, which a workflow's `GITHUB_TOKEN` cannot be granted, so the weekly system review runs this in its step 1."*
   Note that `tools/check_bypass_merges.py:20-21` speaks only about **rule suites** (`rulesets/rule-suites`), not about the ruleset configuration endpoint (`rulesets/20822054`) or the commit-to-PR endpoint (`commits/<sha>/pulls`). Whether `GITHUB_TOKEN` on the public repository `ZK-Theory/TDL` (`private: false`) can read `rulesets/20822054`, `rulesets/rule-suites`, and `commits/<sha>/pulls` under `permissions: contents: read` vs `permissions: contents: read, pull-requests: read` is **UNVERIFIED** until the U-3 workflow probe runs (`06v:159`; `P-089` item 3, `03-decisions-and-open-questions.md:6105-6107`).
3. **Existing workflow `permissions:` blocks in `.github/workflows/` (verified at `dbd54fe38`):**
   - `.github/workflows/ci.yml`: no top-level `permissions:` block; job `watchdog-schedule-liveness` declares `permissions: actions: read, contents: read` (`ci.yml:239-241`).
   - `.github/workflows/merge-admission.yml`: top-level `permissions: contents: read, pull-requests: read, checks: read` (`.github/workflows/merge-admission.yml:52-55`); job `merge-admission` declares `checks: read, actions: read, contents: write, pull-requests: write` (`:70-83`).
   - `.github/workflows/merge-admission-sweep.yml`: top-level `permissions: contents: read` (`merge-admission-sweep.yml:58-59`); job `sweep` declares `checks: read, actions: write, contents: write, pull-requests: write` (`:74-80`).
   - `.github/workflows/ars-artefact-currency.yml`: top-level `permissions: contents: read` (`ars-artefact-currency.yml:12-13`).
   - `.github/workflows/ars-artefact-currency-watchdog.yml`: top-level `permissions: actions: read, contents: read` (`ars-artefact-currency-watchdog.yml:14-16`).
   - `.github/workflows/research-system-suite.yml`: top-level `permissions: contents: read` (`research-system-suite.yml:30-31`).

#### 4.2.2 Design of a runnable read-only U-3 probe

- **Why a `workflow_dispatch`-only workflow cannot probe U-3 before landing on `main`:**
  GitHub Actions does not register or allow `workflow_dispatch` on a new workflow file until that workflow file exists on the repository's default branch (`main`) (`tools/check_workflow_liveness.py:64-67`). Merging a probe workflow onto `main` before WP9.5 code is outside `P-089` (`03-decisions-and-open-questions.md:6127-6135`).
- **How the U-3 probe runs without touching `main` (and its side effects, `R2-m6`):**
  On Stephen's authorization, the reviewing session pushes a throwaway branch `probe/w9-u3-token-read` and opens a **draft, never-merged pull request** containing a temporary workflow `.github/workflows/u3-probe-temp.yml` triggered by `on: pull_request:`. GitHub Actions executes `on: pull_request:` workflows from the PR head commit immediately using a standard `GITHUB_TOKEN` scoped to the workflow's declared `permissions:` block, without modifying `main`. **Side effects (`R2-m6`):** opening that draft PR triggers the repository's existing `on: pull_request:` workflows (`ci.yml`, `merge-admission.yml`, `ars-artefact-currency.yml`, and `research-system-suite.yml`) against the throwaway branch; those runs are read-only/harmless on a never-merged PR and cancel as soon as the reviewing session records the outputs below, closes the draft PR, and deletes the remote branch `probe/w9-u3-token-read`.
- **What the probe tests (two jobs, four read-only GET calls + pinned-key body checks, `R2-m6`):**
  - Because GitHub can return HTTP 200 with optional administrative fields (such as `bypass_actors`, `rules[].parameters`, or `conditions`) omitted to a lower-privileged token, an HTTP 200 status alone does not prove the token can run §4.1's pin checks! Therefore, the probe logs both HTTP status + `X-Accepted-GitHub-Permissions` **and** which pinned top-level/nested keys are present in each HTTP 200 JSON body (`R2-m6`):
  - **Job 1 (`probe-contents-only`, `permissions: contents: read`):**
    1. `gh api -i repos/ZK-Theory/TDL/rulesets/20822054` — check presence of `id`, `enforcement`, `conditions.ref_name.include`, `bypass_actors`, and per-rule `parameters`.
    2. `gh api -i "repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=day&per_page=5"` — check JSON array length and `after_sha`/`result`/`actor_name`/`pushed_at` on the first item.
    3. `gh api -i repos/ZK-Theory/TDL/commits/dbd54fe382e7b2849d3f2038393cbdb4d709477b/pulls` — check JSON array length and `number`/`merged_at`/`merge_commit_sha`.
  - **Job 2 (`probe-with-pull-requests-read`, `permissions: contents: read, pull-requests: read`):**
    4. `gh api -i repos/ZK-Theory/TDL/commits/dbd54fe382e7b2849d3f2038393cbdb4d709477b/pulls` — check array length and `number`/`merged_at`/`merge_commit_sha`.
    (And `.github/workflows/legacy-write-detector.yml` declares `permissions: contents: read, pull-requests: read` unconditionally so `commits/<C>/pulls` and `pulls/<N>` always have `pull-requests: read` scope; §10.2.)
- **Exact temporary probe workflow YAML (`.github/workflows/u3-probe-temp.yml` on the throwaway draft PR):**
  ```yaml
  name: U-3 Token Read Probe (Throwaway Draft PR)
  on:
    pull_request:
  defaults:
    run:
      shell: bash
  jobs:
    probe-contents-only:
      runs-on: windows-latest
      timeout-minutes: 5
      permissions:
        contents: read
      env:
        GH_TOKEN: ${{ github.token }}
      steps:
        - name: Probe ruleset, rule-suites, and commits/pulls under contents-read
          run: |
            set +e
            probe_one() {
              local label="$1"
              local ep="$2"
              local kind="$3"
              out="$(gh api -i "$ep" 2>&1)"
              rc=$?
              status="$(printf '%s\n' "$out" | head -n 1 | tr -d '\r')"
              perms="$(printf '%s\n' "$out" | grep -i '^X-Accepted-GitHub-Permissions:' | tr -d '\r')"
              keys="$(printf '%s\n' "$out" | awk 'found{print} /^\r?$/{found=1}' | python -c "
            import json, sys
            raw = sys.stdin.read().strip()
            try:
                doc = json.loads(raw)
            except Exception as exc:
                print('non-json:' + type(exc).__name__)
                raise SystemExit(0)
            if '$kind' == 'ruleset' and isinstance(doc, dict):
                rule_types = sorted(r.get('type') for r in doc.get('rules', []) if isinstance(r, dict) and 'parameters' in r)
                print(f\"keys={sorted(k for k in ('id','name','enforcement','conditions','bypass_actors','rules') if k in doc)} rules_with_params={rule_types}\")
            elif isinstance(doc, list):
                first_keys = sorted(doc[0].keys()) if doc and isinstance(doc[0], dict) else []
                wanted = ('after_sha','result','actor_name','pushed_at') if '$kind' == 'suites' else ('number','merged_at','merge_commit_sha')
                print(f\"count={len(doc)} first_has={sorted(k for k in wanted if k in first_keys)}\")
            else:
                print(f'unexpected_type={type(doc).__name__}')
            ")"
              echo "perm=$label endpoint=$ep rc=$rc status=$status perms=$perms body=$keys"
              printf -- '- `%s` | `%s` | exit `%d` | `%s` | `%s` | `%s`\n' "$label" "$ep" "$rc" "$status" "$perms" "$keys" >> "$GITHUB_STEP_SUMMARY"
            }
            probe_one "contents: read" "repos/ZK-Theory/TDL/rulesets/20822054" "ruleset"
            probe_one "contents: read" "repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=day&per_page=5" "suites"
            probe_one "contents: read" "repos/ZK-Theory/TDL/commits/dbd54fe382e7b2849d3f2038393cbdb4d709477b/pulls" "pulls"
            exit 0

    probe-with-pull-requests-read:
      runs-on: windows-latest
      timeout-minutes: 5
      permissions:
        contents: read
        pull-requests: read
      env:
        GH_TOKEN: ${{ github.token }}
      steps:
        - name: Probe commits/pulls under pull-requests-read
          run: |
            set +e
            ep="repos/ZK-Theory/TDL/commits/dbd54fe382e7b2849d3f2038393cbdb4d709477b/pulls"
            out="$(gh api -i "$ep" 2>&1)"
            rc=$?
            status="$(printf '%s\n' "$out" | head -n 1 | tr -d '\r')"
            perms="$(printf '%s\n' "$out" | grep -i '^X-Accepted-GitHub-Permissions:' | tr -d '\r')"
            keys="$(printf '%s\n' "$out" | awk 'found{print} /^\r?$/{found=1}' | python -c "
            import json, sys
            try:
                doc = json.loads(sys.stdin.read().strip())
                first_keys = sorted(doc[0].keys()) if isinstance(doc, list) and doc and isinstance(doc[0], dict) else []
                print(f\"count={len(doc) if isinstance(doc, list) else -1} first_has={sorted(k for k in ('number','merged_at','merge_commit_sha') if k in first_keys)}\")
            except Exception as exc:
                print('non-json:' + type(exc).__name__)
            ")"
            echo "endpoint=$ep rc=$rc status=$status perms=$perms body=$keys"
            printf -- '- `pull-requests: read` | `%s` | exit `%d` | `%s` | `%s` | `%s`\n' "$ep" "$rc" "$status" "$perms" "$keys" >> "$GITHUB_STEP_SUMMARY"
            exit 0
  ```
- **Which call decides D-8 (`06v:159,571`; `P-064` item 8, `03-decisions-and-open-questions.md:4232-4233`):**
  Call 2 (`GET repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=day&per_page=5`) decides D-8. If Call 2 returns HTTP 403 or 404 (or omits `after_sha`/`result`/`actor_name`) under `GITHUB_TOKEN`, D-8 applies to `rule-suites`. If Call 1 (`rulesets/20822054`) returns HTTP 200 with all pinned keys (`bypass_actors`, `rules[].parameters`, `conditions`) even when Call 2 fails, the CI workflow still runs the `rulesets/20822054` configuration check on every run and defers only `rulesets/rule-suites` under D-8; if Call 1 omits pinned fields under `GITHUB_TOKEN`, that missing-field scope is also recorded for Stephen at `P-090` before code dispatch.

| Endpoint | Token & Permissions | Observed HTTP status, pinned keys & details | Result | Recorded by / Date |
|---|---|---|---|---|
| `GET repos/ZK-Theory/TDL/rulesets/20822054` | Owner `gh` login (local) | **HTTP 200**: `id: 20822054`, `name: "P-049 Gate 6 main merge admission"`, `enforcement: "active"`, `target_include: ["refs/heads/main"]`, `allowed_merge_methods: ["squash"]`, `merge_queue: {merge_method: "SQUASH", max_entries_to_merge: 1}`, 4 required status checks (`integration_id: 15368`), `bypass_actors: [{actor_id: 5, actor_type: "RepositoryRole", bypass_mode: "pull_request"}]` | **PASS** (verified live) | Reviewing session (`wp9-5-note-r1-review-2026-11-21.md:198`, `r2-review:217`) and authoring session (Appendix A §21.1), 2026-11-21 |
| `GET repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=month&per_page=100` | Owner `gh` login (local) | **HTTP 200**: 57 entries at `dbd54fe38` (`33` `bypass`, `24` `pass`), newest `after_sha: "dbd54fe382e7b2849d3f2038393cbdb4d709477b"` (`result: "bypass"`, `pushed_at: "2026-11-21T20:20:44+00:00"`, `actor_name: "stephendor"`), oldest `bb9d91d45493f7dfdf31aa1c3e6b34ecf6113a32` (`2026-10-21T22:42:20+01:00`) | **PASS** (verified live) | Reviewing session (`wp9-5-note-r1-review-2026-11-21.md:198`) and authoring session (Appendix A §21.1), 2026-11-21 |
| `GET repos/ZK-Theory/TDL/commits/dbd54fe3.../pulls` | Owner `gh` login (local) | **HTTP 200**: PR `#446`, `merge_commit_sha == "dbd54fe382e7b2849d3f2038393cbdb4d709477b"` | **PASS** (verified live) | Reviewing session (`wp9-5-note-r1-review-2026-11-21.md:183,300`), 2026-11-21 |
| `GET repos/ZK-Theory/TDL/rulesets/20822054` | CI `GITHUB_TOKEN` (`contents: read`) | **OPEN GAP (U-3, UNVERIFIED)** — pending throwaway draft-PR probe run | Pending | Owner: Stephen authorizes run; reviewing session runs and records HTTP status, `X-Accepted-GitHub-Permissions`, and pinned-key presence here before code dispatch |
| `GET repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=day&per_page=5` | CI `GITHUB_TOKEN` (`contents: read`) | **OPEN GAP (U-3, UNVERIFIED)** — decides D-8; expected HTTP 403/404 per `tools/check_bypass_merges.py:20-21`; pending probe run | Pending | Owner: Stephen authorizes run; reviewing session runs and records HTTP status, `X-Accepted-GitHub-Permissions`, and pinned-key presence here before code dispatch |
| `GET repos/ZK-Theory/TDL/commits/dbd54fe3.../pulls` | CI `GITHUB_TOKEN` (`contents: read` vs `pull-requests: read`) | **OPEN GAP (U-3, UNVERIFIED)** — pending probe run | Pending | Owner: Stephen authorizes run; reviewing session runs and records HTTP status, `X-Accepted-GitHub-Permissions`, and pinned-key presence here before code dispatch |

#### 4.2.3 Exact D-8 fallback (`06v:159,571`; `P-064` item 8, `03-decisions-and-open-questions.md:4232-4233`)

- **Exact texts:**
  - `06v` §6 row `D-8` (`06v-w9-implementation-plan.md:571`):
    > *"Record as a known limit that bypass use between batches is seen only at the next pre-batch local read, under the owner's `gh`. The alternative is a token with ruleset read access."*
  - `P-064` item 8 (`03-decisions-and-open-questions.md:4232-4233`):
    > *"D-8, the CI token limit. This applies only if U-3 shows the CI token cannot read rule-suites. Bypass use between batches is then a known limit, seen at the next pre-batch read."*
  - `06v` §2.8 row `U-3` (`06v-w9-implementation-plan.md:159`):
    > *"A read-only probe from a workflow run. If the token cannot, the limit goes to Stephen as D-8. It is not a package-level fallback."*
- **How D-8 is gated so a workflow edit alone cannot silently enable it (`R1-m1`, `R2-M1`):**
  1. D-8 applies **only** to `rulesets/rule-suites` (and only if the U-3 probe shows `GITHUB_TOKEN` cannot read `rulesets/rule-suites`, and Stephen confirms D-8 rather than provisioning a ruleset-read token). If `GITHUB_TOKEN` can read `rulesets/20822054` with its pinned fields, `tools/check_legacy_writes.py` still reads and enforces the `rulesets/20822054` configuration in CI on every run.
  2. Because `06v:159` states *"the limit goes to Stephen as D-8. It is not a package-level fallback"*, `tools/check_legacy_writes.py` refuses `--ruleset-check ci-d8` unless `.research-system/evidence/w9/walk-baseline.json` (committed at `<head>`, §6.2) carries an explicit owner-accepted, **hash-bound** `d8_rule_suites_limit_decision_ref`:
     `{"id": "P-09x", "source_path": "docs/plans/agentic-research-system/03-decisions-and-open-questions.md", "source_commit": "<40-hex ancestor of P1>", "entry_sha256": "<64-hex>"}`,
     matching the `### P-09x` section slice at `<source_commit>` (`is_ancestor(source_commit, P1)`), naming `"D-8"` and `"rule-suites"`, and protected once non-null by Rule 0 item 2 (`R2-M1`). Without that verified hash-bound decision reference at `<head>`, passing `--ruleset-check ci-d8` fails closed (`ERROR: main_ruleset: --ruleset-check ci-d8 requires a verified hash-bound d8_rule_suites_limit_decision_ref in walk-baseline.json`).
  3. On the operator machine before every batch (`06v:603`) and at L-1, `tools/check_legacy_writes.py` always runs with `--ruleset-check require` (the default), reading both `rulesets/20822054` and `rulesets/rule-suites` under Stephen's `gh` login.
  4. **Scope of the D-8 known limit (`R1-i3`):** Because 33 of 57 `refs/heads/main` rule-suite evaluations in the past month at `dbd54fe38` were `result: "bypass"`, D-8 means CI does not inspect `rule-suites` bypass metadata between batches. However, the Git first-parent walk in CI still inspects every commit on `main` (including every bypass merge) against Rules 0, 1, 2, and 3.

---

### 4.3 U-4: Operator machine's path to the vault and read-only dry run

#### 4.3.1 Verified repository facts on the vault path and why `tools/check_legacy_log_baseline.py` needs its own root-junction check

1. **The repository junction vs the real vault directory:**
   - In the main checkout `C:\Users\steph\TDL`, `C:\Users\steph\TDL\vault` is a gitignored Windows directory junction (`Attributes: Directory, ReparsePoint`, `LinkType: Junction`) targeting `C:\Users\steph\Documents\TDA-Research` (`01-current-system-evidence.md:357`; `CLAUDE.md:15,28`; `CONVENTIONS.md:790,796`).
   - Because `vault/` is gitignored, linked worktrees under `C:\Users\steph\TDL\.apm\worktrees\<name>` do not have a `vault\` junction (`CLAUDE.md:28`).
2. **WP9.2 segmentation contract census figures (`w9-segmentation-contract-v1.md:233-258`, evidence for the grammar, NOT a baseline):**
   - At the WP9.2 contract census on `2026-10-23` (`09:07:42Z`), `C:\Users\steph\Documents\TDA-Research\04-Methods\Computational-Log.md` was `700,632` bytes, SHA-256 `de44a67b8b72b62bbd17fafee9a20f91308c66e6105e860155bce25120ef1026` (LF, no BOM), yielding `255` dated entries and `1` structural block (`# Computational Log` at L4436), with **0 blockers** (`w9-segmentation-contract-v1.md:242`).
   - At the revision-3 re-run on `2026-10-23` (`12:04:22Z`), the live page had grown by one successor entry to `703,531` bytes, SHA-256 `19ad5c4d797d02cfef8e384255bcb960e90830ea9a6a7c83cb3029ca7ab66bb6`, yielding `256` entries and `1` structural block (at L4476), with **0 blockers** (`w9-segmentation-contract-v1.md:254-256`).
   - As `w9-segmentation-contract-v1.md:258` states: *"The census is evidence for the grammar, not a baseline. The L-0b export is the baseline, taken under §6."*
3. **What WP9.3's `handle_bound_read` and `LegacyReader.__init__` actually check (`research_system/legacy/reader.py:140-206,241-248` and `research_system/store/anchor.py:1934-1950`):**
   - `handle_bound_read(root, path)` (`research_system/legacy/reader.py:140-206`) opens the root directory with `open_registered_root_anchor(root, delete_protect=True)` (`reader.py:152`). In `research_system/store/anchor.py:1934-1950`, `open_registered_root_anchor` calls `_open_directory_anchor(path, reject_reparse=False, delete_protect=delete_protect)` because *"Registered roots may themselves be junctions, so this purpose-named seam follows the root alias while retaining the physical identity handle."*
   - Inside the root, `handle_bound_read` opens each intermediate directory with `open_registered_member_directory_anchor(child)` (`reader.py:160`), rejects any intermediate directory where `os.path.normcase(str(child_anchor.final_path)) != os.path.normcase(str(child))` (`:164-165`), and checks `if candidate.is_symlink() or candidate.is_junction(): raise ReadRefused("the registered path is a symlink or junction")` on the leaf (`:168-169`).
   - `LegacyReader.__init__` (`research_system/legacy/reader.py:241-248`) checks `Path(os.path.abspath(vault_root)).relative_to(self.repository_root)` and raises `ReadRefused("the vault is read through its real path, never through the repository")`. Because `os.path.abspath` is **lexical** (it does not resolve junctions or symlinks), `LegacyReader.__init__` rejects `<repo>/vault`, but a junction located outside `repository_root` would not be caught by `LegacyReader.__init__` or by `open_registered_root_anchor` (`reject_reparse=False`).

#### 4.3.2 How `tools/check_legacy_log_baseline.py` validates `--vault-root`

To reject **both** `<repo>/vault` and any external symlink or junction passed as `--vault-root`, `tools/check_legacy_log_baseline.py` performs an explicit three-step check before calling `handle_bound_read` (`research_system/legacy/reader.py:140-206`):
1. **Explicit CLI argument required (`P-083` item 2 `m-3`):** `--vault-root <path>` is required (no default to `<repo>/vault`).
2. **Root-level symlink/junction refusal on the given path and every ancestor:**
   ```python
   given_vault = Path(os.path.abspath(vault_root))
   if not given_vault.exists() or not given_vault.is_dir():
       raise ReadRefused(f"vault_root does not exist or is not a directory: {given_vault}")
   if given_vault.is_symlink() or given_vault.is_junction():
       raise ReadRefused(f"vault_root must be the real vault directory, not a symlink or junction: {given_vault}")
   resolved_vault = given_vault.resolve(strict=True)
   if os.path.normcase(str(resolved_vault)) != os.path.normcase(str(given_vault)):
       raise ReadRefused(f"vault_root resolves through a reparse point or alias: {given_vault} -> {resolved_vault}")
   ```
   (On Python 3.13 / Windows 11, `Path.is_junction()` and `Path.is_symlink()` are standard `pathlib.Path` methods used at `research_system/legacy/reader.py:168`, and comparing `os.path.normcase(str(given_vault.resolve(strict=True)))` against `os.path.normcase(str(given_vault))` catches any ancestor junction as well.)
3. **Disjointness from `repository_root` (both lexical and resolved):**
   Neither `given_vault` nor `resolved_vault` may be equal to or inside `repository_root.resolve(strict=True)` (`relative_to` check).
4. **Handle-bound read of the member file:**
   Calls `raw, physical, _ = handle_bound_read(resolved_vault, "04-Methods/Computational-Log.md")` (`research_system/legacy/reader.py:140-206`), which verifies `04-Methods` is not a link/junction, `Computational-Log.md` is a regular file with `st_nlink == 1`, and file identity `(st_dev, st_ino, st_size, st_mtime_ns, st_nlink)` and parent directory anchors remain invariant across the read (`reader.py:157-204`).

#### 4.3.3 Recorded U-4 metadata read (`2026-11-21T21:06:44Z`) and pre-code reader+segmenter dry-run gate

1. **Live U-4 metadata read (executed by the reviewing session on Stephen's authorization at `2026-11-21T21:06:44Z`; `handoffs/wp9-5-gemini-note-r2-followup-2026-11-21.md:49-56`):**

| Path | Property | Prior recorded evidence (`01-current-system-evidence.md:357`; `w9-segmentation-contract-v1.md:242,254-256`) | Live U-4 metadata verification (`2026-11-21 21:06:44 UTC`) |
|---|---|---|---|
| `C:\Users\steph\TDL\vault` | `Attributes`, `LinkType`, `Target` | `Directory, ReparsePoint`; `Junction` -> `C:\Users\steph\Documents\TDA-Research` | **`Attributes: Directory, ReparsePoint`; `LinkType: Junction`; `Target: C:\Users\steph\Documents\TDA-Research`** (Verified `2026-11-21T21:06:44Z`) |
| `C:\Users\steph\Documents\TDA-Research\04-Methods\Computational-Log.md` | `Length`, `LastWriteTimeUtc`, `Attributes`, `LinkType`, `SHA256` | WP9.2 census (`2026-10-23`, grammar evidence only): `700,632` bytes (`de44a67b...`, 255 entries, 1 structural, 0 blockers), then `703,531` bytes (`19ad5c4d...`, 256 entries, 1 structural, 0 blockers) | **`Length: 833,453` bytes; `LastWriteTimeUtc: 2026-11-21 19:24:58`; `Attributes: Archive`; `LinkType: None`; SHA-256 `73fcbe839acfc1436c8e4a5b336bcc542bbc72c8cb4f6946865ecc8e33b77c8e`** (Verified `2026-11-21T21:06:44Z`) |

2. **Remaining U-4 pre-code step — handle-bound reader and segmenter dry run (`R1-m8`, `R2-m3`, `R2-m7`):**
   - As `R1-m8` notes, metadata alone does not exercise `handle_bound_read` (`st_nlink == 1`, `open_registered_root_anchor`, `open_registered_member_directory_anchor`) or `segment(raw, "computational_log_entry")` on the current `833,453`-byte live file.
   - `P-089` item 4 (`03-decisions-and-open-questions.md:6116-6117`) explicitly permits U-4's dry run to read the vault (`"U-4's dry run may read the vault; it writes nothing there"`), while Handover §4 (`handoffs/wp9-5-gemini-note-handover-2026-11-21.md:175`) and Follow-up §2 (`handoffs/wp9-5-gemini-note-r2-followup-2026-11-21.md:57-60`) direct this authoring session not to run it itself and to specify it as a pre-code step for the reviewing session.
   - **Exact read-only dry-run scratch script for the reviewing session to run and record before WP9.5 code dispatch (`R2-m7`, `R2-m3`):**
     Save the following read-only script outside the repository (in the reviewing session's temporary/scratchpad directory as `u4_dry_run.py` — never using multi-line generated `python -c` in PowerShell) and run it with `C:\Users\steph\TDL` (or `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note`) as the working directory and `PYTHONPATH=.` so both `research_system` and `tools.w9_segmentation` resolve cleanly:
     ```python
     # scratch/u4_dry_run.py (run from repository or worktree root with PYTHONPATH=.):
     #   .\.venv\Scripts\python.exe <scratch>\u4_dry_run.py
     import os
     from collections import Counter
     from pathlib import Path
     from research_system.legacy.reader import handle_bound_read
     from research_system.legacy.segmentation import segment as rs_segment
     from tools.w9_segmentation import segment as tool_segment

     given_vault = Path(os.path.abspath(r"C:\Users\steph\Documents\TDA-Research"))
     repo_resolved = Path.cwd().resolve(strict=True)
     exists_and_is_dir = given_vault.exists() and given_vault.is_dir()
     not_symlink_or_junction = not given_vault.is_symlink() and not given_vault.is_junction()
     resolved_vault = given_vault.resolve(strict=True)
     abspath_equals_resolved_normcase = os.path.normcase(str(resolved_vault)) == os.path.normcase(str(given_vault))
     disjoint_from_repo_root = (
         not given_vault.is_relative_to(repo_resolved)
         and not resolved_vault.is_relative_to(repo_resolved)
     )
     root_checks = {
         "exists_and_is_dir": exists_and_is_dir,
         "not_symlink_or_junction": not_symlink_or_junction,
         "abspath_equals_resolved_normcase": abspath_equals_resolved_normcase,
         "disjoint_from_repo_root": disjoint_from_repo_root,
     }
     assert all(root_checks.values()), root_checks
     raw, phys, _ = handle_bound_read(resolved_vault, "04-Methods/Computational-Log.md")
     s1 = rs_segment(raw, "computational_log_entry")
     s2 = tool_segment(raw, "computational_log_entry")
     assert s1 == s2, "segmenter mismatch"
     kinds = Counter(r["row_kind"] for r in s1["rows"])
     blockers = [
         (r["row_ordinal"], r["start_line"], r["start_line"] + r["line_count"] - 1, r["blocker_reason"])
         for r in s1["rows"]
         if r["row_kind"] == "blocker"
     ]
     print(
         {
             "root_checks": root_checks,
             "bytes": len(raw),
             "sha256": s1["file_sha256"],
             "link_count": phys["link_count"],
             "canonical_target": phys["canonical_target"],
             "file_facts": s1["file_facts"],
             "row_counts": dict(kinds),
             "blockers": blockers,
         }
     )
     ```
     (Invoked from `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note`: `$env:PYTHONPATH="."; .\.venv\Scripts\python.exe <scratch>\u4_dry_run.py`; prints the three §4.3.2 root-check booleans alongside length, SHA-256, `link_count`, `canonical_target`, `file_facts`, `row_counts`, and blocker metadata — never entry prose — and uses `start_line` and `line_count` per `research_system/legacy/segmentation.py:418-419`, `R3-m6`.)
   - **Dry-run record slot (precondition for WP9.5 code dispatch in §15.1):**
     `OPEN GAP (U-4 reader+segmenter dry run, UNVERIFIED)` — to be run by the reviewing session and recorded here before WP9.5 code is dispatched.

---

## 5. The registration manifest export (M-6)

### 5.1 Why the manifest exists and why CI cannot read the control store

- Under `06v` D-1 (`06v-w9-implementation-plan.md:563`), the W9 control store is `C:/Users/steph/TDL-ARS-G7-Control`, located outside the repository working tree on the operator machine.
- GitHub Actions runners (`windows-latest`) have only the checked-out Git repository (`ZK-Theory/TDL`); they cannot read `C:/Users/steph/TDL-ARS-G7-Control`.
- Therefore, WP9.3 established `.research-system/evidence/w9/registration-manifest.json` (`REGISTRATION_MANIFEST`, `research_system/legacy/evidence.py:37,40,114-131`) as the committed in-repository mirror of the store's registered legacy path set.

### 5.2 When it is written and checked

1. **Per registration batch, before that batch's first observation (`06v:470-473,483-484`):**
   - After a registration batch's `legacy-path-registration` records are resolved into the control store (`LR-005`) and **before** any `legacy-observation` record for that batch is submitted (`LR-015`), the operator runs `tools/export_w9_registration_manifest.py`, commits `.research-system/evidence/w9/registration-manifest.json` to `main` via a reviewed PR, and advances the store binding's `git_head` to that commit via `ars store advance-binding` (`06v:578`).
   - WP9.3's `prepare_observation` (`LR-015`, `research_system/legacy/preparers.py:1200,1215-1218`) already enforces this order: it calls `w9_evidence.require_registered(w9_evidence.read_evidence(reader.repository_root, reader.git_head, w9_evidence.REGISTRATION_MANIFEST), registration)` and raises `EvidenceRefused("W9 registration is not in the registration manifest at git_head")` (`research_system/legacy/evidence.py:130`) if the registration is absent from the committed manifest at `git_head`.
2. **Before every batch (`06v:605` batch checklist):**
   - The batch checklist (`06v-w9-implementation-plan.md:605`, *"check the registration manifest against the store"*) runs `tools/export_w9_registration_manifest.py --check`, failing closed if the committed manifest at the store binding's `git_head` does not equal the store's registered set.

### 5.3 Exact mechanism: `tools/export_w9_registration_manifest.py` (**new**)

- **What it reads (using actual `research_system` seams verified at `dbd54fe38`):**
  1. Takes `--control-root <path>` (the W9 control store root, e.g. `C:/Users/steph/TDL-ARS-G7-Control`) and either `--output <path>` (export mode) or `--check` (verify mode against the committed manifest at the store binding's `git_head`).
  2. Loads and validates the store binding via `_legacy_current_binding(control_root)` (`research_system/cli.py:1662-1684`), which first runs `refuse_gate6_lock_roots` (`research_system/legacy/runtime.py`) against `accepted_genesis_payload()["refused_store_identities"]` (`research_system/legacy/accepted_w9.py:132-149`), loads the unbound manifest via `load_store_manifest_unbound` (`research_system/store/identity.py:636-651`), and returns the `ApprovedProjectBinding` from `load_current_binding` (`research_system/store/current_binding.py:801`). From `binding`, the tool obtains `binding.repository_root` and `git_head = binding.binding["git_head"]` (`research_system/cli.py:1709,1714`).
  3. Rebuilds the read-only W9 projection via `_legacy_projection(control_root)` (`research_system/cli.py:1648-1659`), which replays the ledger through `replay_legacy(events, schemas=schemas)` (`research_system/legacy/replay/driver.py:147-207`).
  4. Reads the recorded path registrations from `state["records"]["legacy_path_registration"]` (`research_system/legacy/replay/reducers.py:70,571`), which is a dict mapping `record_id -> registration_record`. (Under `LR-056`, `legacy-path-registration` is not a supersession target, so every entry in `state["records"]["legacy_path_registration"].values()` is active.)
- **What each manifest entry carries (`R1-M4`, `R1-M5`, `R1-m10`; Owner Point A, §16):**
  - In `.research-system/schemas/contracts/w9/legacy-path-registration.schema.json:54-94`, every `legacy-path-registration` record carries:
    - `root_kind` (`"repository_root"` or `"vault_root"`),
    - `root_id` (non-empty string),
    - `normalized_path` (canonical relative POSIX path),
    - `role` (one of the 13 roles in `legacy-path-registration.schema.json:78-94`), and
    - `source_identity_kind` (one of `"git_tracked"`, `"untracked_file"`, `"restricted_untracked_file"`, `"vault_file"`, `legacy-path-registration.schema.json:70-76`).
  - As `R1-M4` and `R1-M5` demonstrated, `tools/check_legacy_writes.py` needs **both** `role` and `source_identity_kind` on each manifest entry because:
    - `role` distinguishes `shared_enforcement_surface` (Rule 3), `conventions_lock` (`CONVENTIONS.md`, governed by `tools/check_conventions_legacy_locks.py` under W9 §7.3 and excluded from Rule 1), `successor_results_root` (`results/ars/`, excluded from Rule 1 and from §6.6's Git existence check), `legacy_read_only_projection` (`.research-system/projections/legacy/...`, excluded from Rule 1), and `legacy_manuscript_root` (`papers/P01-A-JRSSA/`, `papers/P01-B-JRSSB/`, directory prefix match in Rule 1);
    - `source_identity_kind` distinguishes `git_tracked` registrations (which exist in Git trees and are checked by Rule 1 and §6.6's `git cat-file` check) from `untracked_file` and `restricted_untracked_file` registrations under `repository_root` (such as untracked `*.csv`, `*.pkl`, `.apm/memory/stage-NN/` logs, `.apm/bus/`, and `.research-system/projections/legacy/`, which are **not** in Git and would otherwise cause §6.6's `git cat-file -e <head>:<path>` check to fail permanently!).
  - Under **Owner Point A (Option A1, Recommended, §16)** (`R2-m11 (c),(d)`):
    - Uniform `/2` format policy (matching Option D3): bump `REGISTRATION_MANIFEST_FORMAT` (`research_system/legacy/evidence.py:40`) to **`"w9-registration-manifest/2"`** because no live `/1` manifest exists prior to L-1 and Option A1 changes the closed per-entry key set from 3 keys to 5 keys:
      ```json
      {
        "format": "w9-registration-manifest/2",
        "registrations": [
          {
            "normalized_path": "contracts/stochastic-tests/monte-carlo-permutation-p-value.yaml",
            "role": "shared_enforcement_surface",
            "root_id": "ZK-Theory/TDL",
            "root_kind": "repository_root",
            "source_identity_kind": "git_tracked"
          }
        ]
      }
      ```
    - What changes in `research_system/legacy/evidence.py:40,114-131` (`require_registered`, `R1-m10`, `R2-m11 (c),(d)`):
      In `evidence.py:122-130`, `require_registered` currently checks `REGISTRATION_MANIFEST_FORMAT` (`"w9-registration-manifest/1"`), closes each entry on `{"root_kind", "root_id", "normalized_path"}`, and tests `if wanted not in [dict(entry) for entry in entries]:` (`tests/research_system/unit/test_w9_evidence.py:62` explicitly asserts an extra key is refused!).
      Under Option A1:
      1. `REGISTRATION_MANIFEST_FORMAT` moves to `"w9-registration-manifest/2"` (uniform with Option D3's `"w9-shared-surface-changes/2"`);
      2. every entry in `"registrations"` is closed on the 5 keys `{"root_kind", "root_id", "normalized_path", "role", "source_identity_kind"}` (no extra keys allowed, keeping `test_w9_evidence.py:62`'s closed-object guard intact under the updated format);
      3. when `role` and `source_identity_kind` are present on `registration`, `require_registered` checks `(entry["role"], entry["source_identity_kind"]) == (registration.get("role"), registration.get("source_identity_kind"))`;
      4. the membership comparison at line 129 projects each `entry` to the three identity keys `({key: entry[key] for key in ("root_kind", "root_id", "normalized_path")})` before testing `wanted not in ...`, avoiding the 3-key vs 5-key dict mismatch; and
      5. **dated WP9.3 amendment and blast-radius scope:** because `require_registered` is an accepted WP9.3 gate at `LR-015` (`prepare_observation`) and the 3-key manifest shape is built/appended by `tests/research_system/unit/test_w9_evidence.py`, `tests/research_system/integration/w9_runtime_harness.py:451-466`, `test_w9_wp9_4_1_runtime.py:95-109`, and `test_w9_wp9_4_2_runtime.py:86-100`, selecting Option A1 requires updating those four test/harness files alongside `evidence.py:40,114-131` and recording a dated WP9.3 amendment, an independent review, and a decision-register entry (`P-090`). No WP9.4 production code changes (only test fixture manifest builders add `"role"` and `"source_identity_kind"`); because `docs/plans/agentic-research-system/transition/w9/wp9-4-1-record.md:114,130` cites `test_w9_wp9_4_1_runtime.py` pass counts (`13 passed`, `688.11s`), whether WP9.4's recorded pass counts are re-recorded (counting against Owner Point G) is put to Stephen in §16.3. (Option A2 avoids touching any WP9.3/WP9.4 file.)
- **Sorting and serialization:**
  - Entries in `"registrations"` are sorted by `(entry["root_kind"], entry["root_id"], entry["normalized_path"])`, checked for uniqueness on `(root_kind, root_id, normalized_path)`, and written as UTF-8 JSON (`json.dumps(payload, indent=2, sort_keys=True) + "\n"`, LF line endings).
- **How `--check` mode works (store-equals-manifest check):**
  1. Loads `binding = _legacy_current_binding(control_root)` and `state, _ = _legacy_projection(control_root)`.
  2. Projects the expected registration list from `state["records"]["legacy_path_registration"].values()`.
  3. Reads `.research-system/evidence/w9/registration-manifest.json` from Git at `binding.binding["git_head"]` via `evidence.read_evidence(binding.repository_root, binding.binding["git_head"], evidence.REGISTRATION_MANIFEST)` (`research_system/legacy/evidence.py:92-105`).
  4. Validates the committed manifest's 5-key schema (`"w9-registration-manifest/2"` under Option A1) and compares `manifest["registrations"]` against the projected list from the store.
  5. If they differ, exits `1` with `ERROR: registration_manifest: store_manifest_mismatch at git_head=<git_head>: missing_in_manifest=<...>, extra_in_manifest=<...>`.

---

## 6. The post-merge first-parent detector (`tools/check_legacy_writes.py` and `.github/workflows/legacy-write-detector.yml`)

### 6.1 Time-indexed evidence evaluation, trust-root boundary, and "pin, no lockstep" decision

No repository-content trust root stops a merged commit from changing `.github/workflows/legacy-write-detector.yml` or scripts on `main` (GitHub runs workflows from the pushed commit on GitHub Free; `CONVENTIONS.md:721-725`). Under **Stephen's `2026-11-22` decision (*"pin, no lockstep", to be entered in `P-090` with the other owner points*)**:
- **Preventive (`Option I1` CODEOWNERS + optional `Option I3`):** `.github/CODEOWNERS` (`@stephendor`) protects the workflow, 7 WP9.5 `tools/` files, `test_w9_detectors.py`, `accepted_w9.py`, and `/.research-system/evidence/w9/` (plus `/tools/w9_segmentation.py` under Recommended `I1-include-seg`, §16.1), optionally paired with out-of-tree `vars.W9_DETECTOR_PIN` (`I3`). Pin advances merge via Stephen's `Bypass reason:` review; `Option I2` fails R1-B1 scenarios 4–5 (§16.1).
- **Pin kept, lockstep dropped (no Rule 0.3):** Unpinned edits to non-code-owned closure modules are **not** violations; head's `baselines[-1]` keeps running until Stephen advances the pin, exiting `2` (`ERROR`) on incompatible formats/uncaught errors (§6.3).
- **No PR-time pin-advance gate (`admission-controls`):** Runs `L1_LIVE`, F1 tests, `--verify-watched-to-fail` (under `L1_LIVE`), and optional K1—no `HEAD` blob check, no gating row check, no PR verdict comparison, and no `gh` calls (optional advisory Rule 0.2 row report only). Pin advances rely solely on Stephen's PR review + attached manual comparison diff (§6.2.2, §13.2 `HR-3`).

Because single-snapshot `<head>` evaluation fails via atomic disarm, retroactive false positives, retroactive blessing, and self-edits, WP9.5 enforces:

| Evidence / artifact | Evaluated at / how | Why |
|---|---|---|
| `registration-manifest.json` (Rules 1, 3) | **`P1` union `C`** ($\text{Manifest}(P_1) \cup \text{Manifest}(C)$) | Blocks atomic disarm and retroactive false positives. |
| `legacy-write-records.json` (Rules 1–3) | **Commit `C`** | Requires in-PR record at `C` (`06v:212,479-481`); blocks retroactive blessing. |
| `shared-surface-changes.json` (Rule 3) | **Commit `C`** (or `<head>` with late-entry Rule 3 `acknowledged`, §6.2.2) | Binds late recovery to WP9.3 `check_change_list` (`evidence.py:190-218`, `acceptance.py:121-136`). |
| Monotonicity & rows (**Rule 0**) | **Every `P1 -> C` in `(b0, head]`** | Ledgers & `walk-baseline.json` top-level keys monotonic; `baselines[0]` & `baselines[k]` pass (i)–(iv); no Rule 0.3 lockstep. |
| 22-blob detector code | **Confined `cat-file blob` + `hash-object --no-filters` + `python -S -P`** | Rejects traversal/Windows device/trailing-dot names; child `[sys.executable, "-S", "-P", ...]`, `PYTHONPATH`, `PYTHONSAFEPATH=1`, `1x` post-merge walk (§6.2.3, §10.2). |

---

### 6.2 The walk baseline (`walk-baseline.json`), acknowledged violations, pin-advance comparison procedure, and import closure

#### 6.2.1 Summary of first-parent commits touching guarded prefixes between `4b143c92` and `dbd54fe3`

Running `git --no-replace-objects rev-list --first-parent --reverse 4b143c9225035cc29e37351445f1c3a4ab09ceb1..dbd54fe382e7b2849d3f2038393cbdb4d709477b` yields **320** first-parent commits on `main`, of which **22** touched `CONVENTIONS.md`, `results/`, `papers/`, `contracts/`, or `.apm/`: 9 `CONVENTIONS.md`-only pure-successor PRs (`#172`, `#178`, `#183`, `#278`, `#345`, `#376`, `#384`, `#419`, `#425`), 1 mixed PR (`#277` `1dbf6b7b`), 3 `.apm/tracker.md` Working-Note PRs (`#368` `452352ff`, `#388` `e3519ba7`, `#433` `a6a98966`), 3 ARS contract PRs (`#168`, `#169`, `#334`), 3 pre-W9/ruled/reviewed results PRs (`#125`, `#129`, `#401`), 2 direct pushes (`5df0c001`, `811d5a2b`, replayed in `W9-T7`), and 1 revert PR (`#219` `b132406e`). Exact hashes and reproduction commands are in §21.1 item 3 (`wp9-5-note-r2-review-2026-11-21.md:137-148`, `wp9-5-note-r3-review-2026-11-21.md:107-117`).

#### 6.2.2 Committed append-only walk-baseline ledger, acknowledged violations, pin-advance comparison evidence, and walk cost

Instead of hard-coding a baseline SHA inside `tools/check_legacy_writes.py`:
1. **Committed append-only ledger (`.research-system/evidence/w9/walk-baseline.json`, format `"w9-walk-baseline/1"`):**
   Added at L-1 (and as a dated row in `06v-addendum-2026-11-10-w9-paths.md` under Owner Point C):
   ```json
   {
     "format": "w9-walk-baseline/1",
     "d8_rule_suites_limit_decision_ref": null,
     "ruleset_gap_acknowledgements": [
       {
         "previous_recorded_at": "2026-11-21T21:00:00Z",
         "acknowledged_through": "2027-01-05T00:00:00Z",
         "disposition_ref": {
           "id": "P-09z",
           "source_path": "docs/plans/agentic-research-system/03-decisions-and-open-questions.md",
           "source_commit": "<40-hex-ancestor-of-P1>",
           "entry_sha256": "<64-hex>"
         }
       }
     ],
     "baselines": [
       {
         "baseline_commit": "<40-hex-first-parent-ancestor-of-L1-commit>",
         "recorded_in_decision_ref": {
           "id": "P-09x",
           "source_path": "docs/plans/agentic-research-system/03-decisions-and-open-questions.md",
           "source_commit": "<40-hex-ancestor-of-P1>",
           "entry_sha256": "<64-hex>"
         },
         "detector_closure_blobs": {
           "tools/check_legacy_writes.py": "<40-hex>",
           "tools/check_conventions_legacy_locks.py": "<40-hex>",
           "tools/check_legacy_log_baseline.py": "<40-hex>",
           "tools/run_w9_detector_controls.py": "<40-hex>",
           "tools/run_w9_pinned_detectors.py": "<40-hex>",
           "tools/_w9_detector_evidence.py": "<40-hex>",
           "tools/w9_segmentation.py": "43e1454de09b61e274954c42b21d6ae533857a24",
           ".github/workflows/legacy-write-detector.yml": "<40-hex>",
           "research_system/__init__.py": "41de4e49cfa4bc4e29418bfb59ef0fa9d3c40124",
           "research_system/canonical.py": "98705180cd8201db2456e1290437e5d3b28f82d8",
           "research_system/errors.py": "a50550e3a65e75c7cbc0febe6435efdd982ca138",
           "research_system/legacy/__init__.py": "25552c51ef74c9057f01c68138df6870dc91a7f6",
           "research_system/legacy/accepted_w9.py": "<40-hex>",
           "research_system/legacy/evidence.py": "<40-hex>",
           "research_system/legacy/export_recheck.py": "a90b88fee6290936aea27f9b758e01499893226e",
           "research_system/legacy/reader.py": "8a6cc1ba1684bef77d9a7623712a6e773d9e189c",
           "research_system/legacy/segmentation.py": "d92c4dcfd26f452708cdcc1cbb6d9dde7c9471d6",
           "research_system/store/__init__.py": "83e1969c3f72f1e31e6fa7eb007693746298e669",
           "research_system/store/anchor.py": "bcf9f6c0ded7cd324c0ec737eb976cb3f9498ca5",
           "research_system/store/durability.py": "be598aeb363422336bc376ebdf488fe04872e804",
           "research_system/store/lock.py": "9ccd930d01b6c4f67a9b812987b0faf1ad0f6753",
           "research_system/store/writer.py": "4e6254160249b9c187a3439633995ea0160f6a94"
         },
         "pre_baseline_dispositions_ref": {
           "id": "P-09w",
           "source_path": "docs/plans/agentic-research-system/03-decisions-and-open-questions.md",
           "source_commit": "<40-hex-ancestor-of-P1>",
           "entry_sha256": "<64-hex>"
         }
       }
     ],
     "acknowledged": [
       {
         "commit": "<40-hex>",
         "rule": "Rule 1",
         "path": "papers/P01-A-JRSSA/...",
         "old_blob": "<40-hex>",
         "new_blob": "<40-hex>",
         "disposition_ref": {
           "id": "P-09y",
           "source_path": "docs/plans/agentic-research-system/03-decisions-and-open-questions.md",
           "source_commit": "<40-hex-strictly-after-commit-and-at-or-before-P1-of-C_ack>",
           "entry_sha256": "<64-hex>"
         }
       }
     ]
   }
   ```
   *(All top-level keys are closed and protected by Rule 0.2 (§6.5): `format` is immutable; `d8_rule_suites_limit_decision_ref` is immutable once non-null; `baselines`, `acknowledged`, and `ruleset_gap_acknowledgements` are strictly append-only. `baselines[0]` carries `{"baseline_commit", "recorded_in_decision_ref", "detector_closure_blobs", "pre_baseline_dispositions_ref"}`—where `pre_baseline_dispositions_ref` is a hash-bound register reference (`R4-i6`)—and every appended row `baselines[k]` for $k \ge 1$ carries `{"recorded_in_decision_ref", "detector_closure_blobs"}`. **Blob computation:** because `.gitattributes:14` specifies `* text=auto eol=lf` and `.claude/rules/apm-outputs.md:37` warns against raw `git hash-object <file>` on CRLF working copies, PR authors compute `detector_closure_blobs` entries with `git rev-parse :<path>` (from staged index) or `git hash-object --path=<path> <path>`.)*
2. **Baseline, disposed vs walked intervals, content pin, and loud incompatibility failure (`R5-m1`):**
   - **`baselines[0]["baseline_commit"]` fixes the original walk start** (immutable; any known first-parent ancestor of the L-1 commit on `main`).
   - **Pre-baseline disposed interval `(4b143c92, baselines[0]["baseline_commit"]]`:** At L-1, run §21.1 item 3 over `(dbd54fe3, baselines[0]["baseline_commit"]]` and record every guarded commit's disposition in `pre_baseline_dispositions_ref` (§6.2.1 covers `4b143c92..dbd54fe3`).
   - **Walked interval `(baselines[0]["baseline_commit"], head]`:** Walked once (`1x`) per post-merge run with `baselines[-1]["detector_closure_blobs"]`; every commit passes Rules 0–3 or holds a valid `acknowledged` entry.
   - **CLI lockouts, first-parent chain, and loud exit `2`:** Passing `--baseline`, `--head`, `--pr-map`, `--manifest-file`, `--verdict-json`, or `--acknowledged-from` without `--ruleset-check skip` exits `2` (§6.3 item 4). `check_legacy_writes.py` verifies `baselines[0]["baseline_commit"]` (and referenced commits) in `git --no-replace-objects rev-list --first-parent <head>`. Every WP9.5 tool wraps `main()` to exit **`2`** on any uncaught exception—never `0` and never `1`—so if production evidence formats evolve incompatibly ahead of a pin advance, the pinned tool turns the run red loudly (`R5-m1`).
3. **Clearable true positives: the append-only `acknowledged` list (Owner Point C):**
   - Appended row `{"commit", "rule", "path", "old_blob", "new_blob", "disposition_ref", ...}` (for `rule == "Rule 3"`, also `"independent_review"` matching §6.4 item 2):
     1. `a["commit"]` lies on `<head>`'s first-parent chain strictly after `baselines[0]["baseline_commit"]`.
     2. `a["disposition_ref"]["source_commit"]` satisfies `commit < source_commit <= P1(C_ack)` with `### <id>` slice SHA-256 matching `entry_sha256` at `P1(C_ack)` and naming `commit[:8]`, `rule`, `path`, `old_blob[:8]`, and `new_blob[:8]`.
     3. Scope: exempts only `(commit, rule, path, old_blob, new_blob)`.
     4. **Rule 3 late change-list entry and independent-review requirement:** When `a["rule"] == "Rule 3"`, `a` must also carry `"independent_review"` verified at `P1(C_ack)` per §6.4 item 2 (satisfying `W9` §4.3, `09-migration-compatibility-and-pilot.md:183-188`), **and** `<head>:.research-system/evidence/w9/shared-surface-changes.json` must hold a matching entry `(pr_number_or_null, a["path"], a["old_blob"], a["new_blob"], affected_registrations)` where:
        - `affected_registrations` is **non-empty**, unless `"none derived"` is explicitly stated in **both** the `### P-0xx` slice and `independent_review` (`evidence.py:221-252` permits `[]` structurally, so the detector enforces non-emptiness unless derived);
        - `"pr_number"` equals `pr_number(a["commit"])` for PR merges, or `null` **strictly** for an acknowledgement-backed entry whose `a["commit"]` has `pr_number == None` (direct push; ordinary in-commit Rule 3 PR entries still forbid `null`);
        - *Why late entries work cleanly against WP9.3:* `check_change_list` calls `require_change_list` (`research_system/legacy/evidence.py:190-218`; `acceptance.py:121-136`), which requires the acceptance's declared `git_blob` to equal `shared-surface-changes.json` at `git_head` and `git_commit` to be an ancestor holding it. Thus every acceptance evaluated at or after the late entry's `git_head` enforces it, stale declarations are refused, and previously committed acceptances retain their verdict.
4. **Post-merge walk (`1x`), manual pin-advance comparison evidence, advisory row check, and pre-code walk stop rule (*pin design decided by Stephen, 2026-11-22, to be entered in `P-090` with the other owner points*):**
   - **Post-merge walk (`1x`):** `.github/workflows/legacy-write-detector.yml` and `tools/run_w9_pinned_detectors.py` assemble only `baselines[-1]["detector_closure_blobs"]` and execute **one** walk over `(baselines[0]["baseline_commit"], head]`.
   - **Old-vs-new comparison procedure (review evidence attached to pin-advance PR, not a gate; no new tool file):** Applies when appending `baselines[k]` ($k \ge 1$); L-1 row `0` creation checks Rule 0.2 (i)–(iv) with no prior comparison. Assemble `baselines[k-1]` (`T_old`) and `baselines[k]` (`T_new`) via §6.2.3's confined `python -S -P` assembly, run `check_legacy_writes.py --repo-root . --ruleset-check skip --baseline <b0> --head <candidate> --verdict-json --acknowledged-from <pr_base>` on each (all tool versions keep this interface or document changes in `### P-0xx`; offline tests pass `--pr-map`), diff outputs, and attach to the PR.
     - **Complete verdict & failure semantics:** Verdict on `V` in `(baselines[0]["baseline_commit"], candidate]` under tool `t` is the `(rule, path)` set reported after `<pr_base>` `acknowledged` rows—**including Rule 0** (`("Rule 0.1", path)`, `("Rule 0.2", path)`; no Rule 0.3 or Rule 0.2 (v), so nothing nests). `--verdict-json` emits **one** JSON object carrying `"error"` on failure (exit `2`); **any `ERROR` on either side—including identical `ERROR` on both tools—is `ERROR`**, never clean.
     - **Per-line slice & same-PR `acknowledged`:** List each differing `(V, rule, path)` on its own line in `recorded_in_decision_ref`'s `### P-0xx` slice as `V[:8] | <rule> | <path>`. Green-to-red Rules 1–3 differences needing clearing must carry `acknowledged` in the **same PR** (Rule 0 changes cannot use `acknowledged`, §6.5, and fail review unless resolved or exempted under Owner Point C).
   - **No PR-time pin-advance gate in `admission-controls`:** Runs no `HEAD` blob check, gating row check, verdict comparison, or `gh` call; Rule 0.2 (i)–(iv) on added rows may emit an **advisory** report labelled advisory.
   - **Measured `1x` stand-ins & pre-code walk stop rule (§12.3, §15.2 item 5, §21.1 item 10):** Local 6-subprocess `1x` walk stand-ins: **`14.05s`** (60 commits, 6 guarded), **`34.46s`** (178, 12 guarded), **`62.84s`** (320, 22 guarded), with ~15% variance (R5: `11.79s`/`34.85s`/`61.58s` + `~11.3s` across 22 live `gh api` calls) and no full Python rule eval; manual 2-tool comparison takes ~2x (`24.04s` measured `2x` at 60 commits; `68.92s` and `125.68s` **extrapolated as `2 × 1x`**). **Pre-code / rehearsal stop rule (§15.2 item 5):** if one post-merge `1x` walk with real rules and `gh api` exceeds **`600s` (10 min)**, stop and return to Stephen for a **design amendment** (e.g. a hash-bound baseline-epoch advancement row or Git batching), not a runtime flag (`UNVERIFIED-5`, §15.1, §21.2).

#### 6.2.3 Detector import closure, stdlib-only isolation, no-lockstep trade-off, and operator-machine pinning

1. **Deterministic AST closure & 22-blob map (`compute_detector_import_closure(repo_root, entry_scripts)` in `tools/_w9_detector_evidence.py`, **new**):**
   Walks `ast.Import`/`ast.ImportFrom` (`research_system` and `tools`, including ancestor `__init__.py` files; `tools/` is a namespace package) across the **6** runtime `tools/` scripts (`check_legacy_writes.py`, `check_conventions_legacy_locks.py`, `check_legacy_log_baseline.py`, `run_w9_detector_controls.py`, `run_w9_pinned_detectors.py`, `_w9_detector_evidence.py`) plus **15** existing `dbd54fe38` modules (§6.2.2) = **21** runtime modules, plus `.github/workflows/legacy-write-detector.yml` = **22 blobs** (`pyproject.toml`, `uv.lock`, and M-6 `tools/export_w9_registration_manifest.py` omitted; §2.3, §13.2 `HR-7`).
2. **Stdlib-only enforcement, Windows-hardened assembly, and `python -S -P` isolation (§21.1 item 9):**
   - `test_detector_closure_is_stdlib_only` checks all 21 runtime modules import only `sys.stdlib_module_names | {"research_system", "tools"}` (all 15 existing have 0 third-party imports); `test_recorded_detector_import_closure_covers_ast_walk`, `test_pinned_wrapper_is_self_contained_stdlib_only` (wrapper imports no `tools.*`/`research_system.*`), and `test_derived_closure_tools_and_accepted_w9_are_codeowned` (Owner Point I `w9_segmentation.py` choice) enforce closure completeness and CODEOWNERS.
   - Before writing into `$DETECTOR_DIR`, §10.2 and `run_w9_pinned_detectors.py` validate `PurePosixPath(rel_path).as_posix() == rel_path` (no leading `/`, `\`, `:`, `..`, `.`, trailing `.`/space, or Windows reserved names `CON`, `PRN`, `AUX`, `NUL`, `COM1`–`9`, `LPT1`–`9`), verify `git cat-file -t <blob_sha> == "blob"` and `dest.resolve().is_relative_to(detector_dir.resolve())`, then verify `dest.is_file()` and `git --no-replace-objects hash-object --no-filters <dest> == blob_sha`.
   - Runs under cleared `PYTHONHOME`/`VIRTUAL_ENV`, `PYTHONPATH="$DETECTOR_DIR"`, `PYTHONSAFEPATH=1`, and `python -S -P "$DETECTOR_DIR/tools/<script>.py"` (`3.13.x` Recommended vs `3.13.5`, §16.1; not `-I`/`-E` which ignore `PYTHONPATH`), spawning every child explicitly as `[sys.executable, "-S", "-P", ...]` so neither checkout modules nor `site-packages` enter child `sys.path` (§21.1 item 9).
3. **No-lockstep lag trade-off (`2026-11-22` decision):** Non-code-owned closure edits need no `baselines` append; head's `baselines[-1]` stays safely pinned until Stephen advances it (or fails loudly with exit `2` on format incompatibility).
4. **Operator-machine wrapper (`tools/run_w9_pinned_detectors.py`):** Self-contained stdlib-only file run directly from `origin/main` before every batch and weekly D-5 run (`06v:603-604`):
   ```bash
   git fetch --no-tags origin main:refs/remotes/origin/main
   git --no-replace-objects show refs/remotes/origin/main:tools/run_w9_pinned_detectors.py | python -S -P - --repo-root .
   ```
   Verifies `origin/main == git ls-remote origin refs/heads/main`, checks `W9_DETECTOR_PIN` via `gh api` (`encoding="utf-8"`) under I3 (`UNVERIFIED-4`), writes the 22 confined blobs with post-write `git hash-object --no-filters`, and launches `[sys.executable, "-S", "-P", ...]` for the 3 detectors and `run_w9_detector_controls.py --code-root "$DETECTOR_DIR" --repo-root . --verify-watched-to-fail ...`. (`export_w9_registration_manifest.py` runs unpinned in CODEOWNERS; `HR-7`.)

---

### 6.3 First-parent diff semantics, PR mapping, and failure modes

1. **Refusing shallow clones and non-first-parent baselines:**
   - `git --no-replace-objects rev-parse --is-shallow-repository` must equal `"false"` (matching `research_system/legacy/acceptance.py:89-90`).
   - `<baseline>` must lie on `<head>`'s first-parent chain (§6.2.2).
2. **Computing the first-parent diff for both 1-parent and 2-parent commits:**
   - For each commit `C` in `git --no-replace-objects rev-list --first-parent --reverse <baseline>..<head>`:
     - Query `git --no-replace-objects rev-list --parents -n 1 <C>`, yielding `<C> <P1> [<P2> ...]`.
     - Run `git --no-replace-objects diff-tree -r --no-renames -z <P1> <C>`.
     - Each NUL-delimited record yields `(old_mode, new_mode, old_blob, new_blob, status, path)`.
     - **Why explicit `<P1> <C>` is required:** Single-argument `git diff-tree -r <C>` prints nothing on a 2-parent merge commit (verified on `b132406e` in `wp9-5-note-r1-review-2026-11-21.md:299`); passing `<P1> <C>` compares `main`'s previous tree at `P1` against `C`'s tree for both 1-parent and 2-parent commits.
     - **Mode-only changes:** If a guarded file appears in `diff-tree -r --no-renames -z <P1> <C>` with `old_blob == new_blob` and `old_mode != new_mode`, it still enters Rule 1/2/3 evaluation; because `legacy-write-records.json` requires `old_blob != new_blob` (§6.4), a mode-only change **fails closed** (`ERROR: post_merge_first_parent: mode-only change on guarded path '<path>' at commit <C> (<old_mode> -> <new_mode>) is prohibited`).
3. **Mapping each first-parent commit `C` to its PR:**
   - When commit `C` touches at least one guarded path (Rule 0, Rule 1, Rule 2, or Rule 3):
     1. **Primary lookup (`commits/<C>/pulls` with retry and backoff):** Calls `gh api repos/ZK-Theory/TDL/commits/<C>/pulls`, retrying up to 3 times (`1s`, `2s`, `4s`) if HTTP 200 has no PR with `pull.get("merged_at") and pull.get("merge_commit_sha") == C`.
     2. **Subject-hinted fallback lookup (`pulls/<N>` verified by `merge_commit_sha == C`):** If retries still find no match, parses trailing `(#<N>)` or `^Merge pull request #(<N>) `, queries `gh api repos/ZK-Theory/TDL/pulls/<N>`, and accepts `<N>` **iff** `pull.get("merged_at")` is non-empty **and** `pull.get("merge_commit_sha") == C` (so `5df0c001`, whose subject reuses `#215` merged at `a426b731`, maps to `pr_number = None`).
     3. **API failure vs unmapped commit:** API/transport/JSON errors exit **`2`** (`ERROR: post_merge_first_parent: GitHub API read failed while mapping commit <C>: <stderr_or_status>`); HTTP 200 with no matching merged PR sets `pr_number = None` and exits **`1`** (`pr=none`).
     4. **Test-only flags hard-locked behind `--ruleset-check skip`:** `--baseline <sha>`, `--head <sha>`, `--pr-map <json>`, `--manifest-file <json>`, `--verdict-json`, and `--acknowledged-from <sha>` are test/manual-comparison overrides only. Passing any of them without `--ruleset-check skip` exits **`2`** immediately (`ERROR: post_merge_first_parent: --baseline, --head, --pr-map, --manifest-file, --verdict-json, and --acknowledged-from are permitted only with --ruleset-check skip`), and a unit test verifies none of `--baseline`, `--head`, `--pr-map`, `--manifest-file`, `--verdict-json`, `--acknowledged-from`, `--ruleset-check skip`, or `--classified-locks` appears in `.github/workflows/legacy-write-detector.yml`.
4. **Explicit UTF-8 subprocess decoding and `main()` exit-`2` exception wrapper (`R5-m1`, `R5-m9`):**
   - Every `git` and `gh` subprocess invocation across all WP9.5 tools passes `encoding="utf-8"` explicitly (matching `tools/check_bypass_merges.py:160`, avoiding Windows ANSI `charmap` `UnicodeDecodeError`).
   - Every WP9.5 tool wraps `main()` to catch any uncaught exception and exit **`2`** (`ERROR`, never `0` and never `1`), printing a clear `ERROR: ...` diagnostic—and with `--verdict-json`, `tools/check_legacy_writes.py` always prints **one** JSON object on stdout carrying an `"error"` key on failure.

---

### 6.4 The W9 §4.2 record: format, evaluation at `C`, and provenance verification at `P1`

- **Location:** `.research-system/evidence/w9/legacy-write-records.json` (format `"w9-legacy-write-records/1"`, added as a dated row in `06v-addendum-2026-11-10-w9-paths.md` under Owner Point B).
- **Evaluated at `C`:** When commit `C` (with first parent `P1`, mapped to `pr_number`) touches a guarded path, the detector reads `<C>:.research-system/evidence/w9/legacy-write-records.json`.
- **Provenance checks and conditional reliance on Owner Point I1:**
  `P1` ancestry proves only pre-PR age (that a referenced decision entry or review existed on `main` before PR `C`), **not** Stephen's authorship, because `03-decisions-and-open-questions.md` and `docs/plans/agentic-research-system/reviews/` are not CODEOWNED and ruleset `20822054` has `required_approving_review_count: 0`. Therefore, **Option B1's tamper resistance is conditional on Owner Point I1** (`@stephendor` over `.research-system/evidence/w9/`), and requiring `source_commit`/`review_commit` to precede `C` (`at P1`) is this note's stricter reading of W9 §4.2(b) (`09-migration-compatibility-and-pilot.md:174-176`; Option B2 is the same-PR alternative under I1).
  1. **Pre-existing owner decision (`owner_note` verified at `P1`):** For `"repo_wide_change_4_2_b"`, `"owner_ruling_4_2_c"`, and `"shared_surface_4_3"`, checks `decision_entry_id` (`^P-[0-9]{3}[a-z]?$`), `source_path`, `is_ancestor(repo_root, source_commit, P1)`, and exact `### P-0xx` slice `entry_sha256` naming `normalized_path`, `old_blob[:8]`, and `new_blob[:8]` for every `record["files"]` item (matching `fecfc1da`, `6024-6088`).
  2. **Pre-existing independent review bound to the change (`independent_review` verified at `P1`):** For `"repo_wide_change_4_2_b"` and `"shared_surface_4_3"`, checks `review_path` (`docs/plans/agentic-research-system/reviews/<file>.md`), `is_ancestor(repo_root, review_commit, P1)`, `review_sha256` against `<P1>:<review_path>`, and presence of `decision_entry_id` plus every `(normalized_path, old_blob[:8], new_blob[:8])` inside that review.
  3. **CODEOWNERS / Rule 0 protection (Owner Point I1, §16.1):** Owner Point I1 adds `.research-system/evidence/w9/`, `.github/workflows/legacy-write-detector.yml`, all 7 WP9.5 `tools/` detector/control/exporter/wrapper/helper modules, `tests/tools/test_w9_detectors.py`, and `research_system/legacy/accepted_w9.py` to `.github/CODEOWNERS` (`@stephendor`).
- **Closed JSON schema (`w9-legacy-write-records/1`):**
  ```json
  {
    "format": "w9-legacy-write-records/1",
    "records": [
      {
        "pr_number": 512,
        "allowance_kind": "repo_wide_change_4_2_b",
        "owner_note": {
          "author": "stephendor",
          "decision_entry_id": "P-099",
          "source_path": "docs/plans/agentic-research-system/03-decisions-and-open-questions.md",
          "source_commit": "dbd54fe382e7b2849d3f2038393cbdb4d709477b",
          "entry_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        },
        "independent_review": {
          "reviewer_id": "independent-reviewer-session",
          "review_path": "docs/plans/agentic-research-system/reviews/pr512-semantic-equivalence-review.md",
          "review_commit": "dbd54fe382e7b2849d3f2038393cbdb4d709477b",
          "review_sha256": "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"
        },
        "files": [
          {
            "normalized_path": "papers/P01-A-JRSSA/drafts/sections/compute_table1_effects.py",
            "old_blob": "1111111111111111111111111111111111111111",
            "new_blob": "2222222222222222222222222222222222222222"
          }
        ]
      }
    ]
  }
  ```

---

### 6.5 Rules 0, 1, 2, and 3 of `tools/check_legacy_writes.py`

For each first-parent commit $C \in (\text{baselines}[0][\text{"baseline\_commit"}], \text{head}]$ with first parent $P_1$ and changed file tuples $(m_{\text{old}}, m_{\text{new}}, b_{\text{old}}, b_{\text{new}}, \text{status}, p) \in \text{diff-tree}(P_1, C)$:

#### Rule 0 — Monotonicity of W9 evidence files and governed closure

1. **`registration-manifest.json` is strictly append-only:**
   Every entry present at $P_1$ remains present with identical fields at $C$; otherwise fail closed (`ERROR: post_merge_first_parent: Rule 0 violation at commit <C>: registration-manifest.json deleted or modified existing registration entry <entry>`).
2. **Evidence ledgers, all top-level fields + rows of `walk-baseline.json`, and L-0b classification:**
   - `legacy-write-records.json`, `shared-surface-changes.json`, and `vault-detector-runs.json` are strictly append-only on entries: every entry at $P_1$ stays byte-identical at $C$, and any new `legacy-write-records.json` entry at $C$ has `entry["pr_number"] == pr_number(C)`.
   - Top-level fields of `walk-baseline.json` are governed: `format` (`"w9-walk-baseline/1"`) is immutable; `d8_rule_suites_limit_decision_ref` is immutable once non-null and any non-null value passes the `P1` hash-bound check naming `"D-8"` and `"rule-suites"`; `baselines`, `acknowledged`, and `ruleset_gap_acknowledgements` are strictly append-only.
   - **Row 0 at creation and every appended `baselines[k]` ($k \ge 1$) must satisfy checks (i)–(iv)** (evaluated at the creating commit `C_0` when `walk-baseline.json` first appears—with `C_0`'s first parent `P1(C_0)`—and at `C_k` for each appended `k >= 1`):
     (i) closed keys: `{"baseline_commit", "recorded_in_decision_ref", "detector_closure_blobs", "pre_baseline_dispositions_ref"}` on row `0`, or `{"recorded_in_decision_ref", "detector_closure_blobs"}` on row $k \ge 1$ (no second `baseline_commit`);
     (ii) every entry `(p, expected_blob)` in `row["detector_closure_blobs"]` equals `git --no-replace-objects rev-parse <C>:<p>`;
     (iii) `row["recorded_in_decision_ref"]` (and `row["pre_baseline_dispositions_ref"]` on row `0`) passes the pre-existing (`source_commit` ancestor of $P_1(C)$) hash-bound slice check; and
     (iv) for $k \ge 1$, the `recorded_in_decision_ref` `### P-0xx` slice names every path added, removed, or changed relative to `baselines[k-1]["detector_closure_blobs"]` with `new_blob[:8]` (or `"no blob change"` if identical, and `"rollback"` plus restored paths and `new_blob[:8]` if matching an earlier row), and lists every old-vs-new verdict difference (including Rule 0) one per line as `V[:8] | <rule> | <path>` (§6.2.2 item 4; any Rules 1–3 green-to-red difference cleared on `main` carries an `acknowledged` row in the same PR).
   - **Every newly appended `ruleset_gap_acknowledgements` row ($C_{\text{gap}}$):** closed keys `{"previous_recorded_at", "acknowledged_through", "disposition_ref"}`, `disposition_ref["source_commit"]` ancestor of $P_1(C_{\text{gap}})$, slice naming both `<previous_recorded_at>` and `<acknowledged_through>`.
   - **Every newly appended `acknowledged` row ($C_{\text{ack}}$):** `commit < source_commit <= P1(C_ack)` with slice verification (§6.2.2 item 3); when `rule == "Rule 3"`, also requires `independent_review` at `P1(C_ack)` plus a matching entry (non-empty `affected_registrations` or `"none derived"`, `pr_number` integer or `null` if unmapped) at `<head>:.research-system/evidence/w9/shared-surface-changes.json` (§6.2.2 item 3.4).
   - Once `ACCEPTED_CONVENTIONS_CLASSIFICATION` (`accepted_w9.py`) is populated at L-0b, its pinned classification JSON path cannot be modified or deleted.
   - Failure message: `ERROR: post_merge_first_parent: Rule 0 violation at commit <C>: evidence file '<path>' violated append-only, validation, or immutability invariants`
3. **`detector-controls.json` monotonicity:**
   - Once `.research-system/evidence/w9/detector-controls.json` exists at $P_1$, it cannot be deleted at $C$, and updates pass `require_detector_controls` (`evidence.py:133-154`) with `recorded_at` timestamps $\ge$ $P_1$. *(Lockstep Rule 0.3 is deleted per Stephen's 2026-11-22 decision: editing a closure module without appending a `baselines` row is not a violation; §6.1.)*

#### Rule 1 — Registered `git_tracked` legacy files (`06v:477`; `W9:172-181`)

- **Manifest evaluated at `P1` (union `C`):** Let $\mathcal{M}(P_1, C) = \text{Manifest}(P_1) \cup \text{Manifest}(C)$ be the set of registration entries present in `registration-manifest.json` at $P_1$ or at $C$.
- **Exclusions from Rule 1:** An entry $r \in \mathcal{M}(P_1, C)$ is excluded if: (1) `r["root_kind"] != "repository_root"`; (2) `r["source_identity_kind"] != "git_tracked"`; (3) `r["role"] == "conventions_lock"` (§7); (4) `r["role"] == "shared_enforcement_surface"` (Rule 3); (5) `r["role"] == "successor_results_root"` (`results/ars/`); or (6) `r["role"] == "legacy_read_only_projection"`.
- **Path matching rule:** Exact case-folded match (`r["role"] != "legacy_manuscript_root"`), or directory-prefix match (`papers/P01-A-JRSSA/`, `papers/P01-B-JRSSB/`, `reader.py:51,289-299`).
- **`.apm/tracker.md` Working Notes handling (Owner Point H, §16.9):** Under Option H1 (Recommended), passes Rule 1 iff `check_tracker_working_note_append(raw_P1, raw_C)` via `segment(raw, "tracker_task_row")` and `segment(raw, "working_note_entry")` (`segmentation.py:470-473`) confirms identical bytes outside `## Working Notes`, all prior entries preserved verbatim in order with 0 blockers, and only `[ \t]*\n` separators (`+1`-byte separator verified on `452352ff`, `e3519ba7`, `a6a98966` in `wp9-5-note-r2-review-2026-11-21.md:219`). Under H2/H3, follows that option.
- **Requirement for all other Rule-1 matches:** Unless exempted by `acknowledged` covering `(C, "Rule 1", p, b_old, b_new)` (§6.2.2 item 3), commit $C$ requires mapped `pr_number`, `b_old != b_new`, and a valid `P1`-provenance §4.2 record at $C$ (§6.4). Failure (exit `1`):
  `ERROR: post_merge_first_parent: Rule 1 violation at commit <C> (pr=<pr_or_none>): registered path '<p>' changed (<b_old> -> <b_new>) without a valid in-commit W9 §4.2 record`

#### Rule 2 — Any path under `results/` outside `results/ars/` (`06v:478`; `W9-D13`, `W9-D14`, `W9:140-147,196`)

- **Matching & hard-coded `results/ars/` exemption:** Case-folded path starts with `"results/"` and not `"results/ars/"` (exempting `"results/ars/"` directly per `W9-D14` `09-migration-compatibility-and-pilot.md:768` so unregistered legacy families under `results/`—`W9-D13`, `:767`—stay guarded before `results/ars/` is registered). Requires valid §4.2 record at $C$ (or `acknowledged`); otherwise exit `1`:
  `ERROR: post_merge_first_parent: Rule 2 violation at commit <C> (pr=<pr_or_none>): results path outside results/ars/ '<p>' changed (<b_old> -> <b_new>) without a valid in-commit W9 §4.2 record`

#### Rule 3 — `shared_enforcement_surface` contracts (`06v:212,479-481`; `O-32`; `W9` §4.3, `W9:183-190`; Owner Point D)

- **Shared surfaces:** `{r["normalized_path"] for r in M(P1, C) if r["root_kind"] == "repository_root" and r["role"] == "shared_enforcement_surface"}` (e.g. `contracts/manifests/research-assurance.yaml`, `contracts/stochastic-tests/monte-carlo-permutation-p-value.yaml`, `contracts/stochastic-tests/markov-order-provenance.yaml`, `contracts/topology-invariants/null-operation-changes-ph-input.yaml`; `W9:166`).
- **Requirements:** Unless exempted by a valid Rule 3 `acknowledged` row + `independent_review` + matching entry (`pr_number` or ack-only `null`, non-empty `affected_registrations` or `"none derived"`) in `<head>:shared-surface-changes.json` (§6.2.2 item 3.4): (1) mapped `pr_number` + `shared_surface_4_3` record with `owner_note` & `independent_review` at $P_1$; (2) matching entry in `<C>:shared-surface-changes.json`.
- **Resolving `O-32` (`06v:90-91` vs `evidence.py:231-238`, `acceptance.py:135`; §16.5):** Option D1 (`base_commit`) is race-prone under the merge queue; Option D2 (two PRs) leaves a red window. **Option D3 (Recommended, `"w9-shared-surface-changes/2"`, uniform `/2` with Option A1)** closes entries on `{"pr_number", "surface", "old_blob", "new_blob", "affected_registrations"}` (where `pr_number` is an integer for in-commit PR entries and `null` only for ack-backed unmapped commits, §6.2.2 item 3.4); in `acceptance.py:121-136` (`check_change_list`), an affected observation at `obs_commit` passes iff `evidence.blob_at(repository_root, obs_commit, entry["surface"])` (`evidence.py:179-188`) equals `entry["new_blob"]` or a later `new_blob` for `surface` *(tree-state equivalence semantic; revert cycles `A -> B -> A` noted in `HR-2`)*.
- **Failure message (exit `1`):**
  `ERROR: post_merge_first_parent: Rule 3 violation at commit <C> (pr=<pr_or_none>): shared_enforcement_surface '<s>' changed (<b_old> -> <b_new>) without a valid in-commit shared-surface-changes.json entry and W9 §4.3 owner note`

---

### 6.6 What `tools/check_legacy_writes.py` does with an unreadable registered file or unmappable commit

1. **Missing or malformed evidence files:**
   - If `walk-baseline.json` or `registration-manifest.json` is absent or malformed at `<head>` (once L-1 is active or when `--require-manifest` is set), or if any evidence file present at $P_1$ or $C$ fails JSON/schema validation, `tools/check_legacy_writes.py` fails closed (exit `1`) with `ERROR: post_merge_first_parent: invalid evidence file at <commit>:<path>: <reason>`.
2. **Scope of the Git tree existence check at `<head>` (`R1-M4`):**
   - For every entry $r$ in `registration-manifest.json` at `<head>`:
     - If `r["root_kind"] == "vault_root"` or `r["source_identity_kind"] in {"untracked_file", "restricted_untracked_file"}` or `r["role"] in {"successor_results_root", "legacy_read_only_projection"}`:
       **Do not** run `git cat-file` on `<head>:<normalized_path>`. Untracked and restricted repository registrations (`*.csv`, `*.pkl`, `.apm/memory/stage-NN/` logs, `.apm/bus/`, and `.research-system/projections/legacy/`) and vault files live outside Git; `results/ars/` (`successor_results_root`) is an output directory that need not exist in Git before the first successor result is committed. Untracked and vault registrations are checked handle-bound on the operator machine at `LR-015` (`prepare_observation`, `research_system/legacy/preparers.py:1221`), `LR-016`/`LR-020` (`reread_items`, `research_system/legacy/acceptance.py:60-79`), and by `tools/check_legacy_log_baseline.py`.
     - If `r["root_kind"] == "repository_root"` and `r["source_identity_kind"] == "git_tracked"` and `r["role"] != "successor_results_root"`:
       - If `r["role"] == "legacy_manuscript_root"` (directory path ending in `/`, e.g. `papers/P01-A-JRSSA/`): verify `git --no-replace-objects cat-file -t <head>:<normalized_path_trimmed> == "tree"`.
       - Otherwise (a `git_tracked` file registration): verify `git --no-replace-objects cat-file -t <head>:<normalized_path> == "blob"`.
       - If missing or wrong object type at `<head>`, fail closed (exit `1`) with:
         `ERROR: post_merge_first_parent: git_tracked registered path '<normalized_path>' (role=<role>) is missing or not a <blob|tree> at <head>`
3. **Unmappable commit:**
   - As specified in §6.3 item 3, if GitHub API lookup fails with a transport/HTTP error, exit **`2`**; if the commit has no merged PR with `merge_commit_sha == C`, `pr_number` is `None` and Rules 0–3 fail closed with exit **`1`**.

---

## 7. The `CONVENTIONS.md` legacy-lock check (`tools/check_conventions_legacy_locks.py`)

### 7.1 Authority and verified baseline constants

- **Authority:** `W9` §4.4 (`09-migration-compatibility-and-pilot.md:198`), `W9` §5.5 (`:302-304`), `W9` §7.3 items 1–5 (`:385-417`), `06v` §3 row `O-12` (`06v-w9-implementation-plan.md:192`), `06v` §4 row `W9-T19` (`:242`), and `w9-segmentation-contract-v1.md` §3 and §8 (`w9-segmentation-contract-v1.md:83-138,244`).
- **Pinned baseline constants (`CONVENTIONS_LOCK` in `research_system/legacy/reader.py:43-49`):**
  - `repository_path`: `"CONVENTIONS.md"`
  - `git_commit`: `"4b143c9225035cc29e37351445f1c3a4ab09ceb1"`
  - `git_blob`: `"4620c71607ca3a06c6df3b8e96a6bddffc783960"`
  - `byte_length`: `33645`
  - `sha256`: `"d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589"`
- **Interaction with `role == "conventions_lock"` in Rule 1 (`R1-M5`):**
  Under `W9` §7.3 (`09-migration-compatibility-and-pilot.md:416-417`), `CONVENTIONS.md` is registered at its repository path with `role: "conventions_lock"`. As settled in §6.5 Rule 1 exclusion 3, `tools/check_legacy_writes.py` excludes `role == "conventions_lock"` from Rule 1 (so pure insertions of successor units into `CONVENTIONS.md` do not require a W9 §4.2 record) and delegates `CONVENTIONS.md` enforcement to `tools/check_conventions_legacy_locks.py`.

### 7.2 What it reads

1. **Baseline bytes:**
   - Reads `CONVENTIONS.md` from Git blob `4620c71607ca3a06c6df3b8e96a6bddffc783960` (`4b143c9225035cc29e37351445f1c3a4ab09ceb1:CONVENTIONS.md`) via `git --no-replace-objects cat-file blob 4620c71607ca3a06c6df3b8e96a6bddffc783960` (or from `--baseline-file <path>` in unit tests).
   - Verifies `len(baseline_raw) == 33645`, `git_blob_id(baseline_raw) == "4620c71607ca3a06c6df3b8e96a6bddffc783960"`, and `sha256_hex(baseline_raw) == "d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589"` (`research_system/legacy/reader.py:43-49,75-77`).
2. **Candidate bytes:**
   - By default, reads `CONVENTIONS.md` from `repository_root` via `handle_bound_read(repository_root, "CONVENTIONS.md")` (`research_system/legacy/reader.py:140-206`), or from `--candidate-file <path>` / `--git-ref <ref>:CONVENTIONS.md`.
3. **Segmentation (`R1-M2`):**
   - Calls `segment(baseline_raw, "conventions_unit")` and `segment(candidate_raw, "conventions_unit")` from `research_system/legacy/segmentation.py:429-488` and `tools/w9_segmentation.py:461-518`, asserting exact dict equality between the runtime segmenter and the reference segmenter.

### 7.3 Verified unit counts at `4b143c92` (`4620c716`) vs `dbd54fe3` and classification source

Direct execution of `segment(raw, "conventions_unit")` on `4620c716` (`4b143c92:CONVENTIONS.md`, 33,645 bytes, 575 lines) and on `dbd54fe3:CONVENTIONS.md` (51,774 bytes, 822 lines, SHA-256 `2ce15910d2f6712e2d4311578ebe8a5b6e7b1f83086c1c5483ea4876636ff97c`) gives the following exact per-section unit counts (Appendix A §21.1):

| `## ` Section (`anchor_text`) | Units at `4b143c92` (`4620c716`) | Units at `dbd54fe3` (`HEAD`) | Baseline units preserved in order? | Inserted successor units at `dbd54fe3` | Provisional section class (`W9` §7.3 items 1 & 4) |
|---|---|---|---|---|---|
| `Research Assurance (locked 2026-06-02)` | 3 | 3 | Yes (3/3) | 0 | Legacy-lock section |
| `APM Prose Production Frozen — ARS Transition (locked 2026-07-17)` | 2 | 2 | Yes (2/2) | 0 | Legacy-lock section (or per-unit classified at L-0b; Owner Point J) |
| `Repo-Wide CI: Windows Only, Lint Blocks (locked 2026-09-08, amended 2026-09-11)` | 0 *(absent at `4b143c92`)* | 6 | N/A (post-freeze section) | 6 (in new section) | Successor section |
| `Authorship` | 5 | 5 | Yes (5/5) | 0 | Legacy-lock section |
| `Programme Structure (as of 2026-04-07)` | 4 | 4 | Yes (4/4) | 0 | Legacy-lock section |
| `Always` | 24 | 24 | Yes (24/24) | 0 | Legacy-lock section |
| `Never` | 13 | 13 | Yes (13/13) | 0 | Legacy-lock section |
| `Methodological Conventions` | 6 | 6 | Yes (6/6) | 0 | Legacy-lock section |
| `Citation Conventions` | 3 | 3 | Yes (3/3) | 0 | Legacy-lock section |
| `ARS Foundation Governance` | 2 | 9 | Yes (2/2) | 7 (in successor section) | Wholly successor section (`W9:388-390,405-407`) |
| `Computational Environment` | 8 | 15 | Yes (8/8) | **7** (in legacy-lock section) | Legacy-lock section |
| **Total** | **70 units** (10 sections) | **90 units** (11 sections) | **All 70 preserved** | **7 inserted inside the 9 legacy sections** (+7 in `ARS Foundation Governance`, +6 in `Repo-Wide CI`) | **68 units** in the 9 legacy sections; **2 units** in `ARS Foundation Governance` |

**Provisional 9-section partition vs L-0b pinned classification (`R1-M9`, `R2-M4`, `R2-m3`; Owner Point J, §16):**
- `W9` §7.3 item 1 (`09-migration-compatibility-and-pilot.md:385-393`) states that the legacy set is decided by object, then date, and that *"The baseline observer lists every entry and lock with its classification; an entry it cannot classify is a blocker, and Stephen accepts the list."* And `06v:593` (row `L-0b`) records *"the `CONVENTIONS.md` baseline recorded"*.
- Until L-0b's classified list is accepted by Stephen, treating all `68` baseline units across the 9 non-`ARS Foundation Governance` sections as legacy locks is the **strictest (conservative) provisional rule**: every single one of those 68 units (and indeed all 70 baseline units, including the 2 baseline units in `ARS Foundation Governance`) is currently preserved byte-for-byte at `dbd54fe3`.
- **Pinning the L-0b classification exactly like `ACCEPTED_CL_EXPORT` (`R2-M4`, `research_system/legacy/accepted_w9.py:86-88`):**
  Leaving the L-0b classification file unpinned or reading it from `<head>` would let a PR reclassify a legacy unit to `"successor"` and edit that unit in the same commit! Therefore, `research_system/legacy/accepted_w9.py` defines `ACCEPTED_CONVENTIONS_CLASSIFICATION: tuple[MappingProxyType[str, Any], ...] = ()` (empty before L-0b, populated by the L-0b PR with `{"repository_path", "git_commit", "git_blob", "sha256", "byte_length"}`).
  - While `ACCEPTED_CONVENTIONS_CLASSIFICATION == ()`, `tools/check_conventions_legacy_locks.py` enforces the conservative 9-section (`68`-unit) partition.
  - Once L-0b populates `ACCEPTED_CONVENTIONS_CLASSIFICATION`, `tools/check_conventions_legacy_locks.py` reads the closed `"w9-conventions-classified-locks/1"` JSON from Git **only at `ACCEPTED_CONVENTIONS_CLASSIFICATION[-1]["git_commit"]:repository_path`** (never `<head>` or the working tree), verifies `git_blob_id`, `sha256_hex`, and `len(raw)`, indexes units by the actual `conventions_unit` unique key `(anchor_text, unit_hash)` (`research_system/legacy/segmentation.py:391-402`) with 1-based `unit_ordinal` per section (`:390,398`), and verifies coverage of all 70 baseline units. The workflow passes **no** `--classified-locks` flag; `--classified-locks` is a test-only override that exits **`2`** unless `--candidate-file` is also passed (`R2-M4`), and the L-0b classification file is protected by Rule 0 item 2 (`§6.5`).

### 7.4 Exact insertion-only decision rule and structural/table edge cases

Given baseline segmentation $S_{\text{base}}$ (from blob `4620c716`) and candidate segmentation $S_{\text{cand}}$:

1. **File-level encoding invariants:**
   - `S_cand["file_facts"]["has_utf8_bom"]` must be `False` and `S_cand["file_facts"]["line_ending"]` must be `"LF"` (`.gitattributes:14` enforces `* text=auto eol=lf` across the repository). Otherwise fail closed with `ERROR: conventions_repository_check: file encoding/EOL violation`.
2. **Zero blocker rows (`R2-m3`):**
   - Neither $S_{\text{base}}$ nor $S_{\text{cand}}$ may contain any row with `row_kind == "blocker"` (e.g. `duplicate_anchor` within a section). Otherwise fail closed with `ERROR: conventions_repository_check: segmentation blocker at lines <start_line>-<start_line + line_count - 1>: <blocker_reason>`.
3. **Legacy-lock section preservation (in order):**
   - Every section title $s \in \mathcal{L}$ (the 9 legacy-lock sections, or sections holding at least one `"legacy"` unit under `ACCEPTED_CONVENTIONS_CLASSIFICATION`) must appear in $S_{\text{cand}}$, and their first appearances in $S_{\text{cand}}$ must preserve their baseline relative order $s_1, \dots, s_m$. Otherwise fail closed with:
     `ERROR: conventions_repository_check: legacy section '<s>' is missing, renamed, or reordered`
4. **Per-section ordered-subsequence preservation of legacy units (`R2-m3`):**
   - For each legacy-lock section $s \in \mathcal{L}$, let $B(s) = [h_1, \dots, h_m]$ be the ordered baseline `unit_hash` (`== raw_row_sha256` on `conventions_unit`, `research_system/legacy/segmentation.py:398,420`) values of legacy units in section $s$, and let $C(s) = [u_1, \dots, u_n]$ be the ordered candidate `unit_hash` values in section $s$.
   - Every $h_j \in B(s)$ must exist in $C(s)$ (if missing, fail closed with `ERROR: conventions_repository_check: legacy unit modified or deleted in section '<s>' (baseline row_ordinal=<row_ordinal>, unit_ordinal=<unit_ordinal>, expected unit_hash=<h_j>)`), and their indices in $C(s)$ must satisfy $\text{idx}(h_1) < \dots < \text{idx}(h_m)$ (if not, fail closed with `ERROR: conventions_repository_check: legacy units reordered in section '<s>'`).
5. **Unit kind of inserted successor units and structural bytes (`R1-m11`, `R2-m3`, `R2-i2`):**
   - Under `research_system/legacy/segmentation.py:391-425` (and `tools/w9_segmentation.py:388-458`), `segment(raw, "conventions_unit")` does **not** emit a `unit_kind` field on each row; each item row carries the exact keys `row_ordinal` (1-based), `row_kind: "item"`, `anchor_text`, `start_byte`, `byte_length`, `start_line` (1-based), `line_count`, `raw_row_sha256`, `anchor_line_sha256`, `blocker_reason: None`, `unit_ordinal` (1-based within its `## ` section), and `unit_hash`.
   - However, `W9` §7.3 item 4 (`09-migration-compatibility-and-pilot.md:404-405`) states: *"every later change to a section that holds legacy locks must be a pure insertion of successor bullets or paragraphs. No legacy bullet or paragraph is modified or deleted."*
   - To enforce that newly inserted units in a legacy-lock section are bullets or paragraphs (and **not** inserted tables), for every candidate row $c_i \in C(s)$ whose `unit_hash` $u_i \notin B(s)$, `tools/check_conventions_legacy_locks.py` inspects the first byte of `candidate_raw[c_i["start_byte"] : c_i["start_byte"] + c_i["byte_length"]]`. Under `conventions_unit` (`tools/w9_segmentation.py:415-457`; `segmentation.py:363-390`), a table unit always begins with `|` (`0x7c`), whereas a bullet begins with `- ` or `* ` and a paragraph begins with any other non-blank character. If an inserted unit in a legacy-lock section begins with `|`, the checker fails closed (exiting `1`) with:
     `ERROR: conventions_repository_check: inserted unit in legacy section '<s>' at lines <start_line>-<start_line + line_count - 1> is a table, not a bullet or paragraph (W9 §7.3 item 4)`
   - **Explicitly accepted structural behavior (`w9-segmentation-contract-v1.md:100-105,244`; `HR-6` in §13.2, `R2-i2`):** Under `w9-segmentation/1.0.0` §3, `---` horizontal rules, blank lines, the `*Last updated: ...*` footer, the H1 title before the first `## `, and `### ` sub-headings inside a `## ` section (such as `### Contract artifacts are LF-only in the working tree (locked 2026-07-28)` inside `## Computational Environment`, added by `#172` `7347ae95`) are structural bytes outside `conventions_unit` items. Consequently, editing a legacy `### ` sub-heading or moving a legacy bullet across `### ` sub-headings inside the same `## ` section is not detected mechanically and is tracked as human-review item `HR-6` (§13.2).

### 7.5 What it outputs and where it runs

- **Output (`w9-conventions-check/1`):**
  ```json
  {
    "format": "w9-conventions-check/1",
    "baseline_commit": "4b143c9225035cc29e37351445f1c3a4ab09ceb1",
    "baseline_blob": "4620c71607ca3a06c6df3b8e96a6bddffc783960",
    "classification_blob": null,
    "candidate_sha256": "2ce15910d2f6712e2d4311578ebe8a5b6e7b1f83086c1c5483ea4876636ff97c",
    "legacy_sections_checked": 9,
    "legacy_units_verified": 68,
    "inserted_successor_units_in_legacy_sections": 7,
    "total_candidate_units": 90,
    "status": "ok"
  }
  ```
- **Where it runs:** Before every batch on the operator machine (`06v:604`, via `tools/run_w9_pinned_detectors.py` from the `python -S -P` assembled tree), post-merge in `.github/workflows/legacy-write-detector.yml` (executed from `$RUNNER_TEMP/w9-detector` with no `--classified-locks`), in `tests/tools/test_w9_detectors.py`, and—if Stephen chooses **Option K1** in §16.11—on every pull request in `.github/workflows/ci.yml` `admission-controls` (`06v:491-492`, `< 0.15s`, zero ruleset change). *Honest scope note (`R4-i2`):* PR-time execution in `admission-controls` runs from the PR's checked-out `HEAD`, so if a PR modifies a closure module (`segmentation.py`) in the same PR it judges itself; the content-pinned post-merge run is the independent check.

### 7.6 Negative and positive controls (`W9-T19`, `O-13`)

1. **Positive controls (must exit 0):**
   - Baseline blob `4620c716` against itself -> exits `0` (`inserted_successor_units_in_legacy_sections == 0`).
   - Current `CONVENTIONS.md` at `dbd54fe38` -> exits `0` (`legacy_units_verified == 68`, `inserted_successor_units_in_legacy_sections == 7`, `total_candidate_units == 90`).
   - Byte copy of `CONVENTIONS.md` with a new successor bullet inserted into `## Always` and into `## ARS Foundation Governance` -> exits `0`.
2. **Negative controls (`watched_to_fail`, must exit 1):**
   - **Control N1 (modified legacy bullet):** Change 1 byte in a baseline bullet of `## Always` -> exits `1` (`legacy unit modified or deleted in section 'Always'`).
   - **Control N2 (deleted legacy paragraph):** Delete the `**Rule**:` paragraph in `## Research Assurance (locked 2026-06-02)` -> exits `1` (`legacy unit modified or deleted`).
   - **Control N3 (reordered legacy bullets):** Swap two baseline bullets in `## Never` -> exits `1` (`legacy units reordered in section 'Never'`).
   - **Control N4 (duplicate unit in section):** Duplicate a bullet verbatim in `## Always` -> exits `1` (`segmentation blocker ... duplicate_anchor`).
   - **Control N5 (missing/renamed legacy section):** Rename `## Citation Conventions` -> exits `1` (`legacy section 'Citation Conventions' is missing, renamed, or reordered`).
   - **Control N6 (inserted table in legacy section):** Insert a `| col1 | col2 |` table into `## Always` -> exits `1` (`inserted unit in legacy section 'Always' ... is a table, not a bullet or paragraph`).
   - **Control N7 (reclassified legacy unit in head/copy ignored against pinned `ACCEPTED_CONVENTIONS_CLASSIFICATION`, `R2-M4`):** In a synthetic repo where `ACCEPTED_CONVENTIONS_CLASSIFICATION` pins a classification blob marking unit `U` as `"legacy"`, commit an edited classification file at `HEAD` flipping `U` to `"successor"` and modify `U` in `CONVENTIONS.md` -> running `tools/check_conventions_legacy_locks.py` (which reads only the pinned blob) still exits `1` (`legacy unit modified or deleted`).

---

## 8. The vault Computational-Log detector (`tools/check_legacy_log_baseline.py`) and D-5 cadence

### 8.1 Authority and design constraints

- **Authority:** `W9` §4.4 (`09-migration-compatibility-and-pilot.md:197`), `W9` §7.3 items 1–6 (`:385-415`), `06v` §3 row `O-11` (`06v-w9-implementation-plan.md:191`), `06v` §4 row `W9-T19` (`:242`), `06v` §5 (`:493-496`), `06v` §6 `D-5` (`:567`) and `D-7` (`:569`), and `P-089` item 3 (`03-decisions-and-open-questions.md:6105-6115`).
- **No real L-0b export exists yet (`06v` D-7, `:569`; `P-089` "Not authorized", `:6127-6135`):**
  - `ACCEPTED_CL_EXPORT` in `research_system/legacy/accepted_w9.py:86-88` is currently the empty tuple `()`.
  - Therefore, WP9.5 designs and tests `tools/check_legacy_log_baseline.py` against a **synthetic fixture export** in WP9.3's `w9-cl-export/1` format (`research_system/legacy/evidence.py:43,277-362`) and a **synthetic classified legacy-entry list** (§8.3; Owner Point J).

### 8.2 What it reads and the exact comparison rule

1. **Inputs:**
   - `--vault-root <path>`: real vault path (`C:\Users\steph\Documents\TDA-Research` or `tmp_path`), validated per §4.3.2 (`is_symlink()`, `is_junction()`, `resolve(strict=True)` outside `repository_root`), reading `04-Methods/Computational-Log.md` via `handle_bound_read(resolved_vault, "04-Methods/Computational-Log.md")` (`research_system/legacy/reader.py:140-206`).
   - Baseline export and classification source (mutually exclusive):
     - **Production mode (`--repository-root <repo> --git-commit <sha>`, default `HEAD`):** Reads `ACCEPTED_CL_EXPORT` (`research_system/legacy/accepted_w9.py:86-88`, mapping three member descriptors):
       ```python
       {
           "export": {"repository_path": ..., "git_commit": ..., "git_blob": ..., "sha256": ..., "byte_length": ...},
           "retained_copy": {"repository_path": ..., "git_commit": ..., "git_blob": ..., "sha256": ..., "byte_length": ...},
           "classified_list": {"repository_path": ..., "git_commit": ..., "git_blob": ..., "sha256": ..., "byte_length": ...},
       }
       ```
       If `ACCEPTED_CL_EXPORT` is empty `()`, fails closed: `ERROR: vault_computational_log: ACCEPTED_CL_EXPORT is empty; L-0b baseline export has not been accepted yet`. When populated at L-0b, reads all three members via `git --no-replace-objects show <git_commit>:<repository_path>` matching `git_blob_id`, `sha256_hex`, and `len`; validates via `evidence.require_cl_export(export)` (`research_system/legacy/evidence.py:277-362`); runs `report = recheck_cl_export(export, retained_raw)` (`research_system/legacy/export_recheck.py:32-89`, producer `CL_EXPORT_PRODUCER`, `tools/w9_segmentation.py` blob `43e1454de09b61e274954c42b21d6ae533857a24`, `evidence.py:52-54`); **explicitly requires `report["void"] is False`** (`recheck_cl_export` does not raise on divergence, `R2-m12` — exit `1` with `ERROR: vault_computational_log: recheck_cl_export reported void=True`); and validates `classified_list` (§8.3).
     - **Fixture mode (`--fixture-export-json <path> --fixture-retained-copy <path> [--fixture-classified-list <path>]`):** Same `require_cl_export` + `recheck_cl_export` (`void == False`) checks from disk.
2. **Whole-page live segmentation (`R1-M2`):** Calls `live_seg = segment(live_raw, "computational_log_entry")` (`research_system/legacy/segmentation.py:429-488`, `region=None` because prepended successor entries shift line numbers and byte offsets of all legacy rows below them, `w9-segmentation-contract-v1.md:189-192`) and verifies agreement with `tools/w9_segmentation.py:461-518`.
3. **Exact five-part decision rule (`R1-M1`, `R1-M9`, `R1-m8`, `R2-m3`, `R2-i4`):**
   - **Check 1 — No UTF-8 BOM, CRLF tolerance on successor prepends, zero blockers (`W9:197`):** Requires `live_seg["file_facts"]["has_utf8_bom"] is False`. Because Obsidian/Windows edits may save prepended successor entries with CRLF (`"line_ending": "mixed"`), Check 1 ignores file-level `line_ending` while Checks 3–4 verify exact `raw_row_sha256` (`w9-segmentation-contract-v1.md:168-169`), catching any legacy LF->CRLF change. Rejects any `"blocker"` row (`unparseable_anchor`, `duplicate_anchor`, `unaddressed_region`; 0 blockers in `w9-segmentation-contract-v1.md:242,254-256`; intentional strictness over successor anchors):
     `ERROR: vault_computational_log: live file contains segmentation blocker at row_ordinal=<row_ordinal> (lines <start_line>-<start_line + line_count - 1>): <blocker_reason> (<anchor_text_or_none>)`
   - **Check 2 — Complete classification (`R1-M9`; Owner Point J):** `require_cl_export` permits `class: None` in raw exports (`evidence.py:347-360`). Resolves `class_by_ordinal` from `classified_list` (`"w9-cl-classified-list/1"`, §8.3) or fixture `export["classifications"]`; every row must be `"legacy"` or `"successor"` (`ERROR: vault_computational_log: baseline export has unclassified or blocker row at row_ordinal=<ord>`).
   - **Check 3 — Legacy `"item"` rows byte-identical (`W9:197,402-403`; `w9-segmentation-contract-v1.md:189-192`):** Indexes live `"item"` rows by `anchor_text`; every baseline legacy item row $b \in L_{\text{item}}$ must exist (`ERROR: vault_computational_log: missing or renamed legacy heading anchor '<anchor>' (baseline row_ordinal=<row_ordinal>, raw_row_sha256=<sha>)`) and match `anchor_line_sha256` + `raw_row_sha256` (`ERROR: vault_computational_log: byte change inside legacy entry '<anchor>' (expected raw_row_sha256=<b_sha>, got <l_sha> at live lines <l["start_line"]>-<l["start_line"] + l["line_count"] - 1>)`).
   - **Check 4 — Legacy `"structural"` rows byte-identical (`w9-segmentation-contract-v1.md:184-188`):** Each $b \in L_{\text{struct}}$ matches a unique live `"structural"` row on `anchor_line_sha256` + `raw_row_sha256` (`ERROR: vault_computational_log: modified or missing legacy structural block (anchor_line_sha256=<sha>)`).
   - **Check 5 — Relative order preserved:** Matched live `row_ordinal` values over $L_{\text{item}} \cup L_{\text{struct}}$ are strictly increasing (`ERROR: vault_computational_log: legacy entries reordered in live file`).

### 8.3 Format of `classified_list` and what changes when L-0b is accepted

In `research_system/legacy/accepted_w9.py:86-88`, WP9.3 already fixed the shape of an `ACCEPTED_CL_EXPORT` entry:
```python
# An ACCEPTED_CL_EXPORT entry: {"export": {"repository_path", "git_commit", "git_blob", "sha256", "byte_length"},
# "retained_copy": {the same fields}, "classified_list": {the same fields}}.
ACCEPTED_CL_EXPORT: tuple[MappingProxyType[str, Any], ...] = ()
```
Because WP9.3 fixed `require_cl_export` (`evidence.py:277-362`) for `"export"` but did not yet define a validator for `"classified_list"`, WP9.5 defines the closed format `"w9-cl-classified-list/1"` (validated by `require_cl_classified_list`, in `tools/_w9_detector_evidence.py` or `research_system/legacy/evidence.py` under Owner Point J):
```json
{
  "format": "w9-cl-classified-list/1",
  "export_git_blob": "<40-hex>",
  "export_sha256": "<64-hex>",
  "retained_copy_git_blob": "<40-hex>",
  "classifications": [
    {
      "ordinal": 1,
      "row_kind": "structural",
      "anchor_text": null,
      "anchor_line_sha256": "<64-hex>",
      "raw_row_sha256": "<64-hex>",
      "class": "legacy"
    },
    {
      "ordinal": 2,
      "row_kind": "item",
      "anchor_text": "2026-07-16|RESULT|P01-A: ...",
      "anchor_line_sha256": "<64-hex>",
      "raw_row_sha256": "<64-hex>",
      "class": "legacy"
    }
  ]
}
```
Every 1-based row ordinal $1, \dots, N$ of `export["segmentation"]["rows"]` (`research_system/legacy/segmentation.py:408`; `research_system/legacy/evidence.py:347-358`, matching `row["row_ordinal"]`) must appear in `classified_list["classifications"]` with matching `(ordinal, row_kind, anchor_text, anchor_line_sha256, raw_row_sha256)` and with `class` in `{"legacy", "successor"}` (no `null` allowed in the accepted classified list!). (`R2-m3`.)

| Aspect | In WP9.5 (before L-0b) | When L-0b is authorized (`06v` D-7) and accepted by PR |
|---|---|---|
| `ACCEPTED_CL_EXPORT` (`research_system/legacy/accepted_w9.py:86-88`) | `()` (empty tuple) | Appended with one `MappingProxyType({"export": {...}, "retained_copy": {...}, "classified_list": {...}})` entry, where each of the 3 members carries `{"repository_path", "git_commit", "git_blob", "sha256", "byte_length"}` (`accepted_w9.py:86-87`). |
| W9 paths addendum row (`06v-addendum-2026-11-10-w9-paths.md:29`) | File names open (`in the evidence area; file name not yet fixed`) | Dated amendment fixing the three `.research-system/evidence/w9/` paths for `export`, `retained_copy`, and `classified_list`. |
| `tools/check_legacy_log_baseline.py` | Tested against synthetic `w9-cl-export/1` and `w9-cl-classified-list/1` fixtures via `--fixture-export-json`, `--fixture-retained-copy`, `--fixture-classified-list`. Production mode checks `ACCEPTED_CL_EXPORT` and fails closed while empty. | Production mode reads `ACCEPTED_CL_EXPORT[-1]` at `--git-commit HEAD` without needing a detector rewrite. |

---

### 8.4 Settling D-5: pre-batch and weekly cadence, gate placement at batch start, reset, weekly cost, and self-attestation

- **Authority:** `06v` §5 (`06v-w9-implementation-plan.md:495-496`), `06v` §6 `D-5` (`:567`), and `06v` §7 batch checklist (`:604`).
- **What each clean run produces and records:**
  1. `tools/check_legacy_log_baseline.py` outputs a canonical JSON report (`format: "w9-vault-log-check/1"`):
     ```json
     {
       "format": "w9-vault-log-check/1",
       "export_git_blob": "<40-hex>",
       "retained_copy_git_blob": "<40-hex>",
       "classified_list_git_blob": "<40-hex>",
       "live_file_sha256": "<64-hex>",
       "live_file_byte_length": 833453,
       "legacy_items_verified": 255,
       "legacy_structural_verified": 1,
       "status": "ok"
     }
     ```
     *(Note: `833453` and `255` above are illustrative placeholders from the U-4 metadata read and WP9.2 census; actual counts come from the L-0b classified export.)*
     It computes `output_sha256 = sha256_hex(canonical_bytes(report))` (`research_system/canonical.py:40-52`).
  2. With `--record-run .research-system/evidence/w9/vault-detector-runs.json`, a clean run appends a `"kind": "run"` entry to `.research-system/evidence/w9/vault-detector-runs.json` (`format: "w9-vault-detector-runs/1"`):
     ```json
     {
       "format": "w9-vault-detector-runs/1",
       "entries": [
         {
           "kind": "run",
           "run_at": "2026-11-21T21:00:00Z",
           "export_git_blob": "<40-hex>",
           "classified_list_git_blob": "<40-hex>",
           "live_file_sha256": "<64-hex>",
           "output_sha256": "<64-hex>",
           "status": "ok"
         },
         {
           "kind": "owner_cadence_reset",
           "reset_at": "2026-12-10T10:00:00Z",
           "decision_ref": "P-09x",
           "reason": "Missed weekly run during holiday week; fresh pre-batch run verified clean"
         }
       ]
     }
     ```
- **Correcting the four D-5 design flaws identified in `R1-M8`:**
  1. **Gate placement at batch start (`LR-003` and `LR-015`) as well as batch acceptance (`LR-016` and `LR-020`):**
     A batch begins with path registration (`LR-003`, `prepare_proposal` in `research_system/legacy/preparers.py:686-690`) and observation (`LR-015`, `prepare_observation` in `preparers.py:1215-1218`), and concludes with closed-reference acceptance (`LR-016` and `LR-020`, `check_environment` in `research_system/legacy/acceptance.py:147-152`). Placing the D-5 gate only in `acceptance.py` would check the cadence after the batch's registrations and observations were already recorded in the store.
     Under **Owner Point E (Option E1, Recommended, §16)**, `require_vault_detector_cadence` is called at **`LR-003`** (`preparers.py:686-690`), **`LR-015`** (`preparers.py:1215-1218`), **`LR-016`**, and **`LR-020`** (`acceptance.py:147-152`), so a missed run blocks the next batch **before** its first registration or observation can enter the store!
  2. **Never gate on "file present" (`R1-M8`):**
     Gating on whether `vault-detector-runs.json` exists in Git would let deleting the file disable the check. Instead, `require_vault_detector_cadence` is gated strictly on `bool(reader.accepted_cl_export)` (i.e., once `ACCEPTED_CL_EXPORT` in `research_system/legacy/accepted_w9.py:88` is non-empty after L-0b, `vault-detector-runs.json` is unconditionally required at `reader.git_head` and its absence raises `EvidenceRefused`!). Before L-0b (and in existing WP9.3/WP9.4 unit tests where `accepted_cl_export == ()`), the check is inert unless explicitly invoked.
  3. **Exact cadence rule and explicit owner reset (`R1-M8`):**
     Given `entries` in `vault-detector-runs.json` at `git_head` and the command timestamp `now`:
     - Timestamps across `entries` (`run_at` for `"kind": "run"`, `reset_at` for `"kind": "owner_cadence_reset"`) must be strictly non-decreasing.
     - The last entry in `entries` must be a `"kind": "run"` entry with `status == "ok"`, `export_git_blob == accepted_cl_export[-1]["export"]["git_blob"]`, `classified_list_git_blob == accepted_cl_export[-1]["classified_list"]["git_blob"]`, and `0 <= (now - last_run_at) <= timedelta(days=7)` (proving the pre-batch run occurred within the last 7 days).
     - Since the most recent `"kind": "owner_cadence_reset"` entry (or the first entry if no reset exists), every consecutive pair of `"kind": "run"` entries `(r_prev, r_curr)` must satisfy `r_curr.run_at - r_prev.run_at <= timedelta(days=7)`.
     - If a weekly run was missed (creating a >7-day gap between consecutive runs), the next batch is blocked until a reviewed PR records an `"owner_cadence_reset"` entry naming Stephen's `decision_ref` (`P-0xx`) followed by a fresh `"kind": "run"` entry. Thus one missed weekly run blocks the **next** batch (`06v:567`) until Stephen explicitly resets the cadence, rather than permanently bricking the store forever.
  4. **Explicit statement of the weekly operational cost and self-attestation limit (`R1-M8`, `R3-m2`, `R3-m9 (c)`):**
     - **Operational cost:** Because `research_system/legacy/evidence.py:92-105` (`read_evidence`) reads every evidence file from Git at the store binding's `git_head` (never from the working tree), running via `tools/run_w9_pinned_detectors.py` and recording each weekly run in `.research-system/evidence/w9/vault-detector-runs.json` requires a **weekly reviewed PR to `main`** (Stephen's bypass merge under Option I1 with a `Bypass reason:` line in the PR body per `tools/check_bypass_merges.py:41,135`) and, before any store command `LR-003`/`LR-015`/`LR-016`/`LR-020` runs against that evidence, an `ars store advance-binding` authorized by Stephen under `06v` D-1 (`:578`).
     - **Self-attestation limit:** Because CI runners cannot see `C:\Users\steph\Documents\TDA-Research`, both `run_at` and `output_sha256` in `vault-detector-runs.json` are produced on the operator machine and self-attested by the operator's commit; no independent remote runner can verify that the local vault file was read at `run_at`. This is recorded as Human-Review / Operational claim `HR-4` in §13.2.

### 8.5 Negative and positive controls (`W9-T19`, `O-13`)

All controls run on synthetic fixture bytes in `tmp_path` (never reading or writing the real vault):
1. **Positive controls (must exit 0):**
   - Clean match between fixture retained copy and live copy -> exits `0`.
   - Prepending a new successor entry at the top of the live copy (including a successor entry with CRLF line endings while legacy entries remain LF, `R1-m8`) -> exits `0`.
   - Modifying an entry classified as `"successor"` in `classified_list` -> exits `0`.
2. **Negative controls (`watched_to_fail`, must exit 1):**
   - **Control V1 (1-byte edit inside a legacy entry body, or LF->CRLF conversion inside a legacy entry):** -> exits `1` (`byte change inside legacy entry '<anchor>'`).
   - **Control V2 (renamed legacy heading anchor):** -> exits `1` (`missing or renamed legacy heading anchor`).
   - **Control V3 (deleted legacy entry):** -> exits `1` (`missing or renamed legacy heading anchor`).
   - **Control V4 (duplicate heading anchor):** -> exits `1` (`live file contains segmentation blocker ... duplicate_anchor`).
   - **Control V5 (unparseable dated-looking heading):** -> exits `1` (`live file contains segmentation blocker ... unparseable_anchor`).
   - **Control V6 (reordered legacy entries):** -> exits `1` (`legacy entries reordered in live file`).

---

## 9. The detector-controls file (`.research-system/evidence/w9/detector-controls.json`)

### 9.1 Fixed WP9.3 format and invariants

In `research_system/legacy/evidence.py:38,41,59-64,133-154`, WP9.3 fixed the path, format string, and closed schema of `.research-system/evidence/w9/detector-controls.json`:

- **Path:** `.research-system/evidence/w9/detector-controls.json` (`DETECTOR_CONTROLS`, `evidence.py:38`)
- **Format string:** `"w9-detector-controls/1"` (`DETECTOR_CONTROLS_FORMAT`, `evidence.py:41`)
- **Required detectors and control kinds (`REQUIRED_DETECTOR_CONTROLS`, `evidence.py:59-64`):**
  ```python
  REQUIRED_DETECTOR_CONTROLS = {
      "main_ruleset": "recorded_read",
      "post_merge_first_parent": "watched_to_fail",
      "vault_computational_log": "watched_to_fail",
      "conventions_repository_check": "watched_to_fail",
  }
  ```
- **Validation in `require_detector_controls` (`evidence.py:133-154`):**
  - Top-level closed keys: `{"format", "detectors"}`.
  - Each item in `"detectors"` has closed keys `{"detector", "control", "output_sha256", "recorded_at"}`, covering all four keys in `REQUIRED_DETECTOR_CONTROLS` with no duplicates, 64-hex lowercase `"output_sha256"`, and UTC ISO-8601 `"recorded_at"`.

### 9.2 Binding `output_sha256` to the detector tool blob and deterministic synthetic commits

As `R1-m4` identified:
1. `require_detector_controls` (`evidence.py:133-154`) checks JSON shape only; if a detector script were later weakened, a stale `output_sha256` would still pass `require_detector_controls` unless the transcript binds the detector tool's Git blob and CI re-verifies the `watched_to_fail` controls!
2. Synthetic Git commits created in `tmp_path` for cases 3 and 4 of `post_merge_first_parent` would have different commit SHAs on each run unless all Git author/committer identity and timestamp environment variables are pinned.

**How `tools/run_w9_detector_controls.py` makes the transcripts deterministic and binds them to the detector closure blobs (`R1-m4`, `R2-m8`, `R2-M3`):**

1. **Pinned and isolated Git environment for all synthetic commits in negative controls (`R2-m8`):**
   Every `git` subprocess executed by `tools/run_w9_detector_controls.py` runs with an empty temporary `GIT_CONFIG_GLOBAL` file inside the control's temporary directory, `GIT_CONFIG_NOSYSTEM=1`, explicit CLI overrides `-c core.autocrlf=false -c commit.gpgsign=false`, and fixed author/committer metadata:
   ```python
   CONTROL_GIT_ENV = {
       "GIT_AUTHOR_NAME": "W9 Control Runner",
       "GIT_AUTHOR_EMAIL": "w9-controls@tdl.local",
       "GIT_AUTHOR_DATE": "2026-11-21T00:00:00Z",
       "GIT_COMMITTER_NAME": "W9 Control Runner",
       "GIT_COMMITTER_EMAIL": "w9-controls@tdl.local",
       "GIT_COMMITTER_DATE": "2026-11-21T00:00:00Z",
       "GIT_CONFIG_NOSYSTEM": "1",
       "GIT_CONFIG_GLOBAL": str(empty_gitconfig_path),
   }
   ```
   Every synthetic `git` invocation prefixes `["git", "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", ...]`. With pinned tree blobs, parent SHAs, message bytes, `CONTROL_GIT_ENV`, and user/system Git config isolated, every synthetic commit SHA `<C>` generated in `tmp_path` is deterministic across repeated runs on the same Git toolchain (bit-for-bit identity across distinct Git versions or unmeasured host machines is not claimed without cross-host measurement, `R2-m8`).
2. **Binding each detector tool's Git blob ID and `closure_blobs` map into the hashed transcript (`R1-m4`, `R2-M3`, `R3-m7 (d)`):**
   Each detector's canonical transcript includes `"tool_git_blob": git_blob_id(Path(tool_path).read_bytes())` (`research_system/legacy/reader.py:75-77`) and `"closure_blobs"` (the `{path: git_blob_id}` map of every module in `compute_detector_import_closure` for that detector):
   ```json
   {
     "format": "w9-control-transcript/1",
     "detector": "post_merge_first_parent",
     "tool_path": "tools/check_legacy_writes.py",
     "tool_git_blob": "<40-hex>",
     "closure_blobs": {
       "tools/_w9_detector_evidence.py": "<40-hex>",
       "research_system/legacy/evidence.py": "<40-hex>"
     },
     "cases": [
       {
         "case_id": "replay_5df0c001",
         "exit_code": 1,
         "error_lines": ["ERROR: post_merge_first_parent: ..."]
       }
     ]
   }
   ```
   The detector entry's `output_sha256` is `sha256_hex(canonical_bytes(transcript))` (`research_system/canonical.py:40-52`).
3. **CI and wrapper re-verification of `watched_to_fail` hashes after L-1:** `tools/run_w9_detector_controls.py --code-root <detector_dir> --repo-root <checkout_root> --verify-watched-to-fail <detector_controls_json>` separates `--code-root` (assembled closure bytes/imports) from `--repo-root` (Git object DB for bare clones, defaulting to `--repo-root` when omitted), wraps `main()` to exit `2`, uses `encoding="utf-8"` on `git`, and spawns child Python interpreters via `[sys.executable, "-S", "-P", ...]`. Executed under `python -S -P` in `.github/workflows/legacy-write-detector.yml` (§10.2), `tools/run_w9_pinned_detectors.py` (§6.2.3), and `L1_LIVE` `admission-controls` (§10.3), failing closed on mismatch (`ERROR: detector_controls: recomputed output_sha256 for '<detector>' does not match detector-controls.json`; M-6 sits outside the 22-blob runtime closure, `HR-7`).

---

## 10. Merging is not going live (`P-089` item 3)

### 10.1 Why WP9.5 must stay inactive on `main` and the vault after merge

- `P-089` (`03-decisions-and-open-questions.md:6113-6115,6129-6130`) withholds authorization for **L-1** ("the detectors live on `main` or the vault") and requires that merging WP9.5 must not start any detector automatically on `main` or the vault.
- While `.research-system/evidence/w9/detector-controls.json` is absent on `main`, WP9.3's `prepare_proposal` (`LR-003`, `research_system/legacy/preparers.py:686-690`) refuses any path registration on a store bound to `main`.

### 10.2 Full `.github/workflows/legacy-write-detector.yml` specification

In WP9.5, `.github/workflows/legacy-write-detector.yml` is committed with `on: workflow_dispatch:` only (no `inputs:`), `fetch-depth: 0`, `permissions: contents: read, pull-requests: read`, path-confined 22-blob assembly, stdlib-only `python -S -P` + `PYTHONSAFEPATH=1` execution (no `uv sync`), `--code-root` / `--repo-root` split on `--verify-watched-to-fail`, and `--ruleset-check <require|ci-d8>` selected from U-3/D-8:

```yaml
name: W9 Legacy Write Detector

on:
  workflow_dispatch:

permissions:
  contents: read
  pull-requests: read

defaults:
  run:
    shell: bash

jobs:
  detect-legacy-writes:
    name: W9 Post-Merge Legacy Write and CONVENTIONS Lock Check
    runs-on: windows-latest
    timeout-minutes: 15

    steps:
      - name: Checkout repository with full history
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Fetch current origin/main tip
        env:
          GIT_TERMINAL_PROMPT: "0"
        run: git fetch --no-tags origin main:refs/remotes/origin/main

      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with:
          # Under Owner Point I (§16.1), Option I1-py-minor (Recommended) uses "3.13"; Option I1-py-patch pins "3.13.5".
          python-version: "3.13.5"

      - name: Assemble content-pinned detector tree from recorded closure blobs
        id: pin
        env:
          # Under Option I3, flip REQUIRE_I3_PIN to "true" so an empty vars.W9_DETECTOR_PIN fails closed.
          REQUIRE_I3_PIN: "false"
          W9_DETECTOR_PIN_VAR: ${{ vars.W9_DETECTOR_PIN }}
        run: |
          set -euo pipefail
          main_tip="$(git --no-replace-objects rev-parse refs/remotes/origin/main | tr -d '\r')"
          detector_dir="${RUNNER_TEMP}/w9-detector"
          python - <<'PY' "$main_tip" "$detector_dir" > "${RUNNER_TEMP}/w9-pin.env"
          import hashlib, json, os, pathlib, shutil, subprocess, sys
          from pathlib import PurePosixPath
          WIN_RESERVED = {
              "CON", "PRN", "AUX", "NUL",
              *(f"COM{i}" for i in range(1, 10)),
              *(f"LPT{i}" for i in range(1, 10)),
          }
          main_tip, detector_dir = sys.argv[1], pathlib.Path(sys.argv[2])
          raw = subprocess.check_output(
              ["git", "--no-replace-objects", "show", f"{main_tip}:.research-system/evidence/w9/walk-baseline.json"]
          )
          wb = json.loads(raw.decode("utf-8"))
          blobs = wb["baselines"][-1]["detector_closure_blobs"]
          canonical = json.dumps(blobs, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
          blobs_sha256 = hashlib.sha256(canonical).hexdigest()
          require_i3 = os.environ.get("REQUIRE_I3_PIN", "false").lower() == "true"
          var_raw = os.environ.get("W9_DETECTOR_PIN_VAR", "").strip()
          if require_i3 and not var_raw:
              raise SystemExit("ERROR: W9_DETECTOR_PIN is required under Option I3 but is empty")
          if var_raw:
              pv = json.loads(var_raw)
              if pv["walk_baseline_commit"] != wb["baselines"][0]["baseline_commit"]:
                  raise SystemExit(
                      f"ERROR: walk_baseline_commit {wb['baselines'][0]['baseline_commit']} != W9_DETECTOR_PIN {pv['walk_baseline_commit']}"
                  )
              if pv["closure_blobs_sha256"] != blobs_sha256:
                  raise SystemExit(
                      f"ERROR: closure_blobs_sha256 {blobs_sha256} != W9_DETECTOR_PIN {pv['closure_blobs_sha256']}"
                  )
          baseline_commit = wb["baselines"][0]["baseline_commit"]
          chain = subprocess.check_output(
              ["git", "--no-replace-objects", "rev-list", "--first-parent", main_tip], text=True, encoding="utf-8"
          ).splitlines()
          if baseline_commit not in chain:
              raise SystemExit(f"ERROR: baseline commit {baseline_commit} is not on origin/main ({main_tip}) first-parent chain")
          shutil.rmtree(detector_dir, ignore_errors=True)
          detector_dir.mkdir(parents=True, exist_ok=True)
          resolved_root = detector_dir.resolve()
          for rel_path, blob_sha in blobs.items():
              if not rel_path or "\\" in rel_path or rel_path.startswith("/") or ":" in rel_path:
                  raise SystemExit(f"ERROR: invalid closure path key {rel_path!r}")
              pp = PurePosixPath(rel_path)
              if pp.is_absolute() or ".." in pp.parts or "." in pp.parts or pp.as_posix() != rel_path:
                  raise SystemExit(f"ERROR: unconfined closure path key {rel_path!r}")
              if any(part.endswith((".", " ")) or part.split(".", 1)[0].upper() in WIN_RESERVED for part in pp.parts):
                  raise SystemExit(f"ERROR: prohibited Windows path segment in {rel_path!r}")
              obj_probe = subprocess.run(
                  ["git", "--no-replace-objects", "cat-file", "-t", blob_sha],
                  capture_output=True, text=True, encoding="utf-8",
              )
              if obj_probe.returncode != 0:
                  raise SystemExit(f"ERROR: {rel_path} pin {blob_sha} is an absent or invalid object")
              if obj_probe.stdout.strip() != "blob":
                  raise SystemExit(f"ERROR: {rel_path} pin {blob_sha} has type {obj_probe.stdout.strip()}, expected blob")
              dest = (resolved_root / pp).resolve()
              if not dest.is_relative_to(resolved_root):
                  raise SystemExit(f"ERROR: path traversal outside {resolved_root}: {rel_path!r}")
              dest.parent.mkdir(parents=True, exist_ok=True)
              dest.write_bytes(subprocess.check_output(["git", "--no-replace-objects", "cat-file", "blob", blob_sha]))
              if not dest.is_file():
                  raise SystemExit(f"ERROR: missing written closure file {rel_path!r}")
              written_sha = subprocess.check_output(
                  ["git", "--no-replace-objects", "hash-object", "--no-filters", str(dest)],
                  text=True, encoding="utf-8",
              ).strip()
              if written_sha != blob_sha:
                  raise SystemExit(f"ERROR: post-write blob mismatch for {rel_path!r}: {written_sha} != {blob_sha}")
          print(f"MAIN_TIP={main_tip}")
          print(f"DETECTOR_DIR={detector_dir}")
          PY
          cat "${RUNNER_TEMP}/w9-pin.env" >> "$GITHUB_ENV"
          source "${RUNNER_TEMP}/w9-pin.env"
          git --no-replace-objects show "${MAIN_TIP}:.research-system/evidence/w9/detector-controls.json" > "${RUNNER_TEMP}/detector-controls.json"

      - name: Run content-pinned W9 post-merge detector, CONVENTIONS lock check, and watched-to-fail verify
        env:
          GH_TOKEN: ${{ github.token }}
          PYTHONPATH: ${{ env.DETECTOR_DIR }}
          PYTHONSAFEPATH: "1"
        run: |
          set -euo pipefail
          unset PYTHONHOME VIRTUAL_ENV || true
          # Ruleset flag: '--ruleset-check require' when U-3 shows rule-suites is readable by GITHUB_TOKEN,
          # or '--ruleset-check ci-d8' when Stephen confirms D-8 (decided after U-3 probe before code dispatch).
          python -S -P "${DETECTOR_DIR}/tools/check_legacy_writes.py" \
            --repo-root . \
            --ruleset-check ci-d8
          python -S -P "${DETECTOR_DIR}/tools/check_conventions_legacy_locks.py" \
            --repo-root . \
            --git-ref "${MAIN_TIP}:CONVENTIONS.md"
          python -S -P "${DETECTOR_DIR}/tools/run_w9_detector_controls.py" \
            --code-root "$DETECTOR_DIR" \
            --repo-root . \
            --verify-watched-to-fail "${RUNNER_TEMP}/detector-controls.json"

      - name: Remove temporary content-pinned detector directory
        if: always()
        run: |
          if [ -n "${DETECTOR_DIR:-}" ] && [ -d "$DETECTOR_DIR" ]; then
            rm -rf "$DETECTOR_DIR" || true
          fi
```

**Why every part of this workflow skeleton is required:**
1. **`fetch-depth: 0`:** `check_legacy_writes.py` refuses shallow clones; `check_conventions_legacy_locks.py` reads blob `4620c716` at `4b143c92`.
2. **No `workflow_dispatch` `inputs:` and `pipefail`-safe shell:** Prevents narrowing walks; Python `rev-list` avoids SIGPIPE 141; forward slashes avoid Git Bash backslash-dropping.
3. **Confined 22-blob assembly, post-write hash check, `python -S -P`, and Option I3 sequencing:** §6.2.3 validation (traversal, absolute, trailing `.`/space, Windows reserved names) + `dest.is_file()` + `git --no-replace-objects hash-object --no-filters` runs before `python -S -P` + `PYTHONPATH="$DETECTOR_DIR"` + `PYTHONSAFEPATH=1` (child `[sys.executable, "-S", "-P", ...]`; `--code-root "$DETECTOR_DIR" --repo-root .` on `--verify-watched-to-fail`). **I3 upgrade sequence:** merge pin advance first, then update `vars.W9_DETECTOR_PIN` (expected red `push` run until update, then `workflow_dispatch` green); Option I1 CODEOWNERS protects the workflow.
4. **Watchdog compatibility:** `tools/check_workflow_liveness.py:78-92` requires `state == "active"`; `.github/workflows/ci.yml:255-279` (`:263,276`) watches only `ars-artefact-currency-watchdog.yml` and `research-system-suite.yml`.
5. **Pre-L-1 throwaway rehearsal & L-1 exit criterion:** Because `walk-baseline.json` is absent on `origin/main` before L-1, rehearsal uses a **separate temporary throwaway workflow** differing on `on: pull_request`, no `git fetch origin main` overwrite, and `MAIN_TIP="$GITHUB_SHA"` reading synthetic PR-head evidence (closed without merging like U-3); **a green `workflow_dispatch` run of unmodified `.github/workflows/legacy-write-detector.yml` on the L-1 merge commit on `main` is a required L-1 exit criterion**.

### 10.3 The L-1 tripwire test and how L-1 switches it

`tests/tools/test_w9_detectors.py` loads `.github/workflows/legacy-write-detector.yml` with **`yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)`** (`tests/tools/test_ars_currency_workflow_controls.py:19-22`):
```python
# Flipped from False to True in the L-1 activation PR authorized by Stephen (06v §7 L-1).
L1_LIVE = False
```
`test_legacy_write_detector_l1_activation_state` asserts:
- **While `L1_LIVE is False`:** `set(doc["on"].keys()) == {"workflow_dispatch"}`; none of `.research-system/evidence/w9/{detector-controls,registration-manifest,walk-baseline,vault-detector-runs}.json` exists in `REPO_ROOT`.
- **When `L1_LIVE is True` (flipped at L-1, in `ci.yml` `admission-controls` under Option F1):** `set(doc["on"].keys()) == {"push", "schedule", "workflow_dispatch"}`, `doc["on"]["push"] == {"branches": ["main"]}`, and `.research-system/evidence/w9/{detector-controls,walk-baseline,registration-manifest}.json` exist and pass schema checks + `--verify-watched-to-fail`. Per Stephen's `2026-11-22` decision, `admission-controls` runs no `HEAD` blob check, gating row check, verdict comparison, or `gh` call (optional advisory-only Rule 0.2 row report allowed); wiring into `ci.yml` (F1) + CODEOWNERS (I1) protects `L1_LIVE` (§6.2.2).

---

## 11. Where the controls run and scratch-clone mechanics

### 11.1 Hard isolation rule (`06v:193,497-502`)

Every negative control and integration test runs exclusively on a scratch Git clone or a byte copy inside `pytest`'s `tmp_path` (or `tempfile.TemporaryDirectory`), **never** writing to `main`, the working checkout, any linked worktree, or `C:\Users\steph\Documents\TDA-Research`.

### 11.2 How the W9-T7 scratch clone is constructed and replayed

`06v:230,499` specify replaying `5df0c001` and `811d5a2b` on a scratch clone from the local object store. Placing `W9-T7` in `tests/tools/test_w9_detectors.py` (`unit`, `ci.yml` `admission-controls`) rather than a `@pytest.mark.slow` integration file is a recorded departure from `06v:230` (`integration, slow`) put to Stephen in §16.7 (Owner Point F, plus a dated `06v-addendum` row).

1. **Measured bare scratch clone from the local object store (`~1.57–1.99s`; Appendix A §21.1):**
   `git clone --bare --local --no-hardlinks <REPO_ROOT> <tmp_path>/scratch.git`, followed immediately by `git --git-dir=<tmp_path>/scratch.git remote remove origin`.
2. **Dynamic derivation of the 10-entry fixture registration manifest via `git diff-tree`:**
   Derives the 7 `results/` paths changed by `5df0c001` (`5df0c001~1..5df0c001`, 11 total files) and the 3 `contracts/manifests/input-provenance/` paths changed by `811d5a2b` (`811d5a2b~1..811d5a2b`, 9 total files), building `"w9-registration-manifest/2"` (under Option A1).
3. **Executing the replay:**
   - **T7-1 (Historical SHAs in `<tmp_path>/scratch.git`):** Runs `check_legacy_writes.py --repo-root <tmp_path>/scratch.git --ruleset-check skip --manifest-file <manifest> --pr-map <empty>` across `a426b731..5df0c001` (exit `1`, Rules 1 & 2 on the 7 `results/` files), `1d3a0769..811d5a2b` (exit `1`, Rule 1 on the 3 manifests), and `4b143c92..811d5a2b` (exit `1`).
   - **T7-2 (In-tree manifest at `P1` via throwaway `GIT_INDEX_FILE`):** Builds synthetic baseline `B0` + commits `C_5df` and `C_811` without `--manifest-file` (`< 0.3s`), asserting the same Rule 1 and Rule 2 failures.

### 11.3 How the test proves it never writes the real repository or the vault

As `R1-m3`, `R2-m16`, `R3-m8`, and `R4-m9` established, in a linked worktree `--git-dir` is `.git/worktrees/<name>` (holding `HEAD`, `index`, `FETCH_HEAD`, and `ORIG_HEAD`, **not** `config` or `hooks/`—those live in shared `--git-common-dir` alongside sibling worktrees' refs). Therefore, tests in `tests/tools/test_w9_detectors.py` and `tests/research_system/integration/test_w9_wp9_5_detectors.py`:
1. Run every detector subprocess with `cwd=tmp_path` and `GIT_DIR` pinned to `<tmp_path>`.
2. Before and after each test, compare exact equality of:
   - **Locally (checkout-scoped, flake-free):** `(relpath, st_size, st_mtime_ns)` over `--git-dir` files `{HEAD, index, FETCH_HEAD, ORIG_HEAD}` **only**, plus the checked-out branch's own ref (`git -C <REPO_ROOT> --no-optional-locks symbolic-ref -q HEAD` + `rev-parse`) and `git -C <REPO_ROOT> --no-optional-locks for-each-ref refs/tags`;
   - **In CI only (`CI=true`, no sibling worktree):** also scans `--git-common-dir` **`config` and `hooks/`**; and
   - `git -C <REPO_ROOT> --no-optional-locks --no-replace-objects status --porcelain=v1 --ignored -z` and `rev-parse HEAD`.

---

## 12. Tests and test-time budget

### 12.1 Test inventory and mapping to `06v` §4

| Test file & group | Markers | Cases covered |
|---|---|---|
| `tests/tools/test_w9_detectors.py` — **`W9-T19` (`CONVENTIONS.md`)** | `unit` (`ci.yml` `admission-controls`) | Baseline `4620c716` and `dbd54fe3` (`68` -> `90` units) pass; pure successor bullet/paragraph insertion passes; L-0b `ACCEPTED_CONVENTIONS_CLASSIFICATION` passes; negative controls N1–N7 exit `1`. |
| `tests/tools/test_w9_detectors.py` — **`W9-T19` (Computational-Log) & D-5** | `unit` (`ci.yml` `admission-controls`) | Clean fixture + prepended LF/CRLF successor entries pass; empty `ACCEPTED_CL_EXPORT` fails; `recheck_cl_export` `void: True` fails; symlink/junction/resolve-mismatch/in-repo `--vault-root` fails; controls V1–V6 exit `1`; D-5 7-day cadence passes, missing file when `ACCEPTED_CL_EXPORT` non-empty fails, >7 days fails until `"owner_cadence_reset"` + `"run"`. |
| `tests/tools/test_w9_detectors.py` — **Rule 0 & closure non-lockstep** | `unit` (`ci.yml` `admission-controls`) | Atomic disarm fails; pre-reg edit passes; retroactive blessing fails; `detector-controls.json` deletion or backdated `recorded_at` fails; editing a closure module without a `baselines` append exits `0` (**no Rule 0.3 lockstep**); row creation (`baselines[0]`) & append (`baselines[k]`) positive/negative controls for (i)–(iv): missing ref, blobs differing from tree at `C`, non-`P1` `source_commit`, wrong `entry_sha256`, extra keys (`baseline_commit`), slice omitting changed path/`new_blob[:8]`, unmentioned no-op/rollback row, CRLF working copy matching `git rev-parse :<path>` / `hash-object --path`. |
| `tests/tools/test_w9_detectors.py` — **Pin-advance comparison procedure & `main()` exit `2`** | `unit` (`ci.yml` `admission-controls`, `--pr-map` offline) | Every tool's `main()` wrapper catches uncaught exceptions and exits `2` (`--verdict-json` emits one JSON object with `"error"`); L-1 `baselines[0]` creation skips comparison while checking (i)–(iv); matching verdicts pass; named `V[:8] \| <rule> \| <path>` difference (including Rule 0 difference) passes while unnamed or malformed line fails; green-to-red Rules 1–3 difference with same-PR `acknowledged` passes; one-sided `ERROR` and **both sides failing identically (`ERROR`)** fail; advisory Rule 0.2 row report runs on pin-advance PRs without failing checks. |
| `tests/tools/test_w9_detectors.py` — **`acknowledged` & Rule 3 late-entry checks** | `unit` (`ci.yml` `admission-controls`) | Exact tuple exempt while sibling fails; backdated/same-commit ref fails; missing `independent_review` fails; missing late `shared-surface-changes.json` entry fails; empty `affected_registrations` without `"none derived"` fails; `"none derived"` in slice + `independent_review` passes; ack-only `pr_number: null` on unmapped commit passes while in-commit PR `pr_number: null` fails. |
| `tests/tools/test_w9_detectors.py` — **Rules 1–3, PR mapping, UTF-8 & CLI lockouts** | `unit` (`ci.yml` `admission-controls`) | Rule 1 exclusions & `legacy_manuscript_root` prefix match; mode-only change fails; H1 Working-Note append passes while task-row edit fails; retry/hint fallback & API exit `2`; non-ASCII PR title/body decoded under explicit UTF-8 without `UnicodeDecodeError`; `--baseline`/`--head`/`--pr-map`/`--manifest-file`/`--verdict-json`/`--acknowledged-from` exit `2` without `--ruleset-check skip`; `--classified-locks` exits `2` without `--candidate-file`; workflow YAML contains none. |
| `tests/tools/test_w9_detectors.py` — **Closure, stdlib, wrapper, CODEOWNERS, `L1_LIVE`, ruleset & pin assembly** | `unit` (`ci.yml` `admission-controls`) | `test_recorded_detector_import_closure_covers_ast_walk`; `test_detector_closure_is_stdlib_only` (21 runtime modules); `test_pinned_wrapper_is_self_contained_stdlib_only`; `test_derived_closure_tools_and_accepted_w9_are_codeowned` (aligned with Owner Point I on `w9_segmentation.py`); `main_ruleset` / D-8 (`--acknowledge-gap`, `ci-d8`); `L1_LIVE` tripwire (`yaml.BaseLoader`, `False` and synthetic `True` incl. `--verify-watched-to-fail`); scratch pin-heredoc tests: valid confined assembly + post-write `git hash-object --no-filters` + parent & child `[sys.executable, "-S", "-P", ...]` isolation pass (`research_system.cli` raises `ModuleNotFoundError`), while `../escape.txt`, `/escape.txt`, `C:/escape.txt`, `tools/a.py.`, `tools/a.py `, `tools/nul`, `tools/CON.py`, off-chain baseline, absent object, and empty/mismatched `W9_DETECTOR_PIN` under `REQUIRE_I3_PIN=true` all exit non-zero. |
| `tests/tools/test_w9_detectors.py` — **`W9-T7` scratch-clone replay** | `unit` (`ci.yml` `admission-controls`) | `~1.57–1.99s` bare clone; derives 10 `git diff-tree` paths of `5df0c001`/`811d5a2b`; T7-1 and T7-2 (`GIT_INDEX_FILE`) assert Rule 1 & Rule 2 exit `1`; checkout-scoped snapshot (`config`/`hooks/` from `--git-common-dir` in `CI=true` only). *(Recorded departure from `06v:230`, Owner Point F.)* |
| `tests/research_system/integration/test_w9_wp9_5_detectors.py` | `integration`, `@pytest.mark.slow` *(selected by `tools/affected_research_tests.py:120-147` on `research_system/`, `tests/research_system/`, or `.research-system/` edits only—NOT `tools/`-only edits; nightly in `research-system-suite.yml:8-9,15,17` `-m "not live_store"`)* | 1. **`M-6`:** scratch W9 control store + scratch Git repo; exports `w9-registration-manifest/2`; `--check` passes & store/manifest drift exits `1`.<br>2. **`O-13`:** runs `tools/run_w9_detector_controls.py` with `CONTROL_GIT_ENV`, UTF-8 decoding, and `-c` flags; verifies deterministic `output_sha256`, `--verify-watched-to-fail` with `--code-root` / `--repo-root` split + pinned wrapper execution (`python -S -P`), `require_detector_controls`, `LR-003`, and immutability snapshot. |

### 12.2 Fixture provenance rule (`06v:248-255`)

- No test reads live bytes from `C:\Users\steph\Documents\TDA-Research`, `C:\Users\steph\TDL\vault`, `papers/`, or `results/`.
- Baseline test verifies blob `4620c71607ca3a06c6df3b8e96a6bddffc783960` / SHA-256 `d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589` (`research_system/legacy/reader.py:43-49`).

### 12.3 Measured timings and test-time budget

Measured operations on this machine (Appendix A §21.1):
- `git clone --bare --local --no-hardlinks` (`58,133` objects, `28` packs, `335.09` MiB) + cleanup: **`1.57–1.99s`**.
- `segment(raw, "conventions_unit")` on `4620c716` (`33,645` B) and `dbd54fe3` (`51,774` B): **< `0.15s`**.
- Stdlib-only `python -S -P` execution: **zero package-install overhead** (no `uv sync`).
- **6-call Option C1 walk stand-ins (§21.1 item 10):** measured local `1x` post-merge stand-in timings are **`14.05s`** (`60` commits, 6 guarded), **`34.46s`** (`178` commits, 12 guarded), and **`62.84s`** (`320` commits, 22 guarded), with ~15% run-to-run noise (R5 reproduced `11.79s` / `34.85s` / `61.58s`) and excluding real rule evaluation + live `gh api` calls (`~11.3s` + backoff across 22 guarded commits in R5). For manual 2-tool comparison, `24.04s` was measured `2x` at 60 commits while `68.92s` and `125.68s` are **extrapolated (`2 × 1x`)**. **Pre-code / rehearsal walk stop rule:** **`600s`** applies to a single `1x` post-merge walk with real rules and `gh api` (§15.2 item 5), separate from Owner Point G's test-suite budget below; hosted `windows-latest` `1x` full-walk time is `UNVERIFIED-5`.

| Test file | Measured vs unmeasured wall-clock budget basis (`--no-cov`, serial, **including `@pytest.mark.slow`**) | Status |
|---|---|---|
| `tests/tools/test_w9_detectors.py` | Segmentation (`< 0.5s`) + synthetic Git/pin/comparison/wrapper controls (`< 5s`) + `W9-T7` bare scratch clone (`~1.57–1.99s` + `0.3s`) + under `L1_LIVE`: `--verify-watched-to-fail` (`< 2s`, synthetic/local controls) and CI-only `--git-common-dir` `config`/`hooks/` snapshot. (Runs no full-history walk; no `gh` calls.) | Runs on every PR in `ci.yml` `admission-controls` (`F1`). |
| `tests/research_system/integration/test_w9_wp9_5_detectors.py` | Scratch W9 store fixture timing for `M-6` and `O-13` (**`UNVERIFIED-3`**: unmeasured here). | Selected via `affected_research_tests.py`; full suite nightly in `research-system-suite.yml`. |

**Unconditional pre-code profiling step (`P-087` item 7, `03-decisions-and-open-questions.md:5919-5923`):** §15.1 item 4 **unconditionally** requires profiling one existing scratch-store test alone on Stephen's machine before code dispatch; **Owner Point G recommends Option G1 (`300s`)** for all new/changed WP9.5 tests (distinct from the pre-code `600s` `1x` full-walk stop rule, §15.2) until that measurement supports tightening to G2 (`120s`). Over-budget returns `PARTIAL`.

---

## 13. Research assurance

WP9.5 touches the **Output / Provenance** assurance lane (`CONVENTIONS.md:20-34`): legacy artifact immutability detection, shared-surface state invalidation detection, `CONVENTIONS.md` lock preservation, vault Computational-Log legacy entry integrity, and detector negative-control evidence hashes.

### 13.1 Machine-checkable claims and their enforcement artifacts

| # | Claim | Enforcement artifact (test / validator / schema) |
|---|---|---|
| MC-1 | Every `legacy_path_registration` record in the W9 control store matches `.research-system/evidence/w9/registration-manifest.json` (`w9-registration-manifest/2` under A1: `root_kind`, `root_id`, `normalized_path`, `role`, `source_identity_kind`) at `binding.binding["git_head"]` (§5.3). | `tools/export_w9_registration_manifest.py --check`; `test_w9_wp9_5_detectors.py` (`M-6`). |
| MC-2 | Confined 22-blob `python -S -P` assembly (trailing-dot/space/device refusal + post-write `git hash-object --no-filters`) executes **`1x`** post-merge walks from `baselines[0]["baseline_commit"]` using `baselines[-1]` (§6.2.3, §10.2); every tool wraps `main()` to exit `2` (`--verdict-json` emits `"error"`), and Rule 0 enforces monotonicity + `baselines` (i)–(iv) with **no Rule 0.3** and **no PR pin-advance gate** (pin advances attach manual `(baselines[0]["baseline_commit"], candidate]` diffs, §6.1, §6.2.2, §6.5). | `tools/check_legacy_writes.py` (Rule 0), workflow pin step, `test_detector_closure_is_stdlib_only`, `test_recorded_detector_import_closure_covers_ast_walk`, `test_pinned_wrapper_is_self_contained_stdlib_only`, `tests/tools/test_w9_detectors.py`. |
| MC-3 | Any guarded first-parent commit `C` after `baselines[0]["baseline_commit"]` changing a registered `git_tracked` `repository_root` legacy path without an in-commit W9 §4.2 record (`P1`-pre-existing `owner_note` + `independent_review` slices) or valid `acknowledged` entry exits `1` (§6.4, §6.5 Rule 1, §6.6). | `tools/check_legacy_writes.py` (Rule 1); `tests/tools/test_w9_detectors.py` (`W9-T7`). |
| MC-4 | Any first-parent commit `C` after `baselines[0]["baseline_commit"]` touching `results/` outside `results/ars/` without a matching §4.2 record at `C` (or valid `acknowledged` entry) exits `1` (§6.5 Rule 2). | `tools/check_legacy_writes.py` (Rule 2); `tests/tools/test_w9_detectors.py` (`W9-T7`). |
| MC-5 | Any first-parent commit `C` after `baselines[0]["baseline_commit"]` modifying a `shared_enforcement_surface` without both an in-commit §4.3 record + `shared-surface-changes.json` entry (or valid `acknowledged` row with `independent_review`, non-empty `affected_registrations`/slice `"none derived"`, ack-only `pr_number: null` when unmapped, and matching late `<head>:shared-surface-changes.json` entry compatible with `require_change_list`) exits `1` (§6.5 Rule 3, `O-32`). | `tools/check_legacy_writes.py` (Rule 3); `tests/tools/test_w9_detectors.py`. |
| MC-6 | `git --no-replace-objects diff-tree -r --no-renames -z <P1> <C>` detects first-parent changes on both 1-parent and 2-parent commits on `main`, failing closed on mode-only changes (§6.3). | `tools/check_legacy_writes.py`; `tests/tools/test_w9_detectors.py`. |
| MC-7 | Every legacy `conventions_unit` in `CONVENTIONS.md` from `4b143c92` (`4620c716`, provisional 68 units or pinned `ACCEPTED_CONVENTIONS_CLASSIFICATION` `(anchor_text, unit_hash)`) is preserved byte-for-byte in order, with no table inserted in a legacy-lock section (§7.3, §7.4). | `tools/check_conventions_legacy_locks.py`; `tests/tools/test_w9_detectors.py` (`W9-T19`, N1–N7). |
| MC-8 | Every legacy `"item"`/`"structural"` row in `ACCEPTED_CL_EXPORT[-1]` (`recheck_cl_export` `void == False`) is preserved byte-for-byte in order in `04-Methods/Computational-Log.md`, with 0 blockers across the live file while LF/CRLF prepended successor entries pass (§8.2, §8.3). | `tools/check_legacy_log_baseline.py`; `tests/tools/test_w9_detectors.py` (`W9-T19`, V1–V6). |
| MC-9 | All four detector controls emit deterministic `output_sha256` (`CONTROL_GIT_ENV`, `-c core.autocrlf=false -c commit.gpgsign=false`) bound to tool `git_blob_id` and `closure_blobs`, passing `evidence.require_detector_controls` and `--verify-watched-to-fail` with `--code-root`/`--repo-root` (§9.2). | `tools/run_w9_detector_controls.py` & `research_system/legacy/evidence.py:133-154`; `test_w9_wp9_5_detectors.py`. |
| MC-10 | While `L1_LIVE is False`, `legacy-write-detector.yml` has `on == {"workflow_dispatch"}` only and zero L-1 evidence files exist on `main`; when `True`, `on["push"]` filters `branches: ["main"]` and `admission-controls` runs `L1_LIVE`, F1 tests, `--verify-watched-to-fail`, optional K1, and optional advisory Rule 0.2 row report with zero PR-time pin-advance gate or `gh` call (§10.3). | `tests/tools/test_w9_detectors.py` (`yaml.BaseLoader`), in `ci.yml` `admission-controls` (`F1`) & CODEOWNERS (`I1`). |

### 13.2 Human-review-only claims and residual architectural limits

| # | Claim / Limit | Reviewer / Owner check and why not mechanized |
|---|---|---|
| HR-1 | **Semantic equivalence, review authenticity, and authorship of register/review entries:** | `check_legacy_writes.py` verifies `P1` ancestry & slices on `legacy-write-records.json` and `walk-baseline.json` (`03-decisions-and-open-questions.md`, `reviews/`, §6.2.2, §6.4). Because those directories are not CODEOWNED, **`P1` ancestry proves pre-PR age, not author identity**; authorship/semantics rest on human review + Option I1 CODEOWNERS on evidence (`W9:174-176`). |
| HR-2 | Completeness of `affected_registrations` in `shared-surface-changes.json` (incl. `B -> A` reverts, §6.5). | Deriving `affected_registrations` from binding tests requires Stephen and the independent reviewer (`W9:185-188`). |
| HR-3 | **Human-review trust root, deliberate pin lag, no machine gate on tool changes, post-merge Rule 0 permanence, and bypass cost (§6.1, §6.2.3, §16.1–§16.2):** | Ruleset `20822054` has `required_approving_review_count: 0`, so preventive control on CODEOWNED paths rests on human review + `.github/CODEOWNERS` (+ optional I3). Under Stephen's `2026-11-22` decision: (a) the pinned detector can lag production code until Stephen merges a pin advance (exiting `2` cleanly on format incompatibility), and (b) **no machine check gates a tool/closure change**—judged solely by Stephen's PR review + attached manual comparison diff (§6.2.2). A rare post-merge Rule 0 violation (affecting the post-merge detector only) remains permanently red across re-walks unless Owner Point C's narrow exemption row is chosen (§16.2). I1 bypasses need `Bypass reason:` (`tools/check_bypass_merges.py:41,135`, `admin-bypass-guard.sh:13-18`). |
| HR-4 | **Self-attestation of weekly vault Computational-Log runs (§8.4):** `vault-detector-runs.json` timestamps/hashes. | CI cannot access `C:\Users\steph\Documents\TDA-Research` to independently execute `tools/check_legacy_log_baseline.py`. |
| HR-5 | **30-day `rule-suites` window & D-8 bypass visibility (§4.1–§4.2):** `MAX_DAYS = 30`. | Fails closed past 30 days without `ruleset_gap_acknowledgements`; under D-8, direct `rule-suites` checks run locally pre-batch (`06v:571,603`). |
| HR-6 | **`CONVENTIONS.md` structural exceptions outside `conventions_unit` rows (§7.4):** `### ` sub-headings, `---`, blanks, H1, footer. | Editing legacy `### ` titles or moving bullets across `### ` sub-headings inside the same `## ` section relies on PR review (`wp9-5-note-r2-review-2026-11-21.md:123`). |
| HR-7 | **`tools/export_w9_registration_manifest.py` (M-6) runs unpinned from checkout (§2.1, §6.2.3):** | Imports `research_system/cli.py` (~161 modules), so excluded from 22-blob `$DETECTOR_DIR` assembly; CODEOWNED under I1 while `cli.py` imports rely on operator checkout. |

---

## 14. Claims for review

An independent adversarial reviewer should attack these 16 claims against `dbd54fe382e7b2849d3f2038393cbdb4d709477b`:

1. **No D-4 trigger (`P-089` item 1):** Zero W9 commands, runtime-binding rows (`275` rows, SHA-256 `82eab93a...451d58`), store append sites, or schema edits; `tools/w9_segmentation.py` (`43e1454de09b61e274954c42b21d6ae533857a24`) and `IMPORTER_MODULES` (`reader.py:42`) untouched (§2.2; `03-decisions-and-open-questions.md:6022-6025,6085-6099`).
2. **Pin, no lockstep, and `1x` post-merge execution (`2026-11-22` decision):** Option I1 CODEOWNERS (+ optional I3 `vars.W9_DETECTOR_PIN`), **no Rule 0.3**, **no PR pin-advance gate** in `admission-controls`, `1x` post-merge walks using `baselines[-1]` via confined `python -S -P` + `hash-object --no-filters`, `main()` exit `2`, and attached manual `(baselines[0]["baseline_commit"], candidate]` diffs (§6.1–§6.2, §6.5, §10.2, §13.2, §16.1–§16.2).
3. **Manifest `/2`, `require_registered`, & WP9.4 counts:** Option A1 updates `REGISTRATION_MANIFEST_FORMAT` (`"w9-registration-manifest/2"`, 5 closed keys, `cli.py:1648-1659`, `evidence.py:40,114-131`) + 4 test builders via dated WP9.3 amendment + review; WP9.4 production code untouched, leaving `wp9-4-1-record.md:114,130` re-recording to Stephen (§2.3, §5.3, §16.3).
4. **Rule 1 matching/exclusions:** Scoping Rule 1 & §6.6 to `repository_root` + `git_tracked` excluding `conventions_lock`, `shared_enforcement_surface`, `successor_results_root`, and `legacy_read_only_projection` avoids untracked/restricted/`results/ars/`/`CONVENTIONS.md` misfires (§6.5–§6.6).
5. **`.apm/tracker.md` Working Notes:** Option H1 checks `tracker_task_row` and `working_note_entry` (`segmentation.py:470-473`) byte equality + `[ \t]*\n` gaps (`#368`, `#388`, `#433`, §6.5, §16.9).
6. **§4.2 keying & `P1` provenance:** `(pr_number, normalized_path, old_blob, new_blob)` + `P1`-pre-existing slices binds without squash SHAs, conditional on Option I1 (`HR-1`, §6.4, §16.1, §16.4).
7. **2-parent diffs & modes:** `git --no-replace-objects diff-tree -r --no-renames -z <P1> <C>` handles 1- and 2-parent commits (`b132406e`) and fails closed on mode-only changes (§6.3).
8. **PR mapping, `5df0c001`/`811d5a2b`, & `W9-T7` lane:** `merge_commit_sha == C` (3 retries + hint, UTF-8, exit `2` on API failure, `--ruleset-check skip` locks debug flags) + `W9-T7` unit replay (`5df0c001` 11 files / 7 `results/`, `811d5a2b` 9 files / 3 manifests, recorded `06v:230` departure, §6.2.1, §6.3, §11.2, §16.7).
9. **Option D3 `O-32` & Rule 3 `acknowledged`:** `"w9-shared-surface-changes/2"` without commit SHA satisfies `require_change_list`/`acceptance.py:121-136` via `evidence.blob_at` (`evidence.py:179-218`); late entries require `independent_review`, non-empty `affected_registrations`/slice `"none derived"`, and `pr_number: null` on unmapped commits only (§6.5, `HR-2`, §16.5).
10. **Ruleset `20822054`, 30-day gap ack, & U-3:** Pinning 16 fields (`integration_id: 15368`) fails closed past 30 days without Rule-0-checked `ruleset_gap_acknowledgements`; U-3 probe tests `GITHUB_TOKEN` across all 3 endpoints (§4.1–§4.2).
11. **Vault junction refusal:** Because `open_registered_root_anchor` (`anchor.py:1934-1950`) allows `reject_reparse=False` and `LegacyReader.__init__` (`reader.py:241-248`) is lexical, `check_legacy_log_baseline.py` and `u4_dry_run.py` explicitly block symlinks/junctions/in-repo paths (§4.3.1–§4.3.3).
12. **`CONVENTIONS.md` counts & L-0b pin:** Parity (`4620c716` 70 -> `dbd54fe3` 90 units, 0 blockers), first-byte `|` filter, `HR-6`, and L-0b `ACCEPTED_CONVENTIONS_CLASSIFICATION` (`(anchor_text, unit_hash)`, N7) (§7.3–§7.6, §16.10).
13. **Vault classification & CRLF:** Reading `ACCEPTED_CL_EXPORT[-1]["classified_list"]` (`1..N`), failing closed on `void == True` or any live `blocker`, preserving legacy `raw_row_sha256` across Obsidian CRLF prepends (§8.2–§8.3, §16.10).
14. **D-5 cadence gate:** Strict `bool(reader.accepted_cl_export)` check at `LR-003`/`LR-015`/`LR-016`/`LR-020` with `"owner_cadence_reset"` recovery (§8.4, §16.6).
15. **Deterministic controls & dual roots:** Binding `git_blob_id`, `closure_blobs`, `CONTROL_GIT_ENV`, and `-c` flags with `--code-root`/`--repo-root` across `run_w9_detector_controls.py --verify-watched-to-fail` and `run_w9_pinned_detectors.py` (§9.2, §10.2, §12.1).
16. **PR wiring, CODEOWNERS, wrapper, & K1:** Wiring `tests/tools/test_w9_detectors.py` (`yaml.BaseLoader`), `test_derived_closure_tools_and_accepted_w9_are_codeowned`, `test_pinned_wrapper_is_self_contained_stdlib_only`, Option I1 (`w9_segmentation.py` & `"3.13"` sub-choices), and Option K1 (`check_conventions_legacy_locks.py` without PR pin-advance gate or `gh` call) (§2.3, §10.3, §16.1, §16.7, §16.11).

---

## 15. Stop rules for the code package

### 15.1 Hard preconditions before WP9.5 code is dispatched (`P-089` item 3, `03-decisions-and-open-questions.md:6104-6115`)

WP9.5 implementation code **must not** be dispatched until all four items below are complete (and item 5's unverified hosted wall time is acknowledged):

1. **U-3 recorded in §4.2.2 (§15.1 gate; `06v:159`):** Stephen authorizes the read-only U-3 throwaway draft-PR probe (§4.2.2); the reviewing session executes it, records HTTP statuses, `X-Accepted-GitHub-Permissions`, and pinned key presence for all 3 endpoints (`rulesets/20822054`, `rulesets/rule-suites`, `commits/dbd54fe3.../pulls`) in §4.2.2, and states whether D-8 applies to `rule-suites`.
2. **U-4 handle-bound reader and segmenter dry run recorded in §4.3.3 (`06v:160`):** Using the already-recorded metadata (`833,453` bytes, SHA-256 `73fcbe83...`), the reviewing session runs scratch script `u4_dry_run.py` (§4.3.3 item 2) against `C:\Users\steph\Documents\TDA-Research\04-Methods\Computational-Log.md` with `PYTHONPATH=.` from repo root and records `root_checks`, `bytes`, `sha256`, `link_count`, `canonical_target`, `file_facts`, `row_counts`, and `blockers` in §4.3.3.
3. **Remaining Owner Points I, C, A, B, D, E, F, G, H, J, K decided by Stephen (`P-090`):** Stephen has already decided the core pin design (**pin, no lockstep**, `2026-11-22`, to be entered in `P-090` with the other owner points). He records his disposition on the open choices across all 11 points (§16.1–§16.11, deciding **I** first) in `03-decisions-and-open-questions.md`, authorizing dated WP9.3 / `CONVENTIONS.md:713-729` / W9 §4.2 amendments as selected and verifying Actions variable write permissions (`UNVERIFIED-4`, §21.2) if Option I3 is chosen.
4. **Unconditional pre-code single scratch-store test timing profile (`P-087` item 7, `03-decisions-and-open-questions.md:5919-5923`):** Profile one existing WP9.3/WP9.4 single scratch-store integration test alone on Stephen's machine (`UNVERIFIED-3`, §21.2) before adding `test_w9_wp9_5_detectors.py`.
5. **Hosted `windows-latest` `1x` full-walk wall time (`UNVERIFIED-5`, §21.2):** Post-merge `1x` walk time with real rules and `gh api` PR mapping on hosted `windows-latest` (including ~60, ~178, and ~320-commit intervals) remains `UNVERIFIED-5` ahead of rehearsal and live activation, bounded by the `600s` pre-code walk stop rule below.

*(Pre-L-1 gate note: after WP9.5 code lands and before L-1 activation on `main`, execute a one-shot throwaway `pull_request` rehearsal using a separate throwaway workflow file differing from `.github/workflows/legacy-write-detector.yml` by running on `on: pull_request`, omitting the `refs/remotes/origin/main` fetch overwrite, and setting `MAIN_TIP="$GITHUB_SHA"` to read synthetic evidence from the PR head rather than `refs/remotes/origin/main` [closed without merging], followed after L-1 merge by a green `workflow_dispatch` run on the L-1 merge commit as an L-1 exit criterion, §10.2 item 5.)*

### 15.2 Stop rules during WP9.5 code implementation

The WP9.5 code worker must stop immediately and return `PARTIAL` if:
1. Any change would modify a protected identity listed in §2.2 (the 275-row runtime-binding census, `wp6_1_06h_current_append_manifest.yaml` blob `1066404a`, `test_wp6_1_06h_append_path_closure.py` blob `3b1eec6e`, `research_system/schema_registry.py` blob `e32cb408`, `research_system/authority.py` blob `9b56b322`, core/W9 schemas, T2 expectations/seal, `tools/w9_segmentation.py` blob `43e1454de09b61e274954c42b21d6ae533857a24`, or `IMPORTER_MODULES` in `research_system/legacy/reader.py:42`) (`06v:614,618-619`).
2. Any change under `research_system/legacy/` would exceed the specific changes approved by Stephen under Owner Points A, D, E, and J.
3. Any test or negative control needs live legacy, vault, or restricted bytes, or writes to / leaves any state in `REPO_ROOT`, any linked worktree, or `C:\Users\steph\Documents\TDA-Research` (`06v:616-617`).
4. The new and changed WP9.5 test files (including `@pytest.mark.slow` tests) exceed the approved serial `--no-cov` test-time budget (Owner Point G, which excludes full-history walks) on Stephen's machine (`P-087` item 7, `03-decisions-and-open-questions.md:5919-5923`).
5. **Pre-code / rehearsal `1x` walk stop rule (distinct from Owner Point G):** If one post-merge `1x` full walk with real rules and PR mapping exceeds **`600s` (10 minutes)** in rehearsal or pre-code smoke measurement, stop and return the question to Stephen for a **design amendment** (for example, hash-bound epoch advancement of `baselines[0]["baseline_commit"]` or Git/PR batching) rather than adding an unapproved runtime flag.
6. *(WP9.5-specific stop rule added by this design note, not in `06v` §8):* Any detector negative control fails to fire on its designated violation case or fires on a clean positive control case, `test_recorded_detector_import_closure_covers_ast_walk` detects an unpinned `research_system` or `tools` import, `test_detector_closure_is_stdlib_only` detects any non-stdlib / non-closure import, or `test_pinned_wrapper_is_self_contained_stdlib_only` fails.

---

## 16. Owner points

Stephen has already decided the core pin design (**pin, no lockstep**, `2026-11-22`, to be entered in `P-090` with the other owner points). His decision is requested on the remaining open choices across the eleven points below (**I** first—because **B**, **C**, and the L-1 guard depend on it—followed by **C, A, B, D, E, F, G, H, J, K**) before WP9.5 code is dispatched. Nothing in this note decides them for him.

### 16.1 Owner Point I *(decide first)* — Trust root protecting detector surface, closure, tripwire, and evidence directory

*Pointers:* §2.3, §6.1, §6.2.3, §10.2, §10.3.

- **Pin design — decided by Stephen, `2026-11-22` *(to be entered in `P-090` with the other owner points)*:** Keep 22-entry stdlib-only `python -S -P` content pin (`baselines[-1]["detector_closure_blobs"]`) + confinement + post-write `git hash-object --no-filters` verify + `main()` exit `2` (`ERROR`); **drop lockstep** (no Rule 0.3; unpinned closure edits are valid and runs use `baselines[-1]` until Stephen merges a pin advance); **remove PR-time pin-advance gates from `admission-controls`**; attach manual `(baselines[0]["baseline_commit"], candidate]` comparison diffs to pin-advance PRs; and walk `1x` post-merge. **What this gives up (§6.1, §13.2):** (a) pinned detectors can lag production code until advanced (exiting `2` loudly on incompatibility); (b) no machine gate checks tool changes—judged solely by Stephen's PR review + attached comparison diff.
- **Open choices (`Options`):**
  - **Option I1 (Rule 0 + `.github/CODEOWNERS` expansion — Recommended):** Enforce Rule 0 monotonicity (§6.5) and §6.2.3 confined `python -S -P` execution (`21` stdlib-only runtime modules + workflow; M-6 excluded -> `HR-7`), adding `@stephendor` CODEOWNERS for `/.github/workflows/legacy-write-detector.yml`, `/tools/check_legacy_writes.py`, `/tools/check_conventions_legacy_locks.py`, `/tools/check_legacy_log_baseline.py`, `/tools/run_w9_detector_controls.py`, `/tools/run_w9_pinned_detectors.py`, `/tools/export_w9_registration_manifest.py`, `/tools/_w9_detector_evidence.py`, `/tests/tools/test_w9_detectors.py`, `/research_system/legacy/accepted_w9.py` (plus `/tools/w9_segmentation.py` under `I1-include-seg`) and directory `/.research-system/evidence/w9/`, enforced by `test_derived_closure_tools_and_accepted_w9_are_codeowned`, `test_detector_closure_is_stdlib_only`, and `test_pinned_wrapper_is_self_contained_stdlib_only` (§12.1).
    - *Cost:* Requires Stephen's `Bypass reason:` merge (`tools/check_bypass_merges.py:41,135`, `admin-bypass-guard.sh:13-18`) on per-batch, weekly vault, ruleset-read, baseline/pin-advance, or code-owned closure PRs (`7` W9 PRs / 4 wk; `14` of `178` commits / 90 d touched the `15` existing modules; pin advances re-record `detector-controls.json` + attach comparison diff).
    - **`tools/w9_segmentation.py` sub-choice (`R5-m5`):** **`Option I1-include-seg` (Recommended):** add `/tools/w9_segmentation.py` (`11` file patterns + dir, `13` non-code-owned modules, `0` test exemption; `43e1454de09b61e274954c42b21d6ae533857a24` stays untouched). **`Option I1-exempt-seg`:** keep `10` file patterns (`14` non-code-owned) + explicit test exemption.
    - **`python-version` sub-choice (`R5-i2`):** **`Option I1-py-minor` (Recommended):** `"3.13"` so hosted `3.13.x` patches don't churn controls/pins; **`Option I1-py-patch`:** exact `"3.13.5"`.
  - **Option I2 (Rule 0 only; keep current 8 CODEOWNERS paths):** Leaves `L1_LIVE`, workflow, tools, `accepted_w9.py`, and evidence unprotected; insufficient for B1 and R1-B1 scenarios 4–5.
  - **Option I3 (Optional out-of-tree anchor, combinable with I1):** Repo Actions variable `W9_DETECTOR_PIN` (`{"walk_baseline_commit", "closure_blobs_sha256"}`), `REQUIRE_I3_PIN: "true"` in §10.2, read via `gh api` in wrapper (§6.2.3). Pin advances merge first -> failing push run until variable updated; Actions variable write permissions remain **`UNVERIFIED-4`** (§21.2).
- **Recommendation:** **Option I1** + **I1-include-seg** + **I1-py-minor** (+ optional **I3** after verifying `UNVERIFIED-4`).
- **What it changes & records needed:** `.github/CODEOWNERS:1-24`, split `tests/tools/test_ci_platform_policy.py` (`W9_DETECTOR_CODEOWNED_FILES`, `W9_DETECTOR_CODEOWNED_DIRS`, `:364-374` without `.is_dir()` on dir, landing all 9 new files together), **amend `CONVENTIONS.md:713-729`** (`## ARS Foundation Governance`, `614-783`), and `P-090` (`I3` also sets `W9_DETECTOR_PIN` at L-1).

### 16.2 Owner Point C — Committed `walk-baseline.json`, pre-baseline dispositions, `1x` post-merge walk, and post-merge Rule 0 recovery sub-choice

*Pointers:* §6.2.1, §6.2.2, §6.5, §10.3.

- **Fixed (`2026-11-22` decision, §6.2.2):** Post-merge runs walk **`1x`** from `baselines[0]["baseline_commit"]` using `baselines[-1]`; pin advances attach manual `(baselines[0]["baseline_commit"], candidate]` comparison diffs; `admission-controls` runs no PR pin-advance gate or `gh` call (§10.3).
- **Options:**
  - **Option C1 (Recommended):** Commit `.research-system/evidence/w9/walk-baseline.json` (`w9-walk-baseline/1`) from `baselines[0]["baseline_commit"]` (first-parent ancestor of L-1 on `main`, disposing `(4b143c92, baseline_commit]` via `P1` hash-bound `pre_baseline_dispositions_ref` refreshed at L-1), with 22-blob `detector_closure_blobs`, `acknowledged` (Rules 1–3; late `<head>:shared-surface-changes.json` + `independent_review` + ack-only `pr_number: null` when unmapped), and `ruleset_gap_acknowledgements`. Subject to `600s` pre-code `1x` walk stop rule (§15.2 item 5, `UNVERIFIED-5`; design amendment if exceeded).
  - **Option C2:** Set `baselines[0]["baseline_commit"]` to `4b143c9225035cc29e37351445f1c3a4ab09ceb1` and carry dispositions for all 22 historic commits (§6.2.1).
  - **Narrowed post-merge Rule 0 recovery sub-choice *(post-merge detector only, `R5-i1`)*:** On a rare post-merge Rule 0 violation on `main`: **`Option C-R0-exemption`** (narrow hash-bound exemption row `(commit, path, old_blob, new_blob)` + `P1` slice, **not specified or built in Revision 6**) vs **`Option C-R0-permanent`** (Rule 0 stays red across re-walks; `HR-3` §13.2).
- **Recommendation:** **Option C1** (contingent on I1) + Stephen's choice between **C-R0-exemption** and **C-R0-permanent**.
- **What it changes & records needed:** Dated row for `walk-baseline.json` in `docs/plans/agentic-research-system/implementation/06v-addendum-2026-11-10-w9-paths.md` and `P-090` (`P-09x` L-1 refresh); `research_system/legacy/` untouched.

### 16.3 Owner Point A — Registration manifest fields (`role`, `source_identity_kind`), `/2` format policy, and WP9.4 pass-count question

*Pointers:* §2.3, §5.3.

- **Options:**
  - **Option A1 (5-key manifest, uniform `"w9-registration-manifest/2"`, closed entries — Recommended):** Bump `REGISTRATION_MANIFEST_FORMAT` to `"w9-registration-manifest/2"` projecting `{"root_kind", "root_id", "normalized_path", "role", "source_identity_kind"}` in `_legacy_projection`, update `require_registered` (`evidence.py:40,114-131`), and update fixture manifest builders in `test_w9_evidence.py`, `w9_runtime_harness.py:451-466`, `test_w9_wp9_4_1_runtime.py:95-109`, and `test_w9_wp9_4_2_runtime.py:86-100`. Because WP9.4 production code is untouched, this note treats WP9.4's acceptance review as not reopened; **Stephen must decide whether `wp9-4-1-record.md:114,130` pass counts (`13 passed in 688.11s (0:11:28)`) are re-recorded after updating the test builders** (re-running both WP9.4 integration files counts against Owner Point G).
  - **Option A2:** Keep `/1` (3 keys, `evidence.py` and WP9.4 tests untouched) and add an unvalidated companion file.
- **Recommendation:** **Option A1** (with Stephen's decision on re-recording `wp9-4-1-record.md:114,130` pass counts).
- **What it changes & records needed:** Edits `evidence.py:40,114-131` and the 4 test files; needs a **dated WP9.3 amendment, independent review, and `P-090`** (`IMPORTER_MODULES` untouched).

### 16.4 Owner Point B — W9 §4.2 write-allowance record format, `at C` evaluation, and `P1` age provenance

*Pointers:* §6.4, `HR-1`.

- **Options:**
  - **Option B1 (Recommended, conditional on Option I1):** Commit `.research-system/evidence/w9/legacy-write-records.json` (`w9-legacy-write-records/1`) keyed by `(pr_number, normalized_path, old_blob, new_blob)` evaluated at `C`, with `P1`-ancestor `owner_note` (`### P-0xx` naming each tuple) and `independent_review` slices (`P1` ancestry proves pre-PR age rather than authorship because register/review directories are not code-owned).
  - **Option B2:** Allow `owner_note`/`independent_review` inside `C` itself under Option I1 CODEOWNERS.
  - **Option B3:** Parse PR bodies/comments via `gh api` (not offline-testable).
- **Recommendation:** **Option B1 — conditional on Option I1**.
- **What it changes & records needed:** Adds a dated row for `legacy-write-records.json` in `06v-addendum-2026-11-10-w9-paths.md:14-15` and `P-090`; `research_system/legacy/` untouched.

### 16.5 Owner Point D — Resolving the `O-32` squash-merge SHA contradiction in `shared-surface-changes.json`

*Pointers:* §6.5 (Rule 3), `HR-2`.

- **Options:**
  - **Option D3 (Blob-keyed, tree-state equivalence, `"w9-shared-surface-changes/2"`, no commit field — Recommended):** Bump `SHARED_SURFACE_CHANGES_FORMAT` (`evidence.py:42`) to `"w9-shared-surface-changes/2"` closed on `{"pr_number", "surface", "old_blob", "new_blob", "affected_registrations"}` (with ack-only `pr_number: null` on unmapped commits), require late `<head>` entries + `independent_review` on Rule 3 acknowledgements (safely checked via `require_change_list` at `evidence.py:190-218`), and check `evidence.blob_at(repository_root, obs_commit, surface)` in `acceptance.py:121-136` against `new_blob` or a later entry (see `HR-2` on `A -> B -> A` reverts).
  - **Option D1:** Add `base_commit` + blob check (queue race, redundant).
  - **Option D2:** Two-PR protocol leaving a red window.
- **Recommendation:** **Option D3**.
- **What it changes & records needed:** Edits `evidence.py:42,190-252`, `acceptance.py:121-136`, WP9.3 tests (`test_w9_evidence_acceptance.py`, `test_w9_wp9_3_2_runtime.py`), and `06v-addendum-2026-11-10-w9-paths.md:28`; needs a **dated WP9.3 amendment (`wp9-3-design-note.md` §10.4), independent review, and `P-090`** (`IMPORTER_MODULES` untouched).

### 16.6 Owner Point E — D-5 missed weekly vault-run gate placement and weekly PR + `advance-binding` cost

*Pointers:* §8.4, `HR-4`.

- **Options:**
  - **Option E1 (Store-preparer gate at `LR-003`/`LR-015` and `LR-016`/`LR-020` — Recommended):** Commit `vault-detector-runs.json` (`w9-vault-detector-runs/1`) with `"run"` / `"owner_cadence_reset"` entries and enforce `require_vault_detector_cadence` when `bool(reader.accepted_cl_export)` is `True` at `LR-003`/`LR-015` (`preparers.py:686-690,1215-1218`) and `LR-016`/`LR-020` (`acceptance.py:147-152`) plus `--check-cadence` (each weekly run needs a reviewed PR + I1 bypass merge + `ars store advance-binding`).
  - **Option E2:** CLI `--check-cadence` only (`preparers.py` and `acceptance.py` untouched).
- **Recommendation:** **Option E1** if weekly PR + `advance-binding` cost is accepted so D-5 is machine-enforced at batch start.
- **What it changes & records needed:** E1 edits `evidence.py`, `preparers.py`, `acceptance.py`, and `06v-addendum-2026-11-10-w9-paths.md`, needing a **dated WP9.3 amendment, independent review, and `P-090`**.

### 16.7 Owner Point F — Running `tests/tools/test_w9_detectors.py` (`L1_LIVE` & `W9-T7` unit lane) in `admission-controls`

*Pointers:* §2.3, §10.3, §11.2, §12.1.

- **Options:**
  - **Option F1 (Wire into `.github/workflows/ci.yml` `admission-controls` — Recommended):** Add `tests/tools/test_w9_detectors.py` to `ci.yml:166-216` (`admission-controls`, precedent `:210`) and `ADMISSION_CONTROL_MODULES` (`test_ci_platform_policy.py:175-229`, precedent `:226`). Covers the `L1_LIVE` tripwire, unit tests + `--verify-watched-to-fail`, optional advisory-only Rule 0.2 row report, and **`W9-T7` as a `unit` test on every PR — an explicit departure from `06v:230,503` ("`W9-T7` ... `integration, slow`")** while `test_w9_wp9_5_detectors.py` remains `integration, @pytest.mark.slow` (`affected_research_tests.py:120-147`; nightly `research-system-suite.yml:8-9,15,17`). **Nothing in `admission-controls` calls `gh`, requires `GH_TOKEN`, adds `pull-requests: read`, runs a PR-time pin-advance gate, or changes `ci.yml`'s `permissions: contents: read` or `timeout-minutes: 20`.**
  - **Option F2:** `legacy-write-detector.yml` only (no pre-L-1 PR tripwire).
- **Recommendation:** **Option F1** paired with **Option I1** (so `L1_LIVE` is code-owner protected).
- **What it changes & records needed:** Edits `.github/workflows/ci.yml:212` (`.github/CODEOWNERS:18`, Stephen merges), `tests/tools/test_ci_platform_policy.py:228`, a **dated addendum row in `06v-addendum-2026-11-10-w9-paths.md` (or `06v` addendum)** recording the `W9-T7` unit-lane departure from `06v:230`, and `P-090`.

### 16.8 Owner Point G — Test-time budget for WP9.5 (including `@pytest.mark.slow`)

*Pointers:* §12.3, §15.1 item 4.

- **Options:**
  - **Option G1 (Recommended pending profile):** Apply the **300-second (5-minute)** serial `--no-cov` budget from `P-087` item 7 (`03-decisions-and-open-questions.md:5919-5923`), counting all new/changed WP9.5 tests including `@pytest.mark.slow` (excluding full-history walks, which are governed separately by the `600s` pre-code walk stop rule in §15.2 item 5; over-budget returns `PARTIAL`; note WP9.4 integration files run ~5–11 minutes if re-run under A1).
  - **Option G2:** Tighten to **120 seconds (2 minutes)** once the unconditional pre-code single scratch-store profile (`UNVERIFIED-3`) is measured.
- **Recommendation:** **Option G1 (`300s`)** until `UNVERIFIED-3` is measured on Stephen's machine.
- **What it changes & records needed:** Recorded in `P-090`; changes no code.

### 16.9 Owner Point H — Routine `.apm/tracker.md` Working-Note appends after registration

*Pointers:* §6.2.1, §6.5 (Rule 1).

- **Options:**
  - **Option H1 (Mechanically verified Working-Note append allowance — Recommended):** Permit `.apm/tracker.md` changes without a §4.2(b) record iff `segment(raw, "tracker_task_row")` and `segment(raw, "working_note_entry")` (`segmentation.py:470-473`) verify every task row, byte outside `## Working Notes`, and prior note stays byte-identical in order with 0 blockers and gaps matching `[ \t]*\n` (`#368`, `#388`, `#433` verified in `wp9-5-note-r2-review-2026-11-21.md:219`; open `O-33` windows still wait).
  - **Option H2:** Require a full §4.2(b) record in `legacy-write-records.json` per append.
  - **Option H3:** Freeze `.apm/tracker.md` at L-1 and write successor notes elsewhere.
- **Recommendation:** **Option H1** (or **Option H3** if Stephen prefers freezing `.apm/tracker.md`).
- **What it changes & records needed:** H1 requires a **dated W9 §4.2 amendment** (`09-migration-compatibility-and-pilot.md` §4.2 and `P-090`), implemented in `tools/check_legacy_writes.py`; `H2`/`H3` need no W9 amendment.

### 16.10 Owner Point J — Source, format, and L-0b pinning of vault and `CONVENTIONS.md` classifications

*Pointers:* §7.3, §7.6, §8.2, §8.3.

- **Options:**
  - **Option J1 (`w9-cl-classified-list/1` + pinned `ACCEPTED_CONVENTIONS_CLASSIFICATION` — Recommended):** Validate `ACCEPTED_CL_EXPORT[-1]["classified_list"]` (`accepted_w9.py:86-88`) against `"w9-cl-classified-list/1"` with 1-based `row_ordinal` (`evidence.py:347-358`, `segmentation.py:408`), and add empty `ACCEPTED_CONVENTIONS_CLASSIFICATION = ()` to `accepted_w9.py` (defaulting to the 9-section 68-unit baseline until L-0b pins `"w9-conventions-classified-locks/1"` by `(anchor_text, unit_hash)` `segmentation.py:391-402` at its pinned commit).
  - **Option J2:** Carry final labels inside `w9-cl-export/1` at L-0b and keep 9 `CONVENTIONS.md` sections permanent.
- **Recommendation:** **Option J1** (preserving D-4 and `IMPORTER_MODULES`, CODEOWNED under Option I1).
- **What it changes & records needed:** Adds `ACCEPTED_CONVENTIONS_CLASSIFICATION` to `research_system/legacy/accepted_w9.py` and populates both constants + `06v-addendum-2026-11-10-w9-paths.md` at L-0b; recorded in `P-090`.

### 16.11 Owner Point K — Running `tools/check_conventions_legacy_locks.py` on PRs in `ci.yml` `admission-controls` (`06v:491-492`)

*Pointers:* §7.5.

- **Options:**
  - **Option K1 (Add to `ci.yml` `admission-controls` — Recommended):** Run `tools/check_conventions_legacy_locks.py` (`< 0.15s`) in `admission-controls` on every PR with zero ruleset change (`06v:491-492`). *Qualification:* at PR time the check runs from the PR head, so a PR that simultaneously modifies a non-code-owned closure module (such as `segmentation.py`) judges itself until the pinned post-merge run.
  - **Option K2:** Keep post-merge CI, operator pre-batch wrapper, and unit tests only.
- **Recommendation:** **Option K1**.
- **What it changes & records needed:** Adds one step inside `ci.yml` `admission-controls` (`.github/CODEOWNERS:18`) and records `P-090`.

---

## 17. Change log

| Revision | Date | Author | Summary |
|---|---|---|---|
| Revision 1 | 2026-11-21 | Gemini agent (under `P-089`) | Initial draft of the WP9.5 design note (`65363e27`) for independent adversarial review. |
| Revision 2 | 2026-11-21 | Gemini agent (under `P-089`) | Rework addressing revision 1 findings (`R1-B1`, `R1-M1`–`R1-M12`, `R1-m1`–`R1-m14`, `R1-i1`–`R1-i6`) from `docs/plans/agentic-research-system/reviews/wp9-5-note-r1-review-2026-11-21.md` (`edb9acc6`). |
| Revision 3 | 2026-11-21 | Gemini agent (under `P-089`) | Revision addressing all 27 findings (`R2-M1`–`R2-M5`, `R2-m1`–`R2-m16`, `R2-i1`–`R2-i6`) from `docs/plans/agentic-research-system/reviews/wp9-5-note-r2-review-2026-11-21.md` (`3cf35bec`). |
| Revision 4 | 2026-11-22 | Gemini agent (under `P-089`) | Narrow rework addressing all 20 findings (`R3-M1`–`R3-M3`, `R3-m1`–`R3-m13`, `R3-i1`–`R3-i4`) from `docs/plans/agentic-research-system/reviews/wp9-5-note-r3-review-2026-11-21.md` (`1bd4ecff`). |
| Revision 5 | 2026-11-22 | Gemini agent (under `P-089`) | Narrow rework & structural cut addressing all 21 findings (`R4-M1`–`R4-M2`, `R4-m1`–`R4-m11`, `R4-i1`–`R4-i8`) from `docs/plans/agentic-research-system/reviews/wp9-5-note-r4-review-2026-11-22.md` (`0e6d23e4`). |
| Revision 6 | 2026-11-22 | Gemini agent (under `P-089`) | Implemented Stephen's `2026-11-22` **pin, no lockstep** decision and resolved all 20 findings (`R5-M1`–`R5-M3`, `R5-m1`–`R5-m11`, `R5-i1`–`R5-i6`) from `docs/plans/agentic-research-system/reviews/wp9-5-note-r5-review-2026-11-22.md` (`d6938710`): deleted Rule 0.3 & PR-time pin-advance gates from `admission-controls` (no `gh`/`GH_TOKEN`/`pull-requests: read`), documented manual `(baselines[0]["baseline_commit"], candidate]` comparison review evidence (Rule 0 included, `V[:8] \| rule \| path`, `--verdict-json` `"error"`), aligned `w9_segmentation.py` & `"3.13"` Owner Point I sub-choices, added `main()` exit `2`, UTF-8 subprocess decoding, Windows device/trailing-dot/post-write hash checks, parent+child `-S -P` probe, wrapper pipe test, labelled extrapolated `2 × 1x` timings, compacted `§18`–`§20`, and updated `§21`. |

---

## 18. Compact disposition index: revisions 1 to 4

Full historical details for revisions 1–4 live in Git history and the archived review reports (`wp9-5-note-r1-review-2026-11-21.md` `edb9acc6`, `wp9-5-note-r2-review-2026-11-21.md` `3cf35bec`, `wp9-5-note-r3-review-2026-11-21.md` `1bd4ecff`). Compact disposition of all 81 findings (34 revision-1, 27 revision-2, 20 revision-3):

| Finding ID | Section(s) | Status |
|---|---|---|
| `R1-B1` | `§6.1, §6.2.2, §6.4, §6.5, §10.2, §12.1, §16.1–§16.2, §16.4` *(pinning iterated in §18 `R3-M1`, §19 `R4-M1`/`R4-M2`, & §20)* | resolved |
| `R1-M1` | `§4.3.1, §4.3.3, §8.2` | resolved |
| `R1-M2` | `§2.1–§2.3, §4.3.1–§4.3.2, §5.3, §7.2, §8.2–§8.3, §9.2` | resolved |
| `R1-M3` | `§6.2.1, §6.5, §7.3, §7.5, §11.2, §12.1, §16.2, §21.1` | resolved |
| `R1-M4` | `§5.3, §6.5 (Rule 1), §6.6, §16.3` | resolved |
| `R1-M5` | `§6.5 (Rule 1), §7.1, §16.9` | resolved |
| `R1-M6` | `§2.3, §6.5 (Rule 3), §16.5` | resolved |
| `R1-M7` | `§2.3, §10.3, §16.7` | resolved |
| `R1-M8` | `§2.3, §8.4, §13.2 HR-4, §16.6` | resolved |
| `R1-M9` | `§7.3, §8.2, §8.3, §16.10` | resolved |
| `R1-M10` | `§6.4, §6.5 Rule 0, §13.2 HR-1/HR-3, §16.1, §16.4` | resolved |
| `R1-M11` | `§4.2.1, §4.2.2, §10.2, §21.2` | resolved |
| `R1-M12` | `§6.2.1, §6.2.2, §14, §16.2, §21.1` | resolved |
| `R1-m1` | `§4.2.3` | resolved |
| `R1-m2` | `§4.1, §12.1, §13.2 HR-5` | resolved |
| `R1-m3` | `§11.3, §12.1` | resolved |
| `R1-m4` | `§9.2, §10.3, §12.1` | resolved |
| `R1-m5` | `§6.3, §6.6, §12.1` | resolved |
| `R1-m6` | `§6.3, §10.2, §12.1` | resolved |
| `R1-m7` | `§10.2` | resolved |
| `R1-m8` | `§4.3.3, §8.2, §8.5, §15.1` | resolved |
| `R1-m9` | `§2.1, §2.2, §5.1, §5.3` | resolved |
| `R1-m10` | `§2.3, §5.3, §16.3` | resolved |
| `R1-m11` | `§7.4, §7.6` | resolved |
| `R1-m12` | `§14` | resolved |
| `R1-m13` | `Header, §8.2, §15.2` | resolved |
| `R1-m14` | `§11.2, §12.3, §16.8, §21.1, §21.2` | resolved |
| `R1-i1` | `§6.5 (Rule 2)` | resolved |
| `R1-i2` | `§6.3, §12.1` | resolved |
| `R1-i3` | `§4.1, §4.2.1–§4.2.3, §13.2 HR-5, §21.1` | resolved |
| `R1-i4` | `§7.4` | resolved |
| `R1-i5` | `§6.3` | resolved |
| `R1-i6` | `§6.4, §6.6` | resolved |
| `Review §2 (R1)` | `Repo-wide citations (corrected across R2 & R3 -> R2-m2/R2-m4)` | resolved |
| `R2-M1` | `§6.1, §6.2.2, §6.3, §6.5, §10.2` *(`tool_pin_commit` & detached worktree superseded in `R3-M1` & §19 `R4-m7`)* | superseded |
| `R2-M2` | `§6.2.2, §6.5, §12.1, §16.2` *(`checkpoints`, `--record-checkpoint`, `--full-rewalk`, `verdict_digest` superseded in `R3-M2`, §19 `R4-M1`, & §20)* | superseded |
| `R2-M3` | `§2.3, §6.2.3, §6.5, §10.2, §12.1, §15.2, §16.1, §21.1` | resolved |
| `R2-M4` | `§2.3, §6.5, §7.3, §7.6, §12.1, §16.10` | resolved |
| `R2-M5` | `§2.3, §10.3, §13.2 HR-1, §16.1` | resolved |
| `R2-m1` | `§6.2.1, §14, §16.2, §21.1` | resolved |
| `R2-m2` | `§2.2` | resolved |
| `R2-m3` | `§4.3.3, §7.3–§7.4, §8.2–§8.3, §12.1, §16.10` | resolved |
| `R2-m4` | `Header, §2.2, §2.3, §6.5, §16.1, §21.1` | resolved |
| `R2-m5` | `§10.2, §10.3` | resolved |
| `R2-m6` | `§4.2.2, §15.1, §21.2` | resolved |
| `R2-m7` | `§4.3.3, §15.1, §21.2` | resolved |
| `R2-m8` | `§9.2, §12.1` | resolved |
| `R2-m9` | `§4.1, §12.1, §14` | resolved |
| `R2-m10` | `§6.4, §14, §16.4` | resolved |
| `R2-m11` | `§2.3, §5.3, §6.5, §12.1, §16.3, §16.5` | resolved |
| `R2-m12` | `§8.2, §8.5, §12.1` | resolved |
| `R2-m13` | `§12.1, §12.3, §15.1, §16.7, §16.8, §21.2` | resolved |
| `R2-m14` | `§6.2.2, §16.2` | resolved |
| `R2-m15` | `§6.2.1, §6.5 (Rule 1), §14, §16.9` | resolved |
| `R2-m16` | `§11.3, §12.1` | resolved |
| `R2-i1` | `§6.3` | resolved |
| `R2-i2` | `§7.4, §13.2 HR-6` | resolved |
| `R2-i3` | `§4.1` | resolved |
| `R2-i4` | `§8.2` | resolved |
| `R2-i5` | `§4.2.2, §14, §21.1` | resolved |
| `R2-i6` | `§12.3, §21.1` | resolved |
| `R3-M1` | `Header, §1, §2.3, §6.1, §6.2.2–§6.2.3, §6.5, §10.2, §12.1, §13.1, §14, §16.1–§16.2, §21.1` *(`uv sync`/`pyproject.toml`/`uv.lock` superseded in §19 `R4-M2`/`R4-m7`)* | superseded |
| `R3-M2` | `§1, §2.1, §6.2.2, §6.5, §12.1, §12.3, §14, §16.2, §21.1` *(Rule 0.2 (v) & dual-tool post-merge walk superseded in §19 `R4-M1` & §20)* | superseded |
| `R3-M3` | `§1, §6.2.2, §6.5, §12.1, §13.1, §14, §16.2, §16.5` | resolved |
| `R3-m1` | `Header, §10.2, §15.1, §16.1, §21.2` | resolved |
| `R3-m2` | `§1, §2.1, §2.3, §6.2.3, §7.5, §8.4, §9.2, §10.2, §12.1, §16.1, §16.10` | resolved |
| `R3-m3` | `§6.2.3, §13.2 HR-3, §16.1` | resolved |
| `R3-m4` | `§1, §2.1, §11.2, §12.1, §12.3, §13.1, §14, §16.2, §16.7` | resolved |
| `R3-m5` | `§1, §12.3, §15.1, §16.8, §21.2` | resolved |
| `R3-m6` | `§4.3.3, §14, §15.1, §21.2` | resolved |
| `R3-m7` | `Header, §1, §9.2, §12.3, §13.1, §14, §16.7, §21.1` | resolved |
| `R3-m8` | `§1, §11.3` | resolved |
| `R3-m9` | `§2.3, §4.2.2, §6.2.3, §8.4, §13.2, §16.1` | resolved |
| `R3-m10` | `§6.2.2, §16.2` | resolved |
| `R3-m11` | `§4.1, §6.2.2, §6.5, §12.1, §14, §16.2` | resolved |
| `R3-m12` | `§10.2, §12.1, §15.1` | resolved |
| `R3-m13` | `§2.3, §5.3, §14, §16.3` | resolved |
| `R3-i1` | `§1, §10.3, §13.1, §14` | resolved |
| `R3-i2` | `§1, §7.5, §15.1, §16.11` | resolved |
| `R3-i3` | `§10.2` | resolved |
| `R3-i4` | `§4.2.2, §21.1` | resolved |

---

## 19. Change log: revision 4 to revision 5

Archived review details for revision 4 (`48b5e935`) live in `docs/plans/agentic-research-system/reviews/wp9-5-note-r4-review-2026-11-22.md` (`0e6d23e4`). Compact disposition of all 21 revision-4 findings (with `R4-M1` and `R4-M2` superseded by Stephen's `2026-11-22` **pin, no lockstep** decision in `§20`):

| Finding ID | Section(s) | Status |
|---|---|---|
| `R4-M1` | `§1, §6.2.2, §6.5, §10.3, §12.1, §12.3, §13.1, §14, §15.1, §15.2, §16.2, §21.1, §21.2` *(PR-time verdict comparison superseded in §20 `R5-M1`–`R5-M3` by manual review diff + `1x` post-merge walk)* | superseded |
| `R4-M2` | `§1, §6.2.2–§6.2.3, §6.5, §10.3, §12.1, §13.1–§13.2, §14, §16.2` *(PR-lane `HEAD:<path>` equality / row checks & Rule 0.3 lockstep superseded in §20 `R5-M1`–`R5-M3`)* | superseded |
| `R4-m1` | `§1, §6.2.2, §6.5, §12.1, §13.1, §14, §16.2, §16.5` | resolved |
| `R4-m2` | `§12.1` | resolved |
| `R4-m3` | `§6.2.3, §10.2, §12.1` | resolved |
| `R4-m4` | `§2.1, §6.2.3, §13.2, §16.1, §21.1` | resolved |
| `R4-m5` | `§9.2, §10.2, §12.1, §13.1, §14` | resolved |
| `R4-m6` | `§6.2.3, §12.1, §14, §16.1` | resolved |
| `R4-m7` | `§1, §2.1, §2.3, §6.2.2–§6.2.3, §10.2, §12.1, §12.3, §13.1, §14, §16.1, §21.1` | resolved |
| `R4-m8` | `§10.2, §15.1` | resolved |
| `R4-m9` | `§11.3, §12.1` | resolved |
| `R4-m10` | `§3, §6.1, §6.2.3, §11.2, §12.1, §16.1, §16.7, §18, §19` | resolved |
| `R4-m11` | `§6.2.3` *(Option I1-narrow deleted in R6 §20 `R5-M1`)* | resolved |
| `R4-i1` | `§6.2.2, §6.5, §10.3, §12.1` | resolved |
| `R4-i2` | `§7.5, §14, §16.11` | resolved |
| `R4-i3` | `§2.3, §5.3, §14, §16.3, §16.8` | resolved |
| `R4-i4` | `§6.2.2, §12.1` | resolved |
| `R4-i5` | `§6.2.3, §10.2, §16.1` | resolved |
| `R4-i6` | `§6.2.2, §13.2, §16.2` | resolved |
| `R4-i7` | `§4.2.2, §21.1` | resolved |
| `R4-i8` | `Header, §1, §6.2.1, §13–§20` | resolved |

---

## 20. Change log: revision 5 to revision 6

Disposes of all 20 findings in `docs/plans/agentic-research-system/reviews/wp9-5-note-r5-review-2026-11-22.md` (`d6938710`, reviewing revision 5 `83b4ae6f`) alongside Stephen's `2026-11-22` **pin, no lockstep** decision (*to be entered in `P-090` with the other owner points*):

| Finding ID | Section(s) | Status | Change in revision 6 |
|---|---|---|---|
| `R5-M1` | `Header, §1, §2.1, §6.1, §6.2.2–§6.2.3, §6.5, §10.3, §12.1, §13.1, §13.2 HR-3, §14, §16.1–§16.2` | resolved | Applied Stephen's `2026-11-22` **pin, no lockstep** decision: removed Rule 0.3, `I1-narrow`, & all PR pin-advance gates from `admission-controls` (no bypassable PR gate); moved `(baselines[0]["baseline_commit"], candidate]` comparison to manual PR review evidence; `1x` post-merge walk on `baselines[-1]`; stated trade-offs in `§6.1`, `HR-3`, `§16.1`. |
| `R5-M2` | `§6.2.2, §6.5, §12.1, §13.2 HR-3, §16.2` | resolved | Included Rule 0 (`Rule 0.1`/`Rule 0.2`) inside `--verdict-json` comparison verdicts (no Rule 0.3 or Rule 0.2 (v) nesting); Rule 0 changes refused in review (`acknowledged` is Rules 1–3 only); `HR-3`/§16.2 permanence scoped to post-merge Rule 0 violations. |
| `R5-M3` | `§1, §2.1, §10.3, §12.3, §13.1, §16.7` | resolved | Removed PR `HEAD:<path>` blob checks, gating row checks, & verdict comparison from `admission-controls` per Follow-up 5 §1.6: zero `gh` calls, `GH_TOKEN`, `pull-requests: read`, or `timeout-minutes: 20` changes needed; completed Owner Point F (`F1`). |
| `R5-m1` | `§2.1, §6.2.2, §6.3, §9.2, §12.1, §13.1` | resolved | Wrapped `main()` to exit `2` (`ERROR`) across all WP9.5 tools; `--verdict-json` always emits JSON with `"error"` on fail; any `ERROR` (incl. both tools failing identically) fails comparison; tests in §12.1. |
| `R5-m2` | `§6.2.2, §6.5, §12.1` | resolved | Enforced line-by-line `V[:8] \| <rule> \| <path>` slice matching; required same-PR `acknowledged` row for Rules 1–3 green-to-red differences needing post-merge clearing. |
| `R5-m3` | `§6.2.2, §12.3, §15.1–§15.2, §16.2, §16.8` | resolved | Scoped `600s` strictly as pre-code/rehearsal `1x` walk stop rule (distinct from G1 `300s` suite budget, which excludes full walks); remedy = design amendment, never mutating `baselines[0]`. |
| `R5-m4` | `§6.2.2, §12.1` | resolved | Clarified L-1 row `0` creation skips prior-vs-new comparison and checks Rule 0.2 (i)–(iv) only; test added in §12.1. |
| `R5-m5` | `§2.3, §6.1, §6.2.3, §12.1, §14, §16.1` | resolved | Added `Option I1-include-seg` (Recommended: 11 files, 0 exemption) vs `I1-exempt-seg` (10 files + exemption) for `/tools/w9_segmentation.py` across §2.3, §6, §12.1, §14, §16.1. |
| `R5-m6` | `§2.1, §6.2.3, §12.1, §14, §15.2, §16.1, §21.1` | resolved | Specified `run_w9_pinned_detectors.py` as self-contained stdlib-only (`test_pinned_wrapper_is_self_contained_stdlib_only`), invoked via `git fetch ... && git show ... \| python -S -P - --repo-root .` (§21.1 tested). |
| `R5-m7` | `§6.2.3, §10.2, §12.1, §13.1` | resolved | Rejected trailing dot/space & Windows device names (`CON`..`LPT9`), added `dest.is_file()` + `git hash-object --no-filters` post-write check in §10.2 heredoc, and added §12.1 tests. |
| `R5-m8` | `§6.2.3, §9.2, §12.1, §21.1` | resolved | Required explicit child spawn `[sys.executable, "-S", "-P", ...]` and extended §21.1 item 9 probe with parent+child `-S -P` checks. |
| `R5-m9` | `§2.1, §6.3, §9.2, §12.1` | resolved | Required explicit `encoding="utf-8"` on all `git`/`gh` subprocesses and added non-ASCII PR UTF-8 test in §12.1. |
| `R5-m10` | `Header, §1, §2.1, §6.2.2, §12.3, §13.1, §14, §21.1` | resolved | Labelled `68.92s`/`125.68s` as **extrapolated (`2 × 1x`)**, recorded R5 stand-ins & `~11.3s` live `gh api` timing in §21.1, and replaced stale `walk_start` outside §18–§20. |
| `R5-m11` | `§6.2.1, §12.1, §13.1, §14, §18–§20` | resolved | Compacted `§6.2.1`, split §12.1's 4,348-char row into 8 group rows, trimmed `MC-2`, claim 2, §18–§20, & restatements strictly below `258,423` bytes. |
| `R5-i1` | `§13.2 HR-3, §16.2` | resolved | Clarified post-merge Rule 0 permanence and Owner Point C recovery sub-choice apply to the post-merge detector only. |
| `R5-i2` | `§10.2, §14, §16.1` | resolved | Added `Option I1-py-minor` (`"3.13"` Recommended) vs `Option I1-py-patch` (`"3.13.5"`) for `actions/setup-python`. |
| `R5-i3` | `§11.3, §12.3` | resolved | Scoped CI-only `--git-common-dir` snapshot strictly to `config` & `hooks/` (removed `objects/` & `refs/`) and budgeted `--verify-watched-to-fail` + snapshot in §12.3. |
| `R5-i4` | `§21.1` | resolved | Cited R5's `404` citation / `497` range count accurately with zero hardcoded fabricated counts. |
| `R5-i5` | `§4.2.2, §21.1` | resolved | Recorded R5's live ruleset re-check (`16/16` pins, `56`/`32`, `4ca375a3`, `check_response_timeout_minutes: 20`) in §21.1 item 8. |
| `R5-i6` | `§6.2.3, §21.1` | resolved | Documented `-P` parent vs `PYTHONSAFEPATH=1` child propagation alongside `[sys.executable, "-S", "-P", ...]`. |

---

## 21. Appendix A: Verification

### 21.1 Reproducible verification commands and script outputs

Checks below are read-only against `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note` (`dbd54fe382e7b2849d3f2038393cbdb4d709477b` / branch `HEAD`) and read-only `gh api` `GET`s (no vault prose read; `git status --short` clean before edits). Prior independent reviews reproduced: R2 (`wp9-5-note-r2-review-2026-11-21.md` §2, §5, `:218`, `0c9a90ed`) walk/counts/ruleset/clone timings; R3 (`wp9-5-note-r3-review-2026-11-21.md` §2, §6, `R3-i4`, `092db1f1`) 22 rows, 15-module closure, counts, live ruleset, YAML/`bash -n`, synthetic U-4; R4 (`wp9-5-note-r4-review-2026-11-22.md` §0, §2, §6, `R4-i7`, `48b5e935`) §21.1 checks, isolation, pin heredoc, citations; R5 (`wp9-5-note-r5-review-2026-11-22.md` §0, §2, §6, `R5-i5`, `83b4ae6f`) 22 guarded commits/walk, 70/90 units, 15 closure blobs, 16/16 pins (`56`/`32`), bare clone, `11.79s`/`34.85s`/`61.58s` stand-ins + `~11.3s` live `gh api`, YAML/`bash -n`, parent `-S -P` isolation, pin confinement, and `404` citations (`497` ranges). *(Revision 6 itself has not yet undergone a sixth independent review.)*

**1. Worktree branch, base commit, and clean tree check:**

```powershell
git -C "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note" branch --show-current
git -C "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note" rev-parse --verify dbd54fe382e7b2849d3f2038393cbdb4d709477b^{commit}
```

Showed branch `docs/w9-wp9-5-design-note` seeded from `origin/main` at `dbd54fe382e7b2849d3f2038393cbdb4d709477b`.

**2. Touched-file diffs for W9-T7 fixture commits `5df0c001` and `811d5a2b`, plus `#419`, `#425`, `#368`, `#129`, `#387`, `#215`, `#219`:**

```powershell
git -C "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note" --no-replace-objects diff-tree -r --no-renames --name-status 5df0c001~1 5df0c001
git -C "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note" --no-replace-objects diff-tree -r --no-renames --name-status 811d5a2b~1 811d5a2b
git -C "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note" --no-replace-objects show -s --format="%H|%P|%cI|%s" 14a81b84 1fba78aa 452352ff 1af52f6d 3fa437a1 a426b731 b132406e
```

Verified: `5df0c001` touched 11 files (7 `results/` files + 4 non-`results/`); `811d5a2b` touched 9 files (3 `contracts/manifests/input-provenance/` files + 6 others); `14a81b84` (`#419`, `2026-11-08T23:10:04Z`, `CONVENTIONS.md` `baceabd6 -> 14d39755`); `1fba78aa` (`#425`, `2026-11-10T21:14:45Z`, `CONVENTIONS.md` `14d39755 -> 1db03819`); `452352ff` (`#368`, `2026-10-17T08:00:26+01:00`, `[DECISION] P06: record L5, A6, A7 and step 3 batches 1-3 of the 06s Phase 5 run (P-058)`, `.apm/tracker.md` `8101faa5 -> c2716092`); `1af52f6d` (`2026-07-18T19:05:13+01:00`, parent `02ebcaf6`); `3fa437a1` (`#387`, `2026-10-21T22:42:45+01:00`); `a426b731` (`#215`, 2 parents); `b132406e` (`#219`, `2026-08-08T22:23:06+01:00`, parents `811d5a2b` & `3bfb279c`).

**3. Full first-parent walk `4b143c92..dbd54fe3` (`320` total commits, `22` guarded commits in §6.2.1):**

```powershell
@'
import subprocess
r = r"C:\Users\steph\TDL\.apm\worktrees\wp9-5-note"
commits = subprocess.check_output(["git", "-C", r, "--no-replace-objects", "rev-list", "--first-parent", "--reverse", "4b143c9225035cc29e37351445f1c3a4ab09ceb1..dbd54fe382e7b2849d3f2038393cbdb4d709477b"], text=True).splitlines()
print("Total first-parent commits:", len(commits))
prefixes = ("CONVENTIONS.md", "results/", "papers/", "contracts/", ".apm/")
hits = []
for c in commits:
    p1 = subprocess.check_output(["git", "-C", r, "--no-replace-objects", "rev-parse", f"{c}^1"], text=True).strip()
    files = subprocess.check_output(["git", "-C", r, "--no-replace-objects", "diff-tree", "-r", "--no-renames", "--name-only", p1, c], text=True).splitlines()
    matched = [f for f in files if f == "CONVENTIONS.md" or f.startswith(prefixes[1:])]
    if matched:
        hits.append((c[:8], len(matched)))
print(f"Guarded commits ({len(hits)}):", hits)
'@ | & "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note\.venv\Scripts\python.exe" -
```

Printed `320` total first-parent commits and `22` guarded commits (`02ebcaf6`, `5795a18b`, `9016b663`, `2111ce62`, `7347ae95`, `9795ee5f`, `f52f52f4`, `5df0c001`, `811d5a2b`, `b132406e`, `1dbf6b7b`, `85c7a02e`, `eba3fe69`, `65f4da4b`, `452352ff`, `3a14a97c`, `53b7c5be`, `e3519ba7`, `633ed58e`, `14a81b84`, `1fba78aa`, `a6a98966`; also confirmed via `git rev-list --first-parent --count`).

**4. `CONVENTIONS.md` exact segmentation parity and unit counts (`4620c716` vs `dbd54fe3`):**

```powershell
@'
import hashlib, subprocess, sys
sys.path.insert(0, r"C:\Users\steph\TDL\.apm\worktrees\wp9-5-note")
from research_system.legacy.segmentation import segment as rs_seg
from tools.w9_segmentation import segment as tool_seg
r = r"C:\Users\steph\TDL\.apm\worktrees\wp9-5-note"
for bref in ["4620c71607ca3a06c6df3b8e96a6bddffc783960", "dbd54fe382e7b2849d3f2038393cbdb4d709477b:CONVENTIONS.md"]:
    raw = subprocess.check_output(["git", "-C", r, "cat-file", "blob", bref])
    s1, s2 = rs_seg(raw, "conventions_unit"), tool_seg(raw, "conventions_unit")
    assert s1 == s2
    sec = {}
    for row in s1["rows"]:
        k = row["anchor_text"].split(" / ", 1)[0]
        sec[k] = sec.get(k, 0) + 1
    blk = [row for row in s1["rows"] if row["blocker_reason"] is not None]
    print(bref[:12], len(raw), hashlib.sha256(raw).hexdigest(), len(raw.splitlines()), len(s1["rows"]), len(blk), len(sec), list(sec.values()))
'@ | & "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note\.venv\Scripts\python.exe" -
```

Verified both segmenters returned identical dicts with 0 blockers: baseline `4620c716` (`33,645` bytes, SHA-256 `d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589`, 575 lines, `70` units across `10` sections: `[3, 2, 5, 4, 24, 13, 6, 3, 2, 8]`) and `dbd54fe3` (`51,774` bytes, SHA-256 `2ce15910d2f6712e2d4311578ebe8a5b6e7b1f83086c1c5483ea4876636ff97c`, 822 lines, `90` units across `11` sections: `[3, 2, 6, 5, 4, 24, 13, 6, 3, 9, 15]`).

**5. AST transitive import closure over existing `research_system` and `tools` modules (15 existing modules -> `21` runtime modules + workflow = `22` entries in `detector_closure_blobs`, excluding `export_w9_registration_manifest.py`):**

```powershell
@'
import ast, pathlib, subprocess
root = pathlib.Path(r"C:\Users\steph\TDL\.apm\worktrees\wp9-5-note")
seeds = [
    "research_system/legacy/reader.py", "research_system/legacy/evidence.py",
    "research_system/legacy/segmentation.py", "research_system/legacy/export_recheck.py",
    "research_system/legacy/accepted_w9.py", "research_system/canonical.py", "tools/w9_segmentation.py",
]
def res(mod):
    parts = mod.split(".")
    for c in (pathlib.Path(*parts).with_suffix(".py"), pathlib.Path(*parts) / "__init__.py"):
        if (root / c).exists(): return c.as_posix()
seen, q = set(), list(seeds)
while q:
    rel = q.pop(0)
    if rel in seen: continue
    seen.add(rel)
    pkg = pathlib.Path(rel).with_suffix("").parts[:-1]
    for node in ast.walk(ast.parse((root / rel).read_text(encoding="utf-8"), filename=rel)):
        mods = []
        if isinstance(node, ast.Import): mods = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            b = node.module or ""
            if node.level: b = ".".join((*pkg[:len(pkg) - node.level + 1], *(b.split(".") if b else [])))
            if b: mods = [b, *(f"{b}.{a.name}" for a in node.names)]
        for m in mods:
            if m.startswith(("research_system", "tools")):
                rpath = res(m)
                if rpath and rpath not in seen: q.append(rpath)
                for k in range(1, len(m.split("."))):
                    init = res(".".join(m.split(".")[:k]))
                    if init and init.endswith("__init__.py") and init not in seen: q.append(init)
for rel in sorted(seen):
    print(rel, subprocess.check_output(["git", "-C", str(root), "rev-parse", f"dbd54fe382e7b2849d3f2038393cbdb4d709477b:{rel}"], text=True).strip())
'@ | & "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note\.venv\Scripts\python.exe" -
```

Yielded exact `15` existing modules (`.__init__` packages + `canonical`, `errors`, `accepted_w9`, `evidence`, `export_recheck`, `reader`, `segmentation`, `store/{anchor,durability,lock,writer}`, `tools/w9_segmentation.py`), recorded in §6.2.3.

**6. Bare-clone timing and `git count-objects -vH` (`R1-m14`, `R2-i6`):**

```powershell
git -C "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note" count-objects -vH
@'
import subprocess, tempfile, time
r = r"C:\Users\steph\TDL\.apm\worktrees\wp9-5-note"
for _ in range(2):
    with tempfile.TemporaryDirectory() as td:
        t0 = time.perf_counter()
        subprocess.run(["git", "clone", "--quiet", "--bare", "--local", "--no-hardlinks", r, f"{td}/r.git"], check=True)
        t1 = time.perf_counter()
        subprocess.run(["git", "--git-dir", f"{td}/r.git", "diff-tree", "-r", "--no-renames", "5df0c001~1", "5df0c001"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "--git-dir", f"{td}/r.git", "diff-tree", "-r", "--no-renames", "811d5a2b~1", "811d5a2b"], check=True, stdout=subprocess.DEVNULL)
        t2 = time.perf_counter()
        print(round(t1 - t0, 3), round(t2 - t0, 3))
'@ | & "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note\.venv\Scripts\python.exe" -
```

Confirmed `58,133` objects in pack (`28` packs, `335.09 MiB`); measured clone at `1.569–1.585s` (`1.646–1.648s` including two `diff-tree` runs) in revision 3 (following `1.71–1.79s` / `1.77–1.86s` in revision 2 and `wp9-5-note-r2-review-2026-11-21.md:218`).

**7. Tracked `contracts/` listing (`git -C "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note" ls-files contracts/`):**

Confirmed tracked paths cited in §6.5 (`contracts/manifests/research-assurance.yaml`, `contracts/stochastic-tests/monte-carlo-permutation-p-value.yaml`, `contracts/stochastic-tests/markov-order-provenance.yaml`, `contracts/topology-invariants/null-operation-changes-ph-input.yaml`, `contracts/schema/contract.schema.yaml`).

**8. Read-only GitHub REST ruleset & rule-suites `GET`s:**

```powershell
gh api repos/ZK-Theory/TDL/rulesets/20822054
gh api --paginate --slurp "repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=month&per_page=100"
```

`rulesets/20822054` returned HTTP 200 (`id: 20822054`, `name: "P-049 Gate 6 main merge admission"`, `enforcement: "active"`, `conditions.ref_name.include: ["refs/heads/main"]`, `pull_request` `required_approving_review_count: 0`, `require_code_owner_review: true`, `required_review_thread_resolution: true`, `allowed_merge_methods: ["squash"]`, `required_status_checks` `strict_required_status_checks_policy: true` with all 4 contexts carrying `integration_id: 15368`, `merge_queue` `SQUASH` 1-by-1 `ALLGREEN` `check_response_timeout_minutes: 20`, `non_fast_forward`, `bypass_actors: [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}]`). `rule-suites?time_period=month` is a sliding 30-day window (`57` / `33` bypass initially; `58` / `34` after `#448` `4ca375a3`; `56` / `32` at `2026-11-21T23:03Z` once `bb9d91d4` aged out, re-verified by R3 `wp9-5-note-r3-review-2026-11-21.md:99`, R4 `wp9-5-note-r4-review-2026-11-22.md:108`, and R5 `wp9-5-note-r5-review-2026-11-22.md:19,112` `R5-i5`, where `commits/dbd54fe3/pulls` -> `#446` and `commits/4ca375a3/pulls` -> `#448`).

**9. Stdlib-only AST check across the 15 existing closure modules + parent/child `python -S -P` scratch isolation test (`R4-m7`, `R5-m8`, `R5-i6`, base Python `3.13.5`):**

```powershell
@'
import ast, json, os, pathlib, subprocess, sys, tempfile
wt = pathlib.Path(r"C:\Users\steph\TDL\.apm\worktrees\wp9-5-note")
rev = "dbd54fe382e7b2849d3f2038393cbdb4d709477b"
mods = [
    "tools/w9_segmentation.py",
    "research_system/__init__.py", "research_system/canonical.py", "research_system/errors.py",
    "research_system/legacy/__init__.py", "research_system/legacy/accepted_w9.py",
    "research_system/legacy/evidence.py", "research_system/legacy/export_recheck.py",
    "research_system/legacy/reader.py", "research_system/legacy/segmentation.py",
    "research_system/store/__init__.py", "research_system/store/anchor.py",
    "research_system/store/durability.py", "research_system/store/lock.py",
    "research_system/store/writer.py",
]
non_std = []
for rel in mods:
    tree = ast.parse((wt / rel).read_text(encoding="utf-8"), filename=rel)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module.split(".")[0]]
        else:
            continue
        for top in names:
            if top not in sys.stdlib_module_names and top not in ("research_system", "tools"):
                non_std.append((rel, top))
print("Non-stdlib imports in 15 existing closure modules:", non_std)

base_py = r"C:\Users\steph\AppData\Local\Programs\Python\Python313\python.exe"
probe = """import importlib, json, os, research_system, research_system.legacy.evidence, subprocess, sys, tools, tools.w9_segmentation
if "--child" in sys.argv:
    print(json.dumps({
        "role": "child",
        "no_site": sys.flags.no_site,
        "safe_path": sys.flags.safe_path,
        "rs_paths": list(research_system.__path__),
        "tools_paths": list(tools.__path__),
        "site_in_path": any("site-packages" in p.lower() for p in sys.path),
        "wt_in_path": any(os.path.normcase(os.getcwd()) == os.path.normcase(os.path.abspath(p or ".")) for p in sys.path),
    }, sort_keys=True))
    raise SystemExit(0)
bad = {}
for m in ("research_system.cli", "tools.check_merge_admission", "yaml", "pytest"):
    try:
        importlib.import_module(m)
        bad[m] = "UNEXPECTED_IMPORT"
    except ModuleNotFoundError as exc:
        bad[m] = type(exc).__name__
print(json.dumps({
    "role": "parent",
    "exe": sys.executable,
    "no_site": sys.flags.no_site,
    "safe_path": sys.flags.safe_path,
    "rs_paths": list(research_system.__path__),
    "tools_paths": list(tools.__path__),
    "site_in_path": any("site-packages" in p.lower() for p in sys.path),
    "wt_in_path": any(os.path.normcase(os.getcwd()) == os.path.normcase(os.path.abspath(p or ".")) for p in sys.path),
    "blocked": bad,
}, sort_keys=True))
subprocess.run([sys.executable, "-S", "-P", __file__, "--child"], check=True)
"""
with tempfile.TemporaryDirectory() as td:
    td_path = pathlib.Path(td)
    for rel in mods:
        dest = td_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(subprocess.check_output(["git", "-C", str(wt), "cat-file", "blob", f"{rev}:{rel}"]))
    (td_path / "tools" / "probe_iso.py").write_text(probe, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONHOME", "VIRTUAL_ENV")}
    env["PYTHONPATH"] = str(td_path)
    env["PYTHONSAFEPATH"] = "1"
    for label, cmd in [
        ("script", [base_py, "-S", "-P", str(td_path / "tools" / "probe_iso.py")]),
        ("module", [base_py, "-S", "-P", "-m", "tools.probe_iso"]),
    ]:
        r = subprocess.run(cmd, cwd=wt, env=env, capture_output=True, text=True, check=True)
        print(label, r.stdout.strip())
'@ | & "C:\Users\steph\AppData\Local\Programs\Python\Python313\python.exe" -
```

Confirmed `Non-stdlib imports in 15 existing closure modules: []`; both `script` (`python -S -P .../probe_iso.py`) and `module` (`python -S -P -m tools.probe_iso`) invocations from `cwd=wt` exited `0`, and BOTH `role: "parent"` and the child launched via `[sys.executable, "-S", "-P", __file__, "--child"]` printed `no_site: 1`, `safe_path: True`, `site_in_path: False`, `wt_in_path: False`, resolved `research_system.__path__` and `tools.__path__` solely inside `<td_path>`, and blocked `research_system.cli`, `tools.check_merge_admission`, `yaml`, and `pytest` with `ModuleNotFoundError` (`R5-m8`, `R5-i6`). Separately verified the stdin pipe wrapper invocation (`git show HEAD:wrap.py | python -S -P - --repo-root .`) in a temporary Git repository, printing `WRAP_OK ['--repo-root', '.'] 1 True` (`R5-m6`).

**10. Representative 6-call Option C1 `1x` post-merge walk stand-in timings (~1 mo `60`, ~3 mo `178`, ~5.5 mo `320` first-parent commits backward from `dbd54fe3`, excluding live `gh api` PR lookups; `R4-M1`, `R5-m10`):**

```powershell
@'
import subprocess, time
r = r"C:\Users\steph\TDL\.apm\worktrees\wp9-5-note"
all_c = subprocess.check_output(
    ["git", "-C", r, "--no-replace-objects", "rev-list", "--first-parent", "--reverse",
     "4b143c9225035cc29e37351445f1c3a4ab09ceb1..dbd54fe382e7b2849d3f2038393cbdb4d709477b"],
    text=True,
).splitlines()
prefixes = ("results/", "papers/", "contracts/", ".apm/")
def walk(sub):
    guarded = 0
    for c in sub:
        p1 = subprocess.check_output(["git", "-C", r, "--no-replace-objects", "rev-parse", f"{c}^1"], text=True).strip()
        out = subprocess.check_output(["git", "-C", r, "--no-replace-objects", "diff-tree", "-r", "--no-renames", "-z", p1, c])
        paths = [tok.decode("utf-8", "replace") for i, tok in enumerate(out.split(b"\x00")) if i % 2 == 1]
        for rev in (p1, c):
            for f in (".research-system/evidence/w9/walk-baseline.json", ".research-system/evidence/w9/registration-manifest.json"):
                subprocess.run(["git", "-C", r, "--no-replace-objects", "cat-file", "-e", f"{rev}:{f}"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if any(p == "CONVENTIONS.md" or p.startswith(prefixes) for p in paths):
            guarded += 1
    return guarded
for label, n in [("1_month_60", 60), ("3_months_178", 178), ("5.5_months_320", 320)]:
    sub = all_c[-n:]
    t0 = time.perf_counter()
    g = walk(sub)
    dt1 = round(time.perf_counter() - t0, 2)
    if n == 60:
        t1 = time.perf_counter()
        walk(sub); walk(sub)
        print({"window": label, "commits": len(sub), "guarded": g, "post_merge_1x_s": dt1, "pr_compare_2x_measured_s": round(time.perf_counter() - t1, 2)})
    else:
        print({"window": label, "commits": len(sub), "guarded": g, "post_merge_1x_s": dt1, "pr_compare_2x_scaled_s": round(dt1 * 2, 2)})
'@ | & "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note\.venv\Scripts\python.exe" -
```

Local 6-call `1x` stand-in timings (without real Rules 0–3 Python evaluation or `gh api` calls):
- `1_month_60` (`60` commits, `6` guarded): **`14.05s`** (`1x`, measured; R5 independent run **`11.79s`**; ~15% run-to-run noise; R5 historical 2x separate run `24.04s`).
- `3_months_178` (`178` commits, `12` guarded): **`34.46s`** (`1x`, measured; R5 **`34.85s`**; extrapolated `2 × 1x`: `68.92s`).
- `5.5_months_320` (`320` commits, `22` guarded): **`62.84s`** (`1x`, measured; R5 **`61.58s`**, plus R5 **`~11.3s`** across `22` live `commits/<sha>/pulls` GETs, or ~14s per unmapped commit under 3-try back-off; extrapolated `2 × 1x`: `125.68s`).
*(Post-merge runs walk `1x` only; the extrapolated `2 × 1x` values apply solely when Stephen runs the manual `k-1`-vs-`k` comparison offline for a pin-advance PR, §6.2.2.)*

### 21.2 Statements marked `UNVERIFIED` (pre-code gates for the reviewing session)

Every statement in this design note that cannot be verified without running a GitHub Actions workflow under `GITHUB_TOKEN`, reading the live vault `Computational-Log.md` bytes, running an isolated scratch-store test on Stephen's machine, checking GitHub repository variable write permissions, or running the `1x` full walk on hosted `windows-latest` is listed here and gated in §15.1:

1. **`UNVERIFIED-1` (U-3 probe, §4.2.2, §15.1 item 1):** The HTTP status codes, `X-Accepted-GitHub-Permissions` headers, and pinned JSON body key presence returned to a GitHub Actions `GITHUB_TOKEN` (under `permissions: contents: read` and under `permissions: contents: read, pull-requests: read`) for:
   - `GET repos/ZK-Theory/TDL/rulesets/20822054`
   - `GET repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=day&per_page=5` (expected HTTP 403/404 per `tools/check_bypass_merges.py:20-21`, which decides D-8)
   - `GET repos/ZK-Theory/TDL/commits/dbd54fe382e7b2849d3f2038393cbdb4d709477b/pulls`
2. **`UNVERIFIED-2` (U-4 handle-bound reader and segmenter dry run on the live `833,453`-byte vault file, §4.3.3 item 2, §15.1 item 2):** The output of running standalone scratch script `u4_dry_run.py` (`root_checks` booleans from §4.3.2, `handle_bound_read(resolved_vault, "04-Methods/Computational-Log.md")`, and both `segment(raw, "computational_log_entry")` functions) on the current `833,453`-byte live file (`link_count == 1`, `file_facts`, `row_counts`, and `blockers == []`).
3. **`UNVERIFIED-3` (Unconditional pre-code single scratch-store test timing profile and operator-machine weekly D-5 run, §12.3, §15.1 item 4):** The wall-clock timing of a single existing WP9.3/WP9.4 scratch-store integration test run alone on Stephen's machine (`P-087` item 7, **unconditionally required before WP9.5 code dispatch**, §15.1 item 4), and end-to-end execution of the weekly operator-machine D-5 workflow against the live vault and control store via `tools/run_w9_pinned_detectors.py` after L-0b/L-1.
4. **`UNVERIFIED-4` (Option I3 `W9_DETECTOR_PIN` GitHub repository Actions variable write permissions, §10.2, §15.1 item 3, §16.1):** Which repository roles on `ZK-Theory/TDL` (`admin` vs `maintain`/`write`) can create, edit, or delete repository Actions variables (`vars.W9_DETECTOR_PIN`) was not verified against live repository settings or documentation permitted here; Stephen must confirm variable write permissions before relying on Option I3 as an out-of-tree trust anchor.
5. **`UNVERIFIED-5` (Hosted `windows-latest` `1x` full-walk wall time + unwritten `tools/` stdlib compliance, §6.2.2, §12.3, §15.1 item 5):** Actual hosted `windows-latest` wall-clock time running real Rules 0–3, `.apm/tracker.md` H1 segmentation checks, and live `gh api` PR lookups for the `1x` post-merge walk (over representative ~60, ~178, and ~320-commit intervals), bounded by the `600s` pre-code walk stop rule (§15.2 item 5), together with verifying stdlib-only imports across the unwritten runtime `tools/` modules (`test_detector_closure_is_stdlib_only` and `test_pinned_wrapper_is_self_contained_stdlib_only` once written).
