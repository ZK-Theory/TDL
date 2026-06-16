---
type: discovery-pre-reg-to-dispatch
created: 2026-06-16
candidate_slug: strand-persistence-survival-testing
verdict: execute-existing-design
state: dispatch-ready
---

# STRAND pre-reg-to-dispatch packet

## Verdict

**execute existing design.** The STRAND Spike pre-registration is locked, the JSON mirror exists, the Spike result validated as `success`, and the next action is a bounded APM task comparing STRAND against existing W2 and persistence-landscape baselines. No pre-registration amendment is needed if the worker keeps the parameters and decision rule below. Any full-scale paper computation, changed null model, changed statistic, changed maximum-null subset, or paper-facing claim requires an amendment before dispatch.

## Locked Parameters

- Candidate: `strand-persistence-survival-testing`
- Governing pre-registration: `vault/00-Meta/Discovery/strand-persistence-survival-testing-spike-prereg.md`
- Machine-readable mirror: `vault/00-Meta/Discovery/strand-persistence-survival-testing-spike-prereg.json`
- Registered at: `2026-06-16`
- Approved by: `Stephen` on `2026-06-16`
- Time box: `4` hours
- Metric space: Existing P01-B Vietoris-Rips persistence diagrams represented by finite feature lifetimes and empirical persistence-survival functions.
- Toy dataset: existing P01-B USoc and BHPS observed diagrams plus cached permutation-null diagrams
- Max units/null diagrams: `100`
- Compute budget: Bounded toy compute using at most 100 cached null diagrams per dataset and existing diagram files only.
- Null operation: Compare observed persistence-lifetime survival summaries to cached permutation-null diagrams; toy p-values permute observed-vs-null labels across diagram-level STRAND statistics.
- Invariance risk: The null must perturb the diagram lifetimes consumed by STRAND, not merely reorder features within a fixed diagram.
- Baselines: W2 permutation test, landscape L2 permutation test
- Planned contracts: spike-result-summary

## Decision Rule

Success criteria:
- STRAND finite-lifetime summaries can be computed for H0 and H1 on the toy subset.
- A survival-effect statistic and Monte Carlo/permutation null are explicitly defined.
- The null operation changes the STRAND input summaries for at least one non-identity null draw.
- The toy result can be compared in direction against existing W2 and landscape L2 outputs.

Failure criteria:
- No implementable STRAND summary is available from existing diagrams.
- The null operation is invariant to the STRAND input.
- Result provenance is insufficient to reconstruct source diagrams, subset size, statistic, and seed.


Outcome-to-prose mapping:
- success: Open a pre-reg-to-dispatch handoff for a bounded APM task comparing STRAND against current baselines.
- partial: Record the implementation or design gap and park until method details or artifacts improve.
- failure: Write a NEGATIVE note and keep current W2/landscape testing.

## Research Assurance Requirements

- **Assurance lanes touched:** Topology; Stochastic / Null Model; Statistical / Panel; Representation; Output / Provenance; Paper Claim.
- **Contracts / schemas in scope:** `contracts/discovery-harness/spike-pre-registration.yaml`, `contracts/discovery-harness/spike-result-summary.yaml`, `contracts/manifests/discovery-harness.yaml`, `tests/discovery/test_spike_preregistration_contract.py`, `tests/discovery/test_spike_result_contract.py`, `tests/discovery/test_strand_spike_compute.py`.
- **Pre-registration or decision rule:** Use `vault/00-Meta/Discovery/strand-persistence-survival-testing-spike-prereg.md` and JSON mirror `vault/00-Meta/Discovery/strand-persistence-survival-testing-spike-prereg.json`. Execute the locked toy comparative design only. Stop for amendment before changing the statistic, null operation, toy scope, decision rule, or prose mapping.
- **Parameters and seeds:** Use existing P01-B observed diagrams and cached permutation-null diagrams named by `results/discovery/strand_persistence_survival_spike_2026-06-16.json`; max 100 cached null diagrams per dataset unless an amendment is filed; seed/provenance inherited from caches (`seed=42`, `B=1000`, `L=5000` in cache metadata).
- **Output paths:** Write new comparative outputs under `results/discovery/` with a date suffix. Do not overwrite the existing Spike output; if rerunning the same file is required, stop and ask for a new output path.
- **Provenance requirements:** Output must record source cache paths, observed diagram source, homology dimensions, statistic definition, null-null reference construction, p-value formula `(r + 1) / (n + 1)`, null subset size, and baseline files read.
- **Vault entries required:** On completion, write a result note under `vault/00-Meta/Discovery/` that references the governing pre-registration, JSON mirror, output artifact, and any amendment if one was required.
- **Partial/failure criteria:** Report Partial rather than silently weakening a requirement if cached diagrams are missing, the null is invariant to STRAND inputs, the output cannot be reproduced from recorded paths, or the worker needs to alter the locked parameters.
- **Human-review-only claims:** Whether STRAND adds publishable value beyond W2/landscape baselines is a human research judgment after the comparative task. The worker may report evidence but must not make a paper-facing adoption claim.

If code reality conflicts with the assurance requirement, stop and report Partial. Do not silently weaken the requirement.

## Dispatch-ready Task Prompt Skeleton

```yaml
schema_version: discovery-agent-task/v1
task_id: discovery-strand-comparison-001
agent: tda-agent
objective: Run the bounded STRAND-vs-baseline comparison described in this packet without changing the locked Spike design.
inputs:
  - vault/00-Meta/Discovery/strand-persistence-survival-testing-spike-prereg.md
  - vault/00-Meta/Discovery/strand-persistence-survival-testing-spike-prereg.json
  - vault/00-Meta/Discovery/strand-persistence-survival-testing-spike-result.md
  - results/discovery/strand_persistence_survival_spike_2026-06-16.json
  - trajectory_tda/discovery/strand_spike.py
outputs:
  - results/discovery/<date-suffixed-strand-comparison>.json
  - vault/00-Meta/Discovery/<date-suffixed-strand-comparison-result>.md
acceptance_criteria:
  - The output exists at the declared path and records all provenance requirements.
  - The governing pre-registration JSON is unchanged.
  - Discovery Harness tests and contract binding checks pass.
  - Research Assurance Evidence is reported lane-by-lane.
research_assurance:
  lanes:
    - topology
    - stochastic-null-model
    - statistical-panel
    - representation
    - output-provenance
    - paper-claim
  governing_artifacts:
    - vault/00-Meta/Discovery/strand-persistence-survival-testing-spike-prereg.json
    - contracts/discovery-harness/spike-pre-registration.yaml
    - contracts/discovery-harness/spike-result-summary.yaml
```
