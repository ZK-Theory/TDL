# WP6.2 T2 Cost-Grant Authority and Versioning Ruling

**Date:** 2026-07-22
**Status:** PROPOSED — Stephen decision required before authority-addendum authorship
or T2 implementation
**Scope:** WP6.2 T2 only; no T3/T4, live call, T1b, eligibility, result, or claim

## Decision required

V2 proved that T2's cost semantics are accepted but its exact canonical transition
family is not. Choose whether to accept the recommended ruling below. Acceptance
authorizes authorship and independent review of a content-addressed T2 authority
addendum only; it does not authorize runtime implementation.

## Existing authority that remains unchanged

- P-020: the existing project-wide `CommandService` remains the sole canonical writer.
- W2: historical schemas/records are never rewritten; breaking required-field changes
  use major version successors with explicit reader/reducer support.
- Accepted WP6.1 schema trees, catalogue, manifests, Stage-2 records, and T1a artifacts
  remain exact-byte immutable.
- The WP6.2 DAG remains `T1a -> T2 -> T3/T4 -> T1b -> T5 -> T6 -> T7 -> T8`.

## Recommended ruling

1. T2 uses the existing `CommandService`; no direct or second canonical writer is
   permitted.
2. Before implementation, author a WP6.2-specific authority addendum and identity
   manifest defining this minimal command/event family:
   - `IssueCostGrant` -> `CostGrantIssued`;
   - `AuthorizeProviderIssue` -> one atomic ordered batch containing
     `CostGrantReserved` then `ProviderCommandIssued`;
   - `RecordProviderReceipt` -> one atomic ordered batch containing
     `ProviderReceiptRecorded` then `CostGrantReconciled`.
3. `CostGrantReconciled` carries actual consumption and refund disposition. Replay of
   either accepted command returns the original receipt and emits no second reservation,
   issue, receipt, reconciliation, refund, or invocation.
4. The addendum names exact schema IDs/versions, reducers, projections, stream owners,
   idempotency keys, concurrency arbitration, expiry/revocation behavior, authority
   grants, receipts, and positive/negative tests. No implementation-defined alias is
   permitted.
5. New `SecretReference`, `CostGrant`, command, and event types begin at `1.0.0` under
   new WP6.2 identities. Existing `ProviderCommand` or `ProviderReceipt` required-field
   expansion uses explicit `2.0.0` successors; `1.1.0` is permitted only for genuinely
   optional backward-compatible additions. Existing `1.0.0` bytes remain unchanged.
6. The addendum receives a fresh independent design/contract review and Stephen's exact
   path/blob/hash acceptance before a T2 implementation brief is issued.

The two-event issue and receipt batches are load-bearing. They prevent a crash window
in which a cost reservation exists without a recorded provider issue, or a receipt is
recorded without deterministic cost reconciliation.

## Required addendum outputs

- one strict authority catalogue with exact command/event/reducer/projection rows;
- strict schemas and an identity manifest for the new/successor types;
- independent expected sets and binding tests;
- concurrency and replay negative controls;
- proof that accepted WP6.1/T1a bytes are unchanged;
- one review prompt and exact-subject acceptance packet.

## Copy-paste owner decision

```text
I accept the recommended WP6.2 T2 cost-grant authority and versioning ruling dated
2026-07-22. CommandService remains the sole canonical writer. Author the separately
content-addressed WP6.2 T2 authority addendum using the three command families and
versioning rules stated in the proposal, then obtain fresh independent review and
return the exact path/blob/hash acceptance packet to me. This acceptance authorizes
addendum authorship and review only; it does not authorize T2 implementation, T3/T4,
any live provider call, T1b, eligibility, result, or claim action.
```

## Alternative

If the recommended transition family is not accepted, provide a replacement that still
uses `CommandService`, preserves atomic reservation/issue and receipt/reconciliation,
names exact versioned identities, and leaves all accepted bytes unchanged. A direct
cost writer or in-place rewrite is not an admissible alternative under current
authority.
