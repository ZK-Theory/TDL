# WP6.2 T2 Standalone Context-Budget V2 Prompt

**Created:** 2026-07-22
**Trial:** `gate6-wp6-2-t2-context-budget-v2`
**Purpose:** Test delivery supervision from the certified V1 packet without replaying
campaign intake or importing APM lifecycle machinery.

## Paste into a fresh supervision task

```text
Supervise trial `gate6-wp6-2-t2-context-budget-v2` for exactly one deliverable: WP6.2
T2, the typed credential and cost pre-issue boundary.

Runtime recommendation:
  model: gpt-5.6-sol
  reasoning_effort: high

Trial envelope:
  workflow_system: standalone
  lifecycle_phase: implement_review_remediate
  supervision_phase: deliver
  context_mode: fresh
  context_budget_tokens: 80000
  rotation_trigger: first auto-compaction or approximately 80000 live input tokens
  fork_turns: none for the implementer and independent reviewer
  supervisor_primary_skills: [tda-task-brief-from-plan]
  supervisor_conditional_skills: [tda-handoff at rotation or final handback]
  external_review_owner: stephen
  author_review_cycle: 1

This is standalone TDL supervision, not an APM-managed process. Do not invoke numbered
APM skills, read or update `.apm` campaign state, use the APM Memory Bank, or apply APM
guides/checkers. The generic terms supervisor, implementer, and reviewer do not confer
APM lifecycle ownership. Invoke research-observer as the required meta-skill; it does
not count against the primary-skill budget.

Authoritative starting packet:
  path: docs/plans/agentic-research-system/handoffs/trials/gate6-wp6-2-context-budget-v1-exact-state-handback.md
  sha256: 209f1cd1f83fd2051d9da1738c4cea58b9262ccd6e5a79a7926dddf85b2e1e4f
  snapshot_main: efcecd8669fb225061c6eaf300e31bc07d352f6e

Start procedure:
1. Verify cwd, repository, detached/attached state, status, and the packet SHA-256.
2. Fetch origin. Compare current origin/main with the packet snapshot. If unchanged,
   accept the packet as the intake baseline. If advanced, inspect the commit/path delta
   only. Reopen a bound gate only when the delta touches its authority or prerequisite.
   Do not repeat the full WP6.1/T1a review history by default.
3. Read AGENTS.md, the packet, the WP6.2 plan's T2 definition, dependency DAG,
   pre-issue matrix, sequencing, stop conditions, and only the code/contracts needed to
   determine T2's exact path scope. Do not front-load unrelated WP6 tasks or reviews.
4. Confirm that T1a acceptance remains current and T2 remains the sole next eligible
   deliverable. Any contrary current evidence is a hard stop.
5. Produce a self-contained T2 brief before dispatch. It must name exact base, unique
   pre-created task branch, exact writable worktree root, allowed and forbidden paths,
   one deliverable, implementer skills, focused tests, candidate-head gates, reviewer
   independence, one remediation cycle, and stop conditions. Do not dispatch while
   path scope is unresolved.

Implementer routing:
- Fresh self-contained task with fork_turns: none.
- Primary skills: schema-contract-design and contract-first-tdd.
- Conditional skill: tda-agent-safety-guardrails, triggered specifically by credential
  secrecy, cost reservation, and pre-invocation fail-closed boundaries.
- The implementer owns only the named T2 worktree and allowed paths. It must verify
  branch attachment before writes and must not bypass hooks.

T2 required surface:
- An opaque, byte-free SecretReference with provider/credential class, resolver
  identity/version, allowed scope, expiry, and redaction proof.
- Resolved use bound to the exact Task, dispatch, attempt, route/profile, adapter
  revision, and ProviderCommand.
- A CostGrant bound to those identities, currency/rate evidence, input/output/total
  token and cost-microunit ceilings, reserved/consumed/refunded amounts, expiry, and
  idempotency identity.
- One project writer atomically reserves sufficient grant before transport invocation
  and reconciles receipt actuals afterward.
- The complete T2 negative matrix perturbs the consumed pre-issue seams and proves
  zero invocation plus byte-identical canonical stores. A typed non-secret rejection
  may be returned but not canonically published.

Hard exclusions:
- T3, T4, every live provider call, T1b, T5-T8, M/H eligibility, research computation,
  results, claims, Gate 5 mutation, third-family providers, autonomous downgrade/cost
  optimization, secret bytes on any context/provider/canonical surface, and S-016
  changes.
- Do not regenerate accepted WP6.1 or T1a artifacts.
- Do not trigger, poll, wait on, or schedule CodeRabbit. Stephen owns it.

Validation and review:
1. During implementation use focused red/green tests for each T2 contract and negative
   seam, plus lint/format for touched code.
2. At candidate head run the affected package/contract gates, hooks, and git diff
   checks. Run a full integration gate only if the plan requires it at this boundary or
   focused evidence reveals broader risk.
3. Dispatch a fresh independent reviewer with fork_turns: none against one exact
   subject. The reviewer must not receive the implementer's conversation history.
4. Permit at most one bounded remediation cycle for valid findings. A new semantic
   subject after that requires a fresh task/reviewer or handback.
5. Stop after T2 is accepted or at the first genuine blocker/owner gate. Do not begin
   T3 or T4.

Trial measurements:
- compactions and approximate context at rotation;
- every task's context mode, fork_turns, model, and reasoning level;
- primary/conditional skills and each conditional trigger;
- packet verification and delta-only reads versus repeated campaign reads;
- certification reuse versus regeneration;
- focused, package/contract, and full validation commands/counts;
- author-review-remediation cycles;
- external-review waits inside supervision;
- dropped requirements, false stops, stale-state decisions, or assurance weakening;
- exact final branch/head/worktree, findings, gates, and next action.

At completion or rotation, invoke tda-handoff with the explicit neutral path
docs/plans/agentic-research-system/handoffs/trials/. Do not write under `.apm`. Return
the exact-state V2 handback to the instruction-design task for assessment before any
general method integration.
```
