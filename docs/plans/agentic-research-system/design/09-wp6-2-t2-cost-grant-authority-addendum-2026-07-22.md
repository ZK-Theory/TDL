# WP6.2 T2 Cost-Grant Authority Addendum

**Date:** 2026-07-22
**Status:** `proposed_pending_fresh_independent_review_and_stephen_exact_hash_acceptance`
**Decision authority:** P-020, P-035, P-036, P-037, and accepted remediation ruling P-038
**Scope:** WP6.2 T2 contract materialization only
**Runtime authority:** None

## 1. Purpose and boundary

This addendum closes the exact canonical-transition contract for the WP6.2 T2
credential and cost boundary. It materializes authority, schema, event-order,
reducer, projection, concurrency, replay, rejection, receipt, and test identities.
It does not implement a command handler, reducer, projection, provider transport,
credential resolver, or live invocation.

The existing project-wide
`research_system.command.service.CommandService` is the only canonical writer.
No adapter, provider process, worktree, cost helper, or second service may allocate
positions, publish events, or update cost state directly.

The transition family is closed and contains exactly:

1. `IssueCostGrant -> [CostGrantIssued]`;
2. `AuthorizeProviderIssue -> [CostGrantReserved, ProviderCommandIssued]`;
3. `RecordProviderReceipt -> [ProviderReceiptRecorded, CostGrantReconciled]`.

The bracket order is canonical transaction order. The two two-event forms are one
atomic W2 batch each. A partial batch, reversed order, duplicate event, extra event,
or separate publication is invalid. No fourth T2 mutation command is authorized.

## 2. Immutable predecessors and version disposition

The accepted WP6.1 command tree
`9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea`, event tree
`154ffc4bdde82fe903718734687e7a62797b1f69`, and core tree
`b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46` remain unchanged. Accepted T1a
artifacts also remain byte-identical.

The accepted ProviderCommand 1.0.0 schema remains at
`.research-system/schemas/adapters/provider-command.schema.json`, Git blob
`9eb58609b9703674912e64f019db3cd4fb147a9c`. The accepted ProviderReceipt 1.0.0
schema remains at `.research-system/schemas/adapters/provider-receipt.schema.json`,
Git blob `8ac904e6c0b16e45034bcdc2221970d6a3ef13a8`. Neither file may be edited.

| Type | Canonical schema ID | Version | Repository path | Disposition |
|---|---|---:|---|---|
| SecretReference | `ars://wp6-2/t2/secret-reference` | 1.0.0 | `.research-system/schemas/wp6-2-t2/secret-reference.schema.json` | new strict identity |
| CostGrant | `ars://wp6-2/t2/cost-grant` | 1.0.0 | `.research-system/schemas/wp6-2-t2/cost-grant.schema.json` | new strict identity |
| PreIssueEvidenceManifest | `ars://wp6-2/t2/pre-issue-evidence-manifest` | 1.0.0 | `.research-system/schemas/wp6-2-t2/pre-issue-evidence-manifest.schema.json` | new strict evidence identity |
| Receipt successor | `ars://core/receipt/v2` | 2.0.0 | `.research-system/schemas/core/receipt-v2.schema.json` | T2 proof surface; Receipt 1.0.0 remains byte-identical and audit-only |
| ProviderCommand successor | `ars://adapters/provider-command/v2` | 2.0.0 | `.research-system/schemas/wp6-2-t2/provider-command-v2.schema.json` | required-field successor; 1.0.0 is audit-only for T2 |
| ProviderReceipt successor | `ars://adapters/provider-receipt/v2` | 2.0.0 | `.research-system/schemas/wp6-2-t2/provider-receipt-v2.schema.json` | required-field successor; 1.0.0 is audit-only for T2 |

A 2.0.0 reader may retain explicit audit support for historical 1.0.0 records. A
1.0.0 reader must reject 2.0.0. T2 issue and reconciliation require the exact 2.0.0
identities. No alias, filename inference, in-place required-field expansion, or
1.1.0 substitution is permitted.

## 3. W2 envelope and receipt rules

Every T2 command carries the W2 command identity and exact values for
`command_id`, `command_type`, `schema_id`, `schema_version`, `submitted_at`,
`actor_id`, optional delegating actor, `authority_grant_id`, `authority_scope`,
`target_stream_id`, the complete ordered write set with an expected version for
each stream, `idempotency_key`, canonical `payload_hash`, correlation and causation,
reason, evidence references, and a strict payload.

Validation follows W2 order. Schema, identity/hash, ownership, authority, expected
versions, idempotency, state preconditions, assurance/dependency gates, and complete
batch integrity all pass before publication. A failure publishes no lifecycle event.

The logical submission tuple is exactly:

```text
(actor_id, authority_scope, command_type, idempotency_key)
```

The same tuple and canonical payload hash returns the original W2 receipt. It emits
no second grant, reservation, issue, provider invocation, provider receipt,
reconciliation, or refund. The same tuple with a different payload hash returns
`idempotency_conflict`. A stale expected version returns `stale_stream_version`.
Neither rejection is auto-rebased.

Accepted and duplicate outcomes use `ars://core/receipt/v2` 2.0.0. They bind the
command, idempotency-key hash, payload hash, event-batch identity, and canonical
ordered events; each event binds its ID, transaction position, stream ID, and
resulting stream version. A duplicate carries the byte-equivalent original outcome
binding and records zero new event or invocation. Rejected and conflict receipts
carry no event entries and bind a stable reason plus unmet preconditions. Exact major
version dispatch is mandatory; Receipt 1.0.0 remains audit-readable but cannot prove
the T2 pre-invocation gate.

## 4. Exact authority catalogue

### 4.1 IssueCostGrant

- **Schema:** `ars://wp6-2/t2/command/IssueCostGrant` 1.0.0.
- **Authority scope:** `wp6.2.t2.cost-grant.issue`.
- **Authority subject:** the exact ResourceGrant revision/hash plus Task, Dispatch,
  and Attempt identities.
- **Target/write set:** the new CostGrant stream only, with expected version `0`.
- **Event set:** exactly `[CostGrantIssued]`.
- **Reducer:** `cost_grant_reducer@1.0.0`.
- **Projections:** `cost_grant_balance_projection@1.0.0` and
  `cost_grant_authorization_projection@1.0.0`.
- **Preconditions:** the ResourceGrant and authority grant are active; the exact
  Task/Dispatch/Attempt, route/profile, adapter revision, SecretReference, prepared
  ProviderCommand 2.0.0, token ceilings, rate evidence, cost ceiling, currency,
  expiry, and revocation bindings agree.
- **Effect:** create one immutable CostGrant with zero initial reservation,
  consumption, and refund amounts. The CommandService supplies event/batch identity.

### 4.2 AuthorizeProviderIssue

- **Schema:** `ars://wp6-2/t2/command/AuthorizeProviderIssue` 1.0.0.
- **Authority scope:** `wp6.2.t2.provider.issue`.
- **Authority subject:** the exact CostGrant, ProviderCommand 2.0.0, and
  SecretReference revisions and hashes.
- **Target:** the CostGrant stream, which is the concurrency-arbitration stream.
- **Ordered write set:** CostGrant stream then ProviderCommand stream, with an
  expected version for each.
- **Event set:** exactly `[CostGrantReserved, ProviderCommandIssued]` in one batch.
- **Reducers:** `cost_grant_reducer@1.0.0` and
  `provider_command_reducer@2.0.0`.
- **Projections:** `cost_grant_balance_projection@1.0.0` and
  `provider_command_lifecycle_projection@2.0.0`.
- **Reservation identity:** `crs_` plus the UUIDv7 portion of the accepted command
  ID. Only CommandService constructs it; callers cannot substitute it.
- **Effect:** reserve the requested token/cost ceiling and record the exact command
  issue atomically before transport invocation. Provider invocation is permitted
  only after the accepted receipt proves both event IDs in canonical order.

Two commands competing for one remaining balance arbitrate under the project writer
lock against the same CostGrant expected version. Exactly one may publish the two-event
batch and invoke; the loser returns `cost_grant_exhausted` or
`stale_stream_version`, publishes nothing, and is not automatically retried. Total
reserved plus consumed microunits never exceeds the grant ceiling.

### 4.3 RecordProviderReceipt

- **Schema:** `ars://wp6-2/t2/command/RecordProviderReceipt` 1.0.0.
- **Authority scope:** `wp6.2.t2.provider.receipt.record`.
- **Authority subject:** the exact issued ProviderCommand, ProviderReceipt 2.0.0,
  CostGrant, and reservation identities and hashes.
- **Target:** the ProviderCommand stream.
- **Ordered write set:** ProviderCommand stream then CostGrant stream, with an
  expected version for each.
- **Event set:** exactly `[ProviderReceiptRecorded, CostGrantReconciled]` in one batch.
- **Reducers:** `provider_command_reducer@2.0.0` and
  `cost_grant_reducer@1.0.0`.
- **Projections:** `provider_command_lifecycle_projection@2.0.0`,
  `provider_receipt_binding_projection@2.0.0`, and
  `cost_grant_balance_projection@1.0.0`.
- **Effect:** record one complete, identity-matched receipt and reconcile its actual
  accounting atomically.

`CostGrantReconciled` carries actual input, output, and total token consumption;
reserved and consumed cost microunits; refund microunits; and the refund disposition.
The semantic identities are:

```text
actual_total_tokens = actual_input_tokens + actual_output_tokens
0 <= consumed_cost_microunits <= reserved_cost_microunits
consumed_cost_microunits =
  ceil_div(actual_input_tokens * input_microunits_per_million_tokens, 1_000_000)
  + ceil_div(actual_output_tokens * output_microunits_per_million_tokens, 1_000_000)
refund_cost_microunits = reserved_cost_microunits - consumed_cost_microunits
refund_disposition = fully_consumed  iff refund_cost_microunits = 0
refund_disposition = refunded       iff refund_cost_microunits > 0
```

The receipt/provider/profile/adapter/policy/context/rendered-payload/command/grant/
reservation identities must all agree. Missing actuals, an incomplete receipt, an
over-consumption, inconsistent totals, or a refund mismatch rejects the full batch.

## 5. SecretReference and pre-issue producer seams

SecretReference is opaque and byte-free. It uses `srf_` plus a lowercase UUIDv7 and
records only an ID, revision/hash, provider and credential class, a typed canonical
secret-resolver registry URI/revision/hash, resolver version, exact allowed identity scope,
expiry, existing authority/resource revocation bindings, and redaction proof. Its
strict schema has no field capable of carrying a secret, raw environment value,
provider token, credential text, or transcript.

Immediately before issue, the candidate must prove sentinel absence independently at
all eight consumed producer seams, in this exact order:

1. compiled context packet;
2. generated adapter/provider file;
3. rendered provider payload;
4. argv, environment-derived config, or provider options;
5. event producer;
6. receipt producer;
7. canonical object producer;
8. fixture/evaluation-evidence producer.

A sentinel at any seam returns `secret_material_detected`, with zero reservation,
zero invocation, and zero canonical publication. A post-run scan is defense in depth
and cannot compensate for a failed or absent pre-issue check.

The `pem_` PreIssueEvidenceManifest binds those eight seams in order, the producer,
policy, and scanner identities/versions/hashes, safe synthetic sentinel identity and
hash (never its value), source-evidence references and hashes, per-seam outcomes, and
an aggregate content hash. The validator canonical-serializes and recursively scans
the actual eight payload objects. Counters and aggregate self-attestation are not
accepted substitutes; a missing, stale, failed, or mismatched seam blocks publication
and invocation.

## 6. CostGrant state, expiry, and revocation

CostGrant is an immutable 1.0.0 object bound to the ResourceGrant, authority grant,
Task/Dispatch/Attempt, route/profile, adapter revision, SecretReference, prepared
ProviderCommand 2.0.0, currency/rate evidence, token ceilings, cost ceiling, expiry,
and idempotency identity. Monetary values are non-negative integer microunits; token
values are non-negative integers. Floating cost values are prohibited.

Expiry and revocation do not create a fourth T2 mutation. New issue authorization
fails closed from existing authority and W8 ResourceGrant state:

- CommandService compares its trusted current command time with `expires_at`;
- it requires the referenced AuthorityGrant and ResourceGrant projections to be active;
- expiry returns `cost_grant_expired` or `secret_reference_expired`;
- existing authority/resource revocation returns `cost_grant_revoked` or
  `secret_reference_revoked`;
- these rejections publish no T2 lifecycle event.

The historical CostGrant object is not rewritten and no clock-derived canonical
projection is invented. A reservation accepted before later expiry or revocation must
still be reconciled by `RecordProviderReceipt`; otherwise cost state could remain
indeterminate. Expiry/revocation blocks new provider issue, not the mandatory recording
and reconciliation of an already-issued command.

## 7. Stable rejection contract

The strict catalogue freezes the complete rejection vocabulary and the test identity
for every case. Required classes include:

- secret missing, wrong type, expired, revoked, identity mismatch, and all eight
  sentinel seams;
- CostGrant missing, wrong type, zero, exhausted, expired, revoked, identity mismatch,
  and insufficient remaining balance;
- two-command over-reservation, stale CostGrant or ProviderCommand versions, and
  same idempotency tuple with a different payload;
- accepted-command replay, event-order swap, partial batch, missing reducer, and
  missing projection;
- schema alias, version, and hash substitution;
- attempted mutation of accepted ProviderCommand/ProviderReceipt 1.0.0 or any
  protected WP6.1/T1a byte.

Every pre-issue rejection has zero provider invocation. Every rejected/conflict path
has zero canonical T2 events. Replay is the sole non-accepted path returning the
original accepted receipt rather than a rejection code.

## 8. Content addressing and manifest dependency graph

Repository identity is computed from exact raw UTF-8/LF bytes before parsing. The same
bytes are then parsed and validated with strict Draft 2020-12 schemas and format
checking. Each leaf identity records repository path, canonical schema ID/version when
applicable, Git blob ID after commit, and raw-byte SHA-256.

The dependency graph is acyclic:

```text
leaf addendum/schemas/catalogue/validator/tests
  -> wp6-2-t2-schema-identities manifest
    -> external independent-review record
      -> external Stephen exact-hash acceptance record
```

The manifest records its own path and schema identity but cannot contain its own hash.
Its Git blob and raw SHA-256 are therefore computed and bound by the exact-state
handback, independent review, and owner-acceptance record. Candidate YAML and Markdown
cannot self-attest review or acceptance.

## 9. Candidate lifecycle and hard stops

All materialized T2 artifacts remain `proposed`. Their intended reviewer is a fresh
independent reviewer who did not author this candidate; their intended acceptor is
Stephen. Review outcome and acceptance are external, attributed records bound to the
exact candidate commit, repository paths, Git blobs, and raw SHA-256 values.

Stop and return to the owner if any exact writer, command/event identity, authority
subject, write set, expected version, reducer, projection, receipt, expiry/revocation
binding, concurrency rule, or version disposition cannot be preserved without a new
canonical transition. This addendum authorizes no T2 runtime implementation, T3/T4,
provider call, T1b, eligibility transition, result, claim, migration, or mutation of
accepted artifacts.

## 10. P-038 relational and replay closure

All five T2 event envelopes require `idempotency_key_hash` and `payload_hash`. The
independent validator rebuilds the command-to-idempotency/payload index from canonical
event bytes and rejects a conflicting binding or duplicate grant, reservation,
invocation, provider-receipt, reconciliation, or refund effect.

Shape validation is followed by independent relational validation. Target stream,
declared write-set stream, and payload entity IDs must agree. `IssueCostGrant` creates
its stream at expected version zero. `AuthorizeProviderIssue` binds the CostGrant
expected version to its exact revision, creates the ProviderCommand stream at version
zero, and derives `crs_<command UUIDv7>` deterministically. `RecordProviderReceipt`
binds exact CostGrant and reservation IDs, revisions, and hashes in addition to the
ProviderCommand and ProviderReceipt. Every authority-subject ID/revision/hash is
compared with the independently supplied canonical object. Receipt event order,
stream IDs, and resulting versions must match the accepted write set.

## 11. Closed cost and rate modes

Actual input, output, and total tokens may not exceed their respective reserved
ceilings. Cost arithmetic is integer-only. `metered` requires both per-million rates
to be positive and no zero-cost authority. `zero_cost_authorized` requires both rates
to be zero and an exact authority ID/revision/hash. Currency and the rate-evidence
ID/revision/hash are equal across grant, reservation, ProviderReceipt, and
reconciliation; the refund cannot be negative.

## 12. Complete W7 successors and identifiers

ProviderCommand 2.0 binds every W7 section 9 class: W2 command/message/dispatch and
control-store position; W4 route/profile/evaluation/policy and exact `res_` snapshot;
W3 candidate/packet/addendum, content hash, and both token gates; W5 purpose and
visibility; W8 resource grant, lease, and stop policy; normalized operation and
rendered hash; permissions/default deny; receipt expectations; and timeout, expiry,
retry, and reconciliation policy.

ProviderReceipt 2.0 binds every W7 section 10 class: command/provider/model/profile/
adapter/policy identities; native IDs; issue/acknowledgement/terminal timestamps;
delivery proof; token/capacity accounting; actions; terminal/native outcome; outputs;
lifecycle evidence; W8 resource/process observations; and redaction/omission evidence.
Typed `not_exposed` with evidence is confined to provider request/session/response
IDs. Inability to prove delivery makes the receipt incomplete and diagnostic-only;
dispatch, delivery, reconciliation, and review gates remain false.

Every canonical ID uses a lowercase UUIDv7 suffix. The accepted W7 `pcmd_` and
`prcp_` aliases remain. New T2 identities use `srf_`, `cgr_`, `crs_`, and `pem_`.

## 13. Independent normative crosswalk

`.research-system/contracts/wp6-2-t2-normative-crosswalk.yaml` maps W2, W7, W8,
06b, P-037, and P-038 to exact schema properties, semantic validators, and positive
and negative tests for C1-C4 and M1-M3. Its expected mapping is a separately authored
literal oracle in `wp6_2_t2_expectations.py`; neither surface is derived from the
schema materializer. This crosswalk and its strict schema remain proposed candidate
evidence and confer no runtime or acceptance authority.
