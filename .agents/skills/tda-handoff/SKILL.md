---
name: tda-handoff
description: Use when ending a substantial session, switching agent runtime (Claude Code, Codex, ChatGPT), pausing a task mid-flight, or preserving decisions before context loss — when the state is not already captured in a plan, commit, or vault entry.
---

# TDA Handoff

A compact, research-safe handoff that lets another agent or a future session
continue without re-derivation. It points to artifacts **by path** and never
duplicates their content. Not for APM Manager/Worker handoffs — those use the
numbered APM handoff skills and the Memory Bank. Skip it when the session was
trivial or its outcome is already fully captured in a commit, plan, or vault
entry.

## Where It Goes

Write to `.apm/memory/handoffs/YYYY-MM-DD-<task>.md` (gitignored runtime
state), or wherever the receiving runtime can read. Session commentary worth
preserving long-term goes to the vault daily note via `vault-sync`, not the
handoff.

## Handoff Document

```markdown
# TDL Handoff: <task>

## Purpose of next session
## Active paper / project
## Current state
## Files and artifacts        (paths, not content)
## Commands run               (exact, re-runnable)
## Contracts and validation   (what is bound, what passed)
## Results and provenance     (which result files, PROVISIONAL flags)
## Decisions made             (with vault entry references)
## Open risks
## Suggested skills
## Next actions
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

## Completion Checklist

- [ ] Active paper / project identified.
- [ ] State summarized without duplicating artifacts — paths and commands
      only.
- [ ] Contracts / validation status and result-provenance status included
      (PROVISIONAL flags carried).
- [ ] Decisions listed with vault references.
- [ ] Open risks and suggested next skills included.
- [ ] Do-not-do list tailored to the task.
- [ ] Dispatch-safety elements present if an autonomous agent consumes it.
- [ ] Sensitive details redacted (no UKDA data excerpts, no credentials).

## Escalate Or Stop When

- The handoff would be the only record of a result or decision — that
  belongs in the vault (`vault-sync` / `commit-log`) first; the handoff
  references it.

## Related Skills

`tda-task-brief-from-plan` (when the next session's work deserves a formal
brief) · `commit-log` · `vault-sync` · the numbered APM handoff skills for
APM agents.
