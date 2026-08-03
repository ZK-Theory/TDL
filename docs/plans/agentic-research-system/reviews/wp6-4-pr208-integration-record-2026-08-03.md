# WP6.4 PR #208 integration record

**Date:** 2026-08-03  
**Pull request:** [#208](https://github.com/stephendor/TDL/pull/208)  
**Disposition:** implementation mechanics integrated and owner-approved; WP6.4
ticket acceptance remains open

## Exact integration

- Merge commit: `be0a6cb57d7ec2839f3b4549a5d68e1b8a64c348`
- First parent: `4f8b9b857bab1a7553af5e6ea3ef170608e7e18e`
- Final PR head / second parent:
  `a958452d608ec49bbc94f3a943b49f55578cbc3b`
- Merge and final-head tree:
  `aebd4b52b2217fa3f20358bc6dc64f36fa58ad4f`
- Owner disposition: Stephen explicitly approved the merged PR on 2026-08-03.

The final PR head is an ancestor of live `origin/main`, and the merge tree is
byte-identical to the reviewed and corrected PR-head tree.

## Accepted evidence carried by the merge

The merge preserves the independently accepted implementation subjects and
durable review records for:

- external origin-witness authority: `031af78d97d30258fc16a6543d6b4719e6b7776d`;
- restore-recovery mechanics: `5b9e3d389f59e861b024d0a7ae92d335ec51d29c`;
- approved restore temporary paths: `ba63eef13ee86ad39e9a69e67dff1f343edce40d`;
- moved-restore admission closure: `0368b69712d915f34722c5f1eded406ed77d6a17`;
- deterministic registry closure and explicit preparation API:
  `7b0b8ea1e253294ceb23d70f75c549dd1af4102f`.

The final test-only correction
`a958452d608ec49bbc94f3a943b49f55578cbc3b` directly asserts canonical
set/frozenset normalization and the optional `approved_witness` and
`approved_witness_path` defaults. Both exact tests passed again at the merge
tree (`2 passed`) on 2026-08-03. The subject-bound broader validation remains
recorded in the five accepted review records merged by PR #208.

## Boundary and remaining acceptance

This record closes the PR #208 implementation, review, merge, and owner
disposition tail. It does **not** close KAN-57, WP6.4, A8, D-G6-5, Gate A, or
Gate 6. The following evidence is still required:

1. owner-materialized, non-null canonical foundation binding to the approved
   external control store, project identity, origin-authority root, witness
   path, and witness raw SHA-256;
2. real external moved-store restore/recovery evidence sufficient to close A8;
3. bounded brief-out/evidence-back evidence with stable identities, exact Git
   subject, authority, findings, and unresolved uncertainty;
4. TDA-scale v1.0.1 and an independently reviewed, non-dispatchable SCALE-01
   Gate 6 preflight with `admission_status: pending_wp6_6`;
5. D-G6-5 over the exact accepted preflight subject.

KAN-68 and genuine distinct-party acceptance remain prerequisites for Gate A
A7. Nothing in this integration authorizes provider invocation, credentials,
dispatch, live research, or pilot-result claims.
