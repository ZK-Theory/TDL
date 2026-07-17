# 06a — WP6.1: Runtime Task Lifecycle and Operator Surface — Dispatch Plan

**Date:** 2026-07-16
**Status:** draft, review pending — authorizes no implementation; dispatch is gated on
Gate 5 close (WP5.6) and Stephen's approval of this plan with its pre-registered
invariant re-baseline (D-G6-3).
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

- **T1 — Rich Task record and ScopeDefinition.** W2 §10 Task definition (identity,
  revision, aliases, project, portfolio/scope references, purpose, risk request,
  governing references, readiness preconditions) and the P-012 ScopeDefinition record
  with versioned membership and typed dispositions. Commands: create/supersede/amend-
  by-revision. **Binding tests:** schema-invalid create rejected atomically; a
  milestone-completion command naming a stale ScopeDefinition revision rejected;
  a completion command omitting a typed disposition for any required member of
  the named revision rejected atomically — an absent tracker row is not a
  disposition (the W0 scope-collapse failure mode: fourteen unlogged Stage-2
  tasks behind a "complete" projection); replay equality across the new record
  set.
- **T2 — Dispatch, claim, lease, attempt.** W2 §12 lifecycle with W8 lease integration
  (the `operations/leases.py` machinery becomes the runtime lease authority);
  idempotency and concurrency per W2 §13. An attempt never silently replaces another
  (P-010 epochs). **Binding tests:** double-claim contention yields exactly one
  holder; a command replayed with the same idempotency key is a no-op with the
  original receipt; attempt supersession preserves the prior attempt's evidence.
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
  resolve is rejected; no single boolean can mark an artefact `accepted`.
- **T5 — Reviews, decisions, corrections at runtime.** W2 §§17–19 command paths on
  top of the WP5.3a authority resolver: review requests/verdicts bound to exact
  subject hashes (P-013); Decision and RuleEvaluation records; corrections as
  compensating events, never ledger edits (P-020 history rule). **Binding tests:**
  a verdict against a changed subject hash is stale and unusable for acceptance;
  a correction leaves the original event chain intact and replayable.
- **T6 — Typed operator command surface.** W8 issue/start/checkpoint/heartbeat/stop/
  resume/review/accept as registered commands with receipts and replay reducers,
  wired to the existing operations modules; stop evidence records requested,
  signalled, process-exited, children/writers-closed, and confirmed-clean (the
  programme's §9 stop contract is the same shape). Proportional profiles per P-025:
  the `trivial` profile keeps typed request/grant/lease/terminal-receipt evidence
  with benchmark/checkpoint/heartbeat groups explicitly `not_applicable`.
  **Binding tests:** every operator command emits exactly one receipt and replayable
  event; a kill-and-recover scenario (Gate-3 recovery pattern) proves the canonical
  tail and projected state; heartbeat lapse on a `long_running` profile produces the
  W8 escalation, not silent continuation.
- **T7 — Human-readable projections.** W2 §11 separate lifecycle projections
  (research-governance status vs operational state, P-008): current task, attempt,
  review, decision, queue, and message views as regenerable files; these are the
  durable local operator surfaces A5 names. **Binding test:** projections rebuild
  byte-identically from replay; deleting every projection loses nothing.
- **T8 — Fixture extension and invariant re-baseline.** Extend the P0/P1 fixture set
  to the new lifecycle surfaces per the reserved rows that 06-evaluation assigns to
  affected interfaces; pre-register the exact invariant changes (fixture_count,
  result_count) in this plan's final revision before dispatch (D-G6-3). Existing
  fixture results must not drift except where pre-registered — drift is a stop
  condition.

## 3. Sequencing, branches, and review

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

## 4. Stop conditions

- Any un-pre-registered change to existing fixture invariants.
- Any code path that lets an operational event (process exit, test pass, merge)
  produce research-governance acceptance (P-008/P-005 violation).
- A second writer or direct ledger append from a worktree (P-020).
- Schema/reducer divergence such that replay of the pre-WP6.1 ledger fails.

## 5. Research assurance triage

- **Lanes:** Output/Provenance primary; others N/A (no research content).
- Machine-checkable claims are the binding tests named per task above; each is an
  enforcement artifact, not a description.
- **Human-review-only:** whether the operator surface is *usable* enough that controls
  will not be routinely bypassed (04-plan §7 stop rule) — assessed in the tranche
  review with Stephen.

## 6. Out of scope

- Live transports, model profiles, threshold policy (WP6.2).
- Portfolio/Discovery records and admission (WP6.5/WP6.6 — W11 first).
- Any change to eval release gating semantics or the published Gate 5
  ReleaseGateDecision.
- Legacy `.apm/` compatibility writes (P-021; W9 territory).
