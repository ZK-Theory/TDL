# RM-03: Brief Export/Import Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> research-assurance-triage, and executing-plans-extras. Read P-042, accepted
> 06i/06j interfaces, RM-02, and RR-C2/RR-M4/RR-M6 before starting.

**Integrated owner:** WP6.4 / KAN-57 under P-047. This plan supplies the real
P-042 owner-operated brief handoff and returned-material seam required before
WP6.4/Gate 6 integration.

**Status:** REVISED 2026-08-05. G-RM-3 is already closed for the accepted plan
bytes. Implementation remains absent and depends on accepted 06i/06j production
interfaces, RM-02 assets, and G-RM-4 where exact asset use is required. Dispatch is blocked on
accepted 06i and 06j exact subjects, RM-02 candidate assets, and G-RM-4
acceptance of every asset selected for export.

**Goal:** provide `ars brief export` and `ars brief import` over authoritative
W3 packet and artefact-use interfaces. Export is a non-governing rendering of
an issued/delivered packet. Import lands immutable candidate artefacts. Every
canonical use of an artefact subject or sensitive sidecar calls the 06i
production resolver.

## Architecture

**Export inputs:**

1. `resolve_context_packet_for_consumer` from accepted 06j, binding exact
   context ID/revision/hash, purpose, consumer, scope and delivery;
2. current RM-02 asset bytes/identity plus G-RM-4 replay-derived acceptance
   through 06i; and
3. exact subjects. Any subject that is an artefact is resolved through the 06i
   production consumer method selected by brief purpose.

Closed purpose mapping:

| Brief purpose | Required 06i production method |
|---|---|
| result analysis/reproduction | `resolve_for_result` |
| scientific/independent review | `resolve_for_review` |
| manuscript review | `resolve_for_manuscript` |
| claim review/promotion preparation | `resolve_for_claim` |
| de-identification reversal | `resolve_sensitive_sidecar` |

The bundle is never authority. The 06j packet remains the governing context
object; 06i remains the use-authority source.

**Import:** validate closed document/session schemas, bind the registered brief,
store exact bytes, and invoke the 06i production `RegisterArtefact` writer.
Initial authority is forced `candidate`; RM code cannot request
`accepted_for_scope`.

No tests define an alternative firewall. Integration tests exercise the 06i
production consumer methods used by the exporter/sidecar resolver.

## Global constraints

- P-042: no provider SDK, HTTP, provider CLI, credentials, or provider choice.
- No execution, runner, dynamic code loading or recipe invocation.
- No new event family or core schema edit. Use accepted 06i/06j commands.
- RM-02 is read-only. WP6.3 accepted pack bytes are neither read nor written.
- If 06i/06j public interfaces or accepted hashes differ, stop Partial.

## File map

**Create:**

~~~text
.research-system/schemas/methods/brief-manifest.schema.json
.research-system/schemas/methods/session-record.schema.json
.research-system/schemas/methods/deidentification-sidecar.schema.json
.research-system/schemas/methods/review-finding-set.schema.json
.research-system/schemas/methods/counterexample-candidate.schema.json
.research-system/schemas/methods/theorem-citation.schema.json
.research-system/schemas/methods/exploratory-memo.schema.json
research_system/methods/brief.py
research_system/methods/importer.py
tests/research_system/unit/test_brief_export.py
tests/research_system/unit/test_brief_import.py
tests/research_system/unit/test_methods_capability_boundary.py
tests/research_system/integration/test_brief_round_trip.py
tests/research_system/integration/test_methods_production_consumers.py
~~~

**Modify:**

~~~text
research_system/cli.py   # exact handler functions: brief_export, brief_import
~~~

The capability boundary names these exact handlers and resolves their complete
call/import graph. It does not allow all `research_system.*`.

## Interfaces

### Brief manifest

Closed `ars://methods/brief-manifest` fields:

~~~text
brief_artefact_id
brief_purpose
context_packet: {context_id, revision, packet_sha256, delivery_receipt_id,
                 delivery_receipt_sha256}
created_at
subjects[]: {subject_id, subject_kind, path_or_name, sha256, role,
             use_predicate_id, use_predicate_version, use_predicate_sha256}
assets[]: {asset_id, version, identity, identity_scheme,
           accepted_use_event_id, accepted_use_event_sha256}
expected_import_types[]
deidentification: null | {sidecar_artefact_id, revision, content_sha256}
prohibitions
required_session_fields
verification_context: null
brief_sha256
~~~

Export re-resolves the 06j packet at load and immediately before return. It
requires current, issued, delivered state; exact recipient/purpose/scope;
complete mandatory closure; no governing omission/conflict; safe source set;
matching delivery hash; and exact subject membership.

Every artefact subject and RM asset is then resolved through the mapped 06i
consumer method. A local path, manifest status or projection cannot substitute.

### Session record

`{operator_actor_id, application_family, application_version,
application_choice_by: "operator", session_date,
responds_to_brief_manifest_sha256}`.

`application_family` is attributed free text, not an eligibility allowlist.
The WP6.3 independent-review pack is not an authority for operator applications.

### Import types

- `ReviewFindingSet`: imported-only local status, exact brief, typed findings;
- `CounterexampleCandidate`: candidate-only, opaque unexecuted recipe;
- `TheoremCitation`: imported-only, no embedded verification assertion;
- `ExploratoryMemo`: imported-only.

All schemas are closed and forbid transcript/hidden-reasoning fields.
Schema-local status is descriptive only. RM-03 requires
`verification_context: null`; RM-04 alone may add the separately attributed
`OperatorVerificationRun` reference and record contract.

### Sidecar

The sidecar bytes contain ID/revision/hash/subject set/transform/sensitivity/
retention and the reversible mapping. They contain no consumer allowlist.
Operator bundles contain only ID/revision/hash. Reversal calls
`resolve_sensitive_sidecar`; 06i replay state independently decides consumer,
scope and current access.

## Obligations

| ID | Obligation | Enforcement |
|---|---|---|
| R3-1 | bounded exact brief/session/evidence | manifest/session/06i registration |
| R3-2 | no provider operation | complete capability graph |
| R3-3 | candidate cannot feed canonical evidence | 06i production consumers, not test helper |
| R3-4 | no transcript/hidden reasoning | closed schemas |
| R3-5 | exact subject inside accepted packet | 06j resolver + subject mapping |
| R3-6 | operator verification is neither embedded nor implied | null slot; RM-04 owns separate request/run records |
| R3-7 | append-only replay | 06i commands |
| R3-8 | rollback without delete | 06i rejected/restricted/superseded |
| R3-9 | RM-owned session provenance | session schema |
| R3-10 | accepted reachable W3 packet | 06j |
| R3-11 | reversible, independently authorized sidecar | 06i sensitive-sidecar consumer |
| R3-12 | Paper Claim governance | assurance + claim resolver |

## Capability boundary

Analyze:

- every created/modified `research_system/methods/**` module;
- exact AST bodies of `brief_export` and `brief_import` in `cli.py`; and
- the fully resolved transitive first-party call/import graph from those roots.

The allowed module set is closed and enumerated from accepted 06i/06j ports,
standard-library parsing/path primitives, `jsonschema`, and `yaml`. A blanket
`research_system.*` allowance is forbidden.

Reject dynamic import, `eval`/`exec`, process launch, socket/network/URL/tool/MCP
seams, credential paths and config-selected transport. Preserve only the
pre-existing fixed-argv Git-root-discovery operation in
`_registered_code_roots`, matched by exact function and AST shape; any second
subprocess call fails.

Neutral fixtures plant each direct, CLI-only, and transitive evasion and prove
the guard fires.

## Tasks

1. **Schemas.** Author seven closed document schemas and `$id` uniqueness tests;
   assert no `ars://methods/event/**`.
2. **Exporter.** Resolve 06j packet twice, 06i assets/subjects by purpose, and
   sidecar when needed; build/register the exact bundle. Candidate asset,
   wrong-purpose consumer or direct-path substitution fails.
3. **Importer.** Validate session/document/brief bindings; content-address bytes;
   call 06i registration writer; assert forced candidate state.
4. **Controls.** Absent/stale/wrong-but-valid/cross-packet/delivery-mismatched
   packet; omitted governing source; unresolved conflict; unsafe source; wrong
   subject; cross-brief substitution; transcript field; unexpected verification
   assertion; wrong/missing/stale sidecar; unauthorized sidecar consumer.
5. **Capability graph.** Implement the closed roots and all direct/CLI/
   transitive negative fixtures above.
6. **Production consumer proof.** Through the real exporter/consumer port,
   prove candidate, local-status parse, projection reclassification,
   wrong-but-valid authority record, superseded artefact, missing P-005
   decision, wrong predicate/scope/consumer, and unauthorized sidecar all fail.
   Prove a correctly accepted review/manuscript subject succeeds without claim
   promotion.
7. **Round trip/replay.** Export -> hand-authored operator bundle -> import ->
   replay equality; no provider call and no execution.

## Assurance and close-out

- **Lanes:** Output/Provenance and Paper Claim governance.
- **Partial:** missing accepted 06i/06j interface; direct-read bypass cannot be
  closed; packet or sidecar authority is caller supplied; capability graph
  cannot resolve a changed handler.

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/unit/test_brief_export.py tests/research_system/unit/test_brief_import.py tests/research_system/unit/test_methods_capability_boundary.py tests/research_system/integration/test_brief_round_trip.py tests/research_system/integration/test_methods_production_consumers.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync python -m pytest -q tests/research_system/smoke/test_append_path_smoke.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system
~~~

Run the full `tests/research_system` tree once at final head because `cli.py`
and shared authority ports are consumed. Update `implementation/README.md` and
Pipeline-Overview with exact 06i/06j subjects, handler graph, and consumer
call-site matrix.
