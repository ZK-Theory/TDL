# WP6.2 T2 Integration Exact-State Handback

**Date:** 2026-07-23

**Workflow:** standalone

**Completed action:** T2-only integration assembled, independently accepted at
the exact reviewed subject, opened as PR #158, and given one bounded
CodeRabbit remediation

**Pull request:** <https://github.com/stephendor/TDL/pull/158>

## Exact state

- Branch: `codex/wp6-2-t2-integration`.
- Current-main subject incorporated:
  `6c7d8dfdfcf875b02fa3a0b89bf84c29f711f0c2`. The initially reviewed base
  `3cc6f2a1f7a90dfd77f8bdae0de9e2c5f934a66d` remains an ancestor.
- Exact independently reviewed integration subject:
  `57cec488f1311342848515078a7abf7b28c14fcc`.
- Pre-remediation handback wrapper:
  `88d496755a7872267fb311fca03204f0c9224469`.
- CodeRabbit remediation commit:
  `211dc7cd26ce7ef59280057fcf7ca536b99f35f7`.
- Final current-main merge wrapper head: `SELF`, the later commit whose tree
  contains this handback. The final Manager response binds its exact SHA
  without creating a self-reference.
- Accepted candidate ancestor:
  `391a92753d7f746fa91a6b5455c9ce0fd01baa52`, tree
  `0254c5416925126412867d61b3045ee1563abd0c`, parent
  `bba49c11ef8cd37dee7fa571f712d77a954f6b16`.
- Final R3 review ancestor:
  `655f4173db93447a068adc6e92621455c4abc85d`.
- Integration merge:
  `2822ef8b61018590066164219ae871bdecfd0780`, with final R3 as first parent
  and current main as second parent.

The integration preserves the exact accepted candidate as a reachable
ancestor. The final R3 report, author handback, P-040 acceptance, and T2
line-ending contract remain retained at their certified historical
identities. The final remediation head intentionally differs from three
candidate leaf artifacts and refreshes their two dependent identity records;
P-040 therefore continues to accept only candidate `391a9275`, not the
remediated head.

## CodeRabbit remediation

Stephen supplied two findings against PR #158. Both remained valid at
`88d496755a7872267fb311fca03204f0c9224469`:

- `AuthorizeProviderIssue.reserved_cost_microunits` rejected zero despite
  permitting `zero_cost_authorized`. Its minimum is now zero while its type
  remains integer in both the generated schema and materializer source.
- The cost-mode test used a redundant singleton set comprehension. It now
  compares directly with `"metered"` and also binds the remediated reservation
  constraint to `{"type": "integer", "minimum": 0}`.

Deterministic materialization changed only five paths: the schema,
materializer, contract test, authority catalogue identity, and identity
manifest. A second materialization was idempotent.

After that remediation, current main advanced through merged PR #157 and
GitHub reported PR #158 as conflicting. Current main was merged mechanically:
its workflow files are exact main bytes, while the ARS index retains only the
T2 navigation added by PR #158. This branch did not alter or manage PR #157.

## Integration evidence

- Pull-request delta at the final current-main merge head: 34 paths, below the target
  of 90 and hard limit of 100.
- Excluded path and added-content scans: zero hits.
- Independent seam review: `accept`; 0 Critical, 0 Major, 0 Minor.
- Focused WP6.2 T2 suite: 135 passed both before and during independent review.
- Post-remediation focused WP6.2 T2 suite: 135 passed.
- Contract framework: all gates passed against 102 contracts.
- Three-dot `git diff --check`: passed.
- No provider call, credential resolution, runtime action, dataset, result, or
  publication artifact was produced.
- Stephen remains the external-review owner. The Manager did not request,
  trigger, poll, schedule, or monitor CodeRabbit.

The independent verdict binds exact subject `57cec488f1311342848515078a7abf7b28c14fcc`.
It does not cover the later CodeRabbit remediation. The final remediation head
is a proposed PR revision pending Stephen's manual disposition.

## Authority boundary

P-040 accepts contract/addendum bytes only. Neither PR #158 nor this handback
authorizes runtime implementation, credential resolution, provider calls,
T3/T4, T1b-M, T1b-H, T5-T8, eligibility, results, claims, publication, or a
Gate 6 transition. Any runtime-T2 brief requires separate owner authorization.

## Exactly one next authorized action

- Stephen manually re-reviews and disposes PR #158. No further WP6 action is
  authorized by this handback.
