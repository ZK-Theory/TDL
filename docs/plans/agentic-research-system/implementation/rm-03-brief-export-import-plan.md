# RM-03: Brief Export/Import Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> research-assurance-triage, and executing-plans-extras. This plan tools the
> P-042 sentence "ARS prepares and records bounded briefs … an authorized
> operator starts the external model session." Everything here is fail-closed:
> an export that cannot prove its inputs does not export; an import that cannot
> prove its shape, provenance, and session record does not land. **Read
> `../reviews/adversarial-rm-lane-plan-suite-review-2026-07-29.md` §C-3 and
> §§M-4-M-8, M-10, M-12 before starting** — revision 1 of this plan was
> rejected on all of them.

**Status:** REVISED 2026-07-29 (revision 2). The adversarial review returned
`reject` on revision 1 for one Critical (C-3, an unrouteable event family) and
seven Majors. Dispatch blocked on **G-RM-3** (fresh review of the revised
suite), on **G-RM-10** (confirming the artefact-family architecture), on the
**accepted artefact-record capability delivered by 06h**, and on **RM-02
merged**.
**Goal:** Deliver `ars brief export` and `ars brief import`: brief bundles
rendered from an accepted W3 context packet and methods-pack assets, and typed,
append-only, replayable landing of operator-returned material as `candidate`
artefacts that no consumer may treat as evidence without an attributed owner
transition.
**Owner authorization:** P-044 (accepted 2026-07-28; G-RM-3 and plan-specific
dependencies remain open).

## What changed in revision 2, and why

| Revision 1 | Revision 2 | Driver |
|---|---|---|
| New `ars://methods/event/MethodBriefRecorded` and `MethodResultImported` | **No new event family.** Briefs and imported results are **artefacts**, registered via the accepted `RegisterArtefact` command | **C-3**: `_build_event` rejects unknown command types and hard-codes `ars://core/event/...`; replay raises `unknown event schema` for anything outside the core and T2 prefixes. The invented family was unreachable and fatal on replay |
| Escalation "structurally unrepresentable" via four local status enums | Claim narrowed to **schema-local** escalation; the real firewall is the accepted `SetArtefactUseAuthority` transition | **M-5**: nothing stopped a consumer citing an `imported` record directly, reclassifying it in a projection, or believing a self-asserted `verified_by_operator` |
| Brief manifest was a bounded "W3 packet" | The brief **binds** an accepted W3 packet by `context_id`, revision and hash, and is explicitly a **non-governing rendering** of it | **M-6**: revision 1's manifest omitted most of W3's mandatory closure fields; `subjects[].sha256` alone does not establish it |
| `application_family` validated against the WP6.3 assurance-pack allowlist | An **RM-owned session record** captures the operator's chosen application as attributed evidence; no eligibility gate; the WP6.3 pack is not read | **M-7**: that allowlist governs independent *review* agents (`codex_standalone`/`claude_standalone`), not research-application sessions. Reusing it would reject valid sessions and silently inherit WP6.3 policy changes |
| `--allow-candidate` flag on export | **Removed entirely** | **M-1**: it bypassed the owner gate G-RM-4 with a local flag |
| "new ULID per `research_system.ids` conventions" | `art_`-prefixed UUIDv7 under the registered `artefact` kind | **M-8**: `research_system.ids` generates prefixed UUIDv7, not ULIDs; no brief/result kind exists in the catalogue, and `artefact: art` already does |
| `verification_context` reserved as nullable, unspecified | Specified now as `{schema_id, schema_version, verification_result_id, content_hash}` | **M-8**: RM-04 would otherwise embed an open object into a closed schema or leave it unconstrained |
| De-identification sidecar `{stripped, mapping_sha256}` | Opaque `sidecar_id` + hash in the brief; the sidecar is an immutable ARS-side object | **M-10**: a digest neither locates nor authorizes the mapping |
| Provider denylist guard | **Capability boundary**: AST import allowlist plus dependency-graph constraint | **M-4**: a denylist is open-world — `importlib`, subprocess, sockets, config-driven endpoints and transitive dependencies all evade it, and it forced provider names into the lane's own files |
| Assurance lane: Output/Provenance | Output/Provenance **and Paper Claim governance** | **M-12** |
| `P-044 (pending)`; "Full quality gates" | Accepted status; exact command set | **m-1**, **m-3** |

## Architecture

**Export** compiles a bundle from two inputs: an accepted **W3 context packet**
(the governing authority for what may be shown) and the RM-02 methods pack (the
protocol to follow). The bundle is a *rendering* — it governs nothing. Its
manifest binds the packet by `context_id`, revision and exact packet hash, so a
reader can always recover the governing object. The export is recorded by
registering the bundle as an artefact.

**Import** validates returned material against closed schemas, requires the
session record, re-verifies the brief manifest hash it responds to, stores the
document content-addressed, and registers it as an artefact at
`use_authority: candidate`.

**The firewall** is not the import schemas. It is the accepted
`ars://core/command/SetArtefactUseAuthority` transition: moving an artefact from
`candidate` to `accepted_for_scope` requires an attributed command whose
`subject_sha256` matches the artefact's `content_sha256`, carrying a
`consumer_predicate`. Nothing in this plan issues that command. Import schemas
still carry closed status enums, but the claim made for them is only the narrow,
true one: **schema-local escalation is unrepresentable** — a returned document
cannot spell itself into acceptance. Consumer-level protection is the artefact
authority state, and it is tested end to end (Task 6).

## Global constraints

- All standing constraints of rm-00 §5 apply. Branch
  `pipe/rm-03-brief-export-import`. Copy `.env` into the worktree.
- **P-042 hard boundary (O-RM-1):** no provider SDK import, no HTTP call, no
  subprocess spawning any model CLI, no credential file read, anywhere in this
  change. Task 5 builds the capability boundary.
- **No new event family and no core-routing change.** Brief and import records
  use the accepted artefact command family wired by 06h. If that capability is
  absent or behaves differently than 06h's acceptance record states, **stop
  Partial** — do not fall back to a direct `ledger.append`.
- **No execution of anything.** `verification_recipe` is recorded as opaque
  text and never run (G-RM-11, review C-4). If a task finds itself needing to
  run returned content, stop Partial.
- Do not modify RM-02's manifest, revision history, assets, or their lifecycle
  fields. The exporter consumes the pack strictly read-only.
- Do not read `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml`
  (M-7) — it is neither a do-not-touch violation nor a dependency; it is simply
  not this lane's authority.

## File map

**Create:**

~~~text
.research-system/schemas/methods/brief-manifest.schema.json           # ars://methods/brief-manifest
.research-system/schemas/methods/session-record.schema.json           # ars://methods/session-record
.research-system/schemas/methods/deidentification-sidecar.schema.json # ars://methods/deidentification-sidecar
.research-system/schemas/methods/review-finding-set.schema.json       # ars://methods/import/ReviewFindingSet
.research-system/schemas/methods/counterexample-candidate.schema.json # ars://methods/import/CounterexampleCandidate
.research-system/schemas/methods/theorem-citation.schema.json         # ars://methods/import/TheoremCitation
.research-system/schemas/methods/operator-verification.schema.json    # ars://methods/import/OperatorVerification
.research-system/schemas/methods/exploratory-memo.schema.json         # ars://methods/import/ExploratoryMemo
research_system/methods/brief.py           # compile/export
research_system/methods/importer.py        # validate/land
tests/research_system/unit/test_brief_export.py
tests/research_system/unit/test_brief_import.py
tests/research_system/unit/test_methods_capability_boundary.py
tests/research_system/integration/test_brief_round_trip.py
tests/research_system/integration/test_claim_consumer_firewall.py
~~~

**Modify:**

~~~text
research_system/cli.py                     # new `brief` group: export, import
~~~

These schemas are **document** schemas under `ars://methods/...`, not event
schemas. No `ars://methods/event/...` id appears anywhere in this plan.

## Interface specifications

### Brief bundle (output of export)

A directory containing:

1. **`brief-manifest.json`** — validates against `ars://methods/brief-manifest`.
   Required:
   - `brief_artefact_id` — `art_`-prefixed UUIDv7 from `research_system.ids`
     under the registered `artefact` kind (M-8);
   - `context_packet` — `{context_id, revision, packet_sha256}` binding the
     **accepted W3 packet** this brief renders (M-6, O-RM-20). Export fails if
     the packet is absent, superseded, or hash-mismatched;
   - `created_at`;
   - `subjects[]` — `{path_or_name, sha256, role}`, exact-subject discipline,
     each entry required to be present in the bound packet's scope;
   - `assets[]` — `{asset_id, version, identity, identity_scheme}` copied from
     the verified RM-02 pack;
   - `expected_import_types[]` — the import `$id`s this brief solicits;
   - `deidentification` — nullable `{sidecar_id, sidecar_hash}` **only** (M-10);
     the mapping never appears in the bundle;
   - `prohibitions` — const block, verbatim: no claim promotion, no result
     acceptance, no transcript return, session record required;
   - `required_session_fields` — const list, per the session record below;
   - `verification_context` — nullable, and **specified now** as
     `{schema_id, schema_version, verification_result_id, content_hash}` (M-8),
     so RM-04 embeds a versioned reference rather than an open object.
2. **`brief.md`** — the operator-facing document: rendered subjects (or their
   de-identified forms), the selected asset protocol bodies, the expected-output
   section naming the import types, and the prohibitions block. Its SHA-256 is
   recorded in the manifest.

**The bundle governs nothing.** State this in the manifest schema description
and in `brief.md`: it is a rendering of the bound context packet, and the packet
is the authority (M-6).

**Export rules, all fail-closed:** any selected asset not `accepted` in the pack
manifest → error, **with no override flag** (M-1); bound packet missing,
superseded or hash-mismatched → error; a subject outside the packet's scope →
error; a subject file unreadable → error; recomputed asset identity mismatch →
error; an unresolved conflict recorded in the packet → error; a source the
packet marks unsafe or restricted → error. On success, register the bundle as an
artefact via the accepted `RegisterArtefact` command.

### Session record (required on every import; P-042 O-RM-3, corrected per M-7)

`ars://methods/session-record`:
`{operator_actor_id, application_family, application_version (nullable),
application_choice_by: const "operator", session_date,
responds_to_brief_manifest_sha256}`.

`application_family` is a **recorded free string with an attributed actor** —
evidence of what the operator chose, not an eligibility check. There is no
allowlist. Rationale (M-7): the WP6.3 assurance pack's `operator_model` list
governs independent review agents, not research-application sessions; borrowing
it would reject valid sessions and make RM policy a silent dependent of WP6.3
review policy.

### Import types (closed status enums — the *schema-local* no-escalation rule)

- `ReviewFindingSet` — `brief_artefact_id`, `findings[]` each
  `{location, severity: note|minor|major|critical, statement,
  falsifiable_check (nullable), self_critique_survived: bool}`;
  `status` enum: **`imported`** only.
- `CounterexampleCandidate` — `brief_artefact_id`, `target_statement`,
  `instance` (structured), `claimed_violation`,
  `verification_recipe` (nullable, **recorded as opaque text, never executed**);
  `status` enum: **`candidate`** only.
- `TheoremCitation` — `brief_artefact_id`, `statement`, `source_reference`;
  `status` enum: **`imported`** only. **No `verification` field** (M-5) — see
  below.
- `ExploratoryMemo` — `brief_artefact_id`, `body`, `decomposition[]` (nullable);
  `status` enum: **`imported`** only.

All: `additionalProperties: false`. The ban on `transcript`, `reasoning`,
`chain_of_thought` fields is expressed by the closed property set; Task 4(c)
tests it.

**Operator verification is a separate attributed record (M-5).** Revision 1 put
`verification: verified_by_operator | unverified` inside `TheoremCitation` —
but that value arrives inside the document the model returned, so it was the
model asserting the operator's act. Verification now lands as
`ars://methods/import/OperatorVerification`:
`{cites_artefact_id, citation_content_hash, verified_by_actor_id, verified_on,
verification_basis}`, imported separately, binding the exact citation bytes. A
`TheoremCitation` with no such record is simply unverified — a state, not a
claim in the document.

### Import landing

`ars brief import --bundle <path>`: validate the document against its declared
import `$id` → validate the session record → verify
`responds_to_brief_manifest_sha256` matches a registered brief artefact → store
the document content-addressed in the object store → register it as an artefact
via `RegisterArtefact` with `authority.use_authority: candidate`. Replay
reproduces the projection (Task 6).

Nothing in this plan issues `SetArtefactUseAuthority`. Promotion to
`accepted_for_scope` is Stephen's attributed act (O-RM-4, W5 §19.3).

## Obligation register

| ID | Source | Obligation | Disposition |
|---|---|---|---|
| R3-1 | P-042 | Record bounded briefs, exact subjects, returned evidence, operator session choice | Brief manifest + session record + artefact registration |
| R3-2 | P-042 / O-RM-1 | No provider invocation surface | Task 5 capability boundary |
| R3-3 | W5 §19 / O-RM-4 | Structurally below acceptance/promotion | Closed status enums (schema-local) **plus** the artefact use-authority firewall; Task 6 |
| R3-4 | W3 §15 / O-RM-6 | No transcripts/hidden reasoning ingested | `additionalProperties: false`; Task 4(c) |
| R3-5 | W3 §9 packet discipline | Subjects bound by exact hash **within a bound accepted packet** | Manifest `context_packet` + `subjects`; Task 4 |
| R3-6 | R2-6 / M-5 | Operator verification is a separate attributed act, not a self-asserted field | `OperatorVerification` record |
| R3-7 | O-RM-16 / W2 | Append-only, replayable through accepted interfaces | `RegisterArtefact`; Task 6 replay |
| R3-8 | O-RM-15 | Rollback = `superseded`/`rejected` use-authority; artefacts immutable, never deleted | No delete path exists in this change; assert in review |
| R3-9 | M-7 | Session authority is RM-owned; the WP6.3 pack is not read | Session record schema |
| R3-10 | M-6 / O-RM-20 | The brief binds an accepted W3 packet and is non-governing | Manifest `context_packet`; Task 4 controls |
| R3-11 | M-10 / O-RM-21 | De-identification is reversible by ARS and not by the operator | Sidecar object; Task 4 round-trip controls |
| R3-12 | M-12 / O-RM-22 | Paper Claim governance applies | Assurance section below |

## Research assurance requirements

- **Lanes:** Output/Provenance **and Paper Claim governance** (M-12). This plan
  carries externally-produced review findings and counterexamples toward work
  that may reach a manuscript, so claim-consumer, wording-strength and
  human-authority controls apply — not provenance controls alone.
- **Machine-checkable claims:** every rule in the two fail-closed lists has a
  red-then-green test; replay reproduces import projections; imported artefacts
  are `candidate` and provably cannot be consumed as evidence (Task 6); the
  capability boundary fires on every evasion path in Task 5.
- **Human-review-only:** is `brief.md` usable by an operator mid-session? Does
  the prohibitions block read as instructions to the *external model* too (it
  should)? Does the bundle make its non-governing status obvious to a reader
  who never sees the packet?
- **Partial criteria:** the 06h artefact capability is absent or differs from
  its acceptance record; core validation routing would have to change; no
  accepted W3 packet mechanism is reachable to bind (report — do not invent a
  substitute packet, which is exactly what M-6 rejected); the sidecar needs an
  object store this plan does not own.

## Tasks

- [ ] **Task 1 — Schemas first.** Author all eight document schemas; contract
      test validating each against the meta-schema and its `$id` uniqueness,
      plus a test asserting **no schema in this plan uses an
      `ars://methods/event/...` id** (C-3 regression guard).
      Commit: `[PIPELINE] P00: methods brief, session, and import schema family`.
- [ ] **Task 2 — Exporter.** Failing test: export for a fixture task where one
      selected asset is `candidate` → typed error with no override available;
      with `accepted` assets and a valid bound packet → bundle validates,
      identities recomputed, brief artefact registered and schema-valid. Then
      implement `brief.py` + CLI `brief export`.
      Commit: `[PIPELINE] P00: fail-closed brief exporter (ars brief export)`.
- [ ] **Task 3 — Importer.** Failing test: a conforming `ReviewFindingSet`
      bundle referencing a registered brief lands as a `candidate` artefact and
      replays. Then implement `importer.py` + CLI `brief import`.
      Commit: `[PIPELINE] P00: typed fail-closed brief importer (ars brief import)`.
- [ ] **Task 4 — Negative controls** (each red first):
      (a) unknown/absent brief hash → rejected;
      (b) missing any session-record field → rejected;
      (c) extra field `transcript`/`reasoning`/`chain_of_thought` → rejected;
      (d) doctored `status` (`accepted`, `promoted`) → schema rejection;
      (e) hash-mismatched subject reference → rejected;
      (f) subject outside the bound packet's scope → rejected;
      (g) **stale packet** (superseded revision) → rejected;
      (h) **omitted governing source** recorded in the packet → rejected;
      (i) unresolved conflict recorded in the packet → rejected;
      (j) unsafe/restricted source in the packet → rejected;
      (k) delivery/packet hash mismatch → rejected;
      (l) sidecar: wrong join, missing sidecar, stale revision, unauthorized
      consumer → each rejected; exact round-trip re-identification succeeds;
      (m) `OperatorVerification` whose `citation_content_hash` does not match
      the cited artefact → rejected (forged operator verification).
      Commit: `[PIPELINE] P00: brief import negative controls`.
- [ ] **Task 5 — Capability boundary (replaces the denylist, M-4).**
      `test_methods_capability_boundary.py` asserts, by AST analysis over
      `research_system/methods/**`:
      (i) every import resolves to an **allowlisted** module set (stdlib subset
      + `jsonschema` + `yaml` + first-party `research_system.*`);
      (ii) no transport or tool interface appears anywhere in the package's
      **transitive** dependency graph;
      (iii) no dynamic import (`importlib`, `__import__`, `eval`, `exec`);
      (iv) no `subprocess`/`os.system`/`os.exec*`;
      (v) no `socket`, no URL literal, no credential-path literal.
      Negative controls plant, in **test fixtures using neutral synthetic
      module names** (never real provider names — O-RM-14, M-4), each of:
      indirect import, dynamic import, subprocess, generic URL, socket,
      MCP/tool seam, and a transitive dependency that itself calls out. Each
      must make the guard fail. Do not commit any plant.
      Commit: `[PIPELINE] P00: capability-boundary guard for the methods package (P-042)`.
- [ ] **Task 6 — Round trip, replay, and the claim-consumer firewall.**
      `test_brief_round_trip.py`: export → write a conforming result bundle by
      hand in the test (simulating the operator) → import → replay/projection
      rebuild reproduces identical state.
      `test_claim_consumer_firewall.py` (M-5) proves the end-to-end property the
      status enums do not:
      (a) an imported `candidate` artefact cannot be consumed as result or
      claim evidence;
      (b) a projection cannot reclassify it;
      (c) a `SetArtefactUseAuthority` with a mismatched `subject_sha256` is
      rejected;
      (d) supersession of an imported artefact leaves the original immutable;
      (e) a consumer parsing `status` loosely still fails the authority check;
      (f) absent an attributed P-005 decision, no promotion path exists.
      Commit: `[PIPELINE] P00: brief round-trip, replay, and claim-consumer firewall`.

## Close-out

- Exact verification commands (m-3):

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/unit/test_brief_export.py tests/research_system/unit/test_brief_import.py tests/research_system/unit/test_methods_capability_boundary.py tests/research_system/integration/test_brief_round_trip.py tests/research_system/integration/test_claim_consumer_firewall.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync python -m pytest -q tests/research_system/smoke/test_append_path_smoke.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system
~~~

  The full `tests/research_system` tree runs once at final exact head, because
  this plan touches `cli.py` and the artefact seam — a broader blast radius than
  RM-02's.
- PR; CodeRabbit concludes; merge per house rule.
- README lane row; vault `[PIPELINE]` entry naming the two CLI commands, the
  schema family, the artefact-family binding, and the P-042 boundary.
