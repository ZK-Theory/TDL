# 06e — WP6.2 literal live-result replacement map

**Date:** 2026-07-17<br>
**Status:** normative proposed plan annex, pending exact-revision review and owner
approval; authorizes no implementation or live call<br>
**Authority:** accepted Gate 5 merge `f49a27fe15ae4df566c9107dc07f7451f51b924a`;
P-035 composition choice; parent plan 06b §6.2

This annex is the exclusive expected-side source for the 51 live-result replacements
used by WP6.2 T7. It was derived once from the accepted `p0-coverage.yaml`, the exact
Gate 5 variant matrix, and the fixture grader manifests at the accepted Gate 5 merge.
Future runtime manifests, result ledgers, and stage loaders are comparison inputs only;
they must not generate, filter, repair, or relabel this expected set.

## 1. Closed construction rule

- A predecessor and successor are literal six-tuples in the canonical order
  `(fixture_id, fixture_revision, grader_id, grader_class, grader_version, variant_id)`.
- The first five successor fields equal the predecessor fields byte-for-byte.
- The successor `variant_id` is exactly `live-capability--` followed by the complete
  predecessor `variant_id`; no other normalization or provider-derived alias is legal.
- `M` rows require an eligible real model grader, cross-family/context independence,
  and a W7 live adapter. `H` rows require the named attributed human authority and use
  typed `not_applicable` provider/model/adapter bindings; model evidence cannot satisfy
  an H row.
- Every row has replacement scope `live_capability_only`. The frozen predecessor
  remains immutable and addressable as `foundation_release` evidence.

The successor construction and H-row binding semantics become authoritative only when
Stephen approves the exact independently reviewed D-G6-3 revision.

## 2. Literal 51-row map

| # | Frozen predecessor six-tuple | Exact successor six-tuple | Expected provider / model / adapter class | Scope |
|---:|---|---|---|---|
| 01 | `(F-005, r1, f-005-human-authority, H, control-store-v1, baseline)` | `(F-005, r1, f-005-human-authority, H, control-store-v1, live-capability--baseline)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 02 | `(F-009, r1, f-009-human-authority, H, adapter-scientific-v1, baseline)` | `(F-009, r1, f-009-human-authority, H, adapter-scientific-v1, live-capability--baseline)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 03 | `(F-009, r1, f-009-human-authority, H, adapter-scientific-v1, fake-claude-adapter-v1-windows-fake-transport)` | `(F-009, r1, f-009-human-authority, H, adapter-scientific-v1, live-capability--fake-claude-adapter-v1-windows-fake-transport)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 04 | `(F-009, r1, f-009-human-authority, H, adapter-scientific-v1, fake-codex-adapter-v1-windows-fake-transport)` | `(F-009, r1, f-009-human-authority, H, adapter-scientific-v1, live-capability--fake-codex-adapter-v1-windows-fake-transport)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 05 | `(F-012, r1, f-012-independent-model, M, adapter-scientific-v1, baseline)` | `(F-012, r1, f-012-independent-model, M, adapter-scientific-v1, live-capability--baseline)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 06 | `(F-012, r1, f-012-independent-model, M, adapter-scientific-v1, fake-claude-adapter-v1-windows-fake-transport)` | `(F-012, r1, f-012-independent-model, M, adapter-scientific-v1, live-capability--fake-claude-adapter-v1-windows-fake-transport)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 07 | `(F-012, r1, f-012-independent-model, M, adapter-scientific-v1, fake-codex-adapter-v1-windows-fake-transport)` | `(F-012, r1, f-012-independent-model, M, adapter-scientific-v1, live-capability--fake-codex-adapter-v1-windows-fake-transport)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 08 | `(F-014, r1, f-014-human-authority, H, adapter-scientific-v1, baseline)` | `(F-014, r1, f-014-human-authority, H, adapter-scientific-v1, live-capability--baseline)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 09 | `(F-014, r1, f-014-human-authority, H, adapter-scientific-v1, fake-claude-adapter-v1-windows-fake-transport)` | `(F-014, r1, f-014-human-authority, H, adapter-scientific-v1, live-capability--fake-claude-adapter-v1-windows-fake-transport)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 10 | `(F-014, r1, f-014-human-authority, H, adapter-scientific-v1, fake-codex-adapter-v1-windows-fake-transport)` | `(F-014, r1, f-014-human-authority, H, adapter-scientific-v1, live-capability--fake-codex-adapter-v1-windows-fake-transport)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 11 | `(F-020, r2, f-020-independent-model, M, adapter-scientific-v1, baseline)` | `(F-020, r2, f-020-independent-model, M, adapter-scientific-v1, live-capability--baseline)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 12 | `(F-020, r2, f-020-independent-model, M, adapter-scientific-v1, fake-claude-adapter-v1-windows-fake-transport)` | `(F-020, r2, f-020-independent-model, M, adapter-scientific-v1, live-capability--fake-claude-adapter-v1-windows-fake-transport)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 13 | `(F-020, r2, f-020-independent-model, M, adapter-scientific-v1, fake-codex-adapter-v1-windows-fake-transport)` | `(F-020, r2, f-020-independent-model, M, adapter-scientific-v1, live-capability--fake-codex-adapter-v1-windows-fake-transport)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 14 | `(F-021, r2, f-021-independent-model, M, context-routing-v1, baseline)` | `(F-021, r2, f-021-independent-model, M, context-routing-v1, live-capability--baseline)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 15 | `(F-022, r1, f-022-human-authority, H, context-routing-v1, baseline)` | `(F-022, r1, f-022-human-authority, H, context-routing-v1, live-capability--baseline)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 16 | `(F-022, r1, f-022-human-authority, H, context-routing-v1, mandatory_closure_sizing-fake-claude-count-v1)` | `(F-022, r1, f-022-human-authority, H, context-routing-v1, live-capability--mandatory_closure_sizing-fake-claude-count-v1)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 17 | `(F-022, r1, f-022-human-authority, H, context-routing-v1, mandatory_closure_sizing-fake-codex-count-v1)` | `(F-022, r1, f-022-human-authority, H, context-routing-v1, live-capability--mandatory_closure_sizing-fake-codex-count-v1)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 18 | `(F-022, r1, f-022-independent-model, M, context-routing-v1, baseline)` | `(F-022, r1, f-022-independent-model, M, context-routing-v1, live-capability--baseline)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 19 | `(F-022, r1, f-022-independent-model, M, context-routing-v1, mandatory_closure_sizing-fake-claude-count-v1)` | `(F-022, r1, f-022-independent-model, M, context-routing-v1, live-capability--mandatory_closure_sizing-fake-claude-count-v1)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 20 | `(F-022, r1, f-022-independent-model, M, context-routing-v1, mandatory_closure_sizing-fake-codex-count-v1)` | `(F-022, r1, f-022-independent-model, M, context-routing-v1, live-capability--mandatory_closure_sizing-fake-codex-count-v1)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 21 | `(F-025, r1, f-025-human-authority, H, context-routing-v1, baseline)` | `(F-025, r1, f-025-human-authority, H, context-routing-v1, live-capability--baseline)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 22 | `(F-025, r1, f-025-human-authority, H, context-routing-v1, mandatory_closure_sizing-fake-claude-count-v1)` | `(F-025, r1, f-025-human-authority, H, context-routing-v1, live-capability--mandatory_closure_sizing-fake-claude-count-v1)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 23 | `(F-025, r1, f-025-human-authority, H, context-routing-v1, mandatory_closure_sizing-fake-codex-count-v1)` | `(F-025, r1, f-025-human-authority, H, context-routing-v1, live-capability--mandatory_closure_sizing-fake-codex-count-v1)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 24 | `(F-025, r1, f-025-independent-model, M, context-routing-v1, baseline)` | `(F-025, r1, f-025-independent-model, M, context-routing-v1, live-capability--baseline)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 25 | `(F-025, r1, f-025-independent-model, M, context-routing-v1, mandatory_closure_sizing-fake-claude-count-v1)` | `(F-025, r1, f-025-independent-model, M, context-routing-v1, live-capability--mandatory_closure_sizing-fake-claude-count-v1)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 26 | `(F-025, r1, f-025-independent-model, M, context-routing-v1, mandatory_closure_sizing-fake-codex-count-v1)` | `(F-025, r1, f-025-independent-model, M, context-routing-v1, live-capability--mandatory_closure_sizing-fake-codex-count-v1)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 27 | `(F-026, r1, f-026-independent-model, M, context-routing-v1, baseline)` | `(F-026, r1, f-026-independent-model, M, context-routing-v1, live-capability--baseline)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 28 | `(F-026, r1, f-026-independent-model, M, context-routing-v1, mandatory_closure_sizing-fake-claude-count-v1)` | `(F-026, r1, f-026-independent-model, M, context-routing-v1, live-capability--mandatory_closure_sizing-fake-claude-count-v1)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 29 | `(F-026, r1, f-026-independent-model, M, context-routing-v1, mandatory_closure_sizing-fake-codex-count-v1)` | `(F-026, r1, f-026-independent-model, M, context-routing-v1, live-capability--mandatory_closure_sizing-fake-codex-count-v1)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 30 | `(F-031, r1, f-031-independent-model, M, context-routing-v1, baseline)` | `(F-031, r1, f-031-independent-model, M, context-routing-v1, live-capability--baseline)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 31 | `(F-031, r1, f-031-independent-model, M, context-routing-v1, mandatory_closure_sizing-fake-claude-count-v1)` | `(F-031, r1, f-031-independent-model, M, context-routing-v1, live-capability--mandatory_closure_sizing-fake-claude-count-v1)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 32 | `(F-031, r1, f-031-independent-model, M, context-routing-v1, mandatory_closure_sizing-fake-codex-count-v1)` | `(F-031, r1, f-031-independent-model, M, context-routing-v1, live-capability--mandatory_closure_sizing-fake-codex-count-v1)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 33 | `(F-032, r1, f-032-independent-model, M, adapter-scientific-v1, baseline)` | `(F-032, r1, f-032-independent-model, M, adapter-scientific-v1, live-capability--baseline)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 34 | `(F-032, r1, f-032-independent-model, M, adapter-scientific-v1, fake-claude-adapter-v1-windows-fake-transport)` | `(F-032, r1, f-032-independent-model, M, adapter-scientific-v1, live-capability--fake-claude-adapter-v1-windows-fake-transport)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 35 | `(F-032, r1, f-032-independent-model, M, adapter-scientific-v1, fake-codex-adapter-v1-windows-fake-transport)` | `(F-032, r1, f-032-independent-model, M, adapter-scientific-v1, live-capability--fake-codex-adapter-v1-windows-fake-transport)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 36 | `(F-033, r1, f-033-human-authority, H, context-routing-v1, baseline)` | `(F-033, r1, f-033-human-authority, H, context-routing-v1, live-capability--baseline)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 37 | `(F-033, r1, f-033-human-authority, H, context-routing-v1, mandatory_closure_sizing-fake-claude-count-v1)` | `(F-033, r1, f-033-human-authority, H, context-routing-v1, live-capability--mandatory_closure_sizing-fake-claude-count-v1)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 38 | `(F-033, r1, f-033-human-authority, H, context-routing-v1, mandatory_closure_sizing-fake-codex-count-v1)` | `(F-033, r1, f-033-human-authority, H, context-routing-v1, live-capability--mandatory_closure_sizing-fake-codex-count-v1)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 39 | `(F-033, r1, f-033-independent-model, M, context-routing-v1, baseline)` | `(F-033, r1, f-033-independent-model, M, context-routing-v1, live-capability--baseline)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 40 | `(F-033, r1, f-033-independent-model, M, context-routing-v1, mandatory_closure_sizing-fake-claude-count-v1)` | `(F-033, r1, f-033-independent-model, M, context-routing-v1, live-capability--mandatory_closure_sizing-fake-claude-count-v1)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 41 | `(F-033, r1, f-033-independent-model, M, context-routing-v1, mandatory_closure_sizing-fake-codex-count-v1)` | `(F-033, r1, f-033-independent-model, M, context-routing-v1, live-capability--mandatory_closure_sizing-fake-codex-count-v1)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 42 | `(F-035, r1, f-035-human-authority, H, context-routing-v1, baseline)` | `(F-035, r1, f-035-human-authority, H, context-routing-v1, live-capability--baseline)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 43 | `(F-035, r1, f-035-human-authority, H, context-routing-v1, mandatory_closure_sizing-fake-claude-count-v1)` | `(F-035, r1, f-035-human-authority, H, context-routing-v1, live-capability--mandatory_closure_sizing-fake-claude-count-v1)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 44 | `(F-035, r1, f-035-human-authority, H, context-routing-v1, mandatory_closure_sizing-fake-codex-count-v1)` | `(F-035, r1, f-035-human-authority, H, context-routing-v1, live-capability--mandatory_closure_sizing-fake-codex-count-v1)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |
| 45 | `(F-035, r1, f-035-independent-model, M, context-routing-v1, baseline)` | `(F-035, r1, f-035-independent-model, M, context-routing-v1, live-capability--baseline)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 46 | `(F-035, r1, f-035-independent-model, M, context-routing-v1, mandatory_closure_sizing-fake-claude-count-v1)` | `(F-035, r1, f-035-independent-model, M, context-routing-v1, live-capability--mandatory_closure_sizing-fake-claude-count-v1)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 47 | `(F-035, r1, f-035-independent-model, M, context-routing-v1, mandatory_closure_sizing-fake-codex-count-v1)` | `(F-035, r1, f-035-independent-model, M, context-routing-v1, live-capability--mandatory_closure_sizing-fake-codex-count-v1)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 48 | `(F-036, r2, f-036-independent-model, M, adapter-scientific-v1, baseline)` | `(F-036, r2, f-036-independent-model, M, adapter-scientific-v1, live-capability--baseline)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 49 | `(F-036, r2, f-036-independent-model, M, adapter-scientific-v1, fake-claude-adapter-v1-windows-fake-transport)` | `(F-036, r2, f-036-independent-model, M, adapter-scientific-v1, live-capability--fake-claude-adapter-v1-windows-fake-transport)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 50 | `(F-036, r2, f-036-independent-model, M, adapter-scientific-v1, fake-codex-adapter-v1-windows-fake-transport)` | `(F-036, r2, f-036-independent-model, M, adapter-scientific-v1, live-capability--fake-codex-adapter-v1-windows-fake-transport)` | eligible model grader / cross-family / W7 live adapter | `live_capability_only` |
| 51 | `(S-016, r1, s-016-human-authority, H, gate5-release-tranche-v1, baseline)` | `(S-016, r1, s-016-human-authority, H, gate5-release-tranche-v1, live-capability--baseline)` | named human authority / `not_applicable` / `not_applicable` | `live_capability_only` |

## 3. Binding and mutation contract

The accepted machine-readable semantic copy records this annex's repository path, Git
blob ID, canonical UTF-8/LF SHA-256, all 51 predecessor tuples, all 51 successor tuples,
and the construction rule. Validation compares this independent expected map with the
observed live manifest and ledger/execution evidence as a multiset of complete rows.

One-at-a-time producing-seam mutations must reject before any capability transition:
omit a predecessor before result production; duplicate a successor; swap two
predecessors; change one successor field; remove or change the `live-capability--`
prefix; relabel an H row as model-produced; use an ineligible/same-family M grader;
change provider/model/adapter class; change replacement scope; or source expected rows
from the live manifest. Every rejection leaves the event tail, accepted-result set,
capability state, Decision set, activation set, and claim set unchanged.
