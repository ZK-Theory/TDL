---
name: tda-handoff
description: Use when ending a substantial session, switching agent runtime (Claude Code, Codex, ChatGPT), pausing a task mid-flight, or preserving decisions before context loss — when the state is not already captured in a plan, commit, or vault entry.
metadata:
  version: "1.3.0"
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

A handoff preserves continuity; it is not capability-completion evidence. When
the named capability is incomplete, say so first and carry the exact functional
gap forward rather than presenting the completed slice as the deliverable.

## Where It Goes

For `workflow_system: standalone`, write to the explicitly authorized neutral
repository path, normally the active project's existing `handoffs/` directory.
If the project has no handoff directory, use `docs/handoffs/` only when that
path is in scope; otherwise return the handback in the final response and ask
the receiver to place it. Never default standalone state into `.apm`.

New standalone handoff filenames use a collision-resistant ULID prefix, minted
with `python tools/system_record_id.py --handoff-slug <short-slug>`. Do not scan
for the highest numeric prefix and increment it: parallel sessions can choose
the same number. Historical numeric filenames remain unchanged. A project may
retain a descriptive suffix, but the 26-character ULID is the record identity.

APM work does not use this skill: its numbered APM handoff skills own paths and
Memory Bank state. Session commentary worth preserving long-term goes to the
vault daily note via `vault-sync`, not the handoff.

## Handoff Document

```markdown
# TDL Handoff: <task>

Capability status: <INCOMPLETE - exact functional gap | INTEGRATED>

## Purpose of next session
## Active paper / project
## Named end-to-end capability
## Capability state           (NOT RUNNABLE | RUNNABLE | PROVEN | INTEGRATED | OWNER-BLOCKED)
## Completed production path  (real entry point through durable/public effect)
## Exact remaining functional gap
## Next production action
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
## Rotation evidence          (actual compaction/owner stop, when applicable)
## Branch / integration state (roles, base, merge strategy, PR path count)
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

Classify every discovered item as required capability work, owner-only,
external, or unrelated. Required capability work must name the next production
action and may not be disposed merely to the handoff, a PR comment, a plan, or
an unnamed successor. `OWNER-BLOCKED` may be used only after safe authorized
work is exhausted and the exact missing owner action is recorded.

Before an autonomous successor acts on inherited deliverable, blocker,
contract, input-root, or output-path claims, re-run the associated task-state
manifest through
`python -m shared.manager_dispatch_check ... --state-manifest <yaml>`. During the
warning-first calibration period, carry each warning into the handoff's open
risks with an explicit disposition.

A hard-stop gated on a precondition must state, in the same place, what
remains forbidden once the precondition clears — not only that the stop
applies until then. The precondition clearing is exactly the moment a
successor reaches for the action; a document that only says "don't, until Y"
hands the reader a green light the moment Y holds and loses the constraint
that was meant to survive it (e.g. "the path opens once Y lands, but issuing
this record is still a multi-party/owner action, not yours" — state the
surviving constraint explicitly, don't defer it to a later document).

Before naming a step actionable ("write the record", "issue the grant"),
confirm a production path — not only a test double — performs it: grep for a
non-test caller of the writer/issuer. If only test fixtures construct the
object or the resolver, label the step "tooling to be built", not "action to
be taken", and name the missing production writer/issuer/runner.

An exact-subject handoff (a review or continuation pinned to a specific
commit/branch) must bind that identity to a concrete, provisioned checkout —
name the exact worktree path and confirm its branch, HEAD, and clean status —
not only state the SHA in prose. A SHA is evidence that a commit exists; a
clean worktree at that SHA is the route the next agent can actually use, and
prose identifiers alone leave a fresh agent starting from an arbitrary
current checkout, reporting subject drift instead of reviewing.

For a standalone large workflow, hand off when actual compaction or an owner stop
makes another task the better continuation surface. Record one next vertical
action, capability state, completed production path, exact remaining functional
gap, exact Git/worktree identities, unresolved findings, validation evidence,
and hard stops; do not copy plans, reviews, or logs into the packet. A PR-ready
or reviewed slice may close its bounded task, but the handoff must retain
`Capability status: INCOMPLETE` until the campaign reaches `INTEGRATED`. Measure
token efficiency separately from session JSONL and billing/token telemetry;
producer self-reporting is not required in this continuity artifact.
Before a PR handoff, record the merge-base changed-path count and the external
review cap; CodeRabbit's hard limit is 100 files.

## Completion Checklist

- [ ] Active paper / project identified.
- [ ] Capability status is first, with the named end-to-end capability,
      completed production path, exact remaining gap, and next production action.
- [ ] Local slice, review, PR, or handoff completion is not reported as
      capability completion.
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
- [ ] Large-workflow closeout includes the required branch/integration state
      and PR file count.
- [ ] Sensitive details redacted (no UKDA data excerpts, no credentials).

## Escalate Or Stop When

- The handoff would be the only record of a result or decision — that
  belongs in the vault (`vault-sync` / `commit-log`) first; the handoff
  references it.

## Related Skills

`tda-task-brief-from-plan` (when the next session's work deserves a formal
brief) · `commit-log` · `vault-sync` · the numbered APM handoff skills for
APM agents · `tda-large-workflow-supervision` (observable rotation).
