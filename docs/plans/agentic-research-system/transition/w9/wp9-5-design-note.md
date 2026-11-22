# WP9.5 Design Note — W9 Detectors (W9-D5)

| Field | Value |
|---|---|
| Date | 2026-11-21 |
| Status | **Revision 4, for independent adversarial review. Nothing in it is implemented.** |
| Package | `06v` WP9.5 — "Detectors (W9-D5)" (`docs/plans/agentic-research-system/implementation/06v-w9-implementation-plan.md:470-503`) |
| Authority | Decision register entry `P-089` (`docs/plans/agentic-research-system/03-decisions-and-open-questions.md:6071-6146`) |
| Base | `origin/main` at `dbd54fe382e7b2849d3f2038393cbdb4d709477b` (`[PIPELINE] P06: WP9.4-2 follow-up: the independent review's Minor findings (P-088 item 5) (#446)`) |
| Worktree / Branch | `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note` on branch `docs/w9-wp9-5-design-note` |
| Prior reviews | Revision 1 (`65363e27`): `docs/plans/agentic-research-system/reviews/wp9-5-note-r1-review-2026-11-21.md` (`edb9acc6`; `REWORK REQUIRED`: 1 Blocking, 12 Major, 14 Minor, 6 Info)<br>Revision 2 (`0c9a90ed`): `docs/plans/agentic-research-system/reviews/wp9-5-note-r2-review-2026-11-21.md` (`3cf35bec`; `REWORK REQUIRED`: 0 Blocking, 5 Major, 16 Minor, 6 Info)<br>Revision 3 (`092db1f1`): `docs/plans/agentic-research-system/reviews/wp9-5-note-r3-review-2026-11-21.md` (`1bd4ecff`; `REWORK REQUIRED`: 0 Blocking, 3 Major, 13 Minor, 4 Info) |
| Not authorized | WP9.5 code, WP9.6, WP9.7, live operations L-0 to L-5 (including L-0b and L-1), creating or binding the real control store, registering or observing any real file, or any write to a legacy file, `main`, or the vault (`03-decisions-and-open-questions.md:6127-6135`) |
| Verification scope (`R2-m4`, `R3-m7 (c)`) | **What was checked and how:** the cited `research_system/`, `tools/`, `tests/`, `.github/`, `pyproject.toml`, `CONVENTIONS.md`, `06v`, `W9`, and `03-decisions-and-open-questions.md` ranges were read directly at `dbd54fe382e7b2849d3f2038393cbdb4d709477b`. Read-only `git`, `gh api` GET, and Python checks in §21.1 verified the 22-commit first-parent walk (`4b143c92..dbd54fe3`), `CONVENTIONS.md` counts, ruleset `20822054` pins (`integration_id: 15368`), bare-clone timings, the 15-module AST closure over existing files, Form (A) blob assembly (`uv sync --locked --no-install-project --offline`, `14.6s`, `PYTHONSAFEPATH=1`, in-closure OK / out-of-closure `ModuleNotFoundError`), and the 320-commit stand-in walk (`23.11s`). Earlier review verification: `wp9-5-note-r2-review-2026-11-21.md` §2 & §5 reproduced the 22-commit walk, `CONVENTIONS.md` counts, ruleset pins, and bare-clone timing (`:218`); `wp9-5-note-r3-review-2026-11-21.md` §2 & §6 reproduced all 22 rows, the 15/20/22 AST closure and 13 recorded blobs, `CONVENTIONS.md` counts, 16/16 live ruleset pins, YAML parsing / `bash -n`, and synthetic U-4 script execution.<br>**What was NOT verified in this session:** the live U-4 metadata read (`2026-11-21T21:06:44Z`) was run earlier by the reviewing session on Stephen's authorization (§4.3.3); this authoring session did not run the CI `GITHUB_TOKEN` U-3 probe (`UNVERIFIED-1`), the U-4 handle-bound reader/segmenter dry run against the live vault (`UNVERIFIED-2`), a single scratch-store M-6/O-13 test timing profile on Stephen's machine or the weekly operator-machine D-5 run (`UNVERIFIED-3`), or GitHub's permission rule for who can write repository variables under Option I3 (`UNVERIFIED-4`) (§15.1, Appendix A §21.2). |

---

## 1. What this note settles

WP9.5 builds the W9 detectors (`06v:470-503`; `W9` §4.4, `docs/plans/agentic-research-system/design/09-migration-compatibility-and-pilot.md:191-202`): the checks that detect when something writes a registered legacy file, writes under `results/` outside `results/ars/`, modifies a locked legacy item of `CONVENTIONS.md`, or alters a legacy entry in the vault's `04-Methods/Computational-Log.md`.

For every mechanism in WP9.5, this note specifies:
- what it reads (with exact Git plumbing or handle-bound filesystem reads);
- the exact decision rule;
- what it writes or reports;
- how it fails (always closed, non-zero exit, with an exact locating `ERROR:` code and message);
- where it runs (CI, the operator machine, or a scratch-clone/byte-copy test);
- its negative control (`recorded_read` or `watched_to_fail`); and
- its automated test.

| Handover §3 item | Settled in | Summary |
|---|---|---|
| 1. Scope, package boundary, and protected identities | §2 | No W9 command, runtime-binding row, ledger append site, schema, or `tools/w9_segmentation.py` byte changes; no D-4 is expected. Explicitly separates new `tools/` helpers from any option that touches `research_system/legacy/`. |
| 2. The ruleset read (`main_ruleset`, `recorded_read`) | §4.1 | Reads ruleset `20822054` configuration and `rulesets/rule-suites` history for `refs/heads/main`, pins one-at-a-time squash merge and status-check invariants, enforces the 30-day rule-suites window ceiling, and records canonical output SHA-256 before every batch and at L-1. |
| 3. U-3 (`GITHUB_TOKEN` ruleset, rule-suites, and `commits/<sha>/pulls` probe + D-8 fallback) | §4.2, §15.1 | Runnable pre-merge `pull_request` probe specification covering `rulesets/20822054`, `rulesets/rule-suites`, and `commits/<sha>/pulls` under `contents: read` and `pull-requests: read`; exact `06v:571` / `P-064` item 8 (`03-decisions-and-open-questions.md:4232-4233`) D-8 fallback. |
| 4. Post-merge first-parent detector (`tools/check_legacy_writes.py` & `.github/workflows/legacy-write-detector.yml`) | §6 | Content-pinned Form (A) blob assembly (`git cat-file blob` + `uv sync --locked --no-install-project`), AST-verified import closure, time-indexed evidence (`P1` manifest, `C` records), hash-bound decision refs, Rule 0 over evidence/closure/workflow/top-level `walk-baseline.json` + appended `baselines` rows, append-only `acknowledged` (with late Rule 3 `shared-surface-changes.json` check), full re-walk from `baselines[0]["baseline_commit"]` + dual-tool pin-advance diff, `git diff-tree -r --no-renames -z <P1> <C>`, retry/hint PR mapping, Rules 1–3, verified 22-commit inventory (`4b143c92..dbd54fe3`). |
| 5. Registration manifest export (M-6) | §5 | `tools/export_w9_registration_manifest.py` projects `state["records"]["legacy_path_registration"]` via `_legacy_projection` (`research_system/cli.py:1648-1659`) and `_legacy_current_binding` (`cli.py:1662-1684`) to `.research-system/evidence/w9/registration-manifest.json` (`"w9-registration-manifest/2"` under Option A1) before each batch's first observation; `--check` and integration test prove store-to-manifest equality at `binding.binding["git_head"]`. |
| 6. Shared-surface rule (O-32, detector half, Rule 3) | §6.5, §16 (Owner Points A, D) | Identifies `shared_enforcement_surface` contracts at `P1`, checks the W9 §4.3 owner note and `.research-system/evidence/w9/shared-surface-changes.json` at `C` (and requires the late change-list entry at head for Rule 3 acknowledgements), and sets out Options D3 (recommended blob-keyed freshness, `"w9-shared-surface-changes/2"`), D1, and D2 for resolving the squash-merge SHA contradiction between `06v:90-91,212,479-481` and `research_system/legacy/evidence.py:231-238` + `acceptance.py:135`. |
| 7. `CONVENTIONS.md` legacy-lock check (`tools/check_conventions_legacy_locks.py`) | §7, §16 (Owner Points J, K) | `segment(raw, "conventions_unit")` (`w9-segmentation/1.0.0`) against baseline commit `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (blob `4620c71607ca3a06c6df3b8e96a6bddffc783960`); provisional 9-section (`68`-unit) partition vs L-0b `ACCEPTED_CONVENTIONS_CLASSIFICATION` constant keyed on `(anchor_text, unit_hash)` (`segmentation.py:391-402`) and protected by Rule 0 + Control N7; bullet/paragraph insertion-only check and structural-byte policy (`HR-6`), plus PR-lane choice (Owner Point K). |
| 8. Vault Computational-Log detector (`tools/check_legacy_log_baseline.py`) and D-5 cadence | §8, §16 (Owner Points E, J) | Compares live `04-Methods/Computational-Log.md` against accepted `w9-cl-export/1` baseline and `ACCEPTED_CL_EXPORT[-1]["classified_list"]` (`research_system/legacy/accepted_w9.py:86-88`, 1-based ordinals); closes on `recheck_cl_export` `void == True`; tested against synthetic fixtures before L-0b; settles D-5 cadence gate at batch start and acceptance, owner reset, weekly PR + `advance-binding` cost, and self-attestation limit. |
| 9. U-4 (operator machine vault path & read-only dry run) | §4.3, §15.1 | Records the live `2026-11-21T21:06:44Z` U-4 metadata read (`833,453` bytes, SHA-256 `73fcbe83...`); specifies the explicit detector-side junction refusal (`Path.is_symlink()`, `Path.is_junction()`, and `resolve(strict=True)` outside `repository_root`) and the pre-code scratch-script dry run (`u4_dry_run.py`, including printed §4.3.2 root-check booleans). |
| 10. Detector-controls file (`.research-system/evidence/w9/detector-controls.json`) | §9 | Control runner binds each detector tool's Git blob and `closure_blobs` map with isolated Git config (`GIT_CONFIG_NOSYSTEM`, `GIT_CONFIG_GLOBAL`, `-c core.autocrlf=false -c commit.gpgsign=false`) and pinned dates into canonical transcripts, producing `w9-detector-controls/1`. |
| 11. Merging is not going live (`P-089` item 3) | §10, §16 (Owner Points I, F) | `.github/workflows/legacy-write-detector.yml` merges with `on: workflow_dispatch:` only, full-history checkout (`fetch-depth: 0`), content-pinned Form (A) blob assembly, and operator wrapper `tools/run_w9_pinned_detectors.py`; `L1_LIVE = False` tripwire constant in `tests/tools/test_w9_detectors.py` runs in a real PR lane under Option F1 (with I1 protecting `L1_LIVE`), loaded via `yaml.BaseLoader`. |
| 12. Where the controls run (`P-089` item 4; `06v` O-13; W9-T7) | §11 | Scratch clones (`git clone --bare --local --no-hardlinks`, measured at 1.71–1.79s) and byte copies under `tmp_path`; W9-T7 replay of `5df0c001` and `811d5a2b` in `tests/tools/test_w9_detectors.py` deriving touched paths via `git diff-tree`; checkout-scoped `--no-optional-locks` immutability snapshot comparing the checked-out branch ref and tag list rather than shared ref files. |
| 13. Tests and test-time budget | §12, §16 (Owner Points F, G) | W9-T7 moved under `tests/tools/test_w9_detectors.py` (`admission-controls` PR lane), W9-T19 (`unit`), M-6/O-13 (`integration` + `@pytest.mark.slow`, accurate `affected_research_tests.py` + `research-system-suite.yml` lane), Rule 0/closure/Form (A) assembly/N7 controls, unconditional pre-code single-store profile (`§15.1` item 4), and 5-minute G1 baseline (`P-087` item 7). |
| 14. Research assurance | §13 | Machine-checkable claims (preventive for CODEOWNED paths under I1, detective for non-CODEOWNED closure modules) vs human-review-only claims (`HR-1`–`HR-6`, including `CONVENTIONS.md` structural exceptions). |
| 15. Claims for review | §14 | 16 numbered load-bearing claims covering trust-root boundary (preventive vs detective), Form (A) content pin + full re-walk + dual-tool pin-advance diff, `acknowledged` (including Rule 3 late entry), time-indexed evidence, Rule 0, Rule 1 exclusions, record keying, allowance kinds, PR mapping, control-run mechanics, and WP9.3 boundary. |
| 16. Stop rules for the code package | §15 | `06v` §8 (`06v:610-620`) stop rules plus WP9.5 preconditions (U-3 recorded with pinned keys, U-4 dry run recorded via `u4_dry_run.py`, Owner Points I–K decided in `P-090`, unconditional single scratch-store test timing profile, plus pre-L-1 workflow rehearsal) and WP9.5-specific stop rules. |
| 17. Owner points | §16 | Eleven owner decisions (**I** first—since B, C, and the L-1 guard depend on it—then **C, A, B, D, E, F, G, H, J, K**), each with options, recommendation, and exact impact on accepted code or documents. |
| 18. Change logs and Verification appendix | §17, §18, §19, §20, §21 | Revision history (§17), revision 1 -> 2 log (§18), revision 2 -> 3 log (§19), complete finding-by-finding revision 3 -> revision 4 log (§20), and Verification appendix with reproducible commands and `UNVERIFIED` pre-code items (§21). |

---

## 2. Scope, package boundary, and protected identities

### 2.1 Deliverables in WP9.5

Under `06v` §5 (`06v-w9-implementation-plan.md:470-503`) and `P-089` (`03-decisions-and-open-questions.md:6091-6118,6141-6143`), WP9.5 delivers:

1. **The registration manifest exporter and store-equality verifier (M-6, `06v:470-473`):**
   - `tools/export_w9_registration_manifest.py` (**new**): calls `_legacy_projection` (`research_system/cli.py:1648-1659`) and `_legacy_current_binding` (`research_system/cli.py:1662-1684`) read-only to export `.research-system/evidence/w9/registration-manifest.json` (`w9-registration-manifest/2` under Option A1, updating `research_system/legacy/evidence.py:37,40,114-131`) and, in `--check` mode, verifies 1:1 set equality between the store's `state["records"]["legacy_path_registration"]` mapping (`research_system/legacy/replay/reducers.py:70,571`) and the committed manifest at `binding.binding["git_head"]` (`research_system/cli.py:1714`).
2. **The post-merge first-parent detector and workflow (`W9-D5`, `O-9`, `O-10`, `O-32`, `06v:189-190,212,474-490`):**
   - `tools/check_legacy_writes.py` (**new**): walks `git --no-replace-objects rev-list --first-parent --reverse <walk_start>..<head>`, checks **Rule 0** (evidence, closure, workflow, top-level `walk-baseline.json`, and appended `baselines` rows + pin-advance verdict diff), **Rule 1** (registered legacy files against the manifest at first parent `P1` and W9 §4.2 record at commit `C`), **Rule 2** (`results/` outside `results/ars/` against W9 §4.2 record at `C`), **Rule 3** (`shared_enforcement_surface` contracts against the manifest at `P1` and `.research-system/evidence/w9/shared-surface-changes.json` + W9 §4.3 owner note at `C`), append-only `acknowledged` exemptions (with late change-list entry requirement for Rule 3), and checks ruleset `20822054` and `rulesets/rule-suites` in local pre-batch mode (and in CI if U-3 permits; otherwise under D-8 fallback).
   - `.github/workflows/legacy-write-detector.yml` (**new**): Windows-only (`runs-on: windows-latest`) workflow committed in WP9.5 with `on: workflow_dispatch:` only so merging WP9.5 does **not** activate automatic detection on `main` before L-1 (§10); when dispatched (or triggered after L-1), assembles `$RUNNER_TEMP/w9-detector` from `baselines[-1]["detector_closure_blobs"]` (`git cat-file blob`, including `pyproject.toml` and `uv.lock`) + `uv sync --locked --no-install-project` before executing the detectors.
3. **The `CONVENTIONS.md` legacy-lock check (`W9-D5`, `O-12`, `06v:192,491-492`):**
   - `tools/check_conventions_legacy_locks.py` (**new**): verifies that `CONVENTIONS.md` preserves every legacy unit from baseline commit `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (blob `4620c71607ca3a06c6df3b8e96a6bddffc783960`, 33,645 bytes, SHA-256 `d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589`, pinned in `CONVENTIONS_LOCK`, `research_system/legacy/reader.py:43-49`) under `segment(data, "conventions_unit")` (`w9-segmentation/1.0.0`, `research_system/legacy/segmentation.py:429-488` and `tools/w9_segmentation.py:461-518`), reading any post-L-0b reclassification strictly from Git at the constant `ACCEPTED_CONVENTIONS_CLASSIFICATION` (`research_system/legacy/accepted_w9.py`, **new field**, keyed on `(anchor_text, unit_hash)`).
4. **The vault Computational-Log baseline detector (`W9-D5`, `O-11`, `D-5`, `D-7`, `06v:191,493-496,567,569`):**
   - `tools/check_legacy_log_baseline.py` (**new**): verifies that `--vault-root` is the real vault directory (never a symlink/junction or a path inside `repository_root`), reads `04-Methods/Computational-Log.md` via `handle_bound_read` (`research_system/legacy/reader.py:140-206`), segments the whole file via `segment(data, "computational_log_entry")` (`research_system/legacy/segmentation.py:429-488`), verifies `recheck_cl_export` returns `"void": False`, and compares every legacy-classified item and structural block against the accepted `w9-cl-export/1` baseline export (`research_system/legacy/evidence.py:277-362`) and its classified list (`ACCEPTED_CL_EXPORT`, `research_system/legacy/accepted_w9.py:86-88`).
5. **The detector negative-control runner and pinned operator-machine wrapper (`O-13`, `06v:193,497-502,603-604`; `R3-m2`):**
   - `tools/run_w9_detector_controls.py` (**new**): executes the `recorded_read` control for `main_ruleset` and the `watched_to_fail` negative controls on scratch clones and byte copies for `post_merge_first_parent`, `vault_computational_log`, and `conventions_repository_check` under isolated Git config (`GIT_CONFIG_NOSYSTEM`, `GIT_CONFIG_GLOBAL`, `-c core.autocrlf=false -c commit.gpgsign=false`), producing `.research-system/evidence/w9/detector-controls.json` (`w9-detector-controls/1`, `research_system/legacy/evidence.py:38,41,59-64,133-154`).
   - `tools/run_w9_pinned_detectors.py` (**new**, `R3-m2`): operator-machine wrapper for pre-batch and weekly runs (`06v:603-604`); verifies `walk-baseline.json` at `origin/main` (and `W9_DETECTOR_PIN` under Option I3), assembles `detector_closure_blobs` into a temporary directory with `uv sync --locked --no-install-project` and `PYTHONSAFEPATH=1`, and invokes `check_legacy_writes.py`, `check_conventions_legacy_locks.py`, `check_legacy_log_baseline.py`, and `--verify-watched-to-fail` from that assembled tree rather than the working checkout.
6. **Tests (`W9-T7`, `W9-T19`, `06v:230,242,503`; `R3-m4`):**
   - `tests/tools/test_w9_detectors.py` (**new**, `unit`, running in `.github/workflows/ci.yml` `admission-controls`): includes `W9-T19`, `W9-T7` scratch-clone replay of `5df0c001` and `811d5a2b` (`R3-m4`), Form (A) pin-assembly test (`R3-m12`), AST import-closure coverage, Control N7, and all per-detector positive and negative controls on byte copies and small synthetic Git repositories.
   - `tests/research_system/integration/test_w9_wp9_5_detectors.py` (**new**, `slow`, `integration`): covers scratch-store `M-6` store-to-manifest equality and `O-13` end-to-end control generation (`R3-m4`).

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
     - `compute_detector_import_closure(repo_root, entry_scripts)` (**new**, in `tools/_w9_detector_evidence.py`): runs an AST walk over the runtime detector/control/wrapper scripts (`check_legacy_writes.py`, `check_conventions_legacy_locks.py`, `check_legacy_log_baseline.py`, `run_w9_detector_controls.py`, `run_w9_pinned_detectors.py`, `_w9_detector_evidence.py`) transitively across `research_system` and `tools` to derive the exact 21-module runtime closure (`6` new `tools/` files + `15` existing repository modules verified at `dbd54fe38`; plus `tools/export_w9_registration_manifest.py`, `.github/workflows/legacy-write-detector.yml`, `pyproject.toml`, and `uv.lock` = `25` blobs in `detector_closure_blobs`, §6.2.3). (`tools/export_w9_registration_manifest.py`, which runs on the operator machine against `C:/Users/steph/TDL-ARS-G7-Control` and imports `research_system/cli.py`, has a 161-module closure and is not assembled in CI, while pinned/code-owned as an operator-machine tool.)
     - `read_real_vault_log(vault_root, repository_root)` (**new**, in `tools/check_legacy_log_baseline.py`): performs the root-level symlink/junction refusal (`vault_root.is_symlink() or vault_root.is_junction()`) and post-`resolve(strict=True)` containment check against `repository_root.resolve(strict=True)` before calling `handle_bound_read(vault_root, "04-Methods/Computational-Log.md")` (§4.3.2).
   - **What touches `research_system/legacy/` (and existing WP9.4 tests) only if Stephen selects the corresponding Owner Point in §16:**
     - **Owner Point A (Option A1, Recommended):** Bumps `REGISTRATION_MANIFEST_FORMAT` to `"w9-registration-manifest/2"` in `research_system/legacy/evidence.py:40,114-131` (`require_registered`), closes each entry on the 5 keys `{"root_kind", "root_id", "normalized_path", "role", "source_identity_kind"}` (matching the uniform `/2` policy with Option D3; no live `/1` manifest exists before L-1), checks `(role, source_identity_kind)` when present on `registration`, and compares membership at line 129 on the three identity keys `("root_kind", "root_id", "normalized_path")`. Because `require_registered` is an accepted WP9.3 gate at `LR-015` and the 3-key manifest shape is also constructed/appended by `tests/research_system/unit/test_w9_evidence.py`, `tests/research_system/integration/w9_runtime_harness.py:451-466`, `test_w9_wp9_4_1_runtime.py:95-109`, and `test_w9_wp9_4_2_runtime.py:86-100` (`R3-m13`), selecting Option A1 requires a **dated WP9.3 amendment, an independent review, and a decision-register entry** (`P-090`). Because no WP9.4 production code changes (only test fixture manifest builders move from 3 keys to 5 keys), WP9.4's review is not reopened (covered by the WP9.3 amendment review; Option A2 avoids touching any WP9.3 code or WP9.4 tests).
     - **Owner Point D (Option D3 Recommended, or D1):** Modifies `research_system/legacy/evidence.py:42,221-252` (`SHARED_SURFACE_CHANGES_FORMAT = "w9-shared-surface-changes/2"` and `_change_entries`) and `research_system/legacy/acceptance.py:121-136` (`check_change_list`). Because `check_change_list` is an accepted WP9.3 gate at `LR-016`/`LR-020` (not merely a WP9.5 detector reader), selecting Option D3 or D1 requires a **dated WP9.3 amendment, an independent review of that change, and a decision-register entry** (§6.5, §16 D).
     - **Owner Point E (Option E1 Recommended):** Adds `VAULT_DETECTOR_RUNS` and `require_vault_detector_cadence` in `research_system/legacy/evidence.py` and calls it from `prepare_proposal` (`LR-003` and `LR-016`, `research_system/legacy/preparers.py:686-690,702-706`), `prepare_observation` (`LR-015`, `preparers.py:1215-1218`), and `check_environment` (`LR-016` and `LR-020`, `research_system/legacy/acceptance.py:147-152`). Because hooking `preparers.py` and `acceptance.py` modifies accepted WP9.3 preparer gates, Option E1 also requires a **dated WP9.3 amendment and independent review** (§8.4, §16 E).
     - **Owner Point J (Option J1 Recommended):** Adds `ACCEPTED_CONVENTIONS_CLASSIFICATION: tuple[MappingProxyType[str, Any], ...] = ()` to `research_system/legacy/accepted_w9.py` (mirroring `ACCEPTED_CL_EXPORT` at `:86-88`; leaf module not in `IMPORTER_MODULES`, populated only at L-0b; no D-4 trigger).

2. **`.github/CODEOWNERS`, `GATE_FILES`, and `test_ci_platform_policy.py` boundary (`.github/CODEOWNERS:1-24`; `tests/tools/test_ci_platform_policy.py:341-375`; `CONVENTIONS.md:713-729`):**
   - `.github/CODEOWNERS` currently lists **exactly eight paths**, all owned by `@stephendor` (`.github/CODEOWNERS:14-24`; `GATE_FILES` in `tests/tools/test_ci_platform_policy.py:341-350`):
     1. `/.github/CODEOWNERS`
     2. `/.github/merge-admission.yml`
     3. `/.github/workflows/merge-admission.yml`
     4. `/.github/workflows/merge-admission-sweep.yml`
     5. `/.github/workflows/ci.yml`
     6. `/tools/check_merge_admission.py`
     7. `/.claude/hooks/admin-bypass-guard.sh`
     8. `/.claude/settings.json`
   - `test_every_gate_file_exists_and_has_a_code_owner` (`tests/tools/test_ci_platform_policy.py:364-369`) asserts `(REPO_ROOT / path).is_file()` for every `GATE_FILES` entry and `rules.get(f"/{path}")`; `test_codeowners_names_no_file_outside_the_gate` (`:372-374`) asserts exact set equality `set(_codeowners_rules()) == {f"/{path}" for path in GATE_FILES}`; `.github/CODEOWNERS:1-12` and `CONVENTIONS.md:713-729` (inside successor section `## ARS Foundation Governance`, `CONVENTIONS.md:614-783`) record Stephen's 2026-09-11 scope decision that CODEOWNERS owns only the merge-admission gate. Therefore, extending CODEOWNERS under **Owner Point I1** to the 10 file patterns (`/.github/workflows/legacy-write-detector.yml`, 7 `tools/` scripts/wrappers, `/tests/tools/test_w9_detectors.py`, and `/research_system/legacy/accepted_w9.py` per `R3-m2` / `test_w9_wp9_3_binding_head.py:199-217`) plus directory pattern `/.research-system/evidence/w9/` requires (`R3-m9`): (a) updating `.github/CODEOWNERS:1-12` header as well as the entries, (b) landing all 9 new files in the same PR as the `.github/CODEOWNERS` edit (with `test_every_gate_file_exists_and_has_a_code_owner` asserting rule presence only — **not** `.is_dir()` — for directory pattern `/.research-system/evidence/w9/` since `.research-system/evidence/` has no tracked files at `dbd54fe3`), (c) updating `test_codeowners_names_no_file_outside_the_gate` and its docstring, (d) amending `CONVENTIONS.md:713-729` (`P-090`), and (e) noting that every bypass PR modifying CODEOWNED paths requires a `Bypass reason:` line in the PR body (`tools/check_bypass_merges.py:41,135`).
   - Note that `tests/tools/test_ci_platform_policy.py` and `tools/check_test_commit_literals.py` are **not** in `.github/CODEOWNERS` or `GATE_FILES`.
   - Under `tests/tools/test_ci_platform_policy.py:286-303` (`test_every_tools_and_contracts_test_runs_in_a_workflow`), every `tests/tools/test_*.py` module must appear in a workflow step's `run:` script (or `CONTROL_EXEMPTIONS`). To actually run on every pull request and merge-group evaluation (rather than merely satisfying string presence in a `workflow_dispatch`-only workflow that never runs on PRs), `tests/tools/test_w9_detectors.py` must be added to `.github/workflows/ci.yml`'s `admission-controls` job (`ci.yml:166-216`) and `ADMISSION_CONTROL_MODULES` (`test_ci_platform_policy.py:175-229`), following the exact precedent of `tests/tools/test_w9_segmentation.py` (`ci.yml:210`; `test_ci_platform_policy.py:226`).
   - Because `.github/workflows/ci.yml` is owned by `@stephendor` in `.github/CODEOWNERS:18` and `.claude/hooks/admin-bypass-guard.sh:13-18,67-68` forbids any agent session from bypassing merge rules, **Stephen performs the merge of any PR that edits `.github/workflows/ci.yml`, `.github/CODEOWNERS`, or (under I1) WP9.5's detector/evidence files himself** (Owner Points I and F, §16).

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
| `06v:230` | `W9-T7` | Replay `5df0c001` and `811d5a2b` on a scratch clone with a fixture registry listing the files they touched; assert both are flagged (`slow`, `integration`). | §11.2, §12.1 |
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

#### 4.2.2 Design of a runnable read-only U-3 probe (`R1-M11`)

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

#### 4.3.1 Verified repository facts on the vault path and why `tools/check_legacy_log_baseline.py` needs its own root-junction check (`R1-M1`, `R1-M2`)

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

#### 4.3.3 Recorded U-4 metadata read (`2026-11-21T21:06:44Z`) and pre-code reader+segmenter dry-run gate (`R1-m8`)

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
      5. **dated WP9.3 amendment and blast-radius scope (`R2-m11 (d)`, `R3-m13`):** because `require_registered` is an accepted WP9.3 gate at `LR-015` (`prepare_observation`) and the 3-key manifest shape is built/appended by `tests/research_system/unit/test_w9_evidence.py`, `tests/research_system/integration/w9_runtime_harness.py:451-466`, `test_w9_wp9_4_1_runtime.py:95-109`, and `test_w9_wp9_4_2_runtime.py:86-100`, selecting Option A1 requires updating those four test/harness files alongside `evidence.py:40,114-131` and recording a dated WP9.3 amendment, an independent review, and a decision-register entry (`P-090`), in the same manner as Options D3 and E1. Because WP9.4 production code is untouched (only the shared manifest fixture builders add `"role"` and `"source_identity_kind"`), Option A1 does not reopen WP9.4's review (covered by the WP9.3 amendment review; Option A2 avoids touching any WP9.3/WP9.4 file).
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

### 6.1 Time-indexed evidence evaluation, trust-root boundary, and why reading at `<head>` alone is broken (`R1-B1`, `R2-M1`, `R2-M3`, `R3-M1`)

**Trust-root boundary (`R2-M1`, `R3-M1`):** There is no trust root inside the repository content that can prevent a merged commit from changing the detector scripts, their imported `research_system/` helpers, or the workflow file on `main` (GitHub runs `.github/workflows/*.yml` from the pushed commit, and ZK-Theory is on GitHub Free without organization-level required workflows; `CONVENTIONS.md:721-725`). Therefore, against self-editing of the detector, its evidence, or its triggers, enforcement splits clearly:
- **Preventive at merge admission (Owner Point I1):** `.github/CODEOWNERS` (`@stephendor`) covers `.github/workflows/legacy-write-detector.yml`, all 7 WP9.5 `tools/` detector/control/exporter/wrapper/helper files, `tests/tools/test_w9_detectors.py`, `research_system/legacy/accepted_w9.py` (`R3-m2`), and directory pattern `/.research-system/evidence/w9/` (optionally paired with out-of-tree `vars.W9_DETECTOR_PIN` under **Option I3**). No PR can touch any code-owned path without Stephen's approval or admin bypass merge.
- **Detective post-merge (the remaining closure modules):** The 13 remaining `research_system/` closure modules plus `tools/w9_segmentation.py` (which also has its D-4 blob pin) are not CODEOWNED under I1-default (unless added in §16 I); Rule 0.3 detects any unauthorized edit to those modules post-merge. **Option I2 does not close R1-B1 scenarios 4 and 5** and leaves CODEOWNED trust-root protection absent (`§16 I`).

Subject to that trust root, Revision 1's single-snapshot design (`<head>` only) suffered four structural defects:
1. **Atomic disarm:** A single squash commit `C` could delete a file's entry from `registration-manifest.json` and modify the file in the same commit; at `<head>` the file is not in the manifest, so Rule 1 would not fire.
2. **Retroactive false positives:** When a file (such as `.apm/tracker.md`) is registered at time `T1` after L-1 baseline `T0`, legitimate commits between `T0` and `T1` touched that file before it was registered; reading the manifest at `<head>` would flag those pre-registration commits forever.
3. **Retroactive blessing:** Reading `legacy-write-records.json` at `<head>` would let a later PR add a record for an earlier unauthorized commit and turn a red detector green, violating `06v:212,479-481` (*"The PR making the change carries its own entry"*).
4. **Detector self-edit / baseline shift:** Running `tools/check_legacy_writes.py` or its imported modules from `<head>`'s checkout or reading a baseline constant from `<head>`'s script would let a commit weaken the detector or its transitive dependencies in the same merge.

**Revision 4 fixes defects 1–3 via time-indexed evidence and Rule 0, and closes defect 4 operationally via Owner Point I1 + content-pinned Form (A) execution:**

| Evidence / artifact | Evaluated at which commit during the walk of commit `C` (with first parent `P1`)? | Why |
|---|---|---|
| `registration-manifest.json` (Rules 1 and 3) | **At `P1` (`<P1>:.research-system/evidence/w9/registration-manifest.json`)** (plus any new entries added in `C` itself, via the union $\text{Manifest}(P_1) \cup \text{Manifest}(C)$) | A file registered at `P1` is protected against removal+edit in `C` (atomic disarm is impossible because `F` is in $\text{Manifest}(P_1)$). Conversely, a commit `C` that landed **before** `F` was registered in the manifest has $F \notin \text{Manifest}(P_1) \cup \text{Manifest}(C)$, so pre-registration commits never suffer retroactive false positives! |
| `legacy-write-records.json` (Rules 1, 2, and 3) | **At `C` (`<C>:.research-system/evidence/w9/legacy-write-records.json`)** | The PR that makes an authorized W9 §4.2 or §4.3 change must carry its own record inside commit `C` (`06v:212,479-481`). No later commit after `C` can retroactively bless an unrecorded write in `C`. |
| `shared-surface-changes.json` (Rule 3, `O-32`) | **At `C` (`<C>:.research-system/evidence/w9/shared-surface-changes.json`)** under Option D3/D1 (or at `<head>` for a valid Rule 3 acknowledgement, `R3-M3`) | Under Option D3 (Recommended), the PR changing a `shared_enforcement_surface` carries its own blob-keyed entry at `C`. A Rule 3 `acknowledged` entry also requires `<head>:shared-surface-changes.json` to hold the late entry before the walk passes (`R3-M3`). |
| Monotonicity of evidence & governed closure (**Rule 0**) | **Every step `P1 -> C` across `baselines[0]["baseline_commit"]..<head>`** | See §6.5 Rule 0: no commit may delete or mutate an existing entry in any evidence file or top-level field of `walk-baseline.json`, append an invalid `baselines` / `acknowledged` / `ruleset_gap_acknowledgements` row, or modify any path in `detector_closure_blobs` without a same-PR `baselines` append and pre-existing hash-bound `P1` decision ref. |
| The detector executable and its full import closure (`R2-M1`, `R2-M3`, `R3-M1`) | **Assembled by content into `$RUNNER_TEMP/w9-detector` from `baselines[-1]["detector_closure_blobs"]`** (`git cat-file blob`, plus `uv sync --locked --no-install-project`) | The **workflow** (and local wrapper `tools/run_w9_pinned_detectors.py`) reads `baselines[-1]["detector_closure_blobs"]` from `walk-baseline.json` at `MAIN_TIP` (checking `vars.W9_DETECTOR_PIN` under Option I3), writes **only** those recorded Git blobs (including `pyproject.toml` and `uv.lock`) into a clean temp directory, installs third-party dependencies with `uv sync --locked --no-install-project`, and runs the detectors with `PYTHONPATH="$DETECTOR_DIR"` and `PYTHONSAFEPATH=1`. Because no other repository file exists inside `$DETECTOR_DIR`, any unpinned `research_system` or `tools` import raises `ModuleNotFoundError`/`ImportError`, and a closure edit can carry its updated blob map in the **same PR** (`R3-M1`). |

---

### 6.2 The walk baseline (`walk-baseline.json`), acknowledged violations, pin-advance verification, import closure, and post-freeze first-parent commit inventory (`R1-B1`, `R1-M3`, `R1-M12`, `R2-M1`, `R2-M2`, `R2-M3`, `R2-m1`, `R2-m14`, `R3-M1`, `R3-M2`, `R3-M3`, `R3-m10`, `R3-m11`; Owner Point C)

#### 6.2.1 Complete verified inventory of first-parent commits touching guarded prefixes between `4b143c92` and `dbd54fe3` (`R2-m1`)

Running `git --no-replace-objects rev-list --first-parent --reverse 4b143c9225035cc29e37351445f1c3a4ab09ceb1..dbd54fe382e7b2849d3f2038393cbdb4d709477b` yields **320** first-parent commits on `main` (Appendix A §21.1). Across all 320 commits, exactly **22** first-parent commits touched a path equal to `CONVENTIONS.md` or under `results/`, `papers/`, `contracts/`, or `.apm/`:

| # | First-parent SHA on `main` (parents) | Date (`%cI`) | PR / Subject | Guarded-prefix paths touched (`old_blob -> new_blob`) | Classification / G7-A & W9 disposition |
|---|---|---|---|---|---|
| 1 | `02ebcaf6` (2 parents; `p1=c2b02b77`) | `2026-07-18T17:46:11+01:00` | `#125` (`Merge pull request #125 from stephendor/run/mcbif-deprivation-scale-coherence`) | Added 3 files under `results/poverty_tda_mcbif/`: `deprivation_scale_coherence_2026-07-16.json`, `resource_preflight_deprivation_scale_coherence_2026-07-16.json`, `staged_launch_plan_deprivation_scale_coherence_2026-07-16.json` | Pre-W9 MCBIF poverty run queued before/at freeze (`W9` §3.2, `09-migration-compatibility-and-pilot.md:143-147`) |
| 2 | `5795a18b` (2 parents; `p1=e68a7c3d`, `p2=1af52f6d`) | `2026-07-19T00:04:52+01:00` | `#129` (`Merge pull request #129 from stephendor/run/h6-markov2-landscape-cells`; second parent `1af52f6d` is `[DATA] P01-B: commit Markov-2 alpha=1 cell JSONs (H6 ruling)`) | Added 2 files under `results/trajectory_tda_integration/post_audit/` (`markov2_alpha_sweep_cell_bhps_alpha1_B1000_L5000_seed42_2026-06-08.json`, `..._usoc_alpha1_..._2026-06-15.json`); modified `results/trajectory_tda_integration/stage1/SUPERSEDED.md` (`34b82105 -> ee7557ad`) | Owner-ruled H6 result commit (`W9` §4.1 row 3, `09-migration-compatibility-and-pilot.md:165`) |
| 3 | `9016b663` (2 parents; `p1=1e9052a8`) | `2026-07-26T02:59:13+01:00` | `#168` (`Merge pull request #168 from stephendor/codex/wp6-3-contract-remediation`) | Modified `contracts/manifests/research-assurance.yaml`, `contracts/stochastic-tests/markov-order-provenance.yaml`, `contracts/topology-invariants/null-operation-changes-ph-input.yaml`; added `contracts/stochastic-tests/markov-order-provenance-json-validation.yaml` | ARS-lane WP6.3 contract remediation (`W9` §4.1 row 4, `:166`) |
| 4 | `2111ce62` (2 parents; `p1=7470dbd2`) | `2026-07-26T12:43:59+01:00` | `#169` (`Merge pull request #169 from stephendor/codex/wp6-3-semantic-remediation`) | Modified `contracts/stochastic-tests/monte-carlo-permutation-p-value.yaml` (`fc216bdb -> 8554b71b`) | ARS-lane WP6.3 contract remediation (`W9` §4.1 row 4, `:166`) |
| 5 | `7347ae95` (2 parents; `p1=6bfc8dd9`) | `2026-07-28T01:23:50+01:00` | `#172` (`Merge pull request #172 from stephendor/pipe/contract-lf-checkout-attributes`) | Modified `CONVENTIONS.md` (`4620c716 -> fecfc1da`) | Pure successor insertion in `CONVENTIONS.md` (`### Contract artifacts are LF-only...` in `## Computational Environment`) |
| 6 | `9795ee5f` (2 parents; `p1=268d597a`) | `2026-07-28T18:33:00+01:00` | `#178` (`Merge pull request #178 from stephendor/docs/wp6-3-review-chain-records`) | Modified `CONVENTIONS.md` (`fecfc1da -> 1ae78f42`) | Pure successor insertion in `CONVENTIONS.md` (`## ARS Foundation Governance`) |
| 7 | `f52f52f4` (2 parents; `p1=7b206fbd`) | `2026-07-28T19:25:25+01:00` | `#183` (`Merge pull request #183 from stephendor/docs/wp6-3-review-chain-records`) | Modified `CONVENTIONS.md` (`1ae78f42 -> f20c8daa`) | Pure successor insertion in `CONVENTIONS.md` (`## ARS Foundation Governance`) |
| 8 | `5df0c001` (1 parent; `p1=a426b731`) | `2026-08-05T05:32:38+01:00` | **Direct push, no PR** (reuses subject `Merge pull request #215 from stephendor/codex/wp64-brief-evidence-r2`; actual `#215` merged at `a426b731`) | Modified 7 `results/` files (plus 4 non-`results/` files): `results/panel_methodology/bhps_nonoverlap/bhps_nonoverlap_reanalysis_2026-06-09.json`, `results/trajectory_tda_bhps/01_trajectories.json`, `results/trajectory_tda_bhps/stage1/bhps_headline_frozen_corrected_2026-07-14.json`, `results/trajectory_tda_integration/01_trajectories.json`, `results/trajectory_tda_integration/05_analysis.json`, `results/trajectory_tda_integration/stage1/headline_vintage_materiality_corrected_2026-07-14.json`, `results/trajectory_tda_integration/stage1/w2_fallback_audit_2026-07-14.json` | **Unauthorized direct push (`W9` §4.1 row 6, `:168`); W9-T7 replay subject 1** |
| 9 | `811d5a2b` (1 parent; `p1=1d3a0769`) | `2026-08-07T00:12:09+01:00` | **Direct push, no PR** (`[PIPELINE] manifest blob-sha updates: b9-om-gmm-inputs, t128-inputs, t138-w2-gap-closure-inputs`) | Modified 3 `contracts/manifests/input-provenance/` files (plus 6 other files): `b9-om-gmm-inputs.yaml`, `t128-inputs.yaml`, `t138-w2-gap-closure-inputs.yaml` | **Unauthorized direct push (`W9` §4.1 row 6, `:168`); W9-T7 replay subject 2** |
| 10 | `b132406e` (2 parents; `p1=811d5a2b`, `p2=3bfb279c`) | `2026-08-08T22:23:06+01:00` | `#219` (`[PIPELINE] P00: restore accepted WP6.4 provenance boundary`) | Restored all 7 `results/` files from `5df0c001` and all 3 `contracts/manifests/input-provenance/` files from `811d5a2b` back to their pre-`5df0c001` / pre-`811d5a2b` blobs | Revert/restoration PR (`W9` §4.1 row 6, `:168`) |
| 11 | `1dbf6b7b` (1 parent; `p1=7cb1380b`) | `2026-09-10T16:49:18Z` | `#277` (`[DECISION] SYS: re-enable repo-wide CI with lint blocking, tests advisory (#277)`) | Modified `CONVENTIONS.md` (`f20c8daa -> 15377fe4`) and 3 `papers/` scripts: `papers/P01-A-JRSSA/drafts/sections/compute_table1_effects.py` (`0bcdac9a -> 0ee246bf`), `papers/shared/scripts/income_vars_check.py` (`5475beed -> ed607f2d`), `papers/shared/scripts/read_jbstat_dict.py` (`230f01f1 -> 6477467c`) | Repo-wide Ruff cleanup (`W9` §4.1 row 1, `:163`) + successor section in `CONVENTIONS.md` |
| 12 | `85c7a02e` (1 parent; `p1=4501d860`) | `2026-09-11T16:13:49Z` | `#278` (`[PIPELINE] SYS: re-derive merge admission at the exact candidate (#278)`) | Modified `CONVENTIONS.md` (`15377fe4 -> 72332a52`) | Successor update in `CONVENTIONS.md` |
| 13 | `eba3fe69` (1 parent; `p1=8d6a5dd8`) | `2026-10-06T16:51:50+01:00` | `#334` (`[PIPELINE] G6: land the 06q retirement fence and the retired-imperatives gate (#334)`) | Added `contracts/process-invariants/retired-plan-imperatives-quoted.yaml` (`00000000 -> b227480f`) | ARS planning contract (`W9` §4.1 row 5, `:167`; not a legacy file) |
| 14 | `65f4da4b` (1 parent; `p1=9f49af60`) | `2026-10-07T08:28:20+01:00` | `#345` (`[DECISION] SYS: pin the pre-commit ruff to the uv.lock ruff (v0.14.9) (#345)`) | Modified `CONVENTIONS.md` (`72332a52 -> 272ef07a`) | Pure successor insertion in `CONVENTIONS.md` (`## Computational Environment`) |
| 15 | `452352ff` (1 parent; `p1=4d867d85`) | `2026-10-17T08:00:26+01:00` | `#368` (`[DECISION] P06: record L5, A6, A7 and step 3 batches 1-3 of the 06s Phase 5 run (P-058) (#368)`) | Modified `.apm/tracker.md` (`8101faa5 -> c2716092`) | Session Working Note append recording 06s Phase 5 batches (`W9` §4.1 row 2, `:164`) |
| 16 | `3a14a97c` (1 parent; `p1=1b8ed812`) | `2026-10-17T16:10:48+01:00` | `#376` (`[DECISION] SYS: require no review producer at merge admission; drop Codex (#376)`) | Modified `CONVENTIONS.md` (`272ef07a -> 0a6cd1b8`) | Successor update in `CONVENTIONS.md` |
| 17 | `53b7c5be` (1 parent; `p1=6e3ad7f3`) | `2026-10-21T13:19:54+01:00` | `#384` (`[DECISION] SYS: no thread-finality waiver; guidance matches the producer config (#384)`) | Modified `CONVENTIONS.md` (`0a6cd1b8 -> baceabd6`) | Successor update in `CONVENTIONS.md` |
| 18 | `e3519ba7` (1 parent; `p1=3fa437a1`) | `2026-10-22T15:28:58+01:00` | `#388` (`[EXPLORE] P00: record the 2026-10-21 worktree sweep in the Tracker (#388)`) | Modified `.apm/tracker.md` (`c2716092 -> e791d95d`) | **Post-G7-A (`3fa437a1`)** worktree-sweep Working Note append in `.apm/tracker.md` (`R1-M5`, `R1-M12`) |
| 19 | `633ed58e` (1 parent; `p1=4a5a1300`) | `2026-10-27T16:23:00Z` | `#401` (`[PIPELINE] P06: W11 byte-identity test and the SUPERSEDED.md Markov-2 correction (review 2026-10-27, D3 + E1) (#401)`) | Modified `results/trajectory_tda_integration/stage1/SUPERSEDED.md` (`ee7557ad -> 84403ce2`) | **Post-G7-A (`3fa437a1`)** reviewed Markov-2 correction to `SUPERSEDED.md`, accounted for in `wp9-3-design-note.md:978` (`P-079`) (`R1-M12`) |
| 20 | `14a81b84` (1 parent; `p1=4307bd6a`) | `2026-11-08T23:10:04Z` | `#419` (`[DECISION] P00: merges go through the queue (A2) and a Gate 7+ intake list (H), from system review 2026-11-03 (#419)`) | Modified `CONVENTIONS.md` (`baceabd6 -> 14d39755`) *(plus ARS plan + `gate7-intake-deferrals.md`, outside legacy prefixes)* | Pure successor insertion in `CONVENTIONS.md` (`R2-m1`) |
| 21 | `1fba78aa` (1 parent; `p1=321c111a`) | `2026-11-10T21:14:45Z` | `#425` (`[PIPELINE] SYS: review 2026-11-10 campaign, hand-built service, bypass audit, nightly recurrence, results gate (#425)`) | Modified `CONVENTIONS.md` (`14d39755 -> 1db03819`) *(plus CI/tools/tests outside legacy prefixes)* | Pure successor insertion in `CONVENTIONS.md` (`R2-m1`) |
| 22 | `a6a98966` (1 parent; `p1=baea2c13`) | `2026-11-12T12:43:39Z` | `#433` (`[EXPLORE] P00: record the 2026-11-12 worktree sweep in the Tracker (#433)`) | Modified `.apm/tracker.md` (`e791d95d -> 509d20bf`) | **Post-G7-A (`3fa437a1`)** worktree-sweep Working Note append in `.apm/tracker.md` (`R1-M5`, `R1-M12`) |

*(Summary: `22` first-parent commits total across `4b143c92..dbd54fe3`: `9` `CONVENTIONS.md`-only PRs `#172, #178, #183, #278, #345, #376, #384, #419, #425` + `1` mixed PR `#277`, `3` `.apm/tracker.md` PRs `#368, #388, #433`, `3` ARS contract PRs `#168, #169, #334`, `3` pre-W9 / ruled / reviewed results PRs `#125, #129, #401`, `2` unauthorized direct pushes `5df0c001, 811d5a2b`, and `1` revert `#219`; reproduced in `wp9-5-note-r2-review-2026-11-21.md:137-148` and `wp9-5-note-r3-review-2026-11-21.md:107-117`, reproducible command in Appendix A §21.1.)*

#### 6.2.2 Committed append-only walk-baseline ledger, acknowledged violations, and full re-walk (`R1-B1`, `R1-M12`, `R2-M1`, `R2-M2`, `R2-m14`, `R3-M1`, `R3-M2`, `R3-M3`, `R3-m10`, `R3-m11`; Owner Point C)

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
           "pyproject.toml": "09d9faa91faff9956bfdd90c849e1287a331e9b6",
           "uv.lock": "87a3862cad49411c8c0164b95bb0bee47c9556a7",
           "tools/check_legacy_writes.py": "<40-hex>",
           "tools/check_conventions_legacy_locks.py": "<40-hex>",
           "tools/check_legacy_log_baseline.py": "<40-hex>",
           "tools/run_w9_detector_controls.py": "<40-hex>",
           "tools/run_w9_pinned_detectors.py": "<40-hex>",
           "tools/export_w9_registration_manifest.py": "<40-hex>",
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
         "pre_baseline_dispositions_ref": "docs/plans/agentic-research-system/transition/w9/wp9-5-design-note.md#621-complete-verified-inventory-of-first-parent-commits-touching-guarded-prefixes-between-4b143c92-and-dbd54fe3-r2-m1"
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
   *(All top-level keys are closed and protected by Rule 0 item 2 (`R2-M1`, `R3-M1`, `R3-M2`): `format` is immutable; `d8_rule_suites_limit_decision_ref` is immutable once non-null; `baselines`, `acknowledged`, and `ruleset_gap_acknowledgements` are strictly append-only. `baselines[0]` carries `{"baseline_commit", "recorded_in_decision_ref", "detector_closure_blobs", "pre_baseline_dispositions_ref"}`; every appended pin-advance row `baselines[k]` for $k \ge 1$ carries `{"recorded_in_decision_ref", "detector_closure_blobs"}`.)*
2. **Baseline, disposed vs walked intervals, and Form (A) content pin (`R2-M1`, `R2-m14`, `R3-M1`, `R3-m10`):**
   - **`baselines[0]["baseline_commit"]` fixes the original walk start** (invariant across the lifetime of the ledger; `R2-M1`). Because under ruleset `20822054`'s squash merge queue the L-1 PR's parent SHA on `main` is not known when the PR branch is written (`R2-m14`), `baselines[0]["baseline_commit"]` may be **any known first-parent ancestor of the L-1 commit on `main`** (e.g., the already-merged WP9.5 code PR's merge commit, or `dbd54fe38`).
   - **Disposed vs walked intervals and L-1 refresh rule (`R3-m10`):**
     - **Pre-baseline interval `(4b143c92, baselines[0]["baseline_commit"]]`:** Every guarded commit up through `baselines[0]["baseline_commit"]` is a pre-baseline commit disposed ahead of L-1 (`§6.2.1` covers `4b143c92..dbd54fe3`). Because `§6.2.1` stops at `dbd54fe3`, at L-1 the author/operator must run the §21.1 item 3 first-parent walk over `(dbd54fe3, baselines[0]["baseline_commit"]]` and record the disposition of any newly observed guarded commit in that span in the L-1 decision entry (`baselines[0]["recorded_in_decision_ref"]` / `pre_baseline_dispositions_ref`).
     - **Walked interval `(baselines[0]["baseline_commit"], head]`:** Every first-parent commit strictly after `baselines[0]["baseline_commit"]` up to `<head>` (including any commits merged between `baseline_commit` and L-1, and all post-L-1 commits) is walked on every run and must pass Rules 0–3 or hold a valid `acknowledged` entry.
   - **`baselines[-1]["detector_closure_blobs"]` fixes the active tool by content (`R3-M1`, Form A):** Because Git blob IDs are SHA-1 content hashes known deterministically before a PR merges under the squash queue, a PR that updates any closure file carries its new `baselines` row with the exact new blob hashes and a pre-existing (`at P1`) hash-bound `recorded_in_decision_ref` in the **same PR** (validated strictly by Rule 0 item 2 & item 3, §6.5).
   - **`--baseline` and `--head` CLI lockouts (`R2-M1`):** Unless `--ruleset-check skip` is also given, passing `--baseline` or `--head` causes `tools/check_legacy_writes.py` to exit **`2`** immediately (`ERROR: post_merge_first_parent: --baseline and --head overrides are permitted only with --ruleset-check skip`). In production/CI mode, the tool always walks `baselines[0]["baseline_commit"]..<head>` at `head = refs/remotes/origin/main`.
   - **First-parent chain membership check (stronger than `merge-base --is-ancestor`):**
     `git merge-base --is-ancestor <baseline> <head>` returns true even if `<baseline>` is on a side branch merged into `main`'s second parent. Therefore, `tools/check_legacy_writes.py` walks `git --no-replace-objects rev-list --first-parent <head>` and verifies that `baselines[0]["baseline_commit"]` (and every `commit` / `source_commit` referenced as on `main`) lies **on `<head>`'s first-parent chain**. Otherwise exit `1`:
     `ERROR: post_merge_first_parent: commit <sha> is not on the first-parent chain of <head>`
3. **Clearable true positives: the append-only `acknowledged` list (`R2-M2`, `R3-M3`; Owner Point C):**
   - When an honest unrecorded write (a true positive) lands on `main`, deleting it from history or modifying historic blobs violates Git immutability and Rule 0; leaving the walk stuck red forever trains operators to ignore CI (`R1-M5`, `R2-M2`).
   - Instead, an owner decision entry (`### P-09y`) on `main` can explicitly acknowledge and dispose of the violation (for instance by recording retroactive review or a clean follow-up revert PR), after which a PR commits an appended row to `walk-baseline.json["acknowledged"]`:
     `{"commit", "rule", "path", "old_blob", "new_blob", "disposition_ref": {"id", "source_path", "source_commit", "entry_sha256"}}`.
   - Validation (checked by Rule 0.2 at the commit `C_ack` that appended row `a`, and at walk time):
     1. `a["commit"]` lies on `<head>`'s first-parent chain strictly after `baselines[0]["baseline_commit"]`.
     2. `a["disposition_ref"]["source_commit"]` is strictly **after** `a["commit"]` (`is_ancestor(a["commit"], source_commit) and a["commit"] != source_commit`) and at or before `P1(C_ack)` (`is_ancestor(source_commit, P1)`), so the owner disposition cannot pre-date or be fabricated in the offending commit or in `C_ack` itself!
     3. At `<P1(C_ack)>`, the `### <id>` slice SHA-256 equals `entry_sha256`, and the slice names `a["commit"][:8]`, `a["rule"]`, `a["path"]`, `a["old_blob"][:8]`, and `a["new_blob"][:8]`.
     4. **Rule 3 late change-list entry requirement (`R3-M3`):** When `a["rule"] == "Rule 3"`, the acknowledgement is valid **only if** `<head>:.research-system/evidence/w9/shared-surface-changes.json` already contains an entry matching `(pr_number(a["commit"]), a["path"], a["old_blob"], a["new_blob"], affected_registrations)`. *Why a late entry is safe:* WP9.3's `check_change_list` (`research_system/legacy/acceptance.py:121-136`) reads `shared-surface-changes.json` at the control store's `git_head`, and appending the late entry to `shared-surface-changes.json` is an allowed append under Rule 0.2 — so adding the late entry ensures both the detector **and** WP9.3 closed-reference acceptance enforce `O-32` (`06v:212`). Without the entry at `<head>`, the detector fails closed (`ERROR: post_merge_first_parent: Rule 3 acknowledgement for <commit[:8]>:<path> requires a corresponding entry in shared-surface-changes.json at <head>`).
   - Exemption scope: the detector exempts **only** the exact tuple `(commit, rule, path, old_blob, new_blob)` (other files or rules touched in `commit` without an acknowledgement or §4.2 record still fail closed!) and prints the matched acknowledgements in `acknowledged_violations` in the JSON output.
4. **Full historical re-walk on every run and dual-tool pin-advance verdict diff (`R3-M2`; Owner Point C):**
   - Every run (CI and operator pre-batch wrapper) always walks the full interval `(baselines[0]["baseline_commit"], head]` using `baselines[-1]["detector_closure_blobs"]`. No stored verdict summary is trusted.
   - To guarantee that no approved tool advance (`baselines[k]` for $k \ge 1$, appended at commit `C_k`) can silently flip past verdicts from red to green without owner accountability (`R2-M2 (b)`, `R3-M2`):
     1. At each pin advance `baselines[k]` ($k \ge 1$), Rule 0.2 assembles `baselines[k-1]`'s recorded `detector_closure_blobs` into a temp directory (reusing `$DETECTOR_DIR`'s synced `.venv` if `pyproject.toml` and `uv.lock` blobs equal `baselines[k]`'s, otherwise running `uv sync --locked --no-install-project` there) alongside `baselines[k]`'s assembled tool.
     2. It walks `(baselines[0]["baseline_commit"], P1(C_k)]` under **both** `baselines[k-1]` and `baselines[k]` (with the same time-indexed evidence and `acknowledged` rows) and compares each commit's `(rule, path, outcome)` tuple.
     3. Every commit `V` in `(baselines[0]["baseline_commit"], P1(C_k)]` whose verdict differs between `baselines[k-1]` and `baselines[k]` **must** have `V[:8]` explicitly named in `baselines[k]["recorded_in_decision_ref"]`'s `### P-0xx` slice at `P1(C_k)` (satisfiable because `V` already merged before `C_k`). Otherwise the detector fails closed:
        `ERROR: post_merge_first_parent: Rule 0: pin advance changes verdicts at <commit_prefixes>`
     4. This comparison is recomputed from scratch on every run; no stored verdict summary is relied upon.
   - **Measured cost (§21.1 item 10):** A Python stand-in executing the full first-parent `git diff-tree -r --no-renames -z <P1> <C>` walk across all **320** commits in `4b143c92..dbd54fe3` ran in **`23.11s`** (`~0.07s`/commit) on this machine; each pin advance `baselines[k]` adds one re-walk over `(baselines[0]["baseline_commit"], P1(C_k)]` per run (plus ~`14.6s` `uv sync` only for advances that change `pyproject.toml`/`uv.lock`).

#### 6.2.3 Detector import closure computation, Form (A) exactness, closure cost, and operator-machine pinning (`R2-M3`, `R3-M1`, `R3-m2`, `R3-m3`)

To prevent any unpinned library module (`research_system/legacy/evidence.py`, `reader.py`, `segmentation.py`, `canonical.py`, etc.) from becoming an unguarded backdoor (`R2-M3`):
1. **Deterministic AST closure walker (`compute_detector_import_closure(repo_root, entry_scripts)` in `tools/_w9_detector_evidence.py`, **new**):**
   Parses Python ASTs (`ast.parse`, walking `ast.Import` and `ast.ImportFrom` including relative imports, restricted to top-level packages `research_system` and `tools`). Package `__init__.py` inclusion rule (`R3-M1`): whenever any imported module path `a.b.c` resolves under `research_system`, every ancestor package `__init__.py` (`research_system/__init__.py`, `research_system/legacy/__init__.py`, `research_system/store/__init__.py`) is added explicitly to the closure; `tools/` has no `__init__.py` and imports as a namespace package under `PYTHONPATH="$DETECTOR_DIR"`. Entry scripts walked are the **6** runtime `tools/` modules (`tools/check_legacy_writes.py`, `tools/check_conventions_legacy_locks.py`, `tools/check_legacy_log_baseline.py`, `tools/run_w9_detector_controls.py`, `tools/run_w9_pinned_detectors.py`, `tools/_w9_detector_evidence.py`).
2. **Verified existing-module closure at `dbd54fe38` (15 existing + 6 new runtime = 21 runtime modules + 4 build/CI/exporter entries = 25 blobs in `detector_closure_blobs`, Appendix A §21.1):**
   Across the existing seeds (`research_system/legacy/{reader,evidence,segmentation,export_recheck,accepted_w9}.py`, `research_system/canonical.py`, `tools/w9_segmentation.py`), the transitive AST closure at `dbd54fe38` comprises the **exact 15 existing Python files** shown in `walk-baseline.json["baselines"][0]["detector_closure_blobs"]` in §6.2.2 (including `research_system/__init__.py`, `research_system/legacy/__init__.py`, and `research_system/store/__init__.py`), plus the 6 new runtime `tools/` modules (`21` runtime modules total), plus `tools/export_w9_registration_manifest.py` (operator-machine exporter importing `research_system/cli.py`), `.github/workflows/legacy-write-detector.yml`, `pyproject.toml`, and `uv.lock` = **25 blobs** total in `detector_closure_blobs`.
3. **Why Form (A) guarantees exact closure (`R3-M1`, verified in §21.1 item 9) and enforcement boundaries:**
   - **Unit test in `tests/tools/test_w9_detectors.py`:** `test_recorded_detector_import_closure_covers_ast_walk` runs `compute_detector_import_closure` over the real detector/control/wrapper files and fails if any imported `research_system` or `tools` module is missing from `RECORDED_DETECTOR_CLOSURE` (in `tools/_w9_detector_evidence.py`) or, when `L1_LIVE is True`, from `walk-baseline.json["baselines"][-1]["detector_closure_blobs"]`.
   - **Form (A) runtime isolation (`R3-M1`):** Because `$RUNNER_TEMP/w9-detector` is populated strictly by `git cat-file blob` for paths in `detector_closure_blobs` and dependencies are synced with `uv sync --locked --no-install-project` (never editable-installing the full working tree) and executed with `PYTHONPATH="$DETECTOR_DIR"` + `PYTHONSAFEPATH=1`, any import of a `research_system` or `tools` module outside `detector_closure_blobs` immediately fails with `ModuleNotFoundError` / `ImportError` (verified in §21.1: `import research_system.cli` raised `ModuleNotFoundError` even from the repository CWD).
   - **Preventive vs detective boundary (`R3-M1`):** Under Owner Point I1, `.github/CODEOWNERS` prevents merges without Stephen's approval/bypass on `.github/workflows/legacy-write-detector.yml`, all WP9.5 `tools/` files, `tests/tools/test_w9_detectors.py`, `research_system/legacy/accepted_w9.py` (`R3-m2`), and `.research-system/evidence/w9/`. For the remaining `research_system/` closure modules (which are not code-owned unless Option I1 expands further) and `tools/w9_segmentation.py` (also guarded by D-4), enforcement is **detective**: an unrecorded edit turns `main` red on Rule 0.3 post-merge because `acknowledged` covers Rules 1–3 only (so every legitimate closure change must carry its same-PR `baselines` row under Form (A), and an unrecorded closure edit requires Stephen's intervention / revert).
4. **Operational cost of the closure rule (`R3-m3`):**
   Seven W9 PRs in the last 4 weeks (`31f675fe`, `23f8f737`, `6aeb3b31`, `baea2c13`, `cc81b733`, `95871b38`, `dbd54fe3`)—and 14 of 178 first-parent commits in 90 days—touched those 15 existing closure modules (`wp9-5-note-r3-review-2026-11-21.md:44`). After L-1, **every** PR modifying any module in `detector_closure_blobs` requires: (a) a pre-existing (`at P1`) hash-bound decision entry naming each changed path and `new_blob[:8]`, (b) a same-PR `baselines` append in `walk-baseline.json`, (c) a re-recorded `detector-controls.json` (since `--verify-watched-to-fail` binds `closure_blobs`), and (d) Stephen's bypass merge with a `Bypass reason:` line (`tools/check_bypass_merges.py:41,135`). Section 16 **Owner Point I** therefore lets Stephen weigh narrowing the closure by moving small detector-only reader helpers (`git_blob_id`, `handle_bound_read`, or `segment` wrappers) into `tools/` (**Option I1-narrow**) against keeping the 15-module shared closure (**Option I1-default**).
5. **Operator-machine pinning (`tools/run_w9_pinned_detectors.py`, `R3-m2`):**
   On the operator machine before every batch and weekly D-5 run (`06v:603-604`), the detectors do **not** run directly against the mutable working checkout; instead, Stephen runs `tools/run_w9_pinned_detectors.py`, which reads `origin/main:.research-system/evidence/w9/walk-baseline.json` (verifying `W9_DETECTOR_PIN` under Option I3 if configured), executes the exact same Form (A) blob assembly + `uv sync --locked --no-install-project` + `PYTHONSAFEPATH=1` isolation in a temporary directory, and invokes `check_legacy_writes.py`, `check_conventions_legacy_locks.py`, `check_legacy_log_baseline.py`, and `--verify-watched-to-fail` from that assembled tree. (`tools/export_w9_registration_manifest.py`, which exports M-6 via `research_system.cli`'s 161-module closure and checks equality against `binding.binding["git_head"]`, remains a code-owned CLI tool in `tools/` rather than inside the Form (A) runtime closure.)

---

### 6.3 First-parent diff semantics, PR mapping, and failure modes (`R1-m5`, `R1-m6`, `R1-i2`)

1. **Refusing shallow clones and non-first-parent baselines:**
   - `git --no-replace-objects rev-parse --is-shallow-repository` must equal `"false"` (matching `research_system/legacy/acceptance.py:89-90`).
   - `<baseline>` must lie on `<head>`'s first-parent chain (§6.2.2).
2. **Computing the first-parent diff for both 1-parent and 2-parent commits:**
   - For each commit `C` in `git --no-replace-objects rev-list --first-parent --reverse <baseline>..<head>`:
     - Query `git --no-replace-objects rev-list --parents -n 1 <C>`, yielding `<C> <P1> [<P2> ...]`.
     - Run `git --no-replace-objects diff-tree -r --no-renames -z <P1> <C>`.
     - Each NUL-delimited record yields `(old_mode, new_mode, old_blob, new_blob, status, path)`.
     - **Why explicit `<P1> <C>` is required:** Single-argument `git diff-tree -r <C>` prints nothing on a 2-parent merge commit (verified on `b132406e` in `wp9-5-note-r1-review-2026-11-21.md:299`); passing `<P1> <C>` compares `main`'s previous tree at `P1` against `C`'s tree for both 1-parent and 2-parent commits.
     - **Mode-only changes (`R1-i2`):** If a guarded file appears in `diff-tree -r --no-renames -z <P1> <C>` with `old_blob == new_blob` and `old_mode != new_mode` (a file-mode change with identical content bytes), it still enters Rule 1/2/3 evaluation. Because `legacy-write-records.json` requires `old_blob != new_blob` (§6.4), a mode-only change on a registered legacy file cannot be authorized by a §4.2 record and **fails closed** (`ERROR: post_merge_first_parent: mode-only change on guarded path '<path>' at commit <C> (<old_mode> -> <new_mode>) is prohibited`).
3. **Mapping each first-parent commit `C` to its PR (`R1-m5`, `R1-m6`):**
   - When commit `C` touches at least one guarded path (Rule 0, Rule 1, Rule 2, or Rule 3):
     1. **Primary lookup (`commits/<C>/pulls` with retry and backoff, `R1-m5`, `R2-i1`):**
        Calls `gh api repos/ZK-Theory/TDL/commits/<C>/pulls`. To guard against any transient empty response from GitHub's commit-to-PR index immediately after a squash push (precautionary; not observed in our reads), if the response is HTTP 200 with no PR matching `pull.get("merged_at") and pull.get("merge_commit_sha") == C`, the detector retries up to 3 times with exponential backoff (`1s`, `2s`, `4s`).
     2. **Subject-hinted fallback lookup (`pulls/<N>` verified by `merge_commit_sha == C`, `R1-m5`):**
        If `commits/<C>/pulls` still returns no match after retries, the detector inspects `C`'s commit subject line for a trailing `(#<N>)` or `^Merge pull request #(<N>) ` hint. If a candidate integer `<N>` is present, it queries `gh api repos/ZK-Theory/TDL/pulls/<N>` directly and accepts `<N>` **if and only if** `pull.get("merged_at")` is non-empty **and** `pull.get("merge_commit_sha") == C`.
        - Why this is unspoofable: The subject line is used strictly as an index hint to query `pulls/<N>`; GitHub's authoritative `pull["merge_commit_sha"] == C` check still decides whether PR `<N>` actually produced commit `C`. For `5df0c001` (whose subject says `Merge pull request #215...`), `pulls/215` has `merge_commit_sha == "a426b731..." != "5df0c001..."` (`wp9-5-note-r1-review-2026-11-21.md:299`), so the hint is rejected and `5df0c001` maps to `pr_number = None`!
     3. **Distinguishing API/transport failure (exit `2`) from an unmapped commit (exit `1`) (`R1-m5`):**
        - If `gh api` fails with a non-zero exit code, timeout, HTTP 4xx/5xx error, or malformed JSON, `tools/check_legacy_writes.py` exits **`2`** (matching `tools/check_bypass_merges.py:25`) with:
          `ERROR: post_merge_first_parent: GitHub API read failed while mapping commit <C>: <stderr_or_status>`
        - If the API succeeds (HTTP 200) and no merged PR has `merge_commit_sha == C`, `pr_number` is `None` and the detector exits **`1`** with `pr=none` in the Rule 0/1/2/3 violation message.
     4. **Test-only flags hard-locked behind `--ruleset-check skip` (`R1-m6`, `R2-M1`):**
        The flags `--baseline <sha>`, `--head <sha>`, `--pr-map <json>`, and `--manifest-file <json>` are **test-only** overrides for offline scratch-clone and unit tests. If **any** of `--baseline`, `--head`, `--pr-map`, or `--manifest-file` is passed when `--ruleset-check` is not `skip`, `tools/check_legacy_writes.py` immediately exits **`2`** before reading any commit (`ERROR: post_merge_first_parent: --baseline, --head, --pr-map, and --manifest-file are permitted only with --ruleset-check skip`). A unit test in `tests/tools/test_w9_detectors.py` parses `.github/workflows/legacy-write-detector.yml` and asserts that **none** of `--baseline`, `--head`, `--pr-map`, `--manifest-file`, `--ruleset-check skip`, or `--classified-locks` appears anywhere in the workflow file!

---

### 6.4 The W9 §4.2 record: format, evaluation at `C`, and provenance verification at `P1` (`R1-B1`, `R1-M5`, `R1-M10`, `R2-m10`; Owner Points B, H, and I)

- **Location:** `.research-system/evidence/w9/legacy-write-records.json` (format `"w9-legacy-write-records/1"`, added as a dated row in `06v-addendum-2026-11-10-w9-paths.md` under Owner Point B).
- **Evaluated at `C` (`R1-B1`):** When commit `C` (with first parent `P1`, mapped to `pr_number`) touches a guarded path, the detector reads `<C>:.research-system/evidence/w9/legacy-write-records.json`.
- **Provenance checks and conditional reliance on Owner Point I1 (`R1-M10`, `R2-m10`):**
  As `R2-m10 (c)` notes, `P1` ancestry proves only that a referenced decision entry or review was committed on `main` **before** PR `C`; it does not by itself prove Stephen authored them because `03-decisions-and-open-questions.md` and `docs/plans/agentic-research-system/reviews/` are not CODEOWNED and ruleset `20822054` has `required_approving_review_count: 0`. Therefore, **Option B1's tamper resistance is explicitly conditional on Owner Point I1** (CODEOWNERS `@stephendor` over `.research-system/evidence/w9/`, preventing any PR without Stephen's approval/bypass from adding a `legacy-write-records.json` entry).
  In addition (`R2-m10 (d)`), requiring `owner_note.source_commit` and `independent_review.review_commit` to precede PR `C` (at `P1`) is **stricter than W9 §4.2(b)** (`09-migration-compatibility-and-pilot.md:174-176`) and is this note's design reading (with Option B2 offered as the same-PR alternative under I1).
  1. **Pre-existing owner decision (`owner_note` verified at `P1`, exact matching grammar, `R2-m10 (a)`):**
     For `"repo_wide_change_4_2_b"`, `"owner_ruling_4_2_c"`, and `"shared_surface_4_3"`, `owner_note` must name:
     - `"decision_entry_id"`: `"P-0xx"` (regex `^P-[0-9]{3}[a-z]?$`),
     - `"source_path"`: `"docs/plans/agentic-research-system/03-decisions-and-open-questions.md"`,
     - `"source_commit"`: a 40-hex commit SHA that is an ancestor of **`P1`** (`is_ancestor(repo_root, source_commit, P1)` is `True`), and
     - `"entry_sha256"`: the SHA-256 of the exact `### P-0xx` section slice (from `### P-0xx` up to the next `\n### ` or EOF) in `<P1>:docs/plans/agentic-research-system/03-decisions-and-open-questions.md`. That slice must exist at `P1` and, for **every** entry `{normalized_path, old_blob, new_blob}` in `record["files"]`, contain the exact `normalized_path` string, `old_blob[:8]` (lowercase 8-char or 40-char prefix), and `new_blob[:8]` (lowercase 8-char or 40-char prefix) — matching the project's existing 8-char blob notation in the decision register (`fecfc1da`, `6024-6088`) with no undefined escape clause (`R2-m10 (a)`).
  2. **Pre-existing independent review bound to the change (`independent_review` verified at `P1`, `R2-m10 (b)`):**
     For `"repo_wide_change_4_2_b"` and `"shared_surface_4_3"`, `independent_review` must name:
     - `"review_path"`: `"docs/plans/agentic-research-system/reviews/<file>.md"`,
     - `"review_commit"`: a 40-hex commit SHA that is an ancestor of **`P1`** (`is_ancestor(repo_root, review_commit, P1)` is `True`), and
     - `"review_sha256"`: matching `sha256_hex` of `<P1>:<review_path>`, **and** the `<P1>:<review_path>` bytes must contain `owner_note["decision_entry_id"]` and every `{normalized_path, old_blob[:8], new_blob[:8]}` touched by the record so an unrelated historical review cannot satisfy `review_sha256` (`R2-m10 (b)`).
  3. **CODEOWNERS / Rule 0 protection (Owner Point I1, §16):**
     Owner Point I1 adds `.research-system/evidence/w9/` (directory pattern), `.github/workflows/legacy-write-detector.yml`, the six WP9.5 detector/control/exporter/helper modules, and `tests/tools/test_w9_detectors.py` to `.github/CODEOWNERS` (`@stephendor`), making every PR that writes `legacy-write-records.json` require Stephen's own code-owner review/bypass at merge admission.
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

### 6.5 Rules 0, 1, 2, and 3 of `tools/check_legacy_writes.py` (`R1-B1`, `R1-M4`, `R1-M5`, `R1-M6`, `R1-i1`, `R2-M1`, `R2-M2`, `R2-M3`, `R2-M4`, `R2-m4`, `R2-m11`)

For each first-parent commit $C \in (\text{baselines}[0][\text{"baseline\_commit"}], \text{head}]$ with first parent $P_1$ and changed file tuples $(m_{\text{old}}, m_{\text{new}}, b_{\text{old}}, b_{\text{new}}, \text{status}, p) \in \text{diff-tree}(P_1, C)$:

#### Rule 0 — Monotonicity of W9 evidence files and governed closure (`R1-B1`, `R1-M10`, `R2-M1`, `R2-M2`, `R2-M3`, `R2-M4`, `R3-M1`, `R3-M2`, `R3-M3`, `R3-m11`; Owner Point I)

1. **`registration-manifest.json` is strictly append-only:**
   If $P_1 \to C$ modifies or deletes `.research-system/evidence/w9/registration-manifest.json`, the detector parses the manifest at $P_1$ (if present at $P_1$) and at $C$. Every registration entry present at $P_1$ must remain present with identical fields at $C$. Deleting or altering an existing registration entry fails closed with:
   `ERROR: post_merge_first_parent: Rule 0 violation at commit <C>: registration-manifest.json deleted or modified existing registration entry <entry>`
2. **Evidence ledgers, all top-level fields + appended rows of `walk-baseline.json`, and the L-0b classification file (`R2-M1`, `R2-M2`, `R2-M4`, `R3-M1`, `R3-M2`, `R3-M3`, `R3-m11`):**
   - `legacy-write-records.json`, `shared-surface-changes.json`, and `vault-detector-runs.json` are strictly append-only on entries: every entry present at $P_1$ remains byte-identical at $C$, and any new entry appended to `legacy-write-records.json` at $C$ must have `entry["pr_number"] == pr_number(C)`.
   - Every top-level field of `walk-baseline.json` is governed: `format` (`"w9-walk-baseline/1"`) is immutable; `d8_rule_suites_limit_decision_ref` is immutable once non-null and any non-null value must pass the pre-existing (`at P1`) hash-bound decision-ref check naming `"D-8"` and `"rule-suites"`; `baselines`, `acknowledged`, and `ruleset_gap_acknowledgements` are strictly append-only.
   - **Every newly appended `baselines[k]` row ($k \ge 1$) at commit $C$ must satisfy (`R3-M1`, `R3-M2`):**
     (i) closed keys `{"recorded_in_decision_ref", "detector_closure_blobs"}` (no second `baseline_commit`);
     (ii) every entry `(p, expected_blob)` in `row["detector_closure_blobs"]` equals `git --no-replace-objects rev-parse <C>:<p>`;
     (iii) `row["recorded_in_decision_ref"]` passes the pre-existing (`source_commit` ancestor of $P_1(C)$) hash-bound slice check;
     (iv) that `### P-0xx` slice explicitly names every path added, removed, or changed relative to `baselines[k-1]["detector_closure_blobs"]` alongside its `new_blob[:8]` (or `"no blob change"` if identical, and `"rollback"` plus restored paths and `new_blob[:8]` if matching an earlier row's map); and
     (v) re-walking `(baselines[0]["baseline_commit"], P1(C)]` under both `baselines[k-1]` and `baselines[k]` reveals no commit whose verdict changed unless `V[:8]` is named in `recorded_in_decision_ref`'s slice (otherwise exit `1` with `ERROR: post_merge_first_parent: Rule 0: pin advance changes verdicts at <commit_prefixes>`).
   - **Every newly appended `ruleset_gap_acknowledgements` row ($C_{\text{gap}}$) (`R3-m11`):** must satisfy closed keys `{"previous_recorded_at", "acknowledged_through", "disposition_ref"}`, with `disposition_ref["source_commit"]` an ancestor of $P_1(C_{\text{gap}})$ and the hash-bound `### P-0xx` slice naming both `<previous_recorded_at>` and `<acknowledged_through>`.
   - **Every newly appended `acknowledged` row ($C_{\text{ack}}$) (`R2-M2`, `R3-M3`):** must satisfy `commit < source_commit <= P1(C_ack)` with slice verification (§6.2.2 item 3), and any `rule == "Rule 3"` row is valid **only if** `<head>:.research-system/evidence/w9/shared-surface-changes.json` contains a matching change-list entry (§6.2.2 item 3.4).
   - Once `ACCEPTED_CONVENTIONS_CLASSIFICATION` (`research_system/legacy/accepted_w9.py`) is populated at L-0b, the committed `CONVENTIONS.md` classification JSON path it pins cannot be modified or deleted (`R2-M4`).
   - Failure message: `ERROR: post_merge_first_parent: Rule 0 violation at commit <C>: evidence file '<path>' violated append-only, validation, or immutability invariants`
3. **`detector-controls.json` and the entire governed detector closure (`R2-M1`, `R2-M3`, `R3-M1`):**
   - Once `.research-system/evidence/w9/detector-controls.json` exists at $P_1$, it cannot be deleted at $C$, and any update must pass `require_detector_controls` (`research_system/legacy/evidence.py:133-154`) with `recorded_at` timestamps $\ge$ those at $P_1$.
   - If $P_1 \to C$ modifies or deletes **any** path listed in `walk-baseline.json` at $P_1$ (`baselines[-1]["detector_closure_blobs"]` evaluated at $P_1$, all 21 runtime modules + `tools/export_w9_registration_manifest.py` + `.github/workflows/legacy-write-detector.yml` + `pyproject.toml` + `uv.lock`, §6.2.3), commit $C$ must carry an appended `baselines` row in `<C>:.research-system/evidence/w9/walk-baseline.json` in the **same commit/PR** satisfying all five Rule 0 item 2 `baselines` checks (including pre-existing `P1` hash-bound decision ref naming each changed module path and `new_blob[:8]`, exact blobs at `C`, and dual-tool verdict-diff check). Otherwise fail closed with:
     `ERROR: post_merge_first_parent: Rule 0 violation at commit <C>: governed detector/closure path '<path>' modified without a valid same-PR baselines append and hash-bound pre-existing decision ref in walk-baseline.json`

#### Rule 1 — Registered `git_tracked` legacy files (`06v:477`; `W9:172-181`; `R1-B1`, `R1-M4`, `R1-M5`)

- **Manifest evaluated at `P1` (union `C`):** Let $\mathcal{M}(P_1, C) = \text{Manifest}(P_1) \cup \text{Manifest}(C)$ be the set of registration entries present in `registration-manifest.json` at $P_1$ or at $C$.
- **Exclusions from Rule 1 (`R1-M4`, `R1-M5`):**
  An entry $r \in \mathcal{M}(P_1, C)$ is **excluded** from Rule 1 if any of the following holds:
  1. `r["root_kind"] != "repository_root"` (vault registrations are `vault_root` and are not in the Git tree);
  2. `r["source_identity_kind"] != "git_tracked"` (`untracked_file` and `restricted_untracked_file` registrations—such as untracked `*.csv`, `*.pkl`, `.apm/memory/stage-NN/` logs, `.apm/bus/`, and `legacy_read_only_projection` under `.research-system/projections/legacy/`—are not tracked in Git);
  3. `r["role"] == "conventions_lock"` (`CONVENTIONS.md` is governed by the insertion-only check in `tools/check_conventions_legacy_locks.py` under W9 §4.4 and §7.3; §7);
  4. `r["role"] == "shared_enforcement_surface"` (governed by Rule 3 below);
  5. `r["role"] == "successor_results_root"` (`results/ars/`, where successor outputs are written; `W9:140-141`); or
  6. `r["role"] == "legacy_read_only_projection"` (`.research-system/projections/legacy/`, rebuilt by WP9.6's projector; `06v:518-520`).
- **Path matching rule for remaining `git_tracked` `repository_root` registrations:**
  A changed path $p$ in $\text{diff-tree}(P_1, C)$ matches a Rule-1 registration $r$ if:
  - `r["role"] != "legacy_manuscript_root"` and $\text{casefold}(p) == \text{casefold}(r[\text{"normalized\_path"}])$; OR
  - `r["role"] == "legacy_manuscript_root"` (e.g. `papers/P01-A-JRSSA/` or `papers/P01-B-JRSSB/`, `research_system/legacy/reader.py:51,289-299`) and $\text{casefold}(p)$ starts with $\text{casefold}(r[\text{"normalized\_path"}].\text{rstrip}("/")) + "/"$.
- **`.apm/tracker.md` Working Notes handling (`R1-M5`, Review §4 H; Owner Point H, §16):**
  If $p == \text{".apm/tracker.md"}$ and Stephen selects **Option H1 (Recommended)** in Owner Point H, a commit $C$ mapped to a merged PR passes Rule 1 on `.apm/tracker.md` if `check_tracker_working_note_append(raw_P1, raw_C)` verifies via `segment(raw, "tracker_task_row")` and `segment(raw, "working_note_entry")` (`research_system/legacy/segmentation.py:470-473`) that:
  (i) every `tracker_task_row` item and every byte before `## Working Notes` (and after it if any subsequent section exists) is byte-identical between $P_1$ and $C$;
  (ii) every `working_note_entry` present at $P_1$ is preserved byte-for-byte and in order at $C$ with 0 blockers; and
  (iii) every byte inside `## Working Notes` that lies outside the `working_note_entry` spans consists solely of whitespace/blank separator lines matching `[ \t]*\n` (each real append adds one blank separator line, `+1` byte, between entries inside the section, as verified on `452352ff`, `e3519ba7`, and `a6a98966` in `wp9-5-note-r2-review-2026-11-21.md:219`).
  Under Option H2 or H3, `.apm/tracker.md` follows that option's rule (§16 H).
- **Requirement for all other Rule-1 matches:**
  Unless exempted by a valid entry in `walk-baseline.json["acknowledged"]` covering `(C, "Rule 1", p, b_old, b_new)` (§6.2.2 item 3), commit $C$ must map to a valid `pr_number` (`merge_commit_sha == C`), `b_old != b_new`, and `<C>:.research-system/evidence/w9/legacy-write-records.json` must contain a valid record for `pr_number` (with `owner_note` and `independent_review` verified at `P1` per §6.4) covering $(p, b_{\text{old}}, b_{\text{new}})$ and every other guarded file touched by $C$.
- **Failure message (closed, exit 1):**
  `ERROR: post_merge_first_parent: Rule 1 violation at commit <C> (pr=<pr_or_none>): registered path '<p>' changed (<b_old> -> <b_new>) without a valid in-commit W9 §4.2 record`

#### Rule 2 — Any path under `results/` outside `results/ars/` (`06v:478`; `W9-D13`, `W9-D14`, `W9:140-147,196`; `R1-i1`, `R2-m4`)

- **Matching rule:** The changed path $p$'s case-folded path starts with `"results/"` and does **not** start with `"results/ars/"`.
- **Deliberate hard-coding of the `results/ars/` prefix exemption (`R1-i1`, `R2-m4`):**
  `W9-D14` (`09-migration-compatibility-and-pilot.md:768`) says *"register `results/ars/` as the `successor_results_root` so the detector exempts exactly that prefix"*. In `tools/check_legacy_writes.py`, Rule 2 exempts the exact normalized prefix `"results/ars/"` directly (whether or not `results/ars/` has been registered in `registration-manifest.json` yet) so that unregistered legacy result families under `results/` (P04, poverty, financial; `W9-D13`, `09-migration-compatibility-and-pilot.md:767`) are always guarded while `results/ars/` never requires a §4.2 record.
- **Requirement:** Unless exempted by a valid entry in `walk-baseline.json["acknowledged"]` covering `(C, "Rule 2", p, b_old, b_new)`, commit $C$ must map to a valid `pr_number`, `b_old != b_new`, and `<C>:.research-system/evidence/w9/legacy-write-records.json` must contain a valid §4.2 record for `pr_number` covering $(p, b_{\text{old}}, b_{\text{new}})$.
- **Failure message (closed, exit 1):**
  `ERROR: post_merge_first_parent: Rule 2 violation at commit <C> (pr=<pr_or_none>): results path outside results/ars/ '<p>' changed (<b_old> -> <b_new>) without a valid in-commit W9 §4.2 record`

#### Rule 3 — `shared_enforcement_surface` contracts (`06v:212,479-481`; `O-32`; `W9` §4.3, `W9:183-190`; `R1-M6`, `R2-m11`; Owner Point D)

- **How the detector identifies shared enforcement surfaces:**
  From $\mathcal{M}(P_1, C) = \text{Manifest}(P_1) \cup \text{Manifest}(C)$, the set of shared enforcement surfaces at commit $C$ is:
  `{r["normalized_path"] for r in M(P1, C) if r["root_kind"] == "repository_root" and r["role"] == "shared_enforcement_surface"}`
  (for example, real repository contract paths such as `contracts/manifests/research-assurance.yaml`, `contracts/stochastic-tests/monte-carlo-permutation-p-value.yaml`, `contracts/stochastic-tests/markov-order-provenance.yaml`, and `contracts/topology-invariants/null-operation-changes-ph-input.yaml`; `W9:166`).
- **What Rule 3 requires when $P_1 \to C$ changes a `shared_enforcement_surface` path $s$ ($b_{\text{old}} \to b_{\text{new}}$):**
  Unless exempted by a valid `acknowledged` row for `(C, "Rule 3", s, b_old, b_new)` **together with a late entry `(pr_number(C), s, b_old, b_new, affected_registrations)` present in `<head>:.research-system/evidence/w9/shared-surface-changes.json`** (§6.2.2 item 3.4, `R3-M3` — guaranteeing WP9.3's `check_change_list` sees the change at the control store's `git_head`):
  1. Commit $C$ must map to `pr_number` (`merge_commit_sha == C`), and `<C>:.research-system/evidence/w9/legacy-write-records.json` must contain a valid record for `pr_number` with `allowance_kind == "shared_surface_4_3"`, `owner_note` verified at $P_1$, `independent_review` (the reviewer's binding-test derivation of affected results) verified at $P_1$, and `(s, b_old, b_new)` in `files`.
  2. `<C>:.research-system/evidence/w9/shared-surface-changes.json` must contain a valid entry for this change to $s$.
- **Resolving the `O-32` squash-merge SHA contradiction (`R1-M6`, `R2-m11 (a),(c)`; Owner Point D, §16):**
  As verified in `wp9-5-note-r1-review-2026-11-21.md:116-124`, `06v:90-91` (*"A commit SHA created by the queue cannot be named inside the PR that creates it"*) and `06v:212,479-481` (*"The PR that changes a shared surface carries its own entry in a committed change list in the W9 evidence area, naming the contract and its old and new blobs"*) conflict with WP9.3's `research_system/legacy/evidence.py:231-238` (`_closed(item, {"merge_commit", "surface", "affected_registrations"}, ...)`) and `research_system/legacy/acceptance.py:135` (`evidence.is_ancestor(repository_root, entry["merge_commit"], str(source.get("git_commit")))`).
  Furthermore, `R1-M6` showed that placing a `base_commit` in the entry (Option D1) is unsound under the merge queue because `main` can advance between `base_commit` and the squash merge commit, allowing an observation taken between `base_commit` and the squash merge to satisfy `obs != base_commit and is_ancestor(base_commit, obs)`.
  Section 16 **Owner Point D** therefore presents three options, recommending **Option D3 (blob-keyed, tree-state equivalence, no commit field)**:
  - **Under Option D3 (Recommended, uniform format `"w9-shared-surface-changes/2"`, `R2-m11 (c)`):**
    - `SHARED_SURFACE_CHANGES_FORMAT` (`research_system/legacy/evidence.py:42`) moves to `"w9-shared-surface-changes/2"` (uniform `/2` versioning policy with Option A1; no live `shared-surface-changes.json` exists before L-1). Each entry has closed keys `{"pr_number", "surface", "old_blob", "new_blob", "affected_registrations"}` (no commit SHA field).
    - In `tools/check_legacy_writes.py` (Rule 3), at commit $C$ (mapped to `pr_number`), the detector checks that `<C>:.research-system/evidence/w9/shared-surface-changes.json` contains an entry with `(entry["pr_number"], entry["surface"], entry["old_blob"], entry["new_blob"]) == (pr_number, s, b_old, b_new)`.
    - In `research_system/legacy/acceptance.py:121-136` (`check_change_list`), for each entry affecting an item's registration, the item's observation commit `obs_commit = str(source.get("git_commit"))` is admitted iff `evidence.blob_at(repository_root, obs_commit, entry["surface"])` (`research_system/legacy/evidence.py:179-188`) equals `entry["new_blob"]` or the `new_blob` of a later entry for the same `surface` in `entries`.
    - **Intent and revert-cycle nuance (`R2-m11 (a)`):** Checking `blob_at == new_blob` tests **tree-state equivalence** (whether the observed result was checked against the same contract bytes as post-change `new_blob`), NOT strict commit-ancestry ordering. Consequently, if two entries form a revert cycle (`A -> B` then `B -> A`), an old observation captured before the first change (at contract state `A`) equals the second entry's `new_blob` (`A`); this is consistent with tree-state equivalence because the reverted contract restored identical bytes `A`, and `HR-2` / reviewer inspection notes if a revert intentionally invalidates old observations.
- **Failure message (closed, exit 1):**
  `ERROR: post_merge_first_parent: Rule 3 violation at commit <C> (pr=<pr_or_none>): shared_enforcement_surface '<s>' changed (<b_old> -> <b_new>) without a valid in-commit shared-surface-changes.json entry and W9 §4.3 owner note`

---

### 6.6 What `tools/check_legacy_writes.py` does with an unreadable registered file or unmappable commit (`R1-M4`)

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

### 7.3 Verified unit counts at `4b143c92` (`4620c716`) vs `dbd54fe3` and classification source (`R1-M3`, `R1-M9`, `R1-m11`; Owner Point J)

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

### 7.4 Exact insertion-only decision rule and structural/table edge cases (`R1-m11`, `R2-m3`, `R2-i2`)

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
- **Where it runs (`R3-m2`, `R3-i2`):** Before every batch on the operator machine (`06v:604`, via `tools/run_w9_pinned_detectors.py` from the Form (A) assembled tree), post-merge in `.github/workflows/legacy-write-detector.yml` (executed from `$RUNNER_TEMP/w9-detector` with no `--classified-locks`), in `tests/tools/test_w9_detectors.py`, and—if Stephen chooses **Option K1** in Owner Point K (§16)—on every pull request in `.github/workflows/ci.yml` `admission-controls` (`06v:491-492`, `< 0.15s`, zero ruleset change).

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

### 8.2 What it reads and the exact comparison rule (`R1-M1`, `R1-M2`, `R1-M9`, `R1-m8`)

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

### 8.3 Format of `classified_list` and what changes when L-0b is accepted (`06v` D-7; `R1-M2`, `R1-M9`; Owner Point J)

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

### 8.4 Settling D-5: pre-batch and weekly cadence, gate placement at batch start, reset, weekly cost, and self-attestation (`06v:495-496,567`; `R1-M8`; Owner Point E)

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

### 9.2 Binding `output_sha256` to the detector tool blob and deterministic synthetic commits (`R1-m4`)

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
3. **CI re-verification of `watched_to_fail` hashes after L-1 (`R1-m4`, `R2-m5 (c)`):**
   Because the three `watched_to_fail` transcripts (`post_merge_first_parent`, `vault_computational_log`, `conventions_repository_check`) are deterministic functions of the repository's object database and the detector closure's bytes, `tools/run_w9_detector_controls.py --repo-root <assembled_detector_dir> --verify-watched-to-fail <extracted_detector_controls_json>` re-runs the three `watched_to_fail` control suites in a temporary directory and asserts that their recomputed `output_sha256` values match the committed hashes in `detector-controls.json`! This step is executed directly in `.github/workflows/legacy-write-detector.yml` (§10.2) and `tools/run_w9_pinned_detectors.py` (§6.2.3), and if anyone edits a detector tool or closure dependency without re-running and re-recording the controls (under Rule 0), `--verify-watched-to-fail` fails closed (`ERROR: detector_controls: recomputed output_sha256 for '<detector>' does not match detector-controls.json`).

---

## 10. Merging is not going live (`P-089` item 3)

### 10.1 Why WP9.5 must stay inactive on `main` and the vault after merge

- `P-089` (`03-decisions-and-open-questions.md:6113-6115,6129-6130`) withholds authorization for **L-1** ("the detectors live on `main` or the vault") and requires that merging WP9.5 must not start any detector automatically on `main` or the vault.
- While `.research-system/evidence/w9/detector-controls.json` is absent on `main`, WP9.3's `prepare_proposal` (`LR-003`, `research_system/legacy/preparers.py:686-690`) refuses any path registration on a store bound to `main`.

### 10.2 Full `.github/workflows/legacy-write-detector.yml` specification (`R1-B1`, `R1-M11`, `R1-m6`, `R1-m7`, `R2-M1`, `R2-M3`, `R2-m5`, `R3-M1`, `R3-m1`, `R3-m12`)

In WP9.5, `.github/workflows/legacy-write-detector.yml` is committed with `on: workflow_dispatch:` only (no `inputs:`, `R2-M1`), full-history checkout (`fetch-depth: 0`), `permissions: contents: read, pull-requests: read`, forward-slash `.venv/Scripts/python.exe` invocations under `shell: bash`, no `grep -q` under `pipefail`, Form (A) content-pinned blob assembly (`detector_closure_blobs` + `uv sync --locked --no-install-project` + `PYTHONSAFEPATH=1`), `--ruleset-check <require|ci-d8>` selected explicitly from U-3/D-8, and `--verify-watched-to-fail`:

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

      - name: Install uv package manager
        run: pip install uv

      - name: Assemble content-pinned detector tree from recorded closure blobs
        id: pin
        env:
          # Under Option I3, flip REQUIRE_I3_PIN to "true" so an empty vars.W9_DETECTOR_PIN fails closed (R3-m1).
          REQUIRE_I3_PIN: "false"
          W9_DETECTOR_PIN_VAR: ${{ vars.W9_DETECTOR_PIN }}
        run: |
          set -euo pipefail
          main_tip="$(git --no-replace-objects rev-parse refs/remotes/origin/main | tr -d '\r')"
          detector_dir="${RUNNER_TEMP}/w9-detector"
          python - <<'PY' "$main_tip" "$detector_dir" > "${RUNNER_TEMP}/w9-pin.env"
          import hashlib, json, os, pathlib, shutil, subprocess, sys
          main_tip, detector_dir = sys.argv[1], pathlib.Path(sys.argv[2])
          raw = subprocess.check_output(
              ["git", "--no-replace-objects", "show", f"{main_tip}:.research-system/evidence/w9/walk-baseline.json"]
          )
          wb = json.loads(raw.decode("utf-8"))
          blobs = wb["baselines"][-1]["detector_closure_blobs"]
          if "pyproject.toml" not in blobs or "uv.lock" not in blobs:
              raise SystemExit("ERROR: detector_closure_blobs must include pyproject.toml and uv.lock")
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
          for rel_path, blob_sha in blobs.items():
              obj_type = subprocess.check_output(
                  ["git", "--no-replace-objects", "cat-file", "-t", blob_sha], text=True
              ).strip()
              if obj_type != "blob":
                  raise SystemExit(f"ERROR: {rel_path} pin {blob_sha} has type {obj_type}, expected blob")
              blob_bytes = subprocess.check_output(["git", "--no-replace-objects", "cat-file", "blob", blob_sha])
              dest = detector_dir / rel_path
              dest.parent.mkdir(parents=True, exist_ok=True)
              dest.write_bytes(blob_bytes)
          print(f"MAIN_TIP={main_tip}")
          print(f"DETECTOR_DIR={detector_dir}")
          PY
          cat "${RUNNER_TEMP}/w9-pin.env" >> "$GITHUB_ENV"
          source "${RUNNER_TEMP}/w9-pin.env"
          git --no-replace-objects show "${MAIN_TIP}:.research-system/evidence/w9/detector-controls.json" > "${RUNNER_TEMP}/detector-controls.json"

      - name: Install dependencies in content-pinned detector tree from lockfile
        working-directory: ${{ env.DETECTOR_DIR }}
        run: uv sync --locked --no-install-project

      - name: Run content-pinned W9 post-merge detector, CONVENTIONS lock check, and watched-to-fail verify
        env:
          GH_TOKEN: ${{ github.token }}
          PYTHONPATH: ${{ env.DETECTOR_DIR }}
          PYTHONSAFEPATH: "1"
        run: |
          set -euo pipefail
          py="${DETECTOR_DIR}/.venv/Scripts/python.exe"
          # Ruleset flag: '--ruleset-check require' when U-3 shows rule-suites is readable by GITHUB_TOKEN,
          # or '--ruleset-check ci-d8' when Stephen confirms D-8 (decided after U-3 probe before code dispatch).
          "$py" "${DETECTOR_DIR}/tools/check_legacy_writes.py" \
            --repo-root . \
            --ruleset-check ci-d8
          "$py" "${DETECTOR_DIR}/tools/check_conventions_legacy_locks.py" \
            --repo-root . \
            --git-ref "${MAIN_TIP}:CONVENTIONS.md"
          "$py" "${DETECTOR_DIR}/tools/run_w9_detector_controls.py" \
            --repo-root "$DETECTOR_DIR" \
            --verify-watched-to-fail "${RUNNER_TEMP}/detector-controls.json"

      - name: Remove temporary content-pinned detector directory
        if: always()
        run: |
          if [ -n "${DETECTOR_DIR:-}" ] && [ -d "$DETECTOR_DIR" ]; then
            rm -rf "$DETECTOR_DIR" || true
          fi
```

**Why every part of this workflow skeleton is required (`R1-B1`, `R1-M11`, `R1-m6`, `R1-m7`, `R2-M1`, `R2-M3`, `R2-m5`, `R3-M1`, `R3-m1`, `R3-m12`):**
1. **`fetch-depth: 0` (`R1-m7`):** `tools/check_legacy_writes.py` refuses shallow clones (`git rev-parse --is-shallow-repository == "false"`), and `tools/check_conventions_legacy_locks.py` reads historical blob `4620c716` from `4b143c92`.
2. **No `workflow_dispatch` `--baseline` / `--head` overrides and no `grep -q` under `pipefail` (`R2-M1`, `R2-m5 (b)`):** Removing `inputs:` prevents manual dispatches from narrowing the walk range to an empty slice; `rev-list --first-parent` membership is checked in Python rather than `rev-list | grep -q` under `set -o pipefail` (which returns SIGPIPE 141 and triggers an error on a valid ancestor). Forward slashes (`.venv/Scripts/python.exe`) avoid Git Bash backslash-dropping (`R2-m5 (a)`).
3. **Form (A) content-pinned blob assembly + `--no-install-project` + `--verify-watched-to-fail` (`R2-M1`, `R2-M3`, `R2-M5`, `R2-m5 (c)`, `R3-M1`, `R3-m1`):** The workflow writes **only** the blobs in `baselines[-1]["detector_closure_blobs"]` (`git cat-file blob`, failing closed if `walk-baseline.json` is absent before L-1, and under Owner Point I3 failing closed if `vars.W9_DETECTOR_PIN` is empty or disagrees on `walk_baseline_commit` / `closure_blobs_sha256`), installs third-party packages via `uv sync --locked --no-install-project` (never editable-installing the checkout), and executes `check_legacy_writes.py` (which defaults `--head` to `refs/remotes/origin/main` when omitted, with `--ruleset-check ci-d8` if D-8 is confirmed after U-3 or `require` if U-3 allows `rule-suites`), `check_conventions_legacy_locks.py` (with **no** `--classified-locks` flag), and `run_w9_detector_controls.py --verify-watched-to-fail "${RUNNER_TEMP}/detector-controls.json"` (extracted directly from `${MAIN_TIP}`) from `$DETECTOR_DIR` with `PYTHONPATH="$DETECTOR_DIR"` and `PYTHONSAFEPATH=1`. Any out-of-closure import raises `ModuleNotFoundError`, and Option I1 CODEOWNERS (optionally paired with Option I3 `vars.W9_DETECTOR_PIN`) is the preventive trust root protecting `.github/workflows/legacy-write-detector.yml` itself.
4. **Compatibility with existing watchdogs (`R3-i3`):**
   - `tools/check_workflow_liveness.py:78-92` (`inactive_tracked_workflows`, called by `.github/workflows/ars-artefact-currency-watchdog.yml:98-112` with `--all-tracked`) checks that every tracked workflow is registered in GitHub Actions with `state == "active"`. On PRs and merge-group runs, `ars-artefact-currency-watchdog.yml:103-112` passes `--tracked-ref FETCH_HEAD` (the base branch `main`), and after merge GitHub registers the `workflow_dispatch`-only workflow as `state: "active"`.
   - `.github/workflows/ci.yml:263,276` (`watchdog-schedule-liveness`, `ci.yml:255-279`) monitors only `ars-artefact-currency-watchdog.yml` and `research-system-suite.yml`; after L-1 enables the detector's `schedule`, optionally extending `watchdog-schedule-liveness` to watch `legacy-write-detector.yml` is left as an optional follow-up (`R3-i3`).
5. **Pre-L-1 throwaway-PR workflow rehearsal (`R3-m12`):**
   Because `walk-baseline.json` does not exist on `origin/main` before L-1, the workflow YAML's `Assemble content-pinned detector tree` step fails closed on `main` until L-1. Before L-1 activation, rehearse the full workflow once on a throwaway PR branch with a temporary `on: pull_request` rehearsal trigger and synthetic `walk-baseline.json` / `detector-controls.json` (like U-3, closing without merging), in addition to the unit test in `tests/tools/test_w9_detectors.py` (§12.1) that runs the Python assembly block against a scratch repo.

### 10.3 The L-1 tripwire test and how L-1 switches it (`R1-M7`, `R2-M5`, `R2-m5 (d)`, `R3-i1`; Owner Points I and F)

In `tests/tools/test_w9_detectors.py`, a module-level constant defines the L-1 activation state, and `.github/workflows/legacy-write-detector.yml` is loaded with **`yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)`** (`tests/tools/test_ars_currency_workflow_controls.py:19-22`, `R3-i1`) so YAML 1.1 never coerces `"on"` into boolean `True`:
```python
# Flipped from False to True in the L-1 activation PR authorized by Stephen (06v §7 L-1).
L1_LIVE = False
```
The test `test_legacy_write_detector_l1_activation_state` asserts:
- **While `L1_LIVE is False` (WP9.5):**
  1. `.github/workflows/legacy-write-detector.yml` has `set(doc["on"].keys()) == {"workflow_dispatch"}` (no `push`, `schedule`, `pull_request`, or `merge_group`);
  2. None of `.research-system/evidence/w9/detector-controls.json`, `.research-system/evidence/w9/registration-manifest.json`, `.research-system/evidence/w9/walk-baseline.json`, or `.research-system/evidence/w9/vault-detector-runs.json` exists in `REPO_ROOT`.
- **When `L1_LIVE is True` (flipped in the L-1 activation PR):**
  1. `.github/workflows/legacy-write-detector.yml` has `set(doc["on"].keys()) == {"push", "schedule", "workflow_dispatch"}` **and** `doc["on"]["push"] == {"branches": ["main"]}` (`R2-m5 (d)`, branch filter required so feature-branch pushes do not trigger `origin/main` checks);
  2. `.research-system/evidence/w9/detector-controls.json` exists and passes `evidence.require_detector_controls` and `--verify-watched-to-fail`;
  3. `.research-system/evidence/w9/walk-baseline.json` and `.research-system/evidence/w9/registration-manifest.json` exist and pass schema validation.
- **Why `tests/tools/test_w9_detectors.py` must run in `.github/workflows/ci.yml`'s `admission-controls` job AND be code-owned under I1 (`R1-M7`, `R2-M5`, Owner Points I and F):**
  If `tests/tools/test_w9_detectors.py` were only named in `.github/workflows/legacy-write-detector.yml` (Option F2), it would never run on pull requests! Running `tests/tools/test_w9_detectors.py` in `ci.yml`'s `admission-controls` job (Option F1) ensures the tripwire runs on every PR, **and** adding `tests/tools/test_w9_detectors.py` and `legacy-write-detector.yml` to `.github/CODEOWNERS` under **Owner Point I1** prevents a non-owner PR from flipping `L1_LIVE = True` or modifying the tripwire without Stephen's approval/bypass (`R2-M5`).

---

## 11. Where the controls run and scratch-clone mechanics (`P-089` item 4; `06v` O-13; W9-T7)

### 11.1 Hard isolation rule (`P-089` item 4; `06v:193,497-502`)

Every negative control and integration test runs exclusively on a scratch Git clone or a byte copy inside `pytest`'s `tmp_path` (or `tempfile.TemporaryDirectory`), **never** by writing to `main`, the working checkout, any linked worktree, or `C:\Users\steph\Documents\TDA-Research`.

### 11.2 How the W9-T7 scratch clone is constructed and replayed (`R1-M3`, `R1-m14`)

`06v` §4 row `W9-T7` (`06v-w9-implementation-plan.md:230`) and `06v` §5 (`:499`) require:
> *"Replay `5df0c001` and `811d5a2b` on a scratch clone from the local object store, fixture registry listing the files `5df0c001` and `811d5a2b` touched"*

1. **Measured bare scratch clone from the local object store (`1.71–1.79s` on this machine; Appendix A §21.1):**
   - `git clone --bare --local --no-hardlinks <REPO_ROOT> <tmp_path>/scratch.git`
   - Verified on `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note` on 2026-11-21 (Appendix A §21.1, reproduced at `1.78s` in `wp9-5-note-r2-review-2026-11-21.md:218`):
     - Copies the local object packs into `<tmp_path>/scratch.git/objects` without hardlinks in **1.71–1.79 seconds**.
     - Contains `4b143c9225035cc29e37351445f1c3a4ab09ceb1`, `a426b731e614986b6ca19a193e452df3e3efd885`, `5df0c001231fc1fac2e78f5f1834ddc754c45492`, `811d5a2b094bc82b135eb74eb6c08302cd5419b2`, and `b132406eff2e2a6b77e44d3c4d8702911f3afddf`.
   - Immediately after cloning, the test runs `git --git-dir=<tmp_path>/scratch.git remote remove origin` so the scratch clone has no remote URL.
2. **Dynamic derivation of the fixture registration manifest from `git diff-tree` (`R1-M3`, `R3-m4`):**
   - Rather than hard-coding file paths that could drift or be mistyped, W9-T7 (placed in `tests/tools/test_w9_detectors.py` so it blocks on every PR in `ci.yml` `admission-controls`, `R3-m4`) derives the exact 7 `results/` paths touched by `5df0c001` and the exact 3 `contracts/` paths touched by `811d5a2b` directly from the scratch clone via `git --git-dir=<tmp_path>/scratch.git --no-replace-objects diff-tree -r --no-renames --name-only <C>~1 <C>`, and asserts that the derived sets equal the verified repository paths (Appendix A §21.1):
     - **From `5df0c001~1..5df0c001`** (11 total changed files, of which 7 are under `results/` and 4 are non-`results/` paths `.claude/CLAUDE.md`, `.codacy/codacy.config.baseline.json`, `.codacy/codacy.config.json`, `.repowise-workspace.yaml`):
       1. `results/panel_methodology/bhps_nonoverlap/bhps_nonoverlap_reanalysis_2026-06-09.json`
       2. `results/trajectory_tda_bhps/01_trajectories.json`
       3. `results/trajectory_tda_bhps/stage1/bhps_headline_frozen_corrected_2026-07-14.json`
       4. `results/trajectory_tda_integration/01_trajectories.json`
       5. `results/trajectory_tda_integration/05_analysis.json`
       6. `results/trajectory_tda_integration/stage1/headline_vintage_materiality_corrected_2026-07-14.json`
       7. `results/trajectory_tda_integration/stage1/w2_fallback_audit_2026-07-14.json`
     - **From `811d5a2b~1..811d5a2b`** (9 total changed files, of which 3 are under `contracts/manifests/input-provenance/` and 6 are non-contract paths `.agents/skills/tda-handoff/SKILL.md`, `.claude/CLAUDE.md`, `.claude/skills/tda-handoff/SKILL.md`, `.githooks/pre-commit`, `.repowise-workspace.yaml`, `tools/skill_sync_state.json`):
       8. `contracts/manifests/input-provenance/b9-om-gmm-inputs.yaml`
       9. `contracts/manifests/input-provenance/t128-inputs.yaml`
       10. `contracts/manifests/input-provenance/t138-w2-gap-closure-inputs.yaml`
   - W9-T7 writes a 10-entry fixture `registration-manifest.json` (`"w9-registration-manifest/2"` under Option A1) registering the 7 `results/` files with `role: "legacy_research_result"`, `source_identity_kind: "git_tracked"` and the 3 `contracts/manifests/input-provenance/` files with `role: "legacy_contract"`, `source_identity_kind: "git_tracked"`.
3. **Executing the replay (`R1-m14`):**
   - **Replay T7-1 (Historical commits `5df0c001` and `811d5a2b` in `<tmp_path>/scratch.git`):**
     Runs `tools/check_legacy_writes.py --repo-root <tmp_path>/scratch.git --ruleset-check skip --manifest-file <tmp_path>/fixture-manifest.json --pr-map <tmp_path>/empty-pr-map.json`:
     - over `--baseline a426b731e614986b6ca19a193e452df3e3efd885 --head 5df0c001231fc1fac2e78f5f1834ddc754c45492`: asserts exit code `1`, flagging all 7 `results/` paths under **both** Rule 1 and Rule 2 (and not flagging the 4 non-`results/` paths);
     - over `--baseline 1d3a0769b93fcdda0dfe4000613c16d5b9d1a527 --head 811d5a2b094bc82b135eb74eb6c08302cd5419b2`: asserts exit code `1`, flagging all 3 `contracts/manifests/input-provenance/` paths under Rule 1 (and not flagging the 6 non-contract paths);
     - over the combined range `--baseline 4b143c9225035cc29e37351445f1c3a4ab09ceb1 --head 811d5a2b094bc82b135eb74eb6c08302cd5419b2`: asserts exit code `1`, flagging both `5df0c001` and `811d5a2b`.
   - **Replay T7-2 (In-tree committed manifest at `P1` using a throwaway `GIT_INDEX_FILE`, `R1-m14`):**
     To also exercise the production code path where `registration-manifest.json` is read directly from `<P1>:.research-system/evidence/w9/registration-manifest.json` (without `--manifest-file`), the test uses a throwaway index file `GIT_INDEX_FILE=<tmp_path>/idx` in `<tmp_path>/scratch.git` (`git read-tree`, `git update-index --add --cacheinfo 100644,<blob>,.research-system/evidence/w9/registration-manifest.json`, `git write-tree`, `git commit-tree`) to create a synthetic baseline commit `B0` holding `registration-manifest.json`, followed by synthetic commits `C_5df` and `C_811` that apply the exact `(path, new_blob)` changes of `5df0c001` and `811d5a2b`. Running `check_legacy_writes.py` without `--manifest-file` across `B0..C_811` takes < 0.3 seconds and asserts the same Rule 1 and Rule 2 failures.

### 11.3 How the test proves it never writes the real repository or the vault (`R1-m3`, `R2-m16`, `R3-m8`)

As `R1-m3` noted, running plain `git status --porcelain` refreshes `.git/index`, and checking only `HEAD` + `show-ref` would miss loose objects, `FETCH_HEAD`, hooks, config edits, or untracked/ignored file changes. However, as `R2-m16` and `R3-m8` noted, scanning shared `--git-common-dir` `objects/`, `worktrees/`, or shared `refs/heads/` / `refs/tags/` files is flaky locally whenever another session commits in a sibling linked worktree (for example under `.apm/worktrees/*`).
Therefore, the immutability fixture in `tests/tools/test_w9_detectors.py` and `tests/research_system/integration/test_w9_wp9_5_detectors.py`:
1. Runs every detector subprocess with `cwd=tmp_path` and `env={**os.environ, "GIT_DIR": str(scratch_git_dir)}` so no Git child process can default to `REPO_ROOT`.
2. Before and after each test:
   - **Locally (`R3-m8`):** records `(relpath, st_size, st_mtime_ns)` over **checkout-local** `--git-dir` files (`HEAD`, `index`, `FETCH_HEAD`, `ORIG_HEAD`, `config`, `hooks/` — excluding shared `objects/`, `worktrees/`, and shared `refs/` directories), **plus** the checked-out branch's own ref value (`git -C <REPO_ROOT> --no-optional-locks symbolic-ref -q HEAD` + its `rev-parse` SHA) and the tag list (`git -C <REPO_ROOT> --no-optional-locks for-each-ref refs/tags`);
   - **In CI (`CI=true`, where no sibling worktree runs concurrently):** also scans `--git-common-dir`; and
   - Runs `git -C <REPO_ROOT> --no-optional-locks --no-replace-objects status --porcelain=v1 --ignored -z` and `git -C <REPO_ROOT> --no-optional-locks --no-replace-objects rev-parse HEAD`.
3. Asserts exact equality of the before and after snapshots.

---

## 12. Tests and test-time budget

### 12.1 Test inventory and mapping to `06v` §4

| Test file | Markers | Cases covered |
|---|---|---|
| `tests/tools/test_w9_detectors.py` | `unit` (default; no `slow` marker; runs in `.github/workflows/ci.yml` `admission-controls` on every PR) | 1. **`W9-T19` (`CONVENTIONS.md` check):** baseline `4620c716` passes; current `CONVENTIONS.md` (`dbd54fe3`, 68 legacy units + 7 inserted in `Computational Environment` + 9 in `ARS Foundation Governance` + 6 in `Repo-Wide CI` = 90 units) passes; pure insertion of successor bullet/paragraph in `## Always` passes; L-0b pinned classification test (`ACCEPTED_CONVENTIONS_CLASSIFICATION` + `(anchor_text, unit_hash)`); negative controls N1–N7 (modified legacy bullet, deleted legacy paragraph, reordered legacy bullets, duplicate unit in section, missing/renamed legacy section, inserted table in legacy section, reclassified unit in head/copy ignored against pinned classification — `R2-M4`) each exit `1`.<br>2. **`W9-T19` (Computational-Log check on synthetic fixture export + classified list):** clean fixture passes; prepended successor entry (including CRLF successor entry above LF legacy entries, `R1-m8`) passes; modified successor-classified entry passes; empty `ACCEPTED_CL_EXPORT` in production mode fails closed; `recheck_cl_export` returning `void: True` fails closed (`R2-m12`); symlink, junction, ancestor-alias, or in-repo `--vault-root` fails closed; negative controls V1–V6 (1-byte edit or LF->CRLF inside legacy entry, renamed legacy heading anchor, deleted legacy entry, duplicate heading anchor, unparseable dated heading, reordered legacy entries) each exit `1`.<br>3. **D-5 cadence check:** clean run within 7 days passes; missing `vault-detector-runs.json` when `ACCEPTED_CL_EXPORT` is non-empty fails closed; latest run > 7 days old fails closed; consecutive runs > 7 days apart fail closed until an `"owner_cadence_reset"` entry followed by a fresh `"run"` entry is recorded.<br>4. **Post-merge detector unit controls (on a module-scoped synthetic Git repo in `tmp_path`):**<br>  - **Time-indexed evidence & Rule 0 (`R1-B1`, `R2-M1`, `R2-M2`, `R2-M3`, `R3-M1`, `R3-M2`):** atomic disarm attempt fails Rule 0 and Rule 1 (manifest read at `P1`); pre-registration edit passes; retroactive blessing fails Rule 0 and Rule 1 (records read at `C`); edits to any module in `detector_closure_blobs` without a same-PR `baselines` append + `P1` hash-bound decision ref fail Rule 0.3; **positive control (`R3-M1`)** where a closure edit carries a valid same-PR `baselines` row + `P1` decision ref naming path and `new_blob[:8]` ends **green** (`exit 0`); **negative controls (`R3-M1`)** for appended `baselines` row with missing decision ref, slice omitting changed path/`new_blob[:8]`, unmentioned no-op row, and unmentioned rollback row each fail closed; **negative control (`R3-M2`)** where a pin advance turns a previously red historical commit green without naming it in the slice fails with `ERROR: post_merge_first_parent: Rule 0: pin advance changes verdicts`; baseline not on `<head>`'s first-parent chain fails closed.<br>  - **`acknowledged` violations & Rule 3 late-entry gate (`R2-M2`, `R3-M3`):** valid `acknowledged` entry (`commit < source_commit <= P1(C_ack)`, slice matching `commit[:8]`, `rule`, `path`, `old_blob[:8]`, `new_blob[:8]`) exempts only that exact tuple while unacknowledged sibling fails; backdated or same-commit `disposition_ref` fails; **Rule 3 negative control (`R3-M3`)** where a Rule 3 `acknowledged` entry lacks a matching entry in `<head>:shared-surface-changes.json` exits `1`, and positive control with late entry passes.<br>  - **Rule 1 matching and exclusions (`R1-M4`, `R1-M5`):** `conventions_lock`, `untracked_file`, `restricted_untracked_file`, `vault_root`, `successor_results_root`, and `legacy_read_only_projection` are excluded from Rule 1 and from §6.6's `git cat-file` check; `legacy_manuscript_root` prefix matching catches edits under `papers/P01-A-JRSSA/...`; mode-only change on a registered file fails closed; `.apm/tracker.md` pure Working-Note append with blank separator lines (under Option H1) passes while a task-row edit fails.<br>  - **Rule 1/2/3 §4.2 record provenance (`R1-M10`, `R2-m10`):** self-authored `source_commit` or `review_commit` not an ancestor of `P1`, or `### P-0xx` slice / review missing touched `(normalized_path, old_blob[:8], new_blob[:8])`, fails closed; valid `P1` provenance with matching `(pr_number, path, old_blob, new_blob)` at `C` passes.<br>  - **Rule 2 & Rule 3 (`O-32`):** unregistered `results/p04/out.json` without §4.2 record at `C` fails Rule 2; `results/ars/out.json` passes; `shared_enforcement_surface` edit without `shared-surface-changes.json` entry or without W9 §4.3 owner note at `C` fails Rule 3.<br>  - **PR mapping, AST import closure, Form (A) workflow pin-assembly script, & CLI lockouts (`R1-m5`, `R1-m6`, `R2-M1`, `R2-M3`, `R3-M1`, `R3-m12`):** retry on transient `[]`, subject-hint `pulls/<N>` fallback verified by `merge_commit_sha == C`, API failure exits `2`; `test_recorded_detector_import_closure_covers_ast_walk` proves AST closure superset; workflow pin-assembly heredoc runs against a scratch repo with synthetic `walk-baseline.json` rows (`R3-m12`: valid assembly passes in-closure import & raises `ModuleNotFoundError` for `research_system.cli`, off-chain `baseline_commit` fails, blob mismatch fails, Option I3 `closure_blobs_sha256` mismatch fails, empty `W9_DETECTOR_PIN` under `REQUIRE_I3_PIN=true` fails); `--baseline`, `--head`, `--pr-map`, `--manifest-file` all exit `2` without `--ruleset-check skip`; `--classified-locks` exits `2` without `--candidate-file`; workflow YAML contains none of them.<br>5. **Ruleset reader (`main_ruleset`) & D-8 unit controls (`R1-m2`, `R2-m9`, `R3-m11`):** live payload shape (with `integration_id: 15368`) passes; drift in `enforcement`, `allowed_merge_methods`, `max_entries_to_merge`, `require_code_owner_review`, `required_status_checks`, `integration_id`, or `bypass_actors` exits `1`; previous read > 30 days old without a valid `ruleset_gap_acknowledgements` row exits `1`; **positive `--acknowledge-gap <P-0xx>`** test backed by a valid hash-bound `ruleset_gap_acknowledgements` row exits `0` (`R3-m11`); invalid `ruleset_gap_acknowledgements` row fails Rule 0.2; **D-8 gate control** asserts `--ruleset-check ci-d8` fails without a verified hash-bound `d8_rule_suites_limit_decision_ref` in `walk-baseline.json` and passes once present (`R3-m11`); `result: "bypass"` evaluation on unrecorded guarded write exits `1`.<br>6. **Pre-L-1 inactivity tripwire (`R1-M7`, `R2-m5 (d)`, `R3-i1`):** loads workflow YAML with `yaml.BaseLoader`; `test_legacy_write_detector_l1_activation_state` checks `L1_LIVE = False` invariants (and tests in synthetic copy that `L1_LIVE = True` requires `push: {"branches": ["main"]}`).<br>7. **`W9-T7` scratch-clone replay (`R3-m4`, `R1-M3`, `R1-m14`):** module-scoped `git clone --bare --local --no-hardlinks` scratch clone of `REPO_ROOT` in `tmp_path` (measured at 1.71–1.79s); derives the 7 `results/` paths of `5df0c001` and 3 `contracts/` paths of `811d5a2b` via `git diff-tree`; runs T7-1 (historical SHAs) and T7-2 (in-tree manifest via throwaway `GIT_INDEX_FILE`); asserts `5df0c001` fires Rule 1 and Rule 2 on all 7 `results/` files and `811d5a2b` fires Rule 1 on all 3 manifests; asserts checkout-scoped `--no-optional-locks` snapshot immutability of `REPO_ROOT`. Running in `tests/tools/test_w9_detectors.py` puts `W9-T7` in `ci.yml` `admission-controls` on every PR. |
| `tests/research_system/integration/test_w9_wp9_5_detectors.py` | `integration`, `@pytest.mark.slow` *(CI lane `R2-m13`, `R3-m4`: `tools/affected_research_tests.py:120-147` selects this file only when a `research_system/` source or `tests/research_system/` helper changes—NOT on `tools/`-only edits, because `module_name` returns `None` for `tools/`—and every `.research-system/evidence/w9/` PR selects all `tests/research_system/contracts/` tests; runs unconditionally nightly/on-demand in `.github/workflows/research-system-suite.yml` `-m "not live_store"`, which is advisory per `:8-9,15,17`)* | 1. **`M-6` (`integration`):** scratch W9 control store + scratch Git repo in `tmp_path`; registers paths across roles (`legacy_research_result`, `shared_enforcement_surface`, `conventions_lock`, `legacy_manuscript_root`, `untracked_file`, `restricted_untracked_file`, `successor_results_root`), runs `tools/export_w9_registration_manifest.py`, commits manifest (`w9-registration-manifest/2`), advances binding, verifies `--check` exits `0`, and verifies store-extra and manifest-extra mismatches exit `1`.<br>2. **`O-13` (`slow`, `integration`):** runs `tools/run_w9_detector_controls.py` end-to-end in `tmp_path` with isolated `CONTROL_GIT_ENV` and `-c` flags, verifies deterministic `output_sha256` across two runs, verifies `--verify-watched-to-fail` fails if any closure module byte is altered, verifies `--verify-watched-to-fail` + operator-machine wrapper `tools/run_w9_pinned_detectors.py` on Form (A) assembled tree (`R3-m2`), and verifies the output passes `evidence.require_detector_controls` and `LR-003`; asserts checkout-scoped `--no-optional-locks` snapshot immutability of `REPO_ROOT`. |

### 12.2 Fixture provenance rule (`06v:248-255`)

- No test reads any live file from `C:\Users\steph\Documents\TDA-Research` or `C:\Users\steph\TDL\vault`, and no unit test reads live `papers/` or `results/` files.
- The `CONVENTIONS.md` baseline test reads blob `4620c71607ca3a06c6df3b8e96a6bddffc783960` from Git (`4b143c9225035cc29e37351445f1c3a4ab09ceb1:CONVENTIONS.md`) and verifies `git_blob_id(raw) == "4620c71607ca3a06c6df3b8e96a6bddffc783960"` and `sha256_hex(raw) == "d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589"` (`research_system/legacy/reader.py:43-49`) before running any assertion.

### 12.3 Measured timings and test-time budget (`R1-m14`, `R2-m13`, `R2-i6`, `R3-m4`, `R3-m5`; Owner Point G)

We measured the three repository/segmentation/assembly operations directly on this machine (Appendix A §21.1):
- `git clone --bare --local --no-hardlinks` of the object store (`58,133` objects, `28` packs, `335.09` MiB per `git count-objects -vH`) into `%TEMP%` + two `git diff-tree` queries + cleanup: **1.77 seconds** in revision 2 (run 1: `1.86s`, run 2: `1.77s`; reproduced at `1.78s` by r2 review, `wp9-5-note-r2-review-2026-11-21.md:218`; `1.60–1.70s` in revision 3).
- `segment(raw, "conventions_unit")` over both `4620c716` (`33,645` bytes) and `dbd54fe3:CONVENTIONS.md` (`51,774` bytes) with both segmenters: **< 0.15 seconds**.
- Form (A) content-pinned assembly (`uv sync --locked --no-install-project --offline`): **`14.6s`**, plus `23.11s` for the 320-commit stand-in walk (`R3-M2`, §21.1 item 10).

| Test file | Measured vs unmeasured wall-clock budget basis (`--no-cov`, serial, **including `@pytest.mark.slow`**) | Status |
|---|---|---|
| `tests/tools/test_w9_detectors.py` | In-memory byte-copy segmentation controls (< 0.5s measured) + module-scoped synthetic Git repo in `tmp_path` + `W9-T7` bare scratch clone (`~1.77s` + `0.3s` T7-2 replay) (`R3-m4`). | Runs on every PR in `ci.yml` `admission-controls` (`F1`). |
| `tests/research_system/integration/test_w9_wp9_5_detectors.py` | **Scratch W9 store fixture timing for `M-6` and `O-13` (`UNVERIFIED-3`: unmeasured here)** (`R2-m13`, `R3-m5`). | Selected by `tools/affected_research_tests.py` only when `research_system/` / `tests/research_system/` / pinned config changes (`R3-m4`); full suite nightly/on-demand in `research-system-suite.yml` (`-m "not live_store"`). |

**Unconditional pre-code profiling step (`P-087` item 7, `03-decisions-and-open-questions.md:5919-5923`; `R2-m13`, `R3-m5`):**
Because no scratch-store timing measurement exists on Stephen's machine for WP9.5's `M-6`/`O-13` store flow (`UNVERIFIED-3`), §15.1 item 4 **unconditionally** requires profiling one existing single scratch-store integration test alone on Stephen's machine before WP9.5 code is dispatched, while **Owner Point G recommends Option G1 (5 minutes / 300 seconds, matching WP9.4-2)** until that profile supports tightening to Option G2 (2 minutes / 120 seconds). All new and changed WP9.5 tests — including `@pytest.mark.slow` tests — count toward the budget, and over-budget returns `PARTIAL` with measurements.

---

## 13. Research assurance

WP9.5 touches the **Output / Provenance** assurance lane (`CONVENTIONS.md:20-34`): legacy artifact immutability detection, shared-surface state invalidation detection, `CONVENTIONS.md` lock preservation, vault Computational-Log legacy entry integrity, and detector negative-control evidence hashes.

### 13.1 Machine-checkable claims and their enforcement artifacts

| # | Claim | Enforcement artifact (test / validator / schema) |
|---|---|---|
| MC-1 | Every `legacy_path_registration` record in the W9 control store appears in `.research-system/evidence/w9/registration-manifest.json` (`w9-registration-manifest/2` under A1, matching `root_kind`, `root_id`, `normalized_path`, `role`, `source_identity_kind`) at `binding.binding["git_head"]`, and vice versa. | `tools/export_w9_registration_manifest.py --check`; tested in `tests/research_system/integration/test_w9_wp9_5_detectors.py` (`test_m6_registration_manifest_matches_store`). |
| MC-2 | Assembled by content from `baselines[-1]["detector_closure_blobs"]` (`git cat-file blob`, `pyproject.toml`, `uv.lock`, `uv sync --locked --no-install-project`, `PYTHONPATH="$DETECTOR_DIR"`, `PYTHONSAFEPATH=1`), `tools/check_legacy_writes.py` (Rule 0) always walks from `baselines[0]["baseline_commit"]` and exits `1` if any unacknowledged commit deletes or alters existing entries in evidence ledgers, mutates top-level fields of `walk-baseline.json`, appends an invalid `baselines` / `acknowledged` / `ruleset_gap_acknowledgements` row, changes a historical verdict across a pin advance without naming it in the `P1` decision slice, or modifies any module in `detector_closure_blobs` without a same-PR `baselines` append and pre-existing hash-bound decision ref at `P1`. *(Trust-root qualification, `R2-M1`, `R3-M1`: preventive blocking against a PR rewriting the workflow, WP9.5 tools, `accepted_w9.py`, tripwire test, or `.research-system/evidence/w9/` rests on Owner Point I1 CODEOWNERS, optionally paired with Option I3; for the remaining non-code-owned closure modules under `research_system/` and `tools/w9_segmentation.py`, Rule 0.3 is **detective** post-merge.)* | `tools/check_legacy_writes.py` (Rule 0), workflow Form (A) assembly step, and `test_recorded_detector_import_closure_covers_ast_walk`; tested in `tests/tools/test_w9_detectors.py`. |
| MC-3 | Any first-parent commit `C` (with first parent `P1`) after `walk_start` that modifies, deletes, renames, or mode-changes a `git_tracked` `repository_root` path registered in `registration-manifest.json` at `P1` (or `C`, excluding `conventions_lock`, `shared_enforcement_surface`, `successor_results_root`, and `legacy_read_only_projection`) without a matching `(pr_number, normalized_path, old_blob, new_blob)` record in `<C>:.research-system/evidence/w9/legacy-write-records.json` whose `owner_note` and `independent_review` commits precede `C` (at `P1`) and name the touched tuple (or an exact valid `walk-baseline.json["acknowledged"]` exemption committed after `C`) causes `tools/check_legacy_writes.py` to exit `1`. | `tools/check_legacy_writes.py` (Rule 1); tested in `tests/tools/test_w9_detectors.py` (including `W9-T7` replay of `5df0c001` and `811d5a2b`, `R3-m4`). |
| MC-4 | Any first-parent commit `C` after `walk_start` that adds, modifies, deletes, renames, or mode-changes any path under `results/` outside `results/ars/`—whether registered or unregistered—without a matching in-commit §4.2 record at `C` (or valid `acknowledged` entry) causes `tools/check_legacy_writes.py` to exit `1`. | `tools/check_legacy_writes.py` (Rule 2); tested in `tests/tools/test_w9_detectors.py` (including `W9-T7` replay of `5df0c001`, `R3-m4`). |
| MC-5 | Any first-parent commit `C` after `walk_start` that modifies a `shared_enforcement_surface` contract registered at `P1` (or `C`) without both an in-commit W9 §4.3 record in `legacy-write-records.json` and an entry in `shared-surface-changes.json` (or a valid `acknowledged` entry paired with a late entry in `<head>:.research-system/evidence/w9/shared-surface-changes.json`, `R3-M3`) causes `tools/check_legacy_writes.py` to exit `1`. | `tools/check_legacy_writes.py` (Rule 3, `O-32`); tested in `tests/tools/test_w9_detectors.py`. |
| MC-6 | `git diff-tree -r --no-renames -z <P1> <C>` detects file changes introduced by both 1-parent squash/direct commits and 2-parent merge commits on `main`. | `tools/check_legacy_writes.py`; tested in `tests/tools/test_w9_detectors.py`. |
| MC-7 | Every legacy unit in `CONVENTIONS.md` from commit `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (blob `4620c71607ca3a06c6df3b8e96a6bddffc783960`) as defined provisionally or by pinned `ACCEPTED_CONVENTIONS_CLASSIFICATION` (`(anchor_text, unit_hash)`) is preserved byte-for-byte and in relative order under `segment(raw, "conventions_unit")`, and any inserted unit in a legacy-lock section is a bullet or paragraph (never a table). | `tools/check_conventions_legacy_locks.py`; tested in `tests/tools/test_w9_detectors.py` (`W9-T19`, controls N1–N7). |
| MC-8 | Every legacy-classified `"item"` and `"structural"` row in the accepted `w9-cl-export/1` baseline export of `04-Methods/Computational-Log.md` (`recheck_cl_export` `void == False`) is preserved byte-for-byte and in relative order in the live vault file, with zero segmentation blocker rows across the live file, while prepended successor entries pass. | `tools/check_legacy_log_baseline.py`; tested in `tests/tools/test_w9_detectors.py` (`W9-T19`, controls V1–V6). |
| MC-9 | All four detector controls produce deterministic `output_sha256` hashes (with isolated Git config `-c core.autocrlf=false -c commit.gpgsign=false`) bound to each detector tool's Git blob and `closure_blobs` map (`R3-m7 (d)`) that pass `evidence.require_detector_controls` and `--verify-watched-to-fail`. | `tools/run_w9_detector_controls.py` and `research_system/legacy/evidence.py:133-154`; tested in `tests/research_system/integration/test_w9_wp9_5_detectors.py`. |
| MC-10 | While `L1_LIVE is False`, `.github/workflows/legacy-write-detector.yml` has `on == {"workflow_dispatch"}` only and none of the live L-1 evidence files is committed on `main`; when `L1_LIVE is True`, `on["push"]` filters `branches: ["main"]`. | `tests/tools/test_w9_detectors.py` (`test_legacy_write_detector_l1_activation_state`, using `yaml.BaseLoader`), wired into `ci.yml` `admission-controls` under Option F1 and code-owned under I1. |

### 13.2 Human-review-only claims and residual architectural limits (`R1-M8`, `R1-M10`, `R1-m2`, `R1-i3`, `R2-M1`, `R2-M5`, `R2-i2`)

| # | Claim / Limit | Reviewer / Owner check and why not mechanized |
|---|---|---|
| HR-1 | Whether a W9 §4.2(b) repository-wide change is truly semantically equivalent on the registered legacy files it touched, whether the independent review was genuinely authored by an independent session, and whether a `### P-0xx` decision entry on `main` was genuinely authored by Stephen (`R2-m10 (c)`). | `tools/check_legacy_writes.py` checks `source_commit`/`review_commit` pre-existence at `P1` and verifies tuple/decision-ID presence inside the slices, while CODEOWNERS (Owner Point I1) requires `@stephendor` on any `legacy-write-records.json` PR, but authorship of the register/review files and semantic equivalence require human review (`W9:174-176`). |
| HR-2 | Whether `affected_registrations` in a `shared-surface-changes.json` entry includes every registered result semantically affected by the contract edit (and whether a contract revert `B -> A` restores compatibility for earlier observations, `R2-m11 (a)`). | The detector and `acceptance.py` verify entry presence and post-change blob state equivalence, but deriving affected registrations from binding tests requires Stephen's note and the independent reviewer's derivation (`W9:185-188`). |
| HR-3 | **Post-merge detection, human merge trust root, and bypass/closure cost (`R1-M10`, `R2-M1`, `R2-M5`, `R3-M1`, `R3-m3`, `R3-m9 (c)`):** `tools/check_legacy_writes.py` is post-merge; ruleset `20822054` has `required_approving_review_count: 0`, and repository content alone cannot prevent a merged commit from editing the workflow or tools (`§6.1`). | Preventive blocking rests on human merge review and `.github/CODEOWNERS` (`@stephendor`, Owner Point I1 — optionally paired with out-of-tree `vars.W9_DETECTOR_PIN` under Option I3; non-code-owned closure modules are detective only). Under I1, every per-batch manifest, weekly vault-run, pre-batch ruleset-read, baseline/pin-advance, and closure-edit PR requires Stephen's own bypass merge with a `Bypass reason:` line (`tools/check_bypass_merges.py:41,135`, `admin-bypass-guard.sh:13-18`). |
| HR-4 | **Self-attestation of the weekly vault Computational-Log detector runs (`R1-M8`):** `vault-detector-runs.json` records `run_at` and `output_sha256` produced on the operator machine. | Because CI cannot access `C:\Users\steph\Documents\TDA-Research`, no remote runner can independently verify that the operator machine ran `tools/check_legacy_log_baseline.py` against the live vault at `run_at`. |
| HR-5 | **30-day rule-suites API window (`R1-m2`) and D-8 bypass visibility between batches (`R1-i3`):** GitHub's `rulesets/rule-suites` endpoint returns at most one month (`MAX_DAYS = 30`), and 33 of 57 evaluations on `refs/heads/main` at `dbd54fe38` were `result: "bypass"`. | The ruleset reader fails closed if the previous recorded read is older than 30 days (unless an owner-acknowledged gap entry exists in `walk-baseline.json`), and under D-8 (if `GITHUB_TOKEN` cannot read `rule-suites`) direct inspection of `rule-suites` occurs at each pre-batch local run under the owner's `gh` (`06v:571,603`). |
| HR-6 | **`CONVENTIONS.md` structural exceptions outside `conventions_unit` rows (`R2-i2`):** Under `w9-segmentation/1.0.0` §3, `### ` sub-headings, `---` horizontal rules, blank lines, the H1 title, and the `*Last updated: ...*` footer are not emitted as `conventions_unit` items (`§7.4`). | Editing a legacy `### ` sub-heading title or moving a legacy bullet under a different `### ` sub-heading within the same `## ` section is not detected mechanically by `tools/check_conventions_legacy_locks.py` and relies on human PR review (`wp9-5-note-r2-review-2026-11-21.md:123`). |

---

## 14. Claims for review (`R1-m12`)

An independent adversarial reviewer should attack each of the following 16 load-bearing claims against the cited repository evidence at base commit `dbd54fe382e7b2849d3f2038393cbdb4d709477b`:

1. **No D-4 trigger (`P-089` item 1):** WP9.5 adds no W9 command, no runtime-binding census row (stays at 275 rows, SHA-256 `82eab93a1b2ac81dd564581237f35e3dff19fee9e824ffff317d0f202b451d58`), no store append site (06h manifest stays at blob `1066404a`, smoke test at `3b1eec6e`), no core or W9 schema, and does not touch `tools/w9_segmentation.py` (blob `43e1454de09b61e274954c42b21d6ae533857a24`, `evidence.py:52-54`) or `IMPORTER_MODULES` (`reader.py:42`). See §2.2 and `03-decisions-and-open-questions.md:6022-6025,6085-6099`.
2. **Trust-root boundary (preventive vs detective), Form (A) content-pinned execution, full re-walk + dual-tool pin-advance diff, time-indexed evidence, and `acknowledged` late Rule 3 check (`R1-B1`, `R2-M1`, `R2-M2`, `R2-M3`, `R3-M1`, `R3-M2`, `R3-M3`):** No repository content alone stops a merged commit from changing a workflow or script on `main`; enforcement is **preventive** under Owner Point I1 CODEOWNERS (optionally paired with fail-closed `vars.W9_DETECTOR_PIN` in Option I3, while Option I2 fails R1-B1 scenarios 4–5) for CODEOWNED files, and **detective** post-merge under Rule 0.3 for non-code-owned closure modules. Assembling `$RUNNER_TEMP/w9-detector` from `detector_closure_blobs` (`git cat-file blob`, `pyproject.toml`, `uv.lock`, `uv sync --locked --no-install-project`, `PYTHONSAFEPATH=1`) runs the exact 25-entry closure (and rejects unpinned imports with `ModuleNotFoundError`), allows same-PR closure updates under Rule 0.2/0.3, always walks from `baselines[0]["baseline_commit"]` while recomputing the dual-tool diff across every pin advance (`ERROR: Rule 0: pin advance changes verdicts`), locks override flags behind `--ruleset-check skip`, time-indexes manifests at `P1` (union `C`) and records at `C`, and requires late `shared-surface-changes.json` entries for Rule 3 acknowledgements. See §6.1, §6.2.2, §6.2.3, §6.5, §10.2, and Owner Points I and C (§16).
3. **Manifest fields and `require_registered` compatibility (`R1-M4`, `R1-M5`, `R1-m10`, `R2-m11 (c),(d)`, `R3-m13`):** Bumping `REGISTRATION_MANIFEST_FORMAT` uniformly to `"w9-registration-manifest/2"` carrying `{"root_kind", "root_id", "normalized_path", "role", "source_identity_kind"}` (projected from `state["records"]["legacy_path_registration"]` via `_legacy_projection` in `research_system/cli.py:1648-1659`) and updating `require_registered` (`research_system/legacy/evidence.py:40,114-131`), `tests/research_system/unit/test_w9_evidence.py`, `w9_runtime_harness.py:451-466`, `test_w9_wp9_4_1_runtime.py:95-109`, and `test_w9_wp9_4_2_runtime.py:86-100` via a dated WP9.3 amendment + independent review gives the detector all needed fields without touching WP9.4 production code or reopening WP9.4's review. See §2.3, §5.3, and Owner Point A (§16).
4. **Rule 1 matching and exclusions (`R1-M4`, `R1-M5`):** Excluding `root_kind != "repository_root"`, `source_identity_kind != "git_tracked"`, and `role in {"conventions_lock", "shared_enforcement_surface", "successor_results_root", "legacy_read_only_projection"}` from Rule 1 and from §6.6's `git cat-file` check ensures the detector never misfires on untracked/restricted files (`*.csv`, `*.pkl`, stage logs, `.apm/bus/`, projections), `results/ars/` before it exists in Git, or `CONVENTIONS.md` successor insertions. See §6.5 (Rule 1) and §6.6.
5. **`.apm/tracker.md` Working Notes handling (`R1-M5`, `R2-m15`, Review §4 H):** Because Phase 5 batch PR `#368` (`452352ff`) and worktree-sweep PRs (`#388` `e3519ba7`, `#433` `a6a98966`) append entries under `## Working Notes` in `.apm/tracker.md`, Owner Point H (Option H1) mechanically verifies via `segment(raw, "tracker_task_row")` and `segment(raw, "working_note_entry")` (`research_system/legacy/segmentation.py:470-473`) that a tracker change in a merged PR preserves every byte outside `## Working Notes`, preserves all prior entries verbatim in order with 0 blockers, and has only `[ \t]*\n` blank separator lines outside entries inside `## Working Notes`. See §6.5 (Rule 1) and Owner Point H (§16).
6. **W9 §4.2 record keying and conditional `P1` provenance (`06v:486`; `R1-B1`, `R1-M10`, `R2-m10`):** Keying `.research-system/evidence/w9/legacy-write-records.json` by `(pr_number, normalized_path, old_blob, new_blob)` allows a PR to carry its own record at `C` without knowing its squash SHA; requiring `owner_note.source_commit` and `independent_review.review_commit` to be ancestors of `P1` with touched `(normalized_path, old_blob[:8], new_blob[:8])` verified in both slices binds the pre-existing provenance to the change (note that Option B1's tamper resistance is conditional on Owner Point I1 CODEOWNERS, because `P1` ancestry alone does not prove Stephen authored non-CODEOWNED files). See §6.4 and Owner Points B and I (§16).
7. **Two-parent merge commits and explicit `<P1> <C>` arguments to `git diff-tree`:** Single-argument `git diff-tree -r <C>` prints nothing on a 2-parent merge commit (verified on `b132406e`); passing `git --no-replace-objects diff-tree -r --no-renames -z <P1> <C>` extracts the exact first-parent tree delta on `main` for both 1-parent and 2-parent commits, and mode-only changes (`old_blob == new_blob`, `old_mode != new_mode`) fail closed. See §6.3.
8. **PR mapping, retry/hint fallback, and genealogy of `5df0c001` and `811d5a2b` (`R1-M3`, `R1-m5`, `R1-m6`, `R2-i1`, `R3-m4`):** Requiring `pull["merge_commit_sha"] == C` on `commits/<C>/pulls` (with 3-try precautionary backoff and `pulls/<N>` subject-hint fallback still verified by `merge_commit_sha == C`, exiting `2` on API failure and locking `--baseline`/`--head`/`--pr-map`/`--manifest-file` behind `--ruleset-check skip`) maps squash and merge PRs accurately while mapping `5df0c001` (`2026-08-05`, 1 parent `a426b731`, reusing `#215`'s merge subject, touching 7 `results/` files + 4 non-`results/` files) and `811d5a2b` (`2026-08-07`, 1 parent `1d3a0769`, touching 3 `contracts/manifests/input-provenance/` files + 6 other files) to `pr_number = None` (replayed on every PR via `W9-T7` in `tests/tools/test_w9_detectors.py`). See §6.2.1, §6.3, §11.2, and §12.1.
9. **Resolving the `O-32` squash-merge SHA contradiction via blob-keyed tree-state equivalence (`R1-M6`, `R2-m11`):** Option D3 bumps `SHARED_SURFACE_CHANGES_FORMAT` uniformly to `"w9-shared-surface-changes/2"` keyed by `{"pr_number", "surface", "old_blob", "new_blob", "affected_registrations"}` (no commit SHA) and checks in `acceptance.py:check_change_list` that `evidence.blob_at(repository_root, obs_commit, surface)` (`evidence.py:179-188`) equals `new_blob` (or a later entry's `new_blob` for `surface`), avoiding both the unknowable squash SHA (`06v:90-91`) and D1's stale-`base_commit` race, with the tree-state-equivalence revert nuance noted in `HR-2`. It modifies accepted WP9.3 gate code in `evidence.py` and `acceptance.py` and requires a dated WP9.3 amendment and independent review. See §6.5 (Rule 3) and Owner Point D (§16).
10. **Ruleset `20822054` pinning, 30-day rule-suites ceiling, and runnable U-3 draft-PR probe (`R1-M11`, `R1-m1`, `R1-m2`, `R2-m6`, `R2-m9`, `R3-m11`):** The ruleset read pins `allowed_merge_methods: ["squash"]`, `merge_queue: {merge_method: "SQUASH", max_entries_to_merge: 1}`, `require_code_owner_review: true`, `strict_required_status_checks_policy: true`, the 4 required contexts with `integration_id: 15368`, and `bypass_actors`, fails closed if the previous read is >30 days old without a schema-validated/Rule-0-checked `walk-baseline.json` `ruleset_gap_acknowledgements` entry, and tests `GITHUB_TOKEN` permissions (`contents: read` and `pull-requests: read`) plus pinned-key presence via a throwaway draft-PR `pull_request` workflow before code dispatch. See §4.1 and §4.2.
11. **Vault root junction refusal vs `open_registered_root_anchor` (`R1-M2`, `R1-m8`, `R3-m6`):** Because `open_registered_root_anchor` (`research_system/store/anchor.py:1934-1950`) sets `reject_reparse=False` and `LegacyReader.__init__` (`reader.py:241-248`) checks `os.path.abspath` lexically, `tools/check_legacy_log_baseline.py` explicitly rejects `vault_root.is_symlink() or vault_root.is_junction()` and requires `os.path.normcase(str(vault_root.resolve(strict=True))) == os.path.normcase(str(vault_root))` outside `repository_root` before calling `handle_bound_read`, and `u4_dry_run.py` exercises and prints all three boolean checks. See §4.3.1, §4.3.2, and §4.3.3.
12. **`CONVENTIONS.md` unit counts, table filter, and pinned L-0b classification (`R1-M3`, `R1-M9`, `R1-m11`, `R2-M4`, `R2-m3`, `R2-i2`):** At `4b143c92` (`4620c716`), `CONVENTIONS.md` has 70 `conventions_unit` items across 10 sections (`68` in the 9 non-governance sections + `2` in `ARS Foundation Governance`); at `dbd54fe3`, it has 90 units across 11 sections (`7` inserted in `Computational Environment`, `7` in `ARS Foundation Governance`, `6` in `Repo-Wide CI`), with all 70 baseline units preserved in order; inserted tables (`|...`) in legacy sections are rejected (using exact `start_byte` + `byte_length`), structural exceptions are tracked as `HR-6`, and any L-0b classification is pinned by `ACCEPTED_CONVENTIONS_CLASSIFICATION` (`accepted_w9.py`, keyed on `(anchor_text, unit_hash)`, tested by Control N7). See §7.3, §7.4, §7.6, and Owner Point J (§16).
13. **Vault Computational-Log classification source, `void == True` refusal, and CRLF resilience (`R1-M1`, `R1-M2`, `R1-M9`, `R1-m8`, `R2-m3`, `R2-m12`, `R2-i4`):** `tools/check_legacy_log_baseline.py` reads `ACCEPTED_CL_EXPORT[-1]`'s three descriptors (`export`, `retained_copy`, `classified_list`, `accepted_w9.py:86-88`), validates `export` with `require_cl_export(export)` (`evidence.py:277-362`), runs `recheck_cl_export(export, retained_raw)` (`export_recheck.py:32-89`) and fails closed when `report["void"] is True`, reads classifications from `classified_list` (`w9-cl-classified-list/1`, 1-based ordinals `1..N`), rejects any live blocker row (`R2-i4`), and checks legacy rows by `raw_row_sha256` without failing on CRLF in prepended successor entries. See §8.2, §8.3, and Owner Point J (§16).
14. **D-5 cadence gate at batch start (`LR-003`/`LR-015`) as well as `LR-016`/`LR-020` (`R1-M8`):** Gating on `bool(reader.accepted_cl_export)` (never on "file present") at `LR-003`, `LR-015`, `LR-016`, and `LR-020` blocks the next batch at batch start when a weekly run is missed, while `"kind": "owner_cadence_reset"` prevents one missed run from permanently bricking the store. See §8.4 and Owner Point E (§16).
15. **Deterministic, closure-bound control output hashes (`R1-m4`, `R2-m8`, `R2-M3`, `R3-m7 (d)`):** Binding each detector tool's `git_blob_id` and `closure_blobs` map with isolated `CONTROL_GIT_ENV` (`GIT_CONFIG_GLOBAL`, `GIT_CONFIG_NOSYSTEM`) and `-c core.autocrlf=false -c commit.gpgsign=false` into `w9-control-transcript/1` makes `output_sha256` deterministic and verifiable via `run_w9_detector_controls.py --verify-watched-to-fail` in CI and via `tools/run_w9_pinned_detectors.py` locally. See §9.2 and §10.2.
16. **PR-lane execution + I1 CODEOWNERS protection of `tests/tools/test_w9_detectors.py` and the `L1_LIVE` tripwire (`R1-M7`, `R2-M5`, `R3-i1`):** Wiring `tests/tools/test_w9_detectors.py` into `.github/workflows/ci.yml`'s `admission-controls` job (`ci.yml:166-216`) and `ADMISSION_CONTROL_MODULES` (`test_ci_platform_policy.py:175-229`)—loading YAML with `yaml.BaseLoader` and protecting `test_w9_detectors.py` and `legacy-write-detector.yml` under Owner Point I1 CODEOWNERS (with updated `GATE_FILES`/policy tests and `CONVENTIONS.md:713-729` amendment)—ensures `L1_LIVE` cannot be flipped or bypassed without Stephen's approval. See §2.3, §10.3, and Owner Points I & F (§16).

---

## 15. Stop rules for the code package

In addition to `06v` §8 (`06v-w9-implementation-plan.md:610-620`), the WP9.5 code package is bound by the following hard preconditions and runtime stop rules:

### 15.1 Hard preconditions before WP9.5 code is dispatched (`P-089` item 3, `03-decisions-and-open-questions.md:6104-6115`)

WP9.5 implementation code **must not** be dispatched until all four of the following are complete:

1. **U-3 recorded in §4.2.2 of this note (`06v:159`; `P-089` item 3, `03-decisions-and-open-questions.md:6105-6107`; `R2-m6`):**
   Stephen authorizes the read-only U-3 throwaway draft-PR probe (§4.2.2); the reviewing session executes it and records the exact HTTP status codes, `X-Accepted-GitHub-Permissions` headers, **and pinned JSON key presence** for `GET repos/ZK-Theory/TDL/rulesets/20822054`, `GET repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=day&per_page=5`, and `GET repos/ZK-Theory/TDL/commits/dbd54fe382e7b2849d3f2038393cbdb4d709477b/pulls` under `GITHUB_TOKEN` (`contents: read` and `pull-requests: read`) in the §4.2.2 table of this note, stating whether D-8 applies to `rule-suites`.
2. **U-4 handle-bound reader and segmenter dry run recorded in §4.3.3 of this note (`06v:160`; `P-089` items 3 & 4, `03-decisions-and-open-questions.md:6105-6107,6116-6117`; `R1-m8`, `R2-m7`, `R3-m6`):**
   The live U-4 metadata read (`2026-11-21T21:06:44Z`, `833,453` bytes, SHA-256 `73fcbe83...`) is already recorded in §4.3.3. Before WP9.5 code is dispatched, the reviewing session writes and runs the read-only scratch script `u4_dry_run.py` specified in §4.3.3 item 2 (which runs the §4.3.2 root checks, `handle_bound_read`, and `segment(raw, "computational_log_entry")` on `C:\Users\steph\Documents\TDA-Research\04-Methods\Computational-Log.md` with `PYTHONPATH=.` from the repo/worktree root and prints `root_checks`, `bytes`, `sha256`, `link_count`, `canonical_target`, `file_facts`, `row_counts`, and `blockers`) and records the result in §4.3.3.
3. **Owner Points I, C, A, B, D, E, F, G, H, J, K decided by Stephen in a decision-register entry (`P-090`):**
   Stephen records his disposition on Owner Points **I** through **K** (§16, deciding **I** first) in `docs/plans/agentic-research-system/03-decisions-and-open-questions.md` (and authorizes the dated WP9.3 amendment if Options A1, D3/D1, or E1 are selected, the dated `CONVENTIONS.md:713-729` CODEOWNERS policy amendment if Option I1 is selected, and the dated W9 §4.2 amendment if Option H1 is selected; if Option I3 is selected, also verify GitHub repository variable write access, `UNVERIFIED-4`, §21.2).
4. **Unconditional pre-code single scratch-store test timing profile (`P-087` item 7, `03-decisions-and-open-questions.md:5919-5923`; `R2-m13`, `R3-m5`):**
   Unconditionally before WP9.5 code is dispatched, profile one existing WP9.3/WP9.4 single scratch-store integration test alone on Stephen's machine (`UNVERIFIED-3`) and record the timing before adding WP9.5's scratch-store flow (`test_w9_wp9_5_detectors.py`).

*(Pre-L-1 gate note, `R3-m12`: after WP9.5 code lands and before L-1 activation on `main`, execute a one-shot throwaway `pull_request` rehearsal of `.github/workflows/legacy-write-detector.yml` with synthetic `walk-baseline.json` / `detector-controls.json`, closed without merging, as specified in §10.2 item 5.)*

### 15.2 Stop rules during WP9.5 code implementation

The WP9.5 code worker must stop immediately and return `PARTIAL` if:
1. Any change would modify a protected identity listed in §2.2 (the 275-row runtime-binding census, `wp6_1_06h_current_append_manifest.yaml` blob `1066404a`, `test_wp6_1_06h_append_path_closure.py` blob `3b1eec6e`, `research_system/schema_registry.py` blob `e32cb408`, `research_system/authority.py` blob `9b56b322`, core/W9 schemas, T2 expectations/seal, `tools/w9_segmentation.py` blob `43e1454de09b61e274954c42b21d6ae533857a24`, or `IMPORTER_MODULES` in `research_system/legacy/reader.py:42`) (`06v:614,618-619`).
2. Any change under `research_system/legacy/` would exceed the specific changes approved by Stephen under Owner Points A, D, E, and J.
3. Any test or negative control needs live legacy, vault, or restricted bytes, or writes to / leaves any state in `REPO_ROOT`, any linked worktree, or `C:\Users\steph\Documents\TDA-Research` (`06v:616-617`).
4. The new and changed WP9.5 test files (including `@pytest.mark.slow` tests) exceed the approved serial `--no-cov` test-time budget (Owner Point G) on Stephen's machine (`P-087` item 7, `03-decisions-and-open-questions.md:5919-5923`).
5. *(WP9.5-specific stop rule added by this design note, not in `06v` §8 (`R1-m13`)):* Any detector negative control fails to fire on its designated violation case or fires on a clean positive control case, or `test_recorded_detector_import_closure_covers_ast_walk` detects an unpinned `research_system` or `tools` import.

---

## 16. Owner points

Stephen's decision is requested on the following eleven points (**I** first—because **B**, **C**, and the L-1 guard depend on it—followed by **C, A, B, D, E, F, G, H, J, K**) before WP9.5 code is dispatched. Nothing in this note decides them for him.

| ID | Decision needed | Options | Recommendation | What it changes in accepted code or documents |
|---|---|---|---|---|
| **I** *(decide first)* | **Trust root protecting the detector surface, closure, tripwire, and `.research-system/evidence/w9/` against self-editing (`R1-B1`, `R1-M7`, `R1-M10`, `R2-M1`, `R2-M3`, `R2-M5`, `R3-M1`, `R3-m1`, `R3-m2`, `R3-m3`, `R3-m9`)** (§2.3, §6.1, §6.2.3, §6.4, §6.5 Rule 0, §10.2, §10.3). | **Option I1 (Rule 0 + Form (A) content-pinned whole-tree execution + `.github/CODEOWNERS` expansion — Recommended):** Enforce Rule 0 monotonicity (§6.5) **and** add **10** file patterns (`/.github/workflows/legacy-write-detector.yml`, `/tools/check_legacy_writes.py`, `/tools/check_conventions_legacy_locks.py`, `/tools/check_legacy_log_baseline.py`, `/tools/run_w9_detector_controls.py`, `/tools/run_w9_pinned_detectors.py` [operator-machine Form (A) batch-gate wrapper, `R3-m2`], `/tools/export_w9_registration_manifest.py`, `/tools/_w9_detector_evidence.py`, `/tests/tools/test_w9_detectors.py` [protecting `L1_LIVE`], and `/research_system/legacy/accepted_w9.py` [holding `ACCEPTED_CL_EXPORT` and `ACCEPTED_CONVENTIONS_CLASSIFICATION`, already governed code under `test_w9_wp9_3_binding_head.py:199-217`, `R3-m2`]) **plus** directory pattern `/.research-system/evidence/w9/` (so existing and L-1/post-L-1 evidence files are owned without failing pre-L-1 absence checks) to `.github/CODEOWNERS` (`@stephendor`), while the remaining 14 `research_system/` closure modules, `tools/w9_segmentation.py` (guarded by D-4), `pyproject.toml`, and `uv.lock` are content-pinned in `detector_closure_blobs` under Rule 0.2/0.3 (§6.2.2, §6.2.3). *Preventive vs detective boundary (`R3-M1`):* CODEOWNERS is **preventive** for the 10 file patterns and `.research-system/evidence/w9/`; for non-code-owned closure modules, Rule 0.3 is **detective** post-merge.<br>**Sub-choice on closure width (`R3-m3`):** **Option I1-default** keeps the 25-entry `detector_closure_blobs`; **Option I1-narrow** narrows the closure ahead of code by moving the few detector-only reader helpers (`git_blob_id`, `handle_bound_read`, or `segment` wrappers) into CODEOWNED `tools/` so non-detector PRs in `research_system/` stop triggering Rule 0.3.<br>*Full operational cost (`R3-m3`, `R3-m9 (c)`):* (1) every per-batch manifest PR, weekly vault-run PR, pre-batch ruleset-read PR, and baseline/pin-advance PR requires Stephen's own bypass merge (`admin-bypass-guard.sh:13-18`) **with a `Bypass reason:` line in the PR body** (`tools/check_bypass_merges.py:41,135`); and (2) under I1-default, every edit to the 14 non-code-owned `research_system/` closure modules (7 W9 PRs in the last 4 weeks: `31f675fe`, `23f8f737`, `6aeb3b31`, `baea2c13`, `cc81b733`, `95871b38`, `dbd54fe3`; 14 of 178 first-parent commits in 90 days) requires a pre-existing (`at P1`) hash-bound decision entry naming each changed path and `new_blob[:8]`, a same-PR `baselines` append, a re-recorded `detector-controls.json` (`--verify-watched-to-fail`), and Stephen's bypass merge with `Bypass reason:`.<br>**Option I2 (Rule 0 only, leaving `.github/CODEOWNERS` and `GATE_FILES` at their current 8 paths):** Do not expand `.github/CODEOWNERS`. *Warning (`R2-M1`, `R2-M5`, `R3-M1`):* under F1 + I2, the L-1 activation PR (`L1_LIVE`, workflow triggers), detector tools/wrapper, `accepted_w9.py`, and evidence files remain outside CODEOWNERS, so `P-089` item 3 and Option B1 are not preventively guarded and R1-B1 scenarios 4 and 5 stay open.<br>**Option I3 (Optional second, out-of-tree anchor — combinable with I1, `R3-m1`):** Define GitHub repository variable `W9_DETECTOR_PIN` storing `{"walk_baseline_commit": ..., "closure_blobs_sha256": ...}` (a canonical SHA-256 of `detector_closure_blobs`, not a commit SHA), set by Stephen at L-1. Once Option I3 is chosen, `.github/workflows/legacy-write-detector.yml` sets `REQUIRE_I3_PIN: "true"` and **fails closed** when `vars.W9_DETECTOR_PIN` is empty or disagrees (§10.2). *Warning (`R3-m1`, `UNVERIFIED-4` §21.2):* who on `ZK-Theory/TDL` can write repository Actions variables (`admin` vs `maintain`/`write`) is unverified here; Stephen must confirm variable write permissions before relying on I3, update `W9_DETECTOR_PIN` on every intentional detector closure upgrade, and keep Option I1 CODEOWNERS on `.github/workflows/legacy-write-detector.yml` and `tools/run_w9_pinned_detectors.py` so a PR cannot remove the check. | **Option I1** (choosing between **I1-default** and **I1-narrow**; optionally paired with **Option I3** after verifying repository variable write access, `UNVERIFIED-4`). **Option I2 does not close R1-B1** and is not sufficient for B1 or the L-1 guard. | **Option I1 (exact edits, `R2-M5`, `R3-m9`):** (1) Updates `.github/CODEOWNERS:1-12` scope header (recording reversal of the 2026-09-11 "merge-admission gate files only" rule) and `.github/CODEOWNERS:14-24` (`@stephendor`) with the **10** file patterns + `/.research-system/evidence/w9/` directory pattern; (2) lands all **9 new files** (`legacy-write-detector.yml`, 7 `tools/` files, `tests/tools/test_w9_detectors.py`) in the **same PR** as the CODEOWNERS edit (since `test_every_gate_file_exists_and_has_a_code_owner` `:364-369` checks `.is_file()`), splits/updates `tests/tools/test_ci_platform_policy.py` (`W9_DETECTOR_CODEOWNED_FILES` + `W9_DETECTOR_CODEOWNED_DIRS`) so directory pattern `/.research-system/evidence/w9/` checks CODEOWNERS ownership **without** `is_dir()` (`.research-system/evidence/` has no tracked file at `dbd54fe3`), and updates `test_codeowners_names_no_file_outside_the_gate` (`:372-374`) and its docstring; (3) **amends `CONVENTIONS.md:713-729`** (inside successor section `## ARS Foundation Governance`, lines 614–783, touching no legacy unit), recorded in `P-090`.<br>**Option I2:** No change to `.github/CODEOWNERS`, `GATE_FILES`, or `CONVENTIONS.md`.<br>**Option I3:** Adds repository variable `W9_DETECTOR_PIN` + sets `REQUIRE_I3_PIN: "true"` in §10.2. |
| **C** | **Committed append-only `walk-baseline.json`, Form (A) content pin, full re-walk + dual-tool diff, `acknowledged` (with late Rule 3 check), and disposition of the 22 post-freeze commits (`4b143c92..dbd54fe3`) (`R1-B1`, `R1-M3`, `R1-M12`, `R2-M1`, `R2-M2`, `R2-m1`, `R2-m14`, `R3-M1`, `R3-M2`, `R3-M3`, `R3-m4`, `R3-m10`, `R3-m11`)** (§6.2, §6.5). | **Option C1:** Commit `.research-system/evidence/w9/walk-baseline.json` (`format: "w9-walk-baseline/1"`, all top-level fields governed by Rule 0.2, §6.2.2) with:<br>  1. `baselines[0]["baseline_commit"]` set to **any known first-parent ancestor of L-1 on `main`** (e.g., the merged WP9.5 code commit), defining the **disposed pre-baseline interval `(4b143c92, baseline_commit]`**—whose `(dbd54fe3, baseline_commit]` delta is refreshed at L-1 into the L-1 decision entry via §21.1 item 3 (`R3-m10`)—and the **walked interval `(baseline_commit, head]`** re-walked in full on every run (`23.11s` stand-in over 320 commits, §21.1 item 10), plus `baselines[-1]["detector_closure_blobs"]` (including `pyproject.toml` and `uv.lock`, `R3-M1` Form A) allowing valid same-PR closure upgrades validated under Rule 0.2/0.3 and a **recomputed dual-tool pin-advance verdict diff** (`ERROR: Rule 0: pin advance changes verdicts`, `R3-M2`);<br>  2. an append-only **`acknowledged`** list (`{commit, rule, path, old_blob, new_blob, disposition_ref}` with `commit < source_commit <= P1(C_ack)` and slice match, **plus mandatory matching late entry in `<head>:shared-surface-changes.json` when `rule == "Rule 3"`**, `R3-M3`); and<br>  3. append-only **`ruleset_gap_acknowledgements`** (`{previous_recorded_at, acknowledged_through, disposition_ref}` validated under Rule 0.2, `R3-m11`).<br>`W9-T7` runs inside `tests/tools/test_w9_detectors.py` (`--baseline` + `--head` under `--ruleset-check skip`, `R3-m4`).<br>**Option C2:** Set `baselines[0]["baseline_commit"]` to `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (`2026-07-18`), and seed historical `acknowledged`/disposition entries for all 22 first-parent commits in §6.2.1 (`5df0c001` + `b132406e`, `811d5a2b` + `b132406e`, `#125`, `#129`, `#168`, `#169`, `#277`, `#334`, `#368`, `#388`, `#401`, `#433`, plus the `9` `CONVENTIONS.md`-only PRs). | **Option C1** (combining L-1 ancestor `baseline_commit`, Form (A) content-pinned `detector_closure_blobs`, recomputed full re-walk + dual-tool verdict diff, append-only `acknowledged` with late Rule 3 check, and `ruleset_gap_acknowledgements`). Starting at L-1 avoids carrying historic exemptions while Form (A) + full re-walk + dual-tool diff allow legitimate upgrades and prevent silent verdict flips (`R3-M1`, `R3-M2`). *(Depends on Option I1.)* | **Option C1 / C2:** Adds a dated row for `.research-system/evidence/w9/walk-baseline.json` in `docs/plans/agentic-research-system/implementation/06v-addendum-2026-11-10-w9-paths.md`. Loader lives in `tools/_w9_detector_evidence.py` (`research_system/legacy/` untouched). |
| **A** | **Carrying `"role"` and `"source_identity_kind"` in `.research-system/evidence/w9/registration-manifest.json` and format-version policy (`R1-M4`, `R1-M5`, `R1-m10`, `R2-m11 (c),(d)`, `R3-m13`)** (§5.3, §6.5, §6.6). | **Option A1 (5-key manifest, uniform `"w9-registration-manifest/2"` format, closed entries — Recommended):** Bump `REGISTRATION_MANIFEST_FORMAT` to **`"w9-registration-manifest/2"`** (same `/2` policy as Option D3, since no live `/1` manifest exists prior to L-1), project the 5 closed keys `{"root_kind", "root_id", "normalized_path", "role", "source_identity_kind"}` from `state["records"]["legacy_path_registration"]`, keep `require_registered` (`research_system/legacy/evidence.py:40,114-131`) strictly closed against extra keys (`test_w9_evidence.py:62`), check `(role, source_identity_kind)` when present on `registration`, and compare membership at line 129 on the 3 identity keys.<br>**Option A2:** Keep `registration-manifest.json` strictly at 3 keys (`"w9-registration-manifest/1"`, `evidence.py` untouched) and commit a companion file in `.research-system/evidence/w9/` mapping `(root_kind, root_id, normalized_path)` to `(role, source_identity_kind)`. | **Option A1.** Both `role` and `source_identity_kind` are already required fields on every `legacy-path-registration` record (`.research-system/schemas/contracts/w9/legacy-path-registration.schema.json:70-94`), Option A2 has no store-preparer check keeping the second file synchronized, and uniform `/2` versioning avoids mixing 3-key and 5-key shapes under `/1`. | **Option A1:** Modifies `REGISTRATION_MANIFEST_FORMAT` and `require_registered` in `research_system/legacy/evidence.py:40,114-131` (an accepted WP9.3 `LR-015` gate, so it **requires a dated WP9.3 amendment, independent review, and decision-register entry**, just like D3 and E1; `IMPORTER_MODULES` is untouched), plus test manifest builders in `tests/research_system/unit/test_w9_evidence.py`, `tests/research_system/integration/w9_runtime_harness.py:451-466`, `tests/research_system/integration/test_w9_wp9_4_1_runtime.py:95-109`, and `tests/research_system/integration/test_w9_wp9_4_2_runtime.py:86-100` (`R3-m13`). Because no WP9.4 production code changes (only test fixture manifest builders move from 3 keys to 5 keys), **WP9.4's acceptance review is not reopened** (covered by the dated WP9.3 amendment and independent review).<br>**Option A2:** Adds a dated row to `06v-addendum-2026-11-10-w9-paths.md` and leaves WP9.3 code and WP9.4 tests untouched. |
| **B** | **Location, in-commit (`at C`) evaluation, and pre-existing (`at P1`) provenance of W9 §4.2 write-allowance records** (`R1-B1`, `R1-M10`, `R2-m10`; §6.4). | **Option B1:** Commit `.research-system/evidence/w9/legacy-write-records.json` (`format: "w9-legacy-write-records/1"`, §6.4), keyed by `(pr_number, normalized_path, old_blob, new_blob)`. Evaluated **at commit `C`** so the PR carries its own record (`06v:486`), with `owner_note.source_commit` (citing a `### P-0xx` register entry whose slice names each `normalized_path`, `old_blob[:8]`, `new_blob[:8]`) and `independent_review.review_commit` (citing a review file binding the decision ID and tuples) required to be ancestors of **`P1`**, governed by Rule 0. Note (`R2-m10 (c),(d)`): `P1` ancestry proves pre-PR age rather than Stephen's authorship because `03-decisions-and-open-questions.md` and `reviews/` are not CODEOWNED, so **Option B1 is conditional on Option I1**; pre-PR `P1` ordering is also this note's stricter reading of W9 §4.2(b).<br>**Option B2:** Same as B1, except allow `owner_note` or `independent_review` to be committed inside `C` itself rather than at `P1`, relying on `.github/CODEOWNERS` (`@stephendor`) under Option I1.<br>**Option B3:** Parse §4.2 allowance metadata out of GitHub PR bodies/comments via `gh api` without a committed file in `.research-system/evidence/w9/`. | **Option B1 — conditional on Option I1.** Offline-testable in scratch clones, prevents retroactive blessing after `C`, binds both `P1` slices directly to the changed blobs (`R2-m10 (a),(b)`), and relies on Option I1 CODEOWNERS to enforce `@stephendor` merge control over `legacy-write-records.json`. | **Option B1 / B2:** Adds a dated row for `.research-system/evidence/w9/legacy-write-records.json` in `docs/plans/agentic-research-system/implementation/06v-addendum-2026-11-10-w9-paths.md` (`06v-addendum-2026-11-10-w9-paths.md:14-15`). Loader lives in `tools/_w9_detector_evidence.py` (`research_system/legacy/` untouched). |
| **D** | **Resolving the `O-32` squash-merge SHA contradiction in `.research-system/evidence/w9/shared-surface-changes.json`** between `06v:90-91,212,479-481` and `research_system/legacy/evidence.py:231-238` + `acceptance.py:135` (`R1-M6`, `R2-m11 (a),(b),(c)`, `R3-M3`; §6.5). | **Option D3 (Blob-keyed, tree-state equivalence, uniform `"w9-shared-surface-changes/2"` format, no commit field — Recommended):** Bump `SHARED_SURFACE_CHANGES_FORMAT` (`evidence.py:42`) to **`"w9-shared-surface-changes/2"`** (matching A1's uniform `/2` policy), with each entry closed on `{"pr_number", "surface", "old_blob", "new_blob", "affected_registrations"}` (no commit SHA). The PR changing a shared surface carries its own entry at `C`; Rule 3 matches `(pr_number, surface, old_blob, new_blob)` at `C`. Under `R3-M3`, any `acknowledged` row clearing a missed Rule 3 violation in `walk-baseline.json` is valid **only** once a late matching entry is appended to `<head>:.research-system/evidence/w9/shared-surface-changes.json`, keeping WP9.3's `check_change_list` (`acceptance.py:121-136`, which reads `shared-surface-changes.json` at `git_head`) bound to the change. In `acceptance.py:121-136`, an affected item's observation at `obs_commit = str(source.get("git_commit"))` passes iff `evidence.blob_at(repository_root, obs_commit, entry["surface"])` (`evidence.py:179-188`) equals `entry["new_blob"]` or the `new_blob` of a later entry for the same `surface` in `entries` *(tree-state equivalence semantic; see `HR-2` on revert cycles `A -> B -> A`, `R2-m11 (a)`)*.<br>**Option D1 (Base-commit + blob check):** Entry carries `{"pr_number", "base_commit", "surface", "old_blob", "new_blob", "affected_registrations"}`. *(Unsound as an ancestry test because `main` can advance in the queue after `base_commit`; redundant with D3.)*<br>**Option D2 (Two-PR protocol, keeping `evidence.py:231` and `acceptance.py:135` unchanged):** W9 §4.3 owner note in PR 1, follow-up PR 2 writes `merge_commit` into `shared-surface-changes.json`. *(Leaves a red detector window between the two PRs.)* | **Option D3.** Avoids both the unknowable squash SHA (`06v:90-91`) and D1's queue race, uses `evidence.blob_at` (`evidence.py:179-188`), allows atomic in-PR reporting at `C` (and safe late-entry recovery on Rule 3 acknowledgements, `R3-M3`), and shares A1's clean `/2` format-versioning policy. | **Option D3 (or D1):** Modifies `research_system/legacy/evidence.py:42,190-252` (`SHARED_SURFACE_CHANGES_FORMAT`, `_change_entries`, and `require_change_list` docstring), `research_system/legacy/acceptance.py:121-136` (`check_change_list`), WP9.3 tests (`tests/research_system/unit/test_w9_evidence_acceptance.py` and `tests/research_system/integration/test_w9_wp9_3_2_runtime.py`, `R2-m11 (b)`), and `06v-addendum-2026-11-10-w9-paths.md:28`. Requires a **dated WP9.3 amendment (`wp9-3-design-note.md` §10.4), an independent review, and a decision-register entry**. (`IMPORTER_MODULES` is untouched.) |
| **E** | **Enforcing D-5 ("a missed weekly vault-detector run blocks the next batch", `06v:567`): gate placement, reset, and weekly PR + `advance-binding` cost** (`R1-M8`, `R2-M5`; §8.4). | **Option E1 (Store-preparer gate at batch start `LR-003`/`LR-015` and batch acceptance `LR-016`/`LR-020`):** Commit `.research-system/evidence/w9/vault-detector-runs.json` (`format: "w9-vault-detector-runs/1"`, §8.4, with `"kind": "run"` and `"kind": "owner_cadence_reset"` entries). When `bool(reader.accepted_cl_export)` is `True` (never gated on "file present"), enforce `require_vault_detector_cadence` at **`LR-003`** (`prepare_proposal`, `research_system/legacy/preparers.py:686-690`), **`LR-015`** (`prepare_observation`, `preparers.py:1215-1218`), **`LR-016`**, and **`LR-020`** (`check_environment`, `research_system/legacy/acceptance.py:147-152`), as well as in `tools/check_legacy_log_baseline.py --check-cadence`. Each weekly run requires a reviewed PR to `main` (requiring Stephen's bypass merge under Option I1) plus `ars store advance-binding` before store commands run.<br>**Option E2 (CLI pre-batch check tool only, leaving `preparers.py` and `acceptance.py` untouched):** Enforce the 7-day cadence and `"owner_cadence_reset"` rule on `.research-system/evidence/w9/vault-detector-runs.json` in `tools/check_legacy_log_baseline.py --check-cadence` (`06v:604`), acknowledging that without E1 the block is CLI-checklist only. | **Option E1** if Stephen accepts the weekly PR (+ I1 bypass merge) + `advance-binding` cost and a dated WP9.3 amendment for hooking `LR-003`/`LR-015`/`LR-016`/`LR-020`; **Option E2** if keeping `preparers.py` and `acceptance.py` untouched is preferred. Recommend **Option E1** so "a missed run blocks the next batch" (`06v:567`) is machine-enforced at batch start. | **Option E1:** Adds `VAULT_DETECTOR_RUNS` and `require_vault_detector_cadence` in `research_system/legacy/evidence.py`, calls it in `research_system/legacy/preparers.py:686-690,1215-1218` and `research_system/legacy/acceptance.py:147-152`, adds a dated row to `06v-addendum-2026-11-10-w9-paths.md`, and requires a **dated WP9.3 amendment and independent review**.<br>**Option E2:** Adds a dated row to `06v-addendum-2026-11-10-w9-paths.md`; `research_system/legacy/` is untouched. |
| **F** | **Running `tests/tools/test_w9_detectors.py` (including `L1_LIVE` tripwire and `W9-T7`) in a real PR lane vs `.github/CODEOWNERS` (`R1-M7`, `R2-M5`, `R2-m13`, `R3-m4`, `R3-m7 (a)`)** (§2.3, §10.3, §12.1). | **Option F1 (Wire into `.github/workflows/ci.yml` `admission-controls` — Recommended):** Add `tests/tools/test_w9_detectors.py` (including `L1_LIVE` tripwire and `W9-T7` scratch-clone replay, `R3-m4`) to `.github/workflows/ci.yml`'s `admission-controls` job (`ci.yml:166-216`) and to `ADMISSION_CONTROL_MODULES` in `tests/tools/test_ci_platform_policy.py:175-229` (following `tests/tools/test_w9_segmentation.py` at `ci.yml:210` and `test_ci_platform_policy.py:226`), with `L1_LIVE = False` flipped to `True` in the L-1 PR. *(Note on I interplay, `R2-M5`: under Option I1, `tests/tools/test_w9_detectors.py` and `legacy-write-detector.yml` are CODEOWNED by `@stephendor`, preventively guarding `L1_LIVE`; under Option I2, an ordinary PR could flip `L1_LIVE = True` + edit `legacy-write-detector.yml` without Stephen's bypass.)* `tests/research_system/integration/test_w9_wp9_5_detectors.py` (`M-6` and `O-13`) runs via `tools/affected_research_tests.py:120-147` on PRs that touch `research_system/` or `tests/research_system/` or `.research-system/`—**not** on `tools/`-only PRs, where it runs in advisory nightly/on-demand `.github/workflows/research-system-suite.yml` (`-m "not live_store"`, `:8-9,15,17`), and every weekly `.research-system/evidence/w9/` PR selects contract tests (`R3-m4`).<br>**Option F2 (Reference in `legacy-write-detector.yml` only):** Would run `test_w9_detectors.py` and the `L1_LIVE` tripwire in **no PR lane** before L-1. | **Option F1** (combined with **Option I1** so `L1_LIVE` is code-owner protected). Stephen merges the WP9.5 PR himself because `.github/workflows/ci.yml` is in `.github/CODEOWNERS:18`. | **Option F1:** Edits `.github/workflows/ci.yml:212` (owned by `@stephendor` in `.github/CODEOWNERS:18`, requiring Stephen's own merge) and `tests/tools/test_ci_platform_policy.py:228`. |
| **G** | **Test-time budget for WP9.5 (including `@pytest.mark.slow` tests)** (`R1-m14`, `R2-m13`, `R3-m5`; §12.3, §15.1). | **Option G1 (Recommended pending unconditional pre-code profile):** Apply the **5-minute (300-second)** serial `--no-cov` budget established for WP9.4-2 in `P-087` item 7 (`03-decisions-and-open-questions.md:5919-5923`), explicitly counting all new and changed WP9.5 tests (including `@pytest.mark.slow` tests in `test_w9_wp9_5_detectors.py`), with over-budget returning `PARTIAL` with measurements.<br>**Option G2:** Tighten the WP9.5 ceiling to **2 minutes (120 seconds)** serial `--no-cov` (all tests, including `slow`) after executing the **unconditional** pre-code profile of one existing single scratch-store test alone on Stephen's machine (`UNVERIFIED-3`, §15.1 item 4, `R2-m13`, `R3-m5`). | **Option G1 (5 minutes / 300 seconds)** until the unconditional pre-code single-store timing profile (`P-087` item 7, §15.1 item 4) is measured and recorded (`R2-m13`, `R3-m5`). | Recorded in the WP9.5 authorization register entry (`P-090`); changes no existing code or document. |
| **H** | **Handling routine `.apm/tracker.md` Working-Note appends after `.apm/tracker.md` is registered** (`R1-M5`, `R2-m15`, Review §4 H; §6.2.1, §6.5 Rule 1). | **Option H1 (Mechanically verified Working-Note append allowance — Recommended):** Add a dated W9 §4.2 amendment permitting a merged PR (`merge_commit_sha == C`) to modify `.apm/tracker.md` without a §4.2(b) record **if and only if** `tools/check_legacy_writes.py` verifies via `segment(raw, "tracker_task_row")` and `segment(raw, "working_note_entry")` (`research_system/legacy/segmentation.py:470-473`) that (i) every `tracker_task_row` and every byte outside `## Working Notes` is byte-identical between `P1` and `C`, (ii) every `working_note_entry` at `P1` is preserved byte-for-byte in order at `C` with 0 blockers, and (iii) any byte inside `## Working Notes` outside entry spans consists solely of whitespace/blank separator lines matching `[ \t]*\n` (e.g. one blank `+1`-byte line per appended note, verified against `#368`, `#388`, and `#433` in `wp9-5-note-r2-review-2026-11-21.md:219`). Under `O-33` (`06v:213`), any blob change during an open `.apm/tracker.md` observation/acceptance window still blocks that open window until re-observed.<br>**Option H2 (Require a full W9 §4.2(b) record in `legacy-write-records.json` for every `.apm/tracker.md` Working-Note PR):** Every Phase-5-style or worktree-sweep tracker PR (`#368` `452352ff` — recording L5, A6, A7 and step 3 batches 1–3 of 06s Phase 5, `R2-m15` — plus worktree sweeps `#388` `e3519ba7` and `#433` `a6a98966`) requires a `legacy-write-records.json` entry with pre-existing register entry and review.<br>**Option H3 (Freeze `.apm/tracker.md` completely at L-1 and move successor notes elsewhere):** No further writes to `.apm/tracker.md` after L-1. | **Option H1** (or **Option H3** if Stephen prefers stopping all `.apm/tracker.md` appends at L-1). Option H1 uses the already-tested `tracker_task_row` and `working_note_entry` segmenters (`segmentation.py:470-473`) and passed independent verification against `#368`, `#388`, and `#433` (`wp9-5-note-r2-review-2026-11-21.md:219`). | **Option H1:** Requires a dated W9 §4.2 amendment (recorded in `03-decisions-and-open-questions.md` `P-090` and `09-migration-compatibility-and-pilot.md` §4.2); implemented inside `tools/check_legacy_writes.py` (`research_system/legacy/` untouched).<br>**Option H2 / H3:** No W9 amendment. |
| **J** | **Source, format, and pinning of the legacy/successor classification for the vault Computational-Log detector and the `CONVENTIONS.md` check** (`R1-M9`, `R2-M4`, `R2-m3`, `R3-m2`; §7.3, §7.6, §8.2, §8.3). | **Option J1 (1-based `w9-cl-classified-list/1` in `ACCEPTED_CL_EXPORT[-1]["classified_list"]`, plus `ACCEPTED_CONVENTIONS_CLASSIFICATION` constant pinning `"w9-conventions-classified-locks/1"` by `(anchor_text, unit_hash)` — Recommended):**<br>1. **Vault detector:** Validate `ACCEPTED_CL_EXPORT[-1]["classified_list"]` (`research_system/legacy/accepted_w9.py:86-88`) against `"w9-cl-classified-list/1"` with **1-based** row ordinals $1, \dots, N$ matching `row["row_ordinal"]` (`evidence.py:347-358`; `segmentation.py:408`) and non-null `"legacy"`/`"successor"` labels (fixture tests may use `--fixture-classified-list`).<br>2. **`CONVENTIONS.md` check (`R2-M4`):** Default to the conservative 9-section (`68`-unit) partition while `ACCEPTED_CONVENTIONS_CLASSIFICATION == ()` in `research_system/legacy/accepted_w9.py`. At L-0b, add `ACCEPTED_CONVENTIONS_CLASSIFICATION` entry `{"repository_path", "git_commit", "git_blob", "sha256", "byte_length"}` pointing to the accepted `"w9-conventions-classified-locks/1"` JSON keyed on `(anchor_text, unit_hash)` (`segmentation.py:391-402`) with 1-based `unit_ordinal` per section; the checker reads that blob **at that pinned commit**, never `<head>` (`--classified-locks` is test-only, locked behind `--candidate-file`), protected by Rule 0.2 and Control N7 (§7.3, §7.6).<br>**Option J2 (Carry final labels directly inside `export["classifications"]` of `w9-cl-export/1` at L-0b, leaving `CONVENTIONS.md` 9-section permanent):** Tightens `require_cl_export` at L-0b to forbid `null` and omits per-unit `CONVENTIONS.md` reclassification. | **Option J1.** Matches `ACCEPTED_CL_EXPORT`'s 3-member structure (`accepted_w9.py:86-88`) without touching WP9.3's `require_cl_export`, keeps D-4 unchanged, and prevents an L-0b classification file edit on `<head>` from self-redefining the `CONVENTIONS.md` lock (`R2-M4`). | **Option J1:** Adds empty `ACCEPTED_CONVENTIONS_CLASSIFICATION: tuple[MappingProxyType[str, Any], ...] = ()` in `research_system/legacy/accepted_w9.py` (leaf module not in `IMPORTER_MODULES`, keeping `tool_sha256` and D-4 unchanged; added to `.github/CODEOWNERS` under Option I1 per `R3-m2` and run via `tools/run_w9_pinned_detectors.py` locally), implemented in `tools/check_legacy_log_baseline.py`, `tools/check_conventions_legacy_locks.py`, and `tools/_w9_detector_evidence.py`. At L-0b, `ACCEPTED_CL_EXPORT`, `ACCEPTED_CONVENTIONS_CLASSIFICATION`, and `06v-addendum-2026-11-10-w9-paths.md` are populated by the L-0b PR. |
| **K** | **Running `tools/check_conventions_legacy_locks.py` on pull requests in `ci.yml` `admission-controls` (`06v:491-492` says `"CONVENTIONS.md check. tools/check_conventions_legacy_locks.py, as a CI job"`)** (`R3-i2`; §7.5). | **Option K1 (Add to `.github/workflows/ci.yml` `admission-controls` — Recommended):** Run `tools/check_conventions_legacy_locks.py` as a fast (`< 0.15s`, §12.3) step in `ci.yml`'s existing required `admission-controls` job on every PR (in addition to post-merge CI in `legacy-write-detector.yml`, operator-machine pre-batch `tools/run_w9_pinned_detectors.py`, and unit tests). Makes `CONVENTIONS.md` legacy-lock preservation **preventive** before merge with **zero** change to ruleset `20822054` (since `admission-controls` is already a required context).<br>**Option K2 (Keep post-merge CI, pre-batch operator wrapper, and unit tests only):** Leave `.github/workflows/ci.yml` unchanged beyond Option F1, saving one step in `admission-controls` at the cost that unrecorded `CONVENTIONS.md` lock edits are only detected post-merge (or at batch start) rather than blocked on PRs. | **Option K1.** Directly implements `06v:491-492` preventively for `< 0.15s` per PR with no ruleset change. | **Option K1:** Adds one step running `tools/check_conventions_legacy_locks.py` inside `.github/workflows/ci.yml` `admission-controls` (already edited under Option F1 and owned by `@stephendor` at `.github/CODEOWNERS:18`).<br>**Option K2:** No additional change. |

---

## 17. Change log

| Revision | Date | Author | Summary |
|---|---|---|---|
| Revision 1 | 2026-11-21 | Gemini agent (under `P-089`) | Initial draft of the WP9.5 design note (`65363e27`) for independent adversarial review. |
| Revision 2 | 2026-11-21 | Gemini agent (under `P-089`) | Rework addressing revision 1 findings (`R1-B1`, `R1-M1`–`R1-M12`, `R1-m1`–`R1-m14`, `R1-i1`–`R1-i6`) from `docs/plans/agentic-research-system/reviews/wp9-5-note-r1-review-2026-11-21.md` (`edb9acc6`). *(Note: 6 residual citation/name defects identified in revision 2's review are corrected in revision 3, §19.)* |
| Revision 3 | 2026-11-21 | Gemini agent (under `P-089`) | Revision addressing every finding (`R2-M1`–`R2-M5`, `R2-m1`–`R2-m16`, `R2-i1`–`R2-i6`) from `docs/plans/agentic-research-system/reviews/wp9-5-note-r2-review-2026-11-21.md` (`3cf35bec`). |
| Revision 4 | 2026-11-22 | Gemini agent (under `P-089`) | Narrow rework addressing all 20 findings (`R3-M1`–`R3-M3`, `R3-m1`–`R3-m13`, `R3-i1`–`R3-i4`) from `docs/plans/agentic-research-system/reviews/wp9-5-note-r3-review-2026-11-21.md` (`1bd4ecff`): Form (A) content-pinning + full re-walk + dual-tool verdict diff, Rule 3 late change-list entry check, operator-machine wrapper `tools/run_w9_pinned_detectors.py` + `accepted_w9.py` CODEOWNERS, `W9-T7` moved to `tests/tools/test_w9_detectors.py`, Owner Point K, complete R3 changelog (§20), and deletion of superseded text in §1–§17. |

---

## 18. Change log: revision 1 to revision 2

Every finding in `docs/plans/agentic-research-system/reviews/wp9-5-note-r1-review-2026-11-21.md` (`edb9acc6`) is disposed of below *(note that `R2-M1`–`R2-M5` and `R2-m1`–`R2-m16` identified remaining gaps and six residual citations from revision 2, all addressed in §19)*:

| Finding ID | Severity | What changed in revision 2 and where |
|---|---|---|
| **R1-B1** | Blocking | **Adopted in full (§6.1, §6.2.2, §6.4, §6.5, §10.2, §12.1, §16 B/C/I).** Time-indexed all evidence reads: Rules 1 and 3 evaluate against `registration-manifest.json` at `P1` (union `C`, preventing atomic disarm and eliminating retroactive false positives on pre-registration commits); `legacy-write-records.json` and `shared-surface-changes.json` are read at `C` (so the PR carries its own record and no later commit can retroactively bless `C`). Added **Rule 0** (monotonicity of `registration-manifest.json`, `legacy-write-records.json`, `shared-surface-changes.json`, `walk-baseline.json`, `vault-detector-runs.json`, `detector-controls.json`, detector tools, and workflow). Replaced the in-script baseline constant with `.research-system/evidence/w9/walk-baseline.json` (`w9-walk-baseline/1`, append-only, verified to lie on `<head>`'s first-parent chain) and pinned detector tool blobs to `<baseline>`. |
| **R1-M1** | Major | **Adopted in full (§4.3.1, §4.3.3, §8.2, §8.4, §18).** Deleted the fabricated `376,784`-byte / `4c1898aa...` / line 541–545 blocker figures and the stray `"Wait:"` paragraph. Replaced §4.3.1 and §4.3.3 with the verified WP9.2 contract census figures from `w9-segmentation-contract-v1.md:242,254-258` (`700,632` bytes / `de44a67b...` / 255 entries / 1 structural / 0 blockers, and `703,531` bytes / `19ad5c4d...` / 256 entries / 1 structural / 0 blockers, explicitly labeled as grammar census evidence, not a baseline) and the live U-4 metadata read from `2026-11-21T21:06:44Z` (`833,453` bytes, SHA-256 `73fcbe83...`). |
| **R1-M2** | Major | **Adopted in full (§2.1, §2.2, §2.3, §4.3.1, §4.3.2, §5.3, §7.2, §8.2, §8.3, §9.2).** Removed every nonexistent symbol (`_is_reparse_or_symlink`, `FILE_ATTRIBUTE_REPARSE_POINT`, `_is_within`, `LegacyReplayEngine`, `state["store_binding"]`, `research_system/core/canonical.py`, `segment_bytes(profile=...)`, `AcceptedClExport`, `export["region"]["kind"]`). Re-derived all mechanisms against the actual code at `dbd54fe38`: `open_registered_root_anchor` (`research_system/store/anchor.py:1934-1950`, `reject_reparse=False`), `handle_bound_read` and `LegacyReader.__init__` (`research_system/legacy/reader.py:140-206,241-248`), `_legacy_projection` (`research_system/cli.py:1648-1659`) calling `replay_legacy` (`research_system/legacy/replay/driver.py:147`), `_legacy_current_binding` (`cli.py:1662-1684`) calling `load_current_binding` (`research_system/store/current_binding.py:801`) with `binding.binding["git_head"]` (`cli.py:1714`), `canonical_bytes` (`research_system/canonical.py:40-48`), `segment(data, selector_kind, ...)` (`research_system/legacy/segmentation.py:429-488`), `require_cl_export(export)` (`research_system/legacy/evidence.py:277-362`), `ACCEPTED_CL_EXPORT` (`research_system/legacy/accepted_w9.py:86-88`), `prepare_proposal` (`research_system/legacy/preparers.py:676,686-690`), `prepare_observation` (`preparers.py:1200,1215-1218`), and `CL_EXPORT_PRODUCER` (`evidence.py:52-54`). Placed detector-only evidence loaders in `tools/_w9_detector_evidence.py` (**new**) and named every option that touches `research_system/legacy/` in §2.3 and §16. |
| **R1-M3** | Major | **Adopted in full (§6.2.1, §6.5, §7.3, §7.5, §11.2, §12.1, §16 C, Appendix A §21.1).** Verified and corrected commit dates, parent counts, PR numbers, and file lists via `git` in the worktree (reproducible commands in Appendix A §21.1; independently reproduced in `wp9-5-note-r2-review-2026-11-21.md:137-164`): `811d5a2b` (`2026-08-07T00:12:09+01:00`, 9 files total: 3 `contracts/manifests/input-provenance/` + 6 others), `b132406e` (`#219`, `2026-08-08T22:23:06+01:00`), `5df0c001` (`2026-08-05T05:32:38+01:00`, 11 files total: 7 `results/` files across `panel_methodology/bhps_nonoverlap/`, `trajectory_tda_bhps/`, and `trajectory_tda_integration/` + 4 non-`results/` files), `#125` `02ebcaf6`, `#129` `5795a18b` (second parent `1af52f6d`), `#168` `9016b663`, `#169` `2111ce62`, `#277` `1dbf6b7b`, `#334` `eba3fe69`, `#368` `452352ff` (caption corrected in revision 3 under `R2-m15`), `#387` `3fa437a1`, `#388` `e3519ba7`, `#401` `633ed58e`, `#419` `14a81b84`, `#425` `1fba78aa`, `#433` `a6a98966`. Corrected `CONVENTIONS.md` per-section counts at `dbd54fe3` (`Always` 24->24, `Never` 13->13, `Computational Environment` 8->15, `inserted_successor_units_in_legacy_sections: 7`, total units `90`). Replaced nonexistent contract examples with real tracked paths (`contracts/manifests/research-assurance.yaml`, `contracts/stochastic-tests/monte-carlo-permutation-p-value.yaml`, etc.). W9-T7 now derives its 10 fixture paths via `git diff-tree`. |
| **R1-M4** | Major | **Adopted in full (§5.3, §6.5 Rule 1, §6.6 item 2, §16 A).** Widened Owner Point A (Option A1) so `registration-manifest.json` carries both `"role"` and `"source_identity_kind"`. Restricted Rule 1 and §6.6's `git cat-file` check to `root_kind == "repository_root"` and `source_identity_kind == "git_tracked"`, explicitly excluding `untracked_file`, `restricted_untracked_file`, `vault_root`, `successor_results_root` (`results/ars/`), and `legacy_read_only_projection` (`.research-system/projections/legacy/`). |
| **R1-M5** | Major | **Adopted in full (§6.5 Rule 1, §7.1, §16 H).** Excluded `role == "conventions_lock"` (`CONVENTIONS.md`) from Rule 1 (since `CONVENTIONS.md` is governed by `tools/check_conventions_legacy_locks.py` under W9 §4.4 and §7.3). Added **Owner Point H** for `.apm/tracker.md` Working Notes (recommending Option H1: a dated W9 §4.2 amendment permitting pure Working-Note appends verified mechanically by `segment(raw, "tracker_task_row")` and `segment(raw, "working_note_entry")`). |
| **R1-M6** | Major | **Adopted in full (§2.3, §6.5 Rule 3, §16 D).** Added **Option D3 (Recommended: blob-keyed `{pr_number, surface, old_blob, new_blob, affected_registrations}`, tree-state freshness via `evidence.blob_at` in `acceptance.py:check_change_list`, no commit field)** alongside D1 and D2. Documented why D1's `base_commit` is unsound under the merge queue and why D2 leaves a red window. Explicitly stated that D3 (or D1) modifies accepted WP9.3 gate code (`evidence.py:_change_entries` and `acceptance.py:check_change_list`) and therefore requires a dated WP9.3 amendment, an independent review, and a decision-register entry. |
| **R1-M7** | Major | **Adopted in full (§2.3, §10.3, §16 F).** Corrected the `.github/CODEOWNERS` list to the exact 8 paths owned by `@stephendor` (`.github/CODEOWNERS:14-24`; `GATE_FILES` in `tests/tools/test_ci_platform_policy.py:341-350`), noting that `test_ci_platform_policy.py` and `check_test_commit_literals.py` are not code-owned and that `tools/affected_research_tests.py:53-56` selects only `research_system/` and `tests/research_system/` imports. Recommended **Option F1** (wiring `tests/tools/test_w9_detectors.py` into `.github/workflows/ci.yml` `admission-controls` and `ADMISSION_CONTROL_MODULES`, merged by Stephen himself under `@stephendor`) and specified the `L1_LIVE = False` constant in `test_w9_detectors.py` flipped to `True` in the L-1 activation PR. |
| **R1-M8** | Major | **Adopted in full (§2.3, §8.4, §13.2 HR-4, §16 E).** Under Option E1, placed the D-5 cadence gate at batch start (`LR-003` in `preparers.py:686-690` and `LR-015` in `preparers.py:1215-1218`) as well as batch acceptance (`LR-016` and `LR-020` in `acceptance.py:147-152`); gated strictly on `bool(reader.accepted_cl_export)` (never on "file present"); added `"kind": "owner_cadence_reset"` in `vault-detector-runs.json` so one missed weekly run blocks the next batch until Stephen resets it rather than bricking the store forever; stated the weekly PR + `ars store advance-binding` cost and the self-attestation limit (`HR-4`). |
| **R1-M9** | Major | **Adopted in full (§7.3, §8.2, §8.3, §16 J).** Defined the closed `"w9-cl-classified-list/1"` format for `ACCEPTED_CL_EXPORT[-1]["classified_list"]` (`research_system/legacy/accepted_w9.py:86-88`), stated that the 9-section (`68`-unit) `CONVENTIONS.md` partition is provisional until L-0b's accepted classification, added `--classified-locks` to `tools/check_conventions_legacy_locks.py`, and added **Owner Point J**. |
| **R1-M10** | Major | **Adopted in full (§6.4, §6.5 Rule 0, §13.2 HR-1/HR-3, §16 B/I).** Required `owner_note.source_commit` (citing a `### P-0xx` register entry) and `independent_review.review_commit` in `legacy-write-records.json` to be ancestors of **`P1`** (pre-existing on `main` before PR `C`), added Rule 0 monotonicity, added **Owner Point I** (expanded in revision 3 under `R2-M5`), and stated the residual post-merge detection limit in `HR-3`. |
| **R1-M11** | Major | **Adopted in full (§4.2.1, §4.2.2, §10.2).** Replaced the unrunnable `workflow_dispatch` probe with a runnable `on: pull_request:` probe on a throwaway draft PR (`probe/w9-u3-token-read`, closed without merging), added the third call (`GET repos/ZK-Theory/TDL/commits/dbd54fe3.../pulls`) tested under both `permissions: contents: read` and `permissions: contents: read, pull-requests: read`, added `X-Accepted-GitHub-Permissions` logging, declared `permissions: contents: read, pull-requests: read` in `legacy-write-detector.yml`, stated that Call 2 (`rule-suites`) decides D-8, and marked `GITHUB_TOKEN` behavior on `rulesets/20822054` and `commits/<sha>/pulls` as `UNVERIFIED` pending the probe. |
| **R1-M12** | Major | **Partly addressed in revision 2, completed in revision 3 (`R2-m1`, §6.2.1, §6.2.2, §16 C, Appendix A §21.1).** Revision 2 listed 20 first-parent commits; revision 3 added the 2 missing `CONVENTIONS.md` PRs (`#419` `14a81b84`, `#425` `1fba78aa`), bringing the verified inventory between `4b143c92` and `dbd54fe3` to all **22** first-parent commits touching `CONVENTIONS.md`, `results/`, `papers/`, `contracts/`, or `.apm/` (with exact SHAs, dates, parent counts, touched paths, and dispositions). |
| **R1-m1** | Minor | **Adopted in full (§4.2.3).** Quoted both `06v:571` and `P-064` item 8 (`03-decisions-and-open-questions.md:4232-4233`) accurately, restricted D-8's trigger strictly to `rulesets/rule-suites`, and required an owner-accepted `d8_rule_suites_limit_decision_ref` in `walk-baseline.json` before `--ruleset-check ci-d8` is admitted. |
| **R1-m2** | Minor | **Adopted in full (§4.1, §12.1, §13.2 HR-5).** Pinned `allowed_merge_methods: ["squash"]`, `merge_queue: {merge_method: "SQUASH", max_entries_to_build: 1, min_entries_to_merge: 1, max_entries_to_merge: 1}`, `strict_required_status_checks_policy: true`, `required_review_thread_resolution: true`, the 4 required status-check contexts, and `target_include: ["refs/heads/main"]` (from our live `gh api` read). Added the 30-day (`MAX_DAYS = 30`) fail-closed age check on the previous recorded ruleset read. |
| **R1-m3** | Minor | **Adopted in full (§11.3, §12.1).** Replaced plain `git status` with a recursive `os.scandir(..., follow_symlinks=False)` snapshot of `.git` plus `git --no-optional-locks --no-replace-objects status --porcelain=v1 --ignored -z` and `rev-parse HEAD`, and pinned `cwd=tmp_path` and `GIT_DIR` in every detector test invocation (scoped to checkout-specific `REPO_ROOT` surfaces in revision 3 under `R2-m16`). |
| **R1-m4** | Minor | **Adopted in full (§9.2, §10.3, §12.1).** Bound each detector tool's `git_blob_id` into `w9-control-transcript/1`, pinned `CONTROL_GIT_ENV` (`GIT_AUTHOR_DATE`, `GIT_COMMITTER_DATE`, etc.) for all synthetic commits so `<C>` SHAs are deterministic, and added `run_w9_detector_controls.py --verify-watched-to-fail` to re-run and compare the 3 `watched_to_fail` hashes in CI after L-1. |
| **R1-m5** | Minor | **Adopted in full (§6.3 item 3, §6.6 item 3, §12.1).** Added 3-try exponential backoff (`1s, 2s, 4s`) on empty `commits/<C>/pulls`, added `pulls/<N>` subject-hint fallback verified by `merge_commit_sha == C`, and separated GitHub API/transport errors (exit `2`) from unmapped commits (exit `1`). |
| **R1-m6** | Minor | **Adopted in full (§6.3 item 3.4, §10.2, §12.1).** Hard-locked `--pr-map` and `--manifest-file` so `tools/check_legacy_writes.py` exits `2` unless `--ruleset-check skip` is also passed (extended to `--baseline` and `--head` in revision 3 under `R2-M1`), and added a unit test verifying `.github/workflows/legacy-write-detector.yml` passes none of them. |
| **R1-m7** | Minor | **Adopted in full (§10.2).** Wrote out the complete `steps:` block of `.github/workflows/legacy-write-detector.yml` with `fetch-depth: 0`, `git fetch --no-tags origin main:refs/remotes/origin/main`, and the check that `target_head` is `origin/main`'s tip or lies on `origin/main`'s first-parent chain. |
| **R1-m8** | Minor | **Adopted in full (§4.3.3, §8.2 Check 1, §8.5, §15.1).** Specified the exact pre-code dry-run check exercising `handle_bound_read` and `segment(raw, "computational_log_entry")` on the real vault path (replaced inline `python -c` with scratch script `u4_dry_run.py` and fixed `start_line`/`line_count` keys in revision 3 under `R2-m3`, `R2-m7`), and removed the whole-file `line_ending == "LF"` requirement from the vault detector so a CRLF successor entry saved by Obsidian does not trip when all legacy row hashes match. |
| **R1-m9** | Minor | **Adopted in full (§2.1, §2.2, §5.1, §5.3).** Removed the unrelated CLI reference to Owner Point A, corrected the D-1 store path to `C:/Users/steph/TDL-ARS-G7-Control` (`06v:563`), and cited `tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml` and `test_wp6_1_06h_append_path_closure.py` for the 275-row census instead of a nonexistent `contracts/runtime-binding-census.yaml` path. |
| **R1-m10** | Minor | **Adopted in full (§2.3, §5.3, §16 A).** Specified the exact update to `require_registered` (`research_system/legacy/evidence.py:124-130`): `_closed` accepts the 5-key manifest entry, verifies `(role, source_identity_kind)` when present, and projects each entry to the 3 identity keys `("root_kind", "root_id", "normalized_path")` at line 129 so `wanted not in ...` matches at `LR-015`. |
| **R1-m11** | Minor | **Adopted in full (§7.4 item 5, §7.6 Control N6).** Added the first-byte `|` check on inserted units in legacy-lock sections of `CONVENTIONS.md` so inserted tables are rejected (`W9` §7.3 item 4 allows only bullets or paragraphs), and stated the accepted structural-byte exceptions (`---` rules, blank lines, footer, H1 preamble, `### ` sub-headings) explicitly. |
| **R1-m12** | Minor | **Adopted in full (§14).** Expanded §14 to 16 load-bearing claims covering time-indexed evidence, Rule 0, manifest fields, Rule 1 matching and exclusions, `.apm/tracker.md` Working Notes, §4.2 record keying and `P1`-anchored provenance, 2-parent merge diffs, PR mapping and `5df0c001`/`811d5a2b` genealogy, Option D3 blob-keyed freshness, ruleset pinning and U-3 probe, explicit vault-root junction refusal, `CONVENTIONS.md` unit counts and table filter, vault detector classification source, D-5 batch-start gate, tool-blob-bound control hashes, and `ci.yml` PR-lane wiring. |
| **R1-m13** | Minor | **Adopted in revision 2, wording tightened in revision 3 (Header, §8.2, §15.2 item 5).** Deleted the stray `"Wait:"` text and labeled §15.2 item 5 as a WP9.5-specific stop rule added by this note rather than citing `06v:629`; rewrote the Header `Verification scope` row in revision 3 (`R2-m4`) so it states accurately what was checked and what was not. |
| **R1-m14** | Minor | **Adopted in full (§11.2, §12.3, §16 G, Appendix A §21.1 & §21.2).** Measured the `--bare --local --no-hardlinks` clone on this machine, specified T7-2 using a throwaway index file (`GIT_INDEX_FILE` with `git read-tree`, `git update-index --add --cacheinfo`, `git write-tree`, `git commit-tree`), and included `@pytest.mark.slow` tests in the §12.3 and Owner Point G budget (keeping G1 `300s` until the pre-code single-store profile `UNVERIFIED-3` is run under `R2-m13`). |
| **R1-i1** | Info | **Recorded (§6.5 Rule 2).** Stated explicitly that hard-coding the `"results/ars/"` prefix exemption in Rule 2 is a deliberate, safe reading of `W9-D14` so `results/ars/` is exempt even before its registration batch lands. |
| **R1-i2** | Info | **Recorded (§6.3 item 2, §12.1).** Stated explicitly that mode-only changes (`old_blob == new_blob`, `old_mode != new_mode`) on a registered legacy file cannot satisfy `old_blob != new_blob` in `legacy-write-records.json` and fail closed. |
| **R1-i3** | Info | **Recorded (§4.1, §4.2.1, §4.2.2, §4.2.3, §13.2 HR-5, Appendix A §21.1).** Populated the owner-`gh` rows in §4.2.2 with the live 2026-11-21 observations, and noted the wider scope of D-8's known limit when queue merges are recorded as `bypass`. |
| **R1-i4** | Info | **Recorded (§7.4 item 1).** Cited `.gitattributes:14` (`* text=auto eol=lf`), confirming Windows runner checkouts produce LF for `CONVENTIONS.md`. |
| **R1-i5** | Info | **Retained (§6.3 item 2).** Kept the 2-parent merge commit `diff-tree -r --no-renames -z <P1> <C>` handling. |
| **R1-i6** | Info | **Retained (§6.4, §6.6).** Kept the rule that an absent `legacy-write-records.json` before L-1 is an error only when a guarded write occurs in `<baseline>..<head>`. |
| **Review §2** | Citation audit | **Partially adopted in revision 2 (~170 of ~175 distinct citations resolved); 6 residual wrong citations/symbols caught in `wp9-5-note-r2-review-2026-11-21.md` §2 (`R2-m2`, `R2-m4`, `R2-M5`) corrected in revision 3 (§19).** Corrected `06v-w9-implementation-plan.md` line references (`U-3` `:159`, `U-4` `:160`, `O-9..O-13` `:189-193`, `W9-T7` `:230`, `W9-T19` `:242`, `D-4` `:566`, `D-7` `:569`, squash merges `:90-91`, stop rules `:610-620`), `03-decisions-and-open-questions.md` references (`P-064` item 8 `:4232-4233`, `P-087` item 7 `:5919-5923`, `P-089` `:6071-6146`), and code/workflow references (`evidence.py:52-54,92-105,221-252`, `preparers.py:676,686-690,1200,1215-1218`, `replay/reducers.py:70,571`, `check_workflow_liveness.py:78-92`, `check_bypass_merges.py:106-110`, `check_merge_admission.py:700-737`, `wp9-4-design-note.md:703,1419`, and `.github/workflows/*.yml`). |

---

## 19. Change log: revision 2 to revision 3

Every finding in `docs/plans/agentic-research-system/reviews/wp9-5-note-r2-review-2026-11-21.md` (`3cf35bec`) is disposed of below:

| Finding ID | Severity | What changed in revision 3 and where |
|---|---|---|
| **R2-M1** | Major | **Adopted in full (§6.1, §6.2.2, §6.3, §6.5 Rule 0, §10.2, §13.1 MC-2, §14 Claim 2, §16 I).** Added explicit trust-root statement in §6.1 (no in-repo check can block a merged commit from disabling future CI runs; `.github/CODEOWNERS` under Owner Point I1 is the preventive control). Fixed `.github/workflows/legacy-write-detector.yml` (§10.2) to resolve `MAIN_TIP`, attach a detached worktree at `baselines[-1]["tool_pin_commit"]` (`$RUNNER_TEMP/w9-detector`), sync its `.venv`, and execute all detector/control commands from `$DETECTOR_DIR` with `PYTHONPATH="$DETECTOR_DIR"` (deleted the vacuous "when `walk-baseline.json` is present at `<baseline>`" clause). Distinguished `baselines[0]["baseline_commit"]` (walk start) from `baselines[-1]["tool_pin_commit"]` (pinned tree), hash-bound all decision references (`{"id": "P-0xx", "entry_sha256": ...}`, including `d8_rule_suites_limit_decision_ref`), placed all top-level `walk-baseline.json` fields under Rule 0.2 (§6.5), removed `workflow_dispatch` `inputs:`, locked `--baseline` and `--head` alongside `--pr-map` and `--manifest-file` behind `--ruleset-check skip` with workflow-argument test coverage (§6.3, §12.1), and qualified MC-2 and Claim 2 accurately. |
| **R2-M2** | Major | **Adopted in full (§6.2.2, §6.5 Rule 0.2, §12.1, §14 Claim 2, §16 C).** Added append-only `acknowledged` violations (`{commit, rule, path, old_blob, new_blob, disposition_ref}` with `commit < source_commit <= P1(C_ack)` and slice match) so honest true positives can be cleared without weakening rules, and append-only `checkpoints` (`{last_verified_commit, tool_pin_commit, verdict_digest, recorded_at}`) plus `--full-rewalk` verdict-diff mode so tool upgrades do not silently re-judge history (`walk-baseline.json` governed by Rule 0.2). |
| **R2-M3** | Major | **Adopted in full (§2.3, §6.2.3, §6.5 Rule 0.3, §10.2, §12.1, §14 Claim 2, §15.2 item 5, §16 I, §21.1).** Computed transitive AST import closure over `research_system` and `tools` from the 7 existing seeds (`15` existing modules at `dbd54fe3`, `20` runtime modules with the 5 new runtime detector/control/helper files, `22` total entries including exporter and workflow in `detector_closure_blobs`). Recorded `detector_closure_blobs` in `baselines[-1]`, verified blobs in `.github/workflows/legacy-write-detector.yml` before execution, covered it under Rule 0.3, and added unit test `test_recorded_detector_import_closure_covers_ast_walk` (also stop rule §15.2 item 5). |
| **R2-M4** | Major | **Adopted in full (§2.3, §6.5 Rule 0.2, §7.3, §7.6 Control N7, §12.1, §16 J).** Pinned post-L-0b `CONVENTIONS.md` classification via empty constant `ACCEPTED_CONVENTIONS_CLASSIFICATION` in `research_system/legacy/accepted_w9.py` (preserving D-4 / `IMPORTER_MODULES`), defaulting to the conservative 9-section (`68`-unit) partition until L-0b commits `"w9-conventions-classified-locks/1"` keyed by `(anchor_text, unit_hash)` (`segmentation.py:391-402`). Checker reads the pinned blob at that commit rather than `<head>`, `--classified-locks` is locked behind `--candidate-file` for tests only, and Rule 0.2 + Control N7 reject silent or head-side reclassification. |
| **R2-M5** | Major | **Adopted in full (§2.3, §10.3, §13.2 HR-1, §16 I).** Rewrote §16 I with exact CODEOWNERS entries (8 files plus `/.research-system/evidence/w9/` directory pattern), exact edits to `tests/tools/test_ci_platform_policy.py` (`W9_DETECTOR_CODEOWNED_FILES`, `W9_DETECTOR_CODEOWNED_DIRS`, `test_every_gate_file_exists_and_has_a_code_owner` `:364-369`, `test_codeowners_names_no_file_outside_the_gate` `:372-374`), required `CONVENTIONS.md:713-729` policy amendment (`P-090`), and bypass-merge cost (`admin-bypass-guard.sh:13-18`). Stated clearly why Option I2 leaves Option B1 ungrounded and fails to preventively guard Option F1's `L1_LIVE` tripwire; added optional out-of-tree `W9_DETECTOR_PIN` anchor as Option I3 (§10.2, §16 I). |
| **R2-m1** | Minor | **Adopted in full (§6.2.1, §14 Claim 8, §16 C, §21.1).** Added missing PRs `#419` (`14a81b84`) and `#425` (`1fba78aa`) to §6.2.1, updating counts from `20` -> `22` guarded first-parent commits and `8` -> `9` `CONVENTIONS.md`-only PRs across §6.2.1, §16 C, and §18; removed `verify_r2.py` reference and provided the reproducible walk command in §21.1. |
| **R2-m2** | Minor | **Adopted in full (§2.2).** Replaced `research_system/legacy/contracts.py` and `"five"` with `research_system/legacy/commands.py:16-31` (`12` members of `LEGACY_COMMAND_TYPES`) and cited `research_system/legacy/routes.py:446-458` for `LEGACY_ROUTED_ROWS` (`49`) and `LEGACY_DEFERRED_ROWS` (`12`). |
| **R2-m3** | Minor | **Adopted in full (§4.3.3, §7.3, §7.4 item 5, §8.2, §8.3, §12.1, §16 J).** Replaced `byte_start`/`byte_end`/`line_start`/`line_end` with exact `segment()` row keys (`start_byte`, `byte_length`, `start_line`, `line_count`, `unit_ordinal`, `unit_hash`, `row_ordinal`, `blocker_reason`) per `research_system/legacy/segmentation.py:391-425`; changed `w9-cl-classified-list/1` entry ordinals to **1-based** (`1..N` matching `row["row_ordinal"]` per `evidence.py:347-358`, `segmentation.py:408`). |
| **R2-m4** | Minor | **Adopted in full (Header, §2.2, §2.3, §6.5, §16 I, §18, §21.1).** Corrected `03-decisions-and-open-questions.md` citations (`:6022-6025,6086-6087` instead of `:6064-6066`), `W9-D14` (`09-migration-compatibility-and-pilot.md:768` instead of `:754`), and `CONVENTIONS.md:713-729` (instead of `:721-723`). Replaced header/§18 "verified everything" wording with an explicit summary of what was verified, how, and what remains unverified. |
| **R2-m5** | Minor | **Adopted in full (§10.2, §10.3).** Switched `.venv\Scripts\python.exe` to forward-slash `.venv/Scripts/python.exe` inside bash steps, replaced `rev-list | grep -q` under `set -o pipefail` with Python first-parent checks, wired `--ruleset-check ci-d8` and `run_w9_detector_controls.py --verify-watched-to-fail` (reading `detector-controls.json` from `MAIN_TIP`), and added `branches: [main]` filter to L-1 `on: push:`. |
| **R2-m6** | Minor | **Adopted in full (§4.2.2, §15.1 item 1, §21.2).** Required U-3 probe JSON output to log presence of pinned response keys (`bypass_actors`, `rules[].parameters`, `conditions`, `integration_id`) per endpoint alongside HTTP status and `X-Accepted-GitHub-Permissions`, and stated that opening the throwaway probe PR triggers `merge-admission`, `ci`, and other `pull_request` workflows. |
| **R2-m7** | Minor | **Adopted in full (§4.3.3, §15.1 item 2, §21.2).** Replaced the multi-line PowerShell `python -c` dry-run snippet with instructions to write and run standalone scratch script `u4_dry_run.py` from the worktree root with `PYTHONPATH=.`, preserving the summary/blocker output fields without reading or printing entry prose. |
| **R2-m8** | Minor | **Adopted in full (§9.2, §12.1).** Added `GIT_CONFIG_GLOBAL` (pointing to an empty temp file) and `-c core.autocrlf=false -c commit.gpgsign=false` to `CONTROL_GIT_ENV`, included the `closure_blobs` map in control transcripts *(note: revision 3 prose said "closure digest", corrected to "`closure_blobs` map" in revision 4 under `R3-m7 (d)`)*, and dropped the unverified cross-machine bit-identity claim. |
| **R2-m9** | Minor | **Adopted in full (§4.1, §12.1, §14 Claim 10).** Pinned `integration_id: 15368` per required status check from live `rulesets/20822054` read, defined `--acknowledge-gap <P-0xx>` for recovery after a >30-day `main_ruleset` interval, and stated the reviewed-PR + `ars store advance-binding` cost of each pre-batch read. |
| **R2-m10** | Minor | **Adopted in full (§6.4, §14 Claim 6, §16 B).** Specified exact §6.4 tuple-matching grammar in owner register entries (`### P-0xx` slice listing `normalized_path`, `old_blob[:8]`, `new_blob[:8]`, removing the undefined `"or ruling reference"` fallback), required independent reviews to explicitly bind the decision ID and tuples, stated Option B1 provenance is **conditional on Option I1** CODEOWNERS, and flagged `P1`-before-PR ordering as this note's stricter reading of W9 §4.2(b). |
| **R2-m11** | Minor | **Adopted in full (§2.3, §5.3, §6.5 Rule 3, §12.1, §16 A/D).** Documented Option D3 tree-state equivalence intent and revert-cycle limitation (`A -> B -> A` under `HR-2`), corrected test file names (`test_w9_evidence_acceptance.py` and `test_w9_wp9_3_2_runtime.py`), unified Options A1 and D3 on `/2` format versions (`"w9-registration-manifest/2"`, `"w9-shared-surface-changes/2"`), and stated Option A1 needs a dated WP9.3 amendment, independent review, and register entry just like D3 and E1. |
| **R2-m12** | Minor | **Adopted in full (§8.2 Check 2, §8.5, §12.1).** Updated Check 2 to inspect `recheck_cl_export`'s returned report (`export_recheck.py:80-89`) and fail closed (`ERROR: ...`) whenever `report["void"] is True`, plus corresponding negative control in §8.5 and §12.1. |
| **R2-m13** | Minor | **Adopted in full (§12.1, §12.3, §15.1 item 4, §16 F/G, §21.2).** Specified the PR/CI lane (`tools/affected_research_tests.py` and `.github/workflows/research-system-suite.yml` `-m "not live_store"`) for `tests/research_system/integration/test_w9_wp9_5_detectors.py`, removed the unverified `20–35 s` timing estimate in favor of `UNVERIFIED-3` pre-code profiling (`P-087` item 7), and recommended Option G1 (`300s`) until measured. |
| **R2-m14** | Minor | **Adopted in full (§6.2.2, §16 C).** Changed `baselines[0]["baseline_commit"]` from the unknowable queue merge parent of L-1 to any known first-parent ancestor of L-1 on `main`, with all intermediate guarded commits up to L-1 disposed in §6.2.1 / `P-09x`. |
| **R2-m15** | Minor | **Adopted in full (§6.2.1, §6.5 Rule 1, §14 Claim 5, §16 H).** Corrected `#368` (`452352ff`) from "worktree sweep" to Phase 5 run record (`record L5, A6, A7 and step 3 batches 1-3 of the 06s Phase 5 run (P-058)`), and specified the `[ \t]*\n` blank separator line rule inside `## Working Notes` (`+1`-byte separator per appended entry matching `#368`, `#388`, `#433`). |
| **R2-m16** | Minor | **Adopted in full (§11.3, §12.1).** Restricted `.git` immutability snapshot in §11.3 to checkout-scoped `REPO_ROOT` files (`HEAD`, `refs/heads/main`, `config`, `hooks`, main worktree `index`, plus `--no-optional-locks status`) so sibling worktrees do not cause false flakiness. |
| **R2-i1** | Info | **Recorded (§6.3 item 3).** Adjusted wording from asserted GitHub behavior to precautionary retry/fallback if `commits/<C>/pulls` returns `[]`. |
| **R2-i2** | Info | **Adopted (§7.4, §13.2 HR-6).** Added **HR-6** covering `CONVENTIONS.md` structural exceptions (`---`, blank lines, footer, H1, `###` sub-headings) and moved bullets across legacy sub-headings. |
| **R2-i3** | Info | **Recorded (§4.1).** Documented the unpinned live ruleset parameters (`require_extra_approval_for_unattributed_changes: true`, `grouping_strategy: ALLGREEN`, `check_response_timeout_minutes: 20`, `dismiss_stale_reviews_on_push: false`). |
| **R2-i4** | Info | **Recorded (§8.2 Check 1).** Noted explicitly that rejecting `blocker` rows across successor entries too is an intentional strictness beyond `W9` §4.4 ("duplicated legacy heading anchors") to preserve whole-page segmentation integrity. |
| **R2-i5** | Info | **Recorded (§4.2.2, §14 Claim 10, §21.1).** Kept the dated pre-`#448` snapshot (`57`, `33 bypass`) alongside post-`#448` (`58`, `34 bypass`) and explained the sliding 30-day window observed on `2026-11-21T23:03Z` (`56`, `32 bypass` as `bb9d91d4` aged out). |
| **R2-i6** | Info | **Recorded (§12.3, §21.1).** Kept verified `git count-objects -vH` figures (`58,133` objects in pack, `28` packs, `335.09 MiB` pack size) and measured local bare-clone timings (`1.57–1.79s`, `1.65–1.86s` with two `diff-tree` runs). |

---

## 20. Change log: revision 3 to revision 4

Every finding in `docs/plans/agentic-research-system/reviews/wp9-5-note-r3-review-2026-11-21.md` (`1bd4ecff`) is disposed of below, with superseded commit-pinning (`tool_pin_commit`, `git worktree add/remove`) and `checkpoints` / `--record-checkpoint` / `--full-rewalk` text deleted from §1–§17:

| Finding ID | Severity | What changed in revision 4 and where |
|---|---|---|
| **R3-M1** | Major | **Adopted Form (A) in full (Header, §1, §2.3, §6.1, §6.2.2, §6.2.3, §6.5 Rule 0, §10.2, §12.1, §13.1 MC-2, §14 Claim 2, §16 I & C, §21.1 item 9).** Replaced `tool_pin_commit` and the workflow's detached worktree with Form (A) content-pinning: `detector_closure_blobs` now pins the 25-entry closure including `pyproject.toml` and `uv.lock`; `.github/workflows/legacy-write-detector.yml` (§10.2) assembles `$RUNNER_TEMP/w9-detector` via `git cat-file blob`, runs `uv sync --locked --no-install-project`, and runs with `PYTHONPATH="$DETECTOR_DIR"` + `PYTHONSAFEPATH=1` (failing out-of-closure imports with `ModuleNotFoundError`). Stated the package ancestor `__init__.py` inclusion rule (`research_system/**/__init__.py` included explicitly; `tools/` namespace package, §6.2.3). Added all five Rule 0.2 validations on every appended `baselines[k]` row ($k \ge 1$): exact blob equality at `C`, pre-existing (`at P1`) hash-bound decision ref, `### P-0xx` slice naming every changed/added/removed path and `new_blob[:8]` (plus explicit `"no blob change"` or `"rollback"` naming), and recomputed dual-tool verdict diff (§6.5). Added the Form (A) positive control (same-PR closure edit + valid `baselines` append ends green) and negative controls (missing decision ref, slice omitting path/`new_blob[:8]`, unmentioned no-op/rollback row) in §12.1. Reworded `MC-2`, §6.2.3, and Claim 2 accurately: **preventive** for CODEOWNED paths and **detective** post-merge for the non-code-owned closure modules. Deleted `tool_pin_commit`, `PINNED_SHA`, and `worktree add/remove` from §1–§17. |
| **R3-M2** | Major | **Adopted in full (§1, §2.1, §6.2.2, §6.5 Rule 0.2, §12.1, §12.3, §14 Claim 2, §16 C, §21.1 item 10).** Deleted `checkpoints`, `--record-checkpoint`, `--full-rewalk`, `verdict_digest`, `last_verified_commit`, and `w9-full-rewalk-diff` everywhere outside §18–§20; every CI and operator-machine run walks `(baselines[0]["baseline_commit"], head]` in full. For each `baselines[k]` ($k \ge 1$) appended at `C_k`, Rule 0.2 assembles both `baselines[k-1]` and `baselines[k]` tools, walks `(baselines[0]["baseline_commit"], P1(C_k)]` under both, and fails with `ERROR: post_merge_first_parent: Rule 0: pin advance changes verdicts at <commit_prefixes>` unless every commit whose verdict changed is named (`V[:8]`) in `recorded_in_decision_ref`'s slice (nothing stored is trusted). Added the pin-advance verdict-flip negative control in §12.1, and measured + recorded the full 320-commit stand-in walk timing (`23.11s` over `4b143c92..dbd54fe3`, §6.2.2, §12.3, §21.1 item 10). |
| **R3-M3** | Major | **Adopted in full (§1, §6.2.2 item 3.4, §6.5 Rule 0.2 & Rule 3, §12.1, §13.1 MC-5, §14 Claim 2, §16 C & D).** Required any `acknowledged` row with `rule == "Rule 3"` to have a matching `(pr_number(commit), path, old_blob, new_blob, affected_registrations)` entry present in `<head>:.research-system/evidence/w9/shared-surface-changes.json` (otherwise exit `1`). Explained why a late entry is safe: WP9.3's `check_change_list` (`research_system/legacy/acceptance.py:121-136`) reads `shared-surface-changes.json` at the control store's `git_head`, and appending the late entry is valid under Rule 0.2. Added matching negative and positive controls in §12.1. |
| **R3-m1** | Minor | **Adopted in full (Header, §10.2, §15.1 item 3, §16 I, §21.2 `UNVERIFIED-4`).** Updated Option I3 (`vars.W9_DETECTOR_PIN`) to pin `{"walk_baseline_commit": ..., "closure_blobs_sha256": ...}` (canonical SHA-256 of `detector_closure_blobs`, not a commit); added `REQUIRE_I3_PIN` env guard in §10.2 so an empty variable fails closed once Option I3 is chosen (`ERROR: W9_DETECTOR_PIN is required under Option I3 but is empty`); removed the uncited "admin-only" claim and recorded GitHub repository variable write permissions as **`UNVERIFIED-4`** (§21.2, §15.1 item 3). |
| **R3-m2** | Minor | **Adopted in full (§1, §2.1, §2.3, §6.2.3, §7.5, §8.4, §9.2, §10.2, §12.1, §16 I & J).** Added operator-machine Form (A) wrapper **`tools/run_w9_pinned_detectors.py`** so pre-batch and weekly D-5 runs (`06v:603-604`) assemble and run detectors from the same blob-pinned tree rather than the mutable working checkout; added `/research_system/legacy/accepted_w9.py` (governed under `tests/research_system/integration/test_w9_wp9_3_binding_head.py:199-217`) and `/tools/run_w9_pinned_detectors.py` to Owner Point I1 CODEOWNERS (now 10 file patterns + 1 dir); covered `run_w9_pinned_detectors.py` in `O-13` (§12.1). |
| **R3-m3** | Minor | **Adopted in full (§6.2.3, §13.2 HR-3, §16 I).** Stated the operational cost of the closure rule (`7` W9 PRs in the last 4 weeks and `14` of `178` first-parent commits in 90 days touched the 15 existing closure modules, each needing a `P1` hash-bound decision ref, same-PR `baselines` append, re-recorded `detector-controls.json`, and `Bypass reason:` merge); added **`Option I1-narrow`** (moving small detector-only reader helpers into `tools/`) alongside **`Option I1-default`** in §6.2.3 and §16 I. |
| **R3-m4** | Minor | **Adopted in full (§1, §2.1, §11.2, §12.1, §12.3, §13.1 MC-3 & MC-4, §14 Claim 8, §16 C & F).** Moved `W9-T7` scratch-clone replay into `tests/tools/test_w9_detectors.py` (running in `ci.yml` `admission-controls` on every PR); stated accurately that `tools/affected_research_tests.py:120-147` selects `tests/research_system/integration/test_w9_wp9_5_detectors.py` only when `research_system/` or `tests/research_system/` or `.research-system/` changes (**not** on `tools/`-only PRs, which run in advisory nightly `.github/workflows/research-system-suite.yml:8-9,15,17`), while weekly `.research-system/evidence/w9/` PRs select all contract tests. |
| **R3-m5** | Minor | **Adopted in full (§1, §12.3, §15.1 item 4, §16 G, §21.2).** Made the single scratch-store integration test timing profile on Stephen's machine (`§15.1` item 4, `P-087` item 7, `UNVERIFIED-3`) **unconditional** before WP9.5 code dispatch. |
| **R3-m6** | Minor | **Adopted in full (§4.3.3, §14 Claim 11, §15.1 item 2, §21.2).** Added the three §4.3.2 root-resolution/disjointness checks (`exists_and_is_dir`, `not_symlink_or_junction`, `abspath_equals_resolved_normcase`, `disjoint_from_repo_root`) to `u4_dry_run.py` as `root_checks` printed booleans. |
| **R3-m7** | Minor | **Adopted in full (Header, §1, §9.2, §12.3, §13.1 MC-9, §14 Claim 15, §16 F, §19 R2-m8, §21.1).** Fixed all four items: `(a)` `.github/workflows/ci.yml:18` -> `.github/CODEOWNERS:18` (§16 F); `(b)` `wp9-5-note-r2-review-2026-11-21.md:162` -> `:218` for the bare-clone timing (§12.3, §21.1 item 6); `(c)` rewrote Header Verification scope and §21.1 intro so R2 (`0c9a90ed`) is credited only for checks present in R2 (walk, counts, ruleset, bare-clone timing) while R3 (`092db1f1`) is credited for reproducing the 22 rows, 15/20/22 AST closure & 13 blobs, counts, 16/16 live pins, YAML/`bash -n`, and synthetic U-4; `(d)` replaced `"closure digest"` with `"closure_blobs" map` (§1, §9.2, §13.1 MC-9, §14 Claim 15, §19 R2-m8). |
| **R3-m8** | Minor | **Adopted in full (§1, §11.3).** Removed shared `refs/heads/` and `refs/tags/` under `--git-common-dir` from the §11.3 `REPO_ROOT` immutability snapshot; replaced with comparing the checked-out branch's ref (`symbolic-ref --quiet HEAD` + `rev-parse`) and `git for-each-ref refs/tags` output alongside checkout-local `HEAD`, `config`, `index`, and `git --no-optional-locks status`. |
| **R3-m9** | Minor | **Adopted in full (§2.3, §4.2.2, §6.2.3, §8.4, §13.2 HR-3, §16 I).** Completed the Option I1 edit list and cost: `(a)` added `.github/CODEOWNERS:1-12` scope header; `(b)` required all 9 new files to land in the **same PR** as `.github/CODEOWNERS` (matching `.is_file()` in `test_every_gate_file_exists_and_has_a_code_owner:364-369`) and prohibited `.is_dir()` on `/.research-system/evidence/w9/` (`.research-system/evidence/` has no tracked file at `dbd54fe3`); `(c)` added the mandatory `Bypass reason:` PR-body line (`tools/check_bypass_merges.py:41,135`) to the stated bypass-merge cost; `(d)` noted that `CONVENTIONS.md:713-729` lies inside successor section `## ARS Foundation Governance` (`614-783`), touching no legacy unit. |
| **R3-m10** | Minor | **Adopted in full (§6.2.2 item 2, §16 C).** Clarified that `(4b143c92, baselines[0]["baseline_commit"]]` is the **disposed** pre-baseline interval and `(baselines[0]["baseline_commit"], head]` is the **walked** interval, and specified the L-1 refresh rule: run §21.1 item 3 over `(dbd54fe3, baselines[0]["baseline_commit"]]` at L-1 and record every newly guarded commit in the L-1 decision entry / `pre_baseline_dispositions_ref`. |
| **R3-m11** | Minor | **Adopted in full (§4.1, §6.2.2, §6.5 Rule 0.2, §12.1, §14 Claim 10, §16 C).** Added closed schema `{"previous_recorded_at", "acknowledged_through", "disposition_ref"}` and Rule 0.2 pre-existing `P1` hash-bound slice validation for `ruleset_gap_acknowledgements`; added `--acknowledge-gap` positive control + invalid-gap Rule 0.2 negative control and explicit D-8 `d8_rule_suites_limit_decision_ref` negative/positive gate test in §12.1. |
| **R3-m12** | Minor | **Adopted in full (§10.2 item 5, §12.1, §15.1).** Added unit-test execution of the workflow's Form (A) Python pin-assembly heredoc in `tests/tools/test_w9_detectors.py` against a scratch repo with synthetic `walk-baseline.json` rows (valid; off-chain baseline; blob mismatch; I3 `closure_blobs_sha256` mismatch; empty `W9_DETECTOR_PIN` under `REQUIRE_I3_PIN=true`), plus a one-shot pre-L-1 throwaway `pull_request` workflow rehearsal matching U-3. |
| **R3-m13** | Minor | **Adopted in full (§2.3, §5.3, §14 Claim 3, §16 A).** Under Option A1, explicitly named all three WP9.4-era files (`tests/research_system/integration/w9_runtime_harness.py:451-466`, `test_w9_wp9_4_1_runtime.py:95-109`, `test_w9_wp9_4_2_runtime.py:86-100`) alongside `test_w9_evidence.py`, and stated explicitly that no WP9.4 production code changes so WP9.4's review is **not** reopened (whereas Option A2 avoids touching them). |
| **R3-i1** | Info | **Adopted in full (§1, §10.3, §13.1 MC-10, §14 Claim 16).** Specified `yaml.load(..., Loader=yaml.BaseLoader)` (`tests/tools/test_ars_currency_workflow_controls.py:19-22`) for loading `.github/workflows/legacy-write-detector.yml` in the `L1_LIVE` tripwire test so `"on"` stays string `"on"`. |
| **R3-i2** | Info | **Adopted via new Owner Point K (§1, §7.5, §15.1, §16 K).** Added Owner Point **K** putting the PR-lane `tools/check_conventions_legacy_locks.py` decision (`06v:491-492`) to Stephen: **Option K1 (Recommended)** adds a `< 0.15s` step to `ci.yml` `admission-controls` (preventive on PRs, zero ruleset change) vs **Option K2** (post-merge CI + operator pre-batch + unit tests only). |
| **R3-i3** | Info | **Recorded (§10.2 item 4).** Noted that `.github/workflows/ci.yml:255-279` (`watchdog-schedule-liveness`, lines `:263,276`) covers only `ars-artefact-currency-watchdog.yml` and `research-system-suite.yml`, with optional post-L-1 extension to `legacy-write-detector.yml`. |
| **R3-i4** | Info | **Recorded (§4.2.2, §21.1 item 8).** Recorded R3's live re-check of ruleset `20822054` (all 16 comparisons matched, 30-day rule-suites window `56` evaluations / `32` bypass newest `4ca375a3`). |

---

## 21. Appendix A: Verification

### 21.1 Reproducible verification commands and script outputs

All checks below are read-only against `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note` (at `dbd54fe382e7b2849d3f2038393cbdb4d709477b` or branch `HEAD`) and read-only GitHub REST API `GET` endpoints (`gh api`); no vault file prose was read, and `git status --short` was verified clean before editing. Earlier independent verification: `docs/plans/agentic-research-system/reviews/wp9-5-note-r2-review-2026-11-21.md` §2 & §5 (against `0c9a90ed`) reproduced the first-parent walk facts, `CONVENTIONS.md` unit counts, ruleset pins, and bare-clone timings (`:218`; R2 did **not** reproduce item 5's AST closure, which did not exist in `0c9a90ed`); `docs/plans/agentic-research-system/reviews/wp9-5-note-r3-review-2026-11-21.md` §2, §6, and `R3-i4` (against `092db1f1`) independently reproduced all 22 first-parent rows, the 15 / 20 / 22 AST closure and all 13 recorded blobs, the `CONVENTIONS.md` counts, 16 of 16 live ruleset pins, both YAML parses + `bash -n`, and synthetic U-4 script execution (`R3-m7 (c)`).

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

**5. AST transitive import closure over existing `research_system` and `tools` modules (15 files at `dbd54fe3`, `R2-M3`):**

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

**8. Read-only GitHub REST ruleset & rule-suites `GET`s (`R1-m2`, `R1-i3`, `R2-m9`, `R2-i3`, `R2-i5`, `R3-i4`):**

```powershell
gh api repos/ZK-Theory/TDL/rulesets/20822054
gh api --paginate --slurp "repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=month&per_page=100"
```

`rulesets/20822054` returned HTTP 200 (`id: 20822054`, `name: "P-049 Gate 6 main merge admission"`, `enforcement: "active"`, `conditions.ref_name.include: ["refs/heads/main"]`, `pull_request` `required_approving_review_count: 0`, `require_code_owner_review: true`, `required_review_thread_resolution: true`, `allowed_merge_methods: ["squash"]`, `required_status_checks` `strict_required_status_checks_policy: true` with all 4 contexts carrying `integration_id: 15368`, `merge_queue` `SQUASH` 1-by-1 `ALLGREEN`, `non_fast_forward`, `bypass_actors: [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}]`). `rule-suites?time_period=month` is a sliding 30-day window (`57` entries / `33` bypass at revision 2's initial read; `58` / `34` bypass after `#448` `4ca375a3` merged; `56` entries / `32` bypass at `2026-11-21T23:03Z` once `bb9d91d4` aged past 30 days, and matched live again in R3 review `wp9-5-note-r3-review-2026-11-21.md:99`).

**9. Form (A) blob assembly (`pyproject.toml`, `uv.lock`, and the 15 existing closure modules) + `uv sync --locked --no-install-project --offline` + `PYTHONSAFEPATH=1` isolation test (`R3-M1`):**

```powershell
git -C "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note" rev-parse dbd54fe382e7b2849d3f2038393cbdb4d709477b:pyproject.toml dbd54fe382e7b2849d3f2038393cbdb4d709477b:uv.lock
@'
import os, pathlib, subprocess, tempfile, time
wt = pathlib.Path(r"C:\Users\steph\TDL\.apm\worktrees\wp9-5-note")
rev = "dbd54fe382e7b2849d3f2038393cbdb4d709477b"
paths = [
    "pyproject.toml", "uv.lock", "tools/w9_segmentation.py",
    "research_system/__init__.py", "research_system/canonical.py", "research_system/errors.py",
    "research_system/legacy/__init__.py", "research_system/legacy/accepted_w9.py",
    "research_system/legacy/evidence.py", "research_system/legacy/export_recheck.py",
    "research_system/legacy/reader.py", "research_system/legacy/segmentation.py",
    "research_system/store/__init__.py", "research_system/store/anchor.py",
    "research_system/store/durability.py", "research_system/store/lock.py",
    "research_system/store/writer.py",
]
with tempfile.TemporaryDirectory() as td:
    td_path = pathlib.Path(td)
    for rel in paths:
        dest = td_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(subprocess.check_output(["git", "-C", str(wt), "cat-file", "blob", f"{rev}:{rel}"]))
    t0 = time.perf_counter()
    subprocess.run(["uv", "sync", "--locked", "--no-install-project", "--offline"], cwd=td_path, check=True)
    dt = round(time.perf_counter() - t0, 2)
    py = td_path / ".venv/Scripts/python.exe"
    env = {**os.environ, "PYTHONPATH": str(td_path), "PYTHONSAFEPATH": "1"}
    r_ok = subprocess.run([str(py), "-c", "import research_system.legacy.evidence"], cwd=wt, env=env)
    r_bad = subprocess.run([str(py), "-c", "import research_system.cli"], cwd=wt, env=env, capture_output=True, text=True)
    print({"sync_seconds": dt, "in_closure_rc": r_ok.returncode, "out_of_closure_rc": r_bad.returncode})
'@ | & "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note\.venv\Scripts\python.exe" -
```

Confirmed `pyproject.toml` blob `09d9faa91faff9956bfdd90c849e1287a331e9b6` and `uv.lock` blob `87a3862cad49411c8c0164b95bb0bee47c9556a7`; `uv sync --locked --no-install-project --offline` exited `0` in `14.6s`; from `cwd=wt` with `PYTHONPATH=<td_path>` and `PYTHONSAFEPATH=1`, in-closure import `research_system.legacy.evidence` exited `0` while out-of-closure import `research_system.cli` failed with `ModuleNotFoundError: No module named 'research_system.cli'` (`rc=1`).

**10. Full 320-commit first-parent walk stand-in timing (`4b143c92..dbd54fe3`, `R3-M2`):**

```powershell
@'
import subprocess, time
r = r"C:\Users\steph\TDL\.apm\worktrees\wp9-5-note"
commits = subprocess.check_output(["git", "-C", r, "--no-replace-objects", "rev-list", "--first-parent", "--reverse", "4b143c9225035cc29e37351445f1c3a4ab09ceb1..dbd54fe382e7b2849d3f2038393cbdb4d709477b"], text=True).splitlines()
t0 = time.perf_counter()
guarded = 0
for c in commits:
    p1 = subprocess.check_output(["git", "-C", r, "--no-replace-objects", "rev-parse", f"{c}^1"], text=True).strip()
    out = subprocess.check_output(["git", "-C", r, "--no-replace-objects", "diff-tree", "-r", "--no-renames", "-z", p1, c])
    paths = [tok.decode("utf-8", "replace") for i, tok in enumerate(out.split(b"\x00")) if i % 2 == 1]
    if any(p == "CONVENTIONS.md" or p.startswith(("results/", "papers/", "contracts/", ".apm/")) for p in paths):
        guarded += 1
print({"commits": len(commits), "guarded": guarded, "seconds": round(time.perf_counter() - t0, 2)})
'@ | & "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note\.venv\Scripts\python.exe" -
```

Walked all `320` first-parent commits (`22` guarded commits matched) in **`23.11s`** (`~0.07s`/commit).

### 21.2 Statements marked `UNVERIFIED` (pre-code gates for the reviewing session)

Every statement in this design note that cannot be verified without running a GitHub Actions workflow under `GITHUB_TOKEN`, reading the live vault `Computational-Log.md` bytes, running an isolated scratch-store test on Stephen's machine, or checking GitHub repository variable write permissions is listed here and gated in §15.1:

1. **`UNVERIFIED-1` (U-3 probe, §4.2.2, §15.1 item 1; `R2-m6`):** The HTTP status codes, `X-Accepted-GitHub-Permissions` headers, **and pinned JSON body key presence** returned to a GitHub Actions `GITHUB_TOKEN` (under `permissions: contents: read` and under `permissions: contents: read, pull-requests: read`) for:
   - `GET repos/ZK-Theory/TDL/rulesets/20822054`
   - `GET repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=day&per_page=5` (expected HTTP 403/404 per `tools/check_bypass_merges.py:20-21`, which decides D-8)
   - `GET repos/ZK-Theory/TDL/commits/dbd54fe382e7b2849d3f2038393cbdb4d709477b/pulls`
2. **`UNVERIFIED-2` (U-4 handle-bound reader and segmenter dry run on the live `833,453`-byte vault file, §4.3.3 item 2, §15.1 item 2; `R2-m3`, `R2-m7`, `R3-m6`):** The output of running standalone scratch script `u4_dry_run.py` (`root_checks` booleans from §4.3.2, `handle_bound_read(resolved_vault, "04-Methods/Computational-Log.md")`, and both `segment(raw, "computational_log_entry")` functions) on the current `833,453`-byte live file (`link_count == 1`, `file_facts`, `row_counts`, and `blockers == []`).
3. **`UNVERIFIED-3` (Unconditional pre-code single scratch-store test timing profile and operator-machine weekly D-5 run, §12.3, §15.1 item 4; `R2-m13`, `R3-m5`):** The wall-clock timing of a single existing WP9.3/WP9.4 scratch-store integration test run alone on Stephen's machine (`P-087` item 7, **unconditionally required before WP9.5 code dispatch**, §15.1 item 4), and end-to-end execution of the weekly operator-machine D-5 workflow against the live vault and control store via `tools/run_w9_pinned_detectors.py` after L-0b/L-1.
4. **`UNVERIFIED-4` (Option I3 `W9_DETECTOR_PIN` GitHub repository Actions variable write permissions, §10.2, §15.1 item 3, §16 I; `R3-m1`):** Which repository roles on `ZK-Theory/TDL` (`admin` vs `maintain`/`write`) can create, edit, or delete repository Actions variables (`vars.W9_DETECTOR_PIN`) was not verified against live repository settings or documentation permitted here; Stephen must confirm variable write permissions before relying on Option I3 as an out-of-tree trust anchor.
