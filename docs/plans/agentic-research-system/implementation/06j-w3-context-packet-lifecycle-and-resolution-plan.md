# 06j: W3 Context Packet Lifecycle and Resolution Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> schema-contract-design, research-assurance-triage, and
> executing-plans-extras. Read accepted W3 sections 9-12, 14-16 and 19, W2
> command/event rules, RR-M4, and PR198-F2/F4 from the PR #198 pre-merge
> review before starting.

**Status:** REVISED 2026-07-30 (suite revision 4). The exact-subject runtime has
`ContextCandidate`, `compile_candidate`, `SourceResolver`, and token gates, but
no authoritative packet object, lifecycle writer, delivery record, or
acceptance resolver. Bounded candidate authoring is blocked on accepted 06h and
fresh G-RM-3 review. Runtime implementation is separately blocked on independent
review and G-RM-12 approval of the exact candidate bytes.

**Goal:** implement an immutable W3 packet/manifest producer and an
authoritative resolver over the complete W3
`requested -> compiling -> compiled -> validated -> issued -> delivered`
command-written lifecycle so RM-03 can bind a real issued-and-delivered packet
rather than a local manifest.

## G-RM-12 exact decision subject

W3 says packet lifecycle events are W2 extensions but grants no implementation
authority.

### Stage A: bounded candidate authoring

After accepted 06h and G-RM-3, a contract author may create only:

~~~text
.research-system/contracts/candidates/06j-w3-context-packet-v1/
  catalogue-addendum.yaml
  commands/<nine candidate command schemas>
  events/<nine candidate event schemas>
  objects/context-packet.schema.json
  objects/context-manifest.schema.json
  objects/context-delivery-receipt.schema.json
  transition-table.yaml
  authority-scopes.yaml
  identity-manifest.yaml
~~~

These paths are inert proposal bytes: Stage A may add contract-shape tests
under the same candidate directory but may not modify the accepted owner
catalogue, canonical schema roots, `research_system/**`, replay, CLI or runtime
registration. The identity manifest binds every leaf by Git blob and canonical
SHA-256 but does not accept itself. Independent exact-subject review checks W3
field/lifecycle completeness, W2 semantics, all nine mappings, authority scopes,
fixtures and identity before Stephen decides G-RM-12.

### Gate decision

Stephen must approve and pin the exact candidate blobs/hashes for the command/
event family, object schemas, transition table, authority scopes and catalogue
addendum before Stage B implementation:

~~~text
RequestContextPacket    -> ContextPacketRequested
BeginContextCompilation -> ContextCompilationStarted
CompleteContextCompilation -> ContextPacketCompiled
ValidateContextPacket   -> ContextPacketValidated
IssueContextPacket      -> ContextPacketIssued
RecordContextDelivery   -> ContextPacketDelivered
FailContextPacket       -> ContextPacketFailed
ExpireContextPacket     -> ContextPacketExpired
SupersedeContextPacket  -> ContextPacketSuperseded
~~~

Any post-review candidate-byte change invalidates G-RM-12 and returns to
Stage A. Plan prose is not an exact schema decision subject.

All IDs use the accepted `ctx_` UUIDv7 kind. Addenda are new immutable `ctx_`
objects binding a base ID/revision/hash; they use the same lifecycle and never
patch a failed base.

## File map

**Stage B creates or materializes byte-for-byte from the G-RM-12 candidate:**

~~~text
.research-system/contracts/context-packet-v1/catalogue-addendum.yaml
.research-system/contracts/context-packet-v1/transition-table.yaml
.research-system/contracts/context-packet-v1/authority-scopes.yaml
.research-system/contracts/context-packet-v1/identity-manifest.yaml
.research-system/schemas/core/commands/<nine context command schemas>
.research-system/schemas/core/events/<nine context event schemas>
.research-system/schemas/context/context-packet.schema.json
.research-system/schemas/context/context-manifest.schema.json
.research-system/schemas/context/context-delivery-receipt.schema.json
research_system/context/registry.py
research_system/context/service.py
tests/research_system/contracts/test_context_packet_materialization.py
tests/research_system/integration/test_context_packet_lifecycle.py
tests/research_system/integration/test_context_packet_resolution.py
~~~

**Modify:**

~~~text
accepted WP6.1 owner catalogue/materializer sources named by G-RM-12
research_system/context/models.py
research_system/context/compiler.py
research_system/context/sources.py
research_system/command/service.py
research_system/projection/replay.py
research_system/cli.py
~~~

No `ars://methods/event/**` family is created. Stage B materializes every
accepted candidate component into its mapped canonical destination without
semantic alteration. Every canonical loader requires the exact G-RM-12
identity-manifest blob/hash and verifies the catalogue addendum, transition
table, authority scopes, command/event schemas and object schemas against their
bound candidate SHA-256 values before registration or use. Core schema
materialization is allowed only inside this plan after G-RM-12, not by RM-03.

## Packet authority contract

`ContextPacketManifest` contains every accepted W3 section 9.2 field:
context/request/parent IDs, revision, schema/compiler/policy versions, exact
rendered hash, project/task/purpose/role/risk/actor/session, control-store
identity and source position/hash, both token gates, candidate-set digest,
included/omitted/conflict entries, freshness/security/independence evidence,
delivery refs, currency triggers, retention, and supersession lineage.

The compiler:

1. submits `RequestContextPacket` before source resolution and receives the
   stable request/context identity;
2. submits `BeginContextCompilation` before reading candidate sources;
3. resolves mandatory direct sources through `SourceResolver`, verifies exact
   revisions/hashes, authority class, sensitivity, conflicts, freshness and
   required closure, renders deterministically, and applies the reference-token
   gate;
4. writes immutable packet/manifest objects and submits
   `CompleteContextCompilation`;
5. exposes the compiled, unissued candidate to W4/W7 only for evaluated routing
   and bound-provider counting, then submits `ValidateContextPacket` only after
   the provider-capacity, manifest, security and independence checks pass; and
6. submits `FailContextPacket` from requested, compiling or compiled on any
   source, conflict, security, token, rendering, provider-capacity, manifest or
   independence failure.

The producer cannot issue its own candidate. Validation binds independent
source/current-snapshot evidence; issuance requires an exact authority grant;
delivery requires a recipient/session/adapter receipt whose content hash equals
the issued bytes.

`resolve_context_packet_for_consumer(context_id, revision, packet_sha256,
consumer_id, purpose, scope, evaluation_time)` rebuilds current state from the
verified ledger, reads the immutable objects by exact hash, revalidates currency
triggers and the direct-source snapshot, and returns only an issued, delivered,
current, non-conflicted, non-superseded packet whose request, compilation,
validation, delivery recipient, purpose and scope match. Local manifest fields
or caller assertions never select state.

## Transition and failure rules

- `requested -> compiling -> compiled -> validated -> issued -> delivered`;
- `requested|compiling|compiled -> failed`;
- `issued|delivered -> expired|superseded`;
- no reverse transition; no in-place revision; changed bytes create a new
  revision/object;
- missing mandatory source, unsafe source, unresolved governing conflict,
  token-gate failure, unverifiable freshness, rendering failure, insufficient
  provider capacity, packet/manifest mismatch, wrong delivery hash, or
  independence failure emits an attributable failed state and no
  issued/delivered state;
- discovering an incomplete issued base supersedes/fails it and requires a new
  complete packet; an addendum cannot repair it.

## Required controls

Positive and distinguishing negatives cover: mandatory-source absence;
wrong-but-valid source; stale/superseded/cross-packet subject; candidate-set
omission; unresolved conflict; unsafe/restricted source; direct-index authority;
token gate; wrong role/risk/purpose/scope; wrong packet revision/hash; delivery
recipient/session/adapter/hash mismatch; changed currency source position;
addendum against failed base; duplicate/reordered lineage; non-idempotent retry;
direct ledger append; missing reducer; genesis/incremental replay equality;
failure before source resolution; failure during compiling; provider-capacity
failure after compiled; packet/manifest mismatch after compiled; an attributable
`ContextPacketFailed` replay record for each validation-precondition rejection;
retry of every failed phase; and the distinguishing absence of a request for a
never-requested packet.

The exact-subject W3 fixtures F-025 through F-030 remain the semantic oracle.
Schema tests alone are not closure.

## Stage B tasks

1. **Catalogue and schemas.** Materialize the catalogue addendum, transition
   table, authority scopes, identity manifest, exact nine-command/event family
   and closed packet/manifest/receipt schemas into their canonical file-map
   paths byte-for-byte. At load, require the exact accepted manifest blob/hash
   and verify every mapped component against its bound candidate SHA-256; reject
   missing components, manifest substitution and candidate/canonical divergence.
2. **Immutable producer.** Extend the current compiler; command-write requested
   and compiling before fallible work, store exact rendered bytes/manifest, and
   command-write compiled or failed.
3. **Lifecycle authority.** Implement validation, issuance, delivery, expiry,
   failure from every W3-permitted phase, supersession, idempotency and pure
   reducers.
4. **Resolver.** Implement the only public consumption interface with
   load/consumption revalidation.
5. **CLI.** Add bounded
   request/begin-compilation/complete-compilation/validate/issue/deliver/fail/
   expire/supersede operations. A high-level compile operation may orchestrate
   the first three but cannot omit their receipts. Every lifecycle write
   submits its named command; no direct append/object mutation.
6. **Adversarial corpus.** Prove CLI reachability for all nine lifecycle
   commands, including pre-registration `fail`, successful `expire`,
   invalid-state rejection, idempotent retry, and genesis/incremental replay.
   Run all required controls through production
   producer/resolver call sites, including F-025-F-030.

## Validation and close-out

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/contracts/test_context_packet_materialization.py tests/research_system/integration/test_context_packet_lifecycle.py tests/research_system/integration/test_context_packet_resolution.py tests/research_system/integration/test_context_routing_fixtures.py tests/research_system/integration/test_context_routing_fixture_corpus.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system/context research_system/command research_system/projection
~~~

Run the full `tests/research_system` tree once at final head because core
command/replay/schema surfaces change. Record exact schema identities, catalogue
rows, CLI reachability and transition coverage for all nine commands,
producer/resolver call sites, F-025-F-030 outcomes, and negative-control
liveness. If RM-01's append-path smoke gate already exists on current `main`,
add all nine families and run the registry-to-smoke-manifest completeness check
before 06j merge. Otherwise publish their exact smoke cases as blocking input
to RM-01's final candidate reconciliation. The plan that merges second owns the
final complete gate. Independent exact-subject acceptance is required before
RM-03 may consume this capability.
