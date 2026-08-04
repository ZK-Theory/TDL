---
name: tda-large-workflow-supervision
description: Use when supervising a large, multi-stage, review-heavy TDL campaign outside APM, especially when capability completion, exact-state handbacks, fresh-task rotation, or bounded context inheritance are needed.
metadata:
  version: "1.3.0"
  tier: optional
  lanes: []
  roles:
    - manager
    - orchestrator
  runtime: agnostic
---

# TDA Large-Workflow Supervision

Supervise a large TDL campaign without making one conversation the state store.
This skill is for `workflow_system: standalone`, not APM. If the campaign is
APM-managed, use the numbered APM lifecycle skills; generic role names do not
establish APM ownership.

The named end-to-end capability is the unit of completion; slices, exact
subjects, PRs, reviews, and handoffs are delivery mechanics. Apply the
repository's `Capability-first delivery` rules.

This tier-3 coordination skill may produce briefs, exact-state packets, review
prompts, and handbacks. It may not create claims, results, canonical compute, or
contract implementations without a relevant tier-1 or tier-2 skill.

## Initiation

1. Declare `workflow_system: standalone` and choose supervision phase
   `certify` or `deliver` before loading workflow state.
2. Reject numbered APM skills, `.apm` campaign state, the APM Memory Bank, and
   APM guides/checkers. Leave any foreign APM state untouched.
3. Set one observable end-to-end capability, its state, next production action,
   and rotation trigger. The action has an exact subject; the campaign does not
   end with that subject. Rotate after actual compaction makes the task an
   unreliable continuation surface, not at an estimated token threshold.
4. Load only skills required by the action or an observed assurance trigger;
   fixed skill counts are not evidence of efficiency.
5. Read only matching OPEN observations and active cross-cutting principles.
6. Before non-research assurance blocks delivery, record its protected asset,
   credible failure, insufficiency of current controls, cheapest adequate
   control, evidence stage, and effort bound. General hardening defaults to at
   most 10% unless Stephen elevates it.

## Capability Campaign Contract

Record `NOT RUNNABLE`, `RUNNABLE`, `PROVEN`, `INTEGRATED`, or `OWNER-BLOCKED`.
Until `INTEGRATED`, reports lead with `Capability status: INCOMPLETE - <exact
functional gap>`. Never promote a locally complete slice to campaign completion.

Build a thin real production or public path first. Required dependencies found
while doing so remain in the campaign unless they require an owner-only action,
external authority, protected-byte mutation, or are demonstrably unrelated.
Plans, mechanics harnesses, synthetic evidence, nominal tests, accepted
fragments, intermediate PRs, and handoffs do not establish completion.

## Certification And Delivery

`certify` may reconstruct the campaign once. It emits an identity-based packet
with revisions, branches, roots, owners, gates, findings, evidence, capability
state, next action, and hard stops. It points to authorities rather than copying
them.

`deliver` starts fresh from a certified packet. Verify the packet identity and
current repository/remote delta. Read only the next action's authorities and
dependencies changed since the packet. Reopen a settled gate only when the
delta touches its authority or prerequisite.

Before generation, inventory existing deterministic artifacts and compare their
accepted identities or exact bytes. Regenerate only for a demonstrated mismatch
and within explicit write authority.

Read-only validation also governs the launcher. Historical-Git suites require a
history-bearing temporary clone with `core.autocrlf=false` and
`core.longpaths=true`; use a verified external interpreter and check ignored
residue after hooks.

## Dispatch Envelope

Every implementer or reviewer dispatch records:

- workflow and supervision phase; lifecycle phase;
- named capability, current state, completed production path, exact remaining
  functional gap, and next production action;
- exact base, subject, branch, writable root, and write owner;
- one bounded contribution to the named capability, allowed paths, forbidden
  paths, and hard stops;
- context mode, observable rotation condition, and fork policy;
- required skills and the reason or trigger for each;
- focused, candidate-head, and integration validation boundaries;
- external-review owner, file-count limit, and final acceptance-review boundary;
- research-value disposition for each blocking non-research control; and
- management, candidate, review, and integration branch roles plus merge strategy.

Independent reviewers receive no parent history (`fork_turns="none"` in Codex).
For implementation, choose the least costly context mode that still carries the
required evidence: a fresh task for a new or independence-sensitive subject, or
a bounded continuation when replaying the same evidence would cost more. Record
the reason. Never use full-history inheritance after actual compaction. An
implementer owns one bounded vertical contribution, while the supervisor retains
ownership of the capability across contributions and PRs.

During construction, use direct tests and proportionate review; ordinary defects
or missing dependencies required by the capability stay in the campaign. Do not
force an independent acceptance cycle after every construction step. Once an
integrated candidate exercises the real end-to-end path, conduct the required
final independent review and one bounded remediation. A proposed second final
acceptance remediation is a rescope event requiring finding triage and owner
ruling; it does not make the incomplete capability complete.

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

When the file cap requires multiple PRs, keep one campaign status across them.
Each accepted PR is an integration milestone. After the final seam lands,
exercise the assembled end-to-end capability before claiming `INTEGRATED`.

CodeRabbit review binds a commit, not a PR. Before merging, filter
`gh api .../pulls/N/reviews` to the configured reviewer, take the latest
`commit_id`, and compare it with `gh pr view N --json headRefOid`. A later
commit makes the current bytes unreviewed.

## Exact-State Record

At rotation or completion, invoke `tda-handoff` and write to the authorized
neutral project handoff path, never `.apm`. Record packet predecessor identity,
capability state, completed production path, exact remaining functional gap,
next production action, exact current Git/worktree state, decisions, unresolved
findings, validation evidence, and hard stops. Repository and owner records
remain authoritative; the packet is a continuity aid, not self-attestation or
completion evidence.

Do not burden the producer handoff with self-reported efficiency metrics. Audit
token efficiency separately from session JSONL and `ccusage codex session` (or
equivalent billing telemetry), using stable task/session identifiers.

## Self-Test Prompts

- *A standalone supervisor is called a Manager and finds a populated `.apm`
  bus.* -> Leave it untouched; role-name similarity does not confer APM state.
- *CodeRabbit is still running.* -> Return control to Stephen; do not poll or
  wait in the substantive task.
- *A construction test exposes another required missing producer.* -> Keep it
  in the capability campaign and implement it within scope; do not call the
  preceding slice complete and abandon the dependency to a handoff.
- *A second final acceptance remediation appears necessary.* -> Stop for
  rescope and owner ruling; report the capability as incomplete.
- *The proposed PR changes 104 files.* -> Split before external review and
  record the integration seam; keep the campaign active across the PRs.

## Completion Checklist

- [ ] Standalone identity and supervision phase declared.
- [ ] Named end-to-end capability, state, real seam, and next production action
      recorded.
- [ ] The completed production path and exact remaining functional gap are
      explicit; local slice completion is not reported as campaign completion.
- [ ] Packet/delta verified without unnecessary campaign replay.
- [ ] Context mode, observable rotation trigger, required skills, validation,
      and final acceptance-review boundary recorded.
- [ ] Existing artifacts certified before any regeneration.
- [ ] Research-value, branch topology, merge strategy, and PR file cap recorded.
- [ ] A real end-to-end path has been exercised before `INTEGRATED` is claimed.
- [ ] No required capability dependency is disposed only to a PR comment,
      plan, handoff, or unnamed successor.
- [ ] Neutral exact-state handback emitted at completion or rotation.

## Escalate Or Stop When

- The exact writable root, subject revision, owner gate, or path scope is
  unresolved.
- A required owner decision is absent, destructive or external action authority
  is absent, protected bytes must change, or authoritative contracts demonstrably
  contradict one another.
- A second final acceptance remediation requires rescope and owner ruling.
- PR packaging exceeds the external reviewer's file cap without an authorized,
  dependency-safe split.

## Related Skills

`tda-task-brief-from-plan` (dispatch contract) - `tda-handoff` (neutral
exact-state record) - `research-assurance-triage` (assurance-lane routing) -
numbered APM skills (only when `workflow_system: apm`).
