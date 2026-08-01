# WP6.5 W11 contract-foundation verifier remediation exact-subject review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, contract and authority,
  read-only
- Review task: `019fbe1f-8e9c-70e1-be29-a86b271d80f2`
- Reviewed subject: `3e4462285f3a256dc3c57105898225e86236a78c`
- Direct parent: `fb61ca152138e6f46c5388b47325efec28e60316`
- Tree: `492250abc28ab651d592a8f124b23409fa8f963f`
- Full materialization base and merge base:
  `c84eb2aaf0890d36d3735d08a14169f4c50935cd`
- Full foundation boundary: exactly 65 paths
- Corrective delta: exactly 3 paths
- Verdict: `rework_required`
- Findings: 0 Critical, 0 Major, 1 Minor

## Executive disposition

The exact subject closes the three prior Major findings: catalogue admission
now proves exact 61-family closure and unique logical/schema identities,
coordinated duplicate dossier rows are rejected, and same-root schema additions
and replacements are observed. The exact 65-path foundation boundary,
protected W11 bytes, and inactive runtime boundary also remain intact.

One public-helper failure contract remains incomplete. The custom/no-op rubric
validation seam handles a missing `axis_definitions` field, but other malformed
axis shapes still escape as raw `KeyError` or `TypeError`. The subject therefore
remains quarantined and is not PR-, merge-, activation-, or
completion-authorized. A narrowly corrected new exact subject requires fresh
independent review.

## Exact identity and preserved boundary

The subject has the required parent, tree, and merge base. Its corrective delta
contains exactly:

- `.research-system/schemas/contracts/w11/w11-schema-catalogue-content.schema.json`;
- `tests/research_system/contracts/test_w11_contract_materialization.py`; and
- `tools/verify_w11_materialization.py`.

The complete foundation range remains exactly 65 paths. No production
`research_system` path, runtime schema binding, command/event path, handler,
ledger event, reducer, projection, OR-140 execution, dossier admission,
transition, migration, or cutover is added.

The protected W11 authority remains byte-identical:

- blob `f90729d0c42a0de98d064fac0824d1969c871c82`;
- raw SHA-256
  `65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70`;
- 185,214 LF-only bytes.

## Validated closures and evidence

Fresh review validation established:

- exact 61-family catalogue closure;
- unique catalogue and owner logical/schema identities;
- rejection of a coordinated duplicate dossier row with recomputed aggregates;
- same-root late-add and replacement schema visibility;
- exact 65-path foundation-envelope closure;
- unchanged protected W11 bytes and SHA-256; and
- no W11 runtime activation.

```text
Focused W11 contract suite through the shared virtual environment: 41 passed
Candidate review worktree changes after validation: none
```

These positives close the prior Major findings but do not override the
remaining malformed-axis probes below.

## m-01 - malformed rubric axes still leak uncontrolled exceptions

The custom/no-op callback path through the public rubric helper still assumes
several axis fields and container shapes after reference resolution. Although
the newly authored negative near
`test_w11_contract_materialization.py:1181` covers a missing
`axis_definitions` field, independent probes found that a missing or unknown
`axis_kind`, a missing `required_axis_ids`, and non-list axis structures can
still raise raw `KeyError` or `TypeError` around
`tools/verify_w11_materialization.py:453`.

A public verification seam must translate every malformed rubric-axis shape
into a controlled `SchemaError` or `ConfigurationError`. Raw mapping, lookup,
iteration, and container-type exceptions must not escape through a custom or
no-op reference validator.

## Required bounded correction

The next exact subject must add focused negative cases for missing and unknown
`axis_kind`, missing `required_axis_ids`, and non-list axis structures, and must
return a controlled `SchemaError` or `ConfigurationError` for each case. The
correction must not widen scope: preserve the now-closed catalogue, dossier,
registry-refresh, envelope, protected-byte, and runtime-inertness controls.

No integration or acceptance is authorized until a fresh independent review
accepts the corrected exact subject.
