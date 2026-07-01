# P0 Review and Foundation Implementation Handover Prompt

You are taking over the Agentic Research System (ARS) P0 lane in `C:\Users\steph\TDL` as a fresh agent. Earlier sessions completed and committed the W1–W8 specifications, Gate 3 reconciliation, and the review-pending P0 implementation plan suite. Your job is to close the P0 plan review gate and, only after Stephen explicitly approves the exact scope, implement the narrow production-intended foundation work package by work package.

## Current authority

- Gate 3 W6 v0.3, W7 v0.2, W8 v0.2, and 06c v0.2 are accepted under P-030.
- The P0 materialization/foundation plan suite is committed but remains `review_pending`.
- This handover does not itself authorize implementation, fixture materialization, a control root, live provider use, migration, a pilot, or research claims.
- If Stephen supplies an accepted review or explicitly approves the plan in the new session, record that authority and proceed from the corresponding gate. Otherwise, review first and request approval.

## Repository anchors

- Repository: `C:\Users\steph\TDL`
- Planning root: `C:\Users\steph\TDL\docs\plans\agentic-research-system`
- Branch at handoff: `main`
- P0 plan commit: `9c55cb2fe5dbafe27ccf1dda0feac1d053c110d9`
- Gate 3 acceptance commit: `bdff66f`
- P0 implementation branch after approval: `codex/ars-p0-foundation`
- P0 implementation location after approval: an isolated Git worktree, not the dirty main checkout

At handoff, the ARS planning tree matches `HEAD`. The main checkout also contains unrelated `.superpowers` changes and untracked research result/checkpoint files. Preserve them, do not stage them, and do not use them as P0 evidence.

## Mandatory startup

1. Invoke `task-observer`; read OPEN observations for every skill you load. In particular, apply Observation 11, **“Plans need a forward-obligation scan”** (OPEN, 2026-07-01, `superpowers:writing-plans`).
2. Read repository `AGENTS.md` and obey its cwd/branch checks, GitNexus rules, message-file commit rule, and research-prefixed subjects.
3. Verify cwd, active branch/worktree, `HEAD`, and `git status` before writing.
4. Do not spawn subagents unless Stephen explicitly requests delegation or parallel agent work.
5. Treat the committed plans/specifications as authority; verify live repository state directly and do not rely on memory for current hashes or dirty-state claims.
6. Do not stage or modify unrelated compute, checkpoints, results, vault files, `.apm/`, active contracts, current papers, or the `.superpowers` change.

## First read order

Read these files in order:

1. `docs/plans/agentic-research-system/05-p0-materialization-and-foundation-implementation-plan.md`
2. `docs/plans/agentic-research-system/implementation/README.md`
3. `docs/plans/agentic-research-system/implementation/01-control-plane-and-replay-plan.md`
4. `docs/plans/agentic-research-system/implementation/02-context-routing-and-assurance-plan.md`
5. `docs/plans/agentic-research-system/implementation/03-adapters-and-operations-plan.md`
6. `docs/plans/agentic-research-system/implementation/04-evaluation-and-p0-fixtures-plan.md`
7. `docs/plans/agentic-research-system/reviews/adversarial-gate3-W6-W7-W8-review-reconciliation-2026-07-01.md`
8. `docs/plans/agentic-research-system/design/06c-gate3-foundation-critical-interface-manifest-2026-07-01.md`
9. `docs/plans/agentic-research-system/design/01-system-architecture.md`
10. `docs/plans/agentic-research-system/design/02-task-event-and-artifact-schema.md`
11. `docs/plans/agentic-research-system/design/03-context-memory-and-retrieval.md`
12. `docs/plans/agentic-research-system/design/04-agent-roles-and-model-routing.md`
13. `docs/plans/agentic-research-system/design/05-research-assurance-and-independent-review.md`
14. `docs/plans/agentic-research-system/design/06-evaluation-observability-and-audit.md`
15. `docs/plans/agentic-research-system/design/07-runtime-adapters-and-policy-parity.md`
16. `docs/plans/agentic-research-system/design/08-resource-checkpoint-and-operations.md`
17. `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`
18. `docs/plans/agentic-research-system/04-parallel-specification-and-foundation-pilot-plan.md`

Use narrower source reads when reviewing a specific work package, but complete the master/index/child-plan read before making a gate recommendation.

## P0 scope in one view

The suite defines four separable work packages:

1. **WP1 — control plane and replay:** package/schema foundation, explicit external control root, one writer, immutable objects/receipts, atomic JSONL event batches, pure replay, disposable projections, and CLI.
2. **WP2 — context, routing, and assurance:** immutable context candidates, distinct reference/provider token gates, complete mandatory-source closure, requirement integrity, evidence-derived independence, and deterministic eligibility-first routing.
3. **WP3 — adapters and operations:** canonical provider-neutral policy, semantic parity, normalized commands/receipts, fake and subprocess transports, proportional operational profiles, grants/leases, checkpoints, stop, and recovery.
4. **WP4 — evaluation and fixtures:** W6 schemas/models, trace completeness, non-compensable graders, retention/deletion verification, exact fixture materialization, paired calibration, scenarios A–E, coverage, and release decisions.

Execution order is WP1, then WP2 and WP3 independently, then integrated WP4. WP4 may scaffold against fakes after WP1 but cannot issue a P0 decision until WP1–WP3 pass their review checkpoints.

## Exact materialization closure

The P0 plan names exactly 37 cases:

```text
F-001 F-002 F-003 F-004 F-005
F-007 F-008 F-009 F-010 F-011 F-012 F-013 F-014
F-020 F-021 F-022 F-025 F-026 F-027 F-028
F-031 F-032 F-033 F-034 F-035 F-036
S-001 S-002 S-003 S-004 S-006 S-008 S-009 S-010 S-011 S-012 S-013
```

`F-021` remains priority P1 but has a `p0_materialization` sizing variant required by P-028. Do not relabel it. Deferred Gate 5/pilot cases remain outside this closure, including S-014/S-015/S-016.

## Retention boundary added during plan self-review

W6 explicitly deferred retention durations and deletion verification to the P0 plan. The master plan now proposes:

- R1 redacted command/tool summaries: 180 days;
- R1 operational measurements and grader explanations: 365 days;
- R2 restricted local references: 90 days or earlier source expiry;
- R2 minimized sensitive excerpts: 30 days or earlier source expiry;
- R3 content: prohibited from fixture and trace storage.

Expiring R1/R2 payloads stay outside immutable events, receipts, and the canonical object store in an explicit authorized evidence root. Canonical state retains only R0 identity/hash/policy/consumer/expiry/deletion evidence. Review these durations, owners, extension authorities, replica rules, and `EvidenceDeletionVerified` semantics explicitly; do not silently treat them as accepted defaults.

## Required first gate: adversarial plan review

Unless Stephen provides an already completed review or explicit plan approval, use `adversarial-design-review` and review the master plus all four child plans as one interface suite. The review must attack at least:

- exact compliance with accepted W1–W8/06c semantics;
- forward obligations deferred by the specifications to P0 or Gate 5;
- file ownership and shared-module collisions across work packages;
- undefined or inconsistent test/helper APIs in code snippets;
- command/event/receipt ordering and zero-or-one writer recovery;
- dimensional consistency of token/resource/risk units;
- provider and operational two-stage ordering;
- authority, verifier feasibility, and no-self-approval;
- exact 37-case coverage, priority versus `gate_stage`, and deferred cases;
- retention/minimization/deletion behavior;
- stop conditions, rollback/revertibility, and forbidden migration/live-use paths.

Write a dated review under `docs/plans/agentic-research-system/reviews/`. Do not edit implementation files during the review. Reconcile accepted findings into the plan suite, validate the documentation-only diff, commit it, and request Stephen's explicit approval of the resulting exact scope.

## Implementation startup after explicit approval

After Stephen approves the plan:

1. Confirm the approval in a dated repository decision/reconciliation record and update the plan/index status without broadening scope.
2. Use `superpowers:using-git-worktrees` to create an isolated worktree on `codex/ars-p0-foundation`; do not implement on dirty `main`.
3. Use `superpowers:executing-plans`; use a subagent-driven workflow only if Stephen explicitly authorizes delegation.
4. Start with WP1 Task 1 and follow TDD exactly: failing test, observed failure, minimal implementation, targeted pass, lint, scoped commit, review checkpoint.
5. Before editing any existing function/class/method, run GitNexus upstream impact and warn on HIGH/CRITICAL risk. Before every commit, run `detect_changes(scope: staged)`.
6. Use task-specific commit-message files and `git commit -F`; use `[PIPELINE] P00:` for implementation slices unless a narrower accepted prefix is specified.
7. Use only deterministic fake transports/clocks for P0. Live Claude/Codex smoke requires a separate bounded approval after WP3 review.
8. Require an explicit absolute external control root and evidence root. Never infer either from cwd, and never point tests at the real repository/control state.

## Non-negotiable boundaries

- No migration of T1.28, current APM tasks, either active paper, `.apm/`, legacy buses, existing research results, contracts, caches, or vault state.
- No raw UKDA data, secrets, `.env` contents, hidden reasoning, or full transcripts in contexts, fixtures, traces, events, or reusable packages.
- No live provider command, credentials, broad shell/network grant, long-running process, or real control store without the specific later approval.
- No fixture defect, missing evidence, unavailable independence, or provider outage may become a pass.
- No scientific result or producer `passed` flag may establish its own oracle or paper claim.
- No change to an accepted W1–W8/06c semantic may be smuggled in as implementation; stop and request a versioned decision.
- No P0 release decision authorizes Gate 5, migration, pilot initialization, or claim promotion.

## Verification baseline

Planning-only review changes use:

```powershell
git diff --check
git diff --cached --check
```

Implementation verification follows the exact child-plan commands, with the global baseline:

```powershell
uv run ruff check research_system tools/ars tests/research_system
uv run pytest tests/research_system -q --no-cov
```

At each gate, also verify that unrelated main-checkout files, `.apm/`, active research state, and external control/evidence roots were not touched.

## First-session completion standard

Return one of these evidence-backed outcomes:

1. **Review pending:** review completed and recorded, with required changes awaiting Stephen's decision;
2. **Plan accepted:** review reconciled and Stephen explicitly approved the exact P0 scope, with the isolated implementation worktree ready but no unreviewed code started; or
3. **WP1 in progress/complete:** only if approval was explicit, with exact tests, commits, GitNexus scope, and remaining checkpoint stated.

Always report the live branch/worktree, `HEAD`, files changed, verification commands/results, P0 gate status, and exact next action. Do not imply approval or implementation authority from this handover alone.
