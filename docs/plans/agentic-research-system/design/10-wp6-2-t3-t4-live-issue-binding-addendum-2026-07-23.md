# WP6.2 T3/T4 Live-Issue Binding Addendum

**Status:** proposed candidate pending fresh independent review and Stephen's
exact-identity acceptance. It authorizes no runtime implementation, credential
resolution, provider call, smoke test, result, claim, or publication.

## 1. Authority and immutable predecessors

This addendum is the shared contract boundary for T3 Claude and T4 Codex. It is
authored from dispatch base `2291b5d4736ad604ce9763d9c677e707970ef14e`
under brief 13. P-037 through P-041, W2, W7, W8, and implementation plan 06b
remain controlling.

The accepted T2 family, ProviderCommand 2.0, ProviderReceipt 2.0, WP6.1, and
T1a are immutable. In particular, the accepted T2 issue is an authority/cost
subset; it is necessary but insufficient evidence of a live provider
invocation.

## 2. Ownership and transitions

`research_system.command.service.CommandService` is the sole canonical ledger
writer. The shared live coordinator is
`research_system.live_issue.coordinator.LiveIssueCoordinator`; this name fixes
future ownership but does not authorize its implementation.

The new transitions are:

1. `ClaimLiveProviderInvocation -> [LiveProviderInvocationClaimed]`;
2. publish `ProviderInvocationEvidence` idempotently through
   `research_system.store.canonical_objects.CanonicalObjectStore`;
3. `RecordLiveProviderInvocationOutcome ->
   [ProviderInvocationOutcomeRecorded, LiveProviderReceiptRecorded,
   LiveCostGrantReconciled]` as one ordered atomic ledger batch.

The claim writes a new `provider_invocation` stream at expected version zero.
It does not change T2 cost-grant or provider-command stream versions. The
outcome transition advances the same invocation stream and the existing
cost-grant stream using one ordered write set. Rejection or conflict produces
zero events and zero invocations. Concurrent claims have exactly one winner
and are never automatically retried.

Reducers are `provider_invocation_reducer@1.0.0`,
`live_provider_receipt_reducer@3.0.0`, and
`cost_grant_reducer@1.0.0`. Projections are
`provider_invocation_lifecycle_projection@1.0.0`,
`live_provider_receipt_binding_projection@3.0.0`, and
`cost_grant_balance_projection@1.0.0`.

## 3. Canonical pre-call claim

Only a newly accepted, non-duplicate `AuthorizeProviderIssue` Receipt 2.0 may
claim. `CommandService` loads the exact transaction and revalidates its ordered
`CostGrantReserved` and `ProviderCommandIssued` events, hashes, versions, W2
tuple, tail binding, and all authority triples under the writer lock.

The command binds the exact ProviderCommand, CostGrant, reservation,
SecretReference, Task, Dispatch, Attempt, ResourceGrant, route/profile,
context, policy, adapter, and `LiveIssueBinding` triples; provider family and
normalized operation; deterministic invocation identity; complete W2 tuple;
preflight hashes and expected versions; resolver trust-root requirements; and
the resolver-owned `CredentialUseReceipt` triple.

The intent hash is:

```text
SHA-256(
  UTF-8("ars:wp6-2:live-claim-intent:v1\0")
  || canonical_json(claim_intent_preimage)
)
```

The strict preimage is reconstructed from an explicit allowlist in the
`ClaimLiveProviderInvocation` schema. It includes the claim schema/version,
command envelope, complete write/tail binding, deterministic invocation
identity, accepted T2 receipt/transaction/event proof, all canonical triples,
resolver trust-root and requirement fields, provider/operation, and preflight
hashes and versions. It excludes exactly the CredentialUseReceipt
identity/revision/hash, the completed payload hash, and submission/recording
timestamps. It is never derived by deleting arbitrary keys from caller input.

The final W2 payload hash covers every completed claim field, including the
intent hash and CredentialUseReceipt triple. Changing an intent field
invalidates the resolver proof. Changing only the resolver-receipt triple
leaves the intent hash unchanged but invalidates the completed payload binding.

All object resolution, policy compilation, argv and payload construction,
expiry/revocation checks, resolver-proof validation, and secret scans happen
before claim without project-ledger or canonical-object mutation. Under the
writer lock, drift in any accepted T2 proof, object version, preflight hash,
expiry, revocation, or tail binding rejects with zero effects.

## 4. LiveIssueBinding 1.0

`LiveIssueBinding` is strict, content-addressed, and pre-credential. It binds:

- independently loaded policy bundle and applicability-manifest triples,
  compiler/generator identity and revision, compiled projection hash, and exact
  ordered control membership;
- context packet/addenda triples, rendered managed-content hash, and both W3
  token-gate decisions;
- provider family, native model/version selector, evaluated W4 route/profile,
  and reasoning setting;
- adapter revision and exact argv profile: executable, ordered flags,
  model/profile/reasoning selection, sandbox, cwd/root, network, tools,
  permissions, environment allowlist, and prohibited options;
- SecretReference resolver ID/version, resolver trust-root triple, credential
  class/scope, isolated auth-context requirements, and expiry/revocation rule;
- timeout, cancellation, retry prohibition, response protocol, required
  provider-native identity/status fields, accounting method, ceilings,
  expected payload/context hashes, and exact ProviderReceipt proof needed for
  `delivery = proven`.

Canonical policy is recompiled from independently resolved bundle and manifest
inputs. A caller-supplied projection and caller-supplied identity cannot vouch
for one another. A provider whose native CLI cannot bind the accepted model,
credential scope, sandbox/root, or response protocol exactly remains
`unsupported`; ambient defaults are forbidden.

The schema prohibits CredentialUseReceipt data, claim-intent hashes, receipt
identities/hashes, resolver-produced use evidence, raw credentials, and secret
sentinels.

## 5. Resolver-owned CredentialUseReceipt 1.0

The named credential resolver durably owns and produces a strict, non-secret
`CredentialUseReceipt`. Neither coordinator nor adapter may construct it. It
binds the resolver identity/version and trust root, SecretReference triple and
credential class, deterministic proposed claim command and invocation
identities, exact intent hash, provider family, requested scope, isolated auth
context, provider process/session context, checked expiry/revocation state and
time, and the declaration `contains_credential_bytes = false`.

The coordinator validates the proof against an independently configured trust
root before claim. Until claim commits, the proof remains resolver-owned and is
not published in the project canonical store. Coordinator-fabricated,
wrong-root, stale, wrong-scope, wrong-provider, wrong-context, wrong-claim,
expired, or revoked proof rejects with zero project-canonical effects.

## 6. Invocation and crash semantics

An accepted claim authorizes at most one local invocation attempt. It does not
promise exactly-once external execution. The lifecycle is:

- `not_invoked`: independent process/session evidence proves creation never
  began;
- `observed`: provider outcome and accounting evidence were captured;
- `uncertain`: the claim exists but execution extent cannot be proved.

A crash after claim never causes automatic retry. `uncertain` is visible and
ineligible for research use. Unresolved cost remains reserved or is
conservatively consumed under the recorded disposition; token actuals are not
invented and unresolved reservation is never silently refunded.

## 7. ProviderInvocationEvidence 1.0

The coordinator constructs strict content-addressed evidence from actual
process/provider observations, not command assertions. It binds the claim and
LiveIssueBinding triples; actual argv hash, cwd/root and redacted
environment/config evidence; CredentialUseReceipt triple; timestamps;
provider-native request/session/thread/response identities; actual
provider/model/version/profile proof or explicit inability to prove each;
payload/context delivery evidence; terminal/error class; exit,
cancellation/timeout; attempted/allowed/denied tools/actions; output
references/hashes; token/accounting method, omissions and integer cost
calculation; and per-seam secret-scan dispositions required by 06b section 4.

Raw credentials, hidden reasoning, unrestricted transcripts, and sentinels are
forbidden.

## 8. Outcome, evidence orphan, and replay

Evidence publication and ledger commit are intentionally not atomic. A crash
after idempotent evidence publication leaves an inert orphan. It authorizes no
claim, invocation, receipt, result, refund, or research use. Exact replay
verifies and reuses the same object identity, invokes nothing, and cannot
publish a distinct identity for the same evidence.

The atomic outcome batch binds claim, evidence, actual native
provider/model/profile, command, policy, context/payload, reservation, output,
live ProviderReceipt 3.0, and cost reconciliation. It represents terminal,
timed-out, cancelled, blocked, duplicate, uncertain, and not-invoked outcomes
without manufacturing completeness or token actuals.

Metered reconciliation retains T2 integer ceiling arithmetic. An accepted
`zero_cost_authorized` path pins zero rates and its authority triple. Later
expiry or revocation does not strand reconciliation for an accepted
invocation. Exact replay returns the original accepted outcome and creates no
second invocation, evidence, receipt, reconciliation, or refund.

## 9. Dependency graph and provider separation

For `A -> B`, B directly hashes or binds A. The complete direct graph is:

```text
LiveIssueBinding -> claim_intent_hash
claim_intent_hash -> CredentialUseReceipt
claim_intent_hash -> completed_claim_payload_hash
LiveIssueBinding -> completed_claim_payload_hash
CredentialUseReceipt -> completed_claim_payload_hash
```

Its transitive closure is acyclic. No edge returns from
CredentialUseReceipt to LiveIssueBinding or claim_intent_hash.

The shared coordinator owns ordering only. Claude and Codex keep separate
renderers, native evidence parsers, canaries, negative matrices, and bounded
smoke evidence. Evidence for one provider family proves nothing for the other.

## 10. Lifecycle boundary

This candidate remains `proposed`. Passing author tests is not acceptance.
Only a fresh independent review followed by Stephen's acceptance of the exact
candidate commit/tree and every path/blob/raw-SHA-256 identity can accept it.
No shared-coordinator or provider-adapter implementation may resume before that
separate decision.
