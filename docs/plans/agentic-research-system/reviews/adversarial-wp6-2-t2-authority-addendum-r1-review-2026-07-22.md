# WP6.2 T2 Authority Addendum R1 Adversarial Review

**Date:** 2026-07-22
**Verdict:** `rework_required`
**Lifecycle phase:** independent contract review, R1
**Workflow system:** standalone; no APM state or authority
**External-review owner:** Stephen; no agent-operated CodeRabbit activity

## Exact review subject

| Item | Identity |
|---|---|
| Candidate commit | `1144d6a6d0feb28473fb540d41ff03bff79eec24` |
| Review wrapper source | `69a0fee6171fc25f936c8e3e03343bfbd0338440` |
| Review branch | `review/ars-wp6-2-t2-authority-addendum-r1` |
| Reviewer task | `019f8a80-2e64-7633-acbd-f6fb7f12ef9b` |
| Reviewer final-response SHA-256 | `87cfdbdbe85153d862af99a5aeed1a1a091257b70053d9512cb4f9edf782ee6a` |

The reviewer inspected a clean detached checkout at the candidate commit and made no
repository writes. This document is the manager's durable rendering and triage of the
reviewer's task-final response. It does not replace that response or claim that the
manager performed the independent review; the response identity above binds the source.

## Validation evidence

The reviewer reported these successful checks against the exact candidate:

- 113 focused tests;
- Ruff;
- 102 contract gates;
- 12 generated-schema byte comparisons;
- 21 manifest leaves; and
- protected-byte checks.

The isolated WP6.3 failure was classified as pre-existing: the stale
`validate-topology` pin at
`.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml:412` has identical
relevant blobs in the candidate and baseline. It is outside this T2 review.

## Findings

### Critical

#### C1 - The bound receipt cannot prove the atomic events required before invocation

The addendum requires both event IDs in canonical order before transport invocation
(`design/09-wp6-2-t2-cost-grant-authority-addendum-2026-07-22.md:124`), and W2 requires
event IDs and positions (`design/02-task-event-and-artifact-schema.md:271`). The bound
strict receipt exposes only batch ID, stream version, and reason fields
(`.research-system/schemas/core/receipt.schema.json:12`). The invocation gate is
therefore unrepresentable.

**Manager disposition:** valid and blocking. Preserve the accepted Receipt 1.0 bytes
and authorize a strict Receipt 2.0 successor that can prove the ordered event batch.

#### C2 - Accepted events cannot rebuild the idempotency index

W2 requires accepted envelopes to retain the idempotency key and payload hash
(`design/02-task-event-and-artifact-schema.md:549`). Every candidate T2 event schema
omits both while forbidding additional fields
(`tests/research_system/contracts/wp6_2_t2_schema_materializer.py:574`). Canonical event
bytes therefore cannot prevent duplicate grants, reservations, invocations, receipts,
or reconciliations after an index rebuild.

**Manager disposition:** valid and blocking. Require both hashes in every T2 event
envelope and test reconstruction from canonical event bytes.

#### C3 - The secret-free boundary is declarative, not enforced

The addendum claims that no `SecretReference` field can carry credential text
(`design/09-wp6-2-t2-cost-grant-authority-addendum-2026-07-22.md:168`), but `resolver_id`
accepts any non-empty string
(`tests/research_system/contracts/wp6_2_t2_schema_materializer.py:115`). An adversarial
probe placed synthetic credential material there. Pre-issue evidence is only an untyped
ID/hash (`tests/research_system/contracts/wp6_2_t2_schema_materializer.py:528`), while
mutation tests validate fabricated
counters instead of scanning the eight producer seams
(`tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py:42`).

**Manager disposition:** valid and blocking. Constrain resolver identity, add a typed
pre-issue evidence manifest, and require evidence-producing recursive probes over the
actual eight seams. Aggregate self-attestation is insufficient.

#### C4 - Exact writer targets and authority subjects are not enforced

`IssueCostGrant` requires one identical new stream at version zero
(`design/09-wp6-2-t2-cost-grant-authority-addendum-2026-07-22.md:90`), but target,
write-set stream, payload ID, and expected version are independently constrained
(`tests/research_system/contracts/wp6_2_t2_schema_materializer.py:417`). A probe accepted
three different grant IDs and expected version `7`. `RecordProviderReceipt` also omits
CostGrant revision/hash and reservation revision/hash from its purportedly exact subject
(`.research-system/contracts/wp6-2-t2-cost-grant-authority-catalogue.yaml:311` and
`tests/research_system/contracts/wp6_2_t2_schema_materializer.py:550`).

**Manager disposition:** valid and blocking. Add semantic relational validation and
negative fixtures; extend the receipt-recording authority subject to bind the exact
grant and reservation revisions and hashes.

### Major

#### M1 - Cost reconciliation is not tied to rates or token ceilings

CostGrant records rate evidence
(`tests/research_system/contracts/wp6_2_t2_schema_materializer.py:151`), but validation
checks only token addition and refund subtraction
(`tests/research_system/contracts/wp6_2_t2_authority_validation.py:374`). It accepted 150
actual tokens, zero consumed cost, and a full refund.

**Manager disposition:** valid defect exposing an authority gap. Token ceilings must be
enforced, but the exact integer cost formula, rounding, and zero-rate policy require an
owner ruling before remediation.

#### M2 - The ProviderCommand/ProviderReceipt 2.0 successors are incomplete against W7

W7 requires control-position, routing, permission, timing, transport, tool/action,
output, retry, and W8 evidence
(`design/07-runtime-adapters-and-policy-parity.md:160`). The strict v2 command and receipt
required sets omit substantial portions
(`.research-system/schemas/wp6-2-t2/provider-command-v2.schema.json:15` and
`provider-receipt-v2.schema.json:15`).

**Manager disposition:** valid and blocking. The successors need a complete normative
W7 crosswalk and must represent every required field or a W7-permitted typed inability.

#### M3 - Canonical identifier syntax is not enforced

W2 requires lowercase UUIDv7 identifiers
(`design/02-task-event-and-artifact-schema.md:127`). Candidate schemas accept arbitrary
hex-and-hyphen suffixes
(`tests/research_system/contracts/wp6_2_t2_schema_materializer.py:23`), and positive fixtures use
values such as `sref_abc`
(`tests/research_system/contracts/test_wp6_2_t2_authority_contract.py:83`).

**Manager disposition:** partially valid as stated and blocking in effect. UUIDv7 suffix
enforcement is required. The accepted W7 `pcmd_` and `prcp_` identities are explicit
scoped exceptions to P-007's general three-letter-prefix form and must not be renamed;
new T2 first-class identities must use three-letter prefixes.

### Minor

No Minor findings.

## Remediation boundary

The rejected candidate remains immutable review history. No runtime implementation,
live provider call, T3/T4, T1b, eligibility, result, claim, or accepted-artifact rewrite
is authorized. One bounded contract/addendum remediation cycle may begin only after
Stephen accepts the separately content-addressed P-038 proposal. The new candidate must
then receive a fresh independent R2 review with no inherited author conversation.
