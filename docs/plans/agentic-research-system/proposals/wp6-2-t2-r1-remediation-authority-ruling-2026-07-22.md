# WP6.2 T2 R1 Remediation Authority Ruling

**Date:** 2026-07-22
**Decision ID:** P-038 (proposed)
**Status:** PROPOSED - pending Stephen's exact acceptance
**Amends:** P-037 only to close the R1 contract gaps
**Scope:** one T2 contract/addendum remediation and fresh independent R2; no runtime

## Decision required

The R1 adversarial review of candidate
`1144d6a6d0feb28473fb540d41ff03bff79eec24` returned `rework_required` with four
Critical and three Major findings. P-037 authorizes the three command families and
non-destructive successor versioning, but does not settle all exact choices needed to
remediate those findings without invention by the author.

Accepting this proposal authorizes one bounded author remediation cycle and one fresh
independent R2 review. It does not accept the remediated candidate in advance.

## Proposed ruling

### 1. Command family and immutable history

- `CommandService` remains the sole canonical writer.
- P-037's three command/event families and their event order remain unchanged.
- Candidate `1144d6a6d0feb28473fb540d41ff03bff79eec24` remains immutable rejected history.
- All previously accepted WP6.1, T1a, W2, W7, and W8 bytes remain immutable.

### 2. Receipt 2.0 proof surface

Preserve `ars://core/receipt` version `1.0.0` and its bytes. Authorize a breaking
successor with:

- schema ID `ars://core/receipt/v2`;
- version `2.0.0`; and
- repository path `.research-system/schemas/core/receipt-v2.schema.json`.

An accepted or duplicate Receipt 2.0 must bind `command_id`, `idempotency_key_hash`,
`payload_hash`, `event_batch_id`, and a canonical ordered event list. Each event entry
must bind `event_id`, `transaction_position`, `stream_id`, and
`resulting_stream_version`. A rejected or conflict receipt carries no event entries and
binds a stable reason plus unmet preconditions. Duplicate replay returns a
byte-equivalent outcome binding to the original accepted receipt and emits no event or
invocation. Readers and reducers must dispatch by exact major version; Receipt 1.0 is
audit-readable but cannot satisfy this T2 pre-invocation gate.

### 3. Rebuildable T2 event envelopes

Each of the five new T2 event schemas at version `1.0.0` must require
`idempotency_key_hash` and `payload_hash` in addition to `command_id`. Tests must prove
that the idempotency index can be rebuilt from canonical event bytes and that replay
cannot duplicate reservation, invocation, receipt, reconciliation, or refund effects.

### 4. Enforced secret boundary and pre-issue evidence

Authorize a new strict type:

- name `PreIssueEvidenceManifest`;
- schema ID `ars://wp6-2/t2/pre-issue-evidence-manifest`;
- version `1.0.0`;
- path `.research-system/schemas/wp6-2-t2/pre-issue-evidence-manifest.schema.json`;
- canonical ID prefix `pem_` plus a lowercase UUIDv7 suffix.

The manifest must bind the ordered eight producer-seam identities; policy and scanner
identities/versions; a safe synthetic sentinel identity and hash; source evidence
references and hashes; per-seam outcomes; and one aggregate content hash. It records no
credential or sentinel value. `SecretReference.resolver_id` must be a typed canonical
registry identity, not an arbitrary string. Pre-issue validation recursively scans the
actual serialized seam payloads for prohibited secret material and the safe sentinel;
fabricated counters or aggregate self-attestation cannot satisfy the gate. Any failed,
missing, stale, or mismatched seam blocks canonical publication and provider invocation.

### 5. Relational identity and authority validation

Strict shape schemas remain necessary but do not substitute for semantic validation.
The independent validator and negative fixtures must enforce:

- equality of target stream ID, declared write-set stream ID, and payload entity ID;
- `IssueCostGrant.expected_version == 0`;
- deterministic reservation identity derivation;
- equality of every command subject ID/revision/hash with the bound canonical objects;
- for `RecordProviderReceipt`, exact CostGrant ID/revision/hash and reservation
  ID/revision/hash in addition to the provider command and receipt bindings; and
- exact ordered-event and resulting-stream-version relations.

### 6. Token ceilings and integer cost arithmetic

Actual input, output, and total tokens must not exceed their reserved component and
total ceilings. Cost is calculated in integer microunits as:

```text
ceil_div(actual_input_tokens * input_microunits_per_million_tokens, 1_000_000)
+ ceil_div(actual_output_tokens * output_microunits_per_million_tokens, 1_000_000)
```

`consumed_cost_microunits` must equal that result and
`refund_cost_microunits = reserved_cost_microunits - consumed_cost_microunits`, with no
negative amount. Rates use one closed mode: `metered` requires both rates to be positive;
`zero_cost_authorized` requires both to be zero and binds an explicit authority
ID/revision/hash. Currency and rate-evidence identities must agree across the grant,
reservation, provider receipt, and reconciliation. No floating-point arithmetic is
permitted.

### 7. Complete W7 successors

ProviderCommand 2.0 and ProviderReceipt 2.0 must crosswalk every normative requirement
in W7 sections 9 and 10. A field may be absent only where W7 expressly permits an
inability to prove or provider non-exposure, represented by a typed `not_exposed`
disposition with evidence. An incomplete receipt remains diagnostic-only and cannot
satisfy dispatch, delivery, reconciliation, or review gates.

### 8. Canonical identifier syntax

All canonical ID schemas and fixtures must enforce a lowercase UUIDv7 suffix. Preserve
the accepted W7 `pcmd_` and `prcp_` prefixes as scoped aliases/exceptions; they are not
renamed by this remediation. New T2 first-class identities use three-letter prefixes:
`srf_` for SecretReference, `cgr_` for CostGrant, `crs_` for CostGrantReservation, and
`pem_` for PreIssueEvidenceManifest. Placeholder suffixes such as `_abc` are invalid in
positive fixtures.

### 9. Independent completeness oracle and review gate

The remediation must include a machine-readable normative crosswalk from W2, W7, W8,
06b, P-037, and P-038 to each schema property, relational validator, and positive or
negative test. The expected oracle must be authored independently of the materializer.
Counterexamples must cover every R1 finding. Existing deterministic artifacts must be
certified before any authorized regeneration.

The author produces one new immutable candidate commit and exact-state handback. A fresh
independent R2 reviewer receives no author or manager conversation history and reviews
that exact candidate. Stephen remains the owner of any CodeRabbit activity. No
implementation brief may issue until the exact remediated paths, Git blobs, raw-byte
SHA-256 identities, candidate commit, and an approving independent verdict are returned
to Stephen for acceptance.

## Hard stops

Stop without writes outside the bounded contract/addendum surface if remediation would:

- change the P-037 command family or event ordering;
- mutate any accepted schema, fixture, catalogue, manifest, Stage-2 record, or T1a byte;
- require runtime code, a live provider call, T3/T4, T1b, eligibility, result, or claim
  action;
- invent an additional authority choice; or
- fail an exact worktree, branch, subject, protected-byte, or independent-oracle check.

## Copy-paste owner decision

```text
I accept the proposed WP6.2 T2 R1 remediation authority ruling dated 2026-07-22 at the
exact repository path, Git blob, raw-byte SHA-256 identity, and manager commit stated in
the acceptance packet. Author one bounded contract/addendum remediation cycle under
P-037 and P-038, preserving the rejected R1 candidate and all accepted bytes, then send
the new immutable candidate for fresh independent R2 review. This acceptance authorizes
contract/addendum remediation and review only; it authorizes no runtime implementation,
live provider call, T3/T4, T1b, eligibility, result, or claim action.
```
