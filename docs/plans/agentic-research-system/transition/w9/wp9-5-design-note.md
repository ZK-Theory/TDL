# WP9.5 Design Note — W9 Detectors (W9-D5)

| Field | Value |
|---|---|
| Date | 2026-11-22 |
| Status | **Revision 5, for independent adversarial review. Nothing in it is implemented.** |
| Package | `06v` WP9.5 — "Detectors (W9-D5)" (`docs/plans/agentic-research-system/implementation/06v-w9-implementation-plan.md:470-503`) |
| Authority | Decision register entry `P-089` (`docs/plans/agentic-research-system/03-decisions-and-open-questions.md:6071-6146`) |
| Base | `origin/main` at `dbd54fe382e7b2849d3f2038393cbdb4d709477b` (`[PIPELINE] P06: WP9.4-2 follow-up: the independent review's Minor findings (P-088 item 5) (#446)`) |
| Worktree / Branch | `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note` on branch `docs/w9-wp9-5-design-note` |
| Prior reviews | Revision 1 (`65363e27`): `wp9-5-note-r1-review-2026-11-21.md` (`edb9acc6`; `REWORK REQUIRED`: 1 Blocking, 12 Major, 14 Minor, 6 Info)<br>Revision 2 (`0c9a90ed`): `wp9-5-note-r2-review-2026-11-21.md` (`3cf35bec`; `REWORK REQUIRED`: 0 Blocking, 5 Major, 16 Minor, 6 Info)<br>Revision 3 (`092db1f1`): `wp9-5-note-r3-review-2026-11-21.md` (`1bd4ecff`; `REWORK REQUIRED`: 0 Blocking, 3 Major, 13 Minor, 4 Info)<br>Revision 4 (`48b5e935`): `wp9-5-note-r4-review-2026-11-22.md` (`0e6d23e4`; `REWORK REQUIRED`: 0 Blocking, 2 Major, 11 Minor, 8 Info) |
| Not authorized | WP9.5 code, WP9.6, WP9.7, live operations L-0 to L-5 (including L-0b and L-1), creating or binding the real control store, registering or observing any real file, or any write to a legacy file, `main`, or the vault (`03-decisions-and-open-questions.md:6127-6135`) |
| Verification scope | **What was checked and how:** cited repository ranges were read at `dbd54fe382e7b2849d3f2038393cbdb4d709477b`; §21.1 verified the 22-commit walk, `CONVENTIONS.md` counts (70/90 units), ruleset `20822054` pins, bare-clone timings, the 15-module stdlib-only closure (0 non-stdlib imports), isolated `python -S -P` execution (`PYTHONPATH` + `PYTHONSAFEPATH=1`, script and `-m` forms, `ModuleNotFoundError` for out-of-closure/third-party modules), and 6-call Option C1 walk benchmarks (`14.05s`/`24.04s` at 60 commits, `34.46s`/`68.92s` at 178, `62.84s`/`125.68s` at 320). Prior reviews independently reproduced R2's walk/counts/ruleset/clone checks (`wp9-5-note-r2-review-2026-11-21.md` §2, §5, `:218`; not AST closure), R3's 22 rows, 15-module closure, counts, live ruleset, YAML/`bash -n`, and synthetic U-4 (`wp9-5-note-r3-review-2026-11-21.md` §2, §6, `R3-i4`), and R4's §21.1 checks, isolation, pin-step scratch runs, and 610 citations (`wp9-5-note-r4-review-2026-11-22.md` §2, §6, `R4-i7`).<br>**NOT verified here:** live U-4 metadata read (`2026-11-21T21:06:44Z`) was recorded earlier (§4.3.3); this session did not run the CI `GITHUB_TOKEN` U-3 probe (`UNVERIFIED-1`), live vault U-4 dry run (`UNVERIFIED-2`), single scratch-store M-6/O-13 test timing or weekly operator D-5 run (`UNVERIFIED-3`), GitHub repository variable write permissions under I3 (`UNVERIFIED-4`), or hosted `windows-latest` full-walk `1x`/`2x` wall time (`UNVERIFIED-5`) (§15.1, §21.2). |

---

## 1. What this note settles

WP9.5 builds the W9 detectors (`06v:470-503`; `W9` §4.4, `09-migration-compatibility-and-pilot.md:191-202`), specifying inputs, decision rules, outputs, closed `ERROR:` failures, execution lanes, negative controls, and tests. Each rule is specified once in its owning section below:

| Handover §3 item | Owning sections | Summary |
|---|---|---|
| 1. Scope & protected identities | §2, §3 | No D-4 trigger (§2.2); separates `tools/` readers from Owner Point changes under `research_system/legacy/` and WP9.4 test fixtures (§2.3). |
| 2. Ruleset read (`main_ruleset`) | §4.1 | Pins ruleset `20822054` and `rule-suites` history (`MAX_DAYS = 30`), outputting canonical `w9-main-ruleset-read/1` SHA-256. |
| 3. U-3 probe & D-8 fallback | §4.2, §15.1 | Pre-code draft-PR `pull_request` probe of `GITHUB_TOKEN` and pinned keys; `rule-suites` failure triggers hash-bound D-8 fallback. |
| 4. First-parent detector | §6, §10.2, §16.1–16.2 | Content-pinned `python -S -P` execution over 22 stdlib-only blobs (`detector_closure_blobs`); time-indexed Rules 0–3; PR-time blob/row/verdict comparison in `admission-controls` (`L1_LIVE`), single `1x` post-merge walk, and `600s` stop rule. |
| 5. Registration manifest (M-6) | §5, §16.3 | `tools/export_w9_registration_manifest.py` exports `w9-registration-manifest/2` (Option A1) from `_legacy_projection` / `_legacy_current_binding`; `--check` verifies store equality at `git_head` (unpinned residual `HR-7`). |
| 6. Shared-surface rule (`O-32`, Rule 3) | §6.2.2, §6.5, §16.5 | In-commit §4.3 record + `w9-shared-surface-changes/2` (Option D3 blob-keyed freshness); Rule 3 acknowledgements also require `independent_review`, non-empty `affected_registrations` / `"none derived"`, and `pr_number: null` when unmapped. |
| 7. `CONVENTIONS.md` check | §7, §16.10–16.11 | Segments baseline `4620c716` vs candidate via `conventions_unit`; 68-unit provisional partition or pinned L-0b classification (`ACCEPTED_CONVENTIONS_CLASSIFICATION`); bullet/paragraph insertions only; PR-lane choice (Owner Point K). |
| 8. Vault Computational-Log & D-5 | §8, §16.6, §16.10 | `tools/check_legacy_log_baseline.py` verifies live entries against accepted `w9-cl-export/1` + 1-based `w9-cl-classified-list/1` (`void == False` required); D-5 cadence gated at `LR-003`/`LR-015`/`LR-016`/`LR-020`. |
| 9. U-4 vault path & dry run | §4.3, §15.1 | Records `2026-11-21T21:06:44Z` metadata (`833,453` B) and pre-code `u4_dry_run.py` (`root_checks` + `handle_bound_read` + `segment`). |
| 10. Detector controls | §9 | `tools/run_w9_detector_controls.py` binds tool blobs + `closure_blobs` map under isolated `CONTROL_GIT_ENV` (`--code-root` / `--repo-root` split). |
| 11. Merging is not going live | §10, §16.1, §16.7 | `workflow_dispatch`-only commit until L-1; confined `python -S -P` assembly; `L1_LIVE = False` tripwire (`yaml.BaseLoader`) in `admission-controls` + CODEOWNERS; separate throwaway rehearsal + green L-1 `workflow_dispatch`. |
| 12. Scratch clones & isolation | §11 | Bare local scratch clones (`~1.71–1.99s`); `W9-T7` in `tests/tools/test_w9_detectors.py` (departure from `06v:230`); `REPO_ROOT` checkout-local snapshot (`--git-common-dir` `config`/`hooks/` in CI only). |
| 13. Tests & budget | §12, §16.7–16.8 | Unit PR checks (`W9-T19`, `W9-T7`, stdlib/CODEOWNERS/pin tests), integration `M-6`/`O-13` (`affected_research_tests.py` + nightly), `14.05s`–`125.68s` walk benchmarks, unconditional scratch-store profile (`§15.1`), G1 `300s` baseline. |
| 14. Assurance & claims | §13, §14 | Machine-checkable claims (`MC-1`–`MC-10`), human-review limits (`HR-1`–`HR-7`), and 16 claims for adversarial review. |
| 15. Stop rules & Owner points | §15, §16 | Pre-code gates (`UNVERIFIED-1`–`5`), runtime stop rules (`600s` walk cap), and 11 Owner Points (**I**, then **C, A, B, D, E, F, G, H, J, K**). |
| 16. Change logs & verification | §17–§21 | Revision history (§17), compact R1–R3 index (§18), R3->R4 log (§19), R4->R5 log (§20), and reproducible Verification appendix (§21). |

---

## 2. Scope, package boundary, and protected identities

### 2.1 Deliverables in WP9.5

Under `06v` §5 (`06v-w9-implementation-plan.md:470-503`) and `P-089` (`03-decisions-and-open-questions.md:6091-6118,6141-6143`), WP9.5 delivers:

1. **The registration manifest exporter and store-equality verifier (M-6, `06v:470-473`):**
   - `tools/export_w9_registration_manifest.py` (**new**): calls `_legacy_projection` (`research_system/cli.py:1648-1659`) and `_legacy_current_binding` (`research_system/cli.py:1662-1684`) read-only to export `.research-system/evidence/w9/registration-manifest.json` (`w9-registration-manifest/2` under Option A1, updating `research_system/legacy/evidence.py:37,40,114-131`) and, in `--check` mode, verifies 1:1 set equality between the store's `state["records"]["legacy_path_registration"]` mapping (`research_system/legacy/replay/reducers.py:70,571`) and the committed manifest at `binding.binding["git_head"]` (`research_system/cli.py:1714`).
2. **The post-merge first-parent detector and workflow (`W9-D5`, `O-9`, `O-10`, `O-32`, `06v:189-190,212,474-490`):**
   - `tools/check_legacy_writes.py` (**new**): walks `git --no-replace-objects rev-list --first-parent --reverse <walk_start>..<head>` once per post-merge run with `baselines[-1]`, checks **Rule 0** (evidence, 22-blob closure, workflow, top-level `walk-baseline.json`, and `baselines` rows (i)–(iv)), **Rule 1**, **Rule 2**, **Rule 3** (and `acknowledged` exemptions), plus ruleset `20822054` / `rule-suites` (subject to U-3/D-8).
   - `.github/workflows/legacy-write-detector.yml` (**new**): Windows-only (`runs-on: windows-latest`) workflow committed with `on: workflow_dispatch:` only (§10); assembles `$RUNNER_TEMP/w9-detector` from `baselines[-1]["detector_closure_blobs"]` (`git cat-file blob` with path confinement) and executes directly via stdlib-only `python -S -P` (`PYTHONPATH="$DETECTOR_DIR"`, `PYTHONSAFEPATH=1` — no `pyproject.toml`, `uv.lock`, or `uv sync`).
3. **The `CONVENTIONS.md` legacy-lock check (`W9-D5`, `O-12`, `06v:192,491-492`):**
   - `tools/check_conventions_legacy_locks.py` (**new**): verifies `CONVENTIONS.md` preserves every legacy unit from baseline commit `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (blob `4620c71607ca3a06c6df3b8e96a6bddffc783960`, 33,645 bytes, SHA-256 `d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589`, pinned in `CONVENTIONS_LOCK`, `research_system/legacy/reader.py:43-49`) under `segment(data, "conventions_unit")` (`w9-segmentation/1.0.0`, `research_system/legacy/segmentation.py:429-488` and `tools/w9_segmentation.py:461-518`), reading post-L-0b reclassifications strictly from Git at `ACCEPTED_CONVENTIONS_CLASSIFICATION` (`research_system/legacy/accepted_w9.py`, **new field**, keyed on `(anchor_text, unit_hash)`).
4. **The vault Computational-Log baseline detector (`W9-D5`, `O-11`, `D-5`, `D-7`, `06v:191,493-496,567,569`):**
   - `tools/check_legacy_log_baseline.py` (**new**): rejects symlink/junction/in-repo `--vault-root`, reads `04-Methods/Computational-Log.md` via `handle_bound_read` (`research_system/legacy/reader.py:140-206`), segments via `segment(data, "computational_log_entry")`, requires `recheck_cl_export` `void == False`, and checks every legacy row against `ACCEPTED_CL_EXPORT` (`research_system/legacy/accepted_w9.py:86-88`).
5. **The detector negative-control runner and pinned operator-machine wrapper (`O-13`, `06v:193,497-502,603-604`):**
   - `tools/run_w9_detector_controls.py` (**new**): executes `recorded_read` (`main_ruleset`) and `watched_to_fail` negative controls under isolated `CONTROL_GIT_ENV`, separating `--code-root` and `--repo-root` when verifying from `$DETECTOR_DIR`, producing `.research-system/evidence/w9/detector-controls.json` (`w9-detector-controls/1`, `research_system/legacy/evidence.py:38,41,59-64,133-154`).
   - `tools/run_w9_pinned_detectors.py` (**new**): operator-machine wrapper for pre-batch and weekly runs (`06v:603-604`); verifies self-blob/origin-pinned copy, fetches and verifies `origin/main` against `git ls-remote`, checks `W9_DETECTOR_PIN` under Option I3, assembles the 22 stdlib-only blobs with path confinement, and invokes all detectors via `python -S -P` + `PYTHONSAFEPATH=1` from that assembled tree (§6.2.3).
6. **Tests (`W9-T7`, `W9-T19`, `06v:230,242,503`):**
   - `tests/tools/test_w9_detectors.py` (**new**, `unit`, running in `ci.yml` `admission-controls`): includes `W9-T19`, `W9-T7` scratch-clone replay (departing from `06v:230`'s `integration, slow` lane under Owner Point F), PR-time closure-blob/row/2-tool verdict checks when `L1_LIVE`, stdlib-only closure check, derived CODEOWNERS check, pin-assembly confinement tests, and all unit controls (§12.1).
   - `tests/research_system/integration/test_w9_wp9_5_detectors.py` (**new**, `slow`, `integration`): covers scratch-store `M-6` and `O-13` end-to-end control generation (§12.1).

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
   `P-089` states (`:6141-6143`):
   > *"Boundary: WP9.5's tools under `tools/`, its workflow under `.github/workflows/`, the writers for its formats in the W9 evidence area, its tests and its docs. Nothing under `research_system/legacy/` changes except a reader WP9.5 needs, and the note names it."*
   And item 3 (`:6110-6112`):
   > *"the evidence-area formats WP9.3 fixed: the registration manifest, the detector control-output hashes and the shared-surface change list (P-081 item 4, D). WP9.5 writes to them unchanged, or the note names any change for an owner decision"*

   To keep `research_system/legacy/` as untouched as possible:
   - **All detector-only readers and closure helpers live in `tools/`** (inside the detector scripts or shared helper `tools/_w9_detector_evidence.py`, **new**), NOT in `research_system/legacy/`:
     - `load_registration_manifest_at(repo_root, commit)` (**new**, in `tools/_w9_detector_evidence.py`): reads `<commit>:.research-system/evidence/w9/registration-manifest.json` via `git --no-replace-objects show` and returns the validated list of registration dicts (whereas `evidence.require_registered(manifest, registration)` in `research_system/legacy/evidence.py:114-131` checks membership of a single registration for `LR-015`).
     - `load_shared_surface_changes_at(repo_root, commit)` (**new**, in `tools/_w9_detector_evidence.py`): reads `<commit>:.research-system/evidence/w9/shared-surface-changes.json` and returns the validated entries list (whereas `evidence.require_change_list(repo_root, git_head, declared)` in `research_system/legacy/evidence.py:190-218` requires an acceptance record's `enforcement_change_list` `{git_commit, git_blob}` ref).
     - `load_legacy_write_records_at(repo_root, commit)` (**new**, in `tools/_w9_detector_evidence.py`): reads and validates `<commit>:.research-system/evidence/w9/legacy-write-records.json` (`w9-legacy-write-records/1`, Owner Point B).
     - `load_walk_baseline_at(repo_root, commit)` (**new**, in `tools/_w9_detector_evidence.py`): reads and validates `<commit>:.research-system/evidence/w9/walk-baseline.json` (`w9-walk-baseline/1`, §6.2, Owner Point C).
     - `compute_detector_import_closure(repo_root, entry_scripts)` (**new**, in `tools/_w9_detector_evidence.py`): runs an AST walk over the **6** runtime `tools/` scripts (`check_legacy_writes.py`, `check_conventions_legacy_locks.py`, `check_legacy_log_baseline.py`, `run_w9_detector_controls.py`, `run_w9_pinned_detectors.py`, `_w9_detector_evidence.py`) transitively across `research_system` and `tools` to derive the exact **21**-module stdlib-only runtime closure (`6` new `tools/` files + `15` existing repository modules at `dbd54fe38`), which plus `.github/workflows/legacy-write-detector.yml` forms the **22**-entry `detector_closure_blobs` map (§6.2.3). (`tools/export_w9_registration_manifest.py` runs on the operator machine against `C:/Users/steph/TDL-ARS-G7-Control`, imports `research_system/cli.py`'s 161-module closure, never runs from `$DETECTOR_DIR`, is excluded from `detector_closure_blobs`, remains CODEOWNED under I1, and is recorded as residual `HR-7` in §13.2; `pyproject.toml` and `uv.lock` are also excluded because all runtime modules use only the standard library.)
     - `read_real_vault_log(vault_root, repository_root)` (**new**, in `tools/check_legacy_log_baseline.py`): performs the root-level symlink/junction refusal (`vault_root.is_symlink() or vault_root.is_junction()`) and post-`resolve(strict=True)` containment check against `repository_root.resolve(strict=True)` before calling `handle_bound_read(vault_root, "04-Methods/Computational-Log.md")` (§4.3.2).
   - **What touches `research_system/legacy/` (and existing WP9.4 tests) only if Stephen selects the corresponding Owner Point in §16:**
     - **Owner Point A (Option A1, Recommended):** Bumps `REGISTRATION_MANIFEST_FORMAT` to `"w9-registration-manifest/2"` in `research_system/legacy/evidence.py:40,114-131` (`require_registered`), closes each entry on 5 keys (`{"root_kind", "root_id", "normalized_path", "role", "source_identity_kind"}`), checks `(role, source_identity_kind)`, and compares membership at `:129` on the 3 identity keys. Touches WP9.3 `LR-015` gate and fixture builders in `tests/research_system/unit/test_w9_evidence.py`, `tests/research_system/integration/w9_runtime_harness.py:451-466`, `test_w9_wp9_4_1_runtime.py:95-109`, and `test_w9_wp9_4_2_runtime.py:86-100`, requiring a **dated WP9.3 amendment, independent review, and `P-090` entry**. No WP9.4 production code changes; note `docs/plans/agentic-research-system/transition/w9/wp9-4-1-record.md:114,130` cites `test_w9_wp9_4_1_runtime.py` pass counts (`13 passed`, `688.11s`) as acceptance evidence—whether WP9.4's recorded pass counts are re-recorded (counting against Owner Point G) is left to Stephen in §16.3. (Option A2 avoids touching WP9.3 or WP9.4 files.)
     - **Owner Point D (Option D3 Recommended, or D1):** Modifies `research_system/legacy/evidence.py:42,221-252` (`SHARED_SURFACE_CHANGES_FORMAT = "w9-shared-surface-changes/2"`, `_change_entries`) and `research_system/legacy/acceptance.py:121-136` (`check_change_list`) via a **dated WP9.3 amendment, independent review, and `P-090` entry**.
     - **Owner Point E (Option E1 Recommended):** Adds `VAULT_DETECTOR_RUNS` and `require_vault_detector_cadence` in `research_system/legacy/evidence.py` and hooks `LR-003` (`preparers.py:686-690`), `LR-015` (`preparers.py:1215-1218`), and `LR-016`/`LR-020` (`acceptance.py:147-152`) via a **dated WP9.3 amendment and independent review**.
     - **Owner Point J (Option J1 Recommended):** Adds `ACCEPTED_CONVENTIONS_CLASSIFICATION: tuple[MappingProxyType[str, Any], ...] = ()` in `research_system/legacy/accepted_w9.py` (`:86-88` pattern, leaf module outside `IMPORTER_MODULES`, no D-4 trigger).

2. **`.github/CODEOWNERS`, `GATE_FILES`, and `test_ci_platform_policy.py` boundary (`.github/CODEOWNERS:1-24`; `tests/tools/test_ci_platform_policy.py:341-375`; `CONVENTIONS.md:713-729`):**
   - `.github/CODEOWNERS` currently lists **exactly eight paths**, all owned by `@stephendor` (`.github/CODEOWNERS:14-24`; `GATE_FILES` in `tests/tools/test_ci_platform_policy.py:341-350`): `/.github/CODEOWNERS`, `/.github/merge-admission.yml`, `/.github/workflows/merge-admission.yml`, `/.github/workflows/merge-admission-sweep.yml`, `/.github/workflows/ci.yml`, `/tools/check_merge_admission.py`, `/.claude/hooks/admin-bypass-guard.sh`, and `/.claude/settings.json`.
   - `test_every_gate_file_exists_and_has_a_code_owner` (`test_ci_platform_policy.py:364-369`) asserts `.is_file()` on every `GATE_FILES` entry and `rules.get(f"/{path}")`; `test_codeowners_names_no_file_outside_the_gate` (`:372-374`) asserts exact set equality; `.github/CODEOWNERS:1-12` and `CONVENTIONS.md:713-729` (inside successor section `## ARS Foundation Governance`, `614-783`) limit CODEOWNERS to merge-admission gate files. Extending CODEOWNERS under **Owner Point I1** to the 10 file patterns (`legacy-write-detector.yml`, 7 `tools/` scripts/wrappers/exporters, `test_w9_detectors.py`, `accepted_w9.py`) plus `/.research-system/evidence/w9/` requires the edits and derived-closure test detailed in §16.1.
   - `tests/tools/test_ci_platform_policy.py` and `tools/check_test_commit_literals.py` are not in `.github/CODEOWNERS` or `GATE_FILES`.
   - Under `test_ci_platform_policy.py:286-303`, `tests/tools/test_w9_detectors.py` is wired into `.github/workflows/ci.yml` `admission-controls` (`:166-216`) and `ADMISSION_CONTROL_MODULES` (`:175-229`) alongside `test_w9_segmentation.py` (`ci.yml:210`; `test_ci_platform_policy.py:226`). Because `.github/workflows/ci.yml` is in `.github/CODEOWNERS:18` and `.claude/hooks/admin-bypass-guard.sh:13-18,67-68` forbids agent bypass merges, **Stephen merges PRs editing `ci.yml`, `CODEOWNERS`, or I1 paths himself** (§16.1, §16.7).

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

- **Authority and purpose:** `W9` §4.4 (`09-migration-compatibility-and-pilot.md:195,201-202`), `06v` §3 row `O-10` (`06v-w9-implementation-plan.md:190`), `06v` §7 L-1 and batch checklist (`06v:594,603`), and `REQUIRED_DETECTOR_CONTROLS["main_ruleset"] == "recorded_read"` (`research_system/legacy/evidence.py:59-64`).
- **What it reads (verified live on 2026-11-21 via read-only `gh api` GET; Appendix A §21.1):**
  1. **Ruleset configuration endpoint:**
     `gh api repos/ZK-Theory/TDL/rulesets/20822054` (HTTP `GET`, permitted by `.claude/hooks/admin-bypass-guard.sh:18,96-106`).
     The reader verifies the exact invariants observed on the live ruleset (`01-current-system-evidence.md:409`; Appendix A §21.1):
     - `id == 20822054`, `name == "P-049 Gate 6 main merge admission"`, `target == "branch"`, `enforcement == "active"`;
     - `conditions.ref_name.include == ["refs/heads/main"]` and `conditions.ref_name.exclude == []`;
     - `bypass_actors` is `[{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}]` (repository admin, pull-request bypass mode only);
     - `rules` contains all four required rule objects with their load-bearing parameters:
       - `type == "pull_request"`:
         - `parameters.require_code_owner_review is True`;
         - `parameters.required_approving_review_count == 0`;
         - `parameters.required_review_thread_resolution is True`;
         - `parameters.allowed_merge_methods == ["squash"]` (pins the squash-only PR merge assumption in `06v:90-91`);
       - `type == "merge_queue"`:
         - `parameters.merge_method == "SQUASH"`;
         - `parameters.max_entries_to_build == 1`, `parameters.min_entries_to_merge == 1`, `parameters.max_entries_to_merge == 1` (pins the one-entry-at-a-time merge-queue assumption in `06v:90-91` and `evaluate_merge_group_size` in `tools/check_merge_admission.py:700-737`);
       - `type == "required_status_checks"`:
         - `parameters.strict_required_status_checks_policy is True`;
         - `parameters.required_status_checks` contains all four `{context, integration_id}` pairs verified on the live ruleset (`{"context": "admission-controls", "integration_id": 15368}`, `{"context": "contract-and-session-currency", "integration_id": 15368}`, `{"context": "merge-admission", "integration_id": 15368}`, `{"context": "require-active-currency-workflow", "integration_id": 15368}`, pinning both context names and GitHub Actions app `integration_id == 15368`);
       - `type == "non_fast_forward"`.
     - *(Unpinned parameters note, `R2-i3`:)* The live ruleset also carries additional parameters not pinned as invariants (`require_extra_approval_for_unattributed_changes: true`, merge-queue `grouping_strategy: "ALLGREEN"`, `check_response_timeout_minutes: 20`, and `dismiss_stale_reviews_on_push: false`), left unpinned so routine queue tuning does not trigger false drift.
  2. **Rule-suites evaluation history endpoint:**
     `gh api --paginate --slurp "repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=month&per_page=100"` (HTTP `GET`, matching `tools/check_bypass_merges.py:141-166`).
     - **30-day API window limit and fail-closed freshness requirement (`tools/check_bypass_merges.py:24,57-58,73-90`):**
       GitHub's `rulesets/rule-suites` endpoint accepts `time_period` values `"hour"`, `"day"`, `"week"`, and `"month"` (`MAX_DAYS = 30`, `tools/check_bypass_merges.py:57-58`). A gap longer than 30 days between recorded reads would make bypass evaluations older than 30 days invisible to the API.
       Therefore, if a prior `"main_ruleset"` entry exists in `.research-system/evidence/w9/detector-controls.json` and `now - previous_recorded_at > timedelta(days=30)`, the ruleset reader **fails closed** (exit `1`) with:
       `ERROR: main_ruleset: previous recorded read is older than 30 days (<previous_recorded_at>); rule-suites API window (MAX_DAYS=30) cannot cover the gap without a recorded P-0xx acknowledgement in walk-baseline.json`
       To recover cleanly after a >30-day inactivity window without bricking future pre-batch reads (`R2-m9`, `R3-m11`), the operator passes `--acknowledge-gap <P-0xx>`, which succeeds **only** if `.research-system/evidence/w9/walk-baseline.json` at `<head>` already carries a matching append-only `ruleset_gap_acknowledgements` row (closed schema `{"previous_recorded_at", "acknowledged_through", "disposition_ref": {"id", "source_path", "source_commit", "entry_sha256"}}`) whose `disposition_ref` passes the pre-existing (`source_commit` ancestor of `P1`) hash-bound check under Rule 0 item 2 (§6.5) and whose `### P-0xx` slice names both `<previous_recorded_at>` and `<acknowledged_through>` (`acknowledged_through >= now - timedelta(days=30)`).
     - **How `result == "bypass"` entries are evaluated:**
       On 2026-11-21 at `dbd54fe38`, the live `time_period=month` query returned 57 evaluations on `refs/heads/main`: 33 `"bypass"` and 24 `"pass"`, with newest `after_sha == "dbd54fe382e7b2849d3f2038393cbdb4d709477b"` (`result: "bypass"`, `actor_name: "stephendor"`, `pushed_at: "2026-11-21T20:20:44+00:00"`). (After `#448` `4ca375a3` merged later on 2026-11-21, the month count moved to 58 with 34 `bypass`; `wp9-5-note-r2-review-2026-11-21.md:126`.) Merges performed by the repository owner (including merges touching `CODEOWNERS` or admin merges) are routinely recorded by GitHub as `result: "bypass"`.
       Accordingly, `result == "bypass"` is **not** by itself a failure. Instead, for every evaluation entry in the window on `refs/heads/main`:
       1. If `after_sha` is an ancestor of `<head>` after `<baseline>`, `tools/check_legacy_writes.py` verifies that `after_sha` satisfies Rules 0, 1, 2, and 3 (so any bypass commit that touched a guarded W9 path without a valid in-commit W9 §4.2 / §4.3 record fails closed).
       2. Every `result == "bypass"` entry in the window is recorded in the `"w9-main-ruleset-read/1"` report with `{after_sha, pushed_at, actor_name, touched_guarded_paths}`.
- **With which token:**
  - On the operator machine (at L-1 and before every batch on the `06v:603` batch checklist), it uses Stephen's authenticated `gh` CLI token (invoked via `tools/run_w9_pinned_detectors.py`, `R3-m2`).
  - In CI (`.github/workflows/legacy-write-detector.yml`), token capability is governed by U-3 and D-8 (§4.2).
- **How the read is recorded and when:**
  - **When:** At L-1 (before the first path registration `LR-003`, which checks `require_detector_controls` in `prepare_proposal`, `research_system/legacy/preparers.py:686-690`) and before every batch (`06v:603`).
  - **Operational cost (`R2-m9`, `R3-m9 (c)`):** Because `research_system/legacy/evidence.py:92-105` reads `.research-system/evidence/w9/detector-controls.json` from Git at `binding.binding["git_head"]`, each pre-batch ruleset read that updates `detector-controls.json` requires a **reviewed PR to `main`** (Stephen's bypass merge under Owner Point I1, with a `Bypass reason:` line in the PR body per `tools/check_bypass_merges.py:41,135`) plus `ars store advance-binding` before store commands run against the updated read.
  - **How recorded:** The reader constructs the report object:
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
      "bypass_actors": [
        {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}
      ],
      "rule_suites_ref": "refs/heads/main",
      "rule_suites_time_period": "month",
      "rule_suites_checked_count": 57,
      "rule_suites_bypass_count": 33,
      "unrecorded_legacy_bypass_commits": []
    }
    ```
    It hashes the report with `sha256_hex(canonical_bytes(report))` from `research_system/canonical.py:40-52` (compact P0 canonical JSON, `sort_keys=True`, `separators=(',', ':')`, ASCII keys, no floats) and writes the `"main_ruleset"` entry in `.research-system/evidence/w9/detector-controls.json` with `"control": "recorded_read"`, `"output_sha256": <64-hex>`, and `"recorded_at": <UTC ISO-8601Z>` (§9).
- **How it fails (closed):**
  - Exits `1` (or `2` on `gh api` transport/HTTP error) and refuses to write or update `detector-controls.json` if:
    - `gh api` fails or returns non-JSON (`ERROR: main_ruleset: failed to read rulesets/20822054`);
    - any pinned ruleset invariant above has drifted, including `integration_id` (`ERROR: main_ruleset: ruleset 20822054 configuration drift: <detail>`);
    - the previous recorded read is older than 30 days without an accepted `ruleset_gap_acknowledgements` entry (`ERROR: main_ruleset: previous recorded read is older than 30 days`); or
    - `rulesets/rule-suites` contains any bypass commit that violated Rules 0–3 (`ERROR: main_ruleset: bypass evaluation on refs/heads/main touched guarded path without §4.2 record: <after_sha>`).
- **Negative and positive controls (`R1-m2`, `R2-m9`, `R3-m11`):**
  - Control kind: `recorded_read` (`research_system/legacy/evidence.py:60`; `W9:195`).
  - Unit tests in `tests/tools/test_w9_detectors.py` pass synthetic ruleset and rule-suite payloads to the validator and assert that: (a) `enforcement: "disabled"`, (b) `allowed_merge_methods: ["merge", "squash"]`, (c) `max_entries_to_merge: 2`, (d) missing `require_code_owner_review`, missing required status check context, or changed `integration_id`, (e) an added bypass actor, (f) a >30-day gap since the previous read without a matching hash-bound `ruleset_gap_acknowledgements` row (or with an unhashed/mismatched row), and (g) a `result: "bypass"` evaluation on an unrecorded guarded write each exit `1` with the exact `ERROR: main_ruleset:` message; and **positively** assert that `--acknowledge-gap <P-0xx>` backed by a valid hash-bound `ruleset_gap_acknowledgements` row exits `0` (`R3-m11`).

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
   - `.github/workflows/merge-admission.yml`: top-level `permissions: contents: read, pull-requests: read, checks: read` (`merge-admission.yml:52-55`); job `merge-admission` declares `checks: read, actions: read, contents: write, pull-requests: write` (`:70-83`).
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

### 6.1 Time-indexed evidence evaluation, trust-root boundary, and why reading at `<head>` alone is broken

**Trust-root boundary:** There is no trust root inside repository content that can stop a merged commit from changing the detector scripts, imported `research_system/` helpers, or `.github/workflows/legacy-write-detector.yml` on `main` (GitHub runs workflows from the pushed commit, and ZK-Theory is on GitHub Free without org-level required workflows; `CONVENTIONS.md:721-725`). Against detector, evidence, or trigger tampering, enforcement splits cleanly:
- **Preventive at merge admission (Owner Point I1 + `admission-controls` when `L1_LIVE`):** `.github/CODEOWNERS` (`@stephendor`) protects all 10 CODEOWNED file patterns (`legacy-write-detector.yml`, 7 WP9.5 `tools/` files, `tests/tools/test_w9_detectors.py`, `research_system/legacy/accepted_w9.py`) plus directory pattern `/.research-system/evidence/w9/` (optionally paired with out-of-tree `vars.W9_DETECTOR_PIN` under **Option I3**). Additionally, in `.github/workflows/ci.yml`'s required `admission-controls` job (which runs on PRs and `merge_group`, `ci.yml:12,135`), once `L1_LIVE is True`, `test_w9_detectors.py` verifies `HEAD` blob equality across all 22 `detector_closure_blobs` paths, Rule 0.2 (i)–(iv) on added/initial rows, and the one-shot 2-tool verdict comparison on closure changes (§6.2.2)—blocking unrowed closure edits except by bypass or direct push.
- **Detective post-merge backstop:** The remaining **13** `research_system/` closure modules plus `tools/w9_segmentation.py` (**14** non-code-owned existing closure modules total; `accepted_w9.py` is the 14th `research_system/` module and IS code-owned under I1) are not in CODEOWNERS under I1-default; Rule 0.3 detects any unrowed bypass or direct-push edit post-merge. Whether an unrowed Rule 0.3 miss gets a narrow hash-bound exemption row or stays permanently red (`HR-3`) is put to Stephen in **§16.2 Owner Point C**. **Option I2 fails to close R1-B1 scenarios 4–5** (§16.1).

Subject to that trust root, single-snapshot evaluation at `<head>` fails via atomic disarm, retroactive false positives, retroactive blessing, and detector self-edits; Revision 5 fixes these as follows:

| Evidence / artifact | Evaluated at / how | Why |
|---|---|---|
| `registration-manifest.json` (Rules 1 and 3) | **`P1` union `C`** ($\text{Manifest}(P_1) \cup \text{Manifest}(C)$) | Prevents atomic disarm in `C` and retroactive false positives on pre-registration commits. |
| `legacy-write-records.json` (Rules 1, 2, 3) | **Commit `C`** | PR must carry its own record at `C` (`06v:212,479-481`); prevents retroactive blessing after `C`. |
| `shared-surface-changes.json` (Rule 3) | **Commit `C`** (or `<head>` with late-entry Rule 3 `acknowledged`, §6.2.2) | In-PR reporting at `C`; late recovery still binds WP9.3 `check_change_list` (`evidence.py:190-218`, `acceptance.py:121-136`). |
| Monotonicity & row validation (**Rule 0**) | **Every `P1 -> C` in `(b0, head]` + PR `admission-controls`** | Evidence ledgers & `walk-baseline.json` top-level keys monotonic; `baselines[0]` and `baselines[k]` validated (i)–(iv); PR lane runs one-shot 2-tool verdict comparison on closure edits (§6.2.2). |
| Detector code & 22-blob closure | **Confined `git cat-file blob` assembly + `python -S -P`** | Both CI (§10.2) and local wrapper (§6.2.3) write only `baselines[-1]["detector_closure_blobs"]` (22 stdlib-only blobs, path-confined) and run `python -S -P` with `PYTHONPATH="$DETECTOR_DIR"` + `PYTHONSAFEPATH=1` (no checkout/site-packages leakage; one `1x` post-merge walk). |

---

### 6.2 The walk baseline (`walk-baseline.json`), acknowledged violations, PR-time pin-advance check, import closure, and pre-baseline summary

#### 6.2.1 Summary of first-parent commits touching guarded prefixes between `4b143c92` and `dbd54fe3`

Running `git --no-replace-objects rev-list --first-parent --reverse 4b143c9225035cc29e37351445f1c3a4ab09ceb1..dbd54fe382e7b2849d3f2038393cbdb4d709477b` yields **320** first-parent commits on `main`, of which **22** touched `CONVENTIONS.md`, `results/`, `papers/`, `contracts/`, or `.apm/` (§21.1 item 3, reproduced in `wp9-5-note-r2-review-2026-11-21.md:137-148` and `wp9-5-note-r3-review-2026-11-21.md:107-117`):
- **9 `CONVENTIONS.md`-only pure-successor PRs:** `#172` (`7347ae95`), `#178` (`9795ee5f`), `#183` (`f52f52f4`), `#278` (`85c7a02e`), `#345` (`65f4da4b`), `#376` (`3a14a97c`), `#384` (`53b7c5be`), `#419` (`14a81b84`, `CONVENTIONS.md` `baceabd6 -> 14d39755`), and `#425` (`1fba78aa`, `14d39755 -> 1db03819`);
- **1 mixed PR:** `#277` (`1dbf6b7b`, Ruff cleanup on 3 `papers/` scripts + `CONVENTIONS.md`);
- **3 `.apm/tracker.md` Working-Note PRs:** `#368` (`452352ff`, `8101faa5 -> c2716092`, 06s Phase 5 batches), `#388` (`e3519ba7`), and `#433` (`a6a98966`);
- **3 ARS contract PRs:** `#168` (`9016b663`), `#169` (`2111ce62`), and `#334` (`eba3fe69`);
- **3 pre-W9 / ruled / reviewed results PRs:** `#125` (`02ebcaf6`, MCBIF `results/poverty_tda_mcbif/`), `#129` (`5795a18b`, `p2=1af52f6d` H6 ruling), and `#401` (`633ed58e`, `results/trajectory_tda_integration/stage1/SUPERSEDED.md` Markov-2);
- **2 unauthorized direct pushes (`W9-T7` replay subjects):** `5df0c001` (`2026-08-05T05:32:38+01:00`, `p1=a426b731`, touching 7 `results/` + 4 non-`results/` files) and `811d5a2b` (`2026-08-07T00:12:09+01:00`, `p1=1d3a0769`, touching 3 `contracts/manifests/input-provenance/` + 6 other files); and
- **1 revert PR:** `#219` (`b132406e`, `p1=811d5a2b`, `p2=3bfb279c`, restoring all 10 `results/` and `contracts/` files from `5df0c001` and `811d5a2b`).

#### 6.2.2 Committed append-only walk-baseline ledger, acknowledged violations, PR-time verdict comparison, and walk cost

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
2. **Baseline, disposed vs walked intervals, and Form (A) content pin:**
   - **`baselines[0]["baseline_commit"]` fixes the original walk start** (immutable; may be any known first-parent ancestor of the L-1 commit on `main`, avoiding the unknowable queue merge parent).
   - **Pre-baseline disposed interval `(4b143c92, baselines[0]["baseline_commit"]]`:** At L-1, run §21.1 item 3 over `(dbd54fe3, baselines[0]["baseline_commit"]]` and record the disposition of every guarded commit in the L-1 `pre_baseline_dispositions_ref` decision entry (§6.2.1 covers `4b143c92..dbd54fe3`).
   - **Walked interval `(baselines[0]["baseline_commit"], head]`:** Walked once (`1x`) per post-merge run with `baselines[-1]["detector_closure_blobs"]`; every commit must pass Rules 0–3 or hold a valid `acknowledged` entry.
   - **CLI lockouts & first-parent chain check:** Passing `--baseline`, `--head`, `--pr-map`, `--manifest-file`, `--verdict-json`, or `--acknowledged-from` without `--ruleset-check skip` exits `2` (§6.3 item 4). `check_legacy_writes.py` verifies `baselines[0]["baseline_commit"]` (and every referenced `commit`/`source_commit`) appears in `git --no-replace-objects rev-list --first-parent <head>` (stronger than `merge-base --is-ancestor`).
3. **Clearable true positives: the append-only `acknowledged` list (Owner Point C):**
   - Appended row `{"commit", "rule", "path", "old_blob", "new_blob", "disposition_ref", ...}` (for `rule == "Rule 3"`, also `"independent_review"` matching §6.4 item 2):
     1. `a["commit"]` lies on `<head>`'s first-parent chain strictly after `baselines[0]["baseline_commit"]`.
     2. `a["disposition_ref"]["source_commit"]` satisfies `commit < source_commit <= P1(C_ack)` with `### <id>` slice SHA-256 matching `entry_sha256` at `P1(C_ack)` and naming `commit[:8]`, `rule`, `path`, `old_blob[:8]`, and `new_blob[:8]`.
     3. Scope: exempts only `(commit, rule, path, old_blob, new_blob)`.
     4. **Rule 3 late change-list entry and independent-review requirement:** When `a["rule"] == "Rule 3"`, `a` must also carry `"independent_review"` verified at `P1(C_ack)` per §6.4 item 2 (satisfying `W9` §4.3, `09-migration-compatibility-and-pilot.md:183-188`), **and** `<head>:.research-system/evidence/w9/shared-surface-changes.json` must hold a matching entry `(pr_number_or_null, a["path"], a["old_blob"], a["new_blob"], affected_registrations)` where:
        - `affected_registrations` is **non-empty**, unless `"none derived"` is explicitly stated in **both** the `### P-0xx` slice and `independent_review` (`evidence.py:221-252` permits `[]` structurally, so the detector enforces non-emptiness unless derived);
        - `"pr_number"` equals `pr_number(a["commit"])` for PR merges, or `null` **strictly** for an acknowledgement-backed entry whose `a["commit"]` has `pr_number == None` (direct push; ordinary in-commit Rule 3 PR entries still forbid `null`);
        - *Why late entries work cleanly against WP9.3:* `check_change_list` calls `require_change_list` (`research_system/legacy/evidence.py:190-218`; `acceptance.py:121-136`), which requires the acceptance's declared `git_blob` to equal `shared-surface-changes.json` at `git_head` and `git_commit` to be an ancestor holding it. Thus every acceptance evaluated at or after the late entry's `git_head` enforces it, stale declarations are refused, and previously committed acceptances retain their verdict.
4. **PR-time pin-advance check + verdict comparison (`admission-controls`), single post-merge walk (`1x`), cost, and stop rule (Owner Points C and F):**
   - **Post-merge walk (`1x`):** Both `.github/workflows/legacy-write-detector.yml` and `tools/run_w9_pinned_detectors.py` assemble only `baselines[-1]["detector_closure_blobs"]` and execute **one** walk over `(baselines[0]["baseline_commit"], head]` (no stored verdicts; no second post-merge walk).
   - **PR-time check (`admission-controls` when `L1_LIVE is True`):** Because `ci.yml` `admission-controls` is a required status check under ruleset `20822054` and runs on both PRs and `merge_group` (`.github/workflows/ci.yml:12,135`), on the merge queue it evaluates the exact squash candidate. When `L1_LIVE is True`, `tests/tools/test_w9_detectors.py` verifies:
     1. Every path `p` in `HEAD`'s `baselines[-1]["detector_closure_blobs"]` matches `git rev-parse HEAD:<p>`. (Blocks unrowed closure edits except via bypass or direct push.)
     2. Rule 0.2 checks (i)–(iv) (§6.5) hold for every `baselines` row added since `origin/main`—**and for `baselines[0]` when `walk-baseline.json` is created**.
     3. Whenever `HEAD`'s `detector_closure_blobs` differs from `origin/main`'s `baselines[-1]["detector_closure_blobs"]`, `test_w9_detectors.py` runs a **one-shot verdict comparison** across `(baselines[0]["baseline_commit"], HEAD]` (inclusive of `HEAD`, so `origin/main`'s old tool also judges the candidate commit introducing the new tool):
        - **Verdict definition:** For commit `V` under tool `t`, verdict = `{ (rule, path) }` pairs for which `t` reports a violation at `V` after applying the `acknowledged` rows present at `origin/main`. Rule 0 is excluded from the compared verdict (preventing recursion). Any tool invocation that fails to complete (exit not in `{0, 1}`, `ImportError`, malformed JSON, timeout) is `ERROR`, never empty set.
        - **Confined invocation:** Assembles `origin/main`'s tool (`T_old`) and `HEAD`'s tool (`T_cand`) into two separate scratch directories using §6.2.3's `python -S -P` + `PYTHONSAFEPATH=1` command and invokes `check_legacy_writes.py --repo-root <repo> --ruleset-check skip --baseline <b0> --head HEAD --verdict-json --acknowledged-from <origin_main_sha>` on each (all future pin-advance versions must keep this CLI contract or document an interface change in their `### P-0xx` slice). Note: `ci.yml:139-140` gives `admission-controls` `permissions: contents: read`; if U-3 shows `commits/<sha>/pulls` requires `pull-requests: read`, Owner Point F (§16.7) adds `pull-requests: read` to `admission-controls` (meanwhile local/synthetic PR-map tests pass `--pr-map`).
        - **Slice rule:** Every commit `V` in `(b0, HEAD]` whose verdict differs between `T_old` and `T_cand` must appear in the new row's `recorded_in_decision_ref` `### P-0xx` slice with **`V[:8]` and every differing `(rule, path)` pair**; otherwise the check fails closed (`ERROR: pin_advance: verdict change at <V[:8]> <(rule, path)> not named in decision slice`).
   - **Measured cost & stop rule (§12.3, §21.1 item 10):** Using a realistic 6-subprocess stand-in over Option C1 growth horizons (including `cat-file -e` on evidence blobs at `P1` and `C`): `14.05s` (`1x`) / `24.04s` (`2x`) for 60 commits (`~1 month`, 6 guarded), `34.46s` / `68.92s` for 178 commits (`~3 months`, 12 guarded), and `62.84s` / `125.68s` for 320 commits (`~5.5 months`, 22 guarded; `~0.20s`/commit local Git plumbing; real runs add `gh api` calls on guarded commits). **Wall-time stop rule:** if any full post-merge walk or PR-time comparison exceeds **`10 minutes` (`600s`)**, stop and return to Stephen (for a verified re-baseline or Git-plumbing batching change) rather than raising timeouts. Real-rule full-walk time on `windows-latest` is `UNVERIFIED-5` (§15.1, §21.2).

#### 6.2.3 Detector import closure, stdlib-only isolation, closure cost, and operator-machine pinning

1. **Deterministic AST closure walker (`compute_detector_import_closure(repo_root, entry_scripts)` in `tools/_w9_detector_evidence.py`, **new**):**
   Walks `ast.Import` and `ast.ImportFrom` (restricted to `research_system` and `tools`) across the **6** runtime `tools/` scripts (`tools/check_legacy_writes.py`, `tools/check_conventions_legacy_locks.py`, `tools/check_legacy_log_baseline.py`, `tools/run_w9_detector_controls.py`, `tools/run_w9_pinned_detectors.py`, `tools/_w9_detector_evidence.py`). Whenever any imported module resolves under `research_system`, every ancestor package `__init__.py` (`research_system/__init__.py`, `research_system/legacy/__init__.py`, `research_system/store/__init__.py`) is included explicitly; `tools/` has no `__init__.py` and imports as a namespace package under `PYTHONPATH="$DETECTOR_DIR"`.
2. **Exact 22-blob closure (`15` existing + `6` new runtime `tools/` = `21` runtime modules + workflow):**
   At `dbd54fe38`, the 15 existing modules are `tools/w9_segmentation.py` plus the 14 `research_system/` files in `walk-baseline.json` (§6.2.2). Adding the 6 new runtime `tools/` modules (`21` runtime modules) and `.github/workflows/legacy-write-detector.yml` gives **`22` blobs** in `detector_closure_blobs`. `pyproject.toml`, `uv.lock`, and `tools/export_w9_registration_manifest.py` are **omitted** from `detector_closure_blobs` because all runtime modules use only the standard library and the M-6 exporter never runs from `$DETECTOR_DIR` (§2.3, §13.2 `HR-7`).
3. **Stdlib-only enforcement, path confinement, and exact `python -S -P` isolation command (§21.1 item 9):**
   - **Stdlib-only closure check:** All 15 existing modules have **0** third-party imports (§21.1 item 9). Unit test `test_detector_closure_is_stdlib_only` enforces that every AST import in all 21 derived runtime modules lies in `sys.stdlib_module_names | {"research_system", "tools"}`.
   - **Confined blob assembly:** Before writing any file under `$DETECTOR_DIR`, both the workflow (§10.2) and `tools/run_w9_pinned_detectors.py` validate that every key `rel_path` in `detector_closure_blobs` is a normalized relative POSIX path (`PurePosixPath(rel_path).as_posix() == rel_path`, no leading `/`, no `\`, no `..` or `.` segments), verify `git cat-file -t <blob_sha> == "blob"`, and verify `(detector_dir / rel_path).resolve().is_relative_to(detector_dir.resolve())`.
   - **Exact interpreter command (no `.venv`, no `uv sync`):** Clear `PYTHONHOME` and `VIRTUAL_ENV`, set `PYTHONPATH="$DETECTOR_DIR"` and `PYTHONSAFEPATH=1`, and execute `python -S -P "$DETECTOR_DIR/tools/<script>.py" ...` (CI uses `actions/setup-python@v5` `3.13.5`; the operator wrapper checks `sys.version_info[:3] == (3, 13, 5)`). `-I` and `-E` are **not** used because they ignore `PYTHONPATH`; `-S` strips `site-packages`/`.pth`; `-P` plus `PYTHONSAFEPATH=1` prevent cwd/script-dir leakage in both script and `-m` invocations and in child subprocesses (§21.1 item 9).
   - **Unit & CODEOWNERS checks:** `test_recorded_detector_import_closure_covers_ast_walk` checks AST completeness, and `test_derived_closure_tools_and_accepted_w9_are_codeowned` checks every derived `tools/` module and `accepted_w9.py` appears in `.github/CODEOWNERS`.
   - **Unrowed Rule 0.3 exit choice:** Under `admission-controls` (`L1_LIVE`), unrowed closure edits can only merge via bypass or direct push; Owner Point C (§16.2) puts the recovery choice (**Option C-R0-exemption** vs **Option C-R0-permanent** listed in §13.2 `HR-3`) to Stephen without pre-building an exemption.
4. **Closure operational cost & Option I1-narrow reach:**
   Of the 15 existing closure modules, `accepted_w9.py` is CODEOWNED under I1, leaving **13** `research_system/` modules + `tools/w9_segmentation.py` (**14** non-code-owned modules; 7 W9 PRs in last 4 weeks, 14 of 178 first-parent commits in 90 days, `wp9-5-note-r3-review-2026-11-21.md:44`). Any PR editing them after L-1 needs a `P1` hash-bound decision entry (`new_blob[:8]`), same-PR `baselines` append + PR-time verdict diff, re-recorded `detector-controls.json`, and `Bypass reason:` merge. **Option I1-narrow reach:** because `research_system/legacy/reader.py:37` imports `research_system.store.lock` (`lock.py:3,11` pulls in `store.anchor` and `store.writer`, plus `store.durability` = 5 `store/` modules), moving detector-only reader helpers to `tools/` cuts the 90-day count from **14 commits to 8 at most** (`evidence.py` [5 commits], `reader.py`, `segmentation.py`, `accepted_w9.py`, `export_recheck.py` remain), **or** forks the Windows handle-anchor code W9 relies on (§16.1).
5. **Operator-machine pinning (`tools/run_w9_pinned_detectors.py`):**
   Before every batch and weekly D-5 run (`06v:603-604`), Stephen runs the origin-pinned script (`git show origin/main:tools/run_w9_pinned_detectors.py`), or runs the checkout copy which first checks its own `git hash-object --path=tools/run_w9_pinned_detectors.py` blob equals `origin/main`'s `baselines[-1]["detector_closure_blobs"]` entry and refuses on mismatch. The wrapper runs `git fetch --no-tags origin main:refs/remotes/origin/main`, checks `git rev-parse refs/remotes/origin/main == git ls-remote origin refs/heads/main` (refusing stale local `origin/main`), reads `W9_DETECTOR_PIN` via authenticated `gh api repos/ZK-Theory/TDL/actions/variables/W9_DETECTOR_PIN` when Option I3 is active (`UNVERIFIED-4`), assembles the 22 confined blobs in a temp directory, and runs `check_legacy_writes.py`, `check_conventions_legacy_locks.py`, `check_legacy_log_baseline.py`, and `run_w9_detector_controls.py --code-root "$DETECTOR_DIR" --repo-root . --verify-watched-to-fail ...` via `python -S -P` + `PYTHONSAFEPATH=1`. (`tools/export_w9_registration_manifest.py` remains an unpinned operator tool in CODEOWNERS; §13.2 `HR-7`.)

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
     4. **Test-only flags hard-locked behind `--ruleset-check skip`:** `--baseline <sha>`, `--head <sha>`, `--pr-map <json>`, `--manifest-file <json>`, `--verdict-json`, and `--acknowledged-from <sha>` are test/PR-comparison overrides only. Passing any of them without `--ruleset-check skip` exits **`2`** immediately (`ERROR: post_merge_first_parent: --baseline, --head, --pr-map, --manifest-file, --verdict-json, and --acknowledged-from are permitted only with --ruleset-check skip`), and a unit test verifies none of `--baseline`, `--head`, `--pr-map`, `--manifest-file`, `--verdict-json`, `--acknowledged-from`, `--ruleset-check skip`, or `--classified-locks` appears in `.github/workflows/legacy-write-detector.yml`.

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
     (iv) for $k \ge 1$, the `recorded_in_decision_ref` `### P-0xx` slice names every path added, removed, or changed relative to `baselines[k-1]["detector_closure_blobs"]` with `new_blob[:8]` (or `"no blob change"` if identical, and `"rollback"` plus restored paths and `new_blob[:8]` if matching an earlier row). *(The one-shot 2-tool verdict comparison runs in PR `admission-controls`, §6.2.2 item 4, not inside Rule 0.2.)*
   - **Every newly appended `ruleset_gap_acknowledgements` row ($C_{\text{gap}}$):** closed keys `{"previous_recorded_at", "acknowledged_through", "disposition_ref"}`, `disposition_ref["source_commit"]` ancestor of $P_1(C_{\text{gap}})$, slice naming both `<previous_recorded_at>` and `<acknowledged_through>`.
   - **Every newly appended `acknowledged` row ($C_{\text{ack}}$):** `commit < source_commit <= P1(C_ack)` with slice verification (§6.2.2 item 3); when `rule == "Rule 3"`, also requires `independent_review` at `P1(C_ack)` plus a matching entry (non-empty `affected_registrations` or `"none derived"`, `pr_number` integer or `null` if unmapped) at `<head>:.research-system/evidence/w9/shared-surface-changes.json` (§6.2.2 item 3.4).
   - Once `ACCEPTED_CONVENTIONS_CLASSIFICATION` (`accepted_w9.py`) is populated at L-0b, its pinned classification JSON path cannot be modified or deleted.
   - Failure message: `ERROR: post_merge_first_parent: Rule 0 violation at commit <C>: evidence file '<path>' violated append-only, validation, or immutability invariants`
3. **`detector-controls.json` and the 22-path governed detector closure:**
   - Once `.research-system/evidence/w9/detector-controls.json` exists at $P_1$, it cannot be deleted at $C$, and updates pass `require_detector_controls` (`evidence.py:133-154`) with `recorded_at` timestamps $\ge$ $P_1$.
   - If $P_1 \to C$ modifies or deletes any path listed in `<P1>:walk-baseline.json["baselines"][-1]["detector_closure_blobs"]` (all 21 stdlib-only runtime modules + `.github/workflows/legacy-write-detector.yml`, §6.2.3), commit $C$ must carry an appended `baselines` row in `<C>:walk-baseline.json` in the **same commit/PR** satisfying Rule 0.2 (i)–(iv). Otherwise exit `1`:
     `ERROR: post_merge_first_parent: Rule 0 violation at commit <C>: governed detector/closure path '<path>' modified without a valid same-PR baselines append and hash-bound pre-existing decision ref in walk-baseline.json`
   *(Under `L1_LIVE`, `admission-controls` blocks unrowed closure edits pre-merge except bypass/direct push; §16.2 Owner Point C puts the Rule 0.3 exit choice to Stephen.)*

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
   - `--vault-root <path>`: required real path to the vault directory (`C:\Users\steph\Documents\TDA-Research` on the operator machine, or a `tmp_path` directory in tests). Validated per §4.3.2 (`is_symlink()`, `is_junction()`, and `resolve(strict=True)` outside `repository_root`). Reads `04-Methods/Computational-Log.md` via `handle_bound_read(resolved_vault, "04-Methods/Computational-Log.md")` (`research_system/legacy/reader.py:140-206`).
   - Baseline export and classification source (mutually exclusive):
     - **Production mode (`--repository-root <repo> --git-commit <sha>`, default `HEAD`):**
       Reads the latest accepted export mapping from `ACCEPTED_CL_EXPORT` (`research_system/legacy/accepted_w9.py:86-88`). As documented at `accepted_w9.py:86-88`, each `ACCEPTED_CL_EXPORT` entry is a mapping of three member descriptors:
       ```python
       {
           "export": {"repository_path": ..., "git_commit": ..., "git_blob": ..., "sha256": ..., "byte_length": ...},
           "retained_copy": {"repository_path": ..., "git_commit": ..., "git_blob": ..., "sha256": ..., "byte_length": ...},
           "classified_list": {"repository_path": ..., "git_commit": ..., "git_blob": ..., "sha256": ..., "byte_length": ...},
       }
       ```
       If `ACCEPTED_CL_EXPORT` is empty `()`, production mode fails closed immediately with:
       `ERROR: vault_computational_log: ACCEPTED_CL_EXPORT is empty; L-0b baseline export has not been accepted yet`
       When `ACCEPTED_CL_EXPORT` is populated at L-0b, `tools/check_legacy_log_baseline.py`:
       1. reads the committed export JSON, retained copy bytes, and classified list JSON from Git at their pinned commits/blobs (`git --no-replace-objects show <git_commit>:<repository_path>`) and verifies that each member's `git_blob_id(raw)`, `sha256_hex(raw)`, and `len(raw)` match the pinned `ACCEPTED_CL_EXPORT[-1]` entry;
       2. validates the export dict's shape with `evidence.require_cl_export(export)` (`research_system/legacy/evidence.py:277-362`, a pure shape validator taking the decoded JSON object `export: Any`);
       3. runs `report = recheck_cl_export(export, retained_raw)` (`research_system/legacy/export_recheck.py:32-89`), which raises `EvidenceRefused` on malformed export or wrong producer (`CL_EXPORT_PRODUCER`, `tools/w9_segmentation.py` at blob `43e1454de09b61e274954c42b21d6ae533857a24`, `evidence.py:52-54`) and returns a report dict with `"void": bool` (`export_recheck.py:80-89`) — **crucially, `recheck_cl_export` does NOT raise on row/hash/fact divergence**, so `tools/check_legacy_log_baseline.py` MUST check `if report["void"] is True:` and fail closed (exit `1`) with `ERROR: vault_computational_log: recheck_cl_export reported void=True` (`R2-m12`); and
       4. validates the `classified_list` JSON (§8.3; Owner Point J).
     - **Fixture mode (`--fixture-export-json <path> --fixture-retained-copy <path> [--fixture-classified-list <path>]`, for tests and pre-L-0b negative controls):**
       Reads the fixture export JSON, retained copy bytes, and classified list from disk, runs `evidence.require_cl_export(export)` (`evidence.py:277-362`), runs `report = recheck_cl_export(export, retained_raw)` (`export_recheck.py:32-89`), and fails closed (exit `1`) if `report["void"] is True` (`R2-m12`).
2. **Whole-page segmentation of the live vault file (`R1-M2`):**
   - Calls `live_seg = segment(live_raw, "computational_log_entry")` (`research_system/legacy/segmentation.py:429-488`, with `region=None` so it covers `(1, len(lines))`) and verifies agreement with `tools/w9_segmentation.py:461-518`.
   - Why `region=None` on the live file even when `export["selector"]["region"]` is a sub-range `{"first_line": first, "last_line": last}`: new successor entries are prepended near the top of `04-Methods/Computational-Log.md`, shifting the line numbers and byte offsets of every legacy entry below them (`w9-segmentation-contract-v1.md:189-192`).
3. **Exact five-part decision rule (`R1-M1`, `R1-M9`, `R1-m8`, `R2-m3`, `R2-i4`):**
   - **Check 1 — Live file BOM and zero blocker rows across the live page (`W9:197`, `R1-M1`, `R1-m8`, `R2-m3`, `R2-i4`):**
     - `live_seg["file_facts"]["has_utf8_bom"]` must be `False`.
     - **Line-ending resilience for Obsidian successor edits (`R1-m8`):** Unlike `CONVENTIONS.md` (which is tracked in Git under `.gitattributes`), `04-Methods/Computational-Log.md` is edited in the vault by Obsidian or operator tools on Windows. If a new successor entry at the top of the file is saved with CRLF while all legacy entries retain their exact LF bytes, `live_seg["file_facts"]["line_ending"]` becomes `"mixed"`, even though **zero legacy bytes changed**. Therefore, `tools/check_legacy_log_baseline.py` does **not** fail on `file_facts["line_ending"] != "LF"` alone; instead, Check 3 and Check 4 compare each legacy row's exact slice hash `raw_row_sha256` (which includes that row's line terminators, `w9-segmentation-contract-v1.md:168-169`, so any LF->CRLF change inside a legacy entry immediately changes `raw_row_sha256` and fails Check 3!).
     - **Zero blocker rows (`W9:197`, `R2-i4`, `R2-m3`):** As verified in `w9-segmentation-contract-v1.md:242,254-256`, the live `Computational-Log.md` had **0 blockers** across all 255/256 entries. For every row `r` in `live_seg["rows"]`, `r["row_kind"]` must not be `"blocker"`. *(Intentional strictness vs `W9` §4.4, `R2-i4`: this rejects duplicate and unparseable heading anchors across successor entries as well as legacy entries, because any blocker row compromises whole-page segmentation.)* If any row in `live_seg["rows"]` has `row_kind == "blocker"` (`blocker_reason` in `{"unparseable_anchor", "duplicate_anchor", "unaddressed_region"}`), fail closed immediately with:
       `ERROR: vault_computational_log: live file contains segmentation blocker at row_ordinal=<row_ordinal> (lines <start_line>-<start_line + line_count - 1>): <blocker_reason> (<anchor_text_or_none>)`
   - **Check 2 — Complete legacy/successor classification of baseline export rows (`R1-M9`; Owner Point J):**
     - Why a classification resolution rule is needed (`R1-M9`): In `research_system/legacy/evidence.py:347-360`, `require_cl_export` allows each slot in `export["classifications"]` to have `slot["class"] is None or isinstance(slot["class"], str)` (because the initial raw export at L-0b may leave `class: None` until the classified legacy-entry list is produced and accepted by Stephen under `06v:569,593`, pinned as `ACCEPTED_CL_EXPORT[-1]["classified_list"]` in `accepted_w9.py:86-88`).
     - Under **Owner Point J (§16)**, the detector resolves `class_by_ordinal` from `classified_list` (when provided/pinned, format `"w9-cl-classified-list/1"`, §8.3) or falls back to `export["classifications"]` (in self-contained fixture tests where `export["classifications"]` already carries `"legacy"` / `"successor"`).
     - Every row in `export["segmentation"]["rows"]` must have a resolved classification in `{"legacy", "successor"}` (if any baseline row is `"blocker"` or has `class is None`, fail closed with `ERROR: vault_computational_log: baseline export has unclassified or blocker row at row_ordinal=<ord>`).
   - **Check 3 — Every legacy `"item"` row is preserved byte-for-byte (`W9:197,402-403`; `w9-segmentation-contract-v1.md:189-192`; `R2-m3`):**
     - Let $L_{\text{item}}$ be the ordered list of rows in `export["segmentation"]["rows"]` with `row_kind == "item"` and `class_by_ordinal[row["row_ordinal"]] == "legacy"`.
     - Index all `"item"` rows in `live_seg["rows"]` by `anchor_text` (unique because Check 1 rejected all `duplicate_anchor` blockers).
     - For each baseline legacy item row $b \in L_{\text{item}}$:
       1. Look up `anchor = b["anchor_text"]` in the live item index. If absent, fail closed with:
          `ERROR: vault_computational_log: missing or renamed legacy heading anchor '<anchor>' (baseline row_ordinal=<row_ordinal>, raw_row_sha256=<sha>)`
       2. Let $l$ be the matching live item row. Require `l["anchor_line_sha256"] == b["anchor_line_sha256"]` and `l["raw_row_sha256"] == b["raw_row_sha256"]`. If either differs, fail closed with:
          `ERROR: vault_computational_log: byte change inside legacy entry '<anchor>' (expected raw_row_sha256=<b_sha>, got <l_sha> at live lines <l["start_line"]>-<l["start_line"] + l["line_count"] - 1>)`
   - **Check 4 — Every legacy `"structural"` row is preserved byte-for-byte (`w9-segmentation-contract-v1.md:184-188`):**
     - Let $L_{\text{struct}}$ be the ordered list of rows in `export["segmentation"]["rows"]` with `row_kind == "structural"` and `class_by_ordinal[row["row_ordinal"]] == "legacy"`.
     - For each baseline legacy structural row $b \in L_{\text{struct}}$ (identified by `anchor_line_sha256`, `w9-segmentation-contract-v1.md:186-188`):
       - Require a unique `"structural"` row $l$ in `live_seg["rows"]` with `l["anchor_line_sha256"] == b["anchor_line_sha256"]` and `l["raw_row_sha256"] == b["raw_row_sha256"]`. Otherwise fail closed with:
         `ERROR: vault_computational_log: modified or missing legacy structural block (anchor_line_sha256=<sha>)`
   - **Check 5 — Relative order of legacy rows is preserved:**
     - The matched live `row_ordinal` values for all legacy rows ($L_{\text{item}} \cup L_{\text{struct}}$, ordered by their baseline `row_ordinal`) must be strictly increasing in `live_seg["rows"]`. Otherwise fail closed with:
       `ERROR: vault_computational_log: legacy entries reordered in live file`

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
3. **CI and wrapper re-verification of `watched_to_fail` hashes after L-1:**
   Because the three `watched_to_fail` transcripts (`post_merge_first_parent`, `vault_computational_log`, `conventions_repository_check`) are deterministic functions of the repository's object database and the 21-module runtime closure's bytes, `tools/run_w9_detector_controls.py --code-root <assembled_detector_dir> --repo-root <checkout_root> --verify-watched-to-fail <extracted_detector_controls_json>` separates `--code-root` (which supplies the assembled closure bytes for `tool_git_blob` / `closure_blobs` and imports) from `--repo-root` (which must be a Git repository with object database for `git clone --bare --local` controls such as `replay_5df0c001`, `R4-m5`; `--repo-root` defaults `--code-root` to itself only when omitted in unpinned local tests). Executed via `python -S -P` in `.github/workflows/legacy-write-detector.yml` (§10.2) and `tools/run_w9_pinned_detectors.py` (§6.2.3), failing closed on any hash mismatch (`ERROR: detector_controls: recomputed output_sha256 for '<detector>' does not match detector-controls.json`). (`tools/export_w9_registration_manifest.py` sits outside the 22-blob runtime closure; §13.2 `HR-7`.)

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
              ["git", "--no-replace-objects", "rev-list", "--first-parent", main_tip], text=True
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
              obj_probe = subprocess.run(
                  ["git", "--no-replace-objects", "cat-file", "-t", blob_sha],
                  capture_output=True, text=True,
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
1. **`fetch-depth: 0`:** `check_legacy_writes.py` refuses shallow clones, and `check_conventions_legacy_locks.py` reads blob `4620c716` from `4b143c92`.
2. **No `workflow_dispatch` `inputs:` and no `grep -q` under `pipefail`:** Prevents manual narrowing of walks; Python `rev-list` avoids SIGPIPE 141; forward slashes avoid Git Bash backslash-dropping.
3. **Confined 22-blob assembly, `python -S -P`, `--code-root` / `--repo-root` split, and Option I3 sequencing:** Writes **only** validated relative POSIX paths inside `$DETECTOR_DIR` (failing closed if `walk-baseline.json` is absent before L-1, if any key tries traversal/absolute paths, or if under Option I3 `vars.W9_DETECTOR_PIN` is empty or disagrees on `walk_baseline_commit` / `closure_blobs_sha256`). Executes via `python -S -P` + `PYTHONPATH="$DETECTOR_DIR"` + `PYTHONSAFEPATH=1` (no `site-packages` or head checkout on `sys.path`; out-of-closure imports raise `ModuleNotFoundError`), with `--code-root "$DETECTOR_DIR" --repo-root .` on `--verify-watched-to-fail` so clone controls read `.git` from the checkout. **Option I3 upgrade sequence (`R4-i5`):** merge the pin-advance PR first, then Stephen updates `vars.W9_DETECTOR_PIN`—the automatic `push` run immediately after merge is expected to fail red until the variable update, after which a manual `workflow_dispatch` confirms green. Option I1 CODEOWNERS protects `.github/workflows/legacy-write-detector.yml` itself.
4. **Compatibility with existing watchdogs:** `tools/check_workflow_liveness.py:78-92` checks tracked workflows are `state == "active"`; `.github/workflows/ci.yml:255-279` (`watchdog-schedule-liveness`, lines `:263,276`) watches only `ars-artefact-currency-watchdog.yml` and `research-system-suite.yml` (extending it after L-1 is an optional follow-up).
5. **Pre-L-1 throwaway rehearsal and L-1 exit criterion:** Because `walk-baseline.json` does not exist on `origin/main` before L-1, rehearsal before L-1 uses a **separate temporary throwaway workflow file** (never adding inputs or rehearsal triggers to the committed `.github/workflows/legacy-write-detector.yml`) with `on: pull_request`, no `git fetch origin main` overwrite, and `MAIN_TIP="$GITHUB_SHA"` so the pin step reads `walk-baseline.json` and `detector-controls.json` from the throwaway PR's `HEAD` (closed without merging like U-3). Because that rehearsal differs from the committed YAML on those lines, **a green `workflow_dispatch` run of the unmodified committed `.github/workflows/legacy-write-detector.yml` on the L-1 merge commit on `main` is a required L-1 exit criterion**.

### 10.3 The L-1 tripwire test and how L-1 switches it

In `tests/tools/test_w9_detectors.py`, `.github/workflows/legacy-write-detector.yml` is loaded with **`yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)`** (`tests/tools/test_ars_currency_workflow_controls.py:19-22`) so YAML 1.1 never coerces `"on"` to `True`:
```python
# Flipped from False to True in the L-1 activation PR authorized by Stephen (06v §7 L-1).
L1_LIVE = False
```
The test `test_legacy_write_detector_l1_activation_state` (plus the PR-time pin-advance gate when `L1_LIVE is True`) asserts:
- **While `L1_LIVE is False` (WP9.5):**
  1. `.github/workflows/legacy-write-detector.yml` has `set(doc["on"].keys()) == {"workflow_dispatch"}`;
  2. None of `.research-system/evidence/w9/{detector-controls,registration-manifest,walk-baseline,vault-detector-runs}.json` exists in `REPO_ROOT`.
- **When `L1_LIVE is True` (flipped in the L-1 activation PR, running in `ci.yml` `admission-controls` on PRs and `merge_group`):**
  1. `.github/workflows/legacy-write-detector.yml` has `set(doc["on"].keys()) == {"push", "schedule", "workflow_dispatch"}` and `doc["on"]["push"] == {"branches": ["main"]}`;
  2. `.research-system/evidence/w9/detector-controls.json` exists and passes `require_detector_controls` and `--verify-watched-to-fail`;
  3. `.research-system/evidence/w9/{walk-baseline,registration-manifest}.json` exist and pass schema validation;
  4. Every path `p` in `HEAD`'s `walk-baseline.json["baselines"][-1]["detector_closure_blobs"]` equals `git rev-parse HEAD:<p>`;
  5. Rule 0.2 checks (i)–(iv) (§6.5) hold on `baselines[0]` when `walk-baseline.json` is created and on every `baselines[k]` row added since `origin/main`; and
  6. Whenever `HEAD`'s `detector_closure_blobs` differs from `origin/main`'s last row, the one-shot PR-time 2-tool verdict comparison over `(baselines[0]["baseline_commit"], HEAD]` passes (§6.2.2 item 4).

Wiring `tests/tools/test_w9_detectors.py` into `ci.yml` `admission-controls` (Option F1) and CODEOWNERS (Option I1) protects `L1_LIVE` and blocks unrowed closure edits pre-merge except by bypass or direct push.

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

As `R1-m3`, `R2-m16`, `R3-m8`, and `R4-m9` established, in a linked worktree `--git-dir` is `.git/worktrees/<name>` (which holds `HEAD`, `index`, `FETCH_HEAD`, and `ORIG_HEAD`, **not** `config` or `hooks/`—those live in shared `--git-common-dir` alongside sibling worktrees' refs). Therefore, tests in `tests/tools/test_w9_detectors.py` and `tests/research_system/integration/test_w9_wp9_5_detectors.py`:
1. Run every detector subprocess with `cwd=tmp_path` and `GIT_DIR` pinned to `<tmp_path>`.
2. Before and after each test, compare exact equality of:
   - **Locally (checkout-scoped, flake-free):** `(relpath, st_size, st_mtime_ns)` over `--git-dir` files `{HEAD, index, FETCH_HEAD, ORIG_HEAD}` **only**, plus the checked-out branch's own ref value (`git -C <REPO_ROOT> --no-optional-locks symbolic-ref -q HEAD` + `rev-parse`) and `git -C <REPO_ROOT> --no-optional-locks for-each-ref refs/tags`;
   - **In CI only (`CI=true`, no sibling worktree):** also scans `--git-common-dir` (`config`, `hooks/`, `objects/`, `refs/`); and
   - `git -C <REPO_ROOT> --no-optional-locks --no-replace-objects status --porcelain=v1 --ignored -z` and `rev-parse HEAD`.

---

## 12. Tests and test-time budget

### 12.1 Test inventory and mapping to `06v` §4

| Test file | Markers | Cases covered |
|---|---|---|
| `tests/tools/test_w9_detectors.py` | `unit` (default; no `slow` marker; runs in `ci.yml` `admission-controls` on PRs & `merge_group`) | 1. **`W9-T19` (`CONVENTIONS.md` check):** baseline `4620c716` and `dbd54fe3` (`68` -> `90` units) pass; pure successor bullet/paragraph insertion passes; L-0b `ACCEPTED_CONVENTIONS_CLASSIFICATION` test passes; negative controls N1–N7 exit `1`.<br>2. **`W9-T19` (Computational-Log check):** clean fixture + prepended LF/CRLF successor entry + modified successor entry pass; empty `ACCEPTED_CL_EXPORT` fails; `recheck_cl_export` `void: True` fails; symlink/junction/ancestor-alias/in-repo `--vault-root` fails; controls V1–V6 exit `1`.<br>3. **D-5 cadence check:** within 7 days passes; missing file when `ACCEPTED_CL_EXPORT` non-empty fails; >7 days fails until `"owner_cadence_reset"` + fresh `"run"`.<br>4. **Post-merge & PR-time Rule 0 / closure / `acknowledged` controls (`tmp_path` synthetic Git repo):**<br>  - **Evidence & Rule 0 row validation:** atomic disarm fails; pre-reg edit passes; retroactive blessing fails; edits without same-PR `baselines` row fail Rule 0.3; **positive control** (closure edit + same-PR `baselines` row + `P1` ref naming path & `new_blob[:8]`) exits `0`; **negative controls** for row creation (`baselines[0]`) and appended rows (`baselines[k]`): missing decision ref, blobs differing from tree at `C`, `source_commit` not ancestor of `P1` (same-PR ref), wrong `entry_sha256`, extra keys (second `baseline_commit`), slice omitting changed path/`new_blob[:8]`, unmentioned no-op row, unmentioned rollback row each fail; CRLF working copy uses `git rev-parse :<path>` / `git hash-object --path` matching committed index blob.<br>  - **PR-time pin-advance gate (`admission-controls` `L1_LIVE`):** `HEAD` blob mismatch fails; Rule 0.2 (i)–(iv) on `baselines[0]` creation and added rows enforced; unnamed verdict change over `(b0, HEAD]` fails (`ERROR: pin_advance: ...`); **positive control** where verdict change is named by `V[:8]` and `(rule, path)` pairs passes.<br>  - **`acknowledged` & Rule 3 late-entry gate:** exact tuple exempt while sibling fails; backdated/same-commit ref fails; missing `independent_review` fails; missing late `shared-surface-changes.json` entry fails; empty `affected_registrations` without `"none derived"` fails; `"none derived"` in slice + `independent_review` passes; `pr_number: null` on unmapped-commit acknowledgement passes while in-commit PR `pr_number: null` fails.<br>  - **Rules 1–3, PR mapping & lockouts:** Rule 1 exclusions & `legacy_manuscript_root` prefix match; mode-only change fails; H1 Working-Note append passes while task-row edit fails; retry/hint fallback & API exit `2`; `--baseline`, `--head`, `--pr-map`, `--manifest-file`, `--verdict-json`, `--acknowledged-from` exit `2` without `--ruleset-check skip`; `--classified-locks` exits `2` without `--candidate-file`; workflow YAML contains none.<br>  - **Closure, stdlib, CODEOWNERS & confined assembly:** `test_recorded_detector_import_closure_covers_ast_walk`; `test_detector_closure_is_stdlib_only` (21 runtime modules use stdlib/closure only); `test_derived_closure_tools_and_accepted_w9_are_codeowned`; workflow pin heredoc against scratch repo (valid confined `python -S -P` assembly passes in-closure & raises `ModuleNotFoundError` for `research_system.cli`, path traversal `../escape.txt` fails, absolute key `/escape.txt` & `C:/escape.txt` fail, off-chain baseline fails, absent object fails, I3 digest mismatch or empty under `REQUIRE_I3_PIN=true` fails).<br>5. **`main_ruleset` & D-8 controls:** live payload passes; drift/unacked >30d gap/unrecorded `bypass` exit `1`; `--acknowledge-gap` positive & invalid Rule 0.2 negative controls; `--ruleset-check ci-d8` fails without verified `d8_rule_suites_limit_decision_ref` and passes with it.<br>6. **Pre-L-1 tripwire (`L1_LIVE`):** `yaml.BaseLoader`; `False` and synthetic `True` assertions (incl. blob equality, Rule 0.2 (i)–(iv), PR-time verdict comparison).<br>7. **`W9-T7` scratch-clone replay:** `~1.71–1.99s` bare clone; derives 10 `git diff-tree` paths of `5df0c001`/`811d5a2b`; T7-1 and T7-2 (`GIT_INDEX_FILE`) assert Rule 1 & Rule 2 exit `1`; checkout-scoped immutability snapshot (`config`/`hooks/` from `--git-common-dir` in CI only). *(Recorded departure from `06v:230`, Owner Point F.)* |
| `tests/research_system/integration/test_w9_wp9_5_detectors.py` | `integration`, `@pytest.mark.slow` *(selected by `tools/affected_research_tests.py:120-147` on `research_system/`, `tests/research_system/`, or `.research-system/` edits only—NOT `tools/`-only edits; nightly in `research-system-suite.yml:8-9,15,17` `-m "not live_store"`)* | 1. **`M-6`:** scratch W9 control store + scratch Git repo; exports `w9-registration-manifest/2`; `--check` passes & store/manifest drift exits `1`.<br>2. **`O-13`:** runs `tools/run_w9_detector_controls.py` with `CONTROL_GIT_ENV` and `-c` flags; verifies deterministic `output_sha256`, `--verify-watched-to-fail` with `--code-root` / `--repo-root` split + `tools/run_w9_pinned_detectors.py` (`python -S -P`), `require_detector_controls`, `LR-003`, and immutability snapshot. |

### 12.2 Fixture provenance rule (`06v:248-255`)

- No test reads live bytes from `C:\Users\steph\Documents\TDA-Research`, `C:\Users\steph\TDL\vault`, `papers/`, or `results/`.
- Baseline test verifies blob `4620c71607ca3a06c6df3b8e96a6bddffc783960` / SHA-256 `d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589` (`research_system/legacy/reader.py:43-49`).

### 12.3 Measured timings and test-time budget

Measured operations on this machine (Appendix A §21.1):
- `git clone --bare --local --no-hardlinks` (`58,133` objects, `28` packs, `335.09` MiB) + cleanup: **`1.57–1.99s`**.
- `segment(raw, "conventions_unit")` on `4620c716` (`33,645` B) and `dbd54fe3` (`51,774` B): **< `0.15s`**.
- Stdlib-only `python -S -P` execution: **zero package-install overhead** (no `uv sync`).
- **6-call Option C1 walk benchmarks (§21.1 item 10):** `60` commits (~1 mo, 6 guarded) = **`14.05s`** (`1x` post-merge) / **`24.04s`** (`2x` PR compare); `178` commits (~3 mo, 12 guarded) = **`34.46s`** / **`68.92s`**; `320` commits (~5.5 mo, 22 guarded) = **`62.84s`** / **`125.68s`**; **`600s` wall-time stop rule** applies (§6.2.2, §15.2); hosted `windows-latest` full-walk time is `UNVERIFIED-5`.

| Test file | Measured vs unmeasured wall-clock budget basis (`--no-cov`, serial, **including `@pytest.mark.slow`**) | Status |
|---|---|---|
| `tests/tools/test_w9_detectors.py` | Segmentation (< 0.5s) + synthetic Git controls + `W9-T7` bare scratch clone (`~1.77s` + `0.3s`) + two-walk PR compare (`~24–69s` local Git plumbing over 60–178 commits on closure PRs only; < 1s on non-closure PRs). | Runs on every PR in `ci.yml` `admission-controls` (`F1`). |
| `tests/research_system/integration/test_w9_wp9_5_detectors.py` | Scratch W9 store fixture timing for `M-6` and `O-13` (**`UNVERIFIED-3`**: unmeasured here). | Selected via `affected_research_tests.py`; full suite nightly in `research-system-suite.yml`. |

**Unconditional pre-code profiling step (`P-087` item 7, `03-decisions-and-open-questions.md:5919-5923`):** §15.1 item 4 **unconditionally** requires profiling one existing scratch-store test alone on Stephen's machine before code dispatch; **Owner Point G recommends Option G1 (`300s`)** until that measurement supports tightening to G2 (`120s`). Over-budget returns `PARTIAL`.

---

## 13. Research assurance

WP9.5 touches the **Output / Provenance** assurance lane (`CONVENTIONS.md:20-34`): legacy artifact immutability detection, shared-surface state invalidation detection, `CONVENTIONS.md` lock preservation, vault Computational-Log legacy entry integrity, and detector negative-control evidence hashes.

### 13.1 Machine-checkable claims and their enforcement artifacts

| # | Claim | Enforcement artifact (test / validator / schema) |
|---|---|---|
| MC-1 | Every `legacy_path_registration` record in the W9 control store matches `.research-system/evidence/w9/registration-manifest.json` (`w9-registration-manifest/2` under A1: `root_kind`, `root_id`, `normalized_path`, `role`, `source_identity_kind`) at `binding.binding["git_head"]` (§5.3). | `tools/export_w9_registration_manifest.py --check`; `test_w9_wp9_5_detectors.py` (`M-6`). |
| MC-2 | Assembled by content from `baselines[-1]["detector_closure_blobs"]` (22 entries: 21 stdlib-only runtime modules + workflow) into `$DETECTOR_DIR` with normalized relative POSIX path confinement and invoked via `python -S -P` + `PYTHONPATH="$DETECTOR_DIR"` + `PYTHONSAFEPATH=1` (§10.2), `tools/check_legacy_writes.py` (Rule 0) always runs `1x` post-merge from `baselines[0]["baseline_commit"]` using `baselines[-1]` and exits `1` on ledger/top-level mutation, invalid `baselines`/`acknowledged`/`ruleset_gap_acknowledgements` row, or unrowed Rule 0.3 closure edit. When `L1_LIVE` is `True`, `admission-controls` enforces `HEAD:<path>` blob equality, Rule 0.2 (i)–(iv) on `baselines[0]` and added rows, and the single PR-time dual-tool `(b0, candidate]` verdict diff (§6.2.2, §6.5, §10.3). *(Trust root, §6.1: preventive via Option I1 CODEOWNERS + optional I3 on code-owned paths, and via PR-lane `admission-controls` on the 14 non-code-owned closure modules except bypass/direct push; for bypass/direct-push unrowed edits, Rule 0.3 is detective post-merge and exit/permanence awaits Owner Point C §16.2.)* | `tools/check_legacy_writes.py` (Rule 0), workflow pin-assembly step, `test_detector_closure_is_stdlib_only`, `test_recorded_detector_import_closure_covers_ast_walk`, and `tests/tools/test_w9_detectors.py` (`L1_LIVE`). |
| MC-3 | Any guarded first-parent commit `C` after `walk_start` changing a registered `git_tracked` `repository_root` legacy path without an in-commit W9 §4.2 record (`P1`-pre-existing `owner_note` + `independent_review` slices) or valid `acknowledged` entry exits `1` (§6.4, §6.5 Rule 1, §6.6). | `tools/check_legacy_writes.py` (Rule 1); `tests/tools/test_w9_detectors.py` (incl. `W9-T7`). |
| MC-4 | Any first-parent commit `C` after `walk_start` touching `results/` outside `results/ars/` without a matching §4.2 record at `C` (or valid `acknowledged` entry) exits `1` (§6.5 Rule 2). | `tools/check_legacy_writes.py` (Rule 2); `tests/tools/test_w9_detectors.py` (`W9-T7`). |
| MC-5 | Any first-parent commit `C` after `walk_start` modifying a registered `shared_enforcement_surface` without both an in-commit §4.3 record and `shared-surface-changes.json` entry (or valid `acknowledged` row carrying `independent_review`, non-empty `affected_registrations`/slice `"none derived"`, `pr_number: null` on unmapped commits only, and a matching late `<head>:shared-surface-changes.json` entry compatible with `require_change_list`) exits `1` (§6.5 Rule 3, `O-32`). | `tools/check_legacy_writes.py` (Rule 3); `tests/tools/test_w9_detectors.py`. |
| MC-6 | `git --no-replace-objects diff-tree -r --no-renames -z <P1> <C>` detects first-parent changes on both 1-parent and 2-parent commits on `main`, failing closed on mode-only changes (§6.3). | `tools/check_legacy_writes.py`; `tests/tools/test_w9_detectors.py`. |
| MC-7 | Every legacy `conventions_unit` in `CONVENTIONS.md` from `4b143c92` (`4620c716`, provisional 68 units or pinned `ACCEPTED_CONVENTIONS_CLASSIFICATION` `(anchor_text, unit_hash)`) is preserved byte-for-byte in order, with no table inserted in a legacy-lock section (§7.3, §7.4). | `tools/check_conventions_legacy_locks.py`; `tests/tools/test_w9_detectors.py` (`W9-T19`, N1–N7). |
| MC-8 | Every legacy `"item"`/`"structural"` row in `ACCEPTED_CL_EXPORT[-1]` (`recheck_cl_export` `void == False`) is preserved byte-for-byte in order in `04-Methods/Computational-Log.md`, with 0 blockers across the live file while LF/CRLF prepended successor entries pass (§8.2, §8.3). | `tools/check_legacy_log_baseline.py`; `tests/tools/test_w9_detectors.py` (`W9-T19`, V1–V6). |
| MC-9 | All four detector controls emit deterministic `output_sha256` (`CONTROL_GIT_ENV`, `-c core.autocrlf=false -c commit.gpgsign=false`) bound to tool `git_blob_id` and `closure_blobs`, passing `evidence.require_detector_controls` and `--verify-watched-to-fail` with `--code-root`/`--repo-root` (§9.2). | `tools/run_w9_detector_controls.py` and `research_system/legacy/evidence.py:133-154`; `test_w9_wp9_5_detectors.py`. |
| MC-10 | While `L1_LIVE is False`, `legacy-write-detector.yml` has `on == {"workflow_dispatch"}` only and no live L-1 evidence file exists on `main`; when `True`, `on["push"]` filters `branches: ["main"]` and PR-lane blob/row/verdict checks run in `admission-controls` (§10.3). | `tests/tools/test_w9_detectors.py` (`yaml.BaseLoader`), wired into `ci.yml` `admission-controls` (Option F1) and code-owned (Option I1). |

### 13.2 Human-review-only claims and residual architectural limits

| # | Claim / Limit | Reviewer / Owner check and why not mechanized |
|---|---|---|
| HR-1 | **Semantic equivalence, independent review authenticity, and owner authorship of register/review entries:** | `tools/check_legacy_writes.py` checks `P1` ancestry and tuple/slice text on both `legacy-write-records.json` AND `walk-baseline.json` decision entries (`### P-0xx` in `03-decisions-and-open-questions.md` and `reviews/`, `§6.2.2`, `§6.4`). Because the register and review directories are not CODEOWNED, **`P1` ancestry proves pre-PR age, not author identity**; authorship and semantic equivalence rest on human review and Option I1 CODEOWNERS on the evidence files (`W9:174-176`). |
| HR-2 | Whether `affected_registrations` in `shared-surface-changes.json` captures every affected result (and whether revert `B -> A` restores compatibility for earlier observations, §6.5). | Deriving `affected_registrations` from binding tests requires Stephen's note and the independent reviewer (`W9:185-188`). |
| HR-3 | **Post-merge detection, human merge trust root, Rule 0.3 permanence, and bypass/closure cost (§6.1, §6.2.3, §16.1–§16.2):** | Ruleset `20822054` has `required_approving_review_count: 0`, so preventive control for CODEOWNED files rests on human merge review + `.github/CODEOWNERS` (+ optional I3). For non-code-owned closure modules, unrowed closure edits via admin bypass or direct push are caught only post-merge by Rule 0.3, which currently **remains permanently red** across full re-walks unless Stephen picks the narrow hash-bound Rule 0.3 exemption under **Owner Point C (§16.2)**. I1 bypass merges also require Stephen's `Bypass reason:` line (`tools/check_bypass_merges.py:41,135`, `admin-bypass-guard.sh:13-18`). |
| HR-4 | **Self-attestation of weekly vault Computational-Log runs (§8.4):** `vault-detector-runs.json` records operator-machine timestamps and hashes. | CI cannot access `C:\Users\steph\Documents\TDA-Research` to independently verify operator-machine execution of `tools/check_legacy_log_baseline.py`. |
| HR-5 | **30-day rule-suites window & D-8 bypass visibility (§4.1, §4.2):** GitHub's `rulesets/rule-suites` window is at most 30 days (`MAX_DAYS = 30`), with `bypass` evaluations routine in queue merges. | Fails closed past 30 days without an owner-acked `ruleset_gap_acknowledgements` row; under D-8, direct `rule-suites` inspection happens at local pre-batch runs (`06v:571,603`). |
| HR-6 | **`CONVENTIONS.md` structural exceptions outside `conventions_unit` rows (§7.4):** `### ` sub-headings, `---`, blank lines, H1 title, footer. | Editing a legacy `### ` sub-heading title or moving a legacy bullet between `### ` sub-headings inside the same `## ` section relies on human PR review (`wp9-5-note-r2-review-2026-11-21.md:123`). |
| HR-7 | **`tools/export_w9_registration_manifest.py` (M-6) runs unpinned from the working checkout (§2.1, §6.2.3):** | M-6 imports `research_system/cli.py` (~161-module closure), so it is excluded from the 22-entry stdlib-only `detector_closure_blobs` map and executes from the operator's checked-out tree rather than `$DETECTOR_DIR`. It is CODEOWNED under Option I1 (`@stephendor`), while unpinned transitive imports in `cli.py` rely on the local operator checkout. |

---

## 14. Claims for review

An independent adversarial reviewer should attack each of the following 16 load-bearing claims against the cited repository evidence at base commit `dbd54fe382e7b2849d3f2038393cbdb4d709477b`:

1. **No D-4 trigger (`P-089` item 1):** WP9.5 adds no W9 command, no runtime-binding census row (`275` rows, SHA-256 `82eab93a...451d58`), no store append site, no core/W9 schema, and leaves `tools/w9_segmentation.py` (`43e1454de09b61e274954c42b21d6ae533857a24`) and `IMPORTER_MODULES` (`reader.py:42`) untouched (§2.2; `03-decisions-and-open-questions.md:6022-6025,6085-6099`).
2. **Trust-root boundary, PR-time pin-advance gate, `1x` post-merge walk, stdlib-only `python -S -P` assembly, and Rule 0.3 choice:** Preventive blocking rests on Option I1 CODEOWNERS (plus optional I3 `vars.W9_DETECTOR_PIN`) for code-owned files, and on PR-lane `admission-controls` (`L1_LIVE = True`) checking `HEAD:<path>` blob equality, Rule 0.2 (i)–(iv) on `baselines[0]` / added rows, and a single bounded PR-time dual-tool `(b0, candidate]` verdict comparison (over `(rule, path)`, `ERROR` never `∅`, Rule 0 non-nesting, `V[:8]` + `(rule, path)` slice match) for all 22 closure blobs (§6.1, §6.2.2, §6.5, §10.2, §10.3). Post-merge runs walk `1x` using `baselines[-1]` from `baselines[0]["baseline_commit"]` under confined `python -S -P` + `PYTHONSAFEPATH=1` assembly (no `pyproject.toml`, `uv.lock`, or `uv sync`, §6.2.3, §10.2), with unrowed bypass/direct-push Rule 0.3 exit vs permanence put to Stephen under Owner Point C (§16.2) and `HR-3` (§13.2).
3. **Manifest fields, `require_registered` compatibility, and WP9.4 pass-count question:** Option A1 bumps `REGISTRATION_MANIFEST_FORMAT` uniformly to `"w9-registration-manifest/2"` carrying 5 closed keys in `_legacy_projection` (`cli.py:1648-1659`), updates `require_registered` (`evidence.py:40,114-131`) and the 4 test manifest builders via a dated WP9.3 amendment + independent review, leaves WP9.4 production code untouched, and asks Stephen whether `wp9-4-1-record.md:114,130` (`13 passed`, `688.11s`) pass counts are re-recorded (§2.3, §5.3, §16.3).
4. **Rule 1 matching and exclusions:** Restricting Rule 1 and §6.6 to `root_kind == "repository_root"` and `source_identity_kind == "git_tracked"` while excluding `conventions_lock`, `shared_enforcement_surface`, `successor_results_root`, and `legacy_read_only_projection` avoids misfires on untracked/restricted files, `results/ars/`, or `CONVENTIONS.md` insertions (§6.5 Rule 1, §6.6).
5. **`.apm/tracker.md` Working Notes handling:** Option H1 verifies via `segment(raw, "tracker_task_row")` and `segment(raw, "working_note_entry")` (`segmentation.py:470-473`) that task rows and pre-existing notes stay byte-identical and gaps match `[ \t]*\n` (`#368`, `#388`, `#433`, §6.5 Rule 1, §16.9).
6. **W9 §4.2 record keying and `P1` age provenance:** Keying `legacy-write-records.json` by `(pr_number, normalized_path, old_blob, new_blob)` with `P1`-pre-existing `owner_note` and `independent_review` slices binds records without knowing squash SHAs, conditional on Option I1 CODEOWNERS because `P1` ancestry proves age rather than authorship (§6.4, `HR-1`, §16.1, §16.4).
7. **Two-parent merge diffs & mode changes:** Explicit `git --no-replace-objects diff-tree -r --no-renames -z <P1> <C>` handles 1-parent and 2-parent commits (`b132406e`) and fails closed on mode-only changes (§6.3).
8. **PR mapping, `5df0c001`/`811d5a2b` genealogy, and `W9-T7` unit lane:** Matching `merge_commit_sha == C` (3-try retry + hint fallback, exit `2` on API failure, `--baseline`/`--head`/`--pr-map`/`--manifest-file`/`--verdict-json`/`--acknowledged-from` locked behind `--ruleset-check skip`) maps squash/merge PRs cleanly while `W9-T7` replays direct commits `5df0c001` (11 files, 7 `results/`) and `811d5a2b` (9 files, 3 manifests) in the unit lane (`tests/tools/test_w9_detectors.py`, recorded departure from `06v:230` in §16.7; §6.2.1, §6.3, §11.2).
9. **Option D3 `O-32` resolution and tightened Rule 3 `acknowledged` parity:** Uniform `"w9-shared-surface-changes/2"` without a commit SHA passes `check_change_list` via `evidence.blob_at` (`acceptance.py:121-136`, `evidence.py:179-188`); late entries paired with `acknowledged` require `independent_review`, non-empty `affected_registrations`/slice `"none derived"`, and ack-only `pr_number: null` on unmapped commits, safely enforced by `require_change_list` (`evidence.py:190-218`, §6.5 Rule 3, `HR-2`, §16.5).
10. **Ruleset `20822054` pinning, 30-day gap ack, and U-3 probe:** Pinning `allowed_merge_methods`, `merge_queue`, `require_code_owner_review`, `strict_required_status_checks_policy`, 4 contexts (`integration_id: 15368`), and `bypass_actors` fails closed past 30 days without Rule-0-checked `ruleset_gap_acknowledgements`; U-3 throwaway draft-PR probe verifies `GITHUB_TOKEN` behavior on all 3 endpoints (§4.1, §4.2).
11. **Vault root junction refusal vs `open_registered_root_anchor`:** Because `open_registered_root_anchor` (`anchor.py:1934-1950`) sets `reject_reparse=False` and `LegacyReader.__init__` (`reader.py:241-248`) is lexical, `check_legacy_log_baseline.py` and `u4_dry_run.py` explicitly check symlink/junction/resolve-normcase outside `repository_root` (§4.3.1–§4.3.3).
12. **`CONVENTIONS.md` unit counts, table filter, and L-0b pinning:** Exact parity (`4620c716` 70 units -> `dbd54fe3` 90 units, 0 blockers), first-byte `|` rejection in legacy sections (`start_byte` + `byte_length`), structural exceptions tracked in `HR-6`, and pinned L-0b `ACCEPTED_CONVENTIONS_CLASSIFICATION` (`(anchor_text, unit_hash)`, N7) (§7.3, §7.4, §7.6, §16.10).
13. **Vault classification, `void == True` refusal, and CRLF tolerance:** Reading `ACCEPTED_CL_EXPORT[-1]["classified_list"]` (`w9-cl-classified-list/1`, 1-based `1..N`), failing closed on `recheck_cl_export` `void == True` or any live `blocker`, and matching legacy `raw_row_sha256` without breaking on Obsidian CRLF prepends (§8.2, §8.3, §16.10).
14. **D-5 cadence gate at batch start (`LR-003`/`LR-015`) and `LR-016`/`LR-020`:** Gating strictly on `bool(reader.accepted_cl_export)` with `"owner_cadence_reset"` recovery (§8.4, §16.6).
15. **Deterministic closure-bound control hashes & dual-root verification:** Binding `git_blob_id`, `closure_blobs`, `CONTROL_GIT_ENV`, and `-c` flags with `--code-root`/`--repo-root` split across `run_w9_detector_controls.py --verify-watched-to-fail` and `run_w9_pinned_detectors.py` (§9.2, §10.2, §12.1).
16. **PR-lane wiring, derived CODEOWNERS, and `L1_LIVE` / Option K1:** Wiring `tests/tools/test_w9_detectors.py` (`yaml.BaseLoader`), `test_derived_closure_tools_and_accepted_w9_are_codeowned`, Option I1 CODEOWNERS (10 files + 1 dir), and Option K1 (`check_conventions_legacy_locks.py` in `admission-controls`, noting self-judgement when a closure module changes in the same PR before pinned post-merge execution) (§2.3, §10.3, §16.1, §16.7, §16.11).

---

## 15. Stop rules for the code package

### 15.1 Hard preconditions before WP9.5 code is dispatched (`P-089` item 3, `03-decisions-and-open-questions.md:6104-6115`)

WP9.5 implementation code **must not** be dispatched until all four items below are complete (and item 5's unverified hosted wall time is acknowledged):

1. **U-3 recorded in §4.2.2 (§15.1 gate; `06v:159`):** Stephen authorizes the read-only U-3 throwaway draft-PR probe (§4.2.2); the reviewing session executes it, records HTTP statuses, `X-Accepted-GitHub-Permissions`, and pinned key presence for all 3 endpoints (`rulesets/20822054`, `rulesets/rule-suites`, `commits/dbd54fe3.../pulls`) in §4.2.2, and states whether D-8 applies to `rule-suites`.
2. **U-4 handle-bound reader and segmenter dry run recorded in §4.3.3 (`06v:160`):** Using the already-recorded metadata (`833,453` bytes, SHA-256 `73fcbe83...`), the reviewing session runs scratch script `u4_dry_run.py` (§4.3.3 item 2) against `C:\Users\steph\Documents\TDA-Research\04-Methods\Computational-Log.md` with `PYTHONPATH=.` from repo root and records `root_checks`, `bytes`, `sha256`, `link_count`, `canonical_target`, `file_facts`, `row_counts`, and `blockers` in §4.3.3.
3. **Owner Points I, C, A, B, D, E, F, G, H, J, K decided by Stephen (`P-090`):** Stephen records his disposition on all 11 points (§16.1–§16.11, deciding **I** first) in `03-decisions-and-open-questions.md`, authorizing dated WP9.3 / `CONVENTIONS.md:713-729` / W9 §4.2 amendments as selected and verifying Actions variable write permissions (`UNVERIFIED-4`, §21.2) if Option I3 is chosen.
4. **Unconditional pre-code single scratch-store test timing profile (`P-087` item 7, `03-decisions-and-open-questions.md:5919-5923`):** Profile one existing WP9.3/WP9.4 single scratch-store integration test alone on Stephen's machine (`UNVERIFIED-3`, §21.2) before adding `test_w9_wp9_5_detectors.py`.
5. **Hosted `windows-latest` full-walk wall time (`UNVERIFIED-5`, §21.2):** Both post-merge `1x` walk time and closure-PR `2x` verdict-compare time with real rules and `gh api` PR mapping on hosted `windows-latest` (including ~60, ~178, and ~320-commit intervals) remain `UNVERIFIED-5` ahead of rehearsal and live activation, bounded by the `600s` stop rule below.

*(Pre-L-1 gate note: after WP9.5 code lands and before L-1 activation on `main`, execute a one-shot throwaway `pull_request` rehearsal using a separate throwaway workflow file differing from `.github/workflows/legacy-write-detector.yml` only by reading synthetic evidence from the PR head rather than `refs/remotes/origin/main` [closed without merging], followed after L-1 merge by a green `workflow_dispatch` run on the L-1 merge commit as an L-1 exit criterion, §10.2 item 5.)*

### 15.2 Stop rules during WP9.5 code implementation

The WP9.5 code worker must stop immediately and return `PARTIAL` if:
1. Any change would modify a protected identity listed in §2.2 (the 275-row runtime-binding census, `wp6_1_06h_current_append_manifest.yaml` blob `1066404a`, `test_wp6_1_06h_append_path_closure.py` blob `3b1eec6e`, `research_system/schema_registry.py` blob `e32cb408`, `research_system/authority.py` blob `9b56b322`, core/W9 schemas, T2 expectations/seal, `tools/w9_segmentation.py` blob `43e1454de09b61e274954c42b21d6ae533857a24`, or `IMPORTER_MODULES` in `research_system/legacy/reader.py:42`) (`06v:614,618-619`).
2. Any change under `research_system/legacy/` would exceed the specific changes approved by Stephen under Owner Points A, D, E, and J.
3. Any test or negative control needs live legacy, vault, or restricted bytes, or writes to / leaves any state in `REPO_ROOT`, any linked worktree, or `C:\Users\steph\Documents\TDA-Research` (`06v:616-617`).
4. The new and changed WP9.5 test files (including `@pytest.mark.slow` tests) exceed the approved serial `--no-cov` test-time budget (Owner Point G) on Stephen's machine (`P-087` item 7, `03-decisions-and-open-questions.md:5919-5923`).
5. **Wall-clock stop rule for full walk / PR verdict comparison:** If a full walk with real rules and PR mapping (either the `1x` post-merge walk or the `2x` PR-time dual-tool verdict comparison) exceeds **`600s` (10 minutes)** in rehearsal or smoke measurement, stop and return the question of cadence/scope to Stephen before continuing.
6. *(WP9.5-specific stop rule added by this design note, not in `06v` §8):* Any detector negative control fails to fire on its designated violation case or fires on a clean positive control case, `test_recorded_detector_import_closure_covers_ast_walk` detects an unpinned `research_system` or `tools` import, or `test_detector_closure_is_stdlib_only` detects any non-stdlib / non-closure import.

---

## 16. Owner points

Stephen's decision is requested on the following eleven points (**I** first—because **B**, **C**, and the L-1 guard depend on it—followed by **C, A, B, D, E, F, G, H, J, K**) before WP9.5 code is dispatched. Nothing in this note decides them for him.

### 16.1 Owner Point I *(decide first)* — Trust root protecting detector surface, closure, tripwire, and evidence directory

*Pointers:* §2.3, §6.1, §6.2.3, §10.2, §10.3.

- **Options:**
  - **Option I1 (Rule 0 + stdlib-only `python -S -P` content pin + `.github/CODEOWNERS` expansion — Recommended):** Enforce Rule 0 monotonicity (§6.5) and confine detector execution via `python -S -P` + `PYTHONPATH` + `PYTHONSAFEPATH=1` over the 22-entry stdlib-only `detector_closure_blobs` (`21` runtime modules + workflow; no `pyproject.toml`, `uv.lock`, or `uv sync`, with `tools/export_w9_registration_manifest.py` excluded -> residual `HR-7`), adding **10** file patterns (`/.github/workflows/legacy-write-detector.yml`, `/tools/check_legacy_writes.py`, `/tools/check_conventions_legacy_locks.py`, `/tools/check_legacy_log_baseline.py`, `/tools/run_w9_detector_controls.py`, `/tools/run_w9_pinned_detectors.py`, `/tools/export_w9_registration_manifest.py`, `/tools/_w9_detector_evidence.py`, `/tests/tools/test_w9_detectors.py`, `/research_system/legacy/accepted_w9.py`) plus directory pattern `/.research-system/evidence/w9/` to `.github/CODEOWNERS` (`@stephendor`), backed by `test_derived_closure_tools_and_accepted_w9_are_codeowned` and `test_detector_closure_is_stdlib_only` (§12.1).
    - *Trust-root boundary & operational cost:* Preventive via CODEOWNERS on those 10 files + directory, and via PR-lane `admission-controls` (`L1_LIVE`) on all 22 closure entries except bypass/direct push; detective post-merge under Rule 0.3 for bypass/direct push. Requires Stephen's bypass merge (`Bypass reason:`, `tools/check_bypass_merges.py:41,135`, `admin-bypass-guard.sh:13-18`) on every per-batch manifest, weekly vault-run, ruleset-read, baseline/pin-advance, or closure-edit PR (7 W9 PRs in the last 4 weeks; 14 of 178 first-parent commits in 90 days touched the 15 existing closure modules; non-exempt closure edits also need a `P1` decision ref + `baselines` row + `detector-controls.json` re-record).
    - *Closure-width sub-choice:* **Option I1-default** keeps the **14** non-code-owned closure modules (`13` `research_system/` + `tools/w9_segmentation.py`; `accepted_w9.py` is code-owned). **Option I1-narrow (`§6.2.3`)**: because `reader.py:37` imports `research_system.store.lock` -> `store.anchor` & `store.writer` (`lock.py:3,11`) and `durability.py` is pulled in, moving helpers either cuts the 90-day count from **14 to 8 commits at most** (`evidence.py` [5 commits], `reader.py`, `segmentation.py`, `accepted_w9.py`, and `export_recheck.py` still remain in any narrowing) OR forks the Windows handle-anchor code.
  - **Option I2 (Rule 0 only; leave `.github/CODEOWNERS` at current 8 paths):** Leaves L-1 `L1_LIVE`, workflow, tools, `accepted_w9.py`, and evidence outside `@stephendor`; insufficient for Option B1 and R1-B1 scenarios 4–5.
  - **Option I3 (Optional second, out-of-tree anchor — combinable with I1):** Set GitHub repository variable `W9_DETECTOR_PIN` (`{"walk_baseline_commit", "closure_blobs_sha256"}`), enable `REQUIRE_I3_PIN: "true"` in §10.2, and read it via authenticated `gh api` in `tools/run_w9_pinned_detectors.py` (§6.2.3). Pin advances merge first and expect a failing push run until `W9_DETECTOR_PIN` is updated (red window); Actions variable write permissions remain **`UNVERIFIED-4`** (§21.2).
- **Recommendation:** **Option I1** (choosing between **I1-default** and **I1-narrow** with full reach facts), optionally paired with **Option I3** after verifying Actions variable write permissions (`UNVERIFIED-4`).
- **What it changes & records needed:** I1 updates `.github/CODEOWNERS:1-24`, splits `tests/tools/test_ci_platform_policy.py` (`W9_DETECTOR_CODEOWNED_FILES`, `W9_DETECTOR_CODEOWNED_DIRS`, `:364-374` without `.is_dir()` on `/.research-system/evidence/w9/`, landing all 9 new files in the same PR), and **amends `CONVENTIONS.md:713-729`** (inside `## ARS Foundation Governance`, lines `614-783`); recorded in `P-090`. (`I3` also sets `W9_DETECTOR_PIN` at L-1.)

### 16.2 Owner Point C — Committed `walk-baseline.json`, PR-time pin-advance gate, `1x` post-merge walk, Rule 0.3 exit choice, and pre-baseline dispositions

*Pointers:* §6.2.1, §6.2.2, §6.5, §10.3.

- **Options:**
  - **Option C1 (Recommended):** Commit `.research-system/evidence/w9/walk-baseline.json` (`w9-walk-baseline/1`) starting at `baselines[0]["baseline_commit"]` (any known first-parent ancestor of L-1 on `main`, disposing `(4b143c92, baseline_commit]` via a `P1` hash-bound `pre_baseline_dispositions_ref` refreshed at L-1), with 22-entry stdlib-only `detector_closure_blobs`, `acknowledged` (Rules 1–3, plus late `<head>:shared-surface-changes.json` + `independent_review` + ack-only `pr_number: null` on unmapped commits), and `ruleset_gap_acknowledgements`.
    - **PR-time (`admission-controls`, `L1_LIVE`):** verifies `HEAD:<path>` blobs, Rule 0.2 (i)–(iv) on `baselines[0]` / added rows, and the single bounded `(b0, candidate]` verdict comparison (over `(rule, path)`, `ERROR` never `∅`, Rule 0 non-nesting, `V[:8]` + `(rule, path)` slice match), subject to the **`600s` stop rule** (`§12.3`, `§15.2`, `UNVERIFIED-5` hosted full-walk time).
    - **Post-merge (`legacy-write-detector.yml`):** walks `1x` from `baselines[0]["baseline_commit"]` using `baselines[-1]` only; Rule 0.3 stays as the post-merge backstop.
  - **Option C2:** Set `baselines[0]["baseline_commit"]` to `4b143c9225035cc29e37351445f1c3a4ab09ceb1` and carry `acknowledged`/dispositions for all 22 historic guarded commits (§6.2.1).
  - **Rule 0.3 recovery sub-choice (on an unrowed bypass/direct-push closure edit):**
    - **Option C-R0-exemption:** Allow a narrowly scoped, hash-bound exemption row keyed on `(commit, path, old_blob, new_blob)` + `P1` decision slice (analogous to `acknowledged`; **not built into Revision 5**, implemented only if Stephen picks this option).
    - **Option C-R0-permanent:** Accept that Rule 0.3 stays permanently red across future re-walks if an unrowed closure edit lands by bypass/direct push, documented in `HR-3` (§13.2).
- **Recommendation:** **Option C1** (contingent on Option I1) plus Stephen's choice between **Option C-R0-exemption** and **Option C-R0-permanent**.
- **What it changes & records needed:** Adds a dated row for `.research-system/evidence/w9/walk-baseline.json` in `docs/plans/agentic-research-system/implementation/06v-addendum-2026-11-10-w9-paths.md` and records `P-090` (plus `P-09x` L-1 disposition refresh); `research_system/legacy/` untouched.

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
  - **Option F1 (Wire into `.github/workflows/ci.yml` `admission-controls` — Recommended):** Add `tests/tools/test_w9_detectors.py` to `ci.yml:166-216` (`admission-controls`, precedent `:210`) and `ADMISSION_CONTROL_MODULES` (`test_ci_platform_policy.py:175-229`, precedent `:226`). Covers the `L1_LIVE` tripwire, PR-time `HEAD:<path>` blob/row/verdict checks, and **`W9-T7` as a `unit` test on every PR — an explicit departure from `06v:230,503` ("`W9-T7` ... `integration, slow`")** while `test_w9_wp9_5_detectors.py` remains `integration, @pytest.mark.slow` (`affected_research_tests.py:120-147`; nightly `research-system-suite.yml:8-9,15,17`).
  - **Option F2:** `legacy-write-detector.yml` only (no pre-L-1 PR tripwire).
- **Recommendation:** **Option F1** paired with **Option I1** (so `L1_LIVE` is code-owner protected).
- **What it changes & records needed:** Edits `.github/workflows/ci.yml:212` (`.github/CODEOWNERS:18`, Stephen merges), `tests/tools/test_ci_platform_policy.py:228`, a **dated addendum row in `06v-addendum-2026-11-10-w9-paths.md` (or `06v` addendum)** recording the `W9-T7` unit-lane departure from `06v:230`, and `P-090`.

### 16.8 Owner Point G — Test-time budget for WP9.5 (including `@pytest.mark.slow`)

*Pointers:* §12.3, §15.1 item 4.

- **Options:**
  - **Option G1 (Recommended pending profile):** Apply the **300-second (5-minute)** serial `--no-cov` budget from `P-087` item 7 (`03-decisions-and-open-questions.md:5919-5923`), counting all new/changed WP9.5 tests including `@pytest.mark.slow` (over-budget returns `PARTIAL`; note WP9.4 integration files run ~5–11 minutes if re-run under A1).
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
| Revision 5 | 2026-11-22 | Gemini agent (under `P-089`) | Narrow rework & structural cut addressing all 21 findings (`R4-M1`–`R4-M2`, `R4-m1`–`R4-m11`, `R4-i1`–`R4-i8`) from `docs/plans/agentic-research-system/reviews/wp9-5-note-r4-review-2026-11-22.md` (`0e6d23e4`): moved the bounded dual-tool verdict diff to PR `admission-controls` with `1x` post-merge walks & `600s` stop rule, added PR-lane `HEAD:<path>` blob/row checks + Point C Rule 0.3 exit choice, dropped `pyproject.toml`/`uv.lock`/`uv sync` for confined stdlib-only `python -S -P` execution, excluded the unpinned M-6 exporter (`22` blobs; `HR-7`), compacted §18–§20, stripped heading tags, split §16 subsections, and updated §21. |

---

## 18. Compact disposition index: revisions 1 to 3

Full historical details for revisions 1–3 live in Git history and in the archived review reports (`wp9-5-note-r1-review-2026-11-21.md` `edb9acc6`, `wp9-5-note-r2-review-2026-11-21.md` `3cf35bec`). Below is the compact disposition of all 34 revision-1 findings and all 27 revision-2 findings against the current text:

| Finding ID | Section(s) | Status |
|---|---|---|
| `R1-B1` | `§6.1, §6.2.2, §6.4, §6.5, §10.2, §12.1, §16.1–§16.2, §16.4` *(pinning replaced in §19 `R3-M1` & §20 `R4-M1`/`R4-M2`)* | resolved |
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
| `Review §2 (R1)` | `Repo-wide citations (corrected across R2 & R3 -> §19 R2-m2/R2-m4)` | resolved |
| `R2-M1` | `§6.1, §6.2.2, §6.3, §6.5, §10.2` *(note: `tool_pin_commit` & detached worktree superseded in R4 §19 `R3-M1` and R5 §20 `R4-m7`)* | superseded |
| `R2-M2` | `§6.2.2, §6.5, §12.1, §16.2` *(note: `checkpoints`, `--record-checkpoint`, `--full-rewalk`, & `verdict_digest` superseded in R4 §19 `R3-M2` and R5 §20 `R4-M1`)* | superseded |
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

---

## 19. Change log: revision 3 to revision 4

Full review details for revision 3 live in `docs/plans/agentic-research-system/reviews/wp9-5-note-r3-review-2026-11-21.md` (`1bd4ecff`). Compact disposition of all 20 findings:

| Finding ID | Section(s) | Status | Note |
|---|---|---|---|
| `R3-M1` | `Header, §1, §2.3, §6.1, §6.2.2–§6.2.3, §6.5, §10.2, §12.1, §13.1, §14, §16.1–§16.2, §21.1` | superseded | Deleted `tool_pin_commit`; Form (A) `uv sync`/`pyproject.toml`/`uv.lock` & unpinned exporter in map superseded in R5 (`§20` `R4-M2`, `R4-m4`, `R4-m7`) by 22-blob stdlib-only `python -S -P` assembly + PR-lane check. |
| `R3-M2` | `§1, §2.1, §6.2.2, §6.5, §12.1, §12.3, §14, §16.2, §21.1` | superseded | Deleted `checkpoints` & `--full-rewalk`; post-merge Rule 0.2 (v) dual-tool walk superseded in R5 (`§20` `R4-M1`) by PR-time comparison & `1x` post-merge walk + `600s` stop rule. |
| `R3-M3` | `§1, §6.2.2, §6.5, §12.1, §13.1, §14, §16.2, §16.5` | resolved | Required matching late `<head>:shared-surface-changes.json` entry on Rule 3 `acknowledged`; further tightened in R5 (`§20` `R4-m1`). |
| `R3-m1` | `Header, §10.2, §15.1, §16.1, §21.2` | resolved | `W9_DETECTOR_PIN` stores `closure_blobs_sha256`, `REQUIRE_I3_PIN`, `UNVERIFIED-4`; sequencing updated in R5 (`R4-i5`). |
| `R3-m2` | `§1, §2.1, §2.3, §6.2.3, §7.5, §8.4, §9.2, §10.2, §12.1, §16.1, §16.10` | resolved | Added operator wrapper `tools/run_w9_pinned_detectors.py` & code-owned `accepted_w9.py`; bootstrap/exporter fixed in R5 (`R4-m4`). |
| `R3-m3` | `§6.2.3, §13.2 HR-3, §16.1` | resolved | Stated 14-commit/7-PR closure cost & added Option I1-narrow (reach corrected in R5 `R4-m11`). |
| `R3-m4` | `§1, §2.1, §11.2, §12.1, §12.3, §13.1, §14, §16.2, §16.7` | resolved | Moved `W9-T7` to unit lane & clarified `affected_research_tests.py:120-147`; departure recorded in R5 (`R4-m10 (c)`). |
| `R3-m5` | `§1, §12.3, §15.1, §16.8, §21.2` | resolved | Made pre-code single scratch-store profile unconditional (`UNVERIFIED-3`). |
| `R3-m6` | `§4.3.3, §14, §15.1, §21.2` | resolved | Added `root_checks` booleans to `u4_dry_run.py`. |
| `R3-m7` | `Header, §1, §9.2, §12.3, §13.1, §14, §16.7, §21.1` | resolved | Fixed `.github/CODEOWNERS:18`, `:218`, R2 vs R3 §21.1 credits, and `closure_blobs` map wording. |
| `R3-m8` | `§1, §11.3` | resolved | Scoped local snapshot to checkout `--git-dir`; shared `config`/`hooks/` moved to `CI=true` in R5 (`R4-m9`). |
| `R3-m9` | `§2.3, §4.2.2, §6.2.3, §8.4, §13.2, §16.1` | resolved | Added CODEOWNERS header, same-PR landing, no `.is_dir()`, `Bypass reason:` cost, `CONVENTIONS.md:614-783` note. |
| `R3-m10` | `§6.2.2, §16.2` | resolved | Defined disposed vs walked interval & L-1 refresh rule; ref hash-bound in R5 (`R4-i6`). |
| `R3-m11` | `§4.1, §6.2.2, §6.5, §12.1, §14, §16.2` | resolved | Added `ruleset_gap_acknowledgements` schema, Rule 0.2 check, and `--acknowledge-gap`/D-8 tests. |
| `R3-m12` | `§10.2, §12.1, §15.1` | resolved | Added pin heredoc unit tests + pre-L-1 rehearsal; confinement & separate rehearsal file added in R5 (`R4-m3`, `R4-m8`). |
| `R3-m13` | `§2.3, §5.3, §14, §16.3` | resolved | Named the 3 WP9.4 test files under Option A1; pass-count question added in R5 (`R4-i3`). |
| `R3-i1` | `§1, §10.3, §13.1, §14` | resolved | Used `yaml.BaseLoader` for workflow YAML loading in `L1_LIVE` tripwire. |
| `R3-i2` | `§1, §7.5, §15.1, §16.11` | resolved | Added Owner Point K (`Option K1`/`Option K2`); PR self-judgement noted in R5 (`R4-i2`). |
| `R3-i3` | `§10.2` | resolved | Noted `ci.yml:255-279` (`watchdog-schedule-liveness`) scope. |
| `R3-i4` | `§4.2.2, §21.1` | resolved | Recorded R3 live ruleset re-check (`56`/`32`, `4ca375a3`). |

---

## 20. Change log: revision 4 to revision 5

Every finding in `docs/plans/agentic-research-system/reviews/wp9-5-note-r4-review-2026-11-22.md` (`0e6d23e4`) is disposed of below:

| Finding ID | Section(s) | Status | Change in revision 5 |
|---|---|---|---|
| `R4-M1` | `§1, §6.2.2, §6.5, §10.3, §12.1, §12.3, §13.1, §14, §15.1, §15.2, §16.2, §21.1, §21.2` | resolved | Moved bounded dual-tool verdict comparison (over `(b0, candidate]`, `(rule, path)` pairs, `ERROR` never `∅`, Rule 0 non-nesting, `V[:8]` + `(rule, path)` slice match) into PR `admission-controls`; deleted Rule 0.2 (v); post-merge runs walk `1x` with `baselines[-1]`; added 6-call Option C1 benchmarks (`14.05–62.84s` `1x`, `24.04–125.68s` `2x`), `600s` stop rule, and `UNVERIFIED-5`. |
| `R4-M2` | `§1, §6.2.2–§6.2.3, §6.5, §10.3, §12.1, §13.1–§13.2, §14, §16.2` | resolved | Added PR-lane `HEAD:<path>` blob equality + Rule 0.2 (i)–(iv) checks under `L1_LIVE`; dropped `pyproject.toml`/`uv.lock` from pin; qualified `MC-2`/Claim 2/`HR-3`; put Rule 0.3 exemption-vs-permanence sub-choice to Stephen under Owner Point C (`§16.2`). |
| `R4-m1` | `§1, §6.2.2, §6.5, §12.1, §13.1, §14, §16.2, §16.5` | resolved | Required `independent_review` (`§6.4.2`), non-empty `affected_registrations`/slice `"none derived"`, and ack-only `pr_number: null` on unmapped commits; stated `require_change_list` (`evidence.py:190-218`) late-entry safety; added empty-list and null-PR controls. |
| `R4-m2` | `§12.1` | resolved | Added missing row controls: tree-mismatching blobs (ii), same-PR / non-`P1` `source_commit` (iii), wrong `entry_sha256`, extra `baseline_commit` key, and positive control for a named verdict change. |
| `R4-m3` | `§6.2.3, §10.2, §12.1` | resolved | Required normalized relative POSIX keys (`no ..`, `resolved.is_relative_to(detector_dir.resolve())`); added traversal/absolute-key controls; renamed `"blob mismatch"` -> `"absent object"`. |
| `R4-m4` | `§2.1, §6.2.3, §13.2, §16.1, §21.1` | resolved | Required operator wrapper self-blob check / `origin/main` copy after `git fetch --no-tags` + `git ls-remote` check; removed M-6 exporter from the 22-entry blob map and documented its checkout execution in `HR-7`. |
| `R4-m5` | `§9.2, §10.2, §12.1, §13.1, §14` | resolved | Split `run_w9_detector_controls.py` into `--code-root "$DETECTOR_DIR"` (imports/blobs) and `--repo-root .` (Git object DB). |
| `R4-m6` | `§6.2.3, §12.1, §14, §16.1` | resolved | Added `test_derived_closure_tools_and_accepted_w9_are_codeowned` checking every derived AST-closure `tools/` module plus `accepted_w9.py` against `.github/CODEOWNERS`. |
| `R4-m7` | `§1, §2.1, §2.3, §6.2.2–§6.2.3, §10.2, §12.1, §12.3, §13.1, §14, §16.1, §21.1` | resolved | Dropped `pyproject.toml`, `uv.lock`, `uv sync`, and `.venv` reuse; added `test_detector_closure_is_stdlib_only`; specified pinned `actions/setup-python` + `python -S -P` + `PYTHONPATH` + `PYTHONSAFEPATH=1` (explaining why not `-I`/`-E`); verified stdlib-only & scratch `-S -P` isolation in §21.1. |
| `R4-m8` | `§10.2, §15.1` | resolved | Specified separate throwaway workflow rehearsal file differing only in reading synthetic PR-head evidence rather than `refs/remotes/origin/main`, plus green `workflow_dispatch` on the L-1 commit as L-1 exit criterion. |
| `R4-m9` | `§11.3, §12.1` | resolved | Restricted local immutability snapshot to `--git-dir` (`HEAD`, `index`, `FETCH_HEAD`, `ORIG_HEAD`) + branch ref + tags; scoped `--git-common-dir` `config`/`hooks/` checks to `CI=true` only. |
| `R4-m10` | `§3, §6.1, §6.2.3, §11.2, §12.1, §16.1, §16.7, §18, §19` | resolved | Fixed `"six"` -> `"seven"` tools + `accepted_w9.py` and `13` vs `14` non-code-owned count; recorded `W9-T7` unit-lane departure from `06v:230` (Owner Point F + addendum row); marked superseded mechanisms in `§18`–`§19`. |
| `R4-m11` | `§6.2.3, §16.1` | resolved | Stated Option I1-narrow reach accurately: `reader.py:37` -> `store.lock` -> 5 `store/` modules (`durability`, `anchor`, `writer`, etc.), cutting 90-day commits from `14` to `8` at most or forking Windows handle-anchor code. |
| `R4-i1` | `§6.2.2, §6.5, §10.3, §12.1` | resolved | Applied Rule 0.2 (i)–(iv) checks at `baselines[0]` creation (`walk-baseline.json`) and in PR `admission-controls`. |
| `R4-i2` | `§7.5, §14, §16.11` | resolved | Stated honestly in Option K1 that PR-time `check_conventions_legacy_locks.py` runs from PR head and judges itself when a non-code-owned closure module edits in the same PR. |
| `R4-i3` | `§2.3, §5.3, §14, §16.3, §16.8` | resolved | Put re-recording `wp9-4-1-record.md:114,130` (`13 passed`, `688.11s`) under Option A1 to Stephen (`§16.3`), noting WP9.4's 5–11 min runtime against Owner Point G. |
| `R4-i4` | `§6.2.2, §12.1` | resolved | Specified `git rev-parse :<path>` / `git hash-object --path=<path>` for LF-normalized blob calculation and added a CRLF working-copy test case. |
| `R4-i5` | `§6.2.3, §10.2, §16.1` | resolved | Stated Option I3 merge-then-update sequencing and expected push red window, plus authenticated `gh api` lookup in `tools/run_w9_pinned_detectors.py`. |
| `R4-i6` | `§6.2.2, §13.2, §16.2` | resolved | Changed `pre_baseline_dispositions_ref` to a hash-bound `P-09x` register ref; clarified in `HR-1` that `P1` entries on both `baselines` rows and records prove age, not authorship. |
| `R4-i7` | `§4.2.2, §21.1` | resolved | Recorded R4's live re-check (`16/16` pins, `56`/`32` newest `#448` `4ca375a3`, `commits/dbd54fe3/pulls` -> `#446`, `commits/4ca375a3/pulls` -> `#448`) in §21.1 item 8. |
| `R4-i8` | `Header, §1, §6.2.1, §13–§20` | resolved | Applied all five structural cuts from Follow-up 4 §3 (compact §18–§20, stripped heading tags, split §16 subsections, replaced 22-row table, removed restatements), cutting note size below 341,267 bytes. |

---

## 21. Appendix A: Verification

### 21.1 Reproducible verification commands and script outputs

All checks below are read-only against `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note` (at `dbd54fe382e7b2849d3f2038393cbdb4d709477b` or branch `HEAD`) and read-only GitHub REST API `GET` endpoints (`gh api`); no vault file prose was read, and `git status --short` was verified clean before editing. Prior independent verification: `wp9-5-note-r2-review-2026-11-21.md` §2 & §5 (`0c9a90ed`) reproduced first-parent walk facts, `CONVENTIONS.md` unit counts, ruleset pins, and bare-clone timings (`:218`; R2 did not reproduce item 5's closure); `wp9-5-note-r3-review-2026-11-21.md` §2, §6, and `R3-i4` (`092db1f1`) reproduced all 22 first-parent rows, the 15-existing closure & 13 recorded blobs, counts, 16/16 live pins, YAML/`bash -n`, and synthetic U-4 execution; `wp9-5-note-r4-review-2026-11-22.md` §0, §2, §6, and `R4-i7` (`48b5e935`) reproduced §21.1 items 2–6 and 8–10, YAML/`bash -n`, synthetic U-4 execution, all `610` citation occurrences, and pinned-tree isolation + heredoc checks. *(Revision 5 itself has not yet undergone a fifth independent review.)*

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

`rulesets/20822054` returned HTTP 200 (`id: 20822054`, `name: "P-049 Gate 6 main merge admission"`, `enforcement: "active"`, `conditions.ref_name.include: ["refs/heads/main"]`, `pull_request` `required_approving_review_count: 0`, `require_code_owner_review: true`, `required_review_thread_resolution: true`, `allowed_merge_methods: ["squash"]`, `required_status_checks` `strict_required_status_checks_policy: true` with all 4 contexts carrying `integration_id: 15368`, `merge_queue` `SQUASH` 1-by-1 `ALLGREEN`, `non_fast_forward`, `bypass_actors: [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}]`). `rule-suites?time_period=month` is a sliding 30-day window (`57` / `33` bypass initially; `58` / `34` after `#448` `4ca375a3`; `56` / `32` at `2026-11-21T23:03Z` once `bb9d91d4` aged out, re-verified by R3 `wp9-5-note-r3-review-2026-11-21.md:99` and R4 `wp9-5-note-r4-review-2026-11-22.md:108`, where `commits/dbd54fe3/pulls` -> `#446` and `commits/4ca375a3/pulls` -> `#448`).

**9. Stdlib-only AST check across the 15 existing closure modules + `python -S -P` scratch isolation test (`R4-m7`, base Python `3.13.5`):**

```powershell
@'
import ast, os, pathlib, subprocess, sys, tempfile
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
probe = """import importlib, os, research_system, research_system.legacy.evidence, sys, tools, tools.w9_segmentation
bad = {}
for m in ("research_system.cli", "tools.check_merge_admission", "yaml", "pytest"):
    try:
        importlib.import_module(m)
        bad[m] = "UNEXPECTED_IMPORT"
    except ModuleNotFoundError as exc:
        bad[m] = type(exc).__name__
print({
    "exe": sys.executable,
    "rs_paths": list(research_system.__path__),
    "tools_paths": list(tools.__path__),
    "site_in_path": any("site-packages" in p.lower() for p in sys.path),
    "wt_in_path": any(os.path.normcase(os.getcwd()) == os.path.normcase(os.path.abspath(p or ".")) for p in sys.path),
    "blocked": bad,
})
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

Confirmed `Non-stdlib imports in 15 existing closure modules: []`; both `script` (`python -S -P .../probe_iso.py`) and `module` (`python -S -P -m tools.probe_iso`) invocations from `cwd=wt` exited `0`, resolved `research_system.__path__` and `tools.__path__` solely inside `<td_path>`, kept `site-packages` and the worktree checkout off `sys.path`, and blocked `research_system.cli`, `tools.check_merge_admission`, `yaml`, and `pytest` with `ModuleNotFoundError`.

**10. Representative 6-call Option C1 walk timings (~1 mo `60`, ~3 mo `178`, ~5.5 mo `320` first-parent commits backward from `dbd54fe3`, excluding live `gh api` PR lookups; `R4-M1`):**

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

Measured local 6-call stand-in timings:
- `1_month_60` (`60` commits, `6` guarded): `14.05s` (`1x` post-merge, measured) / `24.04s` (`2x` PR compare, measured separately)
- `3_months_178` (`178` commits, `12` guarded): `34.46s` (`1x`, measured) / `68.92s` (`2x`, `2 × 1x`-scaled)
- `5.5_months_320` (`320` commits, `22` guarded): `62.84s` (`1x`, measured) / `125.68s` (`2x`, `2 × 1x`-scaled)
(Because Option C1 starts `baselines[0]["baseline_commit"]` at or after L-1, these backward slices model representative interval sizes without real Rules 0–3 Python evaluation or `gh api` calls.)

### 21.2 Statements marked `UNVERIFIED` (pre-code gates for the reviewing session)

Every statement in this design note that cannot be verified without running a GitHub Actions workflow under `GITHUB_TOKEN`, reading the live vault `Computational-Log.md` bytes, running an isolated scratch-store test on Stephen's machine, checking GitHub repository variable write permissions, or running the full walk on hosted `windows-latest` is listed here and gated in §15.1:

1. **`UNVERIFIED-1` (U-3 probe, §4.2.2, §15.1 item 1):** The HTTP status codes, `X-Accepted-GitHub-Permissions` headers, and pinned JSON body key presence returned to a GitHub Actions `GITHUB_TOKEN` (under `permissions: contents: read` and under `permissions: contents: read, pull-requests: read`) for:
   - `GET repos/ZK-Theory/TDL/rulesets/20822054`
   - `GET repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=day&per_page=5` (expected HTTP 403/404 per `tools/check_bypass_merges.py:20-21`, which decides D-8)
   - `GET repos/ZK-Theory/TDL/commits/dbd54fe382e7b2849d3f2038393cbdb4d709477b/pulls`
2. **`UNVERIFIED-2` (U-4 handle-bound reader and segmenter dry run on the live `833,453`-byte vault file, §4.3.3 item 2, §15.1 item 2):** The output of running standalone scratch script `u4_dry_run.py` (`root_checks` booleans from §4.3.2, `handle_bound_read(resolved_vault, "04-Methods/Computational-Log.md")`, and both `segment(raw, "computational_log_entry")` functions) on the current `833,453`-byte live file (`link_count == 1`, `file_facts`, `row_counts`, and `blockers == []`).
3. **`UNVERIFIED-3` (Unconditional pre-code single scratch-store test timing profile and operator-machine weekly D-5 run, §12.3, §15.1 item 4):** The wall-clock timing of a single existing WP9.3/WP9.4 scratch-store integration test run alone on Stephen's machine (`P-087` item 7, **unconditionally required before WP9.5 code dispatch**, §15.1 item 4), and end-to-end execution of the weekly operator-machine D-5 workflow against the live vault and control store via `tools/run_w9_pinned_detectors.py` after L-0b/L-1.
4. **`UNVERIFIED-4` (Option I3 `W9_DETECTOR_PIN` GitHub repository Actions variable write permissions, §10.2, §15.1 item 3, §16.1):** Which repository roles on `ZK-Theory/TDL` (`admin` vs `maintain`/`write`) can create, edit, or delete repository Actions variables (`vars.W9_DETECTOR_PIN`) was not verified against live repository settings or documentation permitted here; Stephen must confirm variable write permissions before relying on Option I3 as an out-of-tree trust anchor.
5. **`UNVERIFIED-5` (Hosted `windows-latest` full-walk and closure-PR compare wall times + unwritten `tools/` stdlib compliance, §6.2.2, §12.3, §15.1 item 5; `R4-M1`, `R4-m7`):** Actual hosted `windows-latest` wall-clock time running real Rules 0–3, `.apm/tracker.md` H1 segmentation checks, and live `gh api` PR lookups for both the `1x` post-merge walk and the `2x` closure-PR verdict comparison (over representative ~60, ~178, and ~320-commit intervals), together with verifying stdlib-only imports across the 6 not-yet-written runtime `tools/` modules (enforced once written by `test_detector_closure_is_stdlib_only`). Bounded by the `600s` stop rule (§15.2 item 5).
