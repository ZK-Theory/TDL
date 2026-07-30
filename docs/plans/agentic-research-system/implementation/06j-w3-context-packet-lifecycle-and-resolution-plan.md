# 06j: W3 Context Packet Lifecycle and Resolution Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> schema-contract-design, research-assurance-triage, and
> executing-plans-extras. Read accepted W3 sections 9-12, 14-16 and 19, W2
> command/event rules, and RR-M4 before starting.

**Status:** PROPOSED 2026-07-30. The exact-subject runtime has
`ContextCandidate`, `compile_candidate`, `SourceResolver`, and token gates, but
no authoritative packet object, lifecycle writer, delivery record, or
acceptance resolver. Dispatch is blocked on accepted 06h schema identity, fresh
G-RM-3 review, and G-RM-12 approval of the exact W2 extension below.

**Goal:** implement an immutable W3 packet/manifest producer and an
authoritative resolver over command-written, replay-derived lifecycle state so
RM-03 can bind a real issued-and-delivered packet rather than a local manifest.

## G-RM-12 exact decision subject

W3 says packet lifecycle events are W2 extensions but grants no implementation
authority. Stephen must approve the exact command/event family, schemas,
transition table, and authority scopes before implementation:

~~~text
RegisterContextPacket   -> ContextPacketRegistered   (compiled)
ValidateContextPacket   -> ContextPacketValidated
IssueContextPacket      -> ContextPacketIssued
RecordContextDelivery   -> ContextPacketDelivered
FailContextPacket       -> ContextPacketFailed
ExpireContextPacket     -> ContextPacketExpired
SupersedeContextPacket  -> ContextPacketSuperseded
~~~

All IDs use the accepted `ctx_` UUIDv7 kind. Addenda are new immutable `ctx_`
objects binding a base ID/revision/hash; they use the same lifecycle and never
patch a failed base.

## File map

**Create or materialize under the accepted catalogue process:**

~~~text
.research-system/schemas/core/commands/<seven context command schemas>
.research-system/schemas/core/events/<seven context event schemas>
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

No `ars://methods/event/**` family is created. Core schema materialization is
allowed only inside this plan under G-RM-12, not by RM-03.

## Packet authority contract

`ContextPacketManifest` contains every accepted W3 section 9.2 field:
context/request/parent IDs, revision, schema/compiler/policy versions, exact
rendered hash, project/task/purpose/role/risk/actor/session, control-store
identity and source position/hash, both token gates, candidate-set digest,
included/omitted/conflict entries, freshness/security/independence evidence,
delivery refs, currency triggers, retention, and supersession lineage.

The compiler:

1. resolves mandatory direct sources through `SourceResolver`;
2. verifies exact revisions/hashes, authority class, sensitivity, conflicts,
   freshness, and required closure;
3. deterministically renders bytes and applies both token gates;
4. writes immutable packet/manifest objects;
5. submits `RegisterContextPacket` through `CommandService`.

The producer cannot issue its own candidate. Validation binds independent
source/current-snapshot evidence; issuance requires an exact authority grant;
delivery requires a recipient/session/adapter receipt whose content hash equals
the issued bytes.

`resolve_context_packet_for_consumer(context_id, revision, packet_sha256,
consumer_id, purpose, scope, evaluation_time)` rebuilds current state from the
verified ledger, reads the immutable objects by exact hash, revalidates currency
triggers and the direct-source snapshot, and returns only an issued, delivered,
current, non-conflicted, non-superseded packet whose delivery recipient, purpose
and scope match. Local manifest fields or caller assertions never select state.

## Transition and failure rules

- `registered -> validated -> issued -> delivered`;
- `registered|validated -> failed`;
- `issued|delivered -> expired|superseded`;
- no reverse transition; no in-place revision; changed bytes create a new
  revision/object;
- missing mandatory source, unsafe source, unresolved governing conflict,
  token-gate failure, unverifiable freshness, wrong delivery hash, or
  independence failure emits no issued/delivered state;
- discovering an incomplete issued base supersedes/fails it and requires a new
  complete packet; an addendum cannot repair it.

## Required controls

Positive and distinguishing negatives cover: mandatory-source absence;
wrong-but-valid source; stale/superseded/cross-packet subject; candidate-set
omission; unresolved conflict; unsafe/restricted source; direct-index authority;
token gate; wrong role/risk/purpose/scope; wrong packet revision/hash; delivery
recipient/session/adapter/hash mismatch; changed currency source position;
addendum against failed base; duplicate/reordered lineage; non-idempotent retry;
direct ledger append; missing reducer; genesis/incremental replay equality.

The exact-subject W3 fixtures F-025 through F-030 remain the semantic oracle.
Schema tests alone are not closure.

## Tasks

1. **Catalogue and schemas (G-RM-12).** Materialize the exact seven-command
   family and closed packet/manifest/receipt schemas from accepted W2/W3.
2. **Immutable producer.** Extend the current compiler; store exact rendered
   bytes and manifest; register through the command service.
3. **Lifecycle authority.** Implement validation, issuance, delivery, expiry,
   failure, supersession, idempotency and pure reducers.
4. **Resolver.** Implement the only public consumption interface with
   load/consumption revalidation.
5. **CLI.** Add bounded compile/register/validate/issue/deliver/supersede
   operations. Every write submits a command; no direct append/object mutation.
6. **Adversarial corpus.** Run all required controls through production
   producer/resolver call sites, including F-025-F-030.

## Validation and close-out

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/contracts/test_context_packet_materialization.py tests/research_system/integration/test_context_packet_lifecycle.py tests/research_system/integration/test_context_packet_resolution.py tests/research_system/integration/test_context_routing_fixtures.py tests/research_system/integration/test_context_routing_fixture_corpus.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system/context research_system/command research_system/projection
~~~

Run the full `tests/research_system` tree once at final head because core
command/replay/schema surfaces change. Record exact schema identities, catalogue
rows, transition coverage, producer/resolver call sites, F-025-F-030 outcomes,
and negative-control liveness. Independent exact-subject acceptance is required
before RM-03 may consume this capability.
