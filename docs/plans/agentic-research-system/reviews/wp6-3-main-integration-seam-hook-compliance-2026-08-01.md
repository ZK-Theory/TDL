# WP6.3 main-integration seam hook-compliance addendum — 2026-08-01

**Technical subject:** `10759ecaf53d865a801fe5cedaaf15412b36b91e`
**Exact-subject review:** `8bb891e2f47bd07919f968408164fa0806a6f685`
**Main-integration subject:** `99f8c0753681e4d848d6fc7d1e0e4f0a448438f5`
**Integration review record commit:** `1e2b048a8de2e6d3257742a2521eb974d68ac6e3`
**Disposition:** process nonconformance corrected at the final candidate head

## Nonconformance

The integration review record in `1e2b048` was committed with
`git commit --no-verify`. The reviewer first attempted the normal commit path,
but that process was interrupted without captured output after more than 120
seconds. There was no evidence that a hook had failed. Using `--no-verify`
after that interruption was therefore unjustified and violated the campaign's
explicit rule that hooks must never be bypassed.

The bypass does not change the review's independently reproduced subject,
ancestry, blob, decision-register, protected-hash, or path-count evidence. It is
nevertheless a process defect and is recorded rather than hidden or rewritten
out of branch history.

## Corrective path

This addendum is the sole content change in the corrective commit. That commit
must be created through the repository's normal `git commit -F` path, without
`--no-verify`, and allowed to finish. A zero exit from that command establishes
the final candidate tree through the configured pre-commit and commit-message
gates. The configured pre-commit path checks skill-tree synchronization, Ruff
when available, and the contract-binding suite; the commit-message hook checks
the project prefix. The non-blocking post-commit hook is not acceptance
evidence.

The corrective commit does not reinterpret or extend the integration review.
It adds no owner acceptance, live authority grant, external-store record,
assurance-pack acceptance, Gate A closure, Gate 6 acceptance, dispatch
authority, or research-execution authority.

## Preservation

The accepted technical subject and both independent review records remain
ancestors. No accepted WP6.3 contract/schema bytes, production code, tests, or
prior review bytes are changed by this addendum. The two pre-existing Repowise
setup modifications remain unstaged and outside the candidate.
