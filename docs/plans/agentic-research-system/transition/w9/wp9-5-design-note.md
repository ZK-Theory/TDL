# WP9.5 Design Note — W9 Detectors (W9-D5)

| Field | Value |
|---|---|
| Date | 2026-11-21 |
| Status | **Revision 1, for independent adversarial review. Nothing in it is implemented.** |
| Package | `06v` WP9.5 — "Detectors (W9-D5)" (`docs/plans/agentic-research-system/implementation/06v-w9-implementation-plan.md:470-499`) |
| Authority | Decision register entry `P-089` (`docs/plans/agentic-research-system/03-decisions-and-open-questions.md:6057-6156`) |
| Base | `origin/main` at `dbd54fe382e7b2849d3f2038393cbdb4d709477b` (`[PIPELINE] P06: WP9.4-2 follow-up: the independent review's Minor findings (P-088 item 5) (#446)`) |
| Worktree / Branch | `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note` on branch `docs/w9-wp9-5-design-note` |
| Not authorized | WP9.5 code, WP9.6, WP9.7, live operations L-0 to L-5 (including L-0b and L-1), creating or binding the real control store, registering or observing any real file, or any write to a legacy file, `main`, or the vault (`03-decisions-and-open-questions.md:6085-6091`) |
| Verification note | Every `path:line` citation in this note was read directly from the worktree at base commit `dbd54fe382e7b2849d3f2038393cbdb4d709477b`. Shell probes after worktree creation (`gh api`, `Get-Item`/`Get-FileHash` on the vault path, and `git commit`) were not executed in the authoring session because the Windows `exebox` sandbox driver failed with `CreateProcessSecurityEnvironment: Access is denied` and unsandboxed command prompts were halted by the operator. Both U-3 and U-4 are specified as explicit pre-code gates in §4.2, §4.3, and §15. |

---

## 1. What this note settles

WP9.5 builds the W9 detectors (`06v:470-499`; `W9` §4.4, `docs/plans/agentic-research-system/design/09-migration-compatibility-and-pilot.md:191-210`): the checks that detect when something writes a registered legacy file, writes under `results/` outside `results/ars/`, modifies a locked legacy item of `CONVENTIONS.md`, or alters a legacy entry in the vault's `04-Methods/Computational-Log.md`.

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
| 1. Scope, package boundary, and protected identities | §2 | No W9 command, runtime-binding row, ledger append site, schema, or `tools/w9_segmentation.py` byte changes; no D-4 is expected. |
| 2. The ruleset read (`main_ruleset`, `recorded_read`) | §4.1 | Reads ruleset `20822054` configuration and `rulesets/rule-suites` history for `refs/heads/main`, verifies active invariants, and records canonical output SHA-256 before every batch and at L-1. |
| 3. U-3 (`GITHUB_TOKEN` ruleset & rule-suites read probe + D-8 fallback) | §4.2, §15 | Read-only `workflow_dispatch` probe specification and exact `P-064` item 8 (D-8) fallback. Precondition in §15: reviewing session runs and records U-3 in §4.2 on Stephen's authorization before code dispatch. |
| 4. Post-merge first-parent detector (`tools/check_legacy_writes.py` & `.github/workflows/legacy-write-detector.yml`) | §6 | First-parent walk from recorded baseline commit; `git diff-tree -r --no-renames <P1> <C>` for 1-parent and 2-parent commits; PR mapping; W9 §4.2 record format keyed by `(pr_number, normalized_path, old_blob, new_blob)`; Rules 1, 2, and 3; `5df0c001` and `811d5a2b` genealogy. |
| 5. Registration manifest export (M-6) | §5 | Exporter writes `.research-system/evidence/w9/registration-manifest.json` (`w9-registration-manifest/1`) from store projections before each batch's first observation; check mode and test prove store-to-manifest equality at the bound `git_head`. |
| 6. Shared-surface rule (O-32, detector half, Rule 3) | §6.5, §16 (Owner Points A, D) | How the detector identifies `shared_enforcement_surface` contracts, checks the W9 §4.3 owner note and `.research-system/evidence/w9/shared-surface-changes.json`, and surfaces the squash-merge SHA contradiction between `06v:89-90,212,479-481` and `research_system/legacy/evidence.py:231-238` for Stephen's decision. |
| 7. `CONVENTIONS.md` legacy-lock check (`tools/check_conventions_legacy_locks.py`) | §7 | `conventions_unit` segmentation (`w9-segmentation/1.0.0`) against baseline commit `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (blob `4620c71607ca3a06c6df3b8e96a6bddffc783960`); 9 legacy-lock `## ` sections vs `## ARS Foundation Governance` (successor under W9 §7.3 items 1 & 4); ordered-subsequence insertion-only check. |
| 8. Vault Computational-Log detector (`tools/check_legacy_log_baseline.py`) and D-5 cadence | §8, §16 (Owner Point E) | Compares live `04-Methods/Computational-Log.md` against accepted `w9-cl-export/1` baseline (tested against a synthetic fixture export before L-0b); enforces D-5 pre-batch and 7-day weekly cadence so a missed run blocks the next batch. |
| 9. U-4 (operator machine vault path & read-only dry run) | §4.3, §15 | Handle-bound real vault root `C:\Users\steph\Documents\TDA-Research` vs gitignored repository junction `C:\Users\steph\TDL\vault`; pre-code gate in §15 for live metadata & read-only dry run recording. |
| 10. Detector-controls file (`.research-system/evidence/w9/detector-controls.json`) | §9 | Control runner executes all four required controls (`main_ruleset`, `post_merge_first_parent`, `vault_computational_log`, `conventions_repository_check`), hashes deterministic canonical reports, and writes `w9-detector-controls/1`. |
| 11. Merging is not going live (`P-089` item 3) | §10 | `.github/workflows/legacy-write-detector.yml` merges with `on: workflow_dispatch:` only (satisfying `tools/check_workflow_liveness.py --all-tracked` while staying inactive on `main` pushes and schedules until L-1); proved by a workflow-trigger unit test. |
| 12. Where the controls run (`P-089` item 4; `06v` O-13; W9-T7) | §11 | Scratch clones (`git clone --no-checkout --local --no-hardlinks`) and byte copies under `tmp_path`; W9-T7 replay of `5df0c001` and `811d5a2b`; repository-immutability proof before and after tests. |
| 13. Tests and test-time budget | §12, §16 (Owner Points F, G) | W9-T7 (`slow`, `integration`), W9-T19 (`unit`), M-6 equality, O-32 controls, workflow policy compliance (`tests/tools/test_ci_platform_policy.py:286-303`), per-file timing estimates, and proposed 2-minute (120s) serial `--no-cov` budget. |
| 14. Research assurance | §13 | Machine-checkable claims with enforcement artifacts vs human-review-only claims. |
| 15. Claims for review | §14 | 12 numbered load-bearing claims with exact `path:line` evidence for independent adversarial review. |
| 16. Stop rules for the code package | §15 | `06v` §8 stop rules plus WP9.5 preconditions (U-3 recorded, U-4 recorded, Owner Points A–G decided in `P-090`). |
| 17. Owner points | §16 | Seven owner decisions (A through G), each with explicit options, trade-offs, and a recommendation. |

---

## 2. Scope, package boundary, and protected identities

### 2.1 Deliverables in WP9.5

Under `06v` §5 (`06v-w9-implementation-plan.md:470-499`) and `P-089` (`03-decisions-and-open-questions.md:6080-6114`), WP9.5 delivers:

1. **The registration manifest exporter and store-equality verifier (M-6):**
   - `tools/export_w9_registration_manifest.py` (using a read-only projection helper in `research_system/legacy/evidence.py`, or `ars legacy` read-only CLI helper if selected under Owner Point A), producing `.research-system/evidence/w9/registration-manifest.json` in WP9.3's `w9-registration-manifest/1` format (`research_system/legacy/evidence.py:37,40,114-131`) and verifying 1:1 set equality between the store's `legacy_path_registration` projection and the committed manifest at the store binding's `git_head`.
2. **The post-merge first-parent detector and workflow (`W9-D5`, `O-9`, `O-10`, `O-32`):**
   - `tools/check_legacy_writes.py`: walks `git --no-replace-objects rev-list --first-parent --reverse <baseline>..<head>`, checks Rules 1, 2, and 3 against `.research-system/evidence/w9/registration-manifest.json`, `.research-system/evidence/w9/legacy-write-records.json` (Owner Point B), and `.research-system/evidence/w9/shared-surface-changes.json`, and checks ruleset `20822054` and `rulesets/rule-suites` in local pre-batch mode (and in CI if U-3 permits; otherwise under D-8 fallback).
   - `.github/workflows/legacy-write-detector.yml`: Windows-only (`runs-on: windows-latest`) workflow committed in WP9.5 with `on: workflow_dispatch:` only so merging WP9.5 does **not** activate automatic detection on `main` before L-1 (§10).
3. **The `CONVENTIONS.md` legacy-lock check (`W9-D5`, `O-12`):**
   - `tools/check_conventions_legacy_locks.py`: verifies that `CONVENTIONS.md` preserves every legacy unit from baseline commit `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (blob `4620c71607ca3a06c6df3b8e96a6bddffc783960`, 33,645 bytes, SHA-256 `d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589`, pinned in `research_system/legacy/reader.py:43-49`) under `conventions_unit` segmentation (`w9-segmentation/1.0.0`, `tools/w9_segmentation.py:388-458`).
4. **The vault Computational-Log baseline detector (`W9-D5`, `O-11`, `D-5`, `D-7`):**
   - `tools/check_legacy_log_baseline.py`: reads the live `04-Methods/Computational-Log.md` from the real vault directory `C:\Users\steph\Documents\TDA-Research` via `handle_bound_read` (`research_system/legacy/reader.py:140-206`), segments the whole file under `computational_log_entry` (`research_system/legacy/segmentation.py:429-488`), and compares every legacy-classified item and structural block against the accepted `w9-cl-export/1` baseline export (`research_system/legacy/evidence.py:277-362`). Tested against a synthetic fixture export until L-0b is authorized and pinned in `ACCEPTED_CL_EXPORT` (`research_system/legacy/accepted_w9.py:86-88`).
5. **The detector negative-control runner (`O-13`):**
   - `tools/run_w9_detector_controls.py`: executes the `recorded_read` control for `main_ruleset` and the `watched_to_fail` negative controls on scratch clones and byte copies for `post_merge_first_parent`, `vault_computational_log`, and `conventions_repository_check`, producing `.research-system/evidence/w9/detector-controls.json` (`w9-detector-controls/1`, `research_system/legacy/evidence.py:38,41,59-64,133-154`).
6. **Tests (`W9-T7`, `W9-T19`):**
   - `tests/tools/test_w9_detectors.py` (`unit`, including W9-T19 and all per-detector positive and negative controls on byte copies).
   - `tests/research_system/integration/test_w9_wp9_5_detectors.py` (`slow`, `integration`, including W9-T7 scratch-clone replay of `5df0c001` and `811d5a2b` and the M-6 store-to-manifest equality test).

### 2.2 What WP9.5 does NOT touch and why no D-4 is expected

Per `P-089` item 1 (`03-decisions-and-open-questions.md:6081-6083`), WP9.5 adds **no W9 command** (`ProposeLegacyRecord`, `RecordLegacyGrant`, `WithdrawLegacyGrant`, `RecordLegacySupersession`, and `ResolveW9AuthorityDecision` in `research_system/legacy/contracts.py` remain the entire W9 command surface). Specifically:

| Protected identity / surface | Current pinned value on `main` (`dbd54fe38`) | WP9.5 impact |
|---|---|---|
| Runtime-binding census (`docs/plans/agentic-research-system/contracts/runtime-binding-census.yaml`) | 275 rows; SHA-256 `82eab93a1b2ac81dd564581237f35e3dff19fee9e824ffff317d0f202b451d58` (`03-decisions-and-open-questions.md:6064,6138`) | **Unchanged.** WP9.5 adds no contract or command row (`49` routed, `12` deferred from WP9.4-2). |
| 06h append-path manifest (`tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml`) | Blob `1066404a` (`03-decisions-and-open-questions.md:6065,6139`) | **Unchanged.** WP9.5 detectors are read-only observers and never append to any store ledger. |
| 06h append-path closure smoke test (`tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py`) | Blob `3b1eec6e` (`03-decisions-and-open-questions.md:6065,6139`) | **Unchanged.** |
| Schema registry & authority (`research_system/schema_registry.py`, `research_system/authority.py`) | Blobs `e32cb408` and `9b56b322` (`03-decisions-and-open-questions.md:6066,6140`) | **Unchanged.** |
| Core schemas (`core/commands`, `core/events`), T2 expectations & seal, and the 19 `.research-system/schemas/contracts/w9/*.schema.json` files | Pinned at WP9.1 (`P-073`) | **Unchanged.** |
| Pre-code segmenter (`tools/w9_segmentation.py`) | Blob `43e1454de09b61e274954c42b21d6ae533857a24` (`research_system/legacy/accepted_w9.py:67`) | **Unchanged.** Imported read-only; never modified. |

**Consequence:** Because no runtime-binding row, command type, event type, append site, or schema changes, **no D-4 re-acceptance (`06v:565`) is triggered by WP9.5**. If any implementation choice during WP9.5 construction would alter any row of the table above, work stops immediately for an owner decision (§15).

### 2.3 Boundary with `research_system/legacy/` and `.github/CODEOWNERS`

1. **`research_system/legacy/` boundary (`P-089` item 3, `03-decisions-and-open-questions.md:6105-6106`):**
   *"Nothing under `research_system/legacy/` changes except a reader WP9.5 needs, and the note names it."*
   This note identifies the exact minimal reader changes under `research_system/legacy/` that depend on Stephen's choices in §16:
   - `research_system/legacy/evidence.py`:
     - adding a read-only projection helper `project_registration_manifest(state)` (or reading `state["records"]["legacy_path_registration"]`) and `require_legacy_write_records` for `.research-system/evidence/w9/legacy-write-records.json` (Owner Point B);
     - if Stephen selects Option A1 (Owner Point A), widening `require_registered` (`research_system/legacy/evidence.py:124-127`) so each entry in `registration-manifest.json` carries `"role"` alongside `"root_kind"`, `"root_id"`, and `"normalized_path"`;
     - if Stephen selects Option D1 (Owner Point D), updating `_change_entries` (`research_system/legacy/evidence.py:224-252`) to admit pre-merge PR/blob identification alongside or instead of a post-merge squash SHA;
     - if Stephen selects Option E1 (Owner Point E), adding `VAULT_DETECTOR_RUNS = f"{EVIDENCE_DIRECTORY}/vault-detector-runs.json"` and `require_vault_detector_cadence`, called from `check_environment` in `research_system/legacy/acceptance.py:147-152`.
   No other file in `research_system/legacy/` is touched.
2. **`.github/CODEOWNERS` and `GATE_FILES` boundary (`CONVENTIONS.md:713-730`; `tests/tools/test_ci_platform_policy.py:341-375`):**
   - `.github/CODEOWNERS` guards `.github/workflows/ci.yml`, `.github/workflows/merge-admission.yml`, `.github/workflows/merge-admission-sweep.yml`, `tools/check_merge_admission.py`, `tools/check_test_commit_literals.py`, and `tests/tools/test_ci_platform_policy.py` (`CONVENTIONS.md:721-723`). Any PR modifying those paths requires `@stephen`'s review or admin bypass on merge (`CONVENTIONS.md:724-730`).
   - `.github/workflows/legacy-write-detector.yml`, `tools/check_legacy_writes.py`, `tools/check_conventions_legacy_locks.py`, `tools/check_legacy_log_baseline.py`, `tools/export_w9_registration_manifest.py`, `tools/run_w9_detector_controls.py`, `tests/tools/test_w9_detectors.py`, and `tests/research_system/integration/test_w9_wp9_5_detectors.py` are **not** in `.github/CODEOWNERS`.
   - However, `tests/tools/test_ci_platform_policy.py:286-303` (`test_every_tools_and_contracts_test_runs_in_a_workflow`) asserts that every `tests/tools/test_*.py` stem appears in the `run:` script of at least one workflow in `.github/workflows/*.yml` or in `CONTROL_EXEMPTIONS`. Owner Point F (§16) settles whether `tests/tools/test_w9_detectors.py` is wired into `.github/workflows/ci.yml` (which touches a `CODEOWNERS`-guarded file) or into `.github/workflows/legacy-write-detector.yml` and `.github/workflows/research-system-suite.yml` (which touches no `CODEOWNERS`-guarded file).

---

## 3. Carried obligations

| Source | ID | Obligation | Where settled in this note |
|---|---|---|---|
| `06v:123` | `U-3` | Verify whether the CI token (`GITHUB_TOKEN`) can read ruleset `20822054` and `rulesets/rule-suites`, and apply D-8 if not. Recorded before any WP9.5 code (`P-089` item 3). | §4.2, §15 |
| `06v:124` | `U-4` | Verify the operator machine's path to the vault (`C:\Users\steph\Documents\TDA-Research` vs `C:\Users\steph\TDL\vault` junction) and record a read-only dry run before any WP9.5 code (`P-089` item 3). | §4.3, §15 |
| `06v:160` | `O-9` | Post-merge first-parent walk on `main` (`tools/check_legacy_writes.py`, `.github/workflows/legacy-write-detector.yml`): checks registered files, `results/` outside `results/ars/`, and `shared_enforcement_surface` contracts. | §6 |
| `06v:161` | `O-10` | Ruleset `20822054` and `rule-suites` history read before every batch and in the post-merge detector (subject to U-3 / D-8). | §4.1, §4.2, §6.6 |
| `06v:162` | `O-11` | Vault `Computational-Log.md` baseline detector (`tools/check_legacy_log_baseline.py`) against accepted export; runs before every batch and weekly on the operator machine. | §8 |
| `06v:163` | `O-12` | `CONVENTIONS.md` legacy-lock check (`tools/check_conventions_legacy_locks.py`): insertion-only check against commit `4b143c92`. | §7 |
| `06v:164` | `O-13` | Negative controls for all four detectors (`recorded_read` for `main_ruleset`; `watched_to_fail` for the other three) run on scratch clones or byte copies; output hashes committed to `.research-system/evidence/w9/detector-controls.json` at L-1 before first registration. | §9, §11 |
| `06v:212` | `O-32` | Detector half of shared-surface enforcement: fail when a merged change to a `shared_enforcement_surface` contract lacks an entry in `shared-surface-changes.json` or lacks a W9 §4.3 owner note. | §6.5, §16 (Owner Points A, D) |
| `06v:483-484` | `M-6` | Export `registration-manifest.json` from the control store per registration batch before that batch's first observation; test that the manifest equals the store's registered set at the bound head. | §5 |
| `06v:228` | `W9-T7` | Replay `5df0c001` and `811d5a2b` on a scratch clone with a fixture registry listing the files they touched; assert both are flagged (`slow`, `integration`). | §11.2, §12.1 |
| `06v:240` | `W9-T19` | Computational-Log and `CONVENTIONS.md` checks pass on clean successor insertions and fail on legacy edits, anchor renames, duplicate anchors, and unparseable headings (`unit`). | §7.6, §8.6, §12.1 |
| `06v:567` | `D-5` | Vault detector runs before every batch and weekly on the operator machine; each run files an output hash in the evidence area; a missed run blocks the next batch. | §8.4, §16 (Owner Point E) |
| `06v:570` | `D-7` | L-0b export is produced by Stephen on the operator machine and committed by a reviewed PR; WP9.5 designs and tests the vault detector against a fixture export until L-0b is accepted. | §8.3 |
| `06v:571` | `D-8` | Fallback if U-3 shows the CI token cannot read `rule-suites` (`P-064` item 8). | §4.2.3 |
| `03-decisions-and-open-questions.md:6103-6104` | `P-089` (3) | Merging WP9.5 must not start any detector on `main` or the vault; L-1 is a separate owner decision. | §10 |
| `wp9-4-design-note.md:1487-1495` | WP9.4 carry | Any unobserved edit to a registered legacy file after registration is caught by WP9.5's post-merge first-parent walk (`O-9`), vault log baseline check (`O-11`), or `CONVENTIONS.md` lock check (`O-12`), together with WP9.3's blob-continuity preparers (`LR-015`, `LR-016`, `LR-020`). | §6, §7, §8 |

---

## 4. Interface findings (`path:line` at `dbd54fe38`), ruleset read, U-3, and U-4

### 4.1 The ruleset read (`main_ruleset`, control kind `recorded_read`)

- **Authority and purpose:** `W9` §4.4 (`09-migration-compatibility-and-pilot.md:195,201-202`), `06v` §3 row `O-10` (`06v-w9-implementation-plan.md:161`), `06v` §7 L-1 and batch checklist (`06v-w9-implementation-plan.md:591,602`), and `REQUIRED_DETECTOR_CONTROLS["main_ruleset"] == "recorded_read"` (`research_system/legacy/evidence.py:59-64`).
- **What it reads:**
  1. **Ruleset configuration endpoint:**
     `gh api repos/ZK-Theory/TDL/rulesets/20822054` (HTTP `GET`, allowed by `.claude/hooks/admin-bypass-guard.sh:18,96-106`, which blocks non-`GET` methods and permits read-only `GET` requests to `rulesets`).
     From the JSON response object, the reader extracts and checks:
     - `id == 20822054` and `name == "P-049 Gate 6 main merge admission"` (`docs/plans/agentic-research-system/01-current-system-evidence.md:409`);
     - `enforcement == "active"` (`01-current-system-evidence.md:409`);
     - `target == "branch"` and `conditions.ref_name.include` contains `"~DEFAULT_BRANCH"` or `"refs/heads/main"`;
     - `rules` contains rule types `pull_request` (with `parameters.require_code_owner_review is True` and `parameters.required_approving_review_count == 0`), `required_status_checks`, `merge_queue`, and `non_fast_forward` (`01-current-system-evidence.md:409`; `W9:165-169`);
     - `bypass_actors` contains only the single documented bypass actor: `actor_id == 5`, `actor_type == "RepositoryRole"` (repository admin), `bypass_mode == "pull_request"` (`01-current-system-evidence.md:409`; `docs/plans/agentic-research-system/reviews/g7b-w9-reconciliation-2026-10-22.md:116-117,128`).
  2. **Rule-suites evaluation history endpoint:**
     `gh api --paginate --slurp "repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=<period>"` (HTTP `GET`, using the same pagination and `--slurp` concatenation pattern already implemented in `tools/check_bypass_merges.py:141-166`).
     From the flattened array of rule-suite evaluations on `refs/heads/main`, the reader inspects each entry's `id`, `actor_name`, `before_sha`, `after_sha`, `pushed_at`, `result`, and `evaluation_result`:
     - Every entry in the evaluation window (`--since-iso <UTC>` / since the recorded baseline commit's timestamp) with `result == "bypass"` (or any `result` other than `"pass"`) is extracted and cross-checked against `tools/check_legacy_writes.py`'s first-parent walk for `after_sha`: if `after_sha` touched any registered legacy path, any `results/` path outside `results/ars/`, or any `shared_enforcement_surface` contract without a valid §4.2 / §4.3 record, the check fails closed.
     - Even when an admin bypass merge touched no legacy path (for example, a `CODEOWNERS`-guarded workflow merge on `main`), every `result == "bypass"` evaluation in the window is listed explicitly in the recorded read report with its `after_sha`, `pushed_at`, and mapped PR number (`tools/check_bypass_merges.py:167-180`).
- **With which token:**
  - On the operator machine (at L-1 and before every batch on the `06v:602` batch checklist), it uses Stephen's authenticated `gh` CLI token (repository owner/admin credentials, which can read both `rulesets/20822054` and `rulesets/rule-suites`, as verified in `tools/check_bypass_merges.py:20-21` and observed on 2026-11-21).
  - In CI (`.github/workflows/legacy-write-detector.yml`), token capability is governed by U-3 and D-8 (§4.2).
- **How the read is recorded and when:**
  - **When:** At L-1 (before the first path registration LR-003, which checks `require_detector_controls` in `research_system/legacy/preparers.py:114` / `evidence.py:133-154`) and before every batch (`06v:602`).
  - **How recorded:** The reader serializes a deterministic canonical JSON object:
    ```json
    {
      "format": "w9-main-ruleset-read/1",
      "repository": "ZK-Theory/TDL",
      "ruleset_id": 20822054,
      "ruleset_name": "P-049 Gate 6 main merge admission",
      "enforcement": "active",
      "target_include": ["~DEFAULT_BRANCH"],
      "rule_types": ["merge_queue", "non_fast_forward", "pull_request", "required_status_checks"],
      "require_code_owner_review": true,
      "required_approving_review_count": 0,
      "bypass_actors": [
        {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}
      ],
      "rule_suites_ref": "refs/heads/main",
      "rule_suites_time_period": "month",
      "rule_suites_checked_count": 42,
      "unrecorded_legacy_bypass_commits": []
    }
    ```
    It computes `output_sha256 = sha256_hex(canonical_bytes(report))` and updates the `"main_ruleset"` entry in `.research-system/evidence/w9/detector-controls.json` with `"control": "recorded_read"`, `"output_sha256": output_sha256`, and `"recorded_at": <UTC ISO-8601Z>` (§9).
- **How it fails (closed):**
  - Non-zero exit (`1`) and refuses to write or update `detector-controls.json` if:
    - `gh api` exits non-zero, returns invalid JSON, or returns an empty/non-dict ruleset object (`ERROR: main_ruleset: failed to read rulesets/20822054`);
    - `enforcement != "active"`, any of the four required rule types is missing, `require_code_owner_review` is not `True`, or `bypass_actors` has changed (`ERROR: main_ruleset: ruleset 20822054 configuration drift: <detail>`);
    - `rulesets/rule-suites` fails or returns an unrecorded bypass commit that touched a guarded W9 surface (`ERROR: main_ruleset: bypass evaluation on refs/heads/main touched guarded path without §4.2 record: <after_sha>`).
- **Negative control and test:**
  - The control kind for `main_ruleset` is `recorded_read` (`research_system/legacy/evidence.py:60`; `W9:195`), because mutating ruleset `20822054` on the live repository to watch it fail is forbidden by `.claude/hooks/admin-bypass-guard.sh:104-106` and project safety rules (`06v:164`).
  - In addition to the live `recorded_read`, unit tests in `tests/tools/test_w9_detectors.py` feed synthetic ruleset and rule-suite JSON payloads to the parser and assert that: (a) `enforcement: "disabled"`, (b) an added bypass actor, (c) removal of `merge_queue` or `require_code_owner_review`, and (d) a `result: "bypass"` entry on a commit touching a registered file without a §4.2 record each cause the checker to exit `1` with the exact `ERROR: main_ruleset:` message.

---

### 4.2 U-3: CI token (`GITHUB_TOKEN`) ruleset and rule-suites probe and D-8 fallback

#### 4.2.1 Current repository evidence on U-3

1. **Owner's `gh` login (known to succeed):**
   With Stephen's authenticated `gh` login, `gh api repos/ZK-Theory/TDL/rulesets/20822054` returns ruleset `20822054` (`enforcement: "active"`, bypass actor `RepositoryRole` 5 in `pull_request` mode) and `gh api "repos/ZK-Theory/TDL/rulesets/rule-suites"` returns push/merge evaluations for `refs/heads/main`, including entries with `result: "bypass"` (`01-current-system-evidence.md:409`; `g7b-w9-reconciliation-2026-10-22.md:116-117,128`; `tools/check_bypass_merges.py:19-21,152-180`).
2. **Existing codebase note on `GITHUB_TOKEN` (`tools/check_bypass_merges.py:19-22`):**
   `tools/check_bypass_merges.py:19-22` states:
   > *"Reading rule suites needs the repository owner's token, which a workflow's `GITHUB_TOKEN` cannot be granted, so the weekly system review runs this in its step 1."*
   Furthermore, every existing workflow in `.github/workflows/` (`ci.yml:17`, `merge-admission.yml:17`, `merge-admission-sweep.yml:14-16`, `ars-artefact-currency.yml:14`, `ars-artefact-currency-watchdog.yml:22`, `research-system-suite.yml:28`) declares `permissions: contents: read` (plus `pull-requests: read` and `checks: read` in the sweep workflow) and uses the default `GITHUB_TOKEN`. GitHub Actions workflow syntax does not expose an `administration: read` scope for `GITHUB_TOKEN`, and GitHub's REST API requires repository administration permission to list `rulesets/rule-suites`.
3. **Why U-3 must still be probed and recorded before code (`06v:123`; `P-089` item 3, `03-decisions-and-open-questions.md:6094-6095`):**
   `06v` §2.8 row `U-3` (`06v:123`) and `P-089` item 3 require an explicit read-only probe of both GET endpoints under the CI token (`GITHUB_TOKEN`), with the result recorded in this design note **before any WP9.5 code is dispatched**.

#### 4.2.2 Design of the read-only U-3 probe

Because this design-note package is forbidden from creating or dispatching workflows (`P-089`, `03-decisions-and-open-questions.md:6085-6091`), the probe is specified here as a pre-code gate:

- **What the probe runs (two read-only HTTP `GET` calls under `GITHUB_TOKEN`):**
  1. `gh api -i repos/ZK-Theory/TDL/rulesets/20822054`
  2. `gh api -i "repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&per_page=5"`
- **Probe workflow specification (if run via temporary/dispatched workflow step under `GITHUB_TOKEN`):**
  ```yaml
  name: U-3 Ruleset Read Probe (Read-Only)
  on:
    workflow_dispatch:
  permissions:
    contents: read
  defaults:
    run:
      shell: bash
  jobs:
    u3-probe:
      name: Probe GITHUB_TOKEN ruleset and rule-suites read
      runs-on: windows-latest
      timeout-minutes: 5
      env:
        GH_TOKEN: ${{ github.token }}
      steps:
        - name: Probe ruleset 20822054 and rule-suites GET
          run: |
            set +e
            echo "=== Call 1: GET repos/ZK-Theory/TDL/rulesets/20822054 ==="
            out1="$(gh api -i repos/ZK-Theory/TDL/rulesets/20822054 2>&1)"
            rc1=$?
            status1="$(printf '%s\n' "$out1" | head -n 1)"
            echo "rc1=$rc1 status1=$status1"

            echo "=== Call 2: GET repos/ZK-Theory/TDL/rulesets/rule-suites ==="
            out2="$(gh api -i 'repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&per_page=5' 2>&1)"
            rc2=$?
            status2="$(printf '%s\n' "$out2" | head -n 1)"
            echo "rc2=$rc2 status2=$status2"
            {
              echo "### U-3 Probe Result"
              echo "- Call 1 (\`rulesets/20822054\`): exit \`$rc1\`, HTTP \`$status1\`"
              echo "- Call 2 (\`rulesets/rule-suites\`): exit \`$rc2\`, HTTP \`$status2\`"
            } >> "$GITHUB_STEP_SUMMARY"
            exit 0
  ```
- **What the probe records in this note (table to be populated by the reviewing session on Stephen's authorization before WP9.5 code dispatch):**

| Endpoint | Token | Expected / Observed HTTP status | Result (`PASS` / `HTTP 403/404 -> D-8 active`) | Recorded by / Date |
|---|---|---|---|---|
| `GET repos/ZK-Theory/TDL/rulesets/20822054` | Owner `gh` login (local) | HTTP 200 (`id: 20822054`, `enforcement: "active"`, bypass actor `RepositoryRole` 5 in `pull_request` mode) | Observed on 2026-11-21 (`P-089` handover §3.3; `01-current-system-evidence.md:409`) | Owner `gh` observation (re-run pending in review session) |
| `GET repos/ZK-Theory/TDL/rulesets/rule-suites` | Owner `gh` login (local) | HTTP 200 (array of push/merge suite evaluations on `refs/heads/main`, including `result: "bypass"`) | Observed on 2026-11-21 (`P-089` handover §3.3; `tools/check_bypass_merges.py:19-21`) | Owner `gh` observation (re-run pending in review session) |
| `GET repos/ZK-Theory/TDL/rulesets/20822054` | CI `GITHUB_TOKEN` | **OPEN GAP (U-3)** — pending probe run | Pending | Owner: Stephen authorizes; reviewing session runs and records here before code dispatch |
| `GET repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&per_page=5` | CI `GITHUB_TOKEN` | **OPEN GAP (U-3)** — expected HTTP 403/404 per `tools/check_bypass_merges.py:20-21`; pending probe run | Pending | Owner: Stephen authorizes; reviewing session runs and records here before code dispatch |

#### 4.2.3 Exact D-8 fallback (`P-064` item 8; `06v` §6 D-8)

If the U-3 probe confirms that `GITHUB_TOKEN` cannot read `rulesets/rule-suites` (or `rulesets/20822054`), WP9.5 applies **D-8** verbatim as accepted in `P-064` item 8 (`03-decisions-and-open-questions.md:3996`; `06v-w9-implementation-plan.md:571`):

> **D-8 (`06v:571`, accepted in `P-064` item 8):**
> *"Record as a known limit that bypass use between batches is seen only at the next pre-batch local read, under the owner's `gh`. The alternative is a token with ruleset read access."*

Concretely, `tools/check_legacy_writes.py` supports an explicit `--ruleset-check` flag with two modes:
1. `--ruleset-check require` (**default**, used on the operator machine before every batch in `06v:602` and at L-1): runs both `GET repos/ZK-Theory/TDL/rulesets/20822054` and `GET repos/ZK-Theory/TDL/rulesets/rule-suites?ref=refs/heads/main&time_period=month` under the owner's `gh` and **fails closed** (exit `1`) if either call fails or shows an unrecorded bypass or ruleset drift.
2. `--ruleset-check ci-d8` (used in `.github/workflows/legacy-write-detector.yml` if and only if the recorded U-3 probe activates D-8):
   - Note that the first-parent Git walk on `main` (`git rev-list --first-parent <baseline>..<head>`) sees **every** commit on `main` regardless of whether that commit entered `main` via the merge queue or via an admin bypass PR merge! Therefore, Rules 1, 2, and 3 of `tools/check_legacy_writes.py` still catch any bypass commit on `main` that touched a registered legacy file, `results/` outside `results/ars/`, or a `shared_enforcement_surface` contract without a valid §4.2 / §4.3 record, immediately in CI on `GITHUB_TOKEN`.
   - The only thing `GITHUB_TOKEN` misses under D-8 is the direct API read of `rulesets/20822054` configuration and `rulesets/rule-suites` evaluation metadata between batches, which is executed and recorded locally under `--ruleset-check require` before every batch (`06v:602`).

---

### 4.3 U-4: Operator machine's path to the vault and read-only dry run

#### 4.3.1 Verified repository facts on the vault path and junction handling

1. **The repository junction vs the real vault directory:**
   - In the main checkout `C:\Users\steph\TDL`, `C:\Users\steph\TDL\vault` is a gitignored Windows directory junction (`Attributes: Directory, ReparsePoint`, `LinkType: Junction`) targeting `C:\Users\steph\Documents\TDA-Research` (`docs/plans/agentic-research-system/01-current-system-evidence.md:357`; `CLAUDE.md:15,28`; `CONVENTIONS.md:790,796`).
   - Because `vault/` is gitignored, linked worktrees under `C:\Users\steph\TDL\.apm\worktrees\<name>` do **not** have a `vault\` junction (`CLAUDE.md:28`).
   - At the time of the WP9.2 segmentation contract measurement (`docs/plans/agentic-research-system/transition/w9/w9-segmentation-contract-v1.md:235-236,242,254-256`), `C:\Users\steph\Documents\TDA-Research\04-Methods\Computational-Log.md` was verified at 376,784 bytes, SHA-256 `4c1898aa0a3cf3ba013e8d7f63a84062eb3a8466bcfe3f5823d28f457bd55e97` (143 rows across the whole file: 141 `item`, 1 `structural`, 1 `blocker` in the post-cutoff region at lines 541–545; 105 rows in the legacy tail from line 662 to EOF: 105 `item`, 0 `blocker`).
2. **WP9.3's handle-bound reader refuses the repository junction (`research_system/legacy/reader.py:12-14,140-206,240-248`):**
   - `LegacyReader.__init__` (`research_system/legacy/reader.py:240-248`) checks `_is_within(self.vault_root, self.repository_root)` and raises `LegacyReadError("the vault is read through its real path, never through the repository")` if `vault_root` is inside `repository_root`.
   - `handle_bound_read(root, relative_path)` (`research_system/legacy/reader.py:140-206`) validates every parent directory and the target file with `_is_reparse_or_symlink` (`reader.py:109-116`, checking `Path.is_symlink()` and Windows `FILE_ATTRIBUTE_REPARSE_POINT = 0x0400`, `reader.py:41`) and verifies through `os.path.realpath` on the open file descriptor (`reader.py:182`) that the opened handle resolves strictly inside `root` with matching `(st_dev, st_ino)` (`reader.py:179-197`).

#### 4.3.2 How `tools/check_legacy_log_baseline.py` resolves `--vault-root`

Following `P-083` item 2 (`m-3`, `03-decisions-and-open-questions.md:5471`) and `research_system/legacy/reader.py:140-206,240-248`:
- `tools/check_legacy_log_baseline.py` requires `--vault-root <path>` on the command line (no silent fallback to `<repo>/vault`).
- Before reading `04-Methods/Computational-Log.md`, it checks:
  1. `_is_reparse_or_symlink(Path(vault_root))` is `False` (if the caller passes `C:\Users\steph\TDL\vault`, it fails closed immediately with `ERROR: vault_computational_log: vault_root must be the real vault directory, not a junction or symlink: C:\Users\steph\TDL\vault`);
  2. `_is_within(Path(vault_root).resolve(), repository_root.resolve())` is `False` (`ERROR: vault_computational_log: vault_root is inside repository_root`); and
  3. reads `04-Methods/Computational-Log.md` exclusively through `handle_bound_read(Path(vault_root), "04-Methods/Computational-Log.md")` (`research_system/legacy/reader.py:140-206`).

#### 4.3.3 Open pre-code U-4 step (`P-089` item 3)

Per `P-089` item 3 (`03-decisions-and-open-questions.md:6094-6095`) and Handover §3 item 9:
- **Open gap:** Re-verify the live metadata (`Get-Item`, `Get-FileHash -Algorithm SHA256`, never reading file contents into agent context) of `C:\Users\steph\TDL\vault` and `C:\Users\steph\Documents\TDA-Research\04-Methods\Computational-Log.md` on the operator machine, and record the result in the table below before WP9.5 code is dispatched.
- **Exact read-only PowerShell commands for the reviewing session (on Stephen's authorization):**
  ```powershell
  Get-Item -LiteralPath "C:\Users\steph\TDL\vault" | Select-Object FullName, Attributes, LinkType, Target
  Get-Item -LiteralPath "C:\Users\steph\Documents\TDA-Research\04-Methods\Computational-Log.md" | Select-Object FullName, Length, LastWriteTimeUtc, Attributes, LinkType
  Get-FileHash -LiteralPath "C:\Users\steph\Documents\TDA-Research\04-Methods\Computational-Log.md" -Algorithm SHA256 | Select-Object Algorithm, Hash
  ```

| Path | Property | Prior recorded evidence (`01-current-system-evidence.md:357`; `w9-segmentation-contract-v1.md:242`) | Live U-4 verification (to be recorded by reviewing session before code dispatch) |
|---|---|---|---|
| `C:\Users\steph\TDL\vault` | `Attributes`, `LinkType`, `Target` | `Directory, ReparsePoint`; `Junction` -> `C:\Users\steph\Documents\TDA-Research` | **OPEN GAP (U-4)** — Owner: Stephen authorizes; reviewing session runs and records here |
| `C:\Users\steph\Documents\TDA-Research\04-Methods\Computational-Log.md` | `Length`, `LastWriteTimeUtc`, `SHA256` | `376,784` bytes; SHA-256 `4c1898aa0a3cf3ba013e8d7f63a84062eb3a8466bcfe3f5823d28f457bd55e97` (at WP9.2 contract measurement) | **OPEN GAP (U-4)** — Owner: Stephen authorizes; reviewing session runs and records here |

---

## 5. The registration manifest export (M-6)

### 5.1 Why the manifest exists and why CI cannot read the control store

- Under `06v` D-1 (`06v-w9-implementation-plan.md:561`), the W9 control store lives outside the repository working tree (`C:\Users\steph\.ars\stores\w9-production\`).
- GitHub Actions runners (`windows-latest`) have only the checked-out Git repository (`ZK-Theory/TDL`); they have no access to `C:\Users\steph\.ars\stores\w9-production\`.
- Therefore, WP9.3 established `.research-system/evidence/w9/registration-manifest.json` (`REGISTRATION_MANIFEST`, `research_system/legacy/evidence.py:37,40,114-131`) as the committed in-repository mirror of the store's registered legacy path set.
- Both WP9.3's observation preparer (`LR-015`, which calls `evidence.require_registered` at `research_system/legacy/preparers.py:216` / `evidence.py:114-131`) and WP9.5's post-merge detector (`tools/check_legacy_writes.py`) read `.research-system/evidence/w9/registration-manifest.json` from Git at `git_head`.

### 5.2 When it is written and checked

1. **Per registration batch, before that batch's first observation (`06v:483-484`):**
   - After a registration batch's `legacy-path-registration` records are appended to the external store (`LR-003`) and **before** any `legacy-artifact-observation` record for that batch is proposed (`LR-015`), the operator exports `.research-system/evidence/w9/registration-manifest.json` from the store, commits it to `main` via a reviewed PR, and advances the store binding's `git_head` to that commit.
   - Note that WP9.3's `prepare_observation` (`research_system/legacy/preparers.py:216`) already enforces this order automatically: `evidence.require_registered` (`research_system/legacy/evidence.py:114-131`) reads `.research-system/evidence/w9/registration-manifest.json` from Git at the store binding's `git_head` and raises `LegacyEvidenceError("registration is missing from committed registration manifest")` if the registration is not yet committed in `registration-manifest.json` at `git_head`.
2. **Before every batch (`06v:604` batch checklist):**
   - Step 3 of the batch checklist (`06v-w9-implementation-plan.md:604`) runs the manifest exporter in `--check` mode against the store and the store binding's `git_head`, failing closed if the committed manifest at `git_head` does not equal the store's registered set.

### 5.3 Exact mechanism: `tools/export_w9_registration_manifest.py`

- **What it reads:**
  - Takes `--control-root <path>` (the W9 control store root) and `--repository-root <path>` (default `.`), plus either `--output <path>` (export mode) or `--check` (verify mode against the committed manifest at the store binding's `git_head`).
  - Replays the store's projection state via `LegacyReplayEngine(Path(control_root)).replay()` (`research_system/legacy/replay/engine.py`, using the same read-only projection pattern as `_legacy_projection` in `research_system/cli.py:1648-1659`).
  - Extracts `state["records"]["legacy_path_registration"]` (`research_system/legacy/replay/reducers.py:66`). (Note: under `LR-056`, `legacy-path-registration` is not a supersession target in `research_system/legacy/contracts.py`, so every recorded `legacy_path_registration` record in `state["records"]["legacy_path_registration"]` is active.)
- **How entries are projected and sorted:**
  - Under WP9.3's current `require_registered` (`research_system/legacy/evidence.py:114-131`), each entry has closed keys `{"root_kind", "root_id", "normalized_path"}`:
    ```json
    {
      "format": "w9-registration-manifest/1",
      "registrations": [
        {
          "normalized_path": "contracts/Validation-Table.md",
          "root_id": "ZK-Theory/TDL",
          "root_kind": "repository_root"
        }
      ]
    }
    ```
  - **Role and root-registration visibility (Owner Point A, §16):**
    `tools/check_legacy_writes.py` needs to distinguish:
    1. `role == "shared_enforcement_surface"` (Rule 3, `06v:479-481`) from other registered repository roles (Rule 1, `06v:477`); and
    2. `role == "legacy_manuscript_root"` (`papers/P01-A-JRSSA/` and `papers/P01-B-JRSSB/`, which under WP9.4 Owner Point K, `P-086` item 11, are registered as directory roots ending in `/` whose member files are observed under the root registration and not registered individually) from `role == "successor_results_root"` (`results/ars/`, which is the successor output root where successor writes are allowed, `W9:161,329`).
    - In `research_system/legacy/evidence.py:125`, `require_registered` currently validates each entry with `_closed(entry, {"root_kind", "root_id", "normalized_path"}, "registration manifest entry")`.
    - Under **Owner Point A (Option A1, Recommended)**, `registration-manifest.json` includes `"role"` in each entry (`{"root_kind", "root_id", "normalized_path", "role"}`), and `_closed` in `research_system/legacy/evidence.py:125` is updated to allow `"role"` (`_closed(entry, {"root_kind", "root_id", "normalized_path", "role"}, ...)` or allowing optional `"role"` for backward compatibility with existing WP9.3 unit fixtures).
    - Under **Owner Point A (Option A2, Alternative)**, `registration-manifest.json` keeps only the 3 keys `{"root_kind", "root_id", "normalized_path"}` (`evidence.py:125` untouched), and `registration-manifest.json` is accompanied by (or `tools/check_legacy_writes.py` reads) a role-annotated or shared-surface list.
  - Entries in `"registrations"` are deduplicated and sorted canonically by `(entry["root_kind"], entry["root_id"], entry["normalized_path"])` and serialized with `canonical_bytes` (`research_system/core/canonical.py`, 2-space pretty JSON with trailing `\n` for committed evidence files).
- **How `--check` mode works (store-equals-manifest check):**
  1. Reads `binding = state["store_binding"]`; if `binding is None`, fails closed (`ERROR: registration_manifest: control store has no active store binding`).
  2. Reads `.research-system/evidence/w9/registration-manifest.json` from Git at `binding["git_head"]` via `evidence.read_evidence(repository_root, binding["git_head"], evidence.REGISTRATION_MANIFEST)` (`research_system/legacy/evidence.py:86-99`).
  3. Compares the projected list of registrations from `state["records"]["legacy_path_registration"]` against `manifest["registrations"]`.
  4. If any entry is present in the store but missing from the manifest at `git_head`, or present in the manifest at `git_head` but missing from the store, fails closed (exit `1`) naming every mismatched `(root_kind, root_id, normalized_path)`.
- **Test (M-6):**
  - In `tests/research_system/integration/test_w9_wp9_5_detectors.py`, a test builds a scratch W9 store and scratch Git repo under `tmp_path`, registers paths across `repository_root` and `vault_root` (including a `shared_enforcement_surface` contract and a `legacy_manuscript_root`), exports `registration-manifest.json`, commits it, rebinds `git_head`, and asserts:
    1. `export_w9_registration_manifest.py --check` exits `0`;
    2. registering one additional path in the store without re-exporting causes `--check` to exit `1` with `store_manifest_mismatch`; and
    3. manually adding an extra unregistered entry to `registration-manifest.json` causes `--check` to exit `1` with `store_manifest_mismatch`.

---

## 6. The post-merge first-parent detector (`tools/check_legacy_writes.py` and `.github/workflows/legacy-write-detector.yml`)

### 6.1 What it reads and where it runs

- **Script:** `tools/check_legacy_writes.py`
- **Workflow:** `.github/workflows/legacy-write-detector.yml` (`runs-on: windows-latest`, `defaults: run: shell: bash`; committed with `on: workflow_dispatch:` only in WP9.5 until L-1 per §10).
- **Where it runs:**
  1. On the operator machine before every batch (`06v:602-603` batch checklist) with `--ruleset-check require`.
  2. In CI (`.github/workflows/legacy-write-detector.yml`) on manual `workflow_dispatch` after WP9.5 merges, and on `push: branches: [main]` + weekly `schedule:` once L-1 is authorized by Stephen (`06v:490-492,591-594`).
  3. In automated tests (`tests/tools/test_w9_detectors.py` and W9-T7 in `tests/research_system/integration/test_w9_wp9_5_detectors.py`) on scratch clones under `tmp_path` with `--ruleset-check skip` and `--pr-map <json>`.
- **Inputs read from Git (always with `--no-replace-objects`):**
  1. The baseline commit SHA `<baseline>` and target commit SHA `<head>` (default `HEAD`).
  2. `.research-system/evidence/w9/registration-manifest.json` at `<head>` via `git --no-replace-objects show <head>:.research-system/evidence/w9/registration-manifest.json`, validated by `evidence.require_registered` (`research_system/legacy/evidence.py:114-131`).
  3. `.research-system/evidence/w9/legacy-write-records.json` at `<head>` (the W9 §4.2 record file, §6.4; Owner Point B).
  4. `.research-system/evidence/w9/shared-surface-changes.json` at `<head>`, validated by `evidence.require_change_list` (`research_system/legacy/evidence.py:190-252`; §6.5 and Owner Point D).
  5. First-parent commit chain `git --no-replace-objects rev-list --first-parent --reverse <baseline>..<head>` and each commit's first-parent tree delta `git --no-replace-objects diff-tree -r --no-renames -z <P1> <C>`.

### 6.2 The recorded baseline commit it walks from, and why (Owner Point C)

Why the choice of `<baseline>` is load-bearing:
- The APM prose freeze merged in PR `#126` at commit `4b143c9225035cc29e37351445f1c3a4ab09ceb1` on `2026-07-18T12:19:45Z` (`docs/plans/agentic-research-system/01-current-system-evidence.md:283`; `research_system/legacy/reader.py:45`).
- Between `4b143c92` and today's `main` (`dbd54fe38`), `main`'s first-parent history contains the seven post-freeze writer events audited in G7-A §11 and `W9` §4.1 (`09-migration-compatibility-and-pilot.md:148-159`; `docs/plans/agentic-research-system/transition/W0-legacy-closeout-post-terminal-addendum-2026-10-21.md:332-343`):
  - `1af52f6d` (`#127`, 2026-07-18): 32-file P01-B reconciliation merge;
  - `5df0c001` (2026-08-05): unreviewed direct push touching 7 files under `results/trajectory_tda_integration/stage1/` (reverted on 2026-08-06 by `#219` / `b132406e`);
  - `811d5a2b` (2026-08-05): unreviewed direct push touching 3 manifests under `contracts/manifests/input-provenance/` (reverted on 2026-08-06 by `#219` / `b132406e`);
  - `#168` (`2ef7d8fc`) and `#169` (`17fb5f4d`): LF normalization touching 29 legacy files;
  - `#277` (`3c64a021`): Ruff cleanup touching `papers/P01-A-JRSSA/drafts/sections/compute_table1_effects.py`;
  - `#368` (`3fa437a1`): `Validation-Table.md` precision edit.
- Because `tools/check_legacy_writes.py` walks **commit-by-commit** along `--first-parent <baseline>..<head>`, if the live detector on `main` walked from `4b143c92` on every run, it would visit `5df0c001` and `811d5a2b` on every run and permanently fail (even though `#219` / `b132406e` restored their blobs one day later), and it would also fail on `1af52f6d`, `#168`, `#169`, `#277`, and `#368` unless retroactive §4.2 JSON records were fabricated for pre-W9 commits.
- Conversely, W9-T7 (`06v:228,493`) specifically tests that when `<baseline>..<head>` spans `5df0c001` or `811d5a2b` on a scratch clone with a fixture manifest listing the files they touched, the detector **does** flag both commits!
- Therefore (Owner Point C, §16):
  - **Recommended (Option C1):** The detector reads its default live baseline commit from a pinned field or constant set at L-1 activation (specifically, the L-1 activation commit on `main`, which is a descendant of `dbd54fe38` where the pre-registration inventory has already been reconciled by G7-A §11 and verified by WP9.3's baseline lock checks), while also accepting `--baseline <sha>` on the command line so W9-T7 can walk `a426b731..5df0c001` and `811d5a2b~1..811d5a2b` (or `4b143c92..811d5a2b`).
  - **Alternative (Option C2):** Walk from `4b143c9225035cc29e37351445f1c3a4ab09ceb1` on every live run, which requires committing a historical pre-L-1 disposition table for the G7-A §11 commits (`1af52f6d`, `5df0c001` + `b132406e` revert pair, `811d5a2b` + `b132406e` revert pair, `2ef7d8fc`, `17fb5f4d`, `3c64a021`, `3fa437a1`) and suppressing that historical table during W9-T7.

### 6.3 First-parent diff semantics (`5df0c001` merge-subject / 2-parent handling and `811d5a2b` direct push)

1. **Refusing shallow clones and non-ancestor baselines:**
   - Before walking commits, `tools/check_legacy_writes.py` runs:
     - `git --no-replace-objects rev-parse --is-shallow-repository` -> if `"true"`, fails closed with `ERROR: post_merge_first_parent: shallow repository is not supported` (matching `research_system/legacy/acceptance.py:89-90`).
     - `git --no-replace-objects merge-base --is-ancestor <baseline> <head>` -> if exit code != 0, fails closed with `ERROR: post_merge_first_parent: baseline <baseline> is not an ancestor of <head>`.
2. **How the first-parent diff of each commit $C$ is computed (both 1-parent and 2-parent commits):**
   - The detector lists first-parent commits oldest-first:
     `git --no-replace-objects rev-list --first-parent --reverse <baseline>..<head>`
   - For each commit $C$ in that list, it queries its parent list:
     `git --no-replace-objects rev-list --parents -n 1 <C>`
     which returns `<C> <P1> [<P2> ...]`. Because `<baseline>` is an ancestor of `<head>` and $C \in (\text{baseline}, \text{head}]$, $C$ always has at least one parent, and `<P1>` (`C^1`) is its first parent on `main`.
   - The detector computes the tree delta between `<P1>` and `<C>` explicitly:
     `git --no-replace-objects diff-tree -r --no-renames -z <P1> <C>`
   - **Why passing `<P1> <C>` explicitly is mandatory for 2-parent merge commits:**
     - If one invokes `git diff-tree -r <C>` with a single commit argument on a 2-parent merge commit (without `-m` or `-c`), Git outputs **zero lines** by default, silently hiding every file changed by the merge!
     - By passing both tree-ish arguments `<P1> <C>`, `git diff-tree -r --no-renames -z <P1> <C>` compares the tree of the previous `main` commit `<P1>` directly against the tree of `<C>`. For a 1-parent commit (a squash merge or direct push), `<P1>` is its sole parent; for a 2-parent merge commit, `<P1>` is the `main` parent and the diff outputs every file added, modified, or deleted on `main` by the merged branch, with its exact old 40-hex blob SHA at `<P1>` (`0000000000000000000000000000000000000000` on file creation) and new 40-hex blob SHA at `<C>` (`0000000000000000000000000000000000000000` on file deletion).
     - Passing `--no-renames` disables rename/copy pairing so a rename is emitted as two separate records (a deletion of the old path with `old_blob -> 0000...` and an addition of the new path with `0000... -> new_blob`). Neither the old path nor the new path can evade a registration or `results/` prefix check via rename detection.
3. **How `5df0c001` and `811d5a2b` behave under this rule (and the verified repository genealogy of `5df0c001`):**
   - In repository history (`W0-legacy-closeout-post-terminal-addendum-2026-10-21.md:334-340`; `docs/plans/agentic-research-system/reviews/g7a-w0-post-terminal-addendum-re-review-8988f463-2026-10-22.md:203-215`):
     - PR `#215` merged into `main` as the two-parent merge commit `a426b731` (which touched no legacy result file).
     - Commit `5df0c001` (`2026-08-05`) is a commit on `main` whose first parent is `a426b731` and whose commit message subject reuses `"Merge pull request #215 from ..."`, while modifying 7 files under `results/trajectory_tda_integration/stage1/`.
     - Commit `811d5a2b` (`2026-08-05`) is a single-parent direct push on `main` with no PR that modified 3 files under `contracts/manifests/input-provenance/`.
     - Both were reverted on `2026-08-06` by PR `#219`, which merged as the two-parent merge commit `b132406e`.
   - Under `git --no-replace-objects diff-tree -r --no-renames -z <P1> <C>`:
     - Whether a commit on `main` is a two-parent merge commit (like `a426b731` or `b132406e`) or a single-parent commit carrying a `"Merge pull request #215..."` subject (like `5df0c001`) or a single-parent direct push (like `811d5a2b`), `diff-tree <P1> <C>` extracts the exact `(old_blob, new_blob, path)` triples introduced onto `main` at that step.
   - **How each first-parent commit $C$ is mapped to its PR (and why commit-subject spoofing cannot bypass it):**
     - `06v:486-488` notes: *"The detector maps each squash commit to its PR through the merge-queue derivation that `tools/check_merge_admission.py` already performs."*
     - Inspection of `tools/check_merge_admission.py:700-738` and `.github/workflows/merge-admission.yml:127-130` shows that during a pre-merge `merge_group` run, `merge-admission.yml:128-129` extracts the PR number from the ephemeral ref `refs/heads/gh-readonly-queue/main/pr-<number>-<base_sha>`, while `check_merge_admission.py:703-709` (`evaluate_merge_group_size`) enforces that the queue merges one entry at a time (`total_commits <= 1`). Once the squash commit lands on `main`, the ephemeral `gh-readonly-queue` ref no longer exists.
     - For a post-merge commit $C$ on `main`, `tools/check_bypass_merges.py:93-111,169` already implements the post-merge commit-to-PR lookup via `gh api repos/ZK-Theory/TDL/commits/<C>/pulls`.
     - However, look closely at `merging_pull(pulls, sha)` in `tools/check_bypass_merges.py:93-111`:
       - Lines 98–100 return the PR where `pull.get("merged_at")` is non-empty and `pull.get("merge_commit_sha") == sha`.
       - Lines 101–110 then fall back to the earliest merged PR in `pulls` even when `merge_commit_sha != sha`! For a commit on `main`, if that fallback were used, any earlier PR whose branch happens to be an ancestor of $C$ could be returned even if $C$ itself was a direct push!
     - Therefore, `tools/check_legacy_writes.py` defines strict PR resolution:
       1. **Live mode (CI and operator pre-batch run):** Only when a commit $C$ touches at least one guarded path (so routine ARS commits that touch no guarded path need zero API calls!), query `gh api repos/ZK-Theory/TDL/commits/<C>/pulls` and accept a PR **if and only if** `pull.get("merged_at")` is non-empty **and** `pull.get("merge_commit_sha") == C`.
          - Under this exact rule, for `5df0c001`, PR `#215` has `merge_commit_sha == "a426b731..." != "5df0c001..."`, so `5df0c001` maps to `pr_number = None` (an unmapped direct push) even though its commit subject says `"Merge pull request #215..."`! And even if `#215` were tested as a candidate PR number, there is no §4.2 record for `#215` with `5df0c001`'s 7 file blobs, so `5df0c001` fails closed both ways.
          - For `811d5a2b`, `commits/811d5a2b.../pulls` has no PR with `merge_commit_sha == "811d5a2b..."`, so `811d5a2b` maps to `pr_number = None` and fails closed.
       2. **Offline fixture mode (`--pr-map <path>`, for scratch-clone tests only):** Reads a JSON dict `{"<40-hex-commit-sha>": <int_pr_number_or_null>}` supplied by the test harness. Commit-subject regex parsing (`\(#([0-9]+)\)$` or `^Merge pull request #([0-9]+) `) is never trusted by itself to authorize a §4.2 write in live mode.

### 6.4 The W9 §4.2 record: location, format, and keying by PR number + old/new blobs (Owner Point B)

- **Authority:** `W9` §4.2 (`09-migration-compatibility-and-pilot.md:172-181`) and `06v` §5 (`06v-w9-implementation-plan.md:477-488`).
- **Why keyed by PR number + old/new blob instead of commit SHA (`06v:88-90,486-488`):**
  - Under ruleset `20822054`, `main` is squash-merged one PR at a time through the merge queue (`tools/check_merge_admission.py:703-709`), and a post-merge workflow cannot push a commit back to `main`.
  - A PR that performs an authorized W9 §4.2 write must carry its own §4.2 record inside the PR itself so the post-merge detector passes as soon as the PR merges onto `main`.
  - Inside the PR (before entering the merge queue), the PR's squash commit SHA on `main` does not exist yet—but the **PR number** and **each touched file's `old_blob` (on `main`) and `new_blob` (in the PR tree)** are completely determined!
- **Location (Owner Point B, §16):**
  - Path: `.research-system/evidence/w9/legacy-write-records.json` (to be added as a dated row in `docs/plans/agentic-research-system/implementation/06v-addendum-2026-11-10-w9-paths.md` on Stephen's approval of Owner Point B).
  - If no authorized §4.2 write has ever occurred yet, the file either contains `{"format": "w9-legacy-write-records/1", "records": []}` or (before L-1) may be absent if zero guarded writes occur in `<baseline>..<head>`; if present and malformed, the detector fails closed immediately.
- **Closed JSON schema (`w9-legacy-write-records/1`):**
  ```json
  {
    "format": "w9-legacy-write-records/1",
    "records": [
      {
        "pr_number": 277,
        "allowance_kind": "repo_wide_change_4_2_b",
        "owner_note": {
          "author": "stephen",
          "source_ref": "docs/plans/agentic-research-system/03-decisions-and-open-questions.md#P-099",
          "note_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        },
        "independent_review": {
          "reviewer_id": "independent-reviewer-session",
          "review_path": "docs/plans/agentic-research-system/reviews/pr277-semantic-equivalence-review.md",
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
- **Validation invariants (`require_legacy_write_records` in `research_system/legacy/evidence.py`):**
  1. Top-level closed keys: `{"format", "records"}`, with `"format" == "w9-legacy-write-records/1"` and `"records"` a `list`.
  2. Each record has closed keys `{"pr_number", "allowance_kind", "owner_note", "independent_review", "files"}`:
     - `pr_number`: positive integer (`isinstance(v, int) and not isinstance(v, bool) and v >= 1`), unique across `"records"`.
     - `allowance_kind`: one of:
       - `"repo_wide_change_4_2_b"` (`W9` §4.2 item 1b: requires both `owner_note` with `author == "stephen"` and `independent_review` naming a committed review path at `<head>` whose Git blob SHA-256 matches `review_sha256`);
       - `"owner_ruling_4_2_c"` (`W9` §4.2 item 1c: requires `owner_note` with `author == "stephen"` and `source_ref` pointing to a decision-register entry `03-decisions-and-open-questions.md#P-...`; `independent_review` may be `null` only for `owner_ruling_4_2_c`);
       - `"shared_surface_4_3"` (`W9` §4.3: requires both `owner_note` with `author == "stephen"` and `independent_review` for the independent reviewer's affected-registration derivation).
       *(Note: `W9` §4.2 item 1a — "a legacy-lane commit the freeze permits" — is excluded while the APM freeze stands because the freeze permits none, `W9:173`.)*
     - `files`: non-empty list of closed objects `{"normalized_path", "old_blob", "new_blob"}` where `normalized_path` is a normalized repository-relative POSIX path and `old_blob`, `new_blob` match `^[0-9a-f]{40}$` with `old_blob != new_blob`.
  3. **All-or-nothing PR coverage (`W9:174`):** For a given commit $C$ mapped to `pr_number`, the record's `files` list must cover **every** registered file and every `results/`-outside-`results/ars/` file that $C$ touched, with exact `(normalized_path, old_blob, new_blob)` match. If a PR touches three registered files and its §4.2 record lists only two, the commit fails closed.

### 6.5 The three rules of `tools/check_legacy_writes.py` (including O-32 / Rule 3)

For each first-parent commit $C \in (\text{baseline}, \text{head}]$ with first parent $P_1$ and changed file triples $(p, b_{\text{old}}, b_{\text{new}}) \in \text{diff-tree}(P_1, C)$:

#### Rule 1 — Registered legacy files (`06v:477`; `W9:172-181`)

- **Matching rule:** A changed path $p$ matches a `repository_root` entry $r$ in `registration-manifest.json` if:
  - $r.\text{normalized\_path}$ does not end with `/` and $\text{casefold}(p) == \text{casefold}(r.\text{normalized\_path})$ (case-folded path equality on Windows, `P-087` item 3); OR
  - $r.\text{normalized\_path}$ ends with `/` (a `legacy_manuscript_root` directory registration such as `papers/P01-A-JRSSA/` or `papers/P01-B-JRSSB/`, `research_system/legacy/reader.py:295`, `P-086` item 11) and $\text{casefold}(p)$ starts with $\text{casefold}(r.\text{normalized\_path})$, excluding `role == "successor_results_root"` (`results/ars/`) and excluding `role == "shared_enforcement_surface"` (which is governed by Rule 3).
- **Requirement:** Commit $C$ must map to a valid `pr_number` (`merge_commit_sha == C`), and `legacy-write-records.json` at `<head>` must contain a valid record for `pr_number` covering $(p, b_{\text{old}}, b_{\text{new}})$ (plus every other guarded path touched by $C$).
- **Failure message (closed, exit 1):**
  `ERROR: post_merge_first_parent: Rule 1 violation at commit <C> (pr=<pr_or_none>): registered path '<p>' changed (<b_old> -> <b_new>) without a matching W9 §4.2 record`

#### Rule 2 — Any path under `results/` outside `results/ars/` (`06v:478`; `W9-D13`, `W9-D14`, `W9:172,188-189,197`)

- **Matching rule:** The changed path $p$'s case-folded first path component is `"results"` ($\text{casefold}(p)\text{ starts with }\text{"results/"}$) and its case-folded first two components are **not** `"results/ars"` ($\text{not }\text{casefold}(p)\text{ starts with }\text{"results/ars/"}$).
- **Why Rule 2 is independent of `registration-manifest.json` (`W9-D13`, `W9:188-189`):**
  Rule 2 catches writes to **unregistered** legacy result directories (such as P04, poverty, financial, or a newly created file under `results/trajectory_tda_integration/`) as well as writes that occur before a batch has registered all files under `results/`.
- **Requirement:** Commit $C$ must map to a valid `pr_number`, and `legacy-write-records.json` at `<head>` must contain a valid §4.2 record for `pr_number` covering $(p, b_{\text{old}}, b_{\text{new}})$.
- **Failure message (closed, exit 1):**
  `ERROR: post_merge_first_parent: Rule 2 violation at commit <C> (pr=<pr_or_none>): results path outside results/ars/ '<p>' changed (<b_old> -> <b_new>) without a matching W9 §4.2 record`

#### Rule 3 — `shared_enforcement_surface` contracts (`06v:212,479-481`; `O-32`; `W9` §4.3, `W9:183-189`)

- **How the detector knows which contracts are shared surfaces:**
  Under Owner Point A (Option A1, Recommended), each entry in `registration-manifest.json` carries `"role"`, and the set of shared enforcement surfaces is `{r["normalized_path"] for r in manifest["registrations"] if r["root_kind"] == "repository_root" and r["role"] == "shared_enforcement_surface"}` (for example, `contracts/Validation-Table.md`, `contracts/schemas/meta_contract_schema.yaml`, and the shared contract files registered with `role: "shared_enforcement_surface"`).
- **What Rule 3 requires when $P_1 \to C$ changes a `shared_enforcement_surface` path $s$ ($b_{\text{old}} \to b_{\text{new}}$):**
  1. **W9 §4.3 owner note and independent reviewer derivation:** Commit $C$ must map to `pr_number`, and `legacy-write-records.json` at `<head>` must contain a record for `pr_number` with `allowance_kind == "shared_surface_4_3"` (or `"repo_wide_change_4_2_b"`), `owner_note` authored by `"stephen"`, `independent_review` pointing to the committed reviewer derivation, and `(s, b_old, b_new)` in `files`.
  2. **Entry in `.research-system/evidence/w9/shared-surface-changes.json` (`w9-shared-surface-changes/1`):**
     The change list at `.research-system/evidence/w9/shared-surface-changes.json` must record the change to surface $s$ and its `affected_registrations` list (which WP9.3's `check_shared_surface_changes` in `research_system/legacy/acceptance.py:121-137` reads at `LR-016` and `LR-020` to force fresh post-change observations for affected results).
- **Contradiction surfaced for Stephen's decision (Owner Point D, §16 — Handover §5 stop-and-report item):**
  There is an exact specification conflict between `06v` (`06v:89-90,212,479-481`) and WP9.3's `research_system/legacy/evidence.py:197-198,231-238` + `research_system/legacy/acceptance.py:121-137`:
  - **`06v:89-90`:** *"Squash merges: `main` is squash-merged one entry at a time through the merge queue (`tools/check_merge_admission.py:703-709`). A commit SHA created by the queue cannot be named inside the PR that creates it."*
  - **`06v:212` (row `O-32`) and `06v:479-481`:** *"The PR that changes a shared surface carries its own entry in a committed change list in the W9 evidence area, naming the contract and its old and new blobs (a post-merge workflow cannot commit to `main` under ruleset 20822054). WP9.5: the detector fails when a merged shared-surface change has no entry, or has no W9 §4.3 owner note."*
  - **WP9.3 (`research_system/legacy/evidence.py:197-198,231-238` and `research_system/legacy/acceptance.py:135`):**
    In `evidence.py:231`, `_change_entries` validates each entry in `shared-surface-changes.json` with:
    `_closed(entry, {"merge_commit", "surface", "affected_registrations"}, "shared-surface change entry")`
    where `merge_commit` must be a 40-hex Git commit SHA (`_SHA1`), and `old_blob`, `new_blob`, and `pr_number` are **rejected** by `_closed`! Then `acceptance.py:135` checks:
    `if not evidence.is_ancestor(repository_root, entry["merge_commit"], str(source.get("git_commit"))): raise LegacyEvidenceError("affected result has no observation at or after shared-surface change")`
  - **Why these two cannot both hold simultaneously without a decision:**
    - If the PR changing the shared surface carries its own entry inside that PR (as `06v:212,479-481` requires so the post-merge detector passes on that PR's squash commit $C$), the PR cannot put its own squash commit SHA $C$ into `merge_commit` because $C$ is created by the merge queue after the PR is queued (`06v:89-90`).
    - Nor can the PR put its branch head commit into `merge_commit`, because after a squash merge onto `main`, the PR branch head is **not** an ancestor of `main` (`is_ancestor` in `acceptance.py:135` would return `False` for every subsequent `main` commit!).
    - And if the PR puts its `main` base commit $P_1$ (the commit before the merge) into `merge_commit`, then an old observation taken at $P_1$ (before the shared surface changed!) satisfies `is_ancestor(P_1, P_1) == True` (`git merge-base --is-ancestor X X` exits 0), so `acceptance.py:135` would falsely treat a pre-change observation at $P_1$ as being "at or after" the shared-surface change!
  - Per Handover §5 (*"the plan, W9 and the WP9.3 formats contradict each other in a way that changes a detector's behaviour. Give both citations; do not choose for Stephen"*), this note does **not** choose for Stephen; §16 **Owner Point D** presents the exact options (Option D1: widen `_change_entries` in `evidence.py:231` to key by `pr_number`, `old_blob`, `new_blob`, and `base_commit` with strict non-reflexive descendant check `base_commit != obs_commit and is_ancestor(base_commit, obs_commit)` in `acceptance.py:135`; vs Option D2: keep `evidence.py:231` and `acceptance.py:135` unchanged and use a two-PR protocol for shared-surface changes).
- **Failure message (closed, exit 1):**
  `ERROR: post_merge_first_parent: Rule 3 violation at commit <C> (pr=<pr_or_none>): shared_enforcement_surface '<s_path>' changed (<b_old> -> <b_new>) without a valid shared-surface-changes.json entry and W9 §4.3 owner note`

### 6.6 What `tools/check_legacy_writes.py` does with an unreadable registered file or unmappable commit

1. **Missing or malformed evidence files at `<head>`:**
   - If `.research-system/evidence/w9/registration-manifest.json` is absent or fails `require_registered` at `<head>` (once L-1 is active or when `--require-manifest` is passed), or if `legacy-write-records.json` or `shared-surface-changes.json` fails schema validation, `tools/check_legacy_writes.py` fails closed (exit `1`) with `ERROR: post_merge_first_parent: invalid evidence file at <head>:<path>: <reason>`.
2. **Registered `repository_root` file missing or unreadable at `<head>`:**
   - For every `repository_root` entry in `registration-manifest.json` at `<head>`, the detector verifies that the path (or directory tree, if ending in `/`) exists in `<head>`'s Git tree via `git --no-replace-objects cat-file -e <head>:<normalized_path>` and that for regular file registrations its Git object type is `blob` (`git --no-replace-objects cat-file -t <head>:<normalized_path> == "blob"`). If any registered `repository_root` path is missing from `<head>` or is not a readable blob/tree, the detector fails closed (exit `1`) with:
     `ERROR: post_merge_first_parent: registered repository_root path '<normalized_path>' is missing or unreadable at <head>`
3. **Unmappable commit:**
   - If any commit $C \in (\text{baseline}, \text{head}]$ touches a path matching Rule 1, Rule 2, or Rule 3 and cannot be mapped to a merged PR with `merge_commit_sha == C` (or via `--pr-map` in offline test mode), `pr_number` is `None` and the detector fails closed (exit `1`) with `pr=none` in the Rule 1 / Rule 2 / Rule 3 error message.

---

## 7. The `CONVENTIONS.md` legacy-lock check (`tools/check_conventions_legacy_locks.py`)

### 7.1 Authority and baseline constants

- **Authority:** `W9` §4.4 (`09-migration-compatibility-and-pilot.md:198`), `W9` §5.5 (`:302-304`), `W9` §7.3 items 1, 2, and 4 (`:385-407`), `06v` §3 row `O-12` (`06v-w9-implementation-plan.md:163`), `06v` §4 row `W9-T19` (`:240`), and `w9-segmentation-contract-v1.md` §3 (`docs/plans/agentic-research-system/transition/w9/w9-segmentation-contract-v1.md:83-138,244`).
- **Pinned baseline constants (`CONVENTIONS_LOCK` in `research_system/legacy/reader.py:43-49`):**
  - Baseline commit: `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (PR `#126`, `2026-07-18T12:19:45Z`)
  - Baseline Git blob SHA-1: `4620c71607ca3a06c6df3b8e96a6bddffc783960`
  - Baseline byte length: `33,645` bytes
  - Baseline content SHA-256: `d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589`

### 7.2 What it reads

1. **Baseline bytes:**
   - Reads `CONVENTIONS.md` at `4b143c9225035cc29e37351445f1c3a4ab09ceb1:CONVENTIONS.md` via `git --no-replace-objects cat-file blob 4620c71607ca3a06c6df3b8e96a6bddffc783960` (or from `--baseline-file <path>` in standalone unit tests).
   - Verifies before segmentation that `len(baseline_raw) == 33645`, `git_blob_id(baseline_raw) == "4620c71607ca3a06c6df3b8e96a6bddffc783960"`, and `sha256_hex(baseline_raw) == "d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589"`. Any mismatch fails closed (`ERROR: conventions_repository_check: baseline blob verification failed`).
2. **Candidate bytes:**
   - By default, reads `CONVENTIONS.md` from the repository root via `handle_bound_read(repository_root, "CONVENTIONS.md")` (`research_system/legacy/reader.py:140-206`), or from `--candidate-file <path>` / `--git-ref <ref>:CONVENTIONS.md` when testing byte copies or historical commits.
3. **Segmentation:**
   - Segments both `baseline_raw` and `candidate_raw` with `segment_bytes(..., profile="conventions_unit", region=None)` from `research_system/legacy/segmentation.py:429-488` and `tools/w9_segmentation.py:461-518` (`segmenter_version == "w9-segmentation/1.0.0"`), asserting that both segmenters produce identical output dicts.

### 7.3 Granularity and section classification (`W9` §5.5 and §7.3)

- **Unit granularity (`conventions_unit`, `w9-segmentation-contract-v1.md:83-138`; `tools/w9_segmentation.py:388-458`):**
  - Within each level-2 section (`^## ` at column 0), `conventions_unit` emits one `row_kind == "item"` row per:
    1. **Bullet unit:** starts at a column-0 bullet line (`- ` or `* `) and includes all following indented lines (`  ...` or `\t...`) and any blank lines that precede an indented continuation line of the same bullet (`w9-segmentation-contract-v1.md:107-112`; `tools/w9_segmentation.py:415-433`).
    2. **Table unit:** consecutive column-0 pipe lines (`|...`) (`w9-segmentation-contract-v1.md:114-116`; `tools/w9_segmentation.py:434-443`).
    3. **Paragraph unit:** consecutive non-blank lines that are not column-0 bullets, tables, horizontal rules (`^---[ \t]*$`), the footer (`^\*Last updated:.*\*[ \t]*$`), or ATX headings (`w9-segmentation-contract-v1.md:117-120`; `tools/w9_segmentation.py:444-457`).
  - Blank lines, `---` horizontal rules, the `*Last updated: ...*` footer, the H1 title/preamble before the first `## `, and ATX heading lines are structural (no item row emitted).
  - For every `conventions_unit` item row:
    - `anchor_text` is the enclosing `## ` section title (`w9-segmentation-contract-v1.md:124`);
    - `raw_row_sha256` (`unit_hash`, `w9-segmentation-contract-v1.md:126`) is the lowercase SHA-256 of the unit's exact slice `raw[byte_start:byte_end]`.
  - If two units within the same `## ` section have the same `raw_row_sha256`, the segmenter emits a `row_kind == "blocker"` row with `blocker_reason == "duplicate_anchor"` (`tools/w9_segmentation.py:500-510`).
- **Which sections hold legacy locks (`W9` §7.3 items 1 and 4, `09-migration-compatibility-and-pilot.md:385-393,404-407`):**
  - At baseline commit `4b143c92` (blob `4620c716`), `CONVENTIONS.md` has 10 `## ` sections and 70 units (`w9-segmentation-contract-v1.md:244`).
  - `W9` §7.3 item 1 (`09-migration-compatibility-and-pilot.md:388-390`) states:
    > *"Entries and locks about ARS itself (P00 and other ARS-lane entries, the 'ARS Foundation Governance' section's locks) are **successor** regardless of date."*
  - `W9` §7.3 item 4 (`09-migration-compatibility-and-pilot.md:404-407`) states:
    > *"Since #126, 117 successor lines have been inserted into the 'ARS Foundation Governance' section; under the object rule that whole section is successor, and the rule applies to sections that hold legacy locks."*
  - Therefore, the 10 baseline `## ` sections partition into:
    1. **9 legacy-lock sections** (all `## ` sections present at `4b143c92` except `"ARS Foundation Governance"`):
       - `"Research Assurance (locked 2026-06-02)"`
       - `"APM Prose Production Frozen — ARS Transition (locked 2026-07-17)"`
       - `"Authorship"`
       - `"Programme Structure (as of 2026-04-07)"`
       - `"Always"`
       - `"Never"`
       - `"Methodological Conventions"`
       - `"Citation Conventions"`
       - `"Computational Environment"`
    2. **1 wholly successor baseline section:**
       - `"ARS Foundation Governance"` (`SUCCESSOR_SECTIONS = frozenset({"ARS Foundation Governance"})`)
    3. **Post-baseline `## ` sections added after `4b143c92`:**
       - For example, `"Repo-Wide CI: Windows Only, Lint Blocks (locked 2026-09-08, amended 2026-09-11)"` (`CONVENTIONS.md:54`), which did not exist at `4b143c92` and is wholly successor.

### 7.4 Exact insertion-only decision rule

Given baseline segmentation $S_{\text{base}}$ (from blob `4620c716`) and candidate segmentation $S_{\text{cand}}$:

1. **File-level encoding invariants:**
   - `S_cand["file_facts"]["has_utf8_bom"]` must be `False` and `S_cand["file_facts"]["line_ending"]` must be `"LF"`. Otherwise fail closed with `ERROR: conventions_repository_check: file encoding/EOL violation (has_utf8_bom=..., line_ending=...)`.
2. **Zero blocker rows:**
   - Neither $S_{\text{base}}$ nor $S_{\text{cand}}$ may contain any row with `row_kind == "blocker"` (for example, `duplicate_anchor` caused by duplicating a unit within a section). Otherwise fail closed with `ERROR: conventions_repository_check: segmentation blocker at lines <start>-<end>: <blocker_reason>`.
3. **Legacy-lock section preservation (in order):**
   - Let $\mathcal{L} = [s_1, s_2, \dots, s_9]$ be the ordered list of distinct `anchor_text` values in $S_{\text{base}}$ after excluding `"ARS Foundation Governance"`.
   - Every section title $s_k \in \mathcal{L}$ must appear in $S_{\text{cand}}$, and the sequence of first appearances of $s_1, \dots, s_9$ in $S_{\text{cand}}$ must preserve their baseline relative order. If any legacy-lock section is missing or reordered, fail closed with:
     `ERROR: conventions_repository_check: legacy section '<s_k>' is missing, renamed, or reordered`
4. **Per-section ordered-subsequence (insertion-only) preservation of legacy units:**
   - For each legacy-lock section $s \in \mathcal{L}$:
     - Let $B(s) = [r_1, r_2, \dots, r_m]$ be the ordered list of baseline rows in $S_{\text{base}}$ with `anchor_text == s`. (Since $S_{\text{base}}$ has 0 blockers, all $m$ hashes $h_j = r_j[\text{"raw\_row\_sha256"}]$ in $B(s)$ are distinct.)
     - Let $C(s) = [c_1, c_2, \dots, c_n]$ be the ordered list of candidate rows in $S_{\text{cand}}$ with `anchor_text == s`, with hashes $u_i = c_i[\text{"raw\_row\_sha256"}]$.
     - **Existence check:** Every baseline unit hash $h_j \in B(s)$ must exist in $\{u_1, \dots, u_n\}$. If any $h_j$ is missing (which occurs whether a legacy bullet/paragraph/table was edited by 1 byte or deleted outright), fail closed with:
       `ERROR: conventions_repository_check: legacy unit modified or deleted in section '<s>' (baseline row_ordinal=<ord>, lines <line_start>-<line_end>, expected unit_hash=<h_j>)`
     - **Relative-order (subsequence) check:** Let $\text{idx}(h_j)$ be the index in $C(s)$ where $u_{\text{idx}(h_j)} == h_j$. We require $\text{idx}(h_1) < \text{idx}(h_2) < \dots < \text{idx}(h_m)$. If any two baseline units in section $s$ have been swapped or reordered, fail closed with:
       `ERROR: conventions_repository_check: legacy units reordered in section '<s>' (baseline row_ordinals <ord_a> and <ord_b>)`
     - **Inserted units are pure insertions:** Every candidate row $c_i \in C(s)$ whose hash $u_i \notin \{h_1, \dots, h_m\}$ is recognized as an inserted successor unit. (In current `CONVENTIONS.md` at `dbd54fe38`, for example, `## Always`, `## Never`, and `## Computational Environment` contain successor bullets and paragraphs inserted after `4b143c92`, while all baseline units in all 9 legacy-lock sections remain byte-identical and in order.)

### 7.5 What it outputs and where it runs

- **Output:** With `--json-out <path>` (or stdout in `--json` mode), writes a canonical JSON report:
  ```json
  {
    "format": "w9-conventions-check/1",
    "baseline_commit": "4b143c9225035cc29e37351445f1c3a4ab09ceb1",
    "baseline_blob": "4620c71607ca3a06c6df3b8e96a6bddffc783960",
    "candidate_sha256": "<64-hex>",
    "legacy_sections_checked": 9,
    "legacy_units_verified": 68,
    "inserted_successor_units": 31,
    "status": "ok"
  }
  ```
- **Where it runs:**
  - Before every batch on the operator machine (`06v:602` batch checklist).
  - In `.github/workflows/legacy-write-detector.yml` (on `workflow_dispatch` after WP9.5 merges, and on `push: branches: [main]` + weekly `schedule:` once L-1 activates; also testable in CI unit tests on every PR).

### 7.6 Negative and positive controls (`W9-T19`, `O-13`)

1. **Positive controls (must exit 0):**
   - Running against the baseline blob `4620c716` itself -> exits `0` (`inserted_successor_units == 0`).
   - Running against the current `CONVENTIONS.md` at `dbd54fe38` -> exits `0`.
   - Running against a byte copy of `CONVENTIONS.md` where a new successor bullet `- **Synthetic successor lock (locked 2026-11-21)**: ...` is inserted into `## Always` (a legacy-lock section) and another bullet is inserted into `## ARS Foundation Governance` (a successor section) -> exits `0`.
2. **Negative controls (`watched_to_fail`, must exit 1):**
   - **Control N1 (modified legacy bullet):** On a byte copy in `tmp_path`, change 1 character in the first legacy bullet of `## Always` (`- **Always validate TDA outputs**` -> `- **Always validate TDA output**`) -> exits `1` with `ERROR: conventions_repository_check: legacy unit modified or deleted in section 'Always'`.
   - **Control N2 (deleted legacy paragraph):** On a byte copy, delete the `**Rule**:` paragraph in `## Research Assurance (locked 2026-06-02)` -> exits `1` with `ERROR: conventions_repository_check: legacy unit modified or deleted in section 'Research Assurance (locked 2026-06-02)'`.
   - **Control N3 (reordered legacy bullets):** On a byte copy, swap the first two legacy bullets of `## Never` -> exits `1` with `ERROR: conventions_repository_check: legacy units reordered in section 'Never'`.
   - **Control N4 (duplicate unit within a section):** On a byte copy, duplicate an existing bullet verbatim inside `## Always` -> exits `1` with `ERROR: conventions_repository_check: segmentation blocker ... duplicate_anchor`.
   - **Control N5 (deleted/renamed legacy section heading):** On a byte copy, rename `## Citation Conventions` to `## Citation Rules` -> exits `1` with `ERROR: conventions_repository_check: legacy section 'Citation Conventions' is missing, renamed, or reordered`.

---

## 8. The vault Computational-Log detector (`tools/check_legacy_log_baseline.py`) and D-5 cadence

### 8.1 Authority and design constraints

- **Authority:** `W9` §4.4 (`09-migration-compatibility-and-pilot.md:196`), `W9` §7.3 items 1, 3, 4, and 5 (`:385-413`), `06v` §3 row `O-11` (`06v-w9-implementation-plan.md:162`), `06v` §4 row `W9-T19` (`:240`), `06v` §5 (`:494-496`), `06v` §6 `D-5` (`:567`) and `D-7` (`:570`), and `P-089` item 3 (`03-decisions-and-open-questions.md:6098-6101`).
- **No real L-0b export exists yet (`06v` D-7; `P-089` item 3):**
  - `ACCEPTED_CL_EXPORT` in `research_system/legacy/accepted_w9.py:86-88` is currently the empty tuple `()`.
  - Producing the real L-0b baseline export requires Stephen's authorization (`06v` D-7, `:570`) and is explicitly outside `P-089` ("Not authorized: ... L-0b", `03-decisions-and-open-questions.md:6087`).
  - Therefore, WP9.5 designs and tests `tools/check_legacy_log_baseline.py` against a **synthetic fixture export** in WP9.3's exact `w9-cl-export/1` format (`research_system/legacy/evidence.py:43,277-362`), and specifies the exact zero-code-rewrite switch when L-0b is accepted (§8.3).

### 8.2 What it reads and the exact comparison rule

1. **Inputs:**
   - `--vault-root <path>`: required real path to the vault directory (`C:\Users\steph\Documents\TDA-Research` on the operator machine, or a `tmp_path` directory in tests). Validated per §4.3.2 (`_is_reparse_or_symlink` is `False`, not inside `repository_root`). Reads `04-Methods/Computational-Log.md` via `handle_bound_read(Path(vault_root), "04-Methods/Computational-Log.md")` (`research_system/legacy/reader.py:140-206`).
   - Baseline export source (mutually exclusive):
     - **Production mode (`--repository-root <repo> --git-commit <sha>`, default `HEAD`):**
       Reads the latest accepted export descriptor from `ACCEPTED_CL_EXPORT` (`research_system/legacy/accepted_w9.py:86-88`). If `ACCEPTED_CL_EXPORT` is empty `()`, fails closed immediately with:
       `ERROR: vault_computational_log: ACCEPTED_CL_EXPORT is empty; L-0b baseline export has not been accepted yet`
       When `ACCEPTED_CL_EXPORT` is populated at L-0b, reads the export JSON and the retained copy bytes from Git at `<sha>` via `evidence.require_cl_export(repository_root, git_commit, export_path, expected_export_blob=..., expected_retained_blob=...)` (`research_system/legacy/evidence.py:277-362`) and runs `recheck_cl_export(export, retained_raw)` (`research_system/legacy/export_recheck.py:32-89`) to confirm the runtime segmenter reproduces the export's segmentation of the retained copy before comparing against the live vault file.
     - **Fixture mode (`--fixture-export-json <path> --fixture-retained-copy <path>`, for tests and pre-L-0b negative controls):**
       Reads the fixture export JSON and fixture retained copy from disk, validates the export structure against the `w9-cl-export/1` invariants (`evidence.py:293-360`) and `recheck_cl_export(export, retained_raw)` (`export_recheck.py:32-89`).
2. **Whole-page segmentation of the live vault file:**
   - Calls `live_seg = segment_bytes(live_raw, source_path="04-Methods/Computational-Log.md", profile="computational_log_entry", region=None)` (`research_system/legacy/segmentation.py:429-488`) and verifies agreement with `tools/w9_segmentation.py:461-518`.
   - Note that the live file is segmented with `region=None` (**whole page**), even if the baseline export was produced over a `line_range` or `whole_file` region (`w9-segmentation-contract-v1.md:190-192`). Why? Because new successor entries are prepended near the top of `04-Methods/Computational-Log.md` (reverse-chronological order), shifting the line numbers and byte offsets of all legacy entries below them (`w9-segmentation-contract-v1.md:189-192`), and because an unparseable heading or duplicate anchor anywhere on the page would corrupt whole-page addressability (`W9:196,404-413`).
3. **Exact five-part decision rule:**
   - **Check 1 — Live file encoding and zero blocker rows across the whole page (`W9:196`):**
     - `live_seg["file_facts"]["has_utf8_bom"]` must be `False` and `live_seg["file_facts"]["line_ending"]` must be `"LF"`.
     - For every row `r` in `live_seg["rows"]`, `r["row_kind"]` must **not** be `"blocker"`. If any row in `live_seg["rows"]` has `row_kind == "blocker"` (`blocker_reason` in `{"unparseable_anchor", "duplicate_anchor", "unaddressed_region"}`), fail closed immediately with:
       `ERROR: vault_computational_log: live file contains segmentation blocker at row_ordinal=<ord> (lines <line_start>-<line_end>): <blocker_reason> (<anchor_text_or_none>)`
     *(Note on the existing post-cutoff line 541–545 blocker in the live file: `w9-segmentation-contract-v1.md:242,254-256` noted that at WP9.2 measurement time, lines 541–545 had 1 `unparseable_anchor` blocker `### 2026-07-17 — P01-B Stage 2 Step 2A: ...` in the post-cutoff region because it used ` — ` instead of `: `, while lines 662–3476 had 0 blockers. Under `W9:196` ("flags any byte change inside a legacy entry; a missing, renamed or duplicated legacy heading anchor; any unparseable heading") and `W9:411-413` ("A blocker entry in the Computational-Log stays unaccepted until a separately authorized edit under §4.2 fixes the anchor in the vault"), check whether Check 1 scopes `unparseable_anchor` blockers to the legacy region / classified legacy entries or the whole file — see §8.2 Check 1b below.)*
   - **Check 1b — Scoped vs whole-file blocker rule:**
     - Any `duplicate_anchor` blocker anywhere in `live_seg["rows"]` that collides with a legacy entry's `anchor_text`, or any `unparseable_anchor` / `duplicate_anchor` / `unaddressed_region` blocker at or after the first legacy row in the live file (or any blocker anywhere if the baseline export had 0 blockers in its region), fails closed.
     - Even more simply and deterministically: compare the set of `blocker` rows in `live_seg["rows"]` against any known pre-existing non-legacy blocker recorded in the accepted export (if `export["region"]["kind"] == "whole_file"` has 0 blockers, then 0 blockers are permitted anywhere in `live_seg["rows"]`; if `export["region"]["kind"] == "line_range"` has 0 blockers in the legacy range, then 0 blockers are permitted at or after the first legacy entry in `live_seg["rows"]`, and any new `unparseable_anchor` or `duplicate_anchor` anywhere in the file that was not present at baseline also fails closed!). To ensure zero ambiguity, **any `row_kind == "blocker"` in `live_seg["rows"]` fails closed by default**, and if L-0b is exported as a `line_range` while a pre-existing post-cutoff blocker exists above the range, only a blocker whose exact `(blocker_reason, raw_row_sha256)` is explicitly listed in the accepted export's pre-existing post-cutoff notes could ever be ignored—Wait: under `w9-segmentation-contract-v1.md:199` and `research_system/legacy/evidence.py:322,354`, `require_cl_export` **forbids any blocker row in the export** (`if row["row_kind"] not in {"item", "structural"}: raise LegacyEvidenceError(...)`, `evidence.py:354`)! And under `W9:196`, the vault detector *"flags any byte change inside a legacy entry; a missing, renamed or duplicated legacy heading anchor; any unparseable heading"*. Therefore, **Check 1 requires zero `row_kind == "blocker"` rows across `live_seg["rows"]`** (or across the evaluated region when `--region` is specified).
   - **Check 2 — Baseline export classifications must be complete (`P-068` item 4; `evidence.py:347-360`):**
     - Build the map `class_by_ordinal = {c["ordinal"]: c["class"] for c in export["classifications"]}`.
     - If any row in `export["segmentation"]["rows"]` has `class_by_ordinal[row["row_ordinal"]] is None` (unclassified) or not in `{"legacy", "successor"}`, fail closed with:
       `ERROR: vault_computational_log: baseline export has unclassified or invalid classification at row_ordinal=<ord>`
   - **Check 3 — Every legacy `"item"` row is preserved byte-for-byte (`W9:196,404-407`; `w9-segmentation-contract-v1.md:189-192`):**
     - Let $L_{\text{item}}$ be the ordered list of rows in `export["segmentation"]["rows"]` with `row_kind == "item"` and `class_by_ordinal[row["row_ordinal"]] == "legacy"`.
     - Index all `"item"` rows in `live_seg["rows"]` by `anchor_text`. (Because Check 1 already rejected any `duplicate_anchor` blocker, each `anchor_text` in `live_seg["rows"]` is unique.)
     - For each baseline legacy item row $b \in L_{\text{item}}$:
       1. Look up `anchor = b["anchor_text"]` in the live item index. If missing, fail closed with:
          `ERROR: vault_computational_log: missing or renamed legacy heading anchor '<anchor>' (baseline row_ordinal=<ord>, raw_row_sha256=<sha>)`
       2. Let $l$ be the matching live item row. Require `l["anchor_line_sha256"] == b["anchor_line_sha256"]` and `l["raw_row_sha256"] == b["raw_row_sha256"]`. If either differs, fail closed with:
          `ERROR: vault_computational_log: byte change inside legacy entry '<anchor>' (expected raw_row_sha256=<b_sha>, got <l_sha> at live lines <l_start>-<l_end>)`
   - **Check 4 — Every legacy `"structural"` row is preserved byte-for-byte (`w9-segmentation-contract-v1.md:184-188`):**
     - Let $L_{\text{struct}}$ be the ordered list of rows in `export["segmentation"]["rows"]` with `row_kind == "structural"` and `class_by_ordinal[row["row_ordinal"]] == "legacy"`.
     - For each baseline legacy structural row $b \in L_{\text{struct}}$ (identified by `anchor_line_sha256`, `w9-segmentation-contract-v1.md:186`):
       - Require a `"structural"` row $l$ in `live_seg["rows"]` with `l["anchor_line_sha256"] == b["anchor_line_sha256"]` and `l["raw_row_sha256"] == b["raw_row_sha256"]`. Otherwise fail closed with:
         `ERROR: vault_computational_log: modified or missing legacy structural block (anchor_line_sha256=<sha>)`
   - **Check 5 — Relative order of legacy rows is preserved:**
     - The matched live `row_ordinal` values for all legacy rows ($L_{\text{item}} \cup L_{\text{struct}}$, ordered by their baseline `row_ordinal`) must be strictly increasing in `live_seg["rows"]`. If any two legacy entries were reordered in the live vault file, fail closed with:
       `ERROR: vault_computational_log: legacy entries reordered in live file ('<anchor_a>' and '<anchor_b>')`
   - **Allowed changes (successor insertions):**
     - Any `"item"` row in `live_seg["rows"]` whose `anchor_text` is not in the baseline legacy set (or was classified `"successor"` in the baseline export) is a successor entry; inserting or updating a successor entry does not trigger an error as long as it introduces no blocker row (`unparseable_anchor`, `duplicate_anchor`, `unaddressed_region`) and does not modify, delete, or reorder any legacy row.

### 8.3 What changes when the real L-0b export is accepted (`06v` D-7)

| Aspect | In WP9.5 (before L-0b) | When L-0b is authorized (D-7) and accepted by PR |
|---|---|---|
| `ACCEPTED_CL_EXPORT` (`research_system/legacy/accepted_w9.py:86-88`) | `()` (empty tuple) | Populated with one `AcceptedClExport(version="1.0.0", export_path=".research-system/evidence/w9/cl-baseline-export-v1.json", export_git_blob="<40-hex>", retained_copy_path=".research-system/evidence/w9/cl-baseline-retained-v1.md", retained_copy_git_blob="<40-hex>", accepted_in="P-09x")` entry |
| W9 paths addendum row (`06v-addendum-2026-11-10-w9-paths.md:29`) | `TBD at L-0b` | Dated addendum row naming the two committed `.research-system/evidence/w9/` paths |
| `tools/check_legacy_log_baseline.py` code | **No code logic change required.** In tests and pre-L-0b control runs, invoked with `--fixture-export-json` and `--fixture-retained-copy`. In production mode (without fixture flags), checks `ACCEPTED_CL_EXPORT` and fails closed while it is empty. | Production mode automatically reads `ACCEPTED_CL_EXPORT[-1]` at `--git-commit HEAD`, runs `require_cl_export` and `recheck_cl_export`, and compares the live vault file against the pinned L-0b export. |

### 8.4 Settling D-5: pre-batch and weekly cadence, evidence hash filing, and how a missed run blocks the next batch (Owner Point E)

- **Authority:** `06v` §5 (`06v-w9-implementation-plan.md:494-496`), `06v` §6 `D-5` (`:567`), and `06v` §7 batch checklist (`:602-607`).
- **`06v` D-5 states (`06v:567`):**
  > *"The vault detector runs before every batch and weekly on the operator machine. Each run files an output hash in the evidence area; a missed run blocks the next batch."*
- **What each clean run writes to the W9 evidence area:**
  1. `tools/check_legacy_log_baseline.py` produces a deterministic canonical JSON report of its check:
     ```json
     {
       "format": "w9-vault-log-check/1",
       "export_git_blob": "<40-hex>",
       "retained_copy_git_blob": "<40-hex>",
       "live_file_sha256": "<64-hex>",
       "live_file_byte_length": 376784,
       "legacy_items_verified": 105,
       "legacy_structural_verified": 1,
       "status": "ok"
     }
     ```
     and computes `output_sha256 = sha256_hex(canonical_bytes(report))`.
  2. With `--record-run .research-system/evidence/w9/vault-detector-runs.json`, a clean run appends a run entry to `.research-system/evidence/w9/vault-detector-runs.json` (`format: "w9-vault-detector-runs/1"`):
     ```json
     {
       "format": "w9-vault-detector-runs/1",
       "runs": [
         {
           "run_at": "2026-11-21T20:00:00Z",
           "export_git_blob": "<40-hex>",
           "live_file_sha256": "<64-hex>",
           "output_sha256": "<64-hex>",
           "status": "ok"
         }
       ]
     }
     ```
     (If the check fails, `--record-run` refuses to append a `"status": "ok"` entry and exits `1`.)
- **How "a missed run blocks the next batch" is enforced (Owner Point E, §16):**
  A run is "missed" if either:
  - **(a) Stale pre-batch run:** At the time the next batch is checked or accepted (`now`), the most recent entry in `vault-detector-runs.json` has `now - last_run_at > 7 days` (`timedelta(days=7)`), or there are zero runs recorded; OR
  - **(b) Missed weekly interval between batches:** Any two consecutive entries `runs[i - 1]` and `runs[i]` in `vault-detector-runs.json` (since L-1 activation or since the most recent explicit owner cadence reset `owner_reset_ref`) have `runs[i].run_at - runs[i - 1].run_at > timedelta(days=7)`.
  Where is this block enforced? §16 **Owner Point E** gives Stephen two options:
  - **Option E1 (Recommended — enforced both in `research_system/legacy/acceptance.py` at LR-016 / LR-020 and in the pre-batch check tool):**
    Add `VAULT_DETECTOR_RUNS = f"{EVIDENCE_DIRECTORY}/vault-detector-runs.json"` and `require_vault_detector_cadence(repository_root, git_head, *, now: datetime)` in `research_system/legacy/evidence.py`, and call it from `check_environment` in `research_system/legacy/acceptance.py:147-152` (which already runs at every `LR-016` `legacy-closed-reference-acceptance` proposal and every `LR-020` `ResolveW9AuthorityDecision` batch decision!). That makes "a missed run blocks the next batch" a hard store-preparer gate: no batch can be accepted into the control store if a weekly vault-detector run was missed.
  - **Option E2 (Alternative — enforced by the CLI pre-batch check tool only, leaving `acceptance.py` untouched):**
    Enforce the 7-day cadence check in `tools/check_legacy_log_baseline.py --check-cadence` (run in `06v:602` before every batch) without editing `research_system/legacy/acceptance.py`.

### 8.5 Negative and positive controls (`W9-T19`, `O-13`)

All controls run on synthetic fixture bytes in `tmp_path` (never reading or writing the real vault):
1. **Positive controls (must exit 0):**
   - Clean match between fixture retained copy and live copy -> exits `0`.
   - Prepending a new successor entry `## [2026-11-21] [PIPELINE] P00: Synthetic successor entry` at the top of the live copy (shifting every legacy entry's line numbers and byte offsets downward) -> exits `0`.
   - Modifying a row that was classified `"successor"` in `export["classifications"]` -> exits `0`.
2. **Negative controls (`watched_to_fail`, must exit 1):**
   - **Control V1 (1-byte edit inside a legacy entry body):** Change one character in a legacy entry's `**Results**:` line -> exits `1` with `ERROR: vault_computational_log: byte change inside legacy entry '<anchor>'`.
   - **Control V2 (renamed legacy heading anchor):** Change `## [2026-06-09] [RESULT] P01-A: Stage 1...` to `## [2026-06-09] [RESULT] P01-A: Stage 1 (edited)...` -> exits `1` with `ERROR: vault_computational_log: missing or renamed legacy heading anchor`.
   - **Control V3 (deleted legacy entry):** Delete an entire legacy entry from the live copy -> exits `1` with `ERROR: vault_computational_log: missing or renamed legacy heading anchor`.
   - **Control V4 (duplicate heading anchor):** Insert a new entry that reuses a legacy entry's exact `(date, tag, summary)` anchor -> exits `1` with `ERROR: vault_computational_log: live file contains segmentation blocker ... duplicate_anchor`.
   - **Control V5 (unparseable dated-looking heading):** Insert `## 2026-11-21 — P01-A malformed heading` (missing bracketed tag and colon) -> exits `1` with `ERROR: vault_computational_log: live file contains segmentation blocker ... unparseable_anchor`.
   - **Control V6 (reordered legacy entries):** Swap the positions of two legacy entries without changing their bytes -> exits `1` with `ERROR: vault_computational_log: legacy entries reordered in live file`.

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
- **Validation rules in `require_detector_controls` (`evidence.py:133-154`):**
  - Top-level closed keys: `{"format", "detectors"}`.
  - Each item in `"detectors"` has closed keys `{"detector", "control", "output_sha256", "recorded_at"}`:
    - `"detector"`: one of the four keys in `REQUIRED_DETECTOR_CONTROLS`, with no duplicates and all four present (`set(seen) == set(REQUIRED_DETECTOR_CONTROLS)`).
    - `"control"`: must equal `REQUIRED_DETECTOR_CONTROLS[detector]`.
    - `"output_sha256"`: 64 lowercase hex chars matching `^[0-9a-f]{64}\Z` (`_SHA256`, `evidence.py:65`).
    - `"recorded_at"`: UTC timestamp matching `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?Z\Z` (`_UTC`, `evidence.py:66`).

### 9.2 How `tools/run_w9_detector_controls.py` runs each control and computes `output_sha256`

`tools/run_w9_detector_controls.py` runs each detector's control in an isolated temporary directory (`tempfile.TemporaryDirectory`), verifies that the control behaved as required, constructs a canonical JSON transcript for that detector (normalizing away the ephemeral `tmp_path` prefix so the transcript contains only deterministic inputs, exit codes, and `ERROR:` lines), and hashes the canonical transcript bytes with `sha256_hex(canonical_bytes(transcript))`:

| Detector key | Control kind | What `run_w9_detector_controls.py` executes | Required outcome for hash generation | What is hashed to produce `output_sha256` |
|---|---|---|---|---|
| `main_ruleset` | `recorded_read` | Calls the ruleset `20822054` and `rulesets/rule-suites` reader (§4.1) under the operator's `gh` (or a supplied fixture response in unit tests). | Exit code `0`; all ruleset `20822054` invariants hold; `unrecorded_legacy_bypass_commits == []`. | `canonical_bytes` of the `"w9-main-ruleset-read/1"` report (§4.1). |
| `post_merge_first_parent` | `watched_to_fail` | In a `--no-checkout --local --no-hardlinks` scratch clone under `tmp_path` (§11.2), runs `tools/check_legacy_writes.py` across four negative-control cases: (1) replay of `5df0c001` with the 7-file fixture manifest (fires Rule 1 & Rule 2); (2) replay of `811d5a2b` with the 3-file fixture manifest (fires Rule 1); (3) synthetic unregistered write under `results/p04/out.json` (fires Rule 2); (4) synthetic edit to a `shared_enforcement_surface` contract with no `shared-surface-changes.json` entry / owner note (fires Rule 3). Also runs one positive control (commit touching only `results/ars/run.json` and `research_system/` exits `0`). | All four negative cases exit `1` with their exact `Rule 1` / `Rule 2` / `Rule 3` `ERROR:` message; positive case exits `0`. | `canonical_bytes` of `{"format": "w9-control-transcript/1", "detector": "post_merge_first_parent", "cases": [{"case_id": ..., "exit_code": 1, "error_lines": [...]}, ...]}`. |
| `vault_computational_log` | `watched_to_fail` | On byte copies of the baseline/fixture Computational-Log export under `tmp_path` (§8.5), runs `tools/check_legacy_log_baseline.py` across negative cases V1–V6 (legacy byte edit, anchor rename, deleted legacy entry, duplicate anchor, unparseable heading, reordered legacy entries) plus positive cases (clean copy and prepended successor entry). | All six negative cases exit `1` with their exact `ERROR: vault_computational_log:` message; both positive cases exit `0`. | `canonical_bytes` of `{"format": "w9-control-transcript/1", "detector": "vault_computational_log", "cases": [...]}`. |
| `conventions_repository_check` | `watched_to_fail` | On byte copies of `CONVENTIONS.md` under `tmp_path` (§7.6), runs `tools/check_conventions_legacy_locks.py` across negative cases N1–N5 (modified legacy bullet, deleted legacy paragraph, reordered legacy bullets, duplicate unit in section, renamed legacy section) plus positive cases (baseline `4620c716`, live `CONVENTIONS.md`, and inserted successor bullet). | All five negative cases exit `1` with their exact `ERROR: conventions_repository_check:` message; all positive cases exit `0`. | `canonical_bytes` of `{"format": "w9-control-transcript/1", "detector": "conventions_repository_check", "cases": [...]}`. |

If any negative control unexpectedly exits `0` (fails to fire) or fails for the wrong reason, `tools/run_w9_detector_controls.py` aborts with exit code `1` and writes nothing. When all four controls succeed, it writes the sorted 4-entry `"w9-detector-controls/1"` JSON to `--output` (which at L-1 is `.research-system/evidence/w9/detector-controls.json`) and validates the written bytes with `evidence.require_detector_controls` (`research_system/legacy/evidence.py:133-154`).

---

## 10. Merging is not going live (`P-089` item 3)

### 10.1 Why WP9.5 must stay inactive on `main` and the vault after merge

- `P-089` ("Not authorized", `03-decisions-and-open-questions.md:6085-6091`) explicitly withholds authorization for **L-1** ("the detectors live on `main` or the vault") and requires (`03-decisions-and-open-questions.md:6103-6104`):
  > *"merging WP9.5 must not start any detector on `main` or the vault; L-1 is a separate owner decision."*
- Furthermore, while `.research-system/evidence/w9/detector-controls.json` is not committed on `main`, WP9.3's `prepare_path_registration` (`LR-003`, `research_system/legacy/preparers.py:114`) refuses any path registration on a store bound to `main`. Thus WP9.5 must neither commit `.research-system/evidence/w9/detector-controls.json` on `main` nor schedule/trigger `.github/workflows/legacy-write-detector.yml` automatically on `main`.

### 10.2 How `.github/workflows/legacy-write-detector.yml` is structured in WP9.5

1. **`on: workflow_dispatch:` only before L-1:**
   In WP9.5, `.github/workflows/legacy-write-detector.yml` is committed with **only** a manual `workflow_dispatch` trigger:
   ```yaml
   name: W9 Legacy Write Detector

   on:
     workflow_dispatch:
       inputs:
         baseline_commit:
           description: "First-parent baseline commit SHA (40-hex)"
           required: false
           default: ""

   permissions:
     contents: read

   defaults:
     run:
       shell: bash

   jobs:
     detect-legacy-writes:
       name: W9 Post-Merge Legacy Write and CONVENTIONS Lock Check
       runs-on: windows-latest
       timeout-minutes: 15
       steps:
         ...
   ```
   - There is **no** `push:` trigger, **no** `pull_request:` trigger, **no** `merge_group:` trigger, and **no** `schedule:` trigger in WP9.5.
   - No scheduled task, Windows Task Scheduler entry, or git hook is installed for `tools/check_legacy_log_baseline.py` on the operator machine in WP9.5.
2. **Compatibility with existing repository workflow watchdogs (verified at `dbd54fe38`):**
   - **`.github/workflows/ars-artefact-currency-watchdog.yml:91-112` and `tools/check_workflow_liveness.py:61-93`:**
     The daily watchdog runs `uv run python tools/check_workflow_liveness.py --all-tracked --repo "${GITHUB_REPOSITORY}"` (`ars-artefact-currency-watchdog.yml:95-97`). In `tools/check_workflow_liveness.py:61-93`, `evaluate_workflow_liveness` lists all tracked `.github/workflows/*.yml` files via `git ls-files` and verifies that GitHub Actions reports `state == "active"` for each workflow (`check_workflow_liveness.py:80-83`). It does **not** require `--latest-run-json` when called with `--all-tracked` (`check_workflow_liveness.py:157-161`). GitHub Actions registers a `workflow_dispatch`-only workflow on `main` with `state: "active"`, so `check_workflow_liveness.py --all-tracked` passes immediately after WP9.5 merges.
   - **`.github/workflows/ci.yml:233-279` (`watchdog-schedule-liveness` job):**
     That job checks `--latest-run-json` only for two hardcoded workflows (`ars-artefact-currency-watchdog.yml` and `research-system-suite.yml`, `ci.yml:249-252`), not for `legacy-write-detector.yml`.
   - **`tests/tools/test_ci_platform_policy.py`:**
     - `test_no_job_runs_on_linux` (`:49-57`): satisfied by `runs-on: windows-latest`.
     - `test_bash_scripts_declare_bash` (`:60-75`): satisfied by `defaults: run: shell: bash`.
3. **What L-1 changes later (when Stephen separately authorizes L-1):**
   At L-1 (`06v:589-594`), a small reviewed activation PR:
   1. adds `push: branches: [main]` and `schedule: - cron: "17 7 * * 1"` to `.github/workflows/legacy-write-detector.yml`;
   2. commits `.research-system/evidence/w9/detector-controls.json`, `.research-system/evidence/w9/registration-manifest.json` (initially empty `{"format": "w9-registration-manifest/1", "registrations": []}`), `.research-system/evidence/w9/legacy-write-records.json` (`{"format": "w9-legacy-write-records/1", "records": []}`), and `.research-system/evidence/w9/shared-surface-changes.json` (`{"format": "w9-shared-surface-changes/1", "entries": []}`).
4. **Test proving WP9.5 does not go live on merge:**
   A unit test `test_legacy_write_detector_workflow_is_inactive_until_l1` in `tests/tools/test_w9_detectors.py` loads `.github/workflows/legacy-write-detector.yml` with `yaml.load(..., Loader=yaml.BaseLoader)` (matching `tests/tools/test_ci_platform_policy.py:28-32`) and asserts:
   - `set(workflow["on"].keys()) == {"workflow_dispatch"}` (no `push`, `schedule`, `pull_request`, or `merge_group`);
   - `.research-system/evidence/w9/detector-controls.json` does **not** exist in the working tree on the WP9.5 branch (`not (REPO_ROOT / ".research-system/evidence/w9/detector-controls.json").exists()`).

---

## 11. Where the controls run and scratch-clone mechanics (`P-089` item 4; `06v` O-13; W9-T7)

### 11.1 Hard isolation rule (`P-089` item 4; `06v:164`)

Every negative control and integration test runs exclusively on a scratch Git clone or a byte copy inside `pytest`'s `tmp_path` (or `tempfile.TemporaryDirectory`), **never** by writing to `main`, the working checkout, any linked worktree, or `C:\Users\steph\Documents\TDA-Research`.

### 11.2 How the W9-T7 scratch clone is constructed and replayed

`06v` §4 row `W9-T7` (`06v-w9-implementation-plan.md:228`) and `06v` §5 (`:493`) require:
> *"Replay `5df0c001` and `811d5a2b` on a scratch clone with a fixture registry listing the files they touched; assert both are flagged."*

1. **Fast, isolated local object-store clone without working-tree checkout:**
   - Checking out all 4,163 tracked files of `TDL` on Windows takes ~15 seconds and thousands of filesystem writes.
   - Instead, `tools/check_legacy_writes.py` operates purely on the Git object database (`rev-list`, `diff-tree`, `show <commit>:<path>`, `cat-file`, `merge-base`).
   - Therefore, W9-T7 creates a bare or `--no-checkout` scratch clone in `tmp_path`:
     `git clone --bare --local --no-hardlinks <REPO_ROOT> <tmp_path>/scratch.git`
     - `--local` copies from the local `.git/objects` packfiles without network access.
     - `--no-hardlinks` forces real file copies of the object packs in `<tmp_path>/scratch.git/objects` rather than filesystem hardlinks back into `<REPO_ROOT>/.git/objects`, guaranteeing that even low-level object writes in the scratch clone cannot touch `<REPO_ROOT>/.git`.
     - Immediately after cloning, the test runs `git --git-dir=<tmp_path>/scratch.git remote remove origin` so no command targeting the scratch clone has a remote URL.
2. **Fixture registration manifest for `5df0c001` and `811d5a2b`:**
   - The fixture `.research-system/evidence/w9/registration-manifest.json` lists the 10 files touched by `5df0c001` and `811d5a2b` (`W0-legacy-closeout-post-terminal-addendum-2026-10-21.md:335-340`):
     - The 7 stage-1 result files touched by `5df0c001`:
       - `results/trajectory_tda_integration/stage1/bhps_nonoverlap_reanalysis_2026-06-09.json`
       - `results/trajectory_tda_integration/stage1/01_trajectories.json` (and the remaining 5 stage-1 result JSON paths extracted directly from `git --no-replace-objects diff-tree --no-commit-id --name-only -r 5df0c001~1 5df0c001`)
     - The 3 input-provenance manifests touched by `811d5a2b` (extracted from `git --no-replace-objects diff-tree --no-commit-id --name-only -r 811d5a2b~1 811d5a2b`):
       - `contracts/manifests/input-provenance/t128-inputs.yaml`
       - `contracts/manifests/input-provenance/t138-w2-gap-closure-inputs.yaml`
       - `contracts/manifests/input-provenance/b9-om-gmm-inputs.yaml`
   - To make the fixture manifest present at `<head>` inside `<tmp_path>/scratch.git` (since `.research-system/evidence/w9/registration-manifest.json` did not exist in August 2026 when `5df0c001` and `811d5a2b` were committed), `tools/check_legacy_writes.py` accepts `--manifest-file <path>` (or the test synthesizes commits in `<tmp_path>/scratch.git` via `git hash-object -w` + `git mktree` + `git commit-tree` that replay the exact tree deltas of `5df0c001` and `811d5a2b` on top of a baseline commit carrying `.research-system/evidence/w9/registration-manifest.json`).
   - Doing both in W9-T7 makes the test completely airtight:
     - **Sub-test T7a (actual historical SHAs `5df0c001` and `811d5a2b` in `scratch.git`):** Runs `check_legacy_writes.py` on `<tmp_path>/scratch.git` across `--baseline 5df0c001~1 --head 5df0c001` and `--baseline 811d5a2b~1 --head 811d5a2b` (and `--baseline 4b143c9225035cc29e37351445f1c3a4ab09ceb1 --head 811d5a2b`) with the 10-file fixture manifest, asserting that:
       - `5df0c001` exits `1` and flags all 7 `results/trajectory_tda_integration/stage1/...` files under **both** Rule 1 (registered legacy file without §4.2 record) and Rule 2 (`results/` outside `results/ars/` without §4.2 record);
       - `811d5a2b` exits `1` and flags all 3 `contracts/manifests/input-provenance/...` files under Rule 1 (registered legacy file without §4.2 record).
     - **Sub-test T7b (in-tree committed manifest at `<head>` in `scratch.git`):** Commits `.research-system/evidence/w9/registration-manifest.json` into a branch in `scratch.git`, replays the exact tree diffs of `5df0c001` and `811d5a2b` onto that branch, runs `check_legacy_writes.py` reading the manifest directly from `<head>:.research-system/evidence/w9/registration-manifest.json`, and asserts the same Rule 1 and Rule 2 failures.

### 11.3 How the test proves it never writes the real repository or the vault

In `tests/research_system/integration/test_w9_wp9_5_detectors.py` and `tests/tools/test_w9_detectors.py`, an autouse fixture wraps every test and asserts repository immutability:
1. Before the test runs, it captures:
   - `head_before = git --no-replace-objects rev-parse HEAD` in `REPO_ROOT`;
   - `status_before = git --no-replace-objects status --porcelain=v1 -z` in `REPO_ROOT`;
   - `refs_before = git --no-replace-objects show-ref` in `REPO_ROOT`.
2. After the test completes, it re-runs those three read-only queries on `REPO_ROOT` and asserts `(head_after, status_after, refs_after) == (head_before, status_before, refs_before)`.
3. No test imports or references `C:\Users\steph\Documents\TDA-Research` or `C:\Users\steph\TDL\vault`; every vault detector test passes a synthetic `tmp_path / "vault"` directory created inside the test.

---

## 12. Tests and test-time budget

### 12.1 Test inventory and mapping to `06v` §4

| Test file | Markers | Cases covered |
|---|---|---|
| `tests/tools/test_w9_detectors.py` | `unit` (default; no `slow` marker) | 1. **`W9-T19` (`CONVENTIONS.md` check):** baseline `4620c716` passes; current `CONVENTIONS.md` passes; pure insertion of successor bullet in `## Always` and `## ARS Foundation Governance` passes; negative controls N1–N5 (modified legacy bullet, deleted legacy paragraph, reordered legacy bullets, duplicate unit in section, missing/renamed legacy section) each exit `1` with exact `ERROR: conventions_repository_check:` line.<br>2. **`W9-T19` (Computational-Log check on synthetic fixture export):** clean fixture passes; prepended successor entry at top of file passes; modified successor-classified entry passes; empty `ACCEPTED_CL_EXPORT` in production mode fails closed; junction or in-repo `--vault-root` fails closed; negative controls V1–V6 (1-byte edit in legacy entry, renamed legacy heading anchor, deleted legacy entry, duplicate heading anchor, unparseable dated heading, reordered legacy entries) each exit `1` with exact `ERROR: vault_computational_log:` line.<br>3. **D-5 cadence check:** clean run within 7 days passes; latest run > 7 days old fails closed; consecutive runs with a > 7-day gap fail closed.<br>4. **Post-merge detector unit controls (on small synthetic Git repos built in `tmp_path`):** Rule 1 pass (with matching `(pr_number, path, old_blob, new_blob)` §4.2 record) and fail (no PR, missing record, wrong `old_blob` or `new_blob`, partial file list in PR record, 2-parent merge commit touching registered file, directory prefix match under `papers/P01-A-JRSSA/`); Rule 2 pass (`results/ars/out.json` untouched by Rule 2; `results/p04/out.json` with §4.2 record passes) and fail (unregistered `results/p04/out.json` without §4.2 record exits `1`); Rule 3 (`O-32`) pass and fail (change to `shared_enforcement_surface` without `shared-surface-changes.json` entry or without W9 §4.3 owner note exits `1`); missing/unreadable registered file at `<head>` exits `1`.<br>5. **Ruleset reader (`main_ruleset`) unit controls:** valid ruleset `20822054` + clean `rule-suites` payload passes and produces deterministic `output_sha256`; disabled enforcement, missing `merge_queue` / `require_code_owner_review`, extra bypass actor, and unrecorded bypass commit touching a guarded path each exit `1`.<br>6. **Pre-L-1 inactivity proof (§10.2):** `.github/workflows/legacy-write-detector.yml` has `on == {"workflow_dispatch"}` only, and `.research-system/evidence/w9/detector-controls.json` is not committed on the branch. |
| `tests/research_system/integration/test_w9_wp9_5_detectors.py` | `integration`, with `@pytest.mark.slow` on `W9-T7` and the full 4-control runner | 1. **`W9-T7` (`slow`, `integration`):** `--bare --local --no-hardlinks` scratch clone of `REPO_ROOT` in `tmp_path`; replays `5df0c001` and `811d5a2b` against the 10-file fixture registration manifest (both historical SHAs T7a and grafted manifest branch T7b); asserts `5df0c001` fires Rule 1 and Rule 2 on all 7 stage-1 result files and `811d5a2b` fires Rule 1 on all 3 input-provenance manifests; asserts `REPO_ROOT` immutability before and after.<br>2. **`M-6` (`integration`):** scratch W9 control store + scratch Git repo in `tmp_path`; registers paths via WP9.3 `LegacyService`, runs `export_w9_registration_manifest.py`, commits manifest, rebinds `git_head`, verifies `--check` exits `0`, and verifies store-extra and manifest-extra mismatches exit `1`.<br>3. **`O-13` (`slow`, `integration`):** runs `tools/run_w9_detector_controls.py` end-to-end in `tmp_path`, producing `detector-controls.json` and verifying it passes `research_system/legacy/evidence.py:133-154` `require_detector_controls` and satisfies `LR-003`'s detector-controls precondition on a scratch store. |

### 12.2 Fixture provenance rule (`06v:248-255`)

- No test reads any live file from `C:\Users\steph\Documents\TDA-Research` or `C:\Users\steph\TDL\vault`, and no unit test reads live `papers/` or `results/` files.
- The `CONVENTIONS.md` baseline test reads blob `4620c71607ca3a06c6df3b8e96a6bddffc783960` from Git (commit `4b143c9225035cc29e37351445f1c3a4ab09ceb1`) and verifies `git_blob_id(raw) == "4620c71607ca3a06c6df3b8e96a6bddffc783960"` and `sha256_hex(raw) == "d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589"` (`research_system/legacy/reader.py:43-49`) before running any assertion.

### 12.3 Per-file time estimates and proposed test-time budget (Owner Point G)

Following `P-087` item 7 (`03-decisions-and-open-questions.md:5913-5916`, which set a 5-minute serial `--no-cov` test budget for WP9.4-2 after WP9.4-1's full-store-per-test fixture was refactored):

| Test file | Estimated wall-clock time (serial, `--no-cov` on Windows 11) | Why it stays fast |
|---|---|---|
| `tests/tools/test_w9_detectors.py` | **15 – 25 seconds** | Pure in-memory byte-copy tests for `CONVENTIONS.md` and `Computational-Log.md`, plus small 3-commit `git init` repos in `tmp_path` (shared across read-only negative-control assertions via a module-scoped synthetic repo fixture). |
| `tests/research_system/integration/test_w9_wp9_5_detectors.py` | **30 – 55 seconds** | Uses a single module-scoped `git clone --bare --local --no-hardlinks` scratch clone (~2–4 seconds on Windows because `--bare` skips checking out 4,163 working-tree files) and a single scratch W9 control store for M-6 and O-13. |
| **Total WP9.5 test suite** | **45 – 80 seconds** | Well within a **2-minute (120-second)** hard ceiling. |

**Proposed WP9.5 test-time budget (Owner Point G, §16):** **2 minutes (120 seconds)** for all new and modified WP9.5 test files run serially together with `--no-cov` on Stephen's machine; if exceeded, the worker stops and returns `PARTIAL` rather than letting slow fixtures accumulate.

---

## 13. Research assurance

WP9.5 touches the **Output / Provenance** assurance lane (`CONVENTIONS.md:20-34`): legacy artifact immutability detection, shared-surface state invalidation detection, `CONVENTIONS.md` lock preservation, vault Computational-Log legacy entry integrity, and detector negative-control evidence hashes. It performs no topological, null-model, panel-estimand, representation-freeze, or manuscript-prose computation.

### 13.1 Machine-checkable claims and their enforcement artifacts

| # | Claim | Enforcement artifact (test / validator / schema) |
|---|---|---|
| MC-1 | Every `legacy_path_registration` record in the W9 control store appears in `.research-system/evidence/w9/registration-manifest.json` at the bound `git_head`, and vice versa. | `tools/export_w9_registration_manifest.py --check`; tested in `tests/research_system/integration/test_w9_wp9_5_detectors.py` (`test_m6_registration_manifest_matches_store`). |
| MC-2 | Any first-parent commit on `main` after `<baseline>` that modifies, deletes, or renames a registered `repository_root` path (including any path under a registered `legacy_manuscript_root` directory ending in `/`) without a matching `(pr_number, normalized_path, old_blob, new_blob)` record in `.research-system/evidence/w9/legacy-write-records.json` causes `tools/check_legacy_writes.py` to exit `1`. | `tools/check_legacy_writes.py` (Rule 1); tested in `tests/tools/test_w9_detectors.py` and by `W9-T7` replay of `5df0c001` and `811d5a2b` in `tests/research_system/integration/test_w9_wp9_5_detectors.py`. |
| MC-3 | Any first-parent commit on `main` after `<baseline>` that adds, modifies, deletes, or renames any path under `results/` outside `results/ars/`—whether registered or unregistered—without a matching §4.2 record causes `tools/check_legacy_writes.py` to exit `1`. | `tools/check_legacy_writes.py` (Rule 2); tested in `tests/tools/test_w9_detectors.py` and by `W9-T7` replay of `5df0c001`. |
| MC-4 | Any first-parent commit on `main` after `<baseline>` that modifies a `shared_enforcement_surface` contract without both a W9 §4.3 owner note record and an entry in `.research-system/evidence/w9/shared-surface-changes.json` causes `tools/check_legacy_writes.py` to exit `1`. | `tools/check_legacy_writes.py` (Rule 3, `O-32`); tested in `tests/tools/test_w9_detectors.py`. |
| MC-5 | `git diff-tree -r --no-renames -z <P1> <C>` detects file changes introduced by both 1-parent squash/direct commits and 2-parent merge commits on `main`. | `tools/check_legacy_writes.py`; tested in `tests/tools/test_w9_detectors.py` (`test_two_parent_merge_commit_first_parent_diff_is_detected`). |
| MC-6 | Every unit in the 9 legacy-lock `## ` sections of `CONVENTIONS.md` at commit `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (blob `4620c71607ca3a06c6df3b8e96a6bddffc783960`) is preserved byte-for-byte and in relative order under `conventions_unit` segmentation (`w9-segmentation/1.0.0`), while pure insertions of successor units pass. | `tools/check_conventions_legacy_locks.py`; tested in `tests/tools/test_w9_detectors.py` (`W9-T19`, controls N1–N5). |
| MC-7 | Every legacy-classified `"item"` and `"structural"` row in the accepted `w9-cl-export/1` baseline export of `04-Methods/Computational-Log.md` is preserved byte-for-byte and in relative order in the live vault file, with zero segmentation blocker rows (`unparseable_anchor`, `duplicate_anchor`, `unaddressed_region`), while prepended successor entries pass. | `tools/check_legacy_log_baseline.py`; tested in `tests/tools/test_w9_detectors.py` (`W9-T19`, controls V1–V6). |
| MC-8 | All four detector controls (`main_ruleset: recorded_read`, `post_merge_first_parent: watched_to_fail`, `vault_computational_log: watched_to_fail`, `conventions_repository_check: watched_to_fail`) produce deterministic SHA-256 output hashes that pass `research_system/legacy/evidence.py:133-154` `require_detector_controls`. | `tools/run_w9_detector_controls.py` and `research_system/legacy/evidence.py:133-154`; tested in `tests/research_system/integration/test_w9_wp9_5_detectors.py`. |
| MC-9 | Merging WP9.5 does not activate automatic scheduled or push-triggered runs of `.github/workflows/legacy-write-detector.yml` on `main`, and does not commit `.research-system/evidence/w9/detector-controls.json` before L-1. | `tests/tools/test_w9_detectors.py` (`test_legacy_write_detector_workflow_is_inactive_until_l1`). |

### 13.2 Human-review-only claims

| # | Claim | Reviewer / Owner check and why not mechanized |
|---|---|---|
| HR-1 | Whether a W9 §4.2(b) repository-wide change is truly semantically equivalent on the registered legacy files it touched. | `tools/check_legacy_writes.py` verifies that `legacy-write-records.json` names a committed review file and owner note with matching SHA-256 hashes, but semantic equivalence of code/formatting changes requires human and independent-reviewer judgment (`W9:174-176`). |
| HR-2 | Whether the `affected_registrations` list in a `.research-system/evidence/w9/shared-surface-changes.json` entry includes every registered result whose meaning or validity could be altered by the shared-surface edit. | `tools/check_legacy_writes.py` and `research_system/legacy/acceptance.py:121-137` verify that the entry exists and that every listed affected registration is re-observed after the change, but deriving which results are semantically affected by a contract edit requires Stephen's note and the independent reviewer's derivation (`W9:184-187`). |
| HR-3 | Under D-8 (if U-3 confirms `GITHUB_TOKEN` cannot read `rulesets/rule-suites`), direct API inspection of `rule-suites` evaluation metadata occurs at the operator's pre-batch local check (`06v:602`) rather than inside the CI workflow run. | API permission boundary of GitHub Actions `GITHUB_TOKEN` (`tools/check_bypass_merges.py:20-21`; `P-064` item 8). Note that the Git first-parent walk in CI still inspects every commit on `main` (including bypass merges). |

---

## 14. Claims for review

An independent adversarial reviewer should attack each of the following 12 load-bearing claims against the cited repository evidence at base commit `dbd54fe382e7b2849d3f2038393cbdb4d709477b`:

1. **No D-4 trigger (`P-089` item 1):** WP9.5 adds no W9 command, no runtime-binding census row (stays at 275 rows, SHA-256 `82eab93a1b2ac81dd564581237f35e3dff19fee9e824ffff317d0f202b451d58`), no store append site (06h manifest stays at blob `1066404a`), no core or W9 schema, and does not modify `tools/w9_segmentation.py` (stays at blob `43e1454de09b61e274954c42b21d6ae533857a24`). See §2.2 and `03-decisions-and-open-questions.md:6064-6066,6081-6083,6138-6140`.
2. **Closed 3-key schema of `registration-manifest.json` in WP9.3 vs Rule 3 / root-prefix needs (`evidence.py:124-127`):** `require_registered` in `research_system/legacy/evidence.py:125` currently enforces `_closed(entry, {"root_kind", "root_id", "normalized_path"}, "registration manifest entry")`, which omits `"role"`. Without `"role"` (or a companion mapping), `tools/check_legacy_writes.py` cannot tell from `registration-manifest.json` alone which registered paths have `role == "shared_enforcement_surface"` (Rule 3). See §5.3 and Owner Point A (§16).
3. **Contradiction between `06v:89-90,212,479-481` and `research_system/legacy/evidence.py:197-198,231-238` + `acceptance.py:135` on `shared-surface-changes.json`:** `06v:212,479-481` requires the PR changing a shared surface to carry its own entry naming old and new blobs because a squash-merge commit SHA cannot be known inside the PR (`06v:89-90`), whereas `evidence.py:231` enforces closed keys `{"merge_commit", "surface", "affected_registrations"}` (40-hex `merge_commit`, rejecting `old_blob`, `new_blob`, and `pr_number`) and `acceptance.py:135` tests `is_ancestor(entry["merge_commit"], source["git_commit"])`. See §6.5 and Owner Point D (§16).
4. **Two-parent merge commits require explicit `<P1> <C>` arguments to `git diff-tree`:** Running `git diff-tree -r <C>` with a single commit argument on a 2-parent merge commit outputs nothing by default; passing `git --no-replace-objects diff-tree -r --no-renames -z <P1> <C>` where `<P1>` is the first parent from `git rev-list --parents -n 1 <C>` extracts the exact first-parent tree delta on `main` for both 1-parent and 2-parent commits. See §6.3.
5. **Genealogy of `5df0c001` and why commit-subject PR parsing is spoofable:** Commit `5df0c001` has 1 parent (`a426b731`, the actual 2-parent merge commit of PR `#215`) and reuses `#215`'s `"Merge pull request #215..."` commit subject (`W0-legacy-closeout-post-terminal-addendum-2026-10-21.md:334-340`; `reviews/g7a-w0-post-terminal-addendum-re-review-8988f463-2026-10-22.md:203-215`). Requiring `pull["merge_commit_sha"] == C` (without `tools/check_bypass_merges.py:101-110`'s earliest-merged fallback) plus matching `(pr_number, normalized_path, old_blob, new_blob)` in `legacy-write-records.json` prevents any commit-subject spoofing. See §6.3.
6. **Live walk baseline commit vs historical `5df0c001` / `811d5a2b` on `main`:** Because `5df0c001` and `811d5a2b` are on `main`'s first-parent history after `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (reverted a day later by `#219` / `b132406e`), a commit-by-commit walk starting at `4b143c92` on every live run would fail on `5df0c001` and `811d5a2b` unless the live baseline is pinned at L-1 activation (after `b132406e`) while W9-T7 passes `--baseline` across `5df0c001` and `811d5a2b` in a scratch clone. See §6.2 and Owner Point C (§16).
7. **`CONVENTIONS.md` section partition at `4b143c92` (`4620c716`):** At `4b143c92`, `CONVENTIONS.md` has 10 `## ` sections and 70 `conventions_unit` items (`w9-segmentation-contract-v1.md:244`). Under `W9` §7.3 items 1 and 4 (`09-migration-compatibility-and-pilot.md:388-390,404-407`), `## ARS Foundation Governance` is wholly successor under the object rule, leaving 9 legacy-lock `## ` sections (`68` baseline units), all of which are preserved byte-for-byte and in order in current `CONVENTIONS.md` at `dbd54fe38`. See §7.3–7.4.
8. **Whole-page segmentation of live `Computational-Log.md` by `anchor_text` / `anchor_line_sha256`:** Because successor entries are prepended near the top of `04-Methods/Computational-Log.md`, shifting line numbers and byte offsets of all legacy entries below them (`w9-segmentation-contract-v1.md:189-192`), `tools/check_legacy_log_baseline.py` segments the live file with `region=None`, requires zero `row_kind == "blocker"` rows across the live file, matches legacy `"item"` rows by `anchor_text` and `"structural"` rows by `anchor_line_sha256`, verifies exact `raw_row_sha256` equality, and verifies strictly increasing live `row_ordinal` order across all legacy rows. See §8.2.
9. **Vault junction refusal (`research_system/legacy/reader.py:140-206,240-248`):** `tools/check_legacy_log_baseline.py` refuses any `--vault-root` that is a symlink/junction (`_is_reparse_or_symlink`) or inside `repository_root`, reading `04-Methods/Computational-Log.md` exclusively through `handle_bound_read` on the real vault directory `C:\Users\steph\Documents\TDA-Research` (or a `tmp_path` directory in tests). See §4.3.2.
10. **D-5 enforcement at LR-016 and LR-020 (`research_system/legacy/acceptance.py:139-153`):** Checking `.research-system/evidence/w9/vault-detector-runs.json` inside `check_environment` (`acceptance.py:147-152`) makes "a missed run blocks the next batch" (`06v:567`) a hard preparer gate on batch acceptance rather than a manual checklist convention. See §8.4 and Owner Point E (§16).
11. **`on: workflow_dispatch:` satisfies `check_workflow_liveness.py --all-tracked` while keeping WP9.5 inactive until L-1:** `tools/check_workflow_liveness.py:61-93` (run by `.github/workflows/ars-artefact-currency-watchdog.yml:95-97` with `--all-tracked`) checks only that every tracked workflow is registered in GitHub Actions with `state == "active"`, while `--latest-run-json` is checked only for `ars-artefact-currency-watchdog.yml` and `research-system-suite.yml` in `ci.yml:249-252`. See §10.2.
12. **CI platform policy compliance (`tests/tools/test_ci_platform_policy.py:286-303`):** `test_every_tools_and_contracts_test_runs_in_a_workflow` requires every `tests/tools/test_*.py` module stem to appear in a workflow step's `run:` script or in `CONTROL_EXEMPTIONS`. See §2.3, §10.2, and Owner Point F (§16).

---

## 15. Stop rules for the code package

In addition to `06v` §8 (`06v-w9-implementation-plan.md:623-633`), the WP9.5 code package is bound by the following hard preconditions and runtime stop rules:

### 15.1 Hard preconditions before WP9.5 code is dispatched (`P-089` item 3)

WP9.5 implementation code **must not** be dispatched until all three of the following are complete:

1. **U-3 recorded in §4.2 of this note (`P-089` item 3, `03-decisions-and-open-questions.md:6094-6095`):**
   Stephen authorizes the read-only U-3 probe (§4.2.2); the reviewing session executes it and records the exact HTTP status codes and responses for `GET repos/ZK-Theory/TDL/rulesets/20822054` and `GET repos/ZK-Theory/TDL/rulesets/rule-suites` under `GITHUB_TOKEN` (and re-confirms under the owner's `gh`) in the §4.2.2 table of this note, stating whether D-8 is active.
2. **U-4 recorded in §4.3 of this note (`P-089` item 3, `03-decisions-and-open-questions.md:6094-6095`):**
   Stephen authorizes the read-only U-4 check (§4.3.3); the reviewing session runs the three read-only PowerShell metadata commands on `C:\Users\steph\TDL\vault` and `C:\Users\steph\Documents\TDA-Research\04-Methods\Computational-Log.md` (without reading vault file contents into context) and records the exact attributes, junction target, byte length, `LastWriteTimeUtc`, and SHA-256 in the §4.3.3 table of this note.
3. **Owner Points A through G decided by Stephen in a decision-register entry (`P-090`):**
   Stephen records his disposition on Owner Points A through G (§16) in `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`.

### 15.2 Stop rules during WP9.5 code implementation

The WP9.5 code worker must stop immediately and report if:
1. Any change would modify a protected identity listed in §2.2 (`runtime-binding-census.yaml`, `wp6_1_06h_current_append_manifest.yaml`, `test_wp6_1_06h_append_path_closure.py`, `research_system/schema_registry.py`, `research_system/authority.py`, core/W9 schemas, T2 expectations/seal, or `tools/w9_segmentation.py` blob `43e1454de09b61e274954c42b21d6ae533857a24`).
2. Any change under `research_system/legacy/` would exceed the specific reader additions approved by Stephen under Owner Points A, B, D, and E.
3. Any test or negative control writes to, or leaves any state in, `REPO_ROOT`, any linked worktree, or `C:\Users\steph\Documents\TDA-Research`.
4. The new and changed WP9.5 test files exceed the approved serial `--no-cov` test-time budget (Owner Point G, proposed 2 minutes / 120 seconds); return `PARTIAL` with per-test timings rather than merging slow fixtures.
5. Any detector control fails to fire on its negative control case or fires on a clean positive control case (`06v:629`).

---

## 16. Owner points

Stephen's decision is requested on the following seven points before WP9.5 code is dispatched:

| ID | Decision needed | Options | Recommendation |
|---|---|---|---|
| **A** | **Carrying `"role"` in `.research-system/evidence/w9/registration-manifest.json`** so `tools/check_legacy_writes.py` can distinguish `shared_enforcement_surface` contracts (Rule 3) and `legacy_manuscript_root` directory prefixes (`papers/P01-A-JRSSA/`, `papers/P01-B-JRSSB/`) from `successor_results_root` (`results/ars/`) and ordinary file registrations (Rule 1) (§5.3, §6.5). | **Option A1:** Widen `require_registered` in `research_system/legacy/evidence.py:124-127` to accept `"role"` in each registration-manifest entry (`{"root_kind", "root_id", "normalized_path", "role"}`, allowing optional `"role"` when reading existing 3-key WP9.3 unit-test fixtures so no existing test breaks), and have `tools/export_w9_registration_manifest.py` project `"role"` from `state["records"]["legacy_path_registration"]`.<br>**Option A2:** Keep `registration-manifest.json` strictly at 3 keys (`evidence.py:125` untouched) and commit a separate `.research-system/evidence/w9/shared-surfaces.json` list (or carry `"role"` in a parallel top-level key). | **Option A1.** It keeps a single source of truth for registered paths in `registration-manifest.json`, requires only a 3-line backward-compatible reader update in `research_system/legacy/evidence.py:124-127`, and is explicitly anticipated by `P-089` item 3 (*"Nothing under `research_system/legacy/` changes except a reader WP9.5 needs, and the note names it"*). |
| **B** | **Location and format of the W9 §4.2 write-allowance records** keyed by `(pr_number, normalized_path, old_blob, new_blob)` (§6.4). | **Option B1:** Commit `.research-system/evidence/w9/legacy-write-records.json` (`format: "w9-legacy-write-records/1"`, §6.4), validated by a new `require_legacy_write_records` reader in `research_system/legacy/evidence.py`, and add a dated row for it in `docs/plans/agentic-research-system/implementation/06v-addendum-2026-11-10-w9-paths.md`.<br>**Option B2:** Parse §4.2 allowance metadata out of PR bodies or commit message trailers via `gh api` without a committed JSON file in `.research-system/evidence/w9/`. | **Option B1.** A committed, schema-checked JSON file in `.research-system/evidence/w9/` works offline in scratch-clone tests, is auditable in Git at `<head>`, and matches `06v:212,479-488`'s committed evidence-area design. |
| **C** | **Default baseline commit for the post-merge first-parent walk in `tools/check_legacy_writes.py`** (§6.2). | **Option C1:** Pin the default live baseline commit at L-1 activation (a commit on `main` at or after `dbd54fe38`, after `#219` / `b132406e` already restored the August 2026 `5df0c001` and `811d5a2b` writes and after G7-A §11 audited all pre-Gate-7 writes), while accepting `--baseline <sha>` on the CLI so `W9-T7` walks directly across `5df0c001` and `811d5a2b` in a scratch clone.<br>**Option C2:** Default the live walk to the freeze merge commit `4b143c9225035cc29e37351445f1c3a4ab09ceb1` (`2026-07-18`) and commit a historical pre-L-1 disposition list exempting the G7-A §11 historical commits (`1af52f6d`, `5df0c001`+`b132406e`, `811d5a2b`+`b132406e`, `2ef7d8fc`, `17fb5f4d`, `3c64a021`, `3fa437a1`) unless `--no-historical-exemptions` is passed for `W9-T7`. | **Option C1.** It avoids embedding a historical exemption list in the live detector that could mask `5df0c001` and `811d5a2b` unless a special flag is toggled, while WP9.3's baseline locks and G7-A §11 already close the pre-L-1 period. |
| **D** | **Resolving the `O-32` squash-merge SHA contradiction in `.research-system/evidence/w9/shared-surface-changes.json`** between `06v:89-90,212,479-481` and `research_system/legacy/evidence.py:231-238` + `acceptance.py:135` (§6.5). | **Option D1 (In-PR entry, updating `evidence.py` and `acceptance.py`):** In `research_system/legacy/evidence.py:231`, allow a shared-surface change entry to carry `{"pr_number", "base_commit", "surface", "old_blob", "new_blob", "affected_registrations"}` (while still accepting `"merge_commit"` for backward compatibility with existing WP9.3 unit fixtures). Inside the PR that edits a shared surface, the author records `pr_number`, `base_commit` (the `main` commit the PR is based on / queued against), `old_blob`, `new_blob`, and `affected_registrations`. In `tools/check_legacy_writes.py` (Rule 3), the detector matches `(pr_number, surface, old_blob, new_blob)`. In `research_system/legacy/acceptance.py:135`, for an entry with `base_commit`, require the affected result's observation commit `obs_commit` to be a **strict descendant** of `base_commit` (`obs_commit != base_commit and is_ancestor(base_commit, obs_commit)`) and verify that `<obs_commit>:<surface>` has blob `new_blob` (or a later successor blob), proving the observation occurred at or after the shared-surface PR merged!<br>**Option D2 (Two-PR protocol, keeping `evidence.py:231` and `acceptance.py:135` unchanged):** The PR that edits a `shared_enforcement_surface` carries the W9 §4.3 owner note in `legacy-write-records.json` (keyed by `pr_number`, `old_blob`, `new_blob`), and a follow-up PR immediately records the resulting squash `merge_commit` SHA in `shared-surface-changes.json` before the control store binding advances to accept any batch; Rule 3 in `check_legacy_writes.py` requires `legacy-write-records.json` on the shared-surface commit $C$ itself and requires `shared-surface-changes.json` to contain `merge_commit == C` by `<head>` whenever `<head> != C` (or at pre-batch check time). | **Option D1.** It fulfills `06v:212,479-481` literally (*"The PR that changes a shared surface carries its own entry in a committed change list in the W9 evidence area, naming the contract and its old and new blobs"*), works in a single atomic PR without needing a post-merge follow-up PR, prevents pre-merge observations at `base_commit` from passing `acceptance.py:135`, and preserves backward compatibility with WP9.3's existing `merge_commit` unit tests. |
| **E** | **Enforcing D-5 ("a missed weekly vault-detector run blocks the next batch", `06v:567`)** (§8.4). | **Option E1:** Commit `.research-system/evidence/w9/vault-detector-runs.json` (`w9-vault-detector-runs/1`, added as a dated row in `06v-addendum-2026-11-10-w9-paths.md`) and enforce the 7-day cadence check both in `research_system/legacy/acceptance.py:147-152` (`check_environment` at `LR-016` and `LR-020`, via `evidence.require_vault_detector_cadence`) and in `tools/check_legacy_log_baseline.py --check-cadence`. (Keep `require_vault_detector_cadence` gated on `ACCEPTED_CL_EXPORT` being non-empty or a `check_cadence` flag so existing WP9.3/WP9.4 unit tests that do not test D-5 cadence remain untouched.)<br>**Option E2:** Enforce the 7-day cadence check on `.research-system/evidence/w9/vault-detector-runs.json` in `tools/check_legacy_log_baseline.py --check-cadence` (run on the `06v:602` pre-batch checklist) without editing `research_system/legacy/acceptance.py`. | **Option E1.** Enforcing D-5 in `check_environment` (`acceptance.py:147-152`, gated on `ACCEPTED_CL_EXPORT` being populated or `vault-detector-runs.json` being present) turns "a missed run blocks the next batch" into a machine-enforced store-preparer gate at `LR-016` and `LR-020`. |
| **F** | **Wiring WP9.5's unit tests into CI workflows (`tests/tools/test_ci_platform_policy.py:286-303`) vs `.github/CODEOWNERS`** (§2.3, §10.2). | **Option F1:** Run `tests/tools/test_w9_detectors.py` (`-m "not slow"`) in `.github/workflows/ci.yml`'s `admission-controls` job (`ci.yml:170-216`), add `"tests/tools/test_w9_detectors.py"` to `ADMISSION_CONTROL_MODULES` in `tests/tools/test_ci_platform_policy.py:175-229`, and also run it in `.github/workflows/legacy-write-detector.yml` (requires Stephen's `@stephen` review / admin bypass to merge because `ci.yml` and `test_ci_platform_policy.py` are in `.github/CODEOWNERS`).<br>**Option F2:** Leave `.github/workflows/ci.yml` and `tests/tools/test_ci_platform_policy.py` completely untouched; reference `tests/tools/test_w9_detectors.py` in a step of `.github/workflows/legacy-write-detector.yml` (satisfying `test_every_tools_and_contracts_test_runs_in_a_workflow` in `test_ci_platform_policy.py:286-303`, which scans `step.get("run", "")` across **all** `.github/workflows/*.yml`), and place a companion unit test module under `tests/research_system/unit/test_w9_wp9_5_detectors_unit.py` wired in `tools/affected_research_tests.py` so `research-system-suite.yml` runs the unit tests on PRs without touching any `CODEOWNERS`-guarded file. | **Option F2** if avoiding `CODEOWNERS`/admin-bypass on the WP9.5 PR is preferred; **Option F1** if Stephen wants `test_w9_detectors.py` inside the `ci.yml` `admission-controls` gate immediately on merge. (Recommend **Option F2** for the WP9.5 implementation PR so it merges cleanly through the standard queue without requiring an admin bypass, moving to `ci.yml` at L-1 if desired.) |
| **G** | **Test-time budget for WP9.5** (§12.3). | **Option G1:** Cap all new and modified WP9.5 test files (`tests/tools/test_w9_detectors.py` and `tests/research_system/integration/test_w9_wp9_5_detectors.py`) at **2 minutes (120 seconds)** combined serial wall-clock time with `--no-cov` on Stephen's machine; exceeding 2 minutes triggers a stop and `PARTIAL` return (`P-087` item 7 pattern).<br>**Option G2:** Use the same **5-minute (300-second)** budget as WP9.4-2 (`P-087` item 7). | **Option G1 (2 minutes / 120 seconds).** WP9.5 needs only one `--bare --local --no-hardlinks` scratch clone and one scratch store, which estimate to 45–80 seconds total. |

---

## 17. Change log

| Revision | Date | Author | Summary |
|---|---|---|---|
| Revision 1 | 2026-11-21 | Gemini agent (under `P-089`) | Initial draft of the WP9.5 design note for independent adversarial review. |
