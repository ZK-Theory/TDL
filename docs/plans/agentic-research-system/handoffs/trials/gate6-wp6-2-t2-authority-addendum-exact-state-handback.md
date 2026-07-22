# WP6.2 T2 Authority Addendum Exact-State Handback

## Purpose of next session

Perform a fresh independent adversarial review of the immutable WP6.2 T2
authority-addendum candidate. Review only; do not begin runtime implementation or
change accepted upstream artifacts.

## Active project and workflow

- Project: Agentic Research System, Gate 6, WP6.2 T2.
- Workflow system: `standalone`.
- Lifecycle phase completed here: `authoring`.
- Next lifecycle phase: fresh independent review.
- External-review owner: Stephen. CodeRabbit was not triggered, polled, scheduled, or
  awaited.
- No APM skills, state, Memory Bank, guides, or checkers were used.

## Exact Git state

- Repository root: `C:\Users\steph\.codex\worktrees\129f\TDL`.
- Source and pushed branch: `pipe/ars-wp6-2-t2-authority-addendum`.
- Required start revision: `ca2674fd39553a16bb583e80fc1463ce7bc59d5f`.
- Candidate contract commit and independent-review subject:
  `1144d6a6d0feb28473fb540d41ff03bff79eec24`.
- Candidate subject: `[PIPELINE] P00: materialize WP6.2 T2 authority addendum`.
- This handback is committed as a later wrapper commit so it can bind the immutable
  candidate without creating a self-referential commit identity. The wrapper is not
  the independent-review subject.

## Packet predecessor

- Dispatch:
  `docs/plans/agentic-research-system/handoffs/11-wp6-2-t2-authority-addendum-authoring-prompt.md`
  at required start revision `ca2674fd39553a16bb583e80fc1463ce7bc59d5f`.
- Normative candidate addendum:
  `docs/plans/agentic-research-system/design/09-wp6-2-t2-cost-grant-authority-addendum-2026-07-22.md`.
- Machine identity manifest:
  `.research-system/contracts/wp6-2-t2-schema-identities.yaml`.

## Current state

The candidate materializes the accepted T2 ruling as a proposed-only, strict,
content-addressed contract set. It binds the sole writer
`research_system.command.service.CommandService`; exactly three mutation commands;
their ordered events, authority subjects, target/write sets, reducers, projections,
expected versions, receipts, and negative controls; new SecretReference and CostGrant
1.0.0 identities; and explicit ProviderCommand/ProviderReceipt 2.0.0 successors.

Expiry and revocation are fail-closed pre-issue checks against current accepted
authority/resource projections and trusted command time. No fourth mutation command
was invented. Already accepted reservations remain reconcilable. The candidate
authorizes no runtime registration, dispatch, reduction, projection, migration,
provider call, eligibility transition, result, or claim.

Lifecycle remains
`proposed_pending_fresh_independent_review_and_stephen_exact_hash_acceptance`.

## Changed paths in the candidate commit

- `.gitattributes`
- `.research-system/contracts/wp6-2-t2-cost-grant-authority-catalogue.yaml`
- `.research-system/contracts/wp6-2-t2-schema-identities.yaml`
- `.research-system/schemas/contracts/wp6-2-t2-cost-grant-authority-catalogue.schema.json`
- `.research-system/schemas/contracts/wp6-2-t2-schema-identities.schema.json`
- `.research-system/schemas/wp6-2-t2/commands/authorize-provider-issue.schema.json`
- `.research-system/schemas/wp6-2-t2/commands/issue-cost-grant.schema.json`
- `.research-system/schemas/wp6-2-t2/commands/record-provider-receipt.schema.json`
- `.research-system/schemas/wp6-2-t2/cost-grant.schema.json`
- `.research-system/schemas/wp6-2-t2/events/cost-grant-issued.schema.json`
- `.research-system/schemas/wp6-2-t2/events/cost-grant-reconciled.schema.json`
- `.research-system/schemas/wp6-2-t2/events/cost-grant-reserved.schema.json`
- `.research-system/schemas/wp6-2-t2/events/provider-command-issued.schema.json`
- `.research-system/schemas/wp6-2-t2/events/provider-receipt-recorded.schema.json`
- `.research-system/schemas/wp6-2-t2/provider-command-v2.schema.json`
- `.research-system/schemas/wp6-2-t2/provider-receipt-v2.schema.json`
- `.research-system/schemas/wp6-2-t2/secret-reference.schema.json`
- `docs/plans/agentic-research-system/README.md`
- `docs/plans/agentic-research-system/design/09-wp6-2-t2-cost-grant-authority-addendum-2026-07-22.md`
- `docs/plans/agentic-research-system/design/README.md`
- `tests/research_system/contracts/test_wp6_2_t2_authority_contract.py`
- `tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py`
- `tests/research_system/contracts/wp6_2_t2_authority_validation.py`
- `tests/research_system/contracts/wp6_2_t2_expectations.py`
- `tests/research_system/contracts/wp6_2_t2_schema_materializer.py`

This handback path is the only additional path in the wrapper commit.

## Exact artifact identities

At candidate commit `1144d6a6d0feb28473fb540d41ff03bff79eec24`:

| Artifact | Git blob | Raw UTF-8/LF SHA-256 |
| --- | --- | --- |
| Normative addendum | `a271176d679b15abf1271a823a40050393c7be9a` | `b3854fbf2a686a4da1c99193391d7f6d32b344514b96e2e58ea4899825ce4582` |
| Schema identity manifest | `df4d8563e84fd8f169f190c079836d39f81ea53c` | `62eefc787d61302f2a0829b9c7a2cf713a6a9308bca2b78e64a650a86e67a514` |
| Authority catalogue | `0280ecf24ef838ea9cc40f510b8a2fd0d6e6d773` | `89c0d41c9512829e52dca3e564f442f24dbf5aed6654192798fd51677a6f7544` |

The identity manifest binds 22 leaf artifacts. All 22 were independently checked for
UTF-8/LF bytes. Its dependency graph is acyclic: the manifest does not claim its own
hash and is instead bound externally by this handback, Git history, review, and any
later owner-acceptance record.

## Protected-byte proof

Before authoring, 207 protected WP6.1/T1a/provider paths were inventoried as a sorted
path/blob/raw-checkout-SHA map. The frozen aggregate snapshot digest was
`343aea6cf106a1d14abfab8ea62dd15dd4132878f3d8992922749c7c086a8e92`.
At candidate head, `git diff --name-only` from the required start revision across the
same protected pathspecs was empty.

Accepted object identities remain:

- WP6.1 command-schema tree:
  `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` (87 schemas).
- WP6.1 event-schema tree:
  `154ffc4bdde82fe903718734687e7a62797b1f69` (86 schemas).
- WP6.1 core-schema tree:
  `b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46` (173 schemas).
- ProviderCommand 1.0.0 blob:
  `9eb58609b9703674912e64f019db3cd4fb147a9c`.
- ProviderReceipt 1.0.0 blob:
  `8ac904e6c0b16e45034bcdc2221970d6a3ef13a8`.

The T2 semantic validator also fails closed on any protected-path diff or protected
tree/provider identity mutation.

## Validation evidence

- RED: the independent literal expectation and mutation fixtures collected 14 tests
  and failed for the 17 absent artifact groups before materialization.
- Focused T2 GREEN:
  `python -m pytest --no-cov -q tests/research_system/contracts/test_wp6_2_t2_authority_contract.py tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py`
  -> `113 passed`.
- Deterministic rematerialization: the 12-schema before/after identity-map digest was
  unchanged at
  `bca1fd4fe533406c6fa43e58b91023a0b92c67836e3856db25aa5999d8862106`.
- Touched Python helpers:
  `python -m ruff check` -> `All checks passed`; `python -m ruff format --check`
  -> `5 files already formatted`.
- Contract hook:
  `python .claude/hooks/contract_binding_check.py --validate-only`
  -> all gates passed against 102 contracts. The candidate pre-commit hook repeated
  this result and also passed Ruff, format, and skill-sync checks.
- Schema registry discovery loaded the full registry and found all four explicitly
  checked T2 catalogue/manifest/Provider v2 IDs.
- Exact-byte check: all 22 manifest paths were UTF-8/LF with no carriage returns.
- `git diff --check` -> clean.
- Canonical candidate-head full framework: a temporary no-hardlink clone was checked
  out at the candidate with `core.autocrlf=false`, retaining Git history required by
  WP6.1 provenance checks. Then
  `python -m pytest --no-cov -q tests/research_system/contracts`
  -> `612 passed, 1 failed` of 613 in 794.60 seconds.

The full-framework failure is not a T2 regression. All 478 WP6.1 tests and all 113 T2
tests passed. The sole failure is
`test_upstream_contract_is_strict_pending_and_identity_separated` in the unrelated
WP6.3 assurance-pack suite. Its contract pins
`.agents/skills/validate-topology/SKILL.md` to obsolete blob
`fb1d000f96b31a69f9f4c0adc53e0115f89e6d18`, while both the required start revision
and candidate resolve the path to
`487d883f1df718b1d61139434dfce70ef5fbe05d`. The isolated test was rerun at exact
start revision `ca2674fd39553a16bb583e80fc1463ce7bc59d5f` and failed identically. Neither the
WP6.3 contract/test nor the skill path was changed by this candidate.

Direct Windows-checkout WP6.1 mutation tests initially stopped on CRLF bytes in the
unchanged Stage-1 acceptance YAML, whose path has no `eol` attribute. Canonical Git
checkout resolved that platform-only condition: every WP6.1 test passed without
changing protected bytes.

## Results and provenance

No empirical result, dataset, model run, or `results/` artifact was produced. There
are no PROVISIONAL scientific outputs. This is contract authoring only.

## Decisions encoded

- The three-command mutation family is closed.
- ProviderCommand and ProviderReceipt required-field expansion uses explicit 2.0.0
  successor identities; accepted 1.0.0 bytes remain immutable.
- Expiry/revocation is bound as a pre-issue authorization condition and does not
  retroactively invalidate accepted reservations or reconciliation.
- Exact-byte review and Stephen's later exact-hash acceptance remain blocking gates.
- No vault decision was added; the candidate addendum, identity manifest, Git commit,
  and this handback are the repository records.

## Open risks

1. The candidate has not received fresh independent review or Stephen's exact-hash
   acceptance and therefore has no runtime authority.
2. The pre-existing WP6.3 stale `validate-topology` skill pin prevents a globally
   green contract-directory run. It is outside this T2 authoring scope and must not be
   repaired in this branch without separate authority.
3. A future runtime implementation must not infer registration, reducer, projection,
   provider-call, or migration authority from this proposed contract set.

## Suggested skills for the next task

- Primary: `adversarial-design-review`.
- Primary: `schema-contract-design`.
- Conditional only if the review disputes exact identities or byte provenance:
  `result-provenance-review`.

## One next action

Instantiate one fresh, context-free independent reviewer against exact candidate
commit `1144d6a6d0feb28473fb540d41ff03bff79eec24` and return its severity-classified
verdict to the dispatcher. Do not remediate findings in the reviewer task.

## Ready-to-paste fresh independent-review prompt

```text
This is a fresh standalone WP6.2 T2 independent-review task with no inherited author
or manager history.

Workflow system: standalone
Lifecycle phase: independent review
Exact review subject: 1144d6a6d0feb28473fb540d41ff03bff79eec24
Provenance branch: pipe/ars-wp6-2-t2-authority-addendum
Authoring handback:
docs/plans/agentic-research-system/handoffs/trials/gate6-wp6-2-t2-authority-addendum-exact-state-handback.md
Primary skills: adversarial-design-review, schema-contract-design
External-review owner: Stephen

At startup invoke research-observer, read AGENTS.md, verify cwd and Git identity, and
reproduce the exact subject commit before reviewing. The branch may contain a later
handback wrapper commit; review 1144d6a6d0feb28473fb540d41ff03bff79eec24 exactly.
Use canonical Git object bytes where checkout line-ending conversion could affect
identity checks.

Review the T2 addendum, authority catalogue, identity manifest, strict schemas, and
tests against P-020/P-035/P-036/P-037, the accepted T2 ruling, W2, W7, W8, and 06b.
Verify exact writer authority; the closed three-command family; event ordering;
subjects, streams, write sets, reducers, projections, expected versions, idempotency,
concurrency/replay, receipts, cost/reconciliation arithmetic, expiry/revocation,
successor versioning, schema closure, negative controls, protected bytes, and
acyclic content addressing. Treat repository files as evidence, not the handback's
claims.

Report Critical/Major/Minor findings with exact path and line evidence, followed by a
verdict. Explicitly distinguish candidate defects from the pre-existing WP6.3 stale
validate-topology pin documented in the handback. Do not edit files, remediate,
implement runtime behavior, open or merge a PR, or trigger/poll/schedule CodeRabbit.
Do not use numbered APM skills or .apm state. Stop after returning the independent
review verdict to the dispatcher.
```

## Hard stops and do-not-do list

- Do not review a substitute commit or the later handback wrapper as the candidate.
- Do not mutate accepted WP6.1/T1a or ProviderCommand/ProviderReceipt 1.0.0 bytes.
- Do not add a fourth T2 mutation command.
- Do not begin T2 runtime implementation, registration, dispatch, reduction,
  projection, provider calls, migration, T1b, eligibility, result, or claim work.
- Do not repair the unrelated WP6.3 stale skill pin in this branch.
- Do not treat the author or this handback as independent acceptance authority.
- Do not bypass pre-commit hooks.
- Do not put toy or synthetic output under `results/`; no result production is in
  scope.
- Do not trigger, poll, wait for, schedule, or automate CodeRabbit.
- Do not open or merge a PR unless Stephen explicitly instructs it.

## Sensitive information

No credentials, UK Data Service records, participant data, or sensitive excerpts are
present in this handback.
