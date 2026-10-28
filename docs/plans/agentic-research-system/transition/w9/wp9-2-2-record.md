# WP9.2-2: the legacy runtime, genesis, shared replay and CLI

**Date:** 2026-10-28<br>
**Status:** Revision 1. Not reviewed, not merged, D-4 not accepted.<br>
**Package:** 06v WP9.2, second of its two PRs (P-077 item 4). The design note is `transition/w9/wp9-2-design-note.md`,
revision 3, confirmed and merged as `779fc8bc` (PR #405).<br>
**Authority:** P-076, with P-077. The bootstrap contract was accepted at O-3 (P-078, main `69e9e059`); the catalogue
and annex at O-8 (P-075, main `7979e85a`).<br>
**Base:** `main` at `6ce597ba`.<br>
**Not authorized (P-076):** WP9.3 to WP9.7; live operations L-0 to L-5; a real store, genesis or a grant on one; any
legacy write. Every store in this package's tests is a scratch store under `tmp_path`.

## 1. What landed

| Design note | Code |
|---|---|
| §2 U-7, the four sites | Site 1 and site 4: `research_system/projection/replay.py` (`_replay`). Site 2: `discovery/routes.py` (`shared_event_partition` returns `"legacy"`). Site 3: `discovery/replay/driver.py` (one `continue`). Each imports the predicate lazily |
| §2.1 predicate | `research_system/legacy/commands.py`: `LEGACY_COMMAND_TYPES` (12, a literal) and `is_legacy_projection_event` |
| §3 binding and authority | One `SchemaBinding("ars://core/command", "1.0.0", command_type="ImportAcceptedW9CatalogueGenesis")` in `schema_registry.py`; the genesis command in `SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES` and as `scope_definition` in `_SCOPED_COMMAND_SUBJECT_KINDS` (`authority.py`) |
| §3 route classes, §4 row assignment | `research_system/legacy/routes.py`: `LEGACY_ROW_ROUTES` (61 rows, generated from the accepted catalogue and checked against it by `validate_legacy_route_registry`); `LEGACY_ROUTED_ROWS` = {LR-001}; `LEGACY_DEFERRED_ROWS` (60, tagged); `assign_row`, `e_only_discriminant`, `w9_row_ref`, `validate_transaction_shape` |
| §5.1, §5.2 | `research_system/legacy/accepted_w9.py`: `ACCEPTED`, `RESERVED_EXTERNAL_REFS`, `ROW_IDS`, `CATALOGUE_STREAM_ID`, `accepted_genesis_payload()` |
| §7.1 to §7.3 | `research_system/legacy/runtime.py`: `LegacyRuntime`, `refuse_gate6_store`, `W9Gate6StoreRefused` (reason code `w9_gate6_store_refused`) |
| §7.4 | `research_system/legacy/replay/driver.py` (`replay_legacy`) and `replay/reducers.py` |
| §8 | `ars legacy status` and `ars legacy show <id>` in `cli.py`, read-only; `legacy` joins `main`'s error set |
| §10 D-4 | See §4 |

## 2. Fixed values

- `CATALOGUE_STREAM_ID` is `obj_01a17eb7-5ae0-7000-8000-000000000001`: the `accepted_at` millisecond prefix of the
  reserved refs, with a fixed tail. The design note fixes only that it is a constant.
- `ACCEPTED` carries the O-8 catalogue and annex identities, the O-3 contract (`69e9e059`, blob `6bbbb14a`,
  `47699ed7…ddb1`, 4,164 bytes) and the envelope (`69e9e059`, blob `9b28528c`, `c26f468c…5999`, 11,185 bytes), the
  multiset hash `a8078818…ffde7` and the Gate 6 identity `5e3b95a9…8d69`.
- `accepted_genesis_payload()` names the amended contract and the envelope at `69e9e059`. Its
  `verification_requirements` are the contract's `verification_rules`, verbatim; a test checks them against the file.
- `ACCEPTED_REVISIONS` is empty: LR-002 is inert in v1.

## 3. Interpretations the reviewer should check

1. **Where the store is bound (§7.2).** `LegacyRuntime` is handed a bound ledger, as `DiscoveryRuntime` is. On every
   `submit`, before the lock, it reads `load_store_manifest_unbound(ledger.control_root)` and refuses a refused
   identity; it also refuses when `ledger.store_identity` is refused. A store whose manifest cannot be read is refused,
   because its identity cannot be shown not to be the Gate 6 one. Binding through `load_store_manifest` happens where
   the ledger is built: the CLI runs the refusal first and only then calls `_verified_ledger`, which binds.
2. **G5 in replay.** A record that a Decision resolves must equal its open proposal exactly (the same pre-assigned ID
   and content) and name the resolving Decision. LR-020's ownership transitions have no proposal of their own (P-072
   item 2), so each claims its own identity. Review satisfaction, the Decision's kind and resolver, and the G3 role
   rules are preparer checks for the packages that admit those commands; WP9.2 admits none.
3. **W9-T21, reducer half.** Every root, mapping, transition and recovery Decision adds its ref edges to one graph, and
   a self-reference or cycle is refused. A recovery Decision whose evidence names its recovery root is refused
   explicitly.
4. **LR-002.** `accepted_revisions` is a runtime and replay parameter, empty in production. With no binding row the
   production runtime refuses it ("inactive W9 command binding"). The catalogue's LR-002 identities run on the test
   registry with one test revision.
5. **The site 3 and site 1 negative controls** are simulated, not source edits. Site 3: a wrapper maps `"legacy"` to an
   unhandled partition, which is what removing the `continue` does. Site 1: the forged W2-typed event is passed to
   `_validate_active_lifecycle_binding` directly, which is the check site 1 skips.
6. **C2's messages.** A W2-typed event recorded under its W2 schema with no producer binding fails the shared replay
   with "inactive event schema"; recorded as `ars://core/event`, as the U-7 probe did, it fails with "unbound event
   producer". Both are asserted.
7. **C4.** The consumer test parses the four files and follows every `shared_event_partition` call, including a result
   assigned to a name and compared later, as in the Discovery driver. It also checks that these four are the only
   consumers under `research_system/`. Every partition decision compares against string literals. `==` and `in` select;
   `!=` and `not in` are accepted only as a bare `continue` guard. Any other use of the result fails. Only one decision
   names `"legacy"`: U-7 site 3's `continue` in the driver. Accepted and refused consumer shapes are its controls
   (CodeRabbit nitpick on PR #408: the first version checked only inline comparisons).

## 4. D-4 (design note §10)

WP9.2-2 changes these protected identities. Stephen re-accepts them at exact bytes, as they stand in the merge-queue
entry:

| Identity | Before | After |
|---|---|---|
| Runtime-binding census | 261 rows, `f359855bf5e760c3336dd201dd69e765d5bd0a91836dedcb5ddfecaeea0470d7` | 262 rows, `3d6ae37aba22f58e22d334745dfb0f66fa9f80a4a85c7a9fd633eb24963e9f06` |
| 06h manifest YAML (`tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml`) | count, digest and nine append sites | the new count and digest, and one more append site: `research_system/legacy/runtime.py`, `LegacyRuntime._submit_authorized`, `self.ledger`, `legacy_command_producer` |
| Append-site classification (the smoke test's `APPEND_SITE_CLASSIFICATIONS`) | | `legacy_command_producer` added |
| Command and event schema trees | unchanged | unchanged: no core schema changes |
| T2 validator expectations and seal | | unaffected: none reads the census |

`tests/research_system/unit/test_schema_registry.py` pins the count too (261 → 262).

The two 06h files as committed here (the merge-queue bytes are the ones to accept):

| File | Before (blob) | After (blob, SHA-256, bytes) |
|---|---|---|
| `wp6_1_06h_current_append_manifest.yaml` | `7cfc0758744c829dc0a154dc3f37a851bf280b0b` | `adbb334f0cd08d0ca0ceaed34d43018abf2f119d`, `344a341d687c15ae2437eef05c4a90920774823a699e8725ea188e3fb2b7860c`, 6,343 |
| `test_wp6_1_06h_append_path_closure.py` | `315b58a58ce7a9ec1833faee37a6b48f34901212` | `922ae844cf7500484f11c1fe2f736d1da4681252`, `25c511451fa99fe893d7b5b7ad9bf611c4159407e8bf0a371023591862e72748`, 26,480 |

## 5. Tests

| File | What it covers |
|---|---|
| `tests/research_system/contracts/test_w9_legacy_routes.py` (store-free) | `ACCEPTED` equals the independent O-8, O-3 and envelope pins; the reserved IDs re-derive from their domain strings; the genesis payload validates and carries the contract's values; `LEGACY_COMMAND_TYPES` equals the catalogue's command set; only genesis is bound; the route registry is exact and refuses five catalogue mutations; the 1/60 partition and every tag; C5; C4; row assignment is a bijection onto the 61 rows (LR-035/LR-038, LR-054/LR-055 and the record-less Decision pairs included); the 18 `E:`-only discriminants; W2 refs; transaction shapes; W9-T5; W9-T11 store half; supersession acyclic; W9-T21 reducer half; W9-C25 and the reserved IDs |
| `tests/research_system/integration/test_w9_legacy_runtime.py` | W9-C01-LR-001 and shared replay (generic, rebuild, Discovery, legacy); W9-C11-LR-001 retry; a second genesis; no W11 genesis; the wrong target; W9-C03-LR-001 mutations refused before binding with the receipt root unchanged; tampered catalogue, annex, contract and envelope bytes; a grant scoped elsewhere; W9-T20's three cases with both roots byte-identical when refused; an unreadable manifest; an unbound W9 command; the §2.5 asymmetry; the LR-002 three on the test registry, and LR-002 refused in production; the CLI |
| `tests/research_system/integration/test_w9_legacy_replay.py` | The shared replay with a W9 observation and a schema-valid W2-typed W9 event on the test registry; the predicate-removed, site-3-removed and lifecycle-restored negative controls; C1, C2 (both forms), C3; a deferred row; a schema-invalid payload; a W9 event type under a non-W9 command; replay's second-genesis, payload and no-W11-genesis refusals; the reserved IDs and that no reader dereferences them |

## 6. Verification

Run on the branch's working tree before commit, with `uv run pytest --no-cov -q -p no:cacheprovider`, serially:

| Check | Result |
|---|---|
| The six W9 test files together (materialization, expected catalogue, acceptance envelope, legacy routes, legacy runtime, legacy replay) | 352 passed |
| The regression set: the 06h smoke test, `test_schema_registry.py`, the W11 materialization and catalogue tests, `test_p045_envelope_decision.py`, the Discovery activation and architecture tests, the W9 materialization, catalogue, envelope and legacy-route tests, `test_store.py`, `test_command_service.py`, `test_wp6_2_t2_runtime.py` | 913 passed, 1 skipped (the existing skip in `test_schema_registry.py`) |
| `tests/research_system/integration/test_wp6_6_discovery_runtime.py` (site 2 and site 3 touch its driver) | 100 passed (30 min 31 s) |
| `uv run ruff check` and `uv run ruff format --check` on the changed files | clean |
| `verify_w9_materialization.py --require-catalogue` | 61 pinned rows, 0 problems |

The full suite was not run.

After `5f9bb8f6`, the C4 rework (§3 item 7) replaced one test in `test_w9_legacy_routes.py` with twelve. That file
now gives 51 passed, and ruff is clean. No code under `research_system/` changed.

## 7. Not in this PR

- Commands other than genesis, their binding rows and their D-4 (WP9.3, WP9.4, WP9.6, WP9.7).
- Live operations, including L-3 genesis on a real store. LR-001's two owner preconditions stay L-3 gates: O-8
  current, and the bootstrap implementation independently verified against the accepted contract, which is this PR's
  independent review together with O-3.
