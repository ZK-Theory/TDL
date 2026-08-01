# WP6.5 W11 contract-foundation r2 exact-subject review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, contract and authority, read-only
- Reviewed branch: `codex/review-kan58-w11-contract-r2-9d2b024`
- Reviewed subject: `9d2b0246649c4c61657d15500fa1bc5c4f3fb236`
- Direct parent: `3a3a5355c9fbc3b380e2be26fb364dbd0c0315d9`
- Tree: `5a0d1f36aacd2ebf16e5d5a96c9b4daf3068c654`
- Full materialization range: 66 paths from `c84eb2aaf0890d36d3735d08a14169f4c50935cd`
- Corrective range: 3 paths from `3a3a5355c9fbc3b380e2be26fb364dbd0c0315d9`
- Verdict: `rework_required`
- Findings: 0 Critical, 3 Major, 1 Minor

## Executive disposition

The r2 subject correctly reconstructs the 81 W11 owner rows and their literal
test identities, rejects the previously demonstrated tuple, lineage, rubric,
and cross-kind substitutions, and preserves the accepted W11 source bytes.
However, it violates the admitted bootstrap boundary by placing the semantic
validator in production runtime Python, does not bind its executable subject
guard to the full exact range, and does not require the observed scorecard axis
set to equal the accepted rubric axis set. The subject is therefore
quarantined and is not merge-authorized or evidence that KAN-58 is complete.

This fresh r2 producer may perform one bounded author-review-remediation cycle.
That correction must keep the materialization pre-runtime and inert: move the
semantic admission check to a clearly identified non-runtime materialization
verifier, remove the W11 hooks from production `SchemaRegistry`, pin and cover
the complete admitted range, enforce exact rubric-axis equality, and close the
canonical typed-ID minor without changing the accepted W11 source bytes.

## Exact identity and validation evidence

The reviewer verified the accepted W11 authority exactly at:

- commit `892d1d1650cdcf71d2a886318e174a18e11d5de0`;
- blob `f90729d0c42a0de98d064fac0824d1969c871c82`;
- raw SHA-256 `65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70`;
- 185,214 LF-only bytes with no CR bytes.

Independent identity checks confirmed the reviewed head, branch, parent, tree,
three-path corrective set, 66-path full range, clean substantive status, and a
clean `git diff --check` result. No handler, ledger producer, reducer,
projection, OR-140 import, dossier admission, transition, migration, or cutover
was introduced.

The focused contract suite passed all 17 tests. Direct public-seam probes also
confirmed:

- all 81 owner rows (`OR-001` through `OR-041` and `OR-101` through `OR-140`)
  and their three literal test IDs reconstruct exactly;
- valid tuples admit and missing, duplicate, aliased, swapped, and
  `OR-140`/`OR-001` substitutions reject;
- revision 1 and revision 2 superseding 1 admit, while revision 3 superseding 1
  rejects;
- missing, foreign, ambiguous, wrong-kind, unknown-axis, and out-of-domain
  rubric cases reject;
- representative non-W11 command validation remains functional and malformed
  core input rejects.

The broader schema-registry unit module timed out twice at 120 seconds before
producing test output. It is recorded as inconclusive and is not counted as a
pass.

## M-01 - the admitted pre-runtime boundary is violated

The bootstrap contract's verification rules state that no runtime production
Python is changed and its forbidden list excludes a runtime registry binding.
The subject changes `research_system/schema_registry.py`, adds
`research_system/w11_contract_validation.py`, and invokes the new validator
from public `SchemaRegistry.validate` independently of runtime activation.

A direct probe showed that the bundled runtime registry reports a W11 schema
inactive while public `validate` nevertheless accepts a W11 document. The
absence of command/event activation therefore does not satisfy the stronger
accepted boundary. Semantic admission must be provided by a non-runtime inert
materialization verifier whose interface is identified by the bootstrap
contract and tests.

## M-02 - the executable exact-range guard is not exact

The subject test defines `W11_SUBJECT = "HEAD"` and checks only
`research_system` paths. It does not pin the reviewed `9d2b024...` subject,
verify its tree, or cover the complete 66-path materialization range. The
materialization verifier must fail closed against an exact independently
generated subject/range manifest or equivalent full-range identity control;
worktree-relative `HEAD` and a partial path subset are insufficient.

## M-03 - observed rubric axes need exact-set equality

W11 requires the observed scorecard axis IDs to exactly match the accepted
rubric. The validator currently checks only `required_axis_ids`. A direct
admission probe accepted a scorecard which omitted a valid non-required rubric
axis, and a scorecard can likewise introduce a non-required mismatch. The
verifier must compare the complete observed axis-ID set with the complete
accepted rubric axis-ID set while retaining the existing per-axis kind and
domain checks.

## m-01 - source-reference IDs are only prefix-typed

Cross-kind substitutions reject, but source-reference identity checks accept
malformed values such as `obj_not-a-uuid` and `art_1`. The inert verifier must
apply the canonical UUID-shaped definitions for `obj_` and `art_` identities,
not prefix-only checks.

## Required bounded correction

The r2 remediation must:

1. remove both production-Python W11 validation changes from the full range;
2. provide and identify a non-runtime materialization admission command or
   verifier exercised by the contract tests;
3. bind that verifier to the exact complete subject, tree, and 66-path range or
   a separately generated full-range manifest;
4. enforce complete rubric-axis set equality plus the existing domain checks;
5. enforce canonical typed `obj_` and `art_` identities;
6. preserve the accepted W11 tuple and all non-activation boundaries; and
7. rerun the focused contract suite and exact identity checks before a fresh
   independent review.
