# RM-03: Brief Export/Import Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> research-assurance-triage, and executing-plans-extras. This plan tools the
> P-042 sentence "ARS prepares and records bounded briefs … an authorized
> operator starts the external model session." Everything here is fail-closed:
> an export that cannot prove its inputs does not export; an import that
> cannot prove its shape, provenance, and session metadata does not land.

**Status:** PROPOSED — dispatch blocked on G-RM-2, G-RM-3, **and** on RM-01
Task A merged (green append path) and RM-02 merged (assets to select).
**Goal:** Deliver `ars brief export` and `ars brief import`: schema-validated
brief bundles compiled from methods-pack assets and exact subjects; typed,
append-only, replayable landing of operator-returned results strictly below
result acceptance and claim promotion.
**Architecture:** Export is a pure compilation (no ledger write is required to
*build* the bundle, but the export is *recorded* as an event so imports can bind
to it). Import validates against closed schemas, requires the P-042 session
metadata block, re-verifies the brief-manifest hash it responds to, and lands
one `MethodResultImported` event per import plus content-addressed artifacts in
the object store. Import types carry closed status enums whose members cannot
express acceptance or promotion — escalation is structurally unrepresentable,
not merely forbidden.
**Tech stack:** Python 3.13, argparse (existing CLI conventions), jsonschema,
existing `CommandService`/`EventLedger`/`ObjectStore` seams, pytest, ruff.
**Owner authorization:** P-044 (pending).

## Global constraints

- All standing constraints of rm-00 §5 apply. Branch
  `pipe/rm-03-brief-export-import`.
- **P-042 hard boundary (O-RM-1):** no provider SDK import, no HTTP call, no
  subprocess spawning any model CLI, no credential file read, anywhere in this
  change. Task 5 adds the mechanical guard.
- New event schemas go under `.research-system/schemas/methods/` with
  `ars://methods/...` ids — **not** under `schemas/core/events/` (that family
  is WP6.1's accepted generated set; extending it would create a currency
  question this lane must not own). If the ledger/validator architecture makes
  a separate schema family impossible without modifying core validation
  routing, stop Partial and report the exact constraint.
- Do not modify RM-02's manifest schema, assets, or the manifest's
  `review_state`/`owner_acceptance` fields (state flips are owner-gated under
  G-RM-4). The exporter consumes the pack strictly read-only.

## File map

**Create:**

~~~text
.research-system/schemas/methods/brief-manifest.schema.json          # ars://methods/brief-manifest
.research-system/schemas/methods/brief-recorded.schema.json          # ars://methods/event/MethodBriefRecorded
.research-system/schemas/methods/result-imported.schema.json         # ars://methods/event/MethodResultImported
.research-system/schemas/methods/review-finding-set.schema.json      # ars://methods/import/ReviewFindingSet
.research-system/schemas/methods/counterexample-candidate.schema.json# ars://methods/import/CounterexampleCandidate
.research-system/schemas/methods/theorem-citation.schema.json        # ars://methods/import/TheoremCitation
.research-system/schemas/methods/exploratory-memo.schema.json        # ars://methods/import/ExploratoryMemo
research_system/methods/brief.py           # compile/export
research_system/methods/importer.py        # validate/land
tests/research_system/unit/test_brief_export.py
tests/research_system/unit/test_brief_import.py
tests/research_system/unit/test_no_provider_surface.py
tests/research_system/integration/test_brief_round_trip.py
~~~

**Modify:**

~~~text
research_system/cli.py                     # new `brief` group: export, import
~~~

## Interface specifications

### Brief bundle (output of export)

A directory (or single JSON per implementer judgment — record the choice)
containing:

1. `brief-manifest.json` — validates against `ars://methods/brief-manifest`.
   Required: `brief_id` (new ULID per `research_system.ids` conventions),
   `created_at`, `task_reference` (free-form work identifier plus optional
   ledger task ID), `subjects` (array of `{path_or_name, sha256, role}` —
   exact-subject discipline), `assets` (array of `{asset_id, version, sha256}`
   copied from the verified pack), `expected_import_types` (array of the four
   import `$id`s), `deidentification` (nullable sidecar per RM-02 asset 3:
   `{stripped: [...], mapping_sha256}` — mapping stored ARS-side only, never
   in the operator-facing brief body), `prohibitions` (const block, verbatim:
   no claim promotion, no result acceptance, no transcript return, session
   metadata required), `required_session_metadata` (const list, §import),
   `verification_context` (nullable; RM-04 uses it for round-trips — schema
   reserves it now so RM-04 does not bump the schema).
2. `brief.md` — the operator-facing document: rendered subjects (or
   de-identified forms), selected asset protocol bodies, the expected-output
   section naming the import types, and the prohibitions block. Human-readable;
   its sha256 is recorded in the manifest.

Export rules (all fail-closed): asset not `accepted` in the pack manifest →
error unless `--allow-candidate` is passed **and** the manifest records that
flag was used; subject file unreadable → error; recompiled asset hash mismatch
→ error. On success, emit `MethodBriefRecorded` (brief_id, manifest sha256,
asset ids/hashes, subject hashes) through the ledger seam RM-01 fixed.

### Import types (closed status enums — the structural no-escalation rule)

- `ReviewFindingSet`: `brief_id`, `findings[]` each
  `{location, severity: note|minor|major|critical, statement, falsifiable_check (nullable), self_critique_survived: bool}`,
  `status` enum: **`imported`** only.
- `CounterexampleCandidate`: `brief_id`, `target_statement`, `instance`
  (structured), `claimed_violation`, `verification_recipe` (nullable —
  consumed by RM-04), `status` enum: **`candidate`** only.
- `TheoremCitation`: `brief_id`, `statement`, `source_reference`,
  `verification` enum: **`verified_by_operator` | `unverified`** (R2-6),
  `status` enum: **`imported`** only.
- `ExploratoryMemo`: `brief_id`, `body`, `decomposition[]` (nullable),
  `status` enum: **`imported`** only.

All: `additionalProperties: false`; an explicit schema-level ban on fields
named `transcript`, `reasoning`, `chain_of_thought` is expressed by the closed
property set — the *test* for it is Task 4(c).

### Session metadata block (required on every import; P-042 O-RM-3)

`{operator: str, application_family: str, application_choice_by: const "operator", session_date: str, responds_to_brief_manifest_sha256: str}`.
`application_family` validates against the same recognised-family allowlist the
WP6.3 assurance pack uses (read it from that accepted contract; do not copy the
list into a second authority — reference by path + hash).

### Import landing

`ars brief import --bundle <path>`: validate file against its declared import
`$id` → verify `responds_to_brief_manifest_sha256` matches a recorded
`MethodBriefRecorded` event → store the document content-addressed in the
object store → emit `MethodResultImported` (import type, content id/hash,
brief_id, session metadata). Replay must reproduce the projection (Task 6).

## Obligation register

| ID | Source | Obligation | Disposition |
|---|---|---|---|
| R3-1 | P-042 | Record bounded briefs, exact subjects, returned evidence, operator session choice | Brief manifest + session metadata + events |
| R3-2 | P-042 / O-RM-1 | No provider invocation surface | Task 5 guard test |
| R3-3 | W5 §19 / O-RM-4 | Structurally below acceptance/promotion | Closed status enums; Task 4(d) |
| R3-4 | W3 §15 / O-RM-6 | No transcripts/hidden reasoning ingested | `additionalProperties: false`; Task 4(c) |
| R3-5 | W3 §9.1 packet discipline | Subjects bound by exact hash | Manifest `subjects` + import hash check |
| R3-6 | R2-6 | Unverified theorem retrievals cannot claim verified status | `TheoremCitation.verification` enum |
| R3-7 | O-RM-16 | Append-only, replayable | Events through ledger; Task 6 replay check |
| R3-8 | O-RM-15 | Rollback = disable commands; artifacts immutable | CLI-level disable is sufficient; no delete path exists in this change (assert in review) |
| R3-9 | WP6.3 accepted pack | Allowlist referenced, not duplicated | Session-metadata validation reads the accepted contract by path+hash |

## Research assurance requirements

- **Lanes:** Output/Provenance. **Machine-checkable claims:** every rule in
  the two "fail-closed" lists above has a red-then-green test; replay
  reproduces import projections; the guard test fails when a provider import
  is planted (verified once by mutation, then the plant removed).
- **Human-review-only:** is `brief.md` actually usable by an operator mid-
  session? Does the prohibitions block read as instructions to the *external
  model* too (it should)?
- **Partial criteria:** core validation routing must change; command/event
  surface expansion beyond the two new event types; session-metadata allowlist
  unreadable from the accepted contract.

## Tasks

- [ ] **Task 1 — Schemas first.** Author all seven schemas; contract test
  validating each against the meta-schema and its `$id` uniqueness.
  Commit: `[PIPELINE] P00: methods brief and import schema family`.
- [ ] **Task 2 — Exporter.** Failing test: export for a fixture task with one
  candidate-state asset (no flag) → typed error; with `accepted` assets →
  bundle validates, hashes recomputed, `MethodBriefRecorded` present and
  schema-valid. Then implement `brief.py` + CLI `brief export`.
  Commit: `[PIPELINE] P00: fail-closed brief exporter (ars brief export)`.
- [ ] **Task 3 — Importer.** Failing test: conforming `ReviewFindingSet`
  bundle referencing a recorded brief lands and replays. Then implement
  `importer.py` + CLI `brief import`.
  Commit: `[PIPELINE] P00: typed fail-closed brief importer (ars brief import)`.
- [ ] **Task 4 — Negative controls** (each red first): (a) unknown/absent
  brief hash → rejected; (b) missing any session-metadata field → rejected;
  (c) extra field `transcript`/`reasoning` → rejected; (d) doctored `status`
  value (`accepted`, `promoted`) → schema rejection; (e) hash-mismatched
  subject reference → rejected; (f) `TheoremCitation` with fabricated
  `verification` value → rejected; (g) `application_family` outside the
  referenced allowlist → rejected.
  Commit: `[PIPELINE] P00: brief import negative controls`.
- [ ] **Task 5 — Provider-surface guard.**
  `test_no_provider_surface.py`: walks `research_system/**/*.py` asserting no
  import of provider SDK modules (maintained denylist constant: e.g.
  `anthropic`, `openai`, `google.generativeai`, `google.genai`, `mistralai`,
  `cohere`) and no `requests`/`httpx`/`urllib.request` usage inside
  `research_system/methods/`. Verify it fires by temporarily planting a
  denylisted import (do not commit the plant).
  Commit: `[PIPELINE] P00: mechanical no-provider-surface guard (P-042)`.
- [ ] **Task 6 — Round trip + replay.** Integration test: export → simulate
  operator by writing a conforming result bundle by hand in the test → import
  → `replay`/projection rebuild reproduces identical state.
  Commit: `[PIPELINE] P00: brief round-trip and replay integration`.

## Close-out

- Full quality gates (ruff + the RM-01 smoke + targeted suites); PR;
  CodeRabbit concludes; merge per house rule.
- README lane row; vault `[PIPELINE]` entry naming the two CLI commands, the
  schema family, and the P-042 binding.
