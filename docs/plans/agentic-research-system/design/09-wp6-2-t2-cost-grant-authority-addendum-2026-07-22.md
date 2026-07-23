# WP6.2 T2 Cost-Grant Authority Addendum

**Status:** proposed candidate pending fresh independent static R3 review and
Stephen's exact-hash acceptance. Runtime implementation is not authorized.

## 1. Controlling authority and scope

This addendum closes the final T2 contract-remediation cycle under P-039. Its
controlling exact sources are:

- accepted P-039 proposal at manager commit
  `1301d8a5f089d27270c36b216967000a35472efc`, blob
  `1c6703b37579a0ffa35bfec0f9cccc7180a37f79`, raw SHA-256
  `959ebeafa67368ffc87592134fd9c0caf385b4b562278789273563844295492f`;
- P-039 acceptance registration
  `826ce6ad2cd83cbfc7a0db85b9ad068d91765b84`;
- corrected R2 report at commit
  `a10de8df9e0be8b381e6257aa761d8d8cea2506b`, blob
  `f93c030d59b7df74e08d4a960f28045a6c9fbec2`, raw SHA-256
  `c2bb533d05d40f6720709406d98f096b288894c0eb0e044b44edcd3fc376cf8b`;
- manager triage at commit
  `1301d8a5f089d27270c36b216967000a35472efc`, blob
  `0a8992239165d678439ac1994184cd796006e122`, raw SHA-256
  `0e0314956f3b961e23e128bfb09f4dab420111d96da14f2f1287cb0974402373`.

P-037, P-038, W2, W7, W8, and implementation plan 06b remain applicable
only as amended by P-039. P-039 controls every conflict about C3, M2, effort,
or evidence timing.

This candidate is contract-only. It does not implement provider calls,
credential resolution, security tooling, runtime dispatch, T3/T4, T1b,
eligibility, results, claims, or publication.

## 2. Closed transition family

The sole canonical writer is
`research_system.command.service.CommandService`. T2 defines exactly these
ordered transitions:

1. `IssueCostGrant -> [CostGrantIssued]`;
2. `AuthorizeProviderIssue -> [CostGrantReserved, ProviderCommandIssued]`;
3. `RecordProviderReceipt -> [ProviderReceiptRecorded, CostGrantReconciled]`.

Each accepted command publishes its entire event set in one atomic batch and
in the order above. A partial, reordered, or additional event set is invalid.
Rejections and conflicts publish zero events and invoke no provider. A
duplicate returns the original accepted outcome binding with zero new grant,
reservation, issue, invocation, provider-receipt, reconciliation, or refund
effect.

## 3. Receipt 2.0 is the complete C1 proof

`ars://core/receipt/v2` is a strict successor; Receipt 1.0 bytes remain
immutable. Receipt 2.0 itself, together with its mandatory semantic validator,
enforces all of the following without relying on an external event-count
claim:

- the exact event count for the named T2 command;
- unique, contiguous, zero-based `transaction_position` values;
- the canonical command-specific event order;
- unique lowercase UUIDv7 `evt_` event identities;
- permitted lowercase UUIDv7 `cgr_` or `pcmd_` stream identities according to
  event type;
- `resulting_stream_version = prior_stream_version + 1` for every event;
- accepted-only event batches and status-specific zero-event rules;
- for a duplicate, exact equality to the original accepted receipt for
  command identity and type, idempotency hash, payload hash, batch identity,
  complete ordered event proof, outcome binding, reason, and preconditions,
  plus the exact original accepted receipt hash and zero new effects.

## 4. Event-derived W2 idempotency reconstruction

Every one of the five T2 event envelopes carries:

- `command_id`;
- `actor_id`;
- `authority_scope`;
- `command_type`;
- the logical `idempotency_key`;
- `idempotency_key_hash = SHA-256(UTF-8(idempotency_key))`; and
- the canonical command `payload_hash`.

Reconstruction keys the exact W2 tuple
`(actor_id, authority_scope, command_type, idempotency_key)` and binds it to
`(command_id, payload_hash)`. Re-encountering a tuple with a different command
identity or a different payload hash is `idempotency_conflict`. Canonical event
effects are unique, so replay cannot create a second grant, reservation,
provider command, provider receipt, or reconciliation.

## 5. Unconditional authority triples

Every applicable Task, Dispatch, Attempt, grant, reservation, provider
command, provider receipt, and SecretReference subject is carried as an
unconditional `<stem>_id`, `<stem>_revision`, `<stem>_hash` triple. The semantic
validator compares every triple with an independently owned expected record;
presence alone is insufficient.

The exact command surfaces are:

- `IssueCostGrant`: CostGrant, ResourceGrant, Task, Dispatch, Attempt,
  ProviderCommand, and SecretReference triples;
- `AuthorizeProviderIssue`: those seven triples plus the reservation triple;
- `RecordProviderReceipt`: CostGrant, ResourceGrant, Task, Dispatch, Attempt,
  ProviderCommand, ProviderReceipt, reservation, and SecretReference triples.

Write-set stream identities, target identity, expected versions, deterministic
reservation identity, event stream identities, and resulting versions are
checked relationally against the same command and independently supplied
records.

## 6. Opaque SecretReference boundary

`ars://wp6-2/t2/secret-reference` is strict opaque metadata. It carries a
lowercase UUIDv7 identity, revision and content hash, provider and credential
class metadata, typed resolver identity metadata, allowed scope, expiry,
revocation binding, and an opaque-metadata redaction declaration. It has no
raw credential field and authorizes no credential resolution.

The T2 boundary ends at strict opaque metadata and exact binding. It defines
no credential payload, resolution operation, security tooling, or external
security service.

## 7. Mandatory composed authority-cost gate

One mandatory semantic gate, `validate_t2_authority_cost_gate`, composes:

1. strict JSON Schema validation of the CostGrant, reservation payload,
   ProviderReceipt 2.0 subset, and reconciliation payload;
2. exact integer token totals and ceilings;
3. integer-only cost calculation
   `ceil(input_tokens * input_rate / 1_000_000) +
   ceil(output_tokens * output_rate / 1_000_000)`;
4. exact refund arithmetic `reserved - consumed` and disposition;
5. equality of reserved quantities across reservation and reconciliation;
6. equality of actual and cost quantities across provider receipt and
   reconciliation; and
7. exact equality of currency plus rate-evidence ID, revision, and hash across
   CostGrant, reservation, provider receipt, and reconciliation.

Metered evidence requires positive integer rates. An explicitly authorized
zero-cost record requires zero rates and an exact authority triple. This is a
contract gate, not a new accounting subsystem.

## 8. Provider successors: exact T2 subset only

ProviderCommand 2.0 and ProviderReceipt 2.0 are labeled
`t2_authority_cost_subset`. Their predecessors remain immutable.

ProviderCommand 2.0 validates only the strict T2 groups `provider_binding`,
`w2_binding`, `authority_binding`, `payload_binding`, `permission_binding`,
`accounting_ceiling`, and `lifecycle`, together with its identity and revision
hash.

ProviderReceipt 2.0 validates only the strict T2 groups `command_binding`,
`provider_binding`, `authority_binding`, `delivery_binding`, `timestamps`,
`token_accounting`, `terminal_outcome`, `outputs`, `lifecycle_evidence`,
`evidence_disposition`, and `completeness`, together with its identity and
revision hash.

Every W7 field or runtime assurance outside this exact subset is deferred to
T3/T4; this candidate makes no broader provider-contract claim.

## 9. Exact protected membership and construction independence

`.research-system/contracts/wp6-2-t2-protected-membership.yaml` is the
normative predecessor-membership contract. Against accepted baseline
`69a0fee6171fc25f936c8e3e03343bfbd0338440`, it enumerates exactly 220 paths,
each with its Git blob identity and SHA-256 of raw Git blob bytes. Its sorted
`path|blob|raw-sha` aggregate is
`74c911466203f64277b2189c5fc2455c5644fa24818193cac33c19bed4e5c84c`.

The expected set is derived independently from the accepted baseline's exact
core, WP6.1, T1a, and provider-1.0 path rules. Validation recomputes membership,
count, every baseline blob/raw identity, the aggregate, and every live HEAD
identity. Omission, addition, dependency coupling, or any byte mutation is a
hard failure. The materializer does not import or construct the validator's
expected set, and the validator does not import the materializer.

The R3 crosswalk independently maps C1, C2, C3, C4, M1, M2, M3, and I1 to
authority references, schema properties, semantic validators, and decisive
positive/negative tests. Its expected literals are separately authored and
omission-sensitive.

## 10. Versioning and lifecycle

All new T2 command, event, CostGrant, and SecretReference identities are
1.0.0. Receipt, ProviderCommand, and ProviderReceipt successors are 2.0.0.
Major-version dispatch is exact. Historical schemas and accepted artifacts are
never rewritten.

This candidate remains proposed until a fresh static R3 review identifies the
exact candidate commit/tree and Stephen accepts the exact hash. Acceptance
would authorize only the contract fixed here; runtime work remains separately
gated.
