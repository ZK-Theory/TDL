# WP6.5 W11 contract-foundation semantic remediation exact-subject review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, contract and authority,
  read-only
- Review CWD: clean detached
  `C:\Users\steph\.codex\worktrees\c6e1\TDL`
- Reviewed subject: `fb61ca152138e6f46c5388b47325efec28e60316`
- Direct parent: `21e91d926ca3964f46c45024796cb1c16532ee00`
- Tree: `229a730c07ec97e372580ac05a5696e64980f976`
- Full materialization base and merge base:
  `c84eb2aaf0890d36d3735d08a14169f4c50935cd`
- Full boundary: 65 paths
- Corrective delta: 20 paths
- Verdict: `rework_required`
- Findings: 0 Critical, 3 Major, 1 Minor

## Executive disposition

The exact subject preserves the accepted W11 source bytes and the inert
production boundary, and its focused tests, integration identity check, Ruff,
and diff check pass. Those green checks do not override the fresh adversarial
probes: the actual inert verification seam still accepts an incomplete or
identity-duplicated catalogue, a coordinated duplicate dossier expected-set
row with recomputed aggregates, and stale same-root schema state hidden by the
registry cache. A malformed rubric can also escape the public helper as a raw
`KeyError`.

The subject is therefore quarantined. It is not PR-, merge-, activation-, or
completion-authorized, and it is not evidence that KAN-58 is complete. The
remaining correction must be produced as a new exact subject and receive a
fresh independent exact-subject review. It must remain an inert contract and
catalogue delivery; no runtime binding, handler, ledger event, reducer,
projection, OR-140 execution, dossier admission, transition, migration, or
cutover is authorized.

## Exact identity and preserved boundary

The review bound the candidate to subject
`fb61ca152138e6f46c5388b47325efec28e60316`, direct parent
`21e91d926ca3964f46c45024796cb1c16532ee00`, and tree
`229a730c07ec97e372580ac05a5696e64980f976` in the clean detached review CWD.
The full 65-path materialization boundary and 20-path corrective delta both
resolve from the exact merge base
`c84eb2aaf0890d36d3735d08a14169f4c50935cd`.

The corrective delta consists of 18 W11 schema files, the focused contract
test, and the inert verifier. It adds no production `research_system` path and
does not activate W11 in the runtime registry or any command/event path.

The protected W11 authority remained byte-identical:

- path
  `docs/plans/agentic-research-system/design/11-portfolio-and-discovery-lifecycle.md`;
- commit `892d1d1650cdcf71d2a886318e174a18e11d5de0`;
- blob `f90729d0c42a0de98d064fac0824d1969c871c82`;
- raw SHA-256
  `65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70`;
- 185,214 LF-only bytes.

## Validation evidence

```text
Focused W11 contract suite: 36 passed
Integration identity check: passed
Ruff: passed
git diff --check: passed
Protected W11 blob, raw bytes, and SHA-256: unchanged
Production runtime boundary: inert
Fresh adversarial probes: 3 Major and 1 Minor remained reachable
```

The passing committed checks establish useful positive coverage, but none
rejects the direct semantic and lifecycle probes below. The probe results are
therefore controlling for this verdict.

## M-01 - catalogue admission does not prove exact closure or owner identity

The catalogue verifier accepts a one-row schema catalogue even though the W11
foundation requires exact closure over the 61-family/schema set. It also
accepts duplicate logical and schema identities across the owner contract
rows. Per-list shape, the 81 owner-row identifiers, and literal test identities
do not establish catalogue completeness or unique owner identity.

Admission must require exact equality with the required 61-family/schema
closure and must reject duplicate owner-row `logical_key` and `schema_id`
values. Decisive negatives must exercise both an incomplete one-row catalogue
and distinct owner rows that reuse each identity.

## M-02 - recomputed dossier aggregates admit duplicate expected-set rows

The dossier verifier checks family counts and recomputes family and closure
hashes from the supplied row multisets. A coordinated mutation can duplicate
an expected-set row and recompute all affected counts and hashes; that mutated
dossier still passes. Aggregate self-consistency therefore does not prove the
row-level exact expected set.

Each dossier family must enforce its exact row identity and reject duplicates
before count or hash aggregation. A decisive negative must duplicate one row,
recompute every affected aggregate consistently, and still be rejected at the
row-level closure seam.

## M-03 - cached registry state hides same-root schema changes

The verifier rechecks the root path but returns an `lru_cache`d
`SchemaRegistry` keyed only by that path. A schema added late or replaced under
the same root can therefore be absent from, or stale within, later
verifications even though the caller supplied the current root.

Every verification must recursively re-enumerate the current schema root and
reload it, or bind reuse to a complete current-root fingerprint that changes
for additions, removals, replacements, content changes, and path changes.
Decisive tests must verify both a late-added schema and a replaced schema under
one unchanged root path.

## m-01 - malformed rubric leaks `KeyError` from the public helper

When `verify_w11_document` receives a rubric reference document without
`axis_definitions` and a no-op validation callback, rubric traversal raises a
raw `KeyError`. A public verification helper must not expose an incidental
mapping exception for malformed or invalid caller configuration.

The public seam must reject this case with a controlled `SchemaError` or
`ConfigurationError`, with a decisive test covering the no-op-callback path.

## Required bounded correction

The new exact subject must:

1. require exact 61-family/schema catalogue closure and unique owner logical
   and schema identities;
2. reject duplicate dossier expected-set rows before aggregate validation,
   including when all derived counts and hashes are recomputed;
3. re-enumerate, reload, or completely fingerprint the current recursive
   schema root on every verification;
4. convert malformed-rubric public-helper failures into a controlled
   `SchemaError` or `ConfigurationError`;
5. add direct negative tests for all four reachable cases; and
6. preserve the accepted W11 source bytes, the exact materialization-envelope
   controls, and the inert production boundary.

After that bounded correction, a fresh independent exact-subject review is
required. Until then, `fb61ca152138e6f46c5388b47325efec28e60316`
remains quarantined.
