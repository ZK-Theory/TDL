# 06a — WP6.1: Runtime Task Lifecycle and Operator Surface — Dispatch Plan

**Date:** 2026-07-16
**Status:** draft, review pending — authorizes no implementation; dispatch is gated on
Gate 5 close (WP5.6) and Stephen's approval of this plan with its pre-registered
invariant re-baseline (D-G6-3).
**Revision note (2026-07-17):** revised through the R4 remediation review so every one
of the 104 rows binds exact command/event schema identity and authority subject data,
Decision and RuleEvaluation remain non-compensable, the claim is an atomic relationally
bound two-stream batch, and the correction selector is closed. Exact-
set validation compares complete row records rather than independently creditable
component sets. The revision still authorizes no implementation and requires fresh
independent review before
approval.
**Goal:** Materialize the accepted W2 runtime record set and lifecycle (rich Task,
ScopeDefinition, dispatch/claim/lease/attempt, messages, blockers/Partial, artefact
manifests, reviews/decisions/corrections) and the W8 typed operator command surface,
clearing Gate A blockers A4 and A5 with direct current evidence.

**Governing authority:** W2 §§10–21 (accepted v0.3, P-027); W8 §§7–21 (accepted v0.2,
P-030); 06c interface manifest; P-008 (separate state machines), P-009 (immutable
messages), P-010 (Partial/epoch), P-011 (multidimensional artefact authority), P-012
(ScopeDefinition governs completion), P-013 (reviews bind subject hashes), P-020
(single writer), P-022 (graded independence). Parent: `06-wp6-gate6-readiness-and-
integration-plan.md` §3 WP6.1.

---

## 1. Current state (verified in `research_system/` at drafting time)

Present and exercised by P0 fixtures: command service with ledger-allocated atomic
event batches and receipts; strict replay; authority-grant source/resolver (PR #87/#90);
context compiler; routing engine and independence checks; assurance-requirement models;
operations modules (leases, checkpoints, recovery, resources, profiles); eval harness
with release gating and canonical release-decision publication (WP5.3).

Missing (the A4/A5 gap): reducers know only `TaskCreated`, `TaskSuperseded`,
`ReadinessRequested`, and a partial `DispatchClaimed`. There is no rich Task payload
schema, no ScopeDefinition record or command, no attempt/lease/blocker/Partial/message
lifecycle, no runtime artefact-manifest or review/decision command path, and no typed
operator command surface with durable projections.

## 2. Tasks

Each task lands with schema files under `.research-system/`, registered ID kinds,
reducer + projection coverage, and binding tests. Order is the dependency order.

- **T1 — Contract materialization, then rich Task record and ScopeDefinition.** Before
  runtime implementation, materialize and independently review the two exact manifests
  in §3; D-G6-3 acceptance of their content identities releases the implementation
  phase. Then implement W2 §10 Task definition (identity,
  revision, aliases, project, portfolio/scope references, purpose, risk request,
  governing references, readiness preconditions) and the P-012 ScopeDefinition record
  with versioned membership and typed dispositions. Commands: create/supersede/amend-
  by-revision. The schema field and transition catalogue must equal the accepted W2
  §10/§11 owner rows recorded in the literal §3 annex; validating a smaller
  self-consistent schema is a failure. **Binding tests:** missing, extra, wrong-type,
  and stale-revision fields
  are rejected one at a time and atomically; a
  milestone-completion command naming a stale ScopeDefinition revision rejected;
  a completion command omitting a typed disposition for any required member of
  the named revision rejected atomically — an absent tracker row is not a
  disposition (the W0 scope-collapse failure mode: fourteen unlogged Stage-2
  tasks behind a "complete" projection); replay equality across the new record
  set.
- **T2 — Dispatch, claim, lease, attempt.** W2 §12 lifecycle with W8 lease integration
  (the `operations/leases.py` machinery becomes the runtime lease authority);
  idempotency and concurrency per W2 §13. An attempt never silently replaces another
  (P-010 epochs). `ClaimDispatch` uses the exact two-stream envelope/write set and
  ordered `[DispatchClaimed, TaskClaimStarted]` atomic batch in 06d §1.3; both expected
  versions advance together or neither does. **Binding tests:** double-claim contention
  yields exactly one
  holder; two claimants using conflicting payloads yield exactly one holder and one
  conflict; a command replayed with the same idempotency tuple and canonical payload
  returns the original receipt; the same tuple with a different payload is rejected
  as `idempotency_conflict` with no event publication; omitting or staling only the Task
  binding, naming a current foreign Task, staling the Dispatch-to-Task relation, binding
  the lease to another Task/Dispatch, racing the Task stream, or changing the declared
  write set rejects before authority/idempotency reuse with no Task/Dispatch/event/
  receipt-acceptance change; attempt supersession preserves
  the prior attempt's evidence.
- **T3 — Messages, blockers, input-required, Partial.** W2 §§14–15; P-009 immutable
  publication/delivery/acknowledgement events; Partial as both attempt outcome and
  closed Task outcome with claim restrictions and stop reason (P-010). **Binding
  tests:** acknowledgement of a projection never mutates history; a reopen after
  Partial creates a new epoch with the original Partial evidence intact.
- **T4 — Runtime artefact manifests and validation binding.** W2 §16 manifest fields
  (producing task/attempt/model/commit/environment, input hashes, parameters/seeds/
  vintage, contract-validation result, supersession lineage, retention class,
  consumers); availability/integrity/structural/scientific/authority kept as separate
  dimensions (P-011). Large files stay in existing result roots; the control plane
  stores manifests only. **Binding tests:** a manifest whose input hash does not
  resolve is rejected; each consumer policy is tested against availability,
  regenerability, integrity, structural validation, scientific review, and use
  authority independently; no single boolean, aggregate score, or producer assertion
  can mark an artefact usable.
- **T5 — Reviews, decisions, corrections at runtime.** W2 §§17–19 command paths on
  top of the WP5.3a authority resolver: review requests/verdicts bound to exact
  subject hashes (P-013); Decision and RuleEvaluation records; corrections as
  compensating events, never ledger edits (P-020 history rule). **Binding tests:**
  a verdict against a changed subject hash is stale and unusable for acceptance;
  a producer-related or context-ineligible verdict cannot satisfy the required review
  set; `AcceptTask` fails unless the exact review set is satisfied; only authorized
  `ResolveDecision` can resolve a Decision, and a `RuleEvaluation` cannot supply that
  authority; a correction leaves the original event chain intact and replayable. The
  correction tests compare the closed 06d §1.4 mapping against runtime behavior and
  reject unknown/swapped/zero-owner/multiple-owner/missing-governance-index mappings.
  Decision and RuleEvaluation use distinct authority subjects and owner projections;
  cross-scoped grants, cross-projection routing, and coordinated expected/runtime
  substitutions reject without changing either projection or the governance index.
- **T6 — Typed operator command surface.** Register the exact W8 §20 catalogue —
  `request_resource_grant`, `claim_execution_lease`, `record_heartbeat`,
  `request_pause`, `confirm_pause`, `request_stop`, `confirm_stop`, `request_resume`,
  `release_resources`, `quarantine_orphan`, `adopt_late_artefact`, `create_backup`, and
  `verify_restore` — with the owner-token-to-PascalCase `command_type` mapping pinned in
  06d, W2 command envelopes, semantic events, receipts, replay
  reducers, and the operations modules. No implementation-defined alias or smaller
  catalogue satisfies T6. Stop evidence records requested,
  signalled, process-exited, children/writers-closed, and confirmed-clean (the
  programme's §9 stop contract is the same shape). Proportional profiles per P-025:
  the `trivial` profile keeps typed request/grant/lease/terminal-receipt evidence
  with benchmark/checkpoint/heartbeat groups explicitly `not_applicable`.
  **Binding tests:** exact complete-record multiset equality; for every command, valid
  execution emits exactly one receipt and its exact replayable ordered event set, while
  missing/wrong-type authority,
  subject, state/version, idempotency, and evidence fields reject atomically; a
  kill-and-recover scenario (Gate-3 recovery pattern) proves the canonical tail and
  projected state; the full authority attack set and exact subject binding are exercised
  for all 104 catalogue rows, including every W8 row; heartbeat lapse on a
  `long_running` profile produces the W8
  escalation, not silent continuation.
- **T7 — Human-readable projections.** W2 §11 separate lifecycle projections
  (research-governance status vs operational state, P-008): current task, attempt,
  review, decision, queue, and message views as regenerable files; these are the
  durable local operator surfaces A5 names. **Binding tests:** projections rebuild
  byte-identically from replay; deleting every projection loses nothing; arbitrary
  projection edits are ignored as command authority, diagnosed as drift, and cannot
  alter any accepted command outcome.
- **T8 — Binding-suite closure and invariant preservation.** Add the exact-set and
  one-field-at-a-time tests required by §§3–4. WP6.1 adds no W6 fixture package or
  grader-result row: the Gate 5 evaluation corpus and published release evidence stay
  byte-for-byte outside this tranche. The literal no-change baseline in §4 is the
  D-G6-3 contract; any difference is a stop, not a value to normalize into the plan.

## 3. Accepted literal owner-source catalogue

The normative expected set is the 104-row annex
`06d-wp6-1-owner-source-catalogue.md`, SHA-256
`96932fd752362eddb6da2da77bc0b56ccb8e83ced58e93c3b139e3248acb08f7`.
It has one normalized row per W2 §10–§19 command/edge and one row for each of the
thirteen W8 §20 operator commands. Each row independently names the exact runtime
`command_type`, command schema, ordered semantic-event set, event schema, discriminator
and edge, reducer, exact projections or typed selector, authority/precondition, receipt,
distinct positive test, and its closed negative-test profile.

T1 is split into a contract-materialization phase and a runtime-implementation phase.
In the first phase it creates
`.research-system/contracts/wp6-1-owner-source-catalogue.yaml` as a semantic copy of
that exact annex and records the annex path, Git blob ID, SHA-256, and row keys. The
same phase creates the independently reviewed 104-row
`.research-system/contracts/wp6-1-schema-identities.yaml` under the strict
schema and producer/reviewer/acceptor boundary fixed by 06d §1.1. Every complete row
also carries the exact authority subject binding from 06d §1.2; the correction selector
copies the closed mapping in §1.4. Stephen accepts both manifests' exact repository
paths, schema IDs/versions, Git blob IDs, and SHA-256 values in D-G6-3 before the second
phase may implement or register a command.

The exact-set validator expands only the annex's literal closed state classes, then compares
a multiset of complete expected binding records one-to-one with schemas, command types,
runtime registrations, ordered events, discriminators/edges, reducers, projections or
selectors, authority rules, receipts, and distinct tests. Shared implementation code
does not collapse row cardinality. It rejects a missing, extra, duplicate, aliased,
swapped-key, class-incomplete, or hash-mismatched row. Runtime registrations are
comparison input only and can never generate or repair the expected set.

The annex's base negative profile applies missing/wrong/expired authority, prohibited
actor, wrong scope, and wrong authority subject kind/ID to all 104 rows before
version/state checks. Its remaining profiles include one-field missing/wrong-type,
illegal transition,
stale version or subject hash, conflicting payload, idempotency conflict, authority,
independence, compatibility, supersession, and atomic-no-side-effect cases wherever
applicable. Every rejection leaves the event tail and all affected projections
unchanged.
The mutation suite also changes only `command_type`, duplicates a complete binding,
swaps keys, aliases two tests to one callable, removes one reducer/projection, changes a
message discriminator, and changes one ordered event. It also retains a command type
while changing only its schema ID/version/hash, mutates each row's authority binding,
mutates the closed correction mapping, and races the Task side of `ClaimDispatch`.
Each command-specific schema uses `const` for the exact type; the grant, dispatcher,
event, receipt, and WP6 idempotency tuple carry the identical complete versioned command
identity. `ClaimDispatch` binds and atomically validates the exact Task and Dispatch IDs,
revisions/versions, global position/tail, and complete two-stream write set fixed by 06d
§1.3. It also proves the payload Task revision and lease subject equal the Task revision
stored on the accepted Dispatch; a current unrelated Task is not a valid second stream.
A one-sided or relationally mismatched claim cannot publish.

## 4. D-G6-3 invariant table and executable smoke

WP6.1 is a no-change evaluation re-baseline. The old and approved new values are
identical because T8 adds software contract tests, not W6 fixture packages or results.

| Invariant | Exact old | Exact new | Reason and recomputation |
|---|---:|---:|---|
| `fixture_count` | 40 | **40** | `len(selected_fixture_revisions)` in `p0-coverage.yaml`; no package/revision change. |
| `blocked_fixture_count` | 15 | **15** | The frozen fake-transport M/H restriction is unchanged. |
| `fixtures_with_uncalibrated_mutations` | 0 | **0** | No fixture mutation changes. |
| `mutation_calibration` | `calibrated` | **`calibrated`** | Existing two-repetition calibration remains current. |
| `result_count` | 302 | **302** | No required result key is added, removed, or replaced. |
| `candidate_status` | `blocked` | **`blocked`** | The accepted Gate 5 release decision is immutable. |
| `gate5_authorized` | `false` | **`false`** | WP6.1 cannot authorize or republish Gate 5. |
| O15 deletion initiation | `disabled/deferred` | **`disabled/deferred`** | D-G5-2 remains outside WP6.1. |

The mandatory pre- and post-tranche smoke is:

```text
uv run --no-sync ars eval calibrate --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run --no-sync ars eval run --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run --no-sync pytest -q tests/research_system/integration/test_wp6_1_invariant_baseline.py
```

The baseline test asserts all eight rows, including the coverage-manifest O15 omission,
and verifies the tracked Gate 5 coverage, decision, and fixture bytes are unchanged
from the dispatch base. Stephen's D-G6-3 approval cites this exact plan revision before
any tranche executes.

## 5. Sequencing, branches, and review

- One worktree per tranche; suggested split: T1–T3 (`pipe/ars-wp6-1-task-lifecycle`),
  T4–T5 (`pipe/ars-wp6-1-artefacts-reviews`), T6–T7 (`pipe/ars-wp6-1-operator-surface`),
  T8 rides with each. Concurrency cap 3–4. Commits use the full repository
  convention: `[PIPELINE] P00: <description>` subject, body describing the
  change, and the `Co-Authored-By` trailer; pre-commit hooks run on every
  commit, never skipped.
- Review-then-merge on every PR (CodeRabbit concluded pre-merge); adversarial
  implementation review at tranche completion (pattern:
  `reviews/adversarial-wp4-full-review-2026-07-07.md`).
- Worktree `.env` copy per repo convention immediately after `git worktree add`.

## 6. Stop conditions

- Any un-pre-registered change to existing fixture invariants.
- Any code path that lets an operational event (process exit, test pass, merge)
  produce research-governance acceptance (P-008/P-005 violation).
- A second writer or direct ledger append from a worktree (P-020).
- Schema/reducer divergence such that replay of the pre-WP6.1 ledger fails.
- Any missing, extra, duplicate, aliased, class-incomplete, or hash-mismatched
  owner-source catalogue record; any mismatch from the annex hash above; any component-
  set comparison that loses row cardinality/effects; or any test that derives its
  expected catalogue from implemented registrations.

## 7. Research assurance triage

- **Lanes:** Output/Provenance primary; others N/A (no research content).
- Machine-checkable claims are the binding tests named per task above; each is an
  enforcement artifact, not a description.
- **Human-review-only:** whether the operator surface is *usable* enough that controls
  will not be routinely bypassed (04-plan §7 stop rule) — assessed in the tranche
  review with Stephen.

## 8. Out of scope

- Live transports, model profiles, threshold policy (WP6.2).
- Portfolio/Discovery records and admission (WP6.5/WP6.6 — W11 first).
- Any change to eval release gating semantics or the published Gate 5
  ReleaseGateDecision.
- Legacy `.apm/` compatibility writes (P-021; W9 territory).
