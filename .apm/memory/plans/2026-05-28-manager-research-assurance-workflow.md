# Manager Research Assurance Workflow Strategy

Date: 2026-05-28

This file preserves the strategic Manager workflow for integrating APM with
Superpowers and TDL research-assurance practice. It is intentionally broader
than the early implementation checklist in
`.apm/memory/plans/2026-05-28-apm-research-assurance-integration.md`.

Companion strategic plans:

- `.apm/memory/plans/2026-05-28-worker-research-assurance-workflow.md`
- `.apm/memory/plans/2026-05-28-tdl-research-skillset-design.md`

## Purpose

The Manager checklist is the bridge between APM coordination and TDL scientific
validity. Specialized skills, contracts, schemas, and hooks can grow underneath
this workflow without disturbing APM's core dispatch/review mechanics.

## Manager Step 0: Session Recovery

Run normal APM Manager initiation or handoff recovery.

Checklist:

- Load Tracker, Plan, Spec, handoff, and relevant Worker logs.
- Check active bus files.
- Check active worktrees and branches.
- Surface pending reports, active tasks, and held tasks.
- Surface the `Research Validity Watchlist`.

Skills:

- APM initiation and handoff skills.
- Superpowers only if the session is about process design or debugging.

Output:

```text
Current state
Active work
Pending decisions
Research validity risks
Next Manager action
```

## Manager Step 1: Dispatch Assessment

Extend the existing APM `Dispatch Assessment` with a mandatory research section.

Add:

```text
Research Assurance Assessment:
- Which Ready tasks touch mathematical, statistical, topological, representation, output, or paper-claim logic?
- Which tasks are routine execution versus methodology-changing?
- Which tasks require pre-reg / contract / provenance checks before dispatch?
- Which tasks should remain held until a current result lands?
```

Skills:

- `research-assurance-triage`
- `brainstorming` only if task scope is changing

Output:

- dispatch mode: single / batch / parallel / wait
- research-risk classification for each candidate task

## Manager Step 2: Task Assurance Classification

For each task selected for dispatch, classify lanes:

```text
Topology
Stochastic / Null Model
Statistical / Panel
Representation
Output / Provenance
Paper Claim
```

Then classify each lane as:

```text
Machine-checkable
Human-review-only
Requires pre-reg amendment
Requires new contract
Requires output schema
Requires vault/CONVENTIONS lock
```

This is the key new Manager gate.

## Manager Step 3: Pre-Reg And Decision-Rule Check

Before writing the prompt, the Manager verifies:

```text
- Is there an existing pre-reg / decision rule?
- Are parameters explicit?
- Are stopping / Partial criteria explicit?
- Is the outcome-to-prose mapping explicit?
- Would this task need a pre-reg amendment?
```

For T1.2g-style cases, this is where the Manager catches: same-L design is
infeasible; a new asymmetric-L run requires amendment before dispatch.

Future skills:

- `pre-reg-to-dispatch`
- `statistical-design-audit` when decision rules or p-values are involved

## Manager Step 4: Contract And Validation Planning

The Manager decides what assurance artifacts are needed.

Possible artifacts:

- YAML contract
- binding test
- JSON schema validation
- smoke test
- canary result
- result-provenance checklist
- vault entry requirement
- paper-claim trace

Rule:

```text
Every machine-checkable research claim must either have a contract/test/schema,
or the Manager must explicitly state why it is not machine-checkable.
```

This replaces the narrower contract-extraction phase.

## Manager Step 5: Task Prompt Construction

The APM prompt remains canonical, but now includes an assurance block.

Add to Task Prompt:

```text
Research Assurance Requirements:
- Assurance lanes touched
- Contracts / schemas in scope
- Pre-reg or decision rule
- Parameters and seeds
- Output paths
- Provenance requirements
- Vault entries required
- Partial/failure criteria
```

Also include:

```text
If code reality conflicts with the assurance requirement, stop and report Partial.
Do not silently weaken the requirement.
```

## Manager Step 6: Pre-Dispatch Check

Before writing the bus file, run a short Manager self-check:

```text
- Is the prompt self-contained?
- Does it avoid "see Plan/Spec"?
- Are all result paths explicit?
- Are all parameters explicit?
- Are `.apm` root vs worktree paths explicit?
- Are contracts and validation commands explicit?
- Are vault/report duties explicit?
```

Potential future hook:

- `apm_task_prompt_check.py`

## Manager Step 7: Delivery

Normal APM:

- create branch/worktree if needed
- copy `.env` if needed
- clear report bus
- write task bus
- update Tracker
- direct User to Worker

No change, except the prompt now carries the assurance block.

## Manager Step 8: Report Review

Start with APM review, then apply assurance review.

Review checklist:

```text
APM consistency:
- Report matches Task Log.
- Claimed status matches evidence.
- Deliverables exist.
- Branch/commit state is clean or explained.

Verification:
- Tests pass.
- Contract validator passes.
- JSON schemas pass.
- Smoke/canary passed where required.

Research validity:
- Parameters match pre-reg/task prompt.
- Seeds recorded.
- B/L/null model/Markov order correct.
- p-value denominator correct.
- Cache provenance recorded.
- No overwritten results.
- Decision rule applied correctly.
- Paper-facing conclusion follows the result.
```

Skills:

- `verification-before-completion`
- `systematic-debugging` if anything contradicts
- future `result-provenance-review`
- lane-specific audit skill if the task touched high-risk math

## Manager Step 9: Outcome Decision

Four possible outcomes:

```text
Accept Success
Follow-up required
Planning/spec modification required
New task required
```

Important rule:

```text
A task can pass software tests and still fail research review.
```

If so, do not mark Done. Either issue follow-up or create a corrective task.

## Manager Step 10: Merge And State Update

Only after APM and assurance review pass:

- merge branch
- remove worktree if appropriate
- delete branch if appropriate
- update Tracker
- update Plan/Spec if findings changed scope
- update Working Notes
- ensure vault entries were actually written

Superpowers:

- Use `verification-before-completion` before saying "merged", "done", or
  "accepted".

## Manager Step 11: Handoff

Add a required handoff section:

```text
Research Validity Watchlist:
- provisional results
- superseded outputs
- pending contract gaps
- pre-reg amendments needed
- paper claims awaiting computation
- known null/model risks
- result files requiring cleanup or disclosure
```

This makes the next Manager inherit scientific-risk state, not just task state.

## Minimal First Implementation

Do not automate all of this at once. The first concrete integration is:

1. Add the Manager checklist to an APM guide or new skill.
2. Create `research-assurance-triage` as the first TDL skill.
3. Add a lightweight `apm_task_prompt_check.py` later, after the checklist
   stabilizes through live use.

## Relationship To Current Incremental Plan

The current early implementation plan has already completed:

- Manager dispatch and review baseline.
- Project-local `research-assurance-triage` skill.
- Worker-side `Research Assurance Evidence` workflow.

The next live test is T1.37 review. Hook generation should follow evidence from
that review rather than preempting it.
