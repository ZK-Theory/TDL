# TDL Handoff: WP6.2 T3/T4 reservation-authority join

## Purpose of next session

Perform a fresh independent static review of the immutable candidate's
reservation-authority correction. Report findings only; do not implement
runtime code or accept the candidate.

## Active project and workflow

- Project: Agentic Research System, WP6.2 T3/T4.
- Workflow system: standalone; deliver phase complete.
- Lifecycle: proposed author candidate; passing tests do not imply acceptance.
- Review predecessor: task `019f9b54-fe47-7e30-b2a1-d17224fd309c`,
  turn `019f9b55-069b-7f80-a03f-49d2b36af3f5`, verdict
  `rework_required` (1 Major).

## Packet predecessor

- Governing brief:
  `docs/plans/agentic-research-system/handoffs/13-wp6-2-t3-t4-live-issue-binding-contract-brief.md`.
- Brief source commit: `ac50847fb49f27d412adc45fc2e0a2e10b80c2d2`.
- Immutable dispatch base: `2291b5d4736ad604ce9763d9c677e707970ef14e`.
- Reviewed predecessor candidate:
  `ddb19bd4d06d1c08b421f8980dfd113a99813ce2`.
- Reviewed predecessor wrapper:
  `c952468a416a43358075d6558ce1fb3f22a23aa5`.

## Exact candidate state

- Branch: `codex/wp6-2-t3-t4-live-issue-contract`.
- Candidate commit: `7cd8afe8b47e9d75b6848d0e84e14362c227a4da`.
- Candidate tree: `5e090d486f9d6f91d270f78851f5ad523549253f`.
- Candidate path count against dispatch base: 29.
- Candidate intentionally contains no handback; this file is wrapper-only.
- Exact schema/contract leaf identities are in
  `.research-system/contracts/wp6-2-t3-t4-live-issue-schema-identities.yaml`.
- Exact changed paths are reproducible with:
  `git diff --name-only 2291b5d4736ad604ce9763d9c677e707970ef14e 7cd8afe8b47e9d75b6848d0e84e14362c227a4da`.

## Correction and validation

- The identity manifest now content-addresses the live-issue catalogue as an
  independently loadable contract artifact.
- The catalogue contains the accepted reservation authority record keyed by
  its identity/revision/hash triple.
- Outcome-command and complete event-batch validation load that record from
  independently identified bytes. Caller-supplied reservation snapshots are
  compared to the loaded record and cannot act as authority.
- Full equality binds the reservation, cost grant, provider command, reserved
  amount, post-reservation available balance, currency, rates, rate evidence,
  token and cost ceilings, and zero-cost authority.
- Corrected T2 arithmetic remains:
  `post = post-reservation available + refund`; uncertain disposition rules
  remain unchanged.
- Directly affected slice: 4/4 passed. This includes seven paired substitutions
  rejected through both outcome and complete event-batch entry points.
- Catalogue/identity slice: 4/4 passed.
- Final focused live-issue contract suite: 84/84 passed.
- Isolated immutable proof: 1/1 passed, matching 220/220 protected WP6.1/T1a
  members and all 27/27 effective accepted T2 identities.
- Commit hooks completed successfully, including skill sync, Ruff/format, the
  contract framework gate, and commit-prefix validation.
- `git diff --check` passed.
- No broad suite was run because no runtime surface, accepted predecessor, or
  shared generator changed and all focused gates remained green.

## Results and provenance

No provider call, credential resolution, authentication operation, live smoke,
runtime implementation, Jira mutation, PR, merge, result, claim, profile, or
acceptance action was produced. No rejected prototype bytes were inspected.

## Open risks

- This remains author evidence and requires fresh independent review.
- The authoritative reservation catalogue is proposed contract data, not an
  accepted production persistence implementation.
- Runtime concurrency, persistence, and provider integration remain outside
  this contract-only correction.
- No acceptance or further remediation is authorized by this handback.

## Next action

Review candidate `7cd8afe8b47e9d75b6848d0e84e14362c227a4da` and tree
`5e090d486f9d6f91d270f78851f5ad523549253f` against the single Major from
review task `019f9b54-fe47-7e30-b2a1-d17224fd309c`. Attempt paired substitution
while retaining the accepted reservation triple across amount, balance,
currency, rates/rate evidence, token/cost ceilings, cost-grant linkage, and
provider-command linkage through both composed entry points. Confirm the
catalogue is loaded only after its raw bytes match the identity manifest.
Report a severity-classified verdict only.

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

## Sensitive information

No credential material, UKDA data, secret sentinel, or provider payload is
included.
