# WP9.5 Design Note — W9 Detectors (W9-D5)

| Field | Value |
|---|---|
| Date | 2026-11-24 |
| Status | **Revision 8 + Rule 0 exemption-row addendum, revision 2 (`P-090` items 4–5), for focused review. Nothing in it is implemented.** |
| Package | `06v` WP9.5 — "Detectors (W9-D5)" (`docs/plans/agentic-research-system/implementation/06v-w9-implementation-plan.md:470-503`) |
| Authority | Decision register entry `P-089` (`docs/plans/agentic-research-system/03-decisions-and-open-questions.md:6071-6146`); `P-090` (`0e1269bd`, item 5 `813088e9`, `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`) |
| Base | `origin/main` at `dbd54fe382e7b2849d3f2038393cbdb4d709477b` (`[PIPELINE] P06: WP9.4-2 follow-up: the independent review's Minor findings (P-088 item 5) (#446)`) |
| Worktree / Branch | `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note` on branch `docs/w9-wp9-5-design-note` |
| Prior reviews | Revision 1 (`65363e27`): `wp9-5-note-r1-review-2026-11-21.md` (`edb9acc6`; `REWORK REQUIRED`: 1 Blocking, 12 Major, 14 Minor, 6 Info)<br>Revision 2 (`0c9a90ed`): `wp9-5-note-r2-review-2026-11-21.md` (`3cf35bec`; `REWORK REQUIRED`: 0 Blocking, 5 Major, 16 Minor, 6 Info)<br>Revision 3 (`092db1f1`): `wp9-5-note-r3-review-2026-11-21.md` (`1bd4ecff`; `REWORK REQUIRED`: 0 Blocking, 3 Major, 13 Minor, 4 Info)<br>Revision 4 (`48b5e935`): `wp9-5-note-r4-review-2026-11-22.md` (`0e6d23e4`; `REWORK REQUIRED`: 0 Blocking, 2 Major, 11 Minor, 8 Info)<br>Revision 5 (`83b4ae6f`): `wp9-5-note-r5-review-2026-11-22.md` (`d6938710`; `REWORK REQUIRED`: 0 Blocking, 3 Major, 11 Minor, 6 Info)<br>Revision 6 (`95dfefe7`): `wp9-5-note-r6-review-2026-11-22.md` (`d47a8e72`; `REWORK REQUIRED`: 0 Blocking, 3 Major, 9 Minor, 6 Info)<br>Revision 7 (`08840c3e`): `wp9-5-note-r7-review-2026-11-23.md` (`c4c62b3b`; `REWORK REQUIRED`: 0 Blocking, 1 Major, 10 Minor, 7 Info, plus `R7-d1`)<br>Revision 8 (`526334c8`): `wp9-5-note-r8-review-2026-11-23.md` (`ae608701`; `CONFIRM WITH FINDINGS`: 0 Blocking, 0 Major, 2 Minor, 6 Info)<br>Exemption-row addendum (`b3500098`): `wp9-5-note-exemption-addendum-review-2026-11-24.md` (`REWORK REQUIRED`: 0 Blocking, 2 Major, 7 Minor, 7 Info) |
| Not authorized | WP9.5 code, WP9.6, WP9.7, live operations L-0 to L-5 (including L-0b and L-1), creating or binding the real control store, registering or observing any real file, or any write to a legacy file, `main`, or the vault (`03-decisions-and-open-questions.md:6127-6135`) |
| Verification scope | **Checked here (`dbd54fe38` / worktree `HEAD`, §21.1 items 1–11):** cited lines; 22-commit walk; `CONVENTIONS.md` counts (70/90 units); ruleset `20822054` pins; bare-clone timings; 15-module stdlib-only closure; parent + child `[sys.executable, "-S", "-P", ...]` isolation & Git Bash stdin-pipe wrapper (`item 9`); 27 pin-heredoc cases (`item 11`, incl. `os.path.isreserved`, `casefold()`, `~`, post-loop `hash-object --no-filters`, malformed JSON, I3); and `1x` walk stand-ins (`14.05s`/`34.46s`/`62.84s`; `24.04s` `2x` at 60 commits; `68.92s`/`125.68s` **extrapolated (`2 × 1x`)**). Reviews R2–R6 (`§21.1` intro) reproduced those checks, incl. R6 `12.97s`/`44.03s`/`77.7s` (`26.35s` `2x`), 32 pin runs, `366` citation pairs (`456` range occ), and live ruleset `20822054`.<br>**NOT verified here (§15.1, §21.2):** CI `GITHUB_TOKEN` U-3 probe (`UNVERIFIED-1`), live vault U-4 dry run (`UNVERIFIED-2`), single scratch-store timing & weekly D-5 run (`UNVERIFIED-3`), I3 variable permissions (`UNVERIFIED-4`), and hosted `windows-latest` `1x` walk time (`UNVERIFIED-5`). |

---

## 1. What this note settles

WP9.5 builds the W9 detectors (`06v:470-503`; `W9` §4.4, `09-migration-compatibility-and-pilot.md:191-202`), specifying inputs, decision rules, outputs, closed `ERROR:` failures, execution lanes, negative controls, and tests. Each rule is specified once in its owning section below:

| Handover §3 item | Owning sections | Summary |
|---|---|---|
| 1. Scope & package | §2, §3 | No D-4 trigger (§2.2); separates `tools/` readers from Owner Point changes under `research_system/legacy/` and WP9.4 fixtures (§2.3). |
| 2. Ruleset read (`main_ruleset`) | §4.1 | Pins ruleset `20822054` and `rule-suites` history (`MAX_DAYS = 30`), outputting canonical `w9-main-ruleset-read/1` SHA-256. |
| 3. U-3 probe & D-8 fallback | §4.2, §15.1 | Pre-code draft-PR `pull_request` probe of `GITHUB_TOKEN` and pinned keys; `rule-suites` failure triggers hash-bound D-8 fallback. |
| 4. First-parent detector | §6, §10.2, §16.1–§16.2 | Content-pinned `python -S -P` execution over `detector_closure_blobs` (**21** stdlib-only runtime modules + workflow review blob); time-indexed Rules 0–3 (**pin, no-lockstep**); hash-bound Rule 0 exemption rows (§6.5.1); `1x` post-merge walk; tools exit `2` (`ERROR`) on unparseable/unknown-`format` evidence or uncaught errors and `1` for Rules 0–3; manual comparison procedure; `600s` walk stop rule. |
| 5. Registration manifest (M-6) | §5, §16.3 | `tools/export_w9_registration_manifest.py` exports `w9-registration-manifest/2` (Option A1) from `_legacy_projection` / `_legacy_current_binding`; `--check` verifies store equality at `git_head` (unpinned residual `HR-7`). |
| 6. Shared-surface rule (`O-32`, Rule 3) | §6.2.2, §6.5, §16.5 | In-commit §4.3 record + `w9-shared-surface-changes/2` (Option D3 blob-keyed freshness); Rule 3 acknowledgements also require `independent_review`, non-empty `affected_registrations` / `"none derived"`, and `pr_number: null` when unmapped. |
| 7. `CONVENTIONS.md` check | §7, §16.10–§16.11 | Segments baseline `4620c716` vs candidate via `conventions_unit`; 68-unit provisional partition or pinned L-0b classification (`ACCEPTED_CONVENTIONS_CLASSIFICATION`); bullet/paragraph insertions only; PR-lane choice (Owner Point K). |
| 8. Vault Computational-Log & D-5 | §8, §16.6, §16.10 | `tools/check_legacy_log_baseline.py` verifies live entries against accepted `w9-cl-export/1` + 1-based `w9-cl-classified-list/1` (`void == False` required; L-0b pairs with a pin advance); D-5 cadence gated at `LR-003`/`LR-015`/`LR-016`/`LR-020`. |
| 9. U-4 vault path & dry run | §4.3, §15.1 | Records `2026-11-21T21:06:44Z` metadata (`833,453` B) and pre-code `u4_dry_run.py` (`root_checks` + `handle_bound_read` + `segment`). |
| 10. Detector controls | §9 | `tools/run_w9_detector_controls.py` binds tool blobs + `closure_blobs` map under `CONTROL_GIT_ENV` (`--code-root` required; no default). |
| 11. Merging is not going live | §10, §16.1, §16.7 | `workflow_dispatch`-only commit until L-1; confined `python -S -P` assembly + post-loop hash verification; `L1_LIVE = False` tripwire (`yaml.BaseLoader`) in `admission-controls` + CODEOWNERS; separate throwaway rehearsal + green L-1 `workflow_dispatch`. |
| 12. Where the controls run | §11 | Bare local scratch clones (`~1.57–2.07s`); `W9-T7` in `tests/tools/test_w9_detectors.py` (departure from `06v:230`); `REPO_ROOT` checkout-local snapshot (`--git-common-dir` `config`/`hooks/` in CI only). |
| 13. Tests & budget | §12, §16.7–§16.8 | Unit PR checks (`W9-T19`, `W9-T7`, stdlib/ASCII/wrapper/CODEOWNERS/pin/comparison tests), integration `M-6`/`O-13` (`affected_research_tests.py` + nightly), `14.05s–62.84s` measured `1x` stand-ins, unconditional scratch-store profile (`§15.1`), G1 `300s` budget. |
| 14. Research assurance | §13 | Machine-checkable claims (`MC-1`–`MC-10`) and human-review-only limits (`HR-1`–`HR-7`). |
| 15. Claims for review | §14 | 16 load-bearing claims for independent adversarial attack against `dbd54fe382e7b2849d3f2038393cbdb4d709477b`. |
| 16. Stop rules | §15 | Pre-code gates (`UNVERIFIED-1`–`5`), implementation stop rules (`06v:610-620`), and WP9.5-added pre-code `600s` `1x` walk stop rule. |
| 17. Owner points | §16 | 11 Owner Points and follow-up clarifications decided by Stephen in `P-090` (`0e1269bd`, item 5 `813088e9`); Owner Point C's Rule 0 exemption row is designed in §6.5.1. |

*(Revision history, compact disposition logs, and reproducible verification checks appear in §17–§21.)*

---

## 2. Scope, package boundary, and protected identities

### 2.1 Deliverables in WP9.5

Under `06v` §5 (`06v-w9-implementation-plan.md:470-503`) and `P-089` (`03-decisions-and-open-questions.md:6091-6118,6141-6143`), WP9.5 delivers:

1. **`tools/export_w9_registration_manifest.py` (**new**, M-6, `06v:470-473`):** Reads `_legacy_projection` (`research_system/cli.py:1648-1659`) and `_legacy_current_binding` (`:1662-1684`) to export `.research-system/evidence/w9/registration-manifest.json` (`w9-registration-manifest/2` under A1, updating `research_system/legacy/evidence.py:37,40,114-131`); `--check` verifies equality with store `legacy_path_registration` (`research_system/legacy/replay/reducers.py:70,571`) at `binding.binding["git_head"]` (`research_system/cli.py:1714`; §5).
2. **`tools/check_legacy_writes.py` & `.github/workflows/legacy-write-detector.yml` (**new**, `O-9`, `O-10`, `O-32`, `06v:189-190,212,474-490`):** First-parent detector walking `<b0>..<head>` from `baselines[0]["baseline_commit"]` once (`1x`) per post-merge run with `baselines[-1]` (Rules 0–3, `acknowledged`, `rule0_exemptions` §6.5.1, ruleset `20822054` / U-3/D-8). Every WP9.5 tool wraps `main()` to exit `2` (`ERROR`, never `0` and never `1` — a rule for the tools, not the pin step) on unparseable/unknown-`format` evidence or uncaught exceptions, reserving exit `1` for Rules 0–3 violations, and decodes `git`/`gh` with explicit `encoding="utf-8"` (§6). Windows workflow committed `on: workflow_dispatch:` only, assembling `$RUNNER_TEMP/w9-detector` from `detector_closure_blobs` and running stdlib-only `python -S -P` (`PYTHONPATH="$DETECTOR_DIR"`, `PYTHONSAFEPATH=1` — no `uv sync`, §10).
3. **`tools/check_conventions_legacy_locks.py` (**new**, `O-12`, `06v:192,491-492`):** Verifies `CONVENTIONS.md` preserves every `conventions_unit` from `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (blob `4620c71607ca3a06c6df3b8e96a6bddffc783960`, 33,645 bytes, SHA-256 `d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589`, `CONVENTIONS_LOCK` `research_system/legacy/reader.py:43-49`) via `w9-segmentation/1.0.0` (`research_system/legacy/segmentation.py:429-488`, `tools/w9_segmentation.py:461-518`) and `ACCEPTED_CONVENTIONS_CLASSIFICATION` (`research_system/legacy/accepted_w9.py`, **new**; §7).
4. **`tools/check_legacy_log_baseline.py` (**new**, `O-11`, `D-5`, `D-7`, `06v:191,493-496,567,569`):** Refuses symlink/junction/in-repo `--vault-root`, reads `04-Methods/Computational-Log.md` via `handle_bound_read` (`research_system/legacy/reader.py:140-206`), requires `recheck_cl_export` `void == False`, and checks legacy rows against `ACCEPTED_CL_EXPORT` (`accepted_w9.py:86-88`; §8).
5. **`tools/run_w9_detector_controls.py` & `tools/run_w9_pinned_detectors.py` (**new**, `O-13`, `06v:193,497-502,603-604`):** Emits `.research-system/evidence/w9/detector-controls.json` (`w9-detector-controls/1`, `evidence.py:38,41,59-64,133-154`, `--code-root` required / no default, §9). The pinned wrapper is one **ASCII-only, self-contained stdlib-only file** (zero `tools.*`/`research_system.*` imports) piped by Stephen under Git Bash (or `cmd /c`) from `origin/main` via `git show ... | python -S -P -`, preserving child exit `2` and supporting `--assemble-only --rev <rev> --out <dir>` for §6.2.2's comparison (§6.2.3).
6. **Tests (`W9-T7`, `W9-T19`, `06v:230,242,503`):** `tests/tools/test_w9_detectors.py` (**new**, `unit` in `admission-controls`: `W9-T19`, `W9-T7` departure from `06v:230`, `L1_LIVE` tripwire, stdlib/ASCII/wrapper/CODEOWNERS/pin/comparison/exit-`2`/UTF-8 controls) and `tests/research_system/integration/test_w9_wp9_5_detectors.py` (**new**, `slow`, `integration`: scratch-store `M-6` and `O-13`) (§12.1).

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
- **What it reads (`gh api` GETs; `.claude/hooks/admin-bypass-guard.sh:18,96-106`; §21.1 #8):**
  1. **`rulesets/20822054` (`01-current-system-evidence.md:409`):** Verifies 16 invariants below (`id: 20822054`, `name`, `target == "branch"`, `enforcement == "active"`, `refs/heads/main`, `exclude == []`, single `bypass_actors` `actor_id: 5`, plus rules: `pull_request` [`require_code_owner_review: True`, `required_approving_review_count: 0`, `required_review_thread_resolution: True`, `["squash"]`, `06v:90-91`], `merge_queue` [`SQUASH`, build/min/max `== 1`, `tools/check_merge_admission.py:700-737`], `required_status_checks` [`strict: True`, 4 contexts `integration_id == 15368`], `non_fast_forward`). *(Unpinned `R2-i3`: `require_extra_approval_for_unattributed_changes`, `grouping_strategy`, `check_response_timeout_minutes`, `dismiss_stale_reviews_on_push`.)*
  2. **`rule-suites?ref=refs/heads/main&time_period=month&per_page=100` (`tools/check_bypass_merges.py:141-166`):**
     - **30d window (`MAX_DAYS = 30`, `tools/check_bypass_merges.py:24,57-58,73-90`):** Fails closed if prior `"main_ruleset"` >30d old (`ERROR: main_ruleset: previous recorded read is older than 30 days (<previous_recorded_at>); rule-suites API window (MAX_DAYS=30) cannot cover the gap without a recorded P-0xx acknowledgement in walk-baseline.json`). Recovery: `--acknowledge-gap <P-0xx>` matching `walk-baseline.json` `ruleset_gap_acknowledgements` row (`P1` hash-bound `disposition_ref` §6.5 naming both timestamps, `acknowledged_through >= now - 30d`).
     - **`"bypass"` eval (§21.1 #8):** `"bypass"` alone is valid for owner merges; every `refs/heads/main` entry after `<baseline>` passes Rules 0–3 (`check_legacy_writes.py`), recording `{after_sha, pushed_at, actor_name, touched_guarded_paths}`.
- **Schedule & digest (`06v:603`):** Local `gh` via `run_w9_pinned_detectors.py` at L-1 (`LR-003`, `preparers.py:686-690`) & pre-batch (since `evidence.py:92-105` reads `git_head`, updates need `Bypass reason:` PR `tools/check_bypass_merges.py:41,135` + `ars store advance-binding`). Hashed via `sha256_hex(canonical_bytes(report))` (`canonical.py:40-52`) under `"main_ruleset"`:
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

1. **Owner `gh` login (verified `2026-11-21`, `wp9-5-note-r1-review-2026-11-21.md:198`, §21.1):** HTTP 200 on `rulesets/20822054`, `rulesets/rule-suites?...&time_period=month&per_page=100` (57 entries at `dbd54fe38`: `33` `bypass`, `24` `pass`, newest `dbd54fe382e7b2849d3f2038393cbdb4d709477b`), and `commits/dbd54fe382e7b2849d3f2038393cbdb4d709477b/pulls` (PR `#446`, `merge_commit_sha == "dbd54fe382e7b2849d3f2038393cbdb4d709477b"`).
2. **`tools/check_bypass_merges.py:20-21`:** Notes `GITHUB_TOKEN` cannot read **rule suites** (`rulesets/rule-suites`); whether `GITHUB_TOKEN` on public `ZK-Theory/TDL` reads `rulesets/20822054`, `rule-suites`, and `commits/<sha>/pulls` under `contents: read` vs `contents: read, pull-requests: read` is **`UNVERIFIED`** until U-3 runs (`06v:159`, `P-089` #3 `03-decisions-and-open-questions.md:6105-6107`).
3. **Existing workflow `permissions:` (`dbd54fe38`):** `ci.yml` (no top-level; `watchdog-schedule-liveness`: `actions: read, contents: read`, `:239-241`), `merge-admission.yml` (`:52-55`, `:70-83`), `merge-admission-sweep.yml` (`:58-59`, `:74-80`), `ars-artefact-currency.yml` (`:12-13`), `ars-artefact-currency-watchdog.yml` (`:14-16`), `research-system-suite.yml` (`:30-31`).

#### 4.2.2 Design of a runnable read-only U-3 probe

- **Why a throwaway PR is needed:** GitHub rejects `workflow_dispatch` on workflows absent from `main` (`tools/check_workflow_liveness.py:64-67`), and landing a probe on `main` exceeds `P-089` (`03-decisions-and-open-questions.md:6127-6135`).
- **Execution & side effects (`R2-m6`):** On Stephen's authorization, the reviewing session pushes `probe/w9-u3-token-read` + draft unmerged PR with `.github/workflows/u3-probe-temp.yml` (`on: pull_request:`), logs HTTP statuses, `X-Accepted-GitHub-Permissions`, and HTTP 200 JSON keys (since lower-privilege tokens can omit `bypass_actors`/`parameters`/`conditions`), cancels triggered CI runs, closes the draft PR, and deletes the branch:
  - **Job 1 (`probe-contents-only`, `permissions: contents: read`):** GETs `rulesets/20822054` (`id`, `enforcement`, `conditions.ref_name.include`, `bypass_actors`, `parameters`), `rule-suites?...&time_period=day&per_page=5` (length + `after_sha`/`result`/`actor_name`/`pushed_at`), and `commits/dbd54fe38.../pulls` (length + `number`/`merged_at`/`merge_commit_sha`).
  - **Job 2 (`probe-with-pull-requests-read`, `permissions: contents: read, pull-requests: read`):** GETs `commits/dbd54fe38.../pulls` (`legacy-write-detector.yml` sets `contents: read, pull-requests: read` unconditionally, §10.2).
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

1. **Junction vs real vault:** In `C:\Users\steph\TDL`, `vault` is a gitignored Windows junction -> `C:\Users\steph\Documents\TDA-Research` (`01-current-system-evidence.md:357`, `CLAUDE.md:15,28`, `CONVENTIONS.md:790,796`), absent in `.apm/worktrees/<name>`.
2. **WP9.2 grammar census (`w9-segmentation-contract-v1.md:233-258`, not a baseline):** On `2026-10-23`: `700,632` B (`de44a67b...`, `255` items, `1` structural @ L4436, 0 blockers, `:242`), then `703,531` B (`19ad5c4d...`, `256` items, `1` structural @ L4476, 0 blockers, `:254-256`).
3. **Why `handle_bound_read` & `LegacyReader.__init__` need a root-junction check (`reader.py:140-206,241-248`, `anchor.py:1934-1950`):** `open_registered_root_anchor` uses `reject_reparse=False` (`:1934-1950`), `handle_bound_read` checks intermediate dirs (`:160,164-165`) and leaf `is_symlink()`/`is_junction()` (`:168-169`), and `LegacyReader.__init__` uses lexical `os.path.abspath` (`:241-248`)—so an external junction passed as `--vault-root` would slip past both.

#### 4.3.2 How `tools/check_legacy_log_baseline.py` validates `--vault-root`

Before `handle_bound_read` (`research_system/legacy/reader.py:140-206`): (1) `--vault-root <path>` is required (`P-083` #2 `m-3`); (2) root symlink/junction/resolve check (`research_system/legacy/reader.py:168`):
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
   (3) `given_vault` & `resolved_vault` disjoint from `repository_root.resolve(strict=True)`; (4) `handle_bound_read(resolved_vault, "04-Methods/Computational-Log.md")` enforces `st_nlink == 1` & identity invariance (`reader.py:157-204`).

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

No repository-content trust root stops a merged commit from changing workflows/scripts on `main` (`CONVENTIONS.md:721-725`). Under **Stephen's `2026-11-22` decision (*"pin, no lockstep", for `P-090`*)**:
- **Preventive (`Option I1` CODEOWNERS + optional `I3`):** `.github/CODEOWNERS` (`@stephendor`) protects the workflow, 7 WP9.5 tools, `test_w9_detectors.py`, `accepted_w9.py`, and `/.research-system/evidence/w9/` (plus `/tools/w9_segmentation.py` under Recommended `I1-include-seg`, §16.1), optionally paired with `vars.W9_DETECTOR_PIN` (`I3`). **"Code-owned, so Stephen merges it himself" holds only under `Option I1`** (under `I2`, `walk-baseline.json` is un-owned and lacks I1 bypass protection, `R6-m9`, failing R1-B1 scenarios 4–5).
- **The lockstep rule is deleted (`§6.2.3`, `§13.2 HR-3`):** Unpinned non-code-owned closure edits are valid; `baselines[-1]` keeps running until Stephen advances the pin. Unparseable/unknown-`format` evidence exits `2` (`ERROR`); new files, rules, and constants lag silently (`exit 0`), while a new key under a known `format` is an evidence-validation failure (`§6.6`, `HR-3`), and every known evidence file present at `<head>` is parsed on every run.
- **No PR-time pin-advance gate (`admission-controls`):** Runs `L1_LIVE`, F1 tests, `--verify-watched-to-fail` against assembled `baselines[-1]` `--code-root` (§10.3), and optional K1 (no `HEAD` blob check, gating row check, verdict comparison, or `gh` calls). Pin advances rely on Stephen's review + manual comparison evidence (§6.2.2, `HR-3`).

Because `<head>`-only evaluation fails via atomic disarm, retroactive false positives/blessing, and self-edits, WP9.5 enforces:

| Evidence / artifact | Evaluated at / how | Why |
|---|---|---|
| `registration-manifest.json` (Rules 1, 3) | **`P1` union `C`** ($\text{Manifest}(P_1) \cup \text{Manifest}(C)$) | Blocks atomic disarm and retroactive false positives. |
| `legacy-write-records.json` (Rules 1–3) | **Commit `C`** | Requires in-PR record at `C` (`06v:212,479-481`); blocks retroactive blessing. |
| `shared-surface-changes.json` (Rule 3) | **Commit `C`** (or `<head>` with Rule 3 `acknowledged`) | Binds late recovery to WP9.3 `check_change_list` (`evidence.py:190-218`, `acceptance.py:121-136`). |
| Monotonicity & rows (**Rule 0**) | **Every `P1 -> C` in `(b0, head]`** | Ledgers & `walk-baseline.json` monotonic; `baselines[0]`/`[k]` pass (i)–(iv); Rule 0.3 covers `detector-controls.json`; cleared only by validated `rule0_exemptions` (§6.5.1). |
| Pinned closure code | **Confined `cat-file blob` + post-loop `hash-object --no-filters` + `python -S -P`** | Assembles **21** stdlib runtime modules (+ workflow review blob); refuses traversal/`isreserved`/`~`/`casefold()`; child `[sys.executable, "-S", "-P", ...]`, `PYTHONSAFEPATH=1`, `1x` walk (§6.2.3, §10.2). |

---

### 6.2 The walk baseline (`walk-baseline.json`), acknowledged violations, pin-advance comparison procedure, and import closure

#### 6.2.1 Summary of first-parent commits touching guarded prefixes between `4b143c92` and `dbd54fe3`

`git --no-replace-objects rev-list --first-parent --reverse 4b143c9225035cc29e37351445f1c3a4ab09ceb1..dbd54fe382e7b2849d3f2038393cbdb4d709477b` yields **320** commits, of which **22** touched guarded paths (`CONVENTIONS.md`, `results/`, `papers/`, `contracts/`, `.apm/`): 9 `CONVENTIONS.md`-only PRs (`#172`, `#178`, `#183`, `#278`, `#345`, `#376`, `#384`, `#419`, `#425`), 1 mixed PR (`#277` `1dbf6b7b`), 3 `.apm/tracker.md` Working-Note PRs (`#368` `452352ff`, `#388` `e3519ba7`, `#433` `a6a98966`), 3 contract PRs (`#168`, `#169`, `#334`), 3 results PRs (`#125`, `#129`, `#401`), 2 direct pushes (`5df0c001`, `811d5a2b`, `W9-T7`), and 1 revert PR (`#219` `b132406e`). Reproduced in §21.1 item 3 (`wp9-5-note-r2-review-2026-11-21.md:137-148`, `wp9-5-note-r3-review-2026-11-21.md:107-117`).

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
     ],
     "rule0_exemptions": []
   }
   ```
   *(Top-level keys are closed and Rule 0.2-protected (§6.5): `format` is immutable; `d8_rule_suites_limit_decision_ref` is immutable once non-null; `baselines`, `acknowledged`, `ruleset_gap_acknowledgements`, and `rule0_exemptions` (initialized to `[]` in row `0`, §6.5.1) are strictly append-only. `baselines[0]` holds `{"baseline_commit", "recorded_in_decision_ref", "detector_closure_blobs", "pre_baseline_dispositions_ref"}` (`R4-i6`); `baselines[k]` ($k \ge 1$) holds `{"recorded_in_decision_ref", "detector_closure_blobs"}`. Compute closure blobs via `git rev-parse :<path>` or `git hash-object --path=<path> <path>` because `.gitattributes:14` sets `* text=auto eol=lf` and `.claude/rules/apm-outputs.md:37` forbids raw `git hash-object <file>` on CRLF trees.)*
2. **Baseline, intervals, pin, and loud exit `2` (`R5-m1`, `R6-M1`, `R6-i5`):**
   - `baselines[0]["baseline_commit"]` fixes the immutable walk start (first-parent ancestor of L-1). Pre-baseline `(4b143c92, baselines[0]["baseline_commit"]]` dispositions are recorded at L-1 in `pre_baseline_dispositions_ref` (§21.1 item 3 covers `(dbd54fe3, b0]`); `(baselines[0]["baseline_commit"], head]` is walked `1x` per post-merge run with `baselines[-1]["detector_closure_blobs"]`.
   - CLI test flags (`--baseline`, `--head`, `--pr-map`, `--manifest-file`, `--verdict-json`, `--acknowledged-from`) without `--ruleset-check skip` exit `2` (§6.3 item 4); `baselines[0]["baseline_commit"]` and referenced commits must lie on `rev-list --first-parent <head>`. Every WP9.5 tool wraps `main()` to exit **`2`** (`ERROR`, never `0`/`1` — tools only, not pin step) on unparseable evidence, unknown `format`, or uncaught errors; exit `1` is reserved for Rules 0–3 on readable evidence (§6.6 item 1).
3. **Clearable true positives: append-only `acknowledged` list (Owner Point C):**
   - Row `{"commit", "rule", "path", "old_blob", "new_blob", "disposition_ref", ...}` (for `rule == "Rule 3"`, also `"independent_review"` per §6.4 item 2):
     1. `a["commit"]` lies on `<head>`'s first-parent chain strictly after `baselines[0]["baseline_commit"]`.
     2. `a["disposition_ref"]["source_commit"]` satisfies `commit < source_commit <= P1(C_ack)`, and the `### <id>` slice's SHA-256 equals `entry_sha256` both at `source_commit` and at `P1(C_ack)`, so the cited commit really contains the entry (CodeRabbit on #449, `4674677029`). The slice names `commit[:8]`, `rule`, `path`, `old_blob[:8]`, and `new_blob[:8]`.
     3. Scope: exempts only `(commit, rule, path, old_blob, new_blob)`.
     4. **Rule 3 late change-list & review:** `rule == "Rule 3"` also requires `independent_review` at `P1(C_ack)` (`W9` §4.3, `09-migration-compatibility-and-pilot.md:183-188`) and a matching `<head>:shared-surface-changes.json` entry `(pr_number_or_null, path, old_blob, new_blob, affected_registrations)`: `affected_registrations` non-empty unless `"none derived"` appears in both slice and review (`evidence.py:221-252` permits `[]` structurally); `pr_number` = `pr_number(commit)` or `null` strictly for ack-only unmapped direct pushes. *Why WP9.3 accepts late entries:* `check_change_list` (`research_system/legacy/evidence.py:190-218`; `acceptance.py:121-136`) binds `git_blob` at `git_head` (so post-entry acceptances enforce it while prior acceptances retain their verdicts).
4. **Post-merge walk (`1x`), runnable comparison procedure, advisory report, and walk cost (*pin design decided by Stephen, 2026-11-22, for `P-090`*):**
   - **Post-merge walk (`1x`):** `.github/workflows/legacy-write-detector.yml` and `run_w9_pinned_detectors.py` assemble `baselines[-1]` and walk `(baselines[0]["baseline_commit"], head]` once.
   - **Runnable comparison procedure (manual review evidence on `baselines[k]`, $k \ge 1$; not a gate; L-1 row `0` checks Rule 0.2 (i)–(iv) only):** In **Git Bash** (or `cmd /c`):
     1. **Build `<candidate>`:** `git fetch origin pull/<N>/merge && git branch -f candidate FETCH_HEAD` (or `candidate=$(git commit-tree <PR_tree> -p <pr_base> -m "candidate")`).
     2. **Assemble `<dirA>` (`k-1`) and `<dirB>` (`k`)** using `run_w9_pinned_detectors.py` from `origin/main` (`--assemble-only --rev <rev> --out <dir>`, enforcing §6.2.3/§10.2 confinement + post-loop `hash-object --no-filters`):
        `git --no-replace-objects show refs/remotes/origin/main:tools/run_w9_pinned_detectors.py | python -S -P - --assemble-only --rev <pr_base> --out <dirA>` (repeat with `--rev <candidate> --out <dirB>`).
     3. **Attach code diff & re-record controls (`R6-m7`):** List every changed closure path in row `k` and attach `git --no-replace-objects diff <old_blob> <new_blob>` (showing prior non-code-owned edits captured in row `k`); re-record `detector-controls.json` in the PR.
     4. **Run each assembled tool** (`PYTHONHOME`/`VIRTUAL_ENV` unset, `PYTHONSAFEPATH=1`): **Read the step 3 diff before step 4. Step 4 runs untrusted code: run it with `--pr-map` from a prior run, or with a token limited to `pull-requests: read`.**
        `PYTHONPATH=<dir> python -S -P <dir>/tools/check_legacy_writes.py --repo-root . --ruleset-check skip --baseline <b0> --head <candidate> --pr-map <prior-run-pr-map.json> --verdict-json --acknowledged-from <pr_base>` (`--acknowledged-from <pr_base>` supplies both `acknowledged` and `rule0_exemptions` from `<pr_base>`, §6.5.1. `--pr-map` is required here, not only in tests: an unmerged candidate has no merged PR, so the PR lookup cannot map it. Step 4's precondition says where the map comes from.)
     5. **Diff sorted `w9-verdict/1` JSONs:** Exit `0`/`1` emits `{"format": "w9-verdict/1", "error": null, "verdicts": {"<40-hex>": [["Rule 0.1", "path"], ...]}}` (covering **`Rule 0.1`, `Rule 0.2`, `Rule 0.3`**, and Rules 1–3 with no timing/retry counts and no Rule 0.2 (v)); exit `2` emits `{"format": "w9-verdict/1", "error": "<text>"}`. Any `ERROR` on either/both sides is reported as `ERROR`, never clean.
     6. **Write slice lines:** In `recorded_in_decision_ref`'s `### P-0xx` slice, list **`candidate | <rule> | <path>`** (pre-merge squash candidate) or **`V[:8] | <rule> | <path>`** (`V` in `(b0, pr_base]`). Rules 1–3 green-to-red differences at an earlier `V` that need clearing need `acknowledged` in the same PR. A Rules 1–3 violation at the candidate itself cannot be acknowledged in its own PR, because `commit < source_commit <= P1(C_ack)` has no commit to satisfy it there: fix it before merge, or acknowledge it in a later PR whose `source_commit` lies after the landed commit (CodeRabbit on #449, `4674677021`). (Rule 0 cannot use `acknowledged`; Rule 0 recovery uses §6.5.1 `rule0_exemptions`, never the same commit as the violation—a pin-advance PR may carry exemption rows for an earlier `V` in `(b0, pr_base]` whose `R0-EXEMPT` lines already exist at `P1`). Completeness is a human review check (`HR-3`, `§6.5` Rule 0.2 (iv)).
   - **No PR pin-advance gate in `admission-controls`:** No `HEAD` blob check, gating row check, verdict diff, or `gh` call; optional advisory Rule 0.2 row report compares `HEAD` vs `HEAD^1`, writes to `$GITHUB_STEP_SUMMARY`, and exits `0` (`R6-i4`).
   - **Measured `1x` stand-ins & pre-code walk stop rule (§12.3, §15.2 item 5, §21.1 item 10):** Local 6-call `1x` stand-ins (no full Rules 0–3 eval): **`14.05s`** (`60` commits, 6 guarded), **`34.46s`** (`178`, 12), **`62.84s`** (`320`, 22) with **up to ~28% spread across three independent runs** (R5: `11.79s`/`34.85s`/`61.58s` + `~11.3s` `gh api`; R6: `12.97s`/`44.03s`/`77.7s` + `26.35s` 2x@60); 2-tool comparison ~2x (R5 `24.04s` @60; `68.92s`/`125.68s` **extrapolated as `2 × 1x`**). **Stop rule (§15.2 item 5):** if a real `1x` walk + `gh api` exceeds **`600s`**, stop for a **design amendment**, never a runtime flag (`UNVERIFIED-5`, §15.1, §21.2).

#### 6.2.3 Detector import closure, stdlib-only isolation, no-lockstep trade-off, and operator-machine pinning

1. **Deterministic AST closure & `detector_closure_blobs` (`compute_detector_import_closure(repo_root, entry_scripts)` in `tools/_w9_detector_evidence.py`, **new**):** Walks `ast.Import`/`ast.ImportFrom` (`research_system` & `tools`, incl. `__init__.py`) across **6** runtime `tools/` scripts (`check_legacy_writes.py`, `check_conventions_legacy_locks.py`, `check_legacy_log_baseline.py`, `run_w9_detector_controls.py`, `run_w9_pinned_detectors.py`, `_w9_detector_evidence.py`) + **15** existing `dbd54fe38` modules = **21** stdlib runtime modules, plus `.github/workflows/legacy-write-detector.yml` as a **review record only** (never executed from `$DETECTOR_DIR`, `R6-i1`) = **22** entries (`pyproject.toml`, `uv.lock`, and M-6 `export_w9_registration_manifest.py` omitted; §2.3, `HR-7`).
2. **Stdlib/ASCII checks, confinement, & `python -S -P` isolation (§21.1 items 9, 11):**
   - `test_recorded_detector_import_closure_covers_ast_walk` and `test_detector_closure_is_stdlib_only` run on the tree assembled from `HEAD`'s `baselines[-1]` by the §10.2 pin step body (and on synthetic repositories), never on the checkout's non-code-owned closure modules. They assert a property of the pin: it is closed under its own imports and uses the standard library only. A production edit that adds an import to a non-code-owned closure module is not a violation and leaves `admission-controls` green; it surfaces at the next pin advance, where the row's own tests and the §6.2.2 comparison judge it. Alongside `test_detector_closure_is_stdlib_only` (21 runtime modules; 15 existing = 0 third-party imports) and `test_recorded_detector_import_closure_covers_ast_walk`, `test_pinned_wrapper_is_self_contained_stdlib_only`, **`test_pinned_wrapper_is_ascii_only`** (`R6-m2`), and `test_derived_closure_tools_and_accepted_w9_are_codeowned` (`I1` `w9_segmentation.py` choice) enforce ASCII wrapper safety and CODEOWNERS.
   - §10.2 & `run_w9_pinned_detectors.py` refuse **`casefold()`** collisions, require `PurePosixPath(rel_path).as_posix() == rel_path` (no `/`, `\`, `:`, `..`, `.`, `~`, trailing `.`/space, or **`os.path.isreserved`**), catch `CalledProcessError`/JSON errors with named refusals, check `cat-file -t == "blob"` + `dest.resolve().is_relative_to(detector_dir.resolve())`, and **post-loop re-hash every written key** via `dest.is_file()` & `git --no-replace-objects hash-object --no-filters <dest> == blob_sha` (`R6-m1`, `R6-i3`).
   - Runs with cleared `PYTHONHOME`/`VIRTUAL_ENV`, `PYTHONPATH="$DETECTOR_DIR"`, `PYTHONSAFEPATH=1`, `python -S -P` (`3.13.x` Recommended vs `3.13.5`), spawning children via `[sys.executable, "-S", "-P", ...]` (§21.1 item 9).
3. **No-lockstep lag trade-off (`2026-11-22` decision):** Non-code-owned closure edits need no `baselines` row; `baselines[-1]` stays active—exiting `2` on unparseable/unknown-`format` evidence, or `0` silently for new files, rules, and constants the older pin does not read; a new key under a known `format` is an evidence-validation failure (`§6.6`), and every known evidence file present at `<head>` is parsed on every run (`HR-3`).
4. **Operator-machine wrapper (`tools/run_w9_pinned_detectors.py`):** ASCII stdlib-only file run in **Git Bash** (or `cmd /c`; never PowerShell 5.1, which re-encodes streams, `R6-m2`) pre-batch & weekly (`06v:603-604`):
   ```bash
   git fetch --no-tags origin main:refs/remotes/origin/main
   git --no-replace-objects show refs/remotes/origin/main:tools/run_w9_pinned_detectors.py | python -S -P - --repo-root .
   ```
   Verifies `origin/main == git ls-remote origin refs/heads/main`, checks `W9_DETECTOR_PIN` (`gh api`, `encoding="utf-8"`) under I3 (`UNVERIFIED-4`), assembles confined `$DETECTOR_DIR`, launches `[sys.executable, "-S", "-P", ...]` for all 3 detectors + `run_w9_detector_controls.py --code-root "$DETECTOR_DIR" --repo-root . --verify-watched-to-fail ...`, **propagates child exit `2`** (`R6-i5`), and supports `--assemble-only --rev <rev> --out <dir>` (§6.2.2). (`export_w9_registration_manifest.py` runs unpinned in I1 CODEOWNERS; `HR-7`).

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
4. **Explicit UTF-8 subprocess decoding and `main()` exit-`2` exception wrapper (`R5-m1`, `R5-m9`, `R6-M1`, `R6-m4`, `R6-i5`):**
   - Every `git` and `gh` subprocess invocation across all WP9.5 tools passes `encoding="utf-8"` explicitly (matching `tools/check_bypass_merges.py:140-144`, avoiding Windows ANSI `charmap` `UnicodeDecodeError`).
   - Every WP9.5 tool (`tools/check_legacy_writes.py`, `tools/check_conventions_legacy_locks.py`, `tools/check_legacy_log_baseline.py`, `tools/run_w9_detector_controls.py`, `tools/run_w9_pinned_detectors.py`, `tools/export_w9_registration_manifest.py`) wraps `main()`, and **every entry shim performs its closure/tool imports inside the guarded function** (`R7-m1`) so import-time failures in the assembled tree, unparseable JSON, unknown `format` strings, and uncaught exceptions exit **`2`** (`ERROR`, never `0`/`1` — tools only, not pin step), with `--verdict-json` emitting `{"format": "w9-verdict/1", "error": "<text>"}` (`§6.2.2`, `§6.6`).

---

### 6.4 The W9 §4.2 record: format, evaluation at `C`, and provenance verification at `P1`

- **Location:** `.research-system/evidence/w9/legacy-write-records.json` (format `"w9-legacy-write-records/1"`, added as a dated row in `06v-addendum-2026-11-10-w9-paths.md` under Owner Point B).
- **Evaluated at `C`:** When commit `C` (with first parent `P1`, mapped to `pr_number`) touches a guarded path, the detector reads `<C>:.research-system/evidence/w9/legacy-write-records.json`.
- **Provenance checks and `Option I1` dependency:** `P1` ancestry proves only pre-PR age (since `03-decisions-and-open-questions.md` & `reviews/` are un-owned and ruleset `20822054` has `required_approving_review_count: 0`). Thus **Option B1's tamper resistance depends on Option I1** (`@stephendor` over `.research-system/evidence/w9/`), and requiring `source_commit`/`review_commit` at `P1` enforces W9 §4.2(b) (`09-migration-compatibility-and-pilot.md:174-176`; B2 is the same-PR alternative).
  1. **Pre-existing owner decision (`owner_note` at `P1`):** For `"repo_wide_change_4_2_b"`, `"owner_ruling_4_2_c"`, `"shared_surface_4_3"`: validates `decision_entry_id` (`^P-[0-9]{3}[a-z]?$`), `source_path`, `is_ancestor(source_commit, P1)`, & slice `entry_sha256` naming every `(normalized_path, old_blob[:8], new_blob[:8])` (`fecfc1da`, `6024-6088`).
  2. **Pre-existing independent review (`independent_review` at `P1`):** For `"repo_wide_change_4_2_b"` & `"shared_surface_4_3"`: validates `review_path` (`docs/plans/agentic-research-system/reviews/<file>.md`), `is_ancestor(review_commit, P1)`, `review_sha256` at `<P1>:<review_path>`, & presence of `decision_entry_id` + every `(normalized_path, old_blob[:8], new_blob[:8])`.
  3. **CODEOWNERS / Rule 0 (Option I1, §16.1):** Adds `.research-system/evidence/w9/`, workflow, 7 `tools/` modules, `test_w9_detectors.py`, and `accepted_w9.py` to `.github/CODEOWNERS` (`@stephendor`).
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

#### Rule 0 — Monotonicity of W9 evidence files (`Rule 0.1`, `Rule 0.2`, `Rule 0.3`)

1. **`Rule 0.1` — `registration-manifest.json` is strictly append-only:**
   Every entry present at $P_1$ remains present with identical fields at $C$; otherwise fail closed (`ERROR: post_merge_first_parent: Rule 0 violation at commit <C>: registration-manifest.json deleted or modified existing registration entry <entry>`).
2. **`Rule 0.2` — Evidence ledgers, all top-level fields + rows of `walk-baseline.json`, and L-0b classification:**
   - `legacy-write-records.json`, `shared-surface-changes.json`, and `vault-detector-runs.json` are strictly append-only on entries: every entry at $P_1$ stays byte-identical at $C$, and any new `legacy-write-records.json` entry at $C$ has `entry["pr_number"] == pr_number(C)`.
   - Top-level fields of `walk-baseline.json` are governed: `format` (`"w9-walk-baseline/1"`) is immutable; `d8_rule_suites_limit_decision_ref` is immutable once non-null and any non-null value passes the `P1` hash-bound check naming `"D-8"` and `"rule-suites"`; `baselines`, `acknowledged`, `ruleset_gap_acknowledgements`, and `rule0_exemptions` (`[]` in row `0`; §6.5.1) are strictly append-only.
   - **Row 0 and every appended `baselines[k]` ($k \ge 1$) pass (i)–(iv)** (evaluated at creating commit `C_0`—with `P1(C_0)`—or `C_k`):
     (i) closed keys: `{"baseline_commit", "recorded_in_decision_ref", "detector_closure_blobs", "pre_baseline_dispositions_ref"}` (row `0`), or `{"recorded_in_decision_ref", "detector_closure_blobs"}` ($k \ge 1$, no second `baseline_commit`);
     (ii) every `(p, expected_blob)` in `detector_closure_blobs` equals `git --no-replace-objects rev-parse <C>:<p>`;
     (iii) `recorded_in_decision_ref` (plus `pre_baseline_dispositions_ref` on row `0`) passes the `P1` hash-bound slice check; and
     (iv) for $k \ge 1$, `recorded_in_decision_ref`'s slice names every added/removed/changed path vs `baselines[k-1]` with `new_blob[:8]` (or `"no blob change"`), plus any §6.2.2 verdict lines (completeness is human-reviewed, `HR-3` (b); post-merge checks only `V[:8] | <rule> | <path>` or `candidate | <rule> | <path>` grammar and that `V` resolves in `(b0, C_k]`).
   - **Appended `ruleset_gap_acknowledgements` ($C_{\text{gap}}$):** closed `{"previous_recorded_at", "acknowledged_through", "disposition_ref"}`, `P1` slice naming both timestamps.
   - **Appended `acknowledged` ($C_{\text{ack}}$):** `commit < source_commit <= P1(C_ack)` with §6.2.2 item 3 slice verify; `rule == "Rule 3"` also requires `independent_review` at `P1(C_ack)` & matching `<head>:shared-surface-changes.json` entry (§6.2.2 item 3.4).
   - Once `ACCEPTED_CONVENTIONS_CLASSIFICATION` (`accepted_w9.py`) is populated at L-0b, its JSON path is immutable.
   - Failure: `ERROR: post_merge_first_parent: Rule 0 violation at commit <C>: evidence file '<path>' violated append-only, validation, or immutability invariants`
3. **`Rule 0.3` — `detector-controls.json` monotonicity:** Once present at $P_1$, cannot be deleted at $C$, and updates pass `require_detector_controls` (`evidence.py:133-154`) with `recorded_at` $\ge$ $P_1$.
   - *Exemption scope (§6.5.1):* Exemptable `Rule 0.1`–`Rule 0.3` violations clear solely via validated exact-tuple `rule0_exemptions` rows; unexemptable invariants in §6.5.1 never clear.

#### Rule 1 — Registered `git_tracked` legacy files (`06v:477`; `W9:172-181`)

- **Manifest at `P1` union `C`:** $\mathcal{M}(P_1, C) = \text{Manifest}(P_1) \cup \text{Manifest}(C)$. Excludes entries where `root_kind != "repository_root"`, `source_identity_kind != "git_tracked"`, or `role` $\in$ `{"conventions_lock", "shared_enforcement_surface", "successor_results_root", "legacy_read_only_projection"}`.
- **Path matching:** Case-folded exact match (`role != "legacy_manuscript_root"`), or prefix match (`papers/P01-A-JRSSA/`, `papers/P01-B-JRSSB/`, `reader.py:51,289-299`).
- **`.apm/tracker.md` (Owner Point H, §16.9):** Under H1 (Recommended), passes Rule 1 iff `check_tracker_working_note_append(raw_P1, raw_C)` (`segment(raw, "tracker_task_row")` & `"working_note_entry"`, `segmentation.py:470-473`) confirms identical bytes outside `## Working Notes`, prior entries preserved verbatim with 0 blockers, and `[ \t]*\n` gaps (`452352ff`, `e3519ba7`, `a6a98966`, `wp9-5-note-r2-review-2026-11-21.md:219`).
- **All other matches:** Unless `acknowledged` exempts `(C, "Rule 1", p, b_old, b_new)`, requires mapped `pr_number`, `b_old != b_new`, and valid `P1` §4.2 record (§6.4). Exit `1`:
  `ERROR: post_merge_first_parent: Rule 1 violation at commit <C> (pr=<pr_or_none>): registered path '<p>' changed (<b_old> -> <b_new>) without a valid in-commit W9 §4.2 record`

#### Rule 2 — Any path under `results/` outside `results/ars/` (`06v:478`; `W9-D13`, `W9-D14`, `W9:140-147,196`)

- Case-folded prefix `"results/"` not `"results/ars/"` (`W9-D14` `09-migration-compatibility-and-pilot.md:768` so unregistered `results/` families, `W9-D13` `:767`, remain guarded pre-registration). Requires §4.2 record at $C$ (or `acknowledged`); else exit `1`:
  `ERROR: post_merge_first_parent: Rule 2 violation at commit <C> (pr=<pr_or_none>): results path outside results/ars/ '<p>' changed (<b_old> -> <b_new>) without a valid in-commit W9 §4.2 record`

#### Rule 3 — `shared_enforcement_surface` contracts (`06v:212,479-481`; `O-32`; `W9:183-190`; Owner Point D)

- **Surfaces:** `{r["normalized_path"] for r in M(P1, C) if r["root_kind"] == "repository_root" and r["role"] == "shared_enforcement_surface"}` (`contracts/manifests/research-assurance.yaml`, `monte-carlo-permutation-p-value.yaml`, `markov-order-provenance.yaml`, `null-operation-changes-ph-input.yaml`; `W9:166`).
- **Requirements:** Unless Rule 3 `acknowledged` + `independent_review` + `<head>:shared-surface-changes.json` entry exempts it (§6.2.2 item 3.4), needs mapped `pr_number`, `shared_surface_4_3` record with `owner_note` & `independent_review` at $P_1$, and matching `<C>:shared-surface-changes.json` entry.
- **Resolving `O-32` (`06v:90-91` vs `evidence.py:231-238`, `acceptance.py:135`; §16.5):** D1 races under merge queue; D2 leaves a red window. **Option D3 (`"w9-shared-surface-changes/2"`, uniform `/2` with A1)** closes entries on `{"pr_number", "surface", "old_blob", "new_blob", "affected_registrations"}` (`pr_number` int or ack-only `null`); in `acceptance.py:121-136` (`check_change_list`), passes at `obs_commit` iff `evidence.blob_at(repository_root, obs_commit, entry["surface"])` (`evidence.py:179-188`) matches `entry["new_blob"]` or a later `new_blob` *(tree-state semantic; `A -> B -> A` in `HR-2`)*.
- **Failure (exit `1`):**
  `ERROR: post_merge_first_parent: Rule 3 violation at commit <C> (pr=<pr_or_none>): shared_enforcement_surface '<s>' changed (<b_old> -> <b_new>) without a valid in-commit shared-surface-changes.json entry and W9 §4.3 owner note`

#### 6.5.1 Rule 0 exemption rows

Per Owner Point C (`P-090` item 2 C & item 4 `0e1269bd`, item 5 `813088e9`), an exemptable Rule 0 violation on the post-merge walk clears only through an append-only, hash-bound exemption row backed by a pre-existing register entry:

1. **Where it lives, blast radius (`X-i1`), & row-`0` pinned-copy rule:** `"rule0_exemptions"` lives as a required closed top-level list (initialized to `[]` at row `0`) in `.research-system/evidence/w9/walk-baseline.json` (`"w9-walk-baseline/1"`, `EVIDENCE_DIRECTORY` `research_system/legacy/evidence.py:36`, inside I1-CODEOWNED `/.research-system/evidence/w9/`). Co-locating it inside `walk-baseline.json` avoids adding a new `06v-addendum` path, `<head>` parse target (§6.6 item 1), or `L1_LIVE` file check, and lets `--acknowledged-from <rev>` load both `acknowledged` and `rule0_exemptions` in one `git show`; its cost is blast radius—a defective exemption row sits in the file holding the pin and walk start—mitigated by item 3's mandatory pre-merge run (`X-i1`). Under `§6.6` item 1 (`R7-m2`), a new key under known `"w9-walk-baseline/1"` raises `EvidenceSchemaError` (`exit 1`, `["Rule 0.2", "<path>"]`), not `UnknownEvidenceFormatError` (`exit 2`); because L-1 has not happened yet, `"rule0_exemptions": []` **must exist from row `0`** so every pinned copy accepts it from day one without an exit-`1`/exit-`2` split (unknown `"format"` values at `<head>` still exit `2`).

2. **Row format (closed keys only), sub-check `location` (`X-m2 (a)`), & blob-less transitions:** Each row uses 7 closed keys (`_closed` style, `research_system/legacy/evidence.py:108-111`): `{"commit", "rule", "path", "location", "old_blob", "new_blob", "disposition_ref"}`:
   ```json
   {
     "commit": "<40-hex>",
     "rule": "Rule 0.2",
     "path": ".research-system/evidence/w9/walk-baseline.json",
     "location": "baselines[3]#iii",
     "old_blob": "<40-hex-or-null>",
     "new_blob": "<40-hex-or-null>",
     "disposition_ref": {
       "id": "P-09z",
       "source_path": "docs/plans/agentic-research-system/03-decisions-and-open-questions.md",
       "source_commit": "<40-hex-strictly-after-commit-and-at-or-before-P1-of-C_ex>",
       "entry_sha256": "<64-hex>"
     }
   }
   ```
   - Allowed `(rule, path)` pairs: `Rule 0.1` $\to$ `registration-manifest.json`; `Rule 0.3` $\to$ `detector-controls.json`; `Rule 0.2` $\to$ `walk-baseline.json`, `legacy-write-records.json`, `shared-surface-changes.json`, `vault-detector-runs.json`, L-0b `ACCEPTED_CONVENTIONS_CLASSIFICATION` JSON path, `EvidenceSchemaError` (`§6.6` item 1) on `registration-manifest.json`/`detector-controls.json`, or non-`<head>` `EvidenceParseError`/`UnknownEvidenceFormatError` (`X-M1`).
   - `location`: `"$"` for whole-file, non-`<head>` parse/unknown-format, or top-level `EvidenceSchemaError` faults (where `(old_blob, new_blob)` hashes the single-purpose file transition); on `walk-baseline.json` list items, `^(?:baselines\[(0|[1-9][0-9]*)\]#(?:append_only|i|ii|iii|iv)|(?:acknowledged|ruleset_gap_acknowledgements)\[(0|[1-9][0-9]*)\]#(?:append_only|valid))$` (`X-m2 (a)`) so one row clears one failed sub-check rather than masking a sibling sub-check or unexemptable field changed in the same commit (`P-090` item 5 adds no `rule0_exemptions[k]` location).
   - `old_blob` / `new_blob`: lowercase 40-hex blob OID or JSON `null` (`str | None` matching `blob_at` at `research_system/legacy/evidence.py:179-187`, mapping `diff-tree`'s `0`$\times 40$ null OID to `null`), never both `null`: deletion uses `"new_blob": null` (never on `walk-baseline.json`), file creation uses `"old_blob": null`, and a `P1`/`C` fault without blob change uses `old_blob == new_blob` (both 40-hex). A deleted-then-restored file (other than `walk-baseline.json`) requires both the deletion row (`new_blob: null`) and, where re-creation violates Rule 0 (such as `legacy-write-records.json`), an `old_blob: null` row (`X-m5`, HR-3).

3. **Validity rules & mandatory pre-merge run (`X-M2`, `X-m1`, `X-i3`):** Every row `e` newly appended at `C_ex` (first parent `P1(C_ex)`) must satisfy all 4 checks (any failure emits an **unexemptable** `Rule 0.2` error at `C_ex` and grants no exemption; **a later row cannot clear a validity fault in an earlier one**, `P-090` item 5):
   - *Schema & uniqueness:* exact closed keys/types on `e` and `e["disposition_ref"]` (`id` matching `^P-[0-9]{3}[a-z]?$`, `source_path` fixed to `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`, 40-hex `source_commit`, 64-hex `entry_sha256`), valid `(rule, path, location)` pairing, non-unexemptable target, and no duplicate 6-tuple already in `rule0_exemptions`.
   - *Strict chain & temporal order (`X-m1`):* Build `fp_index` from `git --no-replace-objects rev-list --first-parent --reverse <b0>..<head>` with `fp_index[b0] = -1` (§6.3 item 2; **stricter than** `is_ancestor`, `research_system/legacy/evidence.py:159-176`, which traverses all parents rather than first-parent only). Require `e["commit"]` and `source_commit` in `fp_index` with `0 <= fp_index[e["commit"]] < fp_index[source_commit] <= fp_index[P1(C_ex)] < fp_index[C_ex]`; a row appended at a commit whose first parent is `b0` (`fp_index[P1(C_ex)] == -1`), or with `e["commit"] == b0`, is invalid (never raising `KeyError`).
   - *Hash-bound slice, stated line grammar, & provenance (`X-i3`):* Extract the `### <id>` slice from `<P1(C_ex)>:<source_path>` and from `<source_commit>:<source_path>` (as for `acknowledged`, §6.2.2 item 3.2); both SHA-256 values must equal `entry_sha256`, so `source_commit` really contains the entry it cites (CodeRabbit on #449, `4674677029`). At least one stripped line (optional leading `- `) must match `^R0-EXEMPT \| ([0-9a-f]{8}) \| (Rule 0\.[123]) \| ([^|\s]+) \| ([^|\s]+) \| ([0-9a-f]{8}|null) -> ([0-9a-f]{8}|null)$` with fields equal to `(commit[:8], rule, path, location, old_blob[:8] or "null", new_blob[:8] or "null")`. Because the register is un-owned (`HR-1`), the slice proves age rather than authorship, `source_commit` is bound to the entry by the two-point hash above, and "before the PR" holds as "before the appending commit" under squash-only `main`; authority rests on Stephen's I1 CODEOWNERS review of the row PR (`X-i3`).
   - *Git blob confirmation:* `old_blob == blob_at(P1(e["commit"]), path)` and `new_blob == blob_at(e["commit"], path)` (`evidence.py:179-187`).
   - *Required pre-merge run (`X-M2`, `P-090` item 5 `813088e9`):* A PR that appends to `rule0_exemptions` or otherwise changes `walk-baseline.json` (including L-1 row `0`) carries, in its description, the output of `check_legacy_writes.py --repo-root . --ruleset-check skip --baseline <b0> --head <candidate> --pr-map <prior-run-pr-map.json>` (the §6.2.2 step 4 command, without `--verdict-json` diff or `--acknowledged-from`) showing no new `Rule 0.2` fault at `<candidate>`. The register slice's `entry_sha256` is recomputed against `<pr_base>` after the last rebase.

4. **What `rule0_exemptions` may NOT exempt & malformed intermediates (`X-M1`, `X-m3`, `X-m7`):** Checked unconditionally so a same-commit row on another field never masks them:
   - `rule0_exemptions` itself (any value other than `[]` at row `0`, deletion/mutation of existing rows, extra/missing keys, or invalid appended rows) — prevents self-exemption bootstrap (`X-m7`);
   - commits not on `<head>`'s first-parent chain strictly after `baselines[0]["baseline_commit"]` (or with `commit >= C_ex`);
   - Rules 1–3 (`acknowledged` only, §6.2.2 item 3);
   - `walk-baseline.json["format"]` immutability — rests on §6.6 item 1 alone (§10.2 does not read `format`, `X-m3`): changing `format` at `<head>` raises `UnknownEvidenceFormatError` (`exit 2`) before Rule 0 runs, `format` anchors `rule0_exemptions`'s closed-key contract, and `walk-baseline.json` moves only by a new file path (`P-090` item 5);
   - deletion of `walk-baseline.json` (`new_blob: null`) — destroys `format`, `baselines[0]["baseline_commit"]`, and `rule0_exemptions` together;
   - `walk-baseline.json["baselines"][0]["baseline_commit"]` (immutability/presence) — mutating it would silently truncate `(b0, head]`;
   - `walk-baseline.json["d8_rule_suites_limit_decision_ref"]` (decided unexemptable including its first `null -> non-null` transition, `P-090` item 5 `813088e9`, and its `P1` `"D-8"`/`"rule-suites"` check) — set in row `0` at L-1 and verified by L-1's required pre-merge `--head <candidate>` run (`--ruleset-check ci-d8` independently rejects an invalid ref at `<head>`, §4.2.3);
   - `<head>` exit-`2` errors (§6.6 item 1: `EvidenceParseError` or `UnknownEvidenceFormatError` at `<head>`, missing required `<head>` file, shallow clone, off-chain baseline, or GitHub API failure).
   - **Malformed intermediates (`X-M1`):** When an evidence file fails parsing or schema validation at `P1` or `C`, Rule 0.2's append-only and immutability comparisons, including every unexemptable invariant of item 4, run on raw `json.loads` reads (no closed-key validation) between the nearest earlier first-parent version that parses and the first version at or after `C` that parses. A violation found there is reported at the commit that produced the later version. A violation of one of item 4's unexemptable invariants found there is never cleared by any row. Any other append-only or immutability violation found there stays exemptable under item 3, so a record dropped behind a parse gap can still be exempted (CodeRabbit on #449, `4677581885`; re-review XR-m1). A `"$"` row on a schema fault clears only the schema fault. **`EvidenceParseError` or `UnknownEvidenceFormatError` at a commit other than `<head>`** is a `Rule 0.2` fault at that commit (location `"$"`, exit `1`, exemptable under item 3); at `<head>` it stays exit `2`. **A pin that replaces an evidence format in place** keeps the superseded reader for as long as the walk covers the superseded versions.
   *(Exemptable Rule 0 causes therefore include: defective `baselines[k]` rows incl. concurrent-merge Rule 0.2 (ii) mismatches and slice typos, `acknowledged`/`ruleset_gap_acknowledgements` row errors, extra top-level keys on `walk-baseline.json` clearing `"$"` only, broken append-only ledgers / non-`<head>` parse or unknown-format faults / deleted-then-restored files other than `walk-baseline.json`, and in-place evidence-format changes on those other files under `R7-d1`.)*

5. **Exact tuple matching, recurrence, `--verdict-json`, pin-advance comparison, `R7-d1`, & controls:**
   - *Exact tuple, recurrence, & trace output (`X-i2`):* `check_legacy_writes.py` walks `(b0, head]`, collects all Rule 0–3 findings and validates `rule0_exemptions` rows across `(b0, head]` first, then clears **only** exact 6-tuples `(commit, rule, path, location, old_blob, new_blob)` matching a validated row in the active `rule0_exemptions` snapshot (`<pr_base>` under `--acknowledged-from <pr_base>`, else `<head>`). A sibling rule, `location` (including sibling sub-check `#ii` vs `#iii`), or path at `commit` stays red, and recurrence at any later commit `C2 > C_ex` fails `commit` matching and exits `1` until another post-`C2` register entry and exemption row cover `C2`. For every cleared Rule 0 tuple, `check_legacy_writes.py` emits one diagnostic line (`stderr`, and `$GITHUB_STEP_SUMMARY` in CI) naming the `rule0_exemptions` row index and cleared tuple so exemptions stay visible (`X-i2`).
   - *`--verdict-json` & pin-advance comparison (§6.2.2 steps 4–6):* Cleared Rule 0 tuples are omitted from `verdicts[commit]` (`w9-verdict/1`) identically to `acknowledged`; unexempted/unexemptable faults still emit `["Rule 0.x", "<path>"]` and exit `1`. Loading both `acknowledged` and `rule0_exemptions` from `<pr_base>` keeps `<dirA>` and `<dirB>` aligned while any new Rule 0 fault at `<candidate>` stays visible.
   - *`R7-d1` evidence-format moves (`X-m5`, `X-M1`, `P-090` item 5):* After L-1, an evidence format moves by a **new file path** (keeping the legacy file frozen and still parsed, §6.6 item 1, with zero Rule 0 fault and zero red window), **never in place without a cleared Rule 0 fault**. By `P-090` item 5 (`813088e9`, narrowing item 2 C), **`walk-baseline.json` moves only by a new file path** (re-baseline to be designed when needed). Moving any other evidence file **in place** requires (a) a pin advance supporting both the new format and the superseded reader for as long as the walk covers superseded versions (`X-M1`) and (b) a post-merge register entry + `rule0_exemptions` PR (carrying a red window between merge and `C_ex`); A1 and D3 land pre-code and are unaffected. Tested in §12.1.

---

### 6.6 What `tools/check_legacy_writes.py` does with an unreadable registered file or unmappable commit

1. **Unreadable, unknown-`format`, missing, or malformed evidence files (`R6-M1`, `R7-m1`, `R7-m2`, `X-M1`):**
   - **Every known evidence file present at `<head>`** (`.research-system/evidence/w9/{walk-baseline,registration-manifest,legacy-write-records,shared-surface-changes,detector-controls,vault-detector-runs}.json`) **is parsed on every run** (`R7-m2`).
   - **Total exit-code classification (`R7-m1`, `X-M1`):** Under `--verdict-json`, **every exit `1` carries at least one `(rule, path)` pair**. Because `research_system/legacy/evidence.py:108-131` raises `EvidenceRefused` (`research_system/legacy/evidence.py:69`) for both unknown `format` and closed-key errors, `tools/_w9_detector_evidence.py` defines three `EvidenceRefused` subclasses—**`EvidenceParseError`**, **`UnknownEvidenceFormatError`**, and **`EvidenceSchemaError`**—checking UTF-8/JSON decoding, then that the decoded root is a JSON object, then `body.get("format")`, before delegating closed-key validation to `evidence.py:108-131`. A root that decodes but is not an object (`null`, an array, a number or a string) raises `UnknownEvidenceFormatError`, as a missing `format` key does, never `AttributeError`. So at `<head>` it exits `2`, and at any other commit it is a `Rule 0.2` fault (location `"$"`, exit `1`, exemptable under §6.5.1 item 3) (CodeRabbit on #449, `4677581902`):
     - **At `<head>`, `EvidenceParseError`** (unparseable UTF-8/JSON) and **`UnknownEvidenceFormatError`** (missing or unrecognized `"format"` string) are **`ERROR`: exit `2`** with `--verdict-json` printing `{"format": "w9-verdict/1", "error": "<text>"}`. **At a commit other than `<head>`, `EvidenceParseError` or `UnknownEvidenceFormatError` is a `Rule 0.2` fault at that commit (location `"$"`, exit `1`, exemptable under `§6.5.1` item 3).**
     - **Missing required `<head>` file** (`walk-baseline.json` or `registration-manifest.json` absent once L-1 is active or when `--require-manifest` is set) is **`ERROR`: exit `2`** with `--verdict-json` printing the `"error"` key (a missing file at `<head>` is not a `P1 -> C` diff violation; deleting an existing file on `P1 -> C` triggers Rule 0 exit `1`).
     - **`EvidenceSchemaError`** (**known-`format` closed-key or field-level validation failure** at $P_1$ or $C$, including any extra key under a known `format`, `R7-m2`) exits **`1`** with `ERROR: post_merge_first_parent: invalid evidence file at <commit>:<path>: <reason>` and `--verdict-json` emitting **`["Rule 0.2", "<path>"]`** at that commit. Exit `1` is reserved for violations of Rules 0 to 3 (including `EvidenceSchemaError`, and non-`<head>` `EvidenceParseError`/`UnknownEvidenceFormatError`, as `Rule 0.2`) carrying $\ge 1$ `(rule, path)` pair.
     - **Malformed intermediates & superseded readers (`X-M1`):** When an evidence file fails parsing or schema validation at $P_1$ or $C$, Rule 0.2's append-only and immutability comparisons—including every unexemptable invariant of `§6.5.1` item 4—run on raw `json.loads` reads (no closed-key validation) between the nearest earlier first-parent version that parses and the first version at or after $C$ that parses. A violation found there is reported at the commit that produced the later version, and no row clears it. A `"$"` row on a schema fault clears the schema fault only. A pin that replaces an evidence format in place keeps the superseded reader for as long as the walk covers the superseded versions.
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
       If `ACCEPTED_CL_EXPORT` is empty `()` at the pinned copy and `HEAD` is pre-L-0b (or if L-0b landed without a paired pin advance, §8.3), production mode fails closed with **exit `1`** (`ERROR: vault_computational_log: ACCEPTED_CL_EXPORT is empty; L-0b baseline export has not been accepted yet (if L-0b has landed, the pinned copy predates it: advance the pin)`). When populated at L-0b, reads all three members via `git --no-replace-objects show <git_commit>:<repository_path>` matching `git_blob_id`, `sha256_hex`, and `len`; validates via `evidence.require_cl_export(export)` (`research_system/legacy/evidence.py:277-362`); runs `report = recheck_cl_export(export, retained_raw)` (`research_system/legacy/export_recheck.py:32-89`, producer `CL_EXPORT_PRODUCER`, `tools/w9_segmentation.py` blob `43e1454de09b61e274954c42b21d6ae533857a24`, `evidence.py:52-54`); **explicitly requires `report["void"] is False`** (`recheck_cl_export` does not raise on divergence, `R2-m12` — exit `1` with `ERROR: vault_computational_log: recheck_cl_export reported void=True`); and validates `classified_list` (§8.3). An unparseable export/classified-list JSON or unknown `format` string exits **`2`** (`ERROR`, `R6-M1`).
     - **Fixture mode (`--fixture-export-json <path> --fixture-retained-copy <path> [--fixture-classified-list <path>]`):** Same `require_cl_export` + `recheck_cl_export` (`void == False`) checks from disk (unparseable JSON or unknown `format` exits **`2`**).
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
| `tools/check_legacy_log_baseline.py` | Tested against synthetic `w9-cl-export/1` and `w9-cl-classified-list/1` fixtures via `--fixture-export-json`, `--fixture-retained-copy`, `--fixture-classified-list`. Production mode checks `ACCEPTED_CL_EXPORT` and exits `1` while empty. | **The L-0b PR must be paired with a pin advance** (appending a `baselines` row so the pinned `accepted_w9.py` picks up `ACCEPTED_CL_EXPORT[-1]` and `ACCEPTED_CONVENTIONS_CLASSIFICATION`; until then, the pinned vault detector stays empty and stops with exit `1` while the pinned `CONVENTIONS.md` check silently keeps the 68-unit baseline, `R6-m8`). |

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
3. **CI and wrapper re-verification of `watched_to_fail` hashes after L-1 (`R4-m5`, `R6-M3`):** `tools/run_w9_detector_controls.py --code-root <detector_dir> --repo-root <checkout_root> --verify-watched-to-fail <detector_controls_json>` separates `--code-root` (assembled closure bytes/imports; **`--code-root` has no default**) from `--repo-root` (Git object DB for bare clones), wraps `main()` to exit `2`, uses `encoding="utf-8"` on `git`, and spawns child Python interpreters via `[sys.executable, "-S", "-P", ...]`. **In `admission-controls`, `--verify-watched-to-fail` runs with `--code-root` set to a tree assembled from `HEAD`'s `baselines[-1]` by the §10.2 pin step body, never the checkout; `--code-root` has no default** (executed under `python -S -P` in `admission-controls` §10.3, `.github/workflows/legacy-write-detector.yml` §10.2, and `tools/run_w9_pinned_detectors.py` §6.2.3), failing closed on mismatch (`ERROR: detector_controls: recomputed output_sha256 for '<detector>' does not match detector-controls.json`; M-6 sits outside the 22-blob map, `HR-7`).

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
          main_tip, detector_dir = sys.argv[1], pathlib.Path(sys.argv[2])
          try:
              raw = subprocess.check_output(
                  ["git", "--no-replace-objects", "show", f"{main_tip}:.research-system/evidence/w9/walk-baseline.json"]
              )
              wb = json.loads(raw.decode("utf-8"))
              blobs = wb["baselines"][-1]["detector_closure_blobs"]
              baseline_commit = wb["baselines"][0]["baseline_commit"]
          except (subprocess.CalledProcessError, UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
              raise SystemExit(f"ERROR: invalid walk-baseline.json at {main_tip}: {exc}")
          if not isinstance(blobs, dict) or not isinstance(baseline_commit, str):
              raise SystemExit("ERROR: walk-baseline.json has non-mapping detector_closure_blobs or non-string baseline_commit")
          canonical = json.dumps(blobs, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
          blobs_sha256 = hashlib.sha256(canonical).hexdigest()
          require_i3 = os.environ.get("REQUIRE_I3_PIN", "false").lower() == "true"
          var_raw = os.environ.get("W9_DETECTOR_PIN_VAR", "").strip()
          if require_i3 and not var_raw:
              raise SystemExit("ERROR: W9_DETECTOR_PIN is required under Option I3 but is empty")
          if var_raw:
              try:
                  pv = json.loads(var_raw)
                  pv_base, pv_sha = pv["walk_baseline_commit"], pv["closure_blobs_sha256"]
              except (json.JSONDecodeError, KeyError, TypeError) as exc:
                  raise SystemExit(f"ERROR: invalid W9_DETECTOR_PIN JSON: {exc}")
              if pv_base != baseline_commit:
                  raise SystemExit(f"ERROR: walk_baseline_commit {baseline_commit} != W9_DETECTOR_PIN {pv_base}")
              if pv_sha != blobs_sha256:
                  raise SystemExit(f"ERROR: closure_blobs_sha256 {blobs_sha256} != W9_DETECTOR_PIN {pv_sha}")
          try:
              chain = subprocess.check_output(
                  ["git", "--no-replace-objects", "rev-list", "--first-parent", main_tip], text=True, encoding="utf-8"
              ).splitlines()
          except subprocess.CalledProcessError as exc:
              raise SystemExit(f"ERROR: rev-list failed for {main_tip}: {exc}")
          if baseline_commit not in chain:
              raise SystemExit(f"ERROR: baseline commit {baseline_commit} is not on origin/main ({main_tip}) first-parent chain")
          shutil.rmtree(detector_dir, ignore_errors=True)
          detector_dir.mkdir(parents=True, exist_ok=True)
          resolved_root = detector_dir.resolve()
          seen_folded: dict[str, str] = {}
          written: list[tuple[str, pathlib.Path, str]] = []
          for rel_path, blob_sha in blobs.items():
              if not isinstance(rel_path, str) or not isinstance(blob_sha, str):
                  raise SystemExit(f"ERROR: non-string closure entry {(rel_path, blob_sha)!r}")
              folded = rel_path.casefold()
              if folded in seen_folded:
                  raise SystemExit(f"ERROR: casefold path collision {rel_path!r} vs {seen_folded[folded]!r}")
              seen_folded[folded] = rel_path
              if not rel_path or "\\" in rel_path or rel_path.startswith("/") or ":" in rel_path:
                  raise SystemExit(f"ERROR: invalid closure path key {rel_path!r}")
              pp = PurePosixPath(rel_path)
              if pp.is_absolute() or ".." in pp.parts or "." in pp.parts or pp.as_posix() != rel_path:
                  raise SystemExit(f"ERROR: unconfined closure path key {rel_path!r}")
              if os.path.isreserved(rel_path) or any(
                  "~" in part or part.endswith((".", " ")) or os.path.isreserved(part)
                  for part in pp.parts
              ):
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
              try:
                  dest.write_bytes(subprocess.check_output(["git", "--no-replace-objects", "cat-file", "blob", blob_sha]))
              except subprocess.CalledProcessError as exc:
                  raise SystemExit(f"ERROR: failed reading blob {blob_sha} for {rel_path!r}: {exc}")
              written.append((rel_path, dest, blob_sha))
          for rel_path, dest, blob_sha in written:
              if not dest.is_file():
                  raise SystemExit(f"ERROR: missing written closure file {rel_path!r}")
              try:
                  written_sha = subprocess.check_output(
                      ["git", "--no-replace-objects", "hash-object", "--no-filters", str(dest)],
                      text=True, encoding="utf-8",
                  ).strip()
              except subprocess.CalledProcessError as exc:
                  raise SystemExit(f"ERROR: hash-object failed for {rel_path!r}: {exc}")
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
3. **Confined assembly, post-loop hash check, `python -S -P`, and Option I3 sequencing:** §6.2.3 validation (casefold collision refusal, traversal, absolute, `~`, trailing `.`/space, and `os.path.isreserved`) + post-loop `dest.is_file()` and `git --no-replace-objects hash-object --no-filters` runs before `python -S -P` + `PYTHONPATH="$DETECTOR_DIR"` + `PYTHONSAFEPATH=1` (child `[sys.executable, "-S", "-P", ...]`; `--code-root "$DETECTOR_DIR" --repo-root .` on `--verify-watched-to-fail`). **I3 upgrade sequence:** merge pin advance first, then update `vars.W9_DETECTOR_PIN` (expected red `push` run until update, then `workflow_dispatch` green); Option I1 CODEOWNERS protects the workflow.
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
- **When `L1_LIVE is True` (flipped at L-1, in `ci.yml` `admission-controls` under Option F1):**
  1. `set(doc["on"].keys()) == {"push", "schedule", "workflow_dispatch"}` and `doc["on"]["push"] == {"branches": ["main"]}`;
  2. `.research-system/evidence/w9/{detector-controls,walk-baseline,registration-manifest}.json` exist and pass **schema checks (meaning the top-level shape of those three files only, not their rows, `R6-M3`)** + `require_detector_controls` + `--verify-watched-to-fail`. **In `admission-controls`, `--verify-watched-to-fail` runs with `--code-root` set to a tree assembled from `HEAD`'s `baselines[-1]` by the §10.2 pin step body, never the checkout; `--code-root` has no default** (so editing a non-code-owned closure module without appending a `baselines` row leaves `admission-controls` green, `R6-M3`). **`test_recorded_detector_import_closure_covers_ast_walk` and `test_detector_closure_is_stdlib_only` run on the tree assembled from `HEAD`'s `baselines[-1]` by the §10.2 pin step body (and on synthetic repositories), never on the checkout's non-code-owned closure modules. They assert a property of the pin: it is closed under its own imports and uses the standard library only. A production edit that adds an import to a non-code-owned closure module is not a violation and leaves `admission-controls` green; it surfaces at the next pin advance, where the row's own tests and the §6.2.2 comparison judge it (`R7-M1`).**
  *(Per Stephen's `2026-11-22` decision, `admission-controls` runs no `HEAD` blob check, gating row check, verdict comparison, or `gh` call; an optional advisory Rule 0.2 row report may compare `HEAD` against `HEAD^1`, write text to `$GITHUB_STEP_SUMMARY`, and always exit `0`, `R6-i4`. Wiring into `ci.yml` (F1) + CODEOWNERS (I1) protects `L1_LIVE`, §6.2.2.)*

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
| `tests/tools/test_w9_detectors.py` — **`W9-T19` (Computational-Log) & D-5** | `unit` (`ci.yml` `admission-controls`) | Clean + prepended LF/CRLF successor entries pass; empty `ACCEPTED_CL_EXPORT` fails; `recheck_cl_export` `void: True` fails; symlink/junction/resolve/in-repo `--vault-root` fails; V1–V6 exit `1`; D-5 7-day cadence passes, missing file fails when `ACCEPTED_CL_EXPORT` non-empty, >7 days fails until `"owner_cadence_reset"` + `"run"`. |
| `tests/tools/test_w9_detectors.py` — **Rule 0 & closure changes** | `unit` (`ci.yml` `admission-controls`) | Atomic disarm/retroactive blessing fail; pre-reg edit passes; `detector-controls.json` delete/backdate fails (`Rule 0.3`); closure edit without `baselines` append exits `0`; row `0`/row `k` (i)–(iv) negatives: missing ref, tree mismatch, non-`P1` `source_commit`, wrong `entry_sha256`, extra `baseline_commit`, omitted path/`new_blob[:8]`, unmentioned no-op, Rule 0.2 (iv) grammar (`V[:8]`/`candidate`, `V` in `(b0, C_k]`), CRLF index blob check; **Rule 0 exemptions (§6.5.1, one guard per control on an otherwise-valid row)** — **positive (paired)**: same history without row exits `1`, with `P1`-pre-existing `R0-EXEMPT` slice + valid row exits `0`, omits tuple from `--verdict-json` (incl. via `--acknowledged-from`), and prints one cleared-tuple line naming row index (`X-i2`), plus one slice carrying two `R0-EXEMPT` lines used cleanly by two rows; **N1 (exact 6-tuple & sibling sub-check)**: parametrised over each field (`commit`, `rule`, `path`, `location`, `old_blob`, `new_blob`), sibling `location`, and sibling sub-check (`baselines[k]` fails `#ii` & `#iii`; row for `#iii` exits `1` on `#ii`, `X-m2 (a)`); **N2 (1 fixture each)**: missing `disposition_ref`, missing `id` at `P1`, wrong `entry_sha256`, missing matching `R0-EXEMPT` line, & slice at `P1` differing from candidate-time hash; **N3 (1 fixture each)**: `source_commit <= commit`, `source_commit >= C_ex`, `source_commit` off first-parent chain, `commit` off first-parent chain (second-parent commit), `commit == b0`, & `P1(C_ex) == b0` (`fp_index[b0] = -1`, `X-m1`); **N4 (1 otherwise-valid row each, proven to clear if re-pointed at an exemptable target)**: `rule0_exemptions`, `format`, `baselines[0].baseline_commit`, `d8_rule_suites_limit_decision_ref` (incl. first transition), & `walk-baseline.json` deletion fixed as delete at `D` + restore at `R` (`head = R`); **N5**: deletion/mutation of existing row paired with self-exemption attempt; **N6 (separated)**: extra/missing key on row, `disposition_ref`, & top-level `walk-baseline.json`; **N7 (constructible replacements for `commit == C_ex`)**: `source_commit == commit`, & violation commit immediately followed by row commit with no register commit between; **N8**: recurrence at `C2 > C_ex`; **missing schema/scope controls**: `rule` in `Rule 1`–`Rule 3`, `(rule, path)` mismatch (`Rule 0.1` + `legacy-write-records.json`), bad `location` (`rule0_exemptions[0]`, `baselines[01]`, `baselines[-1]`, missing `#check`), both blobs `null`, duplicate 6-tuple; **three `X-M1` controls**: (i) `X` adds stray key, `F` removes it & rewrites `baselines[0].baseline_commit`, rows for both `X` and `F` $\to$ exit `1` at `F`, (ii) conflict marker at `X`, fixed at `F`, rows for both (no row for `F`'s unchanged-blob successors) $\to$ exit `0`, (iii) pin dropping superseded reader $\to$ exit `2` when superseded version is at `<head>` (exit `1` `Rule 0.2` if non-`<head>`); & **`X-M2`**: documented mandatory pre-merge `--head <candidate>` run (§6.5.1 item 3). |
| `tests/tools/test_w9_detectors.py` — **Exit `2` & `--assemble-only` procedure** | `unit` (`ci.yml` `admission-controls`, `--pr-map`) | Entry shims for `check_legacy_writes.py`, `check_conventions_legacy_locks.py`, `check_legacy_log_baseline.py`, `run_w9_detector_controls.py`, `run_w9_pinned_detectors.py`, and `export_w9_registration_manifest.py` import inside guarded `main()` and exit `2` on import-time/uncaught errors, `EvidenceParseError`, `UnknownEvidenceFormatError`, and missing required `<head>` files (`--verdict-json` emits `{"format": "w9-verdict/1", "error": "..."}`), while `EvidenceSchemaError` (known-`format` closed-key/field failure) emits `["Rule 0.2", "<path>"]` and exit `1` so every exit `1` carries $\ge 1$ `(rule, path)` pair (`R6-M1`, `R7-m1`); row `0` skips diff; **procedure (`R6-M2`)**: `--assemble-only` 2-row diff (incl. `Rule 0.1`–`0.3`, `candidate \| rule \| path`), one-sided or identical `ERROR` -> `ERROR` (completeness = human `HR-3`); Rules 1–3 green-to-red with `acknowledged` passes post-merge. |
| `tests/tools/test_w9_detectors.py` — **`acknowledged` & Rule 3 late entry** | `unit` (`ci.yml` `admission-controls`) | Exact tuple exempt while sibling fails; backdated/same-commit ref, missing `independent_review`, missing late `shared-surface-changes.json`, or empty `affected_registrations` without `"none derived"` fail; `"none derived"` passes; ack-only `pr_number: null` passes while PR `pr_number: null` fails. |
| `tests/tools/test_w9_detectors.py` — **Rules 1–3, PR map, UTF-8 & CLI locks** | `unit` (`ci.yml` `admission-controls`) | Rule 1 exclusions & manuscript prefix; mode-only fails; H1 Working-Note append passes while task-row edit fails; retry/fallback & API `2`; non-ASCII PR UTF-8 decode; test flags rejected without `--ruleset-check skip`; `--classified-locks` needs `--candidate-file`; none in workflow YAML. |
| `tests/tools/test_w9_detectors.py` — **Closure, stdlib/ASCII, wrapper, CODEOWNERS, `L1_LIVE`, ruleset & pin** | `unit` (`ci.yml` `admission-controls`) | `test_recorded_detector_import_closure_covers_ast_walk` & `test_detector_closure_is_stdlib_only` (21 runtime, **scoped to tree assembled from `HEAD`'s `baselines[-1]` & synthetic repos, `R7-M1`**), `test_pinned_wrapper_is_self_contained_stdlib_only`, **`test_pinned_wrapper_is_ascii_only`** (`R6-m2`), child exit `2` (`R6-i5`), `test_derived_closure_tools_and_accepted_w9_are_codeowned` (`w9_segmentation.py` choice); `main_ruleset`/D-8; `L1_LIVE` (`yaml.BaseLoader`, `False`, synthetic `True` top-level shape checks + `--verify-watched-to-fail` with `HEAD` `baselines[-1]` `--code-root`, plus **three unrowed non-code-owned closure edits keeping `admission-controls` green: bytes edit, new internal import, & third-party import**, `R6-M3`, `R7-M1`); §21.1 item 11 pin cases (post-loop re-hash, `-S -P`, traversal/abs/`casefold`/`~`/dot/space/`isreserved`, off-chain, malformed WB, absent/tree, I3). |
| `tests/tools/test_w9_detectors.py` — **`W9-T7` scratch replay** | `unit` (`ci.yml` `admission-controls`) | `~1.57–2.07s` bare clone; derives 10 `diff-tree` paths (`5df0c001`/`811d5a2b`); T7-1/T7-2 (`GIT_INDEX_FILE`) assert Rule 1/2 exit `1`; checkout-scoped snapshot (`config`/`hooks/` in `CI=true`). *(Recorded departure from `06v:230`, Point F.)* |
| `tests/research_system/integration/test_w9_wp9_5_detectors.py` | `integration`, `@pytest.mark.slow` *(selected by `affected_research_tests.py:120-147`, not `tools/`-only edits; nightly `research-system-suite.yml:8-9,15,17` `-m "not live_store"`)* | 1. **`M-6`:** scratch W9 store + Git repo; exports `w9-registration-manifest/2`; `--check` passes & drift exits `1`.<br>2. **`O-13`:** `run_w9_detector_controls.py` (`CONTROL_GIT_ENV`, UTF-8, `-c`); checks `output_sha256`, `--verify-watched-to-fail` (`--code-root`/`--repo-root`, `python -S -P`), `require_detector_controls`, `LR-003`, immutability. |

### 12.2 Fixture provenance rule (`06v:248-255`)

- No test reads live bytes from `C:\Users\steph\Documents\TDA-Research`, `C:\Users\steph\TDL\vault`, `papers/`, or `results/`.
- Baseline test verifies blob `4620c71607ca3a06c6df3b8e96a6bddffc783960` / SHA-256 `d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589` (`research_system/legacy/reader.py:43-49`).

### 12.3 Measured timings and test-time budget

Measured local timings (§21.1): bare clone (`58,133` objects, `28` packs, `335.09` MiB) + cleanup **`1.57–2.07s`** (R6 `1.99–2.07s`); `segment(raw, "conventions_unit")` on `4620c716` (`33,645` B) / `dbd54fe3` (`51,774` B) **`< 0.15s`**; R6 pin-heredoc **`0.32s`/case** (`32` runs = `10.28s`, so `27` cases ≈ `8.6s`); `python -S -P` = zero install overhead; 6-call `1x` walk stand-ins (§21.1 item 10, no Python rule eval): **`14.05s`** (`60`/6), **`34.46s`** (`178`/12), **`62.84s`** (`320`/22), **up to ~28% spread across three independent runs** (R5 `11.79s`/`34.85s`/`61.58s` + `~11.3s` `gh api`; R6 `12.97s`/`44.03s`/`77.7s` + `26.35s` 2x@60; R5 2x `24.04s` @60; `68.92s`/`125.68s` **extrapolated `2 × 1x`**). Hosted full-walk time (`600s` stop rule §15.2 item 5) is `UNVERIFIED-5`.

| Test file | Measured vs estimated budget (`--no-cov`, serial, **incl. `@pytest.mark.slow`**) | Status |
|---|---|---|
| `tests/tools/test_w9_detectors.py` | Segmentation (`< 0.5s`, estimate, unwritten code) + `27` pin cases (`~8.6s`, scaled from R6 `0.32s`/case) + Git/diff/wrapper controls (`~5–10s`, estimate, unwritten code) + `W9-T7` bare clone (`1.57–2.07s` + `< 0.5s` replay, estimate, unwritten code) + under `L1_LIVE`: `--verify-watched-to-fail` on assembled `baselines[-1]` (`~3–6s`, estimate, unwritten code) + `CI=true` `config`/`hooks/` snapshot (`< 0.5s`, estimate, unwritten code). No full walk / `gh`. | Runs in `ci.yml` `admission-controls` (`F1`). |
| `tests/research_system/integration/test_w9_wp9_5_detectors.py` | Scratch W9 store timing for `M-6` & `O-13` (**`UNVERIFIED-3`**). | Selected by `affected_research_tests.py`; nightly `research-system-suite.yml`. |

**Unconditional pre-code profiling (`P-087` item 7, `03-decisions-and-open-questions.md:5919-5923`):** §15.1 item 4 requires profiling one existing scratch-store test on Stephen's machine first; **Owner Point G recommends `G1` (`300s`)** (separate from §15.2's `600s` `1x` walk stop rule) until that run supports `G2` (`120s`). Over-budget -> `PARTIAL`.

---

## 13. Research assurance

WP9.5 touches the **Output / Provenance** assurance lane (`CONVENTIONS.md:20-34`): legacy artifact immutability detection, shared-surface state invalidation detection, `CONVENTIONS.md` lock preservation, vault Computational-Log legacy entry integrity, and detector negative-control evidence hashes.

### 13.1 Machine-checkable claims and their enforcement artifacts

| # | Claim | Enforcement artifact (test / validator / schema) |
|---|---|---|
| MC-1 | Every `legacy_path_registration` record in the W9 control store matches `.research-system/evidence/w9/registration-manifest.json` (`w9-registration-manifest/2` under A1: `root_kind`, `root_id`, `normalized_path`, `role`, `source_identity_kind`) at `binding.binding["git_head"]` (§5.3). | `tools/export_w9_registration_manifest.py --check`; `test_w9_wp9_5_detectors.py` (`M-6`). |
| MC-2 | Confined `python -S -P` assembly of `21` stdlib runtime + `1` workflow review blob (`isreserved`/`~`/`casefold()`, post-loop `hash-object --no-filters`) runs **`1x`** walks from `baselines[0]["baseline_commit"]` on `baselines[-1]` (§6.2.3, §10.2); shims import inside guarded `main()` to exit `2` on import/unparseable-at-`<head>`/unknown-`format`-at-`<head>`/missing-`<head>` errors (`--verdict-json` `"error"`) vs `1` with $\ge 1$ `(rule, path)` pair (`EvidenceSchemaError` & non-`<head>` parse/unknown-format errors $\to$ `["Rule 0.2", <path>]`); Rule 0 enforces `0.1` + `0.2` (i)–(iv) + `0.3` (plus raw `json.loads` invariant comparisons across malformed intermediates, `X-M1`) with no PR gate and clears exemptable exact 6-tuples (with sub-check `location`, `X-m2 (a)`, printing one line per cleared tuple naming row index, `X-i2`) only via `rule0_exemptions` (`[]` from row `0`, `0 <= fp_index[commit] < fp_index[source_commit] <= fp_index[P1(C_ex)] < fp_index[C_ex]` with `fp_index[b0] = -1`, never unexemptable invariants, §6.5.1); closure/stdlib tests run on assembled `baselines[-1]` (never checkout, `R7-M1`); pin advances attach step 3 `git diff` + `--assemble-only` diffs (§6.1–§6.2, §6.5–§6.6). | `tools/check_legacy_writes.py`, pin step, `test_detector_closure_is_stdlib_only`, `test_recorded_detector_import_closure_covers_ast_walk`, `test_pinned_wrapper_is_self_contained_stdlib_only`, `test_pinned_wrapper_is_ascii_only`, `test_w9_detectors.py`. |
| MC-3 | Guarded commit `C` after `baselines[0]["baseline_commit"]` altering registered `git_tracked` `repository_root` paths without `C` W9 §4.2 record (`P1` slices) or `acknowledged` exits `1` (§6.4–§6.6). | `check_legacy_writes.py` (Rule 1); `test_w9_detectors.py` (`W9-T7`). |
| MC-4 | Commit `C` after `baselines[0]["baseline_commit"]` touching `results/` outside `results/ars/` without §4.2 record / `acknowledged` exits `1` (§6.5 Rule 2). | `check_legacy_writes.py` (Rule 2); `test_w9_detectors.py` (`W9-T7`). |
| MC-5 | Commit `C` modifying `shared_enforcement_surface` without `C` §4.3 record + `shared-surface-changes.json` (or Rule 3 `acknowledged` + `independent_review` + `<head>:shared-surface-changes.json` with non-empty `affected_registrations`/slice `"none derived"`, ack-only `null`) exits `1` (§6.5 Rule 3, `O-32`). | `check_legacy_writes.py` (Rule 3); `test_w9_detectors.py`. |
| MC-6 | `diff-tree -r --no-renames -z <P1> <C>` handles 1- and 2-parent commits on `main`, failing closed on mode-only changes (§6.3). | `check_legacy_writes.py`; `test_w9_detectors.py`. |
| MC-7 | Every legacy `conventions_unit` from `4b143c92` (`4620c716`, 68 units or L-0b `ACCEPTED_CONVENTIONS_CLASSIFICATION` `(anchor_text, unit_hash)`) is preserved byte-for-byte in order without inserted tables (§7.3–§7.4). | `check_conventions_legacy_locks.py`; `test_w9_detectors.py` (`W9-T19`, N1–N7). |
| MC-8 | Every `"item"`/`"structural"` row in `ACCEPTED_CL_EXPORT[-1]` (`void == False`) stays byte-identical in `04-Methods/Computational-Log.md` with 0 blockers while LF/CRLF prepended successor entries pass (§8.2–§8.3). | `check_legacy_log_baseline.py`; `test_w9_detectors.py` (`W9-T19`, V1–V6). |
| MC-9 | Controls emit deterministic `output_sha256` (`CONTROL_GIT_ENV`, `-c core.autocrlf=false -c commit.gpgsign=false`) bound to `git_blob_id` & `closure_blobs`, passing `require_detector_controls` & `--verify-watched-to-fail` (required `--code-root`—no default; assembled from `HEAD`'s `baselines[-1]` via `§10.2` in `admission-controls`—plus `--repo-root`, §9.2, §10.3). | `run_w9_detector_controls.py`, `evidence.py:133-154`; `test_w9_wp9_5_detectors.py`. |
| MC-10 | Pre-L-1 (`L1_LIVE is False`): `on == {"workflow_dispatch"}` only, zero L-1 evidence; when `True`: `on["push"]` on `main` and `admission-controls` runs `L1_LIVE`, F1 (top-level JSON shape only), `--verify-watched-to-fail` on assembled `baselines[-1]`, optional K1, & optional 1-sentence advisory Rule 0.2 report—zero PR gate or `gh` call (§10.3). | `test_w9_detectors.py` (`yaml.BaseLoader`), `ci.yml` (`F1`), CODEOWNERS (`I1`). |

### 13.2 Human-review-only claims and residual architectural limits

| # | Claim / Limit | Reviewer / Owner check and why not mechanized |
|---|---|---|
| HR-1 | **Semantic equivalence & authorship of register/review slices:** | Detector checks `P1` ancestry & slices (`03-decisions-and-open-questions.md`, `reviews/`, §6.2.2, §6.4). Because those paths are un-owned, **`P1` proves age, not authorship**; authorship/semantics rely on review + I1 CODEOWNERS (`W9:174-176`). |
| HR-2 | `affected_registrations` completeness (`shared-surface-changes.json`, `B -> A` reverts, §6.5). | Deriving `affected_registrations` requires Stephen + reviewer (`W9:185-188`). |
| HR-3 | **Human-review trust root, deliberate pin lag, Rule 0.2 limits, permanence, & bypass cost (§6.1–§6.2, §6.5–§6.5.1, §16.1–§16.2):** | Ruleset `20822054` has `required_approving_review_count: 0`, so control rests on human review + CODEOWNERS (**only under Option I1**, which owns tools/closure/`walk-baseline.json`; `Option I2` makes a pin advance an ordinary PR) (+ I3). Under Stephen's `2026-11-22` decision: (a) a lagging pin exits `2` on unparseable/unknown-`format`/missing-`<head>` JSON, **or `0` silently** on unread new files, rules, and constants (`§6.1`, while a new key under a known `format` is an evidence-validation failure under `§6.6` and every known evidence file present at `<head>` is parsed every run; L-0b pairs with a pin advance); (b) `admission-controls` runs the tool's unit tests and `--verify-watched-to-fail` and Rule 0 judges the appended row—what is missing is a machine old-versus-new comparison (Stephen reviews the PR + step 3 `git diff <old_blob> <new_blob>` + slices, `R7-m9`); (c) a pin advance takes in the whole current tree, including earlier unreviewed edits to non-code-owned modules that the PR's own diff does not show (Rule 0.2 (ii); no pure rollback without code revert, and fails on out-of-order concurrent closure merges); (d) **After L-1 an evidence format moves by a new file path, never in place without a cleared Rule 0 fault** (`P-090` item 5 `813088e9` narrows item 2 C so `walk-baseline.json` moves only by a new file path, which is a re-baseline to be designed when needed; an in-place move on any other evidence file keeps the superseded reader in the pin for as long as the walk covers superseded versions, `X-M1`, plus a post-merge §6.5.1 row, leaving an intentional red window between merge and `C_ex`; Options A1 and D3 are unaffected because they land before code, `R7-d1`). Post-merge exemptable Rule 0 failures clear solely via `P-090` item 2 C's §6.5.1 `rule0_exemptions` row; an exemption row that makes `walk-baseline.json` unparseable at `<head>`, or that is a schema-valid but invalid row (by bypass or race), cannot be cleared by a later row and is recoverable only by re-baselining at a new path (not designed here, `X-M2`, `P-090` item 5), while §6.5.1 unexemptable invariants stay permanently unexemptable (§16.2). For a deleted-then-restored evidence file (`new_blob: null` + `old_blob: null`), nothing mechanically binds the restored bytes to the deleted file's `old_blob`, so Stephen's I1 review prevents content laundering (`X-m5`); exempting a `Rule 0.1` deletion of a `registration-manifest.json` entry leaves that path unguarded by Rules 1 and 3 on later commits (which union `Manifest(P1)` and `Manifest(C)`), leaving `export_w9_registration_manifest.py --check` (`MC-1`) as the second tripwire (`X-i4`). I1 bypasses need `Bypass reason:` (`tools/check_bypass_merges.py:41,135`, `admin-bypass-guard.sh:13-18`). |
| HR-4 | **Weekly vault attestations (§8.4):** `vault-detector-runs.json`. | CI cannot access `C:\Users\steph\Documents\TDA-Research` to run `check_legacy_log_baseline.py`. |
| HR-5 | **30-day `rule-suites` window & D-8 (`§4.1–§4.2`):** `MAX_DAYS = 30`. | Fails closed past 30d without `ruleset_gap_acknowledgements`; under D-8, direct checks run locally (`06v:571,603`). |
| HR-6 | **`CONVENTIONS.md` structural lines (§7.4):** `### `, `---`, blanks, H1, footer. | Editing legacy `### ` titles or moving bullets across `### ` inside the same `## ` relies on review (`wp9-5-note-r2-review-2026-11-21.md:123`). |
| HR-7 | **`export_w9_registration_manifest.py` (M-6) runs unpinned (§2.1, §6.2.3):** | Imports `research_system/cli.py` (~161 modules), excluded from `$DETECTOR_DIR`; CODEOWNED under I1. |

---

## 14. Claims for review

An independent reviewer should attack these 16 claims against `dbd54fe382e7b2849d3f2038393cbdb4d709477b`:

1. **No D-4 trigger (`P-089` #1):** Zero W9 commands, runtime bindings (`275` rows, `82eab93a...451d58`), append sites, or schemas changed; `w9_segmentation.py` (`43e1454de09b61e274954c42b21d6ae533857a24`) & `IMPORTER_MODULES` (`reader.py:42`) untouched (§2.2; `03-decisions-and-open-questions.md:6022-6025,6085-6099`).
2. **Pin, no lockstep, & `1x` walk (`2026-11-22`):** I1 CODEOWNERS (+ optional I3 `W9_DETECTOR_PIN`), **no PR pin-advance gate** in `admission-controls` (advances attach `--assemble-only` diffs + `git diff <old_blob> <new_blob>`), `1x` walk via `baselines[-1]` (`21` runtime + workflow review blob) under confined `python -S -P` + post-loop `hash-object --no-filters`, `main()` exit `2` on unparseable/unknown-`format`/uncaught errors vs `1` on Rules 0–3, Rule 0 (`0.1` + `0.2` (i)–(iv) grammar-only + `0.3`), and hash-bound Rule 0 exemptions (§6.5.1) (§6.1–§6.2, §6.5–§6.5.1, §10.2, §13.2, §16.1–§16.2).
3. **Manifest `/2` & WP9.4 counts:** Option A1 updates `REGISTRATION_MANIFEST_FORMAT` (`"w9-registration-manifest/2"`, `cli.py:1648-1659`, `evidence.py:40,114-131`) + 4 test builders (WP9.3 amendment + review; WP9.4 code untouched; Stephen decides `wp9-4-1-record.md:114,130` re-record, §2.3, §5.3, §16.3).
4. **Rule 1 scope:** Filtering to `repository_root` + `git_tracked` minus `conventions_lock`, `shared_enforcement_surface`, `successor_results_root`, & `legacy_read_only_projection` avoids untracked/`results/ars/`/`CONVENTIONS.md` misfires (§6.5–§6.6).
5. **`.apm/tracker.md`:** H1 validates `tracker_task_row` & `working_note_entry` (`segmentation.py:470-473`) byte equality + `[ \t]*\n` gaps (`#368`, `#388`, `#433`, §6.5, §16.9).
6. **§4.2 keying & `P1`:** `(pr_number, normalized_path, old_blob, new_blob)` + `P1` slices binds without squash SHAs, conditional on I1 (`HR-1`, §6.4, §16.1, §16.4).
7. **2-parent diffs & modes:** `diff-tree -r --no-renames -z <P1> <C>` covers merges (`b132406e`) and fails closed on mode-only changes (§6.3).
8. **PR mapping & `W9-T7`:** `merge_commit_sha == C` (3 retries + fallback, UTF-8, API exit `2`, `--ruleset-check skip` lockouts) + `W9-T7` unit replay (`5df0c001` 11/7, `811d5a2b` 9/3, `06v:230` departure, §6.2.1, §6.3, §11.2, §16.7).
9. **D3 `O-32` & Rule 3 `acknowledged`:** `"w9-shared-surface-changes/2"` without commit SHA satisfies `require_change_list`/`acceptance.py:121-136` via `evidence.blob_at` (`evidence.py:179-218`); late entries need `independent_review`, non-empty `affected_registrations`/slice `"none derived"`, ack-only `null` (§6.5, `HR-2`, §16.5).
10. **Ruleset `20822054`, gap ack, & U-3:** Pinning 16 fields (`integration_id: 15368`) fails closed >30d without `ruleset_gap_acknowledgements`; U-3 tests `GITHUB_TOKEN` on 3 endpoints (§4.1–§4.2).
11. **Vault junctions:** Because `open_registered_root_anchor` (`anchor.py:1934-1950`) has `reject_reparse=False` and `LegacyReader.__init__` (`reader.py:241-248`) is lexical, `check_legacy_log_baseline.py` & `u4_dry_run.py` block symlinks/junctions/in-repo paths (§4.3.1–§4.3.3).
12. **`CONVENTIONS.md` & L-0b:** Parity (`4620c716` 70 -> `dbd54fe3` 90, 0 blockers), first-byte `|` filter, `HR-6`, L-0b `ACCEPTED_CONVENTIONS_CLASSIFICATION` (`(anchor_text, unit_hash)`, N7) (§7.3–§7.6, §16.10).
13. **Vault & CRLF:** Reads `ACCEPTED_CL_EXPORT[-1]["classified_list"]` (`1..N`), refuses `void == True`/live `blocker`, keeps `raw_row_sha256` across CRLF prepends (§8.2–§8.3, §16.10).
14. **D-5 cadence:** Strict `bool(reader.accepted_cl_export)` at `LR-003`/`LR-015`/`LR-016`/`LR-020` + `"owner_cadence_reset"` (§8.4, §16.6).
15. **Controls & dual roots:** Binding `git_blob_id`, `closure_blobs`, `CONTROL_GIT_ENV`, `-c` flags with required `--code-root` (no default; `baselines[-1]` tree in `admission-controls`) & `--repo-root` across `run_w9_detector_controls.py --verify-watched-to-fail` & `run_w9_pinned_detectors.py` (§9.2, §10.2–§10.3, §12.1).
16. **Wiring, CODEOWNERS, wrapper, & K1:** `test_w9_detectors.py` (`yaml.BaseLoader`), `test_recorded_detector_import_closure_covers_ast_walk` & `test_detector_closure_is_stdlib_only` (scoped to assembled `baselines[-1]`, never checkout, `R7-M1`), `test_derived_closure_tools_and_accepted_w9_are_codeowned`, `test_pinned_wrapper_is_self_contained_stdlib_only`, `test_pinned_wrapper_is_ascii_only`, `L1_LIVE` top-level shape checks (unrowed byte, internal-import, and third-party-import closure edits stay green), I1 (`w9_segmentation.py` & `"3.13"` choices), K1 (no PR gate/`gh` call) (§2.3, §10.3, §16.1, §16.7, §16.11).

---

## 15. Stop rules for the code package

### 15.1 Hard preconditions before WP9.5 code is dispatched (`P-089` #3, `03-decisions-and-open-questions.md:6104-6115`)

WP9.5 code **must not** be dispatched until items 1 to 4 below are complete (and item 5's unverified hosted wall time is acknowledged):

1. **U-3 recorded in §4.2.2 (`06v:159`):** Stephen authorizes the throwaway draft-PR probe (§4.2.2); reviewing session records HTTP statuses, `X-Accepted-GitHub-Permissions`, and JSON keys for all 3 endpoints (`rulesets/20822054`, `rulesets/rule-suites`, `commits/dbd54fe3.../pulls`) and D-8 outcome.
2. **U-4 dry run recorded in §4.3.3 (`06v:160`):** Run `u4_dry_run.py` (§4.3.3 #2, `833,453` B, `73fcbe83...`) against `C:\Users\steph\Documents\TDA-Research\04-Methods\Computational-Log.md` with `PYTHONPATH=.` and record `root_checks`, `bytes`, `sha256`, `link_count`, `canonical_target`, `file_facts`, `row_counts`, `blockers`.
3. **Owner Points I, C, A, B, D, E, F, G, H, J, K decided (`P-090`):** All 11 owner points (§16.1–§16.11) and follow-up clarifications are decided in `P-090` (`0e1269bd`, item 5 `813088e9`: **pin, no lockstep**; **I1** with `I1-include-seg`/`I1-py-minor` and no **I3**, so `UNVERIFIED-4` is moot; **C1** + `C-R0-exemption` + `2026-11-24` pre-merge/`walk-baseline.json`/`d8` rules; **A1** with WP9.4 counts re-recorded; **B1**, **D3**, **E1**, **F1**, **G1**, **H1**, **J1**, **K1**), subject to the `P-090` item 3 amendments before code relies on them.
4. **Unconditional pre-code single scratch-store profile (`P-087` #7, `03-decisions-and-open-questions.md:5919-5923`):** Profile one existing WP9.3/WP9.4 scratch-store test alone on Stephen's machine (`UNVERIFIED-3`, §21.2) before adding `test_w9_wp9_5_detectors.py`.
5. **Hosted `windows-latest` `1x` full-walk wall time (`UNVERIFIED-5`, §21.2):** Post-merge `1x` time with real rules and `gh api` (~60/`178`/`320` commits) remains `UNVERIFIED-5` before rehearsal/activation, bounded by the `600s` walk stop rule.

**Results recorded 2026-11-23 by the reviewing session, on Stephen's authorization:**
- **Item 1, U-3** (draft PR #450 on branch `probe/w9-u3-token-read`, commit `52488192`, run `45282369275`; the PR was closed unmerged, its branch deleted, and the other triggered runs cancelled):
  - `GET rulesets/20822054` under `contents: read`: HTTP 200, `X-Accepted-GitHub-Permissions: metadata=read`. The keys returned were `id`, `name`, `enforcement`, `conditions` and `rules`, with parameters on `merge_queue`, `pull_request` and `required_status_checks`. **`bypass_actors` is absent.** So CI cannot check the bypass list: the `bypass_actors` pin is checked only by the owner-`gh` read (§4.1). The probe printed top-level keys only, so whether CI can read every nested field the ruleset check pins (`conditions.ref_name.include`, the `required_status_checks` contexts and `integration_id`) is unverified; §15.3 carries that check to the code task (CodeRabbit on #449, `4673032974`). The code task must make the CI check tolerate that key's absence explicitly, not treat it as a pass.
  - `GET rulesets/rule-suites?ref=refs/heads/main&time_period=day&per_page=5` under `contents: read`: **HTTP 403**, `X-Accepted-GitHub-Permissions: administration=read`. **D-8 applies to rule-suites** (§4.2.3).
  - `GET commits/dbd54fe3.../pulls`: HTTP 200 under both `contents: read` and `contents: read, pull-requests: read`, accepted permission `pull_requests=read`. It returned one PR, with `number`, `merged_at` and `merge_commit_sha`.
- **Item 2, U-4** (run at 2026-11-23T22:41:48Z from this worktree with the §4.3.3 script verbatim):
  - all four `root_checks` true;
  - `bytes` 835,645, `sha256` `27f756492035bdffc030742e9befc07c6c7fbe8d83d8c65313d592560df7180f`;
  - `link_count` 1, `canonical_target` `C:/Users/steph/Documents/TDA-Research/04-Methods/Computational-Log.md`;
  - `file_facts`: LF, ends with a terminator, no BOM, 6,993 lines;
  - `row_counts`: 324 `item`, 1 `structural`; `blockers` empty;
  - both segmenters agree.

  The file has grown since the 2026-11-21 metadata read (833,453 bytes) because successor entries are added at the top.
- **Item 4, scratch-store profile:** `test_w9_wp9_3_2_runtime.py::test_an_accepted_batch_through_submit_closes_its_whole_file_registration`, run alone, serially, `--no-cov`, on Stephen's machine. It passed in 39.65 s: 21.75 s setup (the scratch store) and 12.25 s call. So each scratch-store flow costs about 34 s. G1's 300 s leaves room for about eight; G2's 120 s would hold about three.
- Item 3 is P-090. Item 5 stays `UNVERIFIED-5`.

*(Pre-L-1 gate: before L-1 on `main`, run one throwaway `on: pull_request` workflow [closed unmerged] reading synthetic evidence from `$GITHUB_SHA`, then after L-1 merge run green `workflow_dispatch` on the L-1 merge commit, §10.2 #5.)*

### 15.2 Stop rules during WP9.5 code implementation

The WP9.5 code worker must stop and return `PARTIAL` if:
1. Any edit alters a §2.2 protected identity (275-row binding census, `wp6_1_06h_current_append_manifest.yaml` `1066404a`, `test_wp6_1_06h_append_path_closure.py` `3b1eec6e`, `schema_registry.py` `e32cb408`, `authority.py` `9b56b322`, core/W9 schemas, T2 seal, `w9_segmentation.py` `43e1454de09b61e274954c42b21d6ae533857a24`, or `IMPORTER_MODULES` `reader.py:42`) (`06v:614,618-619`).
2. Any change in `research_system/legacy/` exceeds Stephen's approved Owner Points A, D, E, J.
3. Any test reads live vault/restricted bytes or mutates `REPO_ROOT`, any worktree, or `C:\Users\steph\Documents\TDA-Research` (`06v:616-617`).
4. New/changed WP9.5 tests (incl. `@pytest.mark.slow`) exceed Owner Point G's serial `--no-cov` budget (`P-087` #7 `03-decisions-and-open-questions.md:5919-5923`, excl. full walks).
5. *(WP9.5-specific stop rule added by this design note, not in `06v` §8):* **Pre-code / rehearsal `1x` walk stop rule (distinct from Owner Point G):** A `1x` full walk with real rules & PR mapping exceeds **`600s`** in rehearsal/smoke -> stop for a **design amendment** (e.g. baseline-epoch advancement or Git/PR batching), never an unapproved runtime flag.
6. *(WP9.5-specific stop rule added by this design note, not in `06v` §8):* Any negative control misfires, any positive control fires, `test_recorded_detector_import_closure_covers_ast_walk` finds an unpinned import in the assembled `baselines[-1]` tree / synthetic repos, or `test_detector_closure_is_stdlib_only` (similarly scoped), `test_pinned_wrapper_is_self_contained_stdlib_only`, or `test_pinned_wrapper_is_ascii_only` fails (`R7-M1`).

### 15.3 Carried to the WP9.5 code task from the r7 review

Named implementation and test obligations from `wp9-5-note-r7-review-2026-11-23.md` for the WP9.5 code brief (not redesigned in this note):

- **`R7-m3` (Comparison placeholders, shell & pretty JSON):** Define `<pr_base>` (`candidate^1` for merge ref; PR must be up to date with `main` for `commit-tree`), `<PR_tree>`, and `<b0>`; pass `--repo-root .` and fetch `origin/main` in step 2; state Git Bash for the procedure (`cmd /c` for the wrapper command only); format `--verdict-json` diffs with `indent=2, sort_keys=True`.
- **`R7-m4` (`--assemble-only` wrapper semantics):** State `--assemble-only` skips `origin/main` freshness and I3 checks, requires `--out` to not exist or be empty (else exit `2`, never overwriting files), and specifies Python `3.13`+ minimum (older interpreter exits `2` with a named message).
- **`R7-m6` (Comparison test observability & test-only helper):** Restate row 1316's checks in observable terms (`--assemble-only --rev <pre-L-1 rev>` exits `2` with a named `"no walk-baseline"` message for row 0; `--verdict-json` prints `error` on each failing side), and state the diff helper lives only in the test file, ships nowhere, and is called by no workflow.
- **`R7-m7` (Single pin-assembly source across CI/wrapper & copy tests):** Specify how `admission-controls` invokes the assembly (extracting the workflow YAML heredoc or calling the checkout wrapper with `--assemble-only --rev HEAD`), test byte-for-byte equality across copies, and run the 27 item-11 pin cases against the wrapper's assembly too.
- **`R7-m8` (Rule 0.2 (iv) verdict-line recognizer):** Define the line pattern (`a line that begins with candidate | or eight lowercase hex digits then | ; other lines are not checked`) and `<rule>` set (`Rule 0.1` to `Rule 0.3`, `Rule 1` to `Rule 3`), and reflect both in row 1315.
- **`R7-i1` (Step 5 on incompatible format advance):** Note that when the old side exits `2` (`ERROR`) on a format move in step 5, step 5 reports `ERROR` and Stephen reads the new tool's verdict list alone.
- **`R7-i2` (Prevent `PYTHONPATH` stdlib shadowing):** Add `"first segment must be tools, research_system or .github"` to the pin-step key refusals (blocking keys like `json.py` or `sitecustomize.py`).
- **`R7-i3` (Empirical timing reconciliation):** Reflect `~34%` spread across four stand-in runs and `18.7s` (`0.69s`/case end-to-end on the 27-case harness) within the `< 40s` unit-lane total under G1 `300s`.
- **`R7-i4` (Live ruleset window re-check):** Recorded `50` entries (`26` bypass, `24` pass, `5d325c5b`..`4ca375a3`, `#446`/`#448`) in R7's sliding window check; no code change.
- **`R7-i5` (PowerShell `$OutputEncoding` detail):** Clean child `powershell.exe` 5.1 non-ASCII loss vs UTF-8 host session is mooted by `test_pinned_wrapper_is_ascii_only`; no code change.
- **`R7-i6` (Pin-step malformed JSON suite):** Include `{not json`, `[]`, `null`, `{"baselines": []}`, non-string `baseline_commit`, non-mapping `detector_closure_blobs`, and empty `detector_closure_blobs` handling in pin-step tests.
- **CodeRabbit on #449, the pin step's case-collision control** (§21.1 item 11, comment `4673033037`). The recorded 27-case run stands as run, but the code task's pin-step tests must make the control prove its own guard:
  - assert the guard's own message, `ERROR: casefold path collision`, not the generic `ERROR:` prefix;
  - add an identical-blob collision case, which exits 0 if the guard is removed, so it isolates the guard from the post-write hash check;
  - add the in-memory guard-removal control: delete the casefold guard in memory, run the case, and confirm the expected refusal no longer occurs.
- **CodeRabbit on #449, nested ruleset fields under the CI token** (§4.2.2, comment `4673032974`). The U-3 probe printed only top-level ruleset keys, and the rule types that carry `parameters`. It found `bypass_actors` absent (§15.1). It did not print `conditions.ref_name.include`, the `required_status_checks` contexts or their `integration_id`, so whether those nested fields reach the CI token is unverified. The CI ruleset check must read and compare each nested field §4.1 pins, report a field it cannot read as unreadable under the token, never as a pass, and test both cases. D-8 is unaffected: it rests on the rule-suites 403.
- **`R7-i7` (Advisory row report & line wrapping):** Name the tool, flag, and trigger if keeping the optional advisory Rule 0.2 row report (or omit it), and keep lines compact.
- **`X-m2 (b, c)` (Exact `location` edge cases & L-0b path):** Define `location` for top-level non-schema faults (`d8_rule_suites_limit_decision_ref`, `rule0_exemptions` mutation), row-internal schema faults, deleted/mutated list-item indices (`P1` index `k`), and unchanged-blob `old_blob == new_blob` scoping; close the L-0b `ACCEPTED_CONVENTIONS_CLASSIFICATION` allowed path once L-0b sets it.
- **`X-i5` (`--acknowledged-from` CLI documentation):** Update §6.3 item 4's flag text in code so `--acknowledged-from <sha>` documents loading both `acknowledged` and `rule0_exemptions`.
- **`X-i7` (`### P-0xx` slice boundary & commit read alignment):** Define one shared slice-extraction rule (start `^### <id>\b`, end next `^### `/`^## `/EOF) and reconcile §4.2.3 (`source_commit`) vs §6.2.2/§6.4/§6.5.1 (`P1`) in `tools/_w9_detector_evidence.py`.

**Carried from the exemption-addendum re-review** (`reviews/wp9-5-note-exemption-addendum-re-review-2026-11-24.md`,
CONFIRM WITH FINDINGS, on PR #451), by Stephen's choice of 2026-11-24. Each is for the code brief, in the re-review's
own wording. None is redesigned here.
- **XR-m1:** the scoping itself is now done in §6.5.1 item 4 (CodeRabbit `4677581885`). Still for the code brief: say
  whether the raw-read rule also applies to Rules 0.1 and 0.3.
- **XR-m2:** qualify the nine remaining "exit 2 on unparseable or unknown-format evidence" statements, including the
  §12.1 test row, with "at `<head>`", and classify anything earlier as a `Rule 0.2` fault.
- **XR-m3:** add a control for the two-point slice hash (`source_commit` and `P1`). Apply one rule across the whole
  `disposition_ref` family: `baselines` rows, `ruleset_gap_acknowledgements`, §6.4 and the D-8 reference. Update the
  `X-i7` item above to match.
- **XR-m4:** rebuild the ordering and exact-tuple controls so each isolates its own guard, on fixtures that pass every
  earlier check.
- **XR-m5:** give a fault inside an exemption row one classification, the item 3 validity fault, so no implementer
  reads it as a `"$"` schema fault that a later row could clear. Stephen ruled out later-row recovery (P-090 item 5).
- **XR-i1 to XR-i5:**
  - XR-i1: the pre-merge run's exact trigger, the assembled tree for L-1, and what "no new fault" means;
  - XR-i2: the stale §20.3 claims;
  - XR-i3: the D-8 example value;
  - XR-i4: control gaps, including a pin advance carrying exemption rows for an earlier violation;
  - XR-i5: the X-m2 (b) dependency of control (ii).

---

## 16. Owner points

Stephen has decided **pin, no lockstep** (`2026-11-22`), all eleven owner points (`2026-11-23`: **I1** with `I1-include-seg`/`I1-py-minor` and no `I3`; **C1** + `C-R0-exemption`; **A1** with WP9.4 counts re-recorded; **B1**; **D3**; **E1**; **F1**; **G1**; **H1**; **J1**; **K1**), and the `2026-11-24` clarifications in `P-090` (`0e1269bd`, item 5 `813088e9`). Subsections §16.1–§16.11 retain the evaluated options as provenance.

### 16.1 Owner Point I *(decide first)* — Trust root protecting detector surface, closure, tripwire, and evidence directory

*Pointers:* §2.3, §6.1, §6.2.3, §10.2, §10.3.

- **Pin design — decided by Stephen, `2026-11-22` *(for `P-090` with the other owner points)*:** Keep content pin of `21` stdlib runtime + `1` workflow review blob (`22` in `baselines[-1]["detector_closure_blobs"]`) under `python -S -P` + confinement + post-loop `git hash-object --no-filters` + `main()` exit `2` (`ERROR` on import/unparseable/unknown-`format`/missing-`<head>` errors, vs `1` with $\ge 1$ `(rule, path)` pair incl. `EvidenceSchemaError` -> `Rule 0.2`); **drop lockstep** (`baselines[-1]` stays active across unpinned closure edits, and `test_recorded_detector_import_closure_covers_ast_walk` / `test_detector_closure_is_stdlib_only` check only the assembled tree/synthetic repos, `R7-M1`); **remove PR pin-advance gates from `admission-controls`**; attach step 3 `git diff <old_blob> <new_blob>` + `--assemble-only` `(baselines[0]["baseline_commit"], candidate]` diffs to pin-advance PRs; walk `1x` post-merge. **Gives up (§6.1–§6.2, §6.5, §13.2):** (a) lagging pin exits `2` on unparseable/unknown-`format`/missing-`<head>` files, **or `0` silently** on unread new files, rules, and constants (while new keys under a known `format` fail closed under `§6.6`, every known evidence file present at `<head>` is parsed every run, and L-0b pairs with a pin advance); (b) `admission-controls` runs the tool's unit tests and `--verify-watched-to-fail` and Rule 0 judges the appended row—what is missing is a machine old-versus-new comparison (judged by Stephen's PR review + step 3 `git diff` + slices, `R7-m9`); (c) a pin advance takes in the whole current tree, including earlier unreviewed edits to non-code-owned modules that the PR's own diff does not show (Rule 0.2 (ii); no pure rollback without code revert, & fails on out-of-order concurrent closure merges); (d) `"code-owned, so Stephen merges it himself"` for `walk-baseline.json` holds only under I1 (under I2, a pin advance is an ordinary PR).
- **Options:**
  - **Option I1 (Rule 0 + `.github/CODEOWNERS` — Recommended):** Enforces Rule 0 (§6.5) & §6.2.3 `python -S -P` (`21` runtime + workflow review blob; M-6 omitted -> `HR-7`), adding `@stephendor` CODEOWNERS for `/.github/workflows/legacy-write-detector.yml`, `/tools/check_legacy_writes.py`, `/tools/check_conventions_legacy_locks.py`, `/tools/check_legacy_log_baseline.py`, `/tools/run_w9_detector_controls.py`, `/tools/run_w9_pinned_detectors.py`, `/tools/export_w9_registration_manifest.py`, `/tools/_w9_detector_evidence.py`, `/tests/tools/test_w9_detectors.py`, `/research_system/legacy/accepted_w9.py` (+ `/tools/w9_segmentation.py` under `I1-include-seg`) and `/.research-system/evidence/w9/`, enforced by `test_derived_closure_tools_and_accepted_w9_are_codeowned`, `test_detector_closure_is_stdlib_only`, `test_pinned_wrapper_is_self_contained_stdlib_only`, & `test_pinned_wrapper_is_ascii_only` (§12.1). *Cost:* Stephen's `Bypass reason:` merge (`tools/check_bypass_merges.py:41,135`, `admin-bypass-guard.sh:13-18`) on batch/weekly/ruleset/baseline/code-owned PRs (`7` W9/4wk; `14`/`178` commits/90d touched 15 existing modules; pin advances re-record `detector-controls.json` + diffs).
    - **`tools/w9_segmentation.py` (`R5-m5`):** **`Option I1-include-seg` (Recommended):** include `/tools/w9_segmentation.py` (11 files + dir, 13 non-owned, 0 exemption; `43e1454de09b61e274954c42b21d6ae533857a24` untouched). **`I1-exempt-seg`:** 10 files (14 non-owned) + exemption.
    - **`python-version` (`R5-i2`):** **`Option I1-py-minor` (Recommended):** `"3.13"` vs **`I1-py-patch`:** `"3.13.5"`.
  - **Option I2 (Rule 0 only; keep 8 CODEOWNERS paths):** Leaves `walk-baseline.json`, `L1_LIVE`, workflow, tools, `accepted_w9.py`, & evidence un-owned, making a pin advance an ordinary PR (`R7-m9`); fails B1 and R1-B1 scenarios 4–5.
  - **Option I3 (Optional out-of-tree anchor, with I1):** Repo Actions variable `W9_DETECTOR_PIN` (`{"walk_baseline_commit", "closure_blobs_sha256"}`), `REQUIRE_I3_PIN: "true"` (§10.2), `gh api` in wrapper (§6.2.3). Variable write permissions are **`UNVERIFIED-4`** (§21.2).
- **Recommendation:** **I1** + **I1-include-seg** + **I1-py-minor** (+ optional **I3** pending `UNVERIFIED-4`).
- **Records:** `.github/CODEOWNERS:1-24`, split `tests/tools/test_ci_platform_policy.py` (`W9_DETECTOR_CODEOWNED_FILES`, `W9_DETECTOR_CODEOWNED_DIRS`, `:364-374` without `.is_dir()`, landing 9 new files together), **amend `CONVENTIONS.md:713-729`** (`## ARS Foundation Governance`, `614-783`), & `P-090`.

### 16.2 Owner Point C — `walk-baseline.json`, pre-baseline dispositions, `1x` walk, and post-merge Rule 0 recovery

*Pointers:* §6.2.1, §6.2.2, §6.5, §6.5.1, §10.3. **Fixed (`2026-11-22`):** `1x` post-merge walk from `baselines[0]["baseline_commit"]` on `baselines[-1]`; pin advances attach manual diffs; no `admission-controls` pin-advance gate or `gh` call.

- **Option C1 (Recommended — chosen in `P-090` item 2 C, `0e1269bd`):** Commit `.research-system/evidence/w9/walk-baseline.json` (`w9-walk-baseline/1`) at `baselines[0]["baseline_commit"]` (disposing `(4b143c92, baseline_commit]` via `P1` `pre_baseline_dispositions_ref`), 22-blob `detector_closure_blobs`, `acknowledged`, `ruleset_gap_acknowledgements`, and `rule0_exemptions` (`[]` from row `0`, §6.5.1). Subject to `600s` `1x` stop rule (§15.2 item 5, `UNVERIFIED-5`).
- **Option C2:** Set `baselines[0]["baseline_commit"]` to `4b143c9225035cc29e37351445f1c3a4ab09ceb1` with all 22 historic rows (§6.2.1).
- **Post-merge Rule 0 recovery sub-choice *(`R5-i1`, `R6-m7(c)`, `R7-d1`)*:** For rare post-merge Rule 0 failures (e.g. out-of-order concurrent closure merges hitting Rule 0.2 (ii), slice typos, or an in-place evidence-format change): **`Option C-R0-exemption`** (**designed in §6.5.1; selected by Stephen in `P-090` item 2 C (`0e1269bd`) & clarified in `P-090` item 5 (`813088e9`)**: hash-bound 6-tuple `(commit, rule, path, location, old_blob, new_blob)` + `P1` `R0-EXEMPT` slice, mandatory pre-merge `--head <candidate>` run on PRs modifying `walk-baseline.json`, no recovery row for invalid rows, and strict unexemptable invariants incl. `d8_rule_suites_limit_decision_ref`'s first transition) vs **`Option C-R0-permanent`** (stays red across re-walks; `HR-3`). **After L-1 an evidence format moves by a new file path, never in place without a cleared Rule 0 fault** (`P-090` item 5 narrows item 2 C so `walk-baseline.json` moves only by a new file path, which is a re-baseline to be designed when needed; in-place moves on other files keep superseded readers while walked versions remain and leave a red window between merge and `C_ex`; Options A1 and D3 are unaffected because they land before WP9.5 code, `R7-d1`).
- **Recommendation / Decision:** **Option C1** + **C-R0-exemption** (§6.5.1), decided by Stephen under I1 in `P-090` (`0e1269bd`, item 5 `813088e9`).
- **Records:** Dated `06v-addendum-2026-11-10-w9-paths.md` row & `P-090` (`0e1269bd`, item 5 `813088e9`; `P-09x` L-1 refresh); `research_system/legacy/` untouched.

### 16.3 Owner Point A — Registration manifest (`role`, `source_identity_kind`), `/2` format, & WP9.4 counts

*Pointers:* §2.3, §5.3.
- **Option A1 (`/2`, 5 keys — Recommended):** Bump `REGISTRATION_MANIFEST_FORMAT` (`"w9-registration-manifest/2"`: `{"root_kind", "root_id", "normalized_path", "role", "source_identity_kind"}`), update `require_registered` (`evidence.py:40,114-131`) & test builders (`test_w9_evidence.py`, `w9_runtime_harness.py:451-466`, `test_w9_wp9_4_1_runtime.py:95-109`, `test_w9_wp9_4_2_runtime.py:86-100`). **Stephen decides whether `wp9-4-1-record.md:114,130` (`13 passed in 688.11s (0:11:28)`) is re-recorded.**
- **Option A2:** Keep `/1` + unvalidated companion file.
- **Records:** Edits `evidence.py:40,114-131` + 4 test files; needs **WP9.3 amendment, independent review, & `P-090`** (`IMPORTER_MODULES` untouched).

### 16.4 Owner Point B — W9 §4.2 record, `at C` eval, & `P1` provenance

*Pointers:* §6.4, `HR-1`.
- **Option B1 (Recommended, conditional on I1):** `.research-system/evidence/w9/legacy-write-records.json` (`w9-legacy-write-records/1`) keyed by `(pr_number, normalized_path, old_blob, new_blob)` at `C`, with `P1`-ancestor `owner_note` & `independent_review` (`P1` proves age, not authorship). **B2:** same-PR refs under I1 CODEOWNERS. **B3:** `gh api` PR bodies (not offline-testable).
- **Records:** `06v-addendum-2026-11-10-w9-paths.md:14-15` row + `P-090`; `research_system/legacy/` untouched.

### 16.5 Owner Point D — Resolving `O-32` in `shared-surface-changes.json`

*Pointers:* §6.5 (Rule 3), `HR-2`.
- **Option D3 (`"w9-shared-surface-changes/2"`, no commit field — Recommended):** Bump `SHARED_SURFACE_CHANGES_FORMAT` (`evidence.py:42`) closed on `{"pr_number", "surface", "old_blob", "new_blob", "affected_registrations"}` (ack-only `pr_number: null` on unmapped), require late `<head>` entries + `independent_review` on Rule 3 acks (`require_change_list` `evidence.py:190-218`), and check `evidence.blob_at(repository_root, obs_commit, surface)` in `acceptance.py:121-136` against `new_blob` or later (`A -> B -> A` in `HR-2`). **D1:** `base_commit` (queue race). **D2:** 2-PR red window.
- **Records:** Edits `evidence.py:42,190-252`, `acceptance.py:121-136`, WP9.3 tests (`test_w9_evidence_acceptance.py`, `test_w9_wp9_3_2_runtime.py`), & `06v-addendum-2026-11-10-w9-paths.md:28`; needs **WP9.3 amendment (`wp9-3-design-note.md` §10.4), independent review, & `P-090`**.

### 16.6 Owner Point E — D-5 cadence gate placement

*Pointers:* §8.4, `HR-4`.
- **Option E1 (Recommended if weekly PR cost accepted):** Commit `vault-detector-runs.json` (`w9-vault-detector-runs/1`, `"run"`/`"owner_cadence_reset"`); enforce `require_vault_detector_cadence` when `bool(reader.accepted_cl_export)` is `True` at `LR-003`/`LR-015` (`preparers.py:686-690,1215-1218`) & `LR-016`/`LR-020` (`acceptance.py:147-152`) + `--check-cadence` (weekly PR + I1 bypass + `ars store advance-binding`). **E2:** CLI `--check-cadence` only.
- **Records:** E1 edits `evidence.py`, `preparers.py`, `acceptance.py`, `06v-addendum-2026-11-10-w9-paths.md`; needs **WP9.3 amendment, independent review, & `P-090`**.

### 16.7 Owner Point F — Running `tests/tools/test_w9_detectors.py` in `admission-controls`

*Pointers:* §2.3, §10.3, §11.2, §12.1.
- **Option F1 (Recommended, paired with I1):** Wire `tests/tools/test_w9_detectors.py` into `ci.yml:166-216` (`admission-controls`, `:210`) & `ADMISSION_CONTROL_MODULES` (`test_ci_platform_policy.py:175-229`, `:226`). Covers `L1_LIVE`, unit tests + top-level shape checks on the 3 JSONs + `--verify-watched-to-fail` with `--code-root` assembled from `HEAD`'s `baselines[-1]` via `§10.2` + `test_recorded_detector_import_closure_covers_ast_walk`/`test_detector_closure_is_stdlib_only` scoped to that assembled `baselines[-1]` tree/synthetic repos (never the checkout's non-code-owned closure modules; byte, internal-import, & third-party-import edits stay green, `R7-M1`), optional 1-sentence advisory Rule 0.2 summary (`HEAD` vs `HEAD^1`, exit `0`), and **`W9-T7` as `unit` — explicit departure from `06v:230,503`** (`test_w9_wp9_5_detectors.py` stays `integration, @pytest.mark.slow`, `affected_research_tests.py:120-147`, nightly `research-system-suite.yml:8-9,15,17`). **Zero `gh`, `GH_TOKEN`, `pull-requests: read`, PR pin-advance gate, or `ci.yml` permissions/timeout changes.** **F2:** `legacy-write-detector.yml` only.
- **Records:** Edits `.github/workflows/ci.yml:212` (`.github/CODEOWNERS:18`), `tests/tools/test_ci_platform_policy.py:228`, `06v-addendum-2026-11-10-w9-paths.md` (`06v:230` departure), & `P-090`.

### 16.8 Owner Point G — Test-time budget

*Pointers:* §12.3, §15.1 item 4. **Option G1 (`300s`, Recommended pending `UNVERIFIED-3`):** serial `--no-cov` incl. `@pytest.mark.slow` (`P-087` item 7 `03-decisions-and-open-questions.md:5919-5923`; distinct from §15.2's `600s` walk stop rule; note WP9.4 integration runs ~5–11 min under A1). **Option G2:** `120s` after `UNVERIFIED-3`. Records in `P-090`.

### 16.9 Owner Point H — Routine `.apm/tracker.md` Working-Note appends

*Pointers:* §6.2.1, §6.5 (Rule 1). **Option H1 (Recommended):** Allow without §4.2(b) iff `segment(raw, "tracker_task_row")` & `"working_note_entry"` (`segmentation.py:470-473`) preserve bytes outside `## Working Notes`, task rows, and prior notes verbatim with 0 blockers & `[ \t]*\n` gaps (`#368`, `#388`, `#433`, `wp9-5-note-r2-review-2026-11-21.md:219`; `O-33` waits). **H2:** full §4.2 record per append. **H3:** freeze `.apm/tracker.md`. H1 needs dated W9 §4.2 amendment (`09-migration-compatibility-and-pilot.md` §4.2, `P-090`).

### 16.10 Owner Point J — Source, format, and L-0b pinning of vault and `CONVENTIONS.md` classifications

*Pointers:* §7.3, §7.6, §8.2, §8.3.

- **Options:**
  - **Option J1 (`w9-cl-classified-list/1` + pinned `ACCEPTED_CONVENTIONS_CLASSIFICATION` — Recommended):** Validate `ACCEPTED_CL_EXPORT[-1]["classified_list"]` (`accepted_w9.py:86-88`) against `"w9-cl-classified-list/1"` with 1-based `row_ordinal` (`evidence.py:347-358`, `segmentation.py:408`), and add empty `ACCEPTED_CONVENTIONS_CLASSIFICATION = ()` to `accepted_w9.py` (defaulting to the 9-section 68-unit baseline until L-0b pins `"w9-conventions-classified-locks/1"` by `(anchor_text, unit_hash)` `segmentation.py:391-402` at its pinned commit).
  - **Option J2:** Carry final labels inside `w9-cl-export/1` at L-0b and keep 9 `CONVENTIONS.md` sections permanent.
- **Recommendation:** **Option J1** (preserving D-4 and `IMPORTER_MODULES`, CODEOWNED under Option I1).
- **What it changes & records needed:** Adds `ACCEPTED_CONVENTIONS_CLASSIFICATION` to `research_system/legacy/accepted_w9.py` and populates both constants + `06v-addendum-2026-11-10-w9-paths.md` at L-0b (any L-0b PR adding new evidence files, rules, or constants must be **paired with a `walk-baseline.json` pin advance** in `baselines[-1]` per §6.1 & §8.3, otherwise an older pinned copy lags silently—exit `0`—on unread files/rules/constants, fails closed on new keys under a known `format` via `§6.6`, or exits `2` on `format` changes); recorded in `P-090`.

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
| Revision 6 | 2026-11-22 | Gemini agent (under `P-089`) | Applied Stephen's `2026-11-22` **pin, no lockstep** decision and resolved all 20 findings (`R5-M1`–`R5-M3`, `R5-m1`–`R5-m11`, `R5-i1`–`R5-i6`) from `wp9-5-note-r5-review-2026-11-22.md` (`d6938710`): deleted lockstep & PR pin-advance gates from `admission-controls`, moved comparison to manual review evidence, added `main()` exit `2`, confinement/UTF-8/`python -S -P` checks, extrapolated `2 × 1x` labels, and updated `§18`–`§21`. |
| Revision 7 | 2026-11-23 | Gemini agent (under `P-089`) | Addressed all 18 findings (`R6-M1`–`R6-M3`, `R6-m1`–`R6-m9`, `R6-i1`–`R6-i6`) from `wp9-5-note-r6-review-2026-11-22.md` (`d47a8e72`), adopting R6's proposed text for `R6-M1`–`R6-M3` (exit `2` on unparseable/unknown-`format`; runnable `--assemble-only` comparison & grammar-only Rule 0.2 (iv); required assembled `--code-root` & schema-only checks in `admission-controls`), hardened `§10.2` (`isreserved`/`~`/`casefold`/re-hash), added `test_pinned_wrapper_is_ascii_only`, labelled `§12.3` estimates, rolled `R4`/`R5` into `§18`/`§19`, and added `27`-case `§21.1` item 11. |
| Revision 8 | 2026-11-23 | Gemini agent (under `P-089`) | Final narrow revision for `wp9-5-note-r7-review-2026-11-23.md` (`c4c62b3b`): resolved `R7-M1` (scoped closure/stdlib tests to assembled `baselines[-1]` + 2 import cases), `R7-m1` (total exit codes, `EvidenceRefused` subclasses, shims importing inside `main()`, `§8.2`), `R7-m2` (`"new keys"` vs files/rules/constants + parse all `<head>` evidence), `R7-m5`, `R7-m9`, `R7-m10` (`§19`), `R7-d1` (`HR-3`/Owner Point C); carried `R7-m3`/`m4`/`m6`–`m8`/`i1`–`i7` to `§15.3` and added `§20.1`. |
| Exemption-row addendum | 2026-11-24 | Gemini agent (under `P-089` / `P-090` item 4) | Designed `rule0_exemptions` (§6.5.1, present as `[]` from row `0` in `walk-baseline.json`), validity/unexemptable rules, exact 6-tuple matching, `--acknowledged-from`/`R7-d1` interactions, and 1 positive + 8 negative controls (§12.1); updated §1, §2.1, §6.1–§6.5, §13–§14, §16.2, and added §20.2. |
| Exemption-row addendum, revision 2 | 2026-11-24 | Gemini agent (under `P-089` / `P-090` items 4–5) | Addressed all 16 findings (`X-M1`–`X-M2`, `X-m1`–`X-m7`, `X-i1`–`X-i7`) from `wp9-5-note-exemption-addendum-review-2026-11-24.md` and `P-090` item 5 (`813088e9`): malformed-intermediate raw-parse checks, non-`<head>` parse/format as `Rule 0.2` exit `1`, persistent superseded readers, mandatory pre-merge `--head <candidate>` runs, `fp_index[b0] = -1` / stricter-than-`is_ancestor`, sub-check `#check` `location`, cleared-tuple output trace, rebuilt §12.1 controls, `X-m2(b,c)`/`X-i5`/`X-i7` in §15.3, and §20.3. |

---

## 18. Compact disposition index: revisions 1 to 5

Archived history lives in Git & review reports (`r1` `edb9acc6`, `r2` `3cf35bec`, `r3` `1bd4ecff`, `r4` `0e6d23e4`). All 102 findings (34 R1, 27 R2, 20 R3, 21 R4):

| Finding ID | Section(s) | Status |
|---|---|---|
| `R1-B1` | `§6.1–§6.5, §10.2, §12.1, §16.1–§16.4` *(iterated in `R3-M1`, `R4-M1`/`R4-M2`, §19)* | resolved |
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
| `R2-M1` | `§6.1–§6.5, §10.2` *(`tool_pin_commit`/worktree superseded in `R3-M1`/`R4-m7`)* | superseded |
| `R2-M2` | `§6.2.2, §6.5, §12.1, §16.2` *(checkpoints superseded in `R3-M2`, `R4-M1`, §19)* | superseded |
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
| `R3-M1` | `Header, §1–§2.3, §6, §10.2, §12–§14, §16, §21` *(`uv sync` superseded in `R4-M2`/`R4-m7`)* | superseded |
| `R3-M2` | `§1–§2.1, §6, §12, §14, §16.2, §21` *(Rule 0.2 (v)/dual walk superseded in `R4-M1`/§19)* | superseded |
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
| `R4-M1` | `§1, §6, §10.3, §12–§16, §21` *(PR verdict diff superseded in §19 `R5-M1`–`R5-M3`)* | superseded |
| `R4-M2` | `§1, §6, §10.3, §12–§14, §16.2` *(PR `HEAD` equality & lockstep superseded in §19 `R5-M1`–`R5-M3`)* | superseded |
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
| `R4-m11` | `§6.2.3` *(Option I1-narrow deleted in R6 §19 `R5-M1`)* | resolved |
| `R4-i1` | `§6.2.2, §6.5, §10.3, §12.1` | resolved |
| `R4-i2` | `§7.5, §14, §16.11` | resolved |
| `R4-i3` | `§2.3, §5.3, §14, §16.3, §16.8` | resolved |
| `R4-i4` | `§6.2.2, §12.1` | resolved |
| `R4-i5` | `§6.2.3, §10.2, §16.1` | resolved |
| `R4-i6` | `§6.2.2, §13.2, §16.2` | resolved |
| `R4-i7` | `§4.2.2, §21.1` | resolved |
| `R4-i8` | `Header, §1, §6.2.1, §13–§20` | resolved |

---

## 19. Change log: revision 5 to revision 6

Archived review details for revision 5 (`83b4ae6f`) and Stephen's `2026-11-22` **pin, no lockstep** decision (*to be entered in `P-090` with the other owner points*) live in `docs/plans/agentic-research-system/reviews/wp9-5-note-r5-review-2026-11-22.md` (`d6938710`). Compact disposition of all 20 revision-5 findings:

| Finding ID | Section(s) | Status |
|---|---|---|
| `R5-M1` | `Header, §1, §2.1, §6.1, §6.2.2–§6.2.3, §6.5, §10.3, §12.1, §13.1, §13.2 HR-3, §14, §16.1–§16.2` | resolved |
| `R5-M2` | `§6.2.2, §6.5, §12.1, §13.2 HR-3, §16.2` | resolved |
| `R5-M3` | `§1, §2.1, §10.3, §12.3, §13.1, §16.7` | resolved |
| `R5-m1` | `§2.1, §6.2.2, §6.3, §9.2, §12.1, §13.1` | resolved |
| `R5-m2` | `§6.2.2, §6.5, §12.1` | resolved |
| `R5-m3` | `§6.2.2, §12.3, §15.1–§15.2, §16.2, §16.8` | resolved |
| `R5-m4` | `§6.2.2, §12.1` | resolved |
| `R5-m5` | `§2.3, §6.1, §6.2.3, §12.1, §14, §16.1` | resolved |
| `R5-m6` | `§2.1, §6.2.3, §12.1, §14, §15.2, §16.1, §21.1` | resolved |
| `R5-m7` | `§6.2.3, §10.2, §12.1, §13.1` | resolved |
| `R5-m8` | `§6.2.3, §9.2, §12.1, §21.1` | resolved |
| `R5-m9` | `§2.1, §6.3, §9.2, §12.1` | resolved |
| `R5-m10` | `Header, §1, §2.1, §6.2.2, §12.3, §13.1, §14, §21.1` | resolved |
| `R5-m11` | `§6.2.1, §12.1, §13.1, §14, §18–§20` | resolved |
| `R5-i1` | `§13.2 HR-3, §16.2` | resolved |
| `R5-i2` | `§10.2, §14, §16.1` | resolved |
| `R5-i3` | `§11.3, §12.3` | resolved |
| `R5-i4` | `§21.1` | resolved |
| `R5-i5` | `§4.2.2, §21.1` | resolved |
| `R5-i6` | `§6.2.3, §21.1` | resolved |

---

## 20. Change log: revision 6 to revision 7

Disposes of all 18 findings in `docs/plans/agentic-research-system/reviews/wp9-5-note-r6-review-2026-11-22.md` (`d47a8e72`, reviewing revision 6 `95dfefe7`), adopting R6's proposed text for `R6-M1`–`R6-M3`:

| Finding ID | Section(s) | Status | Change in revision 7 |
|---|---|---|---|
| `R6-M1` | `§1, §2.1, §6, §8.2, §12–§14, §16.1` | resolved | Adopted R6 proposed text in `§6.6` item 1 (exit `2` `ERROR` + `--verdict-json` `"error"` on unparseable/unknown-`format`; exit `1` reserved for Rules 0–3), `§8.2` (`1` pre-L-0b), `§12.1` tests, & `HR-3` (a); applied across all WP9.5 tools. |
| `R6-M2` | `§2.1, §6, §12–§14, §16.1` | resolved | Adopted R6 proposed text in `§6.2.2` (6-step Git Bash/`cmd` procedure, `pull/<N>/merge`/`commit-tree`, `PYTHONPATH`+`PYTHONSAFEPATH=1` `python -S -P`, sorted `w9-verdict/1`), `§6.5` Rule 0.2 (iv), & `§12.1` row tests. *Departures:* chose `--assemble-only --rev <rev> --out <dir>` on `run_w9_pinned_detectors.py`, included `candidate \| rule \| path` in (iv) grammar, and added `git diff`/re-record (`R6-m7`). |
| `R6-M3` | `§9.2, §10.3, §12–§14, §16.7` | resolved | Adopted R6 proposed text in `§9.2` item 3 (repaired garbled line) & `§10.3`: `--code-root` has no default & in `admission-controls` uses `HEAD`'s `baselines[-1]` tree assembled by `§10.2`, never checkout; schema checks = top-level shape only; added `L1_LIVE` unrowed-edit test (`§12.1`). |
| `R6-m1` | `§6.2.3, §10.2, §12.1, §21.1` | resolved | Moved hash verify post-loop across all written keys; rejected `casefold()` collisions & `~` segments; added tests (`§12.1`, `§21.1`). |
| `R6-m2` | `§1–§2.1, §6, §12–§16, §21` | resolved | Specified Git Bash (`cmd /c` option) on wrapper command, added `test_pinned_wrapper_is_ascii_only`, & added Bash wrapper in `§21.1` item 9. |
| `R6-m3` | `§6.1–§6.5, §13.1` | resolved | Labelled `Rule 0.1`–`Rule 0.3` in `§6.5` (verdict includes `Rule 0.3`); dropped "Rule 0.3" from deleted-lockstep sentences (`R6-i2`). |
| `R6-m4` | `§6.3` | resolved | Fixed `tools/check_bypass_merges.py:160` -> `:140-144` (`_gh` `encoding="utf-8"`). |
| `R6-m5` | `§6.2.2, §12.3, §21.1` | resolved | Labelled §12.3 unwritten timings `(estimate, unwritten code)`, reconciled R6 pin/clone times, recorded R6 stand-ins & `~28%` spread. |
| `R6-m6` | `Header, §21.1` | resolved | Added `27`-case pin-heredoc script (`§21.1` item 11, matching Header) & full wrapper script + `1 True` explanation in item 9. |
| `R6-m7` | `§6.2–§6.5, §13.2, §16.1–§16.2` | resolved | Added `git diff`/re-record to `§6.2.2`; removed "rollback" from Rule 0.2 (iv); added Rule 0.2 (ii) snap/merge-race notes in `HR-3`, `§16.1`–`§16.2`. |
| `R6-m8` | `§6.1, §6.2.3, §8.3, §13.2, §16` | resolved | Noted silent `exit 0` lag on unread additions & required L-0b to pair with a pin advance (`§8.3`, `§16.10`). |
| `R6-m9` | `§6.1, §13.2 HR-3, §16.1` | resolved | Scoped `walk-baseline.json` code-ownership strictly to `Option I1` (un-owned under `Option I2`). |
| `R6-i1` | `§1, §6.1, §6.2.3, §13–§16` | resolved | Distinguished `21` stdlib runtime blobs + `1` workflow review-record blob (`22` recorded, workflow never executed). |
| `R6-i2` | `§1, §6.1, §13–§16` | resolved | Kept deleted-lockstep prose once in `§6.1` (+ §20); aligned `§1` table to 17 Handover `§3` items; tagged `§15.2` item 5. |
| `R6-i3` | `§6.2.3, §10.2, §12.1, §21.1` | resolved | Used `os.path.isreserved` (`part` & `rel_path`), caught `CalledProcessError`/JSON/`KeyError` with `ERROR:`, & tested superscript/space names. |
| `R6-i4` | `§6.2.2, §10.3, §12–§13, §16.7` | resolved | Specified optional advisory Rule 0.2 report in 1 sentence (`HEAD` vs `HEAD^1`, `$GITHUB_STEP_SUMMARY`, exit `0`); dropped test row. |
| `R6-i5` | `§2.1, §6.2–§6.3, §10.2` | resolved | Wrapper propagates child exit `2`; scoped `"never 1"` to WP9.5 tools; replaced heredoc tracebacks with `ERROR:` exit. |
| `R6-i6` | `§21.1` | resolved | Recorded R6 live ruleset/eval re-check (`16/16`, `56`/`32`, `4ca375a3`, `#446`/`#448`) in `§21.1` item 8. |

### 20.1 Change log: revision 7 to revision 8

Disposes of all 18 findings plus `R7-d1` in `docs/plans/agentic-research-system/reviews/wp9-5-note-r7-review-2026-11-23.md` (`c4c62b3b`, reviewing revision 7 `08840c3e`), adopting R7's proposed text for `§2` items and carrying `R7-m3`, `R7-m4`, `R7-m6`–`R7-m8`, and `R7-i1`–`R7-i7` into `§15.3`:

| Finding ID | Section(s) | Status | Change in revision 8 |
|---|---|---|---|
| `R7-M1` | `§6.2.3, §10.3, §12.1, §13–§16` | resolved | Adopted review text in `§6.2.3`/`§10.3` (closure/stdlib tests run only on assembled `baselines[-1]`/synthetic repos, never checkout's non-owned modules); extended `§12.1` (`new internal import`, `third-party import` green); no Owner Point I `(e)` freeze added. |
| `R7-m1` | `§6.3, §6.6, §8.2, §12.1, §13.1, §16.1` | resolved | Exit `1` always carries $\ge 1$ `(rule, path)` (`EvidenceSchemaError` -> `["Rule 0.2", "<path>"]`); import/`EvidenceParseError`/`UnknownEvidenceFormatError`/missing `<head>` exit `2`; updated `§8.2` message & row `1316` per-tool list; shims import inside `main()`. *Note:* subclasses live in `tools/_w9_detector_evidence.py` since `evidence.py:108-131` stays untouched pre-sign-off. |
| `R7-m2` | `§6.1, §6.2.3, §6.6, §13.2, §16.1, §16.10` | resolved | Scoped `exit 0` lag to new files, rules, & constants (`new key` under known `format` = `EvidenceSchemaError`); specified parsing every known `<head>` evidence file each run. |
| `R7-m3` | `§15.3` | carried to code task | Comparison placeholders, step 2 `--repo-root .`/fetch, Git Bash vs `cmd /c`, & `indent=2` JSON diff. |
| `R7-m4` | `§15.3` | carried to code task | `--assemble-only` skips freshness/I3, non-empty `--out` exit `2`, & Python `3.13`+ minimum. |
| `R7-m5` | `§6.2.2` | resolved | Added review text to step 4 (read step 3 diff first; use prior `--pr-map` or `pull-requests: read`-only token). |
| `R7-m6` | `§15.3` | carried to code task | Observable row `1316` phrasing & test-only comparison diff helper scope. |
| `R7-m7` | `§15.3` | carried to code task | Lane assembly reuse mechanism, byte-equality copy test, & 27-case wrapper check. |
| `R7-m8` | `§15.3` | carried to code task | Rule 0.2 (iv) verdict-line prefix recognizer & `<rule>` set (text + row `1315`). |
| `R7-m9` | `§13.2 HR-3, §16.1` | resolved | Added whole-tree snap / unreviewed non-owned edits in `HR-3` & Owner Point I, narrowed `(b)`, & added `"ordinary PR"` to `I2`. |
| `R7-m10` | `§19` | resolved | Changed `"entered in P-090"` to `"to be entered in P-090"`. |
| `R7-d1` | `§13.2 HR-3, §16.2` | resolved | Stated post-L-1 format moves require a new file path or exemption row, not in-place (A1/D3 unaffected pre-code); added to C causes. |
| `R7-i1` | `§15.3` | carried to code task | Step 5 `ERROR` interpretation when old side hits format move. |
| `R7-i2` | `§15.3` | carried to code task | Pin-step first-segment allowlist (`tools`, `research_system`, `.github`). |
| `R7-i3` | `§15.3` | carried to code task | Four-run `~34%` spread & `18.7s` 27-case harness timing reconciliation. |
| `R7-i4` | `§15.3` | carried to code task | Live ruleset sliding window note (`50` / `26` bypass at R7). |
| `R7-i5` | `§15.3` | carried to code task | Clean PowerShell child encoding note (mooted by ASCII wrapper test). |
| `R7-i6` | `§15.3` | carried to code task | Malformed JSON variants & empty-map handling in pin-step tests. |
| `R7-i7` | `§15.3` | carried to code task | Advisory report invocation/omission & long-line hygiene. |

### 20.2 Change log: exemption-row addendum

Adds the Rule 0 exemption-row design requested by Follow-up 8 (`P-090` item 4, `0e1269bd`; Revision 8 reviewed in `wp9-5-note-r8-review-2026-11-23.md` `ae608701`; pre-code gates recorded in `79d8a684`):

| Section(s) | What changed |
|---|---|
| Header | Updated `Date` (`2026-11-24`), `Status` (for independent review), `Authority` (+ `P-090` `0e1269bd`), and `Prior reviews` (+ Revision 8 `526334c8` / `ae608701`). |
| `§1`, `§2.1` | Added `§6.5.1` `rule0_exemptions` pointer in `§1` item 4 and `§2.1` item 2; updated `§1` item 17 to reflect `P-090` decisions and `§6.5.1` (the Revision 8 deferral placeholder stood in `§16.2`; both `§1` and `§16.2` now point to `§6.5.1`). |
| `§6.1`, `§6.2.2`, `§6.5` | Added `"rule0_exemptions": []` from row `0` inside `walk-baseline.json` (`w9-walk-baseline/1`), listed it among strictly append-only Rule 0.2 fields, extended `--acknowledged-from <pr_base>` to supply both `acknowledged` and `rule0_exemptions`, and linked `§6.2.2` step 6 & `§6.5` Rule 0 to `§6.5.1`. |
| `§6.5.1` (**new**) | Designed `rule0_exemptions`: I1-CODEOWNED placement & row-`0` presence (`R7-m2` vs exit `2`), closed 7-key schema + `(old_blob, new_blob)` `null` handling + `location` (`$` vs `baselines/acknowledged/ruleset_gap_acknowledgements[k]`), validity checks (`P1` `entry_sha256`, `R0-EXEMPT \| ...` line grammar, strict `b0 < commit < source_commit <= P1(C_ex) < C_ex`, `blob_at`), unexemptable invariants (`rule0_exemptions` itself, off-chain/same-commit, Rules 1–3, `walk-baseline.json` `format`/`baselines[0].baseline_commit`/`d8_rule_suites_limit_decision_ref`/deletion, exit `2`), exact 6-tuple matching & recurrence, and `--verdict-json` / `--acknowledged-from` / `R7-d1` interactions. |
| `§12.1` | Added 1 positive + 8 negative `rule0_exemptions` controls to the `Rule 0 & closure changes` row. |
| `§13.1`, `§13.2`, `§14`, `§16.2` | Pointed `MC-2`, `HR-3` (`HR-3 (d)` & permanence), Claim 2, and Owner Point C (`Option C1` + `C-R0-exemption`, replacing Revision 8's unbuilt placeholder) to `§6.5.1` (`P-090` `0e1269bd`). |
| `§17`, `§20.2` | Added addendum row to `§17` and this `§20.2` change log. *Untouched per scope rules:* `§4.2.2`, `§4.3.3`, `§10.2`–`§10.3`, `§15.1`, `§15.3`, `§21.1`–`§21.2`. |

### 20.3 Change log: exemption-row addendum, revision 2

Addresses all 16 findings in `wp9-5-note-exemption-addendum-review-2026-11-24.md` (reviewing `b3500098`) and Stephen's `P-090` item 5 (`813088e9`), leaving `§4.2.2`, `§4.3.3`, `§10.2`, `§10.3`, `§15.1` recorded results, `§21`, and commit `1b65fc7e`'s CodeRabbit edits untouched:

| Finding ID | Section(s) | Status & summary (plus departures from review text) |
|---|---|---|
| `X-M1` | `§6.5.1` (#2, #4–#5), `§6.6` (#1), `§12.1`, `§13.1` `MC-2`, `§13.2` `HR-3`, `§16.2` | Added review's 3 sentences: raw `json.loads` unexemptable/append-only comparisons across malformed intermediates reported at later commit; non-`<head>` parse/`UnknownEvidenceFormatError` as `Rule 0.2` `exit 1` (`"$"`); superseded format reader kept while walked versions remain; added all 3 controls in `§12.1`. *Adjustment:* in control (iii), noted `<head>` exit `2` vs non-`<head>` `Rule 0.2` exit `1` to match `X-M1`'s non-`<head>` rule. |
| `X-M2` | `§6.5.1` (#1, #3–#4), `§12.1`, `§13.2` `HR-3`, `§16.2` | Added mandatory pre-merge `--head <candidate>` run (`walk-baseline.json` PRs incl. L-1 row `0`) + post-rebase `entry_sha256` recompute; no `rule0_exemptions[k]` location and invalid rows stay recoverable only via undesigned re-baseline at new path (`P-090` item 5). *Adjustment:* aligned command with `1b65fc7e` (`--pr-map <prior-run-pr-map.json>`, omitting `--acknowledged-from` so the appended candidate row itself validates). |
| `X-m1` | `§6.5.1` (#3), `§12.1`, `§13.1` `MC-2` | Set `fp_index[b0] = -1`; called `fp_index` "stricter than" `is_ancestor`; added `P1(C_ex) == b0` (adopted review's exact guard) & `commit == b0` / off-chain `commit` controls. *(Follow-up 9 §1.3 paraphrased "violating commit"; kept review's exact `fp_index[P1] == -1` guard on appending commits so L-1 row `0` stays recoverable for `#iii`.)* |
| `X-m2` | `§6.5.1` (#2, #5), `§12.1`, `§13.1` `MC-2`, `§15.3` | `(a)` Added `#<check>` sub-check discriminator on `walk-baseline.json` list `location`s (`baselines[3]#iii`), updated JSON example, & added sibling-sub-check control; `(b, c)` carried to `§15.3`. |
| `X-m3` | `§6.5.1` (#4) | Removed false `§10.2` pin-read claim; grounded `format` unexemptability in `§6.6` item 1 (`UnknownEvidenceFormatError` exit `2`), schema contract anchor, & `P-090` item 5 new-path-only rule. |
| `X-m4` | `§6.2.2` (step 6) | Reworded `"never the same commit"` to `"never the same commit as the violation"` so pin-advance PRs can carry rows for earlier `V` with pre-existing `P1` slices. |
| `X-m5` | `§6.5.1` (#2, #4–#5), `§13.2` `HR-3`, `§16.2` | Reworded `"never in place without a cleared Rule 0 fault"`; recorded `P-090` item 5 narrowing so `walk-baseline.json` moves only via new file path (re-baseline to be designed); **chosen option:** documented deleted-then-restored content-laundering human-review limit in `HR-3` (rather than adding restoring commit/blob grammar to deletion slices). |
| `X-m6` | `§12.1` | Rebuilt `Rule 0 & closure changes` exemption controls: 1 guard per control on otherwise-valid rows, paired positive run, N1–N8 + all 6 missing controls + constructible N7 replacements + fixed N4 deletion-restore fixture + 3 `X-M1` controls + `X-M2` step. |
| `X-m7` | `§1` (row 17), `§6.5.1` (#4), `§15.1` (#3), `§16`, `§16.2` | Fixed `"non-empty []"` $\to$ `"any value other than []"`; removed the stale unreviewed parenthetical in `§1` row 17; updated `§15.1` #3 & `§16` intro to decided status; marked `d8_rule_suites_limit_decision_ref` decided unexemptable (incl. first transition, `P-090` item 5). |
| `X-i1`–`X-i7` | `§6.5.1` (#1, #3, #5), `§12.1`, `§13.1`, `§13.2` `HR-3`, `§15.3` | `X-i1`: trimmed redundant CODEOWNERS claim, stated co-location blast radius (`§6.5.1` #1). `X-i2`: added per-cleared-tuple output line naming row index (`§6.5.1` #5, `§12.1`, `MC-2`). `X-i3`: noted age-not-authorship / squash-only guarantee (`§6.5.1` #3). `X-i4`: added `Rule 0.1` deleted-entry `MC-1` tripwire note (`HR-3`). `X-i5`, `X-i7`: carried to `§15.3`. `X-i6`: recorded pre-revision sizes. |

---

## 21. Appendix A: Verification

### 21.1 Reproducible verification commands and script outputs

Read-only checks against `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note` (`dbd54fe382e7b2849d3f2038393cbdb4d709477b` / `HEAD`) & `gh api` `GET`s (no vault prose read; tree clean before edits). Prior reviews reproduced: R2 (`wp9-5-note-r2-review-2026-11-21.md` §2, §5, `:218`, `0c9a90ed`) walk/counts/ruleset/clone timings; R3 (`wp9-5-note-r3-review-2026-11-21.md` §2, §6, `R3-i4`, `092db1f1`) 22 rows, 15 blobs, counts, ruleset, YAML/`bash -n`, synthetic U-4; R4 (`wp9-5-note-r4-review-2026-11-22.md` §0, §2, §6, `R4-i7`, `48b5e935`) §21.1, isolation, pin heredoc, citations; R5 (`wp9-5-note-r5-review-2026-11-22.md` §0, §2, §6, `R5-i5`, `83b4ae6f`) 22/320 walk, 70/90 units, 15 blobs, `16/16` (`56`/`32`), clone, stand-ins (`11.79s`/`34.85s`/`61.58s` + `~11.3s` `gh api`), YAML/`bash -n`, parent `-S -P`, confinement, `404` citations; R6 (`wp9-5-note-r6-review-2026-11-22.md` §0, §2, §6, `R6-i6`, `95dfefe7`) 22/320 walk, 70/90 units, 15 blobs, `16/16` (`56`/`32`, `4ca375a3`, `#446`/`#448`), `1.99–2.07s` clone, `12.97s`/`44.03s`/`77.7s` (`26.35s` 2x) stand-ins, parent+child `-S -P` + wrapper pipe, 32 pin runs (`0.32s`/run), YAML/`bash -n`, `231` pairs (`0` out-of-range); R7 (`wp9-5-note-r7-review-2026-11-23.md` §0, §2–§3, `c4c62b3b`) reproduced all §21.1 items (`PIN_CASES_OK: 27` + 27 extra cases), YAML/`bash -n`, and `219` citation pairs (`0` out-of-range). *(Revision 8 itself has not yet undergone a final focused review.)*

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

`rulesets/20822054` returned HTTP 200 (`id: 20822054`, `P-049 Gate 6 main merge admission`, `enforcement: "active"`, `refs/heads/main`, `required_approving_review_count: 0`, `require_code_owner_review: true`, `required_review_thread_resolution: true`, `squash`, strict status checks `integration_id: 15368`, `merge_queue` `SQUASH` 1-by-1 `ALLGREEN` `check_response_timeout_minutes: 20`, `non_fast_forward`, `bypass_actors: [{actor_id: 5, RepositoryRole, pull_request}]`). `rule-suites?time_period=month`: 30-day sliding window (`57`/`33` initially; `58`/`34` after `#448` `4ca375a3`; `56`/`32` at `2026-11-21T23:03Z`, re-verified R3 `:99`, R4 `:108`, R5 `:19,112`, R6 `wp9-5-note-r6-review-2026-11-22.md:19,113,117` `R6-i6`: `dbd54fe3`->`#446`, `4ca375a3`->`#448`).

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

Confirmed `Non-stdlib imports in 15 existing closure modules: []`; both `script` and `-m tools.probe_iso` runs from `cwd=wt` exited `0`, and parent + child (`[sys.executable, "-S", "-P", ...]`) printed `no_site: 1`, `safe_path: True`, `site_in_path: False`, `wt_in_path: False`, `<td_path>` paths, and blocked non-closure/third-party imports with `ModuleNotFoundError` (`R5-m8`, `R5-i6`). Git Bash wrapper pipe test (PowerShell 5.1 re-encodes non-ASCII stdin, motivating `test_pinned_wrapper_is_ascii_only`; `1 True` = `no_site=1, safe_path=True`):

```bash
set -euo pipefail
py="/c/Users/steph/AppData/Local/Programs/Python/Python313/python.exe"
td=$(cygpath -m "$(mktemp -d)"); trap 'rm -rf "$td"' EXIT
git init -q "$td"; git -C "$td" config core.autocrlf false; git -C "$td" config user.email t@t; git -C "$td" config user.name t
cat > "$td/child.py" <<'EOF'
import sys; print("CHILD", sys.flags.no_site, sys.flags.safe_path, sys.argv[1:])
EOF
cat > "$td/wrap.py" <<'EOF'
import os, subprocess, sys
print("WRAP_OK", sys.argv[1:], sys.flags.no_site, sys.flags.safe_path, flush=True)
subprocess.run([sys.executable, "-S", "-P", os.path.join(os.getcwd(), "child.py"), *sys.argv[1:]], check=True)
EOF
git -C "$td" add child.py wrap.py && git -C "$td" commit -q -m init
(cd "$td" && git --no-replace-objects show HEAD:wrap.py | "$py" -S -P - --repo-root .)
```

Printed `WRAP_OK ['--repo-root', '.'] 1 True` before `CHILD 1 True ['--repo-root', '.']` (`R5-m6`, `R6-m2`, `R6-m6`).

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

`1x` stand-in timings (without Rules 0–3 eval/`gh api`): `1_month_60` (`60`/`6`): **`14.05s`** (R5 **`11.79s`**, R6 **`12.97s`**; 2x: R5 `24.04s`, R6 **`26.35s`**); `3_months_178` (`178`/`12`): **`34.46s`** (R5 **`34.85s`**, R6 **`44.03s`**; extrapolated `2 × 1x`: `68.92s`); `5.5_months_320` (`320`/`22`): **`62.84s`** (R5 **`61.58s`**, R6 **`77.7s`**; up to ~28% spread across 3 runs, plus R5 **`~11.3s`** for `22` live `pulls` GETs or ~14s/unmapped under 3-try back-off; extrapolated `2 × 1x`: `125.68s`). *(Post-merge runs walk `1x` only; extrapolated `2 × 1x` applies solely to manual offline comparison, §6.2.2.)*

**11. `§10.2` pin-heredoc confinement, alias/Windows reserved names, post-loop re-hash, and Option I3 checks (`27` cases under Git Bash, `R6-m1`, `R6-m6`, `R6-i3`, `R6-i5`):**

```powershell
@'
import hashlib, json, os, pathlib, re, subprocess, tempfile, textwrap, yaml
wt = pathlib.Path(r"C:\Users\steph\TDL\.apm\worktrees\wp9-5-note")
note = (wt / "docs/plans/agentic-research-system/transition/w9/wp9-5-design-note.md").read_text("utf-8")
wf = next(textwrap.dedent(m.group(1)) for m in re.finditer(r"^[ \t]*```yaml\n(.*?)\n[ \t]*```", note, re.M | re.S) if "w9-detector" in m.group(1))
pin_step = next(st["run"] for st in yaml.safe_load(wf)["jobs"]["detect-legacy-writes"]["steps"] if "detector_closure_blobs" in st.get("run", ""))
bash_exe, base_py_dir = r"C:\Program Files\Git\bin\bash.exe", r"C:\Users\steph\AppData\Local\Programs\Python\Python313"
def git(cwd, *a, inp=None):
    out = subprocess.check_output(["git", "-C", str(cwd), *a], input=inp, text=inp is None)
    return (out.decode() if isinstance(out, bytes) else out).strip()
def run_case(name, expect_ok, cmap, off_chain=False, wb_raw=None, i3=None):
    with tempfile.TemporaryDirectory() as td:
        rt = pathlib.Path(td); repo = rt / "repo"; repo.mkdir(); rtmp = rt / "tmp"; rtmp.mkdir(); genv = rt / "genv.txt"; genv.write_text("", "utf-8")
        for args in [("init", "-b", "main"), ("config", "user.email", "t@t"), ("config", "user.name", "t"), ("config", "core.autocrlf", "false")]:
            subprocess.run(["git", "-C", str(repo), *args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        (repo / "seed.txt").write_text("0\n", "utf-8"); git(repo, "add", "."); git(repo, "commit", "-q", "-m", "c0")
        c0 = git(repo, "rev-parse", "HEAD")
        if off_chain:
            git(repo, "checkout", "-q", "-b", "side"); (repo / "s.txt").write_text("s\n", "utf-8"); git(repo, "add", "."); git(repo, "commit", "-q", "-m", "side")
            b_ref = git(repo, "rev-parse", "HEAD"); git(repo, "checkout", "-q", "main")
        else: b_ref = c0
        blobs = {k: (git(repo, "rev-parse", "HEAD^{tree}") if v == "TREE" else v if len(v) == 40 else git(repo, "hash-object", "-w", "--stdin", inp=v.encode())) for k, v in cmap.items()}
        ev = repo / ".research-system/evidence/w9"; ev.mkdir(parents=True, exist_ok=True)
        wb = {"schema_version": "w9-walk-baseline/1", "baselines": [{"baseline_commit": b_ref, "detector_closure_blobs": blobs}]}
        (ev / "walk-baseline.json").write_text(wb_raw if wb_raw is not None else json.dumps(wb), "utf-8")
        (ev / "detector-controls.json").write_text("{}", "utf-8"); git(repo, "add", "."); git(repo, "commit", "-q", "-m", "ev")
        git(repo, "update-ref", "refs/remotes/origin/main", git(repo, "rev-parse", "HEAD"))
        dig = hashlib.sha256(json.dumps(blobs, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        env = {**os.environ, "PATH": f"{base_py_dir}{os.pathsep}{os.environ.get('PATH', '')}", "RUNNER_TEMP": str(rtmp), "GITHUB_ENV": str(genv), "REQUIRE_I3_PIN": "true" if i3 else "false", "W9_DETECTOR_PIN_VAR": {"EMPTY": "", "WRONG_DIGEST": json.dumps({"walk_baseline_commit": b_ref, "closure_blobs_sha256": "f"*64}), "WRONG_BASELINE": json.dumps({"walk_baseline_commit": "0"*40, "closure_blobs_sha256": dig}), "VALID": json.dumps({"walk_baseline_commit": b_ref, "closure_blobs_sha256": dig})}.get(i3, "")}
        r = subprocess.run([bash_exe, "-c", pin_step], cwd=str(repo), env=env, capture_output=True, text=True)
        out = r.stdout + r.stderr
        assert "Traceback (most recent call last)" not in out and not list(rt.glob("escaped*")), f"{name}: raw traceback or escape:\n{out}"
        if expect_ok: assert r.returncode == 0, f"{name}: expected 0 got {r.returncode}\n{out}"
        else: assert r.returncode != 0 and "ERROR:" in out, f"{name}: expected named ERROR got {r.returncode}\n{out}"
bad_keys = [("traversal", "../escaped.txt"), ("abs_posix", "/escaped_abs.txt"), ("abs_drive", "C:/escaped_drive.txt"), ("backslash", "tools\\a.py"), ("dot_prefix", "./tools/a.py"), ("double_slash", "tools//a.py"), ("colon_ads", "tools/a.py:evil"), ("trailing_dot", "tools/a.py."), ("trailing_space", "tools/a.py "), ("shortname_tilde", "tools/CHECK_~1.PY"), ("win_nul", "tools/nul"), ("win_con_py", "tools/CON.py"), ("win_con_space", "tools/CON .py"), ("win_nul_space", "tools/NUL .txt"), ("win_conin", "tools/CONIN$"), ("win_com_sup", "tools/COM\u00b9"), ("win_lpt_sup", "tools/LPT\u00b3.txt")]
cases = [("valid_happy", True, {"tools/a.py": "print(1)\n", "research_system/__init__.py": "\n"}, {}), *[(lbl, False, {k: "x\n"}, {}) for lbl, k in bad_keys], ("case_collision", False, {"tools/Dup.py": "1\n", "tools/dup.py": "2\n"}, {}), ("absent_obj", False, {"tools/a.py": "0"*40}, {}), ("tree_obj", False, {"tools/a.py": "TREE"}, {}), ("off_chain_baseline", False, {"tools/a.py": "x\n"}, {"off_chain": True}), ("malformed_wb", False, {"tools/a.py": "x\n"}, {"wb_raw": "{}"}), ("i3_empty", False, {"tools/a.py": "x\n"}, {"i3": "EMPTY"}), ("i3_wrong_digest", False, {"tools/a.py": "x\n"}, {"i3": "WRONG_DIGEST"}), ("i3_wrong_baseline", False, {"tools/a.py": "x\n"}, {"i3": "WRONG_BASELINE"}), ("i3_valid", True, {"tools/a.py": "x\n"}, {"i3": "VALID"})]
for n, ok, cm, kw in cases: run_case(n, ok, cm, **kw)
print(f"PIN_CASES_OK: {len(cases)}")
'@ | & "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note\.venv\Scripts\python.exe" -
```

Reproduced `PIN_CASES_OK: 27` under Git Bash against the extracted `§10.2` heredoc with zero raw tracebacks (`R6-m1`, `R6-m6`, `R6-i3`, `R6-i5`).

### 21.2 Statements marked `UNVERIFIED` (pre-code gates for the reviewing session)

Statements gated in §15.1 pending live `GITHUB_TOKEN`, vault bytes, scratch-store test timing, Actions variable permissions, or hosted walk runs:

1. **`UNVERIFIED-1` (U-3 probe, §4.2.2, §15.1 item 1):** HTTP statuses, `X-Accepted-GitHub-Permissions`, and JSON keys returned to GitHub Actions `GITHUB_TOKEN` (`contents: read` vs `contents: read, pull-requests: read`) for `rulesets/20822054`, `rulesets/rule-suites?ref=refs/heads/main&time_period=day&per_page=5` (expected HTTP 403/404, `tools/check_bypass_merges.py:20-21`, deciding D-8), and `commits/dbd54fe382e7b2849d3f2038393cbdb4d709477b/pulls`.
2. **`UNVERIFIED-2` (U-4 vault dry run, §4.3.3 item 2, §15.1 item 2):** Output of `u4_dry_run.py` (`root_checks` §4.3.2, `handle_bound_read`, and both `segment(..., "computational_log_entry")` functions) on the live `833,453`-byte `04-Methods/Computational-Log.md` (`link_count == 1`, `file_facts`, `row_counts`, `blockers == []`).
3. **`UNVERIFIED-3` (Single scratch-store timing & weekly D-5 run, §12.3, §15.1 item 4):** Standalone timing of one existing WP9.3/WP9.4 scratch-store integration test on Stephen's machine (`P-087` item 7, pre-code gate §15.1 item 4), and live weekly `tools/run_w9_pinned_detectors.py` D-5 execution after L-0b/L-1.
4. **`UNVERIFIED-4` (Option I3 `vars.W9_DETECTOR_PIN` permissions, §10.2, §15.1 item 3, §16.1):** Which `ZK-Theory/TDL` roles (`admin` vs `maintain`/`write`) can write Actions repository variables (`vars.W9_DETECTOR_PIN`).
5. **`UNVERIFIED-5` (Hosted `windows-latest` `1x` walk wall time & unwritten `tools/` checks, §6.2.2, §12.3, §15.1 item 5):** Hosted `windows-latest` `1x` post-merge walk time with Rules 0–3, `.apm/tracker.md` H1 segmentation, and live `gh api` PR lookups (~60/`178`/`320`-commit intervals, `600s` stop rule §15.2 item 5), plus unwritten `tools/` tests `test_detector_closure_is_stdlib_only`, `test_pinned_wrapper_is_self_contained_stdlib_only`, and `test_pinned_wrapper_is_ascii_only`.
