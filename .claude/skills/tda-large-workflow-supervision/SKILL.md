---
name: tda-large-workflow-supervision
description: Use when supervising a large, multi-stage, review-heavy TDL campaign outside APM, especially when exact-state handbacks, fresh-task rotation, bounded context inheritance, or one-cycle delivery control are needed.
metadata:
  version: "1.1.0"
  tier: optional
  lanes: []
  roles:
    - manager
    - orchestrator
  runtime: agnostic
---

# TDA Large-Workflow Supervision

Supervise a large TDL campaign without making one conversation the state store.
This skill is for `workflow_system: standalone`; it does not initiate, recover,
or hand off APM work. If the campaign is APM-managed, stop and use the numbered
APM lifecycle skills instead. Generic role names such as manager, supervisor,
implementer, or reviewer do not establish APM ownership.

This is a tier-3 coordination skill. It may produce briefs, exact-state packets,
review prompts, and handbacks. It may not create paper claims, result artifacts,
canonical computations, or contract-bearing implementations without routing
through the relevant tier-1 or tier-2 skill.

## Initiation
1. Declare `workflow_system: standalone` and choose supervision phase
   `certify` or `deliver` before loading workflow state.
2. Reject numbered APM skills, `.apm` campaign state, the APM Memory Bank, and
   APM guides/checkers. Leave any foreign APM state untouched.
3. Set one vertical action, an exact subject, a context budget, and a rotation
   trigger. Default rotation is first auto-compaction or approximately 80k live
   input tokens, whichever comes first.
4. Select at most two primary skills. Load a conditional skill only when its
   named artifact or assurance trigger exists. The required research-observer
   meta-skill does not count against this budget.
5. Read only OPEN observations matching selected skills plus active
   cross-cutting principles; never dump the complete observation log into the
   task context.
6. Before a non-research assurance control becomes blocking, record its
   research-value disposition: protected asset, credible failure path, why
   existing controls are insufficient, cheapest adequate control, evidentiary
   lifecycle stage, and bounded effort/stop. General hardening defaults to at
   most 10% unless Stephen explicitly elevates it.

## Certification And Delivery

`certify` may reconstruct the wider campaign once. It emits a compact exact-state
packet containing exact revisions, branches, roots, write owners, gate decisions,
unresolved findings, validation evidence, the next vertical action, and hard
stops. The packet points to authorities; it does not copy them.

`deliver` starts fresh from a certified packet. Verify the packet identity and
current repository/remote delta. Read only the selected deliverable's authorities
and dependencies changed since the packet. Reopen a settled gate only when the
delta touches its authority or prerequisite.

Before generation, inventory existing deterministic artifacts and compare their
accepted identities or exact bytes. Regenerate only for a demonstrated mismatch
and within explicit write authority.

Read-only validation governs the launcher as well as the test process. If a suite
resolves historical Git objects, use a history-bearing temporary clone with
`core.autocrlf=false` and `core.longpaths=true`, not `git archive`. Use a verified
external interpreter rather than an environment manager that can create ignored
state in the review root; check ignored residue after hooks.

## Dispatch Envelope

Every implementer or reviewer dispatch records:

- workflow and supervision phase; lifecycle phase;
- exact base, subject, branch, writable root, and write owner;
- one deliverable, allowed paths, forbidden paths, and hard stops;
- context mode, rotation condition, and fork policy;
- at most two primary skills and triggered conditional skills;
- focused, candidate-head, and integration validation boundaries;
- external-review owner, file-count limit, and permitted author-review cycles;
- research-value disposition for each blocking non-research control; and
- management, candidate, review, and integration branch roles plus merge strategy.

Self-contained implementers and independent reviewers receive no parent history
(`fork_turns="none"` in Codex). A small positive fork is allowed only for a direct
continuation with a recorded reason. Full-history inheritance is exceptional and
forbidden after compaction. An implementer owns one vertical deliverable and at
most one author-review-remediation cycle; a new semantic subject gets a fresh task.

A proposed second remediation is a rescope event, not an automatic continuation.
Stop for finding triage and owner ruling; any authorized exception uses a new exact
subject and a fresh task without author/reviewer history.

Stephen triggers and monitors CodeRabbit unless he explicitly delegates that
operation in the current task. Do not poll, wait, schedule, or create review
automations inside a substantive supervision, author, or reviewer task.

## Integration And PR Packaging

Keep management/governance, candidate, review, and integration roles explicit.
Do not make meta-method commits candidate ancestry merely for routing convenience.
An integration branch must preserve an exact accepted candidate as a reachable
ancestor unless a new owner decision authorizes another identity treatment.

Before opening or updating a PR, count merge-base paths with
`git diff --name-only <base>...<head>`. CodeRabbit's hard limit is 100 files;
target 90 or fewer where practical. Split larger work on semantic dependency
boundaries, declare merge order/bases, keep contracts with their review evidence,
and perform a final integration-seam review. Do not squash or rebase away an exact
accepted subject.

## Exact-State Record

At rotation or completion, invoke `tda-handoff` and write to the authorized
neutral project handoff path, never `.apm`. Record packet predecessor identity,
exact current Git/worktree state, decisions, unresolved findings, validation
evidence, one next action, and hard stops. Repository and owner records remain
authoritative; the packet is a continuity aid, not self-attestation.

Also record available efficiency evidence: task/turn count, active duration,
context mode, compactions, inherited turns, validation invocations, regenerated
artifacts, remediation count, external-review waits, and true/false stops. State
when exact token telemetry is unavailable; never replace it with an estimate.

## Self-Test Prompts

- *A standalone supervisor is called a Manager and finds a populated `.apm`
  bus.* -> Leave it untouched; role-name similarity does not confer APM state.
- *An independent reviewer needs a self-contained exact subject.* -> Dispatch
  fresh with no parent history, not a full-history fork.
- *The task reaches first compaction but has an exact-state packet.* -> Rotate;
  do not keep extending the same task because compaction succeeded.
- *CodeRabbit is still running.* -> Return control to Stephen; do not poll or
  wait in the substantive task.
- *A reviewer requests runtime security evidence during contract-only work.* ->
  Apply the research-value/stage gate; defer evidence that needs the runtime
  surface unless separately elevated.
- *A second remediation appears necessary.* -> Stop for rescope and owner ruling;
  do not continue the existing author or reviewer conversation.
- *The proposed PR changes 104 files.* -> Split before external review and record
  the integration seam; do not open an unreviewable PR.

## Completion Checklist

- [ ] Standalone identity and supervision phase declared.
- [ ] One vertical action and exact subject frozen.
- [ ] Packet/delta verified without unnecessary campaign replay.
- [ ] Context, fork, skill, validation, and review-cycle budgets recorded.
- [ ] Existing artifacts certified before any regeneration.
- [ ] Research-value, branch topology, merge strategy, and PR file cap recorded.
- [ ] Neutral exact-state handback emitted at completion or rotation.
- [ ] Efficiency proxies and unavailable telemetry stated without estimation.

## Escalate Or Stop When

- Canonical mutation lacks an accepted writer, command/event identity,
  reducer/projection owner, concurrency rule, or version disposition.
- The exact writable root, subject revision, owner gate, or path scope is
  unresolved.
- A second remediation cycle or post-compaction continuation would be needed.
- PR packaging exceeds the external reviewer's file cap without an authorized,
  dependency-safe split.

## Related Skills

`tda-task-brief-from-plan` (dispatch contract) - `tda-handoff` (neutral
exact-state record) - `research-assurance-triage` (assurance-lane routing) -
numbered APM skills (only when `workflow_system: apm`).
