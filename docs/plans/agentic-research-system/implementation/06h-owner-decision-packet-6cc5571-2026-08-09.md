# WP6.1 06h G-RM-8 owner decision packet

**Decision packet date:** 2026-08-09

**Current-schema candidate:** `6cc557198f0fc0f624ffd834643ec2788f8d2711`

**Candidate tree:** `08b47eecd30e7fc4517c8924b3b6e7750ec8e750`

**Branch:** `codex/wp6-1-kan95-06h-acceptance`

**Decision status:** pending Stephen; this is not a 06h acceptance record

## Capability status

C2 remains **INCOMPLETE**. Commit `6cc5571` proves the current-schema identity,
producer, and append-accounting candidate. The exact remaining 06h functional
gap is an owner-selected, independently evidenced G-RM-8 historical-event
protocol. Until that branch is implemented, reviewed, and separately accepted,
`artefact.register` remains blocked and 06i Stage A must not be authored.

## Candidate evidence

- One immutable `RegisteredSchema` carries the raw bytes, raw-byte SHA-256,
  parsed contract, source path, schema ID, and schema version used by validation.
- Validation and exact identity resolution return the same object.
- The executable manifest accounts for all six current ledger append sites and
  all 86 active runtime bindings.
- The binding-row SHA-256 is
  `d82e45d75df6363c2ee9e5d99acb74ab1a9323034daf24a8a2be8710acfaa725`.
- The final targeted gate passed 55 tests in 157.69 seconds; changed-file Ruff
  checks and repository commit hooks passed.
- Core command tree `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea`, core event tree
  `154ffc4bdde82fe903718734687e7a62797b1f69`, and accepted owner-catalogue blob
  `1adc66921ee9c90d8786ff173748150922f1035e` are unchanged.
- The detailed evidence and two separately unresolved parent-baseline release
  fixtures are recorded in
  `06h-current-producer-and-evidence-record-2026-08-09.md`.

## Decision requested

Stephen must select exactly one protocol below. A selection is authority to
construct and prove that branch under KAN-95; it is not acceptance of the later
exact implementation subject.

### Option A: migrate

Required input evidence: read-only bound-store inventory including store
identity, ledger fingerprint, global positions, event/command/schema
identities, and exact pre-migration batch hashes.

Required implementation proof: content-addressed transformation, deterministic
genesis and incremental replay, projection equivalence outside provenance,
repeat-run no-op, ambiguity/drift rejection, immutable original store, and an
owner-approved atomic binding switch before activation.

### Option B: grandfather

Required input evidence: the same inventory plus an attributed decision binding
`store_identity`, `ledger_fingerprint`, and `max_global_position`.

Required implementation proof: only the exact bound historical set is admitted;
repeat replay is stable; any missing/changed pin or historical-set growth fails;
and a newly malformed event beyond the bound maximum is rejected. The existing
position-only replay parameter is insufficient and is not accepted evidence.

### Option C: no prior store

Required input evidence: independent discovery over every declared root, store
registry, and backup registry, plus operator attestation and a timestamped
zero-store result.

Required implementation proof: triple enforcement from genesis, same-empty-store
idempotence, discovery rerun before activation, hard stop on any prior store or
backup, and a planted historical-store fixture outside the first searched root
that makes the discovery assertion fail.

## Required response

Record one of the following exact decisions:

- `SELECT G-RM-8 MIGRATE for candidate lineage 6cc5571; authorize bounded construction and required evidence capture.`
- `SELECT G-RM-8 GRANDFATHER for candidate lineage 6cc5571; authorize bounded construction and required evidence capture.`
- `SELECT G-RM-8 NO-PRIOR-STORE for candidate lineage 6cc5571; authorize bounded discovery, attestation capture, and construction.`
- `DEFER G-RM-8 for candidate lineage 6cc5571; 06h and C2 remain owner-blocked.`

After the selected branch is implemented and all mandated controls pass, exactly
one fresh no-history independent reviewer may assess that complete exact subject.
Stephen's separate exact-subject acceptance follows that review; neither this
packet nor commit `6cc5571` constitutes acceptance.
