# WP6.5 W11 contract-foundation r2 remediation exact-subject review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, contract and authority, read-only
- Reviewed branch: `codex/review-kan58-w11-contract-f0b075e`
- Reviewed subject: `f0b075eb7147da90b8df326688fcd0243769fedf`
- Direct parent: `9d2b0246649c4c61657d15500fa1bc5c4f3fb236`
- Tree: `124b329328308133e04fba630e2ad43fa6293a62`
- Full materialization range: 65 paths from
  `c84eb2aaf0890d36d3735d08a14169f4c50935cd`
- Corrective range: 6 paths from
  `9d2b0246649c4c61657d15500fa1bc5c4f3fb236`
- Verdict: `rework_required`
- Findings: 0 Critical, 2 Major, 0 Minor

## Executive disposition

The remediation closes the W11 semantic-admission findings from the prior
review. It removes the W11 validator from production runtime Python, restores
ordinary inactive-catalogue behavior, verifies all 81 literal owner rows and
their typed references, and preserves the accepted W11 source bytes. The
external final-subject envelope also verifies successfully through the real
CLI.

Two exact-subject controls remain incomplete. The committed focused test still
claims the prior `9d2b024...` subject, tree, and 66-path range rather than this
65-path final range, and the verifier does not explicitly require its base to
be an ancestor of its subject. The subject is therefore quarantined and is not
PR- or merge-authorized or evidence that KAN-58 is complete. The next fresh
exact subject should change only these envelope controls and their decisive
tests; it must not reintroduce production runtime validation or change the
accepted W11 source bytes.

## Exact identity and preserved evidence

The reviewer confirmed the reviewed branch, subject, direct parent, tree,
65-path full range, six-path corrective delta, clean substantive status, and
clean `git diff --check` result. The full range contains no net production
`research_system` path. No runtime handler, binding, ledger event, reducer,
projection, OR-140 import, dossier admission, transition, migration, or cutover
is introduced.

The accepted W11 authority remained exact:

- commit `892d1d1650cdcf71d2a886318e174a18e11d5de0`;
- blob `f90729d0c42a0de98d064fac0824d1969c871c82`;
- raw SHA-256
  `65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70`;
- 185,214 LF-only bytes.

Validation evidence:

```text
Focused W11 contract suite: 24 passed
Ruff: passed
External final-subject envelope through the real CLI: accepted
Generic inactive catalogue resolution and validation: passed as expected
Runtime validate_active for W11: rejected as expected
W11 active bindings or runtime references: none
```

All owner rows, row/test tuples, lineage rules, complete rubric-axis equality,
typed references, malformed-input controls, and semantic mutations behaved as
required. Generic `SchemaRegistry` resolution and validation of an inactive
catalogue schema is expected and is not runtime authority; the active-binding
seam correctly rejects W11.

The named schema-registry regression cases timed out after 120 seconds without
output. They are inconclusive and are not counted as a pass.

## M-01 - the committed focused test is pinned to the prior subject

The focused test still embeds `9d2b024...`, its tree, and the earlier 66-path
range. It therefore does not durably verify the reviewed
`f0b075eb7147da90b8df326688fcd0243769fedf` subject, tree
`124b329328308133e04fba630e2ad43fa6293a62`, or its 65-path full range. The
independent external envelope did verify the final subject, but that evidence
does not make the stale committed assertion correct.

The correction must remove the stale self-subject claim. The reusable verifier
and its unit tests should prove exact envelope behavior against an externally
supplied immutable subject/tree/path manifest or a stable synthetic Git DAG;
the independent review record must then bind the actual final commit, because
a commit cannot contain its own final Git identity without self-reference.

## M-02 - ancestry is not an explicit envelope invariant

`verify_subject_envelope` checks object and path identities but does not assert
that `base_commit` is an ancestor of `subject_commit`. A reachable
non-ancestor probe was rejected only because its resulting manifest was empty,
not because the relationship itself was forbidden.

The verifier must perform an explicit Git ancestry check before accepting the
range and raise the typed validation failure for a non-ancestor base. A
decisive test must construct or identify a non-ancestor pair with otherwise
plausible envelope fields so rejection cannot be attributed to an incidental
empty or mismatched manifest.

## Required bounded correction

The fresh corrective subject must:

1. remove the stale `9d2b024...` subject/tree/66-path assertion from the
   focused test and use a non-self-referential exact-envelope test model;
2. make base-to-subject ancestry an explicit verifier invariant and add a
   decisive non-ancestor negative;
3. preserve the working external final-subject verification seam so a fresh
   independent reviewer can record the new exact subject, tree, and range;
4. preserve all passing W11 semantic, inertness, and inactive-binding controls;
   and
5. preserve the accepted W11 source and all existing schema bytes.

After that correction, a fresh independent exact-subject review is required
before PR or integration.
