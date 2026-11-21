# WP9.5 Design Note — W9 Detectors (W9-D5)

| Field | Value |
|---|---|
| Date | 2026-11-21 |
| Status | **Revision 2, for independent adversarial review. Nothing in it is implemented.** |
| Package | `06v` WP9.5 — "Detectors (W9-D5)" (`docs/plans/agentic-research-system/implementation/06v-w9-implementation-plan.md:470-503`) |
| Authority | Decision register entry `P-089` (`docs/plans/agentic-research-system/03-decisions-and-open-questions.md:6071-6146`) |
| Base | `origin/main` at `dbd54fe382e7b2849d3f2038393cbdb4d709477b` (`[PIPELINE] P06: WP9.4-2 follow-up: the independent review's Minor findings (P-088 item 5) (#446)`) |
| Worktree / Branch | `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note` on branch `docs/w9-wp9-5-design-note` |
| Prior review | Independent adversarial review of revision 1 (`65363e27`): `docs/plans/agentic-research-system/reviews/wp9-5-note-r1-review-2026-11-21.md` (`edb9acc6`; verdict `REWORK REQUIRED`: 1 Blocking, 12 Major, 14 Minor, 6 Info) |
| Not authorized | WP9.5 code, WP9.6, WP9.7, live operations L-0 to L-5 (including L-0b and L-1), creating or binding the real control store, registering or observing any real file, or any write to a legacy file, `main`, or the vault (`03-decisions-and-open-questions.md:6127-6135`) |
| Verification honesty | In revision 2, every named code symbol, file path, commit hash, date, unit count, and line number was verified directly against the worktree at base commit `dbd54fe382e7b2849d3f2038393cbdb4d709477b` or by running the read-only `git`, `gh api` GET, and Python segmentation/clone commands recorded in Appendix A (§19). The live U-4 metadata read run by the reviewing session on Stephen's authorization at `2026-11-21T21:06:44Z` is recorded in §4.3.3. What could not be run in this session—the CI `GITHUB_TOKEN` U-3 probe and the U-4 handle-bound reader/segmenter dry run against the live vault—are specified as explicit pre-code gates in §4.2.2, §4.3.3, §15.1, and Appendix A (§19.2). |

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
| 4. Post-merge first-parent detector (`tools/check_legacy_writes.py` & `.github/workflows/legacy-write-detector.yml`) | §6 | Time-indexed evidence (manifest read at `P1`; §4.2 and §4.3 records read at `C`); Rule 0 monotonicity over evidence and detector files; committed append-only `walk-baseline.json` verified on `<head>`'s first-parent chain; `git diff-tree -r --no-renames -z <P1> <C>` for 1-parent and 2-parent commits; retry/hint PR mapping with `merge_commit_sha == C`; Rules 1, 2, and 3; verified post-freeze first-parent commit inventory (`4b143c92..dbd54fe3`). |
| 5. Registration manifest export (M-6) | §5 | `tools/export_w9_registration_manifest.py` projects `state["records"]["legacy_path_registration"]` via `_legacy_projection` (`research_system/cli.py:1648-1659`) and `_legacy_current_binding` (`cli.py:1662-1684`) to `.research-system/evidence/w9/registration-manifest.json` before each batch's first observation; `--check` and integration test prove store-to-manifest equality at `binding.binding["git_head"]`. |
| 6. Shared-surface rule (O-32, detector half, Rule 3) | §6.5, §16 (Owner Points A, D) | Identifies `shared_enforcement_surface` contracts at `P1`, checks the W9 §4.3 owner note and `.research-system/evidence/w9/shared-surface-changes.json` at `C`, and sets out Options D3 (recommended blob-keyed freshness), D1, and D2 for resolving the squash-merge SHA contradiction between `06v:90-91,212,479-481` and `research_system/legacy/evidence.py:231-238` + `acceptance.py:135`. |
| 7. `CONVENTIONS.md` legacy-lock check (`tools/check_conventions_legacy_locks.py`) | §7, §16 (Owner Point J) | `segment(raw, "conventions_unit")` (`w9-segmentation/1.0.0`) against baseline commit `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (blob `4620c71607ca3a06c6df3b8e96a6bddffc783960`); provisional 9-section (`68`-unit) partition vs L-0b classified-list input; bullet/paragraph insertion-only check and structural-byte policy. |
| 8. Vault Computational-Log detector (`tools/check_legacy_log_baseline.py`) and D-5 cadence | §8, §16 (Owner Points E, J) | Compares live `04-Methods/Computational-Log.md` against accepted `w9-cl-export/1` baseline and `ACCEPTED_CL_EXPORT[-1]["classified_list"]` (`research_system/legacy/accepted_w9.py:86-88`); tested against a synthetic fixture export before L-0b; settles D-5 cadence gate placement (LR-003/LR-015 batch start as well as LR-016/LR-020), owner reset, weekly PR + `advance-binding` cost, and self-attestation limit. |
| 9. U-4 (operator machine vault path & read-only dry run) | §4.3, §15.1 | Records the live `2026-11-21T21:06:44Z` U-4 metadata read (`833,453` bytes, SHA-256 `73fcbe83...`); specifies the explicit detector-side junction refusal (`Path.is_symlink()`, `Path.is_junction()`, and `resolve(strict=True)` outside `repository_root`) and the pre-code reader+segmenter dry run. |
| 10. Detector-controls file (`.research-system/evidence/w9/detector-controls.json`) | §9 | Control runner binds each detector tool's Git blob and pinned Git author/committer dates into deterministic canonical transcripts, producing `w9-detector-controls/1`. |
| 11. Merging is not going live (`P-089` item 3) | §10, §16 (Owner Point F) | `.github/workflows/legacy-write-detector.yml` merges with `on: workflow_dispatch:` only, full-history checkout (`fetch-depth: 0`), and `origin/main` first-parent head guard; `L1_LIVE = False` tripwire constant in `tests/tools/test_w9_detectors.py` runs in a real PR lane under Option F1. |
| 12. Where the controls run (`P-089` item 4; `06v` O-13; W9-T7) | §11 | Scratch clones (`git clone --bare --local --no-hardlinks`, measured at 1.71–1.79s) and byte copies under `tmp_path`; W9-T7 replay of `5df0c001` and `811d5a2b` deriving touched paths via `git diff-tree`; recursive `--no-optional-locks` `(relpath, size, mtime_ns)` immutability snapshot of `REPO_ROOT`. |
| 13. Tests and test-time budget | §12, §16 (Owner Points F, G) | W9-T7 (`slow`, `integration`), W9-T19 (`unit`), M-6 equality, O-32 controls, Rule 0 monotonicity controls, measured bare-clone timing, and test-time budget (5-minute `P-087` item 7 baseline or 2-minute tightening, including `slow` tests). |
| 14. Research assurance | §13 | Machine-checkable claims with enforcement artifacts vs human-review-only claims (including post-merge detection limits, self-attested weekly vault cadence, and 30-day rule-suites window). |
| 15. Claims for review | §14 | 16 numbered load-bearing claims covering time-indexed evidence, Rule 0, Rule 1 exclusions, record keying, allowance kinds, PR mapping, control-run mechanics, and WP9.3 boundary. |
| 16. Stop rules for the code package | §15 | `06v` §8 (`06v:610-620`) stop rules plus WP9.5 preconditions (U-3 recorded, U-4 dry run recorded, Owner Points A–J decided in `P-090`) and WP9.5-specific stop rules. |
| 17. Owner points | §16 | Ten owner decisions (**A** through **J**), each with options, recommendation, and exact impact on accepted code or documents. |
| 18. Change logs and Verification appendix | §17, §18, §19 | Revision 1 log (§17), complete finding-by-finding revision 1 -> revision 2 disposition log (§18), and Verification appendix of commands run and `UNVERIFIED` pre-code items (§19). |

---

## 2. Scope, package boundary, and protected identities

### 2.1 Deliverables in WP9.5

Under `06v` §5 (`06v-w9-implementation-plan.md:470-503`) and `P-089` (`03-decisions-and-open-questions.md:6091-6118,6141-6143`), WP9.5 delivers:

1. **The registration manifest exporter and store-equality verifier (M-6, `06v:470-473`):**
   - `tools/export_w9_registration_manifest.py` (**new**): calls `_legacy_projection` (`research_system/cli.py:1648-1659`) and `_legacy_current_binding` (`research_system/cli.py:1662-1684`) read-only to export `.research-system/evidence/w9/registration-manifest.json` (`w9-registration-manifest/1`, `research_system/legacy/evidence.py:37,40,114-131`) and, in `--check` mode, verifies 1:1 set equality between the store's `state["records"]["legacy_path_registration"]` mapping (`research_system/legacy/replay/reducers.py:70,571`) and the committed manifest at `binding.binding["git_head"]` (`research_system/cli.py:1714`).
2. **The post-merge first-parent detector and workflow (`W9-D5`, `O-9`, `O-10`, `O-32`, `06v:189-190,212,474-490`):**
   - `tools/check_legacy_writes.py` (**new**): walks `git --no-replace-objects rev-list --first-parent --reverse <baseline>..<head>`, checks **Rule 0** (evidence and detector monotonicity), **Rule 1** (registered legacy files against the manifest at first parent `P1` and W9 §4.2 record at commit `C`), **Rule 2** (`results/` outside `results/ars/` against W9 §4.2 record at `C`), and **Rule 3** (`shared_enforcement_surface` contracts against the manifest at `P1` and `.research-system/evidence/w9/shared-surface-changes.json` + W9 §4.3 owner note at `C`), and checks ruleset `20822054` and `rulesets/rule-suites` in local pre-batch mode (and in CI if U-3 permits; otherwise under D-8 fallback).
   - `.github/workflows/legacy-write-detector.yml` (**new**): Windows-only (`runs-on: windows-latest`) workflow committed in WP9.5 with `on: workflow_dispatch:` only so merging WP9.5 does **not** activate automatic detection on `main` before L-1 (§10).
3. **The `CONVENTIONS.md` legacy-lock check (`W9-D5`, `O-12`, `06v:192,491-492`):**
   - `tools/check_conventions_legacy_locks.py` (**new**): verifies that `CONVENTIONS.md` preserves every legacy unit from baseline commit `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (blob `4620c71607ca3a06c6df3b8e96a6bddffc783960`, 33,645 bytes, SHA-256 `d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589`, pinned in `CONVENTIONS_LOCK`, `research_system/legacy/reader.py:43-49`) under `segment(data, "conventions_unit")` (`w9-segmentation/1.0.0`, `research_system/legacy/segmentation.py:429-488` and `tools/w9_segmentation.py:461-518`).
4. **The vault Computational-Log baseline detector (`W9-D5`, `O-11`, `D-5`, `D-7`, `06v:191,493-496,567,569`):**
   - `tools/check_legacy_log_baseline.py` (**new**): verifies that `--vault-root` is the real vault directory (never a symlink/junction or a path inside `repository_root`), reads `04-Methods/Computational-Log.md` via `handle_bound_read` (`research_system/legacy/reader.py:140-206`), segments the whole file via `segment(data, "computational_log_entry")` (`research_system/legacy/segmentation.py:429-488`), and compares every legacy-classified item and structural block against the accepted `w9-cl-export/1` baseline export (`research_system/legacy/evidence.py:277-362`) and its classified list (`ACCEPTED_CL_EXPORT`, `research_system/legacy/accepted_w9.py:86-88`).
5. **The detector negative-control runner (`O-13`, `06v:193,497-502`):**
   - `tools/run_w9_detector_controls.py` (**new**): executes the `recorded_read` control for `main_ruleset` and the `watched_to_fail` negative controls on scratch clones and byte copies for `post_merge_first_parent`, `vault_computational_log`, and `conventions_repository_check`, producing `.research-system/evidence/w9/detector-controls.json` (`w9-detector-controls/1`, `research_system/legacy/evidence.py:38,41,59-64,133-154`).
6. **Tests (`W9-T7`, `W9-T19`, `06v:230,242,503`):**
   - `tests/tools/test_w9_detectors.py` (**new**, `unit`, including W9-T19 and all per-detector positive and negative controls on byte copies and small synthetic Git repositories).
   - `tests/research_system/integration/test_w9_wp9_5_detectors.py` (**new**, `slow`, `integration`, including W9-T7 scratch-clone replay of `5df0c001` and `811d5a2b`, M-6 store-to-manifest equality, and O-13 end-to-end control generation).

### 2.2 What WP9.5 does NOT touch and why no D-4 is expected

Per `P-089` item 1 (`03-decisions-and-open-questions.md:6091-6099`), WP9.5 adds **no W9 command**. The five W9 commands in `LEGACY_COMMAND_TYPES` (`research_system/legacy/contracts.py`) and the route sets `LEGACY_ROUTED_ROWS` (`49` routed rows) and `LEGACY_DEFERRED_ROWS` (`12` deferred rows) from WP9.4-2 (`P-088`) are unchanged:

| Protected identity / surface | Current pinned value on `main` (`dbd54fe38`) | WP9.5 impact |
|---|---|---|
| Runtime-binding census (275 rows, enforced by `tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml` and `test_wp6_1_06h_append_path_closure.py`) | 275 rows; SHA-256 `82eab93a1b2ac81dd564581237f35e3dff19fee9e824ffff317d0f202b451d58` (`03-decisions-and-open-questions.md:6064,6086`) | **Unchanged.** WP9.5 adds no contract or command row. |
| 06h append-path manifest (`tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml`) | Blob `1066404a` (`03-decisions-and-open-questions.md:6065,6087`) | **Unchanged.** WP9.5 detectors are read-only observers and never append to any store ledger. |
| 06h append-path closure smoke test (`tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py`) | Blob `3b1eec6e` (`03-decisions-and-open-questions.md:6065,6087`) | **Unchanged.** |
| Schema registry & authority (`research_system/schema_registry.py`, `research_system/authority.py`) | Blobs `e32cb408` and `9b56b322` (`03-decisions-and-open-questions.md:6066`) | **Unchanged.** |
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
   - **All detector-only readers live in `tools/`** (inside the detector scripts or a shared helper `tools/_w9_detector_evidence.py`, **new**), NOT in `research_system/legacy/`:
     - `load_registration_manifest_at(repo_root, commit)` (**new**, in `tools/`): reads `<commit>:.research-system/evidence/w9/registration-manifest.json` via `git --no-replace-objects show` and returns the validated list of registration dicts (whereas `evidence.require_registered(manifest, registration)` in `research_system/legacy/evidence.py:114-131` checks membership of a single registration for `LR-015`).
     - `load_shared_surface_changes_at(repo_root, commit)` (**new**, in `tools/`): reads `<commit>:.research-system/evidence/w9/shared-surface-changes.json` and returns the validated entries list (whereas `evidence.require_change_list(repo_root, git_head, declared)` in `research_system/legacy/evidence.py:190-218` requires an acceptance record's `enforcement_change_list` `{git_commit, git_blob}` ref).
     - `load_legacy_write_records_at(repo_root, commit)` (**new**, in `tools/`): reads and validates `<commit>:.research-system/evidence/w9/legacy-write-records.json` (`w9-legacy-write-records/1`, Owner Point B).
     - `load_walk_baseline_at(repo_root, commit)` (**new**, in `tools/`): reads and validates `<commit>:.research-system/evidence/w9/walk-baseline.json` (`w9-walk-baseline/1`, §6.2, Owner Point C).
     - `read_real_vault_log(vault_root, repository_root)` (**new**, in `tools/check_legacy_log_baseline.py`): performs the root-level symlink/junction refusal (`vault_root.is_symlink() or vault_root.is_junction()`) and post-`resolve(strict=True)` containment check against `repository_root.resolve(strict=True)` before calling `handle_bound_read(vault_root, "04-Methods/Computational-Log.md")` (§4.3.2).
   - **What touches `research_system/legacy/` (only if Stephen selects the corresponding Owner Point in §16):**
     - **Owner Point A (Option A1, Recommended):** In `research_system/legacy/evidence.py:114-131` (`require_registered`), widen `_closed` at line 125 from `{"root_kind", "root_id", "normalized_path"}` to `{"root_kind", "root_id", "normalized_path", "role", "source_identity_kind"}` (or accept optional `"role"` and `"source_identity_kind"` for backward compatibility with existing 3-key WP9.3 test fixtures) **and** change line 129 from `if wanted not in [dict(entry) for entry in entries]:` to compare only the three identity keys `({k: entry[k] for k in ("root_kind", "root_id", "normalized_path")})` so `LR-015` continues to match registrations when the manifest carries 5 keys.
     - **Owner Point D (Option D3 Recommended, or D1):** Modifies `research_system/legacy/evidence.py:221-252` (`_change_entries`) and `research_system/legacy/acceptance.py:121-136` (`check_change_list`). Because `check_change_list` is an accepted WP9.3 gate at `LR-016`/`LR-020` (not merely a WP9.5 detector reader), selecting Option D3 or D1 requires a **dated WP9.3 amendment, an independent review of that change, and a decision-register entry** (§6.5, §16 D).
     - **Owner Point E (Option E1 Recommended):** Adds `VAULT_DETECTOR_RUNS` and `require_vault_detector_cadence` in `research_system/legacy/evidence.py` and calls it from `prepare_proposal` (`LR-003` and `LR-016`, `research_system/legacy/preparers.py:686-690,702-706`), `prepare_observation` (`LR-015`, `preparers.py:1215-1218`), and `check_environment` (`LR-016` and `LR-020`, `research_system/legacy/acceptance.py:147-152`). Because hooking `preparers.py` and `acceptance.py` modifies accepted WP9.3 preparer gates, Option E1 also requires a **dated WP9.3 amendment and independent review** (§8.4, §16 E).

2. **`.github/CODEOWNERS` and `GATE_FILES` boundary (`.github/CODEOWNERS:14-24`; `tests/tools/test_ci_platform_policy.py:341-350,372-374`):**
   - `.github/CODEOWNERS` lists **exactly eight paths**, all owned by `@stephendor` (verified directly from `.github/CODEOWNERS:14-24` and `GATE_FILES` in `tests/tools/test_ci_platform_policy.py:341-350`, where `test_codeowners_names_no_file_outside_the_gate` at `:372-374` asserts exact set equality):
     1. `/.github/CODEOWNERS`
     2. `/.github/merge-admission.yml`
     3. `/.github/workflows/merge-admission.yml`
     4. `/.github/workflows/merge-admission-sweep.yml`
     5. `/.github/workflows/ci.yml`
     6. `/tools/check_merge_admission.py`
     7. `/.claude/hooks/admin-bypass-guard.sh`
     8. `/.claude/settings.json`
   - Note that `tests/tools/test_ci_platform_policy.py` and `tools/check_test_commit_literals.py` are **not** in `.github/CODEOWNERS` or `GATE_FILES`.
   - Under `tests/tools/test_ci_platform_policy.py:286-303` (`test_every_tools_and_contracts_test_runs_in_a_workflow`), every `tests/tools/test_*.py` module must appear in a workflow step's `run:` script (or `CONTROL_EXEMPTIONS`). To actually run on every pull request and merge-group evaluation (rather than merely satisfying string presence in a `workflow_dispatch`-only workflow that never runs on PRs), `tests/tools/test_w9_detectors.py` must be added to `.github/workflows/ci.yml`'s `admission-controls` job (`ci.yml:166-216`) and `ADMISSION_CONTROL_MODULES` (`test_ci_platform_policy.py:175-229`), following the exact precedent of `tests/tools/test_w9_segmentation.py` (`ci.yml:210`; `test_ci_platform_policy.py:226`).
   - Because `.github/workflows/ci.yml` is owned by `@stephendor` in `.github/CODEOWNERS:18` and `.claude/hooks/admin-bypass-guard.sh:13-18,67-68` forbids any agent session from bypassing merge rules, **Stephen performs the merge of any PR that edits `.github/workflows/ci.yml` (or `.github/CODEOWNERS`) himself** (Owner Points F and I, §16).

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
- **What it reads (verified live on 2026-11-21 via read-only `gh api` GET; Appendix A §19.1):**
  1. **Ruleset configuration endpoint:**
     `gh api repos/ZK-Theory/TDL/rulesets/20822054` (HTTP `GET`, permitted by `.claude/hooks/admin-bypass-guard.sh:18,96-106`).
     The reader verifies the exact invariants observed on the live ruleset (`01-current-system-evidence.md:409`; Appendix A §19.1):
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
         - `parameters.required_status_checks` contexts include `{"contract-and-session-currency", "require-active-currency-workflow", "merge-admission", "admission-controls"}`;
       - `type == "non_fast_forward"`.
  2. **Rule-suites evaluation history endpoint:**
     `gh api --paginate --slurp "repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=month&per_page=100"` (HTTP `GET`, matching `tools/check_bypass_merges.py:141-166`).
     - **30-day API window limit and fail-closed freshness requirement (`tools/check_bypass_merges.py:24,57-58,73-90`):**
       GitHub's `rulesets/rule-suites` endpoint accepts `time_period` values `"hour"`, `"day"`, `"week"`, and `"month"` (`MAX_DAYS = 30`, `tools/check_bypass_merges.py:57-58`). A gap longer than 30 days between recorded reads would make bypass evaluations older than 30 days invisible to the API.
       Therefore, if a prior `"main_ruleset"` entry exists in `.research-system/evidence/w9/detector-controls.json` (or in the ruleset-read log) and `now - previous_recorded_at > timedelta(days=30)`, the ruleset reader **fails closed** (exit `1`) with:
       `ERROR: main_ruleset: previous recorded read is older than 30 days (<previous_recorded_at>); rule-suites API window (MAX_DAYS=30) cannot cover the gap without an owner reset`
     - **How `result == "bypass"` entries are evaluated:**
       On 2026-11-21, the live `time_period=month` query returned 57 evaluations on `refs/heads/main`: 33 `"bypass"` and 24 `"pass"`, with newest `after_sha == "dbd54fe382e7b2849d3f2038393cbdb4d709477b"` (`result: "bypass"`, `actor_name: "stephendor"`, `pushed_at: "2026-11-21T20:20:44+00:00"`). Merges performed by the repository owner (including merges touching `CODEOWNERS` or admin merges) are routinely recorded by GitHub as `result: "bypass"`.
       Accordingly, `result == "bypass"` is **not** by itself a failure. Instead, for every evaluation entry in the window on `refs/heads/main`:
       1. If `after_sha` is an ancestor of `<head>` after `<baseline>`, `tools/check_legacy_writes.py` verifies that `after_sha` satisfies Rules 0, 1, 2, and 3 (so any bypass commit that touched a guarded W9 path without a valid in-commit W9 §4.2 / §4.3 record fails closed).
       2. Every `result == "bypass"` entry in the window is recorded in the `"w9-main-ruleset-read/1"` report with `{after_sha, pushed_at, actor_name, touched_guarded_paths}`.
- **With which token:**
  - On the operator machine (at L-1 and before every batch on the `06v:603` batch checklist), it uses Stephen's authenticated `gh` CLI token.
  - In CI (`.github/workflows/legacy-write-detector.yml`), token capability is governed by U-3 and D-8 (§4.2).
- **How the read is recorded and when:**
  - **When:** At L-1 (before the first path registration `LR-003`, which checks `require_detector_controls` in `prepare_proposal`, `research_system/legacy/preparers.py:686-690`) and before every batch (`06v:603`).
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
      "required_status_check_contexts": [
        "admission-controls",
        "contract-and-session-currency",
        "merge-admission",
        "require-active-currency-workflow"
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
    - any pinned ruleset invariant above has drifted (`ERROR: main_ruleset: ruleset 20822054 configuration drift: <detail>`);
    - the previous recorded read is older than 30 days (`ERROR: main_ruleset: previous recorded read is older than 30 days`); or
    - `rulesets/rule-suites` contains any bypass commit that violated Rules 0–3 (`ERROR: main_ruleset: bypass evaluation on refs/heads/main touched guarded path without §4.2 record: <after_sha>`).
- **Negative control and test:**
  - Control kind: `recorded_read` (`research_system/legacy/evidence.py:60`; `W9:195`).
  - Unit tests in `tests/tools/test_w9_detectors.py` pass synthetic ruleset and rule-suite payloads to the validator and assert that: (a) `enforcement: "disabled"`, (b) `allowed_merge_methods: ["merge", "squash"]`, (c) `max_entries_to_merge: 2`, (d) missing `require_code_owner_review` or missing required status check context, (e) an added bypass actor, (f) a >30-day gap since the previous read, and (g) a `result: "bypass"` evaluation on an unrecorded guarded write each exit `1` with the exact `ERROR: main_ruleset:` message.

---

### 4.2 U-3: CI token (`GITHUB_TOKEN`) ruleset, rule-suites, and PR-lookup probe, plus D-8 fallback

#### 4.2.1 Current repository evidence on U-3

1. **Owner's `gh` login (verified live on 2026-11-21 in both `wp9-5-note-r1-review-2026-11-21.md:198` and Appendix A §19.1):**
   - `gh api repos/ZK-Theory/TDL/rulesets/20822054` returns HTTP 200 with all ruleset invariants in §4.1.
   - `gh api --paginate --slurp "repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=month&per_page=100"` returns HTTP 200 with 57 entries (33 `bypass`, 24 `pass`; newest `after_sha` `dbd54fe382e7b2849d3f2038393cbdb4d709477b`).
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
- **How the U-3 probe runs without touching `main`:**
  On Stephen's authorization, the reviewing session pushes a throwaway branch `probe/w9-u3-token-read` and opens a **draft, never-merged pull request** containing a temporary workflow `.github/workflows/u3-probe-temp.yml` triggered by `on: pull_request:`. GitHub Actions executes `on: pull_request:` workflows from the PR head commit immediately using a standard `GITHUB_TOKEN` scoped to the workflow's declared `permissions:` block, without modifying `main`. As soon as the run finishes and its HTTP status codes and `X-Accepted-GitHub-Permissions` headers are recorded in the table below, the reviewing session closes the draft PR and deletes the remote branch `probe/w9-u3-token-read`.
- **What the probe tests (two jobs, four read-only GET calls total):**
  - **Job 1 (`probe-contents-only`, `permissions: contents: read`):**
    1. `gh api -i repos/ZK-Theory/TDL/rulesets/20822054`
    2. `gh api -i "repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=day&per_page=5"`
    3. `gh api -i repos/ZK-Theory/TDL/commits/dbd54fe382e7b2849d3f2038393cbdb4d709477b/pulls`
  - **Job 2 (`probe-with-pull-requests-read`, `permissions: contents: read, pull-requests: read`):**
    4. `gh api -i repos/ZK-Theory/TDL/commits/dbd54fe382e7b2849d3f2038393cbdb4d709477b/pulls`
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
            for ep in \
              "repos/ZK-Theory/TDL/rulesets/20822054" \
              "repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=day&per_page=5" \
              "repos/ZK-Theory/TDL/commits/dbd54fe382e7b2849d3f2038393cbdb4d709477b/pulls"; do
              out="$(gh api -i "$ep" 2>&1)"
              rc=$?
              status="$(printf '%s\n' "$out" | head -n 1 | tr -d '\r')"
              perms="$(printf '%s\n' "$out" | grep -i '^X-Accepted-GitHub-Permissions:' | tr -d '\r')"
              echo "endpoint=$ep rc=$rc status=$status perms=$perms"
              printf -- '- `contents: read` | `%s` | exit `%d` | `%s` | `%s`\n' "$ep" "$rc" "$status" "$perms" >> "$GITHUB_STEP_SUMMARY"
            done
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
            echo "endpoint=$ep rc=$rc status=$status perms=$perms"
            printf -- '- `pull-requests: read` | `%s` | exit `%d` | `%s` | `%s`\n' "$ep" "$rc" "$status" "$perms" >> "$GITHUB_STEP_SUMMARY"
            exit 0
  ```
- **Which call decides D-8 (`06v:159,571`; `P-064` item 8, `03-decisions-and-open-questions.md:4232-4233`):**
  Call 2 (`GET repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=day&per_page=5`) decides D-8. If Call 2 returns HTTP 403 or 404 under `GITHUB_TOKEN`, D-8 applies to `rule-suites`. If Call 1 (`rulesets/20822054`) returns HTTP 200 under `GITHUB_TOKEN` even when Call 2 fails, the CI workflow still runs the `rulesets/20822054` configuration check on every run and defers only `rulesets/rule-suites` under D-8!

| Endpoint | Token & Permissions | Observed HTTP status & details | Result | Recorded by / Date |
|---|---|---|---|---|
| `GET repos/ZK-Theory/TDL/rulesets/20822054` | Owner `gh` login (local) | **HTTP 200**: `id: 20822054`, `name: "P-049 Gate 6 main merge admission"`, `enforcement: "active"`, `target_include: ["refs/heads/main"]`, `allowed_merge_methods: ["squash"]`, `merge_queue: {merge_method: "SQUASH", max_entries_to_merge: 1}`, 4 required status checks, `bypass_actors: [{actor_id: 5, actor_type: "RepositoryRole", bypass_mode: "pull_request"}]` | **PASS** (verified live) | Reviewing session (`wp9-5-note-r1-review-2026-11-21.md:198`) and authoring session (Appendix A §19.1), 2026-11-21 |
| `GET repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=month&per_page=100` | Owner `gh` login (local) | **HTTP 200**: 57 entries in the last month (`33` `bypass`, `24` `pass`), newest `after_sha: "dbd54fe382e7b2849d3f2038393cbdb4d709477b"` (`result: "bypass"`, `pushed_at: "2026-11-21T20:20:44+00:00"`, `actor_name: "stephendor"`), oldest `bb9d91d45493f7dfdf31aa1c3e6b34ecf6113a32` (`2026-10-21T22:42:20+01:00`) | **PASS** (verified live) | Reviewing session (`wp9-5-note-r1-review-2026-11-21.md:198`) and authoring session (Appendix A §19.1), 2026-11-21 |
| `GET repos/ZK-Theory/TDL/commits/dbd54fe3.../pulls` | Owner `gh` login (local) | **HTTP 200**: PR `#446`, `merge_commit_sha == "dbd54fe382e7b2849d3f2038393cbdb4d709477b"` | **PASS** (verified live) | Reviewing session (`wp9-5-note-r1-review-2026-11-21.md:183,300`), 2026-11-21 |
| `GET repos/ZK-Theory/TDL/rulesets/20822054` | CI `GITHUB_TOKEN` (`contents: read`) | **OPEN GAP (U-3, UNVERIFIED)** — pending throwaway draft-PR probe run | Pending | Owner: Stephen authorizes run; reviewing session runs and records HTTP status + `X-Accepted-GitHub-Permissions` here before code dispatch |
| `GET repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=day&per_page=5` | CI `GITHUB_TOKEN` (`contents: read`) | **OPEN GAP (U-3, UNVERIFIED)** — decides D-8; expected HTTP 403/404 per `tools/check_bypass_merges.py:20-21`; pending probe run | Pending | Owner: Stephen authorizes run; reviewing session runs and records HTTP status + `X-Accepted-GitHub-Permissions` here before code dispatch |
| `GET repos/ZK-Theory/TDL/commits/dbd54fe3.../pulls` | CI `GITHUB_TOKEN` (`contents: read` vs `pull-requests: read`) | **OPEN GAP (U-3, UNVERIFIED)** — pending probe run | Pending | Owner: Stephen authorizes run; reviewing session runs and records HTTP status + `X-Accepted-GitHub-Permissions` here before code dispatch |

#### 4.2.3 Exact D-8 fallback (`06v:159,571`; `P-064` item 8, `03-decisions-and-open-questions.md:4232-4233`)

- **Exact texts:**
  - `06v` §6 row `D-8` (`06v-w9-implementation-plan.md:571`):
    > *"Record as a known limit that bypass use between batches is seen only at the next pre-batch local read, under the owner's `gh`. The alternative is a token with ruleset read access."*
  - `P-064` item 8 (`03-decisions-and-open-questions.md:4232-4233`):
    > *"D-8, the CI token limit. This applies only if U-3 shows the CI token cannot read rule-suites. Bypass use between batches is then a known limit, seen at the next pre-batch read."*
  - `06v` §2.8 row `U-3` (`06v-w9-implementation-plan.md:159`):
    > *"A read-only probe from a workflow run. If the token cannot, the limit goes to Stephen as D-8. It is not a package-level fallback."*
- **How D-8 is gated so a workflow edit alone cannot silently enable it (`R1-m1`):**
  1. D-8 applies **only** to `rulesets/rule-suites` (and only if the U-3 probe shows `GITHUB_TOKEN` cannot read `rulesets/rule-suites`, and Stephen confirms D-8 rather than provisioning a ruleset-read token). If `GITHUB_TOKEN` can read `rulesets/20822054`, `tools/check_legacy_writes.py` still reads and enforces the `rulesets/20822054` configuration in CI on every run.
  2. Because `06v:159` states *"the limit goes to Stephen as D-8. It is not a package-level fallback"*, `tools/check_legacy_writes.py` refuses `--ruleset-check ci-d8` unless `.research-system/evidence/w9/walk-baseline.json` (committed at `<head>`, §6.2) carries an explicit owner-accepted field `"d8_rule_suites_limit_decision_ref": "P-090"` (or the register entry where Stephen confirms D-8 after the U-3 probe). Without that committed decision reference at `<head>`, passing `--ruleset-check ci-d8` fails closed (`ERROR: main_ruleset: --ruleset-check ci-d8 requires an owner-accepted d8_rule_suites_limit_decision_ref in walk-baseline.json`).
  3. On the operator machine before every batch (`06v:603`) and at L-1, `tools/check_legacy_writes.py` always runs with `--ruleset-check require` (the default), reading both `rulesets/20822054` and `rulesets/rule-suites` under Stephen's `gh` login.
  4. **Scope of the D-8 known limit (`R1-i3`):** Because 33 of 57 `refs/heads/main` rule-suite evaluations in the past month were `result: "bypass"`, D-8 means CI does not inspect `rule-suites` bypass metadata between batches. However, the Git first-parent walk in CI still inspects every commit on `main` (including every bypass merge) against Rules 0, 1, 2, and 3.

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

2. **Remaining U-4 pre-code step — handle-bound reader and segmenter dry run (`R1-m8`):**
   - As `R1-m8` notes, metadata alone does not exercise `handle_bound_read` (`st_nlink == 1`, `open_registered_root_anchor`, `open_registered_member_directory_anchor`) or `segment(raw, "computational_log_entry")` on the current `833,453`-byte live file.
   - `P-089` item 4 (`03-decisions-and-open-questions.md:6116-6117`) explicitly permits U-4's dry run to read the vault (`"U-4's dry run may read the vault; it writes nothing there"`), while Handover §4 (`handoffs/wp9-5-gemini-note-handover-2026-11-21.md:175`) and Follow-up §2 (`handoffs/wp9-5-gemini-note-r2-followup-2026-11-21.md:57-60`) direct this authoring session not to run it itself and to specify it as a pre-code step for the reviewing session.
   - **Exact read-only dry-run command for the reviewing session to execute and record below before WP9.5 code dispatch (prints only metadata, counts, and blocker count—never entry prose):**
     ```powershell
     C:\Users\steph\TDL\.venv\Scripts\python.exe -c "
     from collections import Counter
     from pathlib import Path
     from research_system.legacy.reader import handle_bound_read
     from research_system.legacy.segmentation import segment as rs_segment
     from tools.w9_segmentation import segment as tool_segment

     vault = Path(r'C:\Users\steph\Documents\TDA-Research')
     assert not vault.is_symlink() and not vault.is_junction()
     raw, phys, _ = handle_bound_read(vault, '04-Methods/Computational-Log.md')
     s1 = rs_segment(raw, 'computational_log_entry')
     s2 = tool_segment(raw, 'computational_log_entry')
     assert s1 == s2, 'segmenter mismatch'
     kinds = Counter(r['row_kind'] for r in s1['rows'])
     blockers = [(r['row_ordinal'], r['line_start'], r['line_end'], r['blocker_reason']) for r in s1['rows'] if r['row_kind'] == 'blocker']
     print({'bytes': len(raw), 'sha256': s1['file_sha256'], 'link_count': phys['link_count'], 'canonical_target': phys['canonical_target'], 'file_facts': s1['file_facts'], 'row_counts': dict(kinds), 'blockers': blockers})
     "
     ```
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
  - Under **Owner Point A (Option A1, Recommended, §16)**:
    - Each entry in `registration-manifest.json` carries the 5 closed keys:
      ```json
      {
        "format": "w9-registration-manifest/1",
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
    - What changes in `research_system/legacy/evidence.py:114-131` (`require_registered`, `R1-m10`):
      In `evidence.py:124-130`, `require_registered` currently runs:
      ```python
      entries = [
          _closed(entry, {"root_kind", "root_id", "normalized_path"}, "registration manifest entry")
          for entry in body["registrations"]
      ]
      wanted = {key: registration.get(key) for key in ("root_kind", "root_id", "normalized_path")}
      if wanted not in [dict(entry) for entry in entries]:
          raise EvidenceRefused("W9 registration is not in the registration manifest at git_head")
      ```
      Under Option A1, `require_registered` is updated so that:
      1. each `entry` must be a `Mapping` whose key set is either `{"root_kind", "root_id", "normalized_path", "role", "source_identity_kind"}` (5 keys, required by the exporter and validate-all mode) or `{"root_kind", "root_id", "normalized_path"}` (3 keys, keeping existing WP9.3 unit-test fixtures green);
      2. when `role` and `source_identity_kind` are present on `entry` and on `registration`, `require_registered` checks that `(entry["role"], entry["source_identity_kind"]) == (registration.get("role"), registration.get("source_identity_kind"))`; and
      3. the membership comparison at line 129 projects each `entry` to the three identity keys `({key: entry[key] for key in ("root_kind", "root_id", "normalized_path")})` before testing `wanted not in ...`, avoiding the 3-key vs 5-key dict mismatch noted in `R1-m10`!
- **Sorting and serialization:**
  - Entries in `"registrations"` are sorted by `(entry["root_kind"], entry["root_id"], entry["normalized_path"])`, checked for uniqueness on `(root_kind, root_id, normalized_path)`, and written as UTF-8 JSON (`json.dumps(payload, indent=2, sort_keys=True) + "\n"`, LF line endings).
- **How `--check` mode works (store-equals-manifest check):**
  1. Loads `binding = _legacy_current_binding(control_root)` and `state, _ = _legacy_projection(control_root)`.
  2. Projects the expected registration list from `state["records"]["legacy_path_registration"].values()`.
  3. Reads `.research-system/evidence/w9/registration-manifest.json` from Git at `binding.binding["git_head"]` via `evidence.read_evidence(binding.repository_root, binding.binding["git_head"], evidence.REGISTRATION_MANIFEST)` (`research_system/legacy/evidence.py:92-105`).
  4. Validates the committed manifest's 5-key schema and compares `manifest["registrations"]` against the projected list from the store.
  5. If they differ, exits `1` with `ERROR: registration_manifest: store_manifest_mismatch at git_head=<git_head>: missing_in_manifest=<...>, extra_in_manifest=<...>`.

---

## 6. The post-merge first-parent detector (`tools/check_legacy_writes.py` and `.github/workflows/legacy-write-detector.yml`)

### 6.1 Time-indexed evidence evaluation and why reading at `<head>` alone is broken (`R1-B1`)

Revision 1 read `registration-manifest.json`, `legacy-write-records.json`, and `shared-surface-changes.json` once at `<head>`. As `R1-B1` proved, evaluating historical commits against `<head>` has four fatal defects:
1. **Atomic disarm:** A single squash commit `C` could delete a file's entry from `registration-manifest.json` and modify the file in the same commit; at `<head>` the file is not in the manifest, so Rule 1 would not fire.
2. **Retroactive false positives:** When a file (such as `.apm/tracker.md`) is registered at time `T1` after L-1 baseline `T0`, legitimate commits between `T0` and `T1` touched that file before it was registered; reading the manifest at `<head>` would flag those pre-registration commits forever.
3. **Retroactive blessing:** Reading `legacy-write-records.json` at `<head>` would let a later PR add a record for an earlier unauthorized commit and turn a red detector green, violating `06v:212,479-481` (*"The PR making the change carries its own entry"*).
4. **Detector self-edit / baseline shift:** Running `tools/check_legacy_writes.py` from `<head>`'s checkout or reading a baseline constant from `<head>`'s script would let a commit weaken the detector or advance the baseline constant past itself.

**Revision 2 fixes all four defects by time-indexing every check and adding Rule 0 (monotonicity) and baseline pinning:**

| Evidence / artifact | Evaluated at which commit during the walk of commit `C` (with first parent `P1`)? | Why |
|---|---|---|
| `registration-manifest.json` (Rules 1 and 3) | **At `P1` (`<P1>:.research-system/evidence/w9/registration-manifest.json`)** (plus any new entries added in `C` itself, via the union $\text{Manifest}(P_1) \cup \text{Manifest}(C)$) | A file registered at `P1` is protected against removal+edit in `C` (atomic disarm is impossible because `F` is in $\text{Manifest}(P_1)$). Conversely, a commit `C` that landed **before** `F` was registered in the manifest has $F \notin \text{Manifest}(P_1) \cup \text{Manifest}(C)$, so pre-registration commits never suffer retroactive false positives! |
| `legacy-write-records.json` (Rules 1, 2, and 3) | **At `C` (`<C>:.research-system/evidence/w9/legacy-write-records.json`)** | The PR that makes an authorized W9 §4.2 or §4.3 change must carry its own record inside commit `C` (`06v:212,479-481`). No later commit after `C` can retroactively bless an unrecorded write in `C`. |
| `shared-surface-changes.json` (Rule 3, `O-32`) | **At `C` (`<C>:.research-system/evidence/w9/shared-surface-changes.json`)** under Option D3/D1 (or at `<head>` under two-PR Option D2; see §6.5 and Owner Point D) | Under Option D3 (Recommended), the PR changing a `shared_enforcement_surface` carries its own blob-keyed entry in `shared-surface-changes.json` inside commit `C`. |
| Monotonicity of evidence & detector files (**Rule 0**) | **Every step `P1 -> C` across `<baseline>..<head>`** | See §6.5 Rule 0: no commit may delete or mutate an existing entry in `registration-manifest.json`, `legacy-write-records.json`, `shared-surface-changes.json`, `walk-baseline.json`, or `detector-controls.json`, or modify the detector scripts/workflow without an owner-attested record. |
| The detector executable itself (`tools/check_legacy_writes.py`, `tools/check_conventions_legacy_locks.py`) | **Pinned to `<baseline>` in CI and pre-batch runs** | In `.github/workflows/legacy-write-detector.yml` (and pre-batch runs), the workflow extracts or verifies the detector scripts at `<baseline>` (`git --no-replace-objects show <baseline>:tools/check_legacy_writes.py`) before running the walk, and Rule 0 checks any change to the detector scripts between `<baseline>` and `<head>`. A commit that weakens `tools/check_legacy_writes.py` is still judged by `<baseline>`'s unweakened tool! |

---

### 6.2 The walk baseline (`walk-baseline.json`) and complete post-freeze first-parent commit inventory (`R1-B1`, `R1-M3`, `R1-M12`; Owner Point C)

#### 6.2.1 Complete verified inventory of first-parent commits touching guarded prefixes between `4b143c92` and `dbd54fe3`

Running `git --no-replace-objects rev-list --first-parent --reverse 4b143c9225035cc29e37351445f1c3a4ab09ceb1..dbd54fe382e7b2849d3f2038393cbdb4d709477b` yields **320** first-parent commits on `main` (Appendix A §19.1). Across all 320 commits, exactly **20** first-parent commits touched a path equal to `CONVENTIONS.md` or under `results/`, `papers/`, `contracts/`, or `.apm/`:

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
| 15 | `452352ff` (1 parent; `p1=4d867d85`) | `2026-10-17T08:00:26+01:00` | `#368` (`[DECISION] P06: record L5, A6, A7 and step 3 batches 1-3 of the 06s Phase 5 run (P-058) (#368)`) | Modified `.apm/tracker.md` (`8101faa5 -> c2716092`) | Session Working Note append (`W9` §4.1 row 2, `:164`) |
| 16 | `3a14a97c` (1 parent; `p1=1b8ed812`) | `2026-10-17T16:10:48+01:00` | `#376` (`[DECISION] SYS: require no review producer at merge admission; drop Codex (#376)`) | Modified `CONVENTIONS.md` (`272ef07a -> 0a6cd1b8`) | Successor update in `CONVENTIONS.md` |
| 17 | `53b7c5be` (1 parent; `p1=6e3ad7f3`) | `2026-10-21T13:19:54+01:00` | `#384` (`[DECISION] SYS: no thread-finality waiver; guidance matches the producer config (#384)`) | Modified `CONVENTIONS.md` (`0a6cd1b8 -> baceabd6`) | Successor update in `CONVENTIONS.md` |
| 18 | `e3519ba7` (1 parent; `p1=3fa437a1`) | `2026-10-22T15:28:58+01:00` | `#388` (`[EXPLORE] P00: record the 2026-10-21 worktree sweep in the Tracker (#388)`) | Modified `.apm/tracker.md` (`c2716092 -> e791d95d`) | **Post-G7-A (`3fa437a1`)** worktree-sweep Working Note append in `.apm/tracker.md` (`R1-M5`, `R1-M12`) |
| 19 | `633ed58e` (1 parent; `p1=4a5a1300`) | `2026-10-27T16:23:00Z` | `#401` (`[PIPELINE] P06: W11 byte-identity test and the SUPERSEDED.md Markov-2 correction (review 2026-10-27, D3 + E1) (#401)`) | Modified `results/trajectory_tda_integration/stage1/SUPERSEDED.md` (`ee7557ad -> 84403ce2`) | **Post-G7-A (`3fa437a1`)** reviewed Markov-2 correction to `SUPERSEDED.md`, accounted for in `wp9-3-design-note.md:978` (`P-079`) (`R1-M12`) |
| 20 | `a6a98966` (1 parent; `p1=baea2c13`) | `2026-11-12T12:43:39Z` | `#433` (`[EXPLORE] P00: record the 2026-11-12 worktree sweep in the Tracker (#433)`) | Modified `.apm/tracker.md` (`e791d95d -> 509d20bf`) | **Post-G7-A (`3fa437a1`)** worktree-sweep Working Note append in `.apm/tracker.md` (`R1-M5`, `R1-M12`) |

*(Note: Commits `#419` `14a81b84` on `2026-11-08` and `#425` `1fba78aa` on `2026-11-10` also modified `CONVENTIONS.md` (`baceabd6 -> 14d39755 -> 1db03819`) with pure successor insertions; they are rows 19b/19c in the full 20-commit list from `verify_r2.py` in Appendix A §19.1.)*

#### 6.2.2 Committed append-only walk-baseline record (`.research-system/evidence/w9/walk-baseline.json`) and first-parent chain verification (`R1-B1`, `R1-M12`; Owner Point C)

Instead of hard-coding a baseline SHA inside `tools/check_legacy_writes.py`:
1. **Committed append-only baseline ledger (`.research-system/evidence/w9/walk-baseline.json`, format `"w9-walk-baseline/1"`):**
   Added at L-1 (and as a dated row in `06v-addendum-2026-11-10-w9-paths.md` under Owner Point C):
   ```json
   {
     "format": "w9-walk-baseline/1",
     "d8_rule_suites_limit_decision_ref": null,
     "baselines": [
       {
         "baseline_commit": "<40-hex-L1-parent-commit-on-main>",
         "recorded_in_decision_ref": "P-09x",
         "detector_tool_blobs": {
           "tools/check_legacy_writes.py": "<40-hex>",
           "tools/check_conventions_legacy_locks.py": "<40-hex>",
           "tools/check_legacy_log_baseline.py": "<40-hex>"
         },
         "pre_baseline_dispositions_ref": "docs/plans/agentic-research-system/transition/w9/wp9-5-design-note.md#621-complete-verified-inventory-of-first-parent-commits-touching-guarded-prefixes-between-4b143c92-and-dbd54fe3"
       }
     ]
   }
   ```
2. **Active baseline selection and first-parent chain verification (`R1-B1`):**
   - Unless `--baseline <sha>` is explicitly passed in a `--ruleset-check skip` test, `tools/check_legacy_writes.py` reads `walk-baseline.json` at `<head>` and takes `baseline = baselines[0]["baseline_commit"]` (the original L-1 activation baseline; because Rules 1 and 3 evaluate against the manifest **at `P1`**, the walk can start from the original L-1 baseline without ever flagging pre-registration commits!). If a later owner decision appends a new baseline entry to `baselines`, Rule 0 verifies that `baselines` is strictly append-only and that the new entry cites a decision-register entry existing at `P1`.
   - **First-parent chain membership check (stronger than `merge-base --is-ancestor`):**
     `git merge-base --is-ancestor <baseline> <head>` returns true even if `<baseline>` is on a side branch merged into `main`'s second parent. Therefore, `tools/check_legacy_writes.py` runs:
     `git --no-replace-objects rev-list --first-parent <baseline>~1..<head>` (or walks `rev-list --first-parent <head>`) and verifies that `<baseline>` itself lies **on `<head>`'s first-parent chain**. If `<baseline>` is not on `<head>`'s first-parent chain, the detector fails closed (exit `1`) with:
     `ERROR: post_merge_first_parent: baseline <baseline> is not on the first-parent chain of <head>`

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
     1. **Primary lookup (`commits/<C>/pulls` with retry and backoff, `R1-m5`):**
        Calls `gh api repos/ZK-Theory/TDL/commits/<C>/pulls`. Because GitHub's commit-to-PR index can transiently return `[]` immediately after a squash commit is pushed to `main`, if the response is HTTP 200 with no PR matching `pull.get("merged_at") and pull.get("merge_commit_sha") == C`, the detector retries up to 3 times with exponential backoff (`1s`, `2s`, `4s`).
     2. **Subject-hinted fallback lookup (`pulls/<N>` verified by `merge_commit_sha == C`, `R1-m5`):**
        If `commits/<C>/pulls` still returns no match after retries, the detector inspects `C`'s commit subject line for a trailing `(#<N>)` or `^Merge pull request #(<N>) ` hint. If a candidate integer `<N>` is present, it queries `gh api repos/ZK-Theory/TDL/pulls/<N>` directly and accepts `<N>` **if and only if** `pull.get("merged_at")` is non-empty **and** `pull.get("merge_commit_sha") == C`.
        - Why this is unspoofable: The subject line is used strictly as an index hint to query `pulls/<N>`; GitHub's authoritative `pull["merge_commit_sha"] == C` check still decides whether PR `<N>` actually produced commit `C`. For `5df0c001` (whose subject says `Merge pull request #215...`), `pulls/215` has `merge_commit_sha == "a426b731..." != "5df0c001..."` (`wp9-5-note-r1-review-2026-11-21.md:299`), so the hint is rejected and `5df0c001` maps to `pr_number = None`!
     3. **Distinguishing API/transport failure (exit `2`) from an unmapped commit (exit `1`) (`R1-m5`):**
        - If `gh api` fails with a non-zero exit code, timeout, HTTP 4xx/5xx error, or malformed JSON, `tools/check_legacy_writes.py` exits **`2`** (matching `tools/check_bypass_merges.py:25`) with:
          `ERROR: post_merge_first_parent: GitHub API read failed while mapping commit <C>: <stderr_or_status>`
        - If the API succeeds (HTTP 200) and no merged PR has `merge_commit_sha == C`, `pr_number` is `None` and the detector exits **`1`** with `pr=none` in the Rule 0/1/2/3 violation message.
     4. **Test-only flags hard-locked behind `--ruleset-check skip` (`R1-m6`):**
        The flags `--pr-map <json>` and `--manifest-file <json>` are **test-only** overrides for offline scratch-clone tests. If either `--pr-map` or `--manifest-file` is passed when `--ruleset-check` is not `skip`, `tools/check_legacy_writes.py` immediately exits **`2`** before reading any commit (`ERROR: post_merge_first_parent: --pr-map and --manifest-file are permitted only with --ruleset-check skip`). A unit test in `tests/tools/test_w9_detectors.py` parses `.github/workflows/legacy-write-detector.yml` and asserts that none of `--pr-map`, `--manifest-file`, or `--ruleset-check skip` appears anywhere in the workflow file.

---

### 6.4 The W9 §4.2 record: format, evaluation at `C`, and provenance verification at `P1` (`R1-B1`, `R1-M5`, `R1-M10`; Owner Points B and H)

- **Location:** `.research-system/evidence/w9/legacy-write-records.json` (format `"w9-legacy-write-records/1"`, added as a dated row in `06v-addendum-2026-11-10-w9-paths.md` under Owner Point B).
- **Evaluated at `C` (`R1-B1`):** When commit `C` (with first parent `P1`, mapped to `pr_number`) touches a guarded path, the detector reads `<C>:.research-system/evidence/w9/legacy-write-records.json`.
- **Preventing self-authored owner notes and self-reviews in the same PR (`R1-M10`):**
  As `R1-M10` pointed out, ruleset `20822054` has `required_approving_review_count: 0`, and `.research-system/evidence/w9/*` is not currently in `.github/CODEOWNERS`. If the detector merely checked that `owner_note.author == "stephen"` and that `source_ref` and `review_path` exist at `C`, a PR author could write `"author": "stephen"`, a register entry, and a review file of their own inside the same PR `C`.
  To prevent a PR from fabricating its own authorization at `C`:
  1. **Pre-existing owner decision (`source_ref` verified at `P1`):**
     For `"repo_wide_change_4_2_b"`, `"owner_ruling_4_2_c"`, and `"shared_surface_4_3"`, `owner_note` must name:
     - `"decision_entry_id"`: `"P-0xx"`,
     - `"source_path"`: `"docs/plans/agentic-research-system/03-decisions-and-open-questions.md"`,
     - `"source_commit"`: a 40-hex commit SHA that is an ancestor of **`P1`** (`is_ancestor(repo_root, source_commit, P1)` is `True`, so the owner ruling/note was already committed on `main` **before** PR `C` merged!), and
     - `"entry_sha256"`: the SHA-256 of the `### P-0xx` section slice in `<P1>:docs/plans/agentic-research-system/03-decisions-and-open-questions.md`, which must exist at `P1` and contain the each touched `(normalized_path, old_blob, new_blob)` tuple (or the ruling reference).
  2. **Pre-existing independent review (`independent_review` verified at `P1`):**
     For `"repo_wide_change_4_2_b"` and `"shared_surface_4_3"`, `independent_review` must name:
     - `"review_path"`: `"docs/plans/agentic-research-system/reviews/<file>.md"`,
     - `"review_commit"`: a 40-hex commit SHA that is an ancestor of **`P1`** (`is_ancestor(repo_root, review_commit, P1)` is `True`, so the independent review was committed on `main` **before** `C`), and
     - `"review_blob"` / `"review_sha256"`: matching `<P1>:<review_path>`.
  3. **CODEOWNERS / Rule 0 protection (Owner Point I, §16):**
     In addition to requiring `source_commit` and `review_commit` to precede `C` (at `P1`), Owner Point I proposes adding `.research-system/evidence/w9/**`, `tools/check_legacy_writes.py`, `tools/check_conventions_legacy_locks.py`, `tools/check_legacy_log_baseline.py`, `tools/run_w9_detector_controls.py`, `tools/export_w9_registration_manifest.py`, and `.github/workflows/legacy-write-detector.yml` to `.github/CODEOWNERS` (`@stephendor`) so that any PR modifying an evidence file or detector tool requires Stephen's code-owner review/bypass at merge admission.
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

### 6.5 Rules 0, 1, 2, and 3 of `tools/check_legacy_writes.py` (`R1-B1`, `R1-M4`, `R1-M5`, `R1-M6`, `R1-i1`)

For each first-parent commit $C \in (\text{baseline}, \text{head}]$ with first parent $P_1$ and changed file tuples $(m_{\text{old}}, m_{\text{new}}, b_{\text{old}}, b_{\text{new}}, \text{status}, p) \in \text{diff-tree}(P_1, C)$:

#### Rule 0 — Monotonicity of W9 evidence files and detector surface (`R1-B1`, `R1-M10`; Owner Point I)

1. **`registration-manifest.json` is strictly append-only:**
   If $P_1 \to C$ modifies or deletes `.research-system/evidence/w9/registration-manifest.json`, the detector parses the manifest at $P_1$ (if present at $P_1$) and at $C$. Every registration entry present at $P_1$ must remain present with identical fields at $C$. Deleting or altering an existing registration entry fails closed with:
   `ERROR: post_merge_first_parent: Rule 0 violation at commit <C>: registration-manifest.json deleted or modified existing registration entry <entry>`
2. **`legacy-write-records.json`, `shared-surface-changes.json`, `walk-baseline.json`, and `vault-detector-runs.json` are strictly append-only:**
   If $P_1 \to C$ touches any of these files, every entry present at $P_1$ must remain present and byte-identical at $C$, and any newly appended entry in `legacy-write-records.json` at $C$ must have `entry["pr_number"] == pr_number(C)` (so commit $C$ can only append a record for its **own** PR number, never for an earlier PR number!). Otherwise fail closed with:
   `ERROR: post_merge_first_parent: Rule 0 violation at commit <C>: evidence file '<path>' mutated prior entries or appended a record for a different PR`
3. **`detector-controls.json` and detector tools/workflow:**
   - Once `.research-system/evidence/w9/detector-controls.json` exists at $P_1$, it cannot be deleted at $C$, and any update must pass `require_detector_controls` (`research_system/legacy/evidence.py:133-154`) with `recorded_at` timestamps $\ge$ those at $P_1$.
   - If $P_1 \to C$ modifies any of the detector files (`tools/check_legacy_writes.py`, `tools/check_conventions_legacy_locks.py`, `tools/check_legacy_log_baseline.py`, `tools/run_w9_detector_controls.py`, `tools/export_w9_registration_manifest.py`, `tools/_w9_detector_evidence.py`, or `.github/workflows/legacy-write-detector.yml`), `walk-baseline.json` at $C$ must update `detector_tool_blobs` in a newly appended baseline entry whose `recorded_in_decision_ref` exists in `<P1>:docs/plans/agentic-research-system/03-decisions-and-open-questions.md`. Otherwise fail closed with:
     `ERROR: post_merge_first_parent: Rule 0 violation at commit <C>: detector tool or workflow '<path>' modified without a pre-existing decision-register entry in walk-baseline.json`

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
- **`.apm/tracker.md` Working Notes handling (`R1-M5`; Owner Point H, §16):**
  If $p == \text{".apm/tracker.md"}$ and Stephen selects **Option H1 (Recommended)** in Owner Point H, a commit $C$ mapped to a merged PR passes Rule 1 on `.apm/tracker.md` if `check_tracker_working_note_append(raw_P1, raw_C)` verifies via `segment(raw, "tracker_task_row")` and `segment(raw, "working_note_entry")` (`research_system/legacy/segmentation.py:470-473`) that:
  (i) every `tracker_task_row` item and every byte outside `## Working Notes` is byte-identical between $P_1$ and $C$, and
  (ii) every `working_note_entry` present at $P_1$ is preserved byte-for-byte and in order at $C$ (pure append of new working note(s) with 0 blockers).
  Under Option H2 or H3, `.apm/tracker.md` follows that option's rule (§16 H).
- **Requirement for all other Rule-1 matches:**
  Commit $C$ must map to a valid `pr_number` (`merge_commit_sha == C`), `b_old != b_new`, and `<C>:.research-system/evidence/w9/legacy-write-records.json` must contain a valid record for `pr_number` (with `owner_note` and `independent_review` verified at `P1` per §6.4) covering $(p, b_{\text{old}}, b_{\text{new}})$ and every other guarded file touched by $C$.
- **Failure message (closed, exit 1):**
  `ERROR: post_merge_first_parent: Rule 1 violation at commit <C> (pr=<pr_or_none>): registered path '<p>' changed (<b_old> -> <b_new>) without a valid in-commit W9 §4.2 record`

#### Rule 2 — Any path under `results/` outside `results/ars/` (`06v:478`; `W9-D13`, `W9-D14`, `W9:140-147,196`; `R1-i1`)

- **Matching rule:** The changed path $p$'s case-folded path starts with `"results/"` and does **not** start with `"results/ars/"`.
- **Deliberate hard-coding of the `results/ars/` prefix exemption (`R1-i1`):**
  `W9-D14` (`09-migration-compatibility-and-pilot.md:754`) says *"register `results/ars/` as the `successor_results_root` so the detector exempts exactly that prefix"*. In `tools/check_legacy_writes.py`, Rule 2 exempts the exact normalized prefix `"results/ars/"` directly (whether or not `results/ars/` has been registered in `registration-manifest.json` yet) so that unregistered legacy result families under `results/` (P04, poverty, financial; `W9-D13`) are always guarded while `results/ars/` never requires a §4.2 record.
- **Requirement:** Commit $C$ must map to a valid `pr_number`, `b_old != b_new`, and `<C>:.research-system/evidence/w9/legacy-write-records.json` must contain a valid §4.2 record for `pr_number` covering $(p, b_{\text{old}}, b_{\text{new}})$.
- **Failure message (closed, exit 1):**
  `ERROR: post_merge_first_parent: Rule 2 violation at commit <C> (pr=<pr_or_none>): results path outside results/ars/ '<p>' changed (<b_old> -> <b_new>) without a valid in-commit W9 §4.2 record`

#### Rule 3 — `shared_enforcement_surface` contracts (`06v:212,479-481`; `O-32`; `W9` §4.3, `W9:183-190`; `R1-M6`; Owner Point D)

- **How the detector identifies shared enforcement surfaces:**
  From $\mathcal{M}(P_1, C) = \text{Manifest}(P_1) \cup \text{Manifest}(C)$, the set of shared enforcement surfaces at commit $C$ is:
  `{r["normalized_path"] for r in M(P1, C) if r["root_kind"] == "repository_root" and r["role"] == "shared_enforcement_surface"}`
  (for example, real repository contract paths such as `contracts/manifests/research-assurance.yaml`, `contracts/stochastic-tests/monte-carlo-permutation-p-value.yaml`, `contracts/stochastic-tests/markov-order-provenance.yaml`, and `contracts/topology-invariants/null-operation-changes-ph-input.yaml`; `W9:166`).
- **What Rule 3 requires when $P_1 \to C$ changes a `shared_enforcement_surface` path $s$ ($b_{\text{old}} \to b_{\text{new}}$):**
  1. Commit $C$ must map to `pr_number` (`merge_commit_sha == C`), and `<C>:.research-system/evidence/w9/legacy-write-records.json` must contain a valid record for `pr_number` with `allowance_kind == "shared_surface_4_3"`, `owner_note` verified at $P_1$, `independent_review` (the reviewer's binding-test derivation of affected results) verified at $P_1$, and `(s, b_old, b_new)` in `files`.
  2. `<C>:.research-system/evidence/w9/shared-surface-changes.json` must contain a valid entry for this change to $s$.
- **Resolving the `O-32` squash-merge SHA contradiction (`R1-M6`; Owner Point D, §16):**
  As verified in `wp9-5-note-r1-review-2026-11-21.md:116-124`, `06v:90-91` (*"A commit SHA created by the queue cannot be named inside the PR that creates it"*) and `06v:212,479-481` (*"The PR that changes a shared surface carries its own entry in a committed change list in the W9 evidence area, naming the contract and its old and new blobs"*) conflict with WP9.3's `research_system/legacy/evidence.py:231-238` (`_closed(item, {"merge_commit", "surface", "affected_registrations"}, ...)`) and `research_system/legacy/acceptance.py:135` (`evidence.is_ancestor(repository_root, entry["merge_commit"], str(source.get("git_commit")))`).
  Furthermore, `R1-M6` showed that placing a `base_commit` in the entry (Option D1) is unsound under the merge queue because `main` can advance between `base_commit` and the squash merge commit, allowing an observation taken between `base_commit` and the squash merge to satisfy `obs != base_commit and is_ancestor(base_commit, obs)`.
  Section 16 **Owner Point D** therefore presents three options, recommending **Option D3 (blob-keyed, tree-state freshness, no commit field)**:
  - **Under Option D3 (Recommended):**
    - Each entry in `shared-surface-changes.json` has closed keys `{"pr_number", "surface", "old_blob", "new_blob", "affected_registrations"}` (no commit SHA field!).
    - In `tools/check_legacy_writes.py` (Rule 3), at commit $C$ (mapped to `pr_number`), the detector checks that `<C>:.research-system/evidence/w9/shared-surface-changes.json` contains an entry with `(entry["pr_number"], entry["surface"], entry["old_blob"], entry["new_blob"]) == (pr_number, s, b_old, b_new)`.
    - In `research_system/legacy/acceptance.py:121-136` (`check_change_list`), for each entry affecting an item's registration, the item's observation commit `obs_commit = str(source.get("git_commit"))` is fresh if and only if `evidence.blob_at(repository_root, obs_commit, entry["surface"])` (`research_system/legacy/evidence.py:179-188`) equals `entry["new_blob"]` or the `new_blob` of a later entry for the same `surface` in `entries` (tree-state freshness: at the commit where the affected result was observed, the shared-surface contract already held its post-change blob!).
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

Direct execution of `segment(raw, "conventions_unit")` on `4620c716` (`4b143c92:CONVENTIONS.md`, 33,645 bytes, 575 lines) and on `dbd54fe3:CONVENTIONS.md` (51,774 bytes, 822 lines, SHA-256 `2ce15910d2f6712e2d4311578ebe8a5b6e7b1f83086c1c5483ea4876636ff97c`) gives the following exact per-section unit counts (Appendix A §19.1):

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

**Provisional 9-section partition vs L-0b per-unit classification (`R1-M9`; Owner Point J, §16):**
- `W9` §7.3 item 1 (`09-migration-compatibility-and-pilot.md:385-393`) states that the legacy set is decided by object, then date, and that *"The baseline observer lists every entry and lock with its classification; an entry it cannot classify is a blocker, and Stephen accepts the list."* And `06v:593` (row `L-0b`) records *"the `CONVENTIONS.md` baseline recorded"*.
- Until L-0b's classified list is accepted by Stephen, treating all `68` baseline units across the 9 non-`ARS Foundation Governance` sections as legacy locks is the **strictest (conservative) provisional rule**: every single one of those 68 units (and indeed all 70 baseline units, including the 2 baseline units in `ARS Foundation Governance`) is currently preserved byte-for-byte at `dbd54fe3`.
- To ensure no code rewrite is needed when L-0b is accepted (Owner Point J, §16), `tools/check_conventions_legacy_locks.py` accepts an optional `--classified-locks <path>` (or reads a committed `.research-system/evidence/w9/conventions-legacy-locks.json` once pinned at L-0b) mapping `(anchor_text, raw_row_sha256) -> "legacy" | "successor"`. When no L-0b classification file is pinned yet, it defaults to the conservative 9-section (`68`-unit) partition above.

### 7.4 Exact insertion-only decision rule and structural/table edge cases (`R1-m11`)

Given baseline segmentation $S_{\text{base}}$ (from blob `4620c716`) and candidate segmentation $S_{\text{cand}}$:

1. **File-level encoding invariants:**
   - `S_cand["file_facts"]["has_utf8_bom"]` must be `False` and `S_cand["file_facts"]["line_ending"]` must be `"LF"` (`.gitattributes:14` enforces `* text=auto eol=lf` across the repository). Otherwise fail closed with `ERROR: conventions_repository_check: file encoding/EOL violation`.
2. **Zero blocker rows:**
   - Neither $S_{\text{base}}$ nor $S_{\text{cand}}$ may contain any row with `row_kind == "blocker"` (e.g. `duplicate_anchor` within a section). Otherwise fail closed with `ERROR: conventions_repository_check: segmentation blocker at lines <line_start>-<line_end>: <blocker_reason>`.
3. **Legacy-lock section preservation (in order):**
   - Every section title $s \in \mathcal{L}$ (the 9 legacy-lock sections) must appear in $S_{\text{cand}}$, and their first appearances in $S_{\text{cand}}$ must preserve their baseline relative order $s_1, \dots, s_9$. Otherwise fail closed with:
     `ERROR: conventions_repository_check: legacy section '<s>' is missing, renamed, or reordered`
4. **Per-section ordered-subsequence preservation of legacy units:**
   - For each legacy-lock section $s \in \mathcal{L}$, let $B(s) = [h_1, \dots, h_m]$ be the ordered baseline `raw_row_sha256` values of legacy units in section $s$, and let $C(s) = [u_1, \dots, u_n]$ be the ordered candidate `raw_row_sha256` values in section $s$.
   - Every $h_j \in B(s)$ must exist in $C(s)$ (if missing, fail closed with `ERROR: conventions_repository_check: legacy unit modified or deleted in section '<s>' (baseline row_ordinal=<ord>, expected unit_hash=<h_j>)`), and their indices in $C(s)$ must satisfy $\text{idx}(h_1) < \dots < \text{idx}(h_m)$ (if not, fail closed with `ERROR: conventions_repository_check: legacy units reordered in section '<s>'`).
5. **Unit kind of inserted successor units and structural bytes (`R1-m11`):**
   - Note that `segment(raw, "conventions_unit")` (`tools/w9_segmentation.py:388-458`; `research_system/legacy/segmentation.py:357-426`) does **not** emit a `unit_kind` field on each row (each item row carries `row_ordinal`, `row_kind: "item"`, `anchor_text`, `byte_start`, `byte_end`, `byte_length`, `line_start`, `line_end`, `raw_row_sha256`, `anchor_line_sha256`, `blocker_reason: None`).
   - However, `W9` §7.3 item 4 (`09-migration-compatibility-and-pilot.md:404-405`) states: *"every later change to a section that holds legacy locks must be a pure insertion of successor bullets or paragraphs. No legacy bullet or paragraph is modified or deleted."*
   - To enforce that newly inserted units in a legacy-lock section are bullets or paragraphs (and **not** inserted tables), for every candidate row $c_i \in C(s)$ whose hash $u_i \notin B(s)$, `tools/check_conventions_legacy_locks.py` inspects the first byte of `candidate_raw[c_i["byte_start"]:c_i["byte_end"]]`. Under `conventions_unit` (`tools/w9_segmentation.py:415-457`), a table unit always begins with `|` (`0x7c`), whereas a bullet begins with `- ` or `* ` and a paragraph begins with any other non-blank character. If an inserted unit in a legacy-lock section begins with `|`, the checker fails closed with:
     `ERROR: conventions_repository_check: inserted unit in legacy section '<s>' at lines <line_start>-<line_end> is a table, not a bullet or paragraph (W9 §7.3 item 4)`
   - **Explicitly accepted structural behavior (`w9-segmentation-contract-v1.md:100-105,244`):** Under `w9-segmentation/1.0.0` §3, `---` horizontal rules, blank lines, the `*Last updated: ...*` footer, the H1 title before the first `## `, and `### ` sub-headings inside a `## ` section (such as `### Contract artifacts are LF-only in the working tree (locked 2026-07-28)` inside `## Computational Environment`, added by `#172` `7347ae95`) are structural bytes outside `conventions_unit` items.

### 7.5 What it outputs and where it runs

- **Output (`w9-conventions-check/1`):**
  ```json
  {
    "format": "w9-conventions-check/1",
    "baseline_commit": "4b143c9225035cc29e37351445f1c3a4ab09ceb1",
    "baseline_blob": "4620c71607ca3a06c6df3b8e96a6bddffc783960",
    "candidate_sha256": "2ce15910d2f6712e2d4311578ebe8a5b6e7b1f83086c1c5483ea4876636ff97c",
    "legacy_sections_checked": 9,
    "legacy_units_verified": 68,
    "inserted_successor_units_in_legacy_sections": 7,
    "total_candidate_units": 90,
    "status": "ok"
  }
  ```
- **Where it runs:** Before every batch on the operator machine (`06v:604`), in `.github/workflows/legacy-write-detector.yml`, and in `tests/tools/test_w9_detectors.py`.

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
       3. runs `recheck_cl_export(export, retained_raw)` (`research_system/legacy/export_recheck.py:32-89`), which verifies that `export["producer"]` equals `CL_EXPORT_PRODUCER` (`tools/w9_segmentation.py` at blob `43e1454de09b61e274954c42b21d6ae533857a24`, `evidence.py:52-54`) and that the runtime segmenter `research_system/legacy/segmentation.py` reproduces `export["segmentation"]` over `selector["region"] = {"first_line": first, "last_line": last}` (`evidence.py:296-298`); and
       4. validates the `classified_list` JSON (§8.3; Owner Point J).
     - **Fixture mode (`--fixture-export-json <path> --fixture-retained-copy <path> [--fixture-classified-list <path>]`, for tests and pre-L-0b negative controls):**
       Reads the fixture export JSON, retained copy bytes, and classified list from disk, and runs `evidence.require_cl_export(export)` (`evidence.py:277-362`) and `recheck_cl_export(export, retained_raw)` (`export_recheck.py:32-89`).
2. **Whole-page segmentation of the live vault file (`R1-M2`):**
   - Calls `live_seg = segment(live_raw, "computational_log_entry")` (`research_system/legacy/segmentation.py:429-488`, with `region=None` so it covers `(1, len(lines))`) and verifies agreement with `tools/w9_segmentation.py:461-518`.
   - Why `region=None` on the live file even when `export["selector"]["region"]` is a sub-range `{"first_line": first, "last_line": last}`: new successor entries are prepended near the top of `04-Methods/Computational-Log.md`, shifting the line numbers and byte offsets of every legacy entry below them (`w9-segmentation-contract-v1.md:189-192`).
3. **Exact five-part decision rule (`R1-M1`, `R1-M9`, `R1-m8`):**
   - **Check 1 — Live file BOM and zero blocker rows across the live page (`W9:197`, `R1-M1`, `R1-m8`):**
     - `live_seg["file_facts"]["has_utf8_bom"]` must be `False`.
     - **Line-ending resilience for Obsidian successor edits (`R1-m8`):** Unlike `CONVENTIONS.md` (which is tracked in Git under `.gitattributes`), `04-Methods/Computational-Log.md` is edited in the vault by Obsidian or operator tools on Windows. If a new successor entry at the top of the file is saved with CRLF while all legacy entries retain their exact LF bytes, `live_seg["file_facts"]["line_ending"]` becomes `"mixed"`, even though **zero legacy bytes changed**. Therefore, `tools/check_legacy_log_baseline.py` does **not** fail on `file_facts["line_ending"] != "LF"` alone; instead, Check 3 and Check 4 compare each legacy row's exact slice hash `raw_row_sha256` (which includes that row's line terminators, `w9-segmentation-contract-v1.md:168-169`, so any LF->CRLF change inside a legacy entry immediately changes `raw_row_sha256` and fails Check 3!).
     - **Zero blocker rows (`W9:197`):** As verified in `w9-segmentation-contract-v1.md:242,254-256`, the live `Computational-Log.md` had **0 blockers** across all 255/256 entries. For every row `r` in `live_seg["rows"]`, `r["row_kind"]` must not be `"blocker"`. If any row in `live_seg["rows"]` has `row_kind == "blocker"` (`blocker_reason` in `{"unparseable_anchor", "duplicate_anchor", "unaddressed_region"}`), fail closed immediately with:
       `ERROR: vault_computational_log: live file contains segmentation blocker at row_ordinal=<ord> (lines <line_start>-<line_end>): <blocker_reason> (<anchor_text_or_none>)`
   - **Check 2 — Complete legacy/successor classification of baseline export rows (`R1-M9`; Owner Point J):**
     - Why a classification resolution rule is needed (`R1-M9`): In `research_system/legacy/evidence.py:347-360`, `require_cl_export` allows each slot in `export["classifications"]` to have `slot["class"] is None or isinstance(slot["class"], str)` (because the initial raw export at L-0b may leave `class: None` until the classified legacy-entry list is produced and accepted by Stephen under `06v:569,593`, pinned as `ACCEPTED_CL_EXPORT[-1]["classified_list"]` in `accepted_w9.py:86-88`).
     - Under **Owner Point J (§16)**, the detector resolves `class_by_ordinal` from `classified_list` (when provided/pinned, format `"w9-cl-classified-list/1"`, §8.3) or falls back to `export["classifications"]` (in self-contained fixture tests where `export["classifications"]` already carries `"legacy"` / `"successor"`).
     - Every row in `export["segmentation"]["rows"]` must have a resolved classification in `{"legacy", "successor"}` (if any baseline row is `"blocker"` or has `class is None`, fail closed with `ERROR: vault_computational_log: baseline export has unclassified or blocker row at row_ordinal=<ord>`).
   - **Check 3 — Every legacy `"item"` row is preserved byte-for-byte (`W9:197,402-403`; `w9-segmentation-contract-v1.md:189-192`):**
     - Let $L_{\text{item}}$ be the ordered list of rows in `export["segmentation"]["rows"]` with `row_kind == "item"` and `class_by_ordinal[row["row_ordinal"]] == "legacy"`.
     - Index all `"item"` rows in `live_seg["rows"]` by `anchor_text` (unique because Check 1 rejected all `duplicate_anchor` blockers).
     - For each baseline legacy item row $b \in L_{\text{item}}$:
       1. Look up `anchor = b["anchor_text"]` in the live item index. If absent, fail closed with:
          `ERROR: vault_computational_log: missing or renamed legacy heading anchor '<anchor>' (baseline row_ordinal=<ord>, raw_row_sha256=<sha>)`
       2. Let $l$ be the matching live item row. Require `l["anchor_line_sha256"] == b["anchor_line_sha256"]` and `l["raw_row_sha256"] == b["raw_row_sha256"]`. If either differs, fail closed with:
          `ERROR: vault_computational_log: byte change inside legacy entry '<anchor>' (expected raw_row_sha256=<b_sha>, got <l_sha> at live lines <l_start>-<l_end>)`
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
      "ordinal": 0,
      "row_kind": "structural",
      "anchor_text": null,
      "anchor_line_sha256": "<64-hex>",
      "raw_row_sha256": "<64-hex>",
      "class": "legacy"
    },
    {
      "ordinal": 1,
      "row_kind": "item",
      "anchor_text": "2026-07-16|RESULT|P01-A: ...",
      "anchor_line_sha256": "<64-hex>",
      "raw_row_sha256": "<64-hex>",
      "class": "legacy"
    }
  ]
}
```
Every row ordinal $0, \dots, N-1$ of `export["segmentation"]["rows"]` must appear in `classified_list["classifications"]` with matching `(ordinal, row_kind, anchor_text, anchor_line_sha256, raw_row_sha256)` and with `class` in `{"legacy", "successor"}` (no `null` allowed in the accepted classified list!).

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
  4. **Explicit statement of the weekly operational cost and self-attestation limit (`R1-M8`):**
     - **Operational cost:** Because `research_system/legacy/evidence.py:92-105` (`read_evidence`) reads every evidence file from Git at the store binding's `git_head` (never from the working tree), recording each weekly run in `.research-system/evidence/w9/vault-detector-runs.json` requires a **weekly reviewed PR to `main`** (and, before any store command `LR-003`/`LR-015`/`LR-016`/`LR-020` runs against that evidence, an `ars store advance-binding` authorized by Stephen under `06v` D-1, `:578`).
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

**How `tools/run_w9_detector_controls.py` makes the transcripts 100% deterministic and binds them to the detector tool blobs (`R1-m4`):**

1. **Pinned Git environment for all synthetic commits in negative controls:**
   Every `git commit` or `git commit-tree` executed by `tools/run_w9_detector_controls.py` runs with:
   ```python
   CONTROL_GIT_ENV = {
       "GIT_AUTHOR_NAME": "W9 Control Runner",
       "GIT_AUTHOR_EMAIL": "w9-controls@tdl.local",
       "GIT_AUTHOR_DATE": "2026-11-21T00:00:00Z",
       "GIT_COMMITTER_NAME": "W9 Control Runner",
       "GIT_COMMITTER_EMAIL": "w9-controls@tdl.local",
       "GIT_COMMITTER_DATE": "2026-11-21T00:00:00Z",
       "GIT_CONFIG_NOSYSTEM": "1",
   }
   ```
   With pinned tree blobs, parent SHAs, message bytes, and `CONTROL_GIT_ENV`, every synthetic commit SHA `<C>` generated in `tmp_path` is bit-for-bit identical across machines and runs!
2. **Binding each detector tool's Git blob ID into the hashed transcript:**
   Each detector's canonical transcript includes `"tool_git_blob": git_blob_id(Path(tool_path).read_bytes())` (`research_system/legacy/reader.py:75-77`):
   ```json
   {
     "format": "w9-control-transcript/1",
     "detector": "post_merge_first_parent",
     "tool_path": "tools/check_legacy_writes.py",
     "tool_git_blob": "<40-hex>",
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
3. **CI re-verification of `watched_to_fail` hashes after L-1 (`R1-m4`):**
   Because the three `watched_to_fail` transcripts (`post_merge_first_parent`, `vault_computational_log`, `conventions_repository_check`) are completely deterministic functions of the repository's object database and the three detector scripts' bytes, `tools/run_w9_detector_controls.py --verify-watched-to-fail .research-system/evidence/w9/detector-controls.json` re-runs the three `watched_to_fail` control suites in a temporary directory and asserts that their recomputed `output_sha256` values match the committed hashes in `detector-controls.json`! If anyone edits a detector tool without re-running and re-recording the controls (under Rule 0), `--verify-watched-to-fail` fails closed (`ERROR: detector_controls: recomputed output_sha256 for '<detector>' does not match detector-controls.json`).

---

## 10. Merging is not going live (`P-089` item 3)

### 10.1 Why WP9.5 must stay inactive on `main` and the vault after merge

- `P-089` (`03-decisions-and-open-questions.md:6113-6115,6129-6130`) withholds authorization for **L-1** ("the detectors live on `main` or the vault") and requires that merging WP9.5 must not start any detector automatically on `main` or the vault.
- While `.research-system/evidence/w9/detector-controls.json` is absent on `main`, WP9.3's `prepare_proposal` (`LR-003`, `research_system/legacy/preparers.py:686-690`) refuses any path registration on a store bound to `main`.

### 10.2 Full `.github/workflows/legacy-write-detector.yml` specification (`R1-B1`, `R1-M11`, `R1-m6`, `R1-m7`)

In WP9.5, `.github/workflows/legacy-write-detector.yml` is committed with `on: workflow_dispatch:` only, full-history checkout (`fetch-depth: 0`), `permissions: contents: read, pull-requests: read`, first-parent `origin/main` head validation, and baseline-pinned tool execution:

```yaml
name: W9 Legacy Write Detector

on:
  workflow_dispatch:
    inputs:
      baseline_commit:
        description: "Optional override baseline commit SHA on origin/main's first-parent chain (40-hex)"
        required: false
        default: ""
      head_commit:
        description: "Optional target commit SHA on origin/main's first-parent chain (default: origin/main)"
        required: false
        default: ""

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

      - name: Install dependencies from the lockfile
        run: uv sync --locked --extra dev

      - name: Verify target head is on origin/main first-parent chain and run W9 detectors
        env:
          GH_TOKEN: ${{ github.token }}
          INPUT_BASELINE: ${{ inputs.baseline_commit }}
          INPUT_HEAD: ${{ inputs.head_commit }}
        run: |
          set -euo pipefail
          main_tip="$(git --no-replace-objects rev-parse refs/remotes/origin/main | tr -d '\r')"
          target_head="${INPUT_HEAD:-$main_tip}"
          if [ "$target_head" != "$main_tip" ]; then
            if ! git --no-replace-objects rev-list --first-parent "$main_tip" | tr -d '\r' | grep -qx "$target_head"; then
              echo "ERROR: target_head $target_head is not on origin/main ($main_tip) first-parent chain" >&2
              exit 1
            fi
          fi
          baseline_args=()
          if [ -n "$INPUT_BASELINE" ]; then
            baseline_args=(--baseline "$INPUT_BASELINE")
          fi
          .venv\Scripts\python.exe tools/check_legacy_writes.py \
            --repo-root . \
            --head "$target_head" \
            "${baseline_args[@]}"
          .venv\Scripts\python.exe tools/check_conventions_legacy_locks.py \
            --repo-root . \
            --git-ref "${target_head}:CONVENTIONS.md"
```

**Why every part of this workflow skeleton is required (`R1-B1`, `R1-M11`, `R1-m6`, `R1-m7`):**
1. **`fetch-depth: 0` (`R1-m7`):** `tools/check_legacy_writes.py` refuses shallow clones (`git rev-parse --is-shallow-repository == "false"`), and `tools/check_conventions_legacy_locks.py` reads historical blob `4620c716` from `4b143c92`.
2. **`origin/main` first-parent head guard (`R1-m7`):** A manual `workflow_dispatch` triggered from a feature branch in the GitHub UI sets `GITHUB_REF` to that feature branch. Instead of walking `--head HEAD`, the workflow resolves `refs/remotes/origin/main` and verifies that `target_head` is either `origin/main`'s tip or lies on `origin/main`'s first-parent chain.
3. **Self-integrity against detector weakening (`R1-B1`):** Inside `tools/check_legacy_writes.py`, before walking `baseline..head`, when `.research-system/evidence/w9/walk-baseline.json` is present at `<baseline>`, the tool compares its own running file bytes (`git_blob_id(Path(__file__).read_bytes())`) against `<baseline>:tools/check_legacy_writes.py` (or re-executes the baseline copy from a temp file if `--head` modified `tools/check_legacy_writes.py`), and Rule 0 verifies that any change to a detector script between `<baseline>` and `<head>` is authorized by a pre-existing decision-register entry in `walk-baseline.json`.
4. **Compatibility with existing watchdogs:**
   - `tools/check_workflow_liveness.py:78-92` (`inactive_tracked_workflows`, called by `.github/workflows/ars-artefact-currency-watchdog.yml:98-112` with `--all-tracked`) checks that every tracked workflow is registered in GitHub Actions with `state == "active"`. On PRs and merge-group runs, `ars-artefact-currency-watchdog.yml:103-112` passes `--tracked-ref FETCH_HEAD` (the base branch `main`), and after merge GitHub registers the `workflow_dispatch`-only workflow as `state: "active"`.
   - `.github/workflows/ci.yml:263,276` (`watchdog-schedule-liveness`) checks `--latest-run-json` only for `ars-artefact-currency-watchdog.yml` and `research-system-suite.yml`.

### 10.3 The L-1 tripwire test and how L-1 switches it (`R1-M7`; Owner Point F)

In `tests/tools/test_w9_detectors.py`, a module-level constant defines the L-1 activation state:
```python
# Flipped from False to True in the L-1 activation PR authorized by Stephen (06v §7 L-1).
L1_LIVE = False
```
The test `test_legacy_write_detector_l1_activation_state` asserts:
- **While `L1_LIVE is False` (WP9.5):**
  1. `.github/workflows/legacy-write-detector.yml` has `set(doc["on"].keys()) == {"workflow_dispatch"}` (no `push`, `schedule`, `pull_request`, or `merge_group`);
  2. None of `.research-system/evidence/w9/detector-controls.json`, `.research-system/evidence/w9/registration-manifest.json`, `.research-system/evidence/w9/walk-baseline.json`, or `.research-system/evidence/w9/vault-detector-runs.json` exists in `REPO_ROOT`.
- **When `L1_LIVE is True` (flipped in the L-1 activation PR):**
  1. `.github/workflows/legacy-write-detector.yml` has `set(doc["on"].keys()) == {"push", "schedule", "workflow_dispatch"}`;
  2. `.research-system/evidence/w9/detector-controls.json` exists and passes `evidence.require_detector_controls` and `--verify-watched-to-fail`;
  3. `.research-system/evidence/w9/walk-baseline.json` and `.research-system/evidence/w9/registration-manifest.json` exist and pass schema validation.
- **Why `tests/tools/test_w9_detectors.py` must run in `.github/workflows/ci.yml`'s `admission-controls` job (`R1-M7`, Owner Point F):**
  If `tests/tools/test_w9_detectors.py` were only named in `.github/workflows/legacy-write-detector.yml` (Option F2), it would never run on pull requests, so a normal PR could accidentally add `push:` to `legacy-write-detector.yml` without `test_legacy_write_detector_l1_activation_state` ever running! Running `tests/tools/test_w9_detectors.py` in `ci.yml`'s `admission-controls` job (Option F1, Recommended) ensures the tripwire and all detector unit controls run on every PR and merge-group commit.

---

## 11. Where the controls run and scratch-clone mechanics (`P-089` item 4; `06v` O-13; W9-T7)

### 11.1 Hard isolation rule (`P-089` item 4; `06v:193,497-502`)

Every negative control and integration test runs exclusively on a scratch Git clone or a byte copy inside `pytest`'s `tmp_path` (or `tempfile.TemporaryDirectory`), **never** by writing to `main`, the working checkout, any linked worktree, or `C:\Users\steph\Documents\TDA-Research`.

### 11.2 How the W9-T7 scratch clone is constructed and replayed (`R1-M3`, `R1-m14`)

`06v` §4 row `W9-T7` (`06v-w9-implementation-plan.md:230`) and `06v` §5 (`:499`) require:
> *"Replay `5df0c001` and `811d5a2b` on a scratch clone from the local object store, fixture registry listing the files `5df0c001` and `811d5a2b` touched"*

1. **Measured bare scratch clone from the local object store (`1.71–1.79s` on this machine; Appendix A §19.1):**
   - `git clone --bare --local --no-hardlinks <REPO_ROOT> <tmp_path>/scratch.git`
   - Verified on `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note` on 2026-11-21 (Appendix A §19.1):
     - Copies the local object packs into `<tmp_path>/scratch.git/objects` without hardlinks in **1.71–1.79 seconds**.
     - Contains `4b143c9225035cc29e37351445f1c3a4ab09ceb1`, `a426b731e614986b6ca19a193e452df3e3efd885`, `5df0c001231fc1fac2e78f5f1834ddc754c45492`, `811d5a2b094bc82b135eb74eb6c08302cd5419b2`, and `b132406eff2e2a6b77e44d3c4d8702911f3afddf`.
   - Immediately after cloning, the test runs `git --git-dir=<tmp_path>/scratch.git remote remove origin` so the scratch clone has no remote URL.
2. **Dynamic derivation of the fixture registration manifest from `git diff-tree` (`R1-M3`):**
   - Rather than hard-coding file paths that could drift or be mistyped, W9-T7 derives the exact 7 `results/` paths touched by `5df0c001` and the exact 3 `contracts/` paths touched by `811d5a2b` directly from the scratch clone via `git --git-dir=<tmp_path>/scratch.git --no-replace-objects diff-tree -r --no-renames --name-only <C>~1 <C>`, and asserts that the derived sets equal the verified repository paths (Appendix A §19.1):
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
   - W9-T7 writes a 10-entry fixture `registration-manifest.json` (`w9-registration-manifest/1`) registering the 7 `results/` files with `role: "legacy_research_result"`, `source_identity_kind: "git_tracked"` and the 3 `contracts/manifests/input-provenance/` files with `role: "legacy_contract"`, `source_identity_kind: "git_tracked"`.
3. **Executing the replay (`R1-m14`):**
   - **Replay T7-1 (Historical commits `5df0c001` and `811d5a2b` in `<tmp_path>/scratch.git`):**
     Runs `tools/check_legacy_writes.py --repo-root <tmp_path>/scratch.git --ruleset-check skip --manifest-file <tmp_path>/fixture-manifest.json --pr-map <tmp_path>/empty-pr-map.json`:
     - over `--baseline a426b731e614986b6ca19a193e452df3e3efd885 --head 5df0c001231fc1fac2e78f5f1834ddc754c45492`: asserts exit code `1`, flagging all 7 `results/` paths under **both** Rule 1 and Rule 2 (and not flagging the 4 non-`results/` paths);
     - over `--baseline 1d3a0769b93fcdda0dfe4000613c16d5b9d1a527 --head 811d5a2b094bc82b135eb74eb6c08302cd5419b2`: asserts exit code `1`, flagging all 3 `contracts/manifests/input-provenance/` paths under Rule 1 (and not flagging the 6 non-contract paths);
     - over the combined range `--baseline 4b143c9225035cc29e37351445f1c3a4ab09ceb1 --head 811d5a2b094bc82b135eb74eb6c08302cd5419b2`: asserts exit code `1`, flagging both `5df0c001` and `811d5a2b`.
   - **Replay T7-2 (In-tree committed manifest at `P1` using a throwaway `GIT_INDEX_FILE`, `R1-m14`):**
     To also exercise the production code path where `registration-manifest.json` is read directly from `<P1>:.research-system/evidence/w9/registration-manifest.json` (without `--manifest-file`), the test uses a throwaway index file `GIT_INDEX_FILE=<tmp_path>/idx` in `<tmp_path>/scratch.git` (`git read-tree`, `git update-index --add --cacheinfo 100644,<blob>,.research-system/evidence/w9/registration-manifest.json`, `git write-tree`, `git commit-tree`) to create a synthetic baseline commit `B0` holding `registration-manifest.json`, followed by synthetic commits `C_5df` and `C_811` that apply the exact `(path, new_blob)` changes of `5df0c001` and `811d5a2b`. Running `check_legacy_writes.py` without `--manifest-file` across `B0..C_811` takes < 0.3 seconds and asserts the same Rule 1 and Rule 2 failures.

### 11.3 How the test proves it never writes the real repository or the vault (`R1-m3`)

As `R1-m3` noted, running plain `git status --porcelain` refreshes `.git/index`, and checking only `HEAD` + `show-ref` would miss new loose objects, `FETCH_HEAD`, hooks, config edits, or untracked/ignored file changes.
Therefore, the immutability fixture in `tests/research_system/integration/test_w9_wp9_5_detectors.py` and `tests/tools/test_w9_detectors.py`:
1. Runs every detector subprocess with `cwd=tmp_path` and `env={**os.environ, "GIT_DIR": str(scratch_git_dir)}` so no Git child process can default to `REPO_ROOT`.
2. Before and after each test, takes a pure Python filesystem snapshot (using `os.scandir` with `follow_symlinks=False`, never calling `git status` without `--no-optional-locks`):
   - Recursively records `(relpath, st_size, st_mtime_ns)` for every file under `REPO_ROOT`'s Git metadata directory (`git --no-optional-locks rev-parse --git-dir` and `--git-common-dir`, excluding only external worktree folders under `.apm/worktrees/`); and
   - Runs `git -C <REPO_ROOT> --no-optional-locks --no-replace-objects status --porcelain=v1 --ignored -z` and `git -C <REPO_ROOT> --no-optional-locks --no-replace-objects rev-parse HEAD`.
3. Asserts exact equality of the before and after snapshots.

---

## 12. Tests and test-time budget

### 12.1 Test inventory and mapping to `06v` §4

| Test file | Markers | Cases covered |
|---|---|---|
| `tests/tools/test_w9_detectors.py` | `unit` (default; no `slow` marker) | 1. **`W9-T19` (`CONVENTIONS.md` check):** baseline `4620c716` passes; current `CONVENTIONS.md` (`dbd54fe3`, 68 legacy units + 7 inserted in `Computational Environment` + 9 in `ARS Foundation Governance` + 6 in `Repo-Wide CI` = 90 units) passes; pure insertion of successor bullet/paragraph in `## Always` passes; L-0b `--classified-locks` input test; negative controls N1–N6 (modified legacy bullet, deleted legacy paragraph, reordered legacy bullets, duplicate unit in section, missing/renamed legacy section, inserted table in legacy section) each exit `1`.<br>2. **`W9-T19` (Computational-Log check on synthetic fixture export + classified list):** clean fixture passes; prepended successor entry (including CRLF successor entry above LF legacy entries, `R1-m8`) passes; modified successor-classified entry passes; empty `ACCEPTED_CL_EXPORT` in production mode fails closed; symlink, junction, or in-repo `--vault-root` fails closed; negative controls V1–V6 (1-byte edit or LF->CRLF inside legacy entry, renamed legacy heading anchor, deleted legacy entry, duplicate heading anchor, unparseable dated heading, reordered legacy entries) each exit `1`.<br>3. **D-5 cadence check:** clean run within 7 days passes; missing `vault-detector-runs.json` when `ACCEPTED_CL_EXPORT` is non-empty fails closed; latest run > 7 days old fails closed; consecutive runs > 7 days apart fail closed until an `"owner_cadence_reset"` entry followed by a fresh `"run"` entry is recorded.<br>4. **Post-merge detector unit controls (on a module-scoped synthetic Git repo in `tmp_path`):**<br>  - **Time-indexed evidence & Rule 0 (`R1-B1`):** atomic disarm attempt (commit deletes manifest entry and edits file in `C`) fails Rule 0 and Rule 1 (manifest read at `P1`); pre-registration edit (commit touches file before the commit that adds it to `registration-manifest.json`) passes; retroactive blessing attempt (commit `C1` edits registered file without record; commit `C2` adds record for `C1`'s PR) fails Rule 0 and Rule 1 (records read at `C1`); detector script self-edit without `walk-baseline.json` decision ref fails Rule 0; baseline not on `<head>`'s first-parent chain fails closed.<br>  - **Rule 1 matching and exclusions (`R1-M4`, `R1-M5`):** `conventions_lock`, `untracked_file`, `restricted_untracked_file`, `vault_root`, `successor_results_root`, and `legacy_read_only_projection` are excluded from Rule 1 and from §6.6's `git cat-file` check; `legacy_manuscript_root` directory prefix matching catches edits under `papers/P01-A-JRSSA/...`; mode-only change on a registered file fails closed; `.apm/tracker.md` pure Working-Note append (under Option H1) passes while a task-row edit fails.<br>  - **Rule 1/2/3 §4.2 record provenance (`R1-M10`):** self-authored `source_commit` or `review_commit` not an ancestor of `P1` fails closed; valid `source_commit` and `review_commit` at `P1` with matching `(pr_number, path, old_blob, new_blob)` at `C` passes.<br>  - **Rule 2 & Rule 3 (`O-32`):** unregistered `results/p04/out.json` without §4.2 record at `C` fails Rule 2; `results/ars/out.json` passes; `shared_enforcement_surface` edit without `shared-surface-changes.json` entry or without W9 §4.3 owner note at `C` fails Rule 3.<br>  - **PR mapping & CLI lockouts (`R1-m5`, `R1-m6`):** retry on transient `[]`, subject-hint `pulls/<N>` fallback verified by `merge_commit_sha == C`, API failure exits `2`, `--pr-map` or `--manifest-file` without `--ruleset-check skip` exits `2`, workflow passes no test-only flags.<br>5. **Ruleset reader (`main_ruleset`) unit controls (`R1-m2`):** live payload shape passes; drift in `enforcement`, `allowed_merge_methods`, `max_entries_to_merge`, `require_code_owner_review`, `required_status_checks`, or `bypass_actors` exits `1`; previous read > 30 days old exits `1`.<br>6. **Pre-L-1 inactivity tripwire (`R1-M7`):** `test_legacy_write_detector_l1_activation_state` checks `L1_LIVE = False` invariants. |
| `tests/research_system/integration/test_w9_wp9_5_detectors.py` | `integration`, with `@pytest.mark.slow` on `W9-T7` and `O-13` | 1. **`W9-T7` (`slow`, `integration`):** module-scoped `git clone --bare --local --no-hardlinks` scratch clone of `REPO_ROOT` in `tmp_path` (measured at 1.71–1.79s); derives the 7 `results/` paths of `5df0c001` and 3 `contracts/` paths of `811d5a2b` via `git diff-tree`; runs T7-1 (historical SHAs) and T7-2 (in-tree manifest via throwaway `GIT_INDEX_FILE`); asserts `5df0c001` fires Rule 1 and Rule 2 on all 7 `results/` files and `811d5a2b` fires Rule 1 on all 3 manifests; asserts `--no-optional-locks` snapshot immutability of `REPO_ROOT`.<br>2. **`M-6` (`integration`):** scratch W9 control store + scratch Git repo in `tmp_path`; registers paths across roles (`legacy_research_result`, `shared_enforcement_surface`, `conventions_lock`, `legacy_manuscript_root`, `untracked_file`, `restricted_untracked_file`, `successor_results_root`), runs `tools/export_w9_registration_manifest.py`, commits manifest, advances binding, verifies `--check` exits `0`, and verifies store-extra and manifest-extra mismatches exit `1`.<br>3. **`O-13` (`slow`, `integration`):** runs `tools/run_w9_detector_controls.py` end-to-end in `tmp_path` with `CONTROL_GIT_ENV`, verifies deterministic `output_sha256` across two runs, verifies `--verify-watched-to-fail` fails if a detector tool byte is altered, and verifies the output passes `evidence.require_detector_controls` and `LR-003`. |

### 12.2 Fixture provenance rule (`06v:248-255`)

- No test reads any live file from `C:\Users\steph\Documents\TDA-Research` or `C:\Users\steph\TDL\vault`, and no unit test reads live `papers/` or `results/` files.
- The `CONVENTIONS.md` baseline test reads blob `4620c71607ca3a06c6df3b8e96a6bddffc783960` from Git (`4b143c9225035cc29e37351445f1c3a4ab09ceb1:CONVENTIONS.md`) and verifies `git_blob_id(raw) == "4620c71607ca3a06c6df3b8e96a6bddffc783960"` and `sha256_hex(raw) == "d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589"` (`research_system/legacy/reader.py:43-49`) before running any assertion.

### 12.3 Measured timings and test-time budget (`R1-m14`; Owner Point G)

In revision 2, we measured the two dominant operations directly on this machine (Appendix A §19.1):
- `git clone --bare --local --no-hardlinks` of the 335 MiB object store (`28` packs, `58,133` objects) into `%TEMP%` + two `git diff-tree` queries + cleanup: **1.77 seconds** (run 1: `1.86s`, run 2: `1.77s`).
- `segment(raw, "conventions_unit")` over both `4620c716` (`33,645` bytes) and `dbd54fe3:CONVENTIONS.md` (`51,774` bytes) with both segmenters: **< 0.15 seconds**.

| Test file | Estimated wall-clock time (serial, `--no-cov`, **including `@pytest.mark.slow`**) | Basis |
|---|---|---|
| `tests/tools/test_w9_detectors.py` | **15 – 25 seconds** | In-memory byte-copy segmentation controls (< 2s) + one module-scoped synthetic Git repo in `tmp_path` for Rule 0/1/2/3 unit tests (~10–15s). |
| `tests/research_system/integration/test_w9_wp9_5_detectors.py` | **25 – 50 seconds** | One module-scoped `--bare --local --no-hardlinks` clone (measured at 1.77s) + throwaway `GIT_INDEX_FILE` commit-tree (~0.3s) + one scratch W9 store for M-6 and O-13 (~20–35s, matching WP9.4-2's single-store fixture timing). |
| **Total WP9.5 test suite (all tests, including `slow`)** | **40 – 75 seconds** | Every new test in WP9.5—including `@pytest.mark.slow` tests—counts toward the budget. |

Owner Point G (§16) asks Stephen to choose between the **5-minute (300-second)** budget established for WP9.4-2 in `P-087` item 7 (`03-decisions-and-open-questions.md:5919-5923`) or a tighter **2-minute (120-second)** ceiling, with all tests (including `slow`-marked tests) counting toward the budget and over-budget returning `PARTIAL` with measurements.

---

## 13. Research assurance

WP9.5 touches the **Output / Provenance** assurance lane (`CONVENTIONS.md:20-34`): legacy artifact immutability detection, shared-surface state invalidation detection, `CONVENTIONS.md` lock preservation, vault Computational-Log legacy entry integrity, and detector negative-control evidence hashes.

### 13.1 Machine-checkable claims and their enforcement artifacts

| # | Claim | Enforcement artifact (test / validator / schema) |
|---|---|---|
| MC-1 | Every `legacy_path_registration` record in the W9 control store appears in `.research-system/evidence/w9/registration-manifest.json` (with matching `root_kind`, `root_id`, `normalized_path`, `role`, `source_identity_kind`) at `binding.binding["git_head"]`, and vice versa. | `tools/export_w9_registration_manifest.py --check`; tested in `tests/research_system/integration/test_w9_wp9_5_detectors.py` (`test_m6_registration_manifest_matches_store`). |
| MC-2 | No first-parent commit on `main` after `<baseline>` can delete or alter an existing entry in `registration-manifest.json`, `legacy-write-records.json`, `shared-surface-changes.json`, `walk-baseline.json`, or `vault-detector-runs.json`, append a `legacy-write-records.json` entry for a different PR, or edit a detector tool/workflow without an owner decision ref in `walk-baseline.json` existing at `P1`. | `tools/check_legacy_writes.py` (Rule 0); tested in `tests/tools/test_w9_detectors.py`. |
| MC-3 | Any first-parent commit `C` (with first parent `P1`) after `<baseline>` that modifies, deletes, renames, or mode-changes a `git_tracked` `repository_root` path registered in `registration-manifest.json` at `P1` (or `C`, excluding `conventions_lock`, `shared_enforcement_surface`, `successor_results_root`, and `legacy_read_only_projection`) without a matching `(pr_number, normalized_path, old_blob, new_blob)` record in `<C>:.research-system/evidence/w9/legacy-write-records.json` whose `owner_note` and `independent_review` commits precede `C` (at `P1`) causes `tools/check_legacy_writes.py` to exit `1`. | `tools/check_legacy_writes.py` (Rule 1); tested in `tests/tools/test_w9_detectors.py` and by `W9-T7` replay of `5df0c001` and `811d5a2b` in `tests/research_system/integration/test_w9_wp9_5_detectors.py`. |
| MC-4 | Any first-parent commit `C` after `<baseline>` that adds, modifies, deletes, renames, or mode-changes any path under `results/` outside `results/ars/`—whether registered or unregistered—without a matching in-commit §4.2 record at `C` causes `tools/check_legacy_writes.py` to exit `1`. | `tools/check_legacy_writes.py` (Rule 2); tested in `tests/tools/test_w9_detectors.py` and by `W9-T7` replay of `5df0c001`. |
| MC-5 | Any first-parent commit `C` after `<baseline>` that modifies a `shared_enforcement_surface` contract registered at `P1` (or `C`) without both an in-commit W9 §4.3 record in `legacy-write-records.json` and an entry in `shared-surface-changes.json` causes `tools/check_legacy_writes.py` to exit `1`. | `tools/check_legacy_writes.py` (Rule 3, `O-32`); tested in `tests/tools/test_w9_detectors.py`. |
| MC-6 | `git diff-tree -r --no-renames -z <P1> <C>` detects file changes introduced by both 1-parent squash/direct commits and 2-parent merge commits on `main`. | `tools/check_legacy_writes.py`; tested in `tests/tools/test_w9_detectors.py`. |
| MC-7 | Every legacy unit in `CONVENTIONS.md` from commit `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (blob `4620c71607ca3a06c6df3b8e96a6bddffc783960`) is preserved byte-for-byte and in relative order under `segment(raw, "conventions_unit")`, and any inserted unit in a legacy-lock section is a bullet or paragraph (never a table). | `tools/check_conventions_legacy_locks.py`; tested in `tests/tools/test_w9_detectors.py` (`W9-T19`, controls N1–N6). |
| MC-8 | Every legacy-classified `"item"` and `"structural"` row in the accepted `w9-cl-export/1` baseline export of `04-Methods/Computational-Log.md` is preserved byte-for-byte and in relative order in the live vault file, with zero segmentation blocker rows across the live file, while prepended successor entries pass. | `tools/check_legacy_log_baseline.py`; tested in `tests/tools/test_w9_detectors.py` (`W9-T19`, controls V1–V6). |
| MC-9 | All four detector controls produce deterministic `output_sha256` hashes bound to each detector tool's Git blob that pass `evidence.require_detector_controls` and `--verify-watched-to-fail`. | `tools/run_w9_detector_controls.py` and `research_system/legacy/evidence.py:133-154`; tested in `tests/research_system/integration/test_w9_wp9_5_detectors.py`. |
| MC-10 | While `L1_LIVE is False`, `.github/workflows/legacy-write-detector.yml` has `on == {"workflow_dispatch"}` only and none of the live L-1 evidence files is committed on `main`. | `tests/tools/test_w9_detectors.py` (`test_legacy_write_detector_l1_activation_state`), wired into `ci.yml` `admission-controls` under Option F1. |

### 13.2 Human-review-only claims and residual architectural limits (`R1-M8`, `R1-M10`, `R1-m2`, `R1-i3`)

| # | Claim / Limit | Reviewer / Owner check and why not mechanized |
|---|---|---|
| HR-1 | Whether a W9 §4.2(b) repository-wide change is truly semantically equivalent on the registered legacy files it touched, and whether the independent review was genuinely authored by an independent session. | `tools/check_legacy_writes.py` verifies that `source_commit` and `review_commit` precede `C` (at `P1`) and match the committed decision entry and review file hashes, and CODEOWNERS (Owner Point I) requires `@stephendor` to merge any evidence edit, but semantic equivalence and session independence require human verification (`W9:174-176`). |
| HR-2 | Whether `affected_registrations` in a `shared-surface-changes.json` entry includes every registered result semantically affected by the contract edit. | The detector and `acceptance.py` verify that the entry exists and that listed affected registrations are re-observed after the change, but deriving the affected set from binding tests requires Stephen's note and the independent reviewer's derivation (`W9:185-188`). |
| HR-3 | **Post-merge detection vs preventive merge control (`R1-M10`):** `tools/check_legacy_writes.py` is a post-merge detector on `origin/main`; ruleset `20822054` has `required_approving_review_count: 0`, and `@stephendor`'s admin bypass is available in `pull_request` mode. | Preventive blocking of an unauthorized merge before it lands on `main` rests on human merge review and `.github/CODEOWNERS` (`@stephendor`), while the post-merge detector and WP9.3's store preparers (`LR-015`, `LR-016`, `LR-020`) detect and refuse acceptance after the fact. |
| HR-4 | **Self-attestation of the weekly vault Computational-Log detector runs (`R1-M8`):** `vault-detector-runs.json` records `run_at` and `output_sha256` produced on the operator machine. | Because CI cannot access `C:\Users\steph\Documents\TDA-Research`, no remote runner can independently verify that the operator machine ran `tools/check_legacy_log_baseline.py` against the live vault at `run_at`. |
| HR-5 | **30-day rule-suites API window (`R1-m2`) and D-8 bypass visibility between batches (`R1-i3`):** GitHub's `rulesets/rule-suites` endpoint returns at most one month (`MAX_DAYS = 30`), and 33 of 57 evaluations on `refs/heads/main` last month were `result: "bypass"`. | The ruleset reader fails closed if the previous recorded read is older than 30 days, and under D-8 (if `GITHUB_TOKEN` cannot read `rule-suites`) direct inspection of `rule-suites` occurs at each pre-batch local run under the owner's `gh` (`06v:571,603`). |

---

## 14. Claims for review (`R1-m12`)

An independent adversarial reviewer should attack each of the following 16 load-bearing claims against the cited repository evidence at base commit `dbd54fe382e7b2849d3f2038393cbdb4d709477b`:

1. **No D-4 trigger (`P-089` item 1):** WP9.5 adds no W9 command, no runtime-binding census row (stays at 275 rows, SHA-256 `82eab93a1b2ac81dd564581237f35e3dff19fee9e824ffff317d0f202b451d58`), no store append site (06h manifest stays at blob `1066404a`, smoke test at `3b1eec6e`), no core or W9 schema, and does not touch `tools/w9_segmentation.py` (blob `43e1454de09b61e274954c42b21d6ae533857a24`, `evidence.py:52-54`) or `IMPORTER_MODULES` (`reader.py:42`). See §2.2 and `03-decisions-and-open-questions.md:6085-6099`.
2. **Time-indexed evidence prevents atomic disarm, retroactive false positives, and retroactive blessing (`R1-B1`):** Evaluating `registration-manifest.json` at `P1` (union `C`), evaluating `legacy-write-records.json` and `shared-surface-changes.json` at `C`, enforcing Rule 0 monotonicity across every `P1 -> C` step, and verifying `<baseline>` lies on `<head>`'s first-parent chain prevents a single commit from deleting a manifest entry and editing the file, prevents post-L-1 registrations from flagging pre-registration commits, and prevents a later commit from blessing an earlier unrecorded write. See §6.1, §6.2.2, and §6.5.
3. **Manifest fields and `require_registered` compatibility (`R1-M4`, `R1-M5`, `R1-m10`):** Carrying `"role"` and `"source_identity_kind"` alongside `"root_kind"`, `"root_id"`, and `"normalized_path"` in `registration-manifest.json` (projected from `state["records"]["legacy_path_registration"]` via `_legacy_projection` in `research_system/cli.py:1648-1659`), while updating `require_registered` (`research_system/legacy/evidence.py:124-130`) to compare membership on the 3 identity keys (and verify `role` and `source_identity_kind` when present), gives the detector the exact fields it needs without breaking `LR-015` or existing 3-key WP9.3 test fixtures. See §5.3 and Owner Point A (§16).
4. **Rule 1 matching and exclusions (`R1-M4`, `R1-M5`):** Excluding `root_kind != "repository_root"`, `source_identity_kind != "git_tracked"`, and `role in {"conventions_lock", "shared_enforcement_surface", "successor_results_root", "legacy_read_only_projection"}` from Rule 1 and from §6.6's `git cat-file` check ensures the detector never misfires on untracked/restricted files (`*.csv`, `*.pkl`, stage logs, `.apm/bus/`, projections), `results/ars/` before it exists in Git, or `CONVENTIONS.md` successor insertions. See §6.5 (Rule 1) and §6.6.
5. **`.apm/tracker.md` Working Notes handling (`R1-M5`):** Because routine worktree sweeps (`#368` `452352ff`, `#388` `e3519ba7`, `#433` `a6a98966`) append entries under `## Working Notes` in `.apm/tracker.md`, Owner Point H (Option H1) mechanically verifies via `segment(raw, "tracker_task_row")` and `segment(raw, "working_note_entry")` (`research_system/legacy/segmentation.py:470-473`) that a tracker change in a merged PR is a pure Working-Note append with zero task-row or preamble byte changes. See §6.5 (Rule 1) and Owner Point H (§16).
6. **W9 §4.2 record keying and pre-existing provenance at `P1` (`06v:486`; `R1-B1`, `R1-M10`):** Keying `.research-system/evidence/w9/legacy-write-records.json` by `(pr_number, normalized_path, old_blob, new_blob)` allows a PR to carry its own record at `C` without knowing its squash SHA, while requiring `owner_note.source_commit` and `independent_review.review_commit` to be ancestors of `P1` prevents a PR author from self-authoring an owner ruling or review in the same PR. See §6.4 and Owner Points B and I (§16).
7. **Two-parent merge commits and explicit `<P1> <C>` arguments to `git diff-tree`:** Single-argument `git diff-tree -r <C>` prints nothing on a 2-parent merge commit (verified on `b132406e`); passing `git --no-replace-objects diff-tree -r --no-renames -z <P1> <C>` extracts the exact first-parent tree delta on `main` for both 1-parent and 2-parent commits, and mode-only changes (`old_blob == new_blob`, `old_mode != new_mode`) fail closed. See §6.3.
8. **PR mapping, retry/hint fallback, and genealogy of `5df0c001` and `811d5a2b` (`R1-M3`, `R1-m5`, `R1-m6`):** Requiring `pull["merge_commit_sha"] == C` on `commits/<C>/pulls` (with 3-try backoff and `pulls/<N>` subject-hint fallback still verified by `merge_commit_sha == C`, exiting `2` on API failure and rejecting `--pr-map`/`--manifest-file` unless `--ruleset-check skip`) maps squash and merge PRs accurately while mapping `5df0c001` (`2026-08-05`, 1 parent `a426b731`, reusing `#215`'s merge subject, touching 7 `results/` files + 4 non-`results/` files) and `811d5a2b` (`2026-08-07`, 1 parent `1d3a0769`, touching 3 `contracts/manifests/input-provenance/` files + 6 other files) to `pr_number = None`. See §6.2.1 and §6.3.
9. **Resolving the `O-32` squash-merge SHA contradiction via blob-keyed tree-state freshness (`R1-M6`):** Option D3 keys `shared-surface-changes.json` entries by `{"pr_number", "surface", "old_blob", "new_blob", "affected_registrations"}` (no commit SHA) and checks in `acceptance.py:check_change_list` that `evidence.blob_at(repository_root, obs_commit, surface)` (`evidence.py:179-188`) equals `new_blob` (or a later entry's `new_blob` for `surface`), avoiding both the unknowable squash SHA (`06v:90-91`) and the stale-`base_commit` merge-queue race of D1. Because it modifies accepted WP9.3 gate code in `evidence.py` and `acceptance.py`, it requires a dated WP9.3 amendment and independent review. See §6.5 (Rule 3) and Owner Point D (§16).
10. **Ruleset `20822054` pinning, 30-day rule-suites ceiling, and runnable U-3 draft-PR probe (`R1-M11`, `R1-m1`, `R1-m2`):** The ruleset read pins `allowed_merge_methods: ["squash"]`, `merge_queue: {merge_method: "SQUASH", max_entries_to_merge: 1}`, `require_code_owner_review: true`, `strict_required_status_checks_policy: true`, the 4 required contexts, and `bypass_actors`, fails closed if the previous read is >30 days old, and tests `GITHUB_TOKEN` permissions (`contents: read` and `pull-requests: read`) via a throwaway draft-PR `pull_request` workflow before code dispatch. See §4.1 and §4.2.
11. **Vault root junction refusal vs `open_registered_root_anchor` (`R1-M2`, `R1-m8`):** Because `open_registered_root_anchor` (`research_system/store/anchor.py:1934-1950`) sets `reject_reparse=False` and `LegacyReader.__init__` (`reader.py:241-248`) checks `os.path.abspath` lexically, `tools/check_legacy_log_baseline.py` explicitly rejects `vault_root.is_symlink() or vault_root.is_junction()` and requires `os.path.normcase(str(vault_root.resolve(strict=True))) == os.path.normcase(str(vault_root))` outside `repository_root` before calling `handle_bound_read`. See §4.3.1 and §4.3.2.
12. **`CONVENTIONS.md` unit counts, table filter, and L-0b classification input (`R1-M3`, `R1-M9`, `R1-m11`):** At `4b143c92` (`4620c716`), `CONVENTIONS.md` has 70 `conventions_unit` items across 10 sections (`68` in the 9 non-governance sections + `2` in `ARS Foundation Governance`); at `dbd54fe3`, it has 90 units across 11 sections (`7` inserted in `Computational Environment`, `7` in `ARS Foundation Governance`, `6` in `Repo-Wide CI`), with all 70 baseline units preserved in order; inserted tables (`|...`) in legacy sections are rejected, and an optional `--classified-locks` input accommodates L-0b's accepted classification. See §7.3, §7.4, and Owner Point J (§16).
13. **Vault Computational-Log classification source and CRLF-successor resilience (`R1-M1`, `R1-M2`, `R1-M9`, `R1-m8`):** `tools/check_legacy_log_baseline.py` reads `ACCEPTED_CL_EXPORT[-1]`'s three descriptors (`export`, `retained_copy`, `classified_list`, `accepted_w9.py:86-88`), validates `export` with `require_cl_export(export)` (`evidence.py:277-362`) and `recheck_cl_export(export, retained_raw)` (`export_recheck.py:32-89`), reads legacy/successor classifications from `classified_list` (`w9-cl-classified-list/1`), and checks legacy rows by `raw_row_sha256` without failing if a prepended successor entry introduces CRLF line endings outside legacy rows. See §8.2, §8.3, and Owner Point J (§16).
14. **D-5 cadence gate at batch start (`LR-003`/`LR-015`) as well as `LR-016`/`LR-020` (`R1-M8`):** Gating on `bool(reader.accepted_cl_export)` (never on "file present") at `LR-003`, `LR-015`, `LR-016`, and `LR-020` blocks the next batch at batch start when a weekly run is missed, while `"kind": "owner_cadence_reset"` prevents one missed run from permanently bricking the store. See §8.4 and Owner Point E (§16).
15. **Deterministic, tool-blob-bound control output hashes (`R1-m4`):** Binding each detector tool's `git_blob_id` and `CONTROL_GIT_ENV` into `w9-control-transcript/1` makes `output_sha256` reproducible and verifiable via `run_w9_detector_controls.py --verify-watched-to-fail`. See §9.2.
16. **PR-lane execution of `tests/tools/test_w9_detectors.py` and the `L1_LIVE` tripwire (`R1-M7`):** Wiring `tests/tools/test_w9_detectors.py` into `.github/workflows/ci.yml`'s `admission-controls` job (`ci.yml:166-216`) and `ADMISSION_CONTROL_MODULES` (`test_ci_platform_policy.py:175-229`)—merged by Stephen under `.github/CODEOWNERS:18` (`@stephendor`)—ensures the `L1_LIVE = False` tripwire and detector unit controls actually execute on every PR. See §2.3, §10.3, and Owner Point F (§16).

---

## 15. Stop rules for the code package

In addition to `06v` §8 (`06v-w9-implementation-plan.md:610-620`), the WP9.5 code package is bound by the following hard preconditions and runtime stop rules:

### 15.1 Hard preconditions before WP9.5 code is dispatched (`P-089` item 3, `03-decisions-and-open-questions.md:6104-6115`)

WP9.5 implementation code **must not** be dispatched until all three of the following are complete:

1. **U-3 recorded in §4.2.2 of this note (`06v:159`; `P-089` item 3, `03-decisions-and-open-questions.md:6105-6107`):**
   Stephen authorizes the read-only U-3 throwaway draft-PR probe (§4.2.2); the reviewing session executes it and records the exact HTTP status codes and `X-Accepted-GitHub-Permissions` headers for `GET repos/ZK-Theory/TDL/rulesets/20822054`, `GET repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=day&per_page=5`, and `GET repos/ZK-Theory/TDL/commits/dbd54fe382e7b2849d3f2038393cbdb4d709477b/pulls` under `GITHUB_TOKEN` (`contents: read` and `pull-requests: read`) in the §4.2.2 table of this note, stating whether D-8 applies to `rule-suites`.
2. **U-4 handle-bound reader and segmenter dry run recorded in §4.3.3 of this note (`06v:160`; `P-089` items 3 & 4, `03-decisions-and-open-questions.md:6105-6107,6116-6117`; `R1-m8`):**
   The live U-4 metadata read (`2026-11-21T21:06:44Z`, `833,453` bytes, SHA-256 `73fcbe83...`) is already recorded in §4.3.3. Before WP9.5 code is dispatched, the reviewing session executes the read-only Python dry-run one-liner in §4.3.3 item 2 (which runs `handle_bound_read` and `segment(raw, "computational_log_entry")` on `C:\Users\steph\Documents\TDA-Research\04-Methods\Computational-Log.md` and prints only `bytes`, `sha256`, `link_count`, `canonical_target`, `file_facts`, `row_counts`, and `blockers`) and records the result in §4.3.3.
3. **Owner Points A through J decided by Stephen in a decision-register entry (`P-090`):**
   Stephen records his disposition on Owner Points A through J (§16) in `docs/plans/agentic-research-system/03-decisions-and-open-questions.md` (and, if Option D3/D1 or Option E1 is chosen, authorizes the dated WP9.3 amendment and paths-addendum rows).

### 15.2 Stop rules during WP9.5 code implementation

The WP9.5 code worker must stop immediately and return `PARTIAL` if:
1. Any change would modify a protected identity listed in §2.2 (the 275-row runtime-binding census, `wp6_1_06h_current_append_manifest.yaml` blob `1066404a`, `test_wp6_1_06h_append_path_closure.py` blob `3b1eec6e`, `research_system/schema_registry.py` blob `e32cb408`, `research_system/authority.py` blob `9b56b322`, core/W9 schemas, T2 expectations/seal, `tools/w9_segmentation.py` blob `43e1454de09b61e274954c42b21d6ae533857a24`, or `IMPORTER_MODULES` in `research_system/legacy/reader.py:42`) (`06v:614,618-619`).
2. Any change under `research_system/legacy/` would exceed the specific changes approved by Stephen under Owner Points A, D, E, and J.
3. Any test or negative control needs live legacy, vault, or restricted bytes, or writes to / leaves any state in `REPO_ROOT`, any linked worktree, or `C:\Users\steph\Documents\TDA-Research` (`06v:616-617`).
4. The new and changed WP9.5 test files (including `@pytest.mark.slow` tests) exceed the approved serial `--no-cov` test-time budget (Owner Point G) on Stephen's machine (`P-087` item 7, `03-decisions-and-open-questions.md:5919-5923`).
5. *(WP9.5-specific stop rule added by this design note, not in `06v` §8 (`R1-m13`)):* Any detector negative control fails to fire on its designated violation case or fires on a clean positive control case.

---

## 16. Owner points

Stephen's decision is requested on the following ten points (**A** through **J**) before WP9.5 code is dispatched. Nothing in this note decides them for him.

| ID | Decision needed | Options | Recommendation | What it changes in accepted code or documents |
|---|---|---|---|---|
| **A** | **Carrying `"role"` and `"source_identity_kind"` in `.research-system/evidence/w9/registration-manifest.json`** (`R1-M4`, `R1-M5`, `R1-m10`; §5.3, §6.5, §6.6). | **Option A1:** Project the 5 keys `{"root_kind", "root_id", "normalized_path", "role", "source_identity_kind"}` from `state["records"]["legacy_path_registration"]` into each entry of `registration-manifest.json`. In `research_system/legacy/evidence.py:114-131` (`require_registered`), accept both 5-key entries (and 3-key entries for existing WP9.3 test fixtures), verify `(role, source_identity_kind)` when present, and compare membership at line 129 on the 3 identity keys `("root_kind", "root_id", "normalized_path")`.<br>**Option A2:** Keep `registration-manifest.json` strictly at 3 keys (`evidence.py:125` untouched) and commit a companion file in `.research-system/evidence/w9/` mapping `(root_kind, root_id, normalized_path)` to `(role, source_identity_kind)`. | **Option A1.** Both `role` and `source_identity_kind` are already required fields on every `legacy-path-registration` record (`.research-system/schemas/contracts/w9/legacy-path-registration.schema.json:70-94`), and Option A2 has no store-preparer enforcement keeping the second file synchronized with `registration-manifest.json`. | **Option A1:** Updates `require_registered` in `research_system/legacy/evidence.py:114-131` (not in `IMPORTER_MODULES`, so `tool_sha256` is unchanged) and `tests/research_system/unit/test_w9_evidence.py`.<br>**Option A2:** Adds a dated row to `06v-addendum-2026-11-10-w9-paths.md`. |
| **B** | **Location, in-commit (`at C`) evaluation, and pre-existing (`at P1`) provenance of W9 §4.2 write-allowance records** (`R1-B1`, `R1-M10`; §6.4). | **Option B1:** Commit `.research-system/evidence/w9/legacy-write-records.json` (`format: "w9-legacy-write-records/1"`, §6.4), keyed by `(pr_number, normalized_path, old_blob, new_blob)`. Evaluated **at commit `C`** (`<C>:.research-system/evidence/w9/legacy-write-records.json`) so the PR carries its own record (`06v:486`), with `owner_note.source_commit` (citing a `### P-0xx` register entry) and `independent_review.review_commit` required to be ancestors of **`P1`** (committed on `main` before PR `C` merges), and governed by Rule 0 (append-only, only for `pr_number(C)`).<br>**Option B2:** Same as B1, except allow `owner_note` or `independent_review` to be committed inside `C` itself rather than at `P1`, relying on `.github/CODEOWNERS` (`@stephendor`) under Owner Point I to prevent self-approval.<br>**Option B3:** Parse §4.2 allowance metadata out of GitHub PR bodies/comments via `gh api` without a committed file in `.research-system/evidence/w9/`. | **Option B1** (combined with CODEOWNERS in Owner Point I). It is offline-testable in scratch clones, prevents retroactive blessing after `C`, and prevents a PR author from fabricating a self-authored owner note and review in the same PR. | **Option B1 / B2:** Adds a dated row for `.research-system/evidence/w9/legacy-write-records.json` in `docs/plans/agentic-research-system/implementation/06v-addendum-2026-11-10-w9-paths.md` (`06v-addendum-2026-11-10-w9-paths.md:14-15`). Loader lives in `tools/_w9_detector_evidence.py` (`research_system/legacy/` untouched). |
| **C** | **Committed append-only walk-baseline record (`walk-baseline.json`) and disposition of the 20 post-freeze first-parent commits (`4b143c92..dbd54fe3`)** (`R1-B1`, `R1-M3`, `R1-M12`; §6.2). | **Option C1:** Commit `.research-system/evidence/w9/walk-baseline.json` (`format: "w9-walk-baseline/1"`, §6.2.2), governed by Rule 0 (append-only) and checked to lie on `<head>`'s first-parent chain. At L-1 activation, pin `baselines[0]["baseline_commit"]` to the L-1 parent commit on `main` (at or after `dbd54fe38`), recording the §6.2.1 table as the explicit pre-L-1 disposition of all 20 first-parent guarded-prefix commits between `4b143c92` and `dbd54fe3` (including post-G7-A commits `#388` `e3519ba7`, `#401` `633ed58e`, and `#433` `a6a98966`). W9-T7 passes `--baseline` (under `--ruleset-check skip`) to replay `5df0c001` and `811d5a2b` in the scratch clone.<br>**Option C2:** Set `baselines[0]["baseline_commit"]` in `walk-baseline.json` to the freeze commit `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (`2026-07-18`), and seed historical pre-L-1 disposition entries for the 20 first-parent commits in §6.2.1 (including the `5df0c001` + `b132406e` and `811d5a2b` + `b132406e` revert pairs, `#125` `02ebcaf6`, `#129` `5795a18b`, `#168` `9016b663`, `#169` `2111ce62`, `#277` `1dbf6b7b`, `#334` `eba3fe69`, `#368` `452352ff`, `#388` `e3519ba7`, `#401` `633ed58e`, `#433` `a6a98966`, and the 8 `CONVENTIONS.md` successor-insertion PRs). | **Option C1.** Under time-indexed evidence (§6.1), starting the live walk at the L-1 activation commit (with `walk-baseline.json` append-only and checked on `<head>`'s first-parent chain, and all 20 pre-L-1 commits explicitly disposed in §6.2.1) avoids embedding a historical exemption mechanism in the live detector that would otherwise have to exempt `5df0c001` and `811d5a2b` on `main`. | **Option C1 / C2:** Adds a dated row for `.research-system/evidence/w9/walk-baseline.json` in `docs/plans/agentic-research-system/implementation/06v-addendum-2026-11-10-w9-paths.md`. Loader lives in `tools/_w9_detector_evidence.py` (`research_system/legacy/` untouched). |
| **D** | **Resolving the `O-32` squash-merge SHA contradiction in `.research-system/evidence/w9/shared-surface-changes.json`** between `06v:90-91,212,479-481` and `research_system/legacy/evidence.py:231-238` + `acceptance.py:135` (`R1-M6`; §6.5). | **Option D3 (Blob-keyed, tree-state freshness, no commit field — Recommended):** Each entry in `shared-surface-changes.json` is `{"pr_number", "surface", "old_blob", "new_blob", "affected_registrations"}` (format `"w9-shared-surface-changes/2"`, or tagged union in `"w9-shared-surface-changes/1"` keeping `merge_commit` entries valid for existing WP9.3 unit fixtures). The PR changing a shared surface carries its own entry at `C`; Rule 3 matches `(pr_number, surface, old_blob, new_blob)` at `C`. In `research_system/legacy/acceptance.py:121-136` (`check_change_list`), an affected item's observation at `obs_commit = str(source.get("git_commit"))` is fresh iff `evidence.blob_at(repository_root, obs_commit, entry["surface"])` (`evidence.py:179-188`) equals `entry["new_blob"]` (or the `new_blob` of a later entry for the same `surface` in `entries`).<br>**Option D1 (Base-commit + blob check):** Entry carries `{"pr_number", "base_commit", "surface", "old_blob", "new_blob", "affected_registrations"}`. *(Unsound as a commit-ancestry test because `main` can advance in the merge queue after `base_commit`; only the `blob_at == new_blob` part is sound, making `base_commit` redundant with D3.)*<br>**Option D2 (Two-PR protocol, keeping `evidence.py:231` and `acceptance.py:135` unchanged):** The shared-surface PR carries the W9 §4.3 owner note in `legacy-write-records.json` at `C`, and a follow-up PR records the squash `merge_commit` in `shared-surface-changes.json`. *(Leaves the detector red between the two PRs and leaves the acceptance preparer unaware of the missing entry during that window.)* | **Option D3.** It has no unknowable squash SHA (`06v:90-91`), no history walk, no reflexive-ancestor or stale-`base_commit` merge-queue race, uses `evidence.blob_at` (`evidence.py:179-188`) which already exists, and lets the shared-surface PR carry its own entry atomically at `C` (`06v:212,479-481`). | **Option D3 (or D1):** Modifies `research_system/legacy/evidence.py:42,190-252` (`_change_entries` and `require_change_list` docstring), `research_system/legacy/acceptance.py:121-136` (`check_change_list`), WP9.3 unit tests (`tests/research_system/unit/test_w9_evidence.py`), and `06v-addendum-2026-11-10-w9-paths.md:28`. Because `check_change_list` is an accepted WP9.3 gate at `LR-016`/`LR-020` (not merely a WP9.5 reader), it requires a **dated WP9.3 amendment (`wp9-3-design-note.md` §10.4), an independent review, and a decision-register entry**. (`IMPORTER_MODULES` is untouched.) |
| **E** | **Enforcing D-5 ("a missed weekly vault-detector run blocks the next batch", `06v:567`): gate placement, reset, and weekly PR + `advance-binding` cost** (`R1-M8`; §8.4). | **Option E1 (Store-preparer gate at batch start `LR-003`/`LR-015` and batch acceptance `LR-016`/`LR-020`):** Commit `.research-system/evidence/w9/vault-detector-runs.json` (`format: "w9-vault-detector-runs/1"`, §8.4, with `"kind": "run"` and `"kind": "owner_cadence_reset"` entries). When `bool(reader.accepted_cl_export)` is `True` (never gated on "file present"), enforce `require_vault_detector_cadence` at **`LR-003`** (`prepare_proposal`, `research_system/legacy/preparers.py:686-690`), **`LR-015`** (`prepare_observation`, `preparers.py:1215-1218`), **`LR-016`**, and **`LR-020`** (`check_environment`, `research_system/legacy/acceptance.py:147-152`), as well as in `tools/check_legacy_log_baseline.py --check-cadence`. Each weekly run requires a reviewed PR to `main` and an `ars store advance-binding` before store commands run.<br>**Option E2 (CLI pre-batch check tool only, leaving `preparers.py` and `acceptance.py` untouched):** Enforce the 7-day cadence and `"owner_cadence_reset"` rule on `.research-system/evidence/w9/vault-detector-runs.json` in `tools/check_legacy_log_baseline.py --check-cadence` (run on the `06v:604` pre-batch checklist), acknowledging that without Option E1 the block is a pre-batch CLI checklist gate rather than an in-store preparer gate. | **Option E1** if Stephen accepts the weekly PR + `advance-binding` cost and a dated WP9.3 amendment for hooking `LR-003`/`LR-015`/`LR-016`/`LR-020`; **Option E2** if keeping `research_system/legacy/preparers.py` and `acceptance.py` untouched is preferred. Recommend **Option E1** so "a missed run blocks the next batch" (`06v:567`) is machine-enforced at batch start (`LR-003`/`LR-015`). | **Option E1:** Adds `VAULT_DETECTOR_RUNS` and `require_vault_detector_cadence` in `research_system/legacy/evidence.py`, calls it in `research_system/legacy/preparers.py:686-690,1215-1218` and `research_system/legacy/acceptance.py:147-152`, adds a dated row to `06v-addendum-2026-11-10-w9-paths.md`, and requires a **dated WP9.3 amendment and independent review**.<br>**Option E2:** Adds a dated row to `06v-addendum-2026-11-10-w9-paths.md`; `research_system/legacy/` is untouched. |
| **F** | **Running `tests/tools/test_w9_detectors.py` (including the `L1_LIVE` tripwire) in a real PR lane vs `.github/CODEOWNERS`** (`R1-M7`; §2.3, §10.3). | **Option F1 (Wire into `.github/workflows/ci.yml` `admission-controls` — Recommended):** Add `tests/tools/test_w9_detectors.py` to `.github/workflows/ci.yml`'s `admission-controls` job (`ci.yml:166-216`) and to `ADMISSION_CONTROL_MODULES` in `tests/tools/test_ci_platform_policy.py:175-229` (following the exact precedent of `tests/tools/test_w9_segmentation.py` at `ci.yml:210` and `test_ci_platform_policy.py:226`), with `L1_LIVE = False` in `test_w9_detectors.py` flipped to `True` in the L-1 activation PR. Because `.github/workflows/ci.yml` is owned by `@stephendor` in `.github/CODEOWNERS:18` and `.claude/hooks/admin-bypass-guard.sh:13-18,67-68` forbids any agent bypass, **Stephen merges the WP9.5 PR himself under its code owner**.<br>**Option F2 (Reference in `legacy-write-detector.yml` only, leaving `ci.yml` untouched):** Name `tests/tools/test_w9_detectors.py` only in `.github/workflows/legacy-write-detector.yml`. *(Nominal compliance only: `legacy-write-detector.yml` is `workflow_dispatch`-only until L-1, so `test_w9_detectors.py` and the `L1_LIVE` tripwire would run in **no PR lane**!)* | **Option F1.** It is the only option that executes WP9.5's detector unit controls and the `L1_LIVE = False` inactivity tripwire on every pull request and merge-group evaluation. | **Option F1:** Edits `.github/workflows/ci.yml:212` (owned by `@stephendor` in `.github/CODEOWNERS:18`, requiring Stephen's own merge) and `tests/tools/test_ci_platform_policy.py:228` (not in `.github/CODEOWNERS`). |
| **G** | **Test-time budget for WP9.5 (including `@pytest.mark.slow` tests)** (`R1-m14`; §12.3). | **Option G1:** Apply the **5-minute (300-second)** serial `--no-cov` budget established for WP9.4-2 in `P-087` item 7 (`03-decisions-and-open-questions.md:5919-5923`), explicitly counting all new and changed WP9.5 tests (including `@pytest.mark.slow` tests in `test_w9_wp9_5_detectors.py`), with over-budget returning `PARTIAL` with measurements.<br>**Option G2:** Tighten the WP9.5 ceiling to **2 minutes (120 seconds)** serial `--no-cov` (all tests, including `slow`), based on the measured `1.77s` bare-clone time in §12.3. | **Option G2 (2 minutes / 120 seconds)** (or **Option G1, 5 minutes**, if Stephen prefers a uniform package budget across W9). Either way, all tests including `slow` count toward the budget and one slow test is profiled alone before adding a scratch-store flow (`P-087` item 7). | Recorded in the WP9.5 authorization register entry (`P-090`); changes no existing code or document. |
| **H** | **Handling routine `.apm/tracker.md` Working-Note appends after `.apm/tracker.md` is registered** (`R1-M5`; §6.2.1, §6.5 Rule 1). | **Option H1 (Mechanically verified Working-Note append allowance — Recommended):** Add a dated W9 §4.2 amendment permitting a merged PR (`merge_commit_sha == C`) to modify `.apm/tracker.md` without a §4.2(b) record **if and only if** `tools/check_legacy_writes.py` verifies via `segment(raw, "tracker_task_row")` and `segment(raw, "working_note_entry")` (`research_system/legacy/segmentation.py:470-473`) that (i) every `tracker_task_row`, the preamble, and every byte outside `## Working Notes` is byte-identical between `P1` and `C`, and (ii) every `working_note_entry` at `P1` is preserved byte-for-byte and in order at `C` with 0 blockers (pure append of new working note(s)). Note: under `O-33` (`06v:213`), any blob change to `.apm/tracker.md` during an open observation/acceptance window for `.apm/tracker.md` itself still blocks that open window until re-observed.<br>**Option H2 (Require a full W9 §4.2(b) owner note + independent review record in `legacy-write-records.json` for every `.apm/tracker.md` Working-Note PR):** No W9 amendment; every worktree-sweep tracker PR (`#368`, `#388`, `#433` pattern) must carry a `legacy-write-records.json` entry with a pre-existing register entry and review.<br>**Option H3 (Freeze `.apm/tracker.md` completely at L-1 and move successor worktree-sweep notes to an ARS-owned file outside `.apm/tracker.md`):** No further writes to `.apm/tracker.md` after L-1. | **Option H1** (or **Option H3** if Stephen prefers stopping all `.apm/tracker.md` appends at L-1). Option H1 uses the already-built and tested `tracker_task_row` and `working_note_entry` segmenters (`research_system/legacy/segmentation.py:470-473`) so routine worktree-sweep Working Notes do not force a §4.2(b) ceremony or train operators to ignore a red detector. | **Option H1:** Requires a dated W9 §4.2 amendment (recorded in `03-decisions-and-open-questions.md` `P-090` and `09-migration-compatibility-and-pilot.md` §4.2); implemented inside `tools/check_legacy_writes.py` (`research_system/legacy/` untouched).<br>**Option H2 / H3:** No W9 amendment. |
| **I** | **Protecting the detector surface and `.research-system/evidence/w9/` against self-editing: Rule 0, `.github/CODEOWNERS` + `GATE_FILES`, or both** (`R1-B1`, `R1-M7`, `R1-M10`; §2.3, §6.4, §6.5 Rule 0). | **Option I1 (Both Rule 0 and `.github/CODEOWNERS` + `GATE_FILES` — Recommended):** Enforce Rule 0 monotonicity in `tools/check_legacy_writes.py` (§6.5) **and** add `.github/workflows/legacy-write-detector.yml`, the WP9.5 detector tools (`tools/check_legacy_writes.py`, `tools/check_conventions_legacy_locks.py`, `tools/check_legacy_log_baseline.py`, `tools/run_w9_detector_controls.py`, `tools/export_w9_registration_manifest.py`, `tools/_w9_detector_evidence.py`), and `.research-system/evidence/w9/` to `.github/CODEOWNERS` (`@stephendor`) and `GATE_FILES` in `tests/tools/test_ci_platform_policy.py:341-350`.<br>**Option I2 (Rule 0 monotonicity + baseline-pinned detector execution only, leaving `.github/CODEOWNERS` and `GATE_FILES` at their current 8 paths):** Rely on Rule 0 (§6.5) and `P1`-anchored `source_commit`/`review_commit` verification (§6.4) without expanding `.github/CODEOWNERS`. | **Option I1.** Because ruleset `20822054` has `required_approving_review_count: 0` and `require_code_owner_review: true` (§4.1), adding the detector tools, workflow, and `.research-system/evidence/w9/` to `.github/CODEOWNERS` (`@stephendor`) makes ruleset `20822054` block any PR that edits a detector or W9 evidence file unless Stephen approves/merges it himself! | **Option I1:** Edits `.github/CODEOWNERS` (owned by `@stephendor`, `.github/CODEOWNERS:14`), `GATE_FILES` in `tests/tools/test_ci_platform_policy.py:341-350`, and `CONVENTIONS.md:721-723` (pure successor update in `## ARS Foundation Governance`, which is wholly successor under `W9:405-407`).<br>**Option I2:** No change to `.github/CODEOWNERS` or `GATE_FILES`. |
| **J** | **Source and format of the legacy/successor classification for the vault Computational-Log detector and the `CONVENTIONS.md` check** (`R1-M9`; §7.3, §8.2, §8.3). | **Option J1 (Dedicated `w9-cl-classified-list/1` format for `ACCEPTED_CL_EXPORT[-1]["classified_list"]`, plus provisional 9-section `CONVENTIONS.md` default with optional `--classified-locks` override — Recommended):**<br>1. For the vault detector: validate `ACCEPTED_CL_EXPORT[-1]["classified_list"]` (`research_system/legacy/accepted_w9.py:86-88`) against the closed `"w9-cl-classified-list/1"` schema in §8.3 (every row ordinal classified as `"legacy"` or `"successor"`, no `null`), while allowing fixture tests to pass `--fixture-classified-list` (or pre-populated `export["classifications"]`).<br>2. For `CONVENTIONS.md`: default to the conservative 9-section (`68`-unit) partition (§7.3) prior to L-0b, and accept an optional `--classified-locks` JSON (`"w9-conventions-classified-locks/1"`) if L-0b reclassifies any individual unit inside the 9 sections.<br>**Option J2 (Carry final `"legacy"` / `"successor"` labels directly inside `export["classifications"]` of `w9-cl-export/1` at L-0b):** At L-0b, require `classified_list` in `ACCEPTED_CL_EXPORT` to point to a file whose classifications match `export["classifications"]` with zero `null` slots, and tighten `require_cl_export` at L-0b. | **Option J1.** It matches `ACCEPTED_CL_EXPORT`'s existing 3-member structure (`{"export", "retained_copy", "classified_list"}` in `research_system/legacy/accepted_w9.py:86-88`) and `06v:569,593` (where the raw non-author export is taken first and the classified legacy-entry list is accepted by Stephen second), without modifying WP9.3's `require_cl_export` (`evidence.py:277-362`). | **Option J1:** Implemented in `tools/check_legacy_log_baseline.py` and `tools/check_conventions_legacy_locks.py` (and `tools/_w9_detector_evidence.py`); `research_system/legacy/` is untouched. At L-0b, `ACCEPTED_CL_EXPORT` in `research_system/legacy/accepted_w9.py:88` and row 29 of `06v-addendum-2026-11-10-w9-paths.md` are populated by the L-0b PR. |

---

## 17. Change log

| Revision | Date | Author | Summary |
|---|---|---|---|
| Revision 1 | 2026-11-21 | Gemini agent (under `P-089`) | Initial draft of the WP9.5 design note (`65363e27`) for independent adversarial review. |
| Revision 2 | 2026-11-21 | Gemini agent (under `P-089`) | Complete rework addressing all findings (`R1-B1`, `R1-M1`–`R1-M12`, `R1-m1`–`R1-m14`, `R1-i1`–`R1-i6`, and all §2 citation corrections) from `docs/plans/agentic-research-system/reviews/wp9-5-note-r1-review-2026-11-21.md` (`edb9acc6`). |

---

## 18. Change log: revision 1 to revision 2

Every finding in `docs/plans/agentic-research-system/reviews/wp9-5-note-r1-review-2026-11-21.md` (`edb9acc6`) is disposed of below:

| Finding ID | Severity | What changed in revision 2 and where |
|---|---|---|
| **R1-B1** | Blocking | **Adopted in full (§6.1, §6.2.2, §6.4, §6.5, §10.2, §12.1, §16 B/C/I).** Time-indexed all evidence reads: Rules 1 and 3 evaluate against `registration-manifest.json` at `P1` (union `C`, preventing atomic disarm and eliminating retroactive false positives on pre-registration commits); `legacy-write-records.json` and `shared-surface-changes.json` are read at `C` (so the PR carries its own record and no later commit can retroactively bless `C`). Added **Rule 0** (monotonicity of `registration-manifest.json`, `legacy-write-records.json`, `shared-surface-changes.json`, `walk-baseline.json`, `vault-detector-runs.json`, `detector-controls.json`, detector tools, and workflow). Replaced the in-script baseline constant with `.research-system/evidence/w9/walk-baseline.json` (`w9-walk-baseline/1`, append-only, verified to lie on `<head>`'s first-parent chain) and pinned detector tool blobs to `<baseline>`. |
| **R1-M1** | Major | **Adopted in full (§4.3.1, §4.3.3, §8.2, §8.4, §18).** Deleted the fabricated `376,784`-byte / `4c1898aa...` / line 541–545 blocker figures and the stray `"Wait:"` paragraph. Replaced §4.3.1 and §4.3.3 with the verified WP9.2 contract census figures from `w9-segmentation-contract-v1.md:242,254-258` (`700,632` bytes / `de44a67b...` / 255 entries / 1 structural / 0 blockers, and `703,531` bytes / `19ad5c4d...` / 256 entries / 1 structural / 0 blockers, explicitly labeled as grammar census evidence, not a baseline) and the live U-4 metadata read from `2026-11-21T21:06:44Z` (`833,453` bytes, SHA-256 `73fcbe83...`). |
| **R1-M2** | Major | **Adopted in full (§2.1, §2.2, §2.3, §4.3.1, §4.3.2, §5.3, §7.2, §8.2, §8.3, §9.2).** Removed every nonexistent symbol (`_is_reparse_or_symlink`, `FILE_ATTRIBUTE_REPARSE_POINT`, `_is_within`, `LegacyReplayEngine`, `state["store_binding"]`, `research_system/core/canonical.py`, `segment_bytes(profile=...)`, `AcceptedClExport`, `export["region"]["kind"]`). Re-derived all mechanisms against the actual code at `dbd54fe38`: `open_registered_root_anchor` (`research_system/store/anchor.py:1934-1950`, `reject_reparse=False`), `handle_bound_read` and `LegacyReader.__init__` (`research_system/legacy/reader.py:140-206,241-248`), `_legacy_projection` (`research_system/cli.py:1648-1659`) calling `replay_legacy` (`research_system/legacy/replay/driver.py:147`), `_legacy_current_binding` (`cli.py:1662-1684`) calling `load_current_binding` (`research_system/store/current_binding.py:801`) with `binding.binding["git_head"]` (`cli.py:1714`), `canonical_bytes` (`research_system/canonical.py:40-48`), `segment(data, selector_kind, ...)` (`research_system/legacy/segmentation.py:429-488`), `require_cl_export(export)` (`research_system/legacy/evidence.py:277-362`), `ACCEPTED_CL_EXPORT` (`research_system/legacy/accepted_w9.py:86-88`), `prepare_proposal` (`research_system/legacy/preparers.py:676,686-690`), `prepare_observation` (`preparers.py:1200,1215-1218`), and `CL_EXPORT_PRODUCER` (`evidence.py:52-54`). Placed detector-only evidence loaders in `tools/_w9_detector_evidence.py` (**new**) and named every option that touches `research_system/legacy/` in §2.3 and §16. |
| **R1-M3** | Major | **Adopted in full (§6.2.1, §6.5, §7.3, §7.5, §11.2, §12.1, §16 C, Appendix A §19.1).** Verified and corrected all commit dates, parent counts, PR numbers, and file lists via `git` in the worktree (`verify_r2.py` and `verify_more.py` in Appendix A §19.1): `811d5a2b` (`2026-08-07T00:12:09+01:00`, 9 files total: 3 `contracts/manifests/input-provenance/` + 6 others), `b132406e` (`#219`, `2026-08-08T22:23:06+01:00`), `5df0c001` (`2026-08-05T05:32:38+01:00`, 11 files total: 7 `results/` files across `panel_methodology/bhps_nonoverlap/`, `trajectory_tda_bhps/`, and `trajectory_tda_integration/` + 4 non-`results/` files), `#125` `02ebcaf6`, `#129` `5795a18b` (second parent `1af52f6d`), `#168` `9016b663`, `#169` `2111ce62`, `#277` `1dbf6b7b`, `#334` `eba3fe69`, `#368` `452352ff`, `#387` `3fa437a1`, `#388` `e3519ba7`, `#401` `633ed58e`, `#433` `a6a98966`. Corrected `CONVENTIONS.md` per-section counts at `dbd54fe3` (`Always` 24->24, `Never` 13->13, `Computational Environment` 8->15, `inserted_successor_units_in_legacy_sections: 7`, total units `90`). Replaced nonexistent contract examples with real tracked paths (`contracts/manifests/research-assurance.yaml`, `contracts/stochastic-tests/monte-carlo-permutation-p-value.yaml`, etc.). W9-T7 now derives its 10 fixture paths via `git diff-tree`. |
| **R1-M4** | Major | **Adopted in full (§5.3, §6.5 Rule 1, §6.6 item 2, §16 A).** Widened Owner Point A (Option A1) so `registration-manifest.json` carries both `"role"` and `"source_identity_kind"`. Restricted Rule 1 and §6.6's `git cat-file` check to `root_kind == "repository_root"` and `source_identity_kind == "git_tracked"`, explicitly excluding `untracked_file`, `restricted_untracked_file`, `vault_root`, `successor_results_root` (`results/ars/`), and `legacy_read_only_projection` (`.research-system/projections/legacy/`). |
| **R1-M5** | Major | **Adopted in full (§6.5 Rule 1, §7.1, §16 H).** Excluded `role == "conventions_lock"` (`CONVENTIONS.md`) from Rule 1 (since `CONVENTIONS.md` is governed by `tools/check_conventions_legacy_locks.py` under W9 §4.4 and §7.3). Added **Owner Point H** for `.apm/tracker.md` Working Notes (recommending Option H1: a dated W9 §4.2 amendment permitting pure Working-Note appends verified mechanically by `segment(raw, "tracker_task_row")` and `segment(raw, "working_note_entry")`). |
| **R1-M6** | Major | **Adopted in full (§2.3, §6.5 Rule 3, §16 D).** Added **Option D3 (Recommended: blob-keyed `{pr_number, surface, old_blob, new_blob, affected_registrations}`, tree-state freshness via `evidence.blob_at` in `acceptance.py:check_change_list`, no commit field)** alongside D1 and D2. Documented why D1's `base_commit` is unsound under the merge queue and why D2 leaves a red window. Explicitly stated that D3 (or D1) modifies accepted WP9.3 gate code (`evidence.py:_change_entries` and `acceptance.py:check_change_list`) and therefore requires a dated WP9.3 amendment, an independent review, and a decision-register entry. |
| **R1-M7** | Major | **Adopted in full (§2.3, §10.3, §16 F).** Corrected the `.github/CODEOWNERS` list to the exact 8 paths owned by `@stephendor` (`.github/CODEOWNERS:14-24`; `GATE_FILES` in `tests/tools/test_ci_platform_policy.py:341-350`), noting that `test_ci_platform_policy.py` and `check_test_commit_literals.py` are not code-owned and that `tools/affected_research_tests.py:53-56` selects only `research_system/` and `tests/research_system/` imports. Recommended **Option F1** (wiring `tests/tools/test_w9_detectors.py` into `.github/workflows/ci.yml` `admission-controls` and `ADMISSION_CONTROL_MODULES`, merged by Stephen himself under `@stephendor`) and specified the `L1_LIVE = False` constant in `test_w9_detectors.py` flipped to `True` in the L-1 activation PR. |
| **R1-M8** | Major | **Adopted in full (§2.3, §8.4, §13.2 HR-4, §16 E).** Under Option E1, placed the D-5 cadence gate at batch start (`LR-003` in `preparers.py:686-690` and `LR-015` in `preparers.py:1215-1218`) as well as batch acceptance (`LR-016` and `LR-020` in `acceptance.py:147-152`); gated strictly on `bool(reader.accepted_cl_export)` (never on "file present"); added `"kind": "owner_cadence_reset"` in `vault-detector-runs.json` so one missed weekly run blocks the next batch until Stephen resets it rather than bricking the store forever; stated the weekly PR + `ars store advance-binding` cost and the self-attestation limit (`HR-4`). |
| **R1-M9** | Major | **Adopted in full (§7.3, §8.2, §8.3, §16 J).** Defined the closed `"w9-cl-classified-list/1"` format for `ACCEPTED_CL_EXPORT[-1]["classified_list"]` (`research_system/legacy/accepted_w9.py:86-88`), stated that the 9-section (`68`-unit) `CONVENTIONS.md` partition is provisional until L-0b's accepted classification, added `--classified-locks` to `tools/check_conventions_legacy_locks.py`, and added **Owner Point J**. |
| **R1-M10** | Major | **Adopted in full (§6.4, §6.5 Rule 0, §13.2 HR-1/HR-3, §16 B/I).** Required `owner_note.source_commit` (citing a `### P-0xx` register entry) and `independent_review.review_commit` in `legacy-write-records.json` to be ancestors of **`P1`** (pre-existing on `main` before PR `C`), added Rule 0 monotonicity, added **Owner Point I** (adding detector tools, workflow, and `.research-system/evidence/w9/` to `.github/CODEOWNERS` `@stephendor` and `GATE_FILES`), and stated the residual post-merge detection limit in `HR-3`. |
| **R1-M11** | Major | **Adopted in full (§4.2.1, §4.2.2, §10.2).** Replaced the unrunnable `workflow_dispatch` probe with a runnable `on: pull_request:` probe on a throwaway draft PR (`probe/w9-u3-token-read`, closed without merging), added the third call (`GET repos/ZK-Theory/TDL/commits/dbd54fe3.../pulls`) tested under both `permissions: contents: read` and `permissions: contents: read, pull-requests: read`, added `X-Accepted-GitHub-Permissions` logging, declared `permissions: contents: read, pull-requests: read` in `legacy-write-detector.yml`, stated that Call 2 (`rule-suites`) decides D-8, and marked `GITHUB_TOKEN` behavior on `rulesets/20822054` and `commits/<sha>/pulls` as `UNVERIFIED` pending the probe. |
| **R1-M12** | Major | **Adopted in full (§6.2.1, §6.2.2, §16 C, Appendix A §19.1).** Listed all 20 first-parent commits between `4b143c92` and `dbd54fe3` that touched `CONVENTIONS.md`, `results/`, `papers/`, `contracts/`, or `.apm/` (including post-G7-A commits `#388` `e3519ba7`, `#401` `633ed58e`, and `#433` `a6a98966`, plus `#125` `02ebcaf6` and `#129` `5795a18b`), with exact SHAs, dates, parent counts, touched paths, and dispositions. |
| **R1-m1** | Minor | **Adopted in full (§4.2.3).** Quoted both `06v:571` and `P-064` item 8 (`03-decisions-and-open-questions.md:4232-4233`) accurately, restricted D-8's trigger strictly to `rulesets/rule-suites`, and required an owner-accepted `d8_rule_suites_limit_decision_ref` in `walk-baseline.json` before `--ruleset-check ci-d8` is admitted. |
| **R1-m2** | Minor | **Adopted in full (§4.1, §12.1, §13.2 HR-5).** Pinned `allowed_merge_methods: ["squash"]`, `merge_queue: {merge_method: "SQUASH", max_entries_to_build: 1, min_entries_to_merge: 1, max_entries_to_merge: 1}`, `strict_required_status_checks_policy: true`, `required_review_thread_resolution: true`, the 4 required status-check contexts, and `target_include: ["refs/heads/main"]` (from our live `gh api` read). Added the 30-day (`MAX_DAYS = 30`) fail-closed age check on the previous recorded ruleset read. |
| **R1-m3** | Minor | **Adopted in full (§11.3, §12.1).** Replaced plain `git status` with a recursive `os.scandir(..., follow_symlinks=False)` `(relpath, st_size, st_mtime_ns)` snapshot of `.git` plus `git --no-optional-locks --no-replace-objects status --porcelain=v1 --ignored -z` and `rev-parse HEAD`, and pinned `cwd=tmp_path` and `GIT_DIR` in every detector test invocation. |
| **R1-m4** | Minor | **Adopted in full (§9.2, §10.3, §12.1).** Bound each detector tool's `git_blob_id` into `w9-control-transcript/1`, pinned `CONTROL_GIT_ENV` (`GIT_AUTHOR_DATE`, `GIT_COMMITTER_DATE`, etc.) for all synthetic commits so `<C>` SHAs are deterministic, and added `run_w9_detector_controls.py --verify-watched-to-fail` to re-run and compare the 3 `watched_to_fail` hashes in CI after L-1. |
| **R1-m5** | Minor | **Adopted in full (§6.3 item 3, §6.6 item 3, §12.1).** Added 3-try exponential backoff (`1s, 2s, 4s`) on empty `commits/<C>/pulls`, added `pulls/<N>` subject-hint fallback verified by `merge_commit_sha == C`, and separated GitHub API/transport errors (exit `2`) from unmapped commits (exit `1`). |
| **R1-m6** | Minor | **Adopted in full (§6.3 item 3.4, §10.2, §12.1).** Hard-locked `--pr-map` and `--manifest-file` so `tools/check_legacy_writes.py` exits `2` unless `--ruleset-check skip` is also passed, and added a unit test verifying `.github/workflows/legacy-write-detector.yml` passes none of them. |
| **R1-m7** | Minor | **Adopted in full (§10.2).** Wrote out the complete `steps:` block of `.github/workflows/legacy-write-detector.yml` with `fetch-depth: 0`, `git fetch --no-tags origin main:refs/remotes/origin/main`, and the check that `target_head` is `origin/main`'s tip or lies on `origin/main`'s first-parent chain. |
| **R1-m8** | Minor | **Adopted in full (§4.3.3, §8.2 Check 1, §8.5, §15.1).** Specified the exact pre-code Python dry-run command exercising `handle_bound_read` and `segment(raw, "computational_log_entry")` on the real vault path (printing only length, SHA-256, `link_count`, `canonical_target`, `file_facts`, `row_counts`, and `blockers`), and removed the whole-file `line_ending == "LF"` requirement from the vault detector so a CRLF successor entry saved by Obsidian does not trip when all legacy row hashes match. |
| **R1-m9** | Minor | **Adopted in full (§2.1, §2.2, §5.1, §5.3).** Removed the unrelated CLI reference to Owner Point A, corrected the D-1 store path to `C:/Users/steph/TDL-ARS-G7-Control` (`06v:563`), and cited `tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml` and `test_wp6_1_06h_append_path_closure.py` for the 275-row census instead of a nonexistent `contracts/runtime-binding-census.yaml` path. |
| **R1-m10** | Minor | **Adopted in full (§2.3, §5.3, §16 A).** Specified the exact update to `require_registered` (`research_system/legacy/evidence.py:124-130`): `_closed` accepts the 5-key manifest entry, verifies `(role, source_identity_kind)` when present, and projects each entry to the 3 identity keys `("root_kind", "root_id", "normalized_path")` at line 129 so `wanted not in ...` matches at `LR-015`. |
| **R1-m11** | Minor | **Adopted in full (§7.4 item 5, §7.6 Control N6).** Added the first-byte `|` check on inserted units in legacy-lock sections of `CONVENTIONS.md` so inserted tables are rejected (`W9` §7.3 item 4 allows only bullets or paragraphs), and stated the accepted structural-byte exceptions (`---` rules, blank lines, footer, H1 preamble, `### ` sub-headings) explicitly. |
| **R1-m12** | Minor | **Adopted in full (§14).** Expanded §14 to 16 load-bearing claims covering time-indexed evidence, Rule 0, manifest fields, Rule 1 matching and exclusions, `.apm/tracker.md` Working Notes, §4.2 record keying and `P1`-anchored provenance, 2-parent merge diffs, PR mapping and `5df0c001`/`811d5a2b` genealogy, Option D3 blob-keyed freshness, ruleset pinning and U-3 probe, explicit vault-root junction refusal, `CONVENTIONS.md` unit counts and table filter, vault detector classification source, D-5 batch-start gate, tool-blob-bound control hashes, and `ci.yml` PR-lane wiring. |
| **R1-m13** | Minor | **Adopted in full (Header, §8.2, §15.2 item 5).** Replaced the header's verification row with an explicit statement of what was read, what was run, and what remains a pre-code gate; deleted the stray `"Wait:"` text; and labeled §15.2 item 5 as a WP9.5-specific stop rule added by this note rather than citing `06v:629`. |
| **R1-m14** | Minor | **Adopted in full (§11.2, §12.3, §16 G, Appendix A §19.1).** Measured the `--bare --local --no-hardlinks` clone on this machine (`1.71–1.79s`), specified T7-2 using a throwaway index file (`GIT_INDEX_FILE` with `git read-tree`, `git update-index --add --cacheinfo`, `git write-tree`, `git commit-tree`), and included `@pytest.mark.slow` tests in the §12.3 and Owner Point G budget. |
| **R1-i1** | Info | **Recorded (§6.5 Rule 2).** Stated explicitly that hard-coding the `"results/ars/"` prefix exemption in Rule 2 is a deliberate, safe reading of `W9-D14` so `results/ars/` is exempt even before its registration batch lands. |
| **R1-i2** | Info | **Recorded (§6.3 item 2, §12.1).** Stated explicitly that mode-only changes (`old_blob == new_blob`, `old_mode != new_mode`) on a registered legacy file cannot satisfy `old_blob != new_blob` in `legacy-write-records.json` and fail closed. |
| **R1-i3** | Info | **Recorded (§4.1, §4.2.1, §4.2.2, §4.2.3, §13.2 HR-5, Appendix A §19.1).** Populated the owner-`gh` rows in §4.2.2 with the live 2026-11-21 observations (including 57 `rule-suites` entries: 33 `bypass`, 24 `pass`, newest `dbd54fe38...`), and noted the wider scope of D-8's known limit when queue merges are recorded as `bypass`. |
| **R1-i4** | Info | **Recorded (§7.4 item 1).** Cited `.gitattributes:14` (`* text=auto eol=lf`), confirming Windows runner checkouts produce LF for `CONVENTIONS.md`. |
| **R1-i5** | Info | **Retained (§6.3 item 2).** Kept the 2-parent merge commit `diff-tree -r --no-renames -z <P1> <C>` handling. |
| **R1-i6** | Info | **Retained (§6.4, §6.6).** Kept the rule that an absent `legacy-write-records.json` before L-1 is an error only when a guarded write occurs in `<baseline>..<head>`. |
| **Review §2** | Citation audit | **Adopted in full across the entire document.** Corrected every `06v-w9-implementation-plan.md` line reference (`U-3` `:159`, `U-4` `:160`, `O-9..O-13` `:189-193`, `W9-T7` `:230`, `W9-T19` `:242`, `D-4` `:566`, `D-7` `:569`, squash merges `:90-91`, stop rules `:610-620`), every `03-decisions-and-open-questions.md` reference (`P-064` item 8 `:4232-4233`, `P-087` item 7 `:5919-5923`, `P-089` `:6071-6146`), and every code/workflow reference (`evidence.py:52-54,92-105,221-252`, `preparers.py:676,686-690,1200,1215-1218`, `replay/reducers.py:70,571`, `check_workflow_liveness.py:78-92`, `check_bypass_merges.py:106-110`, `check_merge_admission.py:700-737`, `wp9-4-design-note.md:703,1419`, and `.github/workflows/*.yml`). |

---

## 19. Appendix A: Verification

### 19.1 Commands executed in the worktree (`C:\Users\steph\TDL\.apm\worktrees\wp9-5-note`) during revision 2 authoring

All commands below were read-only against the repository and GitHub REST API (`GET` only); no vault file was read by the authoring session, and `git status --short` was verified clean before and after.

| # | Command run | What it showed |
|---|---|---|
| 1 | `git -C "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note" branch --show-current; git rev-parse --short HEAD; git status --short` | Branch `docs/w9-wp9-5-design-note`, `HEAD` `edb9acc6`, status clean (empty). |
| 2 | `git -C "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note" --no-replace-objects diff-tree -r --no-renames --name-status 5df0c001~1 5df0c001` | 11 files changed: `M .claude/CLAUDE.md`, `A .codacy/codacy.config.baseline.json`, `A .codacy/codacy.config.json`, `M .repowise-workspace.yaml`, and 7 `results/` files (`results/panel_methodology/bhps_nonoverlap/bhps_nonoverlap_reanalysis_2026-06-09.json`, `results/trajectory_tda_bhps/01_trajectories.json`, `results/trajectory_tda_bhps/stage1/bhps_headline_frozen_corrected_2026-07-14.json`, `results/trajectory_tda_integration/01_trajectories.json`, `results/trajectory_tda_integration/05_analysis.json`, `results/trajectory_tda_integration/stage1/headline_vintage_materiality_corrected_2026-07-14.json`, `results/trajectory_tda_integration/stage1/w2_fallback_audit_2026-07-14.json`). |
| 3 | `git -C "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note" --no-replace-objects diff-tree -r --no-renames --name-status 811d5a2b~1 811d5a2b` | 9 files changed: `M .agents/skills/tda-handoff/SKILL.md`, `M .claude/CLAUDE.md`, `M .claude/skills/tda-handoff/SKILL.md`, `M .githooks/pre-commit`, `M .repowise-workspace.yaml`, `M tools/skill_sync_state.json`, and 3 `contracts/manifests/input-provenance/` files (`b9-om-gmm-inputs.yaml`, `t128-inputs.yaml`, `t138-w2-gap-closure-inputs.yaml`). |
| 4 | First-parent walk script (`verify_r2.py` under `.venv\Scripts\python.exe`): `git --no-replace-objects rev-list --first-parent --reverse 4b143c9225035cc29e37351445f1c3a4ab09ceb1..dbd54fe382e7b2849d3f2038393cbdb4d709477b` + `diff-tree -r --no-renames <P1> <C>` filtering for `CONVENTIONS.md`, `results/`, `papers/`, `contracts/`, `.apm/` | 320 total first-parent commits; identified the exact 20 commits touching those prefixes (`02ebcaf6`, `5795a18b`, `9016b663`, `2111ce62`, `7347ae95`, `9795ee5f`, `f52f52f4`, `5df0c001`, `811d5a2b`, `b132406e`, `1dbf6b7b`, `85c7a02e`, `eba3fe69`, `65f4da4b`, `452352ff`, `3a14a97c`, `53b7c5be`, `e3519ba7`, `633ed58e`, `14a81b84`, `1fba78aa`, `a6a98966` — 22 total including `#419` and `#425` on `CONVENTIONS.md`), recorded in §6.2.1. |
| 5 | `CONVENTIONS.md` segmentation check (`verify_r2.py` running `research_system.legacy.segmentation.segment` and `tools.w9_segmentation.segment` on blob `4620c71607ca3a06c6df3b8e96a6bddffc783960` and `dbd54fe382e7b2849d3f2038393cbdb4d709477b:CONVENTIONS.md`) | Both segmenters agreed byte-for-byte on both blobs. Baseline (`4620c716`): `33,645` bytes, SHA-256 `d04fe97e...8589`, 575 lines, LF, no BOM, 70 units across 10 sections (`3, 2, 5, 4, 24, 13, 6, 3, 2, 8`). Head (`dbd54fe3`): `51,774` bytes, SHA-256 `2ce15910d2f6712e2d4311578ebe8a5b6e7b1f83086c1c5483ea4876636ff97c`, 822 lines, LF, no BOM, 90 units across 11 sections (`Computational Environment` grew `8 -> 15`, `ARS Foundation Governance` grew `2 -> 9`, `Repo-Wide CI...` added `6`; all 70 baseline units preserved in order). |
| 6 | Commit details & bare clone timing (`verify_more.py` running `git show -s`, `git clone --bare --local --no-hardlinks` into `tempfile.TemporaryDirectory()`, and two `git diff-tree` queries) | Confirmed `1af52f6d` (`2026-07-18T19:05:13+01:00`, parent `02ebcaf6`, merged by `#129` `5795a18b`), `3fa437a1` (`#387`, `2026-10-21T22:42:45+01:00`), `a426b731` (`#215`, 2 parents), `b132406e` (`#219`, 2 parents `811d5a2b` and `3bfb279c`). Measured `git clone --bare --local --no-hardlinks` at **1.71s – 1.79s** (`1.77s – 1.86s` including two `diff-tree` runs). |
| 7 | `git -C "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note" ls-files contracts/` | Listed all tracked files under `contracts/`, confirming real shared-surface contract paths (`contracts/manifests/research-assurance.yaml`, `contracts/stochastic-tests/monte-carlo-permutation-p-value.yaml`, `contracts/stochastic-tests/markov-order-provenance.yaml`, `contracts/topology-invariants/null-operation-changes-ph-input.yaml`, `contracts/schema/contract.schema.yaml`). |
| 8 | `gh api repos/ZK-Theory/TDL/rulesets/20822054` (read-only GET) | HTTP 200: `id: 20822054`, `name: "P-049 Gate 6 main merge admission"`, `enforcement: "active"`, `conditions.ref_name.include: ["refs/heads/main"]`, `pull_request` (`required_approving_review_count: 0`, `require_code_owner_review: true`, `required_review_thread_resolution: true`, `allowed_merge_methods: ["squash"]`), `required_status_checks` (`strict_required_status_checks_policy: true`, 4 contexts), `merge_queue` (`merge_method: "SQUASH"`, `max_entries_to_build: 1`, `min_entries_to_merge: 1`, `max_entries_to_merge: 1`), `non_fast_forward`, `bypass_actors: [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}]`. |
| 9 | `gh api --paginate --slurp "repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=month&per_page=100"` (read-only GET via `verify_more.py`) | HTTP 200: 57 entries (`{'bypass': 33, 'pass': 24}`), newest `dbd54fe382e7b2849d3f2038393cbdb4d709477b` (`bypass`, `2026-11-21T20:20:44+00:00`, `stephendor`), oldest `bb9d91d45493f7dfdf31aa1c3e6b34ecf6113a32` (`bypass`, `2026-10-21T22:42:20+01:00`, `stephendor`). |

### 19.2 Statements marked `UNVERIFIED` (pre-code gates for the reviewing session)

Every statement in this design note that cannot be verified without running a GitHub Actions workflow under `GITHUB_TOKEN` or reading the live vault `Computational-Log.md` bytes is listed here and gated as a hard precondition of WP9.5 code dispatch in §15.1:

1. **`UNVERIFIED-1` (U-3 probe, §4.2.2, §15.1 item 1):** The HTTP status codes and `X-Accepted-GitHub-Permissions` headers returned to a GitHub Actions `GITHUB_TOKEN` (under `permissions: contents: read` and under `permissions: contents: read, pull-requests: read`) for:
   - `GET repos/ZK-Theory/TDL/rulesets/20822054`
   - `GET repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=day&per_page=5` (expected HTTP 403/404 per `tools/check_bypass_merges.py:20-21`, which decides D-8)
   - `GET repos/ZK-Theory/TDL/commits/dbd54fe382e7b2849d3f2038393cbdb4d709477b/pulls`
2. **`UNVERIFIED-2` (U-4 handle-bound reader and segmenter dry run on the live `833,453`-byte vault file, §4.3.3 item 2, §15.1 item 2):** The output of running `handle_bound_read(Path(r"C:\Users\steph\Documents\TDA-Research"), "04-Methods/Computational-Log.md")` and `segment(raw, "computational_log_entry")` on the current `833,453`-byte live file (`link_count == 1`, `file_facts`, `row_counts`, and `blockers == []`).
