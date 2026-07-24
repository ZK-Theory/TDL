# WP6.2 T3/T4 Live-Issue Binding Contract Brief

**Created:** 2026-07-23
**Status:** authorized for contract/addendum authorship and fresh independent
review only; no provider call or runtime remediation is authorized
**Workflow system:** standalone TDL supervision; never APM
**Vertical outcome:** define the missing canonical claim, live-issue, provider
evidence, and receipt-reconciliation contract shared by T3 Claude and T4 Codex

## 1. Controlling state

The immutable dispatch base is PR #161 merge commit
`2291b5d4736ad604ce9763d9c677e707970ef14e`. Its final runtime-T2 head is
`4375e0a63bd9bc6875822ea27a337360bd08a290`.

Applicable accepted authorities remain:

- P-037 through P-041 in
  `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`,
  with each later decision controlling its explicit amendments;
- W7 in
  `docs/plans/agentic-research-system/design/07-runtime-adapters-and-policy-parity.md`
  and the T2-T4 requirements, DAG, negative matrix, and stops in
  `docs/plans/agentic-research-system/implementation/06b-wp6-2-live-capability-plan.md`;
- T1a subject `599050b0809ed63a69e1a9ce6ac491b61f7ad33e`, protocol blob
  `4c9721a047c9b66912b9786a3b983c6f84e5ab00`, canonical SHA-256
  `e9512bef147d0de9bc9103b20eb1ede8b927979bfe43dd85e61fb6c27f05efda`;
- P-040 contract candidate `391a92753d7f746fa91a6b5455c9ce0fd01baa52`;
- P-041 six-path successor `2048f6470a9542db967186cc260d235c3373de2e`;
- the owner-accepted one-path successor for
  `tests/research_system/contracts/test_wp6_2_t2_authority_contract.py`, Git
  blob `0e9429aef35a61e4621412f6c4ce17fbc5088d8d`, raw-byte SHA-256
  `4d35340efe26779723963088ab4797219c8c02365c623dfc7f785c44b12a94a9`;
- the exact runtime-T2 implementation merged through PR #161.

The uncommitted Claude and Codex prototypes on
`codex/wp6-2-t3-t4-parallel` are rejected exploratory evidence only. Their
focused tests passed, but independent reviews returned `blocked_authority`
because caller-constructed objects could stand in for canonical T2 acceptance,
policy derivation, native selection, and provider evidence. Do not commit,
copy, or treat those bytes as a contract candidate.

## 2. Required operating context

Use a fresh standalone contract-authoring task. Invoke `research-observer`
first and use `tda-large-workflow-supervision` as the coordination procedure.
Use only the contract/schema and test skills actually needed. The author and
fresh reviewer must receive no prototype conversation history; the reviewer
gets only the exact candidate, this brief, the accepted authorities, and the
two durable blocked-review reports produced from the dispatch handback.

Stephen alone triggers and monitors CodeRabbit. Do not invoke numbered APM
skills or update APM state.

Before writing, verify cwd, symbolic branch, exact dispatch base, status, and
the effective P-040/P-041/one-path-successor/T1a identities directly from Git
objects. Record the exact immutable contract-authoring branch point.

## 3. Research and system failure being closed

The research asset is the auditable identity and cost provenance of a live
model contribution. Without this contract, a caller can fabricate mutually
consistent command, reservation, policy, and receipt mappings; the process may
use an ambient credential or different native model/profile; a crash may cause
an unrecorded or repeated invocation; and a schema-valid receipt may claim
delivery, accounting, or completion that the provider did not prove.

The cheapest adequate control is one shared canonical boundary, not duplicated
Claude/Codex trust logic or general security hardening. Provider-specific
rendering and evidence remain separate after that boundary.

## 4. Required contract closure

The candidate must freeze every identity, schema version, writer, stream,
expected version, reducer, projection, authority scope, idempotency key,
receipt proof, rejection, and positive/negative test needed for the following
state machine.

### 4.1 Canonical pre-call claim

Define a new T3/T4 transition, separate from the closed T2 family:

```text
ClaimLiveProviderInvocation -> [LiveProviderInvocationClaimed]
```

The sole canonical writer remains
`research_system.command.service.CommandService`. The claim uses a new
provider-invocation stream so it does not change the accepted T2 provider-command
or cost-grant stream versions.

The claim must bind:

- the newly accepted, non-duplicate `AuthorizeProviderIssue` Receipt 2.0
  identity and raw hash;
- its exact ledger transaction, ordered `CostGrantReserved` and
  `ProviderCommandIssued` event IDs/hashes, and resulting stream versions;
- exact ProviderCommand, CostGrant, reservation, SecretReference, Task,
  Dispatch, Attempt, ResourceGrant, route/profile, context, policy, and adapter
  triples;
- the proposed `LiveIssueBinding` triple;
- provider family and normalized operation;
- a deterministic invocation identity and full W2 idempotency tuple;
- the domain-separated `claim_intent_hash` defined below; and
- the resolver-owned `CredentialUseReceipt` triple/hash.

`claim_intent_hash` is:

```text
SHA-256(
  UTF-8("ars:wp6-2:live-claim-intent:v1\0")
  || canonical_json(claim_intent_preimage)
)
```

The strict `claim_intent_preimage` contains exactly:

- claim schema identity/version, command type
  `ClaimLiveProviderInvocation`, command ID, actor, authority scope,
  idempotency key, correlation and causation identities;
- target invocation stream ID/expected version, complete ordered write set and
  expected stream versions, expected global position, and expected ledger tail
  hash;
- deterministic invocation identity;
- accepted T2 Receipt 2.0, ledger transaction, reservation event, and
  provider-command event identities/hashes/versions;
- every ProviderCommand, CostGrant, reservation, SecretReference, Task,
  Dispatch, Attempt, ResourceGrant, route/profile, context, policy, adapter,
  and `LiveIssueBinding` triple;
- credential-resolver trust-root identity/version/hash and required resolver
  identity/version, credential class/scope, and isolated auth-context
  requirements;
- provider family, normalized operation, preflight output hashes, and every
  expected stream/object version revalidated under the writer lock.

It explicitly excludes the `CredentialUseReceipt` identity/hash, the complete
claim payload hash, and submission/recording timestamps. The intent schema is
strict with `additionalProperties: false`; adding any other pre-receipt field
requires a new intent schema/version and cannot silently exclude that field
from hashing. The completed claim then includes both
`claim_intent_hash` and the `CredentialUseReceipt` triple/hash and receives the
normal W2 canonical full-payload hash. `CommandService` reconstructs the intent
from the enumerated fields and validates both hashes; it never derives the
intent by deleting arbitrary keys from a caller mapping.

Only a new accepted T2 issue may claim. Rejected, conflict, duplicate, replay,
stale, partial, reordered, mismatched, expired, revoked, or already claimed
inputs produce zero claim events and zero provider invocations. Concurrent
claim attempts have exactly one winner and are never automatically retried.

All independent object resolution, policy compilation, native-profile/argv
construction, payload rendering, expiry/revocation checks, credential-use
proof validation, and secret scans occur before the claim and without mutating
the project ledger or canonical object store. Every failure at those seams
therefore leaves canonical project bytes unchanged.

The claim is the last canonical step before invocation. Its command carries the
exact preflight output hashes and expected versions. Under the writer lock,
`CommandService` independently re-resolves or revalidates those hashes,
versions, expiry/revocation states, and the accepted T2 batch before appending
the claim. Drift or failed revalidation produces zero events and zero
invocations.

### 4.2 `LiveIssueBinding` 1.0

Define a strict content-addressed `LiveIssueBinding` with a new first-class
identity. It must bind independently resolved canonical records for:

- policy bundle, applicability manifest, compiler/generator identity and
  revision, compiled projection hash, and exact control membership;
- context packet/addenda, rendered managed-content hash, and both W3 token
  gates;
- provider, native model/version selector, evaluated W4 route/profile and
  reasoning setting;
- adapter revision and an exact provider-specific argv profile: executable,
  ordered flags, model/profile/reasoning selection, sandbox, cwd/root, network,
  tools, permissions, environment allowlist, and prohibited options;
- opaque SecretReference resolver ID/version, resolver trust-root
  identity/version/hash, credential class/scope, required isolated runtime-auth
  context, and expiry/revocation policy;
- timeout, cancellation, retry prohibition, response protocol, required
  provider-native IDs/status fields, accounting method, and cost ceilings;
- expected rendered payload/context hashes and the exact ProviderReceipt
  evidence required to call delivery `proven`.

Canonical policy must be reproduced from independently loaded bundle and
manifest inputs through the accepted compiler. Hashing a caller-supplied
projection against another caller-supplied identity is invalid.

If a supported CLI cannot bind the accepted native model/profile, credential
scope, sandbox/root, or response protocol exactly, that provider remains
`unsupported`; no ambient default may stand in.

`LiveIssueBinding` is strictly pre-credential. Its schema must prohibit any
`CredentialUseReceipt`, claim-intent hash, receipt identity/hash, or
resolver-produced use evidence. It states what the later resolver proof must
satisfy but cannot depend on that proof.

### 4.3 Resolver-owned `CredentialUseReceipt` 1.0

Define a strict non-secret receipt produced and durably owned by the named
credential resolver, never by the coordinator or adapter. It binds:

- resolver ID/version and receipt identity/hash;
- exact SecretReference triple and credential class;
- deterministic proposed claim command/invocation identity and exact
  domain-separated `claim_intent_hash`;
- provider family, requested credential scope, isolated auth-context identity,
  and provider session/process context;
- the checked expiry/revocation state and check time;
- an explicit declaration that no credential bytes are present.

The coordinator obtains this proof before claim, validates it against an
independently configured resolver trust root, and includes its triple/hash in
the claim. The proof may remain in the resolver-owned store until the claim
commits; failed preflight must not publish it into the project canonical store.
Because the credential receipt is excluded from the intent preimage, this
creates no circular hash dependency; the final claim payload hash still covers
the receipt and every other final payload field.
Coordinator-fabricated, stale, wrong-resolver, wrong-scope, wrong-provider,
wrong-auth-context, wrong-claim, expired, or revoked proofs fail before claim
with zero project-canonical effects.

### 4.4 Invocation and crash semantics

An accepted claim authorizes at most one local invocation attempt. It does not
make the external provider call atomic and must not claim exactly-once external
execution.

The candidate must define the durable owner and state transition for invocation
evidence. At minimum it must distinguish:

- `not_invoked`: independently proved process/session creation never began;
- `observed`: provider outcome and accounting evidence were captured;
- `uncertain`: the claim exists but whether, or how far, the provider executed
  cannot be proved.

A crash after claim never triggers automatic provider retry. An uncertain
outcome remains visible and ineligible for research use. The candidate must
freeze conservative cost treatment without inventing token actuals: unresolved
cost remains reserved or is conservatively consumed under an explicit
disposition; it is never silently refunded or reported as exact.

### 4.5 `ProviderInvocationEvidence` 1.0

Define a strict content-addressed evidence artifact constructed by the shared
coordinator from process/provider observations, not command assertions, and
published idempotently through the named canonical object owner. It binds:

- claim and `LiveIssueBinding` triples;
- actual argv-profile hash, cwd/root, redacted environment/config evidence,
  resolver-owned `CredentialUseReceipt` triple, and invocation timestamps;
- provider-native request/session/thread/response IDs where exposed;
- actual provider/model/version/profile evidence or an explicit inability to
  prove each;
- payload/context delivery evidence;
- provider-native terminal/error class, exit/cancellation/timeout status,
  attempted/allowed/denied tools/actions, and output references/hashes;
- token/accounting evidence, method, omissions, and rate/cost calculation;
- secret-scan disposition over every actual producer seam required by 06b
  section 4.

Raw credentials, hidden reasoning, unrestricted transcripts, and secret
sentinels never enter canonical objects.

### 4.6 Outcome and reconciliation successor

Accepted ProviderReceipt 2.0 is the T2 authority/cost subset and remains
immutable. It cannot bind the complete live-issue claim and invocation-evidence
proof. Define explicit successor identities rather than weakening or rewriting
it.

The candidate must define the smallest coherent outcome transition. It must
not claim atomicity across object storage and the ledger. Instead:

1. publish the content-addressed invocation-evidence object idempotently;
2. submit one atomic `CommandService` ledger batch that references the exact
   object triple/hash and records outcome, receipt, and reconciliation.

An evidence object left by a crash before ledger commit is an inert orphan: it
authorizes no claim, invocation, receipt, result, refund, or research use.
Exact replay may reuse the same verified object but never invoke again or
publish a distinct object for the same evidence identity.

The outcome transition must:

- atomically record in the ledger the invocation-outcome reference, the live
  ProviderReceipt successor, and cost reconciliation, or prove why an existing
  accepted event can carry each binding without ambiguity;
- preserve the accepted T2 integer cost, rate-mode, refund, and
  post-expiry/revocation reconciliation rules;
- bind exact claim, invocation evidence, actual native provider/model/profile,
  command, policy, context/payload, reservation, and output identities;
- represent terminal, timed-out, cancelled/blocked, duplicate, uncertain, and
  not-invoked outcomes without manufacturing completeness or token actuals;
- return the original accepted outcome on exact replay and create no second
  invocation, receipt, reconciliation, refund, or evidence object.

If this requires a ProviderReceipt major successor, command/event successors,
or a W2 Receipt successor, version them explicitly and preserve all historical
schemas and records.

### 4.7 Shared coordinator and provider separation

The contract must name one shared coordinator as the only live invocation
owner. Its order is:

1. load the exact accepted T2 ledger batch and Receipt 2.0;
2. independently resolve and hash-check every bound canonical object;
3. compile and verify the canonical policy projection;
4. construct the exact provider-specific argv and managed payload;
5. obtain and validate the resolver-owned `CredentialUseReceipt`;
6. perform every pre-call negative and secret check;
7. submit the claim command; `CommandService` revalidates exact preflight
   hashes/versions and returns a newly accepted claim;
8. invoke the selected provider adapter once;
9. publish content-addressed invocation evidence idempotently through the named
   object owner;
10. submit the atomic ledger outcome/reconciliation command through
   `CommandService`.

Claude and Codex retain separate renderer, native evidence parser, canary,
negative-matrix, and bounded-smoke evidence. Success or completeness for one
family proves nothing for the other.

## 5. Machine acceptance

Literal, implementation-independent tests must prove:

- exact schema/command/event/stream/reducer/projection membership;
- claim accepts only a newly accepted canonical T2 issue and exactly one
  concurrent claimant;
- caller-fabricated receipts, events, objects, policy projections, model
  selectors, argv profiles, reservations, or evidence never authorize a call;
- every 06b section-4 pre-call negative leaves invocation count and canonical
  stores byte-identical;
- replay, crash-before-call, crash-during-call, timeout, nonzero exit,
  malformed/missing response evidence, provider outage, and uncertain outcome
  have exact non-success semantics;
- preflight failures leave the ledger and project canonical object store
  byte-identical; post-claim crashes leave a visible claim and never retry;
- resolver-owned credential receipts reject coordinator fabrication, wrong
  trust root, stale/wrong-scope/wrong-context/wrong-claim proof, expiry, and
  revocation;
- changing any enumerated intent field invalidates the credential receipt;
  changing or omitting the credential-receipt triple leaves the intent hash
  unchanged but invalidates the completed claim's full payload hash/binding;
- independent literal construction proves the intent preimage excludes exactly
  the credential-receipt identity/hash, final payload hash, and timestamps;
  includes command type, claim schema/version, full W2 write/tail bindings, and
  resolver trust-root/requirement fields; and has no extra omitted field;
- an independently authored direct dependency graph defines `A -> B` to
  mean B directly hashes or binds A and proves exactly these five direct edges:
  `LiveIssueBinding -> claim_intent_hash`,
  `claim_intent_hash -> CredentialUseReceipt`,
  `claim_intent_hash -> completed claim payload hash`,
  `LiveIssueBinding -> completed claim payload hash`, and
  `CredentialUseReceipt -> completed claim payload hash`; its transitive closure
  is acyclic; no edge may run from `CredentialUseReceipt` back to
  `LiveIssueBinding` or `claim_intent_hash`, so the graph has no fixed-point
  dependency;
- a crash after idempotent evidence publication but before ledger commit leaves
  an inert orphan; replay references the same verified object without another
  invocation or object identity;
- metered and `zero_cost_authorized` modes, ceilings, actuals, conservative
  uncertainty, refund, and post-expiry/revocation reconciliation;
- actual native model/profile/credential-context mismatch fails closed;
- policy omission/addition/reordering, generator substitution, context/payload
  drift, provider-family substitution, and response-binding substitution fail;
- raw credentials and sentinels cannot enter argv, environment/config capture,
  payload, events, objects, receipts, fixtures, evidence, or outputs;
- exact replay returns the original proof with zero new effects;
- accepted T2, WP6.1, T1a, ProviderCommand/Receipt predecessors, and Gate 5
  bytes remain unchanged.

Use independently authored expected sets. Candidate-generated catalogues,
schemas, or runtime registration cannot define the oracle.

## 6. Required outputs and authorized paths

The contract-authoring task may write only:

1. `docs/plans/agentic-research-system/design/10-wp6-2-t3-t4-live-issue-binding-addendum-2026-07-23.md`;
2. new strict live-issue catalogues, identity manifests, and schemas under
   `.research-system/contracts/` and `.research-system/schemas/`;
3. new strict schemas under `.research-system/schemas/wp6-2-live-issue/`;
4. independent contract validators, expected sets, fixtures, and focused tests
   under `tests/research_system/contracts/`;
5. one exact-state handback under
   `docs/plans/agentic-research-system/handoffs/trials/`;
6. the relevant README indexes and path-specific LF attributes if needed.

Do not edit `research_system/**`, the four uncommitted provider prototype paths,
accepted T2/WP6.1/T1a schemas or tests, provider predecessor schemas, results,
claims, profiles, Gate 5 artifacts, or T1b/T5-T8 surfaces.

Target no more than 30 changed paths. Any expansion requires a concrete
research-value justification and Stephen's approval before writing.

## 7. Validation and review

Use a contract-first RED/GREEN ladder:

1. literal expected command/event/identity membership and negative fixtures;
2. strict Draft 2020-12 schema validation with format checking;
3. semantic validators for canonical resolution, policy derivation, concurrency,
   idempotency, crash/uncertainty, evidence, cost, and replay;
4. focused new live-issue contract tests;
5. unchanged accepted-byte proofs and `git diff --check`.

Do not run the historical 135-test T2 suite or a package-wide suite merely
because they exist. Expand validation only for a concrete changed shared seam
and record the reason.

Return an immutable proposed candidate and compact exact-state handback. A
fresh reviewer with no author history reviews only that candidate. One bounded
remediation cycle is allowed for still-valid findings, followed by a new
history-free review of the changed elements. A second `rework_required` verdict
stops for Stephen.

Passing tests and review do not accept the contract. Stephen must accept the
exact candidate commit/tree and every path/blob/raw-SHA-256 identity before any
shared coordinator or provider adapter implementation resumes.

## 8. Explicit non-goals and stops

This brief authorizes no:

- provider invocation, credential resolution, ambient credential use, live
  smoke, adapter remediation, or shared coordinator implementation;
- mutation of accepted contracts, runtime T2, WP6.1, T1a, Gate 5, results, or
  claims;
- assertion of external exactly-once execution;
- automatic retry after claim or uncertain execution;
- T1b-M/T1b-H, T5-T8, M/H eligibility, publication, or Gate 6 transition.

Stop if the candidate cannot define one canonical writer and object owner,
cannot preserve T2 stream/version semantics, needs secret bytes in canonical
state, treats ambient CLI defaults as evidence, or cannot make uncertainty and
cost disposition explicit.

The sole next dependency after exact contract acceptance is a separately
authorized shared-coordinator implementation, followed by separate corrected
T3 and T4 candidates and independent provider-specific evidence. Nothing in
this brief starts those actions.

