# WP6.2 T2 rate-mode boundary review

**Date:** 2026-07-23

**Workflow:** standalone

**Review context:** fresh independent task with no parent conversation history

**Verdict:** `accept`

**Finding count:** 0 Critical, 0 Major, 0 Minor

## Exact reviewed subject

- Commit: `2048f6470a9542db967186cc260d235c3373de2e`.
- Tree: `1be775711befa047c7baa36fa485e5690b2277f1`.
- Parent: `15341a472cbe1a236d97e20110cb9ba35cc08708`.
- Subject: `[PIPELINE] P00: bind reservation cost to rate mode`.
- Branch: `codex/wp6-2-t2-zero-cost-event-remediation`.

At review, the local, tracking, and live remote branch refs resolved exactly to
the reviewed commit.

## Reviewed delta

The commit changes exactly six paths:

1. `.research-system/contracts/wp6-2-t2-cost-grant-authority-catalogue.yaml`
2. `.research-system/contracts/wp6-2-t2-schema-identities.yaml`
3. `.research-system/schemas/wp6-2-t2/commands/authorize-provider-issue.schema.json`
4. `.research-system/schemas/wp6-2-t2/events/cost-grant-reserved.schema.json`
5. `tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py`
6. `tests/research_system/contracts/wp6_2_t2_schema_materializer.py`

No unrelated path or semantic delta was present.

## Independent evidence

The reviewer verified that both the `AuthorizeProviderIssue` and
`CostGrantReserved` payload schemas:

- require `rate_mode` and `reserved_cost_microunits`;
- keep `reserved_cost_microunits` typed as an integer with base minimum zero;
- require a metered reservation to be at least one; and
- require an authorized zero-cost reservation to equal zero.

Direct boundary validation established:

- metered positive: accepted;
- authorized zero-cost zero: accepted end to end through command, mandatory
  reservation event, provider receipt, and reconciliation;
- metered zero: rejected by `minimum`;
- authorized zero-cost positive: rejected by `const`;
- negative reservation: rejected by `minimum`;
- missing mode: rejected by `required`; and
- unknown mode: rejected by `enum`.

All 15 generated schemas exactly matched materializer output. All 27 manifest
artifact Git-blob and raw-SHA-256 bindings matched immutable Git objects, and
the relevant catalogue bindings matched.

## Proportionate validation

Only the authorized changed-element targets ran: six cases passed in 0.44
seconds. `git diff --check` passed. The 135-test package suite, full contract
framework, and unrelated tests were not run.

## Boundary

This review accepts only the six changed contract/schema/test elements at the
exact reviewed subject. It grants no runtime T2 implementation, credential
resolution, provider call, T3/T4, T1b, eligibility transition, result, claim,
publication, PR merge, or Gate 6 transition authority.
