---
name: spike
description: Use when a Discovery Harness candidate has PROMOTE from /assay and needs a toy-scale feasibility probe, pre-registration, null-model check, or handoff into /pre-reg-to-dispatch.
---

# Spike

Time-boxed feasibility probe for a promoted Discovery Harness candidate. A Spike
is the last front-of-funnel step before APM execution: it confirms that the
metric space exists in practice, a toy signal can be detected or ruled out, and
the null model is well-defined.

## Core Rule

No speculative path becomes an APM task without a locked Spike pre-registration.
PROMOTE from `/assay` is a recommendation; do not run the Spike until Stephen has
explicitly approved the PROMOTE decision.

## Pre-flight Self-check

Before running or dispatching any Spike, re-confirm:

1. The candidate backlog entry has `state: assayed` and `decision: PROMOTE`.
2. Stephen explicitly approved this candidate for Spike.
3. The Assay scorecard validates with
   `trajectory_tda.discovery.assay_scorecard.validate_assay_scorecard`.
4. The Spike pre-registration validates with
   `trajectory_tda.discovery.spike_preregistration.validate_spike_preregistration`.
5. The probe is toy-scale only: `time_box_hours` between 1 and 4, bounded data,
   no full paper computation, no APM worktree yet.

## Procedure

1. **Read evidence.** Read `_backlog.md`, the candidate scorecard, the source
   inbox note, and the relevant plan section (`Discovery-Harness-Plan-16-06-2026`
   section 6).
2. **Write the pre-registration first.** Create
   `vault/00-Meta/Discovery/<slug>-spike-prereg.md` with the fenced block below.
   Validate it before doing any compute or handoff.
3. **Route assurance checks.** For the toy probe, identify the touched lanes:
   topology, null model/statistical design, representation, output/provenance.
   Reuse the lane skills named in the plan; do not create a parallel assurance
   checklist.
4. **Run only the smallest feasible probe.** Use existing artifacts where
   possible. Confirm the metric-space object can be constructed, a toy signal or
   negative result can be stated, and the null operation perturbs the actual
   Spike input.
5. **Record the result.**
   - Success: write a Spike result note, update `_backlog.md` to `spiked`, and
     pass the locked pre-registration to `/pre-reg-to-dispatch`.
   - Partial: write exactly what was feasible and what blocked full success;
     update `_backlog.md` with `parked` or a narrower revisit trigger.
   - Failure: write a `[NEGATIVE]` note and update `_backlog.md` with KILL/PARK
     reason. Feed any durable lesson back into Scout watchlist terms if useful.

## Pre-registration Block

Use this exact fenced block label:

````markdown
```yaml spike_preregistration
schema_version: discovery/spike-pre-registration/v1
candidate_slug: strand-persistence-survival-testing
source_scorecard: vault/00-Meta/Discovery/strand-persistence-survival-testing.md
registered_at: "2026-06-16"
approval:
  approved: true
  approved_by: Stephen
  approved_at: "2026-06-16"
time_box_hours: 4
research_question: Can STRAND add calibrated persistence-diagram testing power?
metric_space: Persistence diagrams already produced by P01-B.
toy_scope:
  dataset: existing P01-B diagrams
  max_units: 100
  compute_budget: toy subset only
topology_gate:
  assay_gate_passed: true
  feature_claim_map: STRAND survival curves localise group differences.
  named_baseline: Existing W2 and landscape L2 permutation tests.
null_model:
  operation: reuse the existing label/permutation null at toy scale
  invariance_risk: STRAND must consume the perturbed diagram summaries, not cached labels.
baselines:
  - W2 permutation test
  - landscape L2 permutation test
decision_rule:
  success_criteria:
    - STRAND can be computed on the toy subset.
    - A test statistic and null are explicitly defined.
  failure_criteria:
    - No implementable STRAND summary is available.
    - The null operation does not perturb the STRAND input.
outcome_to_prose:
  success: Open an APM task to compare STRAND against current baselines.
  partial: Record implementation gap and park until method details improve.
  failure: Write a NEGATIVE note and keep current W2/landscape testing.
planned_contracts:
  - spike-result-summary
next_on_success: /pre-reg-to-dispatch
next_on_failure: write [NEGATIVE] note and update Discovery backlog
```
````

The enforcing contract is `contracts/discovery-harness/spike-pre-registration.yaml`;
the binding test is `tests/discovery/test_spike_preregistration_contract.py`.

## Validation Snippet

```python
from pathlib import Path
import yaml
from trajectory_tda.discovery.spike_preregistration import (
    validate_spike_preregistration,
)

text = Path("vault/00-Meta/Discovery/<slug>-spike-prereg.md").read_text(encoding="utf-8")
block = text.split("```yaml spike_preregistration", 1)[1].split("```", 1)[0]
validate_spike_preregistration(yaml.safe_load(block))
```

## Escalate Or Stop When

- Approval is missing. Do not infer approval from a PROMOTE scorecard.
- The Spike would exceed toy scale or quietly become a full paper computation.
- The null operation would not perturb the object consumed by the Spike.
- Success would bypass `/pre-reg-to-dispatch` and go straight to APM execution.
- A parallel-compute cost estimate is extrapolated from a single `(n_jobs, batch)`
  configuration. Sweep the worker count (at least `n_jobs ∈ {1, N/2, N}`) on a warm
  pool and time strictly more units than workers. A flat per-unit curve means the
  workload is memory/IO-bound — it does not parallelise; cost it at the serial rate
  and escalate early rather than projecting from one optimistic point.
