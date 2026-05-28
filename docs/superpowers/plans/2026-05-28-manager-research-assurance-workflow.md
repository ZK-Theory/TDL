# Manager Research Assurance Workflow Strategy

> **For agentic workers:** This is a strategic workflow reference, not the step-by-step implementation checklist. Use it to preserve the target Manager process while executing the incremental plan in `2026-05-28-apm-research-assurance-integration.md`.

**Goal:** Preserve the full Manager workflow for integrating APM coordination, Superpowers discipline, and TDL research-validity review.

**Architecture:** APM remains canonical for state, dispatch, review, and handoff. Research assurance adds mandatory classification, pre-reg checks, artifact planning, Worker evidence, and scientific-risk handoff. Hooks and lane-specific skills are downstream implementation aids, not replacements for Manager judgment.

**Tech Stack:** APM Manager/Worker guides, project-local Codex skills, Markdown memory artifacts, YAML contracts, JSON schemas, Python hook scripts, result provenance checks, and vault logging.

---

## Recovery Note

`docs/` is ignored in this repository. The durable recovery copy is:

`.apm/memory/plans/2026-05-28-manager-research-assurance-workflow.md`

Companion strategic plans:

- `.apm/memory/plans/2026-05-28-worker-research-assurance-workflow.md`
- `.apm/memory/plans/2026-05-28-tdl-research-skillset-design.md`

## Strategic Workflow

### Manager Step 0: Session Recovery

Run normal APM Manager initiation or handoff recovery.

Checklist:

- Load Tracker, Plan, Spec, handoff, and relevant Worker logs.
- Check active bus files.
- Check active worktrees and branches.
- Surface pending reports, active tasks, and held tasks.
- Surface the `Research Validity Watchlist`.

Output:

```text
Current state
Active work
Pending decisions
Research validity risks
Next Manager action
```

### Manager Step 1: Dispatch Assessment

Extend the existing APM `Dispatch Assessment` with:

```text
Research Assurance Assessment:
- Which Ready tasks touch mathematical, statistical, topological, representation, output, or paper-claim logic?
- Which tasks are routine execution versus methodology-changing?
- Which tasks require pre-reg / contract / provenance checks before dispatch?
- Which tasks should remain held until a current result lands?
```

Output:

- dispatch mode: single / batch / parallel / wait
- research-risk classification for each candidate task

### Manager Step 2: Task Assurance Classification

Classify each selected task by lane:

```text
Topology
Stochastic / Null Model
Statistical / Panel
Representation
Output / Provenance
Paper Claim
```

Then classify each lane:

```text
Machine-checkable
Human-review-only
Requires pre-reg amendment
Requires new contract
Requires output schema
Requires vault/CONVENTIONS lock
```

### Manager Step 3: Pre-Reg And Decision-Rule Check

Before writing the prompt, verify:

```text
- Is there an existing pre-reg / decision rule?
- Are parameters explicit?
- Are stopping / Partial criteria explicit?
- Is the outcome-to-prose mapping explicit?
- Would this task need a pre-reg amendment?
```

This is where T1.2g-style asymmetric-L issues are caught before dispatch.

### Manager Step 4: Contract And Validation Planning

Choose assurance artifacts:

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

### Manager Step 5: Task Prompt Construction

APM prompt remains canonical, with:

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

### Manager Step 6: Pre-Dispatch Check

Before writing the bus file:

```text
- Is the prompt self-contained?
- Does it avoid "see Plan/Spec"?
- Are all result paths explicit?
- Are all parameters explicit?
- Are `.apm` root vs worktree paths explicit?
- Are contracts and validation commands explicit?
- Are vault/report duties explicit?
```

Potential future hook: `apm_task_prompt_check.py`.

### Manager Step 7: Delivery

Normal APM:

- create branch/worktree if needed
- copy `.env` if needed
- clear report bus
- write task bus
- update Tracker
- direct User to Worker

The prompt now carries the assurance block.

### Manager Step 8: Report Review

Start with APM review, then apply assurance review:

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

### Manager Step 9: Outcome Decision

Possible outcomes:

```text
Accept Success
Follow-up required
Planning/spec modification required
New task required
```

Rule:

```text
A task can pass software tests and still fail research review.
```

### Manager Step 10: Merge And State Update

Only after APM and assurance review pass:

- merge branch
- remove worktree if appropriate
- delete branch if appropriate
- update Tracker
- update Plan/Spec if findings changed scope
- update Working Notes
- ensure vault entries were actually written

### Manager Step 11: Handoff

Required handoff section:

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

## Minimal First Implementation

1. Add the Manager checklist to an APM guide or new skill.
2. Create `research-assurance-triage` as the first TDL skill.
3. Add a lightweight `apm_task_prompt_check.py` later, after the checklist stabilizes through live use.

The Manager checklist is the bridge. Specialized skills can grow underneath it without disturbing APM.
