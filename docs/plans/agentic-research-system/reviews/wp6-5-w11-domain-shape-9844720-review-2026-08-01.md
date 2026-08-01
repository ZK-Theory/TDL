# WP6.5 W11 domain-shape correction exact-subject acceptance review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, contract and authority,
  read-only
- Review task: `019fbe60-58b5-76d1-92c2-203ca32c1059`
- Review CWD: clean
  `C:\Users\steph\.codex\worktrees\d0e0\TDL`
- Reviewed subject: `98447202951ea4643435b223f3099b02376d4367`
- Direct parent: `72fdb8c34f43471667a28eddc02f4b9b9375c354`
- Tree: `77e8d1e6c814a50a58a2596fa6fc515de83f2f58`
- Full materialization base and merge base:
  `c84eb2aaf0890d36d3735d08a14169f4c50935cd`
- Full foundation boundary: exactly 65 paths
- Corrective delta: exactly 2 paths
- Review branch and remote candidate: equal to the reviewed subject
- Verdict: `accept_exact_subject`
- Findings: 0 Critical, 0 Major, 0 Minor

## Executive disposition

The exact subject closes the remaining malformed-domain failure contract at
the public W11 scorecard verifier seam. Domain containers, numeric endpoints,
and required-axis cardinality now fail with controlled `SchemaError` outcomes
through no-op and custom reference callbacks. Valid frozen domains continue to
pass, and unrelated callback failures are not swallowed.

The prior catalogue, dossier, registry-refresh, envelope, protected-byte, and
runtime-inertness closures remain intact. The exact subject is accepted as the
bounded W11 contract-foundation replacement candidate. PR #204 may
fast-forward to this exact SHA only. This verdict does not authorize a later or
different head, infer owner or Gate 6 acceptance, or waive current-head
external review coverage before merge.

## Exact identity and preserved boundary

The subject has the required parent, tree, and merge base. Its corrective delta
contains exactly:

- `tools/verify_w11_materialization.py`; and
- `tests/research_system/contracts/test_w11_contract_materialization.py`.

The complete foundation range remains exactly 65 paths. The independent review
branch and remote candidate both resolved to the reviewed subject, ancestry was
valid, and the reviewer finished with a clean worktree. The corrective delta
adds no production `research_system` path, W11 schema, accepted W11 source,
runtime binding, command/event path, producer, reducer, projection, CLI
dispatch, dossier admission, transition, migration, or cutover.

The protected W11 authority remains byte-identical:

- accepted commit `892d1d1650cdcf71d2a886318e174a18e11d5de0`;
- blob `f90729d0c42a0de98d064fac0824d1969c871c82`;
- raw SHA-256
  `65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70`;
- 185,214 LF-only bytes.

## Closure of the prior Minor finding

The exact subject introduces one bounded frozen-domain validator at the rubric
admission seam. It now:

- requires exactly one of `allowed_set` or `bounds` for every axis;
- requires `allowed_set` to be a non-empty JSON list and checks its values
  against the declared axis kind;
- requires numeric bounds to contain exactly `minimum` and `maximum`, with
  finite, non-boolean endpoints of the correct numeric kind and non-descending
  order; and
- requires `required_axis_ids` to be a non-empty list of unique, non-blank
  strings whose axes resolve in the rubric.

The validator runs after the supplied reference callback. It controls malformed
rubric content without masking unrelated exceptions raised by that callback.

## Validation evidence

Fresh review validation established:

- focused W11 contract suite: 63 passed;
- Ruff: passed;
- exact correction and foundation diff checks: passed;
- exact 65-path foundation envelope: passed;
- review branch, remote candidate, subject, parent, tree, ancestry, and clean
  status: matched;
- protected W11 commit, blob, raw hash, byte count, and LF-only identity:
  matched; and
- no runtime, production, schema, source, producer, reducer, projection, CLI,
  migration, or cutover residue.

Independent negative probes exercised:

- `allowed_set` values that were null, integer, string, dictionary, tuple, set,
  or empty;
- mixed `allowed_set` and `bounds`, and a missing domain;
- one-sided, string, boolean, non-finite, and inverted numeric bounds;
- empty, non-list, duplicate, non-string, and blank `required_axis_ids`;
- malformed scorecard axis values through the public schema-gated verifier;
  and
- both no-op and custom reference callbacks.

Every invalid public-path case produced a controlled `SchemaError`. Independent
positive probes for valid gate, integer-score, and registered-measure domains
passed through both callback routes. A deliberately unrelated callback
`RuntimeError` propagated unchanged, proving the correction does not convert or
hide failures owned by the caller.

## Integration boundary

`98447202951ea4643435b223f3099b02376d4367` is the only accepted replacement
subject from this review. PR #204 may be fast-forwarded to that exact commit,
after which its actual current head must receive the required external coverage
before merge. Any semantic change or different tree requires a new exact
subject and review.

This acceptance is limited to the inert W11 contract foundation. It is not
owner acceptance, Gate 6 acceptance, W11 runtime activation, Discovery runtime
completion, dossier admission, TDA-scale admission, or authorization to run
research.
