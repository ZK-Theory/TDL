# WP6.5 W11 domain-shape remediation exact-subject review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, contract and authority,
  read-only
- Review task: `019fbe42-9d5f-7ac2-94c0-9e6a8976f02b`
- Review CWD: clean
  `C:\Users\steph\.codex\worktrees\54d5\TDL`
- Reviewed subject: `72fdb8c34f43471667a28eddc02f4b9b9375c354`
- Direct parent: `3e4462285f3a256dc3c57105898225e86236a78c`
- Tree: `3f667d1afb827a1f057546066c6e8ffe97686563`
- Full materialization base and merge base:
  `c84eb2aaf0890d36d3735d08a14169f4c50935cd`
- Full foundation boundary: exactly 65 paths
- Corrective delta: exactly 2 paths
- Remote candidate: equal to the reviewed subject
- Verdict: `rework_required`
- Findings: 0 Critical, 0 Major, 1 Minor

## Executive disposition

The exact subject converts the previously required malformed rubric-field
cases into controlled `SchemaError` outcomes while preserving the accepted W11
source bytes, the complete foundation envelope, and the runtime-inert boundary.
Its focused suite and exact identity checks pass.

The custom/no-op reference-validation route still does not validate the full
domain shape. Malformed `allowed_set`, `bounds`, and required-axis cardinality
can therefore escape as raw `TypeError` or be accepted silently. The subject
remains quarantined and is not PR-, merge-, activation-, or
completion-authorized. PR #204 must remain frozen. A minimally corrected new
exact subject requires a fresh independent exact-subject review.

## Exact identity and preserved boundary

The subject has the required parent, tree, and merge base. Its corrective delta
contains exactly:

- `tools/verify_w11_materialization.py`; and
- `tests/research_system/contracts/test_w11_contract_materialization.py`.

The complete foundation range remains exactly 65 paths. The remote candidate
branch resolved to the exact reviewed subject, and the independent reviewer
finished with a clean worktree. No production `research_system` path, W11
schema, accepted W11 source, runtime binding, command/event path, producer,
reducer, projection, CLI dispatch, dossier admission, transition, migration,
or cutover is added.

The protected W11 authority remains byte-identical:

- accepted commit `892d1d1650cdcf71d2a886318e174a18e11d5de0`;
- blob `f90729d0c42a0de98d064fac0824d1969c871c82`;
- raw SHA-256
  `65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70`;
- 185,214 LF-only bytes.

## Validation evidence

Fresh review validation established:

- the originally required malformed-field probes return controlled
  `SchemaError` outcomes;
- the focused W11 contract suite passes all 47 tests;
- the exact 65-path subject envelope resolves and passes;
- the protected W11 commit, blob, raw hash, byte count, and LF-only identity
  remain exact;
- the exact correction remains limited to the verifier and its focused tests;
  and
- no runtime, source, schema, or activation surface changed.

These positive results establish the bounded correction already made. They do
not override the independently reachable malformed-domain cases below.

## m-01 - malformed rubric domains remain uncontrolled

The public scorecard verifier's custom/no-op callback route still trusts domain
containers and cardinality after its new axis-shape checks:

- around `tools/verify_w11_materialization.py:481` and line 539,
  `allowed_set` is not required to be a non-empty list and is not made mutually
  exclusive with `bounds`;
- `allowed_set` values of `null` or an integer raise raw `TypeError`, while
  tuple or set values can be accepted silently;
- around line 545, string-valued bound endpoints can reach a raw comparison
  `TypeError`; and
- around lines 492-496, `required_axis_ids=[]` can pass silently.

These paths are reachable when a custom or no-op reference validator does not
perform the schema validation that the helper itself otherwise relies upon. A
public verification seam must reject malformed domain structure and invalid
required-axis cardinality with a controlled `SchemaError` or
`ConfigurationError`; it must not expose incidental iteration/comparison
exceptions or accept alternate container types.

## Required bounded correction

The next exact subject must add only the controlled domain/cardinality checks
and decisive negative cases required for the reachable routes above:

1. require `allowed_set` to be a non-empty list when present;
2. reject an axis that supplies both `allowed_set` and `bounds`;
3. validate bound endpoint types before comparing them;
4. require `required_axis_ids` to be a non-empty list of valid axis IDs; and
5. prove each malformed route returns a controlled configuration/schema error
   through the custom/no-op callback seam.

The correction must preserve the closed catalogue, dossier, registry-refresh,
envelope, protected-byte, and runtime-inertness controls. It must not add W11
runtime behavior, change accepted W11 source/schema bytes, or update PR #204
before a fresh exact-subject review accepts the replacement candidate.

No acceptance or integration is authorized for
`72fdb8c34f43471667a28eddc02f4b9b9375c354`.
