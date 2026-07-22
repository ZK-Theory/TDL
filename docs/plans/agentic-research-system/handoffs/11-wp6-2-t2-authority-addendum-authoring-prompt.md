# WP6.2 T2 Authority-Addendum Authoring Prompt

**Created:** 2026-07-22
**Decision authority:** P-037 and the accepted T2 ruling dated 2026-07-22
**Workflow system:** Standalone TDL supervision; not APM
**Purpose:** Materialize and test the exact T2 authority contract, then return an
exact subject for fresh independent review. This prompt authorizes no runtime
implementation.

## Paste into a fresh authoring task

```text
Author the P-037 WP6.2 T2 cost-grant authority addendum and its strict,
content-addressed contract materialization as exactly one vertical deliverable.

Runtime recommendation:
  model: gpt-5.6-sol
  reasoning_effort: xhigh

Execution context:
  workflow_system: standalone
  supervision_phase: deliver
  lifecycle_phase: materialize
  context_mode: fresh
  context_budget_tokens: 80000
  rotation_trigger: first auto-compaction or approximately 80000 live input tokens
  fork_turns: none
  primary_skills: [schema-contract-design, contract-first-tdd]
  conditional_skills:
    - trigger: completion or rotation
      skill: tda-handoff
  external_review_owner: stephen
  author_review_cycle: 0 in this task; independent review is a fresh next task

This is standalone TDL supervision, not APM. Invoke research-observer as the required
meta-skill; it does not count against the primary-skill budget. Do not invoke numbered
APM skills, read or update `.apm` campaign state, use the APM Memory Bank, or apply APM
guides/checkers. Do not trigger, poll, wait on, or schedule CodeRabbit; Stephen owns it.

Exact Git routing:
  expected_branch: pipe/ars-wp6-2-t2-authority-addendum
  expected_start_revision: use the exact SHA supplied by the dispatcher for this
    branch; verify the remote branch ref, detached/attached HEAD, cwd, and clean status
    before writes
  accepted_wp6_1_integration_base: efcecd8669fb225061c6eaf300e31bc07d352f6e

If the app worktree starts detached, make the single permitted deterministic switch to
the pre-created expected branch only after proving detached HEAD and that branch resolve
to the dispatcher-supplied SHA. Do not create, rename, or substitute another branch.

Read only the authorities needed for this deliverable:
1. AGENTS.md and `tda-large-workflow-supervision`.
2. P-020, P-035, P-036, and P-037 in
   docs/plans/agentic-research-system/03-decisions-and-open-questions.md.
3. docs/plans/agentic-research-system/proposals/
   wp6-2-t2-cost-grant-authority-and-versioning-ruling-2026-07-22.md.
4. W2 schema/version/command/event/atomic-batch rules, W7 provider command/receipt
   rules, W8 resource/grant rules, and the WP6.2 06b T2 definition plus complete
   pre-issue matrix.
5. The accepted WP6.1 catalogue, schema identities, Stage-2 owner record, schemas,
   and contract-test patterns only as immutable interface and validation precedents.

Do not replay WP6.1 review history or regenerate any accepted WP6.1/T1a artifact.
Inventory and hash the protected artifacts first; prove their bytes are unchanged at
candidate head.

Required canonical-transition closure:
- Existing project-wide CommandService is the only writer.
- `IssueCostGrant` emits exactly `[CostGrantIssued]`.
- `AuthorizeProviderIssue` emits exactly the atomic ordered batch
  `[CostGrantReserved, ProviderCommandIssued]`.
- `RecordProviderReceipt` emits exactly the atomic ordered batch
  `[ProviderReceiptRecorded, CostGrantReconciled]`.
- `CostGrantReconciled` carries actual input/output/total token consumption,
  consumed cost microunits, and refund disposition against the reservation.
- Accepted-command replay returns the original receipt and emits no second grant,
  reservation, issue, provider invocation, provider receipt, reconciliation, or
  refund.
- The addendum must freeze exact writer, command/event/schema identities,
  authority subject and scope, target/write-set streams, reducers, projections,
  expected versions, idempotency tuple, concurrency arbitration, expiry/revocation
  behavior, stable rejection codes, receipt bindings, and positive/negative tests.
- The minimal family above is closed. Do not invent a fourth mutation command. If
  expiry/revocation cannot be coherently bound to existing accepted authority without
  another canonical transition, stop and return that exact owner gate.

Versioning:
- New SecretReference, CostGrant, command, and event identities start at 1.0.0.
- Required-field expansion of ProviderCommand or ProviderReceipt uses explicit 2.0.0
  successor identities and explicit reader/reducer compatibility. Do not edit their
  accepted 1.0.0 files.
- Use 1.1.0 only for genuinely optional backward-compatible additions.
- Historical records and every accepted WP6.1/T1a byte remain unchanged.

Required outputs:
1. A normative addendum at
   docs/plans/agentic-research-system/design/
   09-wp6-2-t2-cost-grant-authority-addendum-2026-07-22.md.
2. A strict three-row authority catalogue and strict schema under
   .research-system/contracts/ and .research-system/schemas/contracts/.
3. Strict SecretReference and CostGrant schemas, three command schemas, five event
   schemas, and explicit ProviderCommand/ProviderReceipt successor schemas where the
   accepted T2 bindings require them.
4. A strict schema-identity manifest and companion schema binding every repository
   path, canonical schema ID/version, raw UTF-8/LF SHA-256, ordered event set, reducer,
   projection, stream/write set, authority, receipt, and test identity.
5. Independent literal expected sets, a semantic validator, and binding tests under
   tests/research_system/contracts/. Expected rows must come from P-037/addendum
   authority, never runtime registration, generated schemas, or the implementation
   under test.
6. Negative controls for missing/wrong/expired/revoked/mismatched grants; secret
   sentinel exposure at every named pre-issue producer seam; insufficient balance;
   two-command over-reservation concurrency; stale versions; same idempotency tuple
   with different payload; replay; event-order swap; partial batch; missing reducer or
   projection; alias/version/hash substitution; and attempted mutation of accepted
   ProviderCommand/ProviderReceipt 1.0.0 or WP6.1/T1a bytes.
7. A neutral exact-state handback at
   docs/plans/agentic-research-system/handoffs/trials/
   gate6-wp6-2-t2-authority-addendum-exact-state-handback.md containing the exact
   candidate commit, branch/root, changed paths, validation evidence, addendum and
   identity-manifest Git blob IDs plus raw SHA-256 identities, protected-byte proof,
   unresolved risks, and a ready-to-paste fresh independent-review prompt.

Allowed writes are limited to the named addendum, new T2 contract/schema paths, new
T2 contract-test/helper paths, the T2 exact-state handback, the relevant README index,
and path-specific `.gitattributes` LF entries needed for content-addressed candidate
bytes. Do not modify `research_system/**`, existing WP6.1/T1a artifacts, accepted
ProviderCommand/ProviderReceipt 1.0.0 schemas, Gate 5 artifacts, results, claims, or any
T3/T4/T1b/T5-T8 surface.

Candidate lifecycle:
- Candidate artifacts remain `proposed` and may name the intended independent reviewer
  and acceptor, but must not claim review or acceptance.
- Review and owner acceptance remain external records bound to computed candidate
  identity. Markdown is not the sole acceptance authority.
- Construct repository identity from exact bytes before parsing; then validate those
  same bytes. Keep the hash dependency graph acyclic.

Validation ladder:
1. RED: add literal expected-set and negative fixtures before materialization.
2. GREEN: strict Draft 2020-12 validation with format checking, semantic relations,
   event ordering, idempotency, concurrency/replay invariants, and candidate lifecycle.
3. Focused T2 contract suite plus lint/format for touched test helpers.
4. Existing WP6.1 contract-materialization and Stage-2 acceptance tests unchanged.
5. Full contract framework once at candidate head, plus `git diff --check`, schema
   registry discovery, exact-byte LF checks, and protected-path diff/hash proof.

Commit the candidate using the repository prefix, preferably:
  [PIPELINE] P00: materialize WP6.2 T2 authority addendum
Push only the expected branch. Do not open or merge a PR unless Stephen instructs you.
Do not perform the independent review in this authoring task and do not begin T2 runtime
implementation. Stop after the exact-state handback is committed and pushed, or at the
first genuine authority/path blocker.
```

## Dispatcher completion

Before starting the fresh task, supply the exact pushed SHA of
`pipe/ars-wp6-2-t2-authority-addendum`. The fresh task must reproduce that SHA before
writes. When its exact-state handback returns, assess it here and instantiate the
independent-review prompt against the candidate commit; do not reuse the author task as
reviewer.
