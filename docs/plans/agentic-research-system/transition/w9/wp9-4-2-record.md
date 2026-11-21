# WP9.4-2 Execution Record

- **Date:** 2026-11-20
- **Status:** Built and verified locally on branch `pipe/w9-wp9-4-2-full-path` (unpushed)
- **Package / Scope:** `06v WP9.4` — second of two PRs (**WP9.4-2: W9 full path**)
- **Base commit (`origin/main`):** `f0e010e0637de45ccc27a6814ae7216eab587079` (carries `### P-087` and ancestor `cc81b733`)
- **Authority:**
  - `docs/plans/agentic-research-system/03-decisions-and-open-questions.md` (`P-085`, `P-086` items 1–15, `P-087` items 1–8)
  - `docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md` (rev 8: §§2, 10–18, §19 I/K/O, §26)
  - `docs/plans/agentic-research-system/implementation/06v-addendum-2026-11-10-w9-paths.md` (line 32)
  - Precedent records: `wp9-4-1-record.md` and `wp9-3-1-record.md` (§5 D-4 table convention)
- **Boundary & Not Authorized:**
  - Restricted strictly to worktree `C:\Users\steph\TDL\.apm\worktrees\wp9-4-2` on `pipe/w9-wp9-4-2-full-path`.
  - No modifications under `.research-system/**`, `research_system/store/`, `research_system/command/`, `research_system/discovery/`, `research_system/projection/`, `tools/w9_segmentation.py`, `papers/`, `C:\Users\steph\TDL-ARS-G6-Control`, or vault files.
  - `.research-system/evidence/w9/citation-disambiguation.json` and `.research-system/evidence/w9/legacy-open-items.json` do not exist on disk in the worktree (`false`).
  - No `git push`, PR creation, branch merge, or `--no-verify` commit.

---

## 1. What Landed

### 1.1 Route Partition (`research_system/legacy/routes.py`)
`LEGACY_ROUTED_ROWS` increased to **49** rows (`routes.py:446-453`) and `LEGACY_DEFERRED_ROWS` decreased to **12** rows (`routes.py:454-458`); `"WP9.4"` was removed from `LEGACY_DEFERRED_ROWS`.

| Group | Rows | Route / Mechanism | Key Implementation Anchor(s) |
|---|---|---|---|
| Paper root | `LR-035` | `CreateLegacyPaperRoot` | `routes.py:264-269`, `authority.py:216,257`, `schema_registry.py:278-280`, `preparers.py:1081-1089`, `reducers.py:1259-1276` |
| Paper citation status | `LR-039` | `RecordPaperCitationStatus` | `routes.py:288-293`, `authority.py:217,258`, `records.py:29,222-239`, `schema_registry.py:278-280`, `preparers.py:1092-1154`, `reducers.py:1292-1375` |
| Source inventory request / decision / resolution | `LR-040`, `LR-041`, `LR-042`, `LR-043` | WP9.4-2 proposal / review / resolution / record cycle | `routes.py:294-322`, `preparers.py:73-126,562-582,672-731,852-1074`, `reducers.py:88-161,1111-1160,2012-2045,2266-2333` |
| Transition mapping request / decision / resolution | `LR-044`, `LR-045`, `LR-046`, `LR-047` | WP9.4-2 proposal / review / resolution / record cycle | `routes.py:323-348`, `preparers.py:73-126,672-731,852-1074`, `reducers.py:88-161,1163-1185,2012-2045,2266-2333` |
| Ownership transition (`legacy_owned -> successor_owned`) | `LR-048`, `LR-049`, `LR-050`, `LR-051`, `LR-052`, `LR-053`, `LR-054` | WP9.4-2 proposal / review / resolution / record cycle (plus `LR-053` `open_items_blob` for `LR-054`) | `routes.py:349-394`, `preparers.py:73-126,584-666,672-731,852-1074`, `reducers.py:88-161,1188-1256,2012-2045,2266-2333` |
| Ownership closure (`successor_owned -> closed_reference`) | `LR-055` (via `LR-048..LR-052`, refusing `LR-053`) | WP9.4-2 proposal / review / resolution / record cycle | `routes.py:395-401`, `preparers.py:584-666`, `reducers.py:151-161,180-187,1226-1256` |
| Deferred (remaining 12 rows) | `LR-002` (`catalogue_revision`); `LR-021`, `LR-022`, `LR-061` (`WP9.7`); `LR-036..LR-038`, `LR-056..LR-060` (`WP9.6`) | Explicit deferred entries | `routes.py:454-458` |

### 1.2 Owner Point O — Physical Identity & Directory Prefix Collisions
- **Handle-bound physical identity (`preparers.py:186-285`):** `handle_bound_directory_identity`, `_same_physical_identity`, and `_require_physical_identity` bind and re-verify directory identity (`canonical_target`, `volume_serial_number`, `stable_file_id`, and `link_count` on non-root subjects / R6-i1 exemptions on roots).
- **Registration & target containment collisions (`reducers.py:529-591`):** `_folded_path`, `_normalized_target`, `_registration_conflicts`, and `_check_registration` enforce case-folded path prefix collision checks as well as physical `canonical_target` prefix containment checks (`:563-566`, both child-under-root and root-over-child) independently of `normalized_path` / `root_kind`.
- **Source inventory & ownership checks (`reducers.py:1111-1256`):**
  - `_check_source_inventory` enforces strict row-under-root containment (`"W9 source inventory row path is not strictly under its root"` at `:1139-1140`).
  - `_check_ownership_proposal` enforces matching target paper root (`"W9 mapping target paper root differs from ownership paper_root_ref"` at `:1212-1213`).
  - `_check_ownership_resolution` verifies that `LR-054` does not cite a suspended `LR-039` adoption (`"W9 LR-054 citation status cites a suspended adoption"` at `:1247-1248`).

### 1.3 Owner Point K — Member-Path Extraction & Whole-File Reads
- `LegacyReader.read(self, registration, *, member_path: str | None = None)` (`reader.py:278-303`) accepts optional `member_path` for `legacy_manuscript_root` member extraction (K readings 1–5).
- `LegacyReader._git` passes `--no-replace-objects` (`reader.py:80-92`; `P-087` item 5).
- Replay-level whole-file vs member rules are enforced in `reducers.py` (`_source_matches_registration` `:620-662`, `_whole_file` `:698-713`, `_batch_rules` `:716-747`).

### 1.4 Citation Extractor, Disambiguation Evidence & Reference Graph (`W9-T21`)
- **`research_system/legacy/citations.py`:** Implements deterministic token scanning (`RESULT_EXTENSIONS` `:22`, `_SINGLE_DELIMITERS` `:23`, `tokenize_text` `:45-62`, `scan_file_tokens` `:79-95`), candidate classification (`_classify_candidate` `:142-197`), registered result projection matching (`registered_result_projections` `:209-291`), multi-file extraction (`extract_citations_from_files` `:294-420`), and `extract_citations` (`:460-485`).
- **`research_system/legacy/evidence.py`:** Defines `CITATION_DISAMBIGUATION` (`:48`) and `CITATION_DISAMBIGUATION_FORMAT` (`:49`), parsed and hash-verified via `_disambiguation_entries` (`:458-489`) and `read_citation_disambiguation` (`:492-518`, checking `git_blob_id(raw) != blob` at `:516` and using `--no-replace-objects` via `_evidence_git` at `:510`).
- **Paths addendum re-citation:** `docs/plans/agentic-research-system/implementation/06v-addendum-2026-11-10-w9-paths.md:32` now cites `CITATION_DISAMBIGUATION` (`evidence.py:48`) and `CITATION_DISAMBIGUATION_FORMAT` (`evidence.py:49`).
- **Reference graph & runtime wiring:** `reducers.py` (`_add_edges` `:341-358`, `_check_paper_root_lr035` `:1259-1276`, `_check_citation_status_lr039` `:1292-1375`) and `runtime.py` (`_WP9_3_PREPARERS` `:75-85`, `_SUBJECT_KINDS` `:88-100`).

### 1.5 Read-Only CLI Command
- Added `ars legacy cited-families --root <id> [--reviewer-sha256 <hash>] --control-root <path>` in `research_system/cli.py` (`_legacy_cited_families` `:1987-2033`, parser registration `:2964-2974`).

---

## 2. Fixed Values

- **`citation_status_record_id` (`research_system/legacy/records.py:222-239`):**
  ```python
  derived_id(
      "obj",
      f"w9-citation-status:{root_id}:{supersedes_id or 'none'}:{cited_family_set_sha256}:{extractor_output_sha256}:{reviewer_derivation_sha256}",
      utc_milliseconds(root_created_at),
  )
  ```
- **`CITATION_STATUS_PREPARER_SET_FIELDS`:** `records.py:29`.
- **Evidence constants (`research_system/legacy/evidence.py:48-49`):** `CITATION_DISAMBIGUATION`, `CITATION_DISAMBIGUATION_FORMAT`.
- **Fixture & batch tables (`research_system/legacy/replay/reducers.py:180-187`):** `SOURCE_INVENTORY_UNCONDITIONAL_FIXTURES`, `MAPPING_*`, `OWNERSHIP_54_*`, `OWNERSHIP_55_*`; `WP9_4_2_ROWS` (`:88`), `CHECKED_ROWS` (`:90`), `PRE_ASSIGNED_REFS` (`:101-111`), `_DECISION_PROPOSAL_FIELD` (`:112-121`), `_REVIEW_FIELD_BY_KIND` (`:122-130`), `ownership_resolution_row` (`:151-161`).
- **Expected versions & row sets (`research_system/legacy/preparers.py:73-126`):** `REQUEST_ROWS`, `DECISION_ROWS`, `RESOLUTION_ROWS`, `RECORDED_EVENTS`, `EXPECTED_VERSIONS`.
- **CLI synopsis:** `ars legacy cited-families --root <id> [--reviewer-sha256 <hash>] --control-root <path>`.
- **Durations shard config (`tools/research_system_durations.json`):** Added `test_w9_citations.py: 10`, `test_w9_wp9_4_2_replay.py: 20`, `test_w9_wp9_4_2_runtime.py: 170` (measured wall times: `4.040s`, `8.654s`, `184.112s` — weights within ~14s of measured serial `--no-cov` runtime).

---

## 3. Rulings, Readings, and Departures

Four design/owner rulings were recorded and implemented across code and tests:

1. **`reader.py` `--no-replace-objects` (`P-087` item 5) & K reading 5 (`member_path` compatibility):**
   - `LegacyReader._git` includes `--no-replace-objects` (`reader.py:80-92`). Because `reader.py` belongs to `IMPORTER_MODULES` (`reader.py:42`), new W9 observations produced with this reader carry a new `tool_sha256`.
   - `LegacyReader.read(self, registration, *, member_path=None)` adds keyword-only `member_path` (`reader.py:278-303`), while non-root callers in `preparers.py` (`_read_source_member` `:1192-1195`, `_check_adoption_source` `:451`, `_read_source` `:751`) and `acceptance.py` (`reread_items` `:60-78`) preserve 1-arg `reader.read(registration)` when `member_path is None` for compatibility with WP9.3 monkeypatched readers.
2. **`authority.py` scoped grant actor classes & subject kinds:**
   - Added `CreateLegacyPaperRoot` and `RecordPaperCitationStatus` to both `SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES` (`authority.py:216-217`) and `_SCOPED_COMMAND_SUBJECT_KINDS` (`authority.py:257-258`, mapped to `"scope_definition"`).
3. **`LR-053` `open_items_blob` gating:**
   - Required for `LR-054` (`legacy_owned -> successor_owned`) via `_check_paper_open_items_discharged` (`preparers.py:584-602`), and omitted / refused on `LR-055` (`successor_owned -> closed_reference`) (aligned across `preparers.py` and `reducers.py`).
4. **`LR-050` / `LR-055` prepare-and-commit window checks:**
   - `_check_ownership_transition_env` (`preparers.py:625-666`) re-reads subject registration handle-bound physical identity AND (for `legacy_manuscript_root`) re-lists tracked root files (`list_tracked_root_files` `:525-546`) and re-reads every row blob from the prior `LR-054` mapped inventory (`_prior_lr054_inventory_for_registration` `:605-622`) at both prepare and commit.

---

## 4. D-4 Table (`tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml`)

`CreateLegacyPaperRoot` and `RecordPaperCitationStatus` were appended to `_RUNTIME_BINDINGS` (`research_system/schema_registry.py:278-280`), increasing the runtime-binding census from **273** rows to **275** rows.

| Identity / Artifact | Before (`f0e010e0637de45ccc27a6814ae7216eab587079`) | After (Worktree) |
|---|---|---|
| Runtime-binding census count | `273 rows` | `275 rows` |
| Runtime-binding census digest | `0cca0414641bf4fbed32b5f42d7c3753a8c47dcdd09d815dcba0658ef8814712` | `82eab93a1b2ac81dd564581237f35e3dff19fee9e824ffff317d0f202b451d58` |
| `research_system/schema_registry.py` | Git blob `4d0b3c97b677d1af109e1e4bebe3d587ed59d460` / SHA-256 `ae70b411518930e5674ed326860c975ceb83469d73d0efa0774b758fc8b70f12` / `63,268` bytes | Git blob `e32cb4080d5e9f045d7c113be84f0d1305b824e7` / SHA-256 `95d7612ff2ca61d9df2caeb4c0d82e82420dd8d1369763f55fa9d77bc6169b5b` / `63,552` bytes |
| `research_system/authority.py` | Git blob `47af6b377b81b245401daae116fd519897e4f10d` / SHA-256 `aa9693fa10dcbb69ecb899901c224e42c53d456509d10b1a76db9a829dc49a9e` / `117,696` bytes | Git blob `9b56b32220b1f15f0da76363c92a55340e6b6d7f` / SHA-256 `acf3af6c735ec132a53f9308ac31d262f5ac1344e6c05f1e01891bb3df4db836` / `117,972` bytes |
| `tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml` | Git blob `4c8950421d3a9f25da7cf4b657a358536df42332` / SHA-256 `7b6accbc38792fc707f0dde9574a02db1295189db39ee8683f518a945b05fb24` / `6,343` bytes | Git blob `1066404a69765b0e401ddf63214cd0eb508564e4` / SHA-256 `e02f75e6a4370199a391e6571c65bcec44e62f641b7da1aac42cd1f578e70c48` / `6,343` bytes |
| `tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py` | Git blob `559d684a5d78abc285ce9b50dd23ce071aad32c5` / SHA-256 `33ef58d3828e757f774dd8bd705ac392c2e3f8ec0391dab0f14a8b6643d7b3da` / `26,480` bytes | Git blob `3b1eec6e0fbff4b0daf7a572f42e81c82e8d787d` / SHA-256 `8150ab4928e440a9ec77b3cb22de20a43ed277f27ba9d8fad4398e2ecbe25270` / `26,480` bytes |
| `tests/research_system/unit/test_schema_registry.py` | Git blob `1f0cf37c6367bfedf554f2a235b67cdead38ec02` / SHA-256 `f3c72837c5b60969b2530fb0ce05cb423d5706217a70283c7e7e5cd6094f0781` / `45,427` bytes | Git blob `3cc218156b0785c422cbad6e344e7c53428f2665` / SHA-256 `f98639db86c6257a9532106f2aa8689f52d6d02422379b3195e0fd913f865127` / `45,427` bytes |

**Unchanged protected identities:**
- `owner_source_catalogue` blob: `1adc66921ee9c90d8786ff173748150922f1035e`
- `.research-system/schemas/core/commands` tree: `8a86a0c4921343e6a3afca3f491fad33e9a8a10f`
- `.research-system/schemas/core/events` tree: `058c1d5ddcb9d249916977f12b11768b6d15de0f`
- `tools/w9_segmentation.py` blob: `43e1454de09b61e274954c42b21d6ae533857a24`
- Append sites (`11` total): unchanged.

---

## 5. Tests Added & Updated

- **`tests/research_system/unit/test_w9_citations.py`:** `5 passed` — unit coverage of tokenization, candidate classification, registered result projection matching, disambiguation parsing, and `monkeypatch` `blob_at` -> `"f" * 40` byte-vs-blob hash mismatch control (`EvidenceRefused`: `"W9 citation disambiguation bytes do not hash to their blob at git_head"`).
- **`tests/research_system/integration/test_w9_wp9_4_2_replay.py`:** `8 passed` — WP9.4-2 replay flows, `citation_status_record_id` pinning against independent `derived_id` calculation, outside-root source inventory rejection (`"W9 source inventory row path is not strictly under its root"`), M-10 paper-root mismatch rejection (`"W9 mapping target paper root differs from ownership paper_root_ref"`), suspended `LR-039` adoption rejection before `LR-054` (`"W9 LR-054 citation status cites a suspended adoption"`), and forged-ledger `canonical_target` prefix containment checks across unrelated `normalized_path` values.
- **`tests/research_system/integration/test_w9_wp9_4_2_runtime.py`:** `4 passed` — Store A & Store B end-to-end runtime paths, direct preparer negative controls (including synthetic `link_count: 99` accepted on root `reg_a` per R6-i1 and rejected on non-root `reg_b_child`), and different-inventory checks.
- **Updated existing test suites:**
  - `tests/research_system/contracts/test_w9_import_seam.py`, `test_w9_legacy_routes.py` (49/12 partition; removed duplicate shadowed stub), `test_w9_pilot_promotion_table.py`.
  - `tests/research_system/integration/w9_flows.py`, `test_w9_legacy_replay.py`, `test_w9_legacy_runtime.py`, `test_w9_wp9_3_runtime.py`, `test_w9_wp9_4_1_replay.py`.
  - `tests/research_system/unit/test_w9_reader.py` (`P-087` item 5 `git replace` control + K5), `test_schema_registry.py` (`273 -> 275`), `test_wp6_1_06h_append_path_closure.py`.

---

## 6. Verification

### 6.1 Lint, Format, and Boundary Diffs
- `ruff check` and `ruff format --check` across all 26 changed/added `.py` files: **CLEAN**.
- Forbidden-path diff (`git diff` across `.research-system/`, `research_system/store/`, `research_system/command/`, `research_system/discovery/`, `research_system/projection/`, `tools/w9_segmentation.py`, `papers/`): **empty (`""`)**.

### 6.2 Mutation Testing (44/44 Caught)
- Single-site mutation suite across 44 targeted guards ran against the formatted production code (`507.35s` full 44-mutation run); after fixing the 1-line `_read_source_member` call in `research_system/legacy/preparers.py:451`, `M34..M41` re-ran (`409.39s`) and all 8 were caught.
- **Result:** **44 / 44 caught (`0` survived)**, with all 12 production files verified byte-for-byte restored via SHA-256.
  - Closed the prior 7 survivors via: `M04` retargeted to `if git_blob_id(raw) != blob:` (`evidence.py:516`) with `blob_at` mismatch control; `M09` (`records.py:235`) pinned against independent `derived_id`; `M17` (`reducers.py:563-566`) covered by forged-ledger `canonical_target` prefix tests (`target_only_child`, `f_rec_target_child`/`over_root_target`); `M26` (`reducers.py:1139-1140`), `M30` (`reducers.py:1212-1213`), and `M33` (`reducers.py:1247-1248`) covered by exact error assertions in `test_w9_wp9_4_2_replay.py`; `M34` (`preparers.py:266`) covered by direct `_require_physical_identity` `link_count: 99` root vs child checks in `test_w9_wp9_4_2_runtime.py:1310-1321`.

### 6.3 Serial `--no-cov` Timing Budget (`<= 300.0s` Added)
Profile baseline on `test_w9_wp9_4_1_runtime.py` (`51.950s` wall, `92,757,592` calls) identified `jsonschema.validators.iter_errors` (`22.868s`), `authority._projection` (`22.600s`), `activate_lifecycle_grant` (`22.035s` across 31 calls), and `projection.replay._replay` (`21.894s`) as the quadratic dominant cost as ledgers grow.

Serial `uv run --env-file .env pytest -q -p no:cacheprovider --no-cov` comparison against the base commit (`f0e010e06`):

| Bucket | Time (s) | Files |
|---|---|---|
| Base 8 files at `f0e010e06` (`base_8_then`) | `497.228s` | `test_w9_reader.py`, `test_w9_legacy_routes.py`, `test_w9_pilot_promotion_table.py`, `test_w9_import_seam.py`, `test_w9_legacy_replay.py`, `test_w9_wp9_3_runtime.py`, `test_schema_registry.py`, `test_wp6_1_06h_append_path_closure.py` |
| Base 8 files in worktree (`base_8_now`) | `302.388s` | Same 8 files (`5.494s`, `7.603s`, `0.965s`, `1.558s`, `36.165s`, `86.586s`, `144.925s`, `19.092s`) |
| New 3 test files (`new_3`) | `196.806s` | `test_w9_citations.py` (`4.040s`), `test_w9_wp9_4_2_replay.py` (`8.654s`), `test_w9_wp9_4_2_runtime.py` (`184.112s`) |
| Net delta vs `base_8_then` (`base_8_now + new_3 - base_8_then`) | **`+1.966s`** | **PASS (`+1.966s <= 300.0s`)** |
| Other 2 changed W9 files (`other_changed_2`) | `54.277s` | `test_w9_legacy_runtime.py` (`42.780s`), `test_w9_wp9_4_1_replay.py` (`11.497s`) |

### 6.4 Full W9 + CI Regression (`1,334 passed, 0 failed, 0 skipped, 0 errors`)
Total serial wall across **37** files (**38** runs): **`2,044.892s`**:

- **Run after final production edit (`preparers.py:451` fix):**
  - `test_w9_citations.py`: `5 passed` (`2.28s`, wall `4.040s`)
  - `test_w9_wp9_4_2_replay.py`: `8 passed` (`7.88s`, wall `8.654s`)
  - `test_w9_wp9_4_2_runtime.py`: `4 passed` (`182.89s`, wall `184.112s`)
  - `test_w9_reader.py`: `20 passed` (`4.84s`, wall `5.494s`)
  - `test_w9_legacy_routes.py`: `64 passed` (`6.79s`, wall `7.603s`)
  - `test_w9_pilot_promotion_table.py`: `7 passed` (`0.43s`, wall `0.965s`)
  - `test_w9_import_seam.py`: `10 passed` (`1.04s`, wall `1.558s`)
  - `test_w9_legacy_replay.py`: `39 passed` (`35.33s`, wall `36.165s`)
  - `test_w9_wp9_3_runtime.py`: `21 passed` (`85.48s`, wall `86.586s`)
  - `test_schema_registry.py`: `59 passed` (`143.95s`, wall `144.925s`)
  - `test_wp6_1_06h_append_path_closure.py`: `42 passed` (`18.23s`, wall `19.092s`)
  - `test_w9_legacy_runtime.py`: `37 passed` (`41.54s`, wall `42.780s`)
  - `test_w9_wp9_4_1_replay.py`: `36 passed` (`10.84s`, wall `11.497s`)
  - `test_w9_wp9_4_1_runtime.py`: `13 passed` (`606.59s`, wall `607.820s`)
  - `test_w9_apm_inventory.py`: `42 passed` (`10.47s`, wall `11.498s`)
  - `test_w9_evidence.py`: `9 passed` (`0.90s`, wall `1.882s`)
  - `test_w9_evidence_acceptance.py`: `38 passed` (`8.66s`, wall `12.543s`)
  - `test_w9_export_recheck.py`: `17 passed` (`2.27s`, wall `3.886s`)
  - `test_w9_inventory_region.py`: `24 passed` (`0.53s`, wall `1.067s`)
  - `test_w9_json_families.py`: `23 passed` (`0.45s`, wall `1.000s`)
  - `test_w9_open_items.py`: `24 passed` (`9.46s`, wall `10.224s`)
  - `test_w9_projection_read.py`: `19 passed` (`12.31s`, wall `13.185s`)
  - `test_w9_runtime_segmentation.py`: `84 passed` (`1.91s`, wall `2.439s`)
  - `test_research_system_ci_tools.py`: `61 passed` (`35.73s`, wall `37.432s`)
- **Run immediately prior to the 1-line `preparers.py:451` `_check_adoption_source` fix (`_check_adoption_source` is invoked only on `LR-023`/`LR-029`, never in WP9.3):**
  - `test_w9_acceptance_envelope.py` (`15 passed`), `test_w9_contract_materialization.py` (`69 passed`), `test_w9_expected_catalogue.py` (`186 passed`), `test_w9_precondition_fields.py` (`5 passed`), `test_w9_wp9_3_censuses.py` (`68 passed`), `test_w9_wp9_3_2_batch_build.py` (`13 passed`), `test_w9_wp9_3_2_replay.py` (`39 passed`), `test_w9_wp9_3_2_runtime.py` (`21 passed`), `test_w9_wp9_3_binding_head.py` (`18 passed`), `test_w9_wp9_3_grant_fence.py` (`3 passed`), `test_w9_wp9_3_inventory_builder.py` (`38 passed` in worktree + `1 passed, 38 deselected` in `0.53s` from `%TEMP%` with `--rootdir`), `test_w9_wp9_3_replay.py` (`104 passed`), `test_w9_wp9_3_writers.py` (`48 passed`).

---

## 7. Obligations, Known Limits, and Out-of-Scope Observations

- **Deferred rows remaining (`12`):**
  - `WP9.6` (`LR-036..LR-038`, `LR-056..LR-060`) and `WP9.7` (`LR-021`, `LR-022`, `LR-061`) plus `LR-002` (`catalogue_revision`) remain in `LEGACY_DEFERRED_ROWS` for their respective work packages.
- **Live store operations:** Not authorized or performed in WP9.4-2; all verification ran against temporary fixture stores in unit/integration tests.
- **Out-of-scope `.apm/` worktree cwd quirk:** As previously documented in `wp9-4-1-record.md` §7, `test_w9_wp9_3_inventory_builder.py::test_the_output_guard_requires_a_vault_root` fails if `pytest`'s `cwd` itself contains an `.apm/` parent directory, and passes `1 passed, 38 deselected in 0.53s` when invoked from `%TEMP%` with `--rootdir`.
- **`reader.py` `tool_sha256` shift (`P-087` item 5):** Because `research_system/legacy/reader.py` is listed in `IMPORTER_MODULES`, adding `--no-replace-objects` to `_git` changes the computed `tool_sha256` on newly recorded observations relative to pre-`P-087` fixtures.
