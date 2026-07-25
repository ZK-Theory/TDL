# TDL Handoff: WP6.2 T3/T4 reconciliation correction

## Purpose of next session

Perform a fresh independent static review of the immutable candidate's single
accounting correction. Report findings only; do not implement runtime code.

## Active project and workflow

- Project: Agentic Research System, WP6.2 T3/T4.
- Workflow system: standalone; deliver phase complete.
- Lifecycle: proposed author candidate; passing tests do not imply acceptance.
- Review predecessor: task `019f9b48-1dd9-7c43-9ff6-890c55851651`,
  turn `019f9b48-225c-7232-9bbb-a0588df4162c`, verdict
  `rework_required` (1 Major).

## Packet predecessor

- Governing brief:
  `docs/plans/agentic-research-system/handoffs/13-wp6-2-t3-t4-live-issue-binding-contract-brief.md`.
- Brief source commit: `ac50847fb49f27d412adc45fc2e0a2e10b80c2d2`.
- Immutable dispatch base: `2291b5d4736ad604ce9763d9c677e707970ef14e`.
- Reviewed predecessor candidate:
  `8e4a77d6876d6a0bb15d88f54e89a9f91079f4bd`.
- Reviewed predecessor wrapper:
  `1178d939c8de101313c9b5b5b2653dd8a6eff105`.

## Exact candidate state

- Branch: `codex/wp6-2-t3-t4-live-issue-contract`.
- Candidate commit: `ddb19bd4d06d1c08b421f8980dfd113a99813ce2`.
- Candidate tree: `586acf0a8129b6c1013a8b2e94cf0830267cd398`.
- Candidate path count against dispatch base: 29.
- Candidate intentionally contains no handback; this file is wrapper-only.
- Exact schema/contract leaf identities are in
  `.research-system/contracts/wp6-2-t3-t4-live-issue-schema-identities.yaml`.
- Exact changed paths are reproducible with:
  `git diff --name-only 2291b5d4736ad604ce9763d9c677e707970ef14e ddb19bd4d06d1c08b421f8980dfd113a99813ce2`.

## Contracts and validation

- Exact reconciliation now preserves accepted T2 semantics:
  `remaining = post_reservation_available + refund`; available 90, reserved 10,
  consumed 2, refund 8 requires remaining 98 and rejects 88.
- Every mode joins reservation identity, currency, rates, rate evidence, token
  and cost ceilings, zero-cost authority, and post-reservation balance before
  applying disposition rules.
- Uncertain `reserved` keeps actual tokens, consumption, refund, and remaining
  balance pending. Uncertain `conservatively_consumed` consumes the full
  reservation, refunds zero, and preserves the post-reservation balance.
- Outcome-command validation invokes reconciliation validation. Complete
  event-batch validation invokes it again on the joined reconciliation event.
- Directly affected slice: 3/3 passed.
- Catalogue/identity checks: 3/3 passed.
- Isolated accepted-predecessor byte proof: 1/1 passed.
- Final focused live-issue contract suite: 83/83 passed.
- Immutable proof matched 220/220 protected WP6.1/T1a members and 27/27
  effective accepted T2 identities.
- Commit hooks passed skill sync, Ruff, Ruff format, and 102/102 contract
  framework gates.
- `git diff --check` passed.
- No broad suite was run because no shared generator, accepted predecessor, or
  runtime surface changed and the focused validation remained green.

## Results and provenance

No provider call, credential resolution, authentication operation, live smoke,
result, claim, profile, publication, or external-service mutation was produced.
No rejected prototype bytes were inspected.

## Open risks

- This remains author evidence and requires fresh independent review.
- The semantic validator is focused contract evidence, not a production
  coordinator, ledger, provider adapter, or persistence implementation.
- Runtime concurrency, persistence, and provider integration remain outside
  this contract-only correction.
- No acceptance or further remediation is authorized by this handback.

## Next action

Review candidate `ddb19bd4d06d1c08b421f8980dfd113a99813ce2` and tree
`586acf0a8129b6c1013a8b2e94cf0830267cd398` against the single Major finding
from review task `019f9b48-1dd9-7c43-9ff6-890c55851651`. Reproduce the 98/88
balance example, uncertain-mode authority mismatches, and composed
outcome/event-batch validation. Report a severity-classified verdict only.
Do not remediate, accept, implement, invoke providers, update Jira, open a PR,
or merge.

## Branch and integration state

- Candidate is the direct parent of this wrapper and must remain reachable
  without squash or rebase if later accepted.
- Candidate is 29 paths against the dispatch base; wrapper adds this handback
  for 30, at the task cap and below the 100-path review limit.
- No PR was opened or merged. Jira was not updated.

## Do not do

- Do not invoke providers, resolve credentials, authenticate, or run live smoke.
- Do not implement coordinator, adapter, provider, trust-store, or runtime code.
- Do not modify accepted T2/WP6.1/T1a, Gate 5, results, claims, profiles, T1b,
  or T5-T8 surfaces.
- Do not treat passing tests or review as acceptance.
- Do not trigger CodeRabbit, update Jira, open a PR, or merge.
- Do not place toy or synthetic output in `results/`.

## Sensitive information

No credential material, UKDA data, secret sentinel, or provider payload is
included.
