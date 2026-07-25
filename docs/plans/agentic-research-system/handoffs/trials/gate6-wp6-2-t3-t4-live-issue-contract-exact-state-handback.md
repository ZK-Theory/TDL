# TDL Handoff: WP6.2 T3/T4 final schema-conformance rework

## Purpose of next session

Perform one fresh, history-free independent static review of the immutable
candidate. Report findings only; do not remediate or implement runtime code.

## Active project and workflow

- Project: Agentic Research System, WP6.2 T3/T4.
- Workflow system: standalone; deliver phase complete.
- Lifecycle: proposed author candidate; passing tests do not imply acceptance.
- Review predecessor: task `019f9b28-3b7c-7e70-903a-769e09d2617a`,
  turn `019f9b28-3f54-77c0-87ef-737696adb317`, verdict
  `rework_required` (6 Critical, 1 Major).

## Packet predecessor

- Governing brief:
  `docs/plans/agentic-research-system/handoffs/13-wp6-2-t3-t4-live-issue-binding-contract-brief.md`.
- Brief source commit: `ac50847fb49f27d412adc45fc2e0a2e10b80c2d2`.
- Immutable dispatch base: `2291b5d4736ad604ce9763d9c677e707970ef14e`.
- Reviewed predecessor candidate:
  `edb095af629b988f52bcd0e5a80b473915bf7b35`.
- Reviewed predecessor wrapper:
  `0c55192124d454a04823c8790e82e272ef8922bb`.

## Exact candidate state

- Branch: `codex/wp6-2-t3-t4-live-issue-contract`.
- Candidate commit: `8e4a77d6876d6a0bb15d88f54e89a9f91079f4bd`.
- Candidate tree: `6ef4c4dbc67dbd4cb6b8844b0b5f2429ef87639d`.
- Candidate path count against dispatch base: 29.
- Candidate intentionally contains no handback; this file is wrapper-only.
- Exact schema/contract leaf identities are in
  `.research-system/contracts/wp6-2-t3-t4-live-issue-schema-identities.yaml`.
- Exact changed paths are reproducible with:
  `git diff --name-only 2291b5d4736ad604ce9763d9c677e707970ef14e 8e4a77d6876d6a0bb15d88f54e89a9f91079f4bd`.

## Contracts and validation

- `.gitattributes` is restored to accepted blob
  `6798d947a17f851b93cfa769182027cc778b801f`.
- Resolver authority and resolver-store records are loaded from internally
  identity-checked catalogue bytes; unregistered and mismatched records reject.
- Claim intent and final payload hashes are reconstructed from their documented,
  domain-separated preimages and compared for exact equality.
- Eligible/complete receipts resolve and content-check provider-discriminated
  native evidence, selection, delivery, accounting, and completeness joins.
- Outcome and reconciliation validation use one reservation representation and
  enforce remaining balances, actuals, ceilings, rates, currency, authority,
  disposition, consumption, refunds, and P-037--P-041 integer arithmetic.
- Command validation is composed with the complete ordered three-event batch,
  including identity, lineage, stream-role, transaction, replay, position, and
  hash-chain joins.
- Six reducer/projection references resolve to independent typed schemas whose
  leaf bytes and semantic component identities are manifest-bound.
- Isolated accepted-predecessor byte test: 1/1 passed.
- Final focused live-issue contract suite: 83/83 passed.
- Immutable proof matched 220/220 protected WP6.1/T1a members and 27/27
  effective accepted T2 identities.
- Identity proof covered 17 schema leaves plus 1 contract leaf; catalogue
  semantic resolution covered all 12 references, including 6 typed components.
- Commit hooks passed skill sync, Ruff, Ruff format, and 102/102 contract
  framework gates.
- `git diff --check` passed.
- Historical T2 and package-wide suites were not run: no shared generator,
  predecessor, or runtime seam changed, and focused validation did not fail.

## Results and provenance

No provider call, credential resolution, authentication operation, live smoke,
result, claim, profile, publication, or external-service mutation was produced.
No rejected prototype bytes were inspected.

## Open risks

- This remains author evidence and requires a fresh independent semantic review.
- The validators are focused contract evidence, not production coordinator,
  provider-adapter, cryptographic-store, ledger, or projection implementations.
- Runtime persistence, concurrency, provider-native parsing, and independently
  operated trust-store behavior remain future implementation obligations.
- No further remediation or acceptance action is authorized by this handback.

## Next action

Review candidate `8e4a77d6876d6a0bb15d88f54e89a9f91079f4bd` and tree
`6ef4c4dbc67dbd4cb6b8844b0b5f2429ef87639d` against brief 13 and the seven
final schema-conformance findings. Report severity-classified findings only.
Do not remediate, accept, implement, invoke providers, update Jira, open a PR,
or merge.

## Branch and integration state

- Candidate is a reachable ancestor of the handback wrapper; preserve it
  without squash or rebase if later accepted.
- Candidate is 29 paths against the dispatch base; wrapper adds this handback
  for 30, at the task cap and below the 100-path review limit.
- No PR was opened or merged. Jira was not updated.

## Do not do

- Do not invoke a provider, resolve credentials, authenticate, or run live smoke.
- Do not implement coordinator, adapter, provider, trust-store, or runtime code.
- Do not modify accepted T2/WP6.1/T1a, provider predecessor, Gate 5, results,
  claims, profiles, T1b, or T5-T8 surfaces.
- Do not treat passing tests or review as acceptance.
- Do not trigger CodeRabbit, update Jira, open a PR, or merge.
- Do not place toy or synthetic output in `results/`.

## Sensitive information

No credential material, UKDA data, secret sentinel, or provider payload is
included.
