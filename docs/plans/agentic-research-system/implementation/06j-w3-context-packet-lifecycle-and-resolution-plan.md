# 06j: W3 Context Packet Lifecycle and Resolution Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> schema-contract-design, research-assurance-triage, and
> executing-plans-extras. Read accepted W3 sections 9-12, 14-16 and 19, W2
> command/event rules, RR-M4, PR198-F2/F4 from the PR #198 pre-merge review,
> PR198-RR1 from the independent `8e091a1` rereview, PR198-RR1-A through
> PR198-GRM12 from the independent `d6c9647` rereview, and the transitive
> PR198-RR1-A follow-up from the independent `85f33e6` rereview.

**Status:** REVISED 2026-07-31 (suite revision 6; transitive evaluation caller
inventory amendment). The exact-subject runtime has `ContextCandidate`,
`compile_candidate`, `SourceResolver`, and token gates, but no authoritative
packet object, lifecycle writer, delivery record, or acceptance resolver. Stage
A is non-dispatchable until accepted 06h, an independent exact-subject `accept`,
Stephen's separate explicit G-RM-3 decision, and an accepted decision-register
amendment authorizing the Stage A scope and gate identities. Runtime
implementation is separately blocked on independent review and G-RM-12 approval
of the exact candidate bytes.

**Goal:** implement an immutable W3 packet/manifest producer and an
authoritative resolver over the complete W3
`requested -> compiling -> compiled -> validated -> issued -> delivered`
command-written lifecycle so RM-03 can bind a real issued-and-delivered packet
rather than a local manifest.

## G-RM-12 exact decision subject

W3 says packet lifecycle events are W2 extensions but grants no implementation
authority.

### Stage A: bounded candidate authoring

Only after every Stage A authority prerequisite in the status paragraph is
satisfied may a contract author create:

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
registration. The identity manifest binds every *other* candidate leaf by Git
blob and canonical SHA-256. It deliberately does not hash or accept itself; the
independent review and later owner decision record supply the manifest's own Git
blob and raw SHA-256 externally. Independent exact-subject review checks W3
field/lifecycle completeness, W2 semantics, all nine mappings, authority scopes,
executable F-025-F-028 evidence, reserved F-029/F-030 mappings and identity
before Stephen decides G-RM-12.

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
tests/research_system/integration/test_context_packet_w4_w7_lifecycle.py
tests/research_system/integration/test_context_packet_eval_transitive_boundary.py
tests/research_system/unit/test_context_packet_w4_w7_boundary.py
~~~

**Modify:**

~~~text
accepted WP6.1 owner catalogue/materializer sources named by G-RM-12
.research-system/evals/p0-variant-matrix.yaml
research_system/context/models.py
research_system/context/compiler.py
research_system/context/sources.py
research_system/routing/orchestrator.py
research_system/routing/engine.py
research_system/operations/coordinator.py
research_system/adapters/provider.py
research_system/evals/scenarios.py
research_system/evals/calibration.py
research_system/evals/harness.py
research_system/evals/executors/__init__.py
research_system/evals/executors/context_routing.py
research_system/evals/executors/release_tranche.py
research_system/evals/executors/adapter_scientific.py
research_system/evals/variants.py
research_system/command/service.py
research_system/projection/replay.py
research_system/cli.py
tests/research_system/integration/test_context_routing_fixtures.py
tests/research_system/integration/test_context_routing_fixture_corpus.py
tests/research_system/integration/test_adapter_operations_fixtures.py
tests/research_system/integration/test_eval_cli.py
tests/research_system/integration/test_gate5_variant_execution.py
tests/research_system/unit/test_calibration.py
tests/research_system/unit/test_executors.py
tests/research_system/unit/test_routing_engine.py
tests/research_system/unit/test_routing_orchestrator.py
~~~

No `ars://methods/event/**` family is created. Stage B materializes every
accepted candidate component into its mapped canonical destination without
semantic alteration. Every canonical loader requires the exact G-RM-12
identity-manifest blob/hash and verifies the catalogue addendum, transition
table, authority scopes, command/event schemas and object schemas against their
bound candidate SHA-256 values before registration or use. Core schema
materialization is allowed only inside this plan after G-RM-12, not by RM-03.

A compiled packet may enter W4/W7 only through the context lifecycle service.
The service alone mints an opaque `ContextLifecycleCapability` bound to request,
context ID/revision/hash, attempt, writer and lifecycle version. The capability
constructor requires a module-private mint key; every routing, provider-capacity,
selected-route revalidation, command-template, accounting and provider-issue
signature requires the capability as a non-optional argument and verifies its
identity and binding digest. `LifecycleBoundDispatch` replaces freely
constructible `PreparedDispatch` at the production boundary. Missing, copied or
forged capabilities and directly constructed dispatches are rejected before any
route, grant, lease or provider side effect.

The exact-subject first-party inventory is normative; Stage B may not defer it.
The registry and CLI-root classifications below are closed. The structural test
derives the required root set from the `eval` parser bindings and first-party
reachability into coverage or rederivation, so a newly bound handler, fixture ID
or matrix row has no default class and fails until this table and its structural
test are updated.

| Symbol/seam | Current `research_system/**` callers, wrappers or entries | Required Stage B disposition |
|---|---|---|
| `context.compiler.validate_provider_gate` | no shipped caller; direct compiled-candidate capacity function | move behind the capability-bearing lifecycle prevalidation step; the public unguarded signature disappears |
| `routing.engine.select_route` | `routing.orchestrator.plan_dispatch`; direct calls in `evals/scenarios.py`, `evals/executors/context_routing.py`, and `evals/executors/release_tranche.py` | capability-bearing internal routing kernel only; migrate every listed caller through the lifecycle service and convert failure dictionaries to one lifecycle failure write |
| `routing.engine.PreparedDispatch` | constructed by `routing.orchestrator.plan_dispatch`, `evals/scenarios.py`, and `evals/executors/release_tranche.py`; consumed by `operations/coordinator.py` | replace production construction with sealed `LifecycleBoundDispatch`; no public constructor or duck-typed substitute is accepted |
| `operations.coordinator.issue_prepared_dispatch` and its `AdapterIssuePort.revalidate/build_command` calls | direct callers in `evals/scenarios.py` and `evals/executors/release_tranche.py` | split into pre-issue template validation and post-W8 issue; both require the same capability and immutable template digest |
| `adapters.provider.validate_wrapper_accounting` and operation-policy enforcement | `ProviderAdapter.issue`; `normalize_receipt`; provider wrappers in `evals/scenarios.py`, `evals/executors/release_tranche.py`, and generic `evals/variants.py::_execute_through_fake_provider` | validate the exact template before context issue; remove the generic arbitrary-fixture direct-issue path; later checks accept only the sealed unchanged template |
| `evals.calibration.calibrate_fixture -> require_executor` | direct `eval calibrate` root plus `evals.harness.run_p0_coverage`; executes known-good, known-bad and every mutation repeatedly through the registered executor | consume a typed registered executor whose execution class is closed below; lifecycle-required entries cannot expose or invoke a raw executor without the lifecycle service/capability |
| `evals.harness.run_p0_coverage` | called by CLI `_eval_run`, `_rederive_bound_decision`, and `_publication_evidence`; calls `calibrate_fixture` and `execute_gate5_variant_rows_twice` | pass the lifecycle service through both transitive branches; missing/forged capability fails the protected fixture path before route/grant/lease/provider effects and writes the one attributable failure event |
| `evals.variants.execute_gate5_variant_rows_twice -> require_executor -> _execute_through_fake_provider -> ProviderAdapter.issue` | every row in `.research-system/evals/p0-variant-matrix.yaml`; current generic wrapper builds operation, policy, context/rendered hashes and wrapper accounting locally | delete the arbitrary-fixture provider wrapper. Use a lifecycle variant runner for lifecycle-required IDs, a dedicated exact-ID adapter-scientific runner, and a pure no-provider runner for all remaining IDs; no caller-built W3/W4/W7 command field survives |
| `evals.executors.CONTEXT_ROUTING_EXECUTORS` | exact IDs `F-021`, `F-022`, `F-025`, `F-026`, `F-027`, `F-028`, `F-031`, `F-033`, `F-035`; F-031/F-033 call routing directly and F-025-F-028 are the executable W3 P0 oracle | classify the map as lifecycle-required for provider variants; F-025-F-028 and F-031/F-033 execute through the full lifecycle boundary, while the other pure observations cannot be wrapped in direct provider issue |
| `evals.executors.RELEASE_TRANCHE_EXECUTORS` | exact IDs `S-014`, `S-015`, `S-016`; S-016 constructs `PreparedDispatch`, invokes the coordinator, builds the provider command and issues | classify S-016 as lifecycle-required; S-014/S-015 remain pure release observations and cannot be wrapped in generic provider issue |
| `evals.executors.ADAPTER_SCIENTIFIC_EXECUTORS` | exact IDs `F-007`, `F-008`, `F-009`, `F-010`, `F-011`, `F-012`, `F-013`, `F-014`, `F-020`, `F-032`, `F-034`, `F-036`, `S-003`, `S-004`, `S-013` | only these exact IDs may use the dedicated adapter-scientific runner, and only when its signature rejects context packet, lifecycle dispatch and capability inputs; this exemption never applies to `variants.py` generically |
| `evals.executors.CONTROL_STORE_EXECUTORS` | exact IDs `F-001`, `F-002`, `F-003`, `F-004`, `F-005`, `S-001`, `S-002`, `S-006`, `S-008`, `S-009`, `S-010`, `S-011`, `S-012` | keep as pure observations; their matrix rows cannot construct or issue a provider command |
| CLI and rederivation roots | `eval validate -> _eval_validate -> load_p0_coverage`; `eval calibrate -> _eval_calibrate`; `eval run -> _eval_run`; `eval publish-release -> _eval_publish_release -> _publication_evidence`; unused `_rederive_bound_decision`; `eval release -> _eval_release -> rederive_release_from_snapshot` | classify `eval validate` as pure package/coverage validation and prove it never loads an executor, constructs lifecycle dispatch, routes, coordinates or issues a provider command; guard every live-execution root through the typed registry/lifecycle path or remove the unused root; keep `eval release`/snapshot rederivation reconstruction-only with the same executor/provider-free negative |
| transitive registration | `evals/executors/__init__.py::EXECUTORS/require_executor`, `evals/harness.py`, `evals/calibration.py`, `evals/variants.py`, and CLI handlers above | registration indirection is not an exemption; the execution class and permitted runner are checked at lookup and again at the runner boundary |

A repository-wide AST/import/registry test derives the required CLI-root set
from the `eval` parser bindings and first-party reachability into coverage or
rederivation, fails when any such root lacks a literal class, and rejects new or
unclassified entries, imports of the private mint key, direct dispatch
construction, a returned route-failure dictionary as a terminal result, and any
arbitrary-fixture construction of `ProviderCommand`. Runtime negatives enter
through each protected CLI/rederivation root and through `run_p0_coverage`,
`calibrate_fixture`, and the variant runner; for each lifecycle-required ID they
attempt missing and forged capabilities and assert rejection before route/grant/
lease/provider side effects, exactly one accepted `ContextPacketFailed` event/
batch, and the original receipt on retry. A distinguishing parser-dispatched
`eval validate -> _eval_validate -> load_p0_coverage` negative proves that the
pure validation root never resolves an executor, constructs lifecycle dispatch,
routes, coordinates or issues a provider command. A source-file allowlist or
direct-call-only probe is not closure.

## Packet authority contract

`ContextPacketManifest` contains every accepted W3 section 9.2 field:
context/request/parent IDs, revision, schema/compiler/policy versions, exact
rendered hash, project/task/purpose/role/risk/actor/session, control-store
identity and source position/hash, both token gates, candidate-set digest,
included/omitted/conflict entries, freshness/security/independence evidence,
delivery refs, currency triggers, retention, and supersession lineage.

`ValidateContextPacket` binds the immutable W4 `RouteDecision` and verifier-
route witness plus the exact W7 selected-route revalidation evidence: provider/
adapter/capability/parity identities, rendered hash, exact or accepted upper-
bound count, wrapper/system reserve, both token gates, policy and currentness.
It also binds a frozen `PrevalidatedProviderCommandTemplate` containing the exact
operation, provider/model/profile, adapter revision, context/rendered hashes,
command revision/idempotency key, timeout, policy/parity/currentness identities,
provider-count evidence, complete canonical wrapper-accounting bytes and their
SHA-256, plus the lifecycle-capability digest. The template is immutable and is
part of the issue command's exact evidence.

W8 may later add only its separately owned grant and lease IDs, receipts and
hashes in a sealed envelope. The final `ProviderCommand` embeds the exact
prevalidated template bytes unchanged; no adapter or caller may rebuild or
supply any W3/W4/W7 field. `ProviderAdapter.issue` retains fail-closed seal,
policy and accounting enforcement, but consumes the bound immutable policy
snapshot and template rather than performing a new current-policy lookup or
accepting mutable accounting. A mismatched template/envelope cannot be formed by
the public constructors and is rejected before provider transport.

The authority-grant ordering is explicit and one-directional: the W8 grant/
lease envelope is never verified or bound before `IssueContextPacket` freezes
the `PrevalidatedProviderCommandTemplate`, and it never becomes part of the
context-packet lifecycle state machine. It is instead verified and bound
strictly after packet issuance, at `ProviderAdapter.issue` time, as a
separate sealed envelope alongside the unchanged frozen template.
`ProviderAdapter.issue` rejects, before provider transport: a missing grant or
lease, a grant/lease that does not match the frozen template's context,
rendered-hash, operation or provider/model/profile identities, and a grant or
lease presented after its own validity/expiry window (a late grant). These
are required negative cases alongside the other adversarial controls.

`FailContextPacket` always binds request ID, context ID, lifecycle phase,
failure code and a deterministic failure command/idempotency key. Its packet
evidence is phase-qualified: `requested` and `compiling` require
`packet_evidence_status=absent_before_immutable_bytes` with `packet_revision`
and `packet_sha256` explicitly null; `compiled` requires
`packet_evidence_status=present` with the exact non-null revision/hash. Route
request/decision and W7 identities are required only once those phases exist;
the closed schema rejects placeholders, contradictory nulls and phase/evidence
mismatches.

The context lifecycle service:

1. submits `RequestContextPacket` before source resolution and receives the
   stable request/context identity;
2. submits `BeginContextCompilation` before reading candidate sources;
3. resolves mandatory direct sources through `SourceResolver`, verifies exact
   revisions/hashes, authority class, sensitivity, conflicts, freshness and
   required closure, renders deterministically, and applies the reference-token
   gate;
4. writes immutable packet/manifest objects and submits
   `CompleteContextCompilation`;
5. mints the capability, passes the compiled packet through the guarded W4
   boundary, records the decision/witness, and converts candidate-capacity,
   no-eligible-route, packet/manifest, security or independence rejection into
   the deterministic `FailContextPacket` while still `compiled`;
6. uses the same capability to revalidate the selected route and build the exact
   immutable provider-command template, including provider count, rendered hash,
   complete wrapper accounting, operation, policy, parity and currentness. Every
   rejection or exception becomes the deterministic compiled-phase failure;
7. under the lifecycle writer lock, binds the capability/template digests,
   pre-resolves expected version and issue idempotency, then submits
   `ValidateContextPacket` and `IssueContextPacket` without releasing the lock or
   performing another external or fallible W3/W4/W7 check. A crash after
   validation retries the exact issue command and returns its original receipt;
   and
8. hands only the issued packet, sealed capability and unchanged prevalidated
   template downstream. W8 adds the sealed grant/lease envelope; provider issue
   accepts no caller-supplied W3/W4/W7 field. Existing direct W4 failure returns,
   W7 raises and late command construction are removed as public lifecycle
   outcomes.

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
- `ValidateContextPacket` is legal only after the recorded W4 decision/witness,
  successful selected-route W7 evidence, capability digest and immutable
  provider-command template are bound;
- no fallible W3/W4/W7 validation or command-template construction is legal
  after `validated`; the same locked boundary issues the packet, and crash
  recovery retries that exact issue and returns the original receipt;
- no reverse transition; no in-place revision; changed bytes create a new
  revision/object;
- missing mandatory source, unsafe source, unresolved governing conflict,
  token-gate failure, unverifiable freshness, rendering failure, insufficient
  provider capacity, no eligible route, accounting unavailable, wrapper
  accounting missing/invalid/overflow, packet/manifest mismatch, rendered-hash
  drift, operation/policy/parity/currentness drift or independence failure uses
  one stable failure-command identity, accepts exactly one
  `ContextPacketFailed` event in one batch, and creates no validated/issued/
  delivered state;
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
failure before source resolution; failure during compiling; W4 candidate-
capacity rejection; no eligible route; accounting unavailable; wrapper
accounting missing, invalid or overflowing; packet/manifest mismatch; rendered-
hash drift; operation/policy/parity/currentness drift; late template mutation;
missing or forged lifecycle capability; and missing, mismatched, or late W8
grant/lease binding at provider issue.

For every production-seam rejection, tests derive the deterministic failure
command/idempotency key, submit it twice, and assert exactly one accepted
`ContextPacketFailed` event in one batch, the original receipt on retry, the
phase-correct present/absent packet evidence, no validated/issued/delivered
state, and equal genesis/incremental replay. The never-requested control still
asserts the distinguishing absence of any request or failure record.

F-025 through F-028 are the materialized executable P0 oracle for Stage B.
F-029 and F-030 remain accepted P1 design reservations under 06a: Stage B records
canonical reservation-to-control mappings but does not claim to execute or pass
them. Their fixture packages, materializers, coverage rows and tests are owned by
the pre-pilot P1 follow-up. Schema or reservation presence is not executable
closure.

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
3. **W4/W7 lifecycle boundary.** Make the context lifecycle service the only
   compiled-packet orchestrator. Mint and verify the sealed capability; bind the
   W4 decision/witness, W7 evidence and exact prevalidated provider-command
   template; translate every rejection into the phase-qualified deterministic
   failure; and perform validate/issue under one writer lock.
4. **Call-graph firewall.** Implement every row and exact registry classification
   in the normative caller table. Derive the required root set from the `eval`
   parser bindings and first-party reachability; classify `eval validate` as
   executor/provider-free. Split the generic variant provider wrapper, type
   `require_executor` results, and guard calibration, coverage, variant, CLI and
   rederivation roots. Reject missing/forged capability, unclassified entries,
   direct dispatch construction, arbitrary-fixture provider commands, escaped
   failures and late W3/W4/W7 fields. The negatives traverse the full transitive
   paths and prove protected-root rejection before side effects plus pure-root
   absence of executor/lifecycle/provider effects, not merely absence from an
   allowlisted source file.
5. **Lifecycle authority.** Implement validation, issuance, delivery, expiry,
   failure from every W3-permitted phase, supersession, idempotency and pure
   reducers.
6. **Resolver.** Implement the only public consumption interface with
   load/consumption revalidation.
7. **CLI.** Add bounded
   request/begin-compilation/complete-compilation/validate/issue/deliver/fail/
   expire/supersede operations. A high-level compile operation may orchestrate
   the first three but cannot omit their receipts. Every lifecycle write
   submits its named command; no direct append/object mutation.
8. **Adversarial corpus.** Prove CLI reachability for all nine lifecycle
   commands and run every W4/W7 negative through the production routing/
   coordinator/adapter seams, including executable F-025-F-028. Exercise the
   full CLI/rederivation -> coverage -> calibration/variant -> registry ->
   routing/coordinator/provider chain for every protected registry class.
   Dispatch `eval validate` through the real parser and prove that its pure
   validation path remains executor/lifecycle/provider-free. Prove sealed-
   template immutability, missing/forged-capability rejection before side
   effects, phase-qualified failure, exactly one event/batch, original-receipt
   retry, replay equality and registry/root-classification liveness. Record
   F-029/F-030 as reserved P1 mappings only.

## Validation and close-out

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/contracts/test_context_packet_materialization.py tests/research_system/integration/test_context_packet_lifecycle.py tests/research_system/integration/test_context_packet_resolution.py tests/research_system/integration/test_context_packet_w4_w7_lifecycle.py tests/research_system/integration/test_context_packet_eval_transitive_boundary.py tests/research_system/integration/test_eval_cli.py tests/research_system/integration/test_gate5_variant_execution.py tests/research_system/unit/test_calibration.py tests/research_system/unit/test_executors.py tests/research_system/unit/test_context_packet_w4_w7_boundary.py tests/research_system/integration/test_context_routing_fixtures.py tests/research_system/integration/test_context_routing_fixture_corpus.py tests/research_system/integration/test_adapter_operations_fixtures.py tests/research_system/unit/test_routing_engine.py tests/research_system/unit/test_routing_orchestrator.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system/context research_system/command research_system/projection research_system/routing research_system/operations research_system/adapters research_system/evals research_system/cli.py
~~~

Run the full `tests/research_system` tree once at final head because core
command/replay/schema surfaces change. Record exact schema identities, catalogue
rows, CLI reachability and transition coverage for all nine commands, the
complete literal caller-table, parser-derived CLI-root set and registry/root-
class disposition, capability and sealed-template bindings, full transitive
CLI/calibration/variant negatives, the executor/provider-free `eval validate`
negative, exactly-once failure/retry/replay outcomes, producer/resolver call sites,
executable F-025-F-028 outcomes, explicit P1
F-029/F-030 deferral mappings, and negative-control liveness. If RM-01's
append-path smoke gate already exists on current `main`,
add all nine families and run the registry-to-smoke-manifest completeness check
before 06j merge. Otherwise publish their exact smoke cases as blocking input
to RM-01's final candidate reconciliation. The plan that merges second owns the
final complete gate. Independent exact-subject acceptance is required before
RM-03 may consume this capability.
