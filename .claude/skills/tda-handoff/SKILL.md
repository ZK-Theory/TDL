---
name: tda-handoff
description: Use when ending a substantial session, switching agent runtime (Claude Code, Codex, ChatGPT), pausing a task mid-flight, or preserving decisions before context loss — when the state is not already captured in a plan, commit, or vault entry.
metadata:
  version: "1.1.0"
  tier: core
  lanes: []
  roles:
    - manager
    - operator
  runtime: agnostic
---

# TDA Handoff

A compact, research-safe handoff that lets another agent or a future session
continue without re-derivation. It points to artifacts **by path** and never
duplicates their content. Not for APM Manager/Worker handoffs — those use the
numbered APM handoff skills and the Memory Bank. Skip it when the session was
trivial or its outcome is already fully captured in a commit, plan, or vault
entry.

## Where It Goes

For `workflow_system: standalone`, write to the explicitly authorized neutral
repository path, normally the active project's existing `handoffs/` directory.
If the project has no handoff directory, use `docs/handoffs/` only when that
path is in scope; otherwise return the handback in the final response and ask
the receiver to place it. Never default standalone state into `.apm`.

APM work does not use this skill: its numbered APM handoff skills own paths and
Memory Bank state. Session commentary worth preserving long-term goes to the
vault daily note via `vault-sync`, not the handoff.

## Handoff Document

```markdown
# TDL Handoff: <task>

## Purpose of next session
## Active paper / project
## Current state
## Workflow system            (standalone; otherwise use the owning workflow)
## Packet predecessor         (path plus content identity, when applicable)
## Files and artifacts        (paths, not content)
## Commands run               (exact, re-runnable)
## Contracts and validation   (what is bound, what passed)
## Results and provenance     (which result files, PROVISIONAL flags)
## Decisions made             (with vault entry references)
## Open risks
## Suggested skills
## Next actions
## Rotation evidence          (budget/compaction trigger, when applicable)
## Branch / integration state (roles, base, merge strategy, PR path count)
## Efficiency evidence        (turns, duration, tests, regeneration, waits)
## Do-not-do list
## Sensitive information redacted
```

## Default Do-Not-Do Entries

- Do not bypass pre-commit hooks.
- Do not overwrite archived or date-suffixed result JSONs.
- Do not treat unverified literature leads as sources.
- Do not implement against a math contract authored by the implementing
  agent.
- Do not write P01-A applied interpretation into P01-B methods sections.
- Do not silently change sample counts — cite `sample_provenance.fitted`.
- Do not write toy/synthetic output into `results/` — that tree is for real,
  provenance-tracked compute only.

Trim entries that cannot apply to the next session; add task-specific ones.

## Dispatch Safety

When the handoff will be consumed by an autonomous agent (not a person
resuming), it must additionally: bound scope with explicit hard stops
("continue X only; do NOT proceed to Y"); restate any user-decision gates as
**blocking**, not advisory; and repeat the `results/` provenance rule above.
An open-ended handoff is read maximally by an autonomous agent.

For a standalone large workflow, handoff is also required at first
auto-compaction or the declared context-budget threshold. Record one next
vertical action, exact Git/worktree identities, unresolved findings, validation
evidence, and hard stops; do not copy plans, reviews, or logs into the packet.
For a completed delivery cycle, also record remediation count, true/false stops,
external-review waits, validation invocations, regenerated artifacts, and exact
token telemetry when available. If unavailable, say so rather than estimating.
Before a PR handoff, record the merge-base changed-path count and the external
review cap; CodeRabbit's hard limit is 100 files.

## Completion Checklist

- [ ] Active paper / project identified.
- [ ] Workflow system and neutral path are explicit; standalone state is not
      stored under `.apm`.
- [ ] State summarized without duplicating artifacts — paths and commands
      only.
- [ ] Contracts / validation status and result-provenance status included
      (PROVISIONAL flags carried).
- [ ] Decisions listed with vault references.
- [ ] Open risks and suggested next skills included.
- [ ] Do-not-do list tailored to the task.
- [ ] Dispatch-safety elements present if an autonomous agent consumes it.
- [ ] Large-workflow closeout includes branch/integration state, PR file count,
      and available efficiency evidence without invented telemetry.
- [ ] Sensitive details redacted (no UKDA data excerpts, no credentials).

## Escalate Or Stop When

- The handoff would be the only record of a result or decision — that
  belongs in the vault (`vault-sync` / `commit-log`) first; the handoff
  references it.

## Related Skills

`tda-task-brief-from-plan` (when the next session's work deserves a formal
brief) · `commit-log` · `vault-sync` · the numbered APM handoff skills for
APM agents Â· `tda-large-workflow-supervision` (context-budget rotation).
