# TDL Handoff: WP6.2 T3/T4 live-issue binding rework

## Purpose of next session

Perform one fresh, history-free independent static review of the immutable
reworked candidate. Do not implement or invoke any runtime surface.

## Active project and workflow

- Project: Agentic Research System, WP6.2 T3/T4.
- Workflow system: standalone; deliver phase complete.
- Lifecycle: proposed author candidate; passing tests do not imply acceptance.
- Review predecessor: task `019f9b08-8b2d-77f2-a928-128fa194403f`,
  turn `019f9b08-9126-7e02-81bd-e168683ab3d8`, verdict
  `rework_required` (5 Critical, 3 Major).

## Packet predecessor

- Governing brief:
  `docs/plans/agentic-research-system/handoffs/13-wp6-2-t3-t4-live-issue-binding-contract-brief.md`.
- Brief source commit: `ac50847fb49f27d412adc45fc2e0a2e10b80c2d2`.
- Immutable dispatch base: `2291b5d4736ad604ce9763d9c677e707970ef14e`.
- Reviewed predecessor candidate:
  `cba7973f4b060a286566e30e5e89404869885324`.

## Exact candidate state

- Branch: `codex/wp6-2-t3-t4-live-issue-contract`.
- Candidate commit: `edb095af629b988f52bcd0e5a80b473915bf7b35`.
- Candidate tree: `ea21d35a21ab8f03addaa13adb12b76ee2364aba`.
- Candidate path count against dispatch base: 24.
- Candidate intentionally contains no handback; this file is wrapper-only.
- Exact schema/contract leaf identities are in
  `.research-system/contracts/wp6-2-t3-t4-live-issue-schema-identities.yaml`.
- Exact changed paths are reproducible with:
  `git diff --name-only 2291b5d4736ad604ce9763d9c677e707970ef14e edb095af629b988f52bcd0e5a80b473915bf7b35`.

## Contracts and validation

- The six reviewed adversarial escapes were first reproduced as RED.
- Final focused contract suite: 76/76 passed.
- The suite covers all eight findings: complete W2 envelopes and joins;
  independently loaded resolver authority/store; provider-native evidence and
  eligibility; exact cost reconciliation; final-hash reconstruction; exact
  argv/token gates; deterministic evidence uniqueness; and exact
  manifest/catalogue reference bytes.
- Immutable predecessor proof matched 220/220 protected WP6.1/T1a members and
  27/27 effective accepted T2 identities.
- Commit hooks passed skill sync, Ruff, Ruff format, and 102/102 contract
  framework gates.
- `git diff --check` passed.
- Historical T2 and package-wide suites were not run: no shared generator,
  predecessor, or runtime seam changed, and focused validation did not fail.

## Results and provenance

No provider call, credential resolution, live smoke, result, claim, profile,
or publication was produced. No rejected prototype bytes were inspected.

## Open risks

- This remains author evidence and needs a fresh independent semantic review.
- Trusted-store loading, cryptographic verification, provider-native parsing,
  and ledger persistence are future runtime obligations, not proven runtime
  behavior.
- Catalogue reducer/projection identities bind to the strict catalogue
  contract schema; runtime component implementations do not yet exist.
- A second `rework_required` verdict is an owner stop, not authority for
  another author loop.

## Next action

Review candidate `edb095af629b988f52bcd0e5a80b473915bf7b35` and tree
`ea21d35a21ab8f03addaa13adb12b76ee2364aba` against brief 13 and the previous
eight findings. Report severity-classified findings only. Do not remediate,
accept, implement, invoke providers, update Jira, open a PR, or merge.

## Branch and integration state

- Candidate is a reachable ancestor of the handback wrapper; preserve it
  without squash or rebase if later accepted.
- Candidate is 24 paths against the dispatch base; wrapper adds this handback
  for 25, below the 30-path task cap and 100-path review limit.
- No PR was opened or merged. Jira was not updated.

## Do not do

- Do not invoke a provider, resolve credentials, or run a live smoke.
- Do not implement coordinator, adapter, provider, or shared runtime code.
- Do not modify accepted T2/WP6.1/T1a, provider predecessor, Gate 5, results,
  claims, profiles, T1b, or T5-T8 surfaces.
- Do not treat passing tests or review as acceptance.
- Do not trigger CodeRabbit or update Jira.
- Do not place toy or synthetic output in `results/`.

## Sensitive information

No credential material, UKDA data, secret sentinel, or provider payload is
included.
