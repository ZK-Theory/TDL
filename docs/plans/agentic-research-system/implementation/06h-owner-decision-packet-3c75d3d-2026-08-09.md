# WP6.1 06h G-RM-8 live-main owner decision packet

**Decision packet date:** 2026-08-09

**Live-main current-schema candidate:** `3c75d3d102d8fe14746b19662005e88c4b776ffa`

**Candidate tree:** `01625ae2e64a90981f0721c9bb7b35bf7d3abe25`

**Accounted base:** `9736c900fd4f72e84b2208eeff0dcfb2a2b44106`

**Branch:** `codex/wp6-1-kan95-06h-reconcile-9736c90`

**Historical candidate preserved:** `6cc557198f0fc0f624ffd834643ec2788f8d2711`

**Decision status:** Stephen selected G-RM-8 `GRANDFATHER`; bounded construction
is active, and this remains distinct from later exact-subject acceptance

## Capability status

C2 remains **INCOMPLETE**. Candidate `3c75d3d` proves the reconciled live-main
G-RM-9/current-schema identity, current producer, and append-accounting subject.
Stephen selected G-RM-8 `GRANDFATHER`; construction and exact-prefix evidence
are now active. The remaining 06h gap is the final post-PR #229 binding census,
one fresh no-history review of the complete exact subject, and Stephen's later
exact-subject acceptance. `artefact.register` remains blocked and 06i Stage A
must not be authored.

## Candidate evidence

- One immutable `RegisteredSchema` carries the raw bytes, raw-byte SHA-256,
  parsed contract, source path, schema ID, and schema version used by
  validation; validation and exact identity resolution return the same object.
- The executable manifest accounts for all six current ledger append sites and
  all 112 active runtime bindings at PR #222 merge `9736c900`.
- The binding-row SHA-256 is
  `4b7a5b1813415f360e12d40341320444fc13334a6cb78690effd0695eb4b2b6a`.
- The exact candidate-head identity/append/public-path set passed 9 tests in
  16.15 seconds. The larger same-content pre-commit gate passed 55 tests in
  185.70 seconds; its exact-head repeat timed out without a terminal summary
  and remains unresolved rather than being called green.
- Real PR #222 artefact-authority and W3 context positives passed 2 tests in
  15.28 seconds.
- Core command tree `8a86a0c4921343e6a3afca3f491fad33e9a8a10f`, core event tree
  `058c1d5ddcb9d249916977f12b11768b6d15de0f`, and accepted owner-catalogue blob
  `1adc66921ee9c90d8786ff173748150922f1035e` are unchanged.
- Two release-publication failures were reproduced identically at the exact
  parent and candidate and remain explicitly classified as parent baseline.
- The detailed evidence, exact commands, bounded memory measurement, and
  non-reconstructible historical boundary are recorded in
  `06h-current-producer-and-evidence-record-9736c90-2026-08-09.md`.

## Decision requested

Stephen must select exactly one protocol below. A selection authorizes only the
bounded construction and evidence work under KAN-95; it is not acceptance of
the later exact implementation subject.

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
position-only replay parameter remains insufficient and is not accepted
evidence.

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

- `SELECT G-RM-8 MIGRATE for candidate lineage 3c75d3d; authorize bounded construction and required evidence capture.`
- `SELECT G-RM-8 GRANDFATHER for candidate lineage 3c75d3d; authorize bounded construction and required evidence capture.`
- `SELECT G-RM-8 NO-PRIOR-STORE for candidate lineage 3c75d3d; authorize bounded discovery, attestation capture, and construction.`
- `DEFER G-RM-8 for candidate lineage 3c75d3d; 06h and C2 remain owner-blocked.`

After the selected branch is implemented and all mandated controls pass,
exactly one fresh no-history independent reviewer may assess that complete exact
subject. Stephen's separate exact-subject acceptance follows that review;
neither this packet nor candidate `3c75d3d` constitutes acceptance.

## Recorded response

Stephen recorded exactly:

`SELECT G-RM-8 GRANDFATHER for candidate lineage 3c75d3d; authorize bounded construction and required evidence capture.`

The attributed, content-addressed decision is
`06h-g-rm-8-grandfather-decision-3c75d3d-2026-08-09.json`, decision SHA-256
`07eac8199ffb48ceea6e0d235f0f2193fac4ebaae4b1e3340e39899e59927c74`.
The bounded construction and real-Control proof are recorded in
`06h-g-rm-8-grandfather-evidence-3c75d3d-2026-08-09.md`.
