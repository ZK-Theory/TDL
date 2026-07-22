# Large-Workflow Context Budget and Orchestration Protocol

**Date:** 2026-07-22
**Status:** ADVISORY INTEGRATION APPROVED by Stephen on 2026-07-22; active as
guidance, not a mandatory checker or convention lock
**Scope:** Large, multi-stage, review-heavy workflows such as ARS WP5/WP6
**Workflow system:** Standalone TDL supervision. APM lifecycle, Memory Bank, skills,
state, guides, and checkers are out of scope and remain unchanged.
**Owner decision:** On 2026-07-22 Stephen clarified that this process is independent of
APM. V1 validated certification and rotation. V2 validated standalone delta reuse and
fail-closed supervision by stopping at a genuine missing T2 transition authority. The
advisory integration surface below was activated by Stephen on 2026-07-22.

## 1. Problem

WP5 and WP6 preserved strong assurance but paid repeatedly for conversational history.
The largest WP6 Manager record reached 54 turn contexts, 15 compactions, a final
195k-token input context, and 549.9 million cumulatively reported input tokens, 98.7%
cached. About 40% of its substantive orchestration calls were waits. Seven of 21
subagent launches inherited full Manager history at parent contexts of roughly
102k-209k tokens, including nominally independent reviews.

This was not primarily a prose-length problem. It was a state-placement problem:
campaign state remained in a conversation, so every later action replayed it.

The protocol must preserve the controls that found real WP5/WP6 defects: exact
revision identity, independent review, owner gates, binding tests, negative controls,
worktree ownership, and fail-closed behavior.

## 2. Proposed rules

### 2.1 Campaign state is an artifact

Every large workflow maintains one compact campaign-state packet outside the model
conversation. It contains exact identities and current decisions, not copied plans or
logs. A fresh supervisor reconstructs from this packet plus the named authorities.

Required fields:

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

The packet is replaced only by a newer packet that names its predecessor identity.
It is not self-authoritative: repository and owner records remain the verdict.

### 2.2 Separate certification intake from delivery supervision

Certification/intake may reconstruct a campaign broadly and emit the first exact-state
packet. Delivery supervision starts fresh from that packet, verifies its hash and
current remote delta, and reads only the selected deliverable's authorities plus files
changed since the packet. It must not repeat the full campaign reconstruction unless
the delta invalidates the packet. Either phase may rotate independently.

### 2.3 Rotation budget

- Supervisor: rotate at first auto-compaction or approximately 80k live input tokens.
- Implementer: one vertical deliverable and at most one author-review-remediation cycle.
- Reviewer: one exact subject; a new exact semantic subject gets a fresh reviewer task.
- Polling/monitoring never lives in a substantive supervisor, author, or reviewer task.

The 80k value is a starting threshold. A 64k cap produced a 53%-56% theoretical replay
reduction in sampled WP6 records; 80k produced 44%-47%. Restart overhead makes a
30%-45% net reduction a more realistic initial expectation.

### 2.4 Context inheritance

- Self-contained implementer or independent reviewer: no inherited conversation history.
  In Codex, use `fork_turns="none"`.
- Direct continuation: a small positive turn count with an explicit reason.
- Full-history inheritance: exceptional, justified in the dispatch record, and
  prohibited after compaction.

Cold independent review is both cheaper and more independent.

### 2.5 Skill budget

Every brief records `lifecycle_phase`, at most two `primary_skills`, and conditional
secondary skills. Startup reads only OPEN observations matching selected skills plus
active cross-cutting principles. The full observation log is never emitted into model
context.

### 2.6 External review ownership

Stephen triggers and monitors CodeRabbit manually. Agents do not request, trigger,
poll, schedule, or wait on it unless explicitly instructed in the current task. Agents
process findings only after Stephen supplies them or says the review has concluded.

### 2.7 Certify before regenerate

A stage transition changes the decision or evidence sought; it does not imply rebuilding
deterministic artifacts. Before generation, inventory existing outputs and compare their
exact bytes and accepted identities with the new contract. Regenerate only after a
specific mismatch and within explicit authority.

### 2.8 Validation ladder

1. Edit loop: focused red/green check and lint for touched behavior.
2. Candidate head: affected package or contract gate.
3. Integration candidate: full relevant gate once.
4. Later exact-head change: rerun validation proportional to the changed semantic
   surface; never reuse an old-head claim without an explicit unchanged-surface proof.

### 2.9 Model routing

When Stephen authorizes model overrides:

| Work | Default routing |
|---|---|
| Status collection, packet maintenance, simple reconciliation | balanced model, medium effort |
| Bounded implementation with frozen contract | balanced model, high effort |
| Cross-surface architecture or adversarial acceptance | frontier model, high/xhigh effort |
| External-state monitoring | lightweight isolated task, never the substantive Manager |

Model routing never overrides an assurance requirement or independence rule.

### 2.10 Stacked-PR closure

A clean review stack is not integrated merely because every PR is individually
mergeable. Record the intended integration branch. Merge the bottom layer first,
retarget each surviving child PR to the integration branch, and re-verify that its
delta is exactly the reviewed layer before merging it. The final integration check
must prove every layer and accepted identity reachable from the integration head.
Never merge a child PR while it still targets an intermediate branch and call that
layer integrated.

## 3. Update map

| Target | Proposed change | Activation |
|---|---|---|
| `C:\Users\steph\.Codex\AGENTS.md` | Record Stephen-owned CodeRabbit operation | Applied 2026-07-22 from explicit user instruction |
| global `AGENTS.md` | Add large-workflow rotation, fork, and skill-budget rules | Applied 2026-07-22 after owner approval |
| repo `AGENTS.md` | Point WP-style campaigns to this protocol; retain worktree rules | Applied 2026-07-22 after owner approval |
| `.agents/skills/tda-large-workflow-supervision/SKILL.md` | New standalone certification/delivery supervision workflow; explicitly reject APM routing | Applied 2026-07-22; mirrored by sync tool |
| `.agents/skills/tda-task-brief-from-plan/SKILL.md` | Add lifecycle, context, fork, skill, external-review, and cycle fields | Applied 2026-07-22; mirrored by sync tool |
| `.agents/skills/tda-handoff/SKILL.md` | Make standalone repository handback paths first-class and remove `.apm` as the default for non-APM work | Applied 2026-07-22; mirrored by sync tool |
| `docs/guides/large-workflow-supervision.md` | Standalone task assignment, rotation, and evidence guidance | Applied 2026-07-22 |
| `tools/check_large_workflow_dispatch.py` | Optionally validate a strict standalone dispatch envelope and emit a positive budget signal | Separate implementation/review task after two successful trials |
| `tests/provenance/test_large_workflow_dispatch.py` | Negative controls including forbidden APM routing and review polling ownership | Same checker task |
| `CONVENTIONS.md` | Lock the protocol only after accepted trial evidence | Separate owner decision |

Skill edits must land in `.agents/skills`, be registered if a new skill is created, and
be mirrored through `tools/sync_agent_skills.py`; never edit the mirror directly.

## 4. Ready-to-paste instruction changes

### 4.1 Global or repository `AGENTS.md` block

```markdown
## Large-workflow context discipline

For multi-stage, review-heavy campaigns such as ARS work packages:

- First declare the workflow system. For `standalone`, do not load APM skills, state,
  Memory Bank, guides, or checkers.
- Keep current campaign state in a compact exact-state artifact. Rotate the
  coordinating task at first auto-compaction or approximately 80k live input
  tokens; do not rely on compaction as long-term continuity.
- Self-contained implementers and independent reviewers receive no parent conversation
  history (`fork_turns="none"` in Codex). A bounded positive fork is only for a
  direct continuation. Full-history inheritance requires an explicit reason and is
  forbidden after compaction.
- Each dispatch records lifecycle phase, context mode/budget, at most two primary
  skills, conditional skills, external-review owner, exact subject, one deliverable,
  validation ladder, and hard stops.
- Keep polling and external-review monitoring outside substantive supervisor, author,
  and reviewer tasks.
- Certify existing deterministic artifacts before authorizing regeneration.
```

### 4.2 Proposed standalone supervision skill

Add after the normal initiation reads:

```markdown
### Standalone large-workflow initiation

First declare `workflow_system: standalone`. Do not load APM skills, `.apm` state, the
APM Memory Bank, or APM guides/checkers. Select either `certify` or `deliver` supervision.
Certification may reconstruct the campaign and emit an exact-state packet. Delivery
starts from that packet, verifies its hash and current remote delta, then reads only the
selected deliverable's authorities and changed dependencies. Declare the rotation
threshold and one vertical action before dispatch.
```

### 4.3 `tda-handoff` standalone addition

Replace the user-only/context-window trigger with:

```markdown
For `workflow_system: standalone`, write the exact-state handback to the explicitly
authorized neutral repository path, never `.apm/memory`. Handoff is required when the
User requests it, at first auto-compaction, or when the declared context budget is
reached. It carries exact current state by identity and path, does not copy plans,
reports, or logs, and names one next vertical action plus hard stops.
```

### 4.4 `tda-task-brief-from-plan` template addition

```markdown
## Execution context
- Workflow system: standalone | apm
- Supervision phase: certify | deliver
- Lifecycle phase: plan | materialize | implement | review | remediate | integrate
- Context mode: fresh | bounded continuation
- Context budget: <tokens or observable rotation condition>
- Fork policy: none | <small positive count with reason>
- Primary skills: <maximum two>
- Conditional skills: <trigger -> skill>
- External-review owner: Stephen | not applicable
- Author-review cycle: <integer, normally 1>
```

### 4.5 Dispatch-envelope YAML

```yaml
workflow_system: standalone
lifecycle_phase: review
supervision_phase: deliver
context_mode: fresh
context_budget_tokens: 80000
fork_turns: none
primary_skills:
  - adversarial-design-review
conditional_skills:
  - trigger: produced result artifact exists
    skill: result-provenance-review
external_review_owner: stephen
author_review_cycle: 1
```

## 5. Proposed checker behavior

After two successful trials, add `check_large_workflow_dispatch.py` with an optional
`--dispatch-envelope <path>` argument. It should reject:

- absent exact subject, branch, workspace, or write owner;
- `fork_turns: all` for `lifecycle_phase: review`;
- more than two primary skills;
- missing rotation condition;
- `external_review_owner` other than `stephen` when CodeRabbit is named;
- a second author-review cycle without a fresh-task identity;
- generation authorization without a reuse/certification disposition;
- a stacked child PR whose base is not the declared integration branch at merge time;
- a stack closeout without final reachability proof for every reviewed layer;
- `workflow_system: standalone` combined with any APM skill, state path, guide, or
  checker.

The same change must include negative controls proving each rejection fires and a
positive execution signal in the rendered dispatch-readiness block. Do not make the
checker mandatory until two completed delivery trials demonstrate that the envelope is
stable, useful, and not duplicating authority already held elsewhere.

## 6. Trial and acceptance

V1 closed WP6.1 state reconstruction in a fresh standalone task and rotated at its
first compaction. It proved exact-state certification, fresh `fork_turns: none`
exploration, certify-before-regenerate behavior, and zero external-review waits without
dropped assurance. It did not dispatch T2, exercise implementation/review/remediation,
or produce exact token telemetry. It also incorrectly loaded an APM Manager skill.

V2 started from the V1 packet without repeating intake, rejected APM routing, stayed
below budget with zero compactions, and stopped before dispatch because T2 lacked an
accepted canonical transition family. It recorded:

- supervisor rotations and context at rotation;
- fork modes used;
- primary/conditional skill counts;
- duplicate generation avoided;
- focused versus full validation runs;
- review/remediation rounds;
- any dropped requirement or false stop attributable to the protocol.

The V2 verdict is `approve_advisory_integration` recommended. On Stephen's activation,
the documentation, AGENTS, standalone skill, task-brief, handoff, and neutral guide
updates may proceed through a normal reviewed PR. A later completed implementation/
review/remediation cycle may justify the mandatory checker, its negative controls, and
the `CONVENTIONS.md` lock.

## 7. Trial decision and deferred decisions

Stephen's APM correction is binding. The advisory defaults remain 80k/first-compaction
rotation, one implementer cycle, no-history independent review, at most two primary
skills, and a prose campaign packet rather than a mandatory schema.

Stephen accepted advisory AGENTS/skill/guide integration on 2026-07-22.
Mandatory checker enforcement and a `CONVENTIONS.md` lock remain separately deferred
until a completed implementation/review/remediation cycle supplies supporting evidence.
