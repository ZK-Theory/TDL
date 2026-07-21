---
name: spike
description: Use when a Discovery Harness candidate has PROMOTE from /assay and needs a toy-scale feasibility probe, pre-registration, null-model check, or handoff into /pre-reg-to-dispatch.
metadata:
  version: "1.0.0"
  tier: domain
  lanes:
    - topology
    - stochastic-null
  roles:
    - implementer
    - orchestrator
  runtime: agnostic
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
6. If the Spike's value proposition is framed as "certifies/licenses step X in
   the pipeline" (a theorem, a preprocessing step, a scaling mechanism), grep
   the codebase to confirm step X actually exists as described before locking
   the pre-registration — or write an explicit "X is planned, adoption-gated"
   annotation naming the gate. A formal or methodological argument can be
   correct and still license nothing the codebase does; the empirical referent
   is a checkable claim, not an inherited assumption from the framing memo.

## Procedure

1. **Read evidence.** Read `_backlog.md`, the candidate scorecard, the source
   inbox note, and the relevant plan section (`Discovery-Harness-Plan-16-06-2026`
   section 6).
2. **Write the pre-registration first.** Create
   `vault/00-Meta/Discovery/<slug>-spike-prereg.md` with the fenced block below.
   Validate it before doing any compute or handoff. Default `decision_rule` to a
   **two-sided** test unless a directional argument is explicitly recorded: at
   spike stage nobody has seen the statistic's direction on real data, and a
   pre-committed one-sided rule ("observed > 95th percentile") turns a strong
   finding in the opposite direction into an indistinguishable-from-noise FAIL.
   Report both tails in the result note regardless of which rule is registered,
   so a wrong-tail landing stays visible. Reserve one-sided rules for a full
   dispatch pre-reg where prior evidence already supports a direction.
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

## Toy Probe Execution Notes

- **WSL background compute.** WSL 2 processes die with their parent session —
  `wsl bash -c "... &"`, `Start-Process wsl ... -PassThru`, and PowerShell
  `Start-Job { Start-Process wsl ... }` all silently fail for a long-running
  probe (output file stays empty, no error). Use the Bash tool's
  `run_in_background: true` directly; it is the only mechanism that survives
  across tool calls. Even under `run_in_background`, an inner `wsl bash -c
  '...'` can fail exit-127 with a misleading "No such file or directory" —
  the background wrapper breaks single-quoted `bash -c` payloads, and MSYS
  rewrites absolute POSIX paths into Git-Bash-rooted Windows paths. Launch as
  a direct exec instead, no inner shell: `MSYS_NO_PATHCONV=1 wsl.exe
  <absolute-wsl-python> -u <script-via-/mnt/c/...>`. Reserve `wsl bash -c` for
  short foreground commands only.
- **Progress logging for long background probes.** `python -u` only
  unbuffers Python's own stdout; the shell reading that pipe (PowerShell
  `*>`, similar OS-level redirects) can still buffer it, so the on-disk log
  can lag a live process by minutes — exactly when a mid-run budget/kill
  decision needs real timings. A lone WSL `fstab` mount warning in the output
  file is not a failure signal either way. Make the probe self-log: append
  each progress line to a plain file with an explicit `flush()` (or a
  `logging` handler configured unbuffered), and read that file for status.
  Owning the progress signal inside the process removes the shell's
  buffering from the observability path entirely.
- **Categorical partition inputs (e.g. MCbiF).** When the toy input is panel
  data with categorical states (employment state, deprivation band), the
  partition at each wave is the state label directly — do not introduce
  k-means or re-embedding as an intermediary unless the underlying space is
  genuinely continuous or high-dimensional. Verify whether the feature claim
  concerns the categorical state sequence or the embedding geometry before
  choosing the construction method; a frozen embedding built for trajectory-
  geometry tasks is not automatically the right input for a categorical
  partition probe.
- **Budget-reduced grids: order for a clean truncation.** When per-cell cost
  is uncertain or possibly super-linear, a wall-time/budget STOP is likely to
  truncate the run before the full grid completes. Sequence the loop so the
  smallest COMPLETE, INTERPRETABLE design — every rung including the negative
  control, at the cheapest parameter setting — finishes first, and every
  later block only adds resolution; never let one expensive arm starve the
  control by running rung-major with the slow rung first. Pair with per-cell
  checkpoint flushing so a STOP is a clean truncation of a valid design, not a
  half-built one, and benchmark the per-cell cost's *scaling* (not one point)
  before committing the grid.
- **Fresh-worktree venv provisioning.** If a Spike runs inside an APM
  worktree, `uv sync` failures on source-built optional dependencies and
  file-lock contention from concurrent `uv run` calls are covered in
  `using-git-worktrees-extras`, not here.

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
  and escalate early rather than projecting from one optimistic point. Also confirm
  the sweep's call count is a meaningful fraction of the target run's scale — a
  worker-count sweep at a fraction of target scale (even if fully swept) is
  PROVISIONAL evidence only; say so explicitly before a real launch is approved on
  it, and confirm the benchmark timed the production entry point, not a component
  kernel.
