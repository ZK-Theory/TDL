# Large-Workflow Supervision Guide

**Status:** Active advisory guidance from 2026-07-22
**Workflow system:** Standalone TDL supervision; not APM

Use this guide for multi-stage, review-heavy campaigns whose coordination state
would otherwise accumulate in one long task. It preserves exact-state assurance
while moving continuity into small, inspectable artifacts. APM skills, state,
Memory Bank, guides, and checkers remain unchanged and out of scope.

## Start One Supervision Phase

Declare either:

- `certify`: reconstruct the broader campaign once and emit an exact-state
  packet; or
- `deliver`: start fresh from a certified packet, verify its identity and the
  current delta, then supervise one vertical deliverable.

Set the lifecycle phase, exact subject, one next action, writable root and owner,
at most two primary skills, conditional skill triggers, validation ladder,
review-cycle limit, and hard stops before dispatch.

## Context And Rotation

The advisory supervisor budget is first auto-compaction or approximately 80k
live input tokens. Rotate at the first trigger; do not treat successful
compaction as permission to retain campaign state in the same conversation.

Self-contained implementers and independent reviewers start without inherited
conversation history (`fork_turns="none"` in Codex). Use a small positive fork
only for a direct continuation and record the reason. Never use full-history
inheritance after compaction.

An implementer receives one vertical deliverable and at most one
author-review-remediation cycle. A reviewer receives one exact subject. A new
semantic subject requires a fresh reviewer and a new exact-state record.

## Exact-State Packet

Keep the packet compact and identity-based:

```yaml
schema: tdl.large-workflow-state/v1
campaign_id: <stable-id>
workflow_system: standalone
snapshot_utc: <timestamp>
base_revision: <sha>
active_units:
  - id: <unit-id>
    lifecycle_phase: <phase>
    branch: <branch>
    worktree: <absolute-path>
    subject_revision: <sha>
    write_owner: <task-or-agent>
    status: ready | active | review | blocked | accepted | complete
owner_gates: []
unresolved_findings: []
validation_evidence: []
next_vertical_action: <one action>
hard_stops: []
```

Name a predecessor packet identity when replacing a packet. Verify repository,
remote, and owner records independently; the packet is not self-authoritative.
Point to plans and reviews rather than copying them.

## Delivery Intake

1. Verify cwd, branch attachment, status, packet hash, base revision, and write
   authority.
2. Fetch the current remote when remote state matters. If the base advanced,
   inspect only the commit/path delta first.
3. Reopen a settled gate only if that delta touches its authority or prerequisite.
4. Certify existing deterministic artifacts by identity or exact bytes before
   authorizing regeneration.
5. For canonical mutations, require accepted writer, command/event/schema
   identities, reducers/projections, streams, concurrency/idempotency rules, and
   versioning. Missing authority stops dispatch for a reviewed addendum.

## Validation And Review

- Edit loop: focused red/green checks and lint for touched behavior.
- Candidate head: affected package or contract gate.
- Integration candidate: full relevant gate once.
- Later exact-head changes: validation proportional to the changed semantic
  surface, with no old-head claim reused silently.

Stephen triggers and monitors CodeRabbit unless he explicitly delegates that
operation in the current task. A substantive supervisor, author, or reviewer
does not poll, wait, schedule, or create review automations.

## Rotation Or Completion Record

Use `tda-handoff` at the authorized neutral project handoff path. Include exact
Git/worktree state, packet predecessor, decisions, unresolved findings,
validation evidence, rotation evidence, one next vertical action, and hard
stops. Do not write standalone state under `.apm`.

## Deferred Enforcement

This method is advisory. A mandatory dispatch checker, negative controls, and a
`CONVENTIONS.md` lock remain deferred until a completed
implementation-review-remediation cycle provides further trial evidence.
