# WP9.4-1: W9 adoption, reviewer eligibility, discharge, suspension projection and read interface (LR-023 to LR-034)

**Date:** 2026-11-20<br>
**Status:** Built on branch `pipe/w9-wp9-4-1-adoption-discharge` (code commit `0846bdaf`), awaiting independent review, CodeRabbit, and Stephen's merge. Not reviewed, accepted, or ready to merge.<br>
**Package:** 06v WP9.4, first of two PRs: WP9.4-1 (adoption and discharge; P-086 item 1, owner point A).<br>
**Authority:**
- P-085 and P-086 (`docs/plans/agentic-research-system/03-decisions-and-open-questions.md`, owner points A to O);
- the WP9.4 design note, revision 8 (`28ec7134`, tree equal to `3b1a0e3f`): §1 to §9, §13 to §16 and §18;
- the W9 paths addendum and its 2026-11-20 amendment (`docs/plans/agentic-research-system/implementation/06v-addendum-2026-11-10-w9-paths.md:31`, `:60-75`);
- the owner catalogue annex (`docs/plans/agentic-research-system/transition/w9/wp9-1-catalogue-owner-annex.yaml`, LR-023 to LR-034).<br>

**Base:** `main` at `3b1a0e3f` (squash merge of PR #437).<br>
**Boundary:** Production edits are confined to `research_system/legacy/` and `research_system/cli.py` (one read-only verb, `ars legacy adoption-status`). Supporting edits are confined to `tests/research_system/`, `tools/research_system_durations.json`, line 31 of `implementation/06v-addendum-2026-11-10-w9-paths.md`, and this record. `research_system/schema_registry.py`, `research_system/authority.py`, `store/`, `command/`, `discovery/`, `projection/`, `.research-system/`, `tools/w9_segmentation.py`, `tests/research_system/unit/test_schema_registry.py` and `tests/research_system/smoke/` are unchanged.<br>
**Not authorized (P-085, P-086):**
- WP9.4-2: LR-035, LR-039, LR-040 to LR-055, the citation extractor (§11), the paper root and member files (§10), the reference graph (§12), `ars legacy cited-families`, any change to LR-003, and any D-4 change;
- WP9.7: the `CreateTask`/`AmendTask` guard (owner point J), the content rule at use and promotion (owner point E), LR-021, LR-022 and LR-061;
- any live operation, any real ARS store (`C:/Users/steph/TDL-ARS-G6-Control`), genesis or grant on a real store, any legacy write, or creating `.research-system/evidence/w9/legacy-open-items.json`.

Every store in these tests is a scratch store under `tmp_path`. Every source, open-item file and Git tree is synthetic, in a scratch Git repository under `tmp_path`.

## 1. What landed

### Route partition and row coverage (LR-023 to LR-034)

`routes.py:446-459` routes LR-023 to LR-034 and retags LR-024 and LR-025 from `WP9.7` to `WP9.4` (owner point B). The partition moves from 19 routed / 42 deferred to **31 routed and 30 deferred** (`LEGACY_ROUTED_ROWS`, `routes.py:446`; `LEGACY_DEFERRED_ROWS`, `routes.py:453`; `_VERDICT_ROW_FOR_REQUEST`, `routes.py:474`).

| Row | Kind / step | Implementation (`path:line`) | Summary |
|---|---|---|---|
| LR-023 | Adoption proposal | `routes.py:186`; `records.py:145`, `:155`; `reducers.py:759`, `:788`, `:955`, `:982`; `preparers.py:330`, `:337`, `:429`, `:456-462` | Enforces `families` vs `whole_file` subjects (`rehash_at_use: true`, non-`.json` binary/restricted only), `w9-use:manuscript-claims/\|task-input/\|claim-evidence/` uses, `qualifiers_to_discharge` and `w5_consequence`, observation acceptance not superseded, suspension check at birth, pre-assigned `decision_ref` + derived `rev_` and eligibility `dec_` reservations, and re-read window at preparer |
| LR-024 | Eligibility Decision proposal | `routes.py:192`; `records.py:155`; `reducers.py:173-177`, `:1258`, `:1378`, `:1392`; `preparers.py:592`, `:608-631` | Dedicated branch with no review requirement (`eligibility` payload on `ProposeW9AuthorityDecision`): derives ID (`adoption_eligibility_decision_id`), claims reservation, binds 8 refs in order (`W9:LR-024`, `w9-subject:`, `w9-subject-sha256:`, `w9-eligible-session:`, `w9-eligible-family:`, `w9-eligible-version:`, `w9-eligible-profile:`, `w9-eligible-grade:independent`), checks analyst-creator exemption (§5.3), extends proposal lapse |
| LR-025 | Eligibility Decision resolution | `routes.py:198`; `reducers.py:1483`, `:1574`, `:1586-1589`; `preparers.py:89`, `:675`, `:696-714` | Record-less resolution: single `DecisionResolved` event only, admits `accept` or `reject`, checks expiry and proposal lapse, excludes LR-025 from `RECORDED_EVENTS` (`preparers.py:82`) while keeping `LR-025` in `RESOLVER_ROWS` (`preparers.py:89`) |
| LR-026 | Adoption review request | `routes.py:204`; `reducers.py:886`, `:1027-1034`, `:1076`, `:1114`, `:1128`, `:1147`, `:1174-1175`; `preparers.py:64`, `:498`, `:510-518` | Requires derived review ID, resolved `accept` eligibility Decision matching `eligible_session`, separates analyst session from `eligible_session` in review state (C-m1), parses `w9-applicable-fixtures:` from `review_questions` |
| LR-027 | Adoption review verdict | `routes.py:210`; `reducers.py:1184`, `:1218`; `preparers.py:549`, `:570` | Submitter equals named reviewer (and not creator), `reviewer_session != analyst_session` and `== eligible_session`, `reviewer_profile == eligibility["profile"]`, `reviewer_model_metadata == "<family>@<version>"`, `computed_independence_grade == "independent"` |
| LR-028 | Adoption Decision proposal | `routes.py:216`; `reducers.py:116`, `:913`, `:940`, `:1324`, `:1378`; `preparers.py:71`, `:592`, `:632-649` | `review_id_for` requires satisfied derived review on current hash; parses sorted `w9-fixture:<ID>:<rev_\|art_\|dec_>` tail matching request's `applicable_fixtures` |
| LR-029 | Adoption Decision resolution | `routes.py:222`; `reducers.py:116`, `:940`, `:1522`, `:1562-1567`, `:1574`; `preparers.py:78`, `:86`, `:675`, `:751-754` | G5 + F-8 first limb, `considered_review_ids == [derived_review_id]`, repeated fixture entries, suspension check at resolution (`adoption_suspension_cause`), commit-time source re-read window (W9-T6, O-33) |
| LR-030 | Discharge proposal | `routes.py:231`; `evidence.py:44-47`, `:348`, `:389`, `:413`; `reducers.py:861`, `:955`, `:984`; `preparers.py:377`, `:411`, `:429`, `:463-470` | Uniqueness per `(item_kind, item_id)` across open/recorded discharges; reserves `reviewer_ref` and `decision_ref`; preparer checks open item in `legacy-open-items.json` at `git_head`, generic artefact `accepted_for_scope` (`_check_discharge_artefact`), no legacy byte/blob match (`legacy_content_matches`), and commit-time re-reads |
| LR-031 | Discharge review request | `routes.py:237`; `reducers.py:886`, `:1076`, `:1147`; `preparers.py:65`, `:498`, `:520-527` | Reviewer request checks (§5.3 analyst rule, §5.4 applicable fixtures) plus preparer-only G3 check refusing `reviewer_actor_id == manifest["producer_actor_id"]` |
| LR-032 | Discharge review verdict | `routes.py:243`; `reducers.py:1184`; `preparers.py:549` | Standard WP9.3 verdict checks (submitter matches reviewer, differs from creator and request session, `w9-independent-reviewer` profile) |
| LR-033 | Discharge Decision proposal | `routes.py:249`; `reducers.py:180`, `:913`, `:940`, `:1324`, `:1378`; `preparers.py:72`, `:411`, `:592`, `:650-656` | Standard Decision proposal checks + fixture tail + exactly one `w9-open-items-blob:<sha1>` entry checked by preparer against committed `legacy-open-items.json` at `git_head` (see §3 on item check) |
| LR-034 | Discharge Decision resolution | `routes.py:255`; `reducers.py:940`, `:1522`, `:1574`; `preparers.py:80`, `:87`, `:377`, `:411`, `:675`, `:755-767` | G5 + F-8 first limb; preparer and commit-time re-reads verify artefact still `accepted_for_scope`, still matches no legacy observation, open-item blob unchanged and item still present at `git_head`, and G3 again (`reviewer != producer_actor_id`) |

### Authority-flow, projection, evidence, CLI and paths addendum changes

- **WP9.3 authority-flow changes (§5.1–§5.6):**
  - **Row gate (`reducers.py:85-86`):** `WP9_4_1_ROWS` (`LR-023` to `LR-034`) joins `WP9_3_ROWS` in `CHECKED_ROWS = WP9_3_ROWS | WP9_4_1_ROWS` while keeping LR-016/LR-020 ownership derivation/reservation gated strictly to `WP9_3_ROWS` / `LR-020`.
  - **Derived review resolver (§5.2, `reducers.py:108-131`):** `review_id_for(kind, record)` replaces `_REQUEST_REVIEW_FIELD` and `_FAMILY_REVIEW_FIELD` across replay and `preparers.py`. Returns `NO_REVIEW_REQUIRED` only for `legacy_path_registration`, the derived ID `adoption_review_id` (`records.py:145`) for `legacy_adoption_decision`, the record's field for Kinds with a review field, and raises `IntegrityError` for any unlisted kind.
  - **Analyst rule (§5.3, `reducers.py:1047-1075`):** `_refuse_analyst_creator` exempts `legacy_adoption_decision`, `legacy_discharge_relation` (plus `legacy_field_family_membership` and `legacy_ownership_transitioned` for forward readiness alongside registration/acceptance), and `_creator_role_actor` adds `legacy_source_inventory` returning `observer_actor_id`.
  - **Fixture refs (§5.4, `reducers.py:144-156`, `:879-954`):** Requests at `LR-026`/`LR-031` carry one `w9-applicable-fixtures:<sorted comma-separated IDs>` entry containing all unconditional fixtures and applicable conditional fixtures (`ADOPTION_UNCONDITIONAL_FIXTURES = ("S-017",)`, `ADOPTION_CONDITIONAL_FIXTURES = ("F-015", "F-019", "F-038")`; empty set for `LR-034`, `S-017` + automatic `F-019` for `w9-use:manuscript-claims/` and `w9-use:claim-evidence/`). Decision proposals and resolutions at `LR-028`/`LR-029`/`LR-033`/`LR-034` mirror that exact fixture set as `w9-fixture:<ID>:<rev_|art_|dec_>` entries (followed by one `w9-open-items-blob:<sha1>` entry on `LR-033`/`LR-034`).
  - **G4 subjects (§5.6):** `ProposeLegacyRecord` takes `scope_definition` grant on the pre-assigned `record_id` (`LR-023`, `LR-030`); `RequestW9AuthorityReview`/`RecordW9AuthorityReview` take `review` grant on the derived/pre-assigned `review_id` (`LR-026`/`LR-027`, `LR-031`/`LR-032`); `ProposeW9AuthorityDecision`/`ResolveW9AuthorityDecision` take `decision` grant on the derived eligibility `dec_` (`LR-024`/`LR-025`) or pre-assigned `decision_ref` (`LR-028`/`LR-029`, `LR-033`/`LR-034`). Verified across all 12 rows in `test_w9_wp9_4_1_runtime.py:641`.
- **Suspension projection and legacy read interface (§7, §9):**
  - `research_system/legacy/projection_read.py` (new pure leaf module importing only stdlib and `IntegrityError`) provides `ADOPTION_REF_PATTERN` (`:17`), `adoption_suspension_cause` (`:41`), `adoption_status` (`:132`), `resolve_adoption_ref` (`:150`), `family_admissible` (`:203`), and `legacy_content_matches` (`:241`).
  - `tests/research_system/contracts/test_w9_import_seam.py` enforces via AST inspection (`:91`) that non-legacy modules under `research_system/` import only `research_system.legacy.projection_read` plus the §9 allowlisted modules (`:18-50`).
- **Open-item list reader (`evidence.py:44-47`, `:348-416`):** Reads `.research-system/evidence/w9/legacy-open-items.json` (`w9-legacy-open-items/1`) strictly from Git at `git_head` (never the working tree), optionally checking committed `expected_blob`, and provides `has_open_item`.
- **Read-only CLI (§13):** `ars legacy adoption-status <adoption_id> --control-root <path>` (`cli.py:1978-1984`, `:2907-2914`) calls `_legacy_projection(args.control_root)` (`read_only=True`) and prints `projection_read.adoption_status(state, args.adoption_id)` as JSON.
- **Paths addendum and test shard weights:** `docs/plans/agentic-research-system/implementation/06v-addendum-2026-11-10-w9-paths.md:31` is updated to cite `LEGACY_OPEN_ITEMS`, `evidence.py:44` and `LEGACY_OPEN_ITEMS_FORMAT`, `evidence.py:45` (lines 28–30 retain `evidence.py:39`, `:42`, `:43` unchanged). `tools/research_system_durations.json` adds weights for all 5 new test files.

## 2. Fixed values

- **Derived adoption review ID (`records.py:145-152`):** `derived_id("rev", f"w9-adoption-review:{adoption_id}", utc_milliseconds(created_at))`.
- **Derived adoption eligibility Decision ID (`records.py:155-158`):** `derived_id("dec", f"w9-adoption-eligibility:{adoption_id}", utc_milliseconds(created_at))`.
- **Open-item reader constants and format (`evidence.py:44-47`, `:351-385`):**
  - `LEGACY_OPEN_ITEMS = ".research-system/evidence/w9/legacy-open-items.json"` (`:44`)
  - `LEGACY_OPEN_ITEMS_FORMAT = "w9-legacy-open-items/1"` (`:45`)
  - `OPEN_ITEM_KINDS = frozenset({"a001_item", "audit_hole", "review_finding"})` (`:46`)
  - `OPEN_ITEM_PAPER_KEYS = frozenset({"P01-A", "P01-B"})` (`:47`)
  - Payload schema: closed `{"format": "w9-legacy-open-items/1", "items": [{"item_kind", "item_id", "source", "feeds_papers"}]}` with unique `(item_kind, item_id)` keys.
- **Adoption fixtures (`reducers.py:144-149`):** `ADOPTION_UNCONDITIONAL_FIXTURES = ("S-017",)`, `ADOPTION_CONDITIONAL_FIXTURES = ("F-015", "F-019", "F-038")`; `DISCHARGE_FIXTURES = frozenset()`. Both are bound to `wp9-1-catalogue-owner-annex.yaml` in `tests/research_system/contracts/test_w9_pilot_promotion_table.py`.
- **Use patterns (`reducers.py:181-185`):** `w9-use:manuscript-claims/<P01-A|P01-B>`, `w9-use:task-input/<key>`, `w9-use:claim-evidence/<key>` (`key` matching `^[a-z0-9][a-z0-9._-]*\Z`).
- **Decision / request ref prefixes (`reducers.py:173-180`):** `w9-eligible-session:`, `w9-eligible-family:`, `w9-eligible-version:`, `w9-eligible-profile:`, `w9-eligible-grade:`, `w9-applicable-fixtures:`, `w9-fixture:`, `w9-open-items-blob:`.
- **CLI:** `ars legacy adoption-status <adoption_id> --control-root <path>`.

## 3. Readings and departures

### Departures

- **`LR-033` open-item membership check (`research_system/legacy/preparers.py:650-656`):** `prepare_decision_proposal` calls `_check_discharge_open_item(environment, record, expected_blob=blob)`, which verifies both that `legacy-open-items.json` at `git_head` has Git blob `expected_blob` **and** that the discharge record's `(item_kind, item_id)` appears in that file. WP9.4 design note §8 (`wp9-4-design-note.md:728-729`) specifies only the blob match at LR-033 and checks item presence at LR-030 and LR-034. This tightening rejects an unresolvable Decision proposal early (for instance if `git_head` moved to a committed open-item list that dropped the item between LR-030 and LR-033) while admitting every valid proposal that could pass LR-034.

### Readings

- **R1 (`LR-027` / `LR-032` `_shadow` before `_require_role` ordering, `research_system/legacy/runtime.py:492-493`):** `_submit_wp9_3` calls `self._shadow(...)` before `self._require_role(...)`. When `OWNER` submits a verdict on a review naming another actor (`store.actors.reviewer`), `_shadow` raises `_check_verdict`'s mismatch message (`"W9 verdict is not recorded by the reviewer the request named"`) first; `_require_role` enforces `"W9 LR-027/LR-032 refuses the owner"` separately via `RESOLVER_ROWS` when tested with a matching reviewer/actor boundary.
- **R2 (`W9-T9` suspension cause precedence, `research_system/legacy/projection_read.py:85-86`, `:118-122`; note §7 M-1):** Re-observing a modified JSON source requires committing an updated membership table covering the new bytes (`reducers.py:1778-1784`) and places the prior observation in `state["stale_observations"]` (`reducers.py:1857-1865`). Because `adoption_suspension_cause` checks `stale_observations` (`projection_read.py:85-86`) before scanning later observations (`projection_read.py:118-122`), both new-blob re-observation controls in W9-T9 (same-family and disjoint-family) yield `cause == "observation_stale"`, whereas same-family re-observation at the unchanged blob yields `cause == "later_observation"`.
- **R3 (`06v-addendum-2026-11-10-w9-paths.md:31`):** Line 31 is re-cited with `LEGACY_OPEN_ITEMS`, `evidence.py:44` and `LEGACY_OPEN_ITEMS_FORMAT`, `evidence.py:45`, as directed by that file's 2026-11-20 amendment (`:65-67`) and Handover §4. Existing rows on lines 28–30 (`evidence.py:39`, `:42`, `:43`) did not shift.

## 4. No D-4

`git diff --stat 3b1a0e3f HEAD` over every protected path is empty:
- `.research-system/`, `research_system/schema_registry.py`, `research_system/authority.py`;
- `research_system/store/`, `research_system/command/`, `research_system/discovery/`, `research_system/projection/`;
- `tools/w9_segmentation.py` (blob `43e1454de09b61e274954c42b21d6ae533857a24`);
- `tests/research_system/unit/test_schema_registry.py` and `tests/research_system/smoke/`.

Verified read-only at commit `0846bdaf`:
- `tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml` blob: `4c8950421d3a9f25da7cf4b657a358536df42332`;
- `tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py` blob: `559d684a5d78abc285ce9b50dd23ce071aad32c5`;
- `owner_source_catalogue` blob: `1adc66921ee9c90d8786ff173748150922f1035e` (matches manifest);
- `.research-system/schemas/core/commands` tree: `8a86a0c4921343e6a3afca3f491fad33e9a8a10f` (matches manifest);
- `.research-system/schemas/core/events` tree: `058c1d5ddcb9d249916977f12b11768b6d15de0f` (matches manifest);
- runtime-binding census: `273` rows, digest `0cca0414641bf4fbed32b5f42d7c3753a8c47dcdd09d815dcba0658ef8814712` (matches manifest);
- `_reconcile_append_sites(_manifest_append_sites(doc), _append_sites())`: passed;
- `.research-system/evidence/w9/legacy-open-items.json` does not exist on disk (`False`).

## 5. Tests

| File | Cases | What it shows |
|---|---|---|
| `tests/research_system/unit/test_w9_open_items.py` | 20 passed | Open-item constants (`evidence.py:44-47`), valid multi-item lists read at `git_head`, empty list, refusal on missing/uncommitted/wrong-blob/non-JSON/malformed entries, same `item_id` with distinct `item_kind` |
| `tests/research_system/unit/test_w9_projection_read.py` | 19 passed | Unknown ID refusal, `active` status, W9-T9 causes (`observation_stale`, `later_observation`, root member path isolation, disjoint same-bytes stays active), item selector forward compatibility, supersession & LR-061 `use_mismatch`, `resolve_adoption_ref`, W9-T1 (`Done` status word), W9-T8 & W9-T17 `family_admissible`, `legacy_content_matches` |
| `tests/research_system/contracts/test_w9_import_seam.py` | 6 passed | Scans all non-legacy modules under `research_system/` (only `projection_read` plus §9 allowlisted imports allowed), negative controls for disallowed imports, positive control for `projection_read` |
| `tests/research_system/integration/test_w9_wp9_4_1_replay.py` (+ `w9_flows.py`) | 33 passed | Positive 4-boundary flows (adoption + eligibility + discharge), `review_id_for`, G5 at LR-028/LR-029, §5.3 analyst rule, §5.4 fixtures, LR-023 subject/use/qualifier/consequence/birth-suspension controls (incl. manuscript/claim `successor_ref`, superseded observation, superseded acceptance), LR-024/LR-025 eligibility Decision (incl. derived ID control), LR-026/LR-027 session/profile/model & W9-C controls, LR-030..LR-034 uniqueness/blob/W9-C controls, W9-T9 forged-ledger supersession & LR-061 |
| `tests/research_system/integration/test_w9_wp9_4_1_runtime.py` | 9 passed | Scratch-store end-to-end positive family adoptions + open findings, binary/restricted vs UTF-8 text whole-file adoptions, positive discharge + W9-C11 retries across LR-023..LR-034, role & G4 grant subjects for all 12 rows, W9-T6/O-33 adoption window, W9-T9 scratch-store re-observations, LR-025 record-less accept/reject, LR-030..LR-034 preparer negatives (open-item, non-accepted artefact, legacy copy G3, wrong blob, commit-time drift), CLI `ars legacy adoption-status` (active/suspended/unknown/Gate-6 refusal) |
| `tests/research_system/contracts/test_w9_legacy_routes.py` | 64 passed | Re-pins `LEGACY_ROUTED_ROWS` / `LEGACY_DEFERRED_ROWS` at 31 and 30 (`test_route_classes_are_thirty_one_routed_and_thirty_deferred_with_the_design_note_tags`) |
| `tests/research_system/contracts/test_w9_pilot_promotion_table.py` | 6 passed | Binds `ADOPTION_UNCONDITIONAL_FIXTURES`, `ADOPTION_CONDITIONAL_FIXTURES`, `ADOPTION_FIXTURES` and `DISCHARGE_FIXTURES` to `wp9-1-catalogue-owner-annex.yaml` |
| `tests/research_system/integration/test_w9_legacy_replay.py` | 39 passed | Moves bare deferred-row probe from LR-023 to LR-040 (`WP9.4`) while checking LR-016 and LR-023 reach schema validation |
| `tests/research_system/integration/test_w9_wp9_3_runtime.py` | 20 passed | Updates bound-command deferred-row runtime refusal test from LR-023 to LR-040 |
| `tests/tools/test_research_system_ci_tools.py` | 61 passed | Confirms updated `tools/research_system_durations.json` shard coverage |

## 6. Verification

Run on the operator machine (Windows 11, Python 3.13.5, `uv`), at code commit `0846bdaf`:

- **Targeted runs at `0846bdaf`:**
  - `tests/research_system/unit/test_w9_open_items.py`: `20 passed in 6.94s` (wall `8.6s`).
  - `tests/research_system/unit/test_w9_projection_read.py`: `19 passed in 0.44s` (wall `0.91s`).
  - `tests/research_system/contracts/test_w9_import_seam.py`: `6 passed in 0.90s` (wall `1.36s`).
  - `tests/research_system/integration/test_w9_wp9_4_1_replay.py`: `33 passed in 16.92s` (earlier 30-case run before adding 4 mutation controls: `30 passed in 16.80s`, wall `20.05s`).
  - `tests/research_system/integration/test_w9_wp9_4_1_runtime.py`: `9 passed in 483.93s (0:08:03)` (wall `485.1s`).
  - `tests/research_system/integration/test_w9_wp9_3_runtime.py` + `test_w9_wp9_3_2_runtime.py`: `41 passed in 334.53s (0:05:34)`.
  - `tests/tools/test_research_system_ci_tools.py`: `61 passed in 28.96s`.
- **Full 57-file regression (`task-832`, 1,988 collected items, one serial process at `0846bdaf`):** `1986 passed, 2 failed, 0 skipped in 7445.01s (2:04:05)`, `WALL_SECONDS=7452.05`, `RC=1`. Every test across all 5 new WP9.4-1 files, all updated test files, `test_schema_registry.py` (59 passed), `test_research_system_ci_tools.py` (61 passed), and `test_w9_segmentation.py` passed. Neither failure was caused by WP9.4-1 (see §7):
  1. `tests/research_system/integration/test_w9_wp9_3_inventory_builder.py::test_the_output_guard_requires_a_vault_root` — pre-existing WP9.3-1b cwd sensitivity when run inside `.apm/worktrees/` (`task-878` standalone in worktree: `1 failed, 38 passed in 208.48s`; standalone control at `0846bdaf` from `cwd=$env:TEMP` with `--rootdir` and `--no-cov`: `1 passed, 38 deselected in 0.41s`).
  2. `tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py::test_manifest_accounts_for_exact_runtime_bindings_and_append_sites` — fails on `assert _git_is_ancestor('09be63a9ba7e9525f5f69b8b8154b06d86a3c2b6', 'HEAD')` (`line 205`) because `C:/Users/steph/TDL/.git` is a shallow clone (`git rev-parse --is-shallow-repository` = `true`, shallow root `3fa437a1`, depth 47 to base `3b1a0e3f`; `git merge-base --is-ancestor 09be63a9ba7e9525f5f69b8b8154b06d86a3c2b6 3b1a0e3f` exits `1` on base `3b1a0e3f`). All downstream manifest, blob, tree, census, and append-site checks in that test passed when verified read-only (`task-980`, §4).
- **Mutation script** (scratch, not committed): **64 of 64** single-guard mutations caught, with byte-identical SHA-256 file restoration after every mutation and `0 bad_err`:
  - First pass caught **60 of 64** in `1035.4s`, missing `red-use-manuscript-succ`, `red-obs-superseded`, `red-obs-acc-superseded`, and `red-elig-derived-id`.
  - Added all 4 negative controls to `test_w9_wp9_4_1_replay.py` and re-ran `--only`: **4 of 4** caught in `46.6s`.
- **Added test runtime (for open escalation P-084):** The 5 new WP9.4-1 test files add **`509.13s` (~8 min 29 s)** of pytest time across individual runs (`6.94 + 0.44 + 0.90 + 16.92 + 483.93`; `509.01s` pytest / `516.02s` wall at the 30-case timing pass). `test_w9_wp9_4_1_runtime.py` accounts for `483.93s` across 9 scratch-store `submit` tests (including Gate-6 subprocess CLI probes and multi-step flows).
- **Ruff & pre-commit:** `ruff check`, `ruff format --check`, pack pins (`12 checked, 0 drifted`), 104 contracts, and CRLF checks passed on commit `0846bdaf`; pre-commit hooks run with `--no-verify` forbidden on the record commit too.

## 7. Obligations, known limits, and out-of-scope observations

### Obligations carried beyond WP9.4-1

- **WP9.4-2:** Route LR-035, LR-039, LR-040 to LR-055; implement the citation extractor, paper root/member files, reference graph, `ars legacy cited-families`, LR-003 registration collision/case-folding changes, and any required D-4 bindings.
- **WP9.6:** Binding test proving a real LR-060 supersession suspends an adoption under `P:legacy-adoption-status` (note §7, §15).
- **WP9.7:** Binding test proving a real LR-061 mismatch suspends an adoption, `CreateTask`/`AmendTask` guard (owner point J), and content rule at use/promotion (owner point E).
- **Live operations (Stephen, W0-D1):** Author and commit `.research-system/evidence/w9/legacy-open-items.json` (`w9-legacy-open-items/1`) when ready for live discharges.

### Known limits (preparer-only boundaries, note §8 and §16)

- At discharge replay, forged ledgers pass cleanly when the successor artefact's generic status is not `accepted_for_scope`, its bytes match a recorded legacy observation (`legacy_content_matches`), the open-item blob/membership at `git_head` differs, or G3 fails (`reviewer == producer_actor_id`), because generic artefact manifests and Git evidence are preparer inputs outside the 4-site shared replay boundary.
- `LR-024` / `LR-025` verify attested eligibility metadata strings in replay; family independence, role capability, and context isolation are Stephen's checks at LR-025 (§5.5).
- Whole-file binary vs UTF-8 text checks run at the preparer/re-read (`LR-023`/`LR-029`), not in pure replay (§6.1).

### Out-of-scope observations (reported, not modified)

1. `tests/research_system/integration/test_w9_wp9_3_inventory_builder.py:331-334` (`test_the_output_guard_requires_a_vault_root`) calls `refuse_tool_output(Path("out.json"), repository_root=None, vault_root=None)`. Inside an `.apm/worktrees/...` checkout, `output.resolve()` hits `research_system/legacy/inventory.py:402-403` (`"W9 tool output is under .apm/: out.json"`) before line `:404-405` (`"W9 tool output guard needs the vault root"`). Passes outside `.apm/`.
2. `C:/Users/steph/TDL/.git` is a shallow clone (`3fa437a1`, depth 47 to `3b1a0e3f`), causing `tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py:205` (`_git_is_ancestor('09be63a9ba7e9525f5f69b8b8154b06d86a3c2b6', 'HEAD')`) to fail even at base commit `3b1a0e3f`.
